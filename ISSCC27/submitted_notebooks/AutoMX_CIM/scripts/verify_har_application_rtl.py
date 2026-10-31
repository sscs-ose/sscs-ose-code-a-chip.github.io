"""Run deployed HAR vectors through real MHA RTL and both projection backends."""
from pathlib import Path
import argparse,json,re,subprocess,time
import numpy as np
from ip.automx_mha.verify import reference,pack

DIGITAL_TB=r'''
`timescale 1ns/1ps
module tb_digital_application;
reg clk_i=0,rst_ni=0;always #20 clk_i=~clk_i;
reg cfg_valid_i=0;wire cfg_ready_o;reg [1:0] cfg_stage_i=0,cfg_row_i=0;
reg [3:0] cfg_wpos_i=0,cfg_wneg_i=0;reg req_valid_i=0;wire req_ready_o;
reg [39:0] req_act_x2_i=0;wire rsp_valid_o;reg rsp_ready_i=0;wire rsp_row_o;
wire [47:0] rsp_result_x2_o;wire busy_o,fault_o;
automx_mha_digital_top dut(.*);
reg [39:0] activations[0:4095];reg [127:0] weights[0:4095];reg [95:0] expected[0:4095];
string folder;integer n,f,stage,row,tick=0,start_tick,fd,lat_fd;
reg [47:0] held;always @(posedge clk_i)tick<=tick+1;
initial begin
 if(!$value$plusargs("DATA=%s",folder) || !$value$plusargs("CASES=%d",n))$fatal(1,"arguments");
 $readmemh({folder,"/activations.memh"},activations,0,n-1);
 $readmemh({folder,"/weights.memh"},weights,0,n-1);
 $readmemh({folder,"/outputs.memh"},expected,0,n-1);
 fd=$fopen({folder,"/observed_digital.memh"},"w");lat_fd=$fopen({folder,"/latency_digital.csv"},"w");
 $fdisplay(lat_fd,"frame,cycles");
 repeat(3)@(negedge clk_i);rst_ni=1;repeat(3)@(negedge clk_i);
 for(stage=0;stage<4;stage=stage+1)for(row=0;row<4;row=row+1)begin
  cfg_valid_i=1;cfg_stage_i=stage;cfg_row_i=row;
  cfg_wpos_i=weights[0][8*(stage*4+row)+:4];cfg_wneg_i=weights[0][8*(stage*4+row)+4+:4];
  do @(posedge clk_i);while(!cfg_ready_o);
  @(negedge clk_i);cfg_valid_i=0;
 end
 for(f=0;f<n;f=f+1)begin
  start_tick=tick;req_act_x2_i=activations[f];req_valid_i=1;
  do @(posedge clk_i);while(!req_ready_o);
  @(negedge clk_i);req_valid_i=0;
  for(row=0;row<2;row=row+1)begin
   wait(rsp_valid_o || fault_o);@(negedge clk_i);
   if(fault_o || rsp_row_o!=row || rsp_result_x2_o!==expected[f][48*row+:48])$fatal(1,"digital MHA mismatch frame=%0d row=%0d",f,row);
   held=rsp_result_x2_o;
   repeat(5)begin @(negedge clk_i);if(!rsp_valid_o || rsp_result_x2_o!==held)$fatal(1,"digital backpressure");end
   rsp_ready_i=1;@(negedge clk_i);rsp_ready_i=0;
  end
  $fdisplay(fd,"%024h",{dut.mha_i.output_rows[1],dut.mha_i.output_rows[0]});
  $fdisplay(lat_fd,"%0d,%0d",f,tick-start_tick);
 end
 $fclose(fd);$fclose(lat_fd);$display("DIGITAL_APPLICATION_PASS frames=%0d values=%0d",n,n*8);$finish;
end
initial begin #2000000000;$fatal(1,"digital watchdog");end
endmodule
'''

def command(args,work,name,timeout=600):
    t=time.monotonic();r=subprocess.run(list(map(str,args)),cwd=work,capture_output=True,text=True,timeout=timeout)
    (work/name).write_text(r.stdout+r.stderr)
    if r.returncode:raise RuntimeError((r.stdout+r.stderr)[-3000:])
    return r.stdout,time.monotonic()-t

def verify(root,application,work):
    root=Path(root).resolve();application=Path(application).resolve();work=Path(work).resolve();work.mkdir(parents=True,exist_ok=True)
    data=np.load(application/'application_vectors.npz');deployment=json.loads((application/'deployment.json').read_text())
    weights={k:np.array(v) for k,v in deployment['weights'].items()};n=len(data['y']);assert n<=4096
    refs=[reference(a,weights) for a in data['activation_x2']]
    for name,bits,width,key in [('probabilities',16,32,'probabilities'),('context',5,10,'context_x2')]:
        (work/f'{name}.memh').write_text('\n'.join(f'{pack(g[key],bits):0{width}x}' for g in refs)+'\n')
    import shutil
    for name in ('activations','weights','outputs'):shutil.copy2(application/f'{name}.memh',work/f'{name}.memh')
    ip=root/'ip/automx_mha';results=[]
    # Full application through the unchanged MHA arithmetic, randomized stalls,
    # fixed-point probabilities/context and existing fault regressions.
    tb=work/'tb_mha_ip.sv';tb.write_text((ip/'sim/tb_mha_ip.sv').read_text().replace('[0:255]','[0:4095]').replace('#10000000;','#2000000000;'))
    command(['iverilog','-g2012','-s','tb_mha_ip','-o',work/'unit.vvp',ip/'rtl/automx_mha_ip.sv',tb],work,'unit_compile.log')
    out,elapsed=command(['vvp',work/'unit.vvp','+DATA='+str(work),f'+CASES={n}'],work,'unit.log')
    assert f'MHA_IP_BIT_EXACT_PASS cases={n}' in out
    results.append({'path':'MHA with transaction-model projection','frames':n,'output_values':n*8,'mismatches':0,'simulation_elapsed_s':elapsed})
    # Real integrated readout, all physical column/phase sequencing, functional
    # ADC fixture. Calibration/weights loaded once; host outputs backpressured.
    source=(ip/'sim/tb_mha_mixed_top.sv').read_text()
    source=source.replace('always #5 clk_i=~clk_i','always #20 clk_i=~clk_i').replace('[0:0]','[0:4095]')
    source=source.replace('canonical_','').replace(',0,0);',',0,cases-1);').replace('#2000000;','#2000000000;')
    source=source.replace('integer start_conversion;','integer start_conversion; integer f,cases,tick=0,start_tick,fd,lat_fd; always @(posedge clk_i) tick<=tick+1;')
    marker='if(!$value$plusargs("DATA=%s",folder))$fatal(1,"DATA required");'
    source=source.replace(marker,marker+'\n        if(!$value$plusargs("CASES=%d",cases))$fatal(1,"CASES required");\n        fd=$fopen({folder,"/observed_binary.memh"},"w"); lat_fd=$fopen({folder,"/latency_binary.csv"},"w"); $fdisplay(lat_fd,"frame,cycles");')
    source=source.replace('mha_req_act_x2_i=activation[0];','for(f=0;f<cases;f=f+1)begin\n        mha_mode_i=1;start_tick=tick; mha_req_act_x2_i=activation[f];')
    source=source.replace('expected[0][48*row+:48]','expected[f][48*row+:48]')
    source=source.replace('if(conversions!=64 || vectors!=8)', '$fdisplay(fd,"%024h",{dut.mha_i.output_rows[1],dut.mha_i.output_rows[0]});\n        $fdisplay(lat_fd,"%0d,%0d",f,tick-start_tick);\n        end\n        $fclose(fd);$fclose(lat_fd);\n        if(conversions!=64*cases || vectors!=8*cases)')
    for name,src,top,files,exe in [
        ('binary',source,'tb_mha_mixed_top',[ip/'rtl/automx_mha_ip.sv',root/'rtl/automx_cim_readout_seq.sv',root/'inputs/automx_cim_mixed_signal_proto.sv',root/'inputs/wrapper_blackboxes.sv'],'binary.vvp'),
        ('linear',source.replace('defparam dut.seq_i.BOOT_CYCLES=2;','defparam dut.seq_i.BINARY_DECODE=0;\n    defparam dut.seq_i.BOOT_CYCLES=2;').replace('observed_binary.memh','observed_linear.memh').replace('latency_binary.csv','latency_linear.csv'),'tb_mha_mixed_top',[ip/'rtl/automx_mha_ip.sv',root/'rtl/automx_cim_readout_seq.sv',root/'inputs/automx_cim_mixed_signal_proto.sv',root/'inputs/wrapper_blackboxes.sv'],'linear.vvp'),
        ('digital',DIGITAL_TB,'tb_digital_application',[ip/'rtl/automx_mha_ip.sv',ip/'rtl/automx_ternary_projection_digital.sv'],'digital.vvp')]:
        test=work/f'tb_application_{name}.sv';test.write_text(src)
        command(['iverilog','-g2012','-s',top,'-o',work/exe,*files,test],work,f'{name}_compile.log')
        out,elapsed=command(['vvp',work/exe,'+DATA='+str(work),f'+CASES={n}'],work,f'{name}.log')
        observed=(work/f'observed_{name}.memh').read_text().splitlines();expected=(work/'outputs.memh').read_text().splitlines()
        assert len(observed)==n and [int(v,16) for v in observed]==[int(v,16) for v in expected]
        latency=np.genfromtxt(work/f'latency_{name}.csv',delimiter=',',names=True)['cycles']
        results.append({'path':name,'frames':n,'output_values':n*8,'mismatches':0,'simulation_elapsed_s':elapsed,
            'latency_cycles_mean':float(latency.mean()),'latency_cycles_min':int(latency.min()),'latency_cycles_max':int(latency.max()),
            'latency_us_mean':float(latency.mean()*.04),'clock_mhz':25,'adc_conversions_per_frame':64 if name!='digital' else 0})
        print('APPLICATION_RTL_PATH_PASS',json.dumps(results[-1]),flush=True)
    report={'status':'PASS','frames_per_path':n,'results':results,'observed_predictions_equal_integer_model':True,
       'scope':'Application RTL and digital hardware baseline. Binary mixed top uses functional ADC responses; native transistor evidence is a separate next step.'}
    (work/'verification.json').write_text(json.dumps(report,indent=2)+'\n');return report

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--application',type=Path,required=True);p.add_argument('--work',type=Path,required=True)
    a=p.parse_args();import sys;sys.path.insert(0,str(a.root.resolve()));verify(a.root,a.application,a.work)
