# Reproducing Comparator Atlas

## Run the notebook

Open `Comparator_Atlas.ipynb` and run all cells. The default mode uses the
provided data, verifies experiment records, redraws the figures and remeasures
saved waveforms. Use the fork Colab link in the README before upstream merge.

For local execution from the project directory:

```text
python -m pip install -r requirements-review.txt
python -m pytest --nbmake --nbmake-timeout=600 Comparator_Atlas.ipynb
```

The reviewer environment supports Python 3.10 with NumPy 2.2.6, pandas 2.2.3,
Matplotlib 3.10.3 and ipywidgets 8.1.7. Use a short checkout path on Windows.
If Colab has already imported another package version, restart the runtime
as prompted; the complete downloaded source is reused.

The execution tools and PDK are available free of charge; no paid API key or
commercial EDA license is required. Colab is optional and its free resources
are limited, so long experiments may instead use a local CPU. The project
does not require Colab Pro, a GPU, a paid cloud runner or a Copilot account
to reproduce its results. Keep applicable third-party license notices.

## Execution modes

| Mode | What runs |
| --- | --- |
| Default | Analyze the provided schematic and layout data; no simulator installation is required. |
| `RUN_LIVE_SPICE = True` | Run six fresh schematic examples using an installed ngspice and the pinned public models. |
| `RUN_FULL_CAMPAIGN = True` | Re-run schematic selection, PVT characterization, numerical checks and the lower-energy control. This can take hours. |

For the full schematic campaign, the corresponding CLI stages are:

```text
python -m comparator_atlas optimize
python -m comparator_atlas study
python -m comparator_atlas stress
python -m comparator_atlas.professional_audit
python -m presentation.waveform_lab
```

Windows users may use `node scripts/setup.mjs` to install project-local
Python 3.12.10 and ngspice 47. The recorded reference schematic campaign uses
ngspice 47; a different simulator version is not assumed numerically identical.

## Experiment scopes

### Current adopted layout and historical controls

The current layout is `layout_single_row/v2/`, version **single-row-local-pitch-b1**.
Its paired comparison includes the previously adopted a1 matched control and exact b1
candidate, each in C-only and distributed RC modes: 45 PVT conditions,
four signed inputs, and 10/5 ps steps (1440 recorded transients, 720 pairs).
The primary deadline is 2 ns; 1 ns is a parallel readout of the same waves.
See the [versioned package](layout_single_row/v2/README.md) for raw traces,
native records, model references and the offline remeasurement command.
The [prior a1 version](layout_single_row/v1/README.md) remains byte-identical.

`layout_compact_repair/` remains the **historical original compact control**.
The figures and schematic/RC tables in `results/study/postlayout_pvt45/`
belong to that original study, not the adopted candidate. Its 425.49 fJ
RC mean and 1.835 ns worst latency must not be read as candidate metrics.
The calibrated 49-condition schematic study is a third, distinct population.
Neither nominal-layout study applies schematic width stress or calibration.

Default analysis reconstructs results from recorded sources, not new physical
verification. The native generators are preserved execution-time sources;
they require their documented control/PCell/tool inputs and are not promised
to rebuild on a reviewer's machine using unavailable private directories.
Canonical public MAG/GDS, netlists and recorded checks support inspection.
Independent physical PEX qualification, silicon measurements, post-layout
calibration, noise, mismatch statistics and yield remain outside this entry.

### Archived RC model applicability

**Archived RC-deck outcomes; model physical fidelity not yet qualified.**
This limitation applies to the original five-condition ngspice-42 pilot,
the historical original-control 45-PVT study and the current paired
single-row-a1 and local-pitch b1 qualifications.
Their reported measurements, numerical comparisons and historical pass/fail
records remain unchanged; they describe the decks actually executed.

The recorded extraction used Magic 8.3.684 at
`4f53bb3091d1e4a9b2009a58f157a8a4331d4c84` and open_pdks at
`aa3fc215a80d32437b8cca1cb3fdee819d18c4c9`
([recorded sources](layout_compact_repair/evidence/attempt1/sources.tsv)).
The [export commands](layout_nominal27/layout.tcl) enable coupling for C-only
and distributed RC. The archived
[C-only](layout_compact_repair/evidence/attempt1/atlas.c.spice) and
[RC](layout_compact_repair/evidence/attempt1/atlas.rc.spice) outputs retain
mutual capacitances while grounded capacitance increases; they are not
ground-only exports. The existing
[parasitic accounting](layout_compact_repair/evidence/attempt1/parasitic-analysis.json)
records these native values. The historical original-control full-grid study reuses this same RC netlist,
whose SHA-256 is
`8f76622f875c815303157682cfa841fcb54829d586cb31d858f4c81bc9755f92`.

Physical fidelity has not been qualified by an independent parasitic reference
or a complete common-node capacitance-equivalence check. The physical error
magnitude and direction are unknown: no exact duplication factor, corrected
counts or energy, or conservative performance bound is inferred.
C-only is not independent ground truth, and RC-versus-C performance differences
cannot be attributed solely to resistance. DRC/LVS establish their recorded
structural checks, not parasitic-model fidelity. Schematic results are unaffected
by this extraction concern. Timestep agreement, source hashes and clean-start
same-deck reproduction do not establish silicon PVT performance.

Historical receipts and frozen reproduction sources preserve their original
wording and status; this current limitation governs interpretation of their
RC outcomes, including the saved waveform teaching examples and comparisons
between legal layouts. No model correction was made. The separate,
subsequently run sensitivity check below does not replace any archived result.

### Bounded RC sensitivity check

The [plan](results/study/rc_sensitivity/plan.json) and
[per-pair measurements](results/study/rc_sensitivity/summary.json)
document a subsequent exploratory rerun of two **already published**
points: TT / 1.8 V / 27 C / -10 mV (`c01-rc-m10`) and the slowest archived
RC point, FS / 1.62 V / -40 C / -3 mV (`c37-rc-m03`). The unchanged
5 ps baselines reproduce their archived energy and 1/2 ns decisions.
Each point was run at 10 and 5 ps under seven settings: original; C only
times 0.8 or 1.2; R only times 0.8 or 1.2; and both times 0.8 or 1.2.
Only the original `atlas` subcircuit's 319 C and 675 R cards were scaled.
The 27 MOS, 5 fF external output loads, clocks, thresholds and model files
were held fixed. All 28 new transient records succeeded; the 14 timestep
pairs met the existing 1% energy / 20 ps latency / same-decision rule.

| RC point, 5 ps | Original 2 ns | C x 0.8 | C x 1.2 | R x 0.8 | R x 1.2 | Both x 0.8 | Both x 1.2 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| TT -10 mV | correct | correct | correct | correct | correct | correct | correct |
| FS -3 mV | correct | correct | **unresolved** | correct | correct | correct | **unresolved** |

At 1 ns the TT point is correct in all seven settings; the FS point is
unresolved in all seven. The original FS decision time is 1.835032 ns;
the FS C x 1.2 run records energy but **no** valid 2 ns decision time.
These synchronized +/-20% whole-subcircuit card factors are chosen
illustrations, **not** a characterized PDK uncertainty interval or a
physically qualified PEX alternative. In particular, this is not a
rerun of all 45 PVT conditions or a revision of the archived nominal
180/180 result.

The [runner](reproduction/pvt45/run_rc_sensitivity.py) checks the unchanged
public source/netlist and ngspice-47/model pins, then creates an empty
short-path output directory and keeps each executed deck, log, waveform,
measurement and numerical comparison. Its raw outputs remain local; the
published JSON contains only the path-free plan and qualified measurements,
not a redistributed model tree. From the entry root, with the same pinned
Windows tools and caller-supplied read-only models described in
[the clean-start reproduction](reproduction/pvt45/pvt45_reproduce/README.md):

```powershell
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:OMP_NUM_THREADS = '1'
$env:OPENBLAS_NUM_THREADS = '1'
$env:MKL_NUM_THREADS = '1'
& $Python -B .\reproduction\pvt45\run_rc_sensitivity.py `
  --entry .\reproduction\pvt45 --models $Models `
  --ngspice $Ngspice --out $env:ATLAS_FRESH_SENS_OUT
```

Use a **new, nonexistent, short** `$env:ATLAS_FRESH_SENS_OUT` path; this
optional 28-transient experiment is not started by the notebook default.
The separate [GDS geometry audit and conditional layer-coefficient
components](results/study/gds_geometry/README.md) provide public inputs,
a path-free script and source hashes. Restoring GDS ports and matching
exported polygons do not make its imported RC graph interchangeable with
the archived MAG graph. No complete whole-net R/C estimate or qualified
external PEX reference has been established.

| Experiment | Conditions and controls | Reporting |
| --- | --- | --- |
| Schematic design comparison | 45 PVT combinations at controlled main-pair width stress, plus four nominal controls; 49 conditions per design | Same calibration policy, input band and deadline for circuit comparisons |
| Lower-energy control | Existing `lvt_base_3b` candidate, characterized after the original selection | Identified separately from selection data |
| Extracted layout | Five conditions, nominal matched geometry, code zero, four inputs `-10, -3, +3, +10 mV`, four netlist modes | Original 1 ns pilot and separately labeled retained 2 ns observations |
| Full-grid post-layout study | Same nominal repaired layout and schematic, TT/SS/FF/SF/FS, 1.62/1.8/1.95 V, -40/27/125 C, the same four inputs; 180 points per mode | Independently declared 2 ns primary deadline, with parallel 1 ns results |
| Waveform lab | Eight representative saved schematic/RC traces | Illustrates the measurement rules; not additional validation coverage |

The earlier ngspice-42 layout pilot is 12/20 correct at 1 ns and 20/20 at
the retained 2 ns window. That post-hoc characterization does not revise its
original failed gate.

The completed full-grid ngspice-47 study is distinct: RC is correct at
180/180 points at its prospectively declared 2 ns deadline, and 156/180
at 1 ns; the other 24 are unresolved. All 360 schematic/RC histories
qualify at 10/5 ps under the same numerical criteria. The five pilot
conditions were previously observed, while forty are new post-layout
conditions; this is not a blinded external test. No 3.5 ns result is claimed.

## Full-grid failure distribution

Notebook Section 8 includes a 15-row marginal table locating the original
24 RC decisions unresolved at 1 ns. Reproduce it from the public 360-row
finest-result CSV, without any waveform remeasurement or new simulation:

```text
python -B -m scripts.audit_pvt_failures --format markdown
python -B -m scripts.audit_pvt_failures
```

Run these commands from the entry directory with the existing reviewer
dependencies. The [audit](scripts/audit_pvt_failures.py) reuses the published
grid/rail validators and verifies pinned source artifacts, exactly 180
distinct points per mode, unique point/attempt/run identities, and the fixed
SC/RC outcomes at both deadlines. Missing/duplicate records, inconsistent
labels or incomplete numerical qualification fail rather than shrinking
denominators. JSON output includes all marginal counts and the 24 affected
point/run identities; the [tests](tests/test_pvt_failure_audit.py) also verify
the notebook's displayed table against the actual CSV.

Each factor independently partitions the same 180 RC points: each corner
has 36, each supply/temperature 60, and each signed input 45. The four
partitions overlap and cannot be summed or used as independent observations.
All 24 unresolved records occur at 1.62 V in SS or FS, with all three
temperatures and all four input levels represented. This is a descriptive
association in the archived decks, not a statistical-significance, causal,
continuous-input or silicon claim. RC remains 156 correct / 24 unresolved /
0 wrong at 1 ns and 180 correct at the prospectively declared 2 ns; SC is
180 correct at both. The earlier pilot's post-hoc 2 ns result stays separate.
Record-level classification is not full 720-raw-trace remeasurement, and the
RC model's physical fidelity remains unqualified.

## Independent public-waveform check

From the entry directory, run the standalone standard-library checker:

```text
python -I -S -B scripts/check_public_waveforms.py
```

This command reads the ten published NPZ traces in
`results/study/postlayout_pvt45/representative-traces/` and prints a JSON report
to stdout; it does not install packages, start a simulator, or rewrite files.
Unlike the notebook's existing replay through `comparator_atlas.spice.measure`,
the [checker](scripts/check_public_waveforms.py) separately implements NPZ/NPY
reading, scalar interpolation, decision classification, latency and energy
integration without importing that producer or NumPy. **Independent refers to
the reader and arithmetic implementation, not the experiment or personnel.**

The fixed contract is unchanged: evaluation starts at 22.025 ns; both outputs
must satisfy complementary inclusive 80%/20% supply rails at 1 ns or 2 ns after
that instant. An opposite resolved sign is wrong, while missing complementary
rails are unresolved. Reset checks both output and internal-node pairs against
90% of supply 100 ps before evaluation. Latency is the first sampled valid
point after the last invalid sample before the deadline, with interpolated
evaluation/deadline endpoints; it is not an interpolated threshold-crossing
estimate. Full-cycle core energy is the negative supply voltage times the
trapezoidal integral of supply current over **20-30 ns**, with interpolated
cycle endpoints, regardless of the decision deadline.

The checker pins the public index and comparison-table SHA-256 values,
checks all 60 indexed artifacts, and binds each waveform to its original
metadata, collector record and unique published table row. It compares all
eight measurement fields at both deadlines against the collector and table.
Labels, reset state and unresolved null latency must match exactly; numeric
comparisons use the existing replay tolerance of `1e-11` relative and `1e-11`
absolute in each reported unit solely for arithmetic roundoff. This does not
change the separate simulation-convergence limits of 1% energy and 20 ps.
The JSON includes input/checker hashes, all 20 observations and numeric absolute
differences against both references. Missing, modified, malformed or relabeled
evidence returns a nonzero exit status rather than a partial PASS.

These are **ten existing representative/teaching selections**, not random
samples or a held-out validation set; selection may be post-hoc. The expected
subset has eight correct and two unresolved decisions at 1 ns, and ten correct
at 2 ns. These counts are **not** the full-grid 156/180 and 180/180 results.
No additional simulations, full 720-trace replay, or new statistical coverage
are claimed. The RC decks' physical fidelity remains unqualified. Hashes detect
changes relative to the checked-in pins, not coordinated replacement of the
checker and data; agreement checks measurement arithmetic, not physical truth.
The reader deliberately accepts only the published NPY 1.0, C-order,
little-endian float64 nine-column format and bounded file sizes.

Synthetic hand-calculated cases and missing-trace, tamper, identity and CLI
failure tests are in [test_public_waveforms.py](tests/test_public_waveforms.py).
With the existing reviewer dependencies installed:

```text
python -B -m pytest -q tests/test_public_waveforms.py
```

## Numerical measurements

A decision requires complementary 80%/20% output rails and the correct input
polarity. Zero differential input is unscored. Core energy is integrated over
the complete 20–30 ns cycle; external drivers and calibration infrastructure
are excluded.

Timestep comparisons use identical decision/outcome labels, at most 1% energy
difference and at most 20 ps resolved-latency difference. Sensitive schematic
points receive further timestep halving, with unfavorable corrections retained.
The layout's stored 10/5 ps comparisons are provided for its sampled conditions.
These are numerical consistency checks, not a noise or yield model.

## Data and physical source

| Location | Contents |
| --- | --- |
| `results/study/selection.json` | Declared candidate-selection result |
| `results/study/verified_measurements.csv` | Reported schematic observations after explicit numerical corrections |
| `results/study/measurement_refinements.csv` | Original-to-refined observation replacements |
| `results/study/professional/` | Lower-energy control and its numerical checks |
| `evidence_traces/` | Schematic teaching waveforms and source identities |
| `layout_compact_repair/evidence/attempt1/` | Actual GDS/MAG, LVS/C/RC netlists, checks, measured tables and six RC trace examples |
| `layout_compact_repair/verification-receipt.json` | Physical experiment provenance and measured comparison |
| `layout_nominal27/`, `layout_preflight/` | Physical generation/verification support and preceding references |
| `results/study/postlayout_pvt45/` | Complete 360-row schematic/RC comparison, independently audited results, 45-condition table, figures and ten representative raw examples |

The physical snapshot contains 108 selected files and review tables; it is
not the entire CI payload. Per-file hashes bind the included data to the
recorded experiment. The default notebook checks the data it displays.

### Full-grid numerical reference

The expanded PVT reference uses Windows ngspice 47, Python 3.12.10 and
NumPy 2.2.6. Both schematic and RC use the same tool/model environment.
The extracted RC and GDS are byte-identical to the repaired physical
reference; Magic/DRC/LVS were not rerun for the expanded SPICE study.
The model checkout is unmodified at the pinned SKY130 commit. Its actual
Windows CRLF bytes are recorded separately from canonical Git blobs.

The full reference consists of 720 distinct point/timestep evaluations.
Two reserved-but-unstarted slots and the documented execution continuations
are retained separately. An initial reporting issue accepted only an exact
ngspice log-destination banner after checking the original log and waveform;
later timing and checkpoint-I/O interruptions were resolved through explicit
continuations without changing the circuit, inputs or numerical thresholds.
The original execution-window timing failure remains recorded. Final data
completeness and numerical/functional qualification are separate from that
historical timing-conformance flag.

`source-summary.json` and `independent-audit.json` preserve these distinctions.
The published ten trace examples retain original metadata alongside the linked
collector acceptance; six original metadata files contain the earlier
`measurement_error` status. They were not rewritten. The examples allow
remeasurement of matched TT points, the global-delay FS corner and the
maximum-energy FF point; they do not constitute all 720 original traces.
The default notebook independently checks the complete table and remeasures
the ten included raw waveforms.

### Figure regeneration

```text
python scripts/build_pvt45_figure.py
```

This regenerates the full-PVT timing map, all-180-pair delay/energy comparison,
and matched worst-case waveform from checked data. PDF masters are vector,
with embedded fonts at the actual 7.16-inch two-column size; SVG and 600 dpi
PNG companions and separate captions are also provided. No simulations run.

### Fresh schematic/RC reproduction

The clean-start source is isolated in `reproduction/pvt45/` so its pinned
helper files do not overwrite the main entry or depend on historical private
checkpoints. It requires the existing free Windows x64 Python 3.12.10,
NumPy 2.2.6, ngspice-47 console and the recorded unmodified SKY130 model
checkout. Exact runtime and Windows raw-model identities are verified;
an arbitrary different model checkout is not silently substituted.

From `reproduction/pvt45`, supply your own existing paths and run:

```powershell
& $Python -B .\pvt45_reproduce\reproduce.py --smoke `
  --ngspice $Ngspice --models $Models --out $FreshOutput
```

`--smoke` performs four transients: TT/1.8 V/27 C, -10 mV, schematic and RC,
each at 10 and 5 ps. This clean-start test was executed and independently
remeasured; both numerical pairs and all same-point reference comparisons
pass. It is separate from the 720-transient full-grid dataset.

The explicit `--full` mode uses the complete fixed grid with a fresh ledger,
the original numerical criteria and a bounded local supervisor. Its 720
initial points and possible refinement decks were checked against the
recorded plan. A new full-matrix rerun of this clean entrypoint was **not**
performed. Do not interpret a successful smoke or static plan check as
another full-PVT validation.

Running without a mode prints help and performs no simulation.
Detailed model-byte expectations, parameter examples and output structure
are in [the clean-start README](reproduction/pvt45/pvt45_reproduce/README.md).
No paid API, cloud runner, tool download or global system change is required.

### Re-run the physical flow

The physical reference uses unmodified SKY130 primitive revision
`f62031a1be9aefe902d6d54cddd6f59b57627436`, Magic 8.3.684, Netgen 1.5.323,
open_pdks/sky130A 1.0.608, ngspice `42+ds-3build1` and NumPy 2.2.6.

Prepare the exact historical source without installing tools or running SPICE:

```text
python scripts/reproduce_layout_reference.py --prepare-only
```

The helper verifies source commit `68832ec0ae7c526afcb4cded405a0bfd753a65c3`
and its checksum context. In a disposable Ubuntu 24.04 environment, install
the packages specified by that source's `layout_compact_repair/ci.yml`, then
run `bash layout_compact_repair/run.sh` from the prepared project directory.
The flow preserves structural and simulation evidence and returns a failure
status when its original 1 ns performance gate is not met.

## Strict schematic specification map

The [saved map](results/study/specification_map/selection_map.png) and
[JSON records](results/study/specification_map/summary.json) are descriptive,
post-hoc analysis of the existing `local_boundary` calibrated **schematic**
study: three compared designs, all 49 controlled-width-stress conditions,
and both signs of the recorded nonzero inputs. This is not the nominal
45-PVT RC experiment.

The six minimum absolute inputs (0.25, 0.5, 1, 3, 10, 30 mV) and six recorded
deadlines (0.25, 0.35, 0.5, 0.75, 1, 2 ns) define 36 specification cells.
A design qualifies only when every included point at every condition is
correct. The winner minimizes measured mean full-cycle core energy across
that sampled band, not worst-cycle energy or total system/calibration cost.
No energy budget is imposed. No feasible design yields the explicit status
`No feasible compared design` and JSON-null winner/energy, never a
best-average substitute. Exact equal energy means are recorded as ties;
display selection follows the declared compared-design order.

The analysis calls `entry.load_evidence()` and `entry.summary()` without
changing calibration or original training selection. It rejects missing,
duplicate, unavailable and nonfinite observations. The JSON contains
108 per-design rows, 36 per-specification rows, source/provenance SHA256s,
and the saved figure hash. Recompute and compare all records read-only:

```text
python -B -m presentation.specification_map
```

`--write` regenerates only the JSON, selection map and failure-transition
PNG presentation artifacts; if
used for publication, refresh their entry checksums afterward. No new
SPICE, interpolation, continuous-input coverage, yield or physical-model
qualification is involved. Baseline's zero winning cells apply only to
this compared calibrated sampled domain.

### Matched failures and sampled limits

Schema 2 of the same JSON preserves the original 108 design rows and 36
specifications (28 NONE / 5 selected / 3 control / 0 baseline). It adds:

- `failure_analysis.grouped_counts`: all 10,584 calibrated nonzero
  observations, grouped separately by design/deadline, signed input, corner,
  voltage, temperature, width skew and complete condition. Each group
  explicitly counts correct, wrong and unresolved.
- `matched_samples`: 1,176 one-to-one design/condition/signed-input pairs at
  1 and 2 ns for |input| >= 1 mV, with endpoint run IDs, outcomes, times,
  energies, location and local calibration code. Missing/duplicate/unmatched
  keys, unavailable policies and inconsistent metadata fail explicitly;
  order is lexical keys, not CSV row position. Unresolved times remain null.
- `transition_matrix`: all nine outcome transitions for each design,
  including zeros. There is no monotonicity assumption. Selected wrong-sample
  identities are compared as sets, then both endpoints of every sample wrong
  at either deadline are retained. The archived data give the same 20 at both
  deadlines, all at +/-1 mV. Locations/codes alone do not prove trim saturation,
  residual offset, noise or any other physical cause.
- `sampled_limits`: for each strictly qualified design and each winner,
  minimum `(deadline_ns - decision_time_ns) * 1000` in ps and maximum
  measured full-cycle core energy in fJ over the same included band. All
  exact equal limiting values retain their complete observations in lexical
  sample-key order. Unqualified designs and NONE winners have null limits;
  no energy cap or alternative selection rule is introduced.

Resolved nonzero observations require finite decision times; unresolved
observations require missing times. A 4e-15 ns tolerance handles recorded
seconds-to-nanoseconds roundoff at exact deadline endpoints, not a physical
guardband; reported margins are not clamped or rounded in JSON. The observed
limits are not confidence bounds over continuous PVT/noise/jitter, timing
signoff, a worst-cycle guarantee, or total system/calibration costs. The
same read-only command above recomputes every field and checks both PNG hashes.

## Checks

```text
python -m pytest -q tests presentation
python -m nbqa flake8 --ignore=E402,E226 Comparator_Atlas.ipynb
node --test tests/test_explorer.mjs tests/test_waveform_lab.mjs
```

The entry-specific Linux workflow also executes the notebook from a
notebook-only public download and again after a fresh kernel restart.
This checks the source bootstrap; it is not a Google-account runtime test.
The current run is linked in the submission PR.

Original code is MIT licensed. Model/tool licenses and references are listed
in `THIRD_PARTY_NOTICES.txt` and the notebook. Verbatim upstream tool notices
are in `third_party_licenses/`; tool binaries are obtained separately.
## Adopted local-pitch b1 version

The current layout/report/Notebook/poster explicitly select the exact frozen
local-pitch b1 candidate. [Versioned native assets, matched a1 control, all 1440 full45
and 64 earlier diagnostic traces, numerical receipts and offline audit](layout_single_row/v2/README.md)
are public. All-material area decreases from matched a1's 2074.254 to 1873.3 um2
(9.688013%). Pair order, mirroring, vertical placement, 27 guarded MOS devices,
15 ports, dimensions, body contacts, junctions and local escapes are preserved.
The 14 native checks and one candidate DRC attempt precede full45; both native
proofs/extracts were reused, not rerun. Publication performed no EDA/SPICE.
New local planning margins are at least 0.20 um; inherited unchanged global
M3 margin is 0.16 um. Historical pre-route recovered MAG differs from final MAG.

Both layouts and modes have 180 correct points at 2 ns; RC changes from 24 to 22 unresolved
points at 1 ns, only SS / 1.62 V / 125 C / +/-10 mV. C retains 10 unresolved
keys; FS late points remain, with null recorded latency at 1 ns.
There are 720 finest 5 ps traces and 1440 two-deadline rows, not 1440 independent
finest experiments. This nominal code-zero comparison used known conditions and is
not the calibrated 49-condition schematic study. Approximately 1.94% energy
changes are not robust global PPA benefits; numerical 1% / 20 ps acceptance
bands are not physical uncertainty bounds.
**Archived RC-deck outcomes; model physical fidelity not yet qualified.**
The original studies remain preserved historical control evidence.
The preceding a1 version and its twelve lossless raw partitions remain unchanged.
The b1 source adds eleven lossless sub-30 MB ZIP partitions; exact sizes/member
hashes and model-reference identities are recorded in publication provenance.
Bootstrap downloads both current evidence and retained history; use sufficient
disk space and a short Windows path. Archived host paths in source receipts are
provenance only, not executable dependencies. The default saved-data reader does
not run the archived native scripts that require unavailable private directories.
All 400 models refer to the existing public raw-byte/canonical-Git manifest;
no duplicate model corpus, LFS, private-only raw dependency or installer is added.
# Integrated decision reader and dated execution scope

The report, Notebook and poster now lead with a strict question: is any of
three compared designs correct at every included sampled point before the
deadline? Qualification precedes energy ranking; an infeasible specification
returns **NONE**. The unchanged `presentation/specification_map.py` defines
the 36 choices. `presentation/judge_decision.py` adds exact CSV record
locations and connects the existing stored map and waveform lab, without
changing measurements or promising a retained raw waveform for every key.
Different sampled input-band energies are not a same-specification energy
improvement. This calibrated 49-condition schematic comparison is separate
from the archived nominal code-zero b1/a1 45-PVT layout example.

From the entry directory, the presentation-only regeneration route is
`python -B -m presentation.judge_decision`. It uses shipped Python sources,
checked saved tables and checked existing figures; no private templates,
session files or native geometry generator are required. Individual routes
remain `python -B -m scripts.build_entry_notebook`,
`python -B -m presentation.contest_materials` and the existing study-report
renderer. Default Notebook execution remains saved-data mode; optional
live/full modes keep their documented explicit prerequisites.

**Dated maintainer scope (2026-10-07).** One actual GitHub HTTPS Windows
default saved-data execution on 2026-10-06 retrieved source
`db82273a5df8b73d39ebf20593309e433d1a1d50`: 28 cells visited, 13 code cells
freshly executed, zero **top-level cell** errors, Python 3.10.18 and 11
unchanged review pins. A 2026-10-07 recursive review subsequently found one
saved layout-selector widget error: an obsolete column drop in its callback.
Thus the older run does **not** establish complete interactive-reader success.
Its Notebook SHA256 was
`9335085a23b4f7db0fbded369c4ce969b41e04ffb0e54f8f9ca2d0167c66efd3`.
A separately modified private preview was also executed once locally on
2026-10-07 (28/13/0 top-level), with the same subsequently discovered widget
failure. The initial local publication-candidate run also exposed it and
failed the reader gate before commit or push. This release removes the
obsolete drop and adds actual four-way layout/mode callback checks plus
a recursive error validator and a negative widget-error fixture.
**Neither older run certifies this changed public reader source.**
Historical records are preserved, not relabeled. Detailed receipts remain
private; these statements
are not public execution-proof links. Release-specific execution results
are reported separately with their actual source identities.

No live SPICE, full campaign or native layout reconstruction was enabled in
those reader runs. They are not external-human, Linux or Colab reproduction,
physical-model qualification, silicon evidence or green-CI statements.
Archived native proofs remain reused, not rerun. Archived RC-deck outcomes;
model physical fidelity not yet qualified.

## Release binding and standalone reading

**Notebook and support files.** `entry_checksums.json` seals every entry file.
The Notebook bootstrap embeds `EXPECTED_SUPPORT_DIGEST`: SHA256 of the canonical
JSON (sorted keys, `,`/`:` separators) of that map without the editable
Notebook entry. Before installing anything or importing entry code, it
recomputes the digest from the support folder it found or downloaded. A
reused `comparator-atlas-source` folder from an older run, or a submitted branch
that moved after a Notebook copy was saved, stops with a release-mismatch
error instead of mixing versions; nothing is overwritten. Rename or delete that
folder and Run all again, or open the Notebook stored with the support files.
A downloaded folder without `entry_checksums.json` is also refused. Only a
local development checkout without a release map may continue, and it says so.
The file-by-file seal is then verified as before.

**Standalone report and Notebook-only reading.** Folder-relative links still
work in the complete entry. Each is followed by a *public copy* on GitHub. Linked
evidence is pinned in `presentation/public_sources.json` to an already
published commit whose bytes equal the local file; the build fails if a local
file differs. Regenerated reader documents (Notebook, report, README, guide,
this file) follow the submitted branch. Measurement records link to the pinned
table; record N is line N+1 because the header is line 1. GitHub may show
large CSVs only as raw or downloadable files.

Regeneration order: `python -B -m presentation.judge_decision`, then
`python -B scripts/execute_notebook.py`, then
`python -B -c "from presentation.judge_decision import reseal; reseal()"`.
The last step seals the executed Notebook; the support digest is unchanged.
After publishing changed evidence, refresh its pin with `python -B -m presentation.release_identity --pin PATH`.

## Research extension

Notebook Section 9 reports later schematic studies that ask why no compared
design qualifies at 1 mV and test trim designs that address it. They are an extension,
not part of the sealed decision record of Sections 1-8; nothing in the
specification map, the 49-condition data or the layout example is changed.

**Saved results.** `results/research/` holds the archived outputs of studies
r1-r26j (JSON, JSONL and CSV, LF line endings).
`results/research/manifest.json` lists the SHA256 of every archived file and
of every `research/*.py` script. `presentation/research_extension.py` pins the
manifest's own SHA256 and refuses to draw Section 9 if the manifest, any
archived file or any script differs. Default Notebook execution reads only
these saved files; it runs no simulation.

**Studies.** All scripts are in `research/`; each docstring states its
command line.

| Study | Script | Question |
| --- | --- | --- |
| r1 | `r1_trim_floor.py` | Is every wrong decision explained by the static residual offset? (saved data only) |
| r2 | `r2_prospective.py`, `r2_warm.py` | Do sealed predictions hold for six new designs? |
| r3 | `r3_mismatch_mc.py` | Paired Vth-mismatch Monte Carlo of the trim residual |
| r4 | `r4_tau_model.py`, `r4b_model_atlas.py` | Regeneration-time model of unresolved decisions |
| r5, r6 | `r5_parasitic.py`, `r6_layout_budget.py` | Pre-layout parasitic sensitivity; post-layout slowdown attribution on the b1 extraction |
| r7 | `r7_trim_dnl.py` | Trim-step DNL and the binary major-carry step |
| r8-r10 | `r8_unit_trim_mc.py`, `r9_combo_mc.py`, `r10_combo5b.py` | Unit-element trim and wider input pair in mismatch MC |
| r11 | `r11_post_layout_5b.py` | RC estimate for the fix on the b1 extraction (no drawn layout) |
| r12 | `r12_gate_trim.py` | Gate-switched trim alternative (rejected) |
| r13 | `r13_fix_atlas.py` | Sealed 49-condition atlas test of the fix; per-condition trim code and residual |
| r14 | `r14_energy.py` | Energy across PVT and trim area |
| r15 | `r15_range.py` | Sealed 49-condition tests of trim step against range: 5-bit unit trim with input W 3 (a), 6-bit unit trim with input W 6 (b) |
| r16 | `r16_six_bit.py` | The r15b 6-bit design: paired mismatch MC (TT and SS, 40 seeds each, same draws as r10) and nominal energy at three corners |
| r17 | `r17_post_layout_6b.py` | RC estimate for the 6-bit design on the b1 extraction (no drawn layout), and the unit-array schematic reference r11 should have used |
| r18 | `r18_energy_screen.py` | Nominal TT screen of lower-energy 6-bit trims (input W, trim L, switch W and side) |
| r19 | `r19_rc_wide.py`, `r19_atlas_wide.py`, `r19_mc_wide.py` | The r18 variant `u6_w12_l05` (6-bit unit trim at L 0.5, input W 12): RC estimate as r17, sealed 49-condition test as r15, paired mismatch MC as r16 |
| r20 | `r20_offset_mechanism.py`, `r20_dc_skew.py`, `r20_bin_stress.py` | Why the wider pair needs less trim: untrimmed-offset decomposition, DC current skew of a 4% width skew under the width-binned models, and width skew against an exact current skew (instance `m`) for five designs on 45 conditions |
| r21 | `r21_neutral_atlas.py` | The three sealed designs on all 49 conditions with width skew and with the exact current skew, every +/-1 mV, 1 ns point re-simulated at 0.625 ps |
| r22 | `r22_range_mc.py` | Nominal trim range of the three sealed designs on the 45 r20 conditions, and paired mismatch MC (40 seeds, as r3) of the selected design at SF and FF 1.95 V 125 C and of `lvt_base_3b` at SF 1.95 V 125 C |
| r23 | `r23_noise.py` | Transient thermal (white BSIM4) noise: input-referred noise of five designs at TT and of the selected design at SS 1.62 V -40 C and SF 1.95 V 125 C (40 paired realizations each), its split by device group, and the error rate it gives the r3/r16/r19/r22 MC residuals |
| r24 | `r24_isf.py`, `r24_scaling.py`, `r24_probe.py`, `r24_fixmc.py` | Measured impulse sensitivity (ISF) of the decision: noise predicted from the noiseless trajectory and checked per realization against r23 MC (nine benches), the selected design's noise at the 45 PVT conditions, decision memory of off trim branches and a layout-free fix, the closed-form integration-phase law with an input-common-mode prediction, the gain-suppression law for latch and reset noise, a causal probe of the memory and the equalize fix requalified over PVT, energy and paired mismatch MC |
| r25 | `r25_trim5.py`, `r25_cost.py`, `r25_report.py` | 5-bit trim with the equalizer on the shipped core: trim-length screen (gm/capacitance polarity reversal at the hot corners for L >= 1.25 um), 63-code transfer, 45-condition range, paired mismatch MC at SF/FF 1.95 V 125 C and TT, energy and memory |
| r26 | `r26_scale.py`, `r26_cost.py`, `r26_report.py` | The r25 trim with the input pair and tail widened by k (finer step): end-point screen, full transfer, 45-condition range, paired MC at SF/FF 1.95 V 125 C and TT, energy and memory for 5 bits at k 1.25 and 6 bits at k 1.5 |
| r26b | `r26b_unit.py`, `r26b_cost.py` | Single-bit weights of the width-binary trim over PVT, and the same trim built from unit cells (instance `m` = 2^k, same area): screen, transfer, range, paired MC and cost at k 1.25 and 1.5 |
| r26c | `r26c_stats.py`, `r26c_refine.py`, `r26c_fine.py`, `r26c_eqscale.py`, `r26c_cost.py` | 200-seed paired MC of `u5_k150` at five conditions with 0.01 mV re-bisection of borderline seeds, the 0.01 mV nominal transfer (carry DNL), the equalizer built from 2^k unit devices (`e5_k150`): transfer, range, 200-seed MC, clkb inverter sweep, energy and memory |
| r26d | `r26d_carry.py`, `r26d_segment.py` (with `r26c_eqscale.py`, `r26c_refine.py`, `r26c_stats.py`, `r26c_cost.py`) | The `e5` trim at input-pair scale 1.75 (`e5_k175`; transfer and range also at 1.625): 200-seed MC at the five conditions, energy and memory; local-step spread against the number of toggled bits (carry law) and a static-miss model with its prediction for segmented (thermometer-MSB) codings |
| r26e | `r26e_seg.py`, `r26e_carry.py`, `r26e_compare.py`, `r26e_cost.py` (with `r26c_stats.py`) | The k 1.75 trim with three thermometer MSBs (seven 4-cell segments, ideal decoder) and two binary LSBs (`g5_k175`): transfer, 200-seed MC at the five conditions on the same seeds, energy and memory; step spread by switched cells and steps above 2 mV against the r26d law |
| r26f | `r26f_tail.py`, `r26f_dec.py`, `r26f_kick.py` | Exact-likelihood step model (length bias, grid quantization, carry drift per switched cell) fitted on `e5_k175` and `g5_k175` and cross-predicting their steps above 2 mV; `g5_k175` with a transistor-level thermometer decoder (`d5_k175`): decoder leakage at three channel lengths over 45 conditions, transfer, segment-gate kickback at the clock edge, a hold-capacitor sweep, energy, and 200-seed paired MC at the five conditions against the ideal decoder |
| r26g | `r26g_drv.py` (with `r26f_dec.py`) | `d5_k175` with the two binary LSB switches buffered like the decoder outputs (`b5_k175`) and with every switch driver scaled with its switch (`s5_k175`): segment- and LSB-gate kickback waveforms at code -31, boundaries at codes 0, ±3, ±28 and ±31 bisected to 0.01 mV for the ideal decoder, `d5`, `b5`, `s5` and `d5` with 1, 2 and 4 µm hold capacitors at the five conditions, and the capacitive-divider dip-law fit |
| r26h | `r26h_thev.py`, `r26h_states.py`, `r26h_lincap.py` (with `r26g_drv.py`) | `g5_k175` with each segment source behind a linear series resistor and optional shunt capacitor (`h5_k175`): segment-gate kickback waveforms at code -31 and boundaries at codes 0, ±3, ±28 and ±31 bisected to 0.01 mV for eight (R, C) points at the five conditions (plus a 10 Ω kick as a check against the ideal source), tabulated against the r26g MOS designs; then all 14 gate states per design at code -31, linear drivers fitted per condition to the MOS on and off gates (symmetric, state-aware with separate on / off R and C, and H1 controls with only the off-state R or C changed) and d5 with an ideal 8.3 fF linear hold capacitor, probed the same way |
| r26i | `r26i_drv.py` (with `r26g_drv.py`) | `d5_k175` with the segment output inverters' pull-down or pull-up multiplied by 4, nfet hold capacitors of 1, 1.4 and 1.72 µm and a 1 µm pfet hold capacitor (ten variants including a plain 1 µm rerun): segment-gate kickback at code -31 and boundaries at codes 0, ±3, ±28 and ±31 bisected to 0.01 mV at the five conditions, tabulated with the r26g / r26h references and added gate area |
| r26j | `r26j_verify.py` (with `r26i_drv.py`) | The r26i fixes (d5, H1, H1.4, H1.72, N4 H1, H1 PH1, N4 H1 PH1) under Vth-mismatch Monte Carlo (seeds 0-39 at the five conditions, each paired with `g5_k175` on the same seed; the segment-span boundaries at codes ±28, which define the loss, bisected to 0.01 mV), with the b1 bit-2 gate-net capacitance (1.22 fF to vss, s, vin, tail and x) scaled by 1 and 4 on all 14 segment gates, TT energy per decision at codes 0 and ±31, decoder leakage at the five conditions, a SKY130 design-rule footprint, and the r26b calibration Monte Carlo (seeds 0-19) for all six fixes |
**Re-running.** Live studies use the same project-local ngspice 47 and pinned
SKY130 models as the full campaign (`node scripts/setup.mjs` on Windows;
`NGSPICE_EXE` may name another ngspice 47 console). From the entry directory:

```text
python -B research/r1_trim_floor.py
python -B research/r7_trim_dnl.py
python -B research/archive_results.py research/out
```

`research/out/` and `research/cache/` are ignored scratch folders.
`archive_results.py` replaces `results/research/` and prints the new manifest
SHA256; a changed result must be pinned again in
`presentation/research_extension.py` before the Notebook will display it.
Runtimes on one laptop CPU range from seconds (r1) to several hours per Monte
Carlo or 49-condition study. The r7 trim-DNL study was re-run from the entry
folder and reproduced the archived step boundaries exactly; the other live
studies were not re-run after archiving.

**Scope.** Mismatch MC models threshold-voltage mismatch only, from the PDK's
Pelgrom term, with 40 paired seeds per variant. The fix's RC numbers reuse the
adopted b1 extraction with trim devices split into unit copies and the added
bit's wiring estimated from bit 3; the fix has no drawn or extracted layout.
In the 49-condition atlas (r13) the fix's 5-bit trim saturates at code
+/-31 in 11 conditions with width skew, so it does not qualify at 1 mV.
The r15 6-bit design (b) qualifies at 1 mV at 1 and 2 ns; r16 adds paired
mismatch MC at TT and SS without width skew, but it has no layout. r17
estimates its RC on the b1 extraction as r11 does, with bits 4 and 5 placed on
bit 3's extracted nodes and bit 3's wiring capacitance scaled by 2 and 4; at
code 0 that estimate keeps +/-1 mV correct at 2 ns but not at 1 ns. During r17
one ngspice deck stalled with no CPU use under full load; it was stopped and
the run resumed from its saved rows. r18 is a nominal TT screen only. r19
tests the r18 variant `u6_w12_l05`, chosen after that screen, with the r15
sealed protocol (same 63-code deviation), the r17 RC estimate and the r16
paired seeds; it qualifies at 1 mV at 0.75, 1 and 2 ns using codes -16 to +15,
and like the other 6-bit design it has no layout. Its RC rows halving the
latch-output wiring are a layout assumption, not an extraction. The
shared calibration routine checks `max_code <= 31`;
r15b and r19 use a local copy of `select_trim` with only that check raised to 63,
and r15 and r19 scale ngspice's wall-clock guard (15 s per point) by 4 for the
larger unit-element netlists. r16 and r19 likewise scale r3's 900 s per-deck guard by
4; two SS batches stopped on that guard under full machine load and were
restarted, and the affected seeds then completed normally. Neither change
alters a simulated result.
r20 found that the SKY130 NMOS models are binned by width (low-Vt bin edges
at 1.65, 3.0, 3.01, 5.0, 5.05 and 7.0 um), so the atlas's deterministic width
skew is not an exact current skew and its strength depends on the design's
input width and finger split. r20 and r21 replace it by an instance multiplier
`m = 1 +/- skew` with nominal geometry; that stress is not random mismatch either.
In r20, two baseline conditions (SS and FS 1.62 V -40 C) are unresolved at the
3.5 ns calibration deadline under both stresses and are left out of its ratios.
r21 reproduces the sealed validation rows exactly; the published counts also
include the sealed record's numerical refinement, which re-simulated all +/-1 mV
points of the selected design only, while r21 refines every +/-1 mV, 1 ns point
of all three designs with one 0.625 ps run (no convergence ladder), so its
width-skew counts differ from the published ones by one decision per design.
The six r21 per-condition run files (about 12 MB) are not archived.
r22 measures the trim range at 3.5 ns without skew or mismatch; its Monte Carlo
covers three hot, high-supply corner runs only and, like r3, is not a yield estimate.
r23 adds each transistor's white drain-current noise as a bias-dependent current
source (density from per-device `.noise` tables in `research/cache/r23`, about
0.6 MB each and not archived), sampled every 2 ps from 2 ns before the clock edge,
and bisects the 3.5 ns switching input per realization at trim code 0 on nominal
devices. It has no flicker or induced gate noise and does not include the noise of
switched-on trim branches at a calibrated code; in the trimmed designs the
switched-off branches are kept noiseless (checked against all-noisy runs). Its
error rates assume Gaussian noise added to the noiseless MC residual. Unpruned
6-bit decks exceed r3's 900 s guard, so r23 runs them with a 7200 s guard.
r24 measures the ISF in the r23 deck: a 2 ps triangular charge pulse of +/-20 aC
into an internal node at time tau, the switching input bisected for each sign
(about 4-6 minutes per condition with 12 workers, against about 25 minutes for a
40-realization r23 run). The test bench clocks three cycles with the input held,
so earlier decisions leave charge on the off trim branches (decision memory);
`R24_PRIOR_MV=-5` pins the two earlier cycles to a fixed input, and all r24
atlas, common-mode (`R24_CM_V`) and closed-form results use that pinned bench,
with its own r23 MC for the validation rows. The input-pair closed form is
calibrated once on the atlas; `r24_scaling.py gainlaw` adds the gain-suppression
term with one constant A0 fitted on the same 45 conditions (`gain_law.json`).
`r24_probe.py run` sets the floating trim nodes with ideal switches during the
last reset (`memory_probe.json`); `r24_probe.py qualify`, `spot` and `energy`
requalify the swap, precharge and equalize fixes (`memory_fix_*.json`,
`memory_spot_*.json`, `memory_energy_*.json`), and `r24_fixmc.py run` / `range`
rerun the r22 mismatch Monte Carlo at SF and FF 1.95 V 125 C and the r22 nominal
range with the equalizer added (`fixmc_*.jsonl`, `fixrange_*.json`). The added
devices are nominal (no mismatch, no noise in the ISF) and have no layout.
The trajectories and per-condition ISF scans are not archived;
`r24_report.json` and the r24c JSON files hold every number Section 9 uses.
r25 registers the shipped core with a 5-bit trim (`eq5_l<L>`, trim length L in
hundredths of a µm) and the r24c equalizer in process. `r25_trim5.py screen`
measures the end-point range at TT, SF and FF for L 0.5-2 µm (`screen.jsonl`),
`dnl <L>` the 63-code transfer at five conditions (`dnl_*.json`), `range <L>`
the 45 r22 conditions (`range_*.json`) and `mc <L> <corner> <V> <T>` the paired
40-seed Monte Carlo (`mc_*.jsonl`; the core and the 4b trim devices keep their
r22/r3 draw, the fifth bit draws from seed + 100000). `r25_cost.py` gives the TT
energy and memory (`memory_*.json`) and `r25_report.py` the paired comparison
(`r25_report.json`). Each MC run takes about 10 minutes with 12 workers.
r26 registers `s<bits>_k<100k>` (input W 3k, tail W 7k, trim L 1, equalizer) in
process; `r26_scale.py screen|dnl|range|mc <bits> <k>` writes the same files as
r25 under `out/r26/` (wider devices draw the r22 z scaled by the r3 Pelgrom
sigma, `r3/sigma_*.json`), `r26_cost.py` the TT energy and memory and
`r26_report.py` the paired comparison (`r26_report.json`). r26b registers
`u<bits>_k<100k>` with bit k built from 2^k unit cells (W 0.42 trim device,
W 1 switch, instance multiplier `m`); `r26b_unit.py mcheck` checks `m` against
explicit parallel copies, `weights <bits> <k>` writes the single-bit weights
of both layouts at five conditions (`weights.jsonl`), and `screen`, `dnl`,
`range` and `mc` follow r26 (bit k draws the unit sigma / sqrt(2^k)).
`r26b_cost.py <bits> <k>` gives the TT energy and memory.
r26c reruns `r26b_unit.py mc 5 1.5 <corner> <V> <T> 200` at the five DNL
conditions (TT 1.8 V 27 C, SS/FS 1.62 V -40 C, SF/FF 1.95 V 125 C; seeds 0-39
at SF/FF/TT are the r26b seeds). `r26c_refine.py 5 1.5 <corner> <V> <T> 200 [e]`
re-bisects every seed with 0.85 <= |m| <= 1.15 mV to 0.01 mV at each candidate
code, `r26c_fine.py` gives the 0.01 mV nominal steps, and `r26c_eqscale.py`
registers `e<bits>_k<100k>` (equalizer of bit k = 2^k unit devices, clkb
inverter `m` 4) with `dnl|range|mc|fine` commands (optional inverter `m` last;
`fine` and `r26c_cost.py <bits> <k> [m]` for the inverter sweep; the cost
energy file carries no inverter tag, so the m 1, 2 and 8 outputs are archived
renamed `_i<m>`). The raw
200-seed MC files (about 7 MB) are not archived; `r26c_stats.py <design> 200`
reduces them to one record per seed (`seeds_*.jsonl`, `stats_*.json`) and
`r26c_stats.py sweep` writes `inv_sweep.json`. Each 200-seed condition takes
about 30 minutes with 12 workers.
r26d runs `r26c_eqscale.py dnl|range 5 1.625` and `5 1.75`, then
`r26c_eqscale.py mc 5 1.75 <corner> <V> <T> 200` at the five conditions,
`r26c_refine.py 5 1.75 <corner> <V> <T> 200 e`, `r26c_stats.py e5_k175 200`
and `r26c_cost.py 5 1.75`. `r26d_carry.py e5_k150 e5_k175` fits the step law
on the per-seed candidates and `r26d_segment.py e5_k150 e5_k175` evaluates
the miss model; neither runs a simulation. A cold k 1.75 condition takes
about 50 minutes.
r26e runs `r26e_seg.py check 1.75` and `dnl 1.75`, then
`r26e_seg.py mc 1.75 <corner> <V> <T> 200` at the five conditions,
`r26e_seg.py refine 1.75 <corner> <V> <T> 200` (no borderline seed),
`r26c_stats.py g5_k175 200` and `r26e_cost.py 1.75`.
`r26e_carry.py e5_k175 g5_k175` and `r26e_compare.py` compare the step
classes and tails with the r26d law without simulation. Each condition takes
about 45 minutes.
r26f: `r26f_tail.py e5_k175 g5_k175` fits the step model from the archived
per-seed records without simulation. `r26f_dec.py leak` (with `R26F_L` = 0.15,
0.5 or 1), `dnl 1.75`, `kick 1.75`, `cost 1.75`, then
`r26f_dec.py mc 1.75 <corner> <V> <T> 200` at the five conditions and
`r26f_dec.py compare 200`; `r26f_kick.py <L> [H] [corner]` runs the
channel-length and hold-capacitor probes. Each 200-seed condition takes about
1.5-3 hours with 12 workers and resumes after an interruption; the raw d5 MC
files are summarized in
`compare_d5_k175.json` and not archived.
r26g: `r26g_drv.py kick` (and with `R26G_SCALE=1`), `kick d` (with
`R26F_HOLD` unset, 1, 2 or 4), `probe`, then `probe d` with `R26F_HOLD` = 1, 2
and 4, and `law`, which fits the dip law from the archived kick and probe
summaries without simulation. Each probe family takes about 40 minutes with
12 workers; the per-run `_probe_*.jsonl` logs are summarized in
`probe_drivers_*.json` and not archived.
r26h: `r26h_thev.py kick` and `probe` with `R26H_R` (Ω) / `R26H_C` (fF) set to
1000/0, 2000/0, 4000/0, 7000/0, 2000/20, 7000/10, 7000/20 and 7000/40, then
`table`, which writes `thevenin_k175.json` from the kick and probe files and
the r26g dip law without simulation. Each point takes about 5 minutes with 5
workers; the per-run `_probe_*.jsonl` logs are not archived. The state-aware
extension runs `r26h_states.py` for d5 and (with `R26F_HOLD=1`) d5 H1; per
condition (`R26H_COND`), `r26h_thev.py kick` at the fitted R_on with
`R26H_C` = 0 and 10, `r26h_states.py` at the fitted (R_on, C_on) with
`R26H_OFF=<R_off>:0` and `:10`, and `probe` for the symmetric
(`R26H_R`, `R26H_C`), state-aware (`R26H_OFF=<R_off>:<C_off>`) and H1 R_off-only /
C_off-only drivers; then `R26H_LIN=8.3 r26h_lincap.py kick` and `probe`, and
finally `r26h_states.py fit`, which re-derives every fitted value from these
files, checks it against the run tags and writes `thevenin_state_k175.json`. A
single-condition probe takes 3-4 minutes.
r26i: `r26i_drv.py run` with `R26I_MN` / `R26I_MP` (multiplier 1, 2 or 4),
`R26F_HOLD` (nfet hold capacitor, µm) and `R26I_PH` (pfet hold capacitor, µm)
for (MN, MP, HOLD, PH) = (1, 1, 1, 0), (4, 1, 1, 0), (1, 4, 1, 0), (1, 1, 1, 1),
(4, 1, 1, 1), (4, 1, 0, 0), (1, 1, 1.4, 0) and (1, 1, 1.72, 0), then `table`,
which checks the plain rerun against r26g and writes `fixes_k175.json`. Each
variant takes about 20 minutes with 3 workers (five variants ran side by side).
r26j: with the same `R26I_MN` / `R26I_MP` / `R26F_HOLD` / `R26I_PH` settings for
the seven designs (and `R26J_REF=1` for the `g5_k175` reference), `r26j_verify.py
mcloss 40`, `para` and `energy`; `mcflow 20` for the six fixes; then `table`,
which pairs every design with the reference seed by seed and writes
`verify_k175.json`. The loss Monte Carlo takes about 4 hours per design with 2
workers, and the calibration Monte Carlo about 1.5 hours per condition with 6.
None of these studies is silicon, Linux, Colab or external-human evidence.