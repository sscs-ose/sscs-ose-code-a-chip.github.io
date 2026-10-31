"""ngspice measurement parsing and Stage-4 electrical checks."""
from __future__ import annotations

import math
import re
from typing import Mapping, Sequence

_NUMBER = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?"
_MEASURE = re.compile(rf"^\s*([A-Za-z][A-Za-z0-9_]*)\s*=\s*({_NUMBER})", re.MULTILINE)

def parse_measurements(log: str, expected: Sequence[str] | None = None) -> dict[str, float]:
    """Parse scalar ngspice results, optionally keeping declared measures only.

    ngspice 31 prints internal assignments such as ``stack = ...`` using the
    same textual shape as a ``.measure`` result. The manifest allow-list is
    therefore the authoritative namespace when multiple decks are merged.
    """
    allowed = None if expected is None else {name.lower() for name in expected}
    values: dict[str, float] = {}
    for match in _MEASURE.finditer(log):
        key = match.group(1).lower()
        if allowed is None or key in allowed:
            values[key] = float(match.group(2))
    return values

def validate_measurements(cases: Sequence[Mapping[str, object]], delay_names: Sequence[str],
                          measurements: Mapping[str, float], energy_name: str = "energy_j",
                          zero_tolerance_v: float = 5e-3,
                          minimum_sense_v: float = 1e-3,
                          saturation_drop_ratio: float = 0.01) -> tuple[dict[str, object], list[str]]:
    """Validate sign, zero suppression, monotonicity, delay, and energy."""
    failures: list[str] = []
    normalized = {str(k).lower(): float(v) for k, v in measurements.items()}
    groups: dict[str, list[tuple[int, float]]] = {}
    nonzero_swings: list[float] = []
    zero_swings: list[float] = []
    for case in cases:
        key = str(case["measurement"]).lower(); expected = int(case["expected"])
        if key not in normalized or not math.isfinite(normalized[key]):
            failures.append(f"missing/non-finite measurement {key}"); continue
        value = normalized[key]
        if expected == 0:
            zero_swings.append(abs(value))
            if abs(value) > zero_tolerance_v:
                failures.append(f"{key}: zero case |{value:.6g}| V > {zero_tolerance_v:.6g} V")
        else:
            nonzero_swings.append(abs(value))
            if value * expected <= 0:
                failures.append(f"{key}: sign mismatch, expected integer {expected}, measured {value:.6g} V")
            if abs(value) < minimum_sense_v:
                failures.append(f"{key}: sense swing {abs(value):.6g} V < {minimum_sense_v:.6g} V")
        groups.setdefault(str(case.get("group", "default")), []).append((abs(expected), abs(value)))
    saturation_groups: set[str] = set()
    observed_drops: list[float] = []
    for group, points in groups.items():
        ordered = sorted({x: y for x, y in points}.items())
        for (x0, y0), (x1, y1) in zip(ordered, ordered[1:]):
            if x1 <= x0 or y1 >= y0:
                continue
            drop = y0 - y1
            observed_drops.append(drop)
            allowed_drop = max(zero_tolerance_v, saturation_drop_ratio * max(y0, y1))
            if drop > allowed_drop:
                failures.append(
                    f"{group}: non-monotonic swing {y0:.6g} V at {x0} -> {y1:.6g} V at {x1}; "
                    f"drop {drop:.6g} V exceeds saturation tolerance {allowed_drop:.6g} V"
                )
            else:
                saturation_groups.add(group)
    delays = []
    for name in delay_names:
        key = name.lower()
        if key not in normalized or not math.isfinite(normalized[key]):
            failures.append(f"missing/non-finite delay {key}")
        elif normalized[key] <= 0:
            failures.append(f"{key}: non-positive delay {normalized[key]:.6g} s")
        else:
            delays.append(normalized[key])
    energy_key = energy_name.lower()
    energy = normalized.get(energy_key)
    if energy is None or not math.isfinite(energy):
        failures.append(f"missing/non-finite energy {energy_key}")
    elif energy <= 0:
        failures.append(f"{energy_key}: non-positive energy {energy:.6g} J")
    metrics = {
        "case_count": len(cases),
        "minimum_nonzero_sense_v": min(nonzero_swings) if nonzero_swings else None,
        "maximum_zero_offset_v": max(zero_swings) if zero_swings else None,
        "maximum_delay_s": max(delays) if delays else None,
        "dynamic_energy_j": energy,
        "saturation_detected": bool(saturation_groups),
        "saturation_groups": sorted(saturation_groups),
        "maximum_observed_drop_v": max(observed_drops) if observed_drops else 0.0,
        "saturation_drop_tolerance_ratio": saturation_drop_ratio,
    }
    return metrics, failures