"""
Authentication module for OpenShift authentication.
"""

import os
import json
import logging
import datetime
from flask import current_app
import subprocess
import tempfile

# Initialize logger
logger = logging.getLogger(__name__)

# Path to the authentication configuration file
AUTH_CONFIG_FILE = 'auth_config.json'

def get_auth_config_path():
    """Get the path to the authentication configuration file."""
    return os.path.join(current_app.instance_path, AUTH_CONFIG_FILE)

def load_auth_config():
    """Load authentication configuration from file."""
    config_path = get_auth_config_path()
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading authentication configuration: {e}")
    return {}

def save_auth_config(config):
    """Save authentication configuration to file."""
    config_path = get_auth_config_path()
    try:
        # Ensure instance directory exists
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        
        # Add timestamp
        config['last_updated'] = datetime.datetime.now().isoformat()
        
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
        
        logger.info("Authentication configuration saved")
        return True
    except Exception as e:
        logger.error(f"Error saving authentication configuration: {e}")
        return False

def test_connection(server, token, verify_ssl=True):
    """Test connection to OpenShift cluster."""
    try:
        # Create a temporary kubeconfig file
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp_file:
            kubeconfig_path = temp_file.name
            
            # Write kubeconfig content
            temp_file.write(f"""apiVersion: v1
kind: Config
clusters:
- cluster:
    server: {server}
    insecure-skip-tls-verify: {str(not verify_ssl).lower()}
  name: test-cluster
contexts:
- context:
    cluster: test-cluster
    user: test-user
  name: test-context
current-context: test-context
users:
- name: test-user
  user:
    token: {token}
""")
        
        try:
            # Test connection with the temporary kubeconfig
            version_cmd = ['oc', '--kubeconfig', kubeconfig_path, 'version', '-o', 'json']
            version_result = subprocess.run(
                version_cmd,
                capture_output=True,
                text=True,
                check=True,
                timeout=10
            )
            
            whoami_cmd = ['oc', '--kubeconfig', kubeconfig_path, 'whoami']
            whoami_result = subprocess.run(
                whoami_cmd,
                capture_output=True,
                text=True,
                check=True,
                timeout=5
            )
            
            # Parse version info
            version_info = json.loads(version_result.stdout)
            
            return {
                'success': True,
                'cluster_info': {
                    'name': version_info.get('openshiftVersion', 'Unknown'),
                    'version': version_info.get('serverVersion', {}).get('gitVersion', 'Unknown')
                },
                'user_info': {
                    'name': whoami_result.stdout.strip()
                }
            }
        except subprocess.CalledProcessError as e:
            logger.error(f"Error testing connection: {e.stderr}")
            return {
                'success': False,
                'error': f"Connection failed: {e.stderr}"
            }
        except json.JSONDecodeError:
            logger.error("Error parsing version information")
            return {
                'success': False,
                'error': "Error parsing version information"
            }
        except Exception as e:
            logger.error(f"Unexpected error testing connection: {e}")
            return {
                'success': False,
                'error': f"Unexpected error: {e}"
            }
        finally:
            # Clean up the temporary file
            try:
                os.unlink(kubeconfig_path)
            except Exception as e:
                logger.warning(f"Error removing temporary kubeconfig: {e}")
    except Exception as e:
        logger.error(f"Error creating temporary kubeconfig: {e}")
        return {
            'success': False,
            'error': f"Error creating temporary kubeconfig: {e}"
        }

def create_kubeconfig(server, token, verify_ssl=True):
    """Create a kubeconfig file from the provided authentication details."""
    try:
        kubeconfig_path = os.path.join(current_app.instance_path, 'kubeconfig')
        
        # Ensure instance directory exists
        os.makedirs(os.path.dirname(kubeconfig_path), exist_ok=True)
        
        # Write kubeconfig content
        with open(kubeconfig_path, 'w') as f:
            f.write(f"""apiVersion: v1
kind: Config
clusters:
- cluster:
    server: {server}
    insecure-skip-tls-verify: {str(not verify_ssl).lower()}
  name: openshift-cluster
contexts:
- context:
    cluster: openshift-cluster
    user: openshift-user
  name: openshift-context
current-context: openshift-context
users:
- name: openshift-user
  user:
    token: {token}
""")
        
        # Update application config
        current_app.config['KUBECONFIG_PATH'] = kubeconfig_path
        
        logger.info(f"Created kubeconfig at {kubeconfig_path}")
        return True
    except Exception as e:
        logger.error(f"Error creating kubeconfig: {e}")
        return False
