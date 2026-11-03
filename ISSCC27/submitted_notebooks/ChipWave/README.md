# ChipWave: A Configurable Platform for AI-Driven Chip Design and PPA Exploration

**Authors:** Xiang Li, Wenyu Sun, Yaqing Lai, Yubo Deng, Yongpan Liu

**Affiliation:** Tsinghua University

**First author and contact:** Xiang Li — [xiang-l24@mails.tsinghua.edu.cn](mailto:xiang-l24@mails.tsinghua.edu.cn)

**Conference representative:** Xiang Li (Graduate student, Tsinghua University)

ChipWave helps researchers construct chip-design tasks, change agent roles and
workflows, and follow designs through independent acceptance and physical feedback.
A five-stage RV32I CPU with a four-lane signed INT8 accelerator is the worked chip.
Its application speedup and the workflows' optimization efficiency are separate results.

The [English Notebook](ChipWave.ipynb) is the manuscript.
The [HTML preview](ChipWave.html) is exported from that same executed Notebook;
figures can be opened at their original vector size.
An English [36-second workflow animation](figures/ChipWave_Workflow.html)
appears after the Introduction. It is an offline conceptual illustration,
not a recorded design run. The Notebook embeds it in an isolated frame; viewers
that suppress interactive output can open the standalone file or read the
static platform figure. Playback needs no model account or EDA tools.
The platform is demonstrated through six qualified reference tasks, three fresh task
designs, executed configuration changes and one complete recorded PPA feedback
path. That path reaches a qualified candidate but does not improve the starting
chip. The complete nine-session comparison and four 100 MHz challenges remain
in Notebook Appendix B, including every failure and cost. No workflow superiority
or measured PPA improvement is claimed. All evidence remains in the
[analysis](results/benchmark-study/analysis.json). Final packaging rejects incomplete evidence.

The project connects four contributions:

- Built-in engineering roles and a standard recipe, plus custom roles, dependencies,
  tools, IP and gates through the same public execution kernel.
- Three parameterized task families: counters, synchronous FIFOs and INT8 dot products,
  with six variants, independent graders, faulty mutants and reference physical calibration.
- Frozen comparisons retaining success, failure, cost, source identity and unused slots.
- A CPU plus INT8 dot-product accelerator, with a recorded physical feedback loop
  and checks rejecting measurements from mismatched candidate deliveries.

## Choose your starting point

**One-minute orientation:** open [the HTML manuscript](ChipWave.html) in a
browser. No Python, model account or EDA installation is needed to read it. Start
with the Abstract and Introduction for the research context, §§2–4 for the
architecture and configurable tasks, and §§5–6 for physical feedback, platform evidence and the worked chip.
Setup separates saved-result inspection from real tool replay and new experiments;
Appendix D contains the full reproduction commands. The HTML embeds its figures;
the full evidence download is needed for local links and executable exercises.

**A short circuit exercise:** after extraction, use Python 3.12 and Icarus Verilog
(`iverilog` and `vvp` on PATH), from this directory:

~~~bash
python3 scripts/handshake_lesson.py --output ../handshake-lesson
~~~

Watch a signed dot product wait under backpressure, then see cancellation discard
work. The command simulates the published reference, rejects the existing
cancel-ignored mutant, and writes a CSV trace, VCD waveform and `lesson.json`.
It needs no Python packages, model account, synthesis or physical implementation.
Use a new output directory on every run. See Notebook Appendix A for the annotated trace.

**A workflow exercise:** after installing the public runtime below, run:

~~~bash
python scripts/self_check_benchmark_workflows.py --output ../workflow-branches.json
~~~

This executes the real TaskGraph with **synthetic roles and physical outcomes**.
It demonstrates review, bypass and feedback, not AI design quality or PPA gains.
The measured F2 study exercised the bypass zero times; the lesson explains a
configured capability which those experiments did not exercise.

**A measurement identity exercise:** with Python 3.12, first restore the local
raw evidence (30 GB free working space recommended), then run the lesson:

~~~bash
python scripts/evidence_store.py restore
python scripts/identity_lesson.py --output ../identity-lesson
~~~

This exercises the real measurement loader on copies of saved deliveries. A
netlist from another candidate, a changed clock and a mismatched delivery ID
are deliberately rejected; the original set passes. It starts no model, EDA
or simulation. The receipt distinguishes these injected errors from real design
failures. No original measurement is changed.

**Full evidence:** large raw outputs are losslessly compressed and deduplicated
inside `evidence/`; no external evidence download is required. The result summaries,
source and figures remain directly readable. See `evidence/index.json` for exact
storage sizes and original-file hashes. Before full tool replay, restore all
original paths with `python scripts/evidence_store.py restore`. This preserves
failed trials and all original bytes. Allow 30 GB free space for restoration and
measurement scratch, excluding separately installed tools.

**Start with a real exercise:** [QUICKSTART.md](QUICKSTART.md) describes a small
Linux container and a native route for simulating the dot-product handshake and
rejecting its cancellation fault. Neither requires a model account or full EDA.

## Install for Notebook and workflow execution (no model account)

Start in this directory, with Python 3.12:

~~~bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-notebook.lock.txt
python -m pip install -r runtime/requirements.lock.txt
python -m pip install ./runtime
python -m pip install jupyterlab
jupyter lab ChipWave.ipynb
~~~

Choose **Run → Run All Cells**. Default cells inspect saved evidence; they make no
model or physical-flow calls. The public runtime supplies 15 built-in role templates
and a 20-task standard recipe. The private browser frontend is not required.

For real offline tool checks, prepare the [pinned toolchain](toolchain/README.md).
The [execution guide](scripts/BENCHMARK_USAGE.md) covers the new benchmark extension:

~~~bash
python scripts/replay_benchmark_study.py --output ../benchmark-checks
python scripts/workflow_tutorial.py --output ../workflow-lessons
~~~

Final replay requires a complete export. During local development only, add
--allow-incomplete to check the retained completed parts; the receipt remains marked
as an incomplete campaign. The tutorial executes actual TaskGraph handoffs and Icarus
checks on saved RTL, labeled as replay rather than fresh model generation.

To remeasure the common start and first qualified candidate of each workflow using their delivered netlists,
SPEF, clocks, workloads and activity, without another full physical implementation:

~~~bash
python scripts/replay_benchmark_study.py --output ../power-checks --measurement first-per-workflow
~~~

Power is estimated with Liberty and zero-delay gate activity, not measured silicon
power or glitch-aware signoff.
The bundled KLayout DRC enables BEOL and OFFGRID rules and disables FEOL rules;
LVS uses the bundled Sky130 deck. These are the declared physical checks, not
full foundry signoff. The DRC script retains its GPLv3 license, included in
`toolchain/licenses/GPL-3.0.txt`; the root Apache-2.0 license does not replace it.

## Build tasks and deliberately start new experiments

Task construction itself is account-free:

~~~bash
python scripts/build_benchmark.py --family counter --width 16 --output ../counter-task
python scripts/qualify_benchmark.py --task ../counter-task
python scripts/initialize_benchmark_study.py --output ../new-study
python scripts/run_benchmark_campaign.py --campaign ../new-study --phase references
~~~

The last command only previews the phase and budget. Adding --execute deliberately
starts that phase. See [all phase commands and failure rules](scripts/BENCHMARK_USAGE.md).
Fresh agent runs require the recorded Codex CLI and a user-supplied account;
credentials stay outside the public package.

The template schedules nine PPA sessions, with 1,200 aggregate role seconds and at
most three accepted candidates each, plus three new frontend demonstrations.
Physical waiting is separate. The original budget is at most 41 planned full physical
executions plus three preformal calibration attempts, with a four-hour physical
deadline and thirty-minute postprocessing deadline per accepted attempt.
Failures consume slots and scored sessions are never reset or replaced.
For this saved campaign, the owner explicitly approved one additional dot4
reference calibration, raising its absolute cap from 44 to 45. This attempt
qualified after the original serial PPA/high-frequency batch. Both original dot4
failures remain, and no scored workflow candidate was replaced. See the
[authorization and scope](results/benchmark-study/budget-amendment.json).
New studies still use the original template limits.

The tutorial shows actual role YAML, dependency edits, configuration diffs, tool
outputs and raw-IP adaptation. Changing inputs, prompts, topology, tools, IP or
acceptance creates a new frozen experiment. CSIR checks a typed external behavioral
contract; executable scoreboards check behavior. Full CSIR behavioral lowering and
arbitrary natural-language generation of trustworthy benchmarks are outside this study.

## Inspect previous evidence

The twelve earlier requirements/IP × single/multiple-role generation trials and
the earlier fixed-RTL PPA experiment remain in
[results/configurable-study](results/configurable-study/protocol.json).
They are historical evidence, not new repeats of F0/F1/F2.

~~~bash
python scripts/replay_study.py --output ../historical-checks
python scripts/reproduce.py --output ../cpu-functional-checks
~~~

The second command reruns the CPU benchmark's functional/timing checks, workload
differentials, custom-instruction behavior and NPU protocol checks on the released
design. Its timing/engineering wall-time record is replay metadata, not a newly timed
design session.

## Regenerate the manuscript

~~~bash
python scripts/build_notebook.py
python scripts/render_notebook.py
~~~

The builder requires complete declared evidence; --draft keeps in-progress status.
The renderer executes the account-free cells and exports embedded HTML from the
same Notebook. Plot source manifests bind numerical figures to actual saved data.

The selected distribution uses [Apache-2.0](LICENSE). Third-party IP, tools and PDK
views retain their licenses in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
The full private upstream platform is outside this selected component distribution.
This is one design, one process corner and small descriptive samples; no universal
workflow winner, cross-task RSI learning, first-ever full-flow system or AI-over-rules
claim is made.

## Distribution and complete evidence

The submitted project has a compact storage form. The [evidence index](evidence/index.json)
maps each packed file to its original path, byte length, SHA-256 and local compressed
chunks. Read the Notebook without expanding these files. Before tool replay:

~~~bash
python scripts/evidence_store.py verify
python scripts/evidence_store.py restore
~~~

Restoration requires only Python's standard library. It checks every restored
file and refuses to overwrite a conflicting existing result. Independent paths
remain independently editable; no hardlinks between trials are introduced.
`compact` verifies the store and removes only unchanged restored copies.
A final package is built only after the original study and delivery validators
pass on restored evidence. The ZIP is a transport artifact; submit its project
directory, not the ZIP, to the official repository.

## Evidence scope for this submission

The completed benchmark and nine-session PPA study remain the primary evidence.
[submission-studies.json](submission-studies.json) distinguishes them from the
later stopped capacity study and unsuccessful bounded runtime preflight in
[diagnostics/](diagnostics/). These diagnostics contribute no comparison samples.
The planned 84-session study remains incomplete; no new design sessions or real
physical implementations were started in the deadline sprint.

## Name and provenance

**ChipWave** is the public name of this submission. Historical experiments and
selected upstream components used the name ChipNebula. Their logs, hashes,
license notices and internal `chip_nebula` paths retain their original names
so that recorded evidence remains verifiable. Install the public runtime with
`python -m pip install ./runtime` and use `chipwave --help`; the original command
remains available for replay compatibility.
