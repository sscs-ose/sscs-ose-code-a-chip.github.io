"""Evaluate named metrics and constraints independently of the circuit adapter."""
import json
import math


def validate_policy(policy):
    if set(policy) != {"metrics"} or not policy["metrics"]:
        raise ValueError("Define a nonempty metrics table.")
    for name, metric in policy["metrics"].items():
        allowed = {"label", "display_unit", "display_scale", "target", "scale", "weight", "constraints", "measurement", "frequency_Hz", "prediction_absolute_tolerance"}
        if set(metric)-allowed:
            raise ValueError(f"Unknown metric setting: {name}")
        scale = metric.get("scale", abs(metric["target"]))
        numbers = [metric["target"], scale, metric["weight"], metric.get("display_scale", 1)]
        if not all(math.isfinite(v) for v in numbers) or scale <= 0 or metric["weight"] < 0 or numbers[-1] <= 0:
            raise ValueError(f"Invalid target, scale, weight, or display scale: {name}")
        constraints = metric.get("constraints", {})
        allowed = {"minimum", "maximum", "max_error_percent", "no_worse_than_baseline", "tolerance_percent"}
        if set(constraints)-allowed:
            raise ValueError(f"Unknown constraint: {name}")
        for key in ("minimum", "maximum", "max_error_percent", "tolerance_percent"):
            value = constraints.get(key)
            if value is not None and (not math.isfinite(value) or (key.endswith("percent") and value < 0)):
                raise ValueError(f"Invalid constraint: {name}/{key}")
        if not isinstance(constraints.get("no_worse_than_baseline", False), bool):
            raise ValueError(f"Use true or false for the baseline constraint: {name}")
        low, high = constraints.get("minimum"), constraints.get("maximum")
        if low is not None and high is not None and low > high:
            raise ValueError(f"Minimum exceeds maximum: {name}")
    return policy


def evaluate_metrics(values, policy):
    result = {}
    for name, metric in policy["metrics"].items():
        value, target = values[name], metric["target"]
        if not math.isfinite(value):
            raise ValueError(f"Non-finite metric: {name}")
        scale = metric.get("scale", abs(target))
        error = (value-target)/scale
        result[name] = {"value":value, "error_percent":100*error,
                        "objective":0.5*metric["weight"]*error**2,
                        "dJ_dvalue":metric["weight"]*error/scale}
    return result


def constraint_report(values, baseline, policy):
    measured, reference = evaluate_metrics(values, policy), evaluate_metrics(baseline, policy)
    failures = []
    for name, metric in policy["metrics"].items():
        constraints = metric.get("constraints", {})
        error = abs(measured[name]["error_percent"])
        tolerance = constraints.get("tolerance_percent", 0)

        margin = metric.get("scale", abs(metric["target"]))*tolerance/100
        label, value = metric["label"], values[name]
        if constraints.get("minimum") is not None and value < constraints["minimum"]-margin:
            failures.append(f"{label}: below minimum")
        if constraints.get("maximum") is not None and value > constraints["maximum"]+margin:
            failures.append(f"{label}: above maximum")
        if constraints.get("max_error_percent") is not None and error > constraints["max_error_percent"]+tolerance:
            failures.append(f"{label}: error exceeds limit")
        if constraints.get("no_worse_than_baseline") and error > abs(reference[name]["error_percent"])+tolerance:
            failures.append(f"{label}: error worsens")
    return {"passed":not failures, "failures":failures}


def predicted_metrics(baseline, changes, policy):
    values = {name:baseline[name]+changes[name] for name in policy["metrics"]}
    return {"values":values, "changes":changes, "metrics":evaluate_metrics(values, policy),
            "constraints":constraint_report(values, baseline, policy)}
