"""Display report tables directly from the frozen numerical evidence."""
import hashlib
from html import escape
from importlib.metadata import version
import json
from pathlib import Path
from IPython.display import display, HTML, Image

HERE = Path(__file__).resolve().parent
EVIDENCE = HERE / "evidence"
ASSETS = HERE / "report_assets"


def read(name):
    return json.loads((EVIDENCE / f"{name}.json").read_text())


def table(headers, rows):
    def row(values, tag):
        return "<tr>" + "".join(f"<{tag}>{escape(str(v))}</{tag}>" for v in values) + "</tr>"
    display(HTML('<div class="table-wrap"><table>' + row(headers, "th") +
                 "".join(row(values, "td") for values in rows) + "</table></div>"))


def figure(name):
    display(Image(filename=str(ASSETS / f"{name}.png")))
    if name == "ground_layout":
        display(Image(filename=str(EVIDENCE / "ground_return_schematic.png")))


def verify():

    for folder in (EVIDENCE, ASSETS, HERE.parent/"recorded_runs"):
        manifest = json.loads((folder / "manifest.json").read_text())
        for name, expected in manifest.items():
            if hashlib.sha256((folder / name).read_bytes()).hexdigest() != expected:
                raise ValueError(f"Evidence differs from its manifest: {folder / name}")


def render(name):
    ground, ac = read("ground_return"), read("ac_sensitivity")
    analog = read("analog_inverter")
    metadata = json.loads((ASSETS / "report_metadata.json").read_text())
    if name == "authors":
        authors = json.loads((HERE / "authors.json").read_text())
        names = escape(", ".join(f'{name} ({authors["emails"][name]})'
                                 for name in authors["authors"]))
        affiliations = "<br>".join(escape(a) for a in authors["affiliations"])
        display(HTML('<p style="font-family:Georgia,serif;font-size:16px;line-height:1.5">'
                     f"<strong>{names}</strong><br>{affiliations}<br>"
                     f'Team representative: {escape(authors["representative"])}</p>'))
    elif name == "model_table":

        rho = metadata["sheet_ohms_per_square"] | {"m4": 0.047, "m5": 0.029}
        cuts = metadata["contact_ohms_per_cut"] | {"via3": 3.41, "via4": 0.38}
        table(["Component", "Representation", "Parameter or boundary"], [
            ["LI / M1 / M2", "Finite-volume sheets",
             " / ".join(f"{rho[k]:g}" for k in ("li","m1","m2")) + " Ω/□"],
            ["M3 / M4 / M5", "Finite-volume sheets",
             " / ".join(f"{rho[k]:g}" for k in ("m3","m4","m5")) + " Ω/□"],
            ["MCON / VIA1", "Finite cut conductances",
             " / ".join(f"{cuts[k]:g}" for k in ("mcon","m2c")) + " Ω/cut"],
            ["VIA2 / VIA3 / VIA4", "Finite cut conductances",
             " / ".join(f"{cuts[k]:g}" for k in ("m3c","via3","via4")) + " Ω/cut"],
            ["N / P diffusion contacts", "Explicit cuts at device terminals",
             f'{cuts["ndc,nsc"]:g} / {cuts["pdc,psc"]:g} Ω/cut'],
            ["MOS / poly resistor", "Pinned compact models", "Internal access/end resistance in device models"],
            ["AC capacitance", "Intrinsic device + declared output load", "Routing capacitance omitted"],
            ["External pin patches", "Equipotential regions", "Driven patches fixed; free output voltages solved"]])
    elif name == "operations_table":
        table(["Quantity", "How it is obtained", "Role in the calculation"], [
            ["Geometry and material parameters", "Read the layout, terminal map and pinned technology data",
             "Define the network resistors and fixed boundaries"],
            ["Baseline voltages and device currents", "Solve the connected operating point in ngspice",
             "Establish the bias for measurement and linearization"],
            ["Metric value m", "Apply the declared measurement to the native circuit result",
             "Record the baseline characteristic in its physical units"],
            ["Device-current derivatives", "Query native small-signal terminal responses at the saved bias",
             "Describe how device loading changes with terminal voltage"],
            ["Current-balance Jacobian K", "Assemble network conductances and device derivatives",
             "Relate node-voltage changes to current-imbalance changes"],
            ["Metric derivative q for a DC metric", "Differentiate the measurement using native device derivatives",
             "Weight the voltage changes by their effect on the metric"],
            ["Adjoint vector λ for a DC metric", "Solve Kᵀ λ = q",
             "Combine electrical propagation with the selected metric response"],
            ["Device AC admittance and bias derivatives", "Native terminal queries at each frequency; central DC bias perturbations",
             "Describe the frequency response and its dependence on terminal bias"],
            ["AC adjoint ψ", "Solve Aᵀ ψ = c at the measurement frequency",
             "Evaluate direct wire sensitivity and the bias-weighting vector qℓ"],
            ["DC bias adjoint for an AC metric", "Solve Kᵀ λℓ = qℓ",
             "Include the operating-point shift in the AC response derivative"],
            ["Per-resistor metric derivatives", "Evaluate local endpoint products and any explicit metric term",
             "Estimate the response to each conductance or resistance change"],
            ["First-order candidate estimate", "Sum baseline metric derivatives times mapped resistance changes",
             "Screen every generated span–width candidate"],
            ["Finite candidate prediction", "Check and remesh geometry; reduce the network; update bias and device admittance",
             "Refine the configured candidates with the same calculation for each topology"],
            ["Measured candidate metrics", "Verify the modified layout and run the connected native circuit",
             "Assess the saved prediction against the changed physical model"]])
    elif name == "conditions_table":
        table(["Case", "Supply", "Fixed input / bias", "Load", "Area budget", "Native simulator"], [
            ["Common-source amplifier", "1.2 V", "VIN = 0.954725 V", "1 pF", "10 µm²", "ngspice 47"],
            ["Inverter amplifier", "1.8 V", "VIN = 0.89 V", "100 fF", "4 µm²", "ngspice 47"]])
    elif name == "inverter_table":
        rows = [["Baseline", ".14", "0", f'{analog["cases"]["long"]["metrics"]["vout_V"]:.6f}',
                 f'{ac["baseline"]["metrics"]["gain_dB"]:.7f}',
                 f'{ac["baseline"]["metrics"]["unity_Hz"]/1e9:.6f}',
                 f'{analog["cases"]["long"]["metrics"]["supply_current_A"]*1e6:.4f}']]
        for a in ac["actions"]:
            dc=analog["cases"][a["id"]]["metrics"]; m=a["measured_values"]
            rows.append([a["id"],f'{a["geometry"]["new_width_um"]:.2f}',
                         f'{a["geometry"]["added_area_um2"]:.2f}',f'{dc["vout_V"]:.6f}',
                         f'{m["gain_dB"]:.7f}',f'{m["unity_Hz"]/1e9:.6f}',
                         f'{dc["supply_current_A"]*1e6:.4f}'])
        table(["Case", "Width (µm)", "Area (µm²)", "Vout (V)", "Gain (dB)", "fu (GHz)", "I (µA)"], rows)
    elif name == "ground_table":
        rows=[]
        records=[("baseline",0,ground["baseline"]["metrics"],ground["baseline_DC"]["metrics"])]
        records += [(a["id"],a["geometry"]["added_area_um2"],a["measured_values"],a["DC"])
                    for a in ground["actions"]]
        for label,area,m,dc in records:
            rows.append([label,f"{area:g}",f'{m["gain_dB"]:.6f}',f'{m["unity_Hz"]/1e6:.6f}',
                         f'{dc["supply_current_A"]*1e6:.4f}',f'{dc["local_vss_V"]*1e3:.4f}'])
        table(["Case", "Area (µm²)", "Gain (dB)", "fu (MHz)", "I (µA)", "Local ground (mV)"],rows)
    elif name == "validation_table":
        nominal=ground["actions"]; refined=list(ground["refinement"]["actions"].values())
        both=nominal+refined
        g=max(r["errors"]["gain_change_relative_error"] for r in both)*100
        f=max(r["errors"]["unity_change_relative_error"] for r in both)*100
        mesh=max(max(r["metric_change_mesh_error"]) for r in refined)*100
        sensitivity=max(max(r["sensitivity_mesh_relative_change"]) for r in ground["local_derivatives"].values())*100
        local=max(max(r["relative_error"]) for r in ground["local_derivatives"].values())*100
        table(["Check", "Observed error", "Limit", "Comparison"], [
            ["Inverter local gain derivative", f'{ac["derivative_check"]["relative_error"][0]*100:.5f}%', "1%", "Central ngspice perturbation"],
            ["Inverter local frequency derivative", f'{ac["derivative_check"]["relative_error"][1]*100:.5f}%', "1%", "Central ngspice perturbation"],
            ["Ground-return local derivatives", f"{local:.5f}%", "1%", "Two electrical resistor groups"],
            ["Ground-return corrected gain change", f"{g:.5f}%", "3%", "Nominal + checked finer meshes"],
            ["Ground-return corrected frequency change", f"{f:.5f}%", "3%", "Nominal + checked finer meshes"],
            ["Ground-return finite changes under refinement", f"{mesh:.5f}%", "2%", "Selected physical actions"],
            ["Ground-return sensitivities under refinement", f"{sensitivity:.5f}%", "2%", "Two electrical resistor groups"]])
    elif name == "tools_table":
        table(["Tool / data", "Version / revision", "Role"], [
            ["ngspice", "47", "Coupled DC, AC and transient simulation"],
            ["KLayout", "0.30.12 (native + Python)", "PCell geometry, DRC/LVS and mesh access"],
            ["Xschem", "3.4.4", "Editable schematics and native netlists"],
            ["SKY130A / open_pdks", "1e3554706ddbb2529193bdabbc7128296f3cb44a", "Device models and technology data"],
            ["Python", "3.12", "Tool coordination and numerical processing"],
            ["NumPy / SciPy", f'{version("numpy")} / {version("scipy")}', "Arrays and sparse linear algebra"]])
    elif name == "provenance":
        table(["Evidence", "Record"], [
            ["Inverter DC / AC", "October 27, 2026; predictions and native comparisons"],
            ["Ground-return DC / AC", "October 28, 2026; predictions and native comparisons"],
            ["Report-only AC sweeps", "Same accepted decks; saved full curves and source hashes"],
            ["Payload check", "Curated evidence and report-asset manifests verified on notebook execution"]])
    else:
        raise ValueError(f"Unknown report display: {name}")
