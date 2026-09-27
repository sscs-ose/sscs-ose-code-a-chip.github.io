#!/usr/bin/env python3
"""Run reproducible SKY130 PTAT transistor-level temperature sweeps.

This runner creates NEW simulation evidence. It never overwrites retained run-221
evidence unless the caller explicitly chooses the same output path.
"""
from __future__ import annotations
import argparse, copy, csv, hashlib, json, os, re, shutil, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SPICE = ROOT / "spice"
PLACEHOLDER_RE = re.compile(r"__[A-Z][A-Z0-9_]*__")


def parse_temps(spec: str) -> list[float]:
    if ":" not in spec:
        vals = [float(x) for x in spec.split(",") if x.strip()]
    else:
        a, b, s = (float(x) for x in spec.split(":"))
        if s <= 0 or b < a:
            raise ValueError("temperature range must be start:stop:positive_step")
        vals, x = [], a
        while x <= b + abs(s) * 1e-9:
            vals.append(round(x, 10))
            x += s
    if len(vals) < 2 or any(not (-273.15 < x < 1000) for x in vals):
        raise ValueError("invalid temperature grid")
    if vals != sorted(set(vals)):
        raise ValueError("temperature grid must be strictly increasing")
    return vals


def discover_model_lib() -> Path:
    direct = os.environ.get("SKY130_MODEL_LIB")
    if direct:
        p = Path(direct).expanduser().resolve()
        if p.is_file():
            return p
        raise FileNotFoundError(f"SKY130_MODEL_LIB does not exist: {p}")
    roots = []
    for env in ("PDK_ROOT", "PDKPATH"):
        if os.environ.get(env):
            roots.append(Path(os.environ[env]).expanduser())
    roots += [Path.home()/".volare", Path.home()/".ciel"]
    candidates = []
    for root in roots:
        candidates += [
            root/"sky130A"/"libs.tech"/"ngspice"/"sky130.lib.spice",
            root/"libs.tech"/"ngspice"/"sky130.lib.spice",
        ]
        if root.exists():
            candidates += list(
                root.glob(
                    "sky130/versions/*/sky130A/libs.tech/ngspice/"
                    "sky130.lib.spice"
                )
            )
    for p in candidates:
        if p.is_file():
            return p.resolve()
    raise FileNotFoundError(
        "Cannot locate sky130.lib.spice. Set SKY130_MODEL_LIB or PDK_ROOT."
    )


def prepare_ngspice_environment(output_dir: Path) -> tuple[dict[str, str], Path]:
    """Create an isolated ngspice HOME with SKY130 compatibility enabled."""
    runtime_home = (output_dir / "ngspice_home").resolve()
    runtime_home.mkdir(parents=True, exist_ok=True)
    spiceinit = runtime_home / ".spiceinit"
    spiceinit.write_text("set ngbehavior=hsa\n", encoding="utf-8")
    env = os.environ.copy()
    env["HOME"] = str(runtime_home)
    return env, spiceinit


def load_design() -> dict:
    return json.loads(
        (ROOT/"design_requirements.json").read_text(encoding="utf-8")
    )


def characterization_seed(
    linear_scale: float = 1.0,
    *,
    sensor_linear_scale: float | None = None,
    mirror_linear_scale: float | None = None,
    mirror_length_multiplier: float = 1.0,
    vdd_v: float | None = None,
    branch_current_a: float | None = None,
    reference_current_a: float | None = None,
) -> dict:
    """Return the nominal seed with explicit geometry overrides.

    Scaling W and L by the same factor preserves nominal W/L and the 8:1
    sensor width ratio while increasing device area as scale**2. An additional
    mirror-length multiplier increases mirror L without changing its W. This is used
    only for explicit sizing studies unless design_requirements.json itself is
    changed after verification.
    """
    if not math_isfinite_positive(linear_scale):
        raise ValueError("device linear scale must be a finite positive number")
    sensor_scale = (
        linear_scale if sensor_linear_scale is None else sensor_linear_scale
    )
    mirror_scale = (
        linear_scale if mirror_linear_scale is None else mirror_linear_scale
    )
    if not math_isfinite_positive(sensor_scale):
        raise ValueError("sensor linear scale must be a finite positive number")
    if not math_isfinite_positive(mirror_scale):
        raise ValueError("mirror linear scale must be a finite positive number")
    if not math_isfinite_positive(mirror_length_multiplier):
        raise ValueError("mirror length multiplier must be finite and positive")
    seed = copy.deepcopy(load_design()["nominal_characterization_seed"])
    overrides = {
        "vdd_v": vdd_v,
        "branch_current_a": branch_current_a,
        "reference_current_a": reference_current_a,
    }
    for key, value in overrides.items():
        if value is None:
            continue
        if not math_isfinite_positive(value):
            raise ValueError(f"{key} must be a finite positive number")
        seed[key] = float(value)
    sensor = seed["sensor_nmos"]
    mirror = seed["mirror_pmos"]
    sensor["l_um"] *= sensor_scale
    sensor["w_small_um"] *= sensor_scale
    sensor["w_large_um"] *= sensor_scale
    mirror["l_um"] *= mirror_scale * mirror_length_multiplier
    mirror["w_um"] *= mirror_scale
    return seed


def math_isfinite_value(value: float) -> bool:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return False
    return -float("inf") < number < float("inf")


def math_isfinite_positive(value: float) -> bool:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return False
    return number > 0.0 and number < float("inf")


def seed_geometry(seed: dict) -> dict:
    sensor = seed["sensor_nmos"]
    mirror = seed["mirror_pmos"]
    return {
        "sensor_nmos": {
            "l_um": sensor["l_um"],
            "w_small_um": sensor["w_small_um"],
            "w_large_um": sensor["w_large_um"],
        },
        "mirror_pmos": {
            "l_um": mirror["l_um"],
            "w_um": mirror["w_um"],
        },
    }


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def pdk_revision(model_lib: Path) -> str:
    explicit = os.environ.get("SKY130_PDK_REVISION", "").strip()
    if explicit:
        return explicit
    parts = model_lib.resolve().parts
    if "versions" in parts:
        index = parts.index("versions")
        if index + 1 < len(parts):
            return parts[index + 1]
    return "unknown"


def ngspice_version(ngspice: str) -> str:
    proc = subprocess.run([ngspice, "-v"], text=True, capture_output=True)
    if proc.returncode != 0:
        raise RuntimeError(
            f"ngspice version query failed with exit code {proc.returncode}"
        )
    lines = (proc.stdout + "\n" + proc.stderr).splitlines()
    for line in lines:
        match = re.search(
            r"\bngspice(?:\s+release)?[-\s]+(\d+(?:\.\d+)*)\b",
            line,
            flags=re.IGNORECASE,
        )
        if match:
            return f"ngspice {match.group(1)}"
    raise RuntimeError("unable to parse ngspice version from 'ngspice -v'")


def render(
    mode: str,
    corner: str,
    temps: list[float],
    output_rel: str,
    model_lib: Path,
    device_linear_scale: float = 1.0,
    *,
    sensor_linear_scale: float | None = None,
    mirror_linear_scale: float | None = None,
    mirror_length_multiplier: float = 1.0,
    vdd_v: float | None = None,
    branch_current_a: float | None = None,
    reference_current_a: float | None = None,
) -> str:
    seed = characterization_seed(
        device_linear_scale,
        sensor_linear_scale=sensor_linear_scale,
        mirror_linear_scale=mirror_linear_scale,
        mirror_length_multiplier=mirror_length_multiplier,
        vdd_v=vdd_v,
        branch_current_a=branch_current_a,
        reference_current_a=reference_current_a,
    )
    template = SPICE / (
        "ptat_sky130_mirror.template.spice"
        if mode == "mirror"
        else "ptat_sky130.template.spice"
    )
    text = template.read_text(encoding="utf-8")
    replacements = {
        "__MODEL_LIB__": model_lib.as_posix(),
        "__CORNER__": corner,
        "__VDDVAL__": str(seed["vdd_v"]),
        "__IBIAS__": str(seed["branch_current_a"]),
        "__IREF__": str(seed["reference_current_a"]),
        "__LCH__": str(seed["sensor_nmos"]["l_um"]),
        "__LNS__": str(seed["sensor_nmos"]["l_um"]),
        "__WNS1__": str(seed["sensor_nmos"]["w_small_um"]),
        "__WNS2__": str(seed["sensor_nmos"]["w_large_um"]),
        "__W1__": str(seed["sensor_nmos"]["w_small_um"]),
        "__W2__": str(seed["sensor_nmos"]["w_large_um"]),
        "__LPM__": str(seed["mirror_pmos"]["l_um"]),
        "__WPM__": str(seed["mirror_pmos"]["w_um"]),
        "__OUTPUT_CSV__": output_rel,
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    tline = "foreach t " + " ".join(f"{x:g}" for x in temps)
    text, n = re.subn(r"(?m)^foreach t .*$", tline, text, count=1)
    leftovers = PLACEHOLDER_RE.findall(text)
    if n != 1 or leftovers:
        raise RuntimeError(
            f"template rendering failed for {mode}/{corner}; "
            f"unresolved={leftovers}"
        )
    return text


def validate_csv(path: Path, temps: list[float], mode: str) -> None:
    with path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f, skipinitialspace=True))
    if not rows:
        raise RuntimeError(f"{path}: no simulation rows")
    got = [float(r["temp_c"]) for r in rows]
    if len(got) != len(temps) or any(
        abs(a-b) > 1e-8 for a, b in zip(got, temps)
    ):
        raise RuntimeError(f"{path}: unexpected temperature grid")
    required = {
        "temp_c",
        "vgs_small_v",
        "vgs_large_v",
        "dvgs_v",
        "supply_current_a",
        "power_w",
    }
    if mode == "mirror":
        required |= {"branch_small_a", "branch_large_a"}
    if not required.issubset(rows[0]):
        raise RuntimeError(f"{path}: missing expected columns")
    try:
        numeric_rows = [
            {key: float(row[key]) for key in required}
            for row in rows
        ]
    except (TypeError, ValueError, KeyError) as exc:
        raise RuntimeError(f"{path}: non-numeric simulation data") from exc
    if not all(
        math_isfinite_value(value)
        for row in numeric_rows
        for value in row.values()
    ):
        raise RuntimeError(f"{path}: non-finite simulation data")
    for row in numeric_rows:
        derived_dvgs = row["vgs_small_v"] - row["vgs_large_v"]
        if abs(row["dvgs_v"] - derived_dvgs) > 2.0e-6:
            raise RuntimeError(
                f"{path}: dvgs_v is inconsistent with the recorded VGS values"
            )


def capture_csv_export(netlist: str) -> tuple[str, str]:
    """Export rows through stdout instead of repeated filesystem appends."""
    headers = re.findall(r'(?m)^echo "([^"]+)" > results/.*$', netlist)
    if len(headers) != 1:
        raise RuntimeError("template must have one CSV header export")
    netlist = re.sub(r'(?m)^echo "[^"]+" > results/.*$', "", netlist)
    netlist, count = re.subn(
        r"(?m)^  echo (\$t.*) >> results/.*$",
        r"  echo PTAT_CSV \1", netlist,
    )
    if count != 1:
        raise RuntimeError("template must have one CSV data-row export")
    return netlist, headers[0]


def write_captured_csv(path: Path, header: str, stdout: str,
                       temps: list[float], mode: str) -> None:
    rows = [line.removeprefix("PTAT_CSV ") for line in stdout.splitlines()
            if line.startswith("PTAT_CSV ")]
    path.write_text(header + "\n" + "\n".join(rows) + "\n", encoding="utf-8")
    validate_csv(path, temps, mode)


def run_one(
    mode: str,
    corner: str,
    temps: list[float],
    output_dir: Path,
    model_lib: Path,
    ngspice: str,
    device_linear_scale: float = 1.0,
    *,
    sensor_linear_scale: float | None = None,
    mirror_linear_scale: float | None = None,
    mirror_length_multiplier: float = 1.0,
    vdd_v: float | None = None,
    branch_current_a: float | None = None,
    reference_current_a: float | None = None,
) -> Path:
    output_dir = output_dir.resolve()
    results_root = (ROOT/"results").resolve()
    try:
        output_dir.relative_to(results_root)
    except ValueError as exc:
        raise ValueError(
            "--output-dir must be inside the project results directory"
        ) from exc
    output_dir.mkdir(parents=True, exist_ok=True)
    netdir = output_dir/"netlists"
    logdir = output_dir/"logs"
    netdir.mkdir(exist_ok=True)
    logdir.mkdir(exist_ok=True)
    csv_path = output_dir/f"ptat_{mode}_{corner}.csv"
    output_rel = csv_path.relative_to(results_root).as_posix()
    net = netdir/f"ptat_{mode}_{corner}.spice"
    netlist, header = capture_csv_export(
        render(
            mode,
            corner,
            temps,
            output_rel,
            model_lib,
            device_linear_scale=device_linear_scale,
            sensor_linear_scale=sensor_linear_scale,
            mirror_linear_scale=mirror_linear_scale,
            mirror_length_multiplier=mirror_length_multiplier,
            vdd_v=vdd_v,
            branch_current_a=branch_current_a,
            reference_current_a=reference_current_a,
        )
    )
    net.write_text(netlist, encoding="utf-8")
    ngspice_env, _ = prepare_ngspice_environment(output_dir)
    proc = subprocess.run(
        [ngspice, "-b", str(net)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=300,
        env=ngspice_env,
    )
    (logdir/f"ptat_{mode}_{corner}.log").write_text(
        proc.stdout + "\n--- STDERR ---\n" + proc.stderr,
        encoding="utf-8",
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"ngspice failed for {mode}/{corner}; see {logdir}"
        )
    write_captured_csv(csv_path, header, proc.stdout, temps, mode)
    return csv_path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=("ideal", "mirror", "both"), default="both")
    ap.add_argument("--corners", nargs="+", default=["tt", "ff", "ss"])
    ap.add_argument("--temps", default="-40:125:5")
    ap.add_argument(
        "--vdd-v",
        type=float,
        help="override nominal supply voltage for this generated evidence",
    )
    ap.add_argument(
        "--branch-current-a",
        type=float,
        help="override ideal-bias branch current for this generated evidence",
    )
    ap.add_argument(
        "--reference-current-a",
        type=float,
        help="override PMOS-mirror reference current for this generated evidence",
    )
    ap.add_argument(
        "--device-linear-scale",
        type=float,
        default=1.0,
        help=(
            "Multiply sensor and mirror W and L by this factor while preserving "
            "nominal W/L; intended for explicit sizing studies."
        ),
    )
    ap.add_argument(
        "--sensor-linear-scale",
        type=float,
        help=(
            "Override sensor-only W/L-preserving linear scale; "
            "defaults to --device-linear-scale."
        ),
    )
    ap.add_argument(
        "--mirror-linear-scale",
        type=float,
        help=(
            "Override mirror-only W/L-preserving linear scale; "
            "defaults to --device-linear-scale."
        ),
    )
    ap.add_argument(
        "--mirror-length-multiplier", type=float, default=1.0,
        help="Multiply mirror L after linear scaling; W is unchanged.",
    )
    ap.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT/"results"/"dense_pdk",
    )
    args = ap.parse_args()
    try:
        seed = characterization_seed(
            args.device_linear_scale,
            sensor_linear_scale=args.sensor_linear_scale,
            mirror_linear_scale=args.mirror_linear_scale,
            mirror_length_multiplier=args.mirror_length_multiplier,
            vdd_v=args.vdd_v,
            branch_current_a=args.branch_current_a,
            reference_current_a=args.reference_current_a,
        )
        temps = parse_temps(args.temps)
    except ValueError as exc:
        print(f"SKY130 RUN: FAIL: {exc}", file=sys.stderr)
        return 2
    ngspice = shutil.which("ngspice")
    if not ngspice:
        print("SKY130 RUN: FAIL: ngspice not found", file=sys.stderr)
        return 2
    model_lib = discover_model_lib()
    modes = ("ideal", "mirror") if args.mode == "both" else (args.mode,)
    outputs = []
    try:
        for mode in modes:
            for corner in args.corners:
                outputs.append(
                    str(
                        run_one(
                            mode,
                            corner,
                            temps,
                            args.output_dir,
                            model_lib,
                            ngspice,
                            device_linear_scale=args.device_linear_scale,
                            sensor_linear_scale=args.sensor_linear_scale,
                            mirror_linear_scale=args.mirror_linear_scale,
                            mirror_length_multiplier=args.mirror_length_multiplier,
                            vdd_v=args.vdd_v,
                            branch_current_a=args.branch_current_a,
                            reference_current_a=args.reference_current_a,
                        )
                    )
                )
    except Exception as exc:
        print(f"SKY130 RUN: FAIL: {exc}", file=sys.stderr)
        return 1
    meta = {
        "status": "PASS",
        "model_library": str(model_lib),
        "model_sha256": sha256_file(model_lib),
        "pdk_revision": pdk_revision(model_lib),
        "design_requirements_sha256": sha256_file(
            ROOT / "design_requirements.json"
        ),
        "ngspice": ngspice_version(ngspice),
        "ngspice_compatibility_mode": "hsa",
        "temperature_c": temps,
        "modes": list(modes),
        "corners": args.corners,
        "device_linear_scale": args.device_linear_scale,
        "sensor_linear_scale": (
            args.device_linear_scale
            if args.sensor_linear_scale is None
            else args.sensor_linear_scale
        ),
        "mirror_linear_scale": (
            args.device_linear_scale
            if args.mirror_linear_scale is None
            else args.mirror_linear_scale
        ),
        "effective_geometry": seed_geometry(seed),
        "mirror_length_multiplier": args.mirror_length_multiplier,
        "operating_point": {
            "vdd_v": seed["vdd_v"],
            "branch_current_a": seed["branch_current_a"],
            "reference_current_a": seed["reference_current_a"],
        },
        "outputs": outputs,
    }
    (args.output_dir/"run_metadata.json").write_text(
        json.dumps(meta, indent=2, sort_keys=True)+"\n",
        encoding="utf-8",
    )
    print("SKY130 RUN: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
