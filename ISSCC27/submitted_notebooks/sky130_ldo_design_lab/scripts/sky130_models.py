"""Check and extract the included public SKY130 compact models."""
from pathlib import Path
import hashlib
import json
import tarfile

ROOT = Path(__file__).resolve().parents[1]


def ensure_models(cache_dir=None):
    """Return a portable ngspice library path without downloading a PDK."""
    destination = Path(cache_dir or ROOT / 'work/sky130_models').resolve()
    source = ROOT / 'models'
    manifest = json.loads((source / 'SOURCE_MANIFEST.json').read_text(encoding='utf8'))
    archive = source / manifest['archive']
    if hashlib.sha256(archive.read_bytes()).hexdigest() != manifest['archive_sha256']:
        raise ValueError('The SKY130 model archive does not match its manifest')
    expected = {item['path']: item for item in manifest['downloaded_files']}
    destination.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive, 'r:gz') as bundle:
        for member in bundle:
            if member.name not in expected or not member.isfile():
                raise ValueError('Unexpected model archive entry')
            target = (destination / member.name).resolve()
            if not target.is_relative_to(destination):
                raise ValueError('Model path is outside the extraction directory')
            item = expected[member.name]
            if target.is_file() and hashlib.sha256(target.read_bytes()).hexdigest() == item['sha256']:
                continue
            data = bundle.extractfile(member).read()
            if len(data) != item['bytes'] or hashlib.sha256(data).hexdigest() != item['sha256']:
                raise ValueError('A SKY130 source file differs from its original hash')
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
    for name, item in expected.items():
        if hashlib.sha256((destination / name).read_bytes()).hexdigest() != item['sha256']:
            raise ValueError('Model archive is incomplete')
    lines = ['* Public SKY130 MOS model wrapper', '* Original device parameters are unchanged']
    for corner in ('tt', 'ss', 'ff', 'sf', 'fs'):
        lines.extend([f'.lib {corner}', '.option scale=1e-6',
                      f'.include "{(destination / "models/parameters/lod.spice").as_posix()}"'])
        for family in ('nfet_01v8', 'pfet_01v8', 'nfet_01v8_lvt', 'pfet_01v8_lvt'):
            for suffix in (corner, 'mismatch'):
                path = destination / f'cells/{family}/sky130_fd_pr__{family}__{suffix}.corner.spice'
                lines.append(f'.include "{path.as_posix()}"')
        lines.append(f'.endl {corner}')
    wrapper = destination / 'sky130.lib.spice'
    wrapper.write_text('\n'.join(lines) + '\n', encoding='utf8')
    return wrapper


if __name__ == '__main__':
    print(ensure_models())
