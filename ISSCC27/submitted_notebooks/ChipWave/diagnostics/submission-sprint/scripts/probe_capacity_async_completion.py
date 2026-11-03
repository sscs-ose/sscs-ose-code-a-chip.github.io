"""A tiny live asynchronous tool fixture, no chip-design or physical attempts."""
import json
from pathlib import Path

from capacity_runtime import run
from capacity_accounting_replay import export, replay
from study_portability import private_context
from study_protocol import write_json

ROOT=Path(__file__).resolve().parents[1]


def probe():
    output=ROOT/'checks/native-async-completion-v1'
    private=private_context(ROOT,'capacity-async-completion-v1')
    if output.exists() or private.exists():raise ValueError('Previous fixture is immutable')
    work=output/'project'
    for name in ('rtl','configuration','tests','reports','build','spec'):(work/name).mkdir(parents=True)
    (work/'rtl/probe.sv').write_text('module probe(input a,output y);assign y=a;endmodule\n')
    (work/'tests/delay.py').write_text('import time\ntime.sleep(40)\nprint("ASYNC_HOST_DONE")\n')
    config=dict(record=str(output/'runtime'),private=str(private),project=str(work),workspace=str(work),
                model='gpt-6-luna',limit=300000,active_seconds=180,scored=False)
    result,_=run(config,
        'This is a tiny authorized runtime qualification fixture, not a chip experiment. '
        'Run exactly python tests/delay.py using exec_command with yield_time_ms 1000. '
        'The script sleeps 40 seconds then prints ASYNC_HOST_DONE. Await its actual completion '
        'using functions.wait if the exec cell yields. Do not terminate it. '
        'Then in a separate tool call run exactly cat rtl/probe.sv. '
        'Then use apply_patch to append // reviewed to that file without changing its module. '
        'Finally run exactly capacity-check status in a separate call and stop. '
        'No EDA, model calls, network, credentials or other edits.')
    packet=output/'accounting.json'
    export(private,output/'runtime',packet,config['model'])
    accounting=replay(packet,output/'runtime')
    captures=list((output/'runtime/tools/snapshots').glob('*/capture.json'))
    report=dict(passed=result['passed'] and accounting['passed']
        and '// reviewed' in (work/'rtl/probe.sv').read_text()
        and any(json.loads(p.read_text()).get('capture_phase')=='after_controlled_tool' for p in captures),
        control=result,accounting=accounting,model_invocations=1,physical_attempts=0,
        scope='Real native 40-second asynchronous fixture, subsequent read/patch/status and offline accounting replay; not a design trial')
    write_json(output/'result.json',report)
    print(json.dumps(report),flush=True)
    return report


if __name__=='__main__':raise SystemExit(0 if probe()['passed'] else 1)
