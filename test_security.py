"""Security tests for the StarLogs web server (run with: python -m pytest test_security.py)."""
import pytest
from web_server import WebServer


@pytest.fixture
def client():
    return WebServer(port=3111).app.test_client()


def test_default_binds_localhost():
    assert WebServer(port=3111).host == '127.0.0.1'
    assert WebServer(port=3111, listen_all=True).host == '0.0.0.0'


def test_rejects_foreign_host(client):
    assert client.get('/status', headers={'Host': 'evil.example.com'}).status_code == 403


def test_rejects_cross_site_post(client):
    r = client.post('/api/config', json={'debug_mode': True}, headers={'Origin': 'https://evil.example.com'})
    assert r.status_code == 403


def test_allows_local_origin(client):
    r = client.post('/api/validate_path', json={}, headers={'Origin': 'http://localhost:3111'})
    assert r.status_code != 403


def test_lan_mode_allows_other_hosts():
    c = WebServer(port=3111, listen_all=True).app.test_client()
    assert c.get('/status', headers={'Host': '192.168.1.5:3111'}).status_code == 200


@pytest.mark.parametrize('route', ['/api/analyze_log', '/api/export_log'])
@pytest.mark.parametrize('value', [None, '', 'C:/Windows/win.ini', 'nonexistent.log', 123])
def test_log_endpoints_reject_non_log_files(client, route, value):
    assert client.post(route, json={'log_file': value}).status_code == 400
