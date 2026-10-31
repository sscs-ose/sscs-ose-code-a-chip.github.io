#!/usr/bin/env python3
"""Run a fresh core-bound flow with physical fanout splitting after CTS.

This modifies a build-directory COPY of the installed OpenLane flow entry
point. It does not edit OpenLane itself or relax the max-fanout limit of 10.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import threading

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import run_notebook_core_bound as notebook
from scripts import run_stage8_core_bound_demo as core
from scripts import audit_core_bound_clean as clean
from scripts.run_flow2_remaining_measurements import _sha, _save

CONFIG = core.DESIGN / "config_fanout.json"
ANTENNA_CONFIG = core.DESIGN / "config_fanout_antenna.json"
GUARDED_CONFIG = core.DESIGN / "config_fanout_guarded.json"
GUARD_PLAN = core.DESIGN / "antenna_guards.json"
GUARD_HELPER = Path("scripts/flow2_antenna_guard_odb.py")
HOOK = core.DESIGN / "fanout_hook.tcl"
LEGALIZE = core.DESIGN / "fanout_legalize.tcl"
SPLITTER = Path("scripts/flow2_split_fanout_odb.py")
INPUTS = tuple(dict.fromkeys((*core.INPUTS, CONFIG, HOOK, LEGALIZE, SPLITTER,
                             Path("scripts/run_flow2_core_bound_fanout.py"))))


def patched_flow(source: str, openlane_root: Path, hook: Path, *, guarded_routes=False) -> str:
    origin = "set ::env(OPENLANE_ROOT) [file dirname [file normalize [info script]]]"
    if source.count(origin) != 1:
        raise ValueError("installed OpenLane entry point has an unknown root assignment")
    pattern = r"(?m)^if\s*\{\s*\[\s*info exists flags_map\(-interactive\)\]"
    points = list(re.finditer(pattern, source))
    if len(points) != 1:
        raise ValueError("installed OpenLane main-dispatch marker is ambiguous")
    for p in (openlane_root, hook):
        if any(c in p.as_posix() for c in "{}\n\r"):
            raise ValueError("unsupported flow path characters")
    # Insert before replacing the origin so the match offset stays valid.
    index = points[0].start()
    # tclsh launched as Docker entrypoint need not export PWD. OpenLane's
    # error-reporting code reads it and otherwise hides the original error.
    source = source[:index] + ("set ::env(PWD) [pwd]\n"+
        ("set ::automx_enable_antenna_guards 1\n" if guarded_routes else "")+
        f"source {{{hook.as_posix()}}}\n") + source[index:]
    return source.replace(origin, f"set ::env(OPENLANE_ROOT) {{{openlane_root.as_posix()}}}", 1)


def runtime_command(flow_command: list[str], root: Path) -> list[str]:
    command = list(flow_command)
    image_index = command.index("--entrypoint") + 2
    command = command[:image_index + 1]
    command[command.index("--entrypoint") + 1] = "openroad"
    if "--name" in command:
        name_index = command.index("--name") + 1
        command[name_index] += "-probe"
    return command + ["-exit", "-no_init", "-python", str(root / SPLITTER), "--check-runtime"]


def audit(root: Path, tag: str, *, met2_routes=False, guarded_routes=False) -> dict:
    run_dir = root / core.DESIGN / "runs" / tag
    reasons = []
    metrics = {}
    gds = core._audit(root, tag, reasons, metrics)
    if gds is None:
        reasons.append("verified final core-bound GDS missing")
    reasons.extend(clean._zero_metric_reasons(metrics))
    sta, sta_reasons = clean._sta_reasons(run_dir)
    reasons.extend(sta_reasons)
    arc, arc_reasons = clean._arc_reasons(run_dir)
    reasons.extend(arc_reasons)
    topology = run_dir / "tmp/automx_fanout/topology.json"
    if topology.is_file():
        topo = json.loads(topology.read_text(encoding="utf-8"))
        if (topo.get("remaining_topological_violations") != []
                or topo.get("sink_limit") != (3 if guarded_routes else 4)
                or topo.get("antenna_reserve_per_sink") != (2 if guarded_routes else 1)
                or topo.get("projected_post_diode_sink_limit") != (9 if guarded_routes else 8)):
            reasons.append("post-CTS topology repair incomplete")
        if guarded_routes:
            expected = json.loads((root/GUARD_PLAN).read_text(encoding="utf-8"))["targets"]
            actual = topo.get("antenna_isolation", {}).get("targets", [])
            if (len(actual) != len(expected) or {t["pin"] for t in actual} != {t["pin"] for t in expected}
                    or any(t["master"] != e.get("guard_cell", "sky130_fd_sc_hd__buf_16")
                           for t in actual for e in expected if t["pin"] == e["pin"])
                    or topo.get("post_guard_topological_violations") != []):
                reasons.append("measured antenna endpoint isolation incomplete")
        if guarded_routes and not topo.get("digital_core_controls_included"):
            reasons.append("digital core control sinks missing from reserved fanout count")
    else:
        topo = None
        reasons.append("post-CTS topology report absent")
    config = run_dir / "config.tcl"
    resolved = config.read_text(encoding="utf-8") if config.is_file() else ""
    if not re.search(r'(?m)^set ::env\(MAX_FANOUT_CONSTRAINT\) "10"$', resolved):
        reasons.append("final resolved max-fanout limit must remain 10")
    if met2_routes:
        for name, layer in (("RT_MIN_LAYER", "met2"), ("DRT_MIN_LAYER", "met1"),
                            ("RT_CLOCK_MIN_LAYER", "met2")):
            if not re.search(rf'(?m)^set ::env\({name}\) "{layer}"$', resolved):
                reasons.append(f"antenna recovery requires {name}={layer}")
        if not re.search(r'(?m)^set ::env\(RUN_HEURISTIC_DIODE_INSERTION\) "1"$', resolved):
            reasons.append("antenna recovery must keep diode insertion enabled")
    if guarded_routes:
        for name, value in (("RT_MIN_LAYER", "met1"), ("DRT_MIN_LAYER", "met1"),
            ("GRT_ANT_ITERS", "1"), ("GRT_MAX_DIODE_INS_ITERS", "0"),
            ("GRT_REPAIR_ANTENNAS", "1"), ("RUN_HEURISTIC_DIODE_INSERTION", "1")):
            if not re.search(rf'(?m)^set ::env\({name}\) "{value}"$', resolved):
                reasons.append(f"guarded profile requires {name}={value}")
    tool_failures = []
    for path in sorted((run_dir/"logs").rglob("*.log")):
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            if re.match(r"\[ERROR\s+[A-Z]+-\d+\]", line):
                tool_failures.append({"log": path.relative_to(root).as_posix(), "message": line})
    return {"status": "CORE_BOUND_FANOUT_PHYSICAL_PASS" if not reasons else "FAIL",
            "reasons": reasons, "sta": sta, "antenna": arc,
            "tool_failures": tool_failures,
            "metrics": {k: metrics.get(k) for k in ("flow_status", *clean.ZERO_METRICS)},
            "topology": topo,
            "gds": gds.relative_to(root).as_posix() if gds else None,
            "gds_sha256": _sha(gds) if gds else None}


def _export(root: Path, tag: str) -> None:
    # Dedicated bundle keeps the complete timed OpenLane run, including ODB,
    # reports and GDS; sources remain at their normal paths.
    target = root / "server_results"
    if target.is_symlink() or not target.resolve().is_relative_to(root):
        raise ValueError("server_results must stay within the repository")
    target.mkdir(parents=True, exist_ok=True)
    records = []
    skipped = []
    build_relative = Path("build/flow2_core_bound_fanout") / tag
    run_relative = core.DESIGN / "runs" / tag
    mappings = [(build_relative, build_relative),
                (run_relative, build_relative / "openlane_run"),
                (run_relative / "results/final", Path("physical/sky130/core_bound") / tag)]
    for name in ("summary.json", "history.log"):
        mappings.append((build_relative / name,
                         Path("results/sky130/flow2_core_bound_fanout") / tag / name))
    for relative, exported_relative in mappings:
        source = root / relative
        if source.is_symlink() or not source.resolve().is_relative_to(root):
            skipped.append(relative.as_posix())
            continue
        if not source.exists():
            continue
        paths = sorted(source.rglob("*")) if source.is_dir() else [source]
        for path in paths:
            if path.is_symlink():
                if not path.is_file() or not path.resolve().is_relative_to(root):
                    skipped.append(path.relative_to(root).as_posix())
                    continue
            if not path.is_file():
                continue
            rel = (exported_relative / path.relative_to(source)
                   if source.is_dir() else exported_relative)
            dest = target / rel
            if dest.is_symlink() or not dest.resolve().is_relative_to(target.resolve()):
                raise ValueError(f"export target escapes download folder: {dest}")
            dest.parent.mkdir(parents=True, exist_ok=True)
            if not dest.is_file() or _sha(dest) != _sha(path):
                shutil.copy2(path, dest)
            records.append({"path": rel.as_posix(), "source": path.relative_to(root).as_posix(),
                            "sha256": _sha(dest), "bytes": dest.stat().st_size})
    _save(target / f"flow2_core_bound_fanout_{tag}_export.json", {
        "format": "automx-cim-fanout-export-v1", "tag": tag,
        "files": records, "skipped_symlinks": skipped,
        "scope": "core-bound external-analog flow and final views; complete ADC wrapper remains pending"})


def run(root: Path, *, tag: str, source: Path, pdk_root: Path,
        image: str = notebook.DEFAULT_IMAGE, execute: bool = False,
        audit_existing: bool = False, timeout_s: int = 7200, met2_routes=False,
        guarded_routes=False) -> dict:
    root, source, pdk_root = root.resolve(), source.resolve(), pdk_root.resolve()
    if not re.fullmatch(r"[A-Za-z0-9_-]+", tag) or timeout_s <= 0:
        raise ValueError("invalid fanout flow tag or timeout")
    if execute and audit_existing:
        raise ValueError("--run and --audit-existing are exclusive")
    if guarded_routes and met2_routes:
        raise ValueError("routing profiles are exclusive")
    selected_config = GUARDED_CONFIG if guarded_routes else ANTENNA_CONFIG if met2_routes else CONFIG
    inputs = tuple(dict.fromkeys((*INPUTS, ANTENNA_CONFIG))) if met2_routes else INPUTS
    if guarded_routes:
        inputs = tuple(dict.fromkeys((*INPUTS, GUARDED_CONFIG, GUARD_PLAN, GUARD_HELPER)))
    check = core.inspect(root, require_tool=False)
    report = {"format": "automx-cim-flow2-core-bound-fanout-v1", "tag": tag,
              "status": "BLOCKED_PREREQUISITES" if check["reasons"] else "READY_TO_RUN",
              "reasons": check["reasons"],
              "not_signoff": "external-analog core-bound top only; acquisition/ADC wrapper is a separate physical project"}
    if report["reasons"]:
        return report
    build = root / "build/flow2_core_bound_fanout" / tag
    if audit_existing:
        frozen = json.loads((build / "inputs.json").read_text(encoding="utf-8"))
        current = {rel.as_posix(): _sha(root / rel) for rel in inputs}
        if frozen != current:
            raise ValueError("fanout run inputs differ from their frozen snapshot")
        report.update(audit(root, tag, guarded_routes=True) if guarded_routes else
                      audit(root, tag, met2_routes=met2_routes) if met2_routes else audit(root, tag))
        _save(build / "summary.json", report)
        _export(root, tag)
        return report
    if not execute:
        return report
    notebook._requirements(root, source, pdk_root, image)
    if build.exists() or (root / core.DESIGN / "runs" / tag).exists():
        raise FileExistsError("fanout run tag already exists; audit it or use a new tag")
    build.mkdir(parents=True)
    _save(build / "inputs.json", {rel.as_posix(): _sha(root / rel) for rel in inputs})
    core._snapshot(root, tag)
    installed = source / "flow.tcl"
    driver = build / "flow_with_fanout.tcl"
    log = build / "openlane.log"
    history = build / "history.log"
    history.write_text(f"{datetime.now(timezone.utc).isoformat()} START {tag}\n", encoding="utf-8")
    process = None
    container = "automx-fo-" + tag.lower()

    def stop_container():
        try:
            subprocess.run(["docker", "stop", "--time", "10", container],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=20)
        except (OSError, subprocess.TimeoutExpired):
            pass
        if process and process.poll() is None:
            process.kill()

    try:
        driver.write_text(patched_flow(installed.read_text(encoding="utf-8"), source, root / HOOK,
                         guarded_routes=guarded_routes), encoding="utf-8")
        report["installed_flow_sha256"] = _sha(installed)
        report["patched_flow_sha256"] = _sha(driver)
        command = notebook.docker_command(root, tag, source, pdk_root, image)
        command[command.index("--entrypoint") + 1] = "tclsh"
        command.insert(command.index(image) + 1, str(driver))
        command[command.index("-config_file") + 1] = str(root / selected_config)
        command[2:2] = ["--name", container]
        probe_log = build / "openroad_python_preflight.log"
        print(f"Checking embedded OpenROAD Python before synthesis: {probe_log}", flush=True)
        with probe_log.open("w", encoding="utf-8") as stream:
            try:
                probe = subprocess.run(runtime_command(command, root), cwd=root,
                    stdout=stream, stderr=subprocess.STDOUT, timeout=60, check=False)
            except subprocess.TimeoutExpired:
                # The docker client timeout alone does not stop its container.
                try:
                    subprocess.run(["docker", "stop", "--time", "10", container + "-probe"],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=20, check=False)
                except (OSError, subprocess.TimeoutExpired):
                    pass
                stream.write("\nEmbedded Python preflight timed out after 60s\n")
                raise
        report["embedded_python_preflight"] = {"returncode": probe.returncode,
            "log": probe_log.relative_to(root).as_posix(), "sha256": _sha(probe_log)}
        if probe.returncode:
            raise RuntimeError("OpenROAD embedded Python/ODB probe failed; inspect openroad_python_preflight.log")
        with log.open("w", encoding="utf-8") as stream:
            process = subprocess.Popen(command, cwd=root, stdout=subprocess.PIPE,
                                       stderr=subprocess.STDOUT, text=True, bufsize=1)
            timer = threading.Timer(timeout_s, stop_container)
            timer.start()
            try:
                for line in process.stdout:
                    print(line, end="", flush=True)
                    stream.write(line)
                    stream.flush()
                report["returncode"] = process.wait()
            finally:
                timer.cancel()
        report.update(audit(root, tag, guarded_routes=True) if guarded_routes else
                      audit(root, tag, met2_routes=met2_routes) if met2_routes else audit(root, tag))
        if report["returncode"] != 0:
            report["reasons"].append("OpenLane exited nonzero or timed out")
            report["status"] = "FAIL"
    except BaseException as error:
        if process and process.poll() is None:
            stop_container()
        report["status"] = "INTERRUPTED" if isinstance(error, KeyboardInterrupt) else "FAIL"
        report["error"] = f"{type(error).__name__}: {error}"
        if not isinstance(error, Exception):
            raise
    finally:
        _save(build / "summary.json", report)
        with history.open("a", encoding="utf-8") as stream:
            stream.write(f"{datetime.now(timezone.utc).isoformat()} END {report['status']}\n")
        _export(root, tag)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--tag", default="core_bound_fanout_20261018_01")
    parser.add_argument("--source", type=Path, default=notebook.DEFAULT_SOURCE)
    parser.add_argument("--pdk-root", type=Path, default=notebook.DEFAULT_PDK)
    parser.add_argument("--image", default=notebook.DEFAULT_IMAGE)
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--audit-existing", action="store_true")
    parser.add_argument("--met2-routes", action="store_true", help="keep long signal/clock routes off met1 for antenna recovery")
    parser.add_argument("--guarded-routes", action="store_true", help="measured small-gate isolation and bounded diode repair on met1 global profile")
    parser.add_argument("--timeout-s", type=int, default=7200)
    args = parser.parse_args()
    report = run(args.root, tag=args.tag, source=args.source, pdk_root=args.pdk_root,
                 image=args.image, execute=args.run, audit_existing=args.audit_existing, timeout_s=args.timeout_s,
                 met2_routes=args.met2_routes, guarded_routes=args.guarded_routes)
    print(json.dumps(report, indent=2))
    if (args.run or args.audit_existing) and report["status"] != "CORE_BOUND_FANOUT_PHYSICAL_PASS":
        raise SystemExit(1)
