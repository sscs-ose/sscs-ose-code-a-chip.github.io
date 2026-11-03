"""Exercise the independent waveform checker without running the DUT again."""
import copy
import json
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'verification'))
from check_reset_waveform import measure_reset, vcd_samples
values = dict(clk=0,rst_n=0,pending=0,data0=0,data1=0,host=0,imem_rdata=0,
    imem_valid=0,dmem_req_valid=0,dmem_rsp_ready=0,commit_valid=0,trap_valid=0)
samples = [(0,dict(values)),(50000,dict(values,clk=1,imem_rdata=19)),
    (100000,dict(values,imem_rdata=19)),(250000,dict(values,clk=1,imem_rdata=19)),
    (300000,dict(values,rst_n=1,imem_rdata=19))]
assert measure_reset(samples)[0]['low_pulse_ns'] == 300
results = [{'id':'valid-initial-and-reset-epoch','verdict':'passed','observed':'accepted'}]
for name,index,key,value in [('pulse-too-short',0,'timestamp',150000),
    ('skew-outside-window',4,'timestamp',302000),('pending-during-reset',1,'pending',1),
    ('instruction-memory-not-reset',1,'imem_rdata',0),('commit-during-reset',1,'commit_valid',1)]:
    bad=copy.deepcopy(samples)
    if key == 'timestamp': bad[index]=(value,bad[index][1])
    else: bad[index][1][key]=value
    try: measure_reset(bad)
    except AssertionError: results.append({'id':name,'verdict':'passed','observed':'rejected'})
    else: raise AssertionError(name+' accepted')
actual=measure_reset(vcd_samples(ROOT/'reports/verification/reset-waveform.vcd'))
(ROOT/'reports/verification/reset-checker-tests.json').write_text(json.dumps({
    'verdict':'passed','scope':'checker fixtures only; no DUT/acceptance/coverage inflation',
    'total':len(results),'passed':len(results),'failed':0,'cases':results,
    'actual_waveform_measurements':actual,'commands':['python3 -B tests/test_reset_waveform.py']},indent=2)+'\n')
print('RESET_WAVEFORM_CHECKER_PASS',len(results),actual)
