from flask import Blueprint, render_template, jsonify, request
from app.collector.openshift_collector import (
    get_cluster_info, get_nodes_info, get_basic_info, get_nodes_detailed,
    get_operators_info, get_etcd_info, get_namespaces_list, get_resources_for_namespace,
    get_cluster_resources, get_network_info, get_storage_info, get_security_info,
    get_metrics_info, get_events_info
)
from app.export import _get_latest_collection_data

# Create a Blueprint for the main routes
main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    """Render the main dashboard page."""
    return render_template('pages/dashboard.html', title='OpenShift Cluster Documentation')

@main_bp.route('/cluster')
def cluster_overview():
    data = _get_latest_collection_data() or {}
    cluster = data.get('cluster', {})
    return render_template('pages/cluster_overview.html', title='Cluster Overview', cluster=cluster)

@main_bp.route('/operators')
def operators_view():
    data = _get_latest_collection_data() or {}
    operators = data.get('operators', {})
    return render_template('pages/operators.html', title='Operators', operators=operators)

@main_bp.route('/etcd')
def etcd_view():
    data = _get_latest_collection_data() or {}
    etcd = data.get('etcd', {})
    return render_template('pages/etcd.html', title='ETCD', etcd=etcd)

@main_bp.route('/nodes')
def nodes_view():
    data = _get_latest_collection_data() or {}
    nodes = data.get('nodes', {})
    return render_template('pages/nodes.html', title='Nodes', nodes=nodes)

@main_bp.route('/namespaces')
def namespaces_view():
    data = _get_latest_collection_data() or {}
    namespaces = data.get('namespaces', [])
    return render_template('pages/namespaces.html', title='Namespaces', namespaces=namespaces)

@main_bp.route('/namespace/<namespace>')
def namespace_detail(namespace):
    from app.collector.openshift_collector import get_resources_for_namespace
    from flask import current_app
    kubeconfig = current_app.config.get('KUBECONFIG_PATH')
    ns_data = get_resources_for_namespace(namespace, kubeconfig)
    return render_template('pages/namespace_detail.html', title=f'Namespace: {namespace}', namespace=namespace, ns_data=ns_data)

@main_bp.route('/storage')
def storage_view():
    data = _get_latest_collection_data() or {}
    storage = data.get('storage', {})
    return render_template('pages/storage.html', title='Storage', storage=storage)

@main_bp.route('/network')
def network_view():
    data = _get_latest_collection_data() or {}
    network = data.get('network', {})
    return render_template('pages/network.html', title='Network', network=network)

@main_bp.route('/security')
def security_view():
    data = _get_latest_collection_data() or {}
    security = data.get('security', {})
    return render_template('pages/security.html', title='Security', security=security)

@main_bp.route('/metrics')
def metrics_view():
    data = _get_latest_collection_data() or {}
    metrics = data.get('metrics', {})
    return render_template('pages/metrics.html', title='Metrics', metrics=metrics)

@main_bp.route('/events')
def events_view():
    data = _get_latest_collection_data() or {}
    events = data.get('events', {})
    return render_template('pages/events.html', title='Events', events=events)

@main_bp.route('/collection-status')
def collection_status():
    """Render the collection status page."""
    return render_template('pages/collection_status.html', title='Collection Status')

@main_bp.route('/export')
def export_view():
    """Render the export page."""
    return render_template('pages/export.html', title='Export')

# --- Legacy API endpoints for backward compatibility ---

@main_bp.route('/api/cluster')
def cluster_info():
    """API endpoint to get basic cluster information (legacy)."""
    try:
        cluster_data = get_cluster_info()
        return jsonify(cluster_data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@main_bp.route('/api/nodes')
def nodes_info():
    """API endpoint to get information about cluster nodes (legacy)."""
    try:
        nodes_data = get_nodes_info()
        return jsonify(nodes_data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# --- New API endpoints for enhanced data collection ---

@main_bp.route('/api/v2/cluster')
def basic_info():
    """API endpoint to get enhanced cluster information."""
    try:
        kubeconfig = request.args.get('kubeconfig')
        data = get_basic_info(kubeconfig)
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@main_bp.route('/api/v2/nodes')
def nodes_detailed():
    """API endpoint to get detailed information about cluster nodes."""
    try:
        kubeconfig = request.args.get('kubeconfig')
        data = get_nodes_detailed(kubeconfig)
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@main_bp.route('/api/v2/operators')
def operators_info():
    """API endpoint to get information about cluster operators."""
    try:
        kubeconfig = request.args.get('kubeconfig')
        data = get_operators_info(kubeconfig)
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@main_bp.route('/api/v2/etcd')
def etcd_info():
    """API endpoint to get information about etcd."""
    try:
        kubeconfig = request.args.get('kubeconfig')
        data = get_etcd_info(kubeconfig)
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@main_bp.route('/api/v2/namespaces')
def namespaces_list():
    """API endpoint to get a list of namespaces."""
    try:
        kubeconfig = request.args.get('kubeconfig')
        data = get_namespaces_list(kubeconfig)
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@main_bp.route('/api/v2/namespace/<namespace>')
def namespace_resources(namespace):
    """API endpoint to get resources for a specific namespace."""
    try:
        kubeconfig = request.args.get('kubeconfig')
        data = get_resources_for_namespace(namespace, kubeconfig)
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@main_bp.route('/api/v2/cluster-resources')
def cluster_resources():
    """API endpoint to get cluster-scoped resources."""
    try:
        kubeconfig = request.args.get('kubeconfig')
        data = get_cluster_resources(kubeconfig)
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@main_bp.route('/api/v2/network')
def network_info():
    """API endpoint to get network information."""
    try:
        kubeconfig = request.args.get('kubeconfig')
        data = get_network_info(kubeconfig)
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@main_bp.route('/api/v2/storage')
def storage_info():
    """API endpoint to get storage information."""
    try:
        kubeconfig = request.args.get('kubeconfig')
        data = get_storage_info(kubeconfig)
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@main_bp.route('/api/v2/security')
def security_info():
    """API endpoint to get security information."""
    try:
        kubeconfig = request.args.get('kubeconfig')
        data = get_security_info(kubeconfig)
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@main_bp.route('/api/v2/metrics')
def metrics_info():
    """API endpoint to get metrics information."""
    try:
        kubeconfig = request.args.get('kubeconfig')
        data = get_metrics_info(kubeconfig)
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@main_bp.route('/api/v2/events')
def events_info():
    """API endpoint to get events information."""
    try:
        kubeconfig = request.args.get('kubeconfig')
        limit = request.args.get('limit', 100, type=int)
        data = get_events_info(kubeconfig, limit)
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
