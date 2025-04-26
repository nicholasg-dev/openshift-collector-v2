"""
Scheduler module for handling background data collection tasks.
"""

import logging
import time
import datetime
import os
import json
from flask import current_app
from flask_apscheduler import APScheduler
from app.collector.openshift_collector import (
    get_basic_info, get_nodes_detailed, get_operators_info, get_etcd_info,
    get_namespaces_list, get_resources_for_namespace, get_cluster_resources,
    get_network_info, get_storage_info, get_security_info, get_metrics_info,
    get_events_info
)

# Initialize scheduler
scheduler = APScheduler()

# Initialize logger
logger = logging.getLogger(__name__)

# Collection history
collection_history = []
collection_stats = {
    'total': 0,
    'successful': 0,
    'failed': 0,
    'avg_duration': 0
}

# Collection status
collection_status = {
    'status': 'idle',
    'last_collection': None,
    'next_collection': None,
    'interval': 3600,  # Default to hourly
    'schedule': 'Every hour'
}

def init_app(app):
    """Initialize the scheduler with the Flask app."""
    scheduler.init_app(app)
    scheduler.start()
    
    # Load collection history if exists
    _load_collection_history()
    
    # Schedule the collection job
    _schedule_collection_job()
    
    # Register API endpoints
    _register_api_endpoints(app)

def _schedule_collection_job():
    """Schedule the collection job based on the configured interval."""
    # Remove existing job if it exists
    if scheduler.get_job('collect_data'):
        scheduler.remove_job('collect_data')
    
    # Schedule new job
    interval = collection_status['interval']
    scheduler.add_job(
        id='collect_data',
        func=collect_data,
        trigger='interval',
        seconds=interval,
        next_run_time=datetime.datetime.now() + datetime.timedelta(seconds=interval)
    )
    
    # Update next collection time
    collection_status['next_collection'] = datetime.datetime.now() + datetime.timedelta(seconds=interval)
    collection_status['schedule'] = f'Every {_format_interval(interval)}'
    
    logger.info(f"Scheduled collection job to run every {_format_interval(interval)}")

def _format_interval(seconds):
    """Format interval in seconds to a human-readable string."""
    if seconds < 60:
        return f"{seconds} seconds"
    elif seconds < 3600:
        return f"{seconds // 60} minutes"
    elif seconds < 86400:
        return f"{seconds // 3600} hours"
    else:
        return f"{seconds // 86400} days"

def _load_collection_history():
    """Load collection history from file."""
    history_file = os.path.join(current_app.instance_path, 'collection_history.json')
    if os.path.exists(history_file):
        try:
            with open(history_file, 'r') as f:
                data = json.load(f)
                global collection_history, collection_stats, collection_status
                collection_history = data.get('history', [])
                collection_stats = data.get('stats', collection_stats)
                status_data = data.get('status', {})
                
                # Only update certain fields
                if 'interval' in status_data:
                    collection_status['interval'] = status_data['interval']
                if 'schedule' in status_data:
                    collection_status['schedule'] = status_data['schedule']
                if 'last_collection' in status_data:
                    collection_status['last_collection'] = status_data['last_collection']
                
                logger.info(f"Loaded collection history: {len(collection_history)} entries")
        except Exception as e:
            logger.error(f"Error loading collection history: {e}")

def _save_collection_history():
    """Save collection history to file."""
    history_file = os.path.join(current_app.instance_path, 'collection_history.json')
    try:
        # Ensure instance directory exists
        os.makedirs(os.path.dirname(history_file), exist_ok=True)
        
        with open(history_file, 'w') as f:
            json.dump({
                'history': collection_history,
                'stats': collection_stats,
                'status': collection_status
            }, f, indent=2, default=str)
        
        logger.info(f"Saved collection history: {len(collection_history)} entries")
    except Exception as e:
        logger.error(f"Error saving collection history: {e}")

def collect_data():
    """Collect data from the OpenShift cluster."""
    from app import create_app  # Import here to avoid circular imports
    app = create_app()
    with app.app_context():
        # Update status
        collection_status['status'] = 'running'
        start_time = time.time()
        success = False
        items_collected = 0
        error_details = None
        try:
            logger.info("Starting data collection")
            kubeconfig = current_app.config.get('KUBECONFIG_PATH')
            data = {}
            logger.info("Collecting basic cluster info")
            data['basic_info'] = get_basic_info(kubeconfig)
            items_collected += 1
            logger.info("Collecting nodes info")
            data['nodes'] = get_nodes_detailed(kubeconfig)
            items_collected += 1
            logger.info("Collecting operators info")
            data['operators'] = get_operators_info(kubeconfig)
            items_collected += 1
            logger.info("Collecting etcd info")
            data['etcd'] = get_etcd_info(kubeconfig)
            items_collected += 1
            logger.info("Collecting network info")
            data['network'] = get_network_info(kubeconfig)
            items_collected += 1
            logger.info("Collecting storage info")
            data['storage'] = get_storage_info(kubeconfig)
            items_collected += 1
            logger.info("Collecting security info")
            data['security'] = get_security_info(kubeconfig)
            items_collected += 1
            logger.info("Collecting metrics info")
            data['metrics'] = get_metrics_info(kubeconfig)
            items_collected += 1
            logger.info("Collecting events info")
            data['events'] = get_events_info(kubeconfig)
            items_collected += 1
            logger.info("Collecting cluster resources")
            data['cluster_resources'] = get_cluster_resources(kubeconfig)
            items_collected += 1
            logger.info("Collecting namespaces list")
            namespaces = get_namespaces_list(kubeconfig)
            data['namespaces'] = namespaces
            items_collected += 1
            logger.info("Collecting namespace resources (limited to 5)")
            data['namespace_resources'] = {}
            for namespace in namespaces[:5]:
                logger.info(f"Collecting resources for namespace: {namespace}")
                data['namespace_resources'][namespace] = get_resources_for_namespace(namespace, kubeconfig)
                items_collected += 1
            _save_collected_data(data)
            success = True
            logger.info(f"Data collection completed successfully. Collected {items_collected} items.")
        except Exception as e:
            logger.error(f"Error during data collection: {e}")
            error_details = str(e)
            success = False
        end_time = time.time()
        duration = end_time - start_time
        collection_entry = {
            'timestamp': datetime.datetime.now(),
            'status': 'success' if success else 'error',
            'duration': duration,
            'items_collected': items_collected,
            'details': error_details if error_details else None
        }
        collection_history.append(collection_entry)
        if len(collection_history) > 50:
            collection_history.pop(0)
        collection_stats['total'] += 1
        if success:
            collection_stats['successful'] += 1
        else:
            collection_stats['failed'] += 1
        total_duration = sum(entry['duration'] for entry in collection_history)
        collection_stats['avg_duration'] = total_duration / len(collection_history)
        collection_status['status'] = 'idle'
        collection_status['last_collection'] = datetime.datetime.now()
        _save_collection_history()
        return success

def _save_collected_data(data):
    """Save collected data to file."""
    data_dir = os.path.join(current_app.instance_path, 'collected_data')
    os.makedirs(data_dir, exist_ok=True)
    
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    data_file = os.path.join(data_dir, f'collection_{timestamp}.json')
    
    try:
        with open(data_file, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        
        logger.info(f"Saved collected data to {data_file}")
    except Exception as e:
        logger.error(f"Error saving collected data: {e}")

def _register_api_endpoints(app):
    """Register API endpoints for the scheduler."""
    from flask import jsonify, request
    
    @app.route('/api/v2/collection-status')
    def api_collection_status():
        """API endpoint to get collection status."""
        return jsonify({
            'status': collection_status['status'],
            'last_collection': collection_status['last_collection'],
            'next_collection': collection_status['next_collection'],
            'interval': collection_status['interval'],
            'schedule': collection_status['schedule'],
            'stats': collection_stats,
            'history': collection_history
        })
    
    @app.route('/api/v2/run-collection', methods=['POST'])
    def api_run_collection():
        """API endpoint to run collection manually."""
        if collection_status['status'] == 'running':
            return jsonify({
                'success': False,
                'error': 'Collection is already running'
            })
        
        # Run collection in a separate thread
        from threading import Thread
        thread = Thread(target=collect_data)
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'success': True,
            'message': 'Collection started'
        })
    
    @app.route('/api/v2/update-interval', methods=['POST'])
    def api_update_interval():
        """API endpoint to update collection interval."""
        data = request.json
        interval = data.get('interval')
        
        if not interval or not isinstance(interval, int) or interval < 60:
            return jsonify({
                'success': False,
                'error': 'Invalid interval. Must be an integer >= 60.'
            })
        
        # Update interval
        collection_status['interval'] = interval
        
        # Reschedule collection job
        _schedule_collection_job()
        
        # Save collection history
        _save_collection_history()
        
        return jsonify({
            'success': True,
            'message': f'Collection interval updated to {_format_interval(interval)}'
        })
    
    @app.route('/api/v2/configuration', methods=['GET', 'POST'])
    def api_configuration():
        """API endpoint to get or update configuration."""
        if request.method == 'GET':
            return jsonify({
                'kubeconfig_path': current_app.config.get('KUBECONFIG_PATH'),
                'parallel_jobs': current_app.config.get('PARALLEL_JOBS', 4),
                'enable_cloud_collection': current_app.config.get('ENABLE_CLOUD_COLLECTION', False),
                'enable_ssh_collection': current_app.config.get('ENABLE_SSH_COLLECTION', False),
                'collection_timeout': current_app.config.get('COLLECTION_TIMEOUT', 60),
                'retry_attempts': current_app.config.get('RETRY_ATTEMPTS', 2),
                'retry_delay': current_app.config.get('RETRY_DELAY', 2),
                'log_level': current_app.config.get('LOG_LEVEL', 'INFO')
            })
        else:
            data = request.json
            
            # Update config
            for key, value in data.items():
                if key.upper() in current_app.config:
                    current_app.config[key.upper()] = value
            
            # Save config to instance/config.py
            config_file = os.path.join(current_app.instance_path, 'config.py')
            os.makedirs(os.path.dirname(config_file), exist_ok=True)
            
            try:
                with open(config_file, 'w') as f:
                    f.write("# Instance-specific configuration\n")
                    for key, value in data.items():
                        if isinstance(value, str):
                            f.write(f"{key.upper()} = '{value}'\n")
                        else:
                            f.write(f"{key.upper()} = {value}\n")
                
                return jsonify({
                    'success': True,
                    'message': 'Configuration updated'
                })
            except Exception as e:
                logger.error(f"Error saving configuration: {e}")
                return jsonify({
                    'success': False,
                    'error': f'Error saving configuration: {e}'
                })
