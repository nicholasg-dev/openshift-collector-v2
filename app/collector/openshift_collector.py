import subprocess
import json
import yaml
import os
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from flask import current_app

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Enhanced Helper function (incorporating retry and optional resource logic)
def _run_oc_command(command_args, kubeconfig_path=None, parse_output=None, optional_resource=False, retries=2, delay=2, timeout=60):
    """
    Runs an oc command with retry logic and optional output parsing.

    Args:
        command_args (list): List of arguments for oc command (e.g., ['get', 'nodes']).
        kubeconfig_path (str, optional): Path to the kubeconfig file.
        parse_output (str, optional): 'json' or 'yaml' to parse output. None for raw text.
        optional_resource (bool): If True, treat 'NotFound' errors as non-fatal.
        retries (int): Number of retries on transient errors.
        delay (int): Delay between retries in seconds.
        timeout (int): Timeout for the command execution.

    Returns:
        tuple: (success (bool), result (parsed_data|str|None), error_message (str|None))
               - success: True if command succeeded or was optional and not found.
               - result: Parsed JSON/YAML data, raw stdout string, or None if failed/not found.
               - error_message: Stderr content if an error occurred, or None.
    """
    base_command = ['oc']
    env = os.environ.copy()

    if kubeconfig_path:
        logger.debug(f"Using kubeconfig: {kubeconfig_path}")
        base_command.extend(['--kubeconfig', kubeconfig_path])
    else:
        # Get kubeconfig path from config if specified
        kubeconfig = current_app.config.get('KUBECONFIG_PATH')
        if kubeconfig:
            logger.debug(f"Using kubeconfig from config: {kubeconfig}")
            env['KUBECONFIG'] = kubeconfig

    # Ensure output format arg is present if parsing requested
    if parse_output and f'-o{parse_output}' not in command_args and f'--output={parse_output}' not in command_args:
         # Check if -o exists with different format
        has_other_output = any(arg.startswith('-o') or arg.startswith('--output=') for arg in command_args)
        if not has_other_output:
            command_args.extend(['-o', parse_output])

    full_command = base_command + command_args
    cmd_display = ' '.join(full_command) # For logging
    logger.info(f"Running command: {cmd_display}")

    attempt = 0
    while attempt <= retries:
        attempt += 1
        try:
            result = subprocess.run(
                full_command,
                capture_output=True,
                text=True,
                check=False, # We check returncode manually
                env=env,
                timeout=timeout
            )

            if result.returncode == 0:
                logger.debug(f"Command successful: {cmd_display}")
                output = result.stdout
                if parse_output == 'json':
                    try:
                        return True, json.loads(output), None
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse JSON for command '{cmd_display}': {e}\nOutput: {output[:500]}...")
                        return False, output, f"JSONDecodeError: {e}"
                elif parse_output == 'yaml':
                    try:
                        # Use safe_load_all for potentially multi-document YAML
                        parsed = list(yaml.safe_load_all(output))
                        # Return single doc if only one, else list
                        return True, parsed[0] if len(parsed) == 1 else parsed, None
                    except yaml.YAMLError as e:
                        logger.error(f"Failed to parse YAML for command '{cmd_display}': {e}\nOutput: {output[:500]}...")
                        return False, output, f"YAMLError: {e}"
                else:
                    return True, output.strip(), None # Return raw text stripped of whitespace

            # --- Handle Errors ---
            stderr_lower = result.stderr.lower()
            logger.warning(f"Command failed (rc={result.returncode}, attempt={attempt-1}): {cmd_display}\nStderr: {result.stderr}")

            # Check for 'NotFound' on optional resources
            if optional_resource and ('notfound' in stderr_lower or 'could not find the requested resource' in stderr_lower):
                logger.info(f"Optional resource not found: {cmd_display}")
                return True, None, None # Success=True, Result=None, Error=None

            # Check for transient errors to retry
            transient_errors = ["timeout", "connection refused", "tls handshake", "temporarily unavailable", "too many requests"]
            is_transient = any(err in stderr_lower for err in transient_errors)

            if is_transient and attempt <= retries:
                wait_time = delay * attempt
                logger.warning(f"Transient error detected. Retrying in {wait_time}s...")
                time.sleep(wait_time)
                continue
            else:
                # Non-transient error or retries exhausted
                logger.error(f"Command failed permanently or retries exhausted for: {cmd_display}")
                return False, result.stdout.strip() if result.stdout else None, result.stderr.strip()

        except subprocess.TimeoutExpired:
            logger.error(f"Command timed out: {cmd_display}")
            if attempt <= retries:
                wait_time = delay * attempt
                logger.warning(f"Timeout detected. Retrying in {wait_time}s...")
                time.sleep(wait_time)
                continue
            else:
                 return False, None, "Command timed out after retries"
        except FileNotFoundError:
             logger.error(f"Command 'oc' not found. Is it installed and in PATH?")
             return False, None, "'oc' command not found"
        except Exception as e:
            logger.error(f"Unexpected error running command '{cmd_display}': {e}")
            return False, None, f"Unexpected error: {e}"

    # Should not be reached if loop logic is correct, but as a safeguard
    return False, None, "Maximum retries exceeded"


# For backward compatibility with existing code
def run_oc_command(command):
    """
    Execute an OpenShift CLI command and return the result.
    Legacy function for backward compatibility.

    Args:
        command (list): The command to execute as a list of strings

    Returns:
        dict: The parsed JSON output from the command

    Raises:
        Exception: If the command fails to execute
    """
    try:
        # Get kubeconfig path from config if specified
        kubeconfig = current_app.config.get('KUBECONFIG_PATH')
        env = os.environ.copy()

        if kubeconfig:
            env['KUBECONFIG'] = kubeconfig

        # Run the command and capture output
        result = subprocess.run(
            command,
            env=env,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        # Parse the JSON output
        return json.loads(result.stdout)
    except subprocess.CalledProcessError as e:
        raise Exception(f"Command failed: {e.stderr}")
    except json.JSONDecodeError:
        raise Exception("Failed to parse command output as JSON")

# --- Helper for parsing 'oc get ... -o wide' or similar tabular text output ---
def _parse_oc_get_output(raw_output):
    """Parses tabular `oc get` output into a list of dictionaries."""
    if not raw_output or not isinstance(raw_output, str):
        return []
    lines = raw_output.strip().split('\n')
    if len(lines) < 2: # Need header + at least one data row
        return []

    # Split header carefully, handling potential spaces within column names (less common)
    header = [h.strip() for h in lines[0].split(None)] # Basic split, might need refinement

    parsed_list = []
    num_columns = len(header)
    for line in lines[1:]:
        # Split data lines, handling potential spaces in the last column
        fields = line.split(None, num_columns - 1)
        if len(fields) == num_columns:
             row_dict = dict(zip(header, [f.strip() for f in fields]))
             parsed_list.append(row_dict)
        else:
             logger.warning(f"Skipping malformed line (expected {num_columns} fields, got {len(fields)}): {line}")

    return parsed_list

# --- Collection Functions ---

def get_basic_info(kubeconfig_path=None):
    """Collects basic cluster information."""
    data = {}
    success, result, err = _run_oc_command(['version', '-o', 'json'], kubeconfig_path, parse_output='json')
    data['oc_version'] = result if success else {'error': err or 'Failed to get oc version'}

    success, result, err = _run_oc_command(['get', 'clusterversion', 'version', '-o', 'yaml'], kubeconfig_path, parse_output='yaml')
    data['cluster_version_yaml'] = result if success else {'error': err or 'Failed to get clusterversion'}
    # Extract key fields if available
    if success and isinstance(result, dict):
         data['summary'] = {
             'openshiftVersion': result.get('status', {}).get('desired', {}).get('version', 'N/A'),
             'clusterID': result.get('spec', {}).get('clusterID', 'N/A'),
             'installDateApprox': result.get('metadata', {}).get('creationTimestamp', 'N/A'),
             'available': result.get('status', {}).get('conditions', [{}])[0].get('status', 'Unknown') == 'True' if result.get('status', {}).get('conditions') else 'Unknown',
             'progressing': any(c.get('type') == 'Progressing' and c.get('status') == 'True' for c in result.get('status', {}).get('conditions', [])),
             'degraded': any(c.get('type') == 'Degraded' and c.get('status') == 'True' for c in result.get('status', {}).get('conditions', []))
         }
    else:
        data['summary'] = {'error': 'Could not parse cluster version details'}

    success, result, err = _run_oc_command(['get', 'infrastructure', 'cluster', '-o', 'yaml'], kubeconfig_path, parse_output='yaml')
    data['infrastructure_yaml'] = result if success else {'error': err or 'Failed to get infrastructure'}
    if success and isinstance(result, dict):
        data['summary']['infraName'] = result.get('status', {}).get('infrastructureName', 'N/A')
        data['summary']['apiServerURL'] = result.get('status', {}).get('apiServerURL', 'N/A')
        data['summary']['platform'] = result.get('status', {}).get('platformStatus', {}).get('type', 'N/A')

    success, result, err = _run_oc_command(['cluster-info'], kubeconfig_path, parse_output=None)
    data['cluster_info_dump'] = result if success else f"Error: {err or 'Failed to run cluster-info'}"

    return data

# For backward compatibility with existing code
def get_cluster_info():
    """Legacy function for backward compatibility."""
    try:
        # Try to get actual cluster data using the new function
        data = get_basic_info()
        # Extract relevant information to match the old format
        cluster_info = {
            'version': data.get('summary', {}).get('openshiftVersion', 'Unknown'),
            'platform': data.get('summary', {}).get('platform', 'Unknown'),
            'infrastructure_name': data.get('summary', {}).get('infraName', 'Unknown'),
            'control_plane_topology': data.get('infrastructure_yaml', {}).get('status', {}).get('controlPlaneTopology', 'Unknown'),
            'infrastructure_topology': data.get('infrastructure_yaml', {}).get('status', {}).get('infrastructureTopology', 'Unknown'),
        }
    except Exception as e:
        # Return mock data for testing
        logger.error(f"Using mock data for cluster info: {str(e)}")
        cluster_info = {
            'version': '4.17.4',
            'platform': 'BareMetal',
            'infrastructure_name': 'cluster-kh767-7bmq2',
            'control_plane_topology': 'HighlyAvailable',
            'infrastructure_topology': 'HighlyAvailable',
        }

    return cluster_info

def get_nodes_detailed(kubeconfig_path=None):
    """Collects node list and runs describe in parallel."""
    nodes_data = {'list': [], 'details': {}}
    parallel_jobs = current_app.config.get('PARALLEL_JOBS', 4)

    # Get node list first
    success, result, err = _run_oc_command(['get', 'nodes', '-o', 'wide'], kubeconfig_path, parse_output=None)
    if not success:
        nodes_data['error'] = err or "Failed to get node list"
        return nodes_data
    nodes_data['list_raw'] = result

    # Simple parsing of 'get nodes -o wide' output
    header = []
    lines = result.strip().split('\n')
    if lines:
        header = lines[0].split()
        for line in lines[1:]:
            fields = line.split(maxsplit=len(header)-1) # Split smartly
            node_info = dict(zip(header, fields))
            nodes_data['list'].append(node_info)

    # Describe nodes in parallel
    node_names = [node.get('NAME') for node in nodes_data['list'] if node.get('NAME')]
    if not node_names:
        logger.warning("No node names found to describe.")
        return nodes_data

    with ThreadPoolExecutor(max_workers=parallel_jobs) as executor:
        future_to_node = {executor.submit(_run_oc_command, ['describe', 'node', name], kubeconfig_path): name for name in node_names}
        for future in as_completed(future_to_node):
            node_name = future_to_node[future]
            try:
                success, result_desc, err_desc = future.result()
                if success:
                    nodes_data['details'][node_name] = result_desc
                else:
                    nodes_data['details'][node_name] = f"Error describing node: {err_desc or 'Unknown error'}"
            except Exception as exc:
                logger.error(f'Error describing node {node_name}: {exc}')
                nodes_data['details'][node_name] = f"Exception during describe: {exc}"

    return nodes_data

# For backward compatibility with existing code
def get_nodes_info():
    """Legacy function for backward compatibility."""
    try:
        # Try to get actual cluster data using the new function
        nodes_data = get_nodes_detailed()

        # Extract relevant information to match the old format
        nodes_info = []
        for node in nodes_data.get('list', []):
            # Get node details from the detailed data
            node_details = nodes_data.get('details', {}).get(node.get('NAME', ''), '')

            # Parse capacity from node details (simple text parsing)
            capacity = {}
            if 'Capacity:' in node_details:
                capacity_section = node_details.split('Capacity:')[1].split('Allocatable:')[0].strip()
                for line in capacity_section.split('\n'):
                    if ':' in line:
                        key, value = line.strip().split(':', 1)
                        capacity[key.strip()] = value.strip()

            node_info = {
                'name': node.get('NAME', 'Unknown'),
                'roles': 'master' in node.get('ROLES', '').lower() or 'control-plane' in node.get('ROLES', '').lower(),
                'status': node.get('STATUS', 'Unknown'),
                'os_image': 'Unknown',  # Not available in basic node list
                'kernel_version': 'Unknown',  # Not available in basic node list
                'architecture': 'Unknown',  # Not available in basic node list
                'container_runtime': 'Unknown',  # Not available in basic node list
                'capacity': {
                    'cpu': capacity.get('cpu', node.get('CPU', 'Unknown')),
                    'memory': capacity.get('memory', 'Unknown'),
                    'pods': capacity.get('pods', 'Unknown'),
                }
            }
            nodes_info.append(node_info)
    except Exception as e:
        # Return mock data for testing
        logger.error(f"Using mock data for nodes info: {str(e)}")
        nodes_info = [
            {
                'name': 'control-plane-cluster-kh767-1',
                'roles': True,
                'status': 'Ready',
                'os_image': 'Red Hat Enterprise Linux CoreOS 417.94.202411050056-0',
                'kernel_version': '5.14.0-427.44.1.el9_4.x86_64',
                'architecture': 'amd64',
                'container_runtime': 'cri-o://1.30.7-2.rhaos4.17.git2391edc.el9',
                'capacity': {
                    'cpu': '16',
                    'memory': '49317744Ki',
                    'pods': '250',
                }
            },
            {
                'name': 'control-plane-cluster-kh767-2',
                'roles': True,
                'status': 'Ready',
                'os_image': 'Red Hat Enterprise Linux CoreOS 417.94.202411050056-0',
                'kernel_version': '5.14.0-427.44.1.el9_4.x86_64',
                'architecture': 'amd64',
                'container_runtime': 'cri-o://1.30.7-2.rhaos4.17.git2391edc.el9',
                'capacity': {
                    'cpu': '16',
                    'memory': '49317736Ki',
                    'pods': '250',
                }
            },
            {
                'name': 'control-plane-cluster-kh767-3',
                'roles': True,
                'status': 'Ready',
                'os_image': 'Red Hat Enterprise Linux CoreOS 417.94.202411050056-0',
                'kernel_version': '5.14.0-427.44.1.el9_4.x86_64',
                'architecture': 'amd64',
                'container_runtime': 'cri-o://1.30.7-2.rhaos4.17.git2391edc.el9',
                'capacity': {
                    'cpu': '16',
                    'memory': '49317748Ki',
                    'pods': '250',
                }
            }
        ]

    return nodes_info

def get_operators_info(kubeconfig_path=None):
    """Collects ClusterOperator status and OLM details."""
    operators_data = {}
    success, result, err = _run_oc_command(['get', 'clusteroperators', '-o', 'wide'], kubeconfig_path, parse_output=None)
    operators_data['clusteroperators_raw'] = result if success else f"Error: {err or 'Failed to get clusteroperators'}"
    operators_data['clusteroperators_list'] = _parse_oc_get_output(result) if success else []

    success, result, err = _run_oc_command(['get', 'csv', '--all-namespaces', '-o', 'wide'], kubeconfig_path, parse_output=None)
    operators_data['csv_raw'] = result if success else f"Error: {err or 'Failed to get CSVs'}"
    operators_data['csv_list'] = _parse_oc_get_output(result) if success else []

    # OLM specific (can add more like installplans, catalogsources)
    success, result, err = _run_oc_command(['get', 'subscriptions', '--all-namespaces', '-o', 'wide'], kubeconfig_path, parse_output=None)
    operators_data['subscriptions_raw'] = result if success else f"Error: {err or 'Failed to get subscriptions'}"
    operators_data['subscriptions_list'] = _parse_oc_get_output(result) if success else []

    return operators_data

def get_etcd_info(kubeconfig_path=None):
    """Collects etcd health and member status via rsh."""
    etcd_data = {}
    # Find an etcd pod
    success, pods_json, err = _run_oc_command(['get', 'pods', '-n', 'openshift-etcd', '-l', 'app=etcd', '-o', 'json'], kubeconfig_path, parse_output='json')
    etcd_pod = None
    if success and pods_json and pods_json.get('items'):
        etcd_pod = pods_json['items'][0].get('metadata', {}).get('name')
    else:
        etcd_data['error'] = "Could not find an etcd pod."
        return etcd_data

    if etcd_pod:
        success_h, result_h, err_h = _run_oc_command(['rsh', '-n', 'openshift-etcd', etcd_pod, 'etcdctl', 'endpoint', 'health'], kubeconfig_path)
        etcd_data['health_raw'] = result_h if success_h else f"Error: {err_h or 'Failed to get etcd health'}"

        success_m, result_m, err_m = _run_oc_command(['rsh', '-n', 'openshift-etcd', etcd_pod, 'etcdctl', 'member', 'list', '-w', 'table'], kubeconfig_path)
        etcd_data['members_raw'] = result_m if success_m else f"Error: {err_m or 'Failed to get etcd members'}"
    else:
         etcd_data['error'] = "Found etcd pods json, but could not extract pod name."

    return etcd_data

def get_namespaces_list(kubeconfig_path=None):
    """Gets a list of namespace names."""
    success, result, err = _run_oc_command(['get', 'namespaces', '-o', 'jsonpath={.items[*].metadata.name}'], kubeconfig_path)
    if success:
        return result.split()
    else:
        logger.error(f"Failed to get namespaces: {err}")
        return []

def get_resources_for_namespace(namespace, kubeconfig_path=None):
    """Collects key resources for a specific namespace."""
    ns_data = {'namespace': namespace}
    resources_to_get_yaml = [
        'pods', 'deployments', 'statefulsets', 'daemonsets', 'services',
        'configmaps', 'persistentvolumeclaims', 'routes', 'ingresses',
        'networkpolicies', 'serviceaccounts', 'roles', 'rolebindings',
        'limitranges', 'resourcequotas', 'cronjobs', 'jobs', 'hpa',
        'buildconfigs', 'builds', 'imagestreams'
    ]
    # Secrets are handled separately for redaction
    secrets_success, secrets_result, secrets_err = _run_oc_command(
        ['get', 'secret', '-n', namespace, '-o', 'yaml'], kubeconfig_path, parse_output='yaml'
    )
    if secrets_success:
        # Redact data field
        if isinstance(secrets_result, dict) and 'items' in secrets_result:
             for item in secrets_result.get('items', []):
                 if 'data' in item:
                     item['data'] = {k: '**REDACTED**' for k in item['data']}
        ns_data['secrets_redacted'] = secrets_result
    else:
        ns_data['secrets_redacted'] = {'error': secrets_err or 'Failed to get secrets'}


    parallel_jobs = current_app.config.get('PARALLEL_JOBS', 4)
    with ThreadPoolExecutor(max_workers=parallel_jobs) as executor:
        future_to_resource = {
            executor.submit(
                _run_oc_command,
                ['get', resource, '-n', namespace, '-o', 'yaml'],
                kubeconfig_path,
                parse_output='yaml',
                optional_resource=True # Many might not exist in a namespace
            ): resource
            for resource in resources_to_get_yaml
        }
        for future in as_completed(future_to_resource):
            resource_name = future_to_resource[future]
            try:
                success, result_res, err_res = future.result()
                if success and result_res is not None: # Only store if found
                    ns_data[resource_name] = result_res
                elif not success:
                     # Log error but don't necessarily store it unless needed
                     logger.warning(f"Failed to get {resource_name} in ns {namespace}: {err_res}")
                     ns_data[resource_name] = {'error': f"Failed to get {resource_name}: {err_res or 'Unknown'}"}
                # If success is True but result_res is None, it was optional and not found - do nothing.

            except Exception as exc:
                logger.error(f'Error getting {resource_name} in ns {namespace}: {exc}')
                ns_data[resource_name] = {'error': f"Exception getting {resource_name}: {exc}"}

    # Get events separately as plain text
    success, result, err = _run_oc_command(['get', 'events', '-n', namespace], kubeconfig_path, parse_output=None)
    ns_data['events_raw'] = result if success else f"Error: {err or 'Failed to get events'}"

    return ns_data


def get_cluster_resources(kubeconfig_path=None):
    """Collects common cluster-scoped resources."""
    cluster_data = {}
    resources_to_get_yaml = [
        'clusterroles', 'clusterrolebindings', 'crds', 'apiservices',
        'persistentvolumes', 'storageclasses', 'machineconfigpools',
        'componentstatuses', 'scc' # Security Context Constraints from security section
    ]
    resources_to_get_text = [
        # Add any text-based cluster resources here if needed
    ]
    resources_to_get_optional = [
        'imagepruner', 'clusterautoscaler' # From bash script
    ]

    parallel_jobs = current_app.config.get('PARALLEL_JOBS', 4)
    with ThreadPoolExecutor(max_workers=parallel_jobs) as executor:
        # Yaml resources
        futures_yaml = {
            executor.submit(_run_oc_command, ['get', resource, '-o', 'yaml'], kubeconfig_path, parse_output='yaml'): resource
            for resource in resources_to_get_yaml
        }
        # Optional Yaml resources
        futures_optional = {
             executor.submit(_run_oc_command, ['get', resource, '-o', 'yaml'], kubeconfig_path, parse_output='yaml', optional_resource=True): resource
             for resource in resources_to_get_optional
        }
        # Text resources
        futures_text = {
            executor.submit(_run_oc_command, ['get', resource], kubeconfig_path, parse_output=None): resource
            for resource in resources_to_get_text
        }

        all_futures = {**futures_yaml, **futures_optional, **futures_text}

        for future in as_completed(all_futures):
            resource_name = all_futures[future]
            try:
                success, result_res, err_res = future.result()
                if success and result_res is not None:
                     cluster_data[resource_name] = result_res
                elif not success:
                    logger.warning(f"Failed to get cluster resource {resource_name}: {err_res}")
                    cluster_data[resource_name] = {'error': f"Failed to get {resource_name}: {err_res or 'Unknown'}"}
                # If success is True but result is None, it was optional and not found - do nothing.

            except Exception as exc:
                logger.error(f'Error getting cluster resource {resource_name}: {exc}')
                cluster_data[resource_name] = {'error': f"Exception getting {resource_name}: {exc}"}

    return cluster_data

def get_network_info(kubeconfig_path=None):
    """Collects network configuration and status."""
    net_data = {}
    success, result, err = _run_oc_command(['get', 'network.config', 'cluster', '-o', 'yaml'], kubeconfig_path, parse_output='yaml')
    net_data['network_config_yaml'] = result if success else {'error': err or 'Failed'}
    # Extract summary details
    if success and isinstance(result, dict):
        net_data['summary'] = {
            'clusterNetwork': result.get('status', {}).get('clusterNetwork', []),
            'serviceNetwork': result.get('status', {}).get('serviceNetwork', []),
            'networkType': result.get('status', {}).get('networkType', 'N/A'),
        }

    success, result, err = _run_oc_command(['get', 'netnamespace'], kubeconfig_path, optional_resource=True)
    net_data['netnamespaces_raw'] = result if success and result is not None else "Not Found or Error"

    success, result, err = _run_oc_command(['get', 'hostsubnet'], kubeconfig_path, optional_resource=True)
    net_data['hostsubnets_raw'] = result if success and result is not None else "Not Found or Error"

    return net_data

def get_storage_info(kubeconfig_path=None):
    """Collects storage classes, PVs, and PVCs."""
    storage_data = {}
    success, result, err = _run_oc_command(['get', 'storageclass', '-o', 'yaml'], kubeconfig_path, parse_output='yaml')
    storage_data['storageclasses_yaml'] = result if success else {'error': err or 'Failed'}

    success, result, err = _run_oc_command(['get', 'pv', '-o', 'yaml'], kubeconfig_path, parse_output='yaml')
    storage_data['persistentvolumes_yaml'] = result if success else {'error': err or 'Failed'}

    # PVCs are namespace-scoped, collect summary or link to namespace view
    success, result, err = _run_oc_command(['get', 'pvc', '--all-namespaces', '-o', 'wide'], kubeconfig_path)
    storage_data['pvc_summary_raw'] = result if success else f"Error: {err or 'Failed'}"
    storage_data['pvc_summary_list'] = _parse_oc_get_output(result) if success else []

    return storage_data

def get_security_info(kubeconfig_path=None):
    """Collects security context constraints and OAuth config."""
    sec_data = {}
    success, result, err = _run_oc_command(['get', 'scc', '-o', 'yaml'], kubeconfig_path, parse_output='yaml')
    sec_data['scc_yaml'] = result if success else {'error': err or 'Failed'}

    success, result, err = _run_oc_command(['get', 'oauth', 'cluster', '-o', 'yaml'], kubeconfig_path, parse_output='yaml')
    sec_data['oauth_cluster_yaml'] = result if success else {'error': err or 'Failed'}

    # Certificate Expiry (complex logic from bash, needs careful translation)
    # This is a simplified placeholder - the bash script logic is more robust
    sec_data['cert_expiry_raw'] = "Certificate expiry check needs full implementation."
    # TODO: Translate the bash script's cert expiry logic using Python's openssl bindings or subprocess

    return sec_data

def get_metrics_info(kubeconfig_path=None):
    """Collects node and pod resource usage."""
    metrics_data = {}
    success, result, err = _run_oc_command(['adm', 'top', 'nodes', '--no-headers'], kubeconfig_path)
    metrics_data['node_usage_raw'] = result if success else f"Error: {err or 'Failed'}"
    metrics_data['node_usage_list'] = _parse_oc_get_output(f"NAME CPU(cores) CPU% MEMORY(bytes) MEMORY%\n{result}") if success else [] # Add dummy header for parser

    success, result, err = _run_oc_command(['adm', 'top', 'pods', '--all-namespaces', '--no-headers'], kubeconfig_path)
    metrics_data['pod_usage_raw'] = result if success else f"Error: {err or 'Failed'}"
    metrics_data['pod_usage_list'] = _parse_oc_get_output(f"NAMESPACE NAME CPU(cores) MEMORY(bytes)\n{result}") if success else []

    return metrics_data

def get_events_info(kubeconfig_path=None, limit=100):
    """Gets cluster-wide events, sorted by time."""
    events_data = {}
    success, result, err = _run_oc_command(['get', 'events', '--all-namespaces', f'--sort-by=.lastTimestamp'], kubeconfig_path)
    if success:
        events_data['events_raw'] = result
        # Simple split for summary, more robust parsing is better
        lines = result.strip().split('\n')
        events_data['events_list'] = _parse_oc_get_output(result) if success else []
        # Get recent and warnings for dashboard potentially
        events_data['recent_events_list'] = events_data['events_list'][-20:] # Last 20 approx
        events_data['warning_events_list'] = [e for e in events_data['events_list'] if e.get('TYPE') == 'Warning']
        events_data['top_warning_reasons'] = _summarize_event_warnings(events_data['warning_events_list'])

    else:
        events_data['error'] = err or "Failed to get events"
        events_data['events_raw'] = f"Error: {events_data['error']}"
        events_data['events_list'] = []
        events_data['recent_events_list'] = []
        events_data['warning_events_list'] = []
        events_data['top_warning_reasons'] = {}

    return events_data

def _summarize_event_warnings(warning_events):
    """Counts occurrences of different warning reasons."""
    reasons = {}
    for event in warning_events:
        reason = event.get('REASON', 'Unknown')
        reasons[reason] = reasons.get(reason, 0) + 1
    # Sort by count descending
    sorted_reasons = dict(sorted(reasons.items(), key=lambda item: item[1], reverse=True))
    return sorted_reasons
