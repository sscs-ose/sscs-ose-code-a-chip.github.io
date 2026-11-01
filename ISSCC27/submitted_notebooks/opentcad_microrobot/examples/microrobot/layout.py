"""SKY130 Magic layout/DRC/LVS/RC extraction for the clock bias macro only.

Uses installed PDK generators, explicit routing and the PDK Netgen setup.
No full-controller or fabrication signoff is implied by a macro pass.
"""

import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import PatchCollection
from matplotlib.patches import Patch, Rectangle
import numpy as np

HERE = Path(__file__).parent
BIAS_INSTANCES = {"Xb1", "Xb2", "Xb3", "Xmirror", "Xpdiode", "Xcbiasn", "Xcbiasp"}


def magic_run(dest, script, name, pdk):
    executable = shutil.which("magic")
    if not executable:
        raise FileNotFoundError("Optional Magic executable is required")
    script += '\nputs "OPENTCAD_FLOW_DONE"\nquit -noprompt\n'
    (dest / f"{name}.tcl").write_text(script)
    result = subprocess.run(
        [
            executable,
            "-dnull",
            "-noconsole",
            "-rcfile",
            str(pdk / "libs.tech/magic/sky130A.magicrc"),
            f"{name}.tcl",
        ],
        cwd=dest,
        capture_output=True,
        text=True,
        timeout=120,
    )
    log = result.stdout + result.stderr
    (dest / f"{name}.log").write_text(log)
    # Magic can return zero after a Tcl error; require an explicit end marker.
    if result.returncode or "OPENTCAD_FLOW_DONE" not in log or "Error parsing" in log:
        raise RuntimeError(f"Magic flow failed; inspect {dest / (name + '.log')}")
    return log


def placement_script(pdk):
    generator = pdk / "libs.tech/magic/sky130A.tcl"
    return f"""# Absolute ruleset qualification fixes this PDK generator under Tcl 9.
# Only an in-memory script copy is changed; no device rules/decks are altered.
set fd [open {{{generator}}} r]
set pdk_text [read $fd]
close $fd
uplevel #0 [string map [list {{$sky130::ruleset}} {{$::sky130::ruleset}}] $pdk_text]
random seed 1729
load bias_cells
set specs {{{{Xb1 nfet_01v8 0.5 8 10 10}} {{Xmirror nfet_01v8 0.5 8 25 10}} {{Xb2 nfet_01v8 0.5 8 40 10}} {{Xb3 nfet_01v8 0.5 8 55 10}} {{Xpdiode pfet_01v8 1 8 70 10}} {{Xcbiasn cap_mim_m3_1 7 7 25 30}} {{Xcbiasp cap_mim_m3_1 7 7 55 30}}}}
foreach spec $specs {{
    lassign $spec name dev w l x y
    box values ${{x}}um ${{y}}um ${{x}}um ${{y}}um
    if {{[string match *fet* $dev]}} {{
        magic::gencell sky130::sky130_fd_pr__$dev $name w $w l $l viagb 100
    }} else {{
        magic::gencell sky130::sky130_fd_pr__$dev $name w $w l $l
    }}
}}
select top cell
expand
save bias_cells
foreach cell [cellname list children bias_cells] {{
    load $cell
    save $cell
}}
load bias_cells
"""


def read_instance_pins(dest):
    """Read generated labels/transforms, rather than guessing port positions.

    This adapter requires unrotated cells and the audited 5 nm Magic grid.
    """
    content = (dest / "bias_cells.mag").read_text()
    if "magscale 1 2" not in content:
        raise ValueError("Unsupported Magic grid; update the explicit units adapter")
    instances = {}
    for match in re.finditer(r"use (\S+)\s+(\S+)\n.*?transform 1 0 (\S+) 0 1 (\S+)", content, re.S):
        cell, name, x, y = match.groups()
        labels = {}
        for label in re.finditer(
            r"rlabel (\S+) (\S+) (\S+) (\S+) (\S+) \S+ (\S+)", (dest / f"{cell}.mag").read_text()
        ):
            layer, x1, y1, x2, y2, pin = label.groups()
            labels[pin] = (
                (float(x) + (float(x1) + float(x2)) / 2) * 0.005,
                (float(y) + (float(y1) + float(y2)) / 2) * 0.005,
                layer,
            )
        instances[name] = labels
    if set(instances) != BIAS_INSTANCES:
        raise ValueError("Generated instance inventory differs from the bias schematic")
    return instances


def routing_script(instances):
    lines = [
        "load bias_cells",
        "select top cell",
        "flatten microrobot_bias",
        "load microrobot_bias",
        "select top cell",
    ]

    def rect(layer, x1, y1, x2, y2):
        lines.extend(
            [
                f"box values {min(x1, x2):.3f}um {min(y1, y2):.3f}um "
                f"{max(x1, x2):.3f}um {max(y1, y2):.3f}um",
                f"paint {layer}",
            ]
        )

    def patch(layer, x, y, width):
        rect(layer, x - width / 2, y - width / 2, x + width / 2, y + width / 2)

    def wire(layer, x1, y1, x2, y2, width=0.4):
        rect(
            layer,
            min(x1, x2) - width / 2,
            min(y1, y2) - width / 2,
            max(x1, x2) + width / 2,
            max(y1, y2) + width / 2,
        )

    def via1(x, y):
        patch("metal1", x, y, 0.4)
        patch("metal2", x, y, 0.4)
        patch("via1", x, y, 0.28)

    def via2(x, y):
        patch("metal2", x, y, 0.4)
        patch("metal3", x, y, 0.4)
        patch("via2", x, y, 0.30)

    def via3(x, y):
        patch("metal3", x, y, 0.6)
        patch("metal4", x, y, 0.4)
        patch("via3", x, y, 0.34)

    # Magic contact paint includes cut enclosure; these are NOT GDS cut sizes.
    tracks = {"vss": 45, "vdd": 46.2, "bias_n": 47.4, "bias_p": 48.6, "b2": 49.8}
    connections = {
        "Xb1": {"D": "bias_n", "G": "bias_n", "S": "vss", "B": "vss"},
        "Xb2": {"D": "b2", "G": "b2", "S": "bias_n", "B": "vss"},
        "Xb3": {"D": "vdd", "G": "vdd", "S": "b2", "B": "vss"},
        "Xmirror": {"D": "bias_p", "G": "bias_n", "S": "vss", "B": "vss"},
        "Xpdiode": {"D": "bias_p", "G": "bias_p", "S": "vdd", "B": "vdd"},
    }
    for name, pins in connections.items():
        for pin, net in pins.items():
            x, y, _ = instances[name][pin]
            # Gate/guard contacts extend horizontally. Separate their M2 tracks.
            if pin == "G":
                x -= 1
            if pin == "B":
                x += 1
            via1(x, y)
            wire("metal2", x, y, x, tracks[net])
            via2(x, tracks[net])
    for name, net, escape in (("Xcbiasn", "bias_n", 2), ("Xcbiasp", "bias_p", 88)):
        x, y, _ = instances[name]["C1"]
        # Escape in M4 before descending: a via through the MIM overlaps its
        # bottom plate and would short the capacitor.
        wire("metal4", x, y, x, 39)
        wire("metal4", x, 39, escape, 39)
        via3(escape, 39)
        via2(escape, 39)
        wire("metal2", escape, 39, escape, tracks[net])
        via2(escape, tracks[net])
        x, y, _ = instances[name]["C2"]
        wire("metal3", x, y, 90, y)
        via2(90, y)
        wire("metal2", 90, y, 90, tracks["vss"])
        via2(90, tracks["vss"])
    for net, y in tracks.items():
        wire("metal3", 0, y, 92, y)
        # Nonzero attachment rectangles are required for GDS pin markers.
        # Point ports survive native extraction but are lost on GDS re-import.
        lines.extend(
            [
                f"box values -0.2um {y - 0.2:.3f}um 0.2um {y + 0.2:.3f}um",
                f"label {net} center metal3",
            ]
        )
        if net != "b2":
            lines.append(f"port make {dict(vdd=1, vss=2, bias_n=3, bias_p=4)[net]}")
    lines += [
        "save microrobot_bias",
        "box values -10um 0um 100um 60um",
        "drc check",
        "drc catchup",
        "set f [open drc.txt w]",
        'puts $f "DRC_ERRORS [drc list count total]"',
        "puts $f [drc listall why]",
        "close $f",
        "extract all",
        "ext2spice lvs",
        "ext2spice -o bias_lvs.spice",
        "ext2spice cthresh 0",
        "ext2spice -o bias_capacitance.spice",
        "gds write microrobot_bias.gds",
        "feedback save streamout_feedback.tcl",
    ]
    return "\n".join(lines)


def lvs(dest, schematic, pdk, name):
    executable = os.environ.get("NETGEN") or shutil.which("netgen")
    if not executable:
        raise FileNotFoundError("Set NETGEN to the installed Netgen executable")
    result = subprocess.run(
        [
            executable,
            "-batch",
            "lvs",
            "bias_lvs.spice microrobot_bias",
            f"{schematic} microrobot_bias",
            str(pdk / "libs.tech/netgen/sky130A_setup.tcl"),
            f"{name}.txt",
            "-json",
        ],
        cwd=dest,
        capture_output=True,
        text=True,
        timeout=120,
    )
    (dest / f"{name}.log").write_text(result.stdout + result.stderr)
    report = (dest / f"{name}.txt").read_text()
    return (
        result.returncode == 0
        and "Circuits match uniquely." in report
        and "Property errors" not in report
    )


def render(dest):
    colors = {
        "nwell": "#f2dcb1",
        "pwell": "#e0efd9",
        "ndiff": "#58a66a",
        "pdiff": "#d49191",
        "nmos": "#aa5050",
        "pmos": "#aa5050",
        "poly": "#bd4e4e",
        "locali": "#809493",
        "metal1": "#5a88c6",
        "metal2": "#976caf",
        "metal3": "#db9e45",
        "metal4": "#3c9caa",
        "mimcap": "#448c96",
    }
    shapes = {}
    layer = None
    bounds = []
    for line in (dest / "microrobot_bias.mag").read_text().splitlines():
        if line.startswith("<<"):
            layer = line.split()[1]
        elif line.startswith("rect ") and layer != "checkpaint":
            x1, y1, x2, y2 = np.array([float(x) for x in line.split()[1:]]) * 0.005
            bounds.append((x1, y1, x2, y2))
            if layer in colors:
                shapes.setdefault(layer, []).append(Rectangle((x1, y1), x2 - x1, y2 - y1))
    fig, ax = plt.subplots(figsize=(13, 6), layout="constrained")
    for layer, color in colors.items():
        if layer in shapes:
            ax.add_collection(
                PatchCollection(shapes[layer], facecolor=color, edgecolor="none", alpha=0.8)
            )
    for name, x in (("B1", 14.7), ("mirror", 29.7), ("B2", 44.7), ("B3", 59.7), ("P diode", 74.7)):
        ax.text(x, 8, name, ha="center", fontsize=9)
    ax.text(28.7, 29, "bias_n MIM", ha="center", fontsize=9)
    ax.text(58.7, 29, "bias_p MIM", ha="center", fontsize=9)
    ax.set(
        xlim=(-3, 96),
        ylim=(5, 53),
        xlabel="µm",
        ylabel="µm",
        title="Routed SKY130 clock-bias macro — prototype floorplan",
    )
    ax.set_aspect("equal")
    ax.legend(
        handles=[
            Patch(color=colors[k], label=k)
            for k in ("poly", "metal1", "metal2", "metal3", "metal4")
        ],
        loc="upper center",
        ncol=5,
        fontsize=8,
    )
    fig.savefig(dest / "layout.png", dpi=180)
    plt.close(fig)
    b = np.array(bounds)
    return {
        "width_um": float(b[:, 2].max() - b[:, 0].min()),
        "height_um": float(b[:, 3].max() - b[:, 1].min()),
    }


def check_gds_roundtrip(dest, pdk):
    """Check exported geometry and pin connectivity in an empty Magic session."""
    target = dest / "gds_roundtrip"
    target.mkdir(exist_ok=True)
    magic_run(
        target,
        """gds read ../microrobot_bias.gds
load microrobot_bias
select top cell
expand
box values -10um 0um 100um 60um
drc check
drc catchup
set f [open drc.txt w]
puts $f "DRC_ERRORS [drc list count total]"
puts $f [drc listall why]
close $f
extract all
ext2spice lvs
ext2spice -o bias_lvs.spice
""",
        "roundtrip",
        pdk,
    )
    clean = (target / "drc.txt").read_text().startswith("DRC_ERRORS 0")
    matched = lvs(target, HERE.resolve() / "circuits/bias_reference.spice", pdk, "lvs")
    if not clean or not matched:
        raise RuntimeError("Exported GDS failed round-trip DRC/LVS")
    return {"drc_errors": 0, "lvs_match": True}


def divider_edge_audit(time, rail, clock, divided, start_s):
    """Require two clock rises per Q period, with moving-rail interpolation.

    Match nearest edges: library threshold differences can put Q's crossing
    slightly before the clock's 50% crossing. Raw Q-to-Q time bins would then
    falsely report alternating one/three edges.
    """

    def edges(voltage):
        delta = voltage - rail / 2
        i = np.flatnonzero((delta[:-1] < 0) & (delta[1:] >= 0))
        return time[i] - delta[i] * (time[i + 1] - time[i]) / (delta[i + 1] - delta[i])

    clocks, rises = edges(clock), edges(divided)
    rises = rises[rises > start_s]
    if len(clocks) < 5 or len(rises) < 3:
        return {"clock_edges_per_divided_period": [], "edge_audit_passed": False}
    indices = np.array([np.argmin(abs(clocks - t)) for t in rises])
    counts = np.diff(indices)
    alignment = float(np.max(abs(clocks[indices] - rises)))
    return {
        "clock_edges_per_divided_period": counts.tolist(),
        "maximum_crossing_alignment_s": alignment,
        "edge_audit_passed": bool(
            np.all(counts == 2) and alignment < 0.25 * np.median(np.diff(clocks))
        ),
    }


def storage_iteration(dest, *, reuse=False):
    """Audit 2/3/5 pF storage, preserving failures and matched schematics.

    Reuse is explicit and verifies circuit, timestep and capacitance metadata.
    Full waveforms are needed for the edge-by-edge divider audit.
    """
    from .clock import clock_case
    from opentcad.device.compact import SingleDiodePV

    fit = json.loads((HERE / "results/published/pv_fit.json").read_text())
    model = SingleDiodePV(**fit["fitted_terminal_model"])
    results = {}
    for name, cap, step, stop, extracted in (
        ("post_pv_2pf_halfstep", 2e-12, 25e-9, 0.004, True),
        ("post_pv_3pf", 3e-12, 50e-9, 0.004, True),
        ("post_pv_3pf_halfstep", 3e-12, 25e-9, 0.004, True),
        ("pre_pv_3pf_halfstep", 3e-12, 25e-9, 0.004, False),
        ("post_pv_5pf", 5e-12, 50e-9, 0.004, True),
        ("post_pv_5pf_halfstep", 5e-12, 25e-9, 0.004, True),
        ("post_pv_5pf_quarterstep", 5e-12, 12.5e-9, 0.004, True),
        ("post_pv_5pf_long", 5e-12, 25e-9, 0.020, True),
        ("pre_pv_5pf_halfstep", 5e-12, 25e-9, 0.004, False),
    ):
        circuit = (
            dest / "clock_bias_rc.spice" if extracted else HERE / "circuits/starved_clock.spice"
        )
        target = dest / name
        if reuse and (target / "metrics.json").exists():
            metrics = json.loads((target / "metrics.json").read_text())
            if (
                metrics["netlist_sha256"] != hashlib.sha256(circuit.read_bytes()).hexdigest()
                or metrics["max_timestep_s"] != step
                or metrics["pv_storage_F"] != cap
                or metrics["stop_s"] != stop
            ):
                raise ValueError(f"Stale storage experiment: {target}")
            data = np.loadtxt(target / "clock.dat", skiprows=1)
        else:
            metrics, data = clock_case(
                target,
                circuit_path=circuit,
                pv_model=model,
                pv_storage_F=cap,
                timestep_s=step,
                stop_s=stop,
                output_load_F=2e-15,
            )
        if data is None:
            raise RuntimeError(f"Missing transient for {name}")
        metrics.update(
            divider_edge_audit(
                data[:, 0], data[:, 1], data[:, 2], data[:, 7], 0.6 * metrics["stop_s"]
            )
        )
        results[name] = metrics
    post = results["post_pv_3pf_halfstep"]
    pre = results["pre_pv_3pf_halfstep"]
    coarse = results["post_pv_3pf"]
    results["matched_3pf_relative_changes"] = {
        k: post[k] / pre[k] - 1 for k in ("frequency_Hz", "mean_power_W", "first_high_crossing_s")
    }
    results["post_3pf_timestep_relative_changes"] = {
        k: abs(coarse[k] / post[k] - 1) for k in ("frequency_Hz", "mean_power_W")
    }
    results["accepted_nominal_3pf"] = all(
        r["passed"] and r["edge_audit_passed"] for r in (pre, post, coarse)
    )
    results["accepted_nominal_5pf"] = all(
        results[name]["passed"] and results[name]["edge_audit_passed"]
        for name in (
            "post_pv_5pf",
            "post_pv_5pf_halfstep",
            "post_pv_5pf_quarterstep",
            "post_pv_5pf_long",
            "pre_pv_5pf_halfstep",
        )
    )
    results["post_5pf_fine_timestep_relative_changes"] = {
        k: abs(results["post_pv_5pf_halfstep"][k] / results["post_pv_5pf_quarterstep"][k] - 1)
        for k in ("frequency_Hz", "mean_power_W")
    }
    results["scope"] = (
        "TT only, extracted bias macro; storage and remaining circuit are schematic; "
        "isolated passing runs do not establish robust clock reception"
    )
    (dest / "storage_iteration.json").write_text(json.dumps(results, indent=2) + "\n")
    return results


def tolerance_audit(dest, *, reuse=False):
    """Separate integration-error sensitivity from a physical storage change.

    Tight relative tolerance is tested at two timesteps for both 2 and 5 pF.
    Qualification is a nominal TT numerical check, not a corner/receiver signoff.
    """
    from .clock import clock_case
    from opentcad.device.compact import SingleDiodePV

    fit = json.loads((HERE / "results/published/pv_fit.json").read_text())
    model = SingleDiodePV(**fit["fitted_terminal_model"])
    report = {}
    for name, cap, step, extracted in (
        ("post_pv_2pf_tight", 2e-12, 50e-9, True),
        ("post_pv_2pf_tight_halfstep", 2e-12, 25e-9, True),
        ("post_pv_5pf_tight", 5e-12, 50e-9, True),
        ("post_pv_5pf_tight_halfstep", 5e-12, 25e-9, True),
        ("pre_pv_2pf_tight_halfstep", 2e-12, 25e-9, False),
    ):
        circuit = (
            dest / "clock_bias_rc.spice" if extracted else HERE / "circuits/starved_clock.spice"
        )
        target = dest / name
        if reuse and (target / "metrics.json").exists():
            result = json.loads((target / "metrics.json").read_text())
            expected = {
                "netlist_sha256": hashlib.sha256(circuit.read_bytes()).hexdigest(),
                "pv_storage_F": cap,
                "max_timestep_s": step,
                "relative_tolerance": 1e-6,
                "stop_s": 0.004,
            }
            if any(result.get(k) != v for k, v in expected.items()):
                raise ValueError(f"Stale tolerance experiment: {target}")
            data = np.loadtxt(target / "clock.dat", skiprows=1)
        else:
            result, data = clock_case(
                target,
                circuit_path=circuit,
                pv_model=model,
                pv_storage_F=cap,
                timestep_s=step,
                relative_tolerance=1e-6,
                output_load_F=2e-15,
            )
        if data is None:
            raise RuntimeError(f"Missing tolerance-audit transient: {target}")
        result.update(divider_edge_audit(data[:, 0], data[:, 1], data[:, 2], data[:, 7], 0.0024))
        report[name] = result
    for cap in (2, 5):
        coarse, fine = (report[f"post_pv_{cap}pf_tight{suffix}"] for suffix in ("", "_halfstep"))
        changes = {k: abs(coarse[k] / fine[k] - 1) for k in ("frequency_Hz", "mean_power_W")}
        report[f"{cap}pf_timestep_relative_changes"] = changes
        report[f"nominal_{cap}pf_qualified"] = bool(
            coarse["passed"]
            and fine["passed"]
            and coarse["edge_audit_passed"]
            and fine["edge_audit_passed"]
            and max(changes.values()) < 0.01
        )
    pre, post = report["pre_pv_2pf_tight_halfstep"], report["post_pv_2pf_tight_halfstep"]
    report["nominal_2pf_qualified"] &= pre["passed"] and pre["edge_audit_passed"]
    report["matched_2pf_relative_changes"] = {
        k: post[k] / pre[k] - 1 for k in ("frequency_Hz", "mean_power_W", "first_high_crossing_s")
    }
    report["scope"] = (
        "4 ms, TT, reltol=1e-6, abstol=1e-15 A, Gear2, 25/50 ns; "
        "all divider periods must have two clock rises and scalar timestep changes <1%; "
        "not full PVT, mismatch or full-controller validation"
    )
    (dest / "tolerance_audit.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


def run(destination=HERE / "local_runs/layout/bias_reference_final", *, postlayout=True):
    dest = Path(destination).resolve()
    if (dest / "microrobot_bias.mag").exists():
        raise FileExistsError("Use a fresh output directory; existing layout is preserved")
    dest.mkdir(parents=True, exist_ok=True)
    pdk = Path(os.environ.get("PDK_ROOT", "/usr/local/share/pdk")) / "sky130A"
    source = HERE / "circuits/bias_reference.spice"
    # Ensure the macro still describes the exact characterized clock subset.
    clock = (HERE / "circuits/starved_clock.spice").read_text()
    subset = [
        s.replace("ref_vdd", "vdd")
        for s in clock.splitlines()
        if s.split() and s.split()[0] in BIAS_INSTANCES
    ]
    if not all(s in source.read_text().splitlines() for s in subset) or len(subset) != 7:
        raise ValueError("Bias schematic and clock source differ")
    magic_run(dest, placement_script(pdk), "generate_cells", pdk)
    magic_run(dest, routing_script(read_instance_pins(dest)), "route_extract", pdk)
    if not (dest / "drc.txt").read_text().startswith("DRC_ERRORS 0"):
        raise RuntimeError("Bias layout has DRC errors")
    if (dest / "streamout_feedback.tcl").read_text().strip():
        raise RuntimeError("GDS streamout produced feedback errors")
    matched = lvs(dest, source, pdk, "lvs")
    if not matched:
        raise RuntimeError("Bias macro LVS failed")
    bad = dest / "intentional_lvs_mismatch.spice"
    bad.write_text(source.read_text().replace("Xb1 bias_n bias_n", "Xb1 bias_n vdd"))
    rejected_bad = not lvs(dest, bad, pdk, "negative_control_lvs")
    if not rejected_bad:
        raise RuntimeError("LVS failed to detect the intentional gate connection error")
    roundtrip = check_gds_roundtrip(dest, pdk)
    magic_run(
        dest,
        """load microrobot_bias
select top cell
expand
extract all
ext2sim labels on
ext2sim
extresist tolerance 10
extresist
ext2spice lvs
ext2spice cthresh 0
ext2spice extresist on
ext2spice -o bias_rc.spice
""",
        "extract_rc",
        pdk,
    )
    rc = (dest / "bias_rc.spice").read_text()
    report = {
        "macro": "clock bias only",
        "drc_errors": 0,
        "lvs_match": matched,
        "intentional_wrong_gate_rejected": rejected_bad,
        "gds_roundtrip": roundtrip,
        "dimensions": render(dest),
        "rc_resistors": len(re.findall(r"^R\d+ ", rc, re.M)),
        "rc_capacitors": len(re.findall(r"^C\d+ ", rc, re.M)),
        "schematic_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "clock_source_sha256": hashlib.sha256(clock.encode()).hexdigest(),
        "pdk_generator_sha256": hashlib.sha256(
            (pdk / "libs.tech/magic/sky130A.tcl").read_bytes()
        ).hexdigest(),
        "pdk_netgen_setup_sha256": hashlib.sha256(
            (pdk / "libs.tech/netgen/sky130A_setup.tcl").read_bytes()
        ).hexdigest(),
        "limitations": [
            "Prototype floorplan, not footprint optimized",
            "Only bias macro extracted; oscillator, divider and drivers remain schematic",
            "Magic 8.3.546 legacy RC extraction; compare capacitance-only and RC results",
            "No density/fill/antenna/latch-up/ESD or fabrication signoff",
            "No statistical mismatch, passive extraction corners or 3D field-solver calibration",
        ],
    }
    if postlayout:
        from .clock import clock_case
        from opentcad.device.compact import SingleDiodePV

        composite = []
        for line in clock.splitlines():
            if line.split() and line.split()[0] in BIAS_INSTANCES:
                continue
            composite.append(line)
            if line.startswith("Vbias "):
                composite.append("Xlayout ref_vdd vss bias_n bias_p microrobot_bias")
        cases = {}
        for kind in ("capacitance", "rc"):
            replacement = dest / f"clock_bias_{kind}.spice"
            replacement.write_text(
                "\n".join(composite) + "\n" + (dest / f"bias_{kind}.spice").read_text()
            )
            cases[kind], _ = clock_case(
                dest / f"post_{kind}", circuit_path=replacement, output_load_F=2e-15
            )
        fit = json.loads((HERE / "results/published/pv_fit.json").read_text())
        cases["pv_rc"], _ = clock_case(
            dest / "post_pv_rc",
            circuit_path=dest / "clock_bias_rc.spice",
            output_load_F=2e-15,
            pv_model=SingleDiodePV(**fit["fitted_terminal_model"]),
        )
        before = json.loads((HERE / "results/clock_final/summary.json").read_text())
        ideal = next(
            r
            for r in before["cases"]
            if r["corner"] == "tt"
            and r["voltage_V"] == 1.8
            and r["temperature_C"] == 26.85
            and r["ramp_s"] == 100e-6
        )
        pv = next(r for r in before["cases"] if r["supply"] != "ideal voltage ramp")
        report["postlayout"] = cases
        report["relative_changes"] = {
            key: {
                field: result[field] / (pv if key == "pv_rc" else ideal)[field] - 1
                for field in ("frequency_Hz", "mean_power_W", "first_high_crossing_s")
            }
            for key, result in cases.items()
            if result["passed"]
        }
        if not all(r["passed"] for r in cases.values()):
            report["electrical_status"] = "post-layout clock check failed; redesign needed"
        else:
            report["electrical_status"] = (
                "clock still starts/oscillates with extracted bias macro; remaining layout unverified"
            )
        report["storage_iteration"] = storage_iteration(dest)
        if report["storage_iteration"]["accepted_nominal_5pf"]:
            report["electrical_status"] = (
                "5 pF nominal storage checks pass; only bias macro extracted, "
                "full-controller/PVT verification pending"
            )
        else:
            report["electrical_status"] = (
                "NOT ACCEPTED: clock/divider reception is sensitive to storage, extraction "
                "and timestep; isolated passes do not establish robustness"
            )
        report["tolerance_audit"] = tolerance_audit(dest)
        if report["tolerance_audit"]["nominal_2pf_qualified"]:
            report["electrical_status"] = (
                "Nominal TT 2 pF receiver passes at reltol=1e-6 and 25/50 ns; "
                "loose-setting failures retained; full-controller/PVT validation pending"
            )
    (dest / "summary.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=HERE / "local_runs/layout/bias_reference_final")
    parser.add_argument("--no-postlayout", action="store_true")
    args = parser.parse_args()
    print(json.dumps(run(args.output, postlayout=not args.no_postlayout), indent=2))
