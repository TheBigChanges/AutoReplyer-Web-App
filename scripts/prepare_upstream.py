"""Prepare immutable Docker-pinned bot source and a fresh test-source manifest.

The manifest describes downloaded source, not a cached successful test result.
CI must still run the real PostgreSQL contract tests against that source.
"""
import argparse
from datetime import datetime, timezone
import hashlib
from io import BytesIO
import json
import os
from pathlib import Path
import re
import tarfile
import tempfile
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
MODULES = ('db.py', 'logic.py', 'analytics.py', 'i18n.py', 'automation.py')


def docker_ref(dockerfile):
    match = re.search(r'^ARG AUTOREPLYER_REF=([0-9a-f]{40})\s*$',
                      Path(dockerfile).read_text(), re.MULTILINE)
    if not match:
        raise ValueError('Dockerfile must pin AUTOREPLYER_REF to a full commit SHA.')
    return match.group(1)


def prepare_source(dockerfile, destination, output):
    ref = docker_ref(dockerfile)
    url = f'https://codeload.github.com/TheBigChanges/AutoReplyer/tar.gz/{ref}'
    with urlopen(url, timeout=60) as response:
        content = response.read()
    prefix = 'AutoReplyer-' + ref
    with tarfile.open(fileobj=BytesIO(content), mode='r:gz') as archive:
        members = archive.getmembers()
        if not members or any(not Path(member.name).parts or Path(member.name).parts[0] != prefix for member in members):
            raise ValueError('Archive root does not match the selected Docker commit.')
        destination = Path(destination).resolve()
        destination.mkdir(parents=True, exist_ok=True)
        # A fresh extraction prevents files from an older checkout affecting imports.
        stage = Path(tempfile.mkdtemp(prefix='source-', dir=destination))
        archive.extractall(stage, filter='data')
    source = stage / prefix
    if not all((source / name).is_file() for name in MODULES):
        raise ValueError('Pinned archive is missing required bot modules.')
    manifest = {'upstream_ref': ref,
                'source_sha256': {name: hashlib.sha256((source / name).read_bytes()).hexdigest() for name in MODULES},
                'archive_sha256': hashlib.sha256(content).hexdigest(),
                'download_url': url, 'source_path': str(source),
                'prepared_at': datetime.now(timezone.utc).isoformat(),
                'scope': 'Downloaded source identity only. See the current CI test outcome for compatibility.'}
    output = Path(output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(manifest, indent=2) + '\n')
    return manifest


def verify_source(source, manifest, pin):
    if manifest.get('upstream_ref') != pin:
        raise RuntimeError('Test-source manifest does not match Docker pin. Run scripts/prepare_upstream.py and set AR_TEST_UPSTREAM_MANIFEST.')
    hashes = manifest.get('source_sha256', {})
    if set(hashes) != set(MODULES):
        raise RuntimeError('Test-source manifest must cover all required bot modules.')
    for name in MODULES:
        if hashlib.sha256((Path(source) / name).read_bytes()).hexdigest() != hashes[name]:
            raise RuntimeError(f'Unexpected upstream source: {name}')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dockerfile', type=Path, default=ROOT / 'Dockerfile')
    parser.add_argument('--dest', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    manifest = prepare_source(args.dockerfile, args.dest, args.output)
    if os.environ.get('GITHUB_ENV'):
        values = {'AUTOREPLYER_SOURCE': manifest['source_path'],
                  'AR_TEST_UPSTREAM_MANIFEST': str(args.output.resolve())}
        if any('\n' in value or '\r' in value for value in values.values()):
            raise ValueError('CI source paths cannot contain newlines.')
        with Path(os.environ['GITHUB_ENV']).open('a') as env:
            for key, value in values.items():
                env.write(f'{key}={value}\n')
    print(json.dumps(manifest))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
