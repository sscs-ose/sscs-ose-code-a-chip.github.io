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

### Archived RC model applicability

**Archived RC-deck outcomes; model physical fidelity not yet qualified.**
This limitation applies to both the original five-condition ngspice-42 pilot
and the subsequent separately declared 45-condition ngspice-47 study.
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
records these native values. The full-grid study reuses this same RC netlist,
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
