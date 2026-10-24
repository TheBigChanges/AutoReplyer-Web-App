"""A deploy proof must match both the server revision and the actual public assets."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from threading import Thread
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from scripts import verify_deploy
from server import app as adapter

SHA = 'a' * 40


class HealthRevisionTests(unittest.TestCase):
    def test_health_reports_only_a_valid_public_commit_without_database_access(self):
        with TestClient(adapter.app) as client, patch.object(adapter, 'modules', side_effect=AssertionError('Health must not access DB')):
            for value, expected in [(SHA, SHA), ('not-a-commit', None), ('', None)]:
                with patch.dict(os.environ, {'RENDER_GIT_COMMIT': value}):
                    response = client.get('/api/health')
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json()['revision'], expected)
                self.assertEqual(response.headers['cache-control'], 'no-store')


class DeployProbeTests(unittest.TestCase):
    def setUp(self):
        test = self
        self.revision = SHA
        self.tampered = None
        self.bootstrap_status = 401
        self.csp = True
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                if self.path == '/api/health':
                    status, body = 200, json.dumps({'status':'ok', 'service':'autoreplyer-webapp', 'revision':test.revision}).encode()
                elif self.path == '/api/bootstrap':
                    status, body = test.bootstrap_status, b'{}'
                elif self.path in ['/openapi.json', '/server/app.py']:
                    status, body = 404, b'{}'
                else:
                    name = 'index.html' if self.path == '/' else self.path.lstrip('/')
                    status = 200
                    body = b'changed' if test.tampered == name else (verify_deploy.ROOT/'dist'/name).read_bytes()
                self.send_response(status)
                self.send_header('Cache-Control','no-store')
                self.send_header('X-Content-Type-Options','nosniff')
                if test.csp:
                    self.send_header('Content-Security-Policy', "object-src 'none'; frame-ancestors https://web.telegram.org")
                self.end_headers()
                self.wfile.write(body)
            def log_message(self, *args):
                pass
        self.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        self.thread = Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f'http://127.0.0.1:{self.server.server_port}'

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()

    def test_reports_matching_revision_and_all_assets(self):
        result = verify_deploy.verify_once(self.base, SHA)
        self.assertEqual(result['served_revision'], SHA)
        self.assertEqual(len(result['assets_sha256']), len(verify_deploy.ASSETS))

    def test_healthy_old_revision_is_rejected(self):
        self.revision = 'b' * 40
        with self.assertRaisesRegex(ValueError, 'Revision mismatch'):
            verify_deploy.verify_once(self.base, SHA)

    def test_matching_health_with_stale_asset_is_rejected(self):
        self.tampered = 'app.js'
        with self.assertRaisesRegex(ValueError, 'asset does not match'):
            verify_deploy.verify_once(self.base, SHA)

    def test_unsigned_access_or_missing_headers_cannot_pass(self):
        self.bootstrap_status = 200
        with self.assertRaisesRegex(ValueError, 'expected 401'):
            verify_deploy.verify_once(self.base, SHA)
        self.bootstrap_status = 401
        self.csp = False
        with self.assertRaisesRegex(ValueError, 'CSP'):
            verify_deploy.verify_once(self.base, SHA)


if __name__ == '__main__':
    unittest.main()
