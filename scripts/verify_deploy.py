"""Verify an exact Render revision using public GET requests only. No credentials."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ('index.html', 'app.js', 'styles.css', 'premium.css', 'interactions.js',
          'translations.js', 'i18n.js', 'api-client.js', 'navigation.js',
          'storage.js', 'config.json', 'icon.svg')


def fetch(base, path):
    request = Request(base + path, headers={'Cache-Control': 'no-cache'})
    try:
        response = urlopen(request, timeout=35)
    except HTTPError as error:
        response = error
    with response:
        return response.status, response.headers, response.read(2_000_000)


def verify_once(base, revision, dist=ROOT / 'dist'):
    parsed = urlsplit(base)
    if (parsed.scheme not in ('https', 'http') or not parsed.hostname or
        (parsed.scheme == 'http' and parsed.hostname not in ('127.0.0.1', 'localhost', '::1')) or
        parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path not in ('', '/')):
        raise ValueError('Use an HTTPS service root (HTTP only for loopback tests).')
    if not re.fullmatch(r'[0-9a-f]{40}', revision):
        raise ValueError('Expected revision must be a complete commit SHA.')
    base = base.rstrip('/')
    status, headers, body = fetch(base, '/api/health')
    if status != 200:
        raise ValueError(f'Health returned {status}.')
    health = json.loads(body)
    if health.get('status') != 'ok' or health.get('service') != 'autoreplyer-webapp':
        raise ValueError('Unexpected health response.')
    if health.get('revision') != revision:
        raise ValueError(f'Revision mismatch: expected {revision}, served {health.get("revision")}.')
    if headers.get('Cache-Control') != 'no-store':
        raise ValueError('Health cache policy missing.')
    for directive in ("object-src 'none'", 'https://web.telegram.org'):
        if directive not in headers.get('Content-Security-Policy', ''):
            raise ValueError('Expected CSP protection missing.')
    if headers.get('X-Content-Type-Options') != 'nosniff':
        raise ValueError('nosniff header missing.')
    checked = {}
    for path, expected in [('/api/bootstrap', 401), ('/openapi.json', 404), ('/server/app.py', 404)]:
        status, headers, _ = fetch(base, path)
        if status != expected:
            raise ValueError(f'{path} returned {status}, expected {expected}.')
        if path == '/api/bootstrap' and headers.get('Cache-Control') != 'no-store':
            raise ValueError('Unsigned API cache policy missing.')
        checked[path] = status
    assets = {}
    for name in ASSETS:
        status, _, content = fetch(base, '/' if name == 'index.html' else '/' + name)
        if status != 200 or content != (dist / name).read_bytes():
            raise ValueError(f'Deployed asset does not match this checkout: {name}.')
        assets[name] = hashlib.sha256(content).hexdigest()
    return {'checked_at': datetime.now(timezone.utc).isoformat(), 'base_url': base,
            'expected_revision': revision, 'served_revision': health['revision'],
            'checks': checked, 'assets_sha256': assets,
            'scope': 'Public GET requests only; no authenticated user or bot delivery test.'}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-url', default='https://autoreplyer-web-app.onrender.com')
    parser.add_argument('--revision', required=True)
    parser.add_argument('--attempts', type=int, default=1)
    parser.add_argument('--interval', type=float, default=10)
    parser.add_argument('--output', type=Path, default=ROOT / 'artifacts/render-verification.json')
    args = parser.parse_args(argv)
    if args.attempts < 1 or args.interval < 0:
        parser.error('attempts must be positive; interval cannot be negative.')
    report = {}
    for attempt in range(1, args.attempts + 1):
        try:
            report = verify_once(args.base_url, args.revision)
            report['result'] = 'passed'
            break
        except (ValueError, OSError, URLError) as error:
            report = {'result': 'failed', 'expected_revision': args.revision,
                      'checked_at': datetime.now(timezone.utc).isoformat(),
                      'attempt': attempt, 'error': str(error)}
            print(json.dumps(report), flush=True)
            if attempt < args.attempts:
                time.sleep(args.interval)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report))
    return 0 if report['result'] == 'passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
