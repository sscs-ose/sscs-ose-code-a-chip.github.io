"""Persistent native ADC sessions with real ngspice snapshots and raw segments.

No IC/UIC, state fitting, model substitution or reset on snapshot continuation.
The SAME executable/circuit/settings must pass a small native continuation
probe before this facility is allowed on the full ADC. Snapshot files are
experimental ngspice state, not signoff views or a replacement for raw data.
"""
from __future__ import annotations

from hashlib import sha256
import json
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys

import numpy as np

from scripts import flow2_integration_common as common
from scripts import flow2_live_spice as live
from scripts import flow2_waveforms as waves

ALGORITHM = "NATIVE_SNAPSHOT_RAW_SEGMENTS_V3_LOWERCASE_ALIASES"


class NativeSessionError(ValueError):
    """A failed native attempt with a preserved receipt and diagnostic log."""


def _path_token(path):
    # Nutmeg source/snload pass the word straight to fopen, retaining quotes
    # (observed on the actual ngspice-44.2 server). This is NOT .include/.lib
    # syntax. Use a single unquoted token; never send shell-like quoting.
    token = Path(path).as_posix()
    if not re.fullmatch(r"[A-Za-z0-9_./:+-]+", token):
        raise ValueError("native source/snapshot path requires one unquoted token without spaces: "+token)
    return token


def _native_error(log):
    found = re.search(r"(?im)^.*(?:Command 'source' failed|^\s*error\b|^\s*fatal\b|"
                      r"not implemented|different version of spice|Some error in the CKT|"
                      r"no such command|unknown command|no such vector|syntax error).*$", log)
    return found.group(0).strip() if found else None


def _item(path):
    return {"path": str(Path(path).resolve()), "sha256": common._sha(Path(path))}


def _verified(item):
    path = Path(item["path"])
    if not path.is_file() or common._sha(path) != item["sha256"]:
        raise ValueError("session artifact differs: "+str(path))
    return path


def _stage_inputs(work, circuit, snapshot=None):
    """Use lowercase local filenames; native snload lowercases its arguments.

    Native source and snload also retain quotes. Do not put an absolute
    mixed-case path on either command. Copy the small bare circuit verbatim;
    hardlink/copy an immutable solver snapshot without changing its bytes.
    Absolute .lib/.include paths inside the circuit retain their SPICE syntax.
    """
    work = Path(work)
    aliases = []
    for src, name in ((Path(circuit), "circuit.spice"),
                      (Path(snapshot), "prior.snap") if snapshot else (None, None)):
        if src is None:
            continue
        target = work/name
        if target.exists():
            raise FileExistsError("native input alias already exists: "+str(target))
        original = _item(src)
        method = "COPY"
        if snapshot and name == "prior.snap":
            try:
                os.link(src, target)
                method = "HARDLINK"
            except OSError:
                shutil.copyfile(src, target)
        else:
            shutil.copyfile(src, target)
        staged = _item(target)
        if staged["sha256"] != original["sha256"]:
            raise ValueError("native input changed while staging")
        aliases.append({"original": original, "staged": staged, "method": method})
    return aliases


def control(circuit, *, points, names, conversion=False, start_s=20e-9,
            snapshot=None, snapshot_at_s=0., save_states=True, snapshot_stride=1, num_threads=4):
    if (not points or any(a >= b for a, b in zip(points, points[1:]))
            or any(not np.isfinite(t) or t <= snapshot_at_s for t in points)):
        raise ValueError("future, increasing checkpoints required")
    circuit_token = _path_token(circuit)
    if type(num_threads) is not int or not 1<=num_threads<=32:
        raise ValueError('native thread count must be an integer from 1 to 32')
    snapshot_token = _path_token(snapshot) if snapshot else None
    if not isinstance(snapshot_stride, int) or snapshot_stride < 1:
        raise ValueError("positive integer snapshot stride required")
    if not names or any(not re.fullmatch(r"[vi]\([^\s;]+\)", v, re.I) for v in names):
        raise ValueError("invalid native saved vector")
    # 'script' in the title is required by native snload; source must be a
    # bare circuit, otherwise its .control would run again during snload.
    lines = ["* script: AutoMX native snapshot continuation", ".control",
        "set ngbehavior=hsa", "set skywaterpdk", f"set num_threads={num_threads}",
        "option klu", "option noinit", "set filetype=ascii", "set numdgt=17",
        f"snload {circuit_token} {snapshot_token}" if snapshot else
        f"source {circuit_token}",
        "echo AUTOMX_SESSION_PHASE=PARSED", "rusage"]
    lines += [f"stop when time = {p:.17g}" for p in points]
    lines += ["let automx_first_eoc = 1e99", "repeat 1"]
    # Every checkpoint continues the current transient; no second run/reset.
    # The loop permits exiting soon after an actual completion, avoiding the
    # previous mandatory idle tail to 3 us. Python still validates fresh EOC,
    # reset/start, all bits and post-event stability from native raw segments.
    for index, _ in enumerate(points):
        lines += ["resume" if snapshot or index else "run",
            "let automx_now = time[length(time)-1]",
            f"write segment_{index}.raw "+" ".join(names)]
        if save_states and (index < 4 or index % snapshot_stride == 0 or index == len(points)-1):
            lines += [f"snsave state_{index}.snap"]
        lines += [f"echo AUTOMX_SESSION_CHECKPOINT={index} TIME_S=$&automx_now", "rusage"]
        if conversion:
            lines += [f"if automx_now > {start_s+2e-9:.17g}",
                "if v(EOC_OSR)[length(time)-1] > 1.62",
                "if automx_first_eoc > 1e90", "let automx_first_eoc = automx_now", "end", "end", "end",
                "if automx_now >= automx_first_eoc + 40n", "break", "end"]
    lines += ["end",
        "echo AUTOMX_SESSION_PHASE=RETURNED", "quit", ".endc", ".end", ""]
    return "\n".join(lines)


def merge(segments, *, maximum_gap_s):
    if not segments:
        raise ValueError("no native waveform segments")
    selected, provenance, previous = [], [], None
    for item in segments:
        vectors = waves.read_raw(_verified(item))
        t = vectors["time"]
        if previous is not None:
            if set(vectors) != set(previous):
                raise ValueError("restored waveform vectors changed")
            last = float(previous["time"][-1])
            eps = max(1e-20, abs(last)*1e-9)
            if t[0] < last-eps or t[0]-last > maximum_gap_s*(1+1e-6):
                raise ValueError("snapshot raw continuity gap or overlap")
            if abs(t[0]-last) <= eps:
                for name in vectors:
                    tolerance = 1e-10 if name.startswith("i(") else 1e-5
                    if name != "time" and not np.isclose(vectors[name][0], previous[name][-1], rtol=1e-5, atol=tolerance):
                        raise ValueError("snapshot boundary state discontinuity: "+name)
                vectors = {k: v[1:] for k, v in vectors.items()}
                if not len(vectors["time"]):
                    raise ValueError("snapshot made no forward progress")
        elif t[0] > 1e-20:
            raise ValueError("native history must begin at time zero")
        provenance.append({**item, "first_s": float(t[0]), "last_s": float(t[-1]), "points": len(t)})
        selected.append(vectors)
        previous = vectors
    return {k: np.concatenate([s[k] for s in selected]) for k in selected[0]}, provenance


def _records(work, log, *, points):
    records = []
    for index, at in re.findall(r"AUTOMX_SESSION_CHECKPOINT=(\d+) TIME_S=([+\-\d.eE]+)", log):
        index, at = int(index), float(at)
        if index >= len(points) or abs(at-points[index]) > max(1e-19, abs(at)*1e-7):
            raise ValueError("native stopped early or at an unexpected checkpoint")
        raw, snap = work/f"segment_{index}.raw", work/f"state_{index}.snap"
        vectors = waves.read_raw(raw)
        if abs(vectors["time"][-1]-at) > max(1e-19, abs(at)*1e-7):
            raise ValueError("checkpoint marker/raw time mismatch")
        state = None
        if snap.is_file():
            if snap.stat().st_size < 64 or f"Snapshot saved to state_{index}.snap." not in log:
                raise ValueError("native snapshot did not finish writing")
            state = _item(snap)
        records.append({"at_s": float(vectors["time"][-1]), "raw": _item(raw), "snapshot": state})
    if records and any(a["at_s"] >= b["at_s"] for a, b in zip(records, records[1:])):
        raise ValueError("native checkpoint order invalid")
    return records


def case(folder, *, executable, circuit, points, names, identity, timeout_s,
         conversion=False, start_s=20e-9, maximum_gap_s=1e-9,
         save_states=True, snapshot_stride=1, execute=live.run, num_threads=4):
    """One process per call; later calls resume the last verified native state.

    Completed attempts and their inputs remain immutable. Failed attempts
    are kept; a resume uses only the raw prefix ending at its chosen snapshot.
    A timeout is still PENDING, even if useful snapshot/raw data was saved.
    """
    folder = Path(folder).resolve()
    folder.mkdir(parents=True, exist_ok=True)
    spec = {"algorithm": ALGORITHM, "identity": identity, "circuit": _item(circuit),
        "binary": _item(executable), "points": points, "names": names,
        "conversion": conversion, "start_s": start_s,
        "byteorder": sys.byteorder, "pointer_bytes": struct.calcsize("P"),
        "maximum_gap_s": maximum_gap_s, "save_states": save_states, "snapshot_stride": snapshot_stride}
    # Preserve the identity of historical default four-thread sessions.
    if num_threads!=4:spec['num_threads']=num_threads
    frozen = folder/"inputs.json"
    if frozen.exists() and json.loads(frozen.read_text(encoding="utf-8")) != spec:
        raise FileExistsError("native session changed; use a fresh tag")
    if not frozen.exists():
        common._save(frozen, spec)
    snapshot, at_s, segments, attempts = None, 0., [], []
    for receipt in sorted(folder.glob("attempt_*/receipt.json")):
        r = json.loads(receipt.read_text(encoding="utf-8"))
        if r["spec_sha256"] != common._sha(frozen):
            raise ValueError("native attempt snapshot identity mismatch")
        for item in [r["log"], *r["segments"]]:
            _verified(item)
        for alias in r.get("staged_inputs", []):
            _verified(alias["original"])
            _verified(alias["staged"])
        for item in r.get("observed_segments", []):
            _verified(item)
        if r["snapshot"]:
            _verified(r["snapshot"])
        attempts.append(r)
        if r["status"] == "NATIVE_TRAJECTORY_RETURNED":
            vectors, proofs = merge(r["segments"], maximum_gap_s=maximum_gap_s)
            return r, vectors, proofs
        if r["snapshot"] and r["at_s"] > at_s:
            snapshot, at_s, segments = r["snapshot"], r["at_s"], r["segments"]
    future = [t for t in points if t > at_s+max(1e-20, abs(at_s)*1e-9)]
    if not future:
        raise ValueError("no future checkpoints; inspect incomplete attempt")
    # Keep even an orphan directory left by an OS crash. Never overwrite it,
    # and never pretend that raw without a validated receipt is resumable.
    indices = [int(p.name.split("_")[1]) for p in folder.glob("attempt_*")
               if p.is_dir() and re.fullmatch(r"attempt_\d+", p.name)]
    work = folder/f"attempt_{max(indices, default=-1)+1:03d}"
    work.mkdir()
    staged = _stage_inputs(work, circuit, _verified(snapshot) if snapshot else None)
    driver = control("circuit.spice", points=future, names=names, conversion=conversion,
        start_s=start_s, snapshot="prior.snap" if snapshot else None, snapshot_at_s=at_s,
        save_states=save_states, snapshot_stride=snapshot_stride,num_threads=num_threads)
    (work/"session.script").write_text(driver, encoding="utf-8")
    command = [str(executable), "-n", "-b", "session.script"]
    print(("NATIVE_RESUME" if snapshot else "NATIVE_START")+
        f" {folder.parent.name}: saved_time={at_s:.12g}s; output={work}",flush=True)
    interrupted = False
    try:
        result = execute(command, work, timeout_s)
    except KeyboardInterrupt:
        interrupted = True
        saved_log = work/"ngspice.live.log"
        result = subprocess.CompletedProcess(command, 130, saved_log.read_text(errors="replace") if saved_log.is_file() else "", "")
    except Exception as error:
        saved_log = work/"ngspice.live.log"
        result = subprocess.CompletedProcess(command, -1,
            saved_log.read_text(errors="replace") if saved_log.is_file() else "",
            f"\nERROR: native launch failed: {type(error).__name__}: {error}\n")
    log = result.stdout+result.stderr
    (work/"native.log").write_text(log, encoding="utf-8")
    failure = _native_error(log)
    records = []
    try:
        if not failure:
            records = _records(work, log, points=future)
    except (ValueError, OSError) as error:
        failure = f"invalid native checkpoint: {error}"
    if result.returncode not in (0, 124, 130) and not failure:
        failure = f"native simulator exit {result.returncode}"
    if result.returncode == 0 and not records and not failure:
        failure = "native process returned without any valid raw checkpoint"
    if failure:
        receipt = work/"receipt.json"
        common._save(receipt, {"status": "BLOCKED_NATIVE_SESSION", "error": failure,
            "returncode": result.returncode, "spec_sha256": common._sha(frozen),
            "at_s": at_s, "segments": segments, "snapshot": snapshot,
            "log": _item(work/"native.log"), "from_snapshot": snapshot,
            "staged_inputs": staged,
            "scope": "failed attempt preserved; no new waveform or snapshot accepted"})
        if interrupted:
            raise KeyboardInterrupt
        raise NativeSessionError(f"{failure}; receipt: {receipt}; log: {work/'native.log'}")
    returned = result.returncode == 0 and "AUTOMX_SESSION_PHASE=RETURNED" in log
    saved = [r for r in records if r["snapshot"]]
    chosen = records[-1] if returned and records else saved[-1] if saved else None
    prefix = segments+([chosen["raw"]] if chosen else [])
    r = {"status": "NATIVE_TRAJECTORY_RETURNED" if returned and chosen else "PENDING_NATIVE_CONTINUATION",
        "returncode": result.returncode, "spec_sha256": common._sha(frozen),
        "at_s": chosen["at_s"] if chosen else at_s, "segments": prefix,
        "snapshot": chosen["snapshot"] if chosen else snapshot,
        "observed_at_s": records[-1]["at_s"] if records else at_s,
        "observed_segments": segments+([records[-1]["raw"]] if records else []),
        "resumable_from_snapshot": bool(chosen["snapshot"] if chosen else snapshot),
        "log": _item(work/"native.log"), "from_snapshot": snapshot,
        "staged_inputs": staged,
        "scope": "native trajectory only; measurement/ADC acceptance is a separate raw-data gate"}
    common._save(work/"receipt.json", r)
    if interrupted:
        raise KeyboardInterrupt
    vectors, proofs = merge(prefix, maximum_gap_s=maximum_gap_s) if prefix else (None, [])
    return r, vectors, proofs


def script_probe(folder, *, executable, timeout_s=30, execute=live.run):
    """Mandatory native source/run/stop/resume/raw gate before the large ADC.

    This small linear circuit checks the command interpreter, not ADC physics.
    A parser/path/control error must abort the campaign, not silently disable
    snapshots and launch four equally broken full-ADC attempts.
    """
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    circuit = folder/"native_script_probe.spice"
    text = ("AutoMX native command interpreter probe\n"
            "VIN in 0 PWL(0 0 1n 0 2n 1 8n 1)\n"
            "R1 in out 1k\nC1 out 0 1p\n"
            ".tran 10p 8n 0 10p\n.save v(in) v(out) i(VIN)\n.end\n")
    if circuit.exists() and circuit.read_text(encoding="utf-8") != text:
        raise FileExistsError("native command probe changed; use a fresh tag")
    if not circuit.exists():
        circuit.write_text(text, encoding="utf-8")
    receipt, vectors, proofs = case(folder/"session", executable=executable, circuit=circuit,
        points=[3e-9, 6e-9], names=["v(in)", "v(out)", "i(VIN)"],
        identity={"probe": "SOURCE_STOP_RESUME_RAW_V2"}, timeout_s=timeout_s,
        save_states=False, maximum_gap_s=11e-12, execute=execute)
    if receipt["status"] != "NATIVE_TRAJECTORY_RETURNED":
        raise NativeSessionError("native command probe did not finish; inspect "+str(folder))
    # Exact RC response to a 1 ns linear ramp; check physical native samples.
    errors = []
    for t in (3e-9, 4e-9, 6e-9):
        expected = 1-(1-np.exp(-1))*np.exp(-(t-2e-9)/1e-9)
        errors.append(abs(waves.sample(vectors, "v(out)", t)-expected))
    if max(errors) > .002 or abs(waves.sample(vectors, "v(in)", 6e-9)-1) > 1e-6:
        raise NativeSessionError("native command probe waveform differs from RC ramp response")
    report = {"status": "NATIVE_COMMAND_SCRIPT_PASS", "binary": _item(executable),
        "maximum_rc_response_error_v": max(errors), "session": receipt,
        "raw_proofs": proofs, "scope": "command/source/stop/resume only; not ADC evidence"}
    common._save(folder/"probe.json", report)
    return report


def integrate(vectors, signal, start_s, stop_s):
    time = vectors["time"]
    chosen = (time > start_s)&(time < stop_s)
    t = np.r_[start_s, time[chosen], stop_s]
    y = np.r_[waves.sample(vectors, signal, start_s), vectors[signal.lower()][chosen],
              waves.sample(vectors, signal, stop_s)]
    return float(np.sum(.5*(y[1:]+y[:-1])*(t[1:]-t[:-1])))


def probe(folder, *, executable, model, timeout_s=120, execute=live.run):
    """Exercise the actual native KLU/MOS/MIM snapshot, not an RC-only mock."""
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    cache = folder/"probe.json"
    if cache.is_file():
        saved = json.loads(cache.read_text(encoding="utf-8"))
        if saved["binary"] != _item(executable) or saved["model"] != _item(model):
            raise ValueError("native snapshot capability reference changed")
        for item in saved["proofs"]:
            _verified(item)
        return saved
    circuit = folder/"native_snapshot_probe.spice"
    text = ("Native four-model inverter snapshot continuity probe\n"
        f'.lib "{Path(model).as_posix()}" tt\n'
        ".temp 25\n.option klu method=gear reltol=1e-4 abstol=1e-13\n"
        "VVDD vdd 0 PWL(0 0 .5n 1.8 8n 1.8)\n"
        "VIN inp 0 PWL(0 0 1n 0 1.1n 1.8 3n 1.8 3.1n 0 5n 0 5.1n 1.8 6n 1.8 6.1n 0 8n 0)\n"
        "VFIN EOC_OSR 0 PWL(0 0 1n 0 1.1n 1.8 80n 1.8)\n"
        "Xn0 mid inp 0 0 sky130_fd_pr__nfet_01v8 w=1 l=.15\n"
        "Xp0 mid inp vdd vdd sky130_fd_pr__pfet_01v8 w=1 l=.15\n"
        "Xn1 out mid 0 0 sky130_fd_pr__nfet_01v8_lvt w=1 l=.15\n"
        "Xp1 out mid vdd vdd sky130_fd_pr__pfet_01v8_hvt w=1 l=.15\n"
        "Xcap out 0 sky130_fd_pr__cap_mim_m3_1 w=4.2 l=4.2\n"
        "R1 mid 0 1meg\nC1 mid 0 10f\n.tran 1p 80n 0 20p\n"
        ".save v(inp) v(mid) v(out) i(VVDD) v(EOC_OSR)\n.end\n")
    if circuit.exists() and circuit.read_text(encoding="utf-8") != text:
        raise FileExistsError("native probe circuit changed")
    if not circuit.exists():
        circuit.write_text(text, encoding="utf-8")
    names = ["v(inp)", "v(mid)", "v(out)", "i(VVDD)", "v(EOC_OSR)"]
    identity = {"model": _item(model), "probe": "FOUR_NATIVE_MOS_TYPES_MIM_KLU_V1"}
    _, reference, _ = case(folder/"reference", executable=executable, circuit=circuit,
        points=[4e-9,8e-9,60e-9], names=names, identity=identity, timeout_s=timeout_s,
        maximum_gap_s=21e-12, save_states=False, execute=execute)
    first, _, _ = case(folder/"pause", executable=executable, circuit=circuit,
        points=[4e-9], names=names, identity=identity, timeout_s=timeout_s,
        maximum_gap_s=21e-12, execute=execute)
    if first["snapshot"] is None:
        raise ValueError("native snapshot probe produced no state")
    resumed = folder/("restore_%03d" % len(list(folder.glob("restore_*"))))
    resumed.mkdir()
    staged = _stage_inputs(resumed, circuit, _verified(first["snapshot"]))
    common._save(resumed/"staged_inputs.json", staged)
    script = control("circuit.spice", points=[8e-9,60e-9,80e-9], names=names,
        snapshot="prior.snap", snapshot_at_s=4e-9, save_states=False,
        conversion=True,start_s=0.)
    (resumed/"session.script").write_text(script, encoding="utf-8")
    result = execute([str(executable),"-n","-b","session.script"], resumed, timeout_s)
    log = result.stdout+result.stderr
    (resumed/"native.log").write_text(log, encoding="utf-8")
    if result.returncode or _native_error(log):
        raise NativeSessionError(f"native snapshot restore failed: {_native_error(log) or result.returncode}; inspect {resumed/'native.log'}")
    restored = waves.read_raw(resumed/"segment_1.raw")
    if (restored["time"][0] < 4e-9 or abs(restored["time"][-1]-60e-9)>1e-16
            or (resumed/"segment_2.raw").exists()):
        raise ValueError("native snapshot did not resume at its saved time")
    samples = [4.25e-9,4.75e-9,5.5e-9,6.5e-9,7.5e-9]
    errors = {}
    for name in [v.lower() for v in names]:
        errors[name] = max(abs(waves.sample(reference,name,t)-waves.sample(restored,name,t)) for t in samples)
        if errors[name] > (5e-9 if name.startswith("i(") else .0005):
            raise ValueError("native snapshot continuity differs from uninterrupted reference: "+name)
    report = {"status": "NATIVE_MOS_MIM_KLU_SNAPSHOT_PROBE_PASS", "maximum_absolute_errors": errors,
        "samples_s": samples, "restore_start_s": float(restored["time"][0]),
        "binary": _item(executable), "model": _item(model),
        "proofs": [_item(p) for p in sorted(folder.rglob("*")) if p.is_file() and p != cache],
        "scope": "native continuation capability only; not ADC accuracy, loading or PVT signoff"}
    common._save(cache, report)
    return report
