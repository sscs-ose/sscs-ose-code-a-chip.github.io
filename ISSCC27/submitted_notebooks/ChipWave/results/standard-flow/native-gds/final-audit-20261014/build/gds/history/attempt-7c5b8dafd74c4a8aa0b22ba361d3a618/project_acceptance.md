# Frozen project acceptance audit

GDS export and installed-scope DRC/device LVS/negative controls passed; project audit fails: 41/48 checks pass, 6 mandatory checks pending and 26 typed adapter results not proven.

**Verdict: FAILED / NOT ACCEPTED.** Export success is not signoff or tapeout release.

Final snapshot: `sha256:566e131368689aa75e7522817500b485883cf637f9c71787ad02ae56937afa74`. Frozen acceptance revision 2, constraints revision 2, unchanged signed specification.

| Check | Result | Evidence / reason |
|---|---|---|
| AC-DELIVERY | PENDING | Verifier measured and validated the operator-delivered root contract previously; actual delivered root byte object and delivery manifest are absent from these four captured inputs. Their hash/report alone cannot prove current retrievability. Evidence: reports/verification/delivery.json, reports/verification/delivery-checker-tests.json |
| AC-ORIGINAL | PENDING | Original-source/checker inventory is retained, but full mapped synthesis confirmation is not directly delivered in this authorized read scope. An upstream Gate receipt alone does not close all original-implementation requirements. Evidence: reports/verification/structure/summary.json, reports/pnr/upstream_receipts.json |
| AC-RESOURCES | PENDING | Captured artifacts contain no development allocation, peak RAM/disk, cumulative token or full workflow wall-time receipts; verifier run time is not a substitute. Evidence: reports/verification/downstream-obligations.json |
| AC-PORTS | PASS | Qualified original verification evidence retained without rerunning. Evidence: reports/verification/structure/summary.json, reports/verification/t09-base.json |
| AC-INTEGRATION | PASS | Qualified original verification evidence retained without rerunning. Evidence: reports/verification/candidate-view.json, reports/verification/structure/summary.json |
| AC-STRUCTURE | PASS | Qualified original verification evidence retained without rerunning. Evidence: reports/verification/structure/summary.json, reports/verification/pipeline.json |
| AC-ISA | PASS | Qualified original verification evidence retained without rerunning. Evidence: reports/verification/t09-base.json, reports/verification/t09-enabled.json |
| AC-FETCH | PASS | Qualified original verification evidence retained without rerunning. Evidence: reports/verification/t09-base.json, reports/verification/t09-enabled.json |
| AC-RESET | PASS | Qualified original verification evidence retained without rerunning. Evidence: reports/verification/t09-base.json, reports/verification/t09-enabled.json |
| AC-MEMORY | PASS | Qualified original verification evidence retained without rerunning. Evidence: reports/verification/t09-base.json, reports/verification/t09-enabled.json |
| AC-HAZARDS | PASS | Qualified original verification evidence retained without rerunning. Evidence: reports/verification/t09-base.json, reports/verification/t09-enabled.json |
| AC-EXCEPTIONS | PASS | Qualified original verification evidence retained without rerunning. Evidence: reports/verification/t09-base.json, reports/verification/t09-enabled.json |
| AC-CSR | PASS | Qualified original verification evidence retained without rerunning. Evidence: reports/verification/t09-base.json, reports/verification/t09-enabled.json |
| AC-RETIREMENT | PASS | Qualified original verification evidence retained without rerunning. Evidence: reports/verification/t09-base.json, reports/verification/t09-enabled.json |
| AC-NPU-PORTS | PASS | Qualified original verification evidence retained without rerunning. Evidence: reports/verification/structure/summary.json |
| AC-NPU-ARITH | PASS | Qualified original verification evidence retained without rerunning. Evidence: reports/verification/regression-logs/npu-run.log, reports/verification/fixed-final.json |
| AC-NPU-PROTOCOL | PASS | Qualified original verification evidence retained without rerunning. Evidence: reports/verification/regression-logs/npu-run.log, reports/verification/regression-logs/integration-smoke-run.log |
| AC-NPU-CANCEL | PASS | Qualified original verification evidence retained without rerunning. Evidence: reports/verification/regression-logs/npu-run.log, reports/verification/npu-cancellation-run.log |
| AC-XDOT | PASS | Qualified original verification evidence retained without rerunning. Evidence: reports/performance/workloads.json, reports/verification/regression-logs/custom_traps_tb-0-run.log |
| AC-RUNTIME | PASS | Qualified original verification evidence retained without rerunning. Evidence: reports/verification/runtime.json, reports/verification/fixed-before.json |
| AC-ENVIRONMENT | PASS | Qualified original verification evidence retained without rerunning. Evidence: reports/verification/memory-comparison.json, reports/verification/raw-run-evidence.tar.gz |
| AC-TIMEOUT | PASS | Qualified original verification evidence retained without rerunning. Evidence: reports/verification/t09-base.json, reports/verification/t09-enabled.json |
| AC-ACT4 | PASS | Qualified original verification evidence retained without rerunning. Evidence: reports/verification/t09-base.json, reports/verification/t09-enabled.json |
| AC-DIRECTED | PASS | Qualified original verification evidence retained without rerunning. Evidence: reports/verification/t09-base.json, reports/verification/t09-enabled.json |
| AC-DIFFERENTIAL | PASS | Qualified original verification evidence retained without rerunning. Evidence: reports/verification/t09-base.json, reports/verification/t09-enabled.json |
| AC-BOUNDARIES | PASS | Qualified original verification evidence retained without rerunning. Evidence: reports/verification/t09-base.json, reports/verification/t09-enabled.json |
| AC-BUS | PASS | Qualified original verification evidence retained without rerunning. Evidence: reports/verification/t09-base.json, reports/verification/t09-enabled.json |
| AC-FLUSH | PASS | Qualified original verification evidence retained without rerunning. Evidence: reports/verification/t09-base.json, reports/verification/t09-enabled.json |
| AC-EVALUATOR-RELEASE | PENDING | Authorized resource excludes reference RTL and release mutation results; feedback requires parent-side independent fixed-checker replay after selected delivery. Evidence: reports/verification/downstream-obligations.json |
| AC-PIPELINE | PASS | Qualified original verification evidence retained without rerunning. Evidence: reports/verification/pipeline.json, reports/performance/cycles-base.json |
| AC-PUBLIC-SMOKE | PASS | Qualified original verification evidence retained without rerunning. Evidence: reports/verification/t09-base.json, reports/verification/t09-enabled.json |
| AC-CYCLES | PASS | Qualified original verification evidence retained without rerunning. Evidence: reports/performance/cycles-base.json, reports/performance/cycles-enabled.json |
| AC-DOT64 | PASS | Qualified original verification evidence retained without rerunning. Evidence: reports/performance/workloads.json, reports/verification/memory-comparison.json |
| AC-GEMM8 | PASS | Qualified original verification evidence retained without rerunning. Evidence: reports/performance/workloads.json, reports/verification/memory-comparison.json |
| AC-CONV3 | PASS | Qualified original verification evidence retained without rerunning. Evidence: reports/performance/workloads.json, reports/verification/memory-comparison.json |
| AC-SCORING | PASS | Qualified original verification evidence retained without rerunning. Evidence: reports/verification/scoring.json, reports/verification/t09-base.json |
| AC-PROJECT-COMPLETION | FAIL | Mandatory pending checkpoints and unproven typed adapter results prevent whole-project acceptance. Evidence: build/gds/project_acceptance.json, build/gds/adapter_audit.json |
| AC-PHYSICAL-INPUTS | PASS | Frozen V2 inputs, installed views, selected 4a7cf tool/2 threads and same-spec mapped input revalidated upstream; immutable reports verified here. Evidence: reports/pnr/input_audit.json, reports/pnr/tool_identity.json |
| AC-SYNTHESIS | PENDING | Mapped netlist and synthesis summary/Gate receipt are available via PnR; raw synthesis structural, cell/blackbox and state-to-netlist evidence is outside this task read scope and not reproduced here. Full checkpoint remains pending. Evidence: build/pnr/results/1_2_yosys.v, reports/pnr/upstream_receipts.json |
| AC-FLOORPLAN | PASS | Native planned versus legal-row bounds, integer DBU, margins, sites, placement and pin legality pass at placement/final snapshot. Evidence: reports/pnr/geometry_acceptance.json, reports/pnr/placement_geometry/geometry_acceptance.json |
| AC-PDN-ROUTING | PASS | Actual PG/support inventory, frozen PDN/track/route scripts and routed signal connectivity retained in the same snapshot. Evidence: reports/pnr/database_power_connections.tsv, reports/pnr/geometry_acceptance.json |
| AC-POSTROUTE-STA | PASS | TT 25C/1.8V, propagated 100 ns clock, uncertainty 0.1 ns, nominal R/C and derates 1.0; setup and hold pass. Single corner only. Evidence: reports/pnr/sta_timing.json, reports/pnr/sta_setup_paths.rpt |
| AC-ELECTRICAL | PASS | Characterized slew/capacitance, recovery/removal/pulse checks and frozen external reset waveform pass; characterized fanout ceiling unavailable, structural maximum reported. Evidence: reports/pnr/database_max_slew.rpt, reports/pnr/database_max_capacitance.rpt |
| AC-ROUTE-CLEAN | PASS | Final router DRC/antenna are zero, all functional nets routed, completed execution bound to unchanged final ODB. Evidence: reports/pnr/5_2_route.log, reports/pnr/final_antenna.json |
| AC-EXPORT-CONSISTENCY | PASS | Final ODB versus STA netlist/SPEF identity, ownership/connectivity and 9734 path reload comparisons pass within 1e-6 ns. Evidence: reports/pnr/post_route_export_consistency.json, reports/pnr/spef_binding_audit.json |
| AC-DRC-LVS | PASS | Installed frozen decks on this exact export: DRC zero, nonempty MOS-device-extracted hierarchical LVS matched; metal-width and missing-poly negative controls detected. FEOL DRC/general density excluded. Evidence: build/gds/checks.json, build/gds/drc.lyrdb |
| AC-POWER-AREA | PENDING | Final area accounting is available, but DOT64/GEMM8/CONV3 post-route workload execution and activity windows are absent. Report-only power unavailability is allowed; mandatory final-design functional reruns are not waived. Evidence: reports/pnr/area_and_fanout.json, reports/performance/workloads.json |
| AC-GDS | PASS | Streamed from read-only final ODB via byte-identical regenerated DEF; top/master multiplicities/port labels match; all GDS geometry equals accepted upstream export. AC-POWER-AREA remains a blocking dependency. Evidence: build/gds/readability.json, build/gds/port_boundary.json |

26 required adapters are explicitly listed in adapter_audit.json; 0 has direct operand execution proof. Typed declarations/check links alone are not counted as proven per-operand adapter execution. All 443 requirement rows are retained in requirements_audit.json. Check-level passing evidence does not imply project requirement closure.

Remaining scope limitations:

- FEOL DRC disabled in frozen deck; general metal density not covered beyond vpp overlap rules.
- Only Sky130HD tt_025C_1v80 nominal 100 ns scenario; no multi-corner STA/foundry signoff.
- Independent ERC, EM/IR, pad/package qualification and foundry authorization unavailable.
- Full RTL-to-synthesis formal equivalence was not supplied; mapped-to-post-route equivalence is retained.
- No fabricated-silicon evidence or tapeout.release/signoff claim. Negative GDS files are deliberate corruptions for checker tests only.
