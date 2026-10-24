# Clean-start schematic / extracted-RC reproduction

This entrypoint starts with a **fresh output directory and empty attempt
ledger**. It needs no historical checkpoint, prior raw archive or private
continuation records. It reproduces the fixed nominal 27-device comparator,
not layout generation or a new circuit.

**Validation performed:** the fresh four-transient smoke passed, including
actual runtime/SI/reset checks, both 10/5 ps numerical pairs and all four
same-point reference comparisons. Finest TT -10 mV results are
**0.226010 ns / 240.686 fJ schematic** and **0.537443 ns / 417.751 fJ RC**.
The independent supervisor completed in 35.967 seconds with all owned
processes stopped. Exact receipts and raw NPZ/decks are in
`evidence\smoke-v1`. **A fresh full-matrix rerun was not performed.**

Running without an explicit mode shows help and starts **no simulation**:

```powershell
& $Python -B .\pvt45_reproduce\reproduce.py
```

## Free existing requirements

Use native Windows x64, Python **3.12.10**, NumPy **2.2.6**, ngspice **47**
console and the unmodified SKY130 model revision
`f62031a1be9aefe902d6d54cddd6f59b57627436`.
The exact free binary/DLL/PYD/startup identities are in the small source
closure's `layout_pvt45_windows\evidence\runtime-pins.json`.
The previously provided entry setup can supply these components. This
reproducer does not install or download anything.

Models are caller-supplied and read-only. All 399 model files plus license
must match `layout_pvt45_windows\evidence\model-raw-sha256.json`: both the
tested Windows raw-byte hashes and canonical pinned Git content are checked.
337 files including the license have CRLF-only checkout differences from
their Git blobs; an arbitrary LF checkout does **not** satisfy the exact
Windows raw identity. The reproducer copies matching bytes into its own
`model-source` snapshot and never rewrites the user's PDK.

Preserve the entry-relative paths listed in `source-pins.json`. The small
closure reuses unchanged pure deck, waveform, measurement, SI-geometry,
collector and numerical helpers, plus the tested Windows Job Object
supervisor and bounded single-writer rename helper. Their historical
checkpoint controllers and private archives are **not** dependencies.

## Four-transient smoke

From the entry directory, supply your own existing tool/model locations:

```powershell
$Python = (Resolve-Path $env:ATLAS_PYTHON_EXE).Path
$Ngspice = (Resolve-Path $env:ATLAS_NGSPICE_EXE).Path
$Models = (Resolve-Path $env:ATLAS_MODELS).Path
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:OMP_NUM_THREADS = '1'
$env:OPENBLAS_NUM_THREADS = '1'
$env:MKL_NUM_THREADS = '1'
& $Python -B .\pvt45_reproduce\reproduce.py --smoke `
  --ngspice $Ngspice --models $Models --out $env:ATLAS_FRESH_SMOKE_OUT
```

`--smoke` runs **four transients maximum**: fresh schematic and RC at
TT, 1.8 V, 27 C, -10 mV, each at 10 ps and 5 ps. The first scheduled
schematic trace runs serially and must prove one thread, HSA compatibility,
all 27 inner-MOS SI dimensions, reset and waveform integrity before the
two-process pool is enabled. No uncounted smoke, parse run or automatic
retry is performed.

The two numerical pairs must meet the unchanged 1% energy / 20 ps latency /
identical-decision criteria at both 1 ns and 2 ns. Each trace is also
compared with the already-recorded same-mode/point/timestep reference in
`smoke-reference.json`, using those tolerances rather than exact floating
point equality. This is a new code-reproduction validation identity; it
does not add PVT coverage to or change the original 720-transient study.

## Explicit full plan

```powershell
& $Python -B .\pvt45_reproduce\reproduce.py --full `
  --ngspice $Ngspice --models $Models --out $env:ATLAS_FRESH_FULL_OUT
```

`--full` requires a different, nonexistent owned output directory. It
declares exactly 45 PVT conditions, four signed inputs (-10, -3, +3, +10 mV)
and two modes: **180 schematic and 180 RC points**. All 720 initial
10/5 ps transients precede at most 180 sensitive refinements, with a
900-charged-attempt cap. The original monotone finer-step ladder and
two-consecutive-passing-halving rule remain unchanged. Missing, interrupted
or unconfirmed observations remain unknown, not pass.

The entire execution, including model/source checks, review, checkpoint I/O
and child processes, is inside the independent 30-minute Windows Job Object
watchdog. Two workers each use one ngspice thread. A time limit or global
integrity failure stops execution and retains evidence; no restart or
checkpoint-resume mode is offered. Functional wrong/unresolved points do
not abort the remaining declared matrix.

The full plan and all permitted decks are checked statically against the
frozen study. **A new full-matrix rerun is not part of this entrypoint's
four-transient validation.** Do not describe synthetic plan tests or a
successful smoke as an executed fresh 45-PVT rerun.

## Unchanged circuit and output

Both modes use nominal matched devices (`pair_skew=0`), code zero, VCM =
0.5 VDD, 5 fF per output, a 10 ns clock with 50 ps edges, complementary
80%/20% rails and the 20-30 ns core-energy cycle. The prospective primary
deadline is **2 ns**, with the original **1 ns** results kept separately.
No geometry, passive network, model flavor or testbench parameter is tuned.
There is no 3.5 ns, mismatch/noise/yield or ngspice-42 equivalence claim.

The output retains pre-data source/runtime/model/deck hashes, fresh charged
ledger, exact SPICE decks and `.spiceinit`, raw logs/TSV/NPZ, actual geometry
tables, numerical histories, reference comparisons, finest CSV/JSON and
supervisor result. Executed model includes are relative; input tool/model
paths are not written into the ordinary point identities or decks.
If an exception includes a private path, its exact raw diagnostic is kept
as `private-error.txt` and is not suitable for unreviewed publication.

`result.json` is the final smoke/full result only after the independent
owner reports that all owned processes stopped within the time limit.
Historic DRC/LVS qualification is provenance of the fixed RC netlist;
this entrypoint does not claim a fresh DRC, extraction or silicon result.
