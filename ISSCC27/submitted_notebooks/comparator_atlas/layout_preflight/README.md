# Experimental SKY130 layout toolchain preflight

**Wei-Lun Hsu - National Tsing Hua University**

This is a bounded toolchain experiment, not the submitted Comparator Atlas
result and not a layout of the proposed 35-device comparator. The published
entry and its source commit `2ad1c4c2058060abdfdd42c35aa784c018f6fa67` are unchanged.
No comparator DRC/LVS/PEX, foundry signoff, silicon result, density coverage, or
antenna coverage is claimed.

## Final bounded preflight result

All **four authorized preflight attempts** are consumed. The final
[run 35819766445](https://github.com/WLHsu0827/sscs-ose-code-a-chip.github.io/actions/runs/35819766445),
at [experimental commit d04703af22ca85202d12b7564545d4aec892d191](https://github.com/WLHsu0827/sscs-ose-code-a-chip.github.io/commit/d04703af22ca85202d12b7564545d4aec892d191),
executed the real tools and finished in 49 seconds with **54 PASS / 0 FAIL /
0 skipped**. Every run has `run_attempt=1`; no fifth preflight run is authorized.
The final receipt is `verification_followup_receipt.json`. The original
`verification_receipt.json` and failed evidence remain unchanged.

| Capability | Actual attempt-4 result |
|---|---|
| Pinned tools/deck | Magic 8.3.684, circuit Netgen 1.5.323, generated SKY130A 1.0.608; 91,812 KiB source/build/install total |
| Geometry and DRC | Ten four-terminal primitives plus two routed two-device cells; nonempty active/poly/M1 geometry; all zero errors under `drc(full)` |
| Gate landing repair | Smallest connected M1/contact union area 0.1249749944 um2, exceeding the declared 0.10 um2 threshold |
| Native connectivity and LVS | All 12 named tops/native port lists match independent references, with exact device counts, model flavors, W/L/m and bodies |
| Negative controls | 0.07 um M1 spacing yields two `met1.2` error regions; connection, bulk, doubled-width and SVT-for-LVT references all mismatch |
| Separate PEX outputs | Each route has 0 R / 0 C in LVS, 0 R / 11 C in C-only, and 48 R / 22 C in real RC extraction |

The 20/800 um routes each preserve a genuine three-resistor drain fork:
`D -> D.n0 -> {D.t0, D.t1}`, reaching two distinct transistor drains.
No resistors were inserted or split by the harness.

| Route span (um) | Drain resistor values (ohm) | Drain component R sum (ohm) | Drain C sum (fF) | Total RC-netlist C (fF) |
|---|---|---:|---:|---:|
| 20 | 3.42516, 39.9693, 39.9693 | 83.36376 | 5.34886 | 7.23798 |
| 800 | 136.987, 173.53, 173.53 | 484.047 | 101.18093 | 103.07005 |

The long/short drain R-sum and C-sum ratios are 5.8064439512 and 18.9163541390.
C-only totals are 5.70247/101.53424 fF. All 11 `FLOATING`-annotated capacitors in
each RC netlist remain present and are DC-anchored through the appropriate
resistance component. Magic's capacitance placement is retained, including its
large port-to-body capacitor; this is not a calibrated distributed-capacitance
ladder or a foundry-qualified RC corner.

The downloaded 228,310-byte artifact ZIP matches GitHub's uploaded SHA-256:
`92093a41b5e8d4380b4405a4ad0f6d32719f93dc5483368e28a5b14c4ae1591a`.
All **175** manifest-listed files and the exact file set were verified, both
after extraction and inside the archive. The manifest SHA-256 is
`8ee8fd44493efc48b608199dd11826f4057cf5b5990e0dd6a400a0a873b00432`.
The receipt records representative GDS/MAG/netlist/reference/log hashes;
`artifact-sha256.json` covers every artifact. The ZIP, extracted evidence, and
Actions log are retained in the session's persistent files area.

This qualifies only the small primitive/routed toolchain experiment. It does
not qualify any comparator or run the optional model-based simulation. A
subsequently authorized full-comparator phase is separate from this receipt,
this four-run budget, and the unchanged published submission.

## Reproduce on a disposable Linux host

Ubuntu 24.04, Python 3 standard library, and the packages in `apt-packages.txt`
are the declared environment. Install those packages using the host's package
manager only when authorized. Then, from this directory:

```sh
python3 -m unittest discover -s . -p test_preflight.py -v
timeout --signal=TERM --kill-after=30s 24m bash run.sh
```

All compiled tools and sources stay under `.work`; evidence stays under `out`.
Existing paths are rejected rather than overwriting evidence. Set `LAYOUT_WORK`
and `LAYOUT_OUT` to fresh absolute paths for another run. The scripts do not use
sudo, install system-wide tools, install WSL, use Docker, or fetch a full PDK.

`pins.json` fixes Magic, Tim Edwards' **circuit Netgen** (not the unrelated mesh
generator), and open_pdks to full source commit hashes. The build uses shallow
filtered Git fetches and a sparse open_pdks checkout. It invokes the genuine
`configure` and `make -C sky130 magic-A netgen-A` preprocessing targets, including
their required `custom/scripts` helpers. It never runs vendor/prerequisite or
full-PDK installation targets and never substitutes a fabricated extraction
deck. Generated technology files, hashes, executable/source versions, dependency
versions, build logs, and installed sizes are preserved.

## What is exercised

The accepted four-terminal primitive alternative is used instead of an inverter.
Each of the ten independent cells contains one transistor, actual PCell-generated
contacts and a contacted guard/body ring, with explicit `D G S B` port order.
All have `nf=1`, `m=1`; requested dimensions may not be silently clamped.
The wrapper sets `units internal` before `snap internal` and PCell calls, using
Magic's supported coordinate contract without editing the PDK or hiding warnings.
It removes the generated `FIXED_BBOX` abutment metadata before painting the gate
landing, so Magic recomputes the full physical bounds including the guard ring.
No paint or DRC rule is removed; area selection and DRC cover the full cell.
The gate metal1 landing is extended north on the same connected polygon. Its
actual M1/contact union area must be at least 0.10 um2, independently measured
from the saved geometry and Magic's grid scale, in addition to passing DRC.

| Primitive | W (um) | L (um) |
|---|---:|---:|
| Ordinary SVT NFET input | 3 | 0.15 |
| Ordinary SVT NFET switches | 1, 2 | 0.15 |
| Ordinary SVT PFET | 3 | 0.15 |
| LVT NFET fine-device matrix | 0.42, 0.84 | 2, 4, 6 |

The harness checks nonempty `.mag` rectangles and GDS layer geometry, extracted
transistor count/model/W/L/m/bulk, and Magic **sky130A `drc(full)`**, with Euclidean
distance enabled. A separate 0.07 um metal1 spacing violation must produce DRC
errors. These are local open-source deck checks, not complete tapeout checks.
The selected style is read with `drc list style` and corroborated by captured
raw Magic output.

The independent schematic reference is constructed from `devices.json`, never
copied from the extracted netlist. Netgen explicitly recognizes the four-terminal
primitive classes as `nmos`/`pmos` while retaining distinct SKY130 model names and
the unmodified generated SKY130 setup's W/L and bulk comparisons. No device is
replaced by an empty black box. Four reference mutations must fail: gate/source
short, incorrect bulk, doubled width, and SVT substituted for LVT. A tool exit
code alone is not counted as an LVS match.
Magic itself emits the named top with `ext2spice subcircuit top on`. Both its
SPICE wrapper and the actual `.ext` port order are checked before Netgen starts;
the harness does not manufacture a wrapper around an invalid extraction.

Two PCell-based branched drain probes have 0.36 um metal2 width and 20/800 um
spans from the devices to the external port. Each contains two separately drawn
3/0.15 um SVT NFETs, separated by 12 um, with independent gates and sources.
The actual top ports are `D G S B G2 S2`; the independent two-device reference
requires `D/G/S/B` and `D/G2/S2/B`, including both devices' W/L/m and body checks.
Both gate landings are checked. Real guard-ring taps are joined with a 0.20 um
local-interconnect route outside the device cores.

A metal2 trunk reaches a fork halfway along the span; upper/lower arms connect
through genuine PDK-generated via1 contacts to the **two distinct drain loads**.
This is physical branching, not hand-split resistance. Unlike attempt 3's two
contacts on one drain, these independently gated/sourced devices provide
distinct extraction endpoints. The external drain port is at the far end,
without a zero-ohm alias. The longer 800 um span distinguishes wire-length
dependence from the two fixed contact/diffusion loads; the greater-than-three
R/C ratio criteria are unchanged. Separate files contain:

- `*.lvs.spice`: connectivity only; no parasitic R or C.
- `*.c.spice`: layout-derived capacitance without distributed resistance.
- `*.rc.spice`: actual `extract do resistance` / `.res.ext` output incorporated
  with `ext2spice extresist on`, zero capacitance threshold, and finite resistance
  threshold, explicitly set after the LVS preset.

The pinned modern Magic interface uses `threshold`/`minresist` in milliohms and
`mindelay` in picoseconds, not deprecated `tolerance`. The harness requires
positive R/C values, multiple connected resistors between the external drain and
both distinct transistor drain endpoints, an extracted branch junction, internal nodes, and
increasing extracted drain RC for the longer route. Every MOS terminal and
parasitic node must be DC-connected to the correct external port without shorts.
`FLOATING`-annotated capacitances are retained and checked, not deleted.
It records every resistor/capacitor value, the drain component's element names,
terminal memberships, branch nodes, and actual route coordinates in
`capabilities.json`.
Resistance sums describe the extracted component, not an AC impedance or a
general effective resistance measurement.

The explicit `ngspice()` extraction style emits device geometry in **micrometres**; the
unscaled W/L values are checked directly and extra scale directives are rejected.
No SPICE smoke simulation is included. The earlier schematic-model source is
`google/skywater-pdk-libs-sky130_fd_pr` at
`f62031a1be9aefe902d6d54cddd6f59b57627436`; it is recorded but not downloaded.
The open_pdks layout technology has separate provenance. Model equivalence
between these revisions and a foundry-qualified RC corner is not established.

## Restricted CI and evidence

`ci.yml` is an inert project-scoped workflow template. Its only authorized root
installation is `.github/workflows/comparator-atlas-layout-preflight.yml` on
the author's fork branch `verify/comparator-atlas-layout-preflight`. It triggers
only that branch, only for this experiment, and only in the author's fork.
Never place the root workflow on the submitted branch or upstream; do not open
a formal PR for this preflight. The job is limited to 30 minutes, with a 24-minute
toolchain timeout and an always-run artifact upload.

On that verification branch only, exclude the same branch from the inherited
`lint.yaml` and `run.yaml` push triggers so they do not start an unrelated
historical-notebook checkout. The scoped workflow uses an unauthenticated,
shallow, sparse fetch of this public fork at `GITHUB_SHA`, never recursive
submodule operations. This avoids the historical dangling submodule entry that
caused the first attempt's checkout-action credential cleanup to fail.

The initial authorization allowed at most two remote runs. CI artifacts contain the actual
GDS, Magic layouts, connectivity/C/RC netlists, `.ext`/`.res.ext`, independent
references, DRC/LVS reports, and source/deck/binary/artifact hashes. Successful
installation alone is not a passed layout. Execution receipts and the actual
capability outcome are reported separately after inspecting downloaded evidence.

A subsequent bounded decision authorized up to two more runs (attempts 3/4,
each at most 30 minutes) to repair concrete implementation defects. The initial
`verification_receipt.json`, both original runs, and the following historical
failure analysis remain unchanged. Further runs do not retrospectively turn the
initial 12 PASS / 42 FAIL result green.

Attempt 3, [run 35811055218](https://github.com/WLHsu0827/sscs-ose-code-a-chip.github.io/actions/runs/35811055218),
commit `6dba68679a94f7d6a34c6ee6e03345b726b14711`, executed Magic and Netgen and
recorded **11 PASS / 13 FAIL**, with 30 downstream primitive checks skipped.
Both routed structures passed genuine named-style DRC and positive LVS; all
four negative LVS controls and the negative spacing control passed. The ten
primitive generation checks rejected the exact units/snap deprecation warning,
although the raw logs contain completed extraction and DRC. These warning-based
failures are not evidence of illegal device geometry. Both drain forks reduced
to one drain resistor (37.8702 / 135.924 ohm), so distributed-route RC and its
acceptance comparison remained unproven. All 135 artifact-manifest entries were
verified. Attempt 4 subsequently consumed the final authorized attempt and passed
the complete matrix above. No fifth preflight run or additional triggering push
is authorized.

Original harness code is MIT licensed under the parent project's license.
Fetched third-party sources retain their own licenses. Magic, open_pdks and
circuit Netgen are credited to their upstream projects and contributors.

## Initial verification provenance

Attempt 1: [run 35808864758](https://github.com/WLHsu0827/sscs-ose-code-a-chip.github.io/actions/runs/35808864758),
commit `9b194bb4fc4d6328b2546f983a71b550df084257`, failed in checkout before
dependencies or tools ran. The checkout action's auth cleanup reported
`No url found for submodule path ... sky130-opamp in .gitmodules`.
This is an infrastructure failure, **not** a DRC, LVS, or PEX result.
Attempt 2: [run 35809175154](https://github.com/WLHsu0827/sscs-ose-code-a-chip.github.io/actions/runs/35809175154),
commit `0cd79b96016b4ebc39af26d7c1542bb667c8dce6`, completed in 48 seconds with
**failure**. Both authorized attempts are now consumed. No third run was started,
no controls were relaxed, and no comparator layout was attempted.

Unlike attempt 1, attempt 2 actually built and executed Magic **8.3.684** and
circuit Netgen **1.5.323**, generated the open_pdks **1.0.608** tools-only deck,
and wrote real layouts, extracted devices, DRC results and RC networks.
The recorded source/build/install directories totaled 91,812 KiB (about 89.7 MiB).

| Capability | Actual evidence from attempt 2 | Outcome |
|---|---|---|
| Pinned tools / genuine PDK staging | Built tools, executed version/commit, generated deck and source hashes retained | Passed |
| Ten four-terminal primitives | Nonempty MAG/GDS; one correct model/W/L transistor per cell; D/G/S/B labels and `.ext` ports present | Observed |
| Six LVT dimension combinations | `drc(full)` logs and zero raw DRC errors for all six | Observed local DRC pass |
| SVT NFET, PFET and two routed probes | Three error rectangles each for gate-contact metal1 minimum area, `met1.6` | Failed |
| Deliberate spacing error | Two `met1.2` errors for a 0.07 um gap below the 0.14 um rule | Detected |
| Positive LVS and four LVS mutations | Missing top-level `.subckt` wrapper; Netgen cannot find the named circuit | Blocked, not comparisons |
| Separate C and RC extraction | Each C-only file: 6 C / 0 R; each RC file: 21 R / 11 C plus `.res.ext` | Partial, not accepted PEX |

**First substantive blocker:** the short-channel primitives' isolated gate metal1
landing is approximately 0.29 by 0.23 um (0.0667 um2), below `met1.6`'s
0.083 um2 minimum. The PCell device dimensions themselves are extracted correctly;
this is missing legal landing/routing area in the preflight structure. The
three rectangles are regions for one rule, not three independent rule types.

There are additional harness/integration blockers, all preserved in the failed
evidence rather than relabeled as passes:

- `[drc style]` prints the style but returns an empty Tcl value, so the report's
  style field is blank. The captured Magic log explicitly names `drc(full)`.
  The automated geometry/DRC assertions therefore failed even for the six
  raw-zero-error LVT cells and the correctly detected spacing control.
- `.mag` and `.ext` contain numbered ports, but the selected flat SPICE output
  has no `.subckt` wrapper. Netgen launches and reads the files, then reports
  `Cannot find cell n_input3`; the setup/classification and real comparisons
  are not reached. Wrong-connection/bulk/width/flavor controls are **unproven**.
- `extract style ngspice` is ambiguous at this version; the actual `.ext` style
  is `ngspice()`. The obsolete `-y` accuracy option also produces a warning.
- Both RC files contain real positive extracted elements, but the long drain
  path is represented by only one resistor, not the multiple drain-path
  segments required by the acceptance check. Some internal capacitances carry
  Magic's `; **FLOATING` comment, which the strict parser also needs to handle
  without discarding connectivity checks. No simulation or PEX signoff occurred.

The short/long drain resistors are **51.6048 / 175.749 ohm**. Across each whole
RC netlist, resistor values span 5.8005 to 3285.26 ohm; the latter values include
body-network resistance, not just the deliberately routed metal. Total extracted
RC capacitance is **5.95932 / 35.43025 fF**, with individual capacitors ranging
from 0.03067 fF to 4.64862 / 34.05628 fF. These measurements establish that the
outputs are not the parasitic-free LVS files, but do not satisfy the complete
DRC/LVS/distributed-route acceptance.

The automated receipt remains **12 PASS / 42 FAIL**, not a green preflight.
Post-run read-only inspection verified all **141** recorded artifact hashes and
the device/layer facts above without modifying the downloaded outputs.
`verification_receipt.json` records the exact run, commit, artifact, deck hash,
capability limitations and measured values. The downloaded evidence is also
retained in the session artifact directory. Further execution requires a new
decision; the experimental branch remains at the attempt-2 commit.
