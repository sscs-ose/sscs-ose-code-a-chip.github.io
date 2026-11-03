#!/usr/bin/env python3
"""Full active ADC probes without a nonlinear observation source in the solver.

Preserves the pinned ADC and its exactly reduced passive R network. Sampler
state is evaluated from aligned saved waveforms. Two input-load probes run
first; two real, clocked conversion probes follow when execution succeeds.
This standalone ADC is still driven by ideal supplies/VCM/input sources.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import re
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import run_flow2_adc_input_recovery as recovery
from scripts import flow2_waveforms as waves
from scripts import flow2_adc_runtime as runtime
from scripts import flow2_adc_dc as dc
from scripts import flow2_adc_models as native_models
from scripts import flow2_adc_startup as startup
from scripts import flow2_adc_progress as progress
from scripts import reduce_flow2_adc_capacitors as cap_reduction
from automx_cim.spice import parse_measurements

common, original, live = recovery.common, recovery.original, recovery.live
CFG1, CFG2 = 0x0400, 0x8421  # no AVG/OSR; explicit 5ns edge/delay blocks


def _nodes(pins, cfg1=0, cfg2=0):
    mapping = {"VDD": "VPWR", "VSS": "0", "rst_n": "RST_N",
        "start_conversion_in": "START", "clk_vcm": "CLK_VCM",
        "inp_analog": "AINP", "inn_analog": "AINN", "vcm": "VCM",
        "clk_dig": "ADC_CLK_DIG", "clk_comp": "ADC_CLK_COMP", "clk_ena": "ADC_CLK_ENA",
        "conversion_finished_out": "EOC", "conversion_finished_osr_out": "EOC_OSR"}
    for i in range(16):
        mapping[f"result_out[{i}]"] = f"RESULT_{i}"
        mapping[f"config_1_in[{i}]"] = "VPWR" if cfg1 & (1 << i) else "0"
        mapping[f"config_2_in[{i}]"] = "VPWR" if cfg2 & (1 << i) else "0"
    return [mapping[p] if p in mapping else f"ADC_PRIVATE_{i}" for i, p in enumerate(pins)]


def deck(model: Path, rc: Path, pins: list[str], probes: dict, *, task: str, cm=.9, diff=.1):
    if task not in ("load", "conversion") or not all(math.isfinite(v) for v in (cm, diff)):
        raise ValueError("invalid ADC task or stimulus")
    if task == "load":
        # Preserve the historical input/reset/start/config stimulus. Only
        # remove the nonphysical BSTATE witness and save its gate vectors.
        lines = original.deck(model, rc, pins, probes, cm).splitlines()
        lines = [l for l in lines if not l.startswith(("BSTATE ", ".measure tran sampling_command_margin_v", ".save ", ".end"))]
        saved = ["v(AINP)", "v(AINN)", "i(VINP)", "i(VINN)", "i(VVDD)"]
    else:
        if abs(diff) > .2 or cm-abs(diff)/2 < 0 or cm+abs(diff)/2 > 1.8:
            raise ValueError("conversion input is outside the selected diagnostic range")
        lines = [f".title complete ADC RC conversion differential={diff:g} V",
            f'.lib "{model.as_posix()}" tt', f'.include "{rc.as_posix()}"',
            ".temp 25", ".option method=gear reltol=1e-4 abstol=1e-13",
            "VVDD VPWR 0 1.8", "VVCM VCM 0 .9", "VCLK CLK_VCM 0 0",
            "VRST RST_N 0 PWL(0 0 100n 0 100.1n 1.8 3u 1.8)",
            "VSTART START 0 PWL(0 0 200n 0 200.1n 1.8 250n 1.8 250.1n 0 3u 0)",
            f"VINP AINP 0 {cm+diff/2:.12g}", f"VINN AINN 0 {cm-diff/2:.12g}",
            f"XADC {' '.join(_nodes(pins, CFG1, CFG2))} adc_top_postlayout", ".tran 1n 3u 0 .5n"]
        saved = ["v(AINP)", "v(AINN)", "v(RST_N)", "v(START)", "v(EOC)", "v(EOC_OSR)"]
        saved += [f"v(RESULT_{i})" for i in range(16)]
        # These are RC subcircuit ports, so SPICE maps them to the parent
        # node names. v(xadc.clk_dig) would reference a nonexistent alias.
        saved += [f"v(ADC_{p.upper()})" for p in ("clk_dig", "clk_comp", "clk_ena")]
    saved += [f"v(xadc.{d['gate']})" for group in probes["input_switches"].values() for d in group]
    lines += [".save " + " ".join(saved), waves.control_block(saved, filename="adc.raw", phase="ADC"), ".end", ""]
    if any(re.match(r"(?i)^\s*B\w+", l) for l in lines):
        raise ValueError("no behavioral observation source may enter the ADC solver")
    return "\n".join(lines)


def analyze_load(log, vectors, probes, cm):
    if vectors["time"][0] > 0 or vectors["time"][-1] < 29.99e-9:
        raise ValueError("incomplete input-load transient")
    keys = (*original.MEASURES, *(f"gate_{side}_{i}_{'n' if '__nfet_' in d['primitive'] else 'p'}"
        for side, group in probes["input_switches"].items() for i, d in enumerate(group)))
    if re.search(r"(?im)^\s*(error\b|fatal\b)", log):
        raise ValueError("ADC log contains simulator/measurement errors")
    values = parse_measurements(log, keys)
    if set(values) != set(keys) or not all(math.isfinite(v) for v in values.values()):
        raise ValueError("incomplete ADC scalar measurements")
    for side, sign in (("p", -1), ("n", 1)):
        expected = cm+sign*.001+original.INPUT_STEP_V
        if abs(values[f"input_{side}_v"]-expected) > 1e-5 or abs(waves.sample(vectors, f"v(AIN{side})", 20e-9)-expected) > 1e-5:
            raise ValueError("ADC scalar/waveform stimulus validation failed")
    witness = waves.sampling_witness(vectors, probes)
    return {"raw_measurements": values, "input_common_mode_v": cm, "gate_witness": witness,
        "sampling_command_on_witnessed": witness["sampling_command_on_witnessed"],
        "charge_per_input_c": {s: values[f"charge_{s}_c"] for s in ("p", "n")},
        "apparent_charge_over_step_ff": {s: abs(values[f"charge_{s}_c"])/original.INPUT_STEP_V*1e15 for s in ("p", "n")},
        "differential_charge_over_reference_hold_cap_v": (values["charge_n_c"]-values["charge_p_c"])/(original.REFERENCE_HOLD_FF*1e-15),
        "interpretation": "driven-input charge, including kickback; not deembedded input capacitance or actual held-node droop"}


def analyze_conversion(v, diff, *, minimum_stop_s=2.99e-6, input_sample_s=150e-9,
        reset_sample_s=150e-9, start_sample_s=220e-9, before_start_s=180e-9,
        start_s=200e-9, complete_after_s=205e-9, cm=.9):
    time = v["time"]
    if time[0] > 0 or time[-1] < minimum_stop_s:
        raise ValueError("incomplete conversion transient")
    for key, expected in (("v(AINP)", cm+diff/2), ("v(AINN)", cm-diff/2)):
        if abs(waves.sample(v, key, input_sample_s)-expected) > 1e-5:
            raise ValueError("conversion input does not match the frozen stimulus")
    if waves.sample(v, "v(START)", start_sample_s) < 1.62 or waves.sample(v, "v(RST_N)", reset_sample_s) < 1.62:
        raise ValueError("conversion reset/start stimulus failed")
    if waves.sample(v, "v(EOC_OSR)", before_start_s) > .18:
        raise ValueError("EOC was already high before conversion start")
    eoc = v["v(eoc_osr)"]
    candidates = np.flatnonzero((time[1:] > complete_after_s) & (eoc[:-1] < .9) & (eoc[1:] >= .9)) + 1
    if not len(candidates):
        raise ValueError("no new completed-conversion edge after start")
    # A fresh event plus a stable post-event word is needed; neither a reset
    # value nor a static DC completion flag constitutes a conversion.
    edge = float(time[int(candidates[0])])
    mask = (time >= edge+10e-9) & (time <= edge+30e-9)
    if np.count_nonzero(mask) < 2 or edge+30e-9 > time[-1]:
        raise ValueError("missing post-conversion stability interval")
    word = 0
    for bit in range(16):
        value = v[f"v(result_{bit})"][mask]
        low, high = bool(np.all(value <= .18)), bool(np.all(value >= 1.62))
        if not (low or high):
            raise ValueError("ADC result is unstable or between logic rails")
        if high:
            word |= 1 << bit
    if word & 15:
        raise ValueError("no-OSR configuration must leave the low four result bits zero")
    clock = v["v(adc_clk_dig)"][(time >= start_s) & (time <= edge)]
    if not len(clock) or np.min(clock) > .18 or np.max(clock) < 1.62:
        raise ValueError("no clock activity observed during conversion")
    return {"differential_input_v": diff, "conversion_finished_time_s": edge,
        "start_to_finished_s": edge-start_s, "result_word_16bit": word,
        "result_code_12bit": word >> 4, "fresh_completion_and_stable_code": True,
        "conversion_gate": "TWO_LEVEL_SMOKE_ONLY_NOT_ADC_TRANSFER_OR_NOISE_SIGNOFF"}


def run(root: Path, *, pdk_root=recovery.DEFAULT_PDK, tag="adc_waveform_20261018_01",
        execute=False, timeout_s=900, conversions=True, dc_recovery=False,
        powerup=False, model_reference=None, progress_profile=False):
    root, pdk = Path(root).resolve(), Path(pdk_root).expanduser().resolve()
    common.tag_ok(tag)
    if timeout_s <= 0:
        raise ValueError("positive timeout required")
    if powerup and not dc_recovery:
        raise ValueError("powerup profile requires the verified native-model DC recovery")
    if progress_profile and not powerup:
        raise ValueError("progress profile requires observable startup and native-model DC recovery")
    report = {"format": "automx-cim-flow2-adc-waveform-v1", "tag": tag, "status": "PREPARED",
        "planned_sims": 4 if conversions else 2, "completed_sims": 0, "jobs": [],
        "configuration": {"conversion_cfg1": CFG1, "conversion_cfg2": CFG2,
            "conversion_stop_s": 3e-6, "source": "pinned GL config wiring plus upstream doc/Interface.md"},
        "not_signoff": "full active standalone ADC; ideal driven inputs, external VCM/supplies; no physical conditioning, held-node loading, composite LVS, full transfer/noise/PVT or wrapper views"}
    store, items = None, []
    try:
        paths = {key: root/relative for key, relative in original.adc.FILES.items()}
        if any(not p.is_file() or common._sha(p) != original.adc.EXPECTED_SHA256[k] for k, p in paths.items()):
            raise ValueError("pinned ADC source is missing or changed")
        rc = paths["rc_spice"]
        items = [original.acq._item(root, p) for p in paths.values()]
        model = pdk/"libs.tech/ngspice/sky130.lib.spice"
        if not model.is_file():
            raise ValueError("native SKY130 models and host ngspice are required")
        tool, version = runtime.select(root)
        if dc_recovery and runtime.major_version(version) < 43:
            raise ValueError("the DC recovery profile requires ngspice >=43 with KLU; isolated 44.2 is preferred")
        pins, probes = original.adc._spice_pins(rc), original.input_switches(rc)
        text, reduction = recovery.reducer.reduce_text(rc.read_bytes().decode("utf-8"))
        resistors = None
        if dc_recovery:
            resistors = dc.modelled_resistors(text)
            gates = [d["gate"] for group in probes["input_switches"].values() for d in group]
            text, cr = cap_reduction.reduce_text(text, protected=gates)
            report["floating_capacitor_reduction"] = cr
        report["reduction"] = reduction
        report["source_rc_spice"] = original.acq._item(root, rc)
        report["ngspice_version"] = version
        report["runtime"] = {"executable": tool, "binary_sha256": common._sha(Path(tool)),
                             "mode": "HS_BEFORE_SOURCE_NO_USER_INIT_V2"}
        identity = {"inputs": items, "model": common._sha(model), "ngspice": report["ngspice_version"],
                    "equivalent_sha256": reduction["equivalent_sha256"], "mode": "NONLOADING_ASCII_WAVEFORM_V2",
                    "runtime": report["runtime"], "driver": runtime.driver()}
        driver = runtime.recovery_driver(fast_skywater=powerup) if dc_recovery else runtime.driver()
        net_sha = reduction["equivalent_sha256"]
        if dc_recovery:
            net_sha = report["floating_capacitor_reduction"]["equivalent_sha256"]
            report["runtime"]["mode"] = "HSA_KLU_ZERO_FREE_CHARGE_C_NETWORK_V3"
            report["not_signoff"] += "; unobserved capacitor-only nodes eliminated under zero free charge; no IC, UIC, DC shunts or ideal ADC"
            identity.update(mode="NONLOADING_ASCII_WAVEFORM_DC_RECOVERY_V3", driver=driver,
                derived_RC_sha256=net_sha,
                initial_free_charge="zero on unobserved capacitor-only conductors")
            compiled_model, model_overlay = native_models.compile_tt(pdk)
            report["native_model_overlay"] = model_overlay
            report["runtime"]["mode"] = "HSA_KLU_ZERO_FREE_CHARGE_NATIVE_DW_BRACED_V4"
            identity.update(mode="NONLOADING_ASCII_WAVEFORM_NATIVE_MODELS_V4",
                            native_model_overlay=model_overlay)
            if powerup:
                report["startup_parser_validation"] = startup.validate_four_terminal_mos(text, compiled_model)
                identity.update(mode="OBSERVABLE_ZERO_SUPPLY_STARTUP_V5",
                    power_ramp_s=startup.RAMP_S, load_time_shift_s=startup.SHIFT_S,
                    model_reference=model_reference)
                report["runtime"]["mode"] = "HSA_KLU_SKYWATER_ZERO_SUPPLY_STARTUP_V5"
                report["not_signoff"] += "; explicit supply/reference/input power ramp and reset hold; not historical static-bias stimulus"
                if progress_profile:
                    identity.update(mode="OBSERVABLE_FAST_STARTUP_CHECKPOINTS_V6", progress_profile=progress.PROFILE,
                        power_ramp_s=progress.PROFILE["ramp_s"], load_time_shift_s=progress.PROFILE["load_shift_s"])
                    report["runtime"]["mode"] = "HSA_KLU_SKYWATER_FAST_STARTUP_CHECKPOINTS_V6"
                    report["progress_profile"] = progress.PROFILE
        if not execute:
            return report
        store = common.Store(root, tag, identity)
        net = store.build/("adc_top.dc_recovery.spice" if dc_recovery else "adc_top.equivalent_r.spice")
        if net.is_file() and common._sha(net) != net_sha:
            raise FileExistsError("derived ADC netlist changed; use a new tag")
        if not net.is_file():
            net.write_bytes(text.encode("utf-8"))
        report["equivalent_rc_spice"] = original.acq._item(root, net)
        common._save(store.folder/"resistor_reduction.json", reduction)
        if dc_recovery:
            # Export the actual transitive model definition, not a filename
            # search that missed sky130_fd_pr__model__r+c.model.spice.
            capture = {"libs.tech/ngspice/sky130.lib.spice"}
            capture.update(f["path"] for f in model_overlay["syntax_corrections"])
            for relative in sorted(capture):
                path = pdk/relative
                target = store.build/"model_evidence"/relative
                target.parent.mkdir(parents=True, exist_ok=True)
                data = path.read_bytes()
                if target.is_file() and target.read_bytes() != data:
                    raise FileExistsError("copied PDK model evidence changed; use a fresh tag")
                if not target.is_file():
                    target.write_bytes(data)
            model = store.build/"pdk_models/sky130_tt.lib.spice"
            model.parent.mkdir(parents=True, exist_ok=True)
            if model.is_file() and model.read_bytes() != compiled_model.encode("utf-8"):
                raise FileExistsError("derived native TT model changed; use a fresh tag")
            if not model.is_file():
                model.write_bytes(compiled_model.encode("utf-8"))
            report["derived_native_model"] = original.acq._item(root, model)
            common._save(store.folder/"native_model_overlay.json", model_overlay)
            common._save(store.folder/"floating_capacitor_reduction.json", report["floating_capacitor_reduction"])
            source = dc.model_deck(model, resistors)
            command = [tool, "-n", "-b", "runtime.spice"]
            model_driver = runtime.recovery_driver("model_smoke.spice", fast_skywater=powerup)
            def simulate_model(work):
                (work/"model_smoke.spice").write_text(source, encoding="utf-8")
                (work/"runtime.spice").write_text(model_driver, encoding="utf-8")
                return live.run(command, work, min(timeout_s, 300))
            mr, mw = store.step("pdk_model_smoke", command, tcl=model_driver+source, executor=simulate_model)
            if mr.returncode:
                raise RuntimeError(f"PDK-model smoke exited {mr.returncode}; full ADC probes were not launched")
            report["pdk_model_smoke"] = dc.analyze_model(mr.stdout+mr.stderr)
            if powerup and model_reference is not None:
                if model_reference["model_sha256"] != model_overlay["derived_sha256"]:
                    raise ValueError("startup reference native model hash changed")
                startup.compare_model_reference(report["pdk_model_smoke"], model_reference["smoke"])
                report["pdk_model_smoke"]["reference_comparison"] = "MATCH_PREVIOUS_NATIVE_MODEL_SMOKE"
            report["pdk_model_smoke"]["log"] = original.acq._item(root, store.folder/"pdk_model_smoke.log")
            common.save_summary(store.folder/"summary.json", report)
        jobs = [("load_cm0900", "load", .9, .1), ("load_cm1620", "load", 1.62, .1)]
        if conversions:
            jobs += [("conversion_negative", "conversion", .9, -.1), ("conversion_positive", "conversion", .9, .1)]
        for name, task, cm, diff in jobs:
            content = deck(model, net, pins, probes, task=task, cm=cm, diff=diff)
            if dc_recovery:
                content = content.replace(".option method=gear", ".option klu method=gear", 1)
            if powerup:
                content = startup.deck(content, task=task, cm=cm, diff=diff,
                    **(progress.startup_options() if progress_profile else {}))
            if progress_profile:
                content = progress.checkpoint_deck(content, task=task)
            command = [tool, "-n", "-b", "runtime.spice"]
            def simulate(work, source=content):
                (work/"adc.spice").write_text(source, encoding="utf-8")
                (work/"runtime.spice").write_text(driver, encoding="utf-8")
                return live.run(command, work, timeout_s)
            result, work = store.step(name, command, tcl=driver+content, executor=simulate)
            entry = {"case": name, "task": task, "returncode": result.returncode}
            report["jobs"].append(entry)
            log = result.stdout+result.stderr
            entry["observed_phases"] = re.findall(r"AUTOMX_ADC_PHASE=(\w+)", log)
            elapsed = re.search(r"AUTOMX_ADC_PHASE=DECK_PARSED.*?Total elapsed time \(seconds\)\s*=\s*([\d.]+)", log, re.S)
            entry["elapsed_at_DECK_PARSED_s"] = float(elapsed[1]) if elapsed else None
            entry["dynamic_gmin_observed"] = "Starting dynamic gmin stepping" in log
            entry["progress"] = progress.observe(log, work)
            for partial in entry["progress"]["checkpoints"]:
                partial["raw"] = original.acq._item(root, work/partial["filename"])
            if result.returncode:
                raise RuntimeError(f"ADC exited {result.returncode} at {name}; phases={entry['observed_phases']}")
            if dc_recovery:
                dc.require_klu(log)
            if "RAW_WRITTEN" not in entry["observed_phases"] or re.search(r"(?im)^\s*(error\b|fatal\b)", log):
                raise ValueError("ADC raw write failed or simulator error occurred")
            vectors = waves.read_raw(work/"adc.raw")
            if powerup:
                options = {k: progress.PROFILE[k] for k in ("ramp_s", "load_shift_s")} if progress_profile else {}
                entry["startup"] = startup.validate(vectors, task=task, **options)
            if progress_profile and vectors["time"][-1] < progress.PROFILE[task+"_stop_s"]*(1-1e-6):
                raise ValueError("checkpoint pause is not a completed ADC transient")
            entry["raw_waveform"] = original.acq._item(root, work/"adc.raw")
            if dc_recovery and task == "load":
                log, selected = waves.completed_run_log(log, phase="ADC")
                entry["measurement_log_selection"] = selected
            shift = progress.PROFILE["load_shift_s"] if progress_profile else startup.SHIFT_S
            analysis_vectors = ({**vectors, "time": vectors["time"]-shift}
                                if powerup and task == "load" else vectors)
            entry.update(analyze_load(log, analysis_vectors, probes, cm) if task == "load" else analyze_conversion(vectors, diff))
            if powerup and task == "load":
                entry["gate_witness"]["window_s"] = [t+shift for t in entry["gate_witness"]["window_s"]]
                entry["gate_witness"]["witness_time_s"] += shift
            report["completed_sims"] += 1
            common.save_summary(store.folder/"summary.json", report)
        conversion_jobs = [j for j in report["jobs"] if j["task"] == "conversion"]
        if conversion_jobs:
            if conversion_jobs[0]["result_code_12bit"] == conversion_jobs[1]["result_code_12bit"]:
                raise ValueError("opposite ADC inputs produced the same code")
            report["conversion_gate"] = "TWO_DIFFERENTIAL_CODES_WITH_FRESH_COMPLETION_NOT_FULL_TRANSFER"
        else:
            report["conversion_gate"] = "NOT_REQUESTED"
        report["active_input_load_gate"] = ("ON_COMMAND_OBSERVED" if all(j["sampling_command_on_witnessed"] for j in report["jobs"] if j["task"] == "load") else "PENDING_ACTIVE_SAMPLING_WINDOW")
        report["status"] = "MEASURED_ADC_WAVEFORM_PROTOTYPE"
    except FileExistsError:
        raise
    except (Exception, KeyboardInterrupt) as error:
        report["status"] = "INTERRUPTED" if isinstance(error, KeyboardInterrupt) else "BLOCKED_ADC_WAVEFORM"
        report["error"] = f"{type(error).__name__}: {error}"
        if isinstance(error, KeyboardInterrupt):
            raise
    finally:
        if execute and sys.exc_info()[0] is not FileExistsError:
            if store:
                store.note(f"END {report['status']}: {report['completed_sims']}/{report['planned_sims']}")
            common.save_summary(root/common.BASE/tag/"summary.json", report)
            common.bundle(root, tag, items)
    return report


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", type=Path, default=ROOT)
    p.add_argument("--pdk-root", type=Path, default=recovery.DEFAULT_PDK)
    p.add_argument("--tag", default="adc_waveform_20261018_01")
    p.add_argument("--run", action="store_true")
    p.add_argument("--load-only", action="store_true")
    p.add_argument("--dc-recovery", action="store_true", help="KLU/hsa and equivalent floating-capacitor elimination, with PDK-model smoke first")
    p.add_argument("--powerup", action="store_true", help="zero-supply startup, explicit 20ns source ramps and reset hold; implies --dc-recovery")
    p.add_argument("--progress-profile", action="store_true", help="distinct 0.5ns source ramp, shorter load reset hold and same-trajectory partial raw checkpoints; implies --powerup")
    p.add_argument("--timeout-s", type=int, default=900)
    a = p.parse_args()
    result = run(a.root, pdk_root=a.pdk_root, tag=a.tag, execute=a.run, timeout_s=a.timeout_s,
                 conversions=not a.load_only, dc_recovery=a.dc_recovery or a.powerup or a.progress_profile,
                 powerup=a.powerup or a.progress_profile, progress_profile=a.progress_profile)
    print(json.dumps(result, indent=2))
    if a.run and result["status"] != "MEASURED_ADC_WAVEFORM_PROTOTYPE":
        raise SystemExit(1)
