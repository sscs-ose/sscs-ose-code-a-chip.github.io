# Build tasks and compare workflows

The default notebook and result replay do not start a model or synthesis/place-and-route.
Use Python 3.12 and install the notebook/runtime locks as described in the main README.
Source the pinned-tool environment described in ../toolchain/README.md before simulation
or EDA. Fresh agent runs also require the supported Codex CLI login and network access;
credentials are kept outside projects and are never included in exports.

## Inspect and reproduce saved evidence

From the extracted ChipWave directory:

~~~bash
python scripts/replay_benchmark_study.py --output ../benchmark-checks
python scripts/workflow_tutorial.py --output ../workflow-lessons
~~~

The first command verifies the export hashes, reconstructs all local reference/mutant
checks, simulates qualified routed reference netlists, checks selected new RTL and
recomputes comparative Q. Original failed trials are retained; replay does not repair
them or turn them into fresh design successes.

For a PPA candidate, use ppa/SESSION/candidates/NN/evaluation.json as the
common-baseline comparison. It binds the proved action source and common
constraints, then calculates area, energy and Q ratios against baseline/common.
The nested physical/evaluation.json preserves the legacy physical/measurement
stage's self-normalized score. High-frequency challenges are a separate 100 MHz
endpoint; their self-normalized score does not enter the 95 MHz workflow ranking.

To rerun candidate-bound workloads and OpenSTA power for the common start and lowest-Q
new candidate, without a model account or new full physical implementation:

~~~bash
python scripts/replay_benchmark_study.py --output ../benchmark-power --measurement best
~~~

This can take several minutes and requires Yosys, Verilator, a host C++ compiler
and make, OpenROAD/OpenSTA, and the packaged Sky130HD views. The workload programs
are assembled by `kernel_programs.py`; no external RISC-V compiler is required.
The separate benchmark functional checks use Icarus Verilog. Values are model estimates from
zero-delay gate activity and SPEF, not measured silicon power or glitch-aware signoff.
Use --measurement common to check only the shared start, or all for all qualified
95 MHz candidates. Every output directory must be new.

## Construct another task

~~~bash
python scripts/build_benchmark.py --family counter --width 16 --output ../counter-task
python scripts/qualify_benchmark.py --task ../counter-task
~~~

Other templates use --family fifo --width 8 --depth 4, or --family dot --lanes 2.
Supported dimensions are intentionally finite: width 8/16, depth 4/8, lanes 2/4.
CSIR validates typed interface/external contract attachments. The independent
SystemVerilog scoreboards check the circuit behavior; this is not full CSIR behavioral
lowering.

Each task contains agent/ (requirements, typed contract, development tests, project-local
roles/Recipe), grader/ (reference, final tests and mutants), workload.json,
physical-contract.json, constraints.sdc, commands.json and build.json. Only agent/ is
exposed to an evaluated agent. Task validity needs its own local checks and reference
physical calibration before any agent score is meaningful.

## Start a fresh study, with explicit cost

~~~bash
python scripts/initialize_benchmark_study.py --output ../new-study
python scripts/run_benchmark_campaign.py --campaign ../new-study --phase references
~~~

Initialization creates six tasks, the frozen study template and an empty protected
ledger. It starts no model or full physical flow. The second command **only previews**
the phase and its budget. Inspect all printed constraints before adding --execute.

Execute phases in order, using separate commands:

~~~bash
python scripts/run_benchmark_campaign.py --campaign ../new-study --phase actions --execute
python scripts/run_benchmark_campaign.py --campaign ../new-study --phase references --execute
python scripts/run_benchmark_campaign.py --campaign ../new-study --phase baseline --execute
python scripts/run_benchmark_campaign.py --campaign ../new-study --phase demonstrations --execute
python scripts/run_benchmark_campaign.py --campaign ../new-study --phase freeze --execute
python scripts/run_benchmark_campaign.py --campaign ../new-study --phase ppa --execute
python scripts/run_benchmark_campaign.py --campaign ../new-study --phase high-frequency --execute
python scripts/run_benchmark_campaign.py --campaign ../new-study --phase report --execute
~~~

Actions prove all three nontrivial RTL-action combinations, run 63 CPU/workload cases
and the NPU protocol regressions. It makes no PPA calls and selects by correctness only.
References perform one physical implementation per task and freeze each area cap at
1.25 times its measured reference standard-cell area. The baseline is a shared 95 MHz
CPU+NPU implementation with source-bound measurements. Demonstrations are three
preselected fresh model trials, with one physical slot each when functionality passes.

The PPA phase runs nine independent model sessions in the protocol's seeded order.
All roles in a session share 1,200 seconds; EDA wait is separate. Each has at most
three accepted candidates. F0 has no AI reviewer, F1 reviews every proposal, and F2
reviews the first proposal and proposals following a failed candidate. Model, prompts,
actions and final gates are otherwise shared. No cross-session physical cache is used.

The template caps planned physical executions at 41, with three separately recorded
preformal calibration attempts and an absolute cap of 44. Each physical run has a
four-hour deadline plus thirty minutes for postprocessing. It is not a twelve-hour
promise. Accepted failures and infrastructure timeouts consume slots. The runner will
not reset or replace scored sessions, or automatically rescue failed references.
Inspect the original launch ledger and failure evidence before choosing an allowed
preformal calibration, using benchmark_physical.py --category preformal_calibration
with a new output and identity. Calibration cannot run after the formal freeze.
Any owner-approved one-off budget amendment in the saved campaign is separate from
this reusable template and is not silently inherited.

The saved study has one such explicit amendment: a single dot4 reference
supplement, after its original serial PPA/high-frequency batch, raises the total
cap to 45. Its authorization is in
`results/benchmark-study/budget-amendment.json`. It retains the failed reference
attempts and does not add, reset or replace any scored workflow candidate.

If a task or the common baseline fails qualification, the corresponding evidence is
incomplete. Do not make up its area limit, remove the failed attempt, weaken a gate,
or run a replacement scored session. Missing evidence remains explicit.

## Customize one variable at a time

Generated project-local role YAML is under agent/.chip_nebula/roles/ and the Recipe
is agent/.chip_nebula/recipes/benchmark.yaml. The four offline workflow lessons show
an executed custom role, an added verifier, a dependency edit and raw IP plus adapter.
Each lesson retains configuration.diff, complete YAML, execution order and real
checker output. Saved-RTL replay is labeled as replay, not fresh generation.

Create a new task or study directory for a prompt, model, dependency, IP, action-domain
or acceptance change. Before scored PPA runs, freeze_benchmark_study.py captures the
used SDK resources, implementation helpers, baseline and admitted action library.
Formal sessions reject a source/installed-SDK mismatch. Keep old studies intact.

Export a finished new study for sharing:

~~~bash
python scripts/export_benchmark_study.py --campaign ../new-study --output ../public-results
~~~

A final export requires all declared evidence. --draft is a development-only incomplete
export, labeled accordingly. Authentication and private model homes are excluded.
The raw launch/failure records, candidate-bound measurements and used configurations
remain available for inspection.
