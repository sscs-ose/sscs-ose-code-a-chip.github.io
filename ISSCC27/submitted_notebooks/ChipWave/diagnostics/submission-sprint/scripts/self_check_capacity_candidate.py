"""Actual preprocessing/elaboration and hostile-input admission checks; no model or physical run."""
import json
import shutil
import tempfile
from pathlib import Path

from capacity_candidate import ROOT, admit, configuration, clean_preprocessed
from study_protocol import write_json
from qualify_capacity_tasks import simulate


def check():
    rows = []
    with tempfile.TemporaryDirectory(prefix='capacity-candidate-') as tmp:
        root = Path(tmp)
        for task in ('A1', 'A2', 'B1', 'B2'):
            snapshot = root/task
            (snapshot/'rtl').mkdir(parents=True)
            shutil.copy2(ROOT/'tasks'/task/'grader/reference.sv', snapshot/'rtl/design.sv')
            receipt = admit(snapshot, task, root/(task+'-admitted'))
            assert receipt['passed'] and receipt['task'] == task
            replay = simulate(root/(task+'-admitted/design.sv'), ROOT/'tasks'/task/'grader/final_tb.sv',
                              root/(task+'-normalized-replay'))
            assert replay['passed'], replay
            rows.append(dict(task=task, passed=True, canonical_function_replay_passed=True))
        snapshot = root/'A1'
        original = (snapshot/'rtl/design.sv').read_text()
        faults = {
            'direct_file_access': original+'\nmodule extra; initial $readmemh("secret", a); endmodule\n',
            'macro_system': '`define ESCAPE $system\n'+original+'\nmodule extra; initial `ESCAPE("true"); endmodule\n',
            'frozen_neighbor': original+'\nmodule rv32i_five_stage_cpu; endmodule\n',
            'wrong_port': original.replace('input wire clk', 'input wire BAD_clk').replace('input logic clk', 'input logic BAD_clk'),
            'outside_include': '`include "'+str(ROOT/'tasks/A1/grader/reference.sv')+'"\n',
        }
        # The task generator uses compact declarations; change one name independently of spacing.
        import re
        faults['wrong_port'] = re.sub(r'\bclk\b', 'BAD_clk', original)
        for name, code in faults.items():
            (snapshot/'rtl/design.sv').write_text(code)
            try:
                admit(snapshot, 'A1', root/name)
            except ValueError:
                rows.append(dict(rejected=name))
            else:
                raise AssertionError('Unsafe or wrong-interface source accepted: '+name)
        (snapshot/'rtl/design.sv').write_text(original)
        (snapshot/'configuration').mkdir()
        (snapshot/'configuration/implementation.json').write_text(json.dumps(dict(
            utilization=40, density=.55, area_synthesis=False, repair_margin=20, clock_period=100)))
        try:
            configuration(snapshot)
        except ValueError:
            pass
        else:
            raise AssertionError('Frozen clock made configurable')
        canonical, _ = clean_preprocessed('module okay; /* verilator sc_bv */ // synthesis translate_off\nendmodule')
        assert 'verilator' not in canonical and 'translate_off' not in canonical
        for unsafe in ('import "DPI-C" function int host();', 'bind cpu evil x();'):
            try:
                clean_preprocessed(unsafe)
            except ValueError:
                pass
            else:
                raise AssertionError('Host operation accepted')
    report = dict(passed=True, rows=rows, model_calls=0, physical_attempts=0,
                  scope='Actual Icarus preprocessing and pinned Yosys elaboration; no hidden checker mounted')
    write_json(ROOT/'checks/candidate-admission.json', report)
    return report


if __name__ == '__main__':
    print(json.dumps(check()))
