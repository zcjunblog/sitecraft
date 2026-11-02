#!/usr/bin/env python3
"""Create a skill-only ZIP from this checkout, excluding examples and repository docs."""
from pathlib import Path
import argparse
import hashlib
import zipfile


def package(output):
    source = Path(__file__).resolve().parents[1] / 'skills' / 'sitecraft'
    output = Path(output).expanduser().absolute()
    if output.is_relative_to(source):
        raise SystemExit('Place the ZIP outside skills/sitecraft.')
    output.parent.mkdir(parents=True, exist_ok=True)
    files = sorted(p for p in source.rglob('*') if p.is_file()
                   and '__pycache__' not in p.parts and p.name != '.DS_Store')
    with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in files:
            archive.write(path, 'sitecraft/' + str(path.relative_to(source)))
    with zipfile.ZipFile(output) as archive:
        for path in files:
            assert archive.read('sitecraft/' + str(path.relative_to(source))) == path.read_bytes()
    print(f'{output}: {len(files)} files, {output.stat().st_size} B')
    print('SHA-256: ' + hashlib.sha256(output.read_bytes()).hexdigest())


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', default='outputs/sitecraft.zip')
    package(parser.parse_args().output)
