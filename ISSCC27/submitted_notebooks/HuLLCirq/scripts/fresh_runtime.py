"""Pinned first-ever Windows/WSL setup, read-only verification and local launch.

Default verification never writes, downloads, starts a process or imports the
application. Preparation requires explicit download/license switches. Host data
belongs under .work; no restored circuit or private model cache is consulted.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import platform
import re
import shutil
import stat
import subprocess
import sys
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener
import uuid
import zipfile

ROOT = Path(__file__).resolve().parents[1]
MODEL_MANIFEST_SHA = 'dae161e27b0e90dd1856c8bb3209201fd6736d8eb66298e75ed87571486f4364'
PYTHON_SHA = '4acbed6dd1c744b0376e3b1cf57ce906f9dc9e95e68824584c8099a63025a3c3'
OLLAMA_SHA = 'a1d11d46a944f9c7521f5e9a3a5db51cd3365401da627d96c204698fc6914ff9'
IMAGE_SHA = '428df0d6d7ce167de6a31bc46001f1167b7fb1fbc1ed95fba278367a95883147'
IMAGE_BYTES = 1398053408
PDK_REVISION = '8afc8346a57fe1ab7934ba5a6056ea8b43078e71'
SDC_SHA = '34c8f331c366db51a78ed8a0d2a7bbac3b6c1cfe0277a04c6aca9ba4948e7f78'
REGISTRY = 'https://registry.ollama.ai/v2/library/qwen2.5-coder'
LINK_SCHEMA = 'hullcirq-linux-link-normalization-v1'
READY_SCHEMA = 'hullcirq-fresh-host-runtime-v2'
READY_SCHEMA_V3 = 'hullcirq-fresh-host-runtime-v3'
COMPLETE_READY = 'ready-complete-v2.json'
COMPLETE_PROFILES = {'compiler': 'compiler.json', 'synthesizer': 'synthesizer.json',
                     'physical': 'p/physical_runtime-complete-v2.json',
                     'drc': 'd/drc_runtime-complete-v2.json', 'lvs': 'l/lvs_runtime-complete-v2.json'}


def ready_path(folder):
    complete = Path(folder) / COMPLETE_READY
    return complete if complete.exists() else Path(folder) / 'ready.json'


def profile_paths(state):
    if state.get('schema') == READY_SCHEMA_V3:
        if state.get('profile_paths') != COMPLETE_PROFILES:
            raise ValueError('Complete-inventory profile bindings differ.')
        return COMPLETE_PROFILES
    return {'compiler': 'compiler.json', 'synthesizer': 'synthesizer.json',
            'physical': 'p/physical_runtime.json', 'drc': 'd/drc_runtime.json', 'lvs': 'l/lvs_runtime.json'}


def io_path(path):
    """Local extended-length Windows I/O; logical/config paths stay unchanged."""
    value = os.path.abspath(os.fspath(path))
    if os.name == 'nt' and not value.startswith('\\\\?\\'):
        if not re.match(r'^[A-Za-z]:\\', value):
            raise ValueError('Use an ordinary local Windows drive for runtime I/O.')
        return '\\\\?\\' + value
    return value


def plain_info(path):
    """Never follow a Windows reparse point (including a WSL Linux link)."""
    info = os.lstat(io_path(path))
    if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
        raise ValueError('Runtime link/reparse point requires safe preparation; preserved: ' + str(path))
    if not (stat.S_ISREG(info.st_mode) or stat.S_ISDIR(info.st_mode)):
        raise ValueError('Unsupported runtime file kind; preserved: ' + str(path))
    return info


def plain_entries(folder):
    """Inspect before descending; no link or special entry is silently skipped."""
    folder = Path(folder)
    if not stat.S_ISDIR(plain_info(folder).st_mode):
        raise ValueError('Expected a normal runtime directory.')
    pending = [folder]
    while pending:
        parent = pending.pop()
        with os.scandir(io_path(parent)) as stream:
            members = sorted(stream, key=lambda item: item.name)
        for member in members:
            path = parent / member.name
            info = plain_info(path)
            yield path, info
            if stat.S_ISDIR(info.st_mode):
                pending.append(path)


def plain_child(path, parent):
    """Check lexical components before resolve can hide an internal alias."""
    path, parent = Path(path).absolute(), Path(parent).absolute()
    if path == parent or not path.is_relative_to(parent):
        raise ValueError('Expected a strict runtime child path.')
    relative = path.relative_to(parent)
    if any(part in ('.', '..') or ':' in part for part in relative.parts):
        raise ValueError('Invalid runtime path component.')
    plain_info(parent)
    current = parent
    for part in relative.parts:
        current = current / part
        plain_info(current)
    # Every lexical component was checked without following a link. Resolving
    # the leaf again would both hide aliases and reintroduce MAX_PATH failures.
    return path


def sha(path):
    with open(io_path(path), 'rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def load(path):
    def unique(pairs):
        value = {}
        for key, item in pairs:
            if key in value:
                raise ValueError('Duplicate JSON key: ' + key)
            value[key] = item
        return value
    with open(io_path(path), 'r', encoding='utf-8-sig') as stream:
        return json.load(stream, object_pairs_hook=unique)


def raw_json(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode('utf-8')


def pinned(path, expected, size=None):
    path = Path(path)
    info = plain_info(path)
    if (not stat.S_ISREG(info.st_mode) or (size is not None and info.st_size != size)
            or sha(path) != expected):
        raise ValueError('Missing or mismatched pinned dependency; preserved: ' + str(path))
    return path


def inside(path, parent):
    path, parent = Path(path).resolve(), Path(parent).resolve()
    if path == parent or not path.is_relative_to(parent):
        raise ValueError('Expected a child path inside the fixed runtime root.')
    return path


def host_root(root, distribution):
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,63}', distribution):
        raise ValueError('Use a simple explicit WSL distribution name.')
    binding = str(Path(root).resolve()).casefold() + '\n' + distribution
    return Path(root) / '.work' / 'fresh' / hashlib.sha256(binding.encode()).hexdigest()[:12]


def work_child(root, path):
    root = Path(root).resolve()
    work = inside(root / '.work', root)
    return inside(path, work)


def contained_tree(folder):
    folder = Path(folder).resolve()
    if folder.exists():
        for path, _ in plain_entries(folder):
            if not path.is_relative_to(folder):
                raise ValueError('Existing runtime link escapes its fixed cache; preserved.')


class HTTPSOnly(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, message, headers, newurl):
        if urlsplit(newurl).scheme != 'https':
            raise ValueError('Refusing a non-HTTPS dependency redirect.')
        return super().redirect_request(request, fp, code, message, headers, newurl)


def download(url, target, expected, size=None, *, allowed=False, opener=None):
    """Publish only a fully checked unique partial; never overwrite a conflict."""
    target = Path(target)
    if target.is_symlink():
        raise ValueError('A download destination cannot be a symbolic link.')
    if target.exists():
        pinned(target, expected, size)
        return target
    if not allowed:
        raise ValueError('Missing dependency; explicit --prepare --download required: ' + target.name)
    if urlsplit(url).scheme != 'https':
        raise ValueError('Only fixed HTTPS dependency sources are accepted.')
    target.parent.mkdir(parents=True, exist_ok=True)
    partial = target.with_name(target.name + '.download.' + uuid.uuid4().hex)
    request = Request(url, headers={'User-Agent': 'HuLLCirq-pinned-fresh-setup-v1',
                                   'Accept': 'application/vnd.docker.distribution.manifest.v2+json'})
    open_url = opener or build_opener(HTTPSOnly()).open
    with open_url(request, timeout=60) as response, partial.open('xb') as output:
        count = 0
        while block := response.read(4 * 1024 * 1024):
            count += len(block)
            if size is not None and count > size:
                raise ValueError('Dependency exceeded its pinned byte count; partial retained.')
            output.write(block)
        output.flush()
        os.fsync(output.fileno())
    pinned(partial, expected, size)
    # A concurrent preparer cannot replace an already published dependency.
    if target.exists():
        pinned(target, expected, size)
        return target
    # Windows rename refuses an existing destination. Setup is one-process-only.
    partial.rename(target)
    return target


def write_exact(path, value):
    raw = value if isinstance(value, bytes) else raw_json(value)
    path = Path(path)
    if path.exists():
        if path.read_bytes() != raw:
            raise ValueError('Conflicting existing file preserved: ' + str(path))
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_name(path.name + '.write.' + uuid.uuid4().hex)
    with partial.open('xb') as output:
        output.write(raw)
        output.flush()
        os.fsync(output.fileno())
    partial.rename(path)


def model_pin(root):
    pin = load(Path(root) / 'configs/fresh_model_qwen25_coder.json')
    if (pin.get('manifest_sha256') != MODEL_MANIFEST_SHA or pin.get('registry') != REGISTRY
            or pin.get('family') != 'qwen2.5-coder' or pin.get('tag') != '7b'
            or pin.get('license') != 'Apache-2.0'):
        raise ValueError('Use the unchanged public Qwen2.5-Coder pin.')
    return pin


def prepare_model(root, *, allowed=False, accept_license=False, opener=None):
    pin = model_pin(root)
    target = work_child(root, Path(root) / '.work/m2/ollama-models')
    contained_tree(target)
    manifest = target / 'manifests/registry.ollama.ai/library/qwen2.5-coder/7b'
    if allowed and not accept_license:
        raise ValueError('Read the pinned model license; explicit --accept-model-license is required.')
    # The registry supports tag requests, not the tested manifest-digest URL.
    # A moved tag fails its raw hash before any blob URL is followed.
    staged_manifest = work_child(root, Path(root) / '.work/fresh/model-manifest-qwen25-7b.json')
    source = manifest if manifest.exists() else staged_manifest
    if source == staged_manifest:
        download(REGISTRY + '/manifests/7b', source, MODEL_MANIFEST_SHA, pin['manifest_bytes'],
                 allowed=allowed, opener=opener)
    pinned(source, MODEL_MANIFEST_SHA, pin['manifest_bytes'])
    value = load(source)
    records = [value.get('config')] + value.get('layers', [])
    actual = []
    for record in records:
        if (type(record) is not dict or not re.fullmatch(r'sha256:[0-9a-f]{64}', record.get('digest', ''))
                or type(record.get('size')) is not int or record['size'] <= 0):
            raise ValueError('Malformed pinned model blob record.')
        actual.append({'sha256': record['digest'][7:], 'bytes': record['size']})
    if actual != pin['blobs']:
        raise ValueError('Pinned model manifest inventory differs.')
    for record in actual:
        digest = record['sha256']
        download(REGISTRY + '/blobs/sha256:' + digest, target / ('blobs/sha256-' + digest),
                 digest, record['bytes'], allowed=allowed, opener=opener)
    if not manifest.exists():
        if not allowed:
            raise ValueError('Model publication is missing; verification did not write it.')
        write_exact(manifest, source.read_bytes())
    pinned(manifest, MODEL_MANIFEST_SHA)
    return target


def wsl_path(path):
    value = str(Path(path).resolve())
    match = re.fullmatch(r'([A-Za-z]):\\(.*)', value)
    if not match:
        raise ValueError('Use a local Windows drive path with standard WSL automount.')
    return '/mnt/' + match[1].lower() + '/' + match[2].replace('\\', '/')


def run(command, *, cwd, timeout=120):
    result = subprocess.run(command, cwd=cwd, capture_output=True, text=True,
                            encoding='utf-8', errors='replace', timeout=timeout, shell=False)
    if result.returncode:
        raise ValueError('Dependency preparation command failed (exit ' + str(result.returncode)
                         + '): ' + subprocess.list2cmdline([str(part) for part in command])
                         + '\n' + (result.stdout + result.stderr or '(no stdout/stderr)'))
    return result.stdout.strip()


def prerequisites(root, distribution):
    if os.name != 'nt' or platform.machine().lower() not in ('amd64', 'x86_64'):
        raise ValueError('Fresh preparation requires Windows x86-64.')
    base = ['wsl.exe', '-d', distribution, '--exec']
    release = run(base + ['/bin/cat', '/etc/os-release'], cwd=root)
    for pattern in (r'(?m)^ID=ubuntu$', r'(?m)^VERSION_ID="?24\.04"?$', r'(?m)^VERSION_CODENAME=noble$'):
        if not re.search(pattern, release):
            raise ValueError('The pinned packages require WSL2 Ubuntu 24.04 amd64; no installation attempted.')
    if run(base + ['/usr/bin/uname', '-m'], cwd=root) != 'x86_64':
        raise ValueError('Use an amd64 WSL userspace.')
    kernel = run(base + ['/usr/bin/uname', '-r'], cwd=root).lower()
    if 'wsl2' not in kernel:
        raise ValueError('Use WSL2, not WSL1. The installer does not change WSL configuration.')
    run(base + ['/usr/bin/test', '-d', wsl_path(root)], cwd=root)
    # Require only metadata/runtime primitives; no apt install or sudo is run.
    for path in ('/usr/bin/dpkg-deb', '/usr/bin/env', '/bin/chmod'):
        run(base + ['/usr/bin/test', '-x', path], cwd=root)
    run(base + ['/usr/bin/python3', '--version'], cwd=root)
    run(base + ['/usr/bin/test', '-r', '/usr/lib/x86_64-linux-gnu/libfuse.so.2'], cwd=root)


def inventory(folder):
    result = {}
    for path, info in plain_entries(folder):
        if stat.S_ISREG(info.st_mode):
            if not path.is_relative_to(Path(folder)):
                raise ValueError('Runtime member escapes its extraction root.')
            result[path.relative_to(folder).as_posix()] = {'sha256': sha(path), 'bytes': info.st_size}
    if not result:
        raise ValueError('Empty dependency extraction.')
    return result


def native_packages(root):
    pin = load(Path(root) / 'configs/runtime_m2b.json')['synthesizer']
    # The historical -noabc run did not execute this already-recorded package.
    # A complete fresh extraction still needs its relative documentation target.
    abc = pin['additional_package_acquired_but_unused']
    return [{'name': 'iverilog', 'filename': 'iverilog_12.0-2build2_amd64.deb', 'bytes': 2125764,
             'sha256': 'f19394cee05ad526e0eb3873bc6c17a5828f56df17fbe2db40cb66513a2d4667',
             'source': 'https://archive.ubuntu.com/ubuntu/pool/universe/i/iverilog/iverilog_12.0-2build2_amd64.deb'}
            ] + pin['packages'] + [{'name': 'yosys-abc', 'filename': abc['filename'],
                                   'bytes': abc['bytes'], 'sha256': abc['sha256'],
                                   'source': 'https://archive.ubuntu.com/ubuntu/pool/universe/y/yosys/' + abc['filename']}]


def linux_link_operation(root, distribution, stage, manifest, operation):
    """Preparation-only native boundary; verify() never calls this function."""
    command = ['wsl.exe', '-d', distribution, '--exec', '/usr/bin/python3',
               wsl_path(Path(root) / 'scripts/fresh_linux_links.py'), operation,
               wsl_path(stage), wsl_path(manifest), '--allowed-root', wsl_path(Path(root) / '.work')]
    report = json.loads(run(command, cwd=root, timeout=1200))
    value = load(manifest)
    if (value.get('schema') != LINK_SCHEMA or value.get('mode') != operation
            or report.get('manifest_sha256') != sha(manifest)):
        raise ValueError('Linux link manifest binding differs; stage retained.')
    return value


def preserve_incomplete_stages(root, folder, distribution):
    """Recoverable, verified rename of known failed Deb stages only."""
    if not folder.exists():
        return
    stages = sorted(path for path in folder.iterdir()
                    if re.fullmatch(r'(iverilog|yosys)\.extract\.[0-9a-f]{32}', path.name))
    if not (folder / 'ready.json').exists():
        # A crash after rename but before its inventory publication is also
        # incomplete. Preserve that owned component rather than overwrite it.
        stages += [folder / name for name in ('iverilog', 'yosys')
                   if (folder / name).exists() and not (folder / (name + '-files.json')).exists()]
    if not stages:
        return
    archive_root = work_child(root, Path(root) / '.work/fresh-failures' / folder.name)
    archive_root.mkdir(parents=True, exist_ok=True)
    for stage in stages:
        archived_name = stage.name if '.extract.' in stage.name else stage.name + '.uncommitted.' + uuid.uuid4().hex
        destination = inside(archive_root / archived_name, archive_root)
        if destination.exists():
            raise ValueError('Existing failed-stage archive preserved; no overwrite.')
        before_path = archive_root / (archived_name + '-before.json')
        after_path = archive_root / (archived_name + '-after.json')
        before = linux_link_operation(root, distribution, stage, before_path, 'preserve')
        # Both absolute targets have been checked as checkout-local descendants;
        # WSL audited every entry without following an external link.
        stage.rename(destination)
        after = linux_link_operation(root, distribution, destination, after_path, 'preserve')
        if any(before[key] != after[key] for key in ('files', 'links', 'directories')):
            raise ValueError('Failed-stage preservation mismatch; archive retained.')
        print('Preserved incomplete dependency stage: ' + stage.name, flush=True)


def normalization_receipt(root, folder, distribution, name, target, stage, selected, *, publish=True):
    receipts = folder / 'normalizations'
    receipts.mkdir(exist_ok=True)
    native = receipts / (name + '-' + uuid.uuid4().hex + '-native.json')
    value = linux_link_operation(root, distribution, stage, native, 'audit' if stage == target else 'normalize')
    receipt = receipts / (name + '-links-v1.json')
    record = {'schema': LINK_SCHEMA, 'component': name,
              'runtime_relative': target.relative_to(folder).as_posix(),
              'sources': selected, 'native_manifest': native.relative_to(folder).as_posix(),
              'native_manifest_sha256': sha(native), 'links': value['links']}
    relative = receipt.relative_to(folder).as_posix()
    if publish:
        write_exact(receipt, record)
        return relative
    return relative, record


def verify_normalization(folder, relative, component, expected_sources):
    """Pure file verification, including rejection of reintroduced links."""
    receipt_path = plain_child(folder / relative, folder)
    value = load(receipt_path)
    if (value.get('schema') != LINK_SCHEMA or value.get('component') != component
            or value.get('sources') != expected_sources or type(value.get('links')) is not dict):
        raise ValueError('Dependency normalization provenance differs.')
    target = plain_child(folder / value['runtime_relative'], folder)
    if component in ('iverilog', 'yosys') and target != (folder / component).resolve():
        raise ValueError('Normalization component is bound to a different runtime.')
    native = plain_child(folder / value['native_manifest'], folder)
    pinned(native, value['native_manifest_sha256'])
    original = load(native)
    if (original.get('schema') != LINK_SCHEMA or original.get('mode') not in ('audit', 'normalize')
            or original.get('links') != value['links']):
        raise ValueError('Native link provenance differs.')
    for name, record in value['links'].items():
        pure = PurePosixPath(name)
        if pure.is_absolute() or '..' in pure.parts or '\\' in name or ':' in name:
            raise ValueError('Invalid normalized runtime member.')
        member = plain_child(target / name, target)
        pinned(member, record['sha256'], record['bytes'])
    return value


def recover_pdk_inventory(root, distribution):
    """Recover only the proven old Windows-enumeration omission, never tamper.

    Publish new immutable metadata/state alongside the failed originals. All
    original records must still match, and the complete actual PDK must equal
    its captured Linux pre-normalization evidence. No process/network is used.
    """
    root = Path(root).resolve()
    folder = host_root(root, distribution)
    if (folder / COMPLETE_READY).exists():
        return False
    original_ready_path = folder / 'ready.json'
    state = load(original_ready_path)
    if state.get('schema') != READY_SCHEMA:
        return False
    if (state.get('checkout') != str(root) or state.get('distribution') != distribution
            or state.get('runtime_root') != folder.relative_to(root).as_posix()):
        raise ValueError('Cannot recover a different host binding.')
    if type(state.get('files')) is not dict:
        raise ValueError('Missing original runtime inventory.')
    allowed = (folder, root / '.work/m2/ollama-models', root / '.work/runtime')
    for name, record in state['files'].items():
        member = plain_child(root / name, root / '.work')
        if not any(member.is_relative_to(parent) for parent in allowed):
            raise ValueError('Original inventory escapes its runtime roots.')
        pinned(member, record['sha256'], record['bytes'])
    physical = load(plain_child(folder / 'p/physical_runtime.json', folder))
    manifest_path = plain_child(physical['pdk_manifest_path'], folder)
    pinned(manifest_path, physical['pdk_manifest_sha256'])
    manifest = load(manifest_path)
    pdk = plain_child(manifest['root'], folder)
    if (manifest.get('ciel_revision') != PDK_REVISION or physical.get('appimage_sha256') != IMAGE_SHA
            or physical.get('pdk_revision') != PDK_REVISION):
        raise ValueError('Original PDK source binding differs.')
    actual = inventory(pdk)
    if actual == manifest['files']:
        return False
    receipts = state.get('linux_link_normalizations', {})
    receipt = verify_normalization(folder, receipts['pdk'], 'pdk',
                                   {'ciel_revision': PDK_REVISION, 'appimage_sha256': IMAGE_SHA})
    if (folder / receipt['runtime_relative']).resolve() != pdk:
        raise ValueError('Original PDK receipt root differs.')
    native = load(plain_child(folder / receipt['native_manifest'], folder))
    if native.get('root') != wsl_path(pdk):
        raise ValueError('Native PDK snapshot root differs.')
    expected = {name: {'sha256': record['sha256'], 'bytes': record['bytes']}
                for name, record in native['files'].items()}
    if (actual != expected or not set(manifest['files']) < set(actual)
            or any(actual.get(name) != record for name, record in manifest['files'].items())):
        raise ValueError('PDK difference is not a proven enumeration omission; originals preserved.')
    if (folder / 'workspace').exists():
        raise ValueError('Recover the incomplete setup before any public workspace is opened.')
    # Do not bless newly injected files elsewhere in the cache during recovery.
    old_members = {name for name in state['files'] if (root / name).is_relative_to(folder)}
    added_metadata = {folder / COMPLETE_PROFILES[kind] for kind in ('physical', 'drc', 'lvs')}
    added_metadata |= {folder / 'p/pdk-input-manifest-complete-v2.json', folder / 'p/inventory-recovery-v1.json'}
    for member, info in plain_entries(folder):
        if not stat.S_ISREG(info.st_mode) or '.download.' in member.name or '.extract.' in member.as_posix():
            continue
        if member != original_ready_path and member not in added_metadata and member.relative_to(root).as_posix() not in old_members:
            raise ValueError('Unexpected cache member during metadata recovery; preserved.')
    corrected = dict(manifest, files=actual,
                     inventory_method='complete-nonfollowing-windows-extended-path-v2',
                     original_manifest_sha256=sha(manifest_path),
                     native_manifest_sha256=receipt['native_manifest_sha256'])
    corrected_path = folder / 'p/pdk-input-manifest-complete-v2.json'
    write_exact(corrected_path, corrected)
    complete_physical = dict(physical, pdk_manifest_path=str(corrected_path), pdk_manifest_sha256=sha(corrected_path))
    write_exact(folder / COMPLETE_PROFILES['physical'], complete_physical)
    for kind in ('drc', 'lvs'):
        original = load(plain_child(folder / (kind[0] + '/' + kind + '_runtime.json'), folder))
        if original.get('physical_runtime') != physical:
            raise ValueError('Original DRC/LVS physical source differs; preserved.')
        write_exact(folder / COMPLETE_PROFILES[kind], dict(original, physical_runtime=complete_physical))
    recovery = {'schema': 'hullcirq-complete-pdk-inventory-recovery-v1',
                'parent_ready_sha256': sha(original_ready_path), 'parent_manifest_sha256': sha(manifest_path),
                'native_manifest_sha256': receipt['native_manifest_sha256'],
                'old_file_count': len(manifest['files']), 'complete_file_count': len(actual)}
    write_exact(folder / 'p/inventory-recovery-v1.json', recovery)
    files = {name: record for name, record in state['files'].items()
             if not (root / name).is_relative_to(folder)}
    for member, info in plain_entries(folder):
        if stat.S_ISREG(info.st_mode) and member.name != COMPLETE_READY and '.download.' not in member.name and '.extract.' not in member.as_posix():
            files[member.relative_to(root).as_posix()] = {'sha256': sha(member), 'bytes': info.st_size}
    complete = dict(state, schema=READY_SCHEMA_V3, files=files, profile_paths=COMPLETE_PROFILES,
                    recovery_record='p/inventory-recovery-v1.json', parent_ready_sha256=sha(original_ready_path))
    write_exact(folder / COMPLETE_READY, complete)
    print('Preserved original metadata; recovered complete PDK inventory: '
          + str(len(manifest['files'])) + ' -> ' + str(len(actual)), flush=True)
    return True


def check_inventory(folder, records):
    if type(records) is not dict or not records:
        raise ValueError('Empty runtime inventory.')
    for name, record in records.items():
        pure = PurePosixPath(name)
        if pure.is_absolute() or '..' in pure.parts or '\\' in name or ':' in name:
            raise ValueError('Invalid inventory member.')
        path = plain_child(Path(folder) / name, folder)
        pinned(path, record['sha256'], record['bytes'])
    if set(inventory(folder)) != set(records):
        raise ValueError('Runtime file inventory differs; no files removed.')


def extract_zip(archive, target):
    target = Path(target)
    marker = target.with_name(target.name + '-files.json')
    if target.exists():
        check_inventory(target, load(marker))
        return
    stage = target.with_name(target.name + '.extract.' + uuid.uuid4().hex)
    stage.mkdir(parents=True)
    with zipfile.ZipFile(archive) as packed:
        for member in packed.infolist():
            pure = PurePosixPath(member.filename)
            mode = member.external_attr >> 16
            if pure.is_absolute() or '..' in pure.parts or '\\' in member.filename or ':' in member.filename or stat.S_ISLNK(mode):
                raise ValueError('Unsafe archive member; stage preserved.')
            inside(stage / member.filename, stage)
        packed.extractall(stage)
    records = inventory(stage)
    stage.rename(target)
    write_exact(marker, records)


def prepare(root, distribution, *, allow_download=False, accept_license=False):
    root = Path(root).resolve()
    work_child(root, root / '.work/fresh')
    prerequisites(root, distribution)
    folder = host_root(root, distribution)
    inside(folder, root / '.work')
    if not accept_license:
        raise ValueError('Read docs/fresh_install.md and pass --accept-model-license explicitly.')
    preserve_incomplete_stages(root, folder, distribution)
    contained_tree(folder)
    if not folder.exists() and shutil.disk_usage(root).free < 30 * 1024**3:
        raise ValueError('At least 30 GiB free is required before first preparation; no downloads started.')
    pinned(root / '.work/runtime/downloads/python-3.12.10-embed-amd64.zip', PYTHON_SHA)
    folder.mkdir(parents=True, exist_ok=True)
    if ready_path(folder).exists():
        if not (folder / COMPLETE_READY).exists():
            recover_pdk_inventory(root, distribution)
        return verify(root, distribution)
    model_directory = prepare_model(root, allowed=allow_download, accept_license=accept_license)
    archive = download('https://github.com/ollama/ollama/releases/download/v0.32.15/ollama-windows-amd64.zip',
                       folder / 'downloads/ollama-windows-amd64-v0.32.15.zip', OLLAMA_SHA, allowed=allow_download)
    extract_zip(archive, folder / 'ollama')
    executables = list((folder / 'ollama').rglob('ollama.exe'))
    if len(executables) != 1:
        raise ValueError('Expected exactly one pinned Ollama executable.')
    ollama = executables[0]
    # --version inspects only the isolated client; no daemon or inference starts.
    environment = os.environ.copy()
    environment['OLLAMA_HOST'] = '127.0.0.1:11435'
    version = subprocess.run([str(ollama), '--version'], env=environment, cwd=root,
                             capture_output=True, text=True, timeout=30, shell=False)
    versions = re.findall(r'\bversion(?: is|:)?\s+(\d+\.\d+\.\d+)\b', version.stdout + version.stderr)
    if version.returncode or not versions or any(item != '0.32.15' for item in versions):
        raise ValueError('Isolated Ollama client/version endpoint differs; no process stopped.')
    local = {'kind': 'local_ollama', 'version': '0.32.15', 'executable': str(ollama),
             'model': 'qwen2.5-coder:7b', 'model_directory': str(model_directory),
             'endpoint': 'http://127.0.0.1:11435/v1'}
    write_exact(folder / 'local_runtime.json', local)
    packages = native_packages(root)
    for record in packages:
        url = record['source'].replace('http://', 'https://', 1)
        download(url, folder / 'downloads' / record['filename'], record['sha256'], record['bytes'], allowed=allow_download)
    base = ['wsl.exe', '-d', distribution, '--exec']
    normalizations = {}
    for name, selected in (('iverilog', packages[:1]), ('yosys', packages[1:])):
        target = folder / name
        marker = folder / (name + '-files.json')
        if target.exists():
            check_inventory(target, load(marker))
            existing_receipt = folder / 'normalizations' / (name + '-links-v1.json')
            if existing_receipt.exists():
                relative = existing_receipt.relative_to(folder).as_posix()
                verify_normalization(folder, relative, name, selected)
                normalizations[name] = relative
            else:
                # A previous plain extraction is not relabelled as transformed.
                # Capture its zero-link audit without changing original files.
                normalizations[name] = normalization_receipt(root, folder, distribution, name, target, target, selected)
            continue
        stage = folder / (name + '.extract.' + uuid.uuid4().hex)
        stage.mkdir()
        for record in selected:
            run(base + ['/usr/bin/dpkg-deb', '-x', wsl_path(folder / 'downloads' / record['filename']), wsl_path(stage)], cwd=root)
        receipt_relative, receipt_record = normalization_receipt(root, folder, distribution, name, target, stage, selected, publish=False)
        records = inventory(stage)
        stage.rename(target)
        write_exact(marker, records)
        write_exact(folder / receipt_relative, receipt_record)
        normalizations[name] = receipt_relative
    compiler = {'kind': 'wsl', 'distribution': distribution,
                'executable': wsl_path(folder / 'iverilog/usr/bin/iverilog'),
                'base_directory': wsl_path(folder / 'iverilog/usr/lib/x86_64-linux-gnu/ivl'),
                'working_directory': str(folder / 'syntax')}
    synth = {'kind': 'wsl', 'distribution': distribution, 'executable': wsl_path(folder / 'yosys/usr/bin/yosys'),
             'working_directory': str(folder / 'synthesis'),
             'environment': {'LD_LIBRARY_PATH': wsl_path(folder / 'yosys/usr/lib/x86_64-linux-gnu'),
                             'YOSYS_DATDIR': wsl_path(folder / 'yosys/usr/share/yosys')}}
    run(base + [compiler['executable'], '-B', compiler['base_directory'], '-V'], cwd=root)
    reported = run(base + ['/usr/bin/env', *[key + '=' + value for key, value in synth['environment'].items()], synth['executable'], '-V'], cwd=root)
    if reported != 'Yosys 0.33 (git sha1 2584903a060)':
        raise ValueError('Pinned Yosys version mismatch.')
    write_exact(folder / 'compiler.json', compiler)
    write_exact(folder / 'synthesizer.json', synth)
    image = folder / 'p/runtime/librelane-devshell-x86_64.AppImage'
    sdc = folder / 'p/official_base.sdc'
    # Pre-acquire so the unchanged legacy helper cannot silently download when
    # --download is absent. It performs Ciel dependency acquisition only here.
    download('https://github.com/librelane/librelane/releases/download/3.0.16/librelane-devshell-x86_64.AppImage', image,
             IMAGE_SHA, IMAGE_BYTES, allowed=allow_download)
    download('https://raw.githubusercontent.com/librelane/librelane/3.0.16/librelane/scripts/base.sdc', sdc,
             SDC_SHA, allowed=allow_download)
    if not allow_download and not (folder / 'p/physical_runtime.json').is_file():
        raise ValueError('PDK preparation requires explicit --download, even if the AppImage is cached.')
    python = root / '.work/runtime/python-3.12.10-embed-amd64/python.exe'
    for script, arguments in (
        ('prepare_physical_runtime.py', ['--distribution', distribution, '--output', str(folder / 'p'), '--normalize-linux-file-links']),
        ('prepare_drc_runtime.py', ['--physical-config', str(folder / 'p/physical_runtime.json'), '--output', str(folder / 'd')]),
        ('prepare_lvs_runtime.py', ['--physical-config', str(folder / 'p/physical_runtime.json'), '--output', str(folder / 'l'), '--profile', 'full'])):
        if script == 'prepare_physical_runtime.py' and (folder / 'p/physical_runtime.json').is_file():
            # Do not invoke Ciel (which can use the network) without --download
            # merely because a previous preparation stopped before ready.json.
            continue
        print('Preparing fixed dependency profile: ' + script, flush=True)
        # Native dependency acquisition/version checks, never a design job.
        run([str(python), '-B', '-X', 'utf8', str(root / 'scripts' / script), *arguments], cwd=root, timeout=2400)
    pdk_manifest_value = load(folder / 'p/pdk-input-manifest.json')
    pdk_target = inside(pdk_manifest_value['root'], folder)
    pdk_native = folder / 'p/linux-link-provenance.json'
    if not pdk_native.exists():
        # Reused plain PDKs must also have source-bound provenance; no Ciel call.
        linux_link_operation(root, distribution, pdk_target, pdk_native, 'normalize')
    pdk_sources = {'ciel_revision': PDK_REVISION, 'appimage_sha256': IMAGE_SHA}
    pdk_receipt = folder / 'normalizations/pdk-links-v1.json'
    write_exact(pdk_receipt, {'schema': LINK_SCHEMA, 'component': 'pdk',
                             'runtime_relative': pdk_target.relative_to(folder).as_posix(),
                             'sources': pdk_sources, 'native_manifest': pdk_native.relative_to(folder).as_posix(),
                             'native_manifest_sha256': sha(pdk_native), 'links': load(pdk_native)['links']})
    normalizations['pdk'] = pdk_receipt.relative_to(folder).as_posix()
    files = {}
    for path, info in plain_entries(folder):
        if stat.S_ISREG(info.st_mode) and '.download.' not in path.name and '.extract.' not in path.as_posix():
            files[path.relative_to(root).as_posix()] = {'sha256': sha(path), 'bytes': info.st_size}
    # Shared models and isolated Python must also be fully checksum-bound.
    # Do not make an unrelated user's model cache a launch dependency.
    for item in model_pin(root)['blobs']:
        files[(model_directory / ('blobs/sha256-' + item['sha256'])).relative_to(root).as_posix()] = item
    manifest = model_directory / 'manifests/registry.ollama.ai/library/qwen2.5-coder/7b'
    files[manifest.relative_to(root).as_posix()] = {'sha256': MODEL_MANIFEST_SHA, 'bytes': manifest.stat().st_size}
    for name, record in inventory(python.parent).items():
        files[(python.parent / name).relative_to(root).as_posix()] = record
    archive = root / '.work/runtime/downloads/python-3.12.10-embed-amd64.zip'
    files[archive.relative_to(root).as_posix()] = {'sha256': PYTHON_SHA, 'bytes': archive.stat().st_size}
    state = {'schema': READY_SCHEMA, 'checkout': str(root), 'distribution': distribution,
             'prepared_at': datetime.now(timezone.utc).isoformat(), 'runtime_root': folder.relative_to(root).as_posix(),
             'files': files, 'model_inference_requests': 0, 'circuit_EDA_jobs': 0, 'design_store_writes': 0,
             'system_installs': 0, 'network_sharing': False, 'linux_link_normalizations': normalizations}
    write_exact(folder / 'ready.json', state)
    return verify(root, distribution)


def verify(root, distribution):
    """Only stdlib file reads/hashes; no mkdir, imports, requests or subprocess."""
    root = Path(root).resolve()
    work_child(root, root / '.work/fresh')
    folder = host_root(root, distribution)
    state = load(ready_path(folder))
    if (state.get('schema') not in ('hullcirq-fresh-host-runtime-v1', READY_SCHEMA, READY_SCHEMA_V3) or state.get('checkout') != str(root)
            or state.get('distribution') != distribution or state.get('runtime_root') != folder.relative_to(root).as_posix()):
        raise ValueError('Host binding differs. Prepare anew in the current checkout; never reuse moved absolute paths.')
    if type(state.get('files')) is not dict or not state['files']:
        raise ValueError('Missing prepared-runtime inventory.')
    allowed_roots = (folder, root / '.work/m2/ollama-models', root / '.work/runtime')
    for name, record in state['files'].items():
        pure = PurePosixPath(name)
        if pure.is_absolute() or '..' in pure.parts or '\\' in name or ':' in name:
            raise ValueError('Invalid prepared-runtime inventory member.')
        path = plain_child(root / name, root / '.work')
        if not any(path.is_relative_to(parent.resolve()) for parent in allowed_roots):
            raise ValueError('Runtime inventory includes a non-runtime file.')
        pinned(path, record['sha256'], record['bytes'])
    pinned(root / '.work/runtime/downloads/python-3.12.10-embed-amd64.zip', PYTHON_SHA)
    prepare_model(root, allowed=False)
    profiles = profile_paths(state)
    physical = load(folder / profiles['physical'])
    if (physical.get('appimage_sha256') != IMAGE_SHA or physical.get('pdk_revision') != PDK_REVISION
            or physical.get('base_sdc_sha256') != SDC_SHA or physical.get('distribution') != distribution
            or physical.get('appimage_path') != str(folder / 'p/runtime/librelane-devshell-x86_64.AppImage')
            or physical.get('working_directory') != str(folder / 'p/layout')):
        raise ValueError('Fresh physical runtime is not bound to the current fixed cache.')
    pinned(folder / 'p/runtime/librelane-devshell-x86_64.AppImage', IMAGE_SHA, IMAGE_BYTES)
    pinned(folder / 'p/official_base.sdc', SDC_SHA)
    pinned(folder / 'downloads/ollama-windows-amd64-v0.32.15.zip', OLLAMA_SHA)
    for relative in ('compiler.json', 'synthesizer.json', 'local_runtime.json', profiles['physical'], profiles['drc'], profiles['lvs']):
        if (folder / relative).relative_to(root).as_posix() not in state['files']:
            raise ValueError('Required execution profile not inventoried.')
    pdk_manifest = load(inside(physical['pdk_manifest_path'], folder))
    pdk_root = inside(pdk_manifest['root'], folder)
    if pdk_manifest.get('ciel_revision') != PDK_REVISION:
        raise ValueError('Prepared PDK revision differs.')
    check_inventory(pdk_root, pdk_manifest['files'])
    if state['schema'] in (READY_SCHEMA, READY_SCHEMA_V3):
        receipts = state.get('linux_link_normalizations')
        if type(receipts) is not dict or set(receipts) != {'iverilog', 'yosys', 'pdk'}:
            raise ValueError('Missing Linux link normalization provenance.')
        packages = native_packages(root)
        for kind, sources in (('iverilog', packages[:1]), ('yosys', packages[1:]),
                              ('pdk', {'ciel_revision': PDK_REVISION, 'appimage_sha256': IMAGE_SHA})):
            relative = receipts[kind]
            if (folder / relative).relative_to(root).as_posix() not in state['files']:
                raise ValueError('Normalization provenance is not inventoried.')
            receipt = verify_normalization(folder, relative, kind, sources)
            if kind in ('iverilog', 'yosys'):
                check_inventory(folder / kind, load(folder / (kind + '-files.json')))
            elif (folder / receipt['runtime_relative']).resolve() != pdk_root:
                raise ValueError('PDK normalization is bound to a different root.')
    for kind in ('compiler', 'synthesizer'):
        profile = load(folder / (kind + '.json'))
        expected_leaf = 'iverilog' if kind == 'compiler' else 'yosys'
        if (profile.get('kind') != 'wsl' or profile.get('distribution') != distribution
                or profile.get('executable') != wsl_path(folder / expected_leaf / 'usr/bin' / expected_leaf)
                or not Path(profile['working_directory']).resolve().is_relative_to(folder.resolve())):
            raise ValueError('Execution profile points outside its current host runtime.')
    for kind in ('drc', 'lvs'):
        profile = load(folder / profiles[kind])
        if profile.get('physical_runtime') != physical:
            raise ValueError('DRC/LVS runtime does not retain the exact same physical source.')
    local = load(folder / 'local_runtime.json')
    if (local.get('model_directory') != str(root / '.work/m2/ollama-models') or local.get('endpoint') != 'http://127.0.0.1:11435/v1'
            or not inside(local['executable'], folder).is_file()):
        raise ValueError('Use only the pinned GUI-managed loopback model store.')
    return {'status': 'Passed', 'kind': 'read_only_dependency_integrity_not_circuit_verification',
            'files_verified': len(state['files']), 'runtime_root': folder.relative_to(root).as_posix(),
            'model_requests': 0, 'circuit_EDA_jobs': 0, 'design_store_writes': 0, 'subprocesses': 0,
            'downloads': 0, 'writes': 0}


def launch_arguments(root, distribution, port):
    if type(port) is not int or not 1 <= port <= 65535:
        raise ValueError('Port must be from 1 to 65535.')
    root = Path(root).resolve()
    folder = host_root(root, distribution)
    local = load(folder / 'local_runtime.json')
    arguments = [str(root / '.work/runtime/python-3.12.10-embed-amd64/python.exe'), '-B', '-X', 'utf8',
                 str(root / 'scripts/run_workspace.py'), '--port', str(port),
                 '--workspace-dir', str(folder / 'workspace'), '--ollama-path', local['executable']]
    state = load(ready_path(folder)) if ready_path(folder).exists() else {}
    for kind, relative in profile_paths(state).items():
        arguments += ['--' + kind + '-config', str(folder / relative)]
    return arguments


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument('--prepare', action='store_true')
    modes.add_argument('--verify', action='store_true')
    modes.add_argument('--plan', action='store_true')
    modes.add_argument('--launch', action='store_true')
    parser.add_argument('--distribution', default='Ubuntu')
    parser.add_argument('--download', action='store_true')
    parser.add_argument('--accept-model-license', action='store_true')
    parser.add_argument('--port', type=int, default=8772)
    args = parser.parse_args(argv)
    if (args.download or args.accept_model_license) and not args.prepare:
        parser.error('Download/license switches require --prepare. Default mode is read-only.')
    try:
        if args.plan:
            print(json.dumps({'kind': 'plan_only_no_writes_or_processes', 'runtime_root': host_root(ROOT, args.distribution).relative_to(ROOT).as_posix(),
                              'required_host': 'Windows x64 / PowerShell 7 / WSL2 Ubuntu 24.04 amd64 / FUSE2 compatibility',
                              'model': model_pin(ROOT), 'restored_project_required': False,
                              'private_model_cache_required': False, 'system_install': False}, indent=2))
            return 0
        result = prepare(ROOT, args.distribution, allow_download=args.download, accept_license=args.accept_model_license) if args.prepare else verify(ROOT, args.distribution)
        print(json.dumps(result, indent=2), flush=True)
        if args.launch:
            environment = os.environ.copy()
            # Let the saved GUI provider profile choose its context. No parent change.
            environment.pop('OLLAMA_CONTEXT_LENGTH', None)
            return subprocess.call(launch_arguments(ROOT, args.distribution, args.port), cwd=ROOT, env=environment, shell=False)
        return 0
    except (OSError, ValueError, subprocess.SubprocessError, KeyError, TypeError) as error:
        print('Fresh runtime unavailable: ' + str(error), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
