"""Restore the declared release inputs and compressed layouts; never run the design."""
from pathlib import Path, PurePosixPath
import argparse
import gzip
import json
import shutil
import tarfile
import tempfile
import urllib.request

ROOT = Path(__file__).resolve().parents[1]

def layouts():
    paths = []
    for compressed in sorted((ROOT / 'exports').glob('*.gds.gz')):
        target = compressed.with_suffix('')
        if not target.is_file():
            partial = target.with_name(target.name + '.partial')
            try:
                with gzip.open(compressed, 'rb') as source, partial.open('wb') as out:
                    shutil.copyfileobj(source, out)
                partial.replace(target)
            finally:
                partial.unlink(missing_ok=True)
        paths.append(str(target.relative_to(ROOT)))
    return paths

def restore(archive):
    count = 0
    # Stream once. Reject other top-level payloads and all path/link escapes.
    with tarfile.open(archive, 'r|gz') as stream:
        for member in stream:
            path = PurePosixPath(member.name)
            if path.is_absolute() or '..' in path.parts or not path.parts:
                raise ValueError('Unsafe archive path: ' + member.name)
            allowed = path.parts[0] in {'inputs', 'pdks', 'tools'} or path.parts[:2] == ('data', 'uci_har')
            if not allowed:
                raise ValueError('Unexpected runtime payload: ' + member.name)
            destination = ROOT / member.name
            if not destination.resolve().is_relative_to(ROOT):
                raise ValueError('Destination escapes project: ' + member.name)
            if not (member.isfile() or member.isdir() or member.issym() or member.islnk()):
                raise ValueError('Unsupported archive entry: ' + member.name)
            if member.issym() or member.islnk():
                link = PurePosixPath(member.linkname)
                anchor = ROOT if member.islnk() else destination.parent
                if link.is_absolute() or not (anchor / member.linkname).resolve().is_relative_to(ROOT):
                    raise ValueError('Unsafe archive link: ' + member.name)
            if hasattr(tarfile, 'data_filter'):
                stream.extract(member, ROOT, filter='data')
            else:
                stream.extract(member, ROOT)
            count += 1
    return count

def check():
    required = [
        'inputs/core.gds', 'inputs/conditioner.gds', 'inputs/adc.gds',
        'inputs/digital_blocks/source_library.json',
        'inputs/electrical_candidate/readout/source.sv',
        'pdks/analog/sky130A/libs.tech/ngspice/sky130.lib.spice',
        'pdks/digital/sky130A/libs.tech/openlane/config.tcl',
        'tools/openlane/flow.tcl', 'tools/openlane-image.tar',
        'tools/ngspice/libngspice.so', 'tools/netgen/bin/netgen',
        'tools/opensta_current/build/sta',
        'data/uci_har/UCI HAR Dataset/test/X_test.txt',
        'data/source_notebook_cell_ids.json', 'data/checkpoints',
    ]
    tools = {name: shutil.which(name) for name in ['docker', 'iverilog', 'vvp', 'ngspice', 'klayout', 'magic', 'tclsh']}
    missing = [name for name in required if not (ROOT / name).exists()]
    return {'runtime_files_present': not missing, 'missing_files': missing, 'host_tools': tools,
            'missing_host_tools': [name for name, executable in tools.items() if not executable],
            'scope': 'Presence check; does not execute a design flow or test Docker daemon access.'}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group()
    source.add_argument('--archive', type=Path)
    source.add_argument('--url', help='Explicit HTTPS URL of the prepared runtime GitHub Release asset')
    parser.add_argument('--layouts-only', action='store_true')
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    members = 0
    if args.archive:
        members = restore(args.archive.resolve(strict=True))
    elif args.url:
        if not args.url.startswith('https://'):
            parser.error('--url requires HTTPS')
        with tempfile.TemporaryDirectory(prefix='automx_release_') as folder:
            local = Path(folder) / 'runtime.tar.gz'
            with urllib.request.urlopen(args.url, timeout=90) as response, local.open('wb') as out:
                shutil.copyfileobj(response, out)
            members = restore(local)
    elif not (args.layouts_only or args.check):
        parser.error('Use --archive PATH, --url URL, --layouts-only or --check.')
    rendered = layouts() if not args.check else []
    report = {'restored_archive_members': members, 'layouts': rendered, **check()}
    if members:
        (ROOT / 'runtime_preparation.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))

if __name__ == '__main__':
    main()
