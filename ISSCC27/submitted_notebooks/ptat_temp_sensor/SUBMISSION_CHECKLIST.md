# ISSCC 2027 Code-a-Chip submission checklist

Official IEEE SSCS program page:
https://sscs.ieee.org/membership/awards/ieee-sscs-code-a-chip-travel-grant-awards/

Official Code-a-Chip repository:
https://github.com/sscs-ose/sscs-ose-code-a-chip.github.io

Verified on 2026-09-26.

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
- [x] Real PDK local-mismatch Monte Carlo completed and retained: 100 seeds; current five-point release design FAILS internal statistical targets (66% error yield, 4% branch-mismatch yield).
- [x] Retrospective two-fold calibration robustness study retained: both 50-seed folds independently select the same six-point schedule; opposite-fold error yield is 49/50 (98%) in each direction. This is not promoted as an independent Monte-Carlo confirmation and does not erase the branch-mismatch failure.
- [ ] Layout/DRC/LVS/PEX: optional for Code-a-Chip and not currently claimed.
- [ ] Create/fetch the user fork of `sscs-ose/sscs-ose-code-a-chip.github.io`.
- [ ] Copy/update only this project directory in the competition fork; do not copy this repository's `.github/` workflows into the upstream competition PR.
- [ ] Open the final pull request to the official Code-a-Chip repository and monitor reviewer feedback.

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
