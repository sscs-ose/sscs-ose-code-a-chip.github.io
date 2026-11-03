"""Thin ngspice batch runner: one folder per job, parallel execution, wrdata parsing."""

import os
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np

from .pdk import SPICEINIT


class SpiceError(RuntimeError):
    pass


def run(netlist: str, workdir: Path, seed: int | None = None, timeout: float = 7200) -> Path:
    """Run `netlist` in its own folder `workdir`; returns the folder."""
    workdir = Path(workdir)
    workdir.mkdir(parents=True, exist_ok=True)
    (workdir / ".spiceinit").write_text(SPICEINIT)
    if seed is not None:
        # `.option seed` makes the mismatch draws reproducible across processes
        # (`set rndseed` in .spiceinit does not: verified with ngspice-47)
        title, rest = netlist.split("\n", 1)
        netlist = f"{title}\n.option seed={seed}\n{rest}"
    (workdir / "tb.cir").write_text(netlist)
    r = subprocess.run(["ngspice", "-b", "tb.cir"], cwd=workdir, capture_output=True,
                       text=True, timeout=timeout)
    (workdir / "ngspice.log").write_text(r.stdout + r.stderr)
    bad = [ln for ln in (r.stdout + r.stderr).splitlines()
           if ln.lower().startswith(("error", "fatal")) or "simulation(s) aborted" in ln.lower()]
    if r.returncode != 0 or bad:
        tail = "\n".join((r.stdout + r.stderr).splitlines()[-25:])
        raise SpiceError(f"ngspice failed in {workdir}:\n{tail}")
    return workdir


MB_PER_JOB = 450   # ngspice + SKY130 models, measured ~350 MB


def default_workers() -> int:
    """Parallel ngspice jobs limited by CPU count and by available memory."""
    cpus = max(1, (os.cpu_count() or 2) - 1)
    try:
        with open("/proc/meminfo") as fh:
            avail_kb = next(int(ln.split()[1]) for ln in fh if ln.startswith("MemAvailable"))
        cpus = min(cpus, max(1, int(avail_kb / 1024 * 0.8 / MB_PER_JOB)))
    except (OSError, StopIteration):
        pass
    return int(os.environ.get("SARGEN_JOBS", cpus))


def run_many(jobs, max_workers: int | None = None):
    """jobs: iterable of dicts with keys netlist, workdir, [seed]. Returns list of workdirs."""
    jobs = list(jobs)
    max_workers = max_workers or default_workers()
    with ThreadPoolExecutor(max_workers) as ex:
        futs = [ex.submit(run, j["netlist"], j["workdir"], j.get("seed")) for j in jobs]
        return [f.result() for f in futs]


def _key(name: str) -> str:
    """Normalise vector names: lower case, 'v(node)' -> 'node'."""
    n = name.strip().lower()
    return n[2:-1] if n.startswith("v(") and n.endswith(")") else n


def read_wrdata(path: Path) -> dict:
    """Parse `wrdata` output written with wr_singlescale + wr_vecnames."""
    path = Path(path)
    with path.open() as fh:
        names = fh.readline().split()
    data = np.loadtxt(path, skiprows=1, ndmin=2)
    return {_key(n): data[:, k] for k, n in enumerate(names)}


def read_print(path: Path) -> dict:
    """Parse lines `name = value` written by `print ... > file` / echo."""
    out = {}
    for ln in Path(path).read_text().splitlines():
        if "=" in ln:
            k, v = ln.split("=", 1)
            try:
                out[_key(k)] = float(v.split()[0])
            except (ValueError, IndexError):
                pass
    return out
