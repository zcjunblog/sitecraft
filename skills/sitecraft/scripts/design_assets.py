#!/usr/bin/env python3
"""Search observed design cases and compose an original, editable first-screen seed."""
import argparse
import hashlib
import html
import json
from pathlib import Path
import shutil
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / 'references' / 'design-assets.json'
DIMENSIONS = ('composition', 'typography', 'imagery', 'light_material', 'action', 'mobile')
PROFILES = ('desktop', 'mobile')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read_json(path):
    value = json.loads(Path(path).read_text(encoding='utf-8'))
    require(isinstance(value, dict), f'Expected an object: {path}')
    return value


def sha(path):
    path = Path(path)
    require(path.is_file() and path.stat().st_size, f'Missing or empty file: {path}')
    return hashlib.sha256(path.read_bytes()).hexdigest()


def reference_file(name):
    """Support the source tree and WorkBuddy's flattened references folder."""
    reference_root = (ROOT / 'references').resolve()
    candidate = (reference_root / name).resolve()
    require(candidate.is_relative_to(reference_root), 'Reference path escapes the skill')
    if not candidate.is_file():
        candidate = reference_root / Path(name).name
    sha(candidate)
    return candidate


def choose_case(case_id):
    cases = read_json(CATALOG)['cases']
    found = next((case for case in cases if case['id'] == case_id), None)
    require(found is not None, f'Unknown case: {case_id}')
    return found


def make_plan(case_id, brief):
    case = choose_case(case_id) if case_id != 'custom' else {
        'source': {'url': '', 'date': '', 'kind': 'project-reference', 'scope': '', 'captures': {}},
        'not_borrowing': '',
        'relations': [{'id': key, 'observed': '', 'purpose': '', 'desktop': '', 'mobile': '', 'hook': ''}
                      for key in DIMENSIONS],
    }
    source = dict(case['source'])
    source['captures'] = {profile: str(reference_file(name)) for profile, name in source['captures'].items()}
    return {
        'schema_version': 1, 'status': 'draft', 'request': brief, 'case_id': case_id,
        'source': source,
        'selection': {'fit': '', 'not_borrowing': case['not_borrowing'], 'adaptations': ''},
        'implementation': {'kind': 'project-original' if case_id == 'custom' else 'sitecraft-original-recipe', 'recipe': case_id,
                           'files': [] if case_id == 'custom' else [str(ROOT / 'assets' / 'hero.css')],
                           'parameter_notice': read_json(CATALOG)['parameter_notice']},
        'content': {'brand': '', 'headline': '', 'body': '', 'action': '', 'visual_mode': 'image', 'media': []},
        'relations': [{**item, 'target': {profile: item[profile] for profile in PROFILES}}
                      for item in case['relations']],
    }


def check_plan(path, track=lambda path: None):
    """Structural evidence checks only. A reviewer must inspect the actual images."""
    path = Path(path).resolve()
    plan = read_json(path)
    require(plan.get('schema_version') == 1 and plan.get('status') == 'ready', 'Design plan must be reviewed and ready')
    require(isinstance(plan.get('request'), str) and plan['request'].strip(), 'Keep the original request in the design plan')
    for key in ('fit', 'not_borrowing', 'adaptations'):
        require(isinstance(plan.get('selection', {}).get(key), str) and plan['selection'][key].strip(), f'Declare selection.{key}')
    source = plan.get('source', {})
    for key in ('url', 'date', 'kind', 'scope'):
        require(isinstance(source.get(key), str) and source[key].strip(), f'Declare source.{key}')
    require(source['url'].startswith(('https://', 'http://', 'file://')), 'Declare the actual reference source URL')
    captures = source.get('captures', {})
    require(isinstance(captures, dict) and captures, 'Observe at least one actual reference image')
    from audit_static import image_header
    for profile, value in captures.items():
        require(profile in PROFILES and isinstance(value, str), 'Invalid reference profile')
        image = (path.parent / value).resolve()
        require(image_header(image.read_bytes())[0] is not None, 'Reference must be an actual image')
        track(image)
    if plan.get('case_id') != 'custom':
        case = choose_case(plan.get('case_id'))
        require(all(source.get(key) == case['source'][key] for key in ('url', 'date', 'kind')),
                'Bundled case identity changed; use case_id custom for a newly observed source')
        require(set(captures) == set(case['source']['captures']), 'Do not invent a bundled mobile reference')
        for profile, name in case['source']['captures'].items():
            require(sha(path.parent / captures[profile]) == sha(reference_file(name)), 'Bundled source image must match the observed case')
        track(CATALOG)
    implementation = plan.get('implementation', {})
    require(implementation.get('kind') in ('sitecraft-original-recipe', 'project-original'), 'Declare implementation origin')
    require(implementation.get('files'), 'Link an actual implementation recipe or project design file')
    for name in implementation['files']:
        require(isinstance(name, str), 'Implementation files must be paths')
        actual_file = (path.parent / name).resolve()
        sha(actual_file)
        track(actual_file)
    for key in ('brand', 'headline', 'body', 'action'):
        require(isinstance(plan.get('content', {}).get(key), str) and plan['content'][key].strip(), f'Declare actual content.{key}')
    media = plan['content'].get('media')
    require(isinstance(media, list), 'Declare project media, including none for a deliberate image-free design')
    mode = plan['content'].get('visual_mode', 'image')
    require(mode in ('image', 'typography', 'product-dom'), 'Declare a supported primary visual mode')
    if not media:
        require(mode in ('typography', 'product-dom') and implementation['kind'] == 'project-original',
                'Image-free design needs an actual original typography or product implementation')
        require(isinstance(plan['content'].get('visual_note'), str) and plan['content']['visual_note'].strip(),
                'Explain how actual typography or product content supplies the focal point')
    reference_hashes = {sha(path.parent / value) for value in captures.values()}
    for item in media:
        require(isinstance(item, dict) and all(isinstance(item.get(key), str) and item[key].strip()
                                             for key in ('path', 'alt', 'origin')), 'Media needs path, alt and origin')
        asset = (path.parent / item['path']).resolve()
        require(asset.suffix.lower() in ('.png', '.jpg', '.jpeg', '.webp', '.avif', '.svg'), 'Use a local visual asset')
        require(sha(asset) not in reference_hashes, 'Reference screenshots belong in QA, not in project media')
        track(asset)
    relations = plan.get('relations', [])
    require(isinstance(relations, list) and len(relations) == len(DIMENSIONS), 'Record all six design relationships')
    require(all(isinstance(item, dict) for item in relations), 'Design relationships must be objects')
    require({item.get('id') for item in relations} == set(DIMENSIONS), 'Design relationship IDs must be unique and complete')
    for item in relations:
        for key in ('observed', 'purpose', 'hook'):
            require(isinstance(item.get(key), str) and item[key].strip(), f'Declare relationship {item["id"]}.{key}')
        for profile in PROFILES:
            require(isinstance(item.get('target', {}).get(profile), str) and item['target'][profile].strip(),
                    f'Declare a concrete target for {item["id"]}/{profile}')
    track(path)
    return plan


def compose(args):
    choose_case(args.case)
    out, site = args.out.resolve(), args.site.resolve()
    require(not out.is_relative_to(site) and not site.is_relative_to(out), 'Keep design records outside the release tree')
    require(not out.exists(), f'Existing design record preserved: {out}')
    require(not site.exists() or not any(site.iterdir()), 'Compose only into an empty site; edit existing websites directly')
    require(len(args.media) == len(args.media_alt), 'Provide one --media-alt for every --media')
    mode = getattr(args, 'visual_mode', 'image')
    require(mode in ('image', 'typography', 'product-dom'), 'Unsupported visual mode')
    require(mode != 'image' or args.case == 'collection-led' or len(args.media) == 1, 'This recipe needs one primary visual')
    require(mode == 'image' or not args.media, 'Use either project image media or an explicitly declared original DOM/type focal point')
    plan = make_plan(args.case, args.brief)
    analysis_images = {sha(reference_file(name)) for case in read_json(CATALOG)['cases']
                       for name in case['source']['captures'].values()}
    media = []
    for name, alt in zip(args.media, args.media_alt):
        source = Path(name).resolve()
        require(source.is_file() and source.suffix.lower() in ('.png', '.jpg', '.jpeg', '.webp', '.avif', '.svg'),
                f'Provide a local project visual: {source}')
        require(not source.is_relative_to(ROOT / 'references'), 'Do not publish analysis screenshots as website media')
        require(sha(source) not in analysis_images, 'Do not publish a copied reference screenshot as website media')
        media.append({'path': str(source), 'alt': alt, 'origin': args.media_origin})
    plan['content'] = {'brand': args.brand, 'headline': args.headline, 'body': args.body,
                       'action': args.action, 'visual_mode': mode, 'media': media}
    visual_html = ''
    if mode != 'image':
        require(isinstance(getattr(args, 'visual_note', None), str) and args.visual_note.strip(), 'Explain the original DOM/type focal point')
        plan['content']['visual_note'] = args.visual_note
        plan['implementation']['kind'] = 'project-original'
        if mode == 'product-dom':
            from site_components import render_workspace
            visual_html = '<figure class="hero-media" id="workbench">' + render_workspace(args.workspace) + '</figure>'
    # Keep the record draft: choosing a recipe is not a visual sign-off.
    plan['selection']['fit'] = args.fit
    plan['selection']['adaptations'] = ''
    parts = None
    config = getattr(args, 'sections_data', None)
    base = getattr(args, 'sections_base', Path.cwd())
    if getattr(args, 'sections', None):
        base = args.sections.resolve().parent
        config = read_json(args.sections)
    target = getattr(args, 'primary_target', None)
    if config is not None:
        from site_components import render_parts
        target = target or '#' + config['sections'][0]['id']
        parts = render_parts(config, base, target, args.brand, extra_ids=('workbench',) if mode == 'product-dom' else ())
        for source, _ in parts['assets']:
            require(sha(source) not in analysis_images, 'Analysis screenshots cannot be used as section images')
        plan['implementation']['files'] += [str(ROOT / 'assets' / name) for name in ('site.css', 'site.js')]
    else:
        target = target or '#details'
        require(target == '#details', 'The first-screen seed target is #details; supply sections for other destinations')
    needs_components = parts is not None or mode == 'product-dom'
    if mode == 'product-dom' and parts is None:
        plan['implementation']['files'] += [str(ROOT / 'assets' / name) for name in ('site.css', 'site.js')]
    if needs_components:
        plan['implementation']['files'].append(str(Path(__file__).parent / 'site_components.py'))
    site.mkdir(parents=True, exist_ok=True)
    (site / 'assets').mkdir()
    figures = []
    for index, item in enumerate(media):
        source = Path(item['path'])
        filename = f'visual-{index + 1}{source.suffix.lower()}'
        shutil.copy2(source, site / 'assets' / filename)
        caption = f'<figcaption class="media-caption">{html.escape(item["alt"])}</figcaption>' if args.case == 'collection-led' else ''
        loading = 'fetchpriority="high"' if index == 0 else 'loading="lazy"'
        figures.append(f'<figure class="hero-media"><img src="assets/{filename}" alt="{html.escape(item["alt"], quote=True)}" {loading}>{caption}</figure>')
    picture = '\n'.join(figures)
    if mode == 'product-dom':
        picture = visual_html
    if args.case == 'collection-led':
        picture = '<div class="gallery">' + picture + '</div>'
    text = {key: html.escape(value, quote=True) for key, value in {
        'brand': args.brand, 'headline': args.headline, 'body': args.body,
        'action': args.action, 'target_copy': args.target_copy}.items()}
    headline = text['headline'].replace('\n', '<br>')
    header = parts['header'] if parts else f'<header class="site-header"><a class="wordmark" href="./">{text["brand"]}</a><a class="header-action" href="{html.escape(target)}">{text["action"]}</a></header>'
    sections = parts['sections'] if parts else f'<section id="details" class="details"><h2>{text["action"]}</h2><p>{text["target_copy"]}</p></section>'
    ending = parts['footer'] + parts['dialog'] if parts else ''
    extra_head = '<link rel="stylesheet" href="assets/site.css"><script src="assets/site.js" defer></script>' if needs_components else ''
    document = f'''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{text['brand']}</title><meta name="description" content="{text['body']}"><link rel="stylesheet" href="assets/hero.css">{extra_head}</head>
<body data-recipe="{args.case}">{header}
<main><section class="hero" aria-labelledby="hero-title"><div class="hero-inner"><div class="hero-copy"><h1 id="hero-title">{headline}</h1><p class="intro">{text['body']}</p><a class="primary" data-sitecraft-primary href="{html.escape(target)}">{text['action']}</a></div>{picture}</div></section>
{sections}</main>{ending}</body></html>
'''
    shutil.copy2(ROOT / 'assets' / 'hero.css', site / 'assets' / 'hero.css')
    if needs_components:
        for name in ('site.css', 'site.js'):
            shutil.copy2(ROOT / 'assets' / name, site / 'assets' / name)
    if parts:
        for source, filename in parts['assets']:
            shutil.copy2(source, site / 'assets' / filename)
    (site / 'index.html').write_text(document, encoding='utf-8')
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return {'status': 'draft', 'plan': str(out), 'entry': str(site / 'index.html'),
            'next': 'Observe the reference, adapt concrete targets, then mark the plan ready. No visual review has run.'}


def assemble(spec_path, site, plan):
    spec_path = spec_path.resolve()
    spec = read_json(spec_path)
    for key in ('case', 'request', 'brand', 'headline', 'body', 'action', 'fit'):
        require(isinstance(spec.get(key), str) and spec[key].strip(), f'Site specification requires {key}')
    media = spec.get('media')
    mode = spec.get('visual_mode', 'image')
    require(isinstance(media, list) and (media or mode in ('typography', 'product-dom')), 'Supply project media or an explicit DOM/type focal point')
    require(all(isinstance(item, dict) and all(isinstance(item.get(key), str) and item[key].strip()
                                             for key in ('path', 'alt', 'origin')) for item in media), 'Media requires path, alt and origin')
    args = SimpleNamespace(case=spec['case'], brief=spec['request'], brand=spec['brand'], headline=spec['headline'],
                           body=spec['body'], action=spec['action'], target_copy=spec.get('target_copy', spec['body']),
                           media=[str((spec_path.parent / item['path']).resolve()) for item in media],
                           media_alt=[item['alt'] for item in media], media_origin='; '.join(item['origin'] for item in media),
                           fit=spec['fit'], site=site, out=plan, sections=None, sections_data=spec.get('site'),
                           sections_base=spec_path.parent, primary_target=spec.get('primary_target'), visual_mode=mode,
                           visual_note=spec.get('visual_note'), workspace=spec.get('workspace'))
    return compose(args)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    search = commands.add_parser('search')
    search.add_argument('--query', required=True)
    plan = commands.add_parser('plan')
    plan.add_argument('--case', required=True)
    plan.add_argument('--brief', required=True)
    plan.add_argument('--out', required=True, type=Path)
    seed = commands.add_parser('compose')
    for key in ('case', 'brief', 'brand', 'headline', 'body', 'action', 'target-copy', 'media-origin', 'fit'):
        seed.add_argument('--' + key, required=True)
    seed.add_argument('--media', required=True, action='append')
    seed.add_argument('--media-alt', required=True, action='append')
    seed.add_argument('--site', required=True, type=Path)
    seed.add_argument('--out', required=True, type=Path)
    seed.add_argument('--sections', type=Path)
    seed.add_argument('--primary-target')
    whole = commands.add_parser('assemble')
    whole.add_argument('--spec', type=Path, required=True)
    whole.add_argument('--site', type=Path, required=True)
    whole.add_argument('--plan', type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.command == 'search':
            query = args.query.casefold()
            items = []
            for case in read_json(CATALOG)['cases']:
                matches = [tag for tag in case['tags'] if tag.casefold() in query]
                items.append({'id': case['id'], 'name': case['name'], 'matched_tags': matches,
                              'fit': case['fit'], 'avoid': case['avoid'], 'source': case['source']})
            items.sort(key=lambda item: len(item['matched_tags']), reverse=True)
            output = {'candidates': items, 'has_keyword_match': any(item['matched_tags'] for item in items),
                      'notice': 'Keyword matches suggest candidates, not a design decision. Open the actual captures and inspect fit. If none fits the task and materials, observe another real source and use a custom plan.'}
        elif args.command == 'plan':
            require(not args.out.exists(), f'Existing design record preserved: {args.out}')
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(json.dumps(make_plan(args.case, args.brief), ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
            output = {'status': 'draft', 'plan': str(args.out)}
        elif args.command == 'assemble':
            output = assemble(args.spec, args.site, args.plan)
        else:
            output = compose(args)
    except (ValueError, OSError, KeyError, TypeError) as error:
        parser.exit(1, f'{error}\n')
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
