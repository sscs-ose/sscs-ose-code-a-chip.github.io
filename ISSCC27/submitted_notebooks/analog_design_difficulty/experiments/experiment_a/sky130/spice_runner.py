#!/usr/bin/env python3
"""Small ngspice runner for the SKY130 netlists.

The committed netlists are ordinary SPICE text with a few ``@TOKEN@``
placeholders (PDK library path, corner, temperature, case parameters).
This module fills those tokens, writes the resolved netlist under
``results/generated/`` (git-ignored), runs ngspice in batch mode from this
directory so that the local ``.spiceinit`` is used, and reads ``wrdata``
output back into NumPy arrays.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
NETLISTS = HERE / "netlists"
GENERATED = REPO / "results" / "generated" / "sky130"


def pdk_library() -> Path:
    """Return the SKY130 ngspice model library path.

    Resolution order: ``SKY130_NGSPICE_LIB`` (full path to sky130.lib.spice),
    then ``PDK_ROOT``/sky130A/..., then the volare default ``~/.volare``.
    """
    explicit = os.environ.get("SKY130_NGSPICE_LIB")
    if explicit:
        lib = Path(explicit)
    else:
        root = Path(os.environ.get("PDK_ROOT", Path.home() / ".volare"))
        lib = root / "sky130A" / "libs.tech" / "ngspice" / "sky130.lib.spice"
    if not lib.is_file():
        raise FileNotFoundError(
            f"SKY130 ngspice library not found at {lib}. "
            "Set PDK_ROOT or SKY130_NGSPICE_LIB."
        )
    return lib


def ngspice_version() -> str:
    exe = shutil.which("ngspice")
    if exe is None:
        raise FileNotFoundError("ngspice not found on PATH")
    out = subprocess.run([exe, "--version"], capture_output=True, text=True).stdout
    match = re.search(r"ngspice-\S+", out)
    return match.group(0) if match else out.strip().splitlines()[0]


def render(template: str, tokens: dict[str, object]) -> str:
    text = (NETLISTS / template).read_text()
    for key, value in tokens.items():
        text = text.replace(f"@{key}@", str(value))
    leftover = re.findall(r"@[A-Z0-9_]+@", text)
    if leftover:
        raise ValueError(f"unfilled tokens in {template}: {sorted(set(leftover))}")
    return text


def run(template: str, name: str, tokens: dict[str, object]) -> Path:
    """Render ``template`` with ``tokens`` and run it; return the case directory."""
    case_dir = GENERATED / name
    case_dir.mkdir(parents=True, exist_ok=True)
    full_tokens = {"PDK_LIB": pdk_library(), "OUTDIR": case_dir, **tokens}
    # Subcircuit files (everything in netlists/ that is not a testbench) are
    # rendered next to the testbench so that ``.include "@OUTDIR@/..."`` works.
    for sub in sorted(NETLISTS.glob("*.spice")):
        if not sub.name.startswith("tb_"):
            (case_dir / sub.name).write_text(render(sub.name, full_tokens))
    netlist = case_dir / f"{name}.spice"
    text = render(template, full_tokens)
    log = case_dir / "ngspice.log"
    # SKY130_REUSE=1 skips a case whose resolved netlist is unchanged since a
    # completed earlier run (used only to regenerate figures quickly).
    if (os.environ.get("SKY130_REUSE") == "1" and netlist.is_file() and log.is_file()
            and netlist.read_text() == text and "fatal" not in log.read_text().lower()):
        return case_dir
    netlist.write_text(text)
    proc = subprocess.run(
        ["ngspice", "-b", str(netlist)],
        cwd=HERE,
        capture_output=True,
        text=True,
    )
    (case_dir / "ngspice.log").write_text(proc.stdout + proc.stderr)
    if proc.returncode != 0:
        raise RuntimeError(f"ngspice failed for {name}; see {case_dir / 'ngspice.log'}")
    return case_dir


def run_many(jobs: list[tuple[str, str, dict[str, object]]], workers: int | None = None) -> list[Path]:
    workers = workers or max(1, min(len(jobs), (os.cpu_count() or 2) - 1))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        return list(pool.map(lambda job: run(*job), jobs))


def read_wrdata(path: Path, names: list[str]) -> dict[str, np.ndarray]:
    """Read an ngspice ``wrdata`` file written for vectors ``names``.

    ``wrdata`` writes one (scale, value) column pair per vector; the scale
    (time or frequency) is returned under the key ``"scale"``.
    """
    data = np.loadtxt(path, ndmin=2)
    if data.shape[1] != 2 * len(names):
        raise ValueError(f"{path}: expected {2 * len(names)} columns, found {data.shape[1]}")
    out = {"scale": data[:, 0]}
    for i, name in enumerate(names):
        out[name] = data[:, 2 * i + 1]
    return out


def read_log_values(case_dir: Path) -> dict[str, float]:
    """Parse ``name = value`` lines printed by ``print`` / ``meas`` in the log."""
    values: dict[str, float] = {}
    pattern = re.compile(r"^\s*([A-Za-z_@][\w@\[\]().:]*)\s*=\s*([-+0-9.eE]+)")
    for line in (case_dir / "ngspice.log").read_text().splitlines():
        m = pattern.match(line)
        if m:
            try:
                values[m.group(1).lower()] = float(m.group(2))
            except ValueError:
                pass
    return values
