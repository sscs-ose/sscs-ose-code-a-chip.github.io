# Where the evidence is

The main notebook runs six new latch simulations. Its larger circuit examples
use saved Windows data. The browser preview uses saved data only.
The table below lists the supporting studies. You do not need to read them
all before starting the main notebook.

An audit checks archive/file hashes, rebuilds the circuit decks and repeats
the measurements. It runs no SPICE. Saved vectors keep every parsed float64
sample without downsampling. Original text hashes are recorded; full text
originals remain in the local research archive.

## Saved studies

| Folder under `results/` | What is retained | Audit command |
|---|---|---|
| `sequence/` | 20 complete latch cases and nine unresolved logs | `python sequence_evidence.py` |
| `mechanism/` | The six latch simulations behind the RC prediction check | `python mechanism_evidence.py` |
| `external/` | 57 complete and 15 unresolved single-rail flip-flop attempts | `python external_evidence.py` |
| `scaling/` | All 51 detector-sizing runs | `python scaling_evidence.py` |
| `por/` | 17 complete and 14 unresolved published-POR attempts | `python por_evidence.py` |
| `guard/` | Six pilot, twelve challenge and four smaller-step guard runs | `python guard_evidence.py` |
| `applicability/` | All 72 storage, temperature, isolated DC and resistor records | `python applicability_evidence.py` |
| `reference/` | Nine characterizations, six reference-only starts and 41 complete-circuit runs | `python reference_evidence.py` |

Raw ZIPs contain decks, simulator settings, logs and vector data.
The adjacent manifests record hashes and expected results. Failed requirements
stay in the data. Incomplete simulations have no functional verdict.
Corrupted-data checks are software tests, not extra transistor experiments.

## What each study shows

**Latch and RC explanation.** The 20 sequence cases include normal-write and
retained-state trials at TT/SF, both 27 C, plus numerical repeats. They compare
RC, supply sensing and an RC discharge variant. The nine unresolved sparse
attempts belong to an earlier ideal-input study; later KLU successes do not
erase them. The separate six-run mechanism archive checks two voltage
predictions while retaining both reset misses. Its original prediction sources
are included and hash-checked. See [MECHANISM.md](MECHANISM.md).

**Published single-rail flip-flop.** The external archive keeps all 71 original
attempts and the first incomplete portable no-dip run. The default supported
scope is TT/27 C/1.8 V/10 fF, with sparse/Gear and the tolerances in
`external_spec.json`. Six state/stimulus cases complete. Selected tolerance and
step repeats agree; some KLU no-dip attempts remain unresolved. Repeated settings
are not independent physical conditions. Without a dip, Q=1 must stay stored,
so a reset-to-zero verdict is deliberately false for that control.

**Detector sizing.** Nine TT pilot runs select scale four, then 24 comparisons
and 18 smaller-step repeats check it. Working matched reset cases use 43.7% to
51.3% less supplied energy than the original sensing branch. Detector channel
length and resistance grow fourfold, and release is slower. The gate-rectangle
proxy is not physical area. This does not compare against an optimized
supervisor. SF with the original branch was already explored. Missing, failing
or mixed-comparison controls are rejected before selection.

**Published POR.** The 17 complete records include one POR-only startup,
twelve primary/control integrations and four smaller-step repeats.
The 14 unresolved records contain a legacy-model setup error, an operating-point
fallback and twelve resource-limit attempts. The rejected fallback vectors
are not qualified data. Equal-fraction and zero-volt controls keep the analog
and digital interruptions separate. All retained-state trials pass. A separate
threshold implementation agrees on all sixteen complete coupled traces.
The schematic zero-volt retention result does not establish hardware retention.

**Guard.** In the five challenge reset histories, the original restores two
and the guard restores five. Both preserve data in warm storage. All primary
starts and prior writes pass. Four smaller-step repeats agree. Working primary
energy costs rise about 1.31% to 2.57%; the refined slow pair gives 1.303%.
The failed originals get no energy ranking. Different histories are separate
comparisons, not a lifetime usage mix.

**Temperature and isolated DC.** The 72 records include eight storage traces,
six complete-circuit temperature traces, forty isolated DC sweeps and eighteen
resistor trials. Both circuits pass benign storage. At 125 C both write Q=1
but miss shallow reset. At -40 C cold release fails before the write.
Every failure and secondary FS crossing is retained. Isolated crossings do not
prove complete-circuit reset or hysteresis. [APPLICABILITY.md](APPLICABILITY.md)
gives the limits and commands.

**Reference controller.** The four archives keep all 56 acquired records,
including bare-reference misses, cold setup failures and exercised reset misses.
They also retain the first adapter's three pre-SPICE errors and eight jobs not
started, separately from transistor outcomes. The audit reconstructs the
development fit from the one-uA characterization data. The three-controller
choice uses primary behavior and common smaller-step working energy rows.
[REFERENCE.md](REFERENCE.md) explains the circuit and its mixed source geometry.

## Repeat a study with new simulations

After [setup](README.md), use the environment's Python.

| Command | New simulations |
|---|---:|
| `python execute_sequence_notebook.py` | Six latch cases |
| `python reproduce_sequence.py` | Four matched latch cases |
| `python reproduce_external.py` | Six single-rail flip-flop cases |
| `python reproduce_design.py` | Twelve sizing cases |
| `python reproduce_por.py` | Twelve published-POR cases |
| `python reproduce_guard.py` | Eight original/guard cases |
| `python reproduce_applicability.py` | Six complete-circuit cases and two isolated DC sweeps |
| `python reproduce_reference.py` | Ten selected reference/control cases |

Each command keeps fresh decks, waveforms and logs. It never substitutes saved
successes for incomplete new runs. The companion notebook only audits saved
reference data. The current main checks saved POR, guard and reference data;
the older external/sizing/applicability studies remain optional.

## Scope

These are development conditions, not globally unseen tests or a qualified
continuous range. Ideal added passives, disabled gate tunnelling and documented
schematic geometry limit the results. Compare energy only between working
matched circuits, counting startup and every source.

Windows and Ubuntu on the same computer are portability checks, not independent
reproduction, silicon evidence or a human learning study.
