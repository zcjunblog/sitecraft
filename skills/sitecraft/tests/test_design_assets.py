import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1] / 'scripts'
sys.path.insert(0, str(SCRIPTS))
from design_assets import ROOT, assemble, check_plan, make_plan
from evidence import prepare
from environment import discover
from site_components import validate_sections


class DesignAssetTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name).resolve()
        self.spec = json.loads((ROOT / 'assets/example-spec.json').read_text())
        self.spec['media'][0]['path'] = str(ROOT / 'assets/sample-object.svg')
        self.spec['site']['sections'][0]['items'][0]['image'] = str(ROOT / 'assets/sample-object.svg')

    def tearDown(self):
        self.temp.cleanup()

    def write_spec(self):
        path = self.root / 'spec.json'
        path.write_text(json.dumps(self.spec))
        return path

    def test_full_site_contains_real_sections_local_assets_and_no_unexpanded_fields(self):
        site, plan = self.root / 'site', self.root / 'plan.json'
        result = assemble(self.write_spec(), site, plan)
        document = (site / 'index.html').read_text()
        self.assertEqual(result['status'], 'draft')
        self.assertIn('href="#objects"', document)
        self.assertIn('id="objects"', document)
        self.assertIn('id="contact-dialog"', document)
        self.assertIn('不发送咨询或生成订单', document)
        self.assertNotIn('{{', document)
        self.assertNotIn('https://placehold', document)
        self.assertTrue((site / 'assets/site.js').is_file())
        self.assertTrue((site / 'assets/section-objects-1.svg').is_file())
        self.assertEqual(json.loads(plan.read_text())['status'], 'draft')

    def test_product_dom_site_needs_no_invented_screenshot_or_image(self):
        self.spec = json.loads((ROOT / 'assets/example-workspace-spec.json').read_text())
        site, plan = self.root / 'software', self.root / 'software-plan.json'
        assemble(self.write_spec(), site, plan)
        document = (site / 'index.html').read_text()
        self.assertIn('data-workspace', document)
        self.assertIn('id="workbench"', document)
        self.assertIn('本地演示', document)
        self.assertNotIn('<img', document)
        self.assertTrue((site / 'assets/site.js').is_file())
        data = json.loads(plan.read_text())
        data['status'] = 'ready'
        data['selection']['adaptations'] = '让真实可切换的任务 DOM 承担主体，手机重新编排任务与详情。'
        plan.write_text(json.dumps(data))
        self.assertEqual(check_plan(plan)['content']['visual_mode'], 'product-dom')

    def test_existing_work_is_preserved(self):
        site = self.root / 'site'
        site.mkdir()
        (site / 'index.html').write_text('User work')
        with self.assertRaisesRegex(ValueError, 'empty site'):
            assemble(self.write_spec(), site, self.root / 'plan.json')
        self.assertEqual((site / 'index.html').read_text(), 'User work')

    def test_bundled_source_scope_can_add_actual_observations_without_changing_identity(self):
        plan_path = self.root / 'plan.json'
        assemble(self.write_spec(), self.root / 'site', plan_path)
        plan = json.loads(plan_path.read_text())
        plan['status'] = 'ready'
        plan['selection']['adaptations'] = '沿中央轴呈现当前原创器物，手机动作先于主体。'
        plan['source']['scope'] += ' 本次另记录了标题与主体的实际相对位置。'
        plan_path.write_text(json.dumps(plan))
        self.assertEqual(check_plan(plan_path)['case_id'], 'object-focus')

    def test_missing_destination_rejected_before_site_files_are_written(self):
        self.spec['primary_target'] = '#missing'
        with self.assertRaisesRegex(ValueError, 'Missing section'):
            assemble(self.write_spec(), self.root / 'site', self.root / 'plan.json')
        self.assertFalse((self.root / 'site').exists())

    def test_demo_and_real_contact_boundaries_are_explicit(self):
        self.spec['site']['sections'][-1]['demo'] = False
        with self.assertRaisesRegex(ValueError, 'real contact'):
            validate_sections(self.spec['site'], self.root)
        self.spec['site']['sections'][-1]['methods'] = [{'label': '发送邮件', 'href': 'mailto:hello@example.com'}]
        self.assertIn('contact', validate_sections(self.spec['site'], self.root))

    def test_reference_images_cannot_be_copied_into_published_sections(self):
        self.spec['site']['sections'][0]['items'][0]['image'] = str(ROOT / 'references/benchmarks/apple-desktop.webp')
        with self.assertRaisesRegex(ValueError, 'Analysis screenshots'):
            assemble(self.write_spec(), self.root / 'site', self.root / 'plan.json')

    def test_packaged_flat_reference_paths_remain_usable(self):
        import design_assets
        flat = self.root / 'references'
        flat.mkdir()
        original = ROOT / 'references/benchmarks/apple-desktop.webp'
        shutil.copy2(original, flat / original.name)
        with patch.object(design_assets, 'ROOT', self.root):
            self.assertEqual(design_assets.reference_file('benchmarks/apple-desktop.webp'), flat / original.name)

    def test_all_five_recipes_compose_and_custom_plan_is_not_forced_to_a_recipe(self):
        for case in ('object-focus', 'scene-immersive', 'work-surface', 'collection-led', 'retail-object'):
            with self.subTest(case=case):
                self.spec['case'] = case
                assemble(self.write_spec(), self.root / case, self.root / (case + '.json'))
                self.assertIn('data-recipe="' + case + '"', (self.root / case / 'index.html').read_text())
        plan = make_plan('custom', '用户指定参考')
        self.assertEqual(plan['implementation']['kind'], 'project-original')
        self.assertEqual(plan['source']['captures'], {})


class EvidenceAssemblyTests(unittest.TestCase):
    def test_empty_observations_do_not_become_pass_and_latest_receipt_is_used(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            notes = root / 'notes.json'
            notes.write_text(json.dumps({'reviewer': 'test reviewer', 'checks': {}}))
            old = root / 'old.json'
            latest = root / 'latest.json'
            state = {'site': str(root / 'site'), 'delivery': 'archive', 'active': {
                'stage': 'performance', 'started_ns': 0, 'receipts': {
                    str(old): {'tool': 'desktop', 'root': str(root / 'site')},
                    str(latest): {'tool': 'desktop', 'root': str(root / 'site')}}}}
            latest.write_text('{}')
            result = prepare(state, root, {'performance': (['desktop_report', 'mobile_report'], ['page_identity'])}, notes, [])
            data = json.loads(Path(result['evidence']).read_text())
            self.assertEqual(data['artifacts']['desktop_report'], str(latest))
            self.assertEqual(data['status'], 'unverified')
            self.assertEqual(result['missing_artifacts'], ['mobile_report'])
            self.assertEqual(data['checks']['page_identity']['status'], 'unverified')

    def test_stale_observations_are_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            notes = root / 'notes.json'
            notes.write_text('{}')
            with self.assertRaisesRegex(ValueError, 'fresh observations'):
                prepare({'active': {'stage': 'visual', 'started_ns': notes.stat().st_mtime_ns + 1}}, root, {}, notes, [])

    @patch('environment.shutil.which', return_value=None)
    def test_missing_node_is_unverified_without_installation(self, which):
        with patch('environment.subprocess.run') as run:
            result = discover(Path.cwd())
        self.assertEqual(result['status'], 'unverified')
        run.assert_not_called()


if __name__ == '__main__':
    unittest.main()
