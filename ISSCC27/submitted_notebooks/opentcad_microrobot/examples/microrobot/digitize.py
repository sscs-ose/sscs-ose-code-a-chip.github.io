"""Reproducible color-trace extraction from the supplied supplementary PDF.

Native raster coordinates, explicit tick calibration and pixel sensitivities
are retained. This reconstructs plotted data, not the authors' raw samples.
Requires Poppler pdfimages only for re-extraction; generated CSV is portable.
"""
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image

from opentcad.device.compact import fit_single_diode

HERE = Path(__file__).parent


def extract(pdf, destination):
    pdf, dest = Path(pdf), Path(destination)
    dest.mkdir(parents=True, exist_ok=True)
    calibration = json.loads((HERE / "data/s2e_calibration.json").read_text())
    if hashlib.sha256(pdf.read_bytes()).hexdigest() != calibration["source_pdf_sha256"]:
        raise ValueError("PDF differs from the calibrated source; inspect/recalibrate its figure")
    executable = shutil.which("pdfimages")
    if not executable:
        raise FileNotFoundError("Poppler pdfimages is needed to re-extract the source figure")
    with tempfile.TemporaryDirectory(prefix="opentcad-s2-") as temporary:
        prefix = str(Path(temporary) / "s2")
        subprocess.run([executable, "-f", "8", "-l", "8", "-png", str(pdf), prefix],
                       check=True, capture_output=True)
        pixels = np.asarray(Image.open(prefix + "-000.png").convert("RGB"), dtype=float)
    if pixels.shape[:2] != (calibration["native_image_height_px"],
                             calibration["native_image_width_px"]):
        raise ValueError("Unexpected embedded-image size")
    xmap = np.polyfit(calibration["x_ticks_px"], calibration["x_tick_voltage_V"], 1)
    ymap = np.polyfit(calibration["y_ticks_px"], calibration["y_tick_terminal_current_A"], 1)
    red, green, blue = pixels.transpose(2, 0, 1)
    masks = {0: (blue-red > 30) & (blue-green > 15) & (blue > 70),
             1000: (red-green > 50) & (red-blue > 50) & (red > 130)}
    x0, y0, x1, y1 = calibration["plot_roi_px"]
    rows = []
    for light, mask in masks.items():
        # Keep only one sample per four native columns. Neighboring points
        # are still correlated raster samples, not independent measurements.
        for x in range(x0, x1, 4):
            ys = np.flatnonzero(mask[y0:y1, x]) + y0
            exclusion = calibration["legend_exclusion"]
            if x < exclusion["x_below_px"]:
                ys = ys[ys >= exclusion["y_below_px"]]
            if not len(ys):
                continue
            y = float(np.median(ys))
            rows.append((light, np.polyval(xmap, x), np.polyval(ymap, y), x, y))
    data = np.asarray(rows)
    if min(np.count_nonzero(data[:, 0] == light) for light in (0, 1000)) < 50:
        raise RuntimeError("Too few curve points: source/color calibration needs review")
    np.savetxt(dest / "s2e_digitized.csv", data, delimiter=",",
               header="irradiance_W_m2,voltage_V,terminal_current_A,x_px,y_px", comments="")
    return fit_digitized(data, dest, calibration=calibration)


def fit_digitized(data, destination, *, calibration=None):
    """Re-fit the redistributable numerical CSV without requiring the PDF."""
    dest = Path(destination)
    dest.mkdir(parents=True, exist_ok=True)
    if isinstance(data, (str, Path)):
        data = np.loadtxt(data, delimiter=",", skiprows=1)
    data = np.asarray(data, dtype=float)
    if calibration is None:
        calibration = json.loads((HERE / "data/s2e_calibration.json").read_text())
    xmap = np.polyfit(calibration["x_ticks_px"], calibration["x_tick_voltage_V"], 1)
    ymap = np.polyfit(calibration["y_ticks_px"], calibration["y_tick_terminal_current_A"], 1)
    # Current floor reflects axes + curve thickness/JPEG artifacts. Horizontal
    # uncertainty is evaluated separately through perturbed calibrations.
    current_floor = abs(ymap[0]) * calibration["curve_position_uncertainty_px"]
    sigma_v = abs(xmap[0]) * calibration["axis_position_uncertainty_px"]
    effective_sigma = np.full(len(data), current_floor)
    for light in (0, 1000):
        select = data[:, 0] == light
        slope = np.gradient(data[select, 2], data[select, 1])
        effective_sigma[select] = np.hypot(current_floor, slope*sigma_v)
    fit, metrics = fit_single_diode(data[:, 1], -data[:, 2], data[:, 0],
        series_cells=2, temperature_K=calibration["fit_temperature_K"],
        uncertainty_A=effective_sigma)
    rng = np.random.default_rng(2022)
    trials = []
    for _ in range(48):
        # Global axis offsets and point-level trace position are separate
        # sensitivity perturbations, not an experimental noise model.
        xshift = rng.uniform(-2, 2) + rng.uniform(-3, 3, len(data))
        yshift = rng.uniform(-2, 2) + rng.uniform(-3, 3, len(data))
        model, _ = fit_single_diode(data[:, 1] + xshift*xmap[0],
            -(data[:, 2] + yshift*ymap[0]), data[:, 0], series_cells=2,
            temperature_K=calibration["fit_temperature_K"], uncertainty_A=effective_sigma)
        trials.append([model.saturation_A, model.ideality, model.photocurrent_A,
                       model.open_circuit_V(), model.maximum_power_point()[2]])
    trials = np.asarray(trials)
    np.savetxt(dest / "pv_sensitivity_samples.csv", trials, delimiter=",",
               header="saturation_A,ideality,photocurrent_A,pair_Voc_V,pair_Pmax_W", comments="")
    sensitivity = {name: {"min": float(values.min()), "max": float(values.max())}
                   for name, values in zip(("saturation_A", "ideality", "photocurrent_A",
                                            "pair_Voc_V", "pair_Pmax_W"), trials.T)}
    summary = {"source": calibration, "fitted_terminal_model": asdict(fit),
               "fit_metrics": metrics, "pair_Voc_V": fit.open_circuit_V(),
               "digitization_current_floor_A": current_floor,
               "digitization_voltage_scale_V": sigma_v,
               "fit_weights": "quadrature current floor and observed dI/dV times voltage scale",
               "pair_MPP_V_A_W": fit.maximum_power_point(),
               "sensitivity": sensitivity, "sensitivity_trials": len(trials),
               "limitations": ["Ideal diode with Rs=0 and infinite shunt resistance",
                   "Assumed 300 K; no temperature calibration", "Raster points are correlated",
                   "Sensitivity ranges are not confidence intervals",
                   "Terminal fit does not calibrate a unique TCAD structure or small logic PV"]}
    (dest / "pv_fit.json").write_text(json.dumps(summary, indent=2) + "\n")
    (dest / "pv_pair.spice").write_text(fit.spice_subcircuit("published_pv_pair"))
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2), layout="constrained")
    for light, color in ((0, "#4345a1"), (1000, "#d94435")):
        select = data[:, 0] == light
        v, i = data[select, 1], data[select, 2]
        axes[0].plot(v, i*1e9, ".", color=color, alpha=0.55,
                     label=f"S2E digitized: {light} W/m²")
        grid = np.linspace(v.min(), v.max(), 400)
        axes[0].plot(grid, -fit.current_A(grid, light)*1e9, color=color,
                     label=f"terminal fit: {light} W/m²")
        axes[1].plot(v, (-fit.current_A(v, light)-i)/effective_sigma[select], ".", color=color)
    axes[0].set(xlabel="Series-pair voltage (V)", ylabel="Current entering PV pair (nA)",
                ylim=(-180, 420), title="Published two-cell PV: digitization and terminal fit")
    axes[0].legend(fontsize=8)
    axes[1].axhspan(-1, 1, color="0.8", alpha=0.4)
    axes[1].set(xlabel="Series-pair voltage (V)", ylabel="Residual / digitization scale",
                title="Residual includes current and voltage pixel scales")
    fig.savefig(dest / "pv_fit.png", dpi=170)
    plt.close(fig)
    # Acceptance against caption anchors, with their approximate precision.
    assert abs(fit.open_circuit_V() - 1.24) < 0.025
    assert abs(fit.photocurrent_A / 150e-9 - 1) < 0.1
    assert metrics["weighted_rms_residual"] < 2
    return fit, summary


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdf", type=Path, help="Re-extract from the supplied PDF instead of CSV")
    parser.add_argument("--csv", type=Path, default=HERE / "data/s2e_digitized.csv")
    parser.add_argument("--output", type=Path, default=HERE / "local_runs/published")
    args = parser.parse_args()
    _, report = extract(args.pdf, args.output) if args.pdf else fit_digitized(args.csv, args.output)
    print(json.dumps({k: report[k] for k in ("fitted_terminal_model", "fit_metrics",
                                           "pair_Voc_V", "pair_MPP_V_A_W")}, indent=2))
