"""Vector explanations reuse ChipWave's workflow-board visual language."""
import argparse
import json
from pathlib import Path

from plot_study import WorkflowFigure as WorkflowBoard
from study_protocol import digest,write_json

CASE=Path(__file__).resolve().parents[1]


class WorkflowFigure(WorkflowBoard):
    def text(self,x,y,text,size=15,color='#cbd5e1',bold=False):
        # Diagram bodies remain readable when the notebook scales the vector board.
        size={12:13,13:15}.get(size,size)
        super().text(x,y,text,size,color,bold)


def platform(output):
    f=WorkflowFigure(1440,840,'ChipWave · build tasks, configure workflows, compare evidence',
        'A configurable platform connects benchmark construction, built-in and custom roles, fixed experimental contracts and independent chip evaluation.')
    f.text(28,78,'A research instrument: change the task or workflow; keep the comparison conditions explicit.',17)
    f.card(28,112,440,174,'Build the benchmark',
        ['Choose a family, parameters and interface','CSIR + behavioral acceptance contract','Reference + mutants + 10 MHz calibration'],'tool','Task validity is checked before agent scoring')
    f.card(500,112,440,174,'Configure the experiment',
        ['15 built-in roles / 20-task standard recipe','Customize roles, dependencies, tools and IP','Freeze model, actions, budget and gates'],'agent','Project-local YAML, same TaskGraph kernel')
    f.card(972,112,440,174,'Keep the evaluator independent',
        ['Agent sees requirements + development tests','Reference and held-out grader stay separate','Function + STA + electrical + DRC + LVS'],'gate','Saved success, failure, cost and provenance')
    f.arrow(468,198,500,198);f.arrow(940,198,972,198)
    f.text(28,336,'FLAGSHIP EXAMPLE · one CPU + accelerator; workflow organization is the experimental variable',16,'#7dd3fc',True)
    cards=[('Frozen task',['Five-stage RV32I + dot4','Same starting chip and workloads'],'input'),
           ('Configured roles',['Optimizer and optional reviewer','F0 / F1 / F2 relationships'],'agent'),
           ('Protected tools',['Shared RTL actions + parameters','Synthesis → route → extraction'],'tool'),
           ('Independent measurement',['Qualified area and energy','Retain the best valid candidate'],'gate')]
    for i,(title,lines,kind) in enumerate(cards):
        x=28+i*352
        f.card(x,370,328,146,title,lines,kind)
        if i<3:f.arrow(x+328,442,x+352,442)
    f.arrow(1250,516,545,516,True,570)
    f.text(450,599,'Measured feedback → next proposal within the same frozen workflow and budget',15,'#fcd34d')
    f.card(28,650,676,122,'Application value',['CPU + INT8 accelerator runs useful arithmetic workloads','Application speedup is a property of the worked chip.'],'input')
    f.card(736,650,676,122,'Research value',['The platform exposes role/workflow tradeoffs and their costs','No universal multi-role or cross-task learning claim.'],'input')
    f.text(28,816,'Built-in standard path and focused custom experiments share roles, artifacts, dependencies, gates and failure feedback.',14)
    f.save(output/'benchmark_platform.svg')


def construction(output):
    f=WorkflowFigure(1440,820,'Construct a benchmark that can actually be evaluated',
        'Three parameterized families are checked with reference implementations and independent mutant-tested scoreboards before an evaluated agent is run.')
    f.text(28,78,'Three families, two variants each: counters · synchronous FIFOs · signed INT8 dot products',17)
    stages=[('Task parameters',['Dimensions + behavior','Pinned top-level interface'],'input'),
            ('Construct the task',['Task card + typed CSIR','Public development checker'],'tool'),
            ('Qualify the reference',['Functional + synthesis checks','Reject ≥3 faulty mutants'],'gate'),
            ('Calibrate the task',['Reference GDS + netlist checks','Area cap = 1.25 × cell area'],'gate')]
    for i,(title,lines,kind) in enumerate(stages):
        x=28+i*352
        f.card(x,120,328,145,title,lines,kind)
        if i<3:f.arrow(x+328,192,x+352,192)
    f.card(28,350,660,186,'Evaluated agent workspace',
        ['Requirements, interface and development tests','Configured designer / verifier / tool dependencies','Generated RTL and captured decisions only'],'agent','No reference RTL, held-out vectors or other trials')
    f.card(752,350,660,186,'Separate evaluator workspace',
        ['Frozen final scoreboard and numerical oracle','Candidate-bound physical and workload checks','Record task validity separately from agent success'],'gate','Public materials; isolated during each scored run')
    f.arrow(688,440,752,440)
    f.arrow(1250,265,350,350,bend=315)
    f.text(600,340,'Frozen task + allowed tools',14,'#7dd3fc')
    f.card(28,620,1384,112,'What a reader can reproduce',
        ['Build a new variant → qualify its checks and constraints → choose a workflow → inspect all results and costs'],'tool',
        'Template-based construction; arbitrary natural-language generation is outside the validated scope')
    f.text(28,784,'An invalid task is a construction failure. A correct task with a failing design is an agent result. Keep both.',15)
    f.save(output/'benchmark_construction.svg')


def workflows(output):
    f=WorkflowFigure(1600,970,'PPA exploration · workflow organization as an experimental variable',
        'F0 is a single optimizer, F1 adds fixed independent review, and F2 uses the same roles with first/after-failure conditional review. All have identical actions, budgets and engineering gates.')
    f.text(28,78,'Shared starting CPU + NPU · shared proved RTL actions and implementation parameters · common 95 MHz target',17)
    for i,name in enumerate(('F0','F1','F2')):
        y=135+i*245
        f.text(28,y+28,name,28,'#e0f2fe',True)
        f.text(28,y+58,'3 sessions',13)
        f.card(150,y,255,130,'PPA optimizer',['Read captured real reports','Propose one unseen candidate'],'agent')
        if name=='F0':
            f.arrow(405,y+65,950,y+65)
            f.text(525,y+42,'One role; no AI review',15,'#94a3b8')
        elif name=='F1':
            f.arrow(405,y+65,670,y+65)
            f.text(435,y+42,'Every proposal',14)
            f.card(670,y,245,130,'Independent reviewer',['Same reviewer as F2','Findings return to optimizer'],'agent')
            f.arrow(915,y+65,950,y+65)
            f.arrow(792,y+130,275,y+130,True,y+154)
        else:
            f.arrow(405,y+65,435,y+65)
            f.card(435,y,205,130,'Review condition',['First candidate OR','prior candidate failed'],'gate')
            f.arrow(640,y+65,670,y+65)
            f.card(670,y,245,130,'Independent reviewer',['Same role/prompt as F1','Triggered only when needed'],'agent')
            f.arrow(915,y+65,950,y+65)
            f.arrow(538,y,1070,y,False,y-25)
            f.text(680,y-7,'Bypass path: 0 uses in measured sessions',13,'#7dd3fc')
            f.arrow(792,y+130,275,y+130,True,y+154)
        f.card(950,y,270,130,'Protected EDA tools',['Apply common RTL action flags','Synthesis / P&R / extraction'],'tool')
        f.arrow(1220,y+65,1250,y+65)
        f.card(1250,y,320,130,'Independent engineering gates',['Function / equivalence / workloads','STA / electrical / DRC / LVS'],'gate')
        f.arrow(1410,y+130,275,y+130,True,y+187)
        f.text(655,y+213,'Report + best valid result → next proposal; stop at the shared budget',13,'#fcd34d')
    f.text(28,915,'Per session: all roles share 1,200 s; at most 3 accepted candidates. EDA waiting is recorded separately.',16)
    f.text(28,948,'Failures consume slots. Conditional review changes task dependencies, not acceptance limits or available actions.',15)
    f.save(output/'benchmark_ppa_workflows.svg')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=CASE/'figures')
    args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    platform(args.output);construction(args.output);workflows(args.output)
    write_json(args.output/'benchmark_workflow_sources.json',dict(scope='Protocol/implementation diagrams, not measured superiority',
        source_sha256={name:digest(CASE/'scripts'/name) for name in ('run_benchmark_ppa.py','build_benchmark.py','benchmark_rtl_actions.py')},
        files=['benchmark_platform.svg','benchmark_construction.svg','benchmark_ppa_workflows.svg']))
    print('BENCHMARK_VECTOR_DIAGRAMS_WRITTEN')


if __name__=='__main__':main()
