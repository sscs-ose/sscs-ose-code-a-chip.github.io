"""Measure real calibration/configuration traffic and retained-state RTL idle wake."""
from pathlib import Path
import argparse,csv,json,re,subprocess
import numpy as np

def run(root,application,source,work,readout=None):
    root=Path(root).resolve();application=Path(application).resolve();work=Path(work).resolve();work.mkdir(parents=True,exist_ok=True)
    data=np.load(application/'application_vectors.npz');indices=[int(np.flatnonzero(data['y']==i)[0]) for i in range(6)]
    for name in ('activations','outputs','weights'):
        lines=(application/(name+'.memh')).read_text().splitlines();(work/(name+'.memh')).write_text('\n'.join(lines[i] for i in indices)+'\n')
    text=Path(source).read_text().replace('BOOT_CYCLES=2','BOOT_CYCLES=8192').replace('SETTLE_CYCLES=2','SETTLE_CYCLES=16').replace('adc_timer<=3;','adc_timer<=5;')
    marker='integer start_conversion;'
    text=text.replace(marker,marker+' time cal_begin,cal_end,cfg_begin,cfg_end,reset_release;integer cal_accepted=0,cfg_accepted=0; always @(posedge clk_i)begin if(rst_ni&&cal_valid_i&&cal_ready_o)cal_accepted<=cal_accepted+1; if(rst_ni&&mha_cfg_valid_i&&mha_cfg_ready_o)cfg_accepted<=cfg_accepted+1;end')
    text=text.replace('rst_ni=1;', 'rst_ni=1;reset_release=$time;',1)
    text=text.replace('for(i=0;i<304;i=i+1)begin','while(!cal_ready_o)@(negedge clk_i);cal_begin=$time;for(i=0;i<304;i=i+1)begin',1)
    marker='for(stage=0;stage<4;stage=stage+1)for(row=0;row<4;row=row+1)begin'
    assert marker in text;text=text.replace(marker,'cal_end=$time;cfg_begin=$time;'+marker,1)
    text=text.replace('for(f=0;f<cases;f=f+1)begin','cfg_end=$time;$display("SERVICE_PROGRAMMING cal_ns=%0d cfg_ns=%0d cal_writes=%0d cfg_writes=%0d boot_ns=%0d",cal_end-cal_begin,cfg_end-cfg_begin,cal_accepted,cfg_accepted,cal_begin-reset_release);for(f=0;f<cases;f=f+1)begin\n repeat(1000+31*f)@(negedge clk_i);',1)
    text=re.sub(r'// The original direct readout interface.*?\$finish;', '$finish;',text,flags=re.S)
    tb=work/'tb_idle_wake.sv';tb.write_text(text)
    ro=Path(readout).resolve() if readout else root/'rtl/automx_cim_readout_seq.sv'
    for label,args in [('compile',['iverilog','-g2012','-s','tb_mha_mixed_top','-o',work/'wake.vvp',root/'ip/automx_mha/rtl/automx_mha_ip.sv',ro,root/'inputs/automx_cim_mixed_signal_proto.sv',root/'inputs/wrapper_blackboxes.sv',tb]),
       ('simulation',['vvp',work/'wake.vvp','+DATA='+str(work),'+CASES=6'])]:
        q=subprocess.run(list(map(str,args)),capture_output=True,text=True,cwd=work,timeout=180);(work/(label+'.log')).write_text(q.stdout+q.stderr);assert q.returncode==0,(q.stdout+q.stderr)[-1800:]
    log=(work/'simulation.log').read_text();m=re.search(r'SERVICE_PROGRAMMING cal_ns=(\d+) cfg_ns=(\d+) cal_writes=(\d+) cfg_writes=(\d+) boot_ns=(\d+)',log);assert m
    observed=(work/'observed_binary.memh').read_text().splitlines();expected=(work/'outputs.memh').read_text().splitlines();assert [int(x,16) for x in observed]==[int(x,16) for x in expected]
    lat=list(csv.DictReader((work/'latency_binary.csv').open()))
    result={'status':'PASS','frames':6,'test_indices':indices,'retained_idle_clocks':[1000+31*i for i in range(6)],
       'cold_boot_ns':int(m[5]),'calibration_ns':int(m[1]),'configuration_ns':int(m[2]),'accepted_calibration_writes':int(m[3]),'accepted_weight_row_writes':int(m[4]),
       'calibration_payload_bits':304*21,'resident_threshold_bits':304*12,'weight_payload_bits':16*12,
       'latency_us_after_idle':[int(r['cycles'])*.04 for r in lat],'output_mismatches':0,'clock_mhz':25,
       'scope':'Actual RTL with unforced 8192-clock boot, 304 accepted calibration writes, resident weights, 40–46.2 us idle intervals and six-clock functional ADC response. Analog remains biased; this does not claim an analog power-gated wake.'}
    assert result['accepted_calibration_writes']==304 and result['accepted_weight_row_writes']==16
    (work/'verification.json').write_text(json.dumps(result,indent=2)+'\n');print('IDLE_WAKE_SERVICE_PASS',json.dumps(result),flush=True);return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--application',type=Path,required=True);p.add_argument('--source',type=Path,required=True);p.add_argument('--work',type=Path,required=True);p.add_argument('--readout',type=Path);a=p.parse_args();run(a.root,a.application,a.source,a.work,a.readout)
