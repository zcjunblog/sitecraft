#!/usr/bin/env python3
"""Build a marketplace distribution copy of Sitecraft for WorkBuddy or SkillHub.

The source skill stays untouched; the adapted copy and ZIP are written under outputs/.
"""
from pathlib import Path
import argparse
import hashlib
import re
import shutil
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'skills' / 'sitecraft'
SKIP_DIRS = {'tests', 'evals', 'agents', '__pycache__'}
SKIP_NAMES = {'.DS_Store'}
VERSION = '0.1.0'
WORKBUDDY_VERSION = '0.4.0'

BASE_DESCRIPTION = (
    '用几句日常描述直接产出漂亮、有品牌感的静态官网（HTML/CSS/JS），'
    '并负责视觉判断、动效、手机布局与交付检查。'
    '触发词：静态官网、企业官网、静态网页、纯静态、官网、官网设计、3D 网站、3D 首屏、Sitecraft、sitecraft、$sitecraft。'
)
DESCRIPTION_ZH = '不懂技术，也能用几句日常描述，做出漂亮、有品牌感的官网。'
DESCRIPTION_EN = 'Create beautiful brand websites from a few plain-language sentences.'
EXAMPLES_ZH = [
    '用 Sitecraft 做一个宠物洗美门店官网，明亮、干净、有亲和力，让顾客看懂服务并方便联系我。',
    '用 Sitecraft 做一家鲜花零售门店的官网，白色为底，简约、大气、有浪漫感，手机上也要好看。',
    '用 Sitecraft 优化当前静态网页的动画、连续转场、光影和下拉展开状态，并检查手机效果。',
]
EXAMPLES_EN = [
    'Use Sitecraft to build a site for a pet grooming salon that feels bright, clean and welcoming, so customers understand the services and can reach us easily.',
    'Use Sitecraft to build a flower shop site on a white background that feels simple, spacious and romantic, and also looks good on a phone.',
    'Use Sitecraft to refine the animation, continuous transitions, lighting and dropdown states of my current static site, then check it on mobile.',
]
TAGS = ['web-design', 'static-site', 'landing-page', 'brand-website', 'frontend']

FRONTMATTER = {
    'workbuddy': lambda: (
        'name: sitecraft\n'
        'display_name: Sitecraft · 官网设计\n'
        'display_name_zh: Sitecraft · 官网设计\n'
        'display_name_en: Sitecraft\n'
        'description: |\n'
        '  根据简短的业务需求制作或精修静态官网、企业官网、品牌站和落地页。'
        '  适用于官网设计、3D 网站、交互式 3D 首屏、产品模型展示或静态部署包检查。\n'
        'description_zh: |\n'
        f'  {DESCRIPTION_ZH}\n'
        'description_en: |\n'
        f'  {DESCRIPTION_EN}\n'
        'examples_zh:\n' + ''.join(f'  - {line}\n' for line in EXAMPLES_ZH) +
        'examples_en:\n' + ''.join(f'  - {line}\n' for line in EXAMPLES_EN) +
        f'version: {WORKBUDDY_VERSION}\n'
        'author: zcjunblog\n'
        'license: MIT\n'
    ),
    'skillhub': lambda: (
        'name: sitecraft\n'
        'slug: sitecraft\n'
        'displayName: Sitecraft · 官网设计\n'
        f'version: {VERSION}\n'
        f'summary: {DESCRIPTION_ZH}\n'
        f'description: {BASE_DESCRIPTION}\n'
        'tags: [' + ', '.join(TAGS) + ']\n'
        'license: MIT\n'
        'homepage: https://github.com/zcjunblog/sitecraft\n'
    ),
}


def iter_files(root):
    for path in sorted(root.rglob('*')):
        if not path.is_file() or path.name in SKIP_NAMES:
            continue
        if any(part in SKIP_DIRS for part in path.relative_to(root).parts[:-1]):
            continue
        yield path


def adapt_skill_md(text):
    parts = text.split('---\n', 2)
    if len(parts) != 3:
        raise SystemExit('SKILL.md frontmatter not found')
    body = parts[2]
    body = re.sub(r'\n?维护本 Skill 时可用 \[evals/scenarios\.json\]\(evals/scenarios\.json\).*\n', '\n', body)
    return body.lstrip('\n')


RAW_BASE = 'https://raw.githubusercontent.com/zcjunblog/sitecraft/main/skills/sitecraft/references/'


def flatten_references(staging):
    """WorkBuddy only allows root/second-level/file: fold the image folders that
    sit under references/ up one level and repoint the links."""
    references = staging / 'references'
    subdirs = [d for d in references.iterdir() if d.is_dir()]
    for sub in subdirs:
        for item in sub.iterdir():
            if item.is_file():
                item.rename(references / item.name)
        shutil.rmtree(sub)
    for doc in references.glob('*.md'):
        text = doc.read_text(encoding='utf-8')
        updated = text
        for sub in subdirs:
            updated = updated.replace(f']({sub.name}/', '](')
        if updated != text:
            doc.write_text(updated, encoding='utf-8')


def externalize_images(staging):
    """SkillHub only accepts text files: drop the bundled images and point the
    reference docs at the copies published in the repository."""
    images = sorted(staging.rglob('*.webp'))
    references = staging / 'references'
    for doc in staging.rglob('*.md'):
        text = doc.read_text(encoding='utf-8')
        updated = text
        for image in images:
            rel = image.relative_to(references).as_posix()
            updated = updated.replace(f']({rel})', f']({RAW_BASE}{rel})')
        if updated != text:
            doc.write_text(updated, encoding='utf-8')
    for image in images:
        image.unlink()
    return [image.name for image in images]


def check_links(document, text):
    missing = []
    targets = re.findall(r'\]\(([^)#][^)]*)\)', text)
    targets += re.findall(r'@(references/[\w./-]+\.md)\b', text)
    for target in targets:
        if '://' in target or target.startswith('mailto:'):
            continue
        if not (document.parent / target.split('#')[0]).exists():
            missing.append(target)
    return sorted(set(missing))


def build(target, outdir, zipname, stage_only=False):
    staging = outdir / 'sitecraft'
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True)

    if target == 'workbuddy':
        body = (ROOT / 'distribution/workbuddy/SKILL.md').read_text(encoding='utf-8')
    else:
        body = adapt_skill_md((SOURCE / 'SKILL.md').read_text(encoding='utf-8'))
    (staging / 'SKILL.md').write_text(
        f'---\n{FRONTMATTER[target]()}---\n\n{body}', encoding='utf-8')

    # SkillHub rejects extension-less files; keep the license text readable by both hosts.
    license_name = 'LICENSE.md' if target == 'skillhub' else 'LICENSE'
    shutil.copy2(SOURCE / 'LICENSE', staging / license_name)
    for sub in ('references', 'scripts', 'assets'):
        shutil.copytree(SOURCE / sub, staging / sub,
                        ignore=shutil.ignore_patterns(*SKIP_NAMES, '__pycache__'))

    if target == 'workbuddy':
        flatten_references(staging)
    if target == 'skillhub':
        externalize_images(staging)

    missing = check_links(staging / 'SKILL.md', (staging / 'SKILL.md').read_text(encoding='utf-8'))
    for ref in sorted(staging.joinpath('references').rglob('*.md')):
        missing += [f'{ref.name}: {m}' for m in check_links(ref, ref.read_text(encoding='utf-8'))]
    if missing:
        raise SystemExit(f'Broken relative links: {missing}')

    if stage_only:
        print(f'Unpacked validation candidate: {staging}; no submission ZIP created.')
        return staging

    zippath = outdir / zipname
    files = sorted(iter_files(staging))
    with zipfile.ZipFile(zippath, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in files:
            archive.write(path, 'sitecraft/' + str(path.relative_to(staging)))
    with zipfile.ZipFile(zippath) as archive:
        for path in files:
            assert archive.read('sitecraft/' + str(path.relative_to(staging))) == path.read_bytes()

    digest = hashlib.sha256(zippath.read_bytes()).hexdigest()
    (outdir / zipname.replace('.zip', '.sha256')).write_text(f'{digest}  {zipname}\n', encoding='utf-8')
    print(f'{zippath}: {len(files)} files, {zippath.stat().st_size} B')
    print(f'SHA-256: {digest}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('target', choices=sorted(FRONTMATTER))
    parser.add_argument('--stage-only', action='store_true', help='Prepare an unpacked candidate for testing, without a submission ZIP')
    args = parser.parse_args()
    version = WORKBUDDY_VERSION if args.target == 'workbuddy' else VERSION
    outdir = ROOT / 'outputs' / args.target
    if args.target == 'workbuddy':
        outdir /= version
    if args.stage_only:
        outdir /= 'candidate'
    outdir.mkdir(parents=True, exist_ok=True)
    build(args.target, outdir, f'sitecraft-{args.target}-{version}.zip', stage_only=args.stage_only)
