"""Standalone testbench for the three concrete phase detectors.

This exercises:
    - SingleFlipFlopPhaseDetector
    - EdgeLevelPhaseDetector
    - PFDPhaseDetector

For each detector, the testbench checks:
    - clk_in arrives first  -> up asserted
    - clk_out arrives first -> down asserted
    - aligned edges         -> neither asserted
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from simulator import (
        EdgeLevelPhaseDetector,
        PFDPhaseDetector,
        SingleFlipFlopPhaseDetector,
    )
else:
    from . import (
        EdgeLevelPhaseDetector,
        PFDPhaseDetector,
        SingleFlipFlopPhaseDetector,
    )


@dataclass(frozen=True)
class Scenario:
    name: str
    clk_in_edge_ps: float
    clk_out_edge_ps: float
    expected_up: int
    expected_down: int


SCENARIOS = [
    Scenario(
        name="clk_in_leads",
        clk_in_edge_ps=1000.0,
        clk_out_edge_ps=1200.0,
        expected_up=1,
        expected_down=0,
    ),
    Scenario(
        name="clk_out_leads",
        clk_in_edge_ps=1200.0,
        clk_out_edge_ps=1000.0,
        expected_up=0,
        expected_down=1,
    ),
    Scenario(
        name="aligned",
        clk_in_edge_ps=1000.0,
        clk_out_edge_ps=1000.0,
        expected_up=0,
        expected_down=0,
    ),
]


def expected_valid_time(detector, scenario: Scenario) -> float:
    latest_edge = max(scenario.clk_in_edge_ps, scenario.clk_out_edge_ps)
    if scenario.expected_up:
        return latest_edge + detector.up_prop_delay_ps
    if scenario.expected_down:
        return latest_edge + detector.down_prop_delay_ps
    return latest_edge


def run_testbench() -> int:
    detectors = [
        ("FF1", SingleFlipFlopPhaseDetector()),
        ("EdgeLevel", EdgeLevelPhaseDetector()),
        ("PFD", PFDPhaseDetector()),
    ]

    failures = 0

    for detector_name, detector in detectors:
        print()
        print(f"=== {detector_name} ===")
        print(
            f"up_prop_delay_ps={detector.up_prop_delay_ps:.2f}, "
            f"down_prop_delay_ps={detector.down_prop_delay_ps:.2f}"
        )
        print("scenario         clk_in   clk_out   up  down  valid_time   result")

        for scenario in SCENARIOS:
            up, down, valid_time = detector.detect(
                scenario.clk_in_edge_ps,
                scenario.clk_out_edge_ps,
            )
            expected_time = expected_valid_time(detector, scenario)
            passed = (
                up == scenario.expected_up
                and down == scenario.expected_down
                and abs(valid_time - expected_time) < 1e-9
            )
            status = "PASS" if passed else "FAIL"
            if not passed:
                failures += 1

            print(
                f"{scenario.name:<15}  "
                f"{scenario.clk_in_edge_ps:7.1f}  "
                f"{scenario.clk_out_edge_ps:8.1f}  "
                f"{up:2d}  {down:4d}  "
                f"{valid_time:10.2f}  {status}"
            )

            if not passed:
                print(
                    "  expected:"
                    f" up={scenario.expected_up},"
                    f" down={scenario.expected_down},"
                    f" valid_time={expected_time:.2f}"
                )

    print()
    if failures:
        print(f"FAILED: {failures} scenario checks failed.")
        return 1

    print("PASSED: all phase detector checks succeeded.")
    return 0


if __name__ == "__main__":
    raise SystemExit(run_testbench())
