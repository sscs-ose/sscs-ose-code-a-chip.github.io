# Experiment Protocol — Frozen MVP

## 1. Experimental object

One parameterized square GEMM systolic-array RTL design, instantiated as:

- 2×2
- 4×4
- 8×8

Arithmetic:

- signed INT8 operands;
- INT32 accumulator;
- overflow behavior must be explicitly defined and identical in model and RTL.

Dataflow:

- output-stationary only.

The architecture model and RTL must share a documented cycle convention for fill, steady state, drain, tiling, and result-valid timing.

## 2. Pre-registered workloads

| ID | M | N | K | Purpose |
|---|---:|---:|---:|---|
| W1 | 4 | 4 | 4 | underfilled / small problem |
| W2 | 8 | 8 | 8 | exact-fit regime for 8×8 |
| W3 | 16 | 16 | 16 | tiled square GEMM |
| W4 | 32 | 32 | 32 | larger tiled square GEMM |
| W5 | 32 | 8 | 32 | aspect-ratio stress |
| W6 | 32 | 32 | 8 | short-K / pipeline-overhead stress |

Do not alter this set after Phase 3 begins without an explicit research-lead decision recorded in `docs/DECISIONS.md`.

## 3. Stage A — Architecture model

The model must output at least:

- configuration ID;
- workload ID;
- predicted cycles;
- documented utilization or activity metric if implemented;
- model version / Git commit;
- deterministic seed where relevant.

No implementation-derived Fmax may feed back into the architecture cycle model.

## 4. Stage B — RTL verification

Before physical evaluation:

- compare numerical GEMM outputs against a Python golden model;
- compare model cycle count with RTL-observed cycle count under the same convention;
- use deterministic randomized regression;
- preserve failing seeds and waveforms/logs when debugging;
- do not move to Phase 2 until the 2×2 regression gate is passed.

A model/RTL cycle mismatch is presumed to be a bug or convention mismatch until demonstrated otherwise. It is not automatically a research finding.

## 5. Stage C — Physical implementation

For the final experiment, every 2×2 / 4×4 / 8×8 configuration must use the same frozen recipe except for parameters that unavoidably scale with the design and are explicitly declared.

Freeze and record:

- OpenLane version;
- OpenROAD version;
- Yosys version;
- PDK identifier/version;
- standard-cell library;
- timing corner(s) used for the reported result;
- target clock / clock constraint methodology;
- floorplanning policy;
- core utilization policy;
- routing / placement settings that materially affect comparability;
- exact config files;
- exact invocation command.

Do not independently tune each configuration to maximize its result unless the research protocol is explicitly changed before seeing final rankings.

## 6. Timing-derived metric

Do not label a backend timing result as measured Fmax.

The final implementation frequency quantity must be derived by one documented, scripted rule from preserved timing output. The exact rule is frozen after Phase 0/2 validation and before final Phase 3 data collection.

If the chosen flow only supplies slack at a requested clock period, derive/report a quantity only if the derivation is technically justified and documented. Otherwise report period/slack directly and compute implementation latency using the approved timing methodology.

## 7. Main analysis

For configuration `i`, workload `w`:

```text
T_impl[i,w] = C_rtl[i,w] / F_sta[i]
```

where `F_sta` means the approved STA-derived frequency estimate, not measured silicon frequency.

Primary metrics:

### Top-1 agreement

For each workload, compare:

```text
argmin_i C_model[i,w]
```

with:

```text
argmin_i T_impl[i,w]
```

Report count/6. Do not hide ties; define tie handling before Phase 3.

### Pairwise decision agreement

For the 3 configurations there are 3 pairwise comparisons per workload, or 18 total pairwise decisions across 6 workloads.

Classify each as:

- preserved;
- tied/indeterminate under the predefined rule;
- reversed.

### Decision-margin transformation

For pair `(i,j)` and workload `w`:

```text
M_arch(i,j,w) = log(C_model[i,w] / C_model[j,w])
M_impl(i,j,w) = log(T_impl[i,w] / T_impl[j,w])
```

Analyze whether implementation timing widens, narrows, or reverses the high-level margin.

Kendall/Spearman statistics may be reported as secondary descriptors if meaningful with the small design set; do not use them to create false statistical sophistication.

## 8. Main figures

1. **Model vs RTL cycle correctness** — establishes matched semantics.
2. **Post-route physical scaling** — timing and area for 2×2/4×4/8×8.
3. **Architecture cycles vs implementation-aware latency** — primary cross-layer result across workloads.
4. **Pairwise decision heatmap** — 18 pairwise decisions labeled preserved/tied/reversed, with margin change where useful.
5. **Architecture-to-implementation margin transformation** — show how `M_arch` maps to `M_impl`; omit if it adds no insight.

## 9. Null-result handling

If no ranking reversal occurs, report exactly that within the evaluated domain. Then analyze:

- whether margins were narrowed or widened;
- how close pairwise decisions came to reversal;
- which physical effects contributed to the correction;
- what the result does and does not establish.

Do not claim general simulator reliability from this limited experiment.

## 10. Optional sensitivity analysis

Only after the main frozen experiment is complete and reproducible may one small preregistered backend perturbation be tested as a secondary sensitivity check. It must not replace the main question and must not be selected after seeing which setting produces a reversal.
