"""Small negative controls for study fairness, ranking and clock/source binding."""
from __future__ import annotations

import copy
import itertools
import json
import subprocess
import tempfile
import sys
import time
from types import SimpleNamespace
from unittest.mock import patch
from pathlib import Path

from check_postroute_waveforms import check
from run_postroute_workloads import ROOT, source_views
from audit_parasitics import audit
from evaluate_study_physical import evaluate, checked
from study_protocol import BASELINE, DOMAINS, WORKLOADS, config_tuple, digest, preregistration, rule_candidate, score, write_json
from study_budget import BudgetPool, AgentPoolManager, AgentResult


def rejects(function, *args):
    try:
        function(*args)
    except (ValueError, AssertionError, KeyError):
        return
    raise AssertionError('Negative control was accepted: ' + function.__name__)


def run():
    plan = preregistration()
    jobs = plan['generation']['jobs']
    assert len(jobs) == 12 and len({j['id'] for j in jobs}) == 12
    assert all(sum(j['input'] == entry and j['roles'] == roles for j in jobs) == 3
               for entry, roles in itertools.product(('fresh', 'ip'), ('single', 'multi')))
    assert plan == preregistration() and len(list(itertools.product(*DOMAINS))) == 36
    assert len(plan['ppa']['sessions']) == 7
    for bad in (dict(BASELINE, abc_area=True), dict(BASELINE, density=float('nan')),
                dict(BASELINE, utilization=40.0), dict(BASELINE, utilization=60),
                dict(BASELINE, extra=1)):
        rejects(config_tuple, bad)
    energies = dict.fromkeys(WORKLOADS, 1.0)
    assert score(10, energies, 10, energies)['score'] == 1
    assert score(5, energies, 10, energies)['score'] == 0.5
    rejects(score, 10, {'DOT64': 1}, 10, energies)
    rejects(score, 10, dict(energies, DOT64=0), 10, energies)
    initial = dict(configuration=BASELINE, rank_eligible=True, score=1.0, energy_ratio=1.0,
                   cell_area_um2=10, candidate_index=0)
    proposal, reason = rule_candidate([initial])
    assert proposal == dict(BASELINE, abc_area=1) and reason['rule'] == 'qualified_incumbent'
    failed = dict(initial, rank_eligible=False, failure_classes=['electrical'])
    assert rule_candidate([failed])[0] == dict(BASELINE, repair_margin=10)
    assert rule_candidate([dict(failed, failure_classes=['drc'])])[0] == dict(BASELINE, utilization=30)
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        write_json(root/'summary.json', {'physical_qualified': False, 'configuration': BASELINE,
            'manifest': {'period_ps': 10526}, 'physical_wall_seconds': 1.0, 'failure_classes': []})
        log = root/'evidence/orfs-work/logs/fake/6_report.json'
        write_json(log, {'finish__timing__setup__ws': -0.1, 'finish__timing__hold__ws': 0.1,
                         'finish__timing__drv__max_slew': 1, 'finish__timing__drv__max_cap': 0,
                         'finish__timing__drv__max_fanout': 0})
        result = evaluate(root)
        assert not result['rank_eligible'] and set(result['failure_classes']) == {'physical_execution', 'timing', 'electrical'}
        assert not result['energy_j'] and 'score' not in result
        rejects(evaluate, root)
        allocations=[]
        def fake_role(_pool,task,workspace,**kwargs):
            control=json.loads(Path(task.timeout_control_path).read_text())
            assert control['base_timeout_seconds']==task.timeout and control['extension_seconds']==0
            allocations.append((task.assigned_agent,task.timeout))
            return AgentResult(success=True)
        pool=BudgetPool(root/'shared-budget.json',seconds=20)
        with patch.object(AgentPoolManager,'dispatch',fake_role),patch('study_budget.time.monotonic',side_effect=[100,118.5,120,121.2]):
            for i,role in enumerate(('study-designer','study-verifier')):
                task=SimpleNamespace(assigned_agent=role,timeout_control_path=str(root/f'control-{i}.json'),run_id=str(i))
                assert pool.dispatch(task,root).success
        assert allocations==[('study-designer',20),('study-verifier',1)]
        assert not pool.dispatch(task,root).success and len(allocations)==2
        assert abs(json.loads((root/'shared-budget.json').read_text())['used_agent_seconds']-19.7)<1e-8
        pid_file = root/'child.pid'
        code = ('import subprocess,sys,time; from pathlib import Path; '
                'p=subprocess.Popen([sys.executable,"-c","import time;time.sleep(20)"]); '
                f'Path({str(pid_file)!r}).write_text(str(p.pid)); time.sleep(20)')
        result = checked([sys.executable, '-c', code], root/'timeout.log', time.monotonic()+1)
        assert result['timed_out'] and result['exit_code'] != 0 and pid_file.exists()
        import psutil
        try:
            child = psutil.Process(int(pid_file.read_text()))
            assert child.status() == psutil.STATUS_ZOMBIE or not child.is_running()
        except psutil.NoSuchProcess:
            pass
    for period in (100000, 10526, 10000):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / 'source'; source.mkdir()
            files = []
            for name, content in (('6_final.v', 'module dut(); endmodule\n'), ('6_final.spef', '*SPEF "IEEE 1481-1998"\n'),
                                  ('6_final.sdc', f'create_clock -name clk -period {period / 1000:g} [get_ports clk]\n')):
                (source / name).write_text(content)
                files.append(dict(path=name, sha256=digest(source / name)))
            write_json(source / 'selected-delivery.json', {'id': 'test-only-source', 'collected_files': files})
            assert source_views(source)['period_ps'] == period
            (source/'6_final.odb').write_bytes(b'test database')
            selected=json.loads((source/'selected-delivery.json').read_text())
            selected['content']={'commit':'test-commit'}
            write_json(source/'selected-delivery.json',selected)
            views={name:dict(path=filename,sha256=digest(source/filename)) for name,filename in
                   (('netlist','6_final.v'),('spef','6_final.spef'),('sdc','6_final.sdc'),('database','6_final.odb'))}
            attestation=dict(source_delivery=selected['id'],source_commit='test-commit',views=views,
                snapshot_id='derived-test',liberty_sha256=digest(ROOT/'toolchain/orfs/flow/platforms/sky130hd/lib/sky130_fd_sc_hd__tt_025C_1v80.lib'))
            write_json(source/'measurement-source.json',attestation)
            assert source_views(source)['snapshot']['snapshot_id']=='derived-test'
            bad=copy.deepcopy(attestation);bad['source_commit']='other-commit'
            write_json(source/'measurement-source.json',bad);rejects(source_views,source)
            write_json(source/'measurement-source.json',attestation)
            (source/'6_final.odb').write_bytes(b'changed database');rejects(source_views,source)
            (source/'measurement-source.json').unlink()
            (source / '6_final.v').write_text('changed')
            rejects(source_views, source)

            lines = ['$timescale 1ps $end', '$scope module tb_cpu_elf $end',
                     '$var wire 1 c clk $end', '$var wire 1 r rst_n $end',
                     '$upscope $end', '$enddefinitions $end', '#0', '0c', '0r']
            for i in range(20):
                lines += [f'#{i * period + period // 2}', '1c', f'#{(i + 1) * period}', '0c']
                if i == 2: lines.append('1r')
            rows = []
            for workload in WORKLOADS:
                vcd = root / (workload + '.vcd'); vcd.write_text('\n'.join(lines) + '\n')
                rows.append(dict(workload=workload, vcd=vcd.name, vcd_sha256=digest(vcd),
                                 activity_start_ps=3 * period, activity_end_ps=19 * period))
            summary = dict(clock_period_ns=period / 1000, clock_duty_percent=50,
                           reset_low_ns=3 * period / 1000, rows=rows)
            write_json(root / 'summary.json', summary)
            result = check(root)
            assert all(row['measured_clock_period_ps'] == period for row in result['rows'])
            wrong = copy.deepcopy(summary); wrong['clock_period_ns'] += 0.002
            write_json(root / 'summary.json', wrong); rejects(check, root)
            wrong = copy.deepcopy(summary); wrong['rows'][0]['activity_start_ps'] += period
            write_json(root / 'summary.json', wrong); rejects(check, root)
    with tempfile.TemporaryDirectory() as temporary:
        root=Path(temporary)
        bench=root/'fractional.sv'
        bench.write_text('`timescale 1ns/1ps\nmodule fractional; initial begin #31.578; $display("ACTIVITY_START_PS=%0t",$realtime); end endmodule\n')
        subprocess.run(['iverilog','-g2012','-s','fractional','-o',str(root/'sim'),str(bench)],check=True)
        assert 'ACTIVITY_START_PS=31578' in subprocess.check_output(['vvp',str(root/'sim')],text=True)
        library=ROOT/'toolchain/orfs/flow/platforms/sky130hd/lib/sky130_fd_sc_hd__tt_025C_1v80.lib'
        netlist=root/'test.v';report=root/'report.rpt'
        netlist.write_text('module test(input a,b,output y);\n wire unused_sum;\n sky130_fd_sc_hd__ha_1 h (.A(a),.B(b),.COUT(y),.SUM(unused_sum));\nendmodule\n')
        report.write_text('Found 1 unannotated drivers.\n h/SUM\nFound 0 partially unannotated drivers.\n')
        assert audit(report,netlist,library)['passed']
        report.write_text('Found 1 unannotated drivers.\n h/SUM\nFound 1 partially unannotated drivers.\n h/COUT\n')
        assert not audit(report,netlist,library)['passed']
        report.write_text('Found 1 unannotated drivers.\n h/SUM\nFound 0 partially unannotated drivers.\n')
        netlist.write_text(netlist.read_text().replace('endmodule','assign y = unused_sum;\nendmodule'))
        assert not audit(report,netlist,library)['passed']
    print('STUDY_SELF_CHECK_PASS: 12-cell schedule, 36 parameter tuples, W0, score, immutable source and 10/95/100 MHz waveform negative controls')


if __name__ == '__main__':
    run()
