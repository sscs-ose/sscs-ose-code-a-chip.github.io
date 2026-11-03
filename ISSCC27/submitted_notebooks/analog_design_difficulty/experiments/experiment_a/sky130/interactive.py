#!/usr/bin/env python3
"""Bounded SPICE reruns for the notebook's interactive cells (first cut, tt, 27 C).

The notebook reads the committed results by default. With ``SOURCE = "spice"`` its
cells call the two functions below, which rerun only the bench behind that cell
with the existing scripts:

- ``excitation``: one previous/target acquisition on the input-step test (a), the
  output-port test with the interface resistance ``R_if`` (b), and the connected
  transmission gate (c) -- the benches of ``run_sky130.py``;
- ``width_ladder``: the zero-step hold bench for the gate variants of the width
  ladder and the dummy-switch variant -- ``run_followup.held_sample_residuals``.

Generated netlists and waveforms go to a temporary directory (or ``workdir``),
never to ``results/``; the committed evidence is not modified. Requires ngspice
and SKY130A (``PDK_ROOT`` or ``SKY130_NGSPICE_LIB``, see ``spice_runner.py``).
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

import matplotlib

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
_backend = matplotlib.get_backend()
import spice_runner as sr  # noqa: E402
import run_sky130 as rs  # noqa: E402
import run_followup as rf  # noqa: E402

# the simulation scripts select the Agg backend on import; keep the caller's (e.g. inline) backend
matplotlib.use(_backend)

TESTS = {"input step": ("a", "out"), "output port + R_if": ("b", "samp"), "connected TG": ("c", "samp")}


def _use_workdir(workdir: str | Path | None) -> Path:
    path = Path(workdir) if workdir else Path(tempfile.mkdtemp(prefix="sky130_interactive_"))
    path.mkdir(parents=True, exist_ok=True)
    sr.GENERATED = path
    return path


def excitation(previous: float, target: float, benches: list[str],
               workdir: str | Path | None = None) -> dict[str, tuple]:
    """Rerun the selected benches for one acquisition; return {bench: (t_ns, error_mV)}.

    The error is the bench node (driver output for the input-step test, ``Cs`` otherwise)
    minus its settled value, as in ``results/data/sky130_waveforms_tt.csv``. ``R_if`` is the
    committed interface value (the chosen gate's largest DC on-resistance over 0.6-1.2 V).
    """
    _use_workdir(workdir)
    summary = json.loads((rs.RESULTS_DATA / "sky130_summary.json").read_text())
    rif = summary["switch_ron"]["R_if_ohm"]
    tests = "".join(TESTS[b][0] for b in benches)
    jobs = rs.grid_jobs([(target, previous)], tests, rif=rif)
    out = {}
    for (_, name, _), case_dir in zip(jobs, sr.run_many(jobs)):
        bench = next(b for b in benches if TESTS[b][0] == name[0])
        w = rs.load(case_dir)
        out[bench] = (1e9 * w["t"], 1e3 * (w[TESTS[bench][1]] - w["vref"]))
    return out


def width_ladder(names: list[str] | None = None, workdir: str | Path | None = None) -> dict:
    """Rerun the zero-step hold bench for the width-ladder variants; same keys as ``held_sample``."""
    _use_workdir(workdir)
    return {"VLSB_mV": 1e3 * rf.VLSB, "share_mV": 1e3 * rf.HS_SHARE,
            "variants": rf.held_sample_residuals(names)}
