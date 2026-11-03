#!/usr/bin/env python3
"""Deterministic functional/PPA/time score from evaluator-owned group results.

The input is produced by the independent hidden runner, never by a submission.
This module cannot turn public smoke-test PASS into an official score.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

RULES_PATH = Path(__file__).with_name("score_rules.json")
BASELINES_PATH = Path(__file__).resolve().parents[1] / "benchmark/ppa-baselines.json"


def load_rules() -> dict:
    rules = json.loads(RULES_PATH.read_text())
    if set(rules["tasks"]) != {f"T{i:02d}" for i in range(1, 11)}:
        raise ValueError("score rules must cover T01-T10")
    if rules.get("task_raw_allocations") != {"T09": {"F": 48, "P": 27}}:
        raise ValueError("T09 must reserve 10 normalized points for cycle checks")
    for task, items in rules["tasks"].items():
        allocation = rules["task_raw_allocations"].get(task, {"F": 60, "P": 15})
        for layer, required in allocation.items():
            if not math.isclose(sum(item["points"] for item in items if item["layer"] == layer), required):
                raise ValueError(f"{task} {layer} points do not sum to {required}")
        ids = [item["id"] for item in items]
        if len(ids) != len(set(ids)):
            raise ValueError(f"{task} has duplicate score item IDs")
        for item in items:
            if not item["groups"] or not set(item.get("critical_groups", [])).issubset(item["groups"]):
                raise ValueError(f"{task} {item['id']} has invalid group mapping")
    cycles = [item for item in rules["tasks"]["T09"] if item["id"] == "P_CYCLES"]
    if cycles != [{"id": "P_CYCLES", "layer": "P", "points": 15,
                   "groups": ["CPU-PIPE-CYCLES"], "required_cases_total": 22}]:
        raise ValueError("T09 cycle group must score 10/5/0 points over 22 checks")
    if rules["functional_raw_total"] != 75 or rules["functional_total"] != 50 or \
            rules["ppa_points"] != 50 or rules["time_points"] != 5 or \
            rules["setup_violation_exponent"] != 4 or \
            rules["candidate_delivery_error_penalty"] != 5:
        raise ValueError("score allocation must be functional 50 + PPA 50 + time 5")
    weights = rules.get("task_weights")
    if not isinstance(weights, dict) or set(weights) != set(rules["tasks"]) or \
            not all(isinstance(value, (int, float)) and not isinstance(value, bool) and
                    math.isfinite(value) and value > 0 for value in weights.values()) or \
            not math.isclose(sum(weights.values()), 1.0, rel_tol=0.0, abs_tol=1e-12):
        raise ValueError("task weights must cover T01-T10 and sum to one")
    return rules


def weighted_suite_score(task_scores: dict, rules: dict | None = None) -> dict:
    """Return the non-renormalized weighted display score for available tasks."""
    rules = rules or load_rules()
    weights = rules["task_weights"]
    if not isinstance(task_scores, dict) or not set(task_scores).issubset(weights):
        raise ValueError("task_scores must be a T01-T10 mapping")
    weighted = 0.0
    covered_weight = 0.0
    contributions = {}
    for task, score in task_scores.items():
        if score is None:
            continue
        if not isinstance(score, (int, float)) or isinstance(score, bool) or \
                not math.isfinite(score) or score < 0 or score > 105:
            raise ValueError(f"invalid display score for {task}")
        contribution = weights[task] * score
        contributions[task] = contribution
        weighted += contribution
        covered_weight += weights[task]
    return {
        "weighted_display_score": weighted,
        "weighted_display_possible": 105.0,
        "covered_task_weight": covered_weight,
        "covered_display_possible": 105.0 * covered_weight,
        "weighted_contributions": contributions,
    }


def score_functional(task: str, results: dict, rules: dict) -> tuple[float, float, list[dict]]:
    items = rules["tasks"][task]
    expected = {group for item in items for group in item["groups"]}
    if set(results) != expected:
        raise ValueError(f"group IDs mismatch; missing={sorted(expected-set(results))}; "
                         f"extra={sorted(set(results)-expected)}")
    awarded = []
    scale = rules["functional_total"] / rules["functional_raw_total"]
    basic = edge = 0.0
    for item in items:
        passed = total = 0
        group_fractions = []
        safety = False
        critical_failed = False
        for group in item["groups"]:
            outcome = results[group]
            good = outcome["cases_passed"]
            count = outcome["cases_total"]
            if not isinstance(good, int) or not isinstance(count, int) or \
                    isinstance(good, bool) or isinstance(count, bool) or \
                    count <= 0 or good < 0 or good > count:
                raise ValueError(f"invalid case counts for {group}")
            if "required_cases_total" in item and count != item["required_cases_total"]:
                raise ValueError(f"{group} must contain {item['required_cases_total']} cases")
            if not isinstance(outcome.get("safety_violation", False), bool):
                raise ValueError(f"invalid safety_violation for {group}")
            passed += good
            total += count
            group_fractions.append(good / count)
            safety |= outcome.get("safety_violation", False)
            critical_failed |= group in item.get("critical_groups", []) and good != count
        if safety or critical_failed:
            points = 0.0
        elif item.get("case_fraction"):
            # The MAC's published groups score each scenario only when all
            # three functional seeds pass, retaining its frozen /50 rubric.
            points = item["points"] * passed / total
        elif all(fraction == 1.0 for fraction in group_fractions):
            points = float(item["points"])
        elif sum(group_fractions) * 2 >= len(group_fractions):
            points = item["points"] / 2
        else:
            points = 0.0
        awarded.append({"id": item["id"], "layer": item["layer"],
                        "points": points * scale,
                        "possible_points": item["points"] * scale,
                        "cases_passed": passed, "cases_total": total,
                        "safety_violation": safety or critical_failed})
        if item["layer"] == "F":
            basic += points * scale
        else:
            edge += points * scale
    return basic, edge, awarded


def ppa_score(measurement: dict, reference: dict,
              max_points: float = 50.0,
              reference_points: float = 35.0,
              setup_violation_exponent: float = 4.0) -> float:
    setup_slack = measurement.get("setup_worst_slack_ns")
    hold_slack = measurement.get("hold_worst_slack_ns")
    drc_violations = measurement.get("drc_violations")
    if not isinstance(setup_slack, (int, float)) or isinstance(setup_slack, bool) or \
            not math.isfinite(setup_slack):
        return 0.0
    if not measurement.get("routed", False) or \
            not isinstance(hold_slack, (int, float)) or isinstance(hold_slack, bool) or \
            not math.isfinite(hold_slack) or \
            type(drc_violations) is not int or drc_violations < 0 or \
            measurement.get("annotation_fraction", 0) < 0.95:
        return 0.0
    period_ps = measurement.get("parameter_set", {}).get("period_ps")
    if not isinstance(period_ps, (int, float)) or isinstance(period_ps, bool) or \
            not math.isfinite(period_ps) or period_ps <= 0:
        raise ValueError("invalid target period")
    target_period_ns = period_ps / 1000.0
    worst_setup_delay = target_period_ns + max(0.0, -setup_slack)
    setup_factor = (target_period_ns / worst_setup_delay) ** setup_violation_exponent
    factors = []
    for key, exponent in (("area_um2", 0.35), ("delay_ns", 0.35),
                          ("energy_per_op_pj", 0.30)):
        actual = measurement[key]
        baseline = reference[key]
        if not all(isinstance(value, (int, float)) and math.isfinite(value) and value > 0
                   for value in (actual, baseline)):
            raise ValueError(f"invalid positive PPA value: {key}")
        if key == "delay_ns":
            # A setup miss is already represented by the measured critical-path
            # delay.  A hold miss is a separate min-delay failure, so fold its
            # magnitude into an effective delay to penalize it continuously.
            actual += max(0.0, -hold_slack)
        factors.append(min(2.0, max(0.0, baseline / actual)) ** exponent)
    drc_factor = 0.5 if drc_violations else 1.0
    base = min(max_points, max(0.0, reference_points * math.prod(factors)))
    return base * setup_factor * drc_factor


def ppa_provenance_valid(task: str, measurement: dict, reference: dict) -> bool:
    expected = {"platform": "ASAP7_7p5t_RVT_NLDM", "period_ps": 1000,
                "corner": "WC", "utilization": 10, "density": 0.6,
                "seeds": [11, 29, 47]}
    if task == "T05":
        expected["clock_periods_ps"] = {"wr_clk": 1000, "rd_clk": 1000}
        expected["asynchronous_clock_groups"] = [["wr_clk", "rd_clk"]]
    if task == "T08":
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from t11_sram import contract
        policy = contract()
        expected.update(corner="mixed_WC_standard_cells_TT_SRAM",
                        clock_periods_ps={clock:1000 for clock in ("logic_clk","tx_clk","rx_clk")},
                        asynchronous_clock_groups=[["logic_clk","tx_clk","rx_clk"]],
                        ppa_policy_revision=policy["revision"],memory_mapping="lambdapdk_tdp_4096x32",
                        sram_contract=policy,drc_scope=policy["drc_scope"],lvs_performed=False)
    for record in (measurement, reference):
        rows = record.get("per_seed")
        if record.get("task_id") != task or \
                record.get("measurement_status") != "three_seed" or \
                record.get("parameter_set") != expected or \
                not isinstance(rows, list) or len(rows) != 3 or \
                any(not isinstance(row, dict) or type(row.get("layout_seed")) is not int
                    for row in rows) or \
                sorted(row["layout_seed"] for row in rows) != expected["seeds"] or \
                any(type(row.get("drc_violations")) is not int or
                    row["drc_violations"] < 0 or
                    not isinstance(row.get("setup_worst_slack_ns"), (int, float)) or
                    isinstance(row.get("setup_worst_slack_ns"), bool) or
                    not math.isfinite(row["setup_worst_slack_ns"]) or
                    not isinstance(row.get("hold_worst_slack_ns"), (int, float)) or
                    isinstance(row.get("hold_worst_slack_ns"), bool) or
                    not math.isfinite(row["hold_worst_slack_ns"]) or
                    row.get("annotation_fraction", 0) < 0.95 or
                    any(not isinstance(row.get(key), (int, float)) or
                        not math.isfinite(row[key]) or row[key] <= 0
                        for key in ("area_um2", "delay_ns", "energy_per_op_pj"))
                    for row in rows):
            return False
    # The evaluator owns the testbench and vectors.  Use an explicit workload
    # contract ID as the compatibility gate.  The content hashes remain audit
    # evidence, but must not invalidate every historical baseline whenever the
    # probe implementation receives an unrelated maintenance change.
    expected_workload = "T11-power-v1" if task == "T08" else f"{task}-power-v1"
    if measurement.get("workload_id") != expected_workload or \
            reference.get("workload_id") != expected_workload:
        return False
    if measurement.get("workload_parameters") != reference.get("workload_parameters"):
        return False
    return all(isinstance(record.get("workload_sha256"), str) and
               len(record["workload_sha256"]) == 64
               for record in (measurement, reference))


def score_run(payload: dict, rules: dict | None = None) -> dict:
    rules = rules or load_rules()
    task = payload["task_id"]
    results = payload["groups"]
    if task == "T10":
        sustained = payload.get("sustained_throughput_passed")
        if not isinstance(sustained, bool):
            raise ValueError("T10 sustained_throughput_passed must be boolean")
        if not sustained:
            # The stream/structure gate is evaluator-owned and covers facts that
            # cannot be reconstructed from aggregate group counts alone.  Keep
            # the remaining functional diagnostics, but force P_SYSTOLIC to 0.
            results = dict(results)
            systolic = dict(results.get("MM-SYSTOLIC", {}))
            systolic["safety_violation"] = True
            results["MM-SYSTOLIC"] = systolic
    basic, edge, items = score_functional(task, results, rules)
    functional = basic + edge
    duration = payload["elapsed_seconds"]
    limit = payload["time_limit_seconds"]
    if not all(isinstance(value, (int, float)) and math.isfinite(value)
               for value in (duration, limit)) or duration < 0 or limit <= 0:
        raise ValueError("invalid elapsed/time-limit values")
    delivery = payload["delivery_qualified"]
    if not isinstance(delivery, bool):
        raise ValueError("delivery_qualified must be boolean")
    candidate_errors = payload.get("candidate_delivery_error_count", 0)
    if type(candidate_errors) is not int or candidate_errors < 0:
        raise ValueError("candidate_delivery_error_count must be a nonnegative integer")
    full = math.isclose(functional, rules["functional_total"],
                        rel_tol=0.0, abs_tol=1e-9)
    if full:
        # Avoid exposing binary floating-point noise such as
        # 49.99999999999999 for a fully passing 50-point result.
        scale = rules["functional_total"] / rules["functional_raw_total"]
        basic = sum(item["points"] for item in rules["tasks"][task]
                    if item["layer"] == "F") * scale
        edge = sum(item["points"] for item in rules["tasks"][task]
                   if item["layer"] == "P") * scale
        functional = float(rules["functional_total"])
    baselines = json.loads(BASELINES_PATH.read_text())
    official_reference = baselines.get("tasks", {}).get(task)
    baseline_ready = baselines.get("status") in {"partial_1ghz_qualified", "qualified_1ghz"} and \
        isinstance(official_reference, dict) and \
        official_reference.get("qualification_status") == "qualified_1ghz" and \
        payload.get("ppa_reference") == official_reference
    # Delivery quality is reported independently from RTL function and PPA.
    # Evaluator-adjudicated, candidate-caused fatal handoff errors receive a
    # fixed display-score deduction below; they do not erase an otherwise
    # valid PPA/time measurement.
    eligible = full and isinstance(payload.get("ppa_measurement"), dict) and \
        baseline_ready and \
        ppa_provenance_valid(task, payload["ppa_measurement"], payload["ppa_reference"])
    ppa = ppa_score(payload["ppa_measurement"], payload["ppa_reference"],
                    rules["ppa_points"], rules["ppa_reference_points"],
                    rules["setup_violation_exponent"]) if eligible else 0.0
    ppa_valid = eligible and ppa > 0
    time_points = rules["time_points"]
    time = max(0.0, min(time_points,
                        time_points * (1.0 - duration / limit))) if ppa_valid else 0.0
    width = rules["ppa_bucket_width"]
    bucket = min(round(rules["ppa_points"] / width),
                 math.floor(ppa / width + 0.5)) if ppa_valid else 0
    score_before_penalty = functional + ppa + time
    candidate_penalty = candidate_errors * rules["candidate_delivery_error_penalty"]
    display_score = max(0.0, score_before_penalty - candidate_penalty)
    return {"task_id": task, "functional_basic": basic, "functional_edges": edge,
            "functional_total": functional, "full_functional_pass": full,
            "delivery_qualified": delivery, "ppa_eligible": bool(eligible),
            "ppa_score": ppa, "ppa_rank_bucket": bucket,
            "time_score": time,
            "candidate_delivery_error_count": candidate_errors,
            "candidate_delivery_penalty": candidate_penalty,
            "display_score_before_candidate_penalty": score_before_penalty,
            "display_score": display_score,
            "score_items": items,
            "rank_key": [functional, bucket, -duration if ppa_valid else 0]}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("results", type=Path,
                        help="evaluator-owned group outcomes and PPA/time measurements")
    args = parser.parse_args()
    try:
        print(json.dumps(score_run(json.loads(args.results.read_text())),
                         ensure_ascii=False, indent=2))
    except (OSError, KeyError, ValueError, TypeError) as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
