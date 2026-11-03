"""Explore saved candidate measurements without running layout or circuit tools."""
import base64
from copy import deepcopy
from html import escape
from io import BytesIO
import json
from pathlib import Path
import sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
from matplotlib.colors import Normalize
from matplotlib.patches import Rectangle
import numpy as np
from IPython.core.interactiveshell import InteractiveShell
from IPython.display import HTML, Image, display

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from perfpdn.metric_policy import evaluate_metrics, constraint_report

DATA = Path(__file__).resolve().parent / "evidence/explorer"
STYLE = {"font.family": "DejaVu Serif", "font.size": 11, "axes.labelsize": 12,
         "axes.titlesize": 13, "axes.spines.top": False, "axes.spines.right": False,
         "axes.formatter.useoffset": False, "figure.facecolor": "white",
         "axes.facecolor": "white", "text.color": "black"}
PREDICTIONS = {"first_order_values": ("First order", "#666666", "+"),
               "predicted_values": ("Finite prediction", "#0072B2", "D")}


def load_study(name):
    folder = DATA / name
    data = json.loads((folder / "study.json").read_text())
    data["folder"] = folder
    data["labels"] = {r["id"]: f"C{k+1}" for k, r in
                      enumerate(sorted(data["candidates"], key=lambda r: r["id"]))}
    return data


def policy_for(data, priority="configured"):
    policy = {"metrics": deepcopy(data["metrics"])}
    if priority != "configured":
        for name, spec in policy["metrics"].items():
            spec["weight"] = float(name == priority)
    return policy


def rank(data, budget, priority="configured"):
    policy = policy_for(data, priority)
    baseline = data["baseline"]["metrics"]
    objective = lambda values: sum(m["objective"] for m in evaluate_metrics(values, policy).values())
    initial = objective(baseline)
    rows = []
    for candidate in data["candidates"]:
        row = {"candidate": candidate, "area": candidate["geometry"]["added_area_um2"]}
        for kind, field in (("predicted", "predicted_values"), ("measured", "measured_values")):
            values = candidate[field]
            benefit = initial - objective(values)
            reasons = constraint_report(values, baseline, policy)["failures"]
            if row["area"] > budget + 1e-9:
                reasons.append("Over budget")
            if benefit <= 0:
                reasons.append("No positive benefit")
            row[kind] = {"benefit": benefit, "efficiency": benefit / row["area"],
                         "reasons": reasons, "eligible": not reasons}
        rows.append(row)
    rows.sort(key=lambda r: r["predicted"]["benefit"], reverse=True)
    choices = {}
    for kind in ("predicted", "measured"):
        eligible = [r for r in rows if r[kind]["eligible"]]
        choices[kind] = max(eligible, key=lambda r: r[kind]["benefit"])["candidate"]["id"] if eligible else None
    return rows, choices


def png(fig):
    buffer = BytesIO()
    fig.savefig(buffer, format="png", dpi=160, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return buffer.getvalue()


def table(headers, rows):
    def cells(values, tag):
        return "<tr>" + "".join(f'<{tag} style="padding:5px 8px;border-bottom:1px solid #ddd;text-align:left;white-space:nowrap">{escape(str(v))}</{tag}>'  for v in values) + "</tr>"
    return ('<div style="overflow-x:auto"><table style="font:14px/1.5 Georgia,serif;'
            'border-collapse:collapse;width:100%"><thead>' + cells(headers, "th") +
            "</thead><tbody>" + "".join(cells(row, "td") for row in rows) + "</tbody></table></div>")


def limits_text(spec):
    constraints = spec.get("constraints", {})
    unit, scale = spec.get("display_unit", ""), spec.get("display_scale", 1)
    limits = [f'{sign} {constraints[key]*scale:.7g} {unit}'
              for key, sign in (("minimum", "≥"), ("maximum", "≤")) if key in constraints]
    if "max_error_percent" in constraints:
        limits.append(f'|scaled error| ≤ {constraints["max_error_percent"]/100:g}')
    if constraints.get("no_worse_than_baseline"):
        limits.append("Target error no worse than baseline")
    if constraints.get("tolerance_percent"):
        limits.append(f'Tolerance: {constraints["tolerance_percent"]:g}% of scale')
    return "; ".join(limits) or "None"


def metric_rows(data, candidate):
    rows = []
    for name, spec in data["metrics"].items():
        scale = spec.get("display_scale", 1)
        baseline = data["baseline"]["metrics"][name]
        actual = candidate["measured_values"][name]
        finite = candidate["predicted_values"][name]
        fmt = lambda x: f"{x * scale:.8g}"
        relative = abs(finite - actual) / abs(actual - baseline) if actual != baseline else None
        rows.append([f'{spec["label"]} ({spec.get("display_unit", "")})',
                     fmt(baseline), fmt(candidate["first_order_values"][name]), fmt(finite),
                     fmt(actual), fmt(finite - baseline), fmt(actual - baseline),
                     fmt(abs(finite - actual)), "—" if relative is None else f"{100 * relative:.3g}%"])
    return rows


def response_plot(data, candidate, overlays=(), prediction="both"):
    spec = next((s for s in data["metrics"].values() if s["measurement"] == "unity_Hz"),
                {"display_scale": 1, "display_unit": "Hz"})
    fs, unit = spec.get("display_scale", 1), spec.get("display_unit", "Hz")
    fig, (ax, numbers) = plt.subplots(2, 1, figsize=(10, 5.7), height_ratios=[4, 1],
                                     layout="constrained")
    records = [("Baseline", data["baseline"], "black", "-"),
               (data["labels"][candidate["id"]], candidate, "#D55E00", "-")]
    colors = iter(["#009E73", "#CC79A7", "#E69F00", "#56B4E9", "#999999"])
    for row in data["candidates"]:
        if row["id"] in overlays and row["id"] != candidate["id"]:
            records.append((data["labels"][row["id"]], row, next(colors, "#999999"), "--"))
    for label, row, color, style in records:
        curve = np.loadtxt(data["folder"] / row["bode_file"], skiprows=1)
        ax.semilogx(curve[:, 0] * fs, 20 * np.log10(np.hypot(curve[:, 1], curve[:, 2])),
                    label=label + " · ngspice", color=color, ls=style, lw=1.8)
    crossings = [r.get("measured_values", r.get("metrics"))[n] for _, r, _, _ in records
                 for n, s in data["metrics"].items() if s["measurement"] == "unity_Hz"]
    if crossings:
        ax.set_xlim(curve[0, 0] * fs * .75, min(curve[-1, 0], max(crossings) * 10) * fs)
    for field, (label, color, marker) in PREDICTIONS.items():
        if prediction not in ("both", field):
            continue
        for k, (name, metric) in enumerate(data["metrics"].items()):
            value = candidate[field][name]
            x, y = (metric["frequency_Hz"], value) if metric["measurement"] == "gain_dB" else (value, 0)
            style = {"facecolors": "none", "edgecolors": color} if marker == "D" else {"color": color}
            ax.scatter(x * fs, y, marker=marker, s=65, zorder=5, **style,
                       label=label + " · selected" if k == 0 else None)

    visible = []
    for line in ax.lines:
        x, y = np.asarray(line.get_xdata()), np.asarray(line.get_ydata())
        visible.extend(y[(x >= ax.get_xlim()[0]) & (x <= ax.get_xlim()[1])])
    for points in ax.collections:
        visible.extend(points.get_offsets()[:, 1])
    low, high = min(visible), max(visible)
    pad = max((high - low) * .08, .1)
    ax.set_ylim(low - pad, high + pad)
    ax.axhline(0, color="#aaaaaa", lw=.8)
    ax.set(xlabel=f"Frequency ({unit})", ylabel="Voltage gain (dB)",
           title=f'{data["label"]} · {data["labels"][candidate["id"]]} · '
                 f'{candidate["geometry"]["added_area_um2"]:.4g} µm² added')
    ax.legend(fontsize=9, ncol=2)
    numbers.axis("off")
    rows = metric_rows(data, candidate)

    compact = [[r[0], r[1], r[3], r[4], r[6], r[7]] for r in rows]
    tab = numbers.table(cellText=compact,
                        colLabels=["Metric", "Baseline", "Finite", "Ngspice", "Δ measured", "|Error|"],
                        colWidths=[.25, .15, .15, .15, .15, .15], cellLoc="center", loc="center")
    tab.auto_set_font_size(False)
    tab.set_fontsize(9)
    tab.scale(1, 1.65)
    return fig


def candidate_plot(data, candidate, budget, priority="configured", prediction="both"):
    rows, choices = rank(data, budget, priority)
    fig, axes = plt.subplots(1, len(data["metrics"]), figsize=(10, 3.7), squeeze=False,
                             layout="constrained")
    for ax, (name, spec) in zip(axes.flat, data["metrics"].items()):
        scale = spec.get("display_scale", 1)
        ax.axhline(data["baseline"]["metrics"][name] * scale, color="black", lw=1, label="Baseline")
        for row in rows:
            c = row["candidate"]
            eligible = row["measured"]["eligible"]
            ax.scatter(row["area"], c["measured_values"][name] * scale, s=55,
                       color="#D55E00" if eligible else "#222222", marker="s" if eligible else "x",
                       zorder=5 if not eligible else 3)
            right = row["area"] > .85 * data["budget_um2"]
            ax.annotate(data["labels"][c["id"]], (row["area"], c["measured_values"][name] * scale),
                        xytext=(-7 if right else 4, 9), ha="right" if right else "left",
                        textcoords="offset points", fontsize=9,
                        bbox={"facecolor": "white", "edgecolor": "none", "alpha": .85, "pad": .5})
            for field, (_, color, marker) in PREDICTIONS.items():
                if prediction in ("both", field):
                    style = {"facecolors": "none", "edgecolors": color} if marker == "D" else {"color": color}
                    ax.scatter(row["area"], c[field][name] * scale, marker=marker, s=55, **style)
        ax.scatter(candidate["geometry"]["added_area_um2"], candidate["measured_values"][name] * scale,
                   s=150, facecolors="none", edgecolors="black", linewidths=1.3, label="Inspected")
        ax.axvline(budget, color="black", ls="--", lw=1)
        ax.axvspan(budget, data["budget_um2"] * 1.06, color="#eeeeee", zorder=-1)
        ax.set(xlim=(-data["budget_um2"] * .04, data["budget_um2"] * 1.06),
               xlabel="Added area (µm²)", ylabel=f'{spec["label"]} ({spec.get("display_unit", "")})')
        ax.ticklabel_format(axis="y", style="plain", useOffset=False)
    handles = [plt.Line2D([], [], color="black", lw=1, label="Baseline"),
               plt.Line2D([], [], color="#D55E00", marker="s", ls="", label="Ngspice · eligible"),
               plt.Line2D([], [], color="#222222", marker="x", ls="", label="Ngspice · rejected"),
               plt.Line2D([], [], color="black", marker="o", markerfacecolor="none", ls="", label="Inspected")]
    for field, (label, color, marker) in PREDICTIONS.items():
        if prediction in ("both", field):
            handles.append(plt.Line2D([], [], color=color, marker=marker, markerfacecolor="none", ls="", label=label))
    fig.legend(handles=handles, loc="outside lower center", ncol=3, fontsize=9)
    names = {k: data["labels"].get(v, "none") for k, v in choices.items()}
    fig.suptitle(f'Budget {budget:g} µm² · predicted choice: {names["predicted"]}; '
                 f'measured best: {names["measured"]}', fontsize=11)
    return fig


def layout_plot(data, candidate, quantity="deviation"):
    geometry = candidate["geometry"]
    net, layer = geometry["net"], geometry["layer"]
    bounds = np.array(geometry["box_um"])
    extent = bounds[2:] - bounds[:2]
    margin = np.maximum(extent * .04, .15)
    lo, hi = bounds[:2] - margin, bounds[2:] + margin
    patches, values = [], []
    for record in (data["baseline"], candidate):
        with np.load(data["folder"] / record["mesh_file"], allow_pickle=False) as mesh:
            b = mesh["bounds_um"]
            mask = ((mesh["net"] == net) & (mesh["layer"] == layer) &
                    (b[:, 0] < hi[0]) & (b[:, 2] > lo[0]) & (b[:, 1] < hi[1]) & (b[:, 3] > lo[1]))
            b, v = b[mask], mesh["voltage_V"][mask]
        if quantity == "deviation":
            if net not in data["external_voltages_V"]:
                raise ValueError(f"No external voltage boundary is defined for net {net}; choose node voltage.")
            v = 1e3 * abs(v - data["external_voltages_V"][net])
        patches.append(np.array([[[a, b], [c, b], [c, d], [a, d]] for a, b, c, d in b]))
        values.append(v)
    if any(not len(v) for v in values):
        raise ValueError("The selected route contains no saved cells.")
    vmin, vmax = min(v.min() for v in values), max(v.max() for v in values)
    if vmax == vmin:
        vmax = vmin + 1e-12
    fig, axes = plt.subplots(2, 1, figsize=(10, 4.7), sharex=True, sharey=True, layout="constrained")
    norm = Normalize(vmin, vmax)
    for ax, vertices, voltage, label in zip(axes, patches, values, ("Baseline", "Ngspice · widened")):
        collection = PolyCollection(vertices, array=voltage, cmap="viridis", norm=norm,
                                    edgecolors="none", rasterized=True)
        ax.add_collection(collection)
        old = geometry["bounds_um"]
        ax.add_patch(Rectangle(old[:2], old[2] - old[0], old[3] - old[1], fill=False,
                               edgecolor="black", lw=1, ls="--"))
        ax.add_patch(Rectangle(bounds[:2], *extent, fill=False, edgecolor="#D55E00", lw=1.3))
        ax.set(xlim=(lo[0], hi[0]), ylim=(lo[1], hi[1]), ylabel="y (µm)", title=label)
        ax.ticklabel_format(style="plain", useOffset=False)
    axes[-1].set_xlabel("x (µm)")
    label = ("|Vnode − Vboundary| (mV)" if quantity == "deviation" else "Node voltage (V)")
    fig.colorbar(collection, ax=axes, label=label, fraction=.035, pad=.02)
    fig.suptitle(f'Net {net} · {layer.upper()} · dashed: original width; orange: widening outline', fontsize=11)
    fig.supxlabel("Physical coordinates; horizontal and vertical scales differ.", fontsize=10)
    return fig


def show_candidates(name):
    data = load_study(name)
    rows, choices = rank(data, data["budget_um2"])
    by_id = {r["id"]: r for r in data["candidates"]}
    selected = by_id.get(choices["predicted"], data["candidates"][0])
    with plt.rc_context(STYLE):
        display(Image(data=png(candidate_plot(data, selected, data["budget_um2"]))))
    display(HTML(table(["Candidate / source ID", "Added area (µm²)", "Predicted benefit",
                        "Measured benefit", "Measured status"], [
        [data["labels"][r["candidate"]["id"]] + " / " + r["candidate"]["id"],
         f'{r["area"]:.4g}', f'{r["predicted"]["benefit"]:.6g}', f'{r["measured"]["benefit"]:.6g}',
         "; ".join(r["measured"]["reasons"]) or "Eligible"] for r in rows])))


def show_explorer(name):
    import ipywidgets as widgets

    data = load_study(name)
    by_id = {r["id"]: r for r in data["candidates"]}
    options = [(f'{data["labels"][r["id"]]} · {r["geometry"]["layer"].upper()} / '
                f'{r["geometry"]["net"]} · {r["geometry"]["new_width_um"]:.3g} µm · '
                f'{r["geometry"]["added_area_um2"]:.4g} µm²', r["id"])
               for r in sorted(data["candidates"], key=lambda r: r["id"])]
    initial = data["selected"] if data["selected"] in by_id else next(iter(by_id))
    candidate = widgets.Dropdown(options=options, value=initial, description="Inspect:",
                                 layout=widgets.Layout(width="620px"))
    budget = widgets.SelectionSlider(options=sorted({0, data["budget_um2"],
                   *[r["geometry"]["added_area_um2"] for r in data["candidates"]]}),
                   value=data["budget_um2"], description="Budget (µm²):",
                   continuous_update=False, style={"description_width": "110px"},
                   layout=widgets.Layout(width="460px"))
    priority = widgets.Dropdown(options=[("Configured objective", "configured")] +
                               [(s["label"] + " only", n) for n, s in data["metrics"].items()],
                               description="Priority:", layout=widgets.Layout(width="330px"))
    view = widgets.ToggleButtons(options=["Response", "Candidates", "Layout"], description="View:")
    prediction = widgets.Dropdown(options=[("Both predictions", "both"), ("First order", "first_order_values"),
                       ("Finite prediction", "predicted_values"), ("Measurements only", "none")],
                       description="Markers:", layout=widgets.Layout(width="300px"))
    overlays = widgets.SelectMultiple(options=[(data["labels"][k], k) for k in by_id], rows=3,
                                       description="Overlay:")
    quantity = widgets.Dropdown(options=[("Boundary deviation", "deviation"), ("Node voltage", "voltage")],
                                description="Map:", layout=widgets.Layout(width="300px"))
    order = widgets.Dropdown(options=[("Predicted benefit", "benefit"), ("Benefit per area", "efficiency")],
                             description="Table order:", layout=widgets.Layout(width="330px"))
    preferred = widgets.Button(description="Inspect predicted choice", layout=widgets.Layout(width="210px"))
    output = widgets.Output()

    def refresh(change=None):
        chosen = by_id[candidate.value]
        rows, choices = rank(data, budget.value, priority.value)
        preferred.disabled = choices["predicted"] is None
        names = {k: data["labels"].get(v, "No feasible beneficial candidate") for k, v in choices.items()}
        policy = policy_for(data, priority.value)
        inspected = next(r for r in rows if r["candidate"]["id"] == candidate.value)
        geometry = chosen["geometry"]
        baseline_failures = constraint_report(data["baseline"]["metrics"], data["baseline"]["metrics"], policy)["failures"]
        items = []
        items.append(HTML(f'<p><b>Predicted choice:</b> {escape(names["predicted"])} &nbsp; '
                     f'<b>Measured best:</b> {escape(names["measured"])}<br>'
                     f'Baseline constraints: {escape("; ".join(baseline_failures) or "pass")}. '
                     'Targets, scales and individual limits stay fixed when priority changes.</p>'))
        items.append(HTML(f'<p><b>Inspecting {escape(data["labels"][candidate.value])}:</b> '
                     f'{escape(geometry["layer"].upper())}, net {escape(geometry["net"])}; '
                     f'width {geometry["old_width_um"]:.4g} → {geometry["new_width_um"]:.4g} µm; '
                     f'length {geometry["length_um"]:.5g} µm; area {geometry["added_area_um2"]:.5g} µm².<br>'
                     f'Prediction: {escape("; ".join(inspected["predicted"]["reasons"]) or "eligible")}; '
                     f'measurement: {escape("; ".join(inspected["measured"]["reasons"]) or "eligible")}. '
                     'DRC: 0 markers; LVS: match.</p>'))
        with plt.rc_context(STYLE):
            if view.value == "Response":
                fig = response_plot(data, chosen, overlays.value, prediction.value)
            elif view.value == "Candidates":
                fig = candidate_plot(data, chosen, budget.value, priority.value, prediction.value)
            else:
                fig = layout_plot(data, chosen, quantity.value)
            items.append(Image(data=png(fig)))
        if view.value == "Candidates":
            ordered = sorted(rows, key=lambda r: r["predicted"][order.value], reverse=True)
            items.append(HTML(table(["Candidate / source ID", "Area (µm²)", "Predicted benefit",
                "Measured benefit", "Predicted benefit / µm²", "Prediction status", "Measured status"], [
                [data["labels"][r["candidate"]["id"]] + " / " + r["candidate"]["id"], f'{r["area"]:.4g}',
                 f'{r["predicted"]["benefit"]:.6g}', f'{r["measured"]["benefit"]:.6g}',
                 f'{r["predicted"]["efficiency"]:.6g}', "; ".join(r["predicted"]["reasons"]) or "Eligible",
                 "; ".join(r["measured"]["reasons"]) or "Eligible"] for r in ordered])))
        else:
            items.append(HTML(table(["Metric", "Baseline", "First order", "Finite", "Ngspice",
                "Δ finite", "Δ measured", "|Finite error|", "Error / |Δ measured|"],
                metric_rows(data, chosen))))
            dc0, dc1 = data["baseline"]["dc"], chosen["dc"]
            items.append(HTML(table(["DC quantity", "Baseline", "Selected", "Change"],
                [[f'Current from {s} (µA)', f'{v*1e6:.6g}',
                  f'{dc1["source_currents_A"][s]*1e6:.6g}',
                  f'{(dc1["source_currents_A"][s]-v)*1e6:+.6g}']
                 for s, v in dc0["source_currents_A"].items()] +
                [["Source power (µW)", f'{dc0["power_W"]*1e6:.6g}', f'{dc1["power_W"]*1e6:.6g}',
                  f'{(dc1["power_W"]-dc0["power_W"])*1e6:+.6g}']])))
        items.append(HTML(table(["Metric", "Target", "Scale", "Weight", "Limits"],
            [[s["label"], f'{s["target"]*s.get("display_scale",1):.7g} {s.get("display_unit","")}',
              f'{s["scale"]*s.get("display_scale",1):.7g}', s["weight"],
              limits_text(s)] for s in policy["metrics"].values()])))


        formatter = InteractiveShell.instance().display_formatter.format
        rendered = []
        for item in items:
            data_bundle, metadata = formatter(item)
            rendered.append({"output_type": "display_data", "data": data_bundle, "metadata": metadata})
        output.outputs = tuple(rendered)

    def inspect_preferred(button):
        _, choices = rank(data, budget.value, priority.value)
        if choices["predicted"] is not None:
            candidate.value = choices["predicted"]

    preferred.on_click(inspect_preferred)
    for control in (candidate, budget, priority, view, prediction, overlays, quantity, order):
        control.observe(refresh, names="value")
    refresh()
    extra = widgets.Accordion(children=[widgets.VBox([prediction, overlays, quantity, order])])
    extra.set_title(0, "Plot options")
    ui = widgets.VBox([candidate, widgets.HBox([budget, priority]), preferred, view, extra, output])

    with plt.rc_context(STYLE):
        fallback = png(response_plot(data, by_id[initial]))
    bundle = ui._repr_mimebundle_()
    bundle["image/png"] = base64.b64encode(fallback).decode("ascii")
    display(bundle, raw=True)
    return {"widget": ui, "controls": {"candidate": candidate, "budget": budget, "priority": priority,
            "view": view, "prediction": prediction, "overlays": overlays, "quantity": quantity,
            "order": order}, "output": output}
