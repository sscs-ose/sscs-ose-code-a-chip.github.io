# FoldAgent: Agent-Assisted Logic Folding with Automated Verification

FoldAgent submission package v10 · documentation cleanup · 31 October 2026  
Zhanchen Zhao, Wenyu Sun, Yaqing Lai, Yubo Deng  
Tsinghua University (all authors)

Start with the **[English notebook](FoldAgent.ipynb)** or the **[illustrated English manuscript](FoldAgent.html)**. The English notebook is the primary submission. Optional Chinese reading: [full translation](FoldAgent-zh.html) and [figure guide](REVIEW_zh.md).

FoldAgent connects agent-assisted RTL partitioning to automated verification and documented physical feedback. The notebook leads with one tradeoff: a fixed 1 mm² projected footprint plus a second logic tier preserves measured throughput across 162 paired scenarios, at the cost of 725 functional cross-tier links and a same-cycle round trip. A predict–run–explain exercise separates interface capacity, compute resources and throughput evidence.

## Read and check saved results

Open the HTML directly. For the notebook, use Python 3.12 with the versions in requirements.txt. From this directory:

```sh
python review.py
python -m unittest test_review.py
python reproduction/reproduce_performance.py
```

These commands check saved records and exact reproduction inputs. Default notebook execution redraws the figures and runs the analytical connection-budget example. It performs no chip simulations.

To execute the notebook in an independent package copy and export the same-source HTML:

```sh
python tools/validate_delivery.py
```

## Independently regenerate throughput

The package includes the single-tier reference RTL, the accepted two-tier RTL, the original checker and measurement source, fixed request/response schedules, and arithmetic vectors.

With Icarus Verilog installed, explicitly run:

```sh
python reproduction/reproduce_performance.py --run build/paired-reproduction
```

Use a new output directory. This runs 162 scenarios for each design and checks regenerated metrics against the archived records. See [measurement definitions and dependencies](reproduction/README.md). In v4, both 162-case runs were executed in a fresh package extraction and Python environment. Every measured counter matches the archived report. Complete logs, receipts and comparisons are in portability/.

## Joint timing

The [physical analysis guide](physical/README.md) lists included final netlists, SDCs, SPEFs, original scripts and portable scripts. Exact library identity is recorded; the reader supplies that library and the recorded OpenSTA version. In v4, all three portable timing scripts were executed and reproduced the archived results, including byte-identical full electrical reports. Place-and-route was retained from the frozen experiment.

## Files and authoring

- design/: accepted two-tier RTL, specification and original functional checker.
- reproduction/: single-tier RTL and portable throughput measurement entry.
- physical/: joint timing inputs, scripts and routing-tool patch evidence.
- data/, evidence/, figures/: recorded data, source evidence, PNG/SVG figures.
- sources.json: exact source identities; package-manifest.json: delivered file hashes.
- validation.json: fresh-copy notebook validation.
- tools/build_notebook.py: the sole manuscript source.
- tools/validate_delivery.py: execution and HTML export.

Update the manuscript source before regenerating the notebook. The package retains original archival identifiers in code and reports; the manuscript uses functional tier names.

Project materials use [Apache-2.0](LICENSE), with [directory-specific scope and third-party exceptions](LICENSE-SCOPE.md). OpenROAD patches retain BSD-3-Clause. The authorization and conference representative are recorded in [publication status](PUBLICATION-REVIEW.md).

Fixed public dependency sources and build instructions: [DEPENDENCIES](DEPENDENCIES.md).

## Validation scope

The [portability result](portability/result.json) records 324 RTL simulations and three joint STA runs in an independent extraction on the same host, using recorded installed tools. Logs and receipts are included; public dependency downloads and fixed builds are documented in DEPENDENCIES.md. Rebuilding tools on another operating system remains a separate check.

Conference representative: Zhanchen Zhao, confirmed by the author. Public release under the documented license scheme was confirmed on 31 October 2026; [third-party notices](THIRD-PARTY-NOTICES.md) retain upstream attribution.

## Saved GDS and placement views

Figure 2 now shows both final GDS layouts with equal-scale full-die views and two coordinate-bound closeups. The control-tier GDS is reused; the compute-tier GDS is a format export of the frozen final DEF. See [GDS files and records](physical/gds/README.md). This v10 documentation cleanup preserves the v9 notebook, both HTML copies, all v4 performance/timing results and v5 GDS artifacts/images byte for byte. Open the [simplified placement overview](figures/02-placement.png) for component and terminal positions, alongside the routed geometry in Figure 2.

## Release status

Public redistribution is authorized. The root LICENSE, NOTICE, LICENSE-SCOPE.md and patch-directory license apply the approved scheme. [PUBLICATION-AUTHORIZATION.json](PUBLICATION-AUTHORIZATION.json) records the author's confirmation. Historical experiment reports retain their original dates and status fields; current release status is recorded here.

All four authors are affiliated with Tsinghua University. The project was submitted by zhaozc21 through [official PR #237](https://github.com/sscs-ose/sscs-ose-code-a-chip.github.io/pull/237).

## Submission

The submission is under ISSCC27/submitted_notebooks/FoldAgent/ in [PR #237](https://github.com/sscs-ose/sscs-ose-code-a-chip.github.io/pull/237), targeting the official repository's main branch. See [submission details](SUBMISSION.md) for the required files and deadline. Original project names in source records preserve provenance.

## Agent evidence and upload scope

Follow the [saved agent inputs, frozen briefs and delivered RTL](evidence/agent/README.md). The historical model configuration is recorded alongside the attempt; generation replay requires the original runtime and full assembled prompts. The packaged rerun paths cover verification, performance and timing.

Upload the clean project directory extracted from the submission ZIP. Its exact contents are the entries in package-manifest.json plus that manifest. Notebook validation may create validation/ work copies, runtime caches and browser previews; keep them in the authoring workspace. Retained validation.json and validation-tests.log record the v9 notebook execution and tests; revision-validation.json records this documentation cleanup's link, manifest and unchanged-file checks. Printed HTML retains the design-exercise explanations; expandable code/output listings are hidden in print.
