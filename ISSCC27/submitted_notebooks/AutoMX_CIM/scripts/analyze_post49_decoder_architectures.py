"""Offline decoder architecture screen over existing TT PEX reports.

No SPICE, ADC model, physical sign-off or independent holdout is implied.
The 16 old holdout cases were already inspected while designing the 87-case
calibration sweep; they are retained as a *previously inspected* diagnostic.
Cross-validation excludes both time samples of the queried case.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORTS = {
    "cell49": Path("results/sky130/core_candidate_full_tt/measured.json"),
    "old_holdout": Path("results/sky130/post49_holdout_tt/measured.json"),
    "calibration": Path("results/sky130/post49_calibration_tt/measured.json"),
}
EXPECTED = {
    "cell49": ("automx-cim-core-candidate-full-tt-v1", "MEASURED_TT_CANDIDATE_SCREEN", 101),
    "old_holdout": ("automx-cim-post49-holdout-tt-v1", "MEASURED_HOLDOUT_TT", 16),
    "calibration": ("automx-cim-post49-calibration-tt-v1", "MEASURED_CALIBRATION_TT", 87),
}
OUTPUT = Path("results/sky130/post49_decoder_architecture/offline.json")
TIMES = ("t19", "t21")
CONFIGS = (
    ("differential_only", 0.0, None),
    ("differential_cm_0p05", 0.05, None),
    ("differential_cm_0p2", 0.2, None),
    ("differential_cm_1", 1.0, None),
    ("differential_active_rows", 0.0, "active_rows"),
    ("differential_unsigned_activity", 0.0, "unsigned_activity_x2"),
)


def _hash(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _read_reports(root: Path) -> tuple[dict, dict]:
    reports = {}
    hashes = {}
    for name, relative in REPORTS.items():
        path = root / relative
        if not path.is_file():
            raise FileNotFoundError(f"Copy the measured server report first: {path}")
        value = json.loads(path.read_text(encoding="utf-8"))
        fmt, status, count = EXPECTED[name]
        if (not isinstance(value, dict) or value.get("format") != fmt or
                value.get("status") != status or value.get("failures") or
                value.get("planned_sims") != count or
                value.get("completed_sims") != count or
                not isinstance(value.get("jobs"), list) or len(value["jobs"]) != count):
            raise ValueError(f"Incomplete or wrong {name} measured report: {path}")
        reports[name] = value
        hashes[name] = _hash(path)
    provenance_links = (
        ("4.10 -> 4.9", reports["old_holdout"].get("stage49_sha256"), hashes["cell49"]),
        ("4.12a -> 4.9", reports["calibration"].get("cell49_sha256"), hashes["cell49"]),
        ("4.12a -> 4.10", reports["calibration"].get("old_holdout_sha256"),
         hashes["old_holdout"]),
    )
    mismatches = [f"{link}: recorded={recorded}, current={current}"
                  for link, recorded, current in provenance_links if recorded != current]
    if mismatches:
        raise ValueError("101/16/87 report provenance hashes do not match: "
                         + "; ".join(mismatches)
                         + ". Refresh 4.10 after 4.9 if its link differs; "
                           "then refresh 4.12a after 4.10. Valid SPICE checkpoints "
                           "are reused.")
    if any(len({reports[name].get(key) for name in REPORTS}) != 1
           for key in ("pex_sha256", "model_sha256", "ngspice_version",
                       "load_ff", "pwm_unit_ps")):
        raise ValueError("TT PEX/source/stimulus settings differ across reports")
    if (reports["cell49"]["load_ff"], reports["cell49"]["pwm_unit_ps"]) != (800, 50):
        raise ValueError("Expected the 800 fF / 50 ps candidate")
    return reports, hashes


def observations(jobs: list[dict], *, source: str) -> list[dict]:
    """Recompute labels and metadata from vectors, never trust cached sums."""
    output = []
    names = set()
    for job in jobs:
        name = job.get("case")
        acts, weights = job.get("activation_x2"), job.get("ternary_weights")
        values = job.get("measurements_v")
        if (not isinstance(name, str) or not name or name in names or
                not isinstance(acts, list) or len(acts) != 4 or
                not isinstance(weights, list) or len(weights) != 4 or
                any(not isinstance(row, list) or len(row) != 4 for row in weights) or
                not isinstance(values, dict)):
            raise ValueError(f"Invalid {source} job: {name}")
        names.add(name)
        if (any(type(a) is not int or abs(a) not in (0, 1, 2, 3, 4, 6, 8, 12)
                for a in acts) or
                any(type(w) is not int or w not in (-1, 0, 1)
                    for row in weights for w in row)):
            raise ValueError(f"Invalid E2M1/ternary vector: {name}")
        sums = [sum(acts[row] * weights[row][col] for row in range(4))
                for col in range(4)]
        if sums != job.get("integer_sums"):
            raise ValueError(f"Cached integer sums disagree with vectors: {name}")
        for col in range(4):
            active_rows = sum(acts[row] != 0 and weights[row][col] != 0
                              for row in range(4))
            activity = sum(abs(acts[row]) * abs(weights[row][col])
                           for row in range(4))
            for time in TIMES:
                try:
                    diff = float(values[f"diff_c{col}_{time}"])
                    blp = float(values[f"blp_c{col}_{time}"])
                    bln = float(values[f"bln_c{col}_{time}"])
                except (KeyError, TypeError, ValueError) as error:
                    raise ValueError(f"Missing/non-numeric sample: {name} c{col} {time}") from error
                if (not all(math.isfinite(v) for v in (diff, blp, bln)) or
                        abs(diff - (bln - blp)) > 2e-4):
                    raise ValueError(f"Inconsistent/non-finite bitlines: {name} c{col} {time}")
                output.append({"case": name, "source": source, "column": col,
                               "time": time, "sum": sums[col], "diff_v": diff,
                               "cm_v": (blp + bln) / 2,
                               "active_rows": active_rows,
                               "unsigned_activity_x2": activity})
    return output


def _nearest(training: list[dict], query: dict, *, cm_weight: float,
             condition: str | None) -> tuple[int, float, bool]:
    if condition:
        subset = [item for item in training if item[condition] == query[condition]]
        fallback = not bool(subset)
        candidates = subset or training
    else:
        candidates, fallback = training, False
    if not candidates:
        raise ValueError("No training samples for nearest-neighbour decoder")
    best = min(candidates, key=lambda item: (
        (item["diff_v"] - query["diff_v"]) ** 2 +
        (cm_weight * (item["cm_v"] - query["cm_v"])) ** 2,
        abs(item["sum"]), item["sum"], item["case"], item["time"]))
    distance = math.hypot(best["diff_v"] - query["diff_v"],
                          cm_weight * (best["cm_v"] - query["cm_v"]))
    return best["sum"], distance, fallback


def _score(training: list[dict], queries: list[dict], *, cm_weight: float,
           condition: str | None, exclude_same_case: bool) -> dict:
    columns = []
    for col in range(4):
        pool = [item for item in training if item["column"] == col]
        details = []
        for query in (item for item in queries if item["column"] == col):
            candidates = ([item for item in pool if item["case"] != query["case"]]
                          if exclude_same_case else pool)
            predicted, distance, fallback = _nearest(
                candidates, query, cm_weight=cm_weight, condition=condition)
            known = query["sum"] in {item["sum"] for item in candidates}
            details.append({"case": query["case"], "time": query["time"],
                            "expected": query["sum"], "predicted": predicted,
                            "known_sum": known, "fallback": fallback,
                            "nearest_distance_v": distance,
                            "diff_v": query["diff_v"], "cm_v": query["cm_v"]})
        columns.append({"column": col, "samples": len(details),
                        "mismatches": sum(d["predicted"] != d["expected"] for d in details),
                        "known_sum_mismatches": sum(d["known_sum"] and d["predicted"] != d["expected"]
                                                     for d in details),
                        "unseen_sum_samples": sum(not d["known_sum"] for d in details),
                        "metadata_fallback_samples": sum(d["fallback"] for d in details),
                        "first_mismatches": [d for d in details if d["predicted"] != d["expected"]][:8]})
    return {"samples": sum(c["samples"] for c in columns),
            "mismatches": sum(c["mismatches"] for c in columns),
            "known_sum_mismatches": sum(c["known_sum_mismatches"] for c in columns),
            "unseen_sum_samples": sum(c["unseen_sum_samples"] for c in columns),
            "metadata_fallback_samples": sum(c["metadata_fallback_samples"] for c in columns),
            "columns": columns}


def _select_training_candidates(screens: dict) -> tuple[dict, dict, str]:
    """Choose a family winner, but endorse it only if it beats raw differential.

    The old 16 cases must not participate in this selection. A family winner
    can still be worse than the baseline; calling that winner a selected
    decoder was misleading in the original v1 diagnostic.
    """
    baseline = screens["differential_only"]["case_grouped_cross_validation"]
    families = {
        "two_dimensional": [name for name, weight, _ in CONFIGS if weight > 0],
        "digital_activity_conditioned": [name for name, _, cond in CONFIGS if cond],
    }
    winners = {}
    improvements = {}
    for family, options in families.items():
        winner = min(options, key=lambda key: (
            screens[key]["case_grouped_cross_validation"]["known_sum_mismatches"],
            screens[key]["case_grouped_cross_validation"]["mismatches"],
            options.index(key)))
        candidate = screens[winner]["case_grouped_cross_validation"]
        winners[family] = winner
        improvements[family] = (winner if
                                candidate["known_sum_mismatches"] < baseline["known_sum_mismatches"]
                                and candidate["mismatches"] <= baseline["mismatches"] else None)
    recommended = min(("differential_only", *(name for name in improvements.values() if name)),
                      key=lambda key: (
                          screens[key]["case_grouped_cross_validation"]["known_sum_mismatches"],
                          screens[key]["case_grouped_cross_validation"]["mismatches"]))
    return winners, improvements, recommended


def analyze(training_jobs: list[dict], inspected_jobs: list[dict]) -> dict:
    training = observations(training_jobs, source="101_plus_87_training")
    inspected = observations(inspected_jobs, source="previously_inspected_16")
    if len(training) != 188 * 8 or len(inspected) != 16 * 8:
        raise ValueError("Expected exactly 101+87 training cases and 16 inspected cases")
    if {x["case"] for x in training} & {x["case"] for x in inspected}:
        raise ValueError("Training and inspected case names overlap")
    screens = {}
    for name, cm_weight, condition in CONFIGS:
        screens[name] = {"cm_weight": cm_weight, "metadata_condition": condition,
                         "case_grouped_cross_validation": _score(
                             training, training, cm_weight=cm_weight,
                             condition=condition, exclude_same_case=True)}
    # Select on training only. The previously inspected 16 cases may veto
    # confidence in a candidate, but cannot pick the model or CM weight.
    family_winners, selected, recommended = _select_training_candidates(screens)
    for name in {"differential_only", *family_winners.values()}:
        screen = screens[name]
        screen["previously_inspected_16_diagnostic"] = _score(
            training, inspected, cm_weight=screen["cm_weight"],
            condition=screen["metadata_condition"], exclude_same_case=False)
    cv = screens[recommended]["case_grouped_cross_validation"]
    inspected_score = screens[recommended]["previously_inspected_16_diagnostic"]
    gate = ("BLOCKED_KNOWN_LEVEL_ERRORS" if cv["known_sum_mismatches"] else
            "BLOCKED_INSPECTED_CASE_ERRORS" if inspected_score["mismatches"] else
            "PENDING_FRESH_HOLDOUT_AND_PHYSICAL_ADC")
    return {"training_cases": 188, "previously_inspected_cases": 16,
            "selection_uses_inspected_16": False,
            "best_within_family_training_only": family_winners,
            "improves_over_differential_baseline": selected,
            "recommended_training_only": recommended,
            "decoder_feasibility_gate": gate,
            "cross_validation_unseen_level_samples": cv["unseen_sum_samples"],
            "screens": screens,
            "scope_warning": "TT passive-core point samples only. kNN is an offline architecture probe, not a physical ADC/LUT, independent holdout, noise/PVT proof or sign-off."}


def run(root: str | Path) -> dict:
    root = Path(root).resolve()
    reports, hashes = _read_reports(root)
    result = analyze(reports["cell49"]["jobs"] + reports["calibration"]["jobs"],
                     reports["old_holdout"]["jobs"])
    payload = {"format": "automx-cim-post49-decoder-architecture-v2",
               "status": "DIAGNOSTIC_ONLY",
               "timestamp_utc": datetime.now(timezone.utc).isoformat(),
               "evidence_level": "three_report_JSON_only; raw deck/log hashes not revalidated",
               "input_report_sha256": hashes, **result}
    output = root / OUTPUT
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return payload


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    result = run(args.root)
    print(json.dumps({"status": result["status"],
                      "decoder_feasibility_gate": result["decoder_feasibility_gate"],
                      "best_within_family_training_only": result["best_within_family_training_only"],
                      "improves_over_differential_baseline": result["improves_over_differential_baseline"],
                      "recommended_training_only": result["recommended_training_only"],
                      "screens": {name: {
                          "cross_validation": item["case_grouped_cross_validation"],
                          "inspected_16": item.get("previously_inspected_16_diagnostic")}
                          for name, item in result["screens"].items()
                          if name in ("differential_only", *result["best_within_family_training_only"].values())}},
                     indent=2))
