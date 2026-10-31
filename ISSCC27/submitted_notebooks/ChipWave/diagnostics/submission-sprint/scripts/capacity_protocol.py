"""Public, deterministic rules for the equal-resource workflow study."""
from __future__ import annotations

import math
import random

TASKS = ("A1", "A2", "B1", "B2")
MODELS = {"luna": "gpt-6-luna", "sol": "gpt-6.1-sol"}
WORKFLOWS = ("C0", "C1", "C2", "C3", "C6")
CHECKPOINTS = (250_000, 500_000, 1_000_000)
PHYSICAL_LIMITS = dict(reference_module=4, reference_integration=4,
                       preformal_calibration=1, retained_invalid_pilot=1, pilot=16, formal=168)
GDS_GATES = ("readable_gds", "routed", "zero_unrouted", "hold",
             "drc", "lvs", "provenance")
CONSTRAINT_GATES = ("setup", "hold", "slew", "capacitance", "fanout",
                    "postroute_function", "measurement_valid")


def protocol():
    rng = random.Random(20261021)
    jobs = []
    for task in TASKS:
        for repetition in range(1, 4):
            block = [(model, workflow)
                     for model in MODELS
                     for workflow in (WORKFLOWS if model == "luna" else ("C0", "C3"))]
            rng.shuffle(block)
            jobs.extend(dict(id=f"{model}-{workflow}-{task}-{repetition}",
                             model=MODELS[model], model_group=model, workflow=workflow,
                             task=task, repetition=repetition, status="not_started")
                        for model, workflow in block)
    pilots = [dict(id=f"pilot-r1-{model}-{task}", model=MODELS[model],
                   task=task, workflow="C0", status="not_started")
              for task in TASKS for model in MODELS]
    return dict(schema_version=2, phase="prerequisite_implementation",
                registration_revision="revised-batch-01", retained_invalid_sessions=1,
                design_session_token_ceiling=93_000_000, inherited_physical_attempts=10,
                seed=20261021, seed_scope="group order, not model sampling",
                reasoning="high", formal_jobs=jobs, pilot_jobs=pilots,
                token_limit=1_000_000, checkpoints=CHECKPOINTS,
                tool_limits=dict(development=20, synthesis_sta=6, physical=2),
                active_seconds=5400, physical_seconds=14400, postprocess_seconds=1800,
                physical_limits=PHYSICAL_LIMITS, physical_total=194,
                period_ns=10.526, threads=2, frozen_for_formal=False,
                pilot_launch_allowed=False, formal_launch_allowed=False,
                stop_rule="four Luna pilots all pass or all fail function+integration",
                score="100*F*G*H*min(1,0.5*cbrt(T/Tref*Eref/E*Aref/A))",
                prior_experiments_reclassified=False)


def positive(value):
    return (type(value) in (int, float) and math.isfinite(value) and value > 0)


def score(functional, gds, constraints, candidate=None, reference=None):
    """Grade evaluator-issued evidence; absent or malformed measurements fail closed.

    The caller verifies files and produces booleans outside the agent sandbox.
    This pure function does not authenticate an agent-supplied report.
    """
    f = functional.get("function") is True and functional.get("integration") is True
    g = all(gds.get(key) is True for key in GDS_GATES)
    reasons = []
    if not f:
        reasons.append("functional_or_integration")
    if not g:
        reasons.extend("gds:" + key for key in GDS_GATES if gds.get(key) is not True)
    h = all(constraints.get(key) is True for key in CONSTRAINT_GATES)
    reasons.extend("constraint:" + key for key in CONSTRAINT_GATES
                   if constraints.get(key) is not True)
    ratios = None
    if f and g:
        try:
            if not isinstance(candidate, dict) or not isinstance(reference, dict):
                raise ValueError("missing_measurements")
            workloads = reference["workloads"]
            if not workloads or set(workloads) != set(candidate["workloads"]):
                raise ValueError("workload_set")
            for record in (candidate, reference):
                values = [record["cell_area"], record["die_area"]]
                for w in workloads:
                    values.extend(record["workloads"][w][key]
                                  for key in ("throughput", "latency", "power", "energy"))
                if not all(positive(v) for v in values):
                    raise ValueError("nonpositive_or_nonfinite_measurement")
            area = candidate["cell_area"] / reference["cell_area"]
            die = candidate["die_area"] / reference["die_area"]
            if area > 1.25 or die > 1.25:
                h = False
                reasons.append("constraint:area")
            tr, er = [], []
            for w, ref in workloads.items():
                row = candidate["workloads"][w]
                t, e = row["throughput"] / ref["throughput"], row["energy"] / ref["energy"]
                tr.append(t)
                er.append(e)
                if (t < .8 or row["latency"] / ref["latency"] > 1.25
                        or row["power"] / ref["power"] > 1.25 or e > 1.25):
                    h = False
                    reasons.append("constraint:workload:" + w)
            # Log-domain scoring avoids intermediate products overflowing.
            log_t = sum(math.log(x) for x in tr) / len(tr)
            log_e = sum(math.log(x) for x in er) / len(er)
            log_score = math.log(.5) + (log_t - log_e - math.log(area)) / 3
            p = math.exp(min(0, log_score))
            ratios = dict(throughput=math.exp(log_t), energy=math.exp(log_e),
                          cell_area=area, die_area=die)
        except (ValueError, TypeError, KeyError, OverflowError, ZeroDivisionError) as error:
            h = False
            p = 0
            reasons.append("measurement:" + str(error))
    else:
        h, p = False, 0
    return dict(functional_pass=f, gds_pass=g, joint_pass=f and g,
                constraint_pass=h, final_score=100 * p if f and g and h else 0,
                ratios=ratios, failure_reasons=reasons)


def summarize(rows):
    """Rows must include all planned slots; unstarted rows are not completed results."""
    if not rows:
        raise ValueError("An empty study cannot be summarized")
    counts = {key: sum(r.get(key) is True for r in rows)
              for key in ("functional_pass", "gds_pass", "joint_pass", "constraint_pass")}
    return dict(n=len(rows), **{key + "_rate": count / len(rows) for key, count in counts.items()},
                conditional_gds_rate=(counts["joint_pass"] / counts["functional_pass"]
                                      if counts["functional_pass"] else None),
                average_score=sum(r.get("final_score", 0) for r in rows) / len(rows),
                unfinished=sum(r.get("terminal") is not True for r in rows))
