# AutoAccel Project Summary

Generated: 2026-10-31

## Project objective

Evaluate conventional, single-level Karatsuba, and recursive (threshold-based) Karatsuba multiplier architectures using RTL simulation, synthesis-based generic logic-cell comparison, formal verification, and sky130_fd_sc_hd standard-cell PPA (area, static timing, static leakage).

## Synthesis comparison and recommendations

| Width | Conventional cells | Karatsuba cells | Recommended architecture | Cell-count reduction |
|---:|---:|---:|---|---:|
| 8 | 404 | 492 | Conventional | 17.89% |
| 16 | 1,903 | 1,685 | Karatsuba | 11.46% |
| 32 | 8,306 | 5,943 | Karatsuba | 28.45% |
| 64 | 34,837 | 21,581 | Karatsuba | 38.05% |

## sky130 mapped results (summary)

Mapped cell area (um^2) versus conventional at tt_025C_1v80: recursive Karatsuba -5.6% (N=8); recursive Karatsuba -4.4% (N=16); recursive Karatsuba -16.6% (N=32); recursive Karatsuba -32.8% (N=64). ABC static-timing delay favors the conventional design at every width under the area-oriented mapping. Details in results/sky130_baseline.csv and results/sky130_comparison.csv.

## Verification status

- Conventional simulation: 108 vectors each passed at N=8, N=16, and N=32 in the recorded audit run.
- Karatsuba simulation: 1,045 vectors each passed at N=8, N=16, and N=32 in the recorded audit run.
- Formal equivalence: N=8 passed with SymbiYosys and Bitwuzla for both Karatsuba variants; the recursive architecture was also verified against a bit-accurate software model (exhaustive N<=8; 150,000+ vectors each at N=16, 32, 64; see formal/logs/recursive_model_verify.log).
- N=16 formal equivalence: unresolved; the full 32-bit output proof timed out. Bit 0 passed, but that does not prove the full output. No confirmed counterexample was established by the timeout runs.
- Selector unit tests: 4 tests passed in the recorded audit run.

## Interpretation and limitations

Recommendations minimize the generic logic-cell count reported by the current synthesis flow. These counts are not physical silicon area measurements and do not establish power consumption or timing. The sky130 mapped results add cell area, ABC static timing, and static leakage at the tt_025C_1v80 corner, but still no placement, routing, or dynamic power.

The recommendations apply to the tested operand widths and current RTL and synthesis configuration. Further verification and technology-specific implementation are needed before making broader hardware performance claims.

The repository is licensed under Apache-2.0 (LICENSE at the repository root) and includes the openly licensed analysis notebook required by the IEEE SSCS Code-a-Chip submission instructions. Confirm both against the current submission checklist.
