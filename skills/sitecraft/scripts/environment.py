#!/usr/bin/env python3
"""Bounded, read-only discovery of an existing Node/Playwright/browser installation."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

PROBE = r'''
const fs = require('node:fs');
const {createRequire} = require('node:module');
const path = require('node:path');
const input = JSON.parse(process.argv[1]);
const found = new Map();
for (const root of input.roots) {
  const req = createRequire(path.join(root, 'package.json'));
  for (const name of input.explicit.length ? input.explicit : ['playwright','@playwright/test','playwright-core']) {
    try {
      const entry = req.resolve(name);
      if (found.has(entry)) continue;
      const api = req(entry);
      if (api.chromium) found.set(entry, {module:entry, executable:api.chromium.executablePath()});
    } catch {}
  }
}
process.stdout.write(JSON.stringify([...found.values()].map(item => ({...item, browser_exists:fs.existsSync(item.executable)}))));
'''


def discover(project, module=None, channel=None):
    project = Path(project).expanduser().resolve()
    node = shutil.which('node')
    result = {'status': 'unverified', 'python': sys.executable, 'node': node,
              'playwright_module': None, 'channel': None, 'browser': None,
              'scope': 'Availability only; no browser launched and no dependencies installed', 'issues': []}
    if not node:
        result['issues'].append('Node.js is unavailable; reuse an existing host browser or provide a runtime')
        return result
    try:
        version = subprocess.run([node, '--version'], capture_output=True, text=True, timeout=10, check=True).stdout.strip()
        result['node_version'] = version
        if int(version.lstrip('v').split('.')[0]) < 18:
            result['issues'].append('Browser tools need an existing Node.js 18 or later')
            return result
        # Nearest ancestors plus the skill location. No recursive home-directory scan.
        roots = list(dict.fromkeys([project, *list(project.parents)[:6], Path(__file__).resolve().parents[1], Path.cwd().resolve()]))
        explicit = module or os.environ.get('PLAYWRIGHT_MODULE')
        data = {'roots': [str(path) for path in roots], 'explicit': [str(Path(explicit).expanduser().resolve())] if explicit else []}
        probe = subprocess.run([node, '-e', PROBE, json.dumps(data)], capture_output=True, text=True, timeout=15)
        if probe.returncode:
            result['issues'].append('Existing module probe did not complete; provide --playwright-module explicitly')
            return result
        candidates = json.loads(probe.stdout)
        chrome = Path('/Applications/Google Chrome.app/Contents/MacOS/Google Chrome')
        edge = Path('/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge')
        channels = {'chrome': chrome.is_file() or bool(shutil.which('google-chrome') or shutil.which('google-chrome-stable')),
                    'msedge': edge.is_file() or bool(shutil.which('microsoft-edge'))}
        for item in candidates:
            selected = channel or (None if item['browser_exists'] else next((key for key, available in channels.items() if available), None))
            if selected and not channels.get(selected, False):
                continue
            if not selected and not item['browser_exists']:
                continue
            result.update(status='available', playwright_module=item['module'], channel=selected,
                          browser=str(chrome if selected == 'chrome' else edge) if selected and sys.platform == 'darwin'
                          else selected or item['executable'])
            break
        if result['status'] != 'available':
            result['issues'].append('No existing compatible Playwright/browser pair found. Provide --playwright-module and, if needed, --channel; no installation was attempted.')
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        result['issues'].append(f'Availability probe could not finish: {type(error).__name__}')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, default=Path.cwd())
    parser.add_argument('--playwright-module')
    parser.add_argument('--channel', choices=['chrome', 'msedge'])
    args = parser.parse_args()
    output = discover(args.project, args.playwright_module, args.channel)
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0 if output['status'] == 'available' else 1


if __name__ == '__main__':
    raise SystemExit(main())
