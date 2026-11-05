#!/usr/bin/env python3
"""Build reference-to-render comparison boards and validate explicit visual observations.

This validates provenance and completeness, not aesthetic quality or honest eyesight.
"""
import argparse
import base64
import html
import json
import mimetypes
from pathlib import Path

from design_assets import DIMENSIONS, PROFILES, check_plan, read_json, require, sha

LABELS = {'composition': '构图与尺度', 'typography': '中文排字', 'imagery': '主体与裁切',
          'light_material': '光线与材质', 'action': '主要行动', 'mobile': '阅读顺序与手机重排'}


def embed(path):
    mime = mimetypes.guess_type(str(path))[0] or 'application/octet-stream'
    return f'data:{mime};base64,' + base64.b64encode(Path(path).read_bytes()).decode('ascii')


def build_comparison(plan_path, report_path, out):
    plan_path, report_path, out = map(lambda path: Path(path).resolve(), (plan_path, report_path, out))
    require(out.suffix == '.json', 'Comparison output is a JSON manifest; its sibling HTML is the board')
    require(not out.exists() and not out.with_suffix('.html').exists(), 'Preserve earlier comparison evidence; use a new output name')
    inputs = {}

    def track(path):
        inputs[str(Path(path).resolve())] = sha(path)

    plan = check_plan(plan_path, track)
    report = read_json(report_path)
    require(report.get('status') == 'pass', 'Use a passing browser report for the actual first screen')
    profiles = {item['profile']: item for item in report.get('profiles', [])}
    actual, reference, panels = {}, {}, []
    track(report_path)
    for profile in PROFILES:
        require(profile in profiles, f'Missing current screenshot: {profile}')
        current = (report_path.parent / profiles[profile]['screenshot']).resolve()
        track(current)
        actual[profile] = str(current)
        source_name = plan['source']['captures'].get(profile)
        source = (plan_path.parent / source_name).resolve() if source_name else None
        if source:
            track(source)
            reference[profile] = str(source)
            source_panel = f'<img src="{embed(source)}" alt="{profile}参考截图"><p>历史参考截图；保留原始比例，不当作同视口测量。</p>'
        else:
            source_panel = f'<p class="gap">未采集{profile}参考。本栏没有参考图，该视口目标为项目改编，须以实际成品评审。</p>'
        rows = []
        for item in plan['relations']:
            rows.append('<tr>' + ''.join(f'<td>{html.escape(str(value))}</td>' for value in (
                LABELS[item['id']], item['observed'], item['target'][profile], item['hook'])) + '</tr>')
        panels.append(f'''<section><h2>{profile}</h2><div class="pair"><article><h3>参考</h3>{source_panel}</article>
<article><h3>当前实际首屏</h3><img src="{embed(current)}" alt="{profile}当前截图"><p>{html.escape(str(current))}</p></article></div>
<table><thead><tr><th>关系</th><th>实际观察</th><th>本项目目标</th><th>实现位置</th></tr></thead><tbody>{''.join(rows)}</tbody></table></section>''')
    board = out.with_suffix('.html')
    escaped = {key: html.escape(plan['selection'][key]) for key in ('fit', 'not_borrowing', 'adaptations')}
    document = f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>参考到成品 · 视觉对照</title>
<style>body{{margin:0 auto;max-width:1600px;padding:24px;background:#f5f5f5;color:#202020;font:16px/1.7 system-ui,sans-serif}}.pair{{display:grid;grid-template-columns:1fr 1fr;gap:24px;align-items:start}}article{{background:#fff;padding:16px;min-width:0}}img{{display:block;width:100%;height:auto}}p{{overflow-wrap:anywhere}}table{{border-collapse:collapse;width:100%;background:#fff;margin:24px 0 64px}}td,th{{text-align:left;vertical-align:top;border:1px solid #ccc;padding:12px}}td:first-child{{min-width:7em}}.gap{{border:2px dashed #b2691f;padding:24px}}@media(max-width:800px){{.pair{{grid-template-columns:1fr}}table{{display:block;overflow:auto}}}}</style></head><body>
<h1>参考到成品 · 待实际看图评审</h1><p>{html.escape(plan['request'])}</p>
<p>来源：{html.escape(plan['source']['url'])} · {html.escape(plan['source']['date'])}</p><p>{html.escape(plan['source']['scope'])}</p>
<p><strong>选择依据：</strong>{escaped['fit']}</p><p><strong>本项目改编：</strong>{escaped['adaptations']}</p><p><strong>不借用：</strong>{escaped['not_borrowing']}</p>
<p>骨架数值是适配起点。表格与截图只组织证据；逐项评审、修复和复看后才有视觉结论。静态图不证明动态流畅度。</p>{''.join(panels)}</body></html>'''
    out.parent.mkdir(parents=True, exist_ok=True)
    board.write_text(document, encoding='utf-8')
    result = {'schema_version': 1, 'status': 'prepared', 'plan': str(plan_path),
              'browser_report': str(report_path), 'actual': actual, 'references': reference,
              'inputs': inputs, 'board': str(board), 'board_sha256': sha(board)}
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return result


def review_template(comparison):
    return {'schema_version': 1, 'status': 'unverified', 'reviewer': '', 'mode': 'self',
            'comparison_sha256': sha(comparison), 'inspected': False,
            'items': [{'dimension': dimension, 'profile': profile, 'status': 'unverified',
                       'region': '', 'observation': '', 'reference_relation': '', 'decision': ''}
                      for profile in PROFILES for dimension in DIMENSIONS],
            'findings': []}


def validate_comparison(comparison_path, plan_path, actual_paths, track):
    comparison_path, plan_path = Path(comparison_path).resolve(), Path(plan_path).resolve()
    comparison = read_json(comparison_path)
    require(comparison.get('schema_version') == 1 and comparison.get('status') == 'prepared', 'Generate a comparison manifest')
    require(Path(comparison['plan']).resolve() == plan_path, 'Compare against the approved design plan')
    plan = check_plan(plan_path, track)
    expected_references = {profile: str((plan_path.parent / path).resolve())
                           for profile, path in plan['source']['captures'].items()}
    require(comparison.get('references') == expected_references, 'Comparison references do not match the design plan')
    inputs = comparison.get('inputs', {})
    require(isinstance(inputs, dict) and inputs, 'Comparison must bind its source files')
    for name, expected in inputs.items():
        path = Path(name)
        require(sha(path) == expected, f'Comparison input changed; regenerate board: {path.name}')
        track(path)
    for profile in PROFILES:
        current = Path(actual_paths[profile]).resolve()
        require(comparison.get('actual', {}).get(profile) == str(current), 'Comparison must show the captured current screenshots')
        require(inputs.get(str(current)) == sha(current), 'Current screenshot missing from comparison provenance')
    for path in (plan_path, *map(Path, expected_references.values())):
        require(inputs.get(str(path)) == sha(path), 'Source missing from comparison provenance')
    board = Path(comparison['board'])
    require(sha(board) == comparison.get('board_sha256'), 'Comparison board changed after generation')
    track(board)
    track(comparison_path)
    return comparison


def validate_review(review_path, comparison_path, actual_paths, track, previous_findings=()):
    review = read_json(review_path)
    require(review.get('schema_version') == 1 and review.get('status') == 'pass', 'Visual review has not passed')
    require(review.get('inspected') is True, 'Open the reference and both current screenshots before review')
    require(isinstance(review.get('reviewer'), str) and review['reviewer'].strip(), 'Identify the visual reviewer')
    require(review.get('mode') in ('self', 'independent'), 'Declare self or independent visual review')
    require(review.get('comparison_sha256') == sha(comparison_path), 'Review must belong to this comparison; review again after changes')
    items = review.get('items', [])
    require(isinstance(items, list) and len(items) == len(PROFILES) * len(DIMENSIONS), 'Review every relationship in both profiles')
    wanted = {(profile, dimension) for profile in PROFILES for dimension in DIMENSIONS}
    require({(item.get('profile'), item.get('dimension')) for item in items} == wanted, 'Visual observation IDs are missing or duplicated')
    for item in items:
        require(item.get('status') == 'pass', f'Visual issue not resolved: {item.get("dimension")}/{item.get("profile")}')
        for key in ('region', 'observation', 'reference_relation', 'decision'):
            require(isinstance(item.get(key), str) and item[key].strip(), f'Record actual visual {key}')
    findings = review.get('findings')
    require(isinstance(findings, list), 'Declare visual findings, including none if the actual review found none')
    require(all(isinstance(item, dict) and isinstance(item.get('id'), str) and item['id'].strip() for item in findings), 'Each finding needs a stable ID')
    require(len({item['id'] for item in findings}) == len(findings), 'Finding IDs must be unique')
    require(set(previous_findings).issubset({item['id'] for item in findings}), 'Keep previously recorded findings and show their resolution')
    for item in findings:
        require(item.get('status') == 'resolved', f'Unresolved visual finding: {item["id"]}')
        require(item.get('profile') in PROFILES and item.get('dimension') in DIMENSIONS, 'Locate the visual finding')
        for key in ('problem', 'change', 'recheck', 'before', 'after'):
            require(isinstance(item.get(key), str) and item[key].strip(), f'Record repair {key}: {item["id"]}')
        before = (Path(review_path).parent / item['before']).resolve()
        after = (Path(review_path).parent / item['after']).resolve()
        from audit_static import image_header
        require(image_header(before.read_bytes())[0] is not None, 'Repair before evidence must be an actual image')
        require(after == Path(actual_paths[item['profile']]).resolve(), 'Recheck must point to the current captured screenshot')
        require(sha(before) != sha(after), 'Before and after repair evidence must differ')
        track(before)
        track(after)
    track(Path(review_path).resolve())
    return review


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    board = commands.add_parser('board')
    board.add_argument('--plan', required=True, type=Path)
    board.add_argument('--browser-report', required=True, type=Path)
    board.add_argument('--out', required=True, type=Path)
    template = commands.add_parser('template')
    template.add_argument('--comparison', required=True, type=Path)
    args = parser.parse_args()
    try:
        if args.command == 'board':
            output = build_comparison(args.plan, args.browser_report, args.out)
        else:
            output = review_template(args.comparison)
    except (ValueError, OSError, KeyError, TypeError) as error:
        parser.exit(1, f'{error}\n')
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
