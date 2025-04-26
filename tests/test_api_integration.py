import pytest
from app import create_app

@pytest.fixture
def client():
    app = create_app()
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_health_endpoint(client):
    resp = client.get('/health')
    assert resp.status_code == 200
    assert resp.json['status'] == 'healthy'

# Integration test using real data (no mocking)
def test_cluster_endpoint_real(client):
    resp = client.get('/api/v2/cluster')
    assert resp.status_code == 200
    assert resp.is_json
    # Check for keys expected in real OpenShift cluster data
    assert 'cluster_info_dump' in resp.json
    assert 'cluster_version_yaml' in resp.json
    assert 'infrastructure_yaml' in resp.json
    assert 'oc_version' in resp.json
