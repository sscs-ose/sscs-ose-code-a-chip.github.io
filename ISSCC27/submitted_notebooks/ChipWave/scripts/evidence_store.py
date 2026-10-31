"""Lossless local evidence storage: compact, verify, or restore original paths."""
import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import tempfile

ROOT = Path(__file__).resolve().parents[1]
CHUNK = 16 * 1024 * 1024
HEX = re.compile(r'[0-9a-f]{64}')


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as handle:
        for block in iter(lambda: handle.read(CHUNK), b''):
            h.update(block)
    return h.hexdigest()


def safe(root, name):
    parts = PurePosixPath(name)
    if parts.is_absolute() or '..' in parts.parts or not parts.parts or '\\' in name:
        raise ValueError('Unsafe evidence path: ' + name)
    path = root / name
    if not path.resolve().is_relative_to(root.resolve()):
        raise ValueError('Evidence path escapes project: ' + name)
    if any((root / Path(*parts.parts[:i])).is_symlink() for i in range(1, len(parts.parts)+1)):
        raise ValueError('Evidence path contains a symlink: ' + name)
    return path


def load(root):
    index = json.loads(safe(root, 'evidence/index.json').read_text())
    if index['format_version'] != 1:
        raise ValueError('Unsupported evidence index')
    seen = set()
    for item in index['files']:
        name = item['path']
        if not name.startswith('results/') or name in seen or not HEX.fullmatch(item['sha256']):
            raise ValueError('Invalid evidence entry: ' + name)
        safe(root, name); seen.add(name)
        if not isinstance(item['bytes'], int) or item['bytes'] <= 0 or not item['chunks']:
            raise ValueError('Invalid evidence length')
        if any(not HEX.fullmatch(h) for h in item['chunks']):
            raise ValueError('Invalid chunk identifier')
    return index


def chunk(root, key):
    path = safe(root, 'evidence/objects/' + key + '.gz')
    if path.stat().st_size > CHUNK + 65536:
        raise ValueError('Oversized compressed chunk')
    with gzip.open(path, 'rb') as handle:
        raw = handle.read(CHUNK + 1)
    if len(raw) > CHUNK or hashlib.sha256(raw).hexdigest() != key:
        raise ValueError('Corrupt evidence chunk: ' + key)
    return raw


def stream(root, item, output=None):
    h = hashlib.sha256(); size = 0
    for key in item['chunks']:
        raw = chunk(root, key); h.update(raw); size += len(raw)
        if size > item['bytes']:
            raise ValueError('Evidence exceeds recorded length')
        if output is not None:
            output.write(raw)
    if size != item['bytes'] or h.hexdigest() != item['sha256']:
        raise ValueError('Original evidence hash mismatch: ' + item['path'])


def verify(root=ROOT):
    index = load(root)
    for item in index['files']:
        stream(root, item)
    return index


def restore(root=ROOT):
    index = load(root)
    # Check all existing destinations before writing; never overwrite a user's result.
    for item in index['files']:
        path = safe(root, item['path'])
        if path.exists() and (not path.is_file() or path.stat().st_size != item['bytes'] or digest(path) != item['sha256']):
            raise ValueError('Conflicting existing evidence: ' + item['path'])
    for item in index['files']:
        path = safe(root, item['path'])
        if path.exists():
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        name = None
        try:
            with tempfile.NamedTemporaryFile(dir=path.parent, prefix='.restore-', delete=False) as handle:
                name = handle.name
                stream(root, item, handle)
            # Atomic no-clobber publication; each path has its own independent inode.
            os.link(name, path)
        finally:
            if name is not None:
                Path(name).unlink(missing_ok=True)
    return index


def compact(root=ROOT):
    target = root / 'evidence/index.json'
    if target.exists():
        index = verify(root)
    else:
        objects = safe(root, 'evidence/objects'); objects.mkdir(parents=True, exist_ok=True)
        records = []
        # Keep text summaries, interfaces, figures and code directly readable.
        for path in sorted((root / 'results').rglob('*')):
            if not path.is_file() or path.stat().st_size < 1024 * 1024 or path.suffix in {'.json', '.md', '.yaml', '.yml', '.py', '.sv', '.v', '.svg', '.png', '.html'}:
                continue
            safe(root, path.relative_to(root).as_posix())
            h = hashlib.sha256(); keys = []; size = 0
            with path.open('rb') as handle:
                for raw in iter(lambda: handle.read(CHUNK), b''):
                    key = hashlib.sha256(raw).hexdigest(); keys.append(key); h.update(raw); size += len(raw)
                    stored = safe(root, 'evidence/objects/' + key + '.gz')
                    if not stored.exists():
                        with stored.open('xb') as dest:
                            dest.write(gzip.compress(raw, compresslevel=6, mtime=0))
                    if chunk(root, key) != raw:
                        raise ValueError('Stored evidence differs from source')
            records.append(dict(path=path.relative_to(root).as_posix(), bytes=size, sha256=h.hexdigest(), chunks=keys))
        index = dict(format_version=1, encoding='sha256-addressed gzip chunks; original bytes preserved',
                     files=records, original_bytes=sum(x['bytes'] for x in records),
                     stored_bytes=sum(p.stat().st_size for p in objects.iterdir()),
                     unique_chunks=len(list(objects.iterdir())))
        with target.open('x') as handle:
            json.dump(index, handle, indent=2); handle.write('\n')
        verify(root)
    # Check the complete source set before deleting any expanded evidence.
    for item in index['files']:
        path = safe(root, item['path'])
        if path.exists() and (path.stat().st_size != item['bytes'] or digest(path) != item['sha256']):
            raise ValueError('Changed evidence cannot be compacted: ' + item['path'])
    for item in index['files']:
        safe(root, item['path']).unlink(missing_ok=True)
    return index


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('verify', 'restore', 'compact'))
    args = parser.parse_args()
    result = globals()[args.action]()
    print(json.dumps(dict(action=args.action, passed=True, original_files=len(result['files']),
                         original_bytes=result['original_bytes'], stored_bytes=result['stored_bytes']), indent=2))
