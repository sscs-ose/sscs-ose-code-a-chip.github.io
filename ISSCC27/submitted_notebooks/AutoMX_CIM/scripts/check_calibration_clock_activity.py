"""Count actual threshold-clock transitions in routed-gate VCD, independently of STA."""
from pathlib import Path
import argparse,json,re
from collections import Counter
from scripts.measure_physical_pwm import structural

def run(power,work):
    power=Path(power).resolve();work=Path(work).resolve();work.mkdir(parents=True,exist_ok=True);rows=[]
    for variant in ('binary_reference','binary'):
        folder=power/variant;script=(folder/'power_readout.tcl').read_text()
        net=Path(re.search(r'read_verilog \{(.*?)\}',script)[1]);cells,_=structural(net)
        pins={name:c['pins']['CLK'] for name,c in cells.items() if c['pins'].get('Q','').startswith('thresholds[')}
        clocks=Counter(pins.values());scope=[];codes={};last={};transitions=Counter();times=[]
        with (folder/'activity.vcd').open() as stream:
            for line in stream:
                f=line.split()
                if not f:continue
                if f[0]=='$scope':scope.append(f[2])
                elif f[0]=='$upscope':scope.pop()
                elif f[0]=='$var' and scope==['tb_mha_mixed_top','dut','seq_i']:
                    name=f[4].replace('\\','')
                    if name in clocks:codes[f[3]]=name
                elif f[0]=='$enddefinitions':break
            assert set(codes.values())==set(clocks),(variant,len(codes),len(clocks))
            first=None;end=None
            for line in stream:
                if line.startswith('#'):
                    t=int(line[1:]);end=t
                    if first is None:first=t
                elif len(line)>1 and line[0] in '01xz':
                    code=line[1:].strip()
                    if code in codes:
                        v=line[0];old=last.get(code)
                        if v in '01' and old in ('0','1') and v!=old:transitions[code]+=1
                        last[code]=v
        weighted=sum(transitions[c]*clocks[n] for c,n in codes.items())
        rows.append({'variant':variant,'threshold_flops':len(pins),'clock_nets':len(clocks),
           'weighted_clock_edges':weighted,'minimum_edges':min(transitions[c] for c in codes),
           'maximum_edges':max(transitions[c] for c in codes),'duration_s':(end-first)*1e-12})
        print('CALIBRATION_CLOCK_ACTIVITY',json.dumps(rows[-1]),flush=True)
    result={'status':'PASS','rows':rows,'scope':'Direct 0/1 edge counts from actual gate-level VCD; independent of Liberty internal-power assumptions.'}
    (work/'verification.json').write_text(json.dumps(result,indent=2)+'\n');return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--power',type=Path,required=True);p.add_argument('--work',type=Path,required=True);a=p.parse_args();run(a.power,a.work)
