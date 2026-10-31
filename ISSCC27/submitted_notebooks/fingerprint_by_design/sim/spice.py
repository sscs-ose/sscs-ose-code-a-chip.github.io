"""Shared helpers for running SKY130 mismatch Monte Carlo in ngspice."""
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

PDK_LIB = Path.home() / ".volare/sky130A/libs.tech/ngspice/sky130.lib.spice"
SPINIT = Path.home() / ".volare/sky130A/libs.tech/ngspice/spinit"
# process corner with mismatch; override with SKY130_CORNER (e.g. ss_mm, ff_hh_mm)
CORNER = os.environ.get("SKY130_CORNER", "tt_mm")
# first chip seed; override with CHIP_SEED0 to simulate a different chip range
SEED0 = int(os.environ.get("CHIP_SEED0", "1"))


def mc_control(n_chips, body, seed0=1):
    """ngspice .control block: one virtual chip per seed, same seeds at every
    temperature so chip k has the same mismatch draw everywhere."""
    return f"""
.control
let run = 0
while run < {n_chips}
  let seed = run + {seed0}
  setseed $&seed
  mc_source
  echo "@@CHIP $&seed"
{body}
  let run = run + 1
end
.endc
"""


def run_netlist(text, timeout=3600):
    """Run a netlist in batch mode in a temp dir; return stdout."""
    with tempfile.TemporaryDirectory() as d:
        shutil.copy(SPINIT, Path(d) / ".spiceinit")
        (Path(d) / "c.sp").write_text(text)
        r = subprocess.run(["ngspice", "-b", "c.sp"], cwd=d, capture_output=True,
                           text=True, timeout=timeout)
    return r.stdout


def parse_blocks(stdout):
    """Split stdout on '@@CHIP k' markers -> {k: text}."""
    out, cur = {}, None
    for line in stdout.splitlines():
        m = re.match(r"@@CHIP (\d+)", line.strip())
        if m:
            cur = int(m.group(1))
            out[cur] = []
        elif cur is not None:
            out[cur].append(line)
    return {k: "\n".join(v) for k, v in out.items()}
