"""Shared, finite NPU actions; qualify correctness before any workflow search."""
from __future__ import annotations

import argparse
import itertools
import json
import shutil
import subprocess
import time
from pathlib import Path

from study_protocol import digest, write_json

CASE = Path(__file__).resolve().parents[1]
NPU = 'rtl/npu/nebula_npu_dot4.sv'
ACTIONS = ('operand_isolation', 'reduce_width')


def transform(source, *, operand_isolation=False, reduce_width=False):
    """Mechanical source actions; no search-specific manual RTL editing."""
    if operand_isolation:
        anchor = '    assign req_ready = rst_n && !kill && (phase == IDLE);'
        assert source.count(anchor) == 1
        source = source.replace(anchor, '''    wire accept_operands = rst_n && !kill && (phase == IDLE) && req_valid;
    wire [31:0] multiply_a = accept_operands ? req_a : 32'b0;
    wire [31:0] multiply_b = accept_operands ? req_b : 32'b0;
''' + anchor)
        source = source.replace('$signed(req_a[8*lane +: 8])', '$signed(multiply_a[8*lane +: 8])')
        source = source.replace('$signed(req_b[8*lane +: 8])', '$signed(multiply_b[8*lane +: 8])')
    if reduce_width:
        anchor = '    logic signed [16:0] pair_sum [0:1];'
        assert source.count(anchor) == 1
        source = source.replace(anchor, anchor + '''
    wire signed [17:0] reduced_sum = $signed({pair_sum[0][16], pair_sum[0]})
                                   + $signed({pair_sum[1][16], pair_sum[1]});''')
        anchor = '''rsp_data <= $signed({{15{pair_sum[0][16]}}, pair_sum[0]})
                              + $signed({{15{pair_sum[1][16]}}, pair_sum[1]});'''
        assert source.count(anchor) == 1
        source = source.replace(anchor, 'rsp_data <= {{14{reduced_sum[17]}}, reduced_sum};')
    return source


def materialize(output, actions):
    if set(actions) != set(ACTIONS) or any(type(v) is not bool for v in actions.values()):
        raise ValueError('Both common RTL action flags must be explicit booleans')
    output = Path(output)
    if output.exists():
        raise ValueError('Existing candidate RTL is retained')
    output.mkdir(parents=True)
    for source in (CASE / 'released_design/rtl').rglob('*'):
        if source.is_file():
            target = output / source.relative_to(CASE / 'released_design')
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
    (output / NPU).write_text(transform((output / NPU).read_text(), **actions))
    original = json.loads((CASE / 'released_design/selected-delivery.json').read_text())
    original.update(id='shared-rtl-actions-' + ''.join(str(int(actions[k])) for k in ACTIONS),
                    exported_source_sha256={str(p.relative_to(output)): digest(p) for p in sorted((output / 'rtl').rglob('*.sv'))},
                    rtl_actions=actions, scope='Mechanical shared actions; unchanged CPU and integration RTL')
    write_json(output / 'selected-delivery.json', original)
    return original


def formal(reference, candidate, output):
    output.mkdir(parents=True, exist_ok=False)
    script = f'''read_verilog -sv {reference}
rename nebula_npu_dot4 gold
read_verilog -sv {candidate}
rename nebula_npu_dot4 gate
proc
memory_map
opt
async2sync
equiv_make gold gate equivalence
hierarchy -top equivalence
equiv_simple
equiv_induct -seq 8
equiv_status -assert
'''
    (output / 'prove.ys').write_text(script)
    start = time.monotonic()
    with (output / 'proof.log').open('w') as log:
        result = subprocess.run(['yosys', '-Q', '-T', '-s', str(output / 'prove.ys')], stdout=log, stderr=subprocess.STDOUT, timeout=600)
    passed = result.returncode == 0 and 'Equivalence successfully proven!' in (output / 'proof.log').read_text()
    record = dict(passed=passed, exit_code=result.returncode, seconds=time.monotonic()-start,
                  reference_sha256=digest(reference), candidate_sha256=digest(candidate),
                  script_sha256=digest(output / 'prove.ys'), method='Yosys equiv_simple + temporal induction; async2sync on both designs',
                  scope='NPU outputs and matched state points; synchronous observation, reset/kill and handshake inputs unrestricted')
    write_json(output / 'proof.json', record)
    return record


def qualify(output):
    output = Path(output).resolve()
    if output.exists():
        raise ValueError('Previous action qualification retained')
    output.mkdir(parents=True)
    started = time.monotonic()
    rows = []
    for values in itertools.product((False, True), repeat=2):
        if not any(values):
            continue
        actions = dict(zip(ACTIONS, values))
        name = ''.join(str(int(v)) for v in values)
        source = output / name / 'source'
        materialize(source, actions)
        proof = formal(CASE / 'released_design' / NPU, source / NPU, output / name / 'formal')
        rows.append(dict(actions=actions, proof=proof, source=str(source.relative_to(output))))
    negative = output / 'negative'
    negative.mkdir()
    bad = (CASE / 'released_design' / NPU).read_text().replace('phase <= PRODUCTS;', 'phase <= RESPONSE;')
    (negative / 'bad.sv').write_text(bad)
    control = formal(CASE / 'released_design' / NPU, negative / 'bad.sv', negative / 'formal')
    record = dict(schema_version=1, combinations=rows, wrong_latency_rejected=not control['passed'],
                  action_library_qualified=all(row['proof']['passed'] for row in rows) and not control['passed'],
                  preparation_seconds=time.monotonic()-started, physical_calls=0, model_calls=0,
                  integration_checks='pending; formal alone is not full admission',
                  qualification_policy='Correctness only; no PPA screening and no workgroup-specific action')
    write_json(output / 'qualification.json', record)
    print(json.dumps(record, indent=2), flush=True)
    if not record['action_library_qualified']:
        raise RuntimeError('Shared RTL action correctness qualification failed')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--qualify', type=Path, required=True)
    qualify(parser.parse_args().qualify)
