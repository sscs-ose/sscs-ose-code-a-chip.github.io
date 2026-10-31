# Frozen CPU/NPU verification

From a fresh checkout with the same immutable `.nebula_inputs` resources:

```sh
bash verification/run_regression.sh
python3 -B verification/analyze_results.py
python3 -B verification/write_report.py
```

The runner sources both required environment scripts in the launch shell, checks
Verilator 5.048, creates an identical candidate view and keeps fixed checker hashes
unchanged. `sitecustomize.py` is active only when `NEBULA_VERIFY_CAPTURE` is set.
It preserves temporary results, caches identical builds, adds source coverage and
passive full-memory dumps. Enabled fixtures replace only the DUT instance parameter;
the original fixed file is unchanged. Checkers, corpus, seeds and expectations are
read from the authorized resource, never regenerated.

The consolidated suite contains both core configurations, enabled-top workloads,
custom decode/precise exception/reset checks and standalone NPU acceptance. The
additional observers verify actual stage/RF alignment and the cancellation boundaries
required by the frozen plan. Full memory comparisons use independent oracle store
effects, with tohost treated as external MMIO. Functional bins are instruction
families, branch outcomes and legal memory lanes, separately from test counts.

Existing output directories are rejected so earlier results remain reviewable.
The captured run includes two infrastructure corrections and their affected replays;
the final report retains the original invalid outcomes. Generated objects remain
under ignored `build/verify` and `build/perf`; direct evidence is archived in reports.

For the captured operator-publication feedback, reuse the retained evidence:

```sh
python3 -B tests/test_delivery.py
python3 -B verification/write_report.py --refresh-delivery
```

This checks the actual immutable root contract and all published content hashes,
compares DUT bytes with the formal selected integration and prior run binding,
and validates the prior evidence manifest and fixed resources. It preserves the
prior delivery failure, updates only AC-DELIVERY and its report dependents, and
does not rerun simulations. The original integration omission remains recorded.

This stage does not certify evaluator release, development resource accounting,
mapped structure, physical implementation or GDS. Stage PASS leaves those
project obligations deferred.

The delivery checker selects the Task-designated frozen artifacts by ID, even when
historical artifacts of the same type are captured. Its regression accepts the
complete publication and rejects missing files, wrong types, altered bytes, and
source/companion/manifest/DUT binding mismatches using temporary fixtures only.
Checker test counts are separate from DUT scenarios and code coverage.

For a new frozen physical baseline with unchanged RTL, run:

```sh
python3 -B verification/revalidate_baseline.py
```

This reads the Task's selected input IDs, compares every original evidence hash,
DUT/spec/checker/configuration byte binding, and integration lock changes. It
archives the previous report, replays delivery checks, compiles the existing
enabled-top smoke once with a VCD wrapper, and measures the external reset epoch.
`tests/test_reset_waveform.py` checks positive and negative waveform fixtures.
After a checker-only correction, `--resume-analysis` reuses that completed build
and waveform; it does not compile or simulate again. Build directories are
rejected on a fresh run to preserve evidence. Physical acceptance stays deferred.
