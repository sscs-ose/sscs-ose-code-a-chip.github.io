"""RTL-only structure, immutable inputs and elaboration evidence."""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path.cwd()
OUT = ROOT/'reports/verification/structure'
OUT.mkdir(parents=True, exist_ok=True)
sources = (ROOT/'verification/design.f').read_text().splitlines()
cpu = (ROOT/'rtl/rv32i_five_stage_cpu.sv').read_text()
rows = []
def collect_types(node, table):
    if isinstance(node,dict):
        if node.get('type') == 'BASICDTYPE':table[node['addr']] = node
        for value in node.values():collect_types(value,table)
    elif isinstance(node,list):
        for value in node:collect_types(value,table)
for config, top, params in [('base','rv32i_five_stage_cpu',[]),
        ('enabled','rv32i_five_stage_cpu',['-GENABLE_XNEBULA=1']),
        ('top','nebula_cpu_npu_top',[]), ('npu','nebula_npu_dot4',[])]:
    command = ['verilator', '-Wall', '-Wno-UNUSEDSIGNAL', '--json-only', '--top-module', top,
               *params, '-f', 'verification/design.f', '--Mdir', f'build/verify/structure-{config}',
               '--json-only-output', str(OUT/f'{config}.tree.json'),
               '--json-only-meta-output', str(OUT/f'{config}.meta.json')]
    run = (subprocess.CompletedProcess(command, 0) if '--audit-only' in sys.argv
           else subprocess.run(command, text=True, capture_output=True))
    if '--audit-only' not in sys.argv:
        (OUT/f'{config}.log').write_text(run.stdout+run.stderr)
    row = {'configuration': config, 'returncode': run.returncode, 'command': command}
    if run.returncode == 0:
        tree = json.loads((OUT/f'{config}.tree.json').read_text())
        row['modules'] = [m['origName'] for m in tree['modulesp']]
        types = {};collect_types(tree,types)
        row['ports'] = []
        for v in tree['modulesp'][0]['stmtsp']:
            if v.get('varType') != 'PORT':continue
            bounds = types[v['dtypep']].get('range','0:0').split(':')
            width = abs(int(bounds[0])-int(bounds[-1]))+1
            row['ports'].append({'name':v['origName'],'direction':v['direction'].lower(),'width':width})
    rows.append(row)
assert all(r['returncode'] == 0 for r in rows)
assert 'nebula_npu_dot4' not in rows[0]['modules']
assert 'nebula_npu_dot4' in rows[1]['modules'] and 'nebula_npu_dot4' in rows[2]['modules']
assert rows[0]['ports'] == rows[1]['ports'] == rows[2]['ports']
assert sum(p['width'] for p in rows[2]['ports'] if p['direction']=='input') == 69
assert sum(p['width'] for p in rows[2]['ports'] if p['direction']=='output') == 371
expected_npu = [('clk','input',1),('rst_n','input',1),('req_valid','input',1),('req_ready','output',1),
    ('req_a','input',32),('req_b','input',32),('rsp_valid','output',1),('rsp_ready','input',1),
    ('rsp_data','output',32),('kill','input',1)]
assert [(p['name'],p['direction'],p['width']) for p in rows[3]['ports']] == expected_npu
state_inventory = {
    'IF/ID': ['if_v','if_pc','if_word','if_held','if_fault'],
    'ID/EX': ['ex_v','ex'], 'EX/MEM': ['mem_v','mem','mem_sent'], 'MEM/WB': ['wb_v','wb'],
    'register_file': 'logic [31:0] rf [0:31]; combinational id_a/id_b; rising-edge wb_rf_write',
    'reset': 'always_ff @(posedge clk or negedge rst_n)',
    'npu': 'enabled_npu.npu generated only for ENABLE_XNEBULA == 1',
}
for name in ['if_v','if_pc','ex_v','mem_v','wb_v']:
    assert re.search(r'\b'+name+r'\s*<=',cpu), name
assert 'logic [31:0] rf [0:31];' in cpu
assert 'always_ff @(posedge clk or negedge rst_n)' in cpu
assert 'if (wb_rf_write) rf[wb.rd] <= wb.result;' in cpu
frozen = []
for p in ROOT.glob('.nebula_inputs/*/artifact.json'):
    a = json.loads(p.read_text())
    if a['type'] not in ['acceptance.plan','specification.csir','rtl.integration']:
        continue
    for name in a['content']['paths']:
        p = ROOT/name
        data = os.readlink(p).encode() if p.is_symlink() else p.read_bytes()
        reference = subprocess.check_output(['git','show',a['content']['commit']+':'+name])
        assert data == reference, name
        frozen.append({'path':name,'sha256':hashlib.sha256(data).hexdigest()})
report = {'verdict':'passed','scope':'pre-synthesis RTL structure only',
          'state_inventory':state_inventory,'elaboration':rows,'frozen_inputs':frozen,
          'excluded_resources_review': 'CPU source contains decode, flop RF, four token groups and generated NPU; no internal program/data RAM, cache, predictor, divider or CPU M multiply.',
          'downstream': 'Mapped confirmation is AC-SYNTHESIS; no foundry input used.'}
(OUT/'summary.json').write_text(json.dumps(report, indent=2)+'\n')
print('RTL_STRUCTURE_PASS')
