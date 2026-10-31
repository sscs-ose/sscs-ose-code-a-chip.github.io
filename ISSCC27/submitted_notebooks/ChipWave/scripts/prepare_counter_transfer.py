"""Prepare a new counter contract using the same designer/verifier/auditor topology."""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

import yaml

from chip_nebula.taskgraph.domain import Artifact,ArtifactContent,ArtifactProducer,TaskBrief
from chip_nebula.taskgraph.static_cli import load_compiled_recipe
from chip_nebula.taskgraph.static_store import StaticTaskGraphStore
from study_protocol import MODEL,digest,write_json

CONTRACT='''Create synthesizable SystemVerilog module counter.
Ports: input clk,rst_n,en,load; input [7:0] load_value;
output [7:0] count; output overflow.
Active-low asynchronous reset sets both outputs to zero immediately.
On rising clock edges, load has priority over en: load sets count to
load_value and overflow to zero. Otherwise en increments count modulo 256,
with overflow=1 exactly when that edge wraps previous count 255 to zero.
With neither load nor en, hold count and clear overflow to zero.
overflow is a one-cycle wrap event, not a sticky status bit.
'''


def bench(full):
    values='i' if full else '(i==0 ? 0 : i==1 ? 1 : i==2 ? 254 : i==3 ? 255 : (i*17)%256)'
    return '''`timescale 1ns/1ps
module counter_check_tb;
  logic clk=0,rst_n=0,en=0,load=0;
  logic [7:0] load_value=0;
  wire [7:0] count;
  wire overflow;
  integer value,checks=0;
  counter dut(.*);
  always #5 clk=~clk;
  task automatic tick; @(posedge clk); #1; endtask
  task automatic expect_value(input integer expected,input bit event_bit);
    if(count !== 8'(expected) || overflow !== event_bit)
      $fatal(1,"counter mismatch got=%0d overflow=%b expected=%0d event=%b",count,overflow,expected,event_bit);
    checks++;
  endtask
  initial begin
    #1; rst_n=1; #1; rst_n=0; #1; expect_value(0,0);
    @(negedge clk);rst_n=1;
    for(integer i=0;i<''' + ('256' if full else '16') + ''';i++)begin
      value='''+values+''';
      @(negedge clk);load=1;en=1;load_value=8'(value);
      tick();expect_value(value,0);
      @(negedge clk);load=0;en=0;
      repeat(2)begin tick();expect_value(value,0);end
      @(negedge clk);en=1;
      tick();expect_value((value+1)%256,value==255);
      tick();expect_value((value+2)%256,value==254);
      @(negedge clk);load=1;en=0;load_value=255;
      tick();expect_value(255,0);
      @(negedge clk);load=0;en=1;
      tick();expect_value(0,1);
      @(negedge clk);en=0;
      tick();expect_value(0,0);
    end
    @(negedge clk);load=1;load_value=93;tick();expect_value(93,0);
    @(negedge clk);#1;rst_n=0;#1;expect_value(0,0);
    $display("COUNTER_CHECK_PASS checks=%0d",checks);$finish;
  end
  initial begin #100000;$fatal(1,"counter timeout");end
endmodule
'''


def prepare(root):
    root=Path(root).resolve()
    if root.exists():raise ValueError('Existing transfer project retained')
    for name in ('spec','rtl','tb','tools','tests/designer','tests/reviewer','reports','.chip_nebula/roles','.chip_nebula/recipes'):
        (root/name).mkdir(parents=True,exist_ok=True)
    (root/'spec/counter.md').write_text(CONTRACT)
    (root/'tb/counter_smoke_tb.sv').write_text(bench(False))
    smoke='''from pathlib import Path
import subprocess
root=Path.cwd();out=root/'build/smoke';out.mkdir(parents=True,exist_ok=True)
sources=sorted(root.glob('rtl/**/*.sv'))+sorted(root.glob('rtl/**/*.v'))
subprocess.run(['iverilog','-g2012','-s','counter_check_tb','-o',str(out/'sim'),*map(str,sources),'tb/counter_smoke_tb.sv'],check=True)
subprocess.run(['vvp',str(out/'sim')],check=True,timeout=60)
'''
    (root/'tools/smoke.py').write_text(smoke)
    (root/'tools/audit.py').write_text('''import json,subprocess
from pathlib import Path
r=subprocess.run(['python3','tools/smoke.py'],text=True,capture_output=True,timeout=90)
out=Path('build/audit');out.mkdir(parents=True,exist_ok=True);(out/'audit.log').write_text(r.stdout+r.stderr)
report={'subject':'counter-rtl','verdict':'passed' if r.returncode==0 and 'COUNTER_CHECK_PASS' in r.stdout else 'failed','repair_summary':(r.stdout+r.stderr)[-10000:]}
(out/'report.json').write_text(json.dumps(report,indent=2)+chr(10));print('NEBULA_OUTPUT: '+json.dumps({'report':report}))
''')
    design='''Read spec/counter.md and implement the complete counter in rtl/.
Develop with python3 tools/smoke.py and optional tests/designer/ tests.
Write only rtl/, tests/designer/ and build/. Preserve the supplied contract,
checker and workflow. Do not access other projects, credentials or final
evaluators, and do not invoke additional agents/models. Repair actionable
feedback within your original task. End with NEBULA_OUTPUT: {"rtl":{"module":"counter"}}.
'''
    review='''Independently review and test the delivered counter against spec/counter.md.
Run python3 tools/smoke.py, inspect boundary behavior, and optionally add tests
under tests/reviewer/. Do not change RTL, the contract or supplied checker,
read other projects/final evaluators, access credentials, or invoke extra
agents/models. Write reports/review.json with subject, passed/failed verdict
and actionable repair_summary. Return those same fields in
NEBULA_OUTPUT: {"report":{"subject":"counter-rtl","verdict":"passed or failed","repair_summary":"findings"}}.
Choose an actual verdict; your budget is shared with the designer.
'''
    definitions={'study-designer':(design,['specification.source','verification.report'],['rtl.snapshot']),
                 'study-verifier':(review,['specification.source','rtl.snapshot'],['verification.report']),
                 'study-auditor':('Replay the public checker and preserve its real outcome.',['rtl.snapshot','verification.report'],['verification.report'])}
    for name,(prompt,accepted,produced) in definitions.items():
        (root/'.chip_nebula/roles'/f'{name}.yaml').write_text(yaml.safe_dump(dict(name=name,version=1,system_prompt=prompt,
             accepted_types=accepted,produced_types=produced,framework='codex',model=MODEL),sort_keys=False))
    source={'type':'specification.source','from':'$parameters.source'}
    rtl={'type':'rtl.snapshot','from':'$tasks.designer.outputs.rtl'}
    tools=['python3','iverilog','vvp','verilator','git','make']
    permission=lambda write:dict(read=['spec/**','rtl/**','tb/**','tools/**','tests/**','reports/**','build/**'],write=write,tools=tools)
    tasks={
      'designer':dict(role='study-designer',intent=design,permission=permission(['rtl/**','tests/designer/**','build/**']),
        inputs={'source':source},outputs={'rtl':dict(type='rtl.snapshot',paths=['rtl/**'])},max_attempts=8,
        execution=dict(framework='codex',model=MODEL,reasoning_effort='high',timeout_seconds=1200)),
      'verifier':dict(role='study-verifier',intent=review,permission=permission(['tests/reviewer/**','reports/**','build/**']),
        inputs={'source':source,'rtl':rtl},outputs={'report':dict(type='verification.report',paths=['reports/**','tests/reviewer/**'])},max_attempts=8,
        execution=dict(framework='codex',model=MODEL,reasoning_effort='high',timeout_seconds=1200)),
      'audit':dict(role='study-auditor',intent='Replay unchanged public counter tests.',permission=permission(['build/**']),
        inputs={'rtl':rtl,'review':{'type':'verification.report','from':'$tasks.verifier.outputs.report','release':{'field':'verdict','equals':'passed'}}},
        outputs={'report':dict(type='verification.report',paths=['build/audit/**'])},max_attempts=8,
        execution=dict(executor='tool',command='python3 tools/audit.py',timeout_seconds=120))}
    feedback=[dict(source=name,verdict='fail',target='designer',kind='feedback',summary='Repair the reported counter defect.',
                   summary_field='report.repair_summary',propagate=True) for name in ('verifier','audit')]
    recipe=root/'.chip_nebula/recipes/counter-transfer.yaml'
    recipe.write_text(yaml.safe_dump(dict(name='counter-transfer',version=2,parameters={'source':'specification.source'},tasks=tasks,feedback=feedback),sort_keys=False))
    (root/'.gitignore').write_text('.chip_nebula/\nbuild/\n__pycache__/\n*.pyc\n')
    def git(*args):return subprocess.run(['git',*args],cwd=root,text=True,capture_output=True,check=True).stdout.strip()
    for args in (('init','-q'),('config','user.name','ChipWave transfer automation'),('config','user.email','automation@chipwave.invalid'),
                 ('add','.'),('add','-f','.chip_nebula/roles','.chip_nebula/recipes'),('commit','-qm','Freeze new counter contract and reused collaboration topology')):git(*args)
    commit,tree=git('rev-parse','HEAD'),git('rev-parse','HEAD^{tree}')
    compiled=load_compiled_recipe(recipe,workflow_id='counter-transfer',goal='Reuse the configurable workflow on a new counter contract',
                                  parameters={'source':'counter-contract'},baseline_commit=commit,workers=1)
    artifact=Artifact(id='counter-contract',type='specification.source',schema_version=1,
        producer=ArtifactProducer('external','counter-contract','frozen-input','study-author',1),
        content=ArtifactContent('git',commit,tree,('spec','tb','tools')),
        payload=dict(source_name='Loadable enabled wrapping counter',media_type='text/markdown',content=CONTRACT,
                     content_digest='sha256:'+digest(root/'spec/counter.md'),received_at='2026-10-16T00:00:00+00:00'))
    briefs={task.id:TaskBrief(objective=task.intent,deliverables=tuple(o.name+': '+o.artifact_type for o in task.outputs),
        responsibilities=('Read the fixed counter contract and use actual test evidence.',),exclusions=('No contract, checker, permissions or IP changes.',),
        completion_criteria=('Deliver correct RTL or an honest actionable verification report.',),
        collaboration=tuple('task:'+other.id for other in compiled.tasks if other.id!=task.id)) for task in compiled.tasks}
    with StaticTaskGraphStore(root/'.chip_nebula/shared/memory/taskgraph-v2.db') as store:
        store.create_workflow(compiled.workflow,compiled.roles,compiled.tasks,[artifact],compiled.joint_analysis_groups,compiled.feedback_routes)
        store.freeze_briefs('counter-transfer',briefs)
    git('update-ref','refs/chip-nebula/artifacts/counter-contract',commit)
    write_json(root/'frozen-transfer.json',{'source_sha256':digest(root/'spec/counter.md'),'public_checker_sha256':digest(root/'tb/counter_smoke_tb.sv'),
               'topology':'designer -> independent verifier -> common tool audit; failed reports return to original designer','hidden_planner_calls':0})
    return compiled


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--project',type=Path,required=True)
    prepare(p.parse_args().project)
