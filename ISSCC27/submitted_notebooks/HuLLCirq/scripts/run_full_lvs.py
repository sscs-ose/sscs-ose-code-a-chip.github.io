"""Run the pinned LibreLane CLI with one fixed full-extraction Tcl variant.

The upstream 3.0.16 Tcl is preserved except for ``extract`` -> ``extract all``.
The latter extracts the full fresh geometry without the incremental per-use
missing-.ext timestamp search. No cell abstraction, ignore rule, PDK file,
tool installation, worker, Netgen comparison, or circuit input is changed.
"""
import hashlib
import importlib.metadata
import json
from pathlib import Path
import sys

RELEASE = '3.0.16'
UPSTREAM_SCRIPT_SHA256 = '461bf51e4226c283de33361bad02f48d0335ad7ab05965cbba43e2677e040660'
FULL_SCRIPT_SHA256 = '005c7419a1ffc7a1a7987e74fccd6f450864fd102d6bbae7f6af7fe224b7935d'


def main(argv=None):
    if importlib.metadata.version('librelane') != RELEASE:
        raise RuntimeError('Use the pinned LibreLane 3.0.16 runtime.')
    from librelane.steps.magic import SpiceExtraction
    from librelane.__main__ import cli

    if SpiceExtraction.id != 'Magic.SpiceExtraction':
        raise RuntimeError('Unexpected registered extraction step.')
    original_method = SpiceExtraction.get_script_path
    original_path = Path(original_method(None))
    original = original_path.read_bytes()
    if hashlib.sha256(original).hexdigest() != UPSTREAM_SCRIPT_SHA256:
        raise RuntimeError('Installed upstream extraction Tcl does not match the pinned source.')
    script = Path(__file__).resolve().with_name('extract_spice_full.tcl')
    variant = script.read_bytes()
    if (hashlib.sha256(variant).hexdigest() != FULL_SCRIPT_SHA256
            or original.count(b'\nextract\n') != 1
            or variant != original.replace(b'\nextract\n', b'\nextract all\n', 1)):
        raise RuntimeError('The full-extraction Tcl must be the exact fixed one-line variant.')

    print('HuLLCirq full extraction launcher: ' + json.dumps({
        'librelane': RELEASE, 'entrypoint': 'librelane.__main__.cli',
        'step': SpiceExtraction.id, 'upstream_script_sha256': UPSTREAM_SCRIPT_SHA256,
        'script': str(script), 'script_sha256': FULL_SCRIPT_SHA256,
        'change': 'extract -> extract all', 'added_abstract_cells': 0,
        'added_ignore_rules': 0,
    }), flush=True)
    SpiceExtraction.get_script_path = lambda self: str(script)
    try:
        return cli(args=list(sys.argv[1:] if argv is None else argv))
    finally:
        SpiceExtraction.get_script_path = original_method


if __name__ == '__main__':
    main()
