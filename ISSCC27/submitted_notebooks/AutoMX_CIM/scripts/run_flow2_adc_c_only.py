#!/usr/bin/env python3
"""Two real transistor conversions with contracted wire R; separate from RC signoff."""
from __future__ import annotations
import argparse
from contextlib import redirect_stdout
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import run_flow2_adc_finish as finish
from scripts import flow2_adc_c_only as reduction

common, profile, sessions = finish.common, finish.profile, finish.sessions


def run(root, *, source_tag="readout_progress_20261018_04", tag="wrapper_adc_c_20261020_01",
        execute=False, timeout_s=1800):
    root = Path(root).resolve()
    common.tag_ok(tag)
    if timeout_s <= 0 or tag == source_tag:
        raise ValueError("positive timeout and independent tag required")
    report = {"format": "automx-cim-adc-c-only-prototype-v1", "tag": tag, "status": "PREPARED",
        "jobs": [], "planned_sims": 2, "completed_sims": 0,
        "evidence_scope": "transistor functional two-code test, numeric wire R contracted",
        "not_signoff": "no distributed-R timing, loaded wrapper, full transfer, noise or PVT acceptance"}
    if not execute:
        return report
    previous, net, model, pins, _, source = finish.verify_source(root, source_tag, check_fanout=False)
    tool, version = finish.adc.runtime.select(root)
    if common._sha(Path(tool)) != previous["branches"]["adc"]["runtime"]["binary_sha256"]:
        raise ValueError("use the previously validated isolated native ngspice")
    identity = {"algorithm": reduction.ALGORITHM, "network": common._sha(net), "model": common._sha(model),
        "binary": common._sha(Path(tool)), "source_summary": source["source_summary_sha256"],
        "profile": profile.PROFILE, "runner": common._sha(Path(__file__)),
        "reducer": common._sha(Path(reduction.__file__))}
    store = common.Store(root, tag, identity)
    report["ngspice_version"] = version
    inputs = [finish.core.acq._item(root, p) for p in (net, model, root/common.BASE/source_tag/"summary.json")]
    report['sources']=inputs
    try:
        with (store.folder/"history.log").open("a", encoding="utf-8") as history:
            with redirect_stdout(finish.closure._Tee(sys.stdout, history)):
                store.note("START ADC C-only prototype; all functional MOS/MIM/resistors retained")
                target = store.build/"adc_top.c_only.spice"
                proof = reduction.prepare(net, target)
                aliases = proof.pop("node_aliases")
                common._save(store.build/"wire_aliases.json", aliases)
                common._save(store.folder/"reduction.json", proof)
                report["reduction"] = proof
                probe = sessions.script_probe(store.build/"command_probe", executable=tool, timeout_s=30)
                report["command_probe"] = probe
                for name, diff in (("negative", -.1), ("positive", .1)):
                    store.note("CASE_START " + name)
                    folder = store.build/name
                    folder.mkdir(exist_ok=True)
                    # No removed wire-node probes: acceptance uses real parent ports.
                    text, names = profile.deck(model, target, pins, {"input_switches": {}},
                                               task="conversion", cm=.9, diff=diff)
                    circuit = folder/"circuit.spice"
                    if circuit.exists() and circuit.read_text(encoding="utf-8") != text:
                        raise FileExistsError("C-only deck changed; use a new tag")
                    if not circuit.exists():
                        circuit.write_text(text, encoding="utf-8")
                    item = {"case": name, "differential_input_v": diff, "status": "STARTED"}
                    report["jobs"].append(item)
                    result, vectors, proofs = sessions.case(folder/"sessions", executable=tool, circuit=circuit,
                        points=profile.points("conversion"), names=names, identity=identity, timeout_s=timeout_s,
                        conversion=True, maximum_gap_s=1.1e-9, save_states=False)
                    item.update(native_session=result, raw_segments=proofs)
                    if result["status"] != "NATIVE_TRAJECTORY_RETURNED":
                        item["status"] = "INCOMPLETE_C_ONLY_CONVERSION"
                    else:
                        try:
                            item["analysis"] = profile.analyze(vectors, {}, task="conversion", cm=.9, diff=diff)
                            item["status"] = "REAL_EOC_AND_STABLE_WORD"
                            report["completed_sims"] += 1
                        except ValueError as error:
                            item.update(status="BLOCKED_CONVERSION_ACCEPTANCE", error=str(error))
                    store.note("CASE_END " + name + ": " + item["status"])
                    common.save_summary(store.folder/"summary.json", report)
                    # Resolve the first unsuccessful trajectory before spending
                    # another full budget on a second equally unproven case.
                    if item["status"] != "REAL_EOC_AND_STABLE_WORD":
                        break
                if report["completed_sims"] == 2:
                    codes = [j["analysis"]["result_code_12bit"] for j in report["jobs"]]
                    report["opposite_input_codes"] = codes
                    report["status"] = ("MEASURED_ADC_C_ONLY_TWO_CODE_PROTOTYPE" if codes[0] != codes[1]
                                        else "BLOCKED_IDENTICAL_CODES")
                else:
                    report["status"] = "PENDING_C_ONLY_ADC_EVIDENCE"
    except FileExistsError:
        raise
    except KeyboardInterrupt:
        report["status"] = "INTERRUPTED_INCOMPLETE_CASE_RESTARTS_FROM_ZERO"
        raise
    except Exception as error:
        report.update(status="BLOCKED_C_ONLY_ADC", error=f"{type(error).__name__}: {error}")
    finally:
        if sys.exc_info()[0] is not FileExistsError:
            common.save_summary(store.folder/"summary.json", report)
            store.note("END " + report["status"])
            common.bundle(root, tag, inputs)
    return report


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", type=Path, default=ROOT)
    p.add_argument("--source-tag", default="readout_progress_20261018_04")
    p.add_argument("--tag", default="wrapper_adc_c_20261020_01")
    p.add_argument("--run", action="store_true")
    p.add_argument("--timeout-s", type=int, default=1800)
    a = p.parse_args()
    r = run(a.root, source_tag=a.source_tag, tag=a.tag, execute=a.run, timeout_s=a.timeout_s)
    print(json.dumps(r, indent=2))
    if a.run and r["status"] != "MEASURED_ADC_C_ONLY_TWO_CODE_PROTOTYPE":
        raise SystemExit(1)
