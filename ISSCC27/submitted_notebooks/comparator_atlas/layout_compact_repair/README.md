# Separate compact-layout repair

Author: **Wei-Lun Hsu, National Tsing Hua University**.

**Final result: the physical repair passes all 17 checks, and TT performance
improves, but the original 1 ns five-condition pilot still fails.**
Repair attempt 1 has 68/80 correct rows, 12 unresolved and none wrong.
The 45-PVT sweep was **not run**. The second repair job is **unused**:
the remaining failure is measured performance, not an integrity/DRC defect.
No additional physical work, remote execution, push or PR update followed.

This is a new, explicitly bounded engineering-qualification phase for the
Code-a-Chip entry, not a new circuit, routing algorithm, publication claim,
or retroactive change to an earlier result. The completed four-job preflight
and four-job nominal27 ledgers remain frozen at local commit
`2268e09bccc023177ac488a785244bc19c540c10`.

The target is the actual `compact-shielded-r2` geometry from nominal27 job 4,
experimental commit `561477fe230dff5642fa9c292051c98e04c57856` and
[run 35829241108](https://github.com/WLHsu0827/sscs-ose-code-a-chip.github.io/actions/runs/35829241108).
That layout passed full device/port/LVS and passive-connectivity checks but
failed DRC with 48 `met2.2` regions, so its simulation was **not run**.
The best prior legal layout remains balanced-r1: TT code-zero C/RC decisions
pass, but 14/80 five-condition pilot rows miss the fixed 1 ns requirement.

## Exact repair, not a waiver

The four PFET VDD body transitions `Xrxp.B`, `Xrxn.B`, `Xrqp.B`, and `Xrqn.B`
have 0.26/0.28 um native M2 via pads joined by 0.20 um necks. Their side
notches have a 0.075 um facing-edge gap, below the 0.14 um spacing rule.
The repair paints four continuous **0.36 um-wide M2 rectangles**, each
covering y = -1.800 through -0.955 um at x = -21.2, 21.2, -26, and 26 um.
They fully cover both pads, with at least 0.04 um lateral overhang beyond
the widest pad and 0.01 um vertical coverage beyond the native pad extent.

`protocol.json` fixes the four rectangles on the native 0.005 um grid before
execution. Their exact predicted net material addition is **0.3568 um2**
total; M2 union area becomes 80.3847 um2 and the bounding-box area remains
2207.088 um2. These are geometric calculations, **not assumed parasitic,
speed or energy gains**.

`repair.py` composes the frozen nominal27 PCell, routing, Magic, Netgen and
extraction helpers without editing them or changing their globals. It
regenerates the same real PCells and compact routing, verifies their
placement/pins, and appends only the four M2 paint operations. After actual
Magic execution it checks that saved M2 material equals the old material
union plus exactly those rectangles. All other native layer unions,
contacts, labels and the GDS bounding box must remain unchanged.
The failed MAG also contains 16 `error_p` DRC-feedback rectangles. Their
before/after counts are reported separately from physical mask material;
no erase command removes them, and only full actual DRC may establish that
the violations cleared.
Full named-style DRC, the deliberate spacing negative, independent-reference
LVS and wrong-net/bulk/width/SVT-for-LVT negatives still run.
All 27 devices, full model flavors, W/L/m, body ties and 15 ordered ports
must match. No error polygon, device, body tie, resistor or capacitor is
deleted; no ideal balancing component is inserted.

## Frozen measurements and separate budget

The original non-layout fingerprint remains
`386bc16f5c55c467d0c7d72ec93d553907f8a2f290aa054b2cd50e0cfcf05454`.
Its historical four-job budget is preserved as data, **not reused as new
authorization**. This repair has at most **two new jobs of 30 minutes**,
only on `verify/comparator-atlas-layout-repair-compact` in the authorized
fork. Failed jobs and reruns count. A second job is allowed only for a
concrete integrity/DRC/execution defect, not arbitrary performance retuning.
PR195, both main branches and both older experimental branches are untouched.

The fresh schematic/LVS/C/RC comparison uses the exact published 27-device
`lvt_balanced_4b`, `pair_skew=0`, code zero, 5 fF external loads, 10 ns clock,
50 ps edges, 0.5 VDD common mode, 80%/20% rails and 1 ns primary deadline.
`compare.py` reuses the original simulator, point/deck generators, published
measurements and monotone pending-trace numerical contract. Every scored
condition is audited from 10 to 5 ps, with the same sensitive finer halvings,
1% energy tolerance, 20 ps latency tolerance and identical decisions.
Added numerical coverage does not alter stimuli or acceptance thresholds.
No prior finer contrary evidence can be replaced by a coarse restart.

All 17 structural checks must pass before models or simulation run.
TT +/-3 and +/-10 mV precedes the unchanged five-condition pilot. Only an
all-mode/all-point numerical and functional pilot pass allows the original
45-PVT product within the same job budget. Failures and unfinished stages
are recorded explicitly, not converted to pass or zero-valued metrics.
The native parasitic analysis retains FLOATING annotations, actual R/C
attachment, ground/dynamic pair couplings, true metal areas and path sums;
path sums are not equivalent parallel-network resistances.

## Reproduction and evidence

On the authorized disposable Linux runner, the inert `ci.yml` template is
copied only to the new experimental branch's root workflow directory.
It uses public shallow sparse checkout, exact tool/model pins, the lean
preflight builder and a private simulation virtual environment. There is no
shared-Windows system installation or large PDK image.
Run `bash layout_compact_repair/run.sh` from the entry directory in that
environment; fresh output/work directories are required.

Offline controls:

```sh
python3 -m unittest discover -s layout_nominal27 -p test_nominal27.py -v
python3 -m unittest discover -s layout_compact_repair -p test_repair.py -v
```

These checks do not claim actual DRC or circuit performance.
`inherited-sha256.json` pins every reused module and relevant native source.
Linux requires exact committed LF bytes. The seven preserved pre-existing
Windows CRLF preflight copies have separately recorded exact hashes for
offline checks only; no old file is rewritten or silently normalized.
The immutable published source remains byte-exact, including CRLF.

Each run retains its separate repair protocol and original baseline protocol,
source/hash audit, exact request/delta, native MAG/GDS/LVS/C/RC/EXT/resistance
files, complete structural controls, actual ngspice geometry tables, raw
waveforms/decks/logs, all matched measurements and numerical histories.
`execution.json` records the new phase and exact commit/run URL, while
`manifest.sha256` covers the full payload even on failure.
There is no density/antenna, foundry/silicon, mismatch-stress, or novelty
qualification implied by this repair.

## Actual engineering result

The existing [repair run 35945064081](https://github.com/WLHsu0827/sscs-ose-code-a-chip.github.io/actions/runs/35945064081)
completed at experimental commit
`68832ec0ae7c526afcb4cded405a0bfd753a65c3` in 2 minutes 21 seconds.
It was retrieved and inspected, **not rerun**. All 17 structural controls
pass: real `sky130A` 1.0.608 `drc(full)` reports zero regions, the deliberate
spacing negative reports two, positive Netgen LVS and all four LVS negatives
behave correctly, and all device/port/junction/C/RC attachment checks pass.
Native LVS bytes are identical to the prior nominal27 LVS export.

Actual saved-MAG geometry confirms exactly **+0.3568 um2 of M2** at the four
declared transitions, with all other physical layers, contacts and labels
unchanged. The bounding box remains **129.6 x 17.03 um = 2207.088 um2**.
The prior compact-r2 remains recorded as a DRC failure with **no simulation**;
its status is not rewritten by this successful later repair.

Only legal layouts are compared here. All have 27 devices and 15 ordered
ports, actual DRC zero, and positive LVS plus four negative controls.
Metal areas are measured material unions, including real via residues.
Capacitance sums are listed native values, not effective node capacitance.

| Legal layout | Bbox area (um2) | M1 / M2 / M3 / M4 area (um2) | C-only R/C; sum (fF) | RC R/C; sum C (fF) | Original 1 ns result |
|---|---:|---|---|---|---|
| Initial comb, nominal27 job 2 | 4281.984 | 72.73365 / 520.4124 / 287.520 / 0 | 0/133; 152.95991 | 672/319; 266.51579 | TT C/RC positive-input failure; pilot not run |
| Balanced-r1, nominal27 job 3 | 3297.024 | 72.73365 / 433.1344 / 358.560 / 6.080 | 0/135; 154.61852 | 675/321; 256.75391 | TT passes; pilot 66/80 correct, 14 unresolved |
| **Repaired compact, repair job 1** | **2207.088** | **72.73365 / 80.3847 / 304.776 / 6.080** | **0/133; 111.04544** | **675/319; 181.43686** | **TT passes; pilot 68/80 correct, 12 unresolved** |

Compared with the same legal balanced-r1 TT -3/+3 mV points, repaired RC
latency falls from **0.842970/0.842783 to 0.656880/0.633340 ns**
(22.08%/24.85%), and core energy falls from **520.872/520.806 to
426.103/424.613 fJ** (18.19%/18.47%). Area falls 33.06% and listed RC
capacitance falls 29.33%. This benefit belongs to the now-legal compact
geometry versus balanced-r1, **not a claim that the four pad bridges alone
caused the performance gain**. There is no valid pre-repair compact
simulation with which to isolate that bridge-only performance effect.
The repaired RC still costs 73.98%-74.60% more energy than the matched
244.052 fJ nominal schematic at +/-3 mV.

The repaired RC network contains 675 positive resistors, from 0.138735 to
6182.32 ohms, with a listed sum of 392040.346786 ohms; this is **not an
equivalent resistance**. C-only has 125 positive capacitors out of 133;
RC has 311 positive capacitors out of 319. All remaining zero-valued elements,
11 C-only and 197 RC FLOATING annotations, and all distributed endpoints
remain retained. No parasitic was deleted.

### Pair environment, including residual imbalance

Values below are sums of emitted C-only elements, in fF. Quiet sources here
mean VSS, VDD, vinp and vinn; the full report also counts all constant
code-zero control sources separately. Dynamic coupling is reported, not
treated as necessarily erroneous merely because it is large.

| Native quantity | First side | Mirrored side |
|---|---:|---:|
| xp / xn incident capacitance | 9.73000 | 9.73011 |
| xp / xn to VSS | 3.80040 | 3.80117 |
| xp / xn to tail | 3.13900 | 3.13866 |
| xp / xn to clock | 0.28831 | 0.28793 |
| qp / qn incident capacitance | 9.59847 | 9.56724 |
| qp / qn to quiet sources | 7.92441 | 7.93264 |
| qp / qn to clock | 0.22345 | 0.21005 |
| qp-to-xp / qn-to-xn | 0.15077 | 0.14695 |
| qp-to-xn / qn-to-xp | 0.21612 | 0.21224 |

C-only output quiet-source imbalance is **qn - qp = 0.00823 fF**; contracted
RC output quiet-source imbalance is **-0.04902 fF**. These are small but not
zero. Main input native gate shortest-path resistance is 716.692265 ohms
on each side; drain paths are 42.456755 ohms each. Output reset drain paths
remain 241.406589/242.406589 ohms, illustrating residual series asymmetry.
These paths include genuine contacts/poly/diffusion/interconnect and are
not parallel-network equivalent impedances.

## Matched five-condition measurements

Each list below is ordered **-10 / -3 / +3 / +10 mV**. All 80 rows use
**code zero, pair_skew=0, VCM=0.5 VDD, 5 fF per output, a 10 ns clock with
50 ps edges, 80%/20% rails, and the unchanged 1 ns primary deadline**.
Every displayed result is from its finest qualified **5 ps** trace.
`U` means **unresolved at 1 ns**, not zero latency or a later pass.
Energy is core rail energy over the unchanged 20-30 ns cycle.

| Condition | Mode | Latency at 1 ns (ns), ordered signed inputs | Core energy (fJ), same order |
|---|---|---|---|
| TT 1.8 V, 27 C | Schematic | 0.225548 / 0.280439 / 0.280439 / 0.225548 | 240.683 / 244.052 / 244.052 / 240.683 |
| TT 1.8 V, 27 C | LVS | 0.224885 / 0.279745 / 0.279745 / 0.224885 | 240.688 / 244.059 / 244.059 / 240.688 |
| TT 1.8 V, 27 C | C-only | 0.407713 / 0.503220 / 0.496035 / 0.404151 | 349.433 / 356.211 / 355.642 / 349.231 |
| TT 1.8 V, 27 C | RC | 0.533860 / 0.656880 / 0.633340 / 0.527902 | 417.753 / 426.103 / 424.613 / 417.103 |
| SS 1.62 V, -40 C | Schematic | 0.535088 / 0.666005 / 0.666005 / 0.535088 | 164.086 / 166.879 / 166.879 / 164.086 |
| SS 1.62 V, -40 C | LVS | 0.538890 / 0.664478 / 0.665771 / 0.538873 | 164.093 / 166.885 / 166.879 / 164.093 |
| SS 1.62 V, -40 C | C-only | U / U / U / U | 241.527 / 247.556 / 247.354 / 241.439 |
| SS 1.62 V, -40 C | RC | U / U / U / U | 288.678 / 295.568 / 295.040 / 288.399 |
| SS 1.62 V, 125 C | Schematic | 0.454340 / 0.551253 / 0.551253 / 0.454340 | 205.574 / 208.748 / 208.748 / 205.574 |
| SS 1.62 V, 125 C | LVS | 0.453256 / 0.547412 / 0.549067 / 0.454008 | 205.574 / 208.757 / 208.752 / 205.573 |
| SS 1.62 V, 125 C | C-only | 0.804278 / 0.982854 / 0.971247 / 0.803349 | 290.937 / 297.172 / 296.854 / 290.816 |
| SS 1.62 V, 125 C | RC | U / U / U / U | 344.222 / 351.664 / 350.836 / 343.835 |
| FF 1.95 V, -40 C | Schematic | 0.138727 / 0.165213 / 0.165213 / 0.138727 | 276.525 / 280.861 / 280.861 / 276.525 |
| FF 1.95 V, -40 C | LVS | 0.138394 / 0.165258 / 0.165732 / 0.140176 | 276.528 / 280.868 / 280.856 / 276.535 |
| FF 1.95 V, -40 C | C-only | 0.254630 / 0.307751 / 0.298548 / 0.255201 | 409.134 / 418.254 / 416.919 / 408.757 |
| FF 1.95 V, -40 C | RC | 0.346440 / 0.417553 / 0.392850 / 0.341696 | 493.061 / 504.154 / 500.615 / 491.893 |
| FF 1.95 V, 125 C | Schematic | 0.172926 / 0.203321 / 0.203321 / 0.172926 | 333.812 / 341.332 / 341.332 / 333.812 |
| FF 1.95 V, 125 C | LVS | 0.172516 / 0.203050 / 0.202063 / 0.174541 | 333.869 / 341.353 / 341.421 / 333.885 |
| FF 1.95 V, 125 C | C-only | 0.316206 / 0.374396 / 0.365263 / 0.314921 | 479.938 / 495.737 / 493.290 / 479.237 |
| FF 1.95 V, 125 C | RC | 0.415018 / 0.489979 / 0.463213 / 0.404677 | 570.613 / 590.372 / 583.347 / 568.476 |

The exact unrounded values, input settings, source run IDs, 1 ns rail values
and original numerical evidence are in `evidence/attempt1/matched-metrics.csv`,
`matched-primary-results.json`, `simulation-index.json` and
`numerical-audits.json`. All 160 actual simulator executions, 4320 inner-MOS
W/L audits and recorded resets pass, with no collected simulator warnings.
All 80 numerical histories agree from 10 to 5 ps under the original
1% energy / 20 ps latency / identical decision-and-outcome limits.
None was sensitive or required additional halving. Numerical agreement
does not turn the 12 unresolved 1 ns results into functional passes.

## Retained 2 ns operating-envelope characterization

This section is **post-hoc characterization of already retained measurements**,
not a deadline change or a new qualification. The original pilot remains
**failed at 1 ns**, and **45-PVT was not run**. No SPICE process, changed
netlist, stimulus or additional job was used for this table.
The 2 ns deadline was already among the measured reporting windows.

Each mode has **20 distinct sampled points: five conditions x four signed
inputs**. Thus the RC statement is **20/20 sampled RC points correct at
2 ns**, not 80 independent RC tests, a continuous input range, yield, or
full-PVT coverage. All modes combined account for 80 rows.

| Mode | Correct / unresolved at original 1 ns | Correct at retained 2 ns | Actual 10-to-5 ps comparisons at 2 ns | Max energy difference (%) | Max latency difference (ps) |
|---|---|---|---|---:|---:|
| Schematic | 20 / 0 | 20/20 | 20/20 pass | 0.022136 | 8.806458 |
| LVS | 20 / 0 | 20/20 | 20/20 pass | 0.064777 | 8.154627 |
| C-only | 16 / 4 | 20/20 | 20/20 pass | 0.013901 | 8.591601 |
| RC | 12 / 8 | **20/20** | **20/20 pass** | **0.017914** | **7.848417** |

For the late SS points, the actual 5 ps decision times observed within
2 ns are listed below, again ordered **-10 / -3 / +3 / +10 mV**.
They use the published last-invalid-sample measurement, not a fitted or
hand-edited crossing time.

| Condition | Mode | Retained decision latency (ns) |
|---|---|---|
| SS 1.62 V, -40 C | C-only | 1.007811 / 1.256600 / 1.245400 / 1.002931 |
| SS 1.62 V, -40 C | RC | 1.325825 / 1.581239 / 1.561240 / 1.320796 |
| SS 1.62 V, 125 C | RC | 1.026545 / 1.229269 / 1.204830 / 1.016545 |

The maximum retained RC latency is **1.5812388274873799 ns**, at cold SS,
-3 mV, source trace `3e24dcb7350b577ec46c3195`. Its actual 10-to-5 ps
latency difference is 0.282195 ps and energy difference 0.017914%.
`retained-window-characterization.json` carries every 5 ps source ID and
the specific 2 ns numerical comparison. **3.5 ns is NOT EVALUATED**, and no
cross-deadline stability or convergence is inferred from the 2 ns result.

## Final handoff artifacts and ledger

The local-only implementation commit is
`cdc9f4d5aff0e15c12a08127621e55b32f277052`; its experimental execution commit
is `68832ec0ae7c526afcb4cded405a0bfd753a65c3`.
The new phase used **1/2 repair jobs**. Both older phases remain **4/4**,
with their failures, legal references and receipts unchanged. No second
repair attempt was spent on the performance failure.

`evidence/attempt1` contains the exact repaired MAG/GDS and native
LVS/C/RC/EXT/resistance files, full structural results and all negative
controls, exact material delta, both protocols, model/source hashes, all
five-condition metrics and numerical histories. Six original 5 ps RC
NPZ/deck/log/device-audit examples cover both signs at TT and both SS
conditions; they include failing 1 ns evidence. The complete 160-trace
archive remains preserved in session storage.

| Evidence | SHA-256 |
|---|---|
| Full CI archive, artifact `10786855366`, 26,371,449 bytes | `06195f766e68d131c4cc23eb1bd4ddc9cfeae31f5328f839c0d46314524838ab` |
| Full 1235-file CI manifest | `4ab45d3b394c163016bb3fb52acf83a4986ea777ab09d9e22c1cb2ca492f0344` |
| Raw Actions log | `fd9fe2ce902441a50563b71eba9557b0f2d4207927781b14d4ca79d483ffa872` |
| Actual repaired `atlas.mag` | `b2442585e4f9fec2be04b7dd48de4e5e1b87b8fcc375780df11a845be9a2c342` |
| Actual repaired `atlas.gds` | `a7d778406f5766b443eb954bfda33e56158a7604caf3ccd02d5b634d4b57d910` |
| Native `atlas.lvs.spice` | `847433769a7997beb8da38fdab55760184119c3883967e7d34235d8a934a8a35` |
| Native `atlas.c.spice` | `5f5adafe317eb94436be4b9bc0c1a2cefcaef453c46e03913877961476feee72` |
| Native `atlas.rc.spice` | `8f76622f875c815303157682cfa841fcb54829d586cb31d858f4c81bc9755f92` |

`verification-receipt.json` provides the complete separate ledger, native
hashes, legal-layout comparisons, per-mode sample counts and explicit gated
states. `full-ci-manifest.sha256` describes the authenticated full archive;
`snapshot.sha256` describes only the exact committed subset and derived
tables, so it must not be mistaken for all 1235 files. All 82 original entry
checksum assertions pass, PR195 remains open at `2ad1c4c`, both main branches
are unchanged, and neither older experimental branch was updated.
Parent review is required before any competition-entry publication.
