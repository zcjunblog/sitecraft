#!/usr/bin/env python3
"""Read-only static release/ZIP/tar audit. Python standard library only."""
import argparse
import gzip
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path, PurePosixPath
import re
import stat
import struct
import sys
import tarfile
from urllib.parse import unquote, urljoin, urlsplit
import zipfile

TEXT = {'.html', '.htm', '.css', '.js', '.mjs', '.json', '.svg', '.xml', '.txt'}
RASTER = {'.png', '.jpg', '.jpeg', '.webp', '.gif', '.avif', '.ico'}
FORBIDDEN_DIRS = {'.git', 'node_modules', '__pycache__', 'qa', 'tests', '.qa-tools'}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def image_header(data):
    if data.startswith(b'\x89PNG\r\n\x1a\n') and len(data) >= 24:
        return 'png', list(struct.unpack('>II', data[16:24]))
    if data[:6] in (b'GIF87a', b'GIF89a') and len(data) >= 10:
        return 'gif', list(struct.unpack('<HH', data[6:10]))
    if data[:2] == b'\xff\xd8':
        i = 2
        while i + 9 < len(data):
            if data[i] != 255:
                i += 1
                continue
            marker = data[i + 1]
            if marker in (0xD8, 0xD9) or marker == 255:
                i += 2
                continue
            length = int.from_bytes(data[i + 2:i + 4], 'big')
            if marker in {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF}:
                h, w = struct.unpack('>HH', data[i + 5:i + 9])
                return 'jpg', [w, h]
            if length < 2:
                break
            i += length + 2
        return 'jpg', None
    if data[:4] == b'RIFF' and data[8:12] == b'WEBP':
        chunk = data[12:16]
        if chunk == b'VP8X' and len(data) >= 30:
            return 'webp', [1 + int.from_bytes(data[24:27], 'little'), 1 + int.from_bytes(data[27:30], 'little')]
        if chunk == b'VP8 ' and len(data) >= 30 and data[23:26] == b'\x9d\x01\x2a':
            return 'webp', [n & 0x3FFF for n in struct.unpack('<HH', data[26:30])]
        if chunk == b'VP8L' and len(data) >= 25 and data[20] == 0x2F:
            bits = int.from_bytes(data[21:25], 'little')
            return 'webp', [1 + (bits & 0x3FFF), 1 + ((bits >> 14) & 0x3FFF)]
        return 'webp', None
    if len(data) >= 12 and data[4:8] == b'ftyp' and (b'avif' in data[8:64] or b'avis' in data[8:64]):
        return 'avif', None  # Dimensions require a complete ISOBMFF parser.
    if data[:4] == b'\0\0\1\0' and len(data) >= 8:
        return 'ico', [data[6] or 256, data[7] or 256]
    return None, None


def forbidden(name):
    p = PurePosixPath(name)
    return (bool(set(p.parts) & FORBIDDEN_DIRS) or p.name == '.DS_Store'
            or p.name.startswith('.env') or p.suffix.lower() in {'.pem', '.key', '.p12'})


def css_urls(text):
    # Small lexical scanner: comments and content strings are not network requests.
    def escaped(i):
        i += 1
        if i >= len(text):
            return '', i
        match = re.match(r'[0-9a-fA-F]{1,6}', text[i:])
        if match:
            value = int(match.group(), 16)
            i += len(match.group())
            if i < len(text) and text[i].isspace():
                i += 1
            return chr(value) if 0 < value <= 0x10FFFF and not 0xD800 <= value <= 0xDFFF else '\ufffd', i
        return ('' if text[i] in '\r\n' else text[i]), i + 1

    def quoted(i):
        quote, value = text[i], []
        i += 1
        while i < len(text) and text[i] != quote:
            if text[i] == '\\':
                c, i = escaped(i)
                value.append(c)
            else:
                value.append(text[i])
                i += 1
        return ''.join(value), min(i + 1, len(text))

    refs, i = [], 0
    while i < len(text):
        if text.startswith('/*', i):
            end = text.find('*/', i + 2)
            i = len(text) if end < 0 else end + 2
            continue
        if text[i] in '\'"':
            _, i = quoted(i)
            continue
        if text[i] == '@' and re.match(r'@import\b', text[i:], re.I):
            j = i + 7
            while j < len(text) and text[j].isspace():
                j += 1
            if j < len(text) and text[j] in '\'"':
                value, i = quoted(j)
                refs.append(value)
                continue
        if text[i:i + 4].lower() == 'url(' and (i == 0 or not (text[i - 1].isalnum() or text[i - 1] in '_-')):
            j = i + 4
            while j < len(text) and text[j].isspace():
                j += 1
            if j < len(text) and text[j] in '\'"':
                value, j = quoted(j)
                while j < len(text) and text[j].isspace():
                    j += 1
            else:
                parts = []
                while j < len(text) and text[j] != ')':
                    if text[j] == '\\':
                        c, j = escaped(j)
                        parts.append(c)
                    else:
                        parts.append(text[j])
                        j += 1
                value = ''.join(parts).strip()
            if j < len(text) and text[j] == ')':
                refs.append(value)
            i = j + 1
            continue
        i += 1
    return refs


class Assets(HTMLParser):
    def __init__(self):
        super().__init__()
        self.refs, self.base, self.in_style = [], None, False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == 'base':
            self.base = a.get('href')
        if a.get('src'):
            self.refs.append(a['src'])
        if a.get('poster'):
            self.refs.append(a['poster'])
        if tag in {'link', 'use', 'image'} and a.get('href'):
            self.refs.append(a['href'])
        if a.get('srcset'):
            # Data-URI srcsets require a more complete browser parser; do not invent paths.
            if 'data:' in a['srcset']:
                self.refs.append('data:srcset-needs-browser-review')
            else:
                self.refs.extend(s.strip().split()[0] for s in a['srcset'].split(',') if s.strip())
        self.refs.extend(css_urls(a.get('style', '')))
        self.in_style = tag == 'style' or self.in_style

    def handle_endtag(self, tag):
        if tag == 'style':
            self.in_style = False

    def handle_data(self, data):
        if self.in_style:
            self.refs.extend(css_urls(data))


def audit(args):
    root = Path(args.directory).resolve()
    issues, files, images, data_by_name, external = [], [], [], {}, set()

    def issue(level, code, file, detail=''):
        item = {'level': level, 'code': code, 'file': file}
        if detail:
            item['detail'] = detail
        if item not in issues:
            issues.append(item)

    if not root.is_dir():
        raise ValueError('Deployment directory does not exist')
    for p in sorted(root.rglob('*')):
        name = p.relative_to(root).as_posix()
        if p.is_symlink():
            issue('error', 'symlink_in_release', name)
            continue
        if not p.is_file():
            continue
        if forbidden(name):
            issue('error', 'forbidden_deploy_file', name)
            continue  # Do not read credential or dependency contents.
        data = p.read_bytes()
        data_by_name[name] = data
        item = {'file': name, 'bytes': len(data), 'sha256': digest(data)}
        if p.suffix.lower() in TEXT:
            item['gzip_estimate_bytes'] = len(gzip.compress(data, mtime=0))
        files.append(item)
        if p.suffix.lower() == '.map':
            issue('warning', 'source_map_in_release', name)
        if p.suffix.lower() in RASTER:
            fmt, dimensions = image_header(data)
            image = dict(item, format_detected=fmt, dimensions=dimensions, optimization_evidence='unverified')
            images.append(image)
            expected = 'jpg' if p.suffix.lower() == '.jpeg' else p.suffix.lower()[1:]
            if fmt != expected:
                issue('error', 'image_extension_mismatch', name, 'Header does not match filename format')
            if len(data) > args.max_image_kib * 1024:
                issue('warning', 'large_image', name)

    if 'index.html' not in data_by_name:
        issue('error', 'missing_entrypoint', 'index.html')

    for name, data in data_by_name.items():
        suffix = PurePosixPath(name).suffix.lower()
        if suffix not in {'.html', '.htm', '.css'}:
            continue
        text = data.decode('utf-8', errors='replace')
        base = '/' + name
        if suffix in {'.html', '.htm'}:
            parser = Assets()
            parser.feed(text)
            refs = parser.refs
            if parser.base:
                base = urljoin(base, parser.base)
        else:
            refs = css_urls(text)
        for ref in refs:
            if not ref or ref.startswith('#'):
                continue
            if ref.startswith('data:'):
                if len(ref) > 4096 or ref == 'data:srcset-needs-browser-review':
                    issue('warning', 'inline_asset_needs_review', name)
                continue
            resolved = urlsplit(urljoin(base, ref))
            if resolved.scheme in {'http', 'https'} or resolved.netloc:
                external.add(resolved.geturl())
                continue
            if resolved.scheme:
                continue
            target = unquote(resolved.path).lstrip('/')
            if target.endswith('/'):
                target += 'index.html'
            if target and target not in data_by_name:
                issue('error', 'missing_local_asset', target, 'Referenced by ' + name)

    log = {}
    if args.image_log:
        log_path = Path(args.image_log).resolve()
        for row in json.loads(log_path.read_text())['images']:
            if row['output'] in log:
                raise ValueError('Duplicate image log output: ' + row['output'])
            log[row['output']] = row
        for output in set(log) - {i['file'] for i in images}:
            issue('warning', 'image_log_output_missing', output)
    for image in images:
        record = log.get(image['file'], {})
        source = record.get('source')
        source_path = Path(source) if source else None
        if source_path and not source_path.is_absolute():
            source_path = Path(args.image_log).resolve().parent / source_path
        if source_path and source_path.is_file():
            before = source_path.read_bytes()
            image['source_bytes'] = len(before)
            image['source_dimensions'] = image_header(before)[1]
            image['saved_bytes'] = len(before) - image['bytes']
            if image['saved_bytes'] < 0 and not record.get('reason'):
                issue('warning', 'image_grew_requires_reason', image['file'])
            if digest(before) != image['sha256'] and record.get('decision'):
                image['optimization_evidence'] = 'source_compared'
            elif record.get('decision') == 'preserve' and record.get('reason'):
                image['optimization_evidence'] = 'preserved_with_reason'
                image['preservation_reason'] = record['reason']
        if image['optimization_evidence'] == 'unverified':
            issue('warning', 'image_optimization_unverified', image['file'])
        image['quality_review'] = 'recorded_passed' if record.get('quality_review') == 'passed' else 'not_recorded'
        if image['quality_review'] == 'not_recorded':
            issue('warning', 'image_quality_review_missing', image['file'])

    archive_report = None
    if args.archive:
        archive = Path(args.archive).resolve()
        archive_report = {'bytes': archive.stat().st_size, 'sha256': digest(archive.read_bytes()), 'content_matches': True}
        if archive.stat().st_size > args.max_archive_kib * 1024:
            issue('warning', 'archive_budget_exceeded', archive.name)
        prefix = args.archive_prefix.strip('/')
        if prefix:
            prefix += '/'
        seen = set()

        def inspect(name, size, opener, is_link=False):
            # Never extract an archive; validate names and stream only matching regular files.
            if '\\' in name or name.startswith('/') or '..' in PurePosixPath(name).parts or is_link:
                issue('error', 'unsafe_archive_path', name)
                archive_report['content_matches'] = False
                return
            if forbidden(name):
                issue('error', 'forbidden_deploy_file', name)
                archive_report['content_matches'] = False
            if prefix and not name.startswith(prefix):
                if name == '.openai/hosting.json':
                    return
                issue('warning', 'archive_outside_prefix', name)
                archive_report['content_matches'] = False
                return
            relative = name[len(prefix):]
            if relative in seen:
                issue('error', 'duplicate_archive_entry', relative)
                archive_report['content_matches'] = False
            seen.add(relative)
            expected = data_by_name.get(relative)
            if expected is None:
                if relative != '.openai/hosting.json':
                    issue('warning', 'archive_extra_file', relative)
                    archive_report['content_matches'] = False
                return
            same = size == len(expected)
            if same:
                with opener() as f:
                    same = digest(f.read(len(expected) + 1)) == digest(expected)
            if not same:
                issue('error', 'archive_content_mismatch', relative)
                archive_report['content_matches'] = False

        if zipfile.is_zipfile(archive):
            with zipfile.ZipFile(archive) as z:
                for member in z.infolist():
                    if not member.is_dir():
                        inspect(member.filename, member.file_size, lambda m=member: z.open(m),
                                stat.S_ISLNK(member.external_attr >> 16))
        else:
            with tarfile.open(archive) as t:
                for member in t:
                    if not member.isdir():
                        inspect(member.name, member.size, lambda m=member: t.extractfile(m), not member.isfile())
        for missing in set(data_by_name) - seen:
            issue('error', 'archive_missing_file', missing)
            archive_report['content_matches'] = False
    else:
        issue('warning', 'archive_not_checked', '')

    status = 'fail' if any(i['level'] == 'error' for i in issues) else 'needs_review' if issues else 'pass'
    return {'scope': 'Static artifact audit; gzip is a local estimate, not wire bytes. Not a page-speed or visual-quality certificate.',
            'status': status, 'summary': {'file_count': len(files), 'uncompressed_bytes': sum(f['bytes'] for f in files),
            'image_bytes': sum(i['bytes'] for i in images),
            'text_gzip_estimate_bytes': sum(f.get('gzip_estimate_bytes', 0) for f in files)},
            'budgets': {'max_archive_kib': args.max_archive_kib, 'max_image_kib': args.max_image_kib, 'kind': 'review thresholds, not universal limits'},
            'archive': archive_report, 'largest_files': sorted(files, key=lambda f: f['bytes'], reverse=True)[:10],
            'images': images, 'external_references': sorted(external), 'files': files, 'issues': issues,
            'limitations': ['No full JavaScript import/fetch graph or runtime lazy-load analysis.',
                            'Image headers do not establish decoding correctness or visual quality.',
                            'Image quality_review is a recorded human review, not an automated quality score.']}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('directory', help='Final static web root, not the source repository')
    p.add_argument('--archive', help='Final ZIP or tar archive to compare without extracting')
    p.add_argument('--archive-prefix', default='', help='Web-root prefix inside archive, e.g. dist')
    p.add_argument('--image-log', help='JSON with images [{output, source, decision, quality_review, reason?}]')
    p.add_argument('--max-archive-kib', type=float, default=3072)
    p.add_argument('--max-image-kib', type=float, default=350)
    p.add_argument('--report', help='Write report outside the deploy directory')
    p.add_argument('--strict', action='store_true', help='Exit 2 when review warnings remain; errors always exit 1')
    args = p.parse_args()
    report_destination = None
    try:
        if args.report:
            target = Path(args.report).resolve()
            root = Path(args.directory).resolve()
            inputs = {Path(v).resolve() for v in [args.archive, args.image_log] if v}
            if target == root or root in target.parents or target in inputs:
                raise ValueError('Report must be outside the deployment directory and must not overwrite input files')
            report_destination = target
        if args.max_archive_kib < 0 or args.max_image_kib < 0:
            raise ValueError('Budgets must be non-negative')
        report = audit(args)
    except (OSError, ValueError, KeyError, TypeError, RuntimeError, zipfile.BadZipFile, tarfile.TarError) as e:
        report = {'status': 'fail', 'issues': [{'level': 'error', 'code': 'audit_failed', 'detail': str(e)}]}
    encoded = json.dumps(report, ensure_ascii=False, indent=2) + '\n'
    if report_destination:
        report_destination.parent.mkdir(parents=True, exist_ok=True)
        report_destination.write_text(encoded)
    print(encoded, end='')
    return 1 if report['status'] == 'fail' else 2 if args.strict and report['status'] == 'needs_review' else 0


if __name__ == '__main__':
    sys.exit(main())
