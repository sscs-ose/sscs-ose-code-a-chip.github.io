"""English manuscript cells for the new study; conclusions require completed data."""
import nbformat

from capacity_results import analyze


def table(headers,rows):
    return '| '+' | '.join(headers)+' |\n|'+'|'.join('---' for _ in headers)+'|\n'+''.join(
        '| '+' | '.join(str(v) for v in row)+' |\n' for row in rows)


def cells(root,*,draft=False):
    data=analyze(root)
    if not data['complete'] and not draft:raise ValueError('Completed trial evidence required for result narrative')
    result=[]
    def md(text):result.append(nbformat.v4.new_markdown_cell(text.strip()))
    def figure(name,caption):md(f'[![{caption}](figures/{name}.svg)](figures/{name}.svg)\n\n**{caption}**')
    md('''## From a passing simulation to a chip that can be delivered

Imagine an accelerator that computes every answer correctly in simulation, but
cannot meet timing after routing. Another design fits the clock, yet returns a
canceled command when the CPU stalls. Neither is a successful delivery. A design
agent must connect arithmetic, transaction ownership and physical constraints,
then use a failure in one stage to change a decision made earlier.

ChipNebula lets us turn this challenge into a controlled experiment. We keep
the workload, processor shell, tools and resource ceilings fixed, then change
how the engineering work is organized. Can one agent handle the complete loop?
Does an explicit sequence of checks help? Does giving those checks independent
contexts improve the delivery enough to pay for the handoffs?

The earlier configurable tasks and CPU–accelerator demonstration establish the
building blocks. This study asks a different question from the earlier fixed-start
PPA search: **which workflows deliver a correct, physically qualified integrated
design within the same Token and physical-attempt limits?** The agent designs the
assigned subsystem; the existing CPU and neighboring adapters are supplied IP.
''')
    md('''## Workloads that expose interactions

The four tasks form two families with two complexity levels each. The arithmetic
family asks for exact signed INT8 dot products of lengths 1–64. Its harder level
adds interleaved operand traffic, queued commands and individually canceled
results. The memory family asks two clients to share a byte-writable memory
interface. Its harder level adds multiple outstanding transactions, reordered
memory responses and flush recovery.

These are changes in interaction complexity, not four unrelated architectures.
The task cards publish the interface, reset/cancel priority, finite-stall
assumptions and progress bounds. Held-out checks vary vectors and schedules;
they do not invent new behavioral requirements.
'''+table(['Task','Designed subsystem','Additional interaction'],[
        ['A1','Variable-length dot product','One live command, tails, backpressure and cancel'],
        ['A2','Queued dot product','Four live commands, two operand-beat buffers, ordered results'],
        ['B1','Shared memory interface','Two clients, round-robin grants, one transaction in flight'],
        ['B2','Multiple-in-flight interface','Four outstanding/buffered transactions, tags and stale-response draining']])+'''

The A2 buffers hold operand beats rather than complete vectors. The B-family
integration uses a fixed checksumming accelerator traffic harness. We keep the
CPU ISA, pipeline, firmware and adjacent modules fixed, and do not claim that
this experiment generates an entire CPU from scratch.

Before an agent is evaluated, each task needs an independent behavioral oracle,
compiling fault variants that the oracle rejects, reference synthesis and CPU
integration, and physical reference deliveries. Module references run at 10 MHz;
the complete reference chips run at 95 MHz. Their measured results establish
the task limits before the scored sessions begin. Selected formal safety checks
and finite progress traces supplement testing; they are not a proof of the full
behavior of every generated design.
''')
    figure('capacity_tasks','The designed boundary: more interaction inside the same frozen integration contract.')
    md('''## Change the organization, keep the opportunity to succeed

C0 is a native Codex single session. It can plan, test, inspect reports and
repair; it is not restricted to one-shot generation. C1 loads one engineering
role through ChipNebula. C2 gives that same context explicit implementation,
verification and integration/PPA stages. C3 gives those stages three independent
contexts, returning revisions to the RTL owner. C6 separates architecture, RTL,
verification, timing, power and integration duties.

C2 and C3 share the same stage goals and professional checklists. Every group
can read the same information and use the same development, synthesis and
physical tools. Role calls are serial, so parallel compute is not an additional
advantage. These configurations reuse the ordinary Role, Recipe, TaskGraph and
Artifact mechanisms; the common external evaluator also surrounds native C0.

All roles in a session use the same model and `high` reasoning setting. The
planned main comparison uses GPT-6 Luna, with GPT-6.1 Sol as a stronger-model
reference for C0 and C3. This choice does not establish a capability ordering on
the tasks: that remains an empirical question. No stronger hidden reviewer or
unmetered planning agent participates.
''')
    figure('capacity_workflows','Five organizations share one tool and budget contract; only the organization changes.')
    md('''### Equal ceilings, complete costs

Each session shares one million logical input-plus-output Tokens across all
roles, up to 20 charged development executions, six synthesis checks and two
physical attempts. Cached input remains part of logical input; reasoning Tokens
are not added again when already included in output. Handoffs, retries, context
compression and failed calls remain in the ledger. The limits are equal ceilings,
not a requirement to spend every Token or tool slot.
The frozen shell controller recognizes a restricted set of single read commands
without spending a development slot. Other shell executions, including compound
inspection commands, consume that allowance. We therefore report charged tool
executions rather than interpreting every charged call as a functional test.
The separate synthesis endpoint performs generic integrated synthesis, not mapped
STA; timing evidence comes from the physical flow.
Equal logical Tokens do not imply equal monetary charges or GPU computation.
Service invoice amounts are not captured by this adapter; we report them as
unavailable rather than estimating an unverified price.

The first physical report can guide a second attempt. A failed or timed-out
attempt still consumes its slot. Agent activity, including front-end tools, has
a 90-minute ceiling; deterministic physical execution and postprocessing are
timed separately. The original native process is paused during its controlled
physical wait. There is no third attempt and no replacement of a failed trial.

The observer binds each scored source snapshot to completed, attributable native
usage. At 250k, 500k and one million Tokens, evaluation uses the latest eligible
snapshot, not whichever historical design passes a hidden test. A budget-admitted
physical run can finish after the model stops, but later over-budget edits cannot
enter that delivery. A new RTL version cannot borrow the previous version's GDS.

The three checkpoints are observations of one session, not three independent
samples. First observed success is assessed at these checkpoints and submitted
physical sources; intermediate edits are not continuously graded. Offline final
evaluation is capped at 30 minutes per trial, recorded separately, and never fed
back to the model. In-flight excess Tokens, incomplete accounting and unavailable
costs stay visible. Missing measurements are not treated as zero cost.

Task-template/checker engineering, reference calibration and runtime qualification
are preparation work. The separately metered native CLI preflights are reported
as preparation calls, not design samples. Their counters do not measure the
entire author-side coding effort or tool installation, and we do not claim that
the cost of preparing this experiment is zero.
''')
    md(r'''## Three questions for every delivery

**Does it work?** Functional pass requires the held-out contract checks,
synthesis and CPU integration. **Was a physical design delivered?** GDS pass
requires detailed routing, a readable GDS, zero unrouted connections under the
declared check, hold, the declared DRC rules, LVS and matching provenance.
**Does it have value under the task constraints?** Only a delivery passing both
gates can earn a nonzero task score.

Function and GDS are recorded independently: a wrong circuit can still have a
valid layout. We show both rates, their joint rate, and GDS pass conditioned on
function. A nested funnel uses functional, joint functional/GDS and jointly
constraint-qualified deliveries. A declared rule-set check is not a claim of
foundry signoff or measured silicon performance.

For a nonzero score, setup and electrical checks, postroute functionality and
source-consistent activity/parasitic measurement must also pass. Every workload
must achieve at least 80% of reference throughput, with latency, average modeled
power and energy per useful work no greater than 125% of reference. Standard-cell
area and chip footprint each have the same 125% limit. All use the frozen
10.526 ns clock, Sky130HD TT/25°C/1.8 V corner, two threads, 0.1 ns uncertainty
and 0.5 ns IO delays including reset.

Our score is

$$S=100FGH\min\left(1,\;0.5\sqrt[3]{\frac{T}{T_{ref}}\frac{E_{ref}}{E}\frac{A_{ref}}{A}}\right).$$

Here $F$ and $G$ are the first two gates and $H$ means all task limits pass.
$T$ is useful throughput, $E$ is energy per useful work and $A$ is standard-cell
area of the complete integrated chip. Throughput and energy ratios use geometric
means across workloads; individual workload limits still apply. Canceled or
flushed transactions do not count as useful completed work. The reference scores
50 and the maximum is 100. Any failed gate gives zero; raw PPA remains visible.

This evaluation structure is inspired by
[Build-A-Chip-Bench](https://chipagents.ai/research/build-a-chip-bench).
The tasks, calibrated limits and scoring function here are defined for this
ChipNebula experiment, not a reproduction of unpublished external scoring rules.
''')
    figure('capacity_scoring','A nonzero score requires a correct, physical and constraint-qualified delivery.')
    md('''### What the comparison can establish

C0→C1 examines platform execution overhead. C1→C2 examines explicit stage
guidance. C2→C3 examines independent role contexts, and C3→C6 examines finer
division of responsibilities. A1→A2 and B1→B2 test whether interaction complexity
changes the pattern. The two model settings ask whether workflow effects depend
on the base model.

We average three repetitions within each task, then weight the four tasks equally.
All planned sessions remain in the main denominator, including invalid accounting
and infrastructure failures; a valid-sample analysis is shown separately. Three
repetitions support descriptive findings, not a general optimal number of agents.
The fixed seed controls execution order within task/repetition blocks, not the
model service's sampling randomness.

Design choices are also inspectable: utilization 30/40/50%, placement density
0.55/0.65, area-oriented synthesis on/off, and electrical repair margin 0/10/20%.
Legal internal microarchitecture changes are allowed inside the assigned module.
Workloads, CPU behavior, interfaces, clock and acceptance constraints stay fixed.
Eight native-Codex development pilots use separate test-data variants. If all
four Luna pilots pass function/integration, or all four fail, the formal batch
stops for a discrimination diagnosis. We do not silently retune until the desired
workflow ranking appears.
''')
    if not data['complete']:
        md(f'''## Results status

**Working manuscript: {data['terminal']} of {data['planned']} formal sessions have
terminal results.** The completed-cohort rates, workflow rankings and score curves
are intentionally withheld. Reference qualification and engineering preflights
are preparation evidence, not substitutes for these design sessions.
''')
    else:
        md('''## Read delivery and cost together

Each rate below is an equal-task average with all planned repetitions retained.
The score includes zero-valued failed deliveries. GDS pass is independent of
functional pass; joint and constraint-qualified rates expose the remaining gap.
'''+table(['Model','Workflow','Functional','GDS','Joint','Constraint-qualified','Mean score'],[
            [r['model'],r['workflow'],*[f"{r['equal_task_means'][k+'_rate']:.1%}" for k in
                ('functional_pass','gds_pass','joint_pass','constraint_pass')],
             f"{r['equal_task_means']['average_score']:.2f}"] for r in data['workflows']]))
        md('''The per-task table and complete session ledger accompany these averages.
Interpret them alongside Token use, physical attempts, elapsed time and invalid
measurements. A first successful physical attempt followed by a failed final
submission is reported as a regression; its earlier success does not rescue the
final score. Role switches and repeated stages quantify coordination activity,
but do not by themselves prove a useful repair or a causal need for that role.
''')
        figure('capacity_ppa_tradeoffs','Area and modeled energy of final constraint-qualified deliveries, with qualified/planned counts.')
        md('''The area–energy panel shows only final constraint-qualified deliveries;
it does not replace the complete-cohort success rates above. Each point uses its
own task's full integrated reference. Coincident points retain their true
positions and display their multiplicity. The complete measurement ledger also
retains available raw area, throughput, latency, power and unit-energy values
for failed gates, with missing values explicitly unavailable. Diagnostic first
attempts are kept separate from the final submission.
''')
        figure('capacity_outcomes','Independent functional and GDS rates, joint delivery, and constraint-qualified delivery.')
        figure('capacity_token_curves','The latest eligible submission at each Token ceiling; decreases are preserved.')
        figure('capacity_costs','Actual Token use, active time and physical attempts, including failed trials.')
        figure('capacity_first_success','First observed success cost and unreached endpoints at the declared observation granularity.')
        figure('capacity_coordination','Executed role activity and coordination proxies; these counts do not establish causal benefit.')
        figure('capacity_physical_feedback','Repair and regression between the first and second physical attempts.')
    return result
