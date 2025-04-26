"""
Export module for generating reports from collected data.
"""

import os
import json
import datetime
import logging
import uuid
from flask import current_app, url_for, render_template, send_file
import weasyprint

# Initialize logger
logger = logging.getLogger(__name__)

# Exports history
exports = []

def init_app(app):
    """Initialize the export module with the Flask app."""
    # Load exports history if exists
    _load_exports_history()
    
    # Register API endpoints
    _register_api_endpoints(app)

def _load_exports_history():
    """Load exports history from file."""
    exports_file = os.path.join(current_app.instance_path, 'exports_history.json')
    if os.path.exists(exports_file):
        try:
            with open(exports_file, 'r') as f:
                global exports
                exports = json.load(f)
                logger.info(f"Loaded exports history: {len(exports)} entries")
        except Exception as e:
            logger.error(f"Error loading exports history: {e}")

def _save_exports_history():
    """Save exports history to file."""
    exports_file = os.path.join(current_app.instance_path, 'exports_history.json')
    try:
        # Ensure instance directory exists
        os.makedirs(os.path.dirname(exports_file), exist_ok=True)
        
        with open(exports_file, 'w') as f:
            json.dump(exports, f, indent=2, default=str)
        
        logger.info(f"Saved exports history: {len(exports)} entries")
    except Exception as e:
        logger.error(f"Error saving exports history: {e}")

def _get_latest_collection_data():
    """Get the latest collection data."""
    data_dir = os.path.join(current_app.instance_path, 'collected_data')
    if not os.path.exists(data_dir):
        return None
    
    # Get the latest collection file
    collection_files = [f for f in os.listdir(data_dir) if f.startswith('collection_') and f.endswith('.json')]
    if not collection_files:
        return None
    
    latest_file = max(collection_files)
    latest_file_path = os.path.join(data_dir, latest_file)
    
    try:
        with open(latest_file_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading collection data: {e}")
        return None

def generate_pdf_report(sections=None, title=None, include_timestamp=True, include_charts=True, include_raw_data=False):
    """Generate a PDF report from collected data."""
    # Get the latest collection data
    data = _get_latest_collection_data()
    if not data:
        return None, "No collection data available"
    
    # Filter sections if specified
    if sections:
        data = {k: v for k, v in data.items() if k in sections}
    
    # Generate HTML report
    html = render_template(
        'reports/pdf_report.html',
        data=data,
        title=title or "OpenShift Cluster Documentation",
        timestamp=datetime.datetime.now() if include_timestamp else None,
        include_charts=include_charts,
        include_raw_data=include_raw_data
    )
    
    # Generate PDF from HTML
    exports_dir = os.path.join(current_app.instance_path, 'exports')
    os.makedirs(exports_dir, exist_ok=True)
    
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    export_id = str(uuid.uuid4())
    pdf_file = os.path.join(exports_dir, f'report_{timestamp}_{export_id}.pdf')
    
    try:
        weasyprint.HTML(string=html).write_pdf(pdf_file)
        
        # Add to exports history
        export_entry = {
            'id': export_id,
            'date': datetime.datetime.now().isoformat(),
            'type': 'pdf',
            'sections': sections or list(data.keys()),
            'file': pdf_file,
            'size': os.path.getsize(pdf_file),
            'url': url_for('main.download_export', export_id=export_id, _external=True)
        }
        
        exports.append(export_entry)
        _save_exports_history()
        
        return pdf_file, None
    except Exception as e:
        logger.error(f"Error generating PDF report: {e}")
        return None, f"Error generating PDF report: {e}"

def generate_html_report(sections=None, title=None, include_timestamp=True, include_charts=True, include_raw_data=False):
    """Generate an HTML report from collected data."""
    # Get the latest collection data
    data = _get_latest_collection_data()
    if not data:
        return None, "No collection data available"
    
    # Filter sections if specified
    if sections:
        data = {k: v for k, v in data.items() if k in sections}
    
    # Generate HTML report
    html = render_template(
        'reports/html_report.html',
        data=data,
        title=title or "OpenShift Cluster Documentation",
        timestamp=datetime.datetime.now() if include_timestamp else None,
        include_charts=include_charts,
        include_raw_data=include_raw_data
    )
    
    # Save HTML report
    exports_dir = os.path.join(current_app.instance_path, 'exports')
    os.makedirs(exports_dir, exist_ok=True)
    
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    export_id = str(uuid.uuid4())
    html_file = os.path.join(exports_dir, f'report_{timestamp}_{export_id}.html')
    
    try:
        with open(html_file, 'w') as f:
            f.write(html)
        
        # Add to exports history
        export_entry = {
            'id': export_id,
            'date': datetime.datetime.now().isoformat(),
            'type': 'html',
            'sections': sections or list(data.keys()),
            'file': html_file,
            'size': os.path.getsize(html_file),
            'url': url_for('main.download_export', export_id=export_id, _external=True)
        }
        
        exports.append(export_entry)
        _save_exports_history()
        
        return html_file, None
    except Exception as e:
        logger.error(f"Error generating HTML report: {e}")
        return None, f"Error generating HTML report: {e}"

def generate_json_export(sections=None):
    """Generate a JSON export from collected data."""
    # Get the latest collection data
    data = _get_latest_collection_data()
    if not data:
        return None, "No collection data available"
    
    # Filter sections if specified
    if sections:
        data = {k: v for k, v in data.items() if k in sections}
    
    # Save JSON export
    exports_dir = os.path.join(current_app.instance_path, 'exports')
    os.makedirs(exports_dir, exist_ok=True)
    
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    export_id = str(uuid.uuid4())
    json_file = os.path.join(exports_dir, f'export_{timestamp}_{export_id}.json')
    
    try:
        with open(json_file, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        
        # Add to exports history
        export_entry = {
            'id': export_id,
            'date': datetime.datetime.now().isoformat(),
            'type': 'json',
            'sections': sections or list(data.keys()),
            'file': json_file,
            'size': os.path.getsize(json_file),
            'url': url_for('main.download_export', export_id=export_id, _external=True)
        }
        
        exports.append(export_entry)
        _save_exports_history()
        
        return json_file, None
    except Exception as e:
        logger.error(f"Error generating JSON export: {e}")
        return None, f"Error generating JSON export: {e}"

def _register_api_endpoints(app):
    """Register API endpoints for the export module."""
    from flask import jsonify, request, send_file
    
    @app.route('/api/v2/exports')
    def api_exports():
        """API endpoint to get exports history."""
        return jsonify({
            'exports': exports
        })
    
    @app.route('/api/v2/exports/<export_id>', methods=['DELETE'])
    def api_delete_export(export_id):
        """API endpoint to delete an export."""
        global exports
        
        # Find the export
        export = next((e for e in exports if e['id'] == export_id), None)
        if not export:
            return jsonify({
                'success': False,
                'error': 'Export not found'
            })
        
        # Delete the file
        try:
            os.remove(export['file'])
        except Exception as e:
            logger.error(f"Error deleting export file: {e}")
        
        # Remove from exports history
        exports = [e for e in exports if e['id'] != export_id]
        _save_exports_history()
        
        return jsonify({
            'success': True,
            'message': 'Export deleted'
        })
    
    @app.route('/api/v2/export/report')
    def api_export_report():
        """API endpoint to generate a report."""
        format_type = request.args.get('format', 'pdf')
        sections_str = request.args.get('sections')
        sections = sections_str.split(',') if sections_str else None
        title = request.args.get('title', 'OpenShift Cluster Documentation')
        include_timestamp = request.args.get('timestamp', 'yes') == 'yes'
        include_charts = request.args.get('charts', 'yes') == 'yes'
        include_raw_data = request.args.get('raw_data', 'no') == 'yes'
        
        if format_type == 'pdf':
            file_path, error = generate_pdf_report(
                sections=sections,
                title=title,
                include_timestamp=include_timestamp,
                include_charts=include_charts,
                include_raw_data=include_raw_data
            )
        elif format_type == 'html':
            file_path, error = generate_html_report(
                sections=sections,
                title=title,
                include_timestamp=include_timestamp,
                include_charts=include_charts,
                include_raw_data=include_raw_data
            )
        elif format_type == 'json':
            file_path, error = generate_json_export(sections=sections)
        else:
            return jsonify({
                'success': False,
                'error': f'Unsupported format: {format_type}'
            })
        
        if error:
            return jsonify({
                'success': False,
                'error': error
            })
        
        # Get the export entry
        export = next((e for e in exports if e['file'] == file_path), None)
        if not export:
            return jsonify({
                'success': False,
                'error': 'Export not found'
            })
        
        return jsonify({
            'success': True,
            'message': f'{format_type.upper()} report generated',
            'download_url': export['url']
        })
    
    @app.route('/api/v2/export/<section>')
    def api_export_section(section):
        """API endpoint to export a specific section."""
        format_type = request.args.get('format', 'json')
        
        if format_type == 'json':
            file_path, error = generate_json_export(sections=[section])
        else:
            return jsonify({
                'success': False,
                'error': f'Unsupported format for section export: {format_type}'
            })
        
        if error:
            return jsonify({
                'success': False,
                'error': error
            })
        
        # Get the export entry
        export = next((e for e in exports if e['file'] == file_path), None)
        if not export:
            return jsonify({
                'success': False,
                'error': 'Export not found'
            })
        
        return jsonify({
            'success': True,
            'message': f'{section} exported to {format_type.upper()}',
            'download_url': export['url']
        })
    
    @app.route('/exports/<export_id>')
    def download_export(export_id):
        """Route to download an export."""
        # Find the export
        export = next((e for e in exports if e['id'] == export_id), None)
        if not export:
            return "Export not found", 404
        
        # Send the file
        return send_file(
            export['file'],
            as_attachment=True,
            download_name=os.path.basename(export['file'])
        )
