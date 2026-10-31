#!/usr/bin/env python3
"""Check bounded floorplan changes without running models or EDA."""
from pathlib import Path
import json
import os
import tempfile
import run_ppa_search
from prepare_replay_physical import render_configuration
from publish_ppa_results import comparison_metrics


def self_check():
    original='export CORE_UTILIZATION = 10\nexport PLACE_DENSITY = 0.55\nexport ABC_AREA = 1\nexport SDC_FILE = frozen.sdc\n'
    assert render_configuration(original)==original
    candidate=render_configuration(original,40,0.55)
    assert candidate==original.replace('CORE_UTILIZATION = 10','CORE_UTILIZATION = 40')
    repaired=render_configuration(original,30,0.55,10,10)
    assert repaired==original.replace('CORE_UTILIZATION = 10','CORE_UTILIZATION = 30')+'export CAP_MARGIN = 10\nexport SLEW_MARGIN = 10\n'
    assert render_configuration(repaired,30,0.55,20,20)==repaired.replace('MARGIN = 10','MARGIN = 20')
    for value in (True,-1,51,1.5):
        try:render_configuration(original,30,0.55,value,10)
        except ValueError:pass
        else:raise AssertionError('Invalid repair margin accepted')
    try:render_configuration(repaired+'export CAP_MARGIN = 20\n',30,0.55,10,10)
    except ValueError:pass
    else:raise AssertionError('Duplicate repair margin accepted')
    for util,density in ((True,None),(4,None),(71,None),(None,True),(None,float('nan')),(None,float('inf')),(None,0.29),(None,0.81)):
        try:render_configuration(original,util,density)
        except ValueError:pass
        else:raise AssertionError('Out-of-contract parameter accepted')
    for malformed in (original.replace('export CORE_UTILIZATION = 10\n',''),original+'export CORE_UTILIZATION = 20\n'):
        try:render_configuration(malformed,40,0.55)
        except ValueError:pass
        else:raise AssertionError('Missing/ambiguous physical parameter accepted')
    root=Path(__file__).resolve().parents[1]
    physical=json.loads((root/'results/physical.json').read_text())
    raw=json.loads((root/'results/physical-main/orfs-work/logs/sky130hd/nebula_cpu_npu_top/nebula/6_report.json').read_text())
    comparison_metrics(physical,raw)
    for key,value in [('finish__power__total',float('nan')),('finish__design__die__area',0),
                      ('finish__timing__fmax',-1),('finish__design__die__area',physical['metrics']['die_area_um2']+1)]:
        altered=dict(raw);altered[key]=value
        try:comparison_metrics(physical,altered)
        except ValueError:pass
        else:raise AssertionError('Invalid or contradictory physical measurement accepted')
    saved={key:os.environ.get(key) for key in ('ORFS_ROOT','NUM_CORES')}
    prepare=run_ppa_search.prepare
    class StopBeforeTools(Exception):pass
    def check_environment(*args,**kwargs):
        assert os.environ['ORFS_ROOT']==str(root/'toolchain/orfs')
        assert os.environ['NUM_CORES']=='2'
        raise StopBeforeTools
    try:
        os.environ.update(ORFS_ROOT='/incorrect-caller-flow',NUM_CORES='99')
        run_ppa_search.prepare=check_environment
        with tempfile.TemporaryDirectory(prefix='ppa-environment-check-') as temporary:
            try:run_ppa_search.search(Path(temporary)/'study')
            except StopBeforeTools:pass
            else:raise AssertionError('Preparation boundary was not checked')
    finally:
        run_ppa_search.prepare=prepare
        for key,value in saved.items():
            if value is None:os.environ.pop(key,None)
            else:os.environ[key]=value
    print('PPA_SELF_CHECK_PASS: bounded configuration edits and original-report metric validation, including negative cases')
    print('PPA_ENVIRONMENT_CHECK_PASS: incorrect caller flow/thread settings corrected before preparation; no model or EDA run')


if __name__=='__main__':self_check()
