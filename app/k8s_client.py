# Helper module for Kubernetes/OpenShift direct API calls
import os
import logging
from kubernetes import client, config
from openshift.dynamic import DynamicClient

logger = logging.getLogger(__name__)

def get_k8s_client(kubeconfig_path=None):
    """Get a Kubernetes API client, handling both in-cluster and external configs."""
    try:
        # Check if we're running inside a cluster
        if os.path.exists('/var/run/secrets/kubernetes.io/serviceaccount/token'):
            logger.info("Using in-cluster configuration")
            config.load_incluster_config()
        elif kubeconfig_path and os.path.exists(kubeconfig_path):
            logger.info(f"Loading kubeconfig from {kubeconfig_path}")
            config.load_kube_config(config_file=kubeconfig_path)
        else:
            logger.info("Loading default kubeconfig")
            config.load_kube_config()

        return client.ApiClient()
    except Exception as e:
        logger.error(f"Error creating Kubernetes client: {e}")
        raise

def get_openshift_client(kubeconfig_path=None):
    """Get an OpenShift dynamic client."""
    k8s_client = get_k8s_client(kubeconfig_path)
    return DynamicClient(k8s_client)

def get_k8s_nodes(kubeconfig_path=None):
    """Fetch nodes using kubernetes-client."""
    try:
        k8s_client = get_k8s_client(kubeconfig_path)
        v1 = client.CoreV1Api(k8s_client)
        return v1.list_node().items
    except Exception as e:
        logger.error(f"Error fetching nodes: {e}")
        return []

def get_k8s_namespaces(kubeconfig_path=None):
    """Fetch namespaces using kubernetes-client."""
    try:
        k8s_client = get_k8s_client(kubeconfig_path)
        v1 = client.CoreV1Api(k8s_client)
        return v1.list_namespace().items
    except Exception as e:
        logger.error(f"Error fetching namespaces: {e}")
        return []

def get_k8s_pods(namespace=None, kubeconfig_path=None):
    """Fetch pods using kubernetes-client."""
    try:
        k8s_client = get_k8s_client(kubeconfig_path)
        v1 = client.CoreV1Api(k8s_client)
        if namespace:
            return v1.list_namespaced_pod(namespace).items
        else:
            return v1.list_pod_for_all_namespaces().items
    except Exception as e:
        logger.error(f"Error fetching pods: {e}")
        return []
