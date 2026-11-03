"""Verify this curated archive without executing models or EDA tools."""
import hashlib
import json
from pathlib import Path, PurePosixPath
import sys


def main():
    root = Path(__file__).resolve().parents[1]
    manifest_path = root / 'submission/package_manifest.json'
    if not manifest_path.is_file():
        raise SystemExit('This verifier requires the assembled submission archive.')
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    seen = set()
    total = 0
    for entry in manifest['files']:
        relative = entry['path']
        logical = PurePosixPath(relative)
        if logical.is_absolute() or '..' in logical.parts or '\\' in relative or ':' in relative:
            raise SystemExit('Unsafe manifest member.')
        if relative.casefold() in seen:
            raise SystemExit('Duplicate manifest member.')
        seen.add(relative.casefold())
        path = root.joinpath(*logical.parts)
        if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(root):
            raise SystemExit('Missing or linked member: ' + relative)
        h = hashlib.sha256()
        count = 0
        with path.open('rb') as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b''):
                h.update(block)
                count += len(block)
        if count != entry['bytes'] or h.hexdigest() != entry['sha256']:
            raise SystemExit('Integrity mismatch: ' + relative)
        total += count
    actual = {p.relative_to(root).as_posix().casefold() for p in root.rglob('*')
              if p.is_file() and '.work' not in p.relative_to(root).parts
              and '__pycache__' not in p.relative_to(root).parts}
    expected = seen | {'submission/package_manifest.json'}
    if actual != expected:
        raise SystemExit('Archive has an unlisted or missing file.')
    team = json.loads((root / 'submission/team.json').read_text(encoding='utf-8'))
    if not team.get('confirmed_by_submitter') or not team.get('authors') or not team.get('team_representative'):
        raise SystemExit('Submitter metadata is not confirmed.')
    print(json.dumps({'integrity':'Passed', 'files':len(seen), 'bytes':total,
                      'team_metadata':'Confirmed', 'model_or_eda_started':False}, indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())
