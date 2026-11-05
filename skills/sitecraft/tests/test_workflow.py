import json
import hashlib
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
import zipfile
import zlib


SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'workflow.py'
sys.path.insert(0, str(SCRIPT.parent))
from design_assets import make_plan
from design_review import build_comparison, review_template
STAGES = ('brief', 'references', 'first-screen', 'visual', 'site', 'performance', 'delivery')


def png(width, height, pixel=b'\xff\xff\xff\xff'):
    def chunk(kind, data):
        return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data))
    return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 6, 0, 0, 0))
            + chunk(b'IDAT', zlib.compress((b'\0' + pixel * width) * height)) + chunk(b'IEND', b''))


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name).resolve()
        self.site = self.root / 'site'
        self.site.mkdir()
        (self.site / 'index.html').write_text('<title>Flowers</title><h1>Flowers</h1>')
        self.run_dir = self.root / 'qa'
        self.motion = False
        self.html_only = False
        self.request = '做一个无动画的花店品牌官网'
        self.cli('init', '--site', self.site, '--out', self.run_dir, '--request', self.request)

    def tearDown(self):
        self.temp.cleanup()

    def cli(self, *args, code=0):
        result = subprocess.run([sys.executable, str(SCRIPT), *map(str, args)], capture_output=True, text=True)
        self.assertEqual(result.returncode, code, result.stdout + result.stderr)
        return json.loads(result.stdout)

    def write(self, name, data):
        path = self.run_dir / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False))
        return path

    def browser(self, name, full=False):
        profiles = []
        for profile, width, height in [('desktop', 1440, 900), ('mobile', 390, 844)] + (
                [('reduced-motion', 390, 844)] if full else []):
            shot = self.run_dir / f'{name}-{profile}.png'
            shot.write_bytes(png(width, height))
            profiles.append({'profile': profile, 'issues': [], 'screenshot': shot.name,
                             'title': 'Flowers',
                             'layout': {'viewport': [width, height]}, 'primary_action': {'status': 'pass'}})
        return self.write(name + '.json', {'status': 'pass', 'profiles': profiles})

    def prepare(self, stage):
        self.cli('start', '--run', self.run_dir, '--stage', stage)
        report = self.cli('template', '--stage', stage)
        report.update(status='pass', reviewer='fixture reviewer')
        artifacts = {}
        for name in report['artifacts']:
            path = self.run_dir / (stage + '-' + name + '.txt')
            path.write_text('Actual fixture artifact for ' + name)
            artifacts[name] = str(path)
        if stage == 'brief':
            artifacts['brief'] = str(self.write('brief.json', {
                'request': self.request, 'audience': 'local shoppers', 'primary_action': 'view flowers',
                'title': 'Flowers', 'content': ['flowers', 'contact'], 'constraints': [],
                'features': {name: {'enabled': name == 'motion' and self.motion, 'reason': 'explicit static fixture', 'source_quote': '无动画'}
                             for name in ('motion', 'transition', 'lighting', 'webgl')},
                'budgets': {'lcp_ms': 2500, 'cls': 0.1, 'transfer_bytes': 1048576}}))
        if stage == 'references':
            artifacts['reference_notes'] = str(self.write('reference.json', {
                'source': 'https://example.com/florist', 'observed': 'Side-lit bouquet beside a quiet headline',
                'mapping': 'Keep one flower as focal point and leave room for the Chinese title'}))
            path = self.run_dir / 'reference.png'
            path.write_bytes(png(600, 400))
            artifacts['reference_capture'] = str(path)
            media = self.root / 'product.png'
            media.write_bytes(png(32, 32, b'\0\0\xff\xff'))
            plan = make_plan('retail-object', self.request)
            plan.update(status='ready', case_id='custom')
            plan['source'] = {'url': 'https://example.com/florist', 'date': '2026-11-05',
                              'kind': 'test-fixture', 'scope': 'Synthetic desktop only; mobile is an adaptation',
                              'captures': {'desktop': str(path)}}
            plan['selection'].update(fit='A single flower introduces the retail choice', adaptations='Use actual Chinese text and a mobile action before media')
            plan['content'] = {'brand': 'Flowers', 'headline': 'Pick flowers', 'body': 'Local flower choices',
                               'action': 'View flowers', 'media': [{'path': str(media), 'alt': 'Fixture product', 'origin': 'Synthetic fixture'}]}
            artifacts['design_plan'] = str(self.write('design-plan.json', plan))
        if stage in ('first-screen', 'site'):
            artifacts['entry'] = str(self.site / 'index.html')
            artifacts['browser_report'] = str(self.browser(stage, full=stage == 'site'))
        if stage in ('visual', 'site'):
            for name, width, height in [('desktop', 1440, 900), ('mobile', 390, 844)]:
                key = name + ('_full' if stage == 'site' else '')
                path = self.run_dir / f'{stage}-{key}.png'
                path.write_bytes(png(width, height))
                artifacts[key] = str(path)
        if stage == 'visual':
            browser = self.browser('visual')
            artifacts['browser_report'] = str(browser)
            comparison = self.run_dir / 'comparison.json'
            if comparison.exists():
                comparison.unlink()
                comparison.with_suffix('.html').unlink()
            build_comparison(self.run_dir / 'design-plan.json', browser, comparison)
            artifacts['comparison'] = str(comparison)
            artifacts['visual_review'] = str(self.visual_observations(comparison))
        if stage == 'performance':
            for profile in ('mobile', 'desktop'):
                sample = {'cache_mode': 'cold', 'title': 'Flowers',
                          'metrics': {'lcp_observed_ms': 300, 'cls_observed': 0},
                          'transferred_bytes': 2000, 'transferred_bytes_complete': True,
                          'request_issues': [], 'javascript_errors': [], 'console_errors': []}
                artifacts[profile + '_report'] = str(self.write(profile + '-perf.json', {
                    'status': 'measured', 'environment': {'profile': profile},
                    'samples': [sample, sample, sample, dict(sample, cache_mode='warm')]}))
        if stage == 'delivery':
            path = self.site / 'index.html' if self.html_only else self.run_dir / 'site.zip'
            if not self.html_only:
                with zipfile.ZipFile(path, 'w') as archive:
                    archive.write(self.site / 'index.html', 'index.html')
            artifacts['package'] = str(path)
            archive_args = [] if self.html_only else ['--archive', str(path)]
            result = subprocess.run([sys.executable, str(SCRIPT.parent / 'audit_static.py'), str(self.site),
                                     *archive_args], capture_output=True, text=True)
            artifacts['audit_report'] = str(self.write('audit.json', json.loads(result.stdout)))
            extracted = self.root / 'extracted'
            shutil.copytree(self.site, extracted)
            result = subprocess.run([sys.executable, str(SCRIPT.parent / 'audit_static.py'), str(extracted),
                                     *archive_args], capture_output=True, text=True)
            artifacts['preview_audit'] = str(self.write('preview-audit.json', json.loads(result.stdout)))
            artifacts['package_preview'] = str(self.browser('package'))
        report['artifacts'] = artifacts
        for name, check in report['checks'].items():
            check.update(status='pass', detail='Observed the specific fixture requirement', evidence=[next(iter(artifacts))])
            if stage == 'site' and name in ('motion', 'transition', 'lighting', 'webgl') and not (name == 'motion' and self.motion):
                check.update(status='not_applicable', detail='Explicitly disabled in the brief')
            if name == 'reference_transfer':
                check['evidence'] = ['comparison', 'visual_review']
        self.fixture_receipts(report)
        return self.write(stage + '-result.json', report)

    def visual_observations(self, comparison):
        review = review_template(comparison)
        review.update(status='pass', reviewer='synthetic fixture reviewer', inspected=True)
        for item in review['items']:
            item.update(status='pass', region='Fixture first-screen content region',
                        observation='Fixture text and image occupy the declared reading order',
                        reference_relation='Fixture keeps subject and action adjacent',
                        decision='Retain the fixture layout for gate validation only')
        return self.write('visual-observations.json', review)

    def fixture_receipts(self, report):
        # Synthetic checker outputs exercise gate validation. A separate browser test exercises real capture.
        state = json.loads((self.run_dir / 'workflow.json').read_text())
        receipts = state['active'].setdefault('receipts', {})
        tools = {'browser_report': 'browser', 'mobile_report': 'mobile', 'desktop_report': 'desktop',
                 'audit_report': 'audit', 'preview_audit': 'preview-audit', 'package_preview': 'preview',
                 'comparison': 'comparison'}
        for name, value in report['artifacts'].items():
            path = Path(value)
            files = {str(path): hashlib.sha256(path.read_bytes()).hexdigest()}
            if name in ('browser_report', 'package_preview'):
                for profile in json.loads(path.read_text())['profiles']:
                    shot = path.parent / profile['screenshot']
                    files[str(shot)] = hashlib.sha256(shot.read_bytes()).hexdigest()
            root = self.root / 'extracted' if name in ('preview_audit', 'package_preview') else self.site
            receipts[str(path)] = {'tool': tools.get(name, 'browser'), 'root': str(root), 'files': files}
        (self.run_dir / 'workflow.json').write_text(json.dumps(state))

    def pass_stage(self, stage):
        return self.cli('record', '--run', self.run_dir, '--stage', stage, '--evidence', self.prepare(stage))

    def through(self, last):
        for stage in STAGES[:STAGES.index(last) + 1]:
            self.pass_stage(stage)

    def test_cannot_skip_or_complete_pending_stages(self):
        self.cli('start', '--run', self.run_dir, '--stage', 'site', code=1)
        result = self.cli('status', '--run', self.run_dir, '--require-complete', code=1)
        self.assertFalse(result['complete'])
        self.assertEqual(result['next_stage'], 'brief')

    def test_missing_artifacts_and_unverified_checks_block_retry_keeps_history(self):
        path = self.prepare('brief')
        report = json.loads(path.read_text())
        report['artifacts']['brief'] = 'missing.json'
        path.write_text(json.dumps(report))
        self.cli('record', '--run', self.run_dir, '--stage', 'brief', '--evidence', path, code=1)
        self.pass_stage('brief')
        state = json.loads((self.run_dir / 'workflow.json').read_text())
        self.assertEqual([a['status'] for a in state['attempts']], ['fail', 'pass'])

    def test_unverified_is_not_a_pass_and_cannot_skip_prerequisite(self):
        path = self.prepare('brief')
        report = json.loads(path.read_text())
        report['checks']['requirements']['status'] = 'unverified'
        path.write_text(json.dumps(report))
        self.cli('record', '--run', self.run_dir, '--stage', 'brief', '--evidence', path, code=1)
        self.cli('start', '--run', self.run_dir, '--stage', 'references', code=1)

    def test_source_changes_invalidate_first_screen_and_later_stages(self):
        self.through('visual')
        (self.site / 'index.html').write_text('<title>Changed</title>')
        result = self.cli('status', '--run', self.run_dir)
        self.assertEqual(result['next_stage'], 'first-screen')
        self.cli('start', '--run', self.run_dir, '--stage', 'site', code=1)

    def test_changed_evidence_invalidates_its_stage_and_descendants(self):
        self.through('references')
        (self.run_dir / 'reference.png').write_bytes(png(200, 200))
        self.assertEqual(self.cli('status', '--run', self.run_dir)['next_stage'], 'references')

    def test_old_native_report_cannot_be_reused_after_a_new_start(self):
        self.through('references')
        old_report = self.browser('old')
        path = self.prepare('first-screen')
        report = json.loads(path.read_text())
        report['artifacts']['browser_report'] = str(old_report)
        path.write_text(json.dumps(report))
        result = self.cli('record', '--run', self.run_dir, '--stage', 'first-screen', '--evidence', path, code=1)
        self.assertIn('fresh', ' '.join(result['errors']))

    def test_native_failure_cannot_be_overridden_with_manual_pass(self):
        self.through('references')
        path = self.prepare('first-screen')
        native = self.run_dir / 'first-screen.json'
        report = json.loads(native.read_text())
        report['profiles'][1]['primary_action']['status'] = 'fail'
        native.write_text(json.dumps(report))
        self.fixture_receipts(json.loads(path.read_text()))
        self.cli('record', '--run', self.run_dir, '--stage', 'first-screen', '--evidence', path, code=1)

    def test_performance_measured_does_not_imply_within_budget(self):
        self.through('site')
        path = self.prepare('performance')
        native = self.run_dir / 'mobile-perf.json'
        report = json.loads(native.read_text())
        report['samples'][0]['metrics']['lcp_observed_ms'] = 5000
        native.write_text(json.dumps(report))
        self.fixture_receipts(json.loads(path.read_text()))
        self.cli('record', '--run', self.run_dir, '--stage', 'performance', '--evidence', path, code=1)

    def test_full_flow_only_completes_with_current_package(self):
        self.through('delivery')
        self.assertTrue(self.cli('status', '--run', self.run_dir, '--require-complete')['complete'])
        (self.run_dir / 'site.zip').write_bytes(b'changed package')
        result = self.cli('status', '--run', self.run_dir, '--require-complete', code=1)
        self.assertEqual(result['next_stage'], 'delivery')

    def test_evidence_cannot_claim_an_optional_effect_is_absent_when_enabled(self):
        self.through('visual')
        brief = self.run_dir / 'brief.json'
        plan = json.loads(brief.read_text())
        plan['features']['motion']['enabled'] = True
        brief.write_text(json.dumps(plan))
        self.assertEqual(self.cli('status', '--run', self.run_dir)['next_stage'], 'brief')

    def test_exclusive_writer_does_not_corrupt_existing_state(self):
        before = (self.run_dir / 'workflow.json').read_bytes()
        (self.run_dir / '.workflow.lock').write_text('another writer')
        self.cli('start', '--run', self.run_dir, '--stage', 'brief', code=1)
        self.assertEqual(before, (self.run_dir / 'workflow.json').read_bytes())

    def test_motion_requires_distinct_intermediate_frames_for_both_viewports(self):
        self.motion = True
        self.through('visual')
        path = self.prepare('site')
        self.cli('record', '--run', self.run_dir, '--stage', 'site', '--evidence', path, code=1)
        path = self.prepare('site')
        report = json.loads(path.read_text())
        capture = {'motion': {'trigger': 'Pointer moves over the hero'}}
        for profile in ('desktop', 'mobile'):
            image = self.run_dir / f'unchanged-{profile}.png'
            image.write_bytes(png(1440 if profile == 'desktop' else 390, 900 if profile == 'desktop' else 844))
            capture['motion'][profile] = [{'ms': ms, 'file': image.name} for ms in (0, 100, 200)]
        report['artifacts']['motion_capture'] = str(self.write('motion.json', capture))
        self.fixture_receipts(report)
        path.write_text(json.dumps(report))
        result = self.cli('record', '--run', self.run_dir, '--stage', 'site', '--evidence', path, code=1)
        self.assertIn('distinct', ' '.join(result['errors']))

    def test_changes_during_checks_block_the_result(self):
        self.through('references')
        path = self.prepare('first-screen')
        (self.site / 'index.html').write_text('<title>Changed during review</title>')
        self.cli('record', '--run', self.run_dir, '--stage', 'first-screen', '--evidence', path, code=1)

    def test_delivery_requires_a_separate_extracted_preview_tree(self):
        self.through('performance')
        path = self.prepare('delivery')
        report = json.loads(path.read_text())
        report['artifacts']['preview_audit'] = report['artifacts']['audit_report']
        path.write_text(json.dumps(report))
        self.cli('record', '--run', self.run_dir, '--stage', 'delivery', '--evidence', path, code=1)

    def test_wrong_page_title_and_missing_cold_samples_cannot_pass(self):
        self.through('site')
        path = self.prepare('performance')
        native = self.run_dir / 'mobile-perf.json'
        report = json.loads(native.read_text())
        report['samples'] = report['samples'][:1]
        native.write_text(json.dumps(report))
        self.cli('record', '--run', self.run_dir, '--stage', 'performance', '--evidence', path, code=1)

    def test_offline_html_delivery_can_complete_without_an_archive(self):
        self.html_only = True
        self.run_dir = self.root / 'html-qa'
        self.cli('init', '--site', self.site, '--out', self.run_dir, '--request', self.request, '--delivery', 'html')
        self.through('delivery')
        self.assertTrue(self.cli('status', '--run', self.run_dir, '--require-complete')['complete'])

    def test_malformed_artifact_map_records_a_failure_without_losing_history(self):
        path = self.prepare('brief')
        report = json.loads(path.read_text())
        report['artifacts'] = ['invalid']
        path.write_text(json.dumps(report))
        self.cli('record', '--run', self.run_dir, '--stage', 'brief', '--evidence', path, code=1)
        state = json.loads((self.run_dir / 'workflow.json').read_text())
        self.assertEqual(state['attempts'][-1]['submitted'], report)

    def test_effect_exclusion_requires_a_quote_from_the_original_request(self):
        path = self.prepare('brief')
        plan = json.loads((self.run_dir / 'brief.json').read_text())
        plan['features']['motion']['source_quote'] = 'deadline, tools unavailable'
        (self.run_dir / 'brief.json').write_text(json.dumps(plan))
        result = self.cli('record', '--run', self.run_dir, '--stage', 'brief', '--evidence', path, code=1)
        self.assertIn('source_quote', ' '.join(result['errors']))

    def test_visual_capture_cannot_be_replaced_after_capture(self):
        self.through('first-screen')
        path = self.prepare('visual')
        report = json.loads(path.read_text())
        Path(report['artifacts']['desktop']).write_bytes(png(1440, 900, b'\xff\0\0\xff'))
        self.cli('record', '--run', self.run_dir, '--stage', 'visual', '--evidence', path, code=1)

    def test_reference_plan_must_be_ready_and_bound_to_the_capture(self):
        self.through('brief')
        path = self.prepare('references')
        plan_path = self.run_dir / 'design-plan.json'
        plan = json.loads(plan_path.read_text())
        plan['status'] = 'draft'
        plan_path.write_text(json.dumps(plan))
        result = self.cli('record', '--run', self.run_dir, '--stage', 'references', '--evidence', path, code=1)
        self.assertIn('ready', ' '.join(result['errors']))

    def test_reference_screenshot_cannot_be_used_as_project_media(self):
        self.through('brief')
        path = self.prepare('references')
        plan_path = self.run_dir / 'design-plan.json'
        plan = json.loads(plan_path.read_text())
        plan['content']['media'][0]['path'] = plan['source']['captures']['desktop']
        plan_path.write_text(json.dumps(plan))
        result = self.cli('record', '--run', self.run_dir, '--stage', 'references', '--evidence', path, code=1)
        self.assertIn('screenshots belong in QA', ' '.join(result['errors']))

    def test_visual_comparison_requires_a_native_receipt(self):
        self.through('first-screen')
        path = self.prepare('visual')
        state_path = self.run_dir / 'workflow.json'
        state = json.loads(state_path.read_text())
        comparison = json.loads(path.read_text())['artifacts']['comparison']
        del state['active']['receipts'][comparison]
        state_path.write_text(json.dumps(state))
        result = self.cli('record', '--run', self.run_dir, '--stage', 'visual', '--evidence', path, code=1)
        self.assertIn('fresh comparison', ' '.join(result['errors']))

    def test_visual_observations_must_cover_both_profiles(self):
        self.through('first-screen')
        path = self.prepare('visual')
        review_path = self.run_dir / 'visual-observations.json'
        review = json.loads(review_path.read_text())
        review['items'].pop()
        review_path.write_text(json.dumps(review))
        result = self.cli('record', '--run', self.run_dir, '--stage', 'visual', '--evidence', path, code=1)
        self.assertIn('both profiles', ' '.join(result['errors']))

    def test_unresolved_visual_findings_cannot_be_dropped_on_retry(self):
        self.through('first-screen')
        path = self.prepare('visual')
        review_path = self.run_dir / 'visual-observations.json'
        review = json.loads(review_path.read_text())
        review['findings'] = [{'id': 'mobile-heading', 'status': 'unresolved', 'problem': 'Broken heading'}]
        review_path.write_text(json.dumps(review))
        result = self.cli('record', '--run', self.run_dir, '--stage', 'visual', '--evidence', path, code=1)
        self.assertIn('Unresolved visual finding', ' '.join(result['errors']))
        path = self.prepare('visual')
        result = self.cli('record', '--run', self.run_dir, '--stage', 'visual', '--evidence', path, code=1)
        self.assertIn('previously recorded findings', ' '.join(result['errors']))

    def test_comparison_board_change_blocks_recording(self):
        self.through('first-screen')
        path = self.prepare('visual')
        board = self.run_dir / 'comparison.html'
        board.write_text(board.read_text() + '<p>Changed evidence</p>')
        result = self.cli('record', '--run', self.run_dir, '--stage', 'visual', '--evidence', path, code=1)
        self.assertIn('board changed', ' '.join(result['errors']))

    @unittest.skipUnless(os.environ.get('PLAYWRIGHT_MODULE'), 'Requires an existing Playwright and Chromium')
    def test_real_capture_serves_the_current_site_and_copied_reports_cannot_be_reused(self):
        self.through('references')
        (self.site / 'index.html').write_text('''<!doctype html><meta name="viewport" content="width=device-width,initial-scale=1">
            <title>Flowers</title><h1>Flowers</h1><a id="primary" href="#flowers">Pick flowers</a>
            <section id="flowers" style="margin-top:1200px">A real flower list</section>''')
        path = self.prepare('first-screen')
        state = json.loads((self.run_dir / 'workflow.json').read_text())
        state['active']['receipts'] = {}
        (self.run_dir / 'workflow.json').write_text(json.dumps(state))
        captured = self.cli('check', '--run', self.run_dir, '--tool', 'browser', '--primary', '#primary',
                            '--playwright-module', os.environ['PLAYWRIGHT_MODULE'])
        native = Path(captured['check']['report'])
        report = json.loads(path.read_text())
        report['artifacts']['browser_report'] = str(native)
        path.write_text(json.dumps(report))
        self.cli('record', '--run', self.run_dir, '--stage', 'first-screen', '--evidence', path)
        self.cli('start', '--run', self.run_dir, '--stage', 'first-screen')
        copied = self.run_dir / 'copied'
        shutil.copytree(native.parent, copied)
        report['artifacts']['browser_report'] = str(copied / 'review.json')
        path.write_text(json.dumps(report))
        result = self.cli('record', '--run', self.run_dir, '--stage', 'first-screen', '--evidence', path, code=1)
        self.assertIn('workflow.py check', ' '.join(result['errors']))

    @unittest.skipUnless(os.environ.get('PLAYWRIGHT_MODULE'), 'Requires an existing Playwright and Chromium')
    def test_real_browser_performance_audits_and_extracted_preview_complete_one_revision(self):
        self.through('references')
        (self.site / 'index.html').write_text('''<!doctype html><meta name="viewport" content="width=device-width,initial-scale=1">
            <title>Flowers</title><h1>Flowers</h1><a id="primary" href="#flowers">Pick flowers</a>
            <section id="flowers" style="margin-top:1200px">A real flower list</section>''')
        for stage in STAGES[2:]:
            path = self.prepare(stage)
            report = json.loads(path.read_text())
            state = json.loads((self.run_dir / 'workflow.json').read_text())
            state['active']['receipts'] = {}
            (self.run_dir / 'workflow.json').write_text(json.dumps(state))

            def capture(tool, *extra):
                result = self.cli('check', '--run', self.run_dir, '--tool', tool,
                                  '--playwright-module', os.environ['PLAYWRIGHT_MODULE'], *extra)
                return Path(result['check']['report'])

            if stage in ('first-screen', 'visual', 'site'):
                native = capture('browser', '--primary', '#primary', '--primary-target', '#flowers')
                profiles = {item['profile']: item for item in json.loads(native.read_text())['profiles']}
                if stage != 'visual':
                    report['artifacts']['browser_report'] = str(native)
                if stage != 'first-screen':
                    for profile in ('desktop', 'mobile'):
                        key = profile + ('_full' if stage == 'site' else '')
                        shot = profiles[profile]['screenshot_full' if stage == 'site' else 'screenshot']
                        report['artifacts'][key] = str(native.parent / shot)
                if stage == 'visual':
                    comparison = capture('comparison', '--browser-report', native)
                    report['artifacts']['browser_report'] = str(native)
                    report['artifacts']['comparison'] = str(comparison)
                    report['artifacts']['visual_review'] = str(self.visual_observations(comparison))
            if stage == 'performance':
                for profile in ('desktop', 'mobile'):
                    report['artifacts'][profile + '_report'] = str(capture(profile))
            if stage == 'delivery':
                package = report['artifacts']['package']
                report['artifacts']['audit_report'] = str(capture('audit', '--package', package))
                report['artifacts']['preview_audit'] = str(capture('preview-audit', '--preview-root', self.root / 'extracted', '--package', package))
                report['artifacts']['package_preview'] = str(capture('preview', '--preview-root', self.root / 'extracted',
                                                                  '--primary', '#primary', '--primary-target', '#flowers'))
            if stage == 'visual':
                observations = Path(report['artifacts']['visual_review'])
            else:
                observations = self.write(stage + '-observations.json', {'reviewer': report['reviewer'], 'checks': report['checks']})
            manual = {'site': ['interaction_log'], 'delivery': ['package', 'handoff']}.get(stage, [])
            bindings = [value for name in manual for value in ('--artifact', name + '=' + report['artifacts'][name])]
            prepared = self.cli('prepare', '--run', self.run_dir, '--observations', observations, *bindings)
            self.assertEqual(prepared['prepared']['missing_artifacts'], [])
            self.cli('record', '--run', self.run_dir, '--stage', stage, '--evidence', prepared['prepared']['evidence'])
        self.assertTrue(self.cli('status', '--run', self.run_dir, '--require-complete')['complete'])


if __name__ == '__main__':
    unittest.main()
