"""Run an Analog Design Bench public testbench on one circuit with ngspice."""
from __future__ import annotations

import re
import shutil
import subprocess
import time
from pathlib import Path

SCALAR = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*([-+0-9.eE]+)(?:\s|$)")


def stage(bench_dir: Path, circuit: Path, work: Path, sky130_root: Path) -> Path:
    """Lay out work/ like the task container (/app) and rewrite absolute paths."""
    if work.exists():
        shutil.rmtree(work)
    (work / "testbench").mkdir(parents=True)
    shutil.copy(circuit, work / "circuit.spi")
    for src in bench_dir.iterdir():
        if src.is_file():
            text = src.read_text(errors="replace")
            text = text.replace("/app/", f"{work}/").replace("/opt/sky130/", f"{sky130_root}/")
            (work / "testbench" / src.name).write_text(text)
    return work / "testbench"


def _scalars(text: str) -> dict[str, float]:
    out: dict[str, float] = {}
    for line in text.splitlines():
        m = SCALAR.match(line)
        if m:
            try:
                out[m.group(1)] = float(m.group(2))
            except ValueError:
                pass
    return out


def run_script(script: str, args: list[str], bench_dir: Path, circuit: Path, work: Path, sky130_root: Path,
               python: str = "python3", timeout: int = 900) -> dict:
    """Run a task's public Python checker (it calls ngspice itself) on one circuit."""
    tb = stage(Path(bench_dir), Path(circuit), Path(work), Path(sky130_root))
    start = time.time()
    proc = subprocess.run([python, script, *args], cwd=tb, capture_output=True, text=True, timeout=timeout)
    errors = [l for l in (proc.stdout + proc.stderr).splitlines() if re.search(r"(?i)\berror\b|traceback", l)]
    return {"scalars": _scalars(proc.stdout), "seconds": time.time() - start, "errors": errors[:5],
            "returncode": proc.returncode, "stdout": proc.stdout[-2000:]}


def run(bench: str, bench_dir: Path, circuit: Path, work: Path, sky130_root: Path,
        ngspice: str = "ngspice", timeout: int = 900) -> dict:
    """Run one bench; return its printed scalars, runtime and log tail."""
    tb = stage(Path(bench_dir), Path(circuit), Path(work), Path(sky130_root))
    return run_staged(bench, tb, ngspice, timeout)


def run_staged(bench: str, tb: Path, ngspice: str = "ngspice", timeout: int = 900) -> dict:
    """Run a bench in an already staged testbench directory."""
    deck = tb / bench
    deck.write_text(re.sub(r"(?m)^\s*listing expand.*$", "", deck.read_text()))
    start = time.time()
    proc = subprocess.run([ngspice, "-b", bench], cwd=tb, capture_output=True, text=True, timeout=timeout)
    seconds = time.time() - start
    scalars = _scalars(proc.stdout)
    errors = [l for l in (proc.stdout + proc.stderr).splitlines()
              if re.search(r"(?i)\berror\b", l) and "out of interval" not in l]
    return {"scalars": scalars, "seconds": seconds, "errors": errors[:5], "returncode": proc.returncode}
