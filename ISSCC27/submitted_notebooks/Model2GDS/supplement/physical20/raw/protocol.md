# DAC round 2: full physical qualification and matched family

Prospective protocol, 2026-10-08. The research lead authorizes full downstream
qualification of the round-1 repaired 4x4 design, common-flow integration,
fresh 2x2/4x4/8x8 experiments, and the original analysis if the complete family
qualifies. This supersedes the round-1 development-only stop for new DAC work.
Keep all historical freezes, runs, failed attempts, RTL/model, ISSCC submission
and ZIPs unchanged. Work on `codex/dac27-uddac-research`; local commits only.

## Development, freeze and stop conditions

1. `DEV_001` continues the repaired round-1 4x4 database in a new directory.
   Run the complete downstream flow, including fresh parasitic extraction,
   final STA, full enabled DRC, LVS, all-corner hold, connectivity and final
   antenna checks. Recheck mapped compute retention and authoritative R2R STA
   with the new final artifacts. Old SPEF, old LVS or an exit-zero routing
   command cannot qualify the modified design. This continuation is development
   evidence, never a member of the formal comparative family.
2. If an actual failure warrants repair, at most one additional common
   development recipe revision is allowed. Record the cause and mechanism
   before launching it. Ordinary invocation/parser bugs may be corrected in
   new attempt directories without being misclassified as physical findings;
   they remain subject to the resource limits below.
3. Only after full 4x4 development qualification, freeze the common flow,
   recipe, source hashes, pinned tools/PDK, exact invocation and analysis
   protocol in a versioned record. Then run all three configurations anew,
   sequentially in increasing size. No old 2x2 or development 4x4 result may
   replace a member of this family.
4. If a formal member fails, stop that family. At most one justified common
   signoff correction is allowed: reject the entire partial family, freeze a
   new common recipe, and rerun all three from scratch. No configuration may
   receive a private rescue or performance-selected setting. Failure after
   this bound stops physical salvage in this round.

The initial common candidate is the preserved `flow/final_candidate_02.json`
recipe plus explicit `DRT_THREADS=2` and the round-1 generic post-detailed-route
antenna mechanism. The added stage checks all nets, runs only when needed,
and permits at most two repair/legalization/reroute passes. Use the same
diode master, margin 15 and pinned-tool routing defaults for every size; no
net-name exceptions, hand placement, parameter sweeps or relaxed checkers.
Every pass has preserved input/output identities and native reports. A zero
violation result still proceeds through all downstream qualification steps.

Run one EDA job at a time, with two worker threads where the tool exposes that
control. Wall-clock caps are two hours per downstream development continuation
and four hours per fresh full physical configuration. Stop before launching a
job if workspace disk headroom is below 20 GiB; stop and preserve evidence on
out-of-memory, timeout or storage failure. These are resource/tool limitations,
not architecture infeasibility. There is no automatic hardware-scale or tool
upgrade escape from the bound. Changes to limits require a recorded reason
before further runs and must not depend on desired ranking outcomes.

### Recorded continuation invocation correction

`DEV_001` stopped in Magic.StreamOut because the new continuation adapter had
dropped `design__die__bbox`, which the pinned Magic step needs as `DIE_AREA`.
This is an entry-point error, not a design DRC/LVS failure or a backend recipe
trial. `DEV_002` starts the common post-DRT step on the already repaired database
and emits die/core bounding boxes directly from its current OpenDB geometry
using the pinned floorplan method. The step checks antenna before deciding
whether repair is needed, then all normal downstream checks run again in a new
directory. No old signoff metrics, old extracted views or hand-entered geometry
are used. The resource bounds and common physical controls remain unchanged.

## Qualification and provenance

### One common correction after FINAL_001 rejection

`FINAL_001` stopped at 4x4: final extraction/LVS found an open at an existing
buffer output after the extra post-route `common/dpl.tcl` changed its orientation.
Its routing DRC and logical disconnected-pin counts were zero, demonstrating
why those checks cannot replace extracted LVS. The 2x2 member passed, but the
family is rejected and 8x8 remains NOT_RUN; no comparative result is retained.

Before the next run, `flow/dac27_candidate_02.json` removes only that redundant
post-repair detailed-placement/mirroring call. At pinned OpenROAD commit
`edf00dff99f6c40d67a30c0e22a8191c5d2ed9d6`, `RepairAntennas.cpp` protects existing
placements and legalizes inserted diodes internally, while `GlobalRouter.cpp`
tracks changed nets within its incremental routing guard. The pinned
`test/flow.tcl` post-DRT loop calls repair then detailed routing directly.
Keep explicit placement checks, all downstream checks, two-pass bound, margin,
threads, seed, RTL and remaining physical parameters unchanged for every size.

`DEV_003` imports only design views and the two bound upstream counters from
the original DetailedRouting state of failed FINAL_001, before its repair.
No old extraction, signoff or timing evidence is imported. It must rerun repair
and the complete downstream qualification. If successful, freeze `FINAL_002`
and rerun 2x2, 4x4 and 8x8 from RTL in order. This consumes the one allowed common
formal correction; another physical failure stops salvage this round. Old
freeze records remain reproducible with their recorded Git source versions.

Keep the original numerical/cycle contract, six frozen workloads, signed
INT8/INT32 wrap arithmetic, output-stationary dataflow, 2/4/8 sizes and
compute-only measurement boundary. The unchanged functional regression and
sources must remain qualified before physical evaluation. Keep the pinned
OpenLane/OpenROAD/Yosys image, SKY130A revision and standard-cell library.

Qualification requires completed routing; zero blocking final antenna,
routing DRC, enabled full DRC and disconnected-pin violations; passing LVS;
acceptable hold in every analyzed corner; retained mapped arithmetic and
accumulator state; valid final GDS; fresh extraction and finite authoritative
R2R timing; and matching command/config/source/artifact provenance. Do not
disable checks or weaken existing acceptance predicates. Preserve diagnostic
slew/capacitance/fanout reports with their existing interpretation. A command
failure remains failure even if another output contains a success message.

Use the frozen `docs/PHASE2_TIMING_METHODOLOGY.md` and
`scripts/phase2_r2r_sta.tcl`: final routed netlist, maximum SPEF, propagated SDC
and saved final STA environment from the same run, at `max_ss_100C_1v60`.
Derive only by script `P_sta_ns = 20 - S_r2r_ns > 0` and
`F_sta_MHz = 1000 / P_sta_ns`. Negative setup slack at the fixed 20 ns target
has the existing methodological interpretation; all-corner hold still must
pass. This is a fixed-layout STA estimate, not measured silicon Fmax.

Only a complete qualified formal family enables cross-configuration research
analysis. Individual qualified development values can be reported explicitly
as engineering results. Rejected or missing members expose status/reasons,
not timing/area values to the research analysis. An unlaunched member is
`NOT_RUN`, never a demonstrated physical failure.

## Analysis fixed before formal measurement

Reuse the original six workload observations and existing analysis helpers.
For each configuration/workload, `T_impl_ns = C_rtl * P_sta_ns`. Compare all
three configurations without area filtering for the primary timing result:

- Retain every minimum tied under `math.isclose(a,b,rel_tol=1e-9,abs_tol=0)`.
  Top-1 agreement counts identical unique winners out of six; any multiwinner
  set is tied/indeterminate, with both winner sets shown.
- Classify all 18 pairs as preserved, reversed or tied/indeterminate; a tie
  in either layer is indeterminate, never a strict reversal.
- Report natural-log cycle and latency margins, their differences and the
  existing dimensionless absolute margin-change tolerance `1e-9`.

The separate area analysis uses final `design__core__area` in square
micrometres as the primary budget metric. This measures the compute-fabric
core under the common utilization/floorplanning policy, not a complete chip.
Report `design__instance__area` separately as cell area; do not substitute it
for core area or mix the two in a feasible set.

For every nonnegative core-area budget B, configuration i is feasible iff its
raw-parser-derived core area satisfies `A_core[i] <= B` (inclusive, without
rounding or an area epsilon). Enumerate the complete piecewise-constant budget
domain: `[0, smallest area)`, every interval between sorted distinct observed
core areas, and `[largest area, infinity)`. Equal areas enter together. The
interval lower bound is the canonical reported budget, so every boundary and
feasible set appears; no budget is chosen for a favorable finding.

For each interval and each of the six workloads, report the feasible set and
both cycle-minimum and STA-latency-minimum winner sets, using the same timing
tie rule within that set. An empty set is `NO_FEASIBLE_CONFIGURATION`, not a
slow configuration or a disagreement. Preserve the unconstrained winner sets
alongside constrained winners to distinguish area exclusion from timing
reordering. An area exclusion is never counted as one of the primary 18
timing reversals; breaking a cycle tie is never a strict reversal either.

All values and figures must regenerate from accepted raw evidence through
parsers. Preserve null results. The conclusions apply only to these six
workloads, three compute fabrics and one recipe; make no power/energy,
process-variation, full-system or general simulator-reliability claim.

If full qualification is blocked at the bound, publish the actual gate status,
failure evidence, reproducible commands and remaining cause. Leave comparative
analysis unavailable. This round does not create an abstract, video, large GUI
or FPGA implementation, and does not assert unconfirmed DAC 2027 rules.
