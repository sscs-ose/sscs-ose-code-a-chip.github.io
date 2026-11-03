"""Validate and flatten file symlinks in a caller-owned fresh Linux stage.

Run this stdlib-only helper with WSL's /usr/bin/python3, where Linux links can
be inspected without Windows following them. The caller must own the stage
exclusively and pass its narrow runtime directory as ``allowed_root``. This
module never downloads, extracts, executes dependencies, or publishes a stage.
The separate preserve mode records literal links for quarantine only; it never
resolves targets and supplies no runtime qualification.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import stat
import sys
import uuid


SCHEMA = 'hullcirq-linux-link-normalization-v1'


def _absolute(path):
    path = Path(path)
    if '..' in path.parts:
        raise ValueError('Parent traversal is not allowed in operation paths.')
    return Path(os.path.abspath(path))


def _normal_directory(path):
    """Check every ancestor with lstat before using an operation path."""
    for member in [*reversed(path.parents), path]:
        info = member.lstat()
        if not stat.S_ISDIR(info.st_mode) or stat.S_ISLNK(info.st_mode):
            raise ValueError('Operation directory or ancestor is not a normal directory: ' + str(member))


def _paths(root, manifest_path, allowed_root):
    allowed = _absolute(allowed_root)
    if allowed == Path(allowed.anchor):
        raise ValueError('Allowed root must be a narrow, existing runtime directory.')
    _normal_directory(allowed)
    root, manifest = _absolute(root), _absolute(manifest_path)
    for path in (root, manifest):
        if path == allowed or not path.is_relative_to(allowed):
            raise ValueError('Stage and manifest must be strict children of the allowed root.')
    _normal_directory(root)
    _normal_directory(manifest.parent)
    if manifest == root or manifest.is_relative_to(root):
        raise ValueError('The manifest must be outside the stage tree.')
    try:
        info = manifest.lstat()
    except FileNotFoundError:
        pass
    else:
        if not stat.S_ISREG(info.st_mode):
            raise ValueError('Existing manifest must be a normal file; preserved.')
    # The ancestor checks make lexical and resolved containment equivalent.
    if root.resolve(strict=True) != root or allowed.resolve(strict=True) != allowed:
        raise ValueError('Operation roots must not resolve through links.')
    return root, manifest


def _identity(info):
    # Windows lstat/fstat may disagree on deprecated ctime; compare creation time.
    stamp = getattr(info, 'st_birthtime_ns', info.st_ctime_ns) if os.name == 'nt' else info.st_ctime_ns
    return (info.st_dev, info.st_ino, info.st_mode, info.st_size,
            info.st_mtime_ns, stamp)


def _file_record(path, expected=None, output=None):
    """Read only a regular file; optionally copy the exact bytes being hashed."""
    flags = os.O_RDONLY | getattr(os, 'O_BINARY', 0) | getattr(os, 'O_NOFOLLOW', 0)
    descriptor = os.open(path, flags)
    with os.fdopen(descriptor, 'rb') as stream:
        before = os.fstat(stream.fileno())
        if not stat.S_ISREG(before.st_mode):
            raise ValueError('A runtime file is not regular: ' + str(path))
        if expected is not None and _identity(before) != _identity(expected):
            raise ValueError('Runtime file changed during validation: ' + str(path))
        digest, count = hashlib.sha256(), 0
        while block := stream.read(1024 * 1024):
            digest.update(block)
            count += len(block)
            if output is not None:
                output.write(block)
        after = os.fstat(stream.fileno())
        if _identity(before) != _identity(after) or before.st_ctime_ns != after.st_ctime_ns:
            raise ValueError('Runtime file changed while being read: ' + str(path))
    return {'sha256': digest.hexdigest(), 'bytes': count,
            'mode': stat.S_IMODE(before.st_mode)}


def _link_target(path):
    target = os.readlink(path)
    if (not target or PurePosixPath(target).is_absolute()
            or '\\' in target or ':' in target or '\x00' in target):
        raise ValueError('Only relative Linux link targets are accepted: ' + str(path))
    return target


def _resolve_file(root, link):
    """Resolve component by component, rejecting even an escape that reenters."""
    pending = list(link.relative_to(root).parts)
    current = root
    visited = set()
    while pending:
        component = pending.pop(0)
        if component in ('', '.'):
            continue
        if component == '..':
            if current == root:
                raise ValueError('Link traversal escapes the stage: ' + str(link))
            current = current.parent
            continue
        current = current / component
        try:
            info = current.lstat()
        except (FileNotFoundError, NotADirectoryError) as error:
            raise ValueError('Broken runtime link: ' + str(link)) from error
        if stat.S_ISLNK(info.st_mode):
            if current in visited:
                raise ValueError('Cyclic runtime link: ' + str(link))
            visited.add(current)
            target = _link_target(current)
            current = current.parent
            # str.split preserves trailing slash, unlike PurePath.parts.
            target_parts = target.split('/')
            if target.endswith('/'):
                target_parts.append('.')
            pending = target_parts + pending
        elif pending:
            if not stat.S_ISDIR(info.st_mode):
                raise ValueError('Link traverses a non-directory: ' + str(link))
        elif not stat.S_ISREG(info.st_mode):
            raise ValueError('Runtime links must end at regular files: ' + str(link))
    if current == root or not stat.S_ISREG(current.lstat().st_mode):
        raise ValueError('Runtime links must end at regular files: ' + str(link))
    return current


def _walk_entries(root):
    entries, directories = {}, []
    pending = [root]
    while pending:
        directory = pending.pop()
        _normal_directory(directory)
        with os.scandir(directory) as iterator:
            members = sorted(iterator, key=lambda item: item.name)
        for member in members:
            path = Path(member.path)
            name = path.relative_to(root).as_posix()
            if '\\' in name or ':' in name:
                raise ValueError('Non-portable runtime entry name: ' + name)
            info = path.lstat()
            if stat.S_ISDIR(info.st_mode):
                directories.append(name)
                pending.append(path)
            elif stat.S_ISREG(info.st_mode) or stat.S_ISLNK(info.st_mode):
                entries[name] = info
            else:
                raise ValueError('Special runtime entry is not accepted: ' + name)
    return entries, sorted(directories)


def _inspect(root):
    entries, directories = _walk_entries(root)
    files, links = {}, {}
    # Inventory all entries before any copy or replacement is attempted.
    for name in sorted(entries):
        path, info = root / name, entries[name]
        if stat.S_ISLNK(info.st_mode):
            original_target = _link_target(path)
            resolved = _resolve_file(root, path)
            record = _file_record(resolved, resolved.lstat())
            record.update(original_target=original_target,
                          resolved_target=resolved.relative_to(root).as_posix())
            links[name] = dict(record)
        else:
            record = _file_record(path, info)
        files[name] = record
    return {'files': files, 'links': links, 'directories': directories}, entries


def _inspect_preserved(root):
    """Capture original link text for quarantine; never qualify link targets."""
    entries, directories = _walk_entries(root)
    files, links = {}, {}
    for name in sorted(entries):
        path, info = root / name, entries[name]
        if stat.S_ISLNK(info.st_mode):
            original_target = os.readlink(path)
            literal_bytes = os.fsencode(original_target)
            if _identity(path.lstat()) != _identity(info):
                raise ValueError('Runtime link changed while being preserved: ' + name)
            links[name] = {'original_target': original_target,
                           'link_text_sha256': hashlib.sha256(literal_bytes).hexdigest(),
                           'link_text_bytes': len(literal_bytes),
                           'mode': stat.S_IMODE(info.st_mode)}
        else:
            files[name] = _file_record(path, info)
    return {'files': files, 'links': links, 'directories': directories}, entries


def _raw_json(value):
    return (json.dumps(value, ensure_ascii=True, indent=2, sort_keys=True) + '\n').encode('utf-8')


def _existing_manifest(manifest, raw):
    try:
        info = manifest.lstat()
    except FileNotFoundError:
        return False
    if not stat.S_ISREG(info.st_mode) or manifest.read_bytes() != raw:
        raise ValueError('Conflicting existing link manifest preserved: ' + str(manifest))
    return True


def _publish_manifest(manifest, raw):
    """Create a complete record atomically, never replacing any existing name."""
    temporary = manifest.with_name(manifest.name + '.write.' + uuid.uuid4().hex)
    with temporary.open('xb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    try:
        os.link(temporary, manifest)
    except FileExistsError:
        _existing_manifest(manifest, raw)
    temporary.unlink()


def _content_files(records):
    return {name: {key: record[key] for key in ('sha256', 'bytes', 'mode')}
            for name, record in records.items()}


def _operate(root, manifest_path, *, allowed_root, mode):
    root, manifest = _paths(root, manifest_path, allowed_root)
    inspect = _inspect_preserved if mode == 'preserve' else _inspect
    normalize = mode == 'normalize'
    before, entries = inspect(root)
    value = {'schema': SCHEMA, 'mode': mode, 'root': str(root), **before}
    raw = _raw_json(value)
    exists = _existing_manifest(manifest, raw)
    # Catch changes after the complete initial validation, before any writes.
    repeated, repeated_entries = inspect(root)
    if (repeated != before or set(entries) != set(repeated_entries)
            or any(_identity(entries[name]) != _identity(repeated_entries[name]) for name in entries)):
        raise ValueError('Stage changed during validation; no links replaced.')
    if normalize:
        # Persist original literal links before the first replacement. A failed
        # or interrupted new stage must retain its pre-normalization evidence.
        before_manifest = manifest.with_name(manifest.name + '.before.json')
        _paths(root, before_manifest, allowed_root)
        if not _existing_manifest(before_manifest, raw):
            _publish_manifest(before_manifest, raw)
        for name, record in before['links'].items():
            path = root / name
            _normal_directory(path.parent)
            if (_identity(path.lstat()) != _identity(entries[name])
                    or _link_target(path) != record['original_target']):
                raise ValueError('Runtime link changed before normalization: ' + name)
            # Earlier replacements can shorten a chain. Always copy from its
            # original final regular file, rather than reinterpret that chain.
            source = root / record['resolved_target']
            _normal_directory(source.parent)
            temporary = path.with_name(path.name + '.normalize.' + uuid.uuid4().hex)
            with temporary.open('xb') as output:
                copied = _file_record(source, entries[record['resolved_target']], output)
                output.flush()
                os.fsync(output.fileno())
                if hasattr(os, 'fchmod'):
                    os.fchmod(output.fileno(), record['mode'])
                else:
                    os.chmod(temporary, record['mode'])
            if copied != _content_files({name: record})[name]:
                raise ValueError('Runtime target bytes changed; stage retained: ' + name)
            if _identity(path.lstat()) != _identity(entries[name]):
                raise ValueError('Runtime link changed during copying; stage retained: ' + name)
            os.replace(temporary, path)
    after, final_entries = inspect(root)
    metadata_changed = not normalize and (
        set(entries) != set(final_entries)
        or any(_identity(entries[name]) != _identity(final_entries[name]) for name in entries))
    if (after['directories'] != before['directories']
            or _content_files(after['files']) != _content_files(before['files'])
            or (normalize and after['links']) or (not normalize and after != before)
            or metadata_changed):
        raise ValueError('Final stage inventory differs; stage retained without a manifest.')
    _paths(root, manifest, allowed_root)
    if not exists:
        _publish_manifest(manifest, raw)
    return value


def normalize_tree(root, manifest_path, *, allowed_root):
    """Flatten validated links in one new, exclusively owned staging tree."""
    return _operate(root, manifest_path, allowed_root=allowed_root, mode='normalize')


def audit_tree(root, manifest_path, *, allowed_root):
    """Record validated original bytes and links without changing tree entries."""
    return _operate(root, manifest_path, allowed_root=allowed_root, mode='audit')


def preserve_tree(root, manifest_path, *, allowed_root):
    """Quarantine receipt only: preserve literal links without opening targets.

    Broken, cyclic, absolute and escaping targets are recorded as link text.
    This mode supplies no target-content proof and cannot qualify a runtime.
    """
    return _operate(root, manifest_path, allowed_root=allowed_root, mode='preserve')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=('normalize', 'audit', 'preserve'))
    parser.add_argument('root')
    parser.add_argument('manifest')
    parser.add_argument('--allowed-root', required=True)
    args = parser.parse_args(argv)
    try:
        operation = {'normalize': normalize_tree, 'audit': audit_tree,
                     'preserve': preserve_tree}[args.operation]
        value = operation(args.root, args.manifest, allowed_root=args.allowed_root)
    except (OSError, ValueError) as error:
        print(json.dumps({'error': str(error)}, ensure_ascii=True))
        return 1
    print(json.dumps({'schema': SCHEMA, 'mode': value['mode'], 'root': value['root'],
                      'manifest': str(_absolute(args.manifest)),
                      'manifest_sha256': hashlib.sha256(_raw_json(value)).hexdigest(),
                      'file_count': len(value['files']), 'link_count': len(value['links'])},
                     ensure_ascii=True, sort_keys=True))
    return 0


if __name__ == '__main__':
    sys.exit(main())
