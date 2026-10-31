"""Draw declared workflow/scoring methods using the existing notebook's vector style."""
import json
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

from capacity_integration_physical import ROOT,CASE
from capacity_protocol import WORKFLOWS
from capacity_workflows import configuration
from write_capacity_workflows import write
from study_protocol import digest,write_json

sys.path.append(str(CASE/'scripts'))
from plot_benchmark_workflows import WorkflowFigure

LABELS=dict(autonomous='Design engineer',architecture='Architecture',implementation='Implementation',
    verification='Verification',integration_ppa='Integration / PPA',integration='Integration',
    timing='Timing',power='Power',revision='RTL revision')


def platform(output):
    f=WorkflowFigure(1760,1030,'ChipNebula · build the task, configure the work, inspect the delivery',
        'Task construction and role configuration feed a controlled design loop. All workflows share tools, budgets and independent final checks. The evaluated agent designs a subsystem inside a supplied CPU integration.')
    f.text(28,82,'A research platform: vary engineering organization while keeping the comparison conditions explicit.',22)
    f.card(28,125,520,190,'Build an executable workload task',
        ['Template parameters + workload requirements','Typed CSIR contract, interface and licensed IP',
         'Development checks + frozen CPU shell'],'input',
        'Task family, interface and workload stay fixed within a trial')
    f.card(604,125,550,190,'Configure roles and dependencies',
        ['Built-in or project-local roles and recipes','Prompts, tools, IP, gates and feedback paths',
         'C1 / C2 / C3 / C6; native C0 is the external baseline'],'agent',
        'Freeze each configuration before a new independent session')
    f.card(1210,125,522,190,'Qualify the task independently',
        ['Reference design + hidden behavioral oracle','Compiling faults + CPU integration + GDS',
         'Reference-derived performance and PPA limits'],'gate',
        'Reference RTL and final checks stay outside agent access')
    f.card(28,425,520,180,'Design and repair',
        ['Native session or configured platform roles','Implement the assigned arithmetic / memory block',
         'Keep the supplied CPU, ISA and interfaces fixed'],'agent')
    f.card(604,425,550,180,'Run the shared engineering tools',
        ['Development checks → synthesis → place and route','Actual reports return to the design owner',
         'Second attempt can revise RTL or allowed settings'],'tool')
    f.card(1210,425,522,180,'Evaluate the submitted version',
        ['F: hidden function + synthesis + CPU integration','G: routed GDS + hold + declared DRC / LVS',
         'H: timing, electrical and workload / PPA limits'],'gate')
    f.arrow(288,315,288,425)
    f.arrow(680,315,420,425,bend=334)
    f.arrow(1471,315,1471,425)
    f.arrow(548,511,604,511);f.arrow(1154,511,1210,511)
    f.arrow(879,605,288,605,True,660)
    f.text(300,698,'Report-driven repair within the same allowance; no hidden final score is fed back.',20,'#fcd34d')
    f.text(604,363,'Same model, information and permissions',19)
    f.text(604,392,'1M shared Tokens · at most 2 physical attempts',19,'#7dd3fc')
    f.card(28,760,1704,162,'Keep the experiment inspectable and reusable',
        ['TaskGraph + Artifact: source snapshots, model usage, tool calls, failed attempts and the matching physical views',
         'Independent outcomes: functional pass, GDS pass, joint pass and a constraint-gated score; retain every planned session',
         'Public components: read and replay saved evidence without a model account; start new experiments with explicit budgets'],'input')
    f.text(28,981,'CPU + accelerator is the worked chip. The contribution is the task-building and workflow experiment that readers can reuse.',19)
    f.text(28,1015,'This diagram describes implemented mechanisms and the study protocol, not a measured advantage for a particular workflow.',17)
    f.save(output/'capacity_platform.svg')


def workflows(output):
    f=WorkflowFigure(1900,1210,'One workload, five ways to organize the work',
        'C0 is native Codex; C1 uses one platform role; C2 stages one context; C3 separates three contexts; C6 separates six. Same-role revision resumes the original context. All use shared protected tools and budgets.')
    f.text(28,78,'The experimental variable is organization. Models, information, tool access, checks and resource ceilings stay fixed.',20)
    summaries={'C0':'Native Codex','C1':'Platform role','C2':'Staged context','C3':'Three roles','C6':'Six roles'}
    for row,name in enumerate(WORKFLOWS):
        config=configuration(name);y=125+row*165;phases=config['phases']
        f.text(28,y+30,name,30,'#e0f2fe',True);f.text(28,y+59,summaries[name],18)
        f.text(28,y+88,str(len({p['context'] for p in phases}))+' context'+('s' if name in ('C3','C6') else ''),16)
        for index,phase in enumerate(phases):
            x=220+index*235;context=phase['context'].replace('integration_ppa','integration')
            f.card(x,y,220,112,LABELS[phase['phase']],
                ['Context: '+context,'Resumes RTL owner' if phase['phase']=='revision' else 'Read / act / report'],'agent')
            if index:f.arrow(x-15,y+55,x,y+55)
        if len(phases)>1:
            owner=next(i for i,p in enumerate(phases) if p['phase']=='implementation')
            for index,phase in enumerate(phases):
                if phase['phase'] not in ('architecture','implementation','revision'):
                    f.arrow(220+index*235+110,y+112,220+owner*235+110,y+112,True,y+139)
            f.text(690,y+158,'Failed review → actionable report → implementation owner',15,'#fcd34d')
        else:
            f.text(490,y+42,'The same engineer plans, writes RTL, tests, reads EDA reports and repairs.',19)
            f.text(490,y+77,'C0 bypasses platform orchestration; C1 uses its ordinary Role / Recipe / TaskGraph.',17)
    f.card(28,1010,590,150,'Shared resource pool',
        ['1M logical Tokens across all roles','20 development checks · 6 synthesis checks','At most 2 physical attempts; failures consume slots'],'gate')
    f.card(655,1010,590,150,'Shared tools and feedback',
        ['Function / CPU integration / synthesis / physical tools','First physical report can guide the second attempt','Identical reports; only the RTL owner edits the design'],'tool')
    f.card(1282,1010,590,150,'Independent final evaluation',
        ['Latest budget-admitted source and matching GDS','Hidden function → physical gates → constraint score','No hidden result is returned to any role'],'gate')
    f.text(28,1192,'Declared workflow configurations, not measured superiority. Calls are serial; there is no hidden planner or cross-trial learning.',17)
    f.save(output/'capacity_workflows.svg')


def scoring(output):
    f=WorkflowFigure(1560,850,'Correct RTL is the beginning, not the finish line',
        'Functional and physical outcomes are recorded independently. A nonzero score requires functional, GDS and constraint gates together, with source-bound postroute workload measurements.')
    f.text(28,80,'Deliver one traceable version: RTL + integration + configuration + GDS + reports.',21)
    f.card(28,120,480,205,'F · Function and integration',
        ['Held-out vectors for the public contract','Independent behavioral oracle + CPU workloads','Synthesis and finite progress / fairness checks'],'gate',
        'Coverage alone is not a functional pass')
    f.card(540,120,480,205,'G · Physical delivery',
        ['Readable GDS · detailed route · zero unrouted','Hold · declared DRC rules · LVS','RTL / configuration / netlist / GDS provenance'],'gate',
        'A GDS file alone is not a physical pass')
    f.card(1052,120,480,205,'H · Value within constraints',
        ['Setup + electrical + postroute correctness','Each workload meets its frozen limits','Valid activity / parasitics / power measurement'],'gate',
        'Hard limits cannot be traded against one another')
    f.arrow(268,325,780,405,bend=365);f.arrow(780,325,780,405)
    f.arrow(1292,325,780,405,bend=365)
    f.card(320,405,920,130,'Score only when F, G and H all pass',
        ['S = 100 × F × G × H × min(1, 0.5 × cube_root(T / Tref × Eref / E × Aref / A))',
         'T: effective throughput · E: energy per useful work · A: complete-chip standard-cell area'],'tool')
    f.card(28,610,725,140,'Keep the outcome decomposition',
        ['Report F, G, joint F∧G, conditional G|F and constraint pass rates','A functionally wrong circuit can still have a valid physical layout','Any failed gate produces a zero task score; retain its failure reason'],'input')
    f.card(785,610,747,140,'Keep the comparison honest',
        ['Reference = 50; cap = 100 · raw measurements remain visible','Average repetitions within each task, then weight the four tasks equally','Same 95 MHz target; power is a model estimate, not measured silicon'],'input')
    f.text(28,802,'Throughput and energy ratios use geometric means across workloads; every workload must also pass its own limits.',17)
    f.text(28,832,'This scoring function is defined for ChipNebula. It is not a reproduction of an unpublished external benchmark formula.',16)
    f.save(output/'capacity_scoring.svg')


def tasks(output):
    f=WorkflowFigure(1640,1030,'From workload requirements to a complete integrated chip',
        'Four tasks change interaction complexity inside two fixed CPU integration shells. The agent designs only the highlighted accelerator or memory subsystem; the CPU, firmware and adjacent adapters are frozen.')
    f.text(28,80,'The task is a workload and a public contract. The deliverable is the subsystem inside a source-matched 95 MHz chip.',20)
    f.text(28,133,'A · Exact signed INT8 arithmetic with transaction control',23,'#7dd3fc',True)
    f.card(28,165,365,145,'Frozen CPU and driver',
        ['Variable vectors, length 1–64','Commands / operand beats / cancel','Fixed ISA and integration adapter'],'input')
    f.card(473,165,655,145,'Agent-designed dot-product subsystem',
        ['Arithmetic + command/data ownership + ordered delivery','A1: one command · A2: four live commands + two beat buffers','Exact INT32 result; unused tail lanes have no effect'],'agent')
    f.card(1208,165,404,145,'Frozen result consumer',
        ['Correct value and command ID','Response backpressure and cancel','Short / mixed / long workloads'],'input')
    f.arrow(393,228,473,228);f.arrow(1128,228,1208,228)
    f.arrow(1208,285,1128,285,True)
    f.text(660,345,'A2 adds interleaving, queued results, cancellation and ownership interactions.',18)
    f.text(28,406,'B · Shared memory under contention, reordering and flush',23,'#7dd3fc',True)
    f.card(28,440,365,113,'Frozen CPU adapter',
        ['Word-aligned reads / byte writes','Request ID + stalled responses'],'input')
    f.card(28,585,365,113,'Frozen accelerator adapter',
        ['Checksumming traffic workload','Competes for the same memory'],'input')
    f.card(473,475,655,185,'Agent-designed memory subsystem',
        ['Round-robin arbitration + request/response ownership','B1: one global outstanding transaction','B2: four outstanding / buffered transactions','Per-client response order + stale-response draining'],'agent')
    f.card(1208,475,404,185,'Frozen external memory',
        ['32-bit data + byte write enables','Response tags may reorder','Accepted writes survive a flush','Public finite-stall assumptions'],'input')
    f.arrow(393,496,473,510);f.arrow(393,640,473,626)
    f.arrow(1128,536,1208,536);f.arrow(1208,606,1128,606,True)
    f.text(473,703,'B2 adds ordering and tag lifetime; it does not add a cache or a new CPU ISA.',18)
    f.card(28,760,770,155,'Qualify the task before evaluating an agent',
        ['Independent oracle + compiling mutants + CPU workloads','Module reference at 10 MHz; integrated reference at 95 MHz','Freeze constraints only after the reference qualifies'],'gate')
    f.card(830,760,782,155,'Measure all evaluated deliveries',
        ['Same model, information, tool access and resource ceilings','At most two physical attempts; return the first EDA report','Score the latest budget-admitted source and matching GDS'],'tool')
    f.text(28,970,'Blue: designed by the evaluated agent · gray: supplied and frozen · purple: independent task qualification.',18)
    f.text(28,1005,'Two task families, two complexity levels each. This study does not claim to generate the entire CPU from scratch.',17)
    f.save(output/'capacity_tasks.svg')


def main():
    output=ROOT/'publication/figures';output.mkdir(parents=True,exist_ok=True)
    platform(output);workflows(output);scoring(output);tasks(output)
    declarations={}
    with tempfile.TemporaryDirectory(prefix='capacity-diagram-config-') as temp:
        for name in WORKFLOWS:
            project=Path(temp)/name;project.mkdir()
            recipe=write(project,name,'gpt-6-luna')
            declarations[name]=dict(configuration=configuration(name),
                recipe_sha256=digest(recipe) if recipe else None)
    names=('capacity_platform.svg','capacity_workflows.svg','capacity_scoring.svg','capacity_tasks.svg')
    for name in names:
        svg=ET.parse(output/name);assert svg.getroot().find('{http://www.w3.org/2000/svg}desc') is not None
    write_json(output/'methods.source.json',dict(scope='Implementation/protocol diagrams, no outcome data',
        workflows=declarations,source_sha256={name:digest(ROOT/'scripts'/name) for name in
            ('capacity_protocol.py','capacity_workflows.py','write_capacity_workflows.py','draw_capacity_methods.py')},
        task_contracts={name:digest(ROOT/'task-packages/formal'/name/'agent/spec/task.md') for name in ('A1','A2','B1','B2')},
        drawing_helpers={name:digest(CASE/'scripts'/name) for name in ('plot_study.py','plot_benchmark_workflows.py')}))
    print(json.dumps(dict(figures=names,measured_results=False)))


if __name__=='__main__':main()
