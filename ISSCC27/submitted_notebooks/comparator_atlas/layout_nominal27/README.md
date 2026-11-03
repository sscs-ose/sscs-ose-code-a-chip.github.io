# Nominal published 27-device layout experiment

Author: **Wei-Lun Hsu, National Tsing Hua University**.

**Final bounded result: all four comparator jobs are used.** The best legal
layout is attempt 3, `balanced-shielded-r1`: actual DRC/LVS passes and nominal
TT code-zero C/RC decisions pass, but the five-condition 1 ns pilot does not.
Attempt 4, `compact-shielded-r2`, fails actual M2 spacing DRC and has **no
simulation results**. The current generator/protocol records that failed
final experiment; it is not a qualified release. No fifth job, repair push,
protocol relaxation, or PR update was performed.

This is a separate, bounded layout and extraction experiment for the exact
`lvt_balanced_4b` circuit published at
`2ad1c4c2058060abdfdd42c35aa784c018f6fa67`, with `pair_skew=0`.
It is not the unqualified 35-device coarse/fine candidate and does not update
PR195 or its submission branch.

`protocol.json` freezes the source hash, all 15 ordered ports, nominal device
table, pinned tools/models, structural controls, extraction modes, common
stimulus, measurement contract, and monotone numerical acceptance criteria
before remote execution. `devices.json` is independently checked against that
immutable source, not populated from a layout extraction.

The four preflight attempts are exhausted. The final preflight passed 54/54
checks; its evidence and all earlier failures remain in `../layout_preflight`.
This new phase has a separate maximum of four scoped Linux jobs of at most
30 minutes, only on `verify/comparator-atlas-layout-nominal27` in the authorized
user fork. No layout or simulation is qualified merely by this protocol.

The initial layout is deliberately simple: mirrored PCell pairs, a central
tail device, real guard/body contacts, individual M2 pin escapes and M3 buses.
The placer transforms the exact native polygons produced by the pinned
open_pdks generators. It does not substitute drawn transistor placeholders.
The connected short-channel M1 gate landing repair is retained. Actual
geometric area and paired routing differences must be reported; neither
common-centroid matching nor foundry signoff is claimed.

The routed gate-area audit measures the connected polygon union including
the pinned technology's genuine M1 residues: `metal1`, `viali`, and `via1`.
Magic replaces overlapping M1 tiles with contact tiles; omitting `via1`
understates the physical landing. M2/M3 geometry, disconnected islands, and
bounding-box gaps do not count toward the unchanged 0.10 square-micrometre minimum.

Schematic, connectivity-only, capacitance-only and actual distributed-RC
netlists use identical external 5 fF loads and published measurements.
Actual simulator device dimensions must confirm geometry scaling exactly
once. All failures and finest-step contrary evidence remain visible. An
unambiguous RC pilot failure ends expansion with a root-cause report, not
geometry or stimulus retuning to make a result green.

## Authorized physical routing revision

Attempts 1 and 2 used identical physical polygons. Attempt 1's gate-area
reporter missed the real M1 residue of `via1`; attempt 2 passed all 14
structural checks with that reader corrected, but its code-zero TT C-only
and RC simulations failed for positive inputs. The original layout,
protocol, raw traces, and contrary outcomes remain retained. In that baseline,
qn has 1.28575 fF more listed coupling to VSS, VDD and the ideal input sources
than qp, while the device dimensions, junction geometry, body connections,
and actual simulator scaling agree.

The subsequent explicit decision authorizes only the two remaining
comparator jobs for separately frozen physical revisions, not electrical
retuning or relaxed qualification. `balanced-shielded-r1` preserves all
27 generated devices and their placements. Disjoint mirrored buses share
the same M3 height. The two output buses have equal full spans, real attached
M2 balancing stubs, and three M3 ground shields joined to VSS by two M4
spines and eight genuine `via3` contacts. These are layout polygons, not
inserted ideal capacitors. The stubs match metal extent, not series
resistance; the two output tracks and common tail escape retain explicitly
reported residual asymmetry. No post-layout trim calibration is enabled.

`analyze.py` checks full native LVS/C MOS-card equality including junction
parameters, all three exported device/port/bulk contracts, retained FLOATING
annotations, actual C matrices, and real resistor paths. Its path sums are
not parallel-network equivalent resistances. It measures saved-MAG metal
union areas with genuine contact residues and the actual GDS bounding box.
Fresh four-mode simulation reports the corresponding core-energy cost.
The original TT, pilot, 45-PVT, and monotone numerical gates remain identical;
a clear failure still ends expansion **within each frozen revision**.

Attempt 3 actually passed all 14 structural controls and the TT four-mode
code-zero gate. Its RC -3/+3 mV delays are 0.842970/0.842783 ns and energies
520.872/520.806 fJ, compared with the matched nominal schematic's approximately
0.280439 ns and 244.052 fJ. Output quiet-rail capacitance imbalance fell from
1.28575 to 0.01195 fF, and the actual bounding-box area fell from 4281.984 to
3297.024 square micrometres. This is a real polarity/matching improvement,
not full PVT qualification: the five-condition pilot has 14 unresolved SS
rows out of 80 at 1 ns, so the 45-PVT sweep did not run. `balanced-r1-receipt.json`
retains all primary results, exact artifact hashes, and the distinction between
audited TT/SS results and the declared 10 ps FF pilot.

The final authorized revision, `compact-shielded-r2`, retains that physical
matching arrangement but lowers the same bus/shield pattern by 8.4 micrometres
over the verified M1-only PCells. M2 lanes go either up or down to their actual
M3 connections, rather than requiring all buses above the cells. M2 strips
are 0.20 micrometres wide (deck minimum 0.14), and M3 strips are 0.34
micrometres wide (minimum 0.30); the genuine via generators still supply their
full enclosure pads. Shield spans, output matching, device dimensions,
placement, code zero, and the entire non-layout policy remain fixed.
Shorter/narrower routing is a geometric prediction of lower parasitic loading;
only actual extraction and matched simulation can establish its benefit.
This is comparator job 4 of 4; another failure is retained, not followed by
an unauthorized fifth run.

## Reproduction and evidence

`run.sh` uses a fresh private work directory and reuses only the frozen preflight
toolchain builder, not the exhausted preflight test job. It runs `layout.py`
and the native parasitic analysis before fetching the three exact model flavors
with `setup_models.py`. Simulation
dependencies live in a job-private virtual environment. No system installation
is performed on the shared Windows host.

`simulate.py` preserves each native netlist, uses one `scale=1u`, and queries all
27 actual inner ngspice MOS W/L values in metres. It calls the unchanged
published measurement functions. Four-mode TT and worst-RC numerical audits
retain the finest pending evidence; any failed sweep condition also receives
the bounded refinement sequence before it can be classified. The five-condition
pilot precedes conditional expansion to 45 PVT conditions. The process records
an explicit failure rather than hiding a measurement error or running beyond
the bounded job budget.

`ci.yml` is an inert project-local template. Only its copy on the separate
experimental branch belongs under `.github/workflows`; inherited-workflow
exclusions are also limited to that branch. The job has a 30-minute ceiling,
a 24-minute execution timeout, and an always-upload artifact step.
`execution.json` and `manifest.sha256` preserve the last stage, exit status,
exact commit/run, and every emitted evidence file. Native MAG/GDS/EXT/resistance
extraction, independent references, raw logs, actual geometry audits, simulation
decks, waveforms, all measurements, and contrary refinements remain inspectable.

The offline controls run with:

```sh
python3 -m unittest discover -s layout_nominal27 -p test_nominal27.py -v
```

Those controls do not qualify the physical layout or execute Magic, Netgen,
or ngspice.

## Final comparison and remaining blockers

All three rows below use the same independently verified 27 devices and
15 ports. Positive LVS and all four connection/bulk/width/flavor negatives
pass in every row. A successful LVS result does not waive a DRC failure.
Metal areas are actual saved-MAG conductor unions including contact residues,
not bounding boxes. C counts include retained zero-valued elements; passive
sums are listed values, not effective impedances.

| Actual layout | DRC / LVS | GDS bbox area (um2) | M1 / M2 / M3 / M4 area (um2) | C-only R / C | RC R / C | Functional result |
|---|---|---:|---|---|---|---|
| Initial, job 2 | 0 errors / pass | 4281.984 | 72.734 / 520.412 / 287.520 / 0 | 0 / 133 | 672 / 319 | TT C/RC positive-input failures; SS pilot not run |
| Balanced, job 3 | 0 errors / pass | 3297.024 | 72.734 / 433.134 / 358.560 / 6.080 | 0 / 135 | 675 / 321 | TT all four modes pass; SS pilot incomplete at 1 ns |
| Compact, job 4, **illegal** | **48 met2.2 regions** / pass | 2207.088 | 72.734 / 80.028 / 304.776 / 6.080 | 0 / 133 | 675 / 319 | **Not run: physical gate failed** |

The listed C-only sums are 152.95991, 154.61852, and 110.98653 fF respectively;
the RC sums are 266.51579, 256.75391, and 181.35685 fF. The smaller parasitics
of the **DRC-failing** compact geometry do not establish a usable performance
improvement. Every FLOATING annotation and actual passive remains retained.

### Matched measurements of the best legal layout

The following pairs are **-3 / +3 mV**, at code zero, nominal geometry and
5 fF per output. All entries below use the finest audited 5 ps trace.
An unresolved 1 ns result is not replaced with a later successful decision.
Full -10/-3/+3/+10 mV measurements, both reporting deadlines, the initial
failed layout, reset checks, and FF pilot results are in the per-attempt
`matched-metrics.csv` and original JSON evidence.

| Condition | Mode | Decision latency at 1 ns (ns), -3 / +3 | Core energy (fJ), -3 / +3 |
|---|---|---|---|
| TT 1.8 V, 27 C | Schematic | 0.280439 / 0.280439 | 244.052 / 244.052 |
| TT 1.8 V, 27 C | LVS | 0.279745 / 0.279745 | 244.059 / 244.059 |
| TT 1.8 V, 27 C | C-only | 0.620561 / 0.625556 | 419.083 / 419.418 |
| TT 1.8 V, 27 C | RC | 0.842970 / 0.842783 | 520.872 / 520.806 |
| SS 1.62 V, -40 C | Schematic | 0.666005 / 0.666005 | 166.879 / 166.879 |
| SS 1.62 V, -40 C | LVS | 0.664478 / 0.665771 | 166.885 / 166.879 |
| SS 1.62 V, -40 C | C-only | unresolved / unresolved | 293.031 / 293.144 |
| SS 1.62 V, -40 C | RC | unresolved / unresolved | 361.431 / 361.452 |
| SS 1.62 V, 125 C | Schematic | 0.551253 / 0.551253 | 208.748 / 208.748 |
| SS 1.62 V, 125 C | LVS | 0.547412 / 0.549067 | 208.757 / 208.752 |
| SS 1.62 V, 125 C | C-only | unresolved / unresolved | 346.630 / 346.821 |
| SS 1.62 V, 125 C | RC | unresolved / unresolved | 425.045 / 425.078 |

Thus TT RC costs approximately **113.4% more core energy** than the matched
schematic at the same +/-3 mV points, not an unmatched published stress case.
At the separate 2 ns reporting deadline, cold-SS C-only resolves at
1.622811/1.628452 ns, hot-SS C-only at 1.209979/1.215004 ns, and hot-SS RC
at 1.588771/1.588772 ns. Cold-SS RC +/-3 mV remains unresolved even at 2 ns.
None of these later results passes the fixed 1 ns requirement.

Job 2 retains 16 qualified TT 10-to-5 ps numerical histories despite its
functional failure. Job 3 retains 48 qualified TT/SS 10-to-5 ps histories;
none was sensitive or required finer halving. Its FF pilot rows are the
declared 10 ps observations, not separately numerically qualified results.
All 32 job-2 and 128 job-3 simulator executions, device-unit audits and
recorded resets passed, with no collected simulator warnings. Job 4
numerics are **not run**, not zero-error numerical evidence.

### Actual final pad-spacing failure

The compact revision leaves 0.20 um M2 necks between the native 0.26/0.28 um
via pads on `Xrxp.B`, `Xrxn.B`, `Xrqp.B`, and `Xrqn.B`, all correctly connected
to VDD. Their lanes are at x = -26, -21.2, 21.2, and 26 um. At each transition,
the facing pad edges are y = -1.410 and -1.335 um: the **0.075 um notch gap**
violates the actual **0.14 um `met2.2` spacing** rule. Narrowing the connecting
strip did not remove those side notches. The 48 reported regions are multiple
DRC regions around four physical transitions, not 48 distinct electrical
shorts. This explains why LVS can pass while the layout remains illegal.
No waiver, geometry repair or extra execution followed that failure.

## Exact ledger and native artifacts

| Comparator attempt | Actual run | Experimental commit | Retained result |
|---|---|---|---|
| 1 | [35823631990](https://github.com/WLHsu0827/sscs-ose-code-a-chip.github.io/actions/runs/35823631990) | `0471f6c9314a6df71a296aa93e647edce193117b` | 13 pass / 1 gate-area reporter failure; simulation gated |
| 2 | [35824072501](https://github.com/WLHsu0827/sscs-ose-code-a-chip.github.io/actions/runs/35824072501) | `426c88726b0e869e0e6dd18c3ee17513024c3b40` | 14 physical passes; TT C/RC failure |
| 3 | [35828243323](https://github.com/WLHsu0827/sscs-ose-code-a-chip.github.io/actions/runs/35828243323) | `05cd18f3aa3348b2fc4eb8982f2894c013ef9790` | 14 physical passes; TT success; 14/80 pilot rows unresolved |
| 4 | [35829241108](https://github.com/WLHsu0827/sscs-ose-code-a-chip.github.io/actions/runs/35829241108) | `561477fe230dff5642fa9c292051c98e04c57856` | 13 pass / 1 actual DRC failure; simulation gated |

`verification-receipt.json` contains full archive, log, native-file and
protocol SHA-256 values, all run/commit identities, matched cost deltas and
the remaining acceptance blockers. `published-source-sha256.json` records a
fresh byte-for-byte comparison of every original published file with
`2ad1c4c`: all 83 original tracked files, including the unchanged checksum
manifest, match. All 82 assertions in that original `entry_checksums.json`
also still pass. The original source and preflight receipts are unchanged.

`evidence/attempt1` through `evidence/attempt4` contain exact native MAG/GDS,
LVS/C/RC netlists, EXT/resistance intermediates, independent references,
DRC/LVS logs, routing/placement/protocol tables and available measured
results. Each `snapshot.sha256` describes that exact local subset of the
authenticated CI archive. GDS is explicitly binary in Git. Use
**`evidence/attempt3` for the best legal layout**, not the illegal attempt 4.
The attempt-4 `post-job-analysis.json` is explicitly a read-only analysis
of retained outputs after the failed physical gate, not an executed
simulation or a retroactive qualification.

All full archives, raw waveforms/decks, actual simulator geometry tables,
complete manifests and raw Actions logs also remain in this session's
persistent `nominal27-run1` through `nominal27-run4` artifacts. The final
native evidence and handoff are committed **locally only**; no receipt-only
push consumes an unauthorized fifth job. Both main branches, PR195 and the
exhausted preflight branch remain at their original protected commits.
