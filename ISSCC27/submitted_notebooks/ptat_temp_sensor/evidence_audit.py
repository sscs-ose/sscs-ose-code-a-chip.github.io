#!/usr/bin/env python3
"""Fail-closed integrity check for retained SKY130 run-221 evidence."""
from __future__ import annotations
import csv, hashlib, json, math
from pathlib import Path

ROOT = Path(__file__).resolve().parent
K_OVER_Q = 1.380649e-23 / 1.602176634e-19
TEMPS = [-40.0, -20.0, 0.0, 25.0, 50.0, 75.0, 100.0, 125.0]

class AuditError(RuntimeError):
    pass

def canonical_hash(path: Path) -> str:
    obj = json.loads(path.read_text(encoding="utf-8"))
    payload = (json.dumps(obj, indent=2) + "\n").encode()
    return hashlib.sha256(payload).hexdigest()

def read_csv(path: Path) -> list[dict[str, float]]:
    with path.open(newline="", encoding="utf-8") as f:
        rd = csv.DictReader(f, skipinitialspace=True)
        rows = []
        for n, row in enumerate(rd, start=2):
            try:
                out = {k.strip(): float(str(v).strip()) for k, v in row.items()}
            except Exception as exc:
                raise AuditError(f"{path}:{n}: malformed numeric row") from exc
            if not out or not all(math.isfinite(v) for v in out.values()):
                raise AuditError(f"{path}:{n}: empty/non-finite row")
            rows.append(out)
    if not rows:
        raise AuditError(f"{path}: no data")
    return rows

def fit(x: list[float], y: list[float]) -> tuple[float, float]:
    xb, yb = sum(x)/len(x), sum(y)/len(y)
    den = sum((v-xb)**2 for v in x)
    if den <= 0:
        raise AuditError("zero temperature span")
    slope = sum((a-xb)*(b-yb) for a, b in zip(x, y)) / den
    if not math.isfinite(slope) or slope <= 0:
        raise AuditError("non-positive PTAT slope")
    return slope, yb - slope*xb

def summarize(path: Path, mode: str, ratio: float, vdd: float) -> dict[str, float]:
    rows = read_csv(path)
    required = {"temp_c","vgs_small_v","vgs_large_v","dvgs_v","supply_current_a","power_w"}
    if mode == "mirror":
        required |= {"branch_small_a","branch_large_a"}
    missing = required - set(rows[0])
    if missing:
        raise AuditError(f"{path}: missing columns {sorted(missing)}")
    temps = [r["temp_c"] for r in rows]
    if temps != TEMPS:
        raise AuditError(f"{path}: unexpected temperature grid {temps}")
    dvgs = [r["dvgs_v"] for r in rows]
    slope, intercept = fit(temps, dvgs)
    d25 = next((r["dvgs_v"] for r in rows if r["temp_c"] == 25.0), None)
    if d25 is None:
        raise AuditError(f"{path}: missing 25 C sample")
    out = {
        "ptat_slope_uv_per_k": slope*1e6,
        "dvgs_25c_mv": d25*1e3,
        "effective_n": slope/(K_OVER_Q*math.log(ratio)),
        "max_abs_nonlinearity_c": max(abs((r["dvgs_v"]-(slope*r["temp_c"]+intercept))/slope) for r in rows),
        "max_power_uw": max(r["power_w"] for r in rows)*1e6,
        "min_sensor_headroom_v": min(vdd-r["vgs_small_v"] for r in rows),
    }
    if mode == "mirror":
        out["max_branch_mismatch_percent"] = max(
            abs(r["branch_small_a"]-r["branch_large_a"]) /
            ((r["branch_small_a"]+r["branch_large_a"])/2) * 100 for r in rows
        )
    return out

def close(label: str, actual: float, expected: float) -> None:
    if not math.isclose(actual, expected, rel_tol=2e-5, abs_tol=2e-6):
        raise AuditError(f"{label}: recomputed={actual:.12g}, manifest={expected:.12g}")

def audit() -> dict:
    design_path = ROOT/"design_requirements.json"
    manifest_path = ROOT/"results/sky130_ci_manifest.json"
    design = json.loads(design_path.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("status") != "PASS":
        raise AuditError("manifest status is not PASS")
    h = canonical_hash(design_path)
    if h != manifest.get("design_requirements_sha256") or h != manifest.get("design_requirements_expected_sha256"):
        raise AuditError("design requirements do not match retained run-221 evidence")
    if manifest.get("design_hash_match") is not True:
        raise AuditError("manifest design_hash_match is not true")
    if manifest.get("corners") != ["tt","ff","ss"] or [float(x) for x in manifest.get("temperature_c",[])] != TEMPS:
        raise AuditError("manifest sweep definition changed")
    ratio = float(design["current_density_ratio"])
    vdd = float(design["nominal_characterization_seed"]["vdd_v"])
    headroom_min = float(design["headroom_guardband_v_min"])
    mismatch_max = float(design["mirror_branch_mismatch_percent_max"])
    summaries = {}
    for mode in ("ideal","mirror"):
        summaries[mode] = {}
        for corner in ("tt","ff","ss"):
            path = ROOT/"results/sky130_ci"/f"ptat_{mode}_{corner}.csv"
            got = summarize(path, mode, ratio, vdd)
            stored = manifest["summary"][mode][corner]
            for key, value in got.items():
                close(f"{mode}/{corner}/{key}", value, float(stored[key]))
            if got["min_sensor_headroom_v"] < headroom_min:
                raise AuditError(f"{mode}/{corner}: headroom target violated")
            if mode == "mirror" and got["max_branch_mismatch_percent"] > mismatch_max:
                raise AuditError(f"{mode}/{corner}: mirror mismatch target violated")
            summaries[mode][corner] = got
    return {"status":"PASS","design_sha256":h,"summary":summaries}

if __name__ == "__main__":
    try:
        r = audit()
    except (AuditError, KeyError, ValueError, json.JSONDecodeError) as exc:
        print(f"EVIDENCE AUDIT: FAIL\n{exc}")
        raise SystemExit(1)
    print("EVIDENCE AUDIT: PASS")
    print("design requirements:", r["design_sha256"])
