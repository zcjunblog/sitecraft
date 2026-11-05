#!/usr/bin/env python3
"""Track Sitecraft stage evidence, prerequisites and revision freshness. Standard library only."""
import argparse
from contextlib import contextmanager
import hashlib
import json
import math
import os
from pathlib import Path
import tempfile
import time
import subprocess
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from uuid import uuid4

from audit_static import image_header


STAGES = {
    'brief': (['brief'], ['requirements']),
    'references': (['reference_notes', 'reference_capture'], ['source_observed', 'design_mapping']),
    'first-screen': (['entry', 'browser_report'], ['background_and_fonts']),
    'visual': (['desktop', 'mobile'], ['brand_fit', 'hierarchy', 'mobile_crop']),
    'site': (['entry', 'desktop_full', 'mobile_full', 'interaction_log', 'browser_report'],
             ['content', 'mobile_layout', 'controls', 'motion', 'transition', 'lighting', 'reduced_motion', 'webgl']),
    'performance': (['mobile_report', 'desktop_report'], ['page_identity']),
    'delivery': (['package', 'audit_report', 'preview_audit', 'package_preview', 'handoff'],
                 ['image_quality', 'package_preview', 'instructions']),
}
NAMES = list(STAGES)
FEATURES = ('motion', 'transition', 'lighting', 'webgl')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read_json(path):
    value = json.loads(path.read_text(encoding='utf-8'))
    require(isinstance(value, dict), f'Expected a JSON object: {path.name}')
    return value


def digest(path):
    require(path.is_file() and path.stat().st_size > 0, f'Missing or empty artifact: {path}')
    return hashlib.sha256(path.read_bytes()).hexdigest()


def site_files(site):
    files = {}
    for path in sorted(site.rglob('*')):
        require(not path.is_symlink(), f'Symlinks are unsupported in the release tree: {path}')
        if path.is_file():
            files[path.relative_to(site).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    return files


def site_digest(site):
    return hashlib.sha256(json.dumps(site_files(site), sort_keys=True).encode()).hexdigest()


def save(run, state):
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=run, delete=False) as output:
            temporary = Path(output.name)
            json.dump(state, output, ensure_ascii=False, indent=2, allow_nan=False)
            output.write('\n')
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, run / 'workflow.json')
    finally:
        if temporary and temporary.exists():
            temporary.unlink()


@contextmanager
def locked(run):
    run.mkdir(parents=True, exist_ok=True)
    lock = run / '.workflow.lock'
    try:
        descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        raise ValueError('Another workflow writer holds .workflow.lock. Retry after it finishes; inspect a leftover lock before removing it.')
    try:
        with os.fdopen(descriptor, 'w') as output:
            output.write(str(os.getpid()))
        yield
    finally:
        lock.unlink()


def invalidate(state, stage, reason):
    for name in NAMES[NAMES.index(stage):]:
        state['stages'][name] = {'status': 'stale', 'reason': reason}


def refresh(state):
    current = site_digest(Path(state['site']))
    for name in NAMES:
        stage = state['stages'][name]
        if stage['status'] != 'pass':
            continue
        try:
            require(not stage.get('site_sha256') or stage['site_sha256'] == current, 'Site content changed')
            for path, expected in stage['artifacts'].items():
                require(digest(Path(path)) == expected, f'Artifact changed: {path}')
        except (ValueError, OSError) as error:
            invalidate(state, name, str(error))
            break


def prerequisites(state, stage):
    for name in NAMES[:NAMES.index(stage)]:
        require(state['stages'][name]['status'] == 'pass', f'Complete and recheck {name} before {stage}')


def png_dimensions(path):
    data = path.read_bytes()
    require(data[:8] == b'\x89PNG\r\n\x1a\n' and len(data) >= 24, f'Expected a PNG screenshot: {path.name}')
    return [int.from_bytes(data[16:20], 'big'), int.from_bytes(data[20:24], 'big')]


def fresh(path, active):
    require(path.stat().st_mtime_ns >= active['started_ns'], f'Run a fresh check after start: {path.name}')


def receipt(path, active, tool, root):
    item = active.get('receipts', {}).get(str(path))
    require(item and item['tool'] == tool and item['root'] == str(root),
            f'Run workflow.py check for a fresh {tool} report from the configured directory')
    for filename, expected in item['files'].items():
        require(digest(Path(filename)) == expected, f'Captured evidence changed: {filename}')


def captured_file(path, active, root):
    owner = next((Path(name) for name, item in active.get('receipts', {}).items()
                  if str(path) in item['files'] and item['tool'] == 'browser' and item['root'] == str(root)), None)
    require(owner, 'Capture this artifact with workflow.py check in the current stage')
    receipt(owner, active, 'browser', root)


class PreviewHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        if self.path == '/favicon.ico':
            self.send_response(204)
            self.end_headers()
        else:
            super().do_GET()


def run_check(state, run, args):
    active = state.get('active')
    require(active, 'Start a stage before running checks')
    allowed = {'first-screen': ['browser'], 'visual': ['browser'], 'site': ['browser'],
               'performance': ['mobile', 'desktop'], 'delivery': ['audit', 'preview-audit', 'preview']}
    require(args.tool in allowed.get(active['stage'], []), 'This tool does not belong to the active stage')
    site = Path(state['site'])
    root = Path(args.preview_root).resolve() if args.tool in ('preview', 'preview-audit') and args.preview_root else site
    if args.tool in ('preview', 'preview-audit'):
        require(root != site and site_files(root) == site_files(site), 'Preview must use an independent matching delivery directory')
    require(active['site_sha256'] == site_digest(site), 'Site changed; restart the affected stage')
    directory = run / 'checks' / uuid4().hex
    directory.mkdir(parents=True)
    output = directory / ('review.json' if args.tool in ('browser', 'preview') else 'report.json')
    script_dir = Path(__file__).resolve().parent
    if args.tool in ('audit', 'preview-audit'):
        command = [os.sys.executable, str(script_dir / 'audit_static.py'), str(root), '--report', str(output), '--strict']
        if args.package:
            command += ['--archive', str(Path(args.package).resolve())]
        if args.image_log:
            command += ['--image-log', str(Path(args.image_log).resolve())]
        plan = read_json(Path(state['stages']['brief']['brief_path']))
        for budget in ('archive_kib', 'image_kib'):
            if budget in plan['budgets']:
                command += ['--max-' + budget.replace('_', '-'), str(plan['budgets'][budget])]
        if args.archive_prefix:
            command += ['--archive-prefix', args.archive_prefix]
        process = subprocess.run(command, capture_output=True, text=True, timeout=180)
    else:
        server = ThreadingHTTPServer(('127.0.0.1', 0), partial(PreviewHandler, directory=str(root)))
        worker = Thread(target=server.serve_forever, daemon=True)
        worker.start()
        try:
            url = f'http://127.0.0.1:{server.server_port}/'
            if args.tool in ('browser', 'preview'):
                require(args.primary, 'Provide the actual --primary selector')
                command = ['node', str(script_dir / 'review_site.mjs'), '--url', url, '--out', str(directory), '--primary', args.primary]
                if active['stage'] != 'site':
                    command += ['--draft']
                else:
                    command += ['--full-page']
                if args.primary_target:
                    command += ['--primary-target', args.primary_target]
                if args.motion_plan:
                    command += ['--motion-plan', str(Path(args.motion_plan).resolve())]
                require(active['stage'] != 'site' or args.primary_target, 'Full site checks require --primary-target')
            else:
                plan = read_json(Path(state['stages']['brief']['brief_path']))
                command = ['node', str(script_dir / 'measure_page.mjs'), '--url', url, '--report', str(output),
                           '--profile', args.tool, '--runs', '3', '--warm', '--expect-title', plan['title']]
            if args.playwright_module:
                command += ['--playwright-module', args.playwright_module]
            if args.channel:
                command += ['--channel', args.channel]
            process = subprocess.run(command, capture_output=True, text=True, timeout=240)
        finally:
            server.shutdown()
            server.server_close()
            worker.join()
    require(output.is_file(), f'Check did not produce a report: {process.stderr[-1000:]}')
    require(active['site_sha256'] == site_digest(site), 'Site changed during capture; restart and rerun checks')
    require(root == site or site_files(root) == site_files(site), 'Preview files changed during capture')
    files = {str(path.resolve()): digest(path) for path in directory.iterdir() if path.is_file()}
    active.setdefault('receipts', {})[str(output)] = {'tool': args.tool, 'root': str(root),
                                                     'exit_code': process.returncode, 'files': files}
    return {'report': str(output), 'tool_exit_code': process.returncode, 'status': read_json(output).get('status')}


def check_browser(path, active, tracked, title, full=False):
    fresh(path, active)
    report = read_json(path)
    require(report.get('status') == 'pass', f'Browser report has not passed: {path.name}')
    profiles = {item['profile']: item for item in report.get('profiles', [])}
    wanted = ['desktop', 'mobile', 'reduced-motion'] if full else ['desktop', 'mobile']
    for name in wanted:
        profile = profiles.get(name, {})
        require(profile and profile.get('issues') == [], f'Browser issues or missing profile: {name}')
        require(title in profile.get('title', ''), f'Unexpected browser page identity: {name}')
        require(profile.get('primary_action', {}).get('status') == 'pass', f'Primary action not verified: {name}')
        screenshot = (path.parent / profile['screenshot']).resolve()
        expected = [1440, 900] if name == 'desktop' else [390, 844]
        require(profile.get('layout', {}).get('viewport') == expected, f'Unexpected viewport: {name}')
        require(png_dimensions(screenshot) == expected, f'Unexpected screenshot size: {name}')
        fresh(screenshot, active)
        tracked[str(screenshot)] = digest(screenshot)


def check_brief(plan, state):
    require(plan.get('request') == state['request'], 'Keep the original request in the brief')
    for key in ('audience', 'primary_action', 'title'):
        require(isinstance(plan.get(key), str) and plan[key].strip(), f'Brief requires {key}')
    require(isinstance(plan.get('content'), list) and plan['content'], 'Brief requires actual content sections')
    require(isinstance(plan.get('constraints'), list), 'Brief requires constraints, including explicit user choices')
    for name in FEATURES:
        feature = plan.get('features', {}).get(name, {})
        require(type(feature.get('enabled')) is bool, f'Declare feature enabled: {name}')
        if not feature['enabled']:
            require(feature.get('reason', '').strip(), f'Explain why {name} is outside the requested scope')
            if name != 'webgl':
                quote = feature.get('source_quote')
                require(isinstance(quote, str) and quote.strip() and quote in state['request'],
                        f'Disabling {name} requires the original user constraint as source_quote')
    for name in ('lcp_ms', 'cls', 'transfer_bytes'):
        value = plan.get('budgets', {}).get(name)
        require(type(value) in (int, float) and math.isfinite(value) and value >= 0,
                f'Declare a finite performance budget: {name}')
    for name in ('archive_kib', 'image_kib'):
        if name in plan['budgets']:
            require(type(plan['budgets'][name]) is int and plan['budgets'][name] > 0, f'Invalid optional budget: {name}')


def check_performance(path, profile, plan, active):
    fresh(path, active)
    report = read_json(path)
    require(report.get('status') == 'measured', f'Performance was not measured: {profile}')
    require(report.get('environment', {}).get('profile') == profile, f'Wrong performance profile: {profile}')
    samples = report.get('samples', [])
    require(sum(s.get('cache_mode') == 'cold' for s in samples) >= 3 and
            any(s.get('cache_mode') == 'warm' for s in samples), f'Need three cold and one warm sample: {profile}')
    for sample in samples:
        require(plan['title'] in sample.get('title', ''), f'Unexpected page identity: {profile}')
        require(sample.get('transferred_bytes_complete') is True, f'Incomplete transfer observation: {profile}')
        for key in ('request_issues', 'javascript_errors', 'console_errors'):
            require(sample.get(key) == [], f'{key} in performance sample: {profile}')
        for metric, budget in [('lcp_observed_ms', 'lcp_ms'), ('cls_observed', 'cls')]:
            value = sample.get('metrics', {}).get(metric)
            require(type(value) in (int, float) and math.isfinite(value) and
                    0 <= value <= plan['budgets'][budget], f'Missing or over-budget {metric}: {profile}')
        transferred = sample.get('transferred_bytes')
        require(type(transferred) in (int, float) and math.isfinite(transferred) and
                0 <= transferred <= plan['budgets']['transfer_bytes'], f'Transfer budget exceeded: {profile}')


def check_motion(path, tracked, features, active):
    # A time-indexed sequence makes intermediate states reviewable without bundling video codecs.
    capture = read_json(path)
    for effect in ('motion', 'transition', 'lighting'):
        if not features[effect]['enabled']:
            continue
        sequence = capture.get(effect, {})
        require(sequence.get('trigger', '').strip(), f'Record the observed trigger for {effect}')
        for profile in ('desktop', 'mobile'):
            frames = sequence.get(profile, [])
            require(len(frames) >= 3, f'{effect} needs at least three timed frames: {profile}')
            previous, hashes = -1, set()
            for frame in frames:
                timestamp = frame.get('ms')
                require(type(timestamp) in (int, float) and math.isfinite(timestamp) and timestamp > previous,
                        f'Motion timestamps must increase: {profile}')
                previous = timestamp
                image = (path.parent / frame['file']).resolve()
                expected = [1440, 900] if profile == 'desktop' else [390, 844]
                require(png_dimensions(image) == expected, f'Invalid motion frame viewport: {profile}')
                fresh(image, active)
                tracked[str(image)] = digest(image)
                hashes.add(tracked[str(image)])
            require(len(hashes) > 1, f'Motion evidence must include distinct states: {effect}/{profile}')


def check_audit(path, state, package, active, inline_review=False):
    fresh(path, active)
    audit = read_json(path)
    html_only = state['delivery'] == 'html'
    allowed_warnings = {'archive_not_checked'} if html_only else set()
    if inline_review:
        allowed_warnings.add('inline_asset_needs_review')
    expected_warnings = audit.get('status') == 'needs_review' and audit.get('issues') and all(
        item.get('level') == 'warning' and item.get('code') in allowed_warnings for item in audit['issues'])
    require(audit.get('status') == 'pass' or expected_warnings, 'Package audit must pass, including review warnings')
    root = Path(audit['root']).resolve()
    files = {item['file']: item['sha256'] for item in audit.get('files', [])}
    require(files == site_files(root) == site_files(Path(state['site'])), 'Audit does not match the current release tree')
    if html_only:
        require(set(files) == {'index.html'} and not audit.get('external_references'), 'Offline HTML must be self-contained')
    else:
        archive = audit.get('archive') or {}
        require(archive.get('content_matches') is True and archive.get('sha256') == digest(package),
                'Package does not match the audited archive')
    return root


def validate(state, stage, evidence_path, tracked):
    active = state['active']
    fresh(evidence_path, active)
    report = read_json(evidence_path)
    require(report.get('stage') == stage and report.get('status') == 'pass', 'Stage result must explicitly pass this stage')
    require(isinstance(report.get('reviewer'), str) and report['reviewer'].strip(), 'Record who performed the review')
    artifact_names, checks = STAGES[stage]
    artifacts = report.get('artifacts', {})
    require(isinstance(artifacts, dict) and all(isinstance(value, str) for value in artifacts.values()),
            'Artifacts must map names to file paths')
    require(isinstance(report.get('checks'), dict), 'Checks must be a named object')
    require(all(artifacts.get(name) for name in artifact_names), 'Missing required artifact names')
    paths = {name: (evidence_path.parent / value).resolve() for name, value in artifacts.items()}
    tracked[str(evidence_path)] = digest(evidence_path)
    for path in paths.values():
        tracked[str(path)] = digest(path)
    plan = read_json(Path(state['stages']['brief']['brief_path'])) if stage != 'brief' else read_json(paths['brief'])
    for name in checks:
        check = report.get('checks', {}).get(name, {})
        require(isinstance(check, dict), f'Invalid check record: {name}')
        excluded = stage == 'site' and name in FEATURES and not plan['features'][name]['enabled']
        require(check.get('status') == ('not_applicable' if excluded else 'pass'), f'Check has not passed: {name}')
        require(isinstance(check.get('detail'), str) and check['detail'].strip(), f'Record actual observation: {name}')
        require(isinstance(check.get('evidence'), list) and check['evidence'] and
                all(isinstance(key, str) and key in paths for key in check['evidence']), f'Link check to artifacts: {name}')
    if stage == 'brief':
        check_brief(plan, state)
    if stage == 'references':
        notes = read_json(paths['reference_notes'])
        for name in ('source', 'observed', 'mapping'):
            require(notes.get(name, '').strip(), f'Reference requires {name}')
        require(image_header(paths['reference_capture'].read_bytes())[0] is not None, 'Reference capture must be an actual image')
    if stage in ('first-screen', 'site'):
        require(paths['entry'].is_relative_to(Path(state['site'])), 'Entry must belong to the release tree')
        receipt(paths['browser_report'], active, 'browser', Path(state['site']))
        check_browser(paths['browser_report'], active, tracked, plan['title'], full=stage == 'site')
    if stage in ('visual', 'site'):
        for name, width in [('desktop', 1440), ('mobile', 390)]:
            key = name + ('_full' if stage == 'site' else '')
            size = png_dimensions(paths[key])
            require(size[0] == width and size[1] >= (900 if width == 1440 else 844), f'Invalid {key} screenshot')
            fresh(paths[key], active)
            captured_file(paths[key], active, Path(state['site']))
    if stage == 'site' and any(plan['features'][name]['enabled'] for name in ('motion', 'transition', 'lighting')):
        require('motion_capture' in paths, 'Observe motion, transition and lighting with timed frame evidence')
        captured_file(paths['motion_capture'], active, Path(state['site']))
        check_motion(paths['motion_capture'], tracked, plan['features'], active)
    if stage == 'performance':
        for profile in ('desktop', 'mobile'):
            receipt(paths[profile + '_report'], active, profile, Path(state['site']))
            check_performance(paths[profile + '_report'], profile, plan, active)
    if stage == 'delivery':
        if 'inline_review' in paths:
            review = read_json(paths['inline_review'])
            require(review.get('status') == 'pass' and review.get('detail', '').strip() and review.get('evidence'),
                    'Inline assets need an actual optimization and visual review')
            for filename in review['evidence']:
                path = (paths['inline_review'].parent / filename).resolve()
                tracked[str(path)] = digest(path)
        root = check_audit(paths['audit_report'], state, paths['package'], active, 'inline_review' in paths)
        require(root == Path(state['site']), 'Primary audit must inspect the configured release tree')
        receipt(paths['audit_report'], active, 'audit', root)
        preview_root = check_audit(paths['preview_audit'], state, paths['package'], active, 'inline_review' in paths)
        require(preview_root != root, 'Preview a separate extracted or copied delivery tree')
        receipt(paths['preview_audit'], active, 'preview-audit', preview_root)
        receipt(paths['package_preview'], active, 'preview', preview_root)
        for name in site_files(preview_root):
            path = preview_root / name
            tracked[str(path)] = digest(path)
        if state['delivery'] == 'html':
            require(paths['package'] == Path(state['site']) / 'index.html', 'HTML delivery must use the audited entry')
        check_browser(paths['package_preview'], active, tracked, plan['title'])
    return plan


def result(state):
    next_stage = next((name for name in NAMES if state['stages'][name]['status'] != 'pass'), None)
    summaries = {name: {key: value for key, value in stage.items()
                        if key in ('status', 'errors', 'reason', 'checked_ns')}
                 for name, stage in state['stages'].items()}
    return {'complete': next_stage is None, 'next_stage': next_stage, 'stages': summaries,
            'active': state.get('active'), 'attempts': len(state['attempts'])}


def execute(args):
    if args.command == 'template':
        artifacts, checks = STAGES[args.stage]
        return {'stage': args.stage, 'status': 'unverified', 'reviewer': '',
                'artifacts': dict.fromkeys(artifacts, ''),
                'checks': {name: {'status': 'unverified', 'detail': '', 'evidence': []} for name in checks}}
    run = Path(args.out if args.command == 'init' else args.run).resolve()
    with locked(run):
        if args.command == 'init':
            require(not (run / 'workflow.json').exists(), 'Workflow already exists; resume it instead of overwriting history')
            site = Path(args.site).resolve()
            require(not run.is_relative_to(site) and not site.is_relative_to(run), 'Keep QA and release trees separate')
            site.mkdir(parents=True, exist_ok=True)
            state = {'schema_version': 1, 'request': args.request, 'site': str(site), 'delivery': args.delivery,
                     'stages': {name: {'status': 'pending'} for name in NAMES}, 'attempts': [], 'active': None}
        else:
            state = read_json(run / 'workflow.json')
            require(state.get('schema_version') == 1, 'Unsupported workflow schema')
            refresh(state)
            if args.command in ('start', 'record'):
                # Persist stale results even if a requested advance is subsequently rejected.
                save(run, state)
                prerequisites(state, args.stage)
            if args.command == 'start':
                invalidate(state, args.stage, 'Checks restarted; downstream results need revalidation')
                state['stages'][args.stage] = {'status': 'checking'}
                state['active'] = {'stage': args.stage, 'started_ns': time.time_ns(),
                                   'site_sha256': site_digest(Path(state['site']))}
            if args.command == 'record':
                active = state.get('active')
                require(active and active['stage'] == args.stage, 'Start this stage before running its checks')
                errors, tracked, plan = [], {}, {}
                try:
                    plan = validate(state, args.stage, Path(args.evidence).resolve(), tracked)
                    if NAMES.index(args.stage) >= 2:
                        require(active['site_sha256'] == site_digest(Path(state['site'])),
                                'Site changed during checks; restart and rerun them')
                except (ValueError, OSError, KeyError, TypeError) as error:
                    errors.append(str(error))
                attempt = {'stage': args.stage, 'status': 'fail' if errors else 'pass',
                           'checked_ns': time.time_ns(), 'evidence': str(Path(args.evidence).resolve()),
                           'errors': errors, 'artifacts': tracked, 'capture_receipts': active.get('receipts', {})}
                # Retain check results even when the agent repairs and overwrites the original report.
                try:
                    submitted = read_json(Path(args.evidence).resolve())
                    attempt['submitted'] = submitted
                    native = {}
                    for name, value in submitted.get('artifacts', {}).items():
                        path = (Path(args.evidence).resolve().parent / value).resolve()
                        if path.suffix == '.json' and path.is_file():
                            native[name] = read_json(path)
                    attempt['recorded_results'] = native
                except (ValueError, OSError, TypeError, AttributeError):
                    pass
                if NAMES.index(args.stage) >= 2:
                    attempt['site_sha256'] = active['site_sha256']
                if args.stage == 'brief' and not errors:
                    report = read_json(Path(args.evidence).resolve())
                    attempt['brief_path'] = str((Path(args.evidence).resolve().parent / report['artifacts']['brief']).resolve())
                state['attempts'].append(attempt)
                state['stages'][args.stage] = dict(attempt)
                state['active'] = None
            if args.command == 'check':
                checked = run_check(state, run, args)
        save(run, state)
        output = result(state)
        if args.command == 'record':
            output['errors'] = state['stages'][args.stage]['errors']
        if args.command == 'check':
            output['check'] = checked
        return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    init = commands.add_parser('init')
    init.add_argument('--site', required=True)
    init.add_argument('--out', required=True)
    init.add_argument('--request', required=True)
    init.add_argument('--delivery', choices=['archive', 'html'], default='archive')
    template = commands.add_parser('template')
    template.add_argument('--stage', choices=NAMES, required=True)
    check = commands.add_parser('check')
    check.add_argument('--run', required=True)
    check.add_argument('--tool', choices=['browser', 'mobile', 'desktop', 'audit', 'preview-audit', 'preview'], required=True)
    for name in ('preview-root', 'package', 'image-log', 'archive-prefix', 'primary', 'primary-target', 'motion-plan', 'playwright-module', 'channel'):
        check.add_argument('--' + name)
    for name in ('start', 'record', 'status'):
        command = commands.add_parser(name)
        command.add_argument('--run', required=True)
        if name != 'status':
            command.add_argument('--stage', choices=NAMES, required=True)
        if name == 'record':
            command.add_argument('--evidence', required=True)
        if name == 'status':
            command.add_argument('--require-complete', action='store_true')
    args = parser.parse_args()
    try:
        output = execute(args)
        failed = (args.command == 'record' and bool(output['errors'])) or (
            args.command == 'status' and args.require_complete and not output['complete']) or (
            args.command == 'check' and output['check']['tool_exit_code'] != 0)
    except (ValueError, OSError, KeyError, TypeError, subprocess.TimeoutExpired) as error:
        output, failed = {'status': 'fail', 'errors': [str(error)]}, True
    print(json.dumps(output, ensure_ascii=False, indent=2, allow_nan=False))
    return 1 if failed else 0


if __name__ == '__main__':
    raise SystemExit(main())
