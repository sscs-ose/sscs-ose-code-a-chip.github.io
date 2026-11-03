# Trust Before Pass

**秦睿遥 · Fudan University · [QuRYous111](https://github.com/QuRYous111)**

An evidence-driven, seven-act investigation of power-on-reset verification for
IEEE SSCS Code-a-Chip ISSCC 2027. Decide what a waveform establishes before
trusting a reported delay. A simulation can finish while a delay is undefined;
that same record can still fail an explicitly declared functional requirement.

## Read and run

- **Notebook:** [Trust_Before_Pass.ipynb](Trust_Before_Pass.ipynb), with saved real-data outputs and seven acts. GitHub renders the notebook without installation.
- **No-code investigation:** download/extract this project folder and open [START_HERE.html](START_HERE.html), then follow the labelled controls. GitHub's file preview does not run interactive HTML. [STATIC_WORKBOOK.html](STATIC_WORKBOOK.html) works without scripts.
- **Python replay:** from this directory, install `requirements.txt` in a virtual environment, then run `python validate_notebook.py`. This executes the notebook and 34 tests. See [REPRODUCIBILITY.md](REPRODUCIBILITY.md) for versions, the Windows hash-locked path and optional SPICE/CACE runs. No EDA installation is needed for the default replay.
- **Chinese learning guide:** [TRIAL_GUIDE.html](TRIAL_GUIDE.html); optional written notes in [FEEDBACK_FORM.txt](FEEDBACK_FORM.txt).

The four browser tasks cover observation windows, controlled dependency comparisons,
measurement rules and a held-out slow-supply challenge. Predictions and explanations
precede feedback; TXT/JSON exports retain attempts. Notes stay only in page memory
until exported. Free text is not automatically graded.

## Evidence and contribution

The controls reassess 51 finite choices using Python-precomputed checks of real
archived SPICE data. They do not simulate unsampled conditions. The reusable
Python checker separates measurement validity, scalar limits and a functional
contract. Existing CACE postprocessing hooks are reused; see [CACE_INTEGRATION.md](CACE_INTEGRATION.md).

T1 is a teaching assumption, not the original designer's established specification.
The known upstream HVL correction belongs to its original authors. Investigation
is manual and controlled, not automatic diagnosis. A simple Python baseline agrees
on supported records. The contribution is explicit evidence, reproducibility and
teaching structure, not a new circuit fix or higher fault-detection accuracy.

## Validation and limits

See [SUBMISSION_VALIDATION.json](SUBMISSION_VALIDATION.json) for the submission
copy's execution record. v0.5 browser checks and historical full CACE runs remain
separately labelled; no fresh browser or SPICE run is implied by notebook replay.
Tests use the existing isolated, hash-locked Windows environment in a separate
directory, not a new OS or an independent reproduction. Direct file opening,
cross-browser access and learner outcomes have not been independently evaluated.

Independent human readers: **zero**. Author self-testing is not counted as
independent evidence; no completed author study is asserted. Reader materials are
available for future evaluation. Lack of reader evidence is disclosed, rather than
treated as an official competition eligibility rule. One circuit and limited
conditions; no full-pulse, brownout, broad-PVT or silicon validation claim.

Apache-2.0. [NOTICE](NOTICE) identifies reused circuits, models, upstream fixes
and AI assistance. The recorded v0.5 validation files are historical snapshots;
[SUBMISSION_STATUS.md](SUBMISSION_STATUS.md) describes this submission revision.
