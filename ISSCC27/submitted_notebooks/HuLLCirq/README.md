# HuLLCirq

**Human–local-LLM collaborative circuit design with an English GUI, independent verification and source-bound evidence.**

ISSCC 2027 Code-a-Chip **final review edition**. Use this editable folder for the final submission; the earlier ZIP is a superseded snapshot.

**Author and attending representative:** Ryotaro Kawashima  
**Affiliation:** Department of Biomedical Engineering, Graduate School of Biomedical Engineering, Tohoku University

## Start here

- Open [HuLLCirq.html](HuLLCirq.html) for a readable, static review copy, or edit [HuLLCirq.ipynb](HuLLCirq.ipynb). The notebook now contains the eleven-block architecture, original matrices and independent arithmetic, measured waveforms, and exact saved-source replay results.
- Follow the [five-minute final submission checklist](docs/final_submission_checklist.md). A [PR title](submission/PR_TITLE.txt) and [PR description](submission/PR_DESCRIPTION.md) are prepared for the submitter.
- Follow the [submission and reproduction guide](docs/submission_guide.md) to inspect the saved evidence or prepare a fresh execution environment.
- Use the [evidence index](submission/evidence_index.json) to locate the selected designs, original specifications, independent expectations, retained generation/repair histories and physical results.
- The original work is licensed under [Apache-2.0](LICENSE). Third-party tools, PDKs and models retain their own terms; their binaries and weights are not bundled.

## What HuLLCirq does

A person describes the blocks, external terminals, connections, behavior and constraints of a synchronous digital circuit. A local language model proposes node RTL and integration RTL. Ordinary software freezes inputs and independent expectations, checks source freshness, manages execution and preserves history. Open-source EDA tools produce the actual synthesis, simulation and physical-verification evidence.

| Stages | GUI operation and evidence |
| --- | --- |
| S01–S03 | Save the graph, distinguish external terminals from missing connections, validate the specification and freeze the circuit contract |
| S04–S07 | Generate or repair node RTL, synthesize, simulate the adopted node netlist and derive evidence-backed implementation specifications |
| S08–S10 | Generate integration RTL, synthesize the complete circuit and simulate the adopted global netlist against the same frozen job |
| S11–S14 | Place and route, run DRC and LVS, then check routed-netlist function and extracted static timing |

The GUI includes S06/S10/S14 waveform inspection, generated-file selection, source and change-history inspection, explicit retry/recovery actions and source-bound Functional Maps. Shared definitions can expand into multiple PE instances. The chosen placement mode is **mixed standard-cell placement**; experimental block-region attempts are retained as history. A Functional Map is an evidence-qualified role overlay on the saved placement, not a separate placement algorithm or a proof of exclusive RTL ownership.

## Demonstrated circuits

| Example | Preserved contract | Recorded result |
| --- | --- | --- |
| Main NPU: explicit 2×2 parallel MAC | Eleven nodes, four explicit PEs; original K=3 matrix job, ReLU disabled; expected outputs `[-44, 56, 59, 9]`; 50 ns clock | S01–S14 completed and adopted. The final source-bound layout has 33,681 placed-cell footprints. All seven S14 checks passed with zero mandatory violations across nine STA corners. |
| P1 Counter | Synchronous active-high reset; original 14 cycles and 42 output comparisons; 50 ns clock | A new full GUI S01–S14 flow completed on 2026-10-31. S06, S10 and S14 each show 42 comparisons, zero mismatches and zero missing observations. Magic/KLayout DRC: zero violations. Corrected, source-bound LVS: zero feedback and Unique match. |
| P2 FIFO → XOR | Independent saved non-NPU, multiple-block contract | The saved positive GUI flow completed S01–S14. Earlier failures, repair guidance and their provenance remain in the evidence history. |
| P3 shared 2×2 signed saturating lanes | One shared definition instantiated four times; original 24 cycles and 288 expected outputs | The saved positive GUI flow completed S01–S14. Its later Functional Map retains the same 725 footprints and labels 33 cells per member as checked inference; it does not assert exclusive ownership. |

The NPU and the generic P1/P2/P3 cases are separate designs and execution chains. Results are never transferred between them. The NPU's retained non-overlap LVS extraction feedback is not erased by P1's later warning-free correction.

## Meaning of a pass

S14 uses **routed-netlist functional simulation plus extracted nine-corner static timing analysis**, recorded as `post_route_functional_plus_sta`. It is **not dynamic SDF simulation**, formal equivalence or foundry/tapeout qualification. Functional comparisons are finite checks of the saved input job. A green result proves only the corresponding required checks on its exact retained source.

All demonstrations record development-assistant GUI operation and explicit repair guidance. Some later cases used concrete code guidance in the model instruction. These are not claims of autonomous first-attempt model success or independent human usability evaluation. User-authorized automatic adoption and development-assistant reviews are distinguished from human acceptance.

## Exact-source replay added for this submission

The [saved-RTL guide](docs/saved_rtl_replay.md) provides concrete commands for
`submission/reproduction/p1_counter/`. The adopted Counter RTL and S10 generic
netlist reuse the **unchanged original** testbench, fourteen cycles, forty-two
expected outputs and 50 ns clock. Both builds were actually compiled and
simulated with Icarus 12.0: **42/42 comparisons, zero mismatches and zero missing
samples each**. Five successful native commands cover version/compile/simulate.
No LLM regeneration, new synthesis, physical run or historical adoption change
was performed. [New replay results](submission/reproduction/p1_counter/verification-result.json)
are separate from the historical GUI/native counts below.

`python scripts/render_submission_figures.py --check` reparses the original
specification and VCDs and verifies the derived architecture, arithmetic and
three timing diagrams. `python scripts/verify_submission.py` checks all files.

## Verification snapshot

The latest local closure comprises **113 GUI scenarios**, including 48 continuation scenarios, and **one new P1 complete S01–S14 flow**. It is not 113 full circuit flows. The continuation records eight production intervention packages, I13–I20, with action, result, problem, cause and timestamp.

At the I19/Q6 source snapshot, the software suite recorded 3,077 executed tests, zero failures/errors and 36 skip records. I20 subsequently changed browser-state projection and passed a separate 56-test selection plus fresh actual-GUI reload checks showing 14/14. A new full suite was not run after I20. The latest P1 execution retained six local-model requests (9,244 provider-reported tokens) and 37 executed outer native commands, all exit zero. These counts exclude Codex usage and isolated software-fixture processes.

Independent clean-PC installation, a genuine human usability evaluation, maximum-scale native circuits and the condition-dependent repeated electrical-only generic-v2 branch remain outside the qualified actual-GUI scope. Dynamic SDF, analog circuits, CDC qualification, arbitrary PDKs and formal equivalence are unsupported by this result.

## Reproduction and preservation

The notebook's Python cells calculate the independent NPU reference and validate saved VCDs, figures and evidence. They do not start a server, model, compiler, simulator or EDA flow. Reading the submitted evidence is distinct from replaying retained RTL with installed tools, and both differ from asking the LLM to generate new RTL; identical new model answers are not guaranteed.

Use the [reproduction guide](docs/submission_guide.md) for environment versions, acquisition and launch steps, artifact integrity checks and the boundary between original evidence and public privacy-redacted derivatives. Original data, specifications, expectations and successful/failed histories are preserved privately. Public derivatives must retain their declared transformation and provenance; they must not be presented as byte-identical originals.

HuLLCirq is a provisional name; trademark clearance has not been established. No learning benefit, performance advantage or comparative superiority has been measured.
