"""Pinned LibreLane entrypoint for qualified, per-definition MOSCAP extraction.

Installed PDK/tool files are not edited. The separate technology copy adds a
style used only for a vendor-geometry-qualified decap leaf. Normal definitions
retain the original ngspice style. No warning, cell or device is suppressed.
"""
import hashlib
import importlib.metadata
import json
from pathlib import Path
import sys

RELEASE = '3.0.16'
UPSTREAM_SCRIPT_SHA256 = '461bf51e4226c283de33361bad02f48d0335ad7ab05965cbba43e2677e040660'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main(argv=None):
    if importlib.metadata.version('librelane') != RELEASE:
        raise RuntimeError('Use the pinned LibreLane 3.0.16 runtime.')
    from librelane.steps.magic import SpiceExtraction
    from librelane.__main__ import cli
    root = Path(__file__).resolve().parent
    manifest = json.loads((root / 'input-manifest.json').read_text(encoding='utf-8'))
    profile = manifest['configuration']['profile']
    variant, recognition = profile['extraction_variant'], profile['terminal_recognition_variant']
    if profile['profile_version'] != 'hullcirq-sky130-lvs-v6' or SpiceExtraction.id != 'Magic.SpiceExtraction':
        raise RuntimeError('Require the fixed qualified-terminal extraction profile and step.')
    paths = {name: root / Path(value).name for name, value in (
        ('script', variant['script_path']), ('helper', recognition['helper_path']), ('wrapper', recognition['wrapper_path']))}
    for name, path in paths.items():
        declaration = variant if name == 'script' else recognition
        if sha(path) != declaration[name + '_sha256']:
            raise RuntimeError('A frozen qualified-extraction source changed: ' + name)
    original_method = SpiceExtraction.get_script_path
    original_path = Path(original_method(None))
    if sha(original_path) != UPSTREAM_SCRIPT_SHA256:
        raise RuntimeError('Installed upstream extraction Tcl changed.')
    namespace = {'__name__': 'hullcirq_moscap_fixed_helper', '__file__': str(paths['helper'])}
    exec(compile(paths['helper'].read_bytes(), str(paths['helper']), 'exec'), namespace)
    namespace['prepare'](root)
    print('HuLLCirq MOSCAP extraction launcher: ' + json.dumps({
        'librelane': RELEASE, 'entrypoint': 'librelane.__main__.cli', 'step': SpiceExtraction.id,
        'profile_version': profile['profile_version'], 'upstream_script_sha256': UPSTREAM_SCRIPT_SHA256,
        'script': str(paths['script']), 'script_sha256': sha(paths['script']),
        'helper_sha256': sha(paths['helper']), 'wrapper_sha256': sha(paths['wrapper']),
        'qualified_cell': 'sky130_fd_sc_hd__decap_3', 'added_abstract_cells': 0, 'added_ignore_rules': 0,
    }), flush=True)
    SpiceExtraction.get_script_path = lambda self: str(paths['script'])
    try:
        return cli(args=list(sys.argv[1:] if argv is None else argv))
    finally:
        SpiceExtraction.get_script_path = original_method


if __name__ == '__main__':
    main()
