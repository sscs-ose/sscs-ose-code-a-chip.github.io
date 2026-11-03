"""Assemble the Code-a-Chip submission folder from committed files.

    python scripts/export_submission.py [dest]      (default: dist/GlitchScope)

Layout: GlitchScope.ipynb at the folder root, the glitchscope package, data caches,
benchmarks, scripts, tests, README, LICENSE, tools.env.example (no machine paths).
"""
import io, shutil, subprocess, sys, tarfile
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
dest = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "dist" / "GlitchScope"
if dest.exists():
    shutil.rmtree(dest)
dest.mkdir(parents=True)
tar = subprocess.run(["git", "-C", str(ROOT), "archive", "--format=tar", "HEAD"], check=True, capture_output=True).stdout
with tarfile.open(fileobj=io.BytesIO(tar)) as t:
    t.extractall(dest, filter="data")
shutil.move(dest / "notebooks" / "GlitchScope.ipynb", dest / "GlitchScope.ipynb")
shutil.rmtree(dest / "notebooks")
(dest / "tools.env").unlink(missing_ok=True)
(dest / "tools.env.example").write_text(
    "# Copy to tools.env and adjust, or export these as environment variables.\n"
    "# Only needed to recompute SPICE / synthesis data and for live runs; figures use cached data.\n"
    "GS_LIB=/path/to/sky130_fd_sc_hd__tt_025C_1v80.lib\n"
    "GS_PDK_ROOT=/path/to/sky130A\n"
    "GS_NGSPICE=/path/to/ngspice\n"
    "# layout study only (section 10): OpenROAD, OpenROAD-flow-scripts checkout, Magic\n"
    "GS_OPENROAD=/path/to/openroad\n"
    "GS_ORFS=/path/to/OpenROAD-flow-scripts\n"
    "GS_MAGIC=/path/to/magic\n"
    "GS_YOSYS=/path/to/yosys\n"
    "GS_STA=/path/to/sta\n")
# machine paths in logs / reports written by the local toolchain -> placeholders
import re as _re
_tools = None
_env = ROOT / "tools.env"
if _env.exists():
    for _l in _env.read_text().splitlines():
        if _l.startswith("GS_YOSYS="):
            _tools = str(Path(_l.split("=", 1)[1].strip()).parents[2])
for _p in dest.rglob("*"):
    if _p.is_file() and _p.suffix in (".log", ".tcl", ".txt", ".ipynb", ".json", ".md", ".v", ".sdc"):
        try:
            _t = _p.read_text()
        except UnicodeDecodeError:
            continue
        _n = _t.replace(str(ROOT), "<repo>")
        if _tools:
            _n = _n.replace(_tools, "<tools>")
        if _n != _t:
            _p.write_text(_n)
n = sum(1 for _ in dest.rglob("*") if _.is_file())
size = sum(p.stat().st_size for p in dest.rglob("*") if p.is_file())
print(f"exported {n} files, {size / 1e6:.1f} MB -> {dest}")


# Pre-PR reminder: placeholders still present in the notebook header?
_nb = (dest / "GlitchScope.ipynb").read_text()
if "[DRAFT" in _nb:
    print("WARNING: notebook still contains [DRAFT] placeholders (team / affiliation) -- fill in before the PR.")
if "GITHUB_USER" in _nb:
    print("WARNING: set the fork URL (GITHUB_USER) in the notebook's setup cell -- Colab fetches from it until the PR is merged.")
