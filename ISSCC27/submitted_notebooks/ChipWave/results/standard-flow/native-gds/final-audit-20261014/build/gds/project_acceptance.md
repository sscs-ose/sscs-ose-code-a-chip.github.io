# Frozen project acceptance audit

Physical/export passed; AC-POWER-AREA source-qualified owner receipt adopted. Whole-project acceptance failed: 45/48 direct checks passed, 1 pending, 2 failed; 1/26 typed adapters proven.

**Physical/export: PASSED. AC-POWER-AREA: PASSED in the qualified estimate scope. Whole-project: FAILED / NOT ACCEPTED.**

Snapshot: `sha256:566e131368689aa75e7522817500b485883cf637f9c71787ad02ae56937afa74`. No physical input or exported GDS was edited. Prior failed/unavailable reports are preserved in `history/attempt-cf266b46df624d72941221bc4ba42d7e/`.

| Check | Direct result | Acceptance result | Evidence / reason |
|---|---|---|---|
| AC-DELIVERY | PASS | passed | Actual native 6930-byte root contract equals frozen source lines19..EOF; regular path, manifest, companion and source-identical RTL directly revalidated. Prior missing-input audit is preserved. Evidence: build/gds/evidence/authorized-root-project-delivery/delivery/standard-project/t09-base-contract.md, build/gds/evidence/authorized-root-project-delivery/delivery/standard-project/project-delivery.manifest.json |
| AC-ORIGINAL | PASS | passed | Qualified verifier source/checker lineage and unchanged RTL inventory are now joined to the real captured synthesizable V2 mapped design; no new originality or reference-release claims inferred. Evidence: reports/verification/structure/summary.json, reports/verification/fixed-final.json |
| AC-RESOURCES | FAIL | failed | Captured operator observation confirms historical standard RTL development exceeds frozen 2h budget. Historical peak RAM/disk, cumulative tokens/allocation receipts remain unavailable; no retrospective rerun can erase the failure. Evidence: build/gds/resource_audit.json, build/gds/operator_feedback.json |
| AC-PORTS | PASS | passed | Qualified original verification evidence retained without rerunning. Evidence: reports/verification/structure/summary.json, reports/verification/t09-base.json |
| AC-INTEGRATION | PASS | passed | Qualified original verification evidence retained without rerunning. Evidence: reports/verification/candidate-view.json, reports/verification/structure/summary.json |
| AC-STRUCTURE | PASS | passed | Qualified original verification evidence retained without rerunning. Evidence: reports/verification/structure/summary.json, reports/verification/pipeline.json |
| AC-ISA | PASS | passed | Qualified original verification evidence retained without rerunning. Evidence: reports/verification/t09-base.json, reports/verification/t09-enabled.json |
| AC-FETCH | PASS | passed | Qualified original verification evidence retained without rerunning. Evidence: reports/verification/t09-base.json, reports/verification/t09-enabled.json |
| AC-RESET | PASS | passed | Qualified original verification evidence retained without rerunning. Evidence: reports/verification/t09-base.json, reports/verification/t09-enabled.json |
| AC-MEMORY | PASS | passed | Qualified original verification evidence retained without rerunning. Evidence: reports/verification/t09-base.json, reports/verification/t09-enabled.json |
| AC-HAZARDS | PASS | passed | Qualified original verification evidence retained without rerunning. Evidence: reports/verification/t09-base.json, reports/verification/t09-enabled.json |
| AC-EXCEPTIONS | PASS | passed | Qualified original verification evidence retained without rerunning. Evidence: reports/verification/t09-base.json, reports/verification/t09-enabled.json |
| AC-CSR | PASS | passed | Qualified original verification evidence retained without rerunning. Evidence: reports/verification/t09-base.json, reports/verification/t09-enabled.json |
| AC-RETIREMENT | PASS | passed | Qualified original verification evidence retained without rerunning. Evidence: reports/verification/t09-base.json, reports/verification/t09-enabled.json |
| AC-NPU-PORTS | PASS | passed | Qualified original verification evidence retained without rerunning. Evidence: reports/verification/structure/summary.json |
| AC-NPU-ARITH | PASS | passed | Qualified original verification evidence retained without rerunning. Evidence: reports/verification/regression-logs/npu-run.log, reports/verification/fixed-final.json |
| AC-NPU-PROTOCOL | PASS | passed | Qualified original verification evidence retained without rerunning. Evidence: reports/verification/regression-logs/npu-run.log, reports/verification/regression-logs/integration-smoke-run.log |
| AC-NPU-CANCEL | PASS | passed | Qualified original verification evidence retained without rerunning. Evidence: reports/verification/regression-logs/npu-run.log, reports/verification/npu-cancellation-run.log |
| AC-XDOT | PASS | passed | Qualified original verification evidence retained without rerunning. Evidence: reports/performance/workloads.json, reports/verification/regression-logs/custom_traps_tb-0-run.log |
| AC-RUNTIME | PASS | passed | Qualified original verification evidence retained without rerunning. Evidence: reports/verification/runtime.json, reports/verification/fixed-before.json |
| AC-ENVIRONMENT | PASS | passed | Qualified original verification evidence retained without rerunning. Evidence: reports/verification/memory-comparison.json, reports/verification/raw-run-evidence.tar.gz |
| AC-TIMEOUT | PASS | passed | Qualified original verification evidence retained without rerunning. Evidence: reports/verification/t09-base.json, reports/verification/t09-enabled.json |
| AC-ACT4 | PASS | passed | Qualified original verification evidence retained without rerunning. Evidence: reports/verification/t09-base.json, reports/verification/t09-enabled.json |
| AC-DIRECTED | PASS | passed | Qualified original verification evidence retained without rerunning. Evidence: reports/verification/t09-base.json, reports/verification/t09-enabled.json |
| AC-DIFFERENTIAL | PASS | passed | Qualified original verification evidence retained without rerunning. Evidence: reports/verification/t09-base.json, reports/verification/t09-enabled.json |
| AC-BOUNDARIES | PASS | passed | Qualified original verification evidence retained without rerunning. Evidence: reports/verification/t09-base.json, reports/verification/t09-enabled.json |
| AC-BUS | PASS | passed | Qualified original verification evidence retained without rerunning. Evidence: reports/verification/t09-base.json, reports/verification/t09-enabled.json |
| AC-FLUSH | PASS | passed | Qualified original verification evidence retained without rerunning. Evidence: reports/verification/t09-base.json, reports/verification/t09-enabled.json |
| AC-EVALUATOR-RELEASE | PENDING | deferred | Full source-bound known-reference hazard/exception/handshake evaluator-owner release audit is absent. Parent common-checker replay and three preset NPU faults do not satisfy this obligation. Evidence: reports/verification/downstream-obligations.json, build/gds/operator_feedback.json |
| AC-PIPELINE | PASS | passed | Qualified original verification evidence retained without rerunning. Evidence: reports/verification/pipeline.json, reports/performance/cycles-base.json |
| AC-PUBLIC-SMOKE | PASS | passed | Qualified original verification evidence retained without rerunning. Evidence: reports/verification/t09-base.json, reports/verification/t09-enabled.json |
| AC-CYCLES | PASS | passed | Qualified original verification evidence retained without rerunning. Evidence: reports/performance/cycles-base.json, reports/performance/cycles-enabled.json |
| AC-DOT64 | PASS | passed | Qualified original verification evidence retained without rerunning. Evidence: reports/performance/workloads.json, reports/verification/memory-comparison.json |
| AC-GEMM8 | PASS | passed | Qualified original verification evidence retained without rerunning. Evidence: reports/performance/workloads.json, reports/verification/memory-comparison.json |
| AC-CONV3 | PASS | passed | Qualified original verification evidence retained without rerunning. Evidence: reports/performance/workloads.json, reports/verification/memory-comparison.json |
| AC-SCORING | PASS | deferred | Qualified original verification evidence retained without rerunning. Evidence: reports/verification/scoring.json, reports/verification/t09-base.json |
| AC-PROJECT-COMPLETION | FAIL | failed | Historical resource failure, pending independent evaluator release and unproven typed adapters prevent whole-project acceptance; AC-POWER-AREA owner evidence is now qualified. Evidence: build/gds/project_acceptance.json, build/gds/adapter_audit.json |
| AC-PHYSICAL-INPUTS | PASS | passed | Frozen V2 inputs, installed views, selected 4a7cf tool/2 threads and same-spec mapped input revalidated upstream; immutable reports verified here. Evidence: reports/pnr/input_audit.json, reports/pnr/tool_identity.json |
| AC-SYNTHESIS | PASS | passed | Source-identical frozen V2 mapping directly checked: 16683 characterized cells, no macro/latch/unmapped/forbidden cells, exact ports, 1024 RF flops and nonempty pipeline/NPU state groups. Existing synthesis/STA logs pass; full formal RTL equivalence remains unexecuted. Evidence: build/gds/evidence/artifact-0b514721fd8641408ffcec0d7f4350ec/build/synth/nebula_cpu_npu_top.v, build/gds/evidence/artifact-0b514721fd8641408ffcec0d7f4350ec/build/synth/mapped.json |
| AC-FLOORPLAN | PASS | passed | Native planned versus legal-row bounds, integer DBU, margins, sites, placement and pin legality pass at placement/final snapshot. Evidence: reports/pnr/geometry_acceptance.json, reports/pnr/placement_geometry/geometry_acceptance.json |
| AC-PDN-ROUTING | PASS | passed | Actual PG/support inventory, frozen PDN/track/route scripts and routed signal connectivity retained in the same snapshot. Evidence: reports/pnr/database_power_connections.tsv, reports/pnr/geometry_acceptance.json |
| AC-POSTROUTE-STA | PASS | passed | TT 25C/1.8V, propagated 100 ns clock, uncertainty 0.1 ns, nominal R/C and derates 1.0; setup and hold pass. Single corner only. Evidence: reports/pnr/sta_timing.json, reports/pnr/sta_setup_paths.rpt |
| AC-ELECTRICAL | PASS | passed | Characterized slew/capacitance, recovery/removal/pulse checks and frozen external reset waveform pass; characterized fanout ceiling unavailable, structural maximum reported. Evidence: reports/pnr/database_max_slew.rpt, reports/pnr/database_max_capacitance.rpt |
| AC-ROUTE-CLEAN | PASS | passed | Final router DRC/antenna are zero, all functional nets routed, completed execution bound to unchanged final ODB. Evidence: reports/pnr/5_2_route.log, reports/pnr/final_antenna.json |
| AC-EXPORT-CONSISTENCY | PASS | passed | Final ODB versus STA netlist/SPEF identity, ownership/connectivity and 9734 path reload comparisons pass within 1e-6 ns. Evidence: reports/pnr/post_route_export_consistency.json, reports/pnr/spef_binding_audit.json |
| AC-DRC-LVS | PASS | passed | Installed frozen decks on this exact export: DRC zero, nonempty MOS-device-extracted hierarchical LVS matched; metal-width and missing-poly negative controls detected. FEOL DRC/general density excluded. Evidence: build/gds/checks.json, build/gds/drc.lyrdb |
| AC-POWER-AREA | PASS | passed | Qualified owner receipt for exact final STA netlist: DOT64/GEMM8/CONV3 commit/output comparisons pass; actual full VCD clock/reset/windows checked, tool-report-eligible annotation 59577/59577, separate nominal Liberty/SPEF estimates and unchanged area reported. Zero-delay scope, no silicon/glitch/SDF or energy-improvement claim. Evidence: build/gds/power_area_adoption.json, build/gds/power_waveform_recheck.json |
| AC-GDS | PASS | passed | Streamed from read-only final ODB via byte-identical regenerated DEF; top/master multiplicities/port labels match; all GDS geometry equals accepted upstream export. AC-POWER-AREA remains a blocking dependency. Evidence: build/gds/readability.json, build/gds/port_boundary.json |

All 443 requirement rows and 26 adapter obligations are retained. Only one adapter has complete typed operand proof; workload comparison controls do not replace independent evaluator release.

| Workload | Cycles (including 3 reset cycles) | Eligible window (ns) | Estimated total (mW) | VCD annotation |
|---|---:|---|---:|---|
| DOT64 | 1055 | 300.0–105451.0 | 2.349441638216 | 59577/59577 tool-report-eligible pins |
| GEMM8 | 8215 | 300.0–821451.0 | 2.365025458857 | 59577/59577 tool-report-eligible pins |
| CONV3 | 5323 | 300.0–532251.0 | 2.356985118240 | 59577/59577 tool-report-eligible pins |

The estimates use the exact final netlist, exported SDC/SPEF and nominal TT25°C/1.8V Liberty. Dynamic, leakage, windows, annotation exclusions and source hashes are reported separately in power_area.json. No weighted aggregate is created.

Remaining scope limitations:

- FEOL DRC disabled in frozen deck; general metal density not covered beyond vpp overlap rules.
- Only Sky130HD tt_025C_1v80 nominal 100 ns scenario; no multi-corner STA/foundry signoff.
- Independent ERC, EM/IR, pad/package qualification and foundry authorization unavailable.
- Full RTL-to-synthesis formal equivalence was not supplied; mapped-to-post-route equivalence is retained.
- No fabricated-silicon evidence or tapeout.release/signoff claim. Negative GDS files are deliberate corruptions for checker tests only.
- No new Verilator execution by PnR. No SDF-delay/glitch/silicon-power, energy-improvement or multi-corner signoff claim.
- 100% annotation covers tool-report-eligible pins; sequential internal/hierarchical pins are excluded by the tool.
- The 64 conb_1 static tie cells have characterized leakage and constant Boolean outputs but no internal_power table; no missing table is fabricated.
