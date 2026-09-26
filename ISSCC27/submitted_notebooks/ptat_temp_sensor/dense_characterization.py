#!/usr/bin/env python3
"""Analyze NEW dense-grid SKY130 PTAT evidence without interpolation."""
from __future__ import annotations
import argparse, csv, json, math
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RELEASE = json.loads((ROOT/"release_requirements.json").read_text(encoding="utf-8"))
DESIGN = json.loads((ROOT/"design_requirements.json").read_text(encoding="utf-8"))
DEFAULT_ANCHORS = [
    float(x) for x in RELEASE["release_architecture"]["calibration_anchors_c"]
]
MIRROR_MISMATCH_TARGET = float(DESIGN["mirror_branch_mismatch_percent_max"])
HEADROOM_TARGET = float(DESIGN["headroom_guardband_v_min"])
NOMINAL_VDD = float(DESIGN["nominal_characterization_seed"]["vdd_v"])

def read_xy(path: Path) -> tuple[list[float], list[float], list[dict[str,str]]]:
    with path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f, skipinitialspace=True))
    if not rows:
        raise ValueError(f"{path}: no rows")
    try:
        numeric_rows = [
            {key: float(value) for key, value in row.items()}
            for row in rows
        ]
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{path}: non-numeric data") from exc
    if not all(
        math.isfinite(value)
        for row in numeric_rows
        for value in row.values()
    ):
        raise ValueError(f"{path}: non-finite data")
    t = [row["temp_c"] for row in numeric_rows]
    v = [row["dvgs_v"] for row in numeric_rows]
    if t != sorted(set(t)):
        raise ValueError(f"{path}: invalid temperature grid")
    for row in numeric_rows:
        if not {
            "vgs_small_v",
            "vgs_large_v",
            "dvgs_v",
        }.issubset(row):
            raise ValueError(f"{path}: missing VGS columns")
        derived_dvgs = row["vgs_small_v"] - row["vgs_large_v"]
        if abs(row["dvgs_v"] - derived_dvgs) > 2.0e-6:
            raise ValueError(
                f"{path}: dvgs_v is inconsistent with the recorded VGS values"
            )
    return t, v, rows

def rms(xs: list[float]) -> float:
    return math.sqrt(sum(x*x for x in xs)/len(xs))

def two_point_errors(t: list[float], v: list[float]) -> list[float]:
    g=(t[-1]-t[0])/(v[-1]-v[0]); b=t[0]-g*v[0]
    return [g*x+b-y for x,y in zip(v,t)]

def fixed_pwl_errors(
    t: list[float],
    v: list[float],
    anchors: list[float] | None = None,
) -> list[float]:
    use_anchors = DEFAULT_ANCHORS if anchors is None else anchors
    idx=[]
    for a in use_anchors:
        hit=[i for i,x in enumerate(t) if abs(x-a)<1e-9]
        if not hit:
            raise ValueError(f"anchor {a} C missing from dense grid")
        idx.append(hit[0])
    est=[math.nan]*len(t)
    for ia,ib in zip(idx[:-1],idx[1:]):
        if v[ib] == v[ia]:
            raise ValueError("zero PWL voltage span")
        g=(t[ib]-t[ia])/(v[ib]-v[ia]); b=t[ia]-g*v[ia]
        for j in range(ia,ib+1):
            est[j]=g*v[j]+b
    if any(not math.isfinite(e) for e in est):
        raise ValueError(
            "calibration anchors must cover the full dense temperature grid"
        )
    return [e-y for e,y in zip(est,t)]

def summarize_errors(err: list[float]) -> dict:
    return {"max_abs_error_c":max(abs(x) for x in err), "rms_error_c":rms(err)}

def branch_mismatch_percent(branch_small_a: float, branch_large_a: float) -> float:
    small = abs(branch_small_a)
    large = abs(branch_large_a)
    denom = (small + large) / 2.0
    if denom <= 0.0:
        raise ValueError("branch currents must have a positive mean magnitude")
    return abs(small - large) / denom * 100.0

def load_provenance(input_dir: Path) -> dict:
    path = input_dir / "run_metadata.json"
    if not path.is_file():
        raise FileNotFoundError(f"{path}: missing simulation provenance")
    meta = json.loads(path.read_text(encoding="utf-8"))
    required = (
        "ngspice",
        "ngspice_compatibility_mode",
        "pdk_revision",
        "model_library",
        "model_sha256",
        "design_requirements_sha256",
    )
    missing = [key for key in required if not meta.get(key)]
    if missing:
        raise ValueError(f"{path}: incomplete provenance fields: {missing}")
    if meta["pdk_revision"] == "unknown":
        raise ValueError(f"{path}: exact PDK revision is unknown")
    return {key: meta[key] for key in required}

def analyze(
    input_dir: Path,
    anchors: list[float] | None = None,
    vdd_v: float | None = None,
) -> dict:
    use_anchors = DEFAULT_ANCHORS if anchors is None else anchors
    use_vdd = NOMINAL_VDD if vdd_v is None else float(vdd_v)
    if not math.isfinite(use_vdd) or use_vdd <= 0.0:
        raise ValueError("VDD must be a finite positive value")
    per={}
    for mode in ("ideal","mirror"):
        for corner in ("tt","ff","ss"):
            path=input_dir/f"ptat_{mode}_{corner}.csv"
            if not path.is_file():
                raise FileNotFoundError(path)
            t,v,rows=read_xy(path)
            step=max(b-a for a,b in zip(t,t[1:]))
            item={
                "samples":len(t),
                "max_step_c":step,
                "two_point":summarize_errors(two_point_errors(t,v)),
                "five_point_pwl":summarize_errors(
                    fixed_pwl_errors(t, v, use_anchors)
                ),
                "max_power_uw":max(float(r["power_w"]) for r in rows)*1e6,
                "min_sensor_headroom_v":min(
                    use_vdd
                    - max(float(r["vgs_small_v"]), float(r["vgs_large_v"]))
                    for r in rows
                ),
            }
            if mode=="mirror":
                mismatch=max(
                    branch_mismatch_percent(
                        float(r["branch_small_a"]), float(r["branch_large_a"])
                    )
                    for r in rows
                )
                item["max_branch_mismatch_percent"]=mismatch
                item["pass_branch_mismatch_target"]=mismatch<=MIRROR_MISMATCH_TARGET
            per[f"{mode}_{corner}"]=item
    target=float(RELEASE["release_targets"]["dense_grid_pwl_max_abs_error_c_max"])
    max_step_target=float(RELEASE["release_targets"]["dense_grid_step_c_max"])
    worst=max(x["five_point_pwl"]["max_abs_error_c"] for x in per.values())
    step=max(x["max_step_c"] for x in per.values())
    worst_mirror_mismatch=max(
        x["max_branch_mismatch_percent"]
        for key,x in per.items() if key.startswith("mirror_")
    )
    worst_headroom=min(x["min_sensor_headroom_v"] for x in per.values())
    return {
        "status":"PASS" if (
            worst<=target and step<=max_step_target
            and worst_mirror_mismatch<=MIRROR_MISMATCH_TARGET
            and worst_headroom>=HEADROOM_TARGET
        ) else "FAIL",
        "evidence_boundary":"New transistor-level SKY130 dense-grid evidence; not silicon and not layout-extracted.",
        "calibration":(
            f"fixed {len(use_anchors)}-point PWL using explicit anchors; "
            "no interpolation is used for error scoring"
        ),
        "uses_release_anchors":use_anchors == DEFAULT_ANCHORS,
        "calibration_anchor_count":len(use_anchors),
        "anchors_c":use_anchors,
        "worst_pwl_max_abs_error_c":worst,
        "worst_five_point_pwl_max_abs_error_c":worst,
        "max_temperature_step_c":step,
        "target_max_abs_error_c":target,
        "worst_mirror_branch_mismatch_percent":worst_mirror_mismatch,
        "mirror_branch_mismatch_target_percent":MIRROR_MISMATCH_TARGET,
        "min_sensor_headroom_v":worst_headroom,
        "sensor_headroom_target_v":HEADROOM_TARGET,
        "vdd_v":use_vdd,
        "per_dataset":per,
    }

def main()->int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--input-dir",type=Path,default=ROOT/"results"/"dense_pdk")
    ap.add_argument("--output",type=Path,default=ROOT/"results"/"dense_pdk_analysis.json")
    ap.add_argument(
        "--anchors",
        default=",".join(f"{x:g}" for x in DEFAULT_ANCHORS),
        help="comma-separated calibration temperatures in degC",
    )
    ap.add_argument("--check",action="store_true")
    ap.add_argument(
        "--allow-fail",
        action="store_true",
        help="return success after valid analysis even when targets are missed",
    )
    args=ap.parse_args()
    try:
        anchors = [
            float(x.strip()) for x in args.anchors.split(",") if x.strip()
        ]
        if len(anchors) < 2 or anchors != sorted(set(anchors)):
            raise ValueError(
                "calibration anchors must be unique and strictly increasing"
            )
        provenance=load_provenance(args.input_dir)
        metadata=json.loads(
            (args.input_dir/"run_metadata.json").read_text(encoding="utf-8")
        )
        operating=metadata.get("operating_point", {})
        if "vdd_v" not in operating:
            raise ValueError("run metadata missing operating_point.vdd_v")
        result=analyze(args.input_dir, anchors, float(operating["vdd_v"]))
        result["provenance"]=provenance
        result["operating_point"]=operating
    except Exception as exc:
        print(f"DENSE CHARACTERIZATION: FAIL: {exc}")
        return 1
    rendered=json.dumps(result,indent=2,sort_keys=True)+"\n"
    if args.check:
        if not args.output.is_file() or args.output.read_text(encoding="utf-8")!=rendered:
            print("DENSE CHARACTERIZATION: FAIL: retained result missing/stale")
            return 1
    else:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(rendered,encoding="utf-8")
    print(f"DENSE CHARACTERIZATION: {result['status']}")
    print("worst five-point PWL error:",result["worst_five_point_pwl_max_abs_error_c"])
    print("worst mirror branch mismatch (%):",result["worst_mirror_branch_mismatch_percent"])
    print("minimum sensor headroom (V):",result["min_sensor_headroom_v"])
    return 0 if result["status"]=="PASS" or args.allow_fail else 1

if __name__=="__main__":
    raise SystemExit(main())
