# ISSCC 2027 Code-a-Chip submission checklist

Official IEEE SSCS program page:
https://sscs.ieee.org/membership/awards/ieee-sscs-code-a-chip-travel-grant-awards/

Official Code-a-Chip repository:
https://github.com/sscs-ose/sscs-ose-code-a-chip.github.io

Verified on 2026-09-28.

## Submission package

- [x] Project is openly licensed (Apache-2.0).
- [x] Jupyter notebook exists in `ISSCC27/submitted_notebooks/ptat_temp_sensor/`.
- [x] Notebook explains idea, design decisions, methodology, results, limitations, and reproducibility.
- [x] Notebook identifies the GitHub submission contact.
- [x] Notebook names the team member/submission representative at the top, per upstream guidance.
- [x] Notebook records the retained ngspice and SKY130/open_pdks versions.
- [x] Notebook includes explicit references.
- [x] Notebook cells have stable unique IDs and execute in CI without nbformat ID warnings.
- [x] Real SKY130 transistor-level evidence is retained with provenance.
- [x] Evidence-integrity audit fails closed.
- [x] Digital calibration result is reproducible.
- [x] Readout/ADC quantization budget is reproducible.
- [x] Final calibration architecture is explicitly defined as five-point PWL.
- [x] Two-point target miss is disclosed rather than hidden.
- [x] Submission preflight and unit tests run in GitHub Actions.
- [x] New dense-grid transistor simulation completed and retained: 5 °C TT/FF/SS grid, worst five-point PWL error 0.472 °C, target PASS.
- [x] Real PDK local-mismatch Monte Carlo completed and retained: the original baseline 100-seed design fails the internal statistical targets (66% error yield, 4% branch-mismatch yield); the negative result is preserved as historical evidence.
- [x] Retrospective two-fold calibration robustness study retained: both 50-seed folds independently select the same six-point schedule; opposite-fold error yield is 49/50 (98%) in each direction. This remains historical evidence and is not treated as the final independent qualification.
- [x] Frozen candidate `i5_m16_l4_s8` retained with disjoint 100-seed validation (2000001–2000100): 100% temperature-error yield at ≤0.5 °C and 100% branch-mismatch yield at ≤1%.
- [x] Frozen candidate passes dense TT/FF/SS verification: worst five-point PWL error 0.381358 °C and worst deterministic mirror mismatch 0.395267%.
- [x] Frozen candidate passes the behavioral 12-bit / 1.8-V / gain-10 readout check: worst quantized sampled error 0.462754 °C.
- [x] `results/long_mirror_candidate/qualification.json` reports `QUALIFIED_FOR_RELEASE_REVIEW`; release architecture remains unchanged pending an explicit review decision.
- [ ] Layout/DRC/LVS/PEX: optional for Code-a-Chip and not currently claimed.
- [x] User fork of `sscs-ose/sscs-ose-code-a-chip.github.io` created and used for the submission branch.
- [x] PR changes are limited to `ISSCC27/submitted_notebooks/ptat_temp_sensor/`; no upstream `.github/` workflow files are modified.
- [x] Final pull request opened to the official Code-a-Chip repository: PR #197.
- [ ] Upstream notebook/lint workflows require maintainer approval before jobs execute; monitor CI and reviewer feedback after approval.

## Deadline discrepancy

The two current official sources disagree:

- the **official Code-a-Chip GitHub README** states **October 9, 2026, 11:59 AM Pacific Time**;
- the **IEEE SSCS award page** states **October 31, 2026, 11:59 AM Pacific Time**.

Until the organizers reconcile the dates, use **October 9, 2026, 11:59 AM Pacific Time** as the conservative internal submission-by deadline.

## Local gate

Run:

    make submission-preflight

The gate verifies notebook structure, retained evidence integrity, retained
calibration, and the behavioral readout budget.
