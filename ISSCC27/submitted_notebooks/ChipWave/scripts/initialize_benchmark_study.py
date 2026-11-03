"""Create a new study and task suite without model calls or full physical runs."""
import argparse
import datetime
import json
import random
from pathlib import Path

from build_benchmark import build_task
from study_protocol import digest,write_json

CASE=Path(__file__).resolve().parents[1]


def initialize(output,protocol_path):
    output=Path(output).resolve();protocol_path=Path(protocol_path).resolve()
    if output.exists():raise ValueError('Use a new study directory; prior experiments remain frozen')
    protocol=json.loads(protocol_path.read_text())
    expected=dict(reference=6,demonstration=3,common_baseline=1,ppa=27,high_frequency=4,
                  planned_total=41,preformal_calibration=3,absolute_total=44)
    if protocol['physical_budget']!=expected:raise ValueError('This published study template uses the declared 41+3 physical cap')
    if len(protocol['tasks'])!=6 or len(protocol['ppa_jobs'])!=9:raise ValueError('Study template needs six tasks and nine sessions')
    output.mkdir(parents=True)
    for name in ('checks','benchmark','ppa','baseline','high-frequency','tutorial','reproduction'):
        (output/name).mkdir()
    protocol.update(campaign=output.name,created_at=datetime.datetime.now(datetime.timezone.utc).isoformat())
    write_json(output/'protocol.json',protocol)
    write_json(output/'launch-ledger.json',dict(schema_version=1,limits=expected,launches=[]))
    write_json(output/'progress.json',dict(status='prepared',model_calls=0,full_physical_calls=0,protocol_sha256=digest(output/'protocol.json')))
    for task in protocol['tasks']:build_task(task,output/'benchmark/tasks'/task['id'])
    write_json(output/'benchmark/tasks/suite.json',dict(tasks=protocol['tasks'],families=3,variants=6,qualified=False))
    print('STUDY_PREPARED; model_calls=0; full_physical_calls=0; qualify references before evaluating agents')
    return output


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--protocol',type=Path,default=CASE/'results/benchmark-study/protocol.json')
    args=parser.parse_args();initialize(args.output,args.protocol)
