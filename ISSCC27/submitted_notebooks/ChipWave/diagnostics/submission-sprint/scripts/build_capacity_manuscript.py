"""Assemble the competition story from the current study and preserved earlier evidence."""
import argparse
import copy
import json
import re
import sys
import tempfile
from pathlib import Path

import nbformat

from capacity_integration_physical import ROOT, CASE
from capacity_notebook_cells import cells as capacity_cells
from capacity_results import analyze
from study_protocol import digest, write_json

sys.path.append(str(CASE/'scripts'))
from build_benchmark_notebook import build as earlier_manuscript, TITLE


def section(cells, heading):
    matches=[i for i,c in enumerate(cells) if c.cell_type=='markdown' and
             re.search(r'^## (?:\d+\. )?'+re.escape(heading)+r'\s*$',c.source,re.M)]
    if len(matches)!=1:
        raise ValueError('Expected one preserved manuscript section: '+heading)
    return matches[0]


def assemble(earlier, current, data):
    md=nbformat.v4.new_markdown_cell
    legacy=copy.deepcopy(earlier.cells)
    begin=section(legacy,'Build a benchmark before evaluating an agent')
    historical=section(legacy,'Change the organization, measure the PPA search')
    reproduction=section(legacy,'Reproduce, then extend the experiment')
    conclusion=section(legacy,'What this example teaches, and where it stops')
    positioning=next(c for c in legacy if c.cell_type=='markdown' and c.source.startswith('### Positioning'))
    overview=md('[![Task construction, configurable roles and shared engineering tools feed an independently evaluated delivery.](figures/capacity_platform.svg)](figures/capacity_platform.svg)\n\n**Task construction, configurable roles and shared engineering tools feed an independently evaluated delivery.**')
    abstract='''## Abstract

A circuit that passes simulation may still miss timing, lose a transaction under
backpressure, or fail to produce a qualified layout. Studying chip-design agents
therefore requires both realistic tasks and a way to change how the engineering
work is organized. We present **ChipNebula**, a configurable platform for building
reference-qualified tasks and composing traceable design workflows. Its public
components combine built-in roles and a standard flow with custom roles,
dependencies, tools, supplied IP and independent gates. Readers first construct
a task and modify a workflow, then follow a CPU–accelerator example from
workload requirements through physical implementation. A matched study changes
the organization of the work while keeping the model, information, logical Token
ceiling and physical-attempt allowance fixed. Function, GDS delivery and
constraint-qualified value are measured separately; failed deliveries earn zero.
'''
    if data['complete']:
        values=[r['equal_task_means']['joint_pass_rate'] for r in data['workflows']]
        abstract+=f'''
Across {data['terminal']} registered sessions, observed joint functional/GDS pass
rates range from {min(values):.1%} to {max(values):.1%} across model/workflow settings.
The per-task results and complete costs expose where organization helps, where
it adds work, and where no benefit is observed. Three repeats support descriptive
findings rather than a universal ranking. The educational contribution is a
reusable way to construct, run and inspect these experiments, supported by the
chip, configurations, checks and retained failures.
'''
    else:
        abstract+='''
**Working draft:** the new matched experiment is not yet complete and has no
completed-cohort conclusion.
Earlier experiments are retained as separate evidence, including searches that
did not improve the starting chip. This draft does not claim a workflow winner.
'''
    result=[legacy[0],md(abstract),copy.deepcopy(current[0]),overview,positioning]
    if data.get('stopped_batch'):
        result.insert(2,md('''## What the current experiment can establish

The four task references passed module and 95 MHz CPU-integration qualification.
An initial development run exposed a physical-wait pause defect. After repairing
and testing it, an explicitly authorized revised batch completed eight development
pilots and five of the 84 registered formal sessions. That batch was then stopped:
an asynchronous tool had completed, but its controller still treated it as active
and blocked subsequent work. The pilot admission gate had missed this error.

This is an experimental infrastructure failure, not evidence that a model could
not design a chip. Some integrated deliveries passed function and physical checks,
but the incomplete, affected batch cannot establish a workflow ranking. Its last
formal session finished its accepted physical run and retains two administrative
interventions; its hardware score is diagnostic, not a credited comparison result.
All 18 allocated physical attempts have terminal records, including failures.

The [stopped-batch record](results/capacity-stopped-batch.json) separates raw
outcomes, costs and validity from conclusions. The [runtime diagnosis](results/capacity-async-stop.json)
records the admission withdrawal. Repairs are tested outside the frozen batch;
they do not overwrite trials or turn tests of the runner into design samples.
The earlier completed platform and PPA studies remain the evidence reported below.
'''))
    elif data.get('runtime_stop'):
        result.insert(2,md('''## Runtime qualification stopped the new comparison

All four task references completed module and 95 MHz CPU-integration physical
qualification. The first Luna development pilot then exposed a control defect:
pausing the outer sandbox process did not pause its inner native session.
The model continued polling during physical waiting that the protocol excludes
from active time. We closed admission before any formal session began.

That pilot is invalid for equal-resource comparison. Its recorded Token prefix,
manual intervention and accepted physical attempt are retained, regardless of
the eventual hardware outcome. A process-tree repair passed a 75-second sandbox
test and a 130-second live native waiting fixture, including successful resumed
execution. These are repair checks, not replacement design trials or proof of
complete campaign qualification. No workflow ranking follows from them.

The [runtime-stop record](results/capacity-runtime-stop.json) and
[repair and revised-protocol proposal](experiments/capacity/RUNTIME_REVISION.md)
separate the original failure, repair evidence and conditions for a new batch.
The captured original runtime must not be used to resume scored design sessions.
'''))
    for cell in legacy[begin:historical]:
        if cell.cell_type=='markdown':
            cell.source=cell.source.replace('Workflow efficiency is evaluated\nseparately on a common starting implementation.',
                'Workflow effects are examined separately: the earlier PPA searches share a\nstarting chip, while the new study compares subsystem designs in a frozen integration.')
        result.append(cell)
    result.append(md('''## From a worked example to a matched experiment

The small task and supplied CPU–accelerator example teach the platform's basic
operations. They do not establish that additional roles are useful. In the
earlier twelve-trial generation experiment, every configuration passed the small
functional task. In the separate fixed-start PPA study, none of nine searches
improved the retained area–energy objective. These observations motivate a
harder question: when the design itself contains interacting transactions, can
the same resource allowance produce a better complete delivery?

The following study changes the assigned subsystem inside a frozen CPU shell.
Its final-delivery score is distinct from the earlier search objective Q. The
full earlier methods, negative results and costs remain in the appendix; they
are not counted again as new samples.
'''))
    result+=copy.deepcopy(current[1:])
    result.append(nbformat.v4.new_code_cell('''capacity = json.loads((ROOT / "results/capacity-study/analysis/formal-results.json").read_text())
assert capacity["planned"] == 84
print("Registered formal sessions:", capacity["terminal"], "/", capacity["planned"])
print("Completed cohort:", capacity["complete"])
if not capacity["complete"]:
    print("Working draft: no completed-cohort workflow ranking is available.")
'''))
    result.append(md('''## Reproduce a result, then ask a new question

The default notebook reads saved evidence and does not start model calls or
physical implementation. Install the public Python runtime and the pinned tools
described in the toolchain guide. Restore the saved study into a fresh directory
before running raw-file checks:

```bash
python experiments/capacity/scripts/restore_capacity_study.py \\
  --source results/capacity-study --workspace /tmp/capacity-restored
export CHIPNEBULA_CASE_ROOT="$PWD"
python /tmp/capacity-restored/scripts/analyze_capacity_results.py
python /tmp/capacity-restored/scripts/replay_capacity_reference.py \\
  --task A1 --output /tmp/capacity-reference-replay --remeasure
```

The last command regenerates activity and modeled power from the actual saved
netlist and SPEF. It spends local tool time but no model Tokens or new physical
attempts. All replay outputs use a new directory; archived results stay intact.
Filtered accounting traces separately allow readers to recompute Token totals
and source-snapshot association without an account or private native transcripts.

To inspect the allocation without starting any computation, run:

```bash
python experiments/capacity/scripts/init_capacity_study.py
```

Add `--workspace /tmp/my-capacity-study` to create a fresh, unqualified study.
Follow the [new-experiment guide](experiments/capacity/NEW_EXPERIMENT.md) to
build tasks, qualify the local runtime and references, freeze the inputs, then
run the pilots and admitted formal batch. Changing a role or task is a new
experiment, not an edit to a completed sample. Old passes and credentials are
not copied. Reproduction of saved outcomes and spending new experimental
resources are separate entrypoints.
'''))
    result.append(md('''## What a configurable platform makes possible

The platform's contribution is the experiment researchers can perform: define a
contract, vary the organization, expose downstream feedback, and inspect the
whole delivery and its cost. More roles are useful only when their contribution
survives those checks. A null result can still teach when a simpler workflow is
sufficient; a repair trace can suggest a better configuration to test next.

This study concerns two subsystem families inside a supplied CPU shell, small
repeat counts, one technology corner and serial roles on a shared host. Logical
Tokens are a comparable allowance, not equal monetary charges or compute.
Gate-level activity and Liberty/SPEF power are model estimates without SDF/glitch
or silicon measurement. Declared DRC/LVS checks are not foundry signoff. Selected
formal properties and finite traces do not prove arbitrary generated circuits.
Report-driven repair is demonstrated only where the retained trace supports it;
cross-task policy learning and RSI self-improvement are not established.
'''))
    reference_text=legacy[conclusion].source.split('## References and licenses',1)[1]
    result.append(md('## References and licenses'+reference_text))
    result.append(md('''## Appendix: the earlier fixed-start PPA experiment

This preserved experiment uses F0/F1/F2, a common verified starting chip, a
1,200-second role allowance and three new candidates per search. Its Q objective,
budget, source history and failed candidates remain separate from C0–C6 and the
new final-delivery score. The following evidence has not been relabeled or
replaced to make the newer experiment look better.
'''))
    for cell in legacy[historical:conclusion]:
        if cell.cell_type=='markdown':
            cell.source=re.sub(r'^## (?:\d+\. )?', '### ',cell.source,flags=re.M)
        result.append(cell)
    # Existing sources contain section numbers and figure suffixes; labels are assigned once here.
    number=0;figure=0
    for cell in result:
        if cell.cell_type!='markdown':continue
        def heading(match):
            nonlocal number
            title=re.sub(r'^\d+\. ', '',match[1])
            if title in ('Abstract','References and licenses') or title.startswith('Appendix:'):
                return '## '+title
            number+=1
            return f'## {number}. {title}'
        cell.source=re.sub(r'^## ([^\n]+)$',heading,cell.source,flags=re.M)
        if re.search(r'!\[[^\]]*\]\(figures/',cell.source):
            figure+=1
            if re.search(r'Figure \d+[a-z]?\.',cell.source):
                cell.source=re.sub(r'Figure \d+[a-z]?\.',f'Figure {figure}.',cell.source)
            else:
                cell.source=cell.source.replace('![',f'![Figure {figure}. ',1)
                cell.source=cell.source.replace('**',f'**Figure {figure}. ',1)
    return result


def build(source,output,*,draft=False):
    source,output=Path(source).resolve(),Path(output).resolve()
    data=analyze(source)
    stop=CASE/'results/capacity-runtime-stop.json'
    if stop.exists():
        data['runtime_stop']=json.loads(stop.read_text())
    stopped=CASE/'results/capacity-stopped-batch.json'
    if stopped.exists():
        data['stopped_batch']=json.loads(stopped.read_text())
    if not draft:
        if data.get('runtime_stop'):
            raise ValueError('Runtime qualification stopped; retain a draft until a new admitted campaign is complete')
        status=source/'export-status.json'
        if not data['complete'] or not status.exists() or json.loads(status.read_text()).get('complete') is not True:
            raise ValueError('Final manuscript requires the complete qualified study export')
    with tempfile.TemporaryDirectory(prefix='capacity-manuscript-') as temporary:
        earlier=earlier_manuscript(CASE/'results/benchmark-study',Path(temporary)/'earlier.ipynb')
    body=assemble(earlier,capacity_cells(source,draft=draft),data)
    notebook=nbformat.v4.new_notebook(cells=body,metadata=copy.deepcopy(earlier.metadata))
    notebook.metadata.chipnebula_submission.update(
        stage='working_draft' if draft else 'experiments_complete',title=TITLE,
        formal_terminal=data['terminal'],formal_planned=data['planned'])
    for cell in body:
        if cell.cell_type=='markdown':
            visible=re.sub(r'\]\([^\n]*?\)',']',cell.source)
            if re.search(r'\b[0-9a-f]{40,64}\b',visible):
                raise ValueError('Long source identities belong in manifests, not the main story')
    nbformat.validate(notebook)
    output.parent.mkdir(parents=True,exist_ok=True);nbformat.write(notebook,output)
    write_json(output.with_suffix('.source.json'),dict(draft=draft,formal_complete=data['complete'],
        formal_terminal=data['terminal'],protocol_sha256=digest(source/'protocol.json'),
        legacy_analysis_sha256=digest(CASE/'results/benchmark-study/analysis.json'),
        builder_sha256=digest(Path(__file__)),method_cells_sha256=digest(Path(__file__).with_name('capacity_notebook_cells.py')),
        scope='Unified English body; HTML must be exported from this notebook. Full public archive reproduction and independent review are separate completion gates.'))
    return notebook


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,default=ROOT)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--draft',action='store_true')
    args=parser.parse_args();book=build(args.source,args.output,draft=args.draft)
    print(json.dumps(dict(cells=len(book.cells),draft=args.draft)))
