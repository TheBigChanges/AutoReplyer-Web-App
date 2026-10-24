"""Pin changes prepare new verified inputs; wrong or altered source cannot pass."""
import hashlib
from io import BytesIO
import json
from pathlib import Path
import tarfile
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from scripts import prepare_upstream


class UpstreamPreparationTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.docker = self.root / 'Dockerfile'
        self.output = self.root / 'manifest.json'

    def archive(self, ref, missing=None, extra=None):
        data = BytesIO()
        with tarfile.open(fileobj=data, mode='w:gz') as tar:
            for name in prepare_upstream.MODULES:
                if name == missing:
                    continue
                body = f'# {ref} {name}\n'.encode()
                info = tarfile.TarInfo(f'AutoReplyer-{ref}/{name}')
                info.size = len(body)
                tar.addfile(info, BytesIO(body))
            if extra:
                info = tarfile.TarInfo(extra)
                info.size = 1
                tar.addfile(info, BytesIO(b'x'))
        return data.getvalue()

    def prepare(self, ref, archive_ref=None, missing=None, extra=None):
        self.docker.write_text(f'FROM python:3.13-slim\nARG AUTOREPLYER_REF={ref}\n')
        content = self.archive(archive_ref or ref, missing, extra)
        with patch.object(prepare_upstream, 'urlopen', return_value=BytesIO(content)) as get:
            result = prepare_upstream.prepare_source(self.docker, self.root/'source', self.output)
        get.assert_called_once_with(f'https://codeload.github.com/TheBigChanges/AutoReplyer/tar.gz/{ref}', timeout=60)
        return result

    def test_updated_pin_creates_fresh_manifest_without_reusing_old_success(self):
        first = self.prepare('a'*40)
        second = self.prepare('b'*40)
        self.assertEqual(second['upstream_ref'], 'b'*40)
        self.assertNotEqual(first['source_path'], second['source_path'])
        self.assertNotEqual(first['source_sha256'], second['source_sha256'])
        for name, digest in second['source_sha256'].items():
            self.assertEqual(hashlib.sha256((Path(second['source_path'])/name).read_bytes()).hexdigest(), digest)
        self.assertNotIn('status', second)
        self.assertEqual(json.loads(self.output.read_text()), second)

    def test_wrong_manifest_and_post_download_changes_remain_rejected(self):
        manifest = self.prepare('a'*40)
        source = Path(manifest['source_path'])
        prepare_upstream.verify_source(source, manifest, 'a'*40)
        with self.assertRaisesRegex(RuntimeError, 'does not match Docker pin'):
            prepare_upstream.verify_source(source, manifest, 'b'*40)
        (source/'db.py').write_text('# modified after preparation')
        with self.assertRaisesRegex(RuntimeError, 'Unexpected upstream source: db.py'):
            prepare_upstream.verify_source(source, manifest, 'a'*40)

    def test_archive_from_another_commit_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Archive root'):
            self.prepare('a'*40, archive_ref='b'*40)
        self.assertFalse(self.output.exists())

    def test_missing_bot_module_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'missing required'):
            self.prepare('a'*40, missing='db.py')
        self.assertFalse(self.output.exists())

    def test_unpinned_ref_is_rejected_before_network_access(self):
        for ref in ['main', 'v1', 'abc123', 'a'*40+' trailing']:
            self.docker.write_text(f'ARG AUTOREPLYER_REF={ref}\n')
            with patch.object(prepare_upstream, 'urlopen') as get, self.assertRaises(ValueError):
                prepare_upstream.prepare_source(self.docker, self.root/'source', self.output)
            get.assert_not_called()

    def test_path_traversal_is_rejected(self):
        with self.assertRaises((ValueError, tarfile.FilterError)):
            self.prepare('a'*40, extra=f'AutoReplyer-{"a"*40}/../../escaped.py')
        self.assertFalse((self.root/'source'/'escaped.py').exists())
        self.assertFalse(self.output.exists())


if __name__ == '__main__':
    unittest.main()
