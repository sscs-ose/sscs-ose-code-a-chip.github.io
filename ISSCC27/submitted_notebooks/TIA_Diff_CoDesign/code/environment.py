"""Portable paths and bounded CPU resources for the submitted workflow."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CODE = ROOT / 'code'


def configure():
    allowed = sorted(os.sched_getaffinity(0)) if hasattr(os, 'sched_getaffinity') else list(range(os.cpu_count() or 1))
    budget = min(16, max(1, (os.cpu_count() or 2) // 2), len(allowed))
    if hasattr(os, 'sched_setaffinity'):
        os.sched_setaffinity(0, allowed[:budget])
    for name in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
        os.environ[name] = '1'
    os.environ.setdefault('MPLCONFIGDIR', str(Path(os.environ.get('TMPDIR', '/tmp')) / 'tia-submission-mpl'))
    installed = ROOT / 'tools/opt/bin/ngspice'
    if 'TIA_NGSPICE_BIN' not in os.environ and installed.is_file():
        os.environ['TIA_NGSPICE_BIN'] = str(installed)
    return budget


def spiral_domain(explicit=None):
    """Resolve one domain consistently for prediction and identity checks."""
    return Path(explicit or os.environ.get('TIA_SPIRAL_DOMAIN')
                or ROOT/'data/spiral_search_domain.json').resolve()


def pdk_root():
    location=os.environ.get('TIA_PDK_ROOT')
    if not location:
        raise RuntimeError('Install IHP SG13G2 separately and set TIA_PDK_ROOT to its checkout.')
    path=Path(location).expanduser().resolve()
    if not (path/'ihp-sg13g2/libs.tech/ngspice/models/sg13g2_hbt_mod.lib').is_file():
        raise FileNotFoundError('TIA_PDK_ROOT does not contain the SG13G2 ngspice models.')
    return path
