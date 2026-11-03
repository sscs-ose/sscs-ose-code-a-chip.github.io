"""One non-retryable live C3 qualification with failure feedback and two EDA substitutes."""
import json
from pathlib import Path
import yaml
from chip_nebula.taskgraph.static_cli import run_workflow
from chip_nebula.taskgraph.static_store import StaticTaskGraphStore
from capacity_context import ContextPool
from capacity_graph import freeze
from capacity_accounting_replay import export, replay
from study_portability import private_context
from study_protocol import write_json
from write_capacity_workflows import write

ROOT=Path(__file__).resolve().parents[1]


def probe():
    output=ROOT/'checks/live-c3-sprint'
    private=private_context(ROOT,'submission-sprint-c3')
    if output.exists() or private.exists():raise ValueError('Previous preflight must not be reset or repeated')
    project=output/'project';(project/'spec').mkdir(parents=True)
    (project/'tests').mkdir()
    (project/'tests/delay.py').write_text('import time\ntime.sleep(40)\nprint("ASYNC_FIXTURE_COMPLETE")\n')
    (project/'spec/task.md').write_text('Authorized runtime fixture only. Deliver an identity wire y=a. Physical commands invoke deterministic substitutes, never EDA.\n')
    recipe=write(project,'C3','gpt-6-luna');definition=yaml.safe_load(recipe.read_text())
    instructions={
      'implementation': 'Read inherited reports and rtl/fixture.sv if it exists. On the FIRST implementation create rtl/fixture.sv with module capacity_fixture(input a,output y);assign y=a;endmodule and // initial. Then run exactly python tests/delay.py with yield_time_ms 1000 and await its actual completion. On a FEEDBACK retry, read the physical fixture report and use apply_patch to replace // initial with // repaired without changing y=a. Do not invoke physical or other EDA. Return NEBULA_OUTPUT: {"rtl":{"module":"capacity_fixture"}}.',
      'verification': 'Read rtl/fixture.sv. Confirm y=a regardless of its comment. Write reports/verification/report.json with subject capacity_fixture, verdict passed, repair_summary Identity wire verified. Return NEBULA_OUTPUT: {"report":{"subject":"capacity_fixture","verdict":"passed","repair_summary":"Identity wire verified"}}. Do not edit RTL or invoke physical.',
      'integration_ppa': 'Run exactly capacity-check physical once in a separate tool call. This is a deterministic fixture, not EDA. Read its returned report and write reports/integration_ppa/report.json reflecting its actual verdict. The first fixture deliberately fails until RTL contains // repaired. On failure return NEBULA_OUTPUT: {"report":{"subject":"capacity_fixture","verdict":"failed","repair_summary":"Add // repaired to rtl/fixture.sv; preserve y=a"}}. On pass return the same structure with verdict passed and repair_summary Fixture repaired. Do not edit RTL. Do not invoke physical a second time within this stage.',
      'revision': 'Read the final reports and rtl/fixture.sv. Preserve // repaired and y=a. Return NEBULA_OUTPUT: {"rtl":{"module":"capacity_fixture"}}. No further physical command or changes.'}
    for phase,task in definition['tasks'].items():
        task['intent']=instructions[phase]
        task['max_attempts']=2
        task['execution']['timeout_seconds']=1200
    recipe.write_text(yaml.safe_dump(definition,sort_keys=False))
    for path in (project/'.chip_nebula/roles').glob('*.yaml'):
        role=yaml.safe_load(path.read_text());role['system_prompt']='Tiny runtime qualification fixture, not a chip experiment. Follow only the current stage. Use scoped native tools, no extra models, network or credentials. Keep calls serial. Return the requested NEBULA_OUTPUT JSON.'
        path.write_text(yaml.safe_dump(role,sort_keys=False))
    database=freeze(project,'C3','gpt-6-luna',recipe=recipe)
    pool=ContextPool(private,output/'contexts.json','gpt-6-luna',runtime=dict(record=str(output/'runtime'),limit=500000,active_seconds=1200,scored=False,preflight_fixture='submission-sprint-c3'))
    status=run_workflow(project,database,'capacity',pool,workers=1)
    with StaticTaskGraphStore(database) as store:write_json(output/'graph.json',store.graph_snapshot('capacity'))
    usage=json.loads((output/'runtime/usage.json').read_text())
    contexts=json.loads((output/'contexts.json').read_text())
    fixtures=[json.loads(p.read_text()) for p in sorted((output/'runtime').glob('fixture-physical-*.json'))]
    export(private,output/'runtime',output/'native-accounting.json','gpt-6-luna')
    accounting=replay(output/'native-accounting.json',output/'runtime')
    result=dict(passed=status.value=='complete' and usage['valid'] and accounting['passed'] and len(set(contexts.values()))==3 and [r['status'] for r in fixtures]==['failed','passed'],status=status.value,actual_logical_tokens=usage['actual_tokens'],contexts=len(contexts),model_invocations=len(list((output/'runtime/invocations').glob('*/result.json'))),physical_attempts=0,fixture_physical_calls=len(fixtures),accounting=accounting,scope='Single live public TaskGraph C3 fixture, asynchronous tool completion, independent contexts, failed physical substitute, feedback repair and second substitute; no chip design trial or physical implementation')
    write_json(output/'result.json',result);print(json.dumps(result),flush=True)
    return result


if __name__=='__main__':raise SystemExit(0 if probe()['passed'] else 1)
