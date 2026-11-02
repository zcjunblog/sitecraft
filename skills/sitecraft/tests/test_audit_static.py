import gzip
import json
from pathlib import Path
import struct
import subprocess
import sys
import tarfile
import tempfile
import unittest
import zipfile
import zlib

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'audit_static.py'


def png(padding=0):
    def chunk(kind, data):
        return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data))
    return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', 1, 1, 8, 6, 0, 0, 0))
            + (chunk(b'tEXt', b'comment\0' + b'x' * padding) if padding else b'')
            + chunk(b'IDAT', zlib.compress(b'\0\0\0\0\xff')) + chunk(b'IEND', b''))


class AuditTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.root = self.base / 'release'
        self.root.mkdir()
        self.html = b'<!doctype html><title>Demo</title><p>' + b'hello ' * 500 + b'</p>'
        (self.root / 'index.html').write_bytes(self.html)

    def tearDown(self):
        self.temp.cleanup()

    def archive(self, prefix=''):
        dest = self.base / 'site.zip'
        with zipfile.ZipFile(dest, 'w', zipfile.ZIP_DEFLATED) as z:
            for p in self.root.rglob('*'):
                if p.is_file():
                    z.write(p, prefix + p.relative_to(self.root).as_posix())
        return dest

    def audit(self, *args):
        result = subprocess.run([sys.executable, str(SCRIPT), str(self.root), *map(str, args)],
                                capture_output=True, text=True)
        self.assertTrue(result.stdout.strip(), result.stderr)
        return result.returncode, json.loads(result.stdout)

    def test_real_bytes_and_archive_match(self):
        archive = self.archive()
        code, r = self.audit('--archive', archive)
        self.assertEqual(code, 0)
        self.assertEqual(r['status'], 'pass')
        self.assertEqual(r['summary']['uncompressed_bytes'], len(self.html))
        self.assertEqual(r['archive']['bytes'], archive.stat().st_size)
        self.assertEqual(r['files'][0]['gzip_estimate_bytes'], len(gzip.compress(self.html, mtime=0)))
        self.assertTrue(r['archive']['content_matches'])

    def test_same_size_stale_archive_is_detected(self):
        archive = self.archive()
        (self.root / 'index.html').write_bytes(self.html.replace(b'hello', b'world'))
        code, r = self.audit('--archive', archive)
        self.assertEqual(code, 1)
        self.assertIn('archive_content_mismatch', {i['code'] for i in r['issues']})

    def test_unknown_extra_archive_file_is_not_identical(self):
        archive = self.archive()
        with zipfile.ZipFile(archive, 'a') as z:
            z.writestr('obsolete.js', 'console.log("old")')
        _, r = self.audit('--archive', archive)
        self.assertFalse(r['archive']['content_matches'])

    def test_report_cannot_overwrite_release_or_input_archive(self):
        archive = self.archive()
        before = archive.read_bytes()
        for report in [self.root / 'audit.json', archive]:
            with self.subTest(report=report):
                code, _ = self.audit('--archive', archive, '--report', report)
                self.assertEqual(code, 1)
        self.assertEqual(archive.read_bytes(), before)
        self.assertFalse((self.root / 'audit.json').exists())

    def test_references_include_css_and_srcset(self):
        (self.root / 'index.html').write_text('<link rel="stylesheet" href="style.css"><img srcset="a.png 1x, b.png 2x">')
        (self.root / 'style.css').write_text('body{background:url("/absent.svg?v=1#x")}')
        code, r = self.audit()
        missing = {i['file'] for i in r['issues'] if i['code'] == 'missing_local_asset'}
        self.assertEqual(code, 1)
        self.assertEqual(missing, {'a.png', 'b.png', 'absent.svg'})

    def test_css_ignores_comments_and_content_strings_but_reads_quoted_spaces(self):
        (self.root / 'index.html').write_text('<link rel="stylesheet" href="style.css">')
        (self.root / 'style.css').write_text('/* url(deleted.svg) */ p::before{content:"url(fake.svg)"} body{background:url("my icon.svg")}')
        (self.root / 'my icon.svg').write_text('<svg xmlns="http://www.w3.org/2000/svg"/>')
        code, r = self.audit()
        self.assertEqual(code, 0)
        self.assertFalse(any(i['level'] == 'error' for i in r['issues']))

    def test_image_format_does_not_prove_optimization(self):
        (self.root / 'photo.png').write_bytes(png())
        _, r = self.audit()
        self.assertEqual(r['images'][0]['dimensions'], [1, 1])
        self.assertEqual(r['images'][0]['optimization_evidence'], 'unverified')
        self.assertIn('image_optimization_unverified', {i['code'] for i in r['issues']})

    def test_image_evidence_compares_real_source(self):
        source = self.base / 'source.png'
        source.write_bytes(png(5000))
        (self.root / 'photo.png').write_bytes(png())
        log = self.base / 'images.json'
        log.write_text(json.dumps({'images': [{'output': 'photo.png', 'source': str(source),
            'decision': 'reencode', 'quality_review': 'passed'}]}))
        _, r = self.audit('--image-log', log)
        image = r['images'][0]
        self.assertEqual(image['optimization_evidence'], 'source_compared')
        self.assertGreater(image['source_bytes'], image['bytes'])
        self.assertEqual(image['quality_review'], 'recorded_passed')
        source.unlink()
        _, r = self.audit('--image-log', log)
        self.assertEqual(r['images'][0]['optimization_evidence'], 'unverified')

    def test_renaming_png_to_webp_is_not_conversion(self):
        (self.root / 'photo.webp').write_bytes(png())
        code, r = self.audit()
        self.assertEqual(code, 1)
        self.assertIn('image_extension_mismatch', {i['code'] for i in r['issues']})

    def test_reencoding_that_grows_needs_explanation(self):
        source = self.base / 'source.png'
        source.write_bytes(png())
        (self.root / 'photo.png').write_bytes(png(2000))
        log = self.base / 'images.json'
        log.write_text(json.dumps({'images': [{'output': 'photo.png', 'source': str(source),
            'decision': 'reencode', 'quality_review': 'passed'}]}))
        _, r = self.audit('--image-log', log)
        self.assertIn('image_grew_requires_reason', {i['code'] for i in r['issues']})

    def test_archive_does_not_allow_secret_or_unsafe_path(self):
        archive = self.archive()
        with zipfile.ZipFile(archive, 'a') as z:
            z.writestr('.env', 'private=not-a-real-secret')
            z.writestr('../outside.txt', 'bad')
        code, r = self.audit('--archive', archive)
        self.assertEqual(code, 1)
        codes = {i['code'] for i in r['issues']}
        self.assertTrue({'forbidden_deploy_file', 'unsafe_archive_path'} <= codes)
        self.assertFalse((self.base / 'outside.txt').exists())

    def test_tar_prefix_and_review_exit(self):
        archive = self.base / 'site.tar.gz'
        with tarfile.open(archive, 'w:gz') as t:
            t.add(self.root / 'index.html', arcname='dist/index.html')
        code, r = self.audit('--archive', archive, '--archive-prefix', 'dist', '--max-archive-kib', '0', '--strict')
        self.assertEqual(code, 2)
        self.assertEqual(r['status'], 'needs_review')
        self.assertTrue(r['archive']['content_matches'])


if __name__ == '__main__':
    unittest.main()
