#!/usr/bin/env python3
"""Install this repository's skill; back up an existing installation outside discovery."""
from pathlib import Path
from datetime import datetime, timezone
import argparse
import os
import shutil


def install(target=None):
    source = Path(__file__).resolve().parents[1] / 'skills' / 'sitecraft'
    codex = Path(os.environ.get('CODEX_HOME', str(Path.home() / '.codex'))).expanduser()
    destination = Path(target).expanduser().absolute() if target else codex / 'skills' / 'sitecraft'
    if not (source / 'SKILL.md').is_file():
        raise SystemExit('Cannot find skills/sitecraft/SKILL.md')
    if destination.is_symlink():
        raise SystemExit('Destination is a symlink; choose a regular directory with --target.')
    if destination.resolve().is_relative_to(source):
        raise SystemExit('Destination must be outside the source skill directory.')
    backup = None
    if destination.exists():
        if not destination.is_dir():
            raise SystemExit('Destination exists and is not a directory.')
        backup_root = destination.parent.parent / 'skill-backups'
        backup_root.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        backup = backup_root / f'sitecraft-{stamp}'
        shutil.move(str(destination), str(backup))
    try:
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(source, destination, ignore=shutil.ignore_patterns('__pycache__', '.DS_Store'))
    except Exception:
        if destination.exists():
            shutil.rmtree(destination)
        if backup:
            shutil.move(str(backup), str(destination))
        raise
    print(f'Installed: {destination}')
    if backup:
        print(f'Previous installation backed up: {backup}')
    print('The skill is available on your next Codex turn. Invoke it with $sitecraft.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--target', help='Alternative installation directory')
    install(parser.parse_args().target)
