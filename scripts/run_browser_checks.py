"""Run isolated browser regressions against an owned loopback FastAPI process.

A CI run uses Playwright's installed Chromium; AR_BROWSER_EXECUTABLE can select a
local Chrome binary. Individual browser tests keep their existing Chrome default.
Production credentials are not passed to the test server or browser suites.
"""
import argparse
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
from urllib.error import URLError
from urllib.request import urlopen
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
SUITES = ('browser_check', 'browser_i18n', 'browser_interactions', 'browser_audit',
          'browser_followup', 'browser_navigation', 'browser_motion',
          'browser_entry_state', 'browser_design')
OUTPUT = ROOT / 'artifacts/browser-ci'


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--suites', nargs='+', choices=SUITES, default=list(SUITES))
    args = parser.parse_args(argv)
    OUTPUT.mkdir(parents=True, exist_ok=True)
    results, server = [], None
    failure = None
    passed = False
    with (OUTPUT / 'server.log').open('w') as server_log:
        try:
            env = os.environ.copy()
            for key in ('BOT_TOKEN', 'DATABASE_URL', 'ADMIN_ID', 'REQUIRED_CHANNEL_ID',
                        'AUTOREPLYER_SOURCE', 'WEBAPP_ORIGINS'):
                env.pop(key, None)
            with socket.socket() as sock:
                sock.bind(('127.0.0.1', 0))
                port = sock.getsockname()[1]
            env['PORT'] = str(port)
            env['AR_BASE_URL'] = f'http://127.0.0.1:{port}'
            env['PYTHONUNBUFFERED'] = '1'
            if not env.get('AR_BROWSER_EXECUTABLE'):
                with sync_playwright() as p:
                    env['AR_BROWSER_EXECUTABLE'] = p.chromium.executable_path
            if not Path(env['AR_BROWSER_EXECUTABLE']).is_file():
                raise RuntimeError('Browser not installed. Run python -m playwright install chromium, or set AR_BROWSER_EXECUTABLE.')
            server = subprocess.Popen([sys.executable, '-m', 'server.run'], cwd=ROOT,
                                      env=env, stdout=server_log, stderr=subprocess.STDOUT)
            deadline = time.monotonic() + 30
            while True:
                if server.poll() is not None:
                    raise RuntimeError('Test server exited before readiness; see server.log.')
                try:
                    with urlopen(env['AR_BASE_URL'] + '/api/health', timeout=1) as response:
                        ready = json.load(response).get('service') == 'autoreplyer-webapp'
                    if ready:
                        break
                except (URLError, OSError, ValueError):
                    pass
                if time.monotonic() >= deadline:
                    raise RuntimeError('Test server readiness timed out.')
                time.sleep(.1)
            for suite in args.suites:
                print(f'Running {suite} against the isolated local server...', flush=True)
                start = time.monotonic()
                log_path = OUTPUT / (suite + '.log')
                with log_path.open('w') as log:
                    try:
                        completed = subprocess.run([sys.executable, f'tests/{suite}.py'],
                            cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT, timeout=180)
                        code = completed.returncode
                    except subprocess.TimeoutExpired:
                        log.write('\nSuite exceeded its 180-second deadline.\n')
                        code = 124
                results.append({'suite': suite, 'passed': code == 0, 'exit_code': code,
                                'seconds': round(time.monotonic() - start, 2)})
                print(json.dumps(results[-1]), flush=True)
                if code:
                    print(log_path.read_text()[-4000:], flush=True)
            passed = all(row['passed'] for row in results) and len(results) == len(args.suites)
        except Exception as error:
            failure = str(error)
            print(f'Browser harness failed: {failure}', flush=True)
        finally:
            if server and server.poll() is None:
                server.terminate()
                try:
                    server.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    server.kill()
                    server.wait()
            summary = {'passed': passed, 'results': results, 'harness_error': failure,
                       'scope': 'Owned loopback server; demo and mocked authenticated APIs, no production writes.'}
            (OUTPUT / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    return 0 if passed else 1


if __name__ == '__main__':
    raise SystemExit(main())
