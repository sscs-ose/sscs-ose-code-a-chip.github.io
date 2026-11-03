"""Report the tool and PDK locations used by the two analog examples."""
from importlib.metadata import version
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
print('Python:', sys.version.split()[0])
for package in ('numpy', 'scipy', 'matplotlib', 'klayout', 'gdsfactory', 'ciel'):
    print(f'{package}: {version(package)}')
for tool in ('git', 'klayout', 'xschem'):
    path = shutil.which(tool)
    if not path:
        raise SystemExit(f'Missing {tool}; read the notebook environment setup.')
    print(f'{tool}: {path}')
simulator = Path.home() / '.local/share/perfpdn/tools/ngspice-47/bin/ngspice'
if not simulator.is_file():
    raise SystemExit('Run bash scripts/install_ngspice.sh.')
print(subprocess.check_output([str(simulator), '--version'], text=True).strip())
pdk = Path(os.environ.get('PDK_ROOT', str(Path.home() / '.local/share/perfpdn/pdks'))) / 'sky130A'
for relative in ('libs.tech/ngspice/sky130.lib.spice', 'libs.tech/klayout/drc/sky130A_mr.drc',
                 'libs.tech/klayout/lvs/sky130.lvs', 'libs.tech/magic/sky130A.tech'):
    if not (pdk / relative).is_file():
        raise SystemExit(f'Missing PDK file: {pdk / relative}')
print('SKY130:', pdk)
print('Tool locations are ready. Run uv run --locked python scripts/perfpdn.py --help.')
