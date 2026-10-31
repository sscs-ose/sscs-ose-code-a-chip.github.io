#!/usr/bin/env python3
"""Read-only ZIP/mirror and native-attempt audit of a downloaded ADC finish run."""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path, PurePosixPath
import re
import sys
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import flow2_integration_common as common
from scripts import flow2_adc_native_sessions as sessions
from scripts import flow2_waveforms as waves
from scripts import run_flow2_adc_finish as finish

import numpy as np


def audit(folder):
    folder = Path(folder).resolve()
    index = json.loads((folder/"export.json").read_text(encoding="utf-8"))
    archive = folder/PurePosixPath(index["archive"]["path"]).name
    if common._sha(archive) != index["archive"]["sha256"]:
        raise ValueError("download archive hash mismatch")
    names = set()
    with ZipFile(archive) as z:
        if z.testzip() is not None:
            raise ValueError("download ZIP CRC failure")
        stored = json.loads(z.read("diagnostic_index.json"))
        if stored != {k:v for k,v in index.items() if k != "archive"}:
            raise ValueError("download and ZIP index differ")
        for item in index["files"]:
            rel = PurePosixPath(item["path"])
            if rel.is_absolute() or ".." in rel.parts or rel.as_posix() in names:
                raise ValueError("unsafe/duplicate artifact path")
            names.add(rel.as_posix())
            p = common._verified(folder, item)
            if sha256(z.read(rel.as_posix())).hexdigest() != item["sha256"]:
                raise ValueError("ZIP artifact hash mismatch: "+str(p))
    summary_path = folder/common.BASE/index["tag"]/"summary.json"
    if (folder/"summary.json").read_bytes() != summary_path.read_bytes():
        raise ValueError("summary mirror differs")
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    execution_root = PurePosixPath(summary["execution_root"])
    observations = []
    base = folder/common.BUILD/index["tag"]
    for log_path in sorted(base.rglob("native.log")):
        driver = log_path.parent/"session.script"
        log = log_path.read_text(encoding="utf-8", errors="replace")
        commands = driver.read_text(encoding="utf-8").splitlines()
        command = next((l for l in commands if l.startswith(("source ", "snload "))), "")
        observed = {"log":log_path.relative_to(folder).as_posix(),
            "log_sha256":common._sha(log_path), "command":command,
            "parsed_marker":"AUTOMX_SESSION_PHASE=PARSED" in log,
            "returned_marker":"AUTOMX_SESSION_PHASE=RETURNED" in log,
            "raw_files":len(list(log_path.parent.glob("segment_*.raw"))),
            "source_failed":"Command 'source' failed:" in log}
        references = re.findall(r"Reference value\s*:\s*([+\-\d.eE]+)", log)
        observed["last_reported_transient_s"] = float(references[-1]) if references else None
        observed["timed_out"] = "TIMEOUT after " in log
        observed["solver_messages"] = re.findall(r"Using (KLU|SPARSE 1\.3) as Direct Linear Solver",log)
        quoted = re.fullmatch(r'source "([^"\r\n]+)"', command)
        if quoted:
            try:
                rel = PurePosixPath(quoted[1]).relative_to(execution_root).as_posix()
            except ValueError:
                rel = None
            observed["referenced_circuit_exported"] = rel in names if rel else False
            # This evidence distinguishes a missing copy from retained quotes
            # in the filename printed by native perror.
            observed["literal_quoted_path_in_error"] = '"'+quoted[1]+'": No such file or directory' in log
        if command.startswith("snload "):
            circuit = command.split()[1]
            observed["casefolded_path_failure"] = (circuit != circuit.lower() and
                circuit.lower()+": No such file or directory" in log)
            staged_file=log_path.parent/"staged_inputs.json"
            if staged_file.is_file():
                aliases=json.loads(staged_file.read_text(encoding="utf-8"))
                for alias in aliases:
                    for key in ("original","staged"):
                        rel=PurePosixPath(alias[key]["path"]).relative_to(execution_root).as_posix()
                        common._verified(folder,dict(alias[key],path=rel))
                    if alias["original"]["sha256"] != alias["staged"]["sha256"]:
                        raise ValueError("snapshot input alias differs")
                observed["staged_input_hashes_match"]=True
        records = []
        for raw in sorted(log_path.parent.glob("segment_*.raw"),key=lambda p:int(p.stem.split("_")[1])):
            v = waves.read_raw(raw)
            records.append({"path":raw.relative_to(folder).as_posix(),"sha256":common._sha(raw),
                            "last_s":float(v["time"][-1]),"points":len(v["time"]),"variables":len(v)})
        observed["raw_checkpoints"] = records
        if records and "conversion_" in log_path.as_posix():
            v = waves.read_raw(folder/records[-1]["path"])
            mask = v["time"] >= 20e-9
            clock = v["v(adc_clk_dig)"][mask] > .9
            observed["partial_waveform"] = {"scope":"only the last completed native raw checkpoint",
                "last_s":float(v["time"][-1]),"clock_midrail_crossings_after_start":int(np.count_nonzero(clock[1:]!=clock[:-1])),
                "eoc_full_high_after_start_observed":bool(np.any(v["v(eoc_osr)"][mask]>1.62))}
        observations.append(observed)
    quote_failure = bool(observations) and all(o["source_failed"] and
        o.get("literal_quoted_path_in_error") and o.get("referenced_circuit_exported") and
        not o["parsed_marker"] and not o["raw_files"] for o in observations)
    loads = {}
    if summary["completed_sims"] == 2 and all(j["status"]=="MEASURED_NATIVE_ADC_DIAGNOSTIC"
        for j in summary.get("jobs",[]) if j.get("task")=="load"):
        source = json.loads((folder/common.BASE/summary["source_tag"]/"summary.json").read_text(encoding="utf-8"))
        prior = source["branches"]["adc"]
        source_rc = common._verified(folder,prior["source_rc_spice"])
        pins = finish.adc.original.adc._spice_pins(source_rc)
        probes = finish.adc.original.input_switches(source_rc)
        loads = finish.verified_loads(folder,index["tag"],
            model=common._verified(folder,prior["derived_native_model"]),
            net=common._verified(folder,prior["equivalent_rc_spice"]),pins=pins,probes=probes,
            binary_sha=summary["command_probe"]["binary"]["sha256"],
            source_sha=summary["source_evidence"]["source_summary_sha256"])
        loads = {name:{"validation":"ORIGINAL_RAW_REANALYSIS_MATCH", "analysis":j["analysis"],
                       "native_raw_segments":j["native_raw_segments"]} for name,j in loads.items()}
    diagnosis = "NUTMEG_SOURCE_RETAINED_LITERAL_QUOTES" if quote_failure else "INSPECT_NATIVE_ATTEMPTS"
    if loads and any(o.get("casefolded_path_failure") for o in observations):
        diagnosis = "TWO_LOADS_MEASURED; CONVERSIONS_TIMEOUT; SNLOAD_PATH_CASEFOLDED"
    restore_crash = bool(re.search(r"(?<!\d)-11(?!\d)",summary.get("snapshot_probe",{}).get("error","")))
    if restore_crash:
        diagnosis="NATIVE_SNAPSHOT_RESTORE_SIGSEGV; NO_NEW_CONVERSION_LAUNCHED"
    return {"format":"automx-cim-adc-finish-copy-review-v1", "tag":index["tag"],
        "integrity":{"archive_sha256":common._sha(archive), "verified_payload_files":len(names),
                     "archive_crc":"PASS", "ZIP_and_mirror_hashes":"PASS"},
        "source_status":summary["status"], "completed_sims":summary["completed_sims"],
        "planned_sims":summary["planned_sims"], "native_attempts":observations,
        "diagnosis":diagnosis, "revalidated_loads":loads,
        "snapshot_restore_SIGSEGV":restore_crash,
        "reused_core_bound":summary["source_evidence"]["fanout"],
        "physical_scope":summary["source_evidence"]["physical_scope"],
        "not_signoff":"copy/native-command audit only; no new ADC conversion or full wrapper signoff"}


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("folder", type=Path)
    p.add_argument("--output", type=Path)
    args = p.parse_args()
    result = audit(args.folder)
    if args.output:
        common._save(args.output, result)
    print(json.dumps(result, indent=2))
