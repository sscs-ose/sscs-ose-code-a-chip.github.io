# Final five-minute review and submission

The current official deadline is **2026-11-01 03:59 Japan Standard Time (JST)**,
equivalent to **2026-10-31 11:59 AM Pacific Daylight Time**. Finish the review and
the actual official pull-request submission before that time. The deadline is
early Sunday morning in Japan.

Source: [the official ISSCC 2027 Code-a-Chip README](https://github.com/sscs-ose/sscs-ose-code-a-chip.github.io/blob/main/README.md).
The separate How to Apply page retains an older ISSCC26 directory reference;
use the current ISSCC27 README for this submission's destination and schedule.

## 1. Confirm the identity and claims

- Open [HuLLCirq.html](../HuLLCirq.html) directly in a browser for the readable final review. No server or tool installation is needed. Edit [HuLLCirq.ipynb](../HuLLCirq.ipynb) if a change is required.
- Confirm the author and attending representative are **Ryotaro Kawashima** and
  the affiliation is **Department of Biomedical Engineering, Graduate School of
  Biomedical Engineering, Tohoku University**.
- Inspect the worked circuit example, independent expected-value calculation,
  saved waveform figures and reproduction instructions. Check that they express
  the intended project and that the stated limitations remain visible.
- S14 is routed-netlist functional simulation plus extracted static timing
  analysis. It is not dynamic SDF qualification, formal equivalence or foundry
  signoff. Historical NPU extraction feedback remains separate from P1's later
  warning-free correction.

## 2. Confirm the selected files

- Use the complete reviewed **HuLLCirq** folder as the project payload at
  `ISSCC27/submitted_notebooks/HuLLCirq/` in the public fork.
- Check the [project README](../README.md), [license](../LICENSE),
  [third-party notices](third_party_submission.md) and
  [evidence index](../submission/evidence_index.json) are present.
- Keep the included `.gitattributes`: it preserves exact evidence and manifest bytes across Git newline conversion on Windows.
- Keep the public destination's project folder aligned with this selected file
  list. Do not carry over old uncurated files that are absent from this payload.
- Keep private work directories, unredacted originals, private transfer archives,
  machine settings, tools, PDK installations, model weights and the withheld
  standalone AI artwork outside the public submission.

## 3. Verify the final reviewed version

From the reviewed HuLLCirq folder, use Python 3.12 to run:

```text
python scripts/verify_submission.py
```

This checks the packaged file list and hashes without running a model or EDA.
An intentional edit after the final integrity pass changes the reviewed version;
refresh its manifest and perform the limited checks relevant to that edit before
submitting. A saved ZIP is a fixed snapshot and does not receive folder edits.

## 4. Submit and check the actual pull request

- Inspect the final difference: every submitted change must stay within
  `ISSCC27/submitted_notebooks/HuLLCirq/`.
- Use the prepared [PR title](../submission/PR_TITLE.txt) and [PR description](../submission/PR_DESCRIPTION.md).
- Publish the reviewed version to the submitter's public fork and create the
  pull request to the official repository before the deadline.
- Check the pull-request page shows the intended target repository, project
  directory, notebook, license and supporting files. Save its actual URL.
- Do not treat a local folder, ZIP, draft text or prepared branch as proof of
  submission. The submitter performs the final public push and official PR.

No public fork push, official pull request or external publication is performed
by this checklist. The project preparation records distinguish completed local
checks from the final submission action.

If selected for an award, the representative must attend ISSCC 2027 in person
and present the project poster under the official program conditions. This is a
later award condition, rather than an additional file to fabricate before this
submission.

## Display-check boundary

All four derived figures were rasterized and visually inspected. The notebook's seven read-only cells were executed in order, and the static HTML image/link references were checked. Desktop browser observation was denied by the automation session's Windows access permissions; the final human visual review remains necessary. No browser or operating-system security setting was changed to bypass that boundary.
