# Full-PDK verification evidence — 2026-09-26

This directory retains compact, reviewable evidence from GitHub Actions workflow run `36256551286`, job `108444305769`, generated from commit `54e8b2d46ec2ca3950c944390870cba29656594c`.

The source artifact was `isscc27-full-pdk-verification` (artifact ID `10910494009`); its ZIP SHA-256 recorded by GitHub Actions was `48987112cb7a7678d5b8cc0d279fa2ee4e4c51dd69fadcf34dcce85cbc77c3d9`.

## Dense deterministic verification

- SKY130/open_pdks: `12df12e2e74145e31c5a13de02f9a1e176b56e67`
- ngspice: 46
- corners: TT / FF / SS
- grid: -40 to 125 °C in 5 °C steps
- fixed five-point PWL anchors: -40, -20, 0, 50, 125 °C
- worst five-point sampled-grid error: 0.471568222498 °C
- result: PASS against the 0.5 °C dense-grid target

`dense_pdk_analysis.json` preserves the dense analysis and provenance. The six raw dense CSVs remain in the identified source artifact and are reproducible with `run_sky130.py`.

## Local-mismatch Monte Carlo

- model section: `tt_mm`
- samples: 100 independent seeds (1001-1100)
- grid: -40 to 125 °C in 5 °C steps
- per-sample five-point PWL calibration at the release anchors
- error-yield at <=0.5 °C: 66.0%
- error-yield target: 95.0%
- worst max-absolute error: 1.123970249808 °C
- p95 max-absolute error: 0.961747505276 °C
- ΔVGS standard deviation at 25 °C: 0.011776611629 V
- branch-mismatch yield at <=1%: 4.0%
- result: FAIL against the internal statistical targets

The failure is retained deliberately. It is real simulation evidence and is not converted into a passing claim.

`mismatch_metrics.csv` preserves one derived-metric row for every seed and `mismatch_summary.json` preserves aggregate metrics and provenance. The 3,400 raw temperature rows remain in the identified source artifact and are reproducible with `mismatch_mc.py`.

## Calibration-improvement study

On this discovery dataset, a six-point schedule `[-40, -25, -5, 25, 65, 125] °C` improves the <=0.5 °C error yield from 66% to 98.0%. This is **not a release claim** because the anchors were selected using these same 100 samples. Promotion requires a new independent-seed PDK Monte Carlo run.

No silicon, layout, DRC, LVS, or PEX claim is implied by these files.
