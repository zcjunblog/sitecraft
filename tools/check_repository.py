#!/usr/bin/env python3
"""Check distributable paths, links, example resources and deterministic package contents."""
from pathlib import Path
import json
import re
import sys
import urllib.parse
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ('pawly', 'fluff-club', 'jigen-station', 'zhijian-florist')


def main():
    problems = []
    files = [p for p in ROOT.rglob('*') if p.is_file() and not any(
        part in {'.git', 'node_modules', '__pycache__', 'outputs'} for part in p.relative_to(ROOT).parts)]
    for path in files:
        rel = path.relative_to(ROOT)
        if any(part in {'.openai', 'browser-profile', '.git-browser-profile'} for part in rel.parts):
            problems.append(f'Forbidden directory: {rel}')
        if path.name.startswith('.env') and path.name != '.env.example':
            problems.append(f'Environment file: {rel}')
        if path.suffix in {'.md', '.py', '.js', '.mjs', '.css', '.html', '.json', '.yaml', '.yml', '.txt'} or path.name == 'LICENSE':
            text = path.read_text(encoding='utf-8')
            if re.search('/' + r'(?:Users/[^/\s]+/|(?:private/)?var/folders/)', text):
                problems.append(f'Personal absolute path: {rel}')
            if re.search(r'github_pat_[A-Za-z0-9_]{20,}|gh[pousr]_[A-Za-z0-9]{20,}|sk-(?:proj-)?[A-Za-z0-9_-]{24,}|-----BEGIN (?:RSA |OPENSSH )?PRIVATE KEY-----', text):
                problems.append(f'Potential credential: {rel}')
            if path.suffix == '.md':
                links = re.findall(r'\]\(([^)]+)\)', text)
                links += re.findall(r'(?:src|href)="([^"]+)"', text)
                for target in links:
                    target = target.split('#', 1)[0]
                    if not target or urllib.parse.urlparse(target).scheme or target.startswith('//'):
                        continue
                    destination = path.parent / urllib.parse.unquote(target)
                    if not destination.exists():
                        problems.append(f'Broken Markdown reference: {rel} -> {target}')
        if path.suffix == '.svg':
            ET.fromstring(path.read_text())
    for name in EXAMPLES:
        base = ROOT / 'examples' / name
        for required in ('README.md', 'build.mjs', 'package.json', 'package-lock.json', 'source/index.html', 'site/index.html'):
            if not (base / required).is_file():
                problems.append(f'Missing example file: {name}/{required}')
        package = json.loads((base / 'package.json').read_text())
        if not package.get('scripts', {}).get('build'):
            problems.append(f'Missing build command: {name}')
        for html in (base / 'site').rglob('*.html'):
            for target in re.findall(r'(?:src|href|data-model)="([^"]+)"', html.read_text()):
                parsed = urllib.parse.urlparse(target)
                if parsed.scheme or target.startswith(('#', '//')):
                    continue
                target = urllib.parse.unquote(parsed.path)
                if target and not (html.parent / target).exists():
                    problems.append(f'Missing static resource: {name}/{target}')
        # Runtime imports must resolve within the exported static site.
        for js in (base / 'site').rglob('*.js'):
            for target in re.findall(r'(?:from\s*|import\s*\()([\'\"])(\.[^\'\"]+)\1', js.read_text()):
                ref = target[1]
                if not (js.parent / ref).is_file():
                    problems.append(f'Missing runtime import: {name}/{ref}')
    skill = ROOT / 'skills/sitecraft'
    frontmatter = (skill / 'SKILL.md').read_text().split('---', 2)[1]
    if not re.search(r'^name: sitecraft$', frontmatter, re.M):
        problems.append('Skill name must match sitecraft folder')
    cases = json.loads((skill / 'evals/scenarios.json').read_text())['cases']
    if len({case['id'] for case in cases}) != len(cases):
        problems.append('Duplicate maintenance scenario IDs')
    for name in ('pawly', 'fluff-club', 'jigen-station', 'zhijian-florist', 'nav-gs', 'jkhcz'):
        data = (ROOT / 'docs/images' / f'{name}.webp').read_bytes()
        if data[:4] != b'RIFF' or data[8:12] != b'WEBP':
            problems.append(f'Invalid showcase image: {name}')
    if problems:
        print('\n'.join(problems), file=sys.stderr)
        raise SystemExit(1)
    print(f'Checked {len(files)} files, 4 examples, 6 showcase images, {len(cases)} scenario definitions: passed.')
    print('This check does not establish image rights, visual quality, runtime behavior or online performance.')


if __name__ == '__main__':
    main()
