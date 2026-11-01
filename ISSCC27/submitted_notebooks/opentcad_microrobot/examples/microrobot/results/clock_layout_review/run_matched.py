"""Run only the reviewed 4 ms / 25 ns clock cases, never overwrite a run."""
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import subprocess
import sys
import time

REPO = Path(__file__).resolve().parents[4]
LOCAL = REPO / 'examples/microrobot/local_runs/clock_layout/contact_escape_v2'
SCRIPT = REPO / 'examples/microrobot/local_runs/clock_layout/run_electrical.py'


def run(name):
    dest = LOCAL / name
    dest.mkdir(exist_ok=False)
    command = [sys.executable, '-u', str(SCRIPT), name, '25e-9']
    start = time.monotonic()
    env = os.environ.copy()
    env['PYTHONPATH'] = str(REPO)
    status = {'command': command, 'cwd': str(REPO), 'outer_timeout_s': 220,
              'ngspice_timeout_s': 180, 'created_fresh': True}
    try:
        result = subprocess.run(command, cwd=REPO, env=env, text=True,
                                capture_output=True, timeout=220)
        status['returncode'] = result.returncode
        output = result.stdout + result.stderr
    except subprocess.TimeoutExpired as exc:
        status['outer_timeout'] = True
        output = str(exc) + '\n' + str(exc.stdout) + '\n' + str(exc.stderr)
    status['wall_s'] = time.monotonic() - start
    (dest / 'execution.log').write_text(output)
    (dest / 'execution.json').write_text(json.dumps(status, indent=2) + '\n')
    print(json.dumps({'case': name, **status}), flush=True)


if __name__ == '__main__':
    with ThreadPoolExecutor(max_workers=2) as executor:
        list(executor.map(run, ['schematic_25ns', 'extracted_25ns']))
