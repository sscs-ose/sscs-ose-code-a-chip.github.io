"""Which public testbench to re-run for each showcase circuit, and what to report.

Every entry runs one of the task's own public development benches at the
nominal corner. The complete hidden PVT / mismatch signoff is not re-run here;
its recorded verdicts are shown next to these numbers.
"""
from __future__ import annotations

import re
from pathlib import Path

from . import sim

# (scalar, label, scale, unit)
M = tuple


def _vco(sc: dict[str, float]) -> dict[str, float]:
    f = [sc[f"p{i}_freq"] for i in range(1, 5) if f"p{i}_freq" in sc]
    s = [sc[f"p{i}_swing"] for i in range(1, 5) if f"p{i}_swing" in sc]
    return {"f_ctrl_0v": f[0], "f_ctrl_1v8": f[-1], "tuning_ratio": f[0] / f[-1], "min_swing": min(s)}


def _ldo_line(path: Path) -> None:
    text = path.read_text()
    control = (".control\nrun\nmeas dc vout_162 find v(vout) at=1.62\nmeas dc vout_180 find v(vout) at=1.80\n"
               "meas dc vout_198 find v(vout) at=1.98\nlet line_reg = (vout_198 - vout_162) / 0.36\n"
               "print vout_162 vout_180 vout_198 line_reg\n.endc\n")
    path.write_text(re.sub(r"(?m)^\.end\s*$", control + ".end", text, count=1))


SHOWCASE = {
    "sky130-two-stage-miller-opamp-gain60-ugb200-pm60-noise50uv-pvt": dict(
        title="Two-stage Miller op amp (textbook anchor)", bench="tb_ac_tt.spi", metrics=[
            M(("dc_gain_db", "DC open-loop gain", 1, "dB")), M(("ugb_hz", "Unity-gain bandwidth", 1e-6, "MHz")),
            M(("phase_margin_deg", "Phase margin", 1, "deg")), M(("power_w", "Power", 1e3, "mW")),
            M(("output_common_mode_error_v", "Output bias error", 1e3, "mV"))]),
    "sky130-complementary-folded-cascode-ab-opamp-pvt": dict(
        title="Rail-to-rail class-AB op amp", bench="tb_ac_tt.spi", metrics=[
            M(("gain_10hz_db", "Open-loop gain at 10 Hz", 1, "dB")), M(("ugbw_hz", "Unity-gain bandwidth", 1e-6, "MHz")),
            M(("phase_margin_deg", "Phase margin", 1, "deg")), M(("static_power_w", "Static power", 1e3, "mW"))]),
    "sky130-fd-sampling-feedback-ota-gain8-settling10ns-noise1mv-pvt-mc": dict(
        title="Fully differential gain-8 sampling-feedback OTA", bench="tb_loop_nominal.spi", metrics=[
            M(("low_frequency_loop_gain_db", "Loop gain", 1, "dB")),
            M(("closed_loop_differential_gain_db", "Closed-loop gain", 1, "dB")),
            M(("loop_ugb_hz", "Loop unity-gain frequency", 1e-6, "MHz")), M(("phase_margin_deg", "Phase margin", 1, "deg")),
            M(("power_w", "Power", 1e3, "mW")), M(("output_common_mode_error_v", "Output CM error", 1e3, "mV"))]),
    "sky130-fct-residue-amplifier-900msps": dict(
        title="Floating charge-transfer residue amplifier (900 MS/s)", script="analyze_fct.py", args=[], metrics=[
            M(("sampled_gain_vv", "Sampled gain", 1, "V/V")), M(("sfdr_db", "SFDR", 1, "dB")),
            M(("hold_transition_movement_ratio", "Hold movement", 100, "%")), M(("power_w", "Power", 1e3, "mW"))]),
    "sky130-lc-vco-2ghz-pvt": dict(
        title="2 GHz LC VCO", bench="tb_tune_tt_1p8v_27c.spi", derive=_vco, metrics=[
            M(("f_ctrl_0v", "Frequency at Vctrl = 0 V", 1e-9, "GHz")), M(("f_ctrl_1v8", "Frequency at Vctrl = 1.8 V", 1e-9, "GHz")),
            M(("tuning_ratio", "Tuning ratio", 1, "x")), M(("min_swing", "Smallest differential swing", 1, "V"))]),
    "sky130-bootstrap-driver-pt": dict(
        title="All-NMOS half-bridge bootstrap gate driver", bench="tb_bootstrap_driver_tt_1p80v_27c.spi", metrics=[
            M(("vgs_peak", "Peak high-side Vgs", 1, "V")), M(("vgs_avg", "Average high-side Vgs", 1, "V")),
            M(("vbst_top_peak", "Peak bootstrap node", 1, "V")), M(("p_dut", "Driver power", 1e3, "mW"))]),
    "sky130-ldo-ota5-robust-pvt-mc": dict(
        title="LDO with five-transistor error amplifier", bench="tb_line_dc_tt.spi", patch=_ldo_line, metrics=[
            M(("vout_162", "Vout at Vin = 1.62 V", 1, "V")), M(("vout_180", "Vout at Vin = 1.80 V", 1, "V")),
            M(("vout_198", "Vout at Vin = 1.98 V", 1, "V")), M(("line_reg", "Line regulation", 1e3, "mV/V"))]),
}


def measure(slug: str, circuit: Path, case_dir: Path, work: Path, sky130_root: Path) -> dict:
    """Re-run the nominal bench for one circuit; return {label: value} plus runtime."""
    cfg = SHOWCASE[slug]
    tb = case_dir / "testbench"
    if "script" in cfg:
        r = sim.run_script(cfg["script"], cfg["args"], tb, circuit, work, sky130_root)
    else:
        if "patch" in cfg:
            staged = sim.stage(tb, circuit, work, sky130_root)
            cfg["patch"](staged / cfg["bench"])
            r = sim.run_staged(cfg["bench"], staged)
        else:
            r = sim.run(cfg["bench"], tb, circuit, work, sky130_root)
    sc = cfg["derive"](r["scalars"]) if "derive" in cfg and r["scalars"] else r["scalars"]
    values = {}
    for key, label, scale, unit in cfg["metrics"]:
        values[f"{label} ({unit})"] = sc[key] * scale if key in sc else float("nan")
    return {"values": values, "seconds": r["seconds"], "returncode": r["returncode"]}
