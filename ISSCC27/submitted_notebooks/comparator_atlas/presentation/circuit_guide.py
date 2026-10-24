"""Draw the published topology without changing the circuit or its evidence."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patheffects as path_effects
from matplotlib.patches import Circle

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from comparator_atlas.designs import circuit_text, get_design
from entry_tools import verify_manifest
from presentation.figure_style import FigureProfile, export_figure, publication_style

INK = "#111111"
MUTED = "#555555"
PROFILE = FigureProfile(height_in=5.70)


def connections(text: str) -> dict[str, tuple[str, ...]]:
    devices = {}
    for line in text.splitlines():
        if not line.startswith("X"):
            continue
        fields = line.split()
        if len(fields) != 6 or fields[0] in devices:
            raise ValueError("Unexpected or duplicate transistor definition")
        devices[fields[0]] = tuple(fields[1:])
    return devices


def check_topology(devices: dict[str, tuple[str, ...]]) -> None:
    standard = "sky130_fd_pr__nfet_01v8"
    low_vt = "sky130_fd_pr__nfet_01v8_lvt"
    pfet = "sky130_fd_pr__pfet_01v8"
    expected = {
        "Xinp": ("xp", "vinp", "tail", "vss", low_vt),
        "Xinn": ("xn", "vinn", "tail", "vss", low_vt),
        "Xtail": ("tail", "clk", "vss", "vss", standard),
        "Xln": ("qn", "qp", "xp", "vss", standard),
        "Xlp": ("qp", "qn", "xn", "vss", standard),
        "Xpn": ("qn", "qp", "vdd", "vdd", pfet),
        "Xpp": ("qp", "qn", "vdd", "vdd", pfet),
    }
    for node in ("xp", "xn", "qp", "qn"):
        expected["Xr" + node] = (node, "clk", "vdd", "vdd", pfet)
    for side, drain, gate in (("p", "xp", "vinp"), ("n", "xn", "vinn")):
        for bit in range(4):
            source = f"s{side}{bit}"
            expected[f"Xt{side}{bit}"] = (drain, gate, source, "vss", low_vt)
            expected[f"Xs{side}{bit}"] = (source, f"t{side}{bit}", "tail", "vss", standard)
    if devices != expected:
        raise ValueError("The current electrical topology does not match this annotated diagram")


def wire(ax, points, *, crossing=False):
    line, = ax.plot(
        [point[0] for point in points], [point[1] for point in points],
        color=INK, linewidth=0.8, solid_capstyle="round", zorder=3 if crossing else 1,
    )
    if crossing:
        line.set_path_effects([path_effects.Stroke(linewidth=2.8, foreground="white"),
                               path_effects.Normal()])
    return line


def junction(ax, x, y):
    ax.add_patch(Circle((x, y), 0.022, facecolor=INK, edgecolor=INK, linewidth=0, zorder=5))


def label(ax, x, y, text, *, ha="left", va="center", size=9, color=INK):
    return ax.text(x, y, text, ha=ha, va=va, fontsize=size, color=color, zorder=6)


def mos_symbol(ax, x, y, *, kind="n", gate_side=-1):
    if kind not in ("n", "p") or gate_side not in (-1, 1):
        raise ValueError("MOS polarity and gate orientation must be explicit")
    channel = x + gate_side * 0.13
    gate = x + gate_side * 0.25
    for low, high in ((-0.22, -0.09), (-0.055, 0.055), (0.09, 0.22)):
        wire(ax, [(channel, y + low), (channel, y + high)])
    wire(ax, [(x, y + 0.35), (x, y + 0.22), (channel, y + 0.22)])
    wire(ax, [(x, y - 0.35), (x, y - 0.22), (channel, y - 0.22)])
    wire(ax, [(gate, y - 0.24), (gate, y + 0.24)])
    pin = (x + gate_side * 0.51, y)
    end = gate
    if kind == "p":
        center = gate + gate_side * 0.046
        ax.add_patch(Circle((center, y), 0.046, facecolor="white", edgecolor=INK, linewidth=0.8, zorder=4))
        end = gate + gate_side * 0.092
    wire(ax, [pin, (end, y)])
    upper, lower = (x, y + 0.35), (x, y - 0.35)
    return {
        "D": upper if kind == "n" else lower,
        "G": pin,
        "S": lower if kind == "n" else upper,
        "kind": kind,
        "gate_inversion_bubble": kind == "p",
    }


def device_groups(devices: dict[str, tuple[str, ...]]) -> dict[str, list[str]]:
    check_topology(devices)
    groups = {name: [name] for name in ("Xinp", "Xinn", "Xtail", "Xln", "Xlp", "Xpn", "Xpp")}
    groups["Xr[node]"] = ["Xrxp", "Xrxn", "Xrqp", "Xrqn"]
    for side in ("p", "n"):
        for role in ("t", "s"):
            groups[f"X{role}{side}[k]"] = [f"X{role}{side}{bit}" for bit in range(4)]
    flattened = [name for values in groups.values() for name in values]
    if len(flattened) != 27 or set(flattened) != set(devices):
        raise ValueError("Every netlist instance must be represented exactly once")
    return groups


def schematic_figure(design, devices: dict[str, tuple[str, ...]]):
    groups = device_groups(devices)
    with publication_style(PROFILE):
        figure = plt.figure(figsize=(PROFILE.width_in, PROFILE.height_in))
        ax = figure.add_axes([0, 0, 1, 1])
        ax.set(xlim=(0, PROFILE.width_in), ylim=(0, PROFILE.height_in), aspect="equal")
        ax.axis("off")
        label(ax, 0.16, 5.47, "(a) Regenerative core", size=9.5)
        label(ax, 4.00, 5.47, "(b) Reset (four instances)", size=9.5)
        label(ax, 4.00, 3.55, "(c) Trim bit, k = 0, 1, 2, 3", size=9.5)

        x_left, x_right, center = 1.00, 2.85, 1.925
        supply_y, output_y = 5.06, 4.01
        wire(ax, [(x_left, supply_y), (x_right, supply_y)])
        label(ax, center, supply_y + 0.14, "vdd", ha="center")
        symbols = {}
        for x, suffix, side, output, internal in (
            (x_left, "n", 1, "qn", "xp"), (x_right, "p", -1, "qp", "xn"),
        ):
            p = mos_symbol(ax, x, 4.57, kind="p", gate_side=side)
            n = mos_symbol(ax, x, 3.36, kind="n", gate_side=side)
            symbols["Xp" + suffix] = p
            symbols["Xl" + suffix] = n
            wire(ax, [(x, supply_y), p["S"]])
            wire(ax, [p["D"], n["D"]])
            junction(ax, x, output_y)
            label(ax, x - side * 0.14, output_y, output, ha="right" if side == 1 else "left")
            label(ax, x - side * 0.13, 4.58, "Xp" + suffix,
                  ha="right" if side == 1 else "left")
            label(ax, x - side * 0.13, 4.39, f"{design.latch_p_w:g}/0.15",
                  ha="right" if side == 1 else "left", color=MUTED)
            label(ax, x - side * 0.13, 3.36, "Xl" + suffix,
                  ha="right" if side == 1 else "left")
            label(ax, x - side * 0.13, 3.17, f"{design.latch_n_w:g}/0.15",
                  ha="right" if side == 1 else "left", color=MUTED)
            input_symbol = mos_symbol(ax, x, 2.22, gate_side=-side)
            input_name = "Xinp" if side == 1 else "Xinn"
            symbols[input_name] = input_symbol
            wire(ax, [n["S"], input_symbol["D"]])
            junction(ax, x, 2.77)
            label(ax, x + side * 0.13, 2.77, internal, ha="left" if side == 1 else "right")
            label(ax, x + side * 0.15, 2.33, input_name,
                  ha="left" if side == 1 else "right")
            label(ax, x + side * 0.15, 2.13, "LVT", ha="left" if side == 1 else "right")
            label(ax, x + side * 0.15, 1.94, f"{design.input_w:g}/0.15",
                  ha="left" if side == 1 else "right", color=MUTED)
            label(ax, input_symbol["G"][0] - side * 0.04, input_symbol["G"][1],
                  "vinp" if side == 1 else "vinn", ha="right" if side == 1 else "left")
            wire(ax, [input_symbol["S"], (x, 1.60)])
        wire(ax, [(x_left, 1.60), (x_right, 1.60)])
        junction(ax, center, 1.60)
        label(ax, center + 0.09, 1.62, "tail", va="bottom")
        tail = mos_symbol(ax, center, 1.06)
        symbols["Xtail"] = tail
        wire(ax, [(center, 1.60), tail["D"]])
        wire(ax, [tail["S"], (center, 0.55)])
        for width, y in ((0.30, 0.55), (0.20, 0.49), (0.09, 0.43)):
            wire(ax, [(center - width / 2, y), (center + width / 2, y)])
        label(ax, center + 0.22, 1.13, "Xtail")
        label(ax, center + 0.22, 0.93, f"{design.tail_w:g}/0.15", color=MUTED)
        label(ax, tail["G"][0] - 0.04, tail["G"][1], "clk", ha="right")
        label(ax, center + 0.24, 0.49, "vss")

        gate_left, gate_right = 1.63, 2.22
        for names, gate_x in ((("Xpn", "Xln"), gate_left), (("Xpp", "Xlp"), gate_right)):
            for name in names:
                wire(ax, [symbols[name]["G"], (gate_x, symbols[name]["G"][1])])
            wire(ax, [(gate_x, 3.36), (gate_x, 4.57)])
        wire(ax, [(x_left, output_y), (1.18, output_y), (gate_right, 3.62)], crossing=True)
        wire(ax, [(x_right, output_y), (2.67, output_y), (gate_left, 3.56)], crossing=True)
        junction(ax, gate_left, 3.56)
        junction(ax, gate_right, 3.62)

        reset_x, reset_y = 4.65, 4.61
        reset = mos_symbol(ax, reset_x, reset_y, kind="p")
        symbols["Xr[node]"] = reset
        label(ax, reset_x, reset_y + 0.48, "vdd", ha="center")
        label(ax, reset_x, reset_y - 0.50, "node", ha="center")
        label(ax, reset["G"][0] - 0.04, reset_y, "clk", ha="right")
        label(ax, 5.10, reset_y + 0.12, "Xr[node]")
        label(ax, 5.10, reset_y - 0.08, f"{design.reset_w:g}/0.15", color=MUTED)
        label(ax, 5.10, reset_y - 0.34, "node = xp, xn, qp, qn")

        for x, side in ((4.65, "p"), (6.26, "n")):
            analog = mos_symbol(ax, x, 2.78)
            switch = mos_symbol(ax, x, 1.62)
            symbols[f"Xt{side}[k]"] = analog
            symbols[f"Xs{side}[k]"] = switch
            label(ax, x, 3.26, "xp" if side == "p" else "xn", ha="center")
            wire(ax, [analog["S"], switch["D"]])
            junction(ax, x, 2.16)
            label(ax, x + 0.10, 2.16, f"s{side}[k]")
            label(ax, analog["G"][0] - 0.03, 2.78, "vinp" if side == "p" else "vinn", ha="right")
            label(ax, switch["G"][0] - 0.03, 1.62, f"t{side}[k]", ha="right")
            label(ax, x + 0.19, 2.89, f"Xt{side}[k]")
            label(ax, x + 0.19, 2.68, "LVT", color=MUTED)
            label(ax, x + 0.19, 1.73, f"Xs{side}[k]")
            label(ax, x, 1.13, "tail", ha="center")
        auxiliary_widths = ", ".join(f"{0.42 * (1 << bit):g}" for bit in range(design.trim_bits))
        switch_widths = ", ".join(str(1 << bit) for bit in range(design.trim_bits))
        label(ax, 4.03, 0.84, f"Xt: W = {auxiliary_widths}; L = {design.trim_l:g}", color=MUTED)
        label(ax, 4.03, 0.64, f"Xs: W = {switch_widths}; L = 0.15", color=MUTED)
        label(ax, 0.16, 0.17, "W/L in \N{MICRO SIGN}m. All nMOS bulks: vss; pMOS bulks: vdd. Bulk wires omitted.", color=MUTED)
    return figure, symbols, groups


def build() -> Path:
    verify_manifest("optimization_manifest.json")
    source = ROOT / "results" / "study" / "selected_circuit.spice"
    text = source.read_text(encoding="utf-8")
    design = get_design("lvt_balanced_4b")
    if text != circuit_text(design):
        raise ValueError("The published netlist and annotated sizing model differ")
    devices = connections(text)
    check_topology(devices)
    output = ROOT / "results" / "presentation"
    output.mkdir(parents=True, exist_ok=True)
    figure, symbols, groups = schematic_figure(design, devices)
    figure_review = export_figure(figure, output, "circuit_guide", PROFILE)
    paths = [output / "circuit_guide.svg", output / "circuit_guide.pdf", output / "circuit_guide.png"]
    plt.close(figure)
    caption = (
        "Selected 27-transistor comparator: (a) differential input pair and cross-coupled regenerative "
        "core, (b) one reset PFET for each listed node, and (c) one of four source-gated trim bits "
        "on each side. PMOS gates use inversion bubbles; low-threshold input devices are labeled LVT. "
        "Filled dots denote electrical junctions; unmarked crossings are unconnected. Identical net "
        "labels across panels denote the same electrical node. All NMOS bodies connect to vss and "
        "PMOS bodies to vdd; body wires and external 5 fF loads are omitted. W/L values are in "
        "micrometres. The schematic is checked against the published transistor netlist."
    )
    caption_path = output / "circuit_guide_caption.txt"
    caption_path.write_text(caption + "\n", encoding="utf-8", newline="\n")
    paths.append(caption_path)
    receipt = {
        "status": "topology_guide_checked_against_published_netlist",
        "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "generator_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "design": design.report(),
        "symbol_groups": groups,
        "symbol_geometry": symbols,
        "actual_instance_count": sum(len(group) for group in groups.values()),
        "figure_profile": figure_review,
        "device_inventory": {name: dict(zip(("drain", "gate", "source", "bulk", "model"), pins))
                             for name, pins in devices.items()},
        "artifact_sha256": {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in paths},
        "physical_layout_or_new_simulation_result": False,
        "published_entry_updated": False,
    }
    (output / "circuit_guide_manifest.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(f"Created a source-checked {len(devices)}-device guide in {output.relative_to(ROOT)}")
    return output


if __name__ == "__main__":
    build()
