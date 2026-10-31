import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess

root=Path(__file__).resolve().parents[2]
source=root/'.nebula_inputs/artifact-0b514721fd8641408ffcec0d7f4350ec/reports/verification'
report=root/'reports/pnr'
baseline=json.loads((root/'reports/synthesis/baseline_revalidation.json').read_text())
verification=next(i for i in baseline['current_inputs'] if i['artifact_id']=='artifact-7295759bd83c446780157c3cdc2d72ae')
expected={f['path']:f['sha256'] for f in verification['files']}
folder=report/'reset_evidence';folder.mkdir(exist_ok=True)
for name in ['reset-waveform.json','reset-waveform.vcd','reset-run.log','reset-runtime.log','baseline-commands.json']:
    data=(source/name).read_bytes()
    assert hashlib.sha256(data).hexdigest()==expected['reports/verification/'+name], 'Captured reset evidence hash differs'
    assert data==subprocess.check_output(['git','show',verification['input_commit']+':reports/verification/'+name]), 'Reset source commit differs'
    (folder/name).write_bytes(data)
c=json.loads((root/'physical/chip-nebula/implementation.constraints.json').read_text())
owner=json.loads((folder/'reset-waveform.json').read_text())
assert owner['verdict']=='passed'
assert owner['acceptance_artifact']=='artifact-8bfa326445194758816c2d0d07307a6f'
assert owner['constraints_artifact']=='artifact-0040978541934ec0803b607ff5200dae'
assert owner['constraints_sha256']==hashlib.sha256((root/'physical/chip-nebula/implementation.constraints.json').read_bytes()).hexdigest()
assert owner['spec_digest']==c['spec_digest']==baseline['spec_digest']
integration=next(i for i in baseline['current_inputs'] if any(f['path']=='rtl/integration/nebula_cpu_npu_top.sv' for f in i['files']))
assert owner['integration_artifact']==integration['artifact_id']
model_path='integration/integration_smoke_tb.sv'
model=(source.parents[1]/model_path).read_bytes()
assert hashlib.sha256(model).hexdigest()==next(f['sha256'] for f in integration['files'] if f['path']==model_path)
assert model==subprocess.check_output(['git','show',integration['input_commit']+':'+model_path])
assert b"if (!rst_n) imem_rdata <= 32'h00000013;" in model
(folder/'integration_smoke_tb.sv').write_bytes(model)
for k in ['executable_sha256','version','openroad_executable','openroad_threads','NUM_CORES','environment_source_paths']:
    assert owner['physical_execution_policy'][k]==c['physical_execution'][k]
assert owner['verilator_version']==(folder/'reset-runtime.log').read_text().strip()
assert 'Verilator 5.048 ' in owner['verilator_version']
commands=json.loads((folder/'baseline-commands.json').read_text())
for name in ['reset-runtime.log','reset-compile.log','reset-run.log']:
    command=next(x for x in commands if x['log'].endswith('/'+name))
    assert command['returncode']==0
    for env in c['physical_execution']['environment_source_paths']:assert 'source '+env in command['command']


def measure(vcd):
    assert re.search(r'\$timescale\s+1ps\s+\$end',vcd), 'Unsupported or absent waveform timescale'
    header,body=vcd.split('$enddefinitions $end',1)
    scopes=[];ids={};prefix='reset_waveform_tb.smoke.'
    wanted={'clk','rst_n','pending','data0','data1','host','imem_rdata','imem_valid','dmem_req_valid','dmem_rsp_valid','commit_valid','trap_valid'}
    for line in header.splitlines():
        words=line.split()
        if not words:continue
        if words[0]=='$scope':scopes.append(words[2])
        elif words[0]=='$upscope':scopes.pop()
        elif words[0]=='$var':
            name='.'.join(scopes+[words[4]])
            if name.startswith(prefix) and name[len(prefix):] in wanted:ids[words[3]]=name[len(prefix):]
    assert set(ids.values())==wanted, 'Missing clock/reset/memory/valid waveform witnesses'
    state={};events=[];stamp=None
    for line in body.splitlines():
        line=line.strip()
        if not line:continue
        if line.startswith('#'):
            if stamp is not None:events.append((stamp,state.copy()))
            stamp=int(line[1:]);continue
        if line[0] in '01xz':code=line[1:];value=line[0]
        elif line[0] in 'bB':value,code=line[1:].split()
        else:continue
        if code in ids:state[ids[code]]=int(value,2) if set(value)<=set('01') else None
    assert stamp is not None
    events.append((stamp,state.copy()))
    rises=[];pulses=[];previous={};low=None
    zero_during_reset=wanted-{'clk','rst_n','imem_rdata'}
    instruction_reset_values=set()
    for t,s in events:
        assert s['clk'] in [0,1] and s['rst_n'] in [0,1], 'Unknown clock/reset in waveform'
        if s['clk']==1 and previous.get('clk')==0:rises.append(t)
        if s['rst_n']==0:
            if previous.get('rst_n')!=0:low=t
            instruction_reset_values.add(s['imem_rdata'])
            assert all(s[k]==0 for k in zero_during_reset), 'External-memory state or transaction valid survives reset: '+str((t,{k:s[k] for k in zero_during_reset if s[k]!=0}))
        elif previous.get('rst_n')==0:
            assert low is not None and rises
            pulses.append(dict(assert_ns=low/1000,release_ns=t/1000,low_pulse_ns=(t-low)/1000,release_after_rising_edge_ns=(t-rises[-1])/1000,joint_memory_reset=True))
        previous=s
    assert instruction_reset_values <= {0,19}, 'Instruction memory reset response differs from captured NOP environment'
    assert pulses and len(rises)>=2
    periods={(b-a)/1000 for a,b in zip(rises,rises[1:])}
    assert len(periods)==1, 'Waveform clock period changes'
    return pulses,periods.pop()

# A literal trace exercises initial reset, scalar/vector parsing and the edge reference.
witnesses=['clk','rst_n','pending','data0','data1','host','imem_rdata','imem_valid','dmem_req_valid','dmem_rsp_valid','commit_valid','trap_valid']
fixture='$timescale 1ps $end\n$scope module reset_waveform_tb $end\n$scope module smoke $end\n'+''.join(f'$var wire 1 {i} {n} $end\n' for i,n in enumerate(witnesses))+'$enddefinitions $end\n#0\n'+''.join(f'0{i}\n' for i in range(len(witnesses)))+'#50000\n10\nb10011 6\n#100000\n00\n#150000\n10\n#200000\n00\n#250000\n10\n#300000\n00\n11\n'
assert measure(fixture)==([dict(assert_ns=0.0,release_ns=300.0,low_pulse_ns=300.0,release_after_rising_edge_ns=50.0,joint_memory_reset=True)],100.0)
pulses,period=measure((folder/'reset-waveform.vcd').read_text())
assert period==c['clocks'][0]['period_ns']==owner['clock_period_ns']
for actual,declared in zip(pulses,owner['measurements'],strict=True):
    for k,v in actual.items():assert v==declared[k], 'Owner/raw waveform measurement differs'
    assert actual['low_pulse_ns']>=c['reset']['minimum_low_pulse_ns']
    phase=actual['release_after_rising_edge_ns'];skew=c['reset']['deassertion']['external_release_skew_ns']
    assert phase+skew[0]>=c['reset']['deassertion']['phase_min_ns'] and phase+skew[1]<=c['reset']['deassertion']['phase_max_ns']
    actual['release_interval_with_frozen_skew_ns']=[phase+skew[0],phase+skew[1]]
receipt=dict(schema_version=1,status='passed',measurement_status='measured',responsible_task='standard-cpu-npu:functional-performance-verify',
    source_verification_artifact=verification['artifact_id'],source_verification_commit=verification['input_commit'],captured_by_netlist_artifact='artifact-0b514721fd8641408ffcec0d7f4350ec',
    spec_digest=c['spec_digest'],acceptance_artifact=owner['acceptance_artifact'],constraints_artifact=owner['constraints_artifact'],constraints_sha256=owner['constraints_sha256'],
    clock_period_ns=period,measurements=pulses,waveform_sha256=owner['waveform_sha256'],physical_execution_policy=owner['physical_execution_policy'],
    evidence=[str(p.relative_to(root)) for p in folder.iterdir()],
    instruction_memory_reset_response='Captured source resets the instruction response to NOP 0x13; zero at time 0 is simulator initialization, not an outstanding transaction.',
    reason='Actual V2 waveform supplied by the responsible verification stage in the current netlist capture; hashes, exact published source bytes, input/tool/runtime binding and raw pulse/edge/memory-state witnesses independently revalidated.',
    scope='External simulation reset environment only; final mapped-design recovery/removal/electrical/library pulse checks remain separate physical evidence.')
old=report/'external_reset_dependency.json'
if old.exists() and json.loads(old.read_text())['status']!='passed':
    history=report/'history/reset-dependency';history.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(old,history/'initial_missing_context.json')
old.write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(dict(status='passed',clock_period_ns=period,measurements=pulses),indent=2))
