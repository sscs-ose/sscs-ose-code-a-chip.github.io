#!/usr/bin/env python3
"""Build or verify the external-analog core-bound GDS on the prepared Linux host.

Stage 4/5 and RTL notebook cells run first. This runner launches the pinned
OpenLane 1 image without an interactive ``make mount`` shell, then audits the
physical top. The full mixed-signal wrapper is outside this experiment.
"""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import audit_core_bound_clean as clean_audit  # noqa: E402
from scripts import run_stage8_core_bound_demo as core_bound  # noqa: E402


DEFAULT_IMAGE = "efabless/openlane:30ee1388932eb55a89ad84ee43997bfe3a386421-amd64"
DEFAULT_SOURCE = Path("/home/nam/dependencies/openlane_src")
DEFAULT_PDK = Path("/home/nam/.volare_openlane_30ee138_nam")
RECEIPT = Path("results/receipts/notebook_core_bound.json")


def select_tag(root: Path, preferred: str) -> str:
    """Reuse a completed matching run, or allocate a fresh immutable tag.

    Stage-5 reruns can change the frozen input hashes even when the notebook
    uses the same preferred tag. Never overwrite an older snapshot or run.
    """
    root = root.resolve()
    if not re.fullmatch(r"[A-Za-z0-9_-]+", preferred):
        raise ValueError("OpenLane tag must contain only letters, digits, _ or -")
    snapshots = (
        (root / "build/stage8_core_bound", core_bound.INPUTS),
        (root / "build/stage8_core_bound_clean", clean_audit.INPUT_FILES),
    )
    expected = [
        {relative.as_posix(): sha256((root / relative).read_bytes()).hexdigest()
         for relative in files}
        for _, files in snapshots
    ]
    runs = root / core_bound.DESIGN / "runs"
    candidates = [preferred]
    candidates.extend(sorted({
        p.name for directory, _ in snapshots if directory.is_dir()
        for p in directory.iterdir()
        if p.is_dir() and p.name.startswith(preferred + "_")
    }, reverse=True))

    def snapshot_matches(directory: Path, inputs: dict[str, str],
                         tag: str) -> bool | None:
        path = directory / tag / "inputs.json"
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8")) == inputs
        except (OSError, ValueError):
            return False

    def snapshot_states(tag: str) -> tuple[bool | None, ...]:
        return tuple(snapshot_matches(directory, inputs, tag)
                     for (directory, _), inputs in zip(snapshots, expected))

    def completed_run(tag: str) -> bool:
        run = runs / tag
        gds = run / "results/final/gds/automx_cim_core_bound_demo.gds"
        metrics = run / "reports/metrics.csv"
        if not gds.is_file() or not gds.stat().st_size:
            return False
        try:
            with metrics.open(encoding="utf-8-sig", newline="") as stream:
                rows = list(csv.DictReader(stream))
            return len(rows) == 1 and rows[0].get("flow_status") == "flow completed"
        except (OSError, ValueError, csv.Error):
            return False

    # A complete run with exactly the current physical inputs may be audited.
    for tag in candidates:
        if all(state is True for state in snapshot_states(tag)) and completed_run(tag):
            return tag
    # A partly reserved tag can be used if neither snapshot conflicts and
    # OpenLane has not created a run directory yet.
    for tag in candidates:
        if all(state is not False for state in snapshot_states(tag)) and not (runs / tag).exists():
            return tag
    while True:
        tag = f"{preferred}_{datetime.now(timezone.utc):%Y%m%dT%H%M%S%f}"
        if (not any((directory / tag).exists() for directory, _ in snapshots)
                and not (runs / tag).exists()):
            return tag


def docker_command(root: Path, tag: str, source: Path, pdk_root: Path,
                   image: str, home: Path | None = None) -> list[str]:
    """Use the server's OpenLane image and the same bind mounts as make mount."""
    root = root.resolve()
    source = source.resolve()
    pdk_root = pdk_root.resolve()
    home = (home or Path.home()).resolve()
    if not root.is_relative_to(home):
        raise ValueError(f"project must be under mounted home directory: {home}")
    if not source.is_relative_to(home):
        raise ValueError(f"OpenLane source must be under mounted home directory: {home}")
    if not pdk_root.is_relative_to(home):
        raise ValueError(f"OpenLane PDK root must be under mounted home directory: {home}")
    return [
        "docker", "run", "--rm", "--user", f"{os.getuid()}:{os.getgid()}",
        "--network", "host", "--security-opt", "seccomp=unconfined",
        "-v", f"{source}:/openlane",
        "-v", f"{source / 'designs'}:/openlane/install",
        "-v", f"{home}:{home}", "-v", f"{pdk_root}:{pdk_root}",
        "-e", f"PDK_ROOT={pdk_root}", "-e", "PDK=sky130A",
        "-w", "/openlane", "--entrypoint", "/openlane/flow.tcl", image,
        "-design", str(root / core_bound.DESIGN),
        "-config_file", str(root / clean_audit.VARIANT), "-tag", tag,
    ]


def _requirements(root: Path, source: Path, pdk_root: Path, image: str) -> None:
    if sys.platform != "linux":
        raise RuntimeError("OpenLane notebook build runs only on the prepared Linux server")
    if not (source / "flow.tcl").is_file():
        raise FileNotFoundError(f"OpenLane 1 flow.tcl missing: {source / 'flow.tcl'}")
    if not (pdk_root / "sky130A/libs.tech/openlane/config.tcl").is_file():
        raise FileNotFoundError(f"OpenLane SKY130 PDK missing: {pdk_root}")
    if shutil.which("docker") is None:
        raise RuntimeError("Docker CLI is missing on the Linux server")
    image_check = subprocess.run(["docker", "image", "inspect", image],
                                 stdout=subprocess.DEVNULL,
                                 stderr=subprocess.DEVNULL, check=False)
    if image_check.returncode:
        raise RuntimeError(f"OpenLane image not present locally: {image}")
    if not root.is_dir():
        raise FileNotFoundError(root)


def _render(root: Path, tag: str, gds: Path) -> Path:
    png = root / "results/sky130" / f"{tag}_top.png"
    if not (shutil.which("xvfb-run") and shutil.which("klayout")):
        raise RuntimeError(f"GDS is ready at {gds}; install xvfb, xauth and klayout to render PNG")
    env = os.environ.copy()
    env.update(AUTOMX_GDS=str(gds), AUTOMX_PNG=str(png))
    subprocess.run(["xvfb-run", "-a", "klayout", "-z", "-x", "-r",
                    str(root / "scripts/render_gds_klayout.py")],
                   cwd=root, env=env, check=True)
    if not png.is_file() or png.stat().st_size == 0:
        raise RuntimeError(f"KLayout did not write PNG: {png}")
    return png


def run(root: Path, tag: str, *, source: Path = DEFAULT_SOURCE,
        pdk_root: Path = DEFAULT_PDK, image: str = DEFAULT_IMAGE,
        render: bool = True) -> dict:
    root = root.resolve()
    source = source.resolve()
    pdk_root = pdk_root.resolve()
    run_dir = root / core_bound.DESIGN / "runs" / tag
    # Build this before checking Docker so an existing run can be audited even
    # when the container is not running. Both snapshots reject changed inputs.
    prepared = core_bound.run(root, tag=tag)
    if prepared["status"] != "READY_CORE_BOUND_EXPERIMENT":
        raise RuntimeError("Core-bound prerequisites: " + "; ".join(prepared["reasons"]))
    clean_prepared = clean_audit.run(root, tag)
    if clean_prepared["status"] != "READY_CLEAN_CORE_BOUND_EXPERIMENT":
        raise RuntimeError("Clean variant prerequisites: " +
                           "; ".join(clean_prepared["reasons"]))
    if not run_dir.exists():
        _requirements(root, source, pdk_root, image)
        command = docker_command(root, tag, source, pdk_root, image)
        log = root / "build/stage8_core_bound_clean" / tag / "openlane_notebook.log"
        log.parent.mkdir(parents=True, exist_ok=True)
        print("OpenLane log:", log, flush=True)
        with log.open("w", encoding="utf-8") as stream:
            completed = subprocess.run(command, cwd=root, stdout=stream,
                                       stderr=subprocess.STDOUT, check=False)
        if completed.returncode:
            raise RuntimeError(f"OpenLane exited {completed.returncode}; see {log}")
    top = core_bound.run(root, tag=tag, audit_existing=True)
    if top["status"] != "CORE_BOUND_TOP_DRC_LVS_PASS_EXTERNAL_ANALOG":
        raise RuntimeError("Top GDS audit failed: " + "; ".join(top["reasons"]))
    # This stricter audit is recorded even if clock fanout remains above its
    # zero-violation target. The known clean01 result has 57 violations.
    physical = clean_audit.run(root, tag, audit_existing=True)
    gds = root / top["final_gds"]
    report = {
        "format": "automx-cim-notebook-core-bound-v1",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "status": "CORE_BOUND_GDS_READY",
        "tag": tag,
        "scope": "Stage-5 passive CIM core plus routed digital two-phase controller; external analog front end",
        "gds": top["final_gds"],
        "gds_sha256": top["final_gds_sha256"],
        "top_drc_lvs": top["status"],
        "strict_timing_status": physical["status"],
        "strict_timing_reasons": physical["reasons"],
        "png": None,
        "not_signoff": top["not_signoff"],
    }
    if render:
        report["png"] = _render(root, tag, gds).relative_to(root).as_posix()
    receipt = root / RECEIPT
    receipt.parent.mkdir(parents=True, exist_ok=True)
    receipt.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--tag", default="core_bound_notebook_20261011_01")
    parser.add_argument("--openlane-source", type=Path,
                        default=Path(os.environ.get("AUTOMX_OPENLANE_SOURCE", DEFAULT_SOURCE)))
    parser.add_argument("--openlane-pdk-root", type=Path,
                        default=Path(os.environ.get("AUTOMX_OPENLANE_PDK_ROOT", DEFAULT_PDK)))
    parser.add_argument("--openlane-image", default=os.environ.get("AUTOMX_OPENLANE_IMAGE", DEFAULT_IMAGE))
    parser.add_argument("--no-render", action="store_true")
    args = parser.parse_args()
    print(json.dumps(run(args.root, args.tag, source=args.openlane_source,
                         pdk_root=args.openlane_pdk_root, image=args.openlane_image,
                         render=not args.no_render), indent=2))
