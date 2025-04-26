"""
General application configuration.
This file should be version controlled and should NOT contain secrets.
Instance-specific configuration should go in instance/config.py
When deployed to OpenShift, configuration is primarily through environment variables.
"""

import os

class Config:
    """Base configuration class."""
    # Flask settings
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-key-for-development-only')
    DEBUG = False
    TESTING = False

    # Application settings
    APP_NAME = 'OpenShift Collector v3'

    # OpenShift settings
    # In-cluster config is used if no KUBECONFIG_PATH is provided
    KUBECONFIG_PATH = os.environ.get('KUBECONFIG_PATH')

    # Service account token path when running in OpenShift
    SERVICE_ACCOUNT_TOKEN_PATH = '/var/run/secrets/kubernetes.io/serviceaccount/token'

    # Data collection settings
    COLLECTION_INTERVAL = int(os.environ.get('COLLECTION_INTERVAL', 3600))  # Default to hourly collection (in seconds)
    PARALLEL_JOBS = int(os.environ.get('PARALLEL_JOBS', 4))  # Number of parallel jobs for data collection
    COLLECTION_TIMEOUT = int(os.environ.get('COLLECTION_TIMEOUT', 60))  # Timeout for collection commands
    RETRY_ATTEMPTS = int(os.environ.get('RETRY_ATTEMPTS', 2))  # Number of retry attempts
    RETRY_DELAY = int(os.environ.get('RETRY_DELAY', 2))  # Delay between retries

    # Feature flags
    ENABLE_CLOUD_COLLECTION = os.environ.get('ENABLE_CLOUD_COLLECTION', 'False').lower() == 'true'
    ENABLE_SSH_COLLECTION = os.environ.get('ENABLE_SSH_COLLECTION', 'False').lower() == 'true'

    # Persistence settings
    DATA_DIR = os.environ.get('DATA_DIR', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance'))

    # Logging
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')

    # Namespaces to collect detailed data for (comma-separated list)
    NAMESPACES_TO_COLLECT = os.environ.get('NAMESPACES_TO_COLLECT', '').split(',') if os.environ.get('NAMESPACES_TO_COLLECT') else []

class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    # Use local kubeconfig by default in development
    KUBECONFIG_PATH = os.environ.get('KUBECONFIG_PATH', os.environ.get('KUBECONFIG', os.path.expanduser('~/.kube/config')))

class TestingConfig(Config):
    """Testing configuration."""
    TESTING = True
    DEBUG = True
    # Use a test kubeconfig or mock
    KUBECONFIG_PATH = os.environ.get('TEST_KUBECONFIG_PATH', 'tests/test_kubeconfig')

class ProductionConfig(Config):
    """Production configuration."""
    # In production, SECRET_KEY should be set as an environment variable
    # but we'll provide a default with a warning if it's not set
    SECRET_KEY = os.environ.get('SECRET_KEY')
    if not SECRET_KEY:
        import uuid
        import logging
        logging.warning("WARNING: No SECRET_KEY set for production environment. Using a generated key.")
        logging.warning("This is insecure and will cause sessions to invalidate on restart.")
        SECRET_KEY = str(uuid.uuid4())

    # In OpenShift, we'll use the mounted service account token by default
    # This will be overridden if KUBECONFIG_PATH is explicitly set
    def __init__(self):
        if not self.KUBECONFIG_PATH and os.path.exists(self.SERVICE_ACCOUNT_TOKEN_PATH):
            # We're running in-cluster, use the service account
            os.environ['KUBERNETES_SERVICE_HOST'] = 'https://kubernetes.default.svc'
