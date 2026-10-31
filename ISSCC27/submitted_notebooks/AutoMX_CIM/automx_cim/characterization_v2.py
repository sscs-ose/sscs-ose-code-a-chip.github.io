"""Training-only held-node LUT surrogate for the 2+2 TT readout experiment.

This estimates voltage for unmeasured vectors from measured *sum levels*.
Its tiny-MHA output is architectural sensitivity analysis, not ADC evidence.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np

from .characterization import CIMMacroModel


@dataclass
class HeldNodeMacroModel(CIMMacroModel):
    measured_pattern_invocations: int = 0
    estimated_pattern_invocations: int = 0
    _training_lookup: dict[tuple, tuple[float, ...]] = field(
        default_factory=dict, init=False, repr=False)

    def __post_init__(self) -> None:
        if (self.characterization.get("format") !=
                "automx-cim-stage6-held-node-characterization-v2" or
                self.characterization.get("status") not in {
                    "TT_HELD_NODE_DIAGNOSTIC_V2",
                    "TT_HELD_NODE_EXPLORATORY_CM_UNVERIFIED_V2",
                }):
            raise ValueError("Stage-6 v2 held-node characterization required")
        grouped: dict[tuple, list[tuple[float, ...]]] = {}
        for item in self.characterization["training_vectors"]:
            key = (item["phase"], tuple(item["activation_x2"]),
                   tuple(tuple(row) for row in item["ternary_weights"]))
            value = tuple(item["held_differential_v"])
            grouped.setdefault(key, []).append(value)
        self._training_lookup = {
            key: tuple(sum(row[lane] for row in rows) / len(rows)
                       for lane in range(4))
            for key, rows in grouped.items()}

    def tile(self, act_x2: np.ndarray, ternary: np.ndarray) -> np.ndarray:
        act = np.asarray(act_x2, dtype=np.int64)
        weights = np.asarray(ternary, dtype=np.int64)
        if (act.shape != (32,) or weights.shape != (32, 8) or
                not np.isin(weights, (-1, 0, 1)).all() or
                not np.isin(np.abs(act), (0, 1, 2, 3, 4, 6, 8, 12)).all()):
            raise ValueError("logical 32x8 base-only MXFP4/ternary tile required")
        output = np.zeros(8, dtype=float)
        phases = self.characterization["decoder"]["phases"]
        max_code = self.characterization["physical"]["measured_activation_abs_x2_max"]
        for row in range(0, 32, 4):
            for col in range(0, 8, 4):
                block = weights[row:row + 4, col:col + 4]
                self.max_abs_code_seen = max(self.max_abs_code_seen,
                                             int(np.max(np.abs(act[row:row + 4]))))
                code_outside = np.any(np.abs(act[row:row + 4]) > max_code)
                self.extrapolated_macro_codes += int(code_outside)
                exact_pair = True
                for phase, active in (("a", (0, 1)), ("b", (2, 3))):
                    phase_act = tuple(int(act[row + local]) if local in active else 0
                                      for local in range(4))
                    matrix = tuple(tuple(int(x) for x in line) for line in block)
                    key = (phase, phase_act, matrix)
                    voltages = self._training_lookup.get(key)
                    exact_pair &= voltages is not None
                    for lane in range(4):
                        level = sum(phase_act[local] * matrix[local][lane]
                                    for local in range(4))
                        column = phases[phase]["columns"][lane]
                        levels = column["sum_levels"]
                        if level not in levels:
                            self.sum_outside_columns += 1
                            raise ValueError(f"uncharacterized partial level {level}")
                        index = levels.index(level)
                        interval = column["intervals"][index]
                        voltage = (voltages[lane] if voltages is not None else
                                   (interval["minimum_v"] + interval["maximum_v"]) / 2)
                        decoded = int(np.searchsorted(column["thresholds_v"],
                                                       voltage, side="right"))
                        output[col + lane] += levels[decoded]
                self.evaluated_columns += 4
                self.code_outside_columns += 4 * int(code_outside)
                self.extrapolated_columns += 4 * int(code_outside)
                self.measured_pattern_invocations += int(exact_pair)
                self.estimated_pattern_invocations += int(not exact_pair)
        return output
