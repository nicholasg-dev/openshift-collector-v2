import pytest
from app import create_app
import os

# Example unit test for config loading

def test_app_config_loading(tmp_path):
    # Arrange: create a temp config file
    config_path = tmp_path / "config.py"
    config_content = "KUBECONFIG_PATH = '/tmp/kubeconfig'\nPARALLEL_JOBS = 2"
    config_path.write_text(config_content)

    # Act: create app with this config
    os.environ['FLASK_ENV'] = 'testing'
    app = create_app()
    app.config.from_pyfile(str(config_path))

    # Assert: config values are loaded
    assert app.config['KUBECONFIG_PATH'] == '/tmp/kubeconfig'
    assert app.config['PARALLEL_JOBS'] == 2
lsof -i :5000lsof -i :5000