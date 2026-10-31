"""Capture actual sequencer control windows and ADC response delays at 25 MHz."""
from pathlib import Path
import argparse,csv,json,subprocess,shutil
import numpy as np

TRACE=r'''
realtime closure_pin_start=0;
always @(posedge dut.adc_start) closure_pin_start=$realtime;
integer closure_eoc_fd;
initial begin closure_eoc_fd=$fopen("eoc_timing.csv","w");$fwrite(closure_eoc_fd,"request,start_to_eoc_ns\n");end
always @(posedge adc_eoc) begin if(closure_request>0)begin $fwrite(closure_eoc_fd,"%0d,%.3f\n",closure_request-1,$realtime-closure_pin_start);$fflush(closure_eoc_fd);end end
integer closure_fd,closure_prev_state=-1,closure_prev_launch=0,closure_prev_track=0,closure_prev_pre=0;
integer closure_prev_start=0,closure_prev_select=0,closure_request=0;
realtime closure_phase_start=0,closure_pre_end=0,closure_pulse=0,closure_hold=0,closure_select=0,closure_adc_start=0;
initial begin
 closure_fd=$fopen("control_timing.csv","w");
 $fwrite(closure_fd,"request,phase,column,pre_release_ns,pulse_ns,track_end_ns,select_ns,adc_start_ns,acts_hex,weights_pos_hex,weights_neg_hex\n");
end
always @(posedge clk_i) begin
 #0.001;
 if(dut.seq_i.state==2 && closure_prev_state!=2)closure_phase_start=$realtime;
 if(dut.seq_i.pre_b_o && !closure_prev_pre)closure_pre_end=$realtime;
 if(dut.seq_i.launch && !closure_prev_launch)closure_pulse=$realtime;
 if(!dut.seq_i.track_o && closure_prev_track)closure_hold=$realtime;
 if(dut.seq_i.select_o!=0 && dut.seq_i.select_o!=closure_prev_select)closure_select=$realtime;
 if(dut.seq_i.adc_start_o && !closure_prev_start)begin
  closure_adc_start=$realtime;
  $fwrite(closure_fd,"%0d,%0d,%0d,%.3f,%.3f,%.3f,%.3f,%.3f,%h,%h,%h\n",closure_request,dut.seq_i.phase_b,dut.seq_i.column,
    closure_pre_end-closure_phase_start,closure_pulse-closure_phase_start,closure_hold-closure_phase_start,
    closure_select-closure_phase_start,closure_adc_start-closure_phase_start,dut.seq_i.acts,dut.wp,dut.wn);
  $fflush(closure_fd);closure_request=closure_request+1;
 end
 closure_prev_state=dut.seq_i.state;closure_prev_pre=dut.seq_i.pre_b_o;closure_prev_launch=dut.seq_i.launch;
 closure_prev_track=dut.seq_i.track_o;closure_prev_start=dut.seq_i.adc_start_o;closure_prev_select=dut.seq_i.select_o;
end
'''

def capture(root,application,source,work,settle=16):
    root=Path(root).resolve();application=Path(application).resolve();source=Path(source).resolve();work=Path(work).resolve();work.mkdir(parents=True,exist_ok=False)
    vectors=np.load(application/'application_vectors.npz');indices=[int(np.flatnonzero(vectors['y']==i)[0]) for i in range(6)]
    for name in ('activations','weights','outputs'):
        lines=(application/f'{name}.memh').read_text().splitlines();(work/f'{name}.memh').write_text('\n'.join(lines[i] for i in indices)+'\n')
    text=source.read_text().replace('defparam dut.seq_i.SETTLE_CYCLES=2;',f'defparam dut.seq_i.SETTLE_CYCLES={settle};')
    # The fixture detects START one edge later, then decrements through zero:
    # timer=5 gives six observed START-to-EOC periods, matching nominal native SAR.
    text=text.replace('adc_timer<=3;','adc_timer<=5;')
    text=text.replace('module tb_mha_mixed_top;','module tb_mha_mixed_top;\n'+TRACE)
    (work/'tb.sv').write_text(text)
    cmds=[['iverilog','-g2012','-s','tb_mha_mixed_top','-o',work/'timing.vvp',root/'ip/automx_mha/rtl/automx_mha_ip.sv',root/'rtl/automx_cim_readout_seq.sv',root/'inputs/automx_cim_mixed_signal_proto.sv',root/'inputs/wrapper_blackboxes.sv',work/'tb.sv'],['vvp',work/'timing.vvp','+DATA='+str(work),'+CASES=6']]
    for label,cmd in zip(('compile','simulation'),cmds):
        q=subprocess.run(list(map(str,cmd)),cwd=work,capture_output=True,text=True,timeout=120);(work/(label+'.log')).write_text(q.stdout+q.stderr)
        if q.returncode:raise RuntimeError(q.stdout+q.stderr)
    all_rows=list(csv.DictReader((work/'control_timing.csv').open()));assert len(all_rows)>=384,len(all_rows)
    rows=all_rows[:384]
    eoc=list(csv.DictReader((work/'eoc_timing.csv').open()))[:384]
    assert len(eoc)==384 and all(abs(float(x['start_to_eoc_ns'])-240)<.01 for x in eoc),eoc[:2]
    banks=[]
    for bank in range(8):
        group=[r for r in rows if 4*int(r['phase'])+int(r['column'])==bank];fields={}
        for field in ('pre_release_ns','pulse_ns','track_end_ns','select_ns','adc_start_ns'):
            a=[float(r[field]) for r in group];fields[field]={'min':min(a),'max':max(a)}
        banks.append({'bank':bank,'requests':len(group),**fields})
    result={'status':'PASS','clock_mhz':25,'settle_clocks':settle,'frames':6,'indices':indices,'adc_requests':384,'additional_direct_mode_requests':len(all_rows)-384,'banks':banks,'scope':'Actual RTL state/control timestamps; transistor PWM shape is independently measured from the routed cone. Functional ADC fixture has a declared six-clock response.'}
    (work/'verification.json').write_text(json.dumps(result,indent=2)+'\n');print('CONTROL_TIMING_PASS',json.dumps(result),flush=True);return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--application',type=Path,required=True);p.add_argument('--source',type=Path,required=True);p.add_argument('--work',type=Path,required=True);p.add_argument('--settle',type=int,default=16);a=p.parse_args();capture(a.root,a.application,a.source,a.work,a.settle)
