import pytest
from fastapi.testclient import TestClient

from backend.main import app


def test_frontend_root_serves_korean_application():
    with TestClient(app) as client:
        response = client.get('/')
    assert response.status_code == 200
    assert response.headers['content-type'].startswith('text/html')
    assert '<html lang="ko">' in response.text
    assert '/static/styles.css' in response.text and '/static/app.js' in response.text


@pytest.mark.parametrize('name, content_type', [('styles.css', 'text/css'), ('app.js', 'javascript')])
def test_frontend_assets_have_correct_media_types(name, content_type):
    with TestClient(app) as client:
        response = client.get(f'/static/{name}')
    assert response.status_code == 200
    assert content_type in response.headers['content-type']


def test_static_routes_leave_api_and_swagger_available():
    with TestClient(app) as client:
        assert client.get('/docs').status_code == 200
        assert client.get('/api/health').json() == {'status': 'ok'}
        assert client.get('/static/missing.js').status_code == 404
        assert client.get('/api/unknown').status_code == 404
        paths = client.get('/openapi.json').json()['paths']
    assert {'/api/chat', '/api/plans', '/api/plans/{plan_id}', '/api/logs', '/api/logs/{session_id}'} <= paths.keys()
    assert '/' not in paths
