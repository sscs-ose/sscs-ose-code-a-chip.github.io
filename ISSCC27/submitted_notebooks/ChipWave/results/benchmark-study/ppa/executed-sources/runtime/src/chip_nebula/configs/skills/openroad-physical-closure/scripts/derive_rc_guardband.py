#!/usr/bin/env python3
"""Derive bounded ORFS electrical margins from measured post/pre ratios."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any


def _percentile(values: list[float], quantile: float) -> float:
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * quantile
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    fraction = position - lower
    return ordered[lower] * (1.0 - fraction) + ordered[upper] * fraction


def _ratios(document: dict[str, Any], name: str) -> list[float]:
    raw = document.get(name)
    if not isinstance(raw, list) or not raw:
        raise ValueError(f"{name} must be a non-empty list")
    result: list[float] = []
    for value in raw:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"{name} values must be numbers")
        ratio = float(value)
        if not math.isfinite(ratio) or ratio <= 0:
            raise ValueError(f"{name} values must be positive finite ratios")
        result.append(ratio)
    return result


def derive(document: dict[str, Any]) -> dict[str, Any]:
    if document.get("schema_version") != 1:
        raise ValueError("schema_version must be 1")
    policy = document.get("policy", {})
    if not isinstance(policy, dict):
        raise ValueError("policy must be an object")
    quantile = float(policy.get("percentile", 0.95))
    safety = float(policy.get("safety_percent", 3.0))
    minimum = float(policy.get("min_percent", 0.0))
    maximum = float(policy.get("max_percent", 35.0))
    if not 0 <= quantile <= 1:
        raise ValueError("policy.percentile must be within 0..1")
    if not 0 <= minimum <= maximum <= 100:
        raise ValueError("policy margin bounds must satisfy 0 <= min <= max <= 100")
    if not 0 <= safety <= 100:
        raise ValueError("policy.safety_percent must be within 0..100")

    result: dict[str, Any] = {
        "schema_version": 1,
        "method": "bounded-percentile-post-over-pre-v1",
        "policy": {
            "percentile": quantile,
            "safety_percent": safety,
            "min_percent": minimum,
            "max_percent": maximum,
        },
    }
    for source, target in (
        ("slew_ratios", "slew_margin_percent"),
        ("capacitance_ratios", "cap_margin_percent"),
    ):
        ratios = _ratios(document, source)
        observed = _percentile(ratios, quantile)
        raw_margin = max(0.0, (observed - 1.0) * 100.0) + safety
        bounded = min(maximum, max(minimum, raw_margin))
        result[target] = round(bounded, 3)
        result[source] = {
            "sample_count": len(ratios),
            "percentile_ratio": round(observed, 6),
            "raw_margin_percent": round(raw_margin, 3),
            "clamped": not math.isclose(raw_margin, bounded, abs_tol=1e-12),
        }
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        document = json.loads(args.input.read_text(encoding="utf-8"))
        if not isinstance(document, dict):
            raise ValueError("input root must be an object")
        result = derive(document)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        parser.exit(2, f"guardband derivation failed: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
