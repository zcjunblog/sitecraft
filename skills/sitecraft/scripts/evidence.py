"""Assemble stage evidence from current receipts and explicitly supplied observations."""
import json
from pathlib import Path
from uuid import uuid4


def prepare(state, run, stage_definitions, observations_path, bindings):
    from design_assets import read_json, require
    active = state.get('active')
    require(active is not None, 'Start the current stage before preparing evidence')
    stage = active['stage']
    observations_path = Path(observations_path).resolve()
    require(observations_path.stat().st_mtime_ns >= active['started_ns'], 'Write fresh observations after starting this stage')
    observed = read_json(observations_path)
    visual = stage == 'visual' and isinstance(observed.get('items'), list)
    if visual:
        groups = {'brand_fit': {'imagery', 'light_material'}, 'hierarchy': {'composition', 'typography', 'action'},
                  'mobile_crop': {'imagery', 'mobile'}, 'reference_transfer': set()}
        checks = {}
        for name, dimensions in groups.items():
            selected = [item for item in observed['items'] if not dimensions or item.get('dimension') in dimensions]
            status = 'pass' if observed.get('status') == 'pass' and observed.get('inspected') is True and selected and all(
                item.get('status') == 'pass' for item in selected) else 'unverified'
            checks[name] = {'status': status, 'detail': '\n'.join(
                f'{item.get("profile", "")}/{item.get("region", "")}: {item.get("observation", "")}' for item in selected)}
        observed = {'reviewer': observed.get('reviewer', ''), 'checks': checks}
    require(isinstance(observed.get('reviewer'), str) and observed['reviewer'].strip(), 'Name the actual reviewer')
    require(isinstance(observed.get('checks'), dict), 'Supply actual named observations')
    artifacts = {}
    for binding in bindings:
        key, separator, value = binding.partition('=')
        require(separator and key and value and key not in artifacts, 'Use unique --artifact name=path bindings')
        artifacts[key] = str(Path(value).resolve())
    artifacts['observation_log'] = str(observations_path)
    if visual:
        artifacts.setdefault('visual_review', str(observations_path))
    # A receipt is created by the native check in the current start/record interval.
    receipts = list(active.get('receipts', {}).items())
    latest = {}
    for path, receipt in receipts:
        if receipt['root'] == state['site'] or receipt['tool'] in ('preview', 'preview-audit'):
            latest[receipt['tool']] = Path(path)
    browser = latest.get('browser')
    if browser:
        native = read_json(browser)
        profiles = {item['profile']: item for item in native.get('profiles', [])}
        artifacts.setdefault('browser_report', str(browser))
        if stage in ('visual', 'site'):
            for profile in ('desktop', 'mobile'):
                key = profile + ('_full' if stage == 'site' else '')
                name = profiles.get(profile, {}).get('screenshot_full' if stage == 'site' else 'screenshot')
                if name:
                    artifacts.setdefault(key, str((browser.parent / name).resolve()))
        motion = browser.parent / 'motion-capture.json'
        if stage == 'site' and motion.is_file():
            artifacts.setdefault('motion_capture', str(motion))
    for tool, name in (('comparison', 'comparison'), ('desktop', 'desktop_report'), ('mobile', 'mobile_report'),
                       ('audit', 'audit_report'), ('preview-audit', 'preview_audit'), ('preview', 'package_preview')):
        if tool in latest:
            artifacts.setdefault(name, str(latest[tool]))
    if stage in ('first-screen', 'site'):
        artifacts.setdefault('entry', str(Path(state['site']) / 'index.html'))
    if stage == 'references' and artifacts.get('design_plan'):
        plan_path = Path(artifacts['design_plan'])
        plan = read_json(plan_path)
        capture = next(iter(plan.get('source', {}).get('captures', {}).values()), None)
        if capture:
            artifacts.setdefault('reference_capture', str((plan_path.parent / capture).resolve()))
        notes = run / 'generated' / (uuid4().hex + '-reference.json')
        notes.parent.mkdir(parents=True, exist_ok=True)
        notes.write_text(json.dumps({'source': plan.get('source', {}).get('url', ''),
                                     'observed': '\n'.join(item.get('observed', '') for item in plan.get('relations', [])),
                                     'mapping': plan.get('selection', {}).get('adaptations', '')},
                                    ensure_ascii=False, indent=2), encoding='utf-8')
        artifacts.setdefault('reference_notes', str(notes))
    if stage == 'delivery' and state['delivery'] == 'html':
        artifacts.setdefault('package', str(Path(state['site']) / 'index.html'))
    names, required = stage_definitions[stage]
    checks = {}
    for name in required:
        item = observed['checks'].get(name, {})
        require(isinstance(item, dict), f'Observation must declare status and detail: {name}')
        # Attach evidence names automatically. Do not invent the observation or its status.
        evidence = item.get('evidence') or (['comparison', 'visual_review'] if name == 'reference_transfer' else list(artifacts))
        checks[name] = {'status': item.get('status', 'unverified'), 'detail': item.get('detail', ''), 'evidence': evidence}
    complete = all(artifacts.get(name) and Path(artifacts[name]).is_file() for name in names) and all(
        item['status'] in ('pass', 'not_applicable') and isinstance(item['detail'], str) and item['detail'].strip()
        for item in checks.values())
    output = {'stage': stage, 'status': 'pass' if complete else 'unverified',
              'reviewer': observed['reviewer'], 'artifacts': artifacts, 'checks': checks}
    path = run / 'generated' / (uuid4().hex + '-' + stage + '-result.json')
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(output, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return {'evidence': str(path), 'status': output['status'],
            'missing_artifacts': [name for name in names if not artifacts.get(name) or not Path(artifacts[name]).is_file()],
            'unverified_checks': [name for name, item in checks.items() if item['status'] not in ('pass', 'not_applicable')],
            'next': 'Record this evidence to run the existing validators. Prepared is not accepted or visually approved.'}
