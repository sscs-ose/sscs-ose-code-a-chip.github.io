#!/usr/bin/env python3
"""Finish standalone ADC evidence, reusing the passed core-bound physical run.

Run on Ubuntu only with --run. Default conversions stay in one native process:
ngspice-44.2 snapshot restore crashed in the measured _07 capability probe.
No notebook, core SPICE sweep or new OpenLane routing is launched here.
"""
from __future__ import annotations

import argparse
from contextlib import redirect_stdout
from datetime import datetime, timezone
import copy
import json
import os
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts import flow2_adc_native_sessions as sessions
from scripts import flow2_adc_finish_profile as profile
from scripts import run_flow2_readout_closure as closure
from scripts import run_flow2_core_bound_fanout as fanout

adc, common, core, waves = profile.adc, closure.common, closure.core, profile.waves


def verify_source(root, source_tag, *, check_fanout=True):
    """Validate actual native input artifacts and the two completed partial raw files."""
    path = root/common.BASE/source_tag/"summary.json"
    previous = json.loads(path.read_text(encoding="utf-8"))
    prior = previous["branches"]["adc"]
    net = common._verified(root,prior["equivalent_rc_spice"])
    model = common._verified(root,prior["derived_native_model"])
    log = common._verified(root,prior["pdk_model_smoke"]["log"])
    model_smoke = adc.dc.analyze_model(log.read_text())
    structural = adc.startup.validate_four_terminal_mos(net.read_text(),model.read_text())
    source_rc = common._verified(root,prior["source_rc_spice"])
    probes, pins = adc.original.input_switches(source_rc),adc.original.adc._spice_pins(source_rc)
    evidence = []
    for part in prior["jobs"][0]["progress"]["checkpoints"]:
        raw = common._verified(root,part["raw"])
        vectors = waves.read_raw(raw)
        if vectors["time"][-1] >= 5e-9:
            witness = waves.sampling_witness(vectors,probes,start_s=4e-9,stop_s=5e-9)
            if not witness["sampling_command_on_witnessed"]:
                raise ValueError("shortened reset-track protocol lacks the measured ON witness")
            evidence.append({"raw":part["raw"],"gate_witness":witness})
    if not evidence:
        raise ValueError("verified 5 ns reset-track waveform is required")
    verified_jobs = []
    old_core = previous["child_tags"]["core"]
    for job in previous["branches"]["core"]["jobs"]:
        raw = common._verified(root,job["waveform"])
        log = root/common.BASE/old_core/(f"tt_{job['case']}_{job['variant']}.log")
        measured = core.analyze(log.read_text(),job["case"])
        core.scalar_waveform_agreement(measured["raw_measurements"],waves.read_raw(raw))
        verified_jobs.append(job["case"]+"/"+job["variant"])
    if len(verified_jobs) != 6:
        raise ValueError("all six prior core jobs required")
    routed = previous["child_tags"]["fanout"]
    route_report = previous["branches"]["fanout"]
    if check_fanout:
        frozen = json.loads((root/"build/flow2_core_bound_fanout"/routed/"inputs.json").read_text())
        for relative,digest in frozen.items():
            if common._sha(root/relative) != digest:
                raise ValueError("passed core-bound source changed: "+relative)
        route_report = fanout.audit(root,routed,guarded_routes=True)
    if route_report["status"] != "CORE_BOUND_FANOUT_PHYSICAL_PASS":
        raise ValueError("passed core-bound physical gates required")
    return previous,net,model,pins,probes,{
        "source_summary_sha256":common._sha(path), "model_smoke":model_smoke,
        "structural_native_models":structural,"reset_track_witness":evidence,
        "core_jobs_revalidated":verified_jobs,"fanout_status":route_report["status"],
        "fanout":{k:route_report[k] for k in ("sta","antenna","metrics")},
        "physical_scope":"passed core-bound external-analog top; no full ADC wrapper LVS/PEX claim"}


def verified_loads(root, reuse_tag, *, model, net, pins, probes, binary_sha, source_sha):
    """Reuse only fully measured loads, reanalyzed from their original native raw.

    A changed session launcher does not change a completed load measurement.
    Circuit, model, network, binary, source/profile and all raw proofs still
    have to agree. Never reuse an incomplete conversion as a measured result.
    """
    root = Path(root).resolve()
    common.tag_ok(reuse_tag)
    summary_path = root/common.BASE/reuse_tag/"summary.json"
    saved = json.loads(summary_path.read_text(encoding="utf-8"))
    frozen = json.loads((root/common.BASE/reuse_tag/"inputs.json").read_text(encoding="utf-8"))
    wanted = {"source":source_sha, "profile":profile.PROFILE,
              "model":common._sha(model), "network":common._sha(net), "binary":binary_sha}
    if any(frozen.get(k) != v for k,v in wanted.items()) or saved.get("profile") != profile.PROFILE:
        raise ValueError("completed load source/model/RC/binary/profile changed")
    jobs = [j for j in saved["jobs"] if j.get("task") == "load"]
    if len(jobs) != 2 or {j["case"] for j in jobs} != {"load_cm0900", "load_cm1620"}:
        raise ValueError("two unique completed load cases required")
    verified = {}
    for original in jobs:
        if original["status"] != "MEASURED_NATIVE_ADC_DIAGNOSTIC":
            raise ValueError("load is not complete: "+original["case"])
        job = copy.deepcopy(original)
        proofs = job["native_raw_segments"]
        raw_files = [common._verified(root,p) for p in proofs]
        if not raw_files:
            raise ValueError("completed load has no native raw proofs")
        folder = raw_files[-1].parents[2]
        if folder.name != job["case"] or any(p.parents[2] != folder for p in raw_files):
            raise ValueError("completed load raw case folders disagree")
        circuit = folder/"adc_circuit.spice"
        expected,_ = profile.deck(model,net,pins,probes,task="load",cm=.9 if job["case"]=="load_cm0900" else 1.62)
        expected = expected.replace(root.as_posix(), saved["execution_root"])
        if circuit.read_text(encoding="utf-8") != expected:
            raise ValueError("completed load circuit differs: "+job["case"])
        spec = json.loads((folder/"sessions/inputs.json").read_text(encoding="utf-8"))
        if (spec["circuit"]["sha256"] != common._sha(circuit) or spec["binary"]["sha256"] != wanted["binary"]
                or spec["conversion"] or any(spec["identity"].get(k) != v for k,v in wanted.items())):
            raise ValueError("completed load native spec changed")
        receipt = json.loads((raw_files[-1].parent/"receipt.json").read_text(encoding="utf-8"))
        if receipt != job["native_session"] or receipt["status"] != "NATIVE_TRAJECTORY_RETURNED" or receipt["returncode"]:
            raise ValueError("completed load receipt disagrees")
        if receipt["spec_sha256"] != common._sha(folder/"sessions/inputs.json"):
            raise ValueError("completed load spec hash differs")
        if [p["sha256"] for p in proofs] != [p["sha256"] for p in receipt["segments"]]:
            raise ValueError("completed load raw receipt differs")
        # Map the original server path into the checkout/mirror. No solver
        # binary is read from the export; only its recorded SHA is compared.
        def relative(item):
            rel = Path(item["path"].replace(saved["execution_root"]+"/", "", 1))
            return common._verified(root,dict(item,path=rel.as_posix()))
        log = relative(receipt["log"]).read_text(encoding="utf-8")
        if sessions._native_error(log) or "AUTOMX_SESSION_PHASE=RETURNED" not in log:
            raise ValueError("completed load native log is invalid")
        vectors,_ = sessions.merge([sessions._item(p) for p in raw_files],maximum_gap_s=110e-12)
        cm = .9 if job["case"]=="load_cm0900" else 1.62
        analysis = profile.analyze(vectors,probes,task="load",cm=cm)
        if analysis != job["analysis"]:
            raise ValueError("completed load raw analysis differs")
        derived = common._verified(root,job["derived_samples"])
        with np.load(derived) as old:
            if set(old.files) != set(vectors) or any(not np.array_equal(old[k],v) for k,v in vectors.items()):
                raise ValueError("completed load derived data differs from native raw")
        job["reuse"] = {"source_tag":reuse_tag,"summary_sha256":common._sha(summary_path),
                        "validation":"ORIGINAL_NATIVE_RAW_REANALYZED_WITH_IDENTICAL_CIRCUIT_MODEL_RC_BINARY_PROFILE"}
        verified[job["case"]] = job
    return verified


def _run(root, *, source_tag="readout_progress_20261018_04", tag="adc_continuous_20261019_08",
        reuse_tag=None, execute=False, load_timeout_s=3600, conversion_timeout_s=43200,
        continuous_conversion=True):
    root = Path(root).resolve()
    common.tag_ok(tag); common.tag_ok(source_tag)
    if tag in (source_tag,reuse_tag) or min(load_timeout_s,conversion_timeout_s) <= 0:
        raise ValueError("distinct tags and positive native time budgets required")
    report = {"format":"automx-cim-adc-finish-v1","tag":tag,"source_tag":source_tag,"reuse_tag":reuse_tag,
        "status":"PREPARED","profile":profile.PROFILE,"jobs":[],"completed_sims":0,"planned_sims":4,
        "execution_policy":"CONTINUOUS_SAME_PROCESS" if continuous_conversion else "REQUIRE_NATIVE_SNAPSHOT",
        "conversion_wall_budget_s":conversion_timeout_s,
        "cross_process_resume_enabled":False,
        "reused_sims":0, "newly_completed_sims":0,"planned_new_ADC_sims":2 if reuse_tag else 4,
        "planned_native_invocations":("one command probe; "+("no snapshot process; " if continuous_conversion else "three snapshot probes; ")+
            ("two reused loads; two new conversions" if reuse_tag else "two loads; two conversions")),
        "OpenLane":"REUSE_PASSED_RUN_NO_NEW_ROUTING",
        "not_signoff":"standalone ADC reset-track/2-code prototype only; conditioning, mux, reference, decoder/handshake, full wrapper LVS/PEX/STA/views, ADC transfer/noise/PVT and Stage6/8 remain"}
    if not execute:
        return report
    previous,net,model,pins,probes,source = verify_source(root,source_tag)
    tool,version = adc.runtime.select(root)
    if common._sha(Path(tool)) != previous["branches"]["adc"]["runtime"]["binary_sha256"]:
        raise ValueError("use the already validated isolated ngspice executable")
    identity = {"source":source["source_summary_sha256"],"profile":profile.PROFILE,
        "execution_policy":report["execution_policy"],
        "model":common._sha(model),"network":common._sha(net),"binary":common._sha(Path(tool)),
        "scripts":{p.name:common._sha(p) for p in (Path(__file__),Path(profile.__file__),Path(sessions.__file__))}}
    reused = verified_loads(root,reuse_tag,model=model,net=net,pins=pins,probes=probes,
                binary_sha=common._sha(Path(tool)),source_sha=source["source_summary_sha256"]) if reuse_tag else {}
    identity["reused_load_summary"] = common._sha(root/common.BASE/reuse_tag/"summary.json") if reuse_tag else None
    store = common.Store(root,tag,identity)
    report.update(source_evidence=source,ngspice_version=version,execution_root=str(root),source_child_tags=previous["child_tags"],
        child_tags=dict(previous["child_tags"],adc=tag))
    report["remaining_gates"] = previous.get("remaining_gates",{})
    source_items = [core.acq._item(root,p) for p in (net,model,root/common.BASE/source_tag/"summary.json")]
    prior_adc = previous["branches"]["adc"]
    source_items += [prior_adc["source_rc_spice"], prior_adc["pdk_model_smoke"]["log"]]
    source_items += [w["raw"] for w in source["reset_track_witness"]]
    if reuse_tag:
        source_items += [core.acq._item(root,root/common.BASE/reuse_tag/"summary.json"),
                         core.acq._item(root,root/common.BASE/reuse_tag/"inputs.json")]
        for job in reused.values():
            original_folder = (root/job["native_raw_segments"][-1]["path"]).parents[2]
            source_items.extend(closure._files(root,original_folder.relative_to(root)))
    try:
        store.note("SESSION_START; native partial ON witness verified; core-bound physical run reused")
        with (store.folder/"history.log").open("a",encoding="utf-8") as history:
            with redirect_stdout(closure._Tee(sys.stdout,history)):
                def note(message):
                    print(f"[{datetime.now(timezone.utc).isoformat()}] {message}",flush=True)
                try:
                    report["command_probe"] = sessions.script_probe(store.build/"command_probe", executable=tool)
                except Exception as error:
                    report.update(status="BLOCKED_NATIVE_COMMAND_PREFLIGHT",
                                  error=f"{type(error).__name__}: {error}")
                    note("COMMAND_PREFLIGHT_FAILED "+report["error"])
                    return report
                note("COMMAND_PREFLIGHT "+report["command_probe"]["status"])
                mode = store.build/"snapshot_mode.json"
                if continuous_conversion:
                    report["snapshot_probe"] = {"status":"DISABLED_FOR_CONTINUOUS_EXECUTION",
                        "reason":"native restore SIGSEGV observed in adc_finish_20261019_07; preserve the same running process instead",
                        "same_process_run_resume":True,"cross_process_resume":False}
                    common._save(mode,report["snapshot_probe"])
                elif mode.is_file():
                    report["snapshot_probe"] = json.loads(mode.read_text(encoding="utf-8"))
                    if report["snapshot_probe"]["status"]=="NATIVE_MOS_MIM_KLU_SNAPSHOT_PROBE_PASS":
                        report["snapshot_probe"] = sessions.probe(store.build/"snapshot_probe",executable=tool,model=model)
                else:
                    try:
                        report["snapshot_probe"] = sessions.probe(store.build/"snapshot_probe",executable=tool,model=model)
                    except Exception as error:
                        report["snapshot_probe"] = {"status":"UNAVAILABLE_CONTINUOUS_EXECUTION_ONLY","error":f"{type(error).__name__}: {error}"}
                    common._save(mode,report["snapshot_probe"])
                restore_ok = report["snapshot_probe"]["status"]=="NATIVE_MOS_MIM_KLU_SNAPSHOT_PROBE_PASS"
                report["cross_process_resume_enabled"] = restore_ok
                note("SNAPSHOT_PROBE "+report["snapshot_probe"]["status"])
                common.save_summary(store.folder/"summary.json",report)
                for name,task,cm,diff in (("load_cm0900","load",.9,.1),("load_cm1620","load",1.62,.1),
                        ("conversion_negative","conversion",.9,-.1),("conversion_positive","conversion",.9,.1)):
                    note("CASE_START "+name)
                    if name in reused:
                        report["jobs"].append(reused[name])
                        report["completed_sims"] += 1
                        report["reused_sims"] += 1
                        note("CASE_REUSED "+name+": native raw revalidated; no simulator launched")
                        common.save_summary(store.folder/"summary.json",report)
                        continue
                    item = {"case":name,"task":task,"status":"STARTED"}
                    report["jobs"].append(item)
                    if task=="conversion" and not restore_ok and not continuous_conversion:
                        item.update(status="BLOCKED_NATIVE_SNAPSHOT_PREFLIGHT",
                            error="snapshot capability did not pass; expensive conversion not launched; inspect snapshot_probe")
                        note("CASE_END "+name+": "+item["status"])
                        common.save_summary(store.folder/"summary.json",report)
                        continue
                    try:
                        if task=="conversion" and continuous_conversion:
                            note(f"CONTINUOUS_NATIVE {name}: wall budget={conversion_timeout_s}s; no snsave/snload; keep process alive")
                        folder = store.build/name
                        folder.mkdir(exist_ok=True)
                        text,names = profile.deck(model,net,pins,probes,task=task,cm=cm,diff=diff)
                        circuit = folder/"adc_circuit.spice"
                        if circuit.exists() and circuit.read_text(encoding="utf-8") != text:
                            raise FileExistsError("ADC stimulus changed; use a fresh tag")
                        if not circuit.exists():
                            circuit.write_text(text,encoding="utf-8")
                        result,vectors,proofs = sessions.case(folder/"sessions",executable=tool,circuit=circuit,
                            points=profile.points(task),names=names,identity=identity,
                            timeout_s=load_timeout_s if task=="load" else conversion_timeout_s,
                            conversion=task=="conversion",maximum_gap_s=110e-12 if task=="load" else 1.1e-9,
                            save_states=restore_ok,snapshot_stride=4)
                        item.update(native_session=result,native_raw_segments=[
                            dict(p,path=Path(p["path"]).relative_to(root).as_posix()) for p in proofs])
                        item["native_observed_raw_segments"] = [dict(p,path=Path(p["path"]).relative_to(root).as_posix())
                            for p in result.get("observed_segments",[])]
                        if result["status"] != "NATIVE_TRAJECTORY_RETURNED":
                            item["status"] = ("INCOMPLETE_CONTINUOUS_CONVERSION" if continuous_conversion and task=="conversion"
                                              else "PENDING_NATIVE_CONTINUATION")
                            if continuous_conversion:
                                item["restart_policy"] = "same native process was stopped; no cross-process state restore; a retry starts this incomplete case from zero"
                        else:
                            analysis = profile.analyze(vectors,probes,task=task,cm=cm,diff=diff)
                            item.update(status="MEASURED_NATIVE_ADC_DIAGNOSTIC",analysis=analysis)
                            derived = folder/"merged_native_samples.npz"
                            if derived.exists():
                                with np.load(derived) as prior:
                                    if set(prior.files) != set(vectors) or any(not np.array_equal(prior[k],v) for k,v in vectors.items()):
                                        raise FileExistsError("derived native data changed")
                            else:
                                np.savez_compressed(derived,**vectors)
                            item["derived_samples"] = core.acq._item(root,derived)
                            report["completed_sims"] += 1
                            report["newly_completed_sims"] += 1
                    except KeyboardInterrupt:
                        item["status"]="INTERRUPTED"
                        raise
                    except Exception as error:
                        item.update(status="BLOCKED_NATIVE_CASE",error=f"{type(error).__name__}: {error}")
                    note("CASE_END "+name+": "+item["status"])
                    common.save_summary(store.folder/"summary.json",report)
        measured = {j["case"]:j for j in report["jobs"] if j["status"]=="MEASURED_NATIVE_ADC_DIAGNOSTIC"}
        if report["completed_sims"] == 4:
            a = measured["conversion_negative"]["analysis"]["result_code_12bit"]
            b = measured["conversion_positive"]["analysis"]["result_code_12bit"]
            if a == b:
                report.update(status="BLOCKED_IDENTICAL_CONVERSION_CODES",opposite_input_codes=[a,b])
            else:
                report.update(status="MEASURED_STANDALONE_ADC_PROTOTYPE",opposite_input_codes=[a,b])
        else:
            report["status"]="COMPLETED_WITH_PENDING_NATIVE_CASES"
    except KeyboardInterrupt:
        report["status"]=("INTERRUPTED_NO_CROSS_PROCESS_RESUME" if continuous_conversion
                          else "INTERRUPTED_RESUMABLE_IF_NATIVE_SNAPSHOT_VALID")
        raise
    finally:
        # Preserve core/raw and passed physical source reports in the one
        # export. Only native ADC sessions are new, no full OpenLane rerun.
        for k in ("core","fanout","adc_drc","acquisition"):
            child=previous["child_tags"][k]
            for base in (common.BASE,common.BUILD,common.PHYSICAL):
                source_items.extend(closure._files(root,base/child))
            if k=="fanout":
                run_dir = fanout.core.DESIGN/"runs"/child
                for part in ("reports","logs","results/final"):
                    source_items.extend(closure._files(root,run_dir/part))
        common.save_summary(store.folder/"summary.json",report)
        store.note("SESSION_END "+report["status"])
        destination=common.bundle(root,tag,source_items)
        print("Download folder: "+str(destination.parent),flush=True)
    return report


def run(root, *, source_tag="readout_progress_20261018_04", tag="adc_continuous_20261019_08",
        reuse_tag=None, execute=False, load_timeout_s=3600, conversion_timeout_s=43200,
        continuous_conversion=True):
    args=dict(source_tag=source_tag,tag=tag,reuse_tag=reuse_tag,execute=execute,
        load_timeout_s=load_timeout_s,conversion_timeout_s=conversion_timeout_s,
        continuous_conversion=continuous_conversion)
    if not execute:
        return _run(root,**args)
    common.tag_ok(tag)
    folder=Path(root).resolve()/common.BASE/tag
    folder.mkdir(parents=True,exist_ok=True)
    # Ubuntu releases flock automatically on normal exit, Ctrl-C or process
    # death. A second invocation must not resume a still-running native case.
    with (folder/"runner.lock").open("a+") as lock:
        if os.name=="posix":
            import fcntl
            try:
                fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
            except BlockingIOError as error:
                raise RuntimeError("this ADC campaign is already running; follow its history.log") from error
        return _run(root,**args)


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root",type=Path,default=ROOT)
    p.add_argument("--source-tag",default="readout_progress_20261018_04")
    p.add_argument("--tag",default="adc_continuous_20261019_08")
    p.add_argument("--reuse-tag",help="revalidate and reuse both completed native load measurements")
    p.add_argument("--run",action="store_true")
    p.add_argument("--load-timeout-s",type=int,default=3600)
    p.add_argument("--conversion-timeout-s",type=int,default=43200)
    policy=p.add_mutually_exclusive_group()
    policy.add_argument("--continuous-conversion",dest="continuous_conversion",action="store_true",default=True,
                        help="default: one uninterrupted native process per conversion; no snapshot restore")
    policy.add_argument("--require-snapshot",dest="continuous_conversion",action="store_false",
                        help="experimental diagnostic only: require native snapshot capability before conversions")
    args=p.parse_args()
    r=run(args.root,source_tag=args.source_tag,tag=args.tag,reuse_tag=args.reuse_tag,execute=args.run,
        load_timeout_s=args.load_timeout_s,conversion_timeout_s=args.conversion_timeout_s,
        continuous_conversion=args.continuous_conversion)
    print(json.dumps(r,indent=2))
    if args.run and r["status"]!="MEASURED_STANDALONE_ADC_PROTOTYPE":
        raise SystemExit(1)
