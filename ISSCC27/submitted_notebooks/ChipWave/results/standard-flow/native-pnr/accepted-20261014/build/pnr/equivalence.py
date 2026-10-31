import hashlib
import json
from pathlib import Path
import subprocess

root = Path(__file__).resolve().parents[2]
c = json.loads((root / 'physical/chip-nebula/implementation.constraints.json').read_text())
lib = Path(c['view_binding']['views'][c['view_binding']['liberty']]['installed_path'])
gold = root / 'build/synth/nebula_cpu_npu_top.v'
gate = root / 'build/pnr/results/6_final.sta.v'
top = c['physical_top']
folder = root / 'build/pnr/formal'
folder.mkdir(exist_ok=True)
tool = '/tmp/chipnebula-pinned-tools/bin/yosys'
version = subprocess.check_output([tool,'-V'],text=True).strip()
assert '0.69+77' in version and '9ff27d29c' in version


def run(name,text):
    script = folder / (name+'.ys')
    script.write_text(text)
    log = root / 'reports/pnr' / (name+'.log')
    with log.open('w') as f:
        rc=subprocess.run([tool,'-s',str(script)],cwd=root,stdout=f,stderr=subprocess.STDOUT).returncode
    return rc


prepare=''
for name,netlist in [('gold',gold),('gate',gate)]:
    prepare+=f'''design -reset
read_liberty -ignore_miss_func {lib}
read_verilog {netlist}
hierarchy -check -top {top}
proc
flatten
opt_expr
opt_merge
opt_clean
write_json {folder}/{name}.json
'''
rc=run('equivalence_prepare',prepare)
assert rc==0,'Formal model elaboration failed; no equivalence claim'
states={}
instance_maps={}
model_data={}
model_cells={}
q_aliases={}
for name in ('gold','gate'):
    data=json.loads((folder/(name+'.json')).read_text())
    cells=data['modules'][top]['cells']
    state={}
    instance_map={}
    signal_names={}
    for netname, net in data['modules'][top]['netnames'].items():
        if netname.startswith(('_','$')): continue
        for i,bit in enumerate(net['bits']):
            index=net.get('offset',0)+(len(net['bits'])-1-i if net.get('upto',0) else i)
            signal_names.setdefault(bit,[]).append(f'{netname}[{index}]')
    for cellname,cell in list(cells.items()):
        kind=cell['type']
        assert 'latch' not in kind.lower(), 'Unexpected latch in physical implementation'
        if 'dff' not in kind.lower():continue
        # Library flattening adds a generated suffix; the physical instance name is stable.
        prefix=cellname.split('.$auto$liberty.cc:')[0]
        assert prefix.startswith('$flatten\\'),cellname
        physical_instance=prefix[len('$flatten\\'):]
        q=cell['connections']['Q']
        assert len(q)==1,'Expected characterized single-bit standard-cell register'
        instance=physical_instance
        assert instance not in state,instance
        state[instance]=dict(type=kind,parameters=cell['parameters'],port_directions=cell['port_directions'])
        instance_map[instance]=physical_instance
        model_cells.setdefault(name,{})[instance]=cellname
        q_aliases.setdefault(name,{})[instance]=set(signal_names.get(q[0],[]))
    assert state,'No actual sequential state found'
    states[name]=state
    instance_maps[name]=instance_map
    model_data[name]=data
missing=states['gold'].keys()-states['gate'].keys()
additional=set(states['gate'].keys()-states['gold'].keys())
renamed={}
for instance in missing:
    candidates=[n for n in additional if states['gold'][instance]==states['gate'][n] and q_aliases['gold'][instance]&q_aliases['gate'][n]]
    assert len(candidates)==1, 'Unexplained sequential instance mismatch: '+instance
    actual=candidates[0]
    renamed[actual]=instance
    additional.remove(actual)
    states['gate'][instance]=states['gate'].pop(actual)
assert not additional,'Unmatched implementation state'
for name,data in model_data.items():
    cells=data['modules'][top]['cells']
    for instance,cellname in model_cells[name].items():
        matched=renamed.get(instance,instance) if name=='gate' else instance
        stable='nebula_ff_'+hashlib.sha256(matched.encode()).hexdigest()[:24]
        assert stable not in cells
        cell=cells.pop(cellname)
        ports=data['modules'][top]['ports']
        assert cell['port_directions']['Q']=='output'
        for pin,bits in cell['connections'].items():
            port=stable+'_'+pin
            assert port not in ports
            assert pin=='Q' or cell['port_directions'][pin]=='input'
            ports[port]=dict(direction='input' if pin=='Q' else 'output',bits=bits)
    assert not any('dff' in v['type'].lower() for v in cells.values())
    (folder/(name+'_named.json')).write_text(json.dumps(data)+'\n')
state_equal=states['gold']==states['gate']
audit=dict(schema_version=1,status='passed' if state_equal else 'failed',
           reference_state_count=len(states['gold']),implementation_state_count=len(states['gate']),
           missing=sorted(states['gold'].keys()-states['gate'].keys()),
           additional=sorted(states['gate'].keys()-states['gold'].keys()),
           model_mismatches=[n for n in states['gold'].keys()&states['gate'].keys() if states['gold'][n]!=states['gate'][n]],
           state_models=states,instance_maps=instance_maps,duplicate_state_representative_mapping=renamed)
(root/'reports/pnr/equivalence_state_audit.json').write_text(json.dumps(audit,indent=2)+'\n')
assert state_equal,'Sequential primitive models differ; no proof boundary may conceal that mismatch'
proof=f'''read_json {folder}/gold_named.json
rename {top} gold
write_json {folder}/gold_boundary.json
design -stash gold
read_json {folder}/gate_named.json
rename {top} gate
write_json {folder}/gate_boundary.json
design -copy-from gold -as gold gold
miter -equiv -make_assert -flatten gold gate miter
hierarchy -top miter
opt_expr
opt_merge
opt_clean
sat -verify -prove-asserts -timeout 600 -dump_json {folder}/counterexample.json
'''
rc=run('equivalence',proof)
reference_ports=json.loads((folder/'gold_boundary.json').read_text())['modules']['gold']['ports']
implementation_ports=json.loads((folder/'gate_boundary.json').read_text())['modules']['gate']['ports']
assert {n:(p['direction'],len(p['bits'])) for n,p in reference_ports.items()}=={n:(p['direction'],len(p['bits'])) for n,p in implementation_ports.items()}
receipt=dict(schema_version=1,status='passed' if rc==0 else 'failed',exit_code=rc,tool_version=version,
             reference_netlist='build/synth/nebula_cpu_npu_top.v',implementation_netlist='build/pnr/results/6_final.sta.v',
             reference_sha256=hashlib.sha256(gold.read_bytes()).hexdigest(),implementation_sha256=hashlib.sha256(gate.read_bytes()).hexdigest(),
             liberty_sha256=hashlib.sha256(lib.read_bytes()).hexdigest(),
             sequential_state_count=len(states['gold']),compared_boundary_ports=len(reference_ports),
             evidence=['reports/pnr/equivalence_prepare.log','reports/pnr/equivalence_state_audit.json','reports/pnr/equivalence.log'],
             scope='Exact Liberty sequential primitive type/parameters/pin-direction matching and combinational SAT equivalence of all functional outputs plus every register D/clock/reset/control pin for arbitrary shared register state. Together these establish mapped-to-post-route equivalence by induction on identical register state, including asynchronous controls. No async2sync, ignored unknown cells or clock/reset assumptions. RTL-to-synthesis equivalence remains an upstream receipt.')
(root/'reports/pnr/equivalence.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps({k:v for k,v in receipt.items() if k in ('status','sequential_state_count','compared_boundary_ports','exit_code')},indent=2))
raise SystemExit(rc)
