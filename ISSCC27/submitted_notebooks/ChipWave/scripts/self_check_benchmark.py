"""Boundaries and negative controls for task construction and shared launch accounting."""
import itertools
import json
import tempfile
from pathlib import Path

from benchmark_ppa_proposal import validate as validate_proposal
from build_benchmark import validate as validate_task
from campaign_budget import reserve,finish
from study_protocol import BASELINE,write_json


def rejects(call):
    try:call()
    except (ValueError,KeyError):return
    raise AssertionError('Invalid input was accepted')


def run():
    for task in (dict(id='../answer',family='counter',width=8),dict(id='bad',family='counter',width=True),
                 dict(id='bad',family='fifo',width=8,depth=3),dict(id='bad',family='dot',lanes=3),
                 dict(id='bad',family='counter',width=8,extra='hidden')):
        rejects(lambda:validate_task(task))
    allowed=[dict(zip(('operand_isolation','reduce_width'),v)) for v in itertools.product((False,True),repeat=2)]
    candidate=dict(configuration=dict(BASELINE,abc_area=1),rtl_actions=allowed[0],rationale='Common valid action')
    validate_proposal(candidate,[],allowed)
    rejects(lambda:validate_proposal(candidate,[candidate],allowed))
    rejects(lambda:validate_proposal(dict(candidate,rtl_actions=dict(operand_isolation=1,reduce_width=False)),[],allowed))
    rejects(lambda:validate_proposal(dict(candidate,configuration=dict(BASELINE,repair_margin=99)),[],allowed))
    rejects(lambda:validate_proposal(dict(candidate,rtl_actions=allowed[1]),[],allowed[:1]))
    rejects(lambda:validate_proposal(dict(candidate,rationale=''),[],allowed))
    with tempfile.TemporaryDirectory(prefix='chip-benchmark-budget-') as temp:
        root=Path(temp);(root/'ppa').mkdir()
        limits=dict(reference=1,demonstration=1,common_baseline=1,ppa=1,high_frequency=1,preformal_calibration=1,absolute_total=3)
        write_json(root/'launch-ledger.json',dict(limits=limits,launches=[]))
        reserve(root,'ppa','first',root/'candidate-1')
        rejects(lambda:reserve(root,'ppa','first',root/'candidate-2'))
        rejects(lambda:reserve(root,'ppa','second',root/'candidate-2'))
        finish(root,'first',status='failed',evidence='preserved-failure.json')
        rejects(lambda:finish(root,'first',status='qualified',evidence='rewritten.json'))
        rejects(lambda:reserve(root,'ppa','rescue',root/'candidate-3'))
        reserve(root,'reference','reference',root/'reference')
        (root/'ppa/formal-freeze.json').write_text('{}')
        rejects(lambda:reserve(root,'preformal_calibration','late-rescue',root/'late'))
        rejects(lambda:reserve(root,'reference_supplement','unapproved',root/'supplement'))
        reserve(root,'demonstration','demo',root/'demo')
        rejects(lambda:reserve(root,'high_frequency','fourth',root/'fourth'))
        assert len(json.loads((root/'launch-ledger.json').read_text())['launches'])==3
    print(json.dumps(dict(passed=True,model_calls=0,physical_calls=0,
        checks=['task parameter validation','unseen and qualified RTL actions','invalid parameter/bool/empty rationale rejection',
                'duplicate/category/global launch caps','failure consumes budget','terminal ledger immutability','no post-freeze calibration rescue'])))


if __name__=='__main__':run()
