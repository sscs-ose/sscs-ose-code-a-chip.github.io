"""Portable SKY130 device experiments and replay of native ngspice evidence.

Set SKY130_MODEL to sky130.lib.spice, or set PDK_ROOT to the directory that
contains sky130A. Set NGSPICE to an executable when it is not on PATH.
Run ``python scripts/device_lab.py check`` to check the included device results.
Run ``python scripts/device_lab.py regenerate --output work/device_run``
to launch native ngspice in a new output directory.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "device"
MODEL_MARKER = "${SKY130_MODEL}"
DC_PARAMETERS = ("id", "gm", "gds", "cgg", "vth", "vdsat")
CASES = ("lookup", "dropout", "sizing_initial", "sizing_final", "terminal_nmos", "terminal_pmos")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _physical_columns(frame: pd.DataFrame) -> pd.DataFrame:
    """Expose resistance rather than an output conductance display column."""
    frame = frame.copy()
    if "gds" in frame:
        frame["ro_ohm"] = np.divide(
            1.0, frame["gds"],
            out=np.full(len(frame), np.inf), where=frame["gds"].to_numpy() != 0,
        )
        frame = frame.drop(columns="gds")
    if "gm_gds" in frame:
        frame = frame.rename(columns={"gm_gds": "intrinsic_gain_v_per_v"})
    return frame


def load_gmid(data_dir: Path | str = DATA) -> pd.DataFrame:
    """Native device table with current, gm, ro, capacitance and bias axes."""
    return _physical_columns(pd.read_csv(Path(data_dir) / "lookup" / "measurements.csv"))


def lookup_at_gm_id(kind: str = "nmos", length_um: float = .3,
                    drain_v: float = .9, gm_id: float = 15.0,
                    data_dir: Path | str = DATA) -> dict:
    """Interpolate one unique characterized inversion bracket without extrapolation."""
    if kind not in ("nmos", "pmos"):
        raise ValueError("kind must be nmos or pmos")
    frame = load_gmid(data_dir)
    frame = frame[(frame.kind == kind) & np.isclose(frame.l, length_um)
                  & np.isclose(frame.vds, drain_v) & (frame.id > 1e-9)]
    return _interpolate_ratio(frame, gm_id)


def _interpolate_ratio(frame: pd.DataFrame, gm_id: float) -> dict:
    frame = frame.sort_values("vgs").reset_index(drop=True)
    if len(frame) < 2:
        raise ValueError("Requested bias slice is not characterized")
    values = frame.gm_id.to_numpy()
    exact = np.flatnonzero(np.isclose(values, gm_id, rtol=0, atol=1e-10))
    if len(exact) == 1:
        point = {k: float(frame.iloc[exact[0]][k]) for k in
                 ("vgs", "id", "gm", "id_w", "ro_ohm", "cgg_intrinsic", "w", "l", "vds")}
        point["gm_id_achieved"] = point["gm"] / point["id"]
        return point
    hit = np.flatnonzero((values[:-1] - gm_id) * (values[1:] - gm_id) < 0)
    if len(hit) != 1:
        raise ValueError(f"Expected one gm/Id bracket, found {len(hit)}")
    i = int(hit[0])
    fraction = (gm_id - values[i]) / (values[i + 1] - values[i])
    left, right = frame.iloc[i], frame.iloc[i + 1]
    point = {key: float(left[key] + fraction * (right[key] - left[key]))
             for key in ("vgs", "id", "gm", "id_w", "ro_ohm", "cgg_intrinsic", "w", "l", "vds")}
    point["gm_id_achieved"] = point["gm"] / point["id"]
    return point


def load_dropout(data_dir: Path | str = DATA) -> pd.DataFrame:
    """Native PFET current capacity over VSG and VSD, with source tied body."""
    return _physical_columns(pd.read_csv(Path(data_dir) / "dropout" / "measurements.csv"))


def dropout_summary(load_current_a: float = .05,
                    data_dir: Path | str = DATA) -> pd.DataFrame:
    """Initial width estimates from native current density, not LDO qualification."""
    if load_current_a <= 0:
        raise ValueError("Use a positive target current")
    frame = load_dropout(data_dir)
    frame = frame[np.isclose(frame.vds, .05) | np.isclose(frame.vds, .1)
                  | np.isclose(frame.vds, .2)].copy()
    result = pd.DataFrame({
        "VSG_V": frame.vgs,
        "VSD_V": frame.vds,
        "current_density_uA_per_um": frame.id_w * 1e6,
        "estimated_total_width_um": load_current_a / frame.id_w,
        "target_current_mA": load_current_a * 1e3,
    })
    return result.sort_values(["VSG_V", "VSD_V"]).reset_index(drop=True)


def load_sizing_history(data_dir: Path | str = DATA) -> pd.DataFrame:
    """Native sizing iterations in simulation order."""
    return pd.read_csv(Path(data_dir) / "sizing_iterations.csv")


def sizing_final(data_dir: Path | str = DATA) -> dict:
    """Independently recover the final sizing point from its native gate sweep."""
    frame = _physical_columns(pd.read_csv(Path(data_dir) / "sizing_final" / "measurements.csv"))
    return _interpolate_ratio(frame[frame.id > 1e-9], 15.0)


def sizing_comparison(data_dir: Path | str = DATA) -> pd.DataFrame:
    """Compare an initial width prediction with its actual native fixture and closure."""
    point = lookup_at_gm_id(data_dir=data_dir)
    target_current = 100e-6 / 15.0
    width = target_current / point["id_w"]
    initial = pd.read_csv(Path(data_dir) / "sizing_initial" / "measurements.csv").sort_values("vgs")
    if not np.allclose(initial.w, width):
        raise ValueError("Initial sizing fixture does not match the lookup width")
    initial_current = float(np.interp(point["vgs"], initial.vgs, initial.id))
    initial_gm = float(np.interp(point["vgs"], initial.vgs, initial.gm))
    final = sizing_final(data_dir)
    return pd.DataFrame([
        {"case": "Width scaling prediction", "width_um": width, "gate_V": point["vgs"],
         "current_uA": target_current * 1e6, "gm_uS": 100.0, "gm_id_per_V": 15.0,
         "evidence": "Initial calculation from native lookup current density"},
        {"case": "Actual first geometry", "width_um": width, "gate_V": point["vgs"],
         "current_uA": initial_current * 1e6, "gm_uS": initial_gm * 1e6,
         "gm_id_per_V": initial_gm / initial_current,
         "evidence": "Interpolation of native sweep at predicted gate bias"},
        {"case": "Sizing closure", "width_um": final["w"], "gate_V": final["vgs"],
         "current_uA": final["id"] * 1e6, "gm_uS": final["gm"] * 1e6,
         "gm_id_per_V": final["gm"] / final["id"],
         "evidence": "Native final geometry sweep with gm/Id restored"},
    ])


def _terminal_frame(folder: Path) -> tuple[pd.DataFrame, dict]:
    gate = np.atleast_2d(np.loadtxt(folder / "gate.tsv", skiprows=1))
    drain = np.atleast_2d(np.loadtxt(folder / "drain.tsv", skiprows=1))
    op = np.asarray(np.loadtxt(folder / "op.tsv", skiprows=1)).reshape(-1)
    if gate.shape != drain.shape or gate.shape[1] != 5:
        raise ValueError("Unexpected terminal current table dimensions")
    if not np.allclose(gate[:, 0], drain[:, 0]):
        raise ValueError("Terminal injection frequency grids differ")
    frequency = gate[:, 0]
    omega = 2 * np.pi * frequency
    frame = pd.DataFrame({
        "frequency_hz": frequency,
        "cgg_terminal_f": gate[:, 2] / omega,
        "cgd_transfer_f": -drain[:, 2] / omega,
        "cdg_transfer_f": -gate[:, 4] / omega,
        "cdd_terminal_f": drain[:, 4] / omega,
        "gm_terminal_s": gate[:, 3],
        "ro_terminal_ohm": 1 / drain[:, 3],
    })
    index = int(np.argmin(np.abs(frequency - 1e4)))
    summary = dict(frame.iloc[index])
    summary["cgg_intrinsic_op_f"] = float(op[6])
    summary["terminal_to_intrinsic_ratio"] = summary["cgg_terminal_f"] / float(op[6])
    summary["gate_voltage_V"] = float(op[1])
    summary["drain_voltage_V"] = float(op[2])
    return frame, summary


def load_terminal_response(kind: str = "nmos", data_dir: Path | str = DATA) -> pd.DataFrame:
    if kind not in ("nmos", "pmos"):
        raise ValueError("kind must be nmos or pmos")
    return _terminal_frame(Path(data_dir) / ("terminal_" + kind))[0]


def terminal_summary(data_dir: Path | str = DATA) -> pd.DataFrame:
    records = []
    for kind in ("nmos", "pmos"):
        _, values = _terminal_frame(Path(data_dir) / ("terminal_" + kind))
        records.append({"kind": kind, **values})
    return pd.DataFrame(records)


def verify_saved_data(data_dir: Path | str = DATA) -> dict:
    """Check source hashes, native table dimensions and documented landmarks."""
    data_dir = Path(data_dir)
    manifest = json.loads((ROOT / "FOUNDATIONAL_EVIDENCE.json").read_text())
    checked = 0
    for record in manifest["files"]:
        path = ROOT / record["published_path"]
        if _sha256(path) != record["published_sha256"]:
            raise ValueError(f"Evidence hash differs: {record['published_path']}")
        checked += 1
    table = load_gmid(data_dir)
    if len(table) != 6498 or len(table.groupby(["kind", "l", "vds"])) != 18:
        raise ValueError("Unexpected lookup grid")
    drop = dropout_summary(data_dir=data_dir)
    selected = drop[np.isclose(drop.VSG_V, 1.8) & np.isclose(drop.VSD_V, .1)].iloc[0]
    point = sizing_final(data_dir)
    terminal = terminal_summary(data_dir)
    if not np.isclose(selected.current_density_uA_per_um, 16.388752739441806, rtol=1e-10):
        raise ValueError("Saved dropout landmark changed")
    if not np.isclose(point["gm"], 99.9997928623085e-6, rtol=1e-8):
        raise ValueError("Saved sizing landmark changed")
    if not (terminal.cgg_terminal_f > terminal.cgg_intrinsic_op_f).all():
        raise ValueError("Unexpected terminal capacitance relationship")
    return {"native_evidence_files_verified": checked, "lookup_rows": len(table),
            "dropout_width_estimate_um": float(selected.estimated_total_width_um),
            "sizing_final_gm_uS": point["gm"] * 1e6,
            "evidence_class": "Replay of saved native ngspice compact model data"}


def native_tools() -> tuple[Path, Path]:
    """Discover public PDK and native executable without any laboratory dependency."""
    model_setting = os.environ.get("SKY130_MODEL")
    if model_setting:
        candidates = [Path(model_setting).expanduser()]
    else:
        base = os.environ.get("PDK_ROOT")
        if not base:
            raise RuntimeError("Set SKY130_MODEL to sky130.lib.spice, or set PDK_ROOT to its public PDK installation")
        root = Path(base).expanduser()
        candidates = [root / "sky130A/libs.tech/ngspice/sky130.lib.spice",
                      root / "libs.tech/ngspice/sky130.lib.spice",
                      root / "share/pdk/sky130A/libs.tech/ngspice/sky130.lib.spice"]
    model = next((p.resolve() for p in candidates if p.is_file()), None)
    if model is None:
        raise FileNotFoundError("No sky130.lib.spice found under the configured public PDK path")
    simulator = os.environ.get("NGSPICE") or shutil.which("ngspice")
    if not simulator:
        raise RuntimeError("Set NGSPICE to the native ngspice executable, or add ngspice to PATH")
    executable = Path(shutil.which(simulator) or simulator).expanduser().resolve()
    if not executable.is_file():
        raise FileNotFoundError("NGSPICE does not name an executable file")
    return executable, model


def _parse_dc(folder: Path, settings: dict) -> pd.DataFrame:
    raw = np.atleast_2d(np.loadtxt(folder / "table.tsv", skiprows=1))
    devices = settings["devices"]
    columns = 1 + len(devices) * len(DC_PARAMETERS)
    if raw.shape != (settings["points_per_device"], columns) or not np.isfinite(raw).all():
        raise ValueError("Unexpected native DC table shape or nonfinite output")
    frames = []
    for i, device in enumerate(devices):
        width = len(DC_PARAMETERS)
        frame = pd.DataFrame(raw[:, 1 + i * width:1 + (i + 1) * width], columns=DC_PARAMETERS)
        for key, value in device.items():
            frame[key] = value
        frame["vgs" if settings["sweep"] == "gate" else "vds"] = raw[:, 0]
        frame["id"] = frame.id.abs()
        frame["gm_id"] = frame.gm / frame.id.replace(0, np.nan)
        frame["id_w"] = frame.id / frame.w
        frame["gm_gds"] = frame.gm / frame.gds.replace(0, np.nan)
        frame["cgg_intrinsic"] = frame.cgg
        frame["ft_proxy_hz"] = frame.gm / (2 * np.pi * frame.cgg)
        frames.append(frame)
    result = pd.concat(frames, ignore_index=True)
    result.to_csv(folder / "measurements.csv", index=False)
    return result


def regenerate(output_dir: Path | str, cases: tuple[str, ...] = CASES) -> dict:
    """Run the curated transistor fixtures in native ngspice, preserving saved data."""
    executable, model = native_tools()
    output = Path(output_dir).resolve()
    if output == DATA.resolve() or DATA.resolve() in output.parents:
        raise ValueError("Choose a new work directory outside the included data")
    if output.exists() and any(output.iterdir()):
        raise FileExistsError("Choose an empty output directory for a fresh native run")
    if any(case not in CASES for case in cases):
        raise ValueError("Unknown characterization case")
    # ngspice accepts forward slashes on Windows. Backslashes in a quoted
    # include can be interpreted as escapes by the SPICE command parser.
    model_text = model.as_posix()
    if any(c in model_text for c in ('\n', '\r', '"')):
        raise ValueError("PDK path contains unsupported quote or newline")
    output.mkdir(parents=True, exist_ok=True)
    environment = os.environ.copy()
    version = subprocess.run([str(executable), "--version"], capture_output=True, text=True, timeout=20)
    results = []
    for case in cases:
        source = DATA / case
        folder = output / case
        folder.mkdir()
        template = (source / "fixture.spice").read_text()
        if template.count(MODEL_MARKER) != 1:
            raise ValueError("Expected one public PDK model placeholder")
        deck = template.replace(MODEL_MARKER, model_text)
        (folder / "fixture.spice").write_text(deck)
        # Prevent an unrelated user startup file from changing the fixture.
        initialization = folder / "init"
        initialization.mkdir()
        startup = "set ngbehavior=hsa\nset ng_nomodcheck\n"
        (initialization / "spinit").write_text(startup)
        (initialization / ".spiceinit").write_text(startup)
        (folder / ".spiceinit").write_text(startup)
        environment["SPICE_USERINIT_DIR"] = str(initialization)
        result = subprocess.run([str(executable), "-b", "fixture.spice"], cwd=folder,
                                env=environment, capture_output=True, text=True, timeout=300)
        log = result.stdout + result.stderr
        (folder / "ngspice.log").write_text(log)
        if result.returncode or re.search(r"(^|\n)\s*(?:fatal error|error:)", log, re.I):
            raise RuntimeError(f"Native ngspice failed for {case}. Inspect its saved log")
        settings = json.loads((source / "settings.json").read_text())
        if settings["analysis"] == "dc":
            rows = len(_parse_dc(folder, settings))
        else:
            frame, summary = _terminal_frame(folder)
            frame.to_csv(folder / "terminal_parameters.csv", index=False)
            (folder / "summary.json").write_text(json.dumps(summary, indent=2) + '\n')
            rows = len(frame)
        shutil.copyfile(source / "settings.json", folder / "settings.json")
        results.append({"case": case, "return_code": result.returncode, "rows": rows,
                        "deck_sha256": _sha256(folder / "fixture.spice")})
    report = {"evidence_class": "Fresh native ngspice compact model simulation",
              "simulator_version": version.stdout + version.stderr,
              "model_library_sha256": _sha256(model), "cases": results}
    (output / "native_run_manifest.json").write_text(json.dumps(report, indent=2) + '\n')
    return report


def figures(output_dir: Path | str | None = None, data_dir: Path | str = DATA,
            load_current_a: float = .05) -> dict:
    """Return three figures from native evidence. Saving is optional."""
    import matplotlib.pyplot as plt
    table = load_gmid(data_dir)
    fig1, axes = plt.subplots(1, 2, figsize=(10, 3.7), constrained_layout=True)
    for kind, axis in zip(("nmos", "pmos"), axes):
        for length in (.15, .3, 1.):
            rows = table[(table.kind == kind) & np.isclose(table.l, length)
                         & np.isclose(table.vds, .9) & (table.id > 1e-9)]
            axis.semilogx(rows.id_w * 1e6, rows.gm_id, label=f"L = {length:g} um")
        axis.set(title=kind.upper(), xlabel="Current density (uA/um)", ylabel="gm / Id (1/V)", ylim=(0, 30))
        axis.grid(alpha=.25)
        axis.legend()
    fig2, axes = plt.subplots(1, 2, figsize=(10, 3.7), constrained_layout=True)
    drop = load_dropout(data_dir)
    for gate, rows in drop.groupby("vgs"):
        axes[0].plot(rows.vds, rows.id_w * 1e6, label=f"VSG = {gate:g} V")
    axes[0].set(xlabel="VSD (V)", ylabel="Current density (uA/um)", title="PFET current capacity")
    axes[0].legend(fontsize=8)
    summary = dropout_summary(load_current_a=load_current_a, data_dir=data_dir)
    for drain, rows in summary.groupby("VSD_V"):
        axes[1].semilogy(rows.VSG_V, rows.estimated_total_width_um, 'o-', label=f"VSD = {drain:g} V")
    axes[1].set(xlabel="VSG (V)", ylabel="First width estimate (um)",
                title=f"{load_current_a * 1e3:g} mA current capacity estimate")
    axes[1].legend(fontsize=8)
    for axis in axes:
        axis.grid(alpha=.25)
    fig3, axes = plt.subplots(1, 2, figsize=(10, 3.7), constrained_layout=True)
    summaries = terminal_summary(data_dir).set_index("kind")
    for kind, axis in zip(("nmos", "pmos"), axes):
        response = load_terminal_response(kind, data_dir)
        axis.semilogx(response.frequency_hz, response.cgg_terminal_f * 1e15, label="Terminal capacitance")
        axis.axhline(summaries.loc[kind, "cgg_intrinsic_op_f"] * 1e15, color='tab:orange', label="Intrinsic operating parameter")
        axis.set(title=kind.upper(), xlabel="Frequency (Hz)", ylabel="Gate capacitance (fF)")
        axis.grid(alpha=.25)
        axis.legend(fontsize=8)
    result = {"gm_id": fig1, "dropout": fig2, "terminal_loading": fig3}
    if output_dir is not None:
        destination = Path(output_dir)
        destination.mkdir(parents=True, exist_ok=True)
        for name, fig in result.items():
            fig.savefig(destination / (name + '.png'), dpi=150)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("check", "summary", "figures", "regenerate"))
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.command == "check":
        print(json.dumps(verify_saved_data(), indent=2))
    elif args.command == "summary":
        print(json.dumps({"sizing": sizing_final(), "terminal": terminal_summary().to_dict('records'),
                          "dropout": dropout_summary().to_dict('records')}, indent=2))
    elif args.command == "figures":
        if args.output is None:
            parser.error("figures requires --output")
        figures(args.output)
    else:
        if args.output is None:
            parser.error("regenerate requires --output")
        print(json.dumps(regenerate(args.output), indent=2))


if __name__ == "__main__":
    main()
