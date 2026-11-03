"""
PrecisionFit -- central path resolution.

Every script in this project resolves paths through this module instead of
hard-coding relative paths like "../../results". That means the scripts work
no matter what the current working directory is (shell, notebook kernel, CI).

Repo layout (see the implementation guide, section 0):

    precisionfit/
    |- src/python/      <- this file lives here
    |- src/verilog/rtl/ <- generated .v files
    |- src/tb/
    |- synth/
    |- results/sweeps/  results/pareto/
    `- report/
"""
from pathlib import Path

# src/python/paths.py -> parents[2] == precisionfit/
ROOT = Path(__file__).resolve().parents[2]

PYTHON_DIR = ROOT / "src" / "python"
VERILOG_DIR = ROOT / "src" / "verilog"
RTL_DIR = VERILOG_DIR / "rtl"
TB_DIR = ROOT / "src" / "tb"
SYNTH_DIR = ROOT / "synth"
RESULTS_DIR = ROOT / "results"
SWEEPS_DIR = RESULTS_DIR / "sweeps"
PARETO_DIR = RESULTS_DIR / "pareto"
REPORT_DIR = ROOT / "report"
NOTEBOOKS_DIR = ROOT / "notebooks"

ALL_DIRS = (
    RTL_DIR, TB_DIR, SYNTH_DIR, RESULTS_DIR, SWEEPS_DIR, PARETO_DIR,
    REPORT_DIR, NOTEBOOKS_DIR,
)


def ensure_dirs() -> None:
    """Create every output directory if it does not already exist."""
    for d in ALL_DIRS:
        d.mkdir(parents=True, exist_ok=True)


def rel(p) -> str:
    """Return a path relative to the repo root, for readable print statements."""
    p = Path(p)
    try:
        return str(p.resolve().relative_to(ROOT))
    except ValueError:
        return str(p)
