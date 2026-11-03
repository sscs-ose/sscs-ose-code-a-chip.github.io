"""Unforced readout boot, resident-state idle and always-biased analog DC power."""
from pathlib import Path
import argparse,json,re,subprocess
from scripts.qualified_cim_sar import coupled_deck,SharedSpice
from scripts.portable_cim_sar import cap_map
from scripts import flow2_adc_partition as adc
from scripts.measure_activity_power import run_command
from scripts.standalone_runtime import container

def run(root,application,work,core_views=None,native=None):
    root=Path(root).resolve();work=Path(work).resolve();work.mkdir(parents=True,exist_ok=True)
    deployment=json.loads((Path(application)/'deployment.json').read_text())
    thresholds=(Path(native)/'thresholds.memh').read_text() if native else '\n'.join(f'{100+80*(i%38):03x}' for i in range(304))+'\n'
    (work/'thresholds.memh').write_text(thresholds)
    masks=[]
    for row in deployment['weights']['O']:
        pos=sum(int(v>0)<<i for i,v in enumerate(row));neg=sum(int(v<0)<<i for i,v in enumerate(row));masks.append(pos|(neg<<4))
    (work/'weight_rows.memh').write_text('\n'.join(f'{v:02x}' for v in masks)+'\n')
    part=root/'third_party/SKY130_SAR_ADC1/mixed_signal_partition'
    entries=cap_map((part/'spice'/adc.FILES[2]).read_text())
    core=Path(core_views).resolve() if core_views else None
    loading=next((core/n for n in ('core_acquisition.grouped.pex.spice','core_acquisition.fast.pex.spice','core_acquisition.pex.spice') if (core/n).exists()),None) if core else None
    profile={'core_pex':True,'core_pex_path':str(loading)} if core else None
    circuit,external,vectors=coupled_deck(root,[0]*4,deployment['weights']['O'],0,sum(c for c,_,_ in entries),profile=profile)
    circuit=re.sub(r'(?m)^VTRACK .*$', 'VTRACK TRACK 0 0',circuit)
    deck=work/'idle.spice';deck.write_text(circuit)
    with (work/'analog_idle.log').open('w') as log:
        spice=SharedSpice(root/'tools/ngspice/libngspice.so',log)
        for key in external:spice.initial(key,{'VSAMPLE':1.8,'VSAMPLEN':0,'VBOTTOMP':.9,'VBOTTOMN':.9}.get(key,0))
        for cmd in ('set ngbehavior=hsa','set skywaterpdk','set num_threads=1','set noinit'):spice.command(cmd)
        spice.command('source '+str(deck));spice.command('option klu');spice.command('op')
        currents={p:float(spice.vector('i('+p+')')[-1]) for p in ('VCORE_METER','VCOND_METER','VADC_METER','VVCM','VBOTTOMP','VBOTTOMN')}
        powers={k:currents[v]*1.8 for k,v in [('core_w','VCORE_METER'),('conditioner_w','VCOND_METER'),('adc_w','VADC_METER')]}
        powers['reference_bridge_w']=-.9*sum(currents[k] for k in ('VVCM','VBOTTOMP','VBOTTOMN'))
        powers['monitored_w']=sum(powers.values());assert powers['monitored_w']>0
        spice.command('destroy all')
    primitive=root/'pdks/digital/sky130A/libs.ref/sky130_fd_sc_hd/verilog/primitives.v'
    models=primitive.with_name('sky130_fd_sc_hd.v');netlist=root/'inputs/digital_blocks/readout/automx_cim_readout_seq.nl.v'
    body='''`timescale 1ns/1ps
module tb_idle;
reg clk_i=0;always #20 clk_i=~clk_i;
reg rst_ni=0;wire ready,cal_ready,cfg_ready,calibrated;integer clocks=0;integer waited;string folder;integer idle;integer j;
reg cal_valid=0,cfg_valid=0;reg [8:0] cal_address=0;reg [11:0] cal_threshold=0;reg [1:0] cfg_row=0;reg [3:0] cfg_pos=0,cfg_neg=0;reg [11:0] tables[0:303];reg [7:0] masks[0:3];
automx_cim_readout_seq dut(.clk_i(clk_i),.rst_ni(rst_ni),.cfg_valid_i(cfg_valid),.cfg_ready_o(cfg_ready),.cfg_row_i(cfg_row),.cfg_wpos_i(cfg_pos),.cfg_wneg_i(cfg_neg),
 .cal_valid_i(cal_valid),.cal_ready_o(cal_ready),.cal_address_i(cal_address),.cal_threshold_i(cal_threshold),.calibrated_o(calibrated),.eval_valid_i(1'b0),.eval_ready_o(ready),.act_x2_i(20'b0),.raw_mode_i(1'b1),
 .result_ready_i(1'b1),.adc_eoc_i(1'b0),.adc_word_i(16'b0));
initial begin
 if(!$value$plusargs("DATA=%s",folder))$fatal(1,"DATA required");
 if(!$value$plusargs("IDLE=%d",idle))idle=0;
 if(!idle)begin $dumpfile({folder,"/activity.vcd"});$dumpvars(0,dut);end
 repeat(4)@(negedge clk_i);rst_ni=1;waited=0;
 while(!ready && waited<8300)begin @(negedge clk_i);waited=waited+1;end
 if(waited!=8192)$fatal(1,"unforced boot count %0d",waited);
 $display("BOOT_PASS clocks=%0d duration_ns=%0d",waited,waited*40);
 if(idle)begin
  if(idle==2)begin $dumpfile({folder,"/activity.vcd"});$dumpvars(0,dut);end
  $readmemh({folder,"/../thresholds.memh"},tables);$readmemh({folder,"/../weight_rows.memh"},masks);
  for(j=0;j<304;j=j+1)begin
   while(!cal_ready)@(negedge clk_i);
   cal_valid=1;cal_address=j;cal_threshold=tables[j];@(negedge clk_i);cal_valid=0;
   while(!cal_ready)@(negedge clk_i);
  end
  if(!calibrated)$fatal(1,"Resident calibration did not validate");
  for(j=0;j<4;j=j+1)begin
   while(!cfg_ready)@(negedge clk_i);
   cfg_valid=1;cfg_row=j;cfg_pos=masks[j][3:0];cfg_neg=masks[j][7:4];@(negedge clk_i);cfg_valid=0;
  end
  repeat(4)@(negedge clk_i);
  $display("RESIDENT_STATE_PROGRAMMED thresholds=304 weight_rows=4");
  if(idle==1)begin $dumpfile({folder,"/activity.vcd"});$dumpvars(0,dut);repeat(1000)@(negedge clk_i);end
 end
 $display("IDLE_PASS clocks=%0d",idle==1?1000:0);$finish;
end
endmodule
'''
    tb=work/'tb_idle.sv';tb.write_text(body)
    run_command(['iverilog','-g2012','-DFUNCTIONAL','-DUNIT_DELAY=','-s','tb_idle','-o',work/'idle.vvp',primitive,models,netlist,tb],work,'compile.log')
    digital=[];lib=root/'pdks/digital/sky130A/libs.ref/sky130_fd_sc_hd/lib/sky130_fd_sc_hd__tt_025C_1v80.lib'
    for label in ('cold','programming','idle'):
        folder=work/label;folder.mkdir(exist_ok=True)
        out=run_command(['vvp',work/'idle.vvp','+DATA='+str(folder),'+IDLE='+str({'cold':0,'programming':2,'idle':1}[label])],work,label+'_simulation.log',timeout=600)
        text=(folder/'activity.vcd').read_text();times=list(map(int,re.findall(r'^#(\d+)\s*$',text,re.M)))
        duration=(max(times)-min(times))*1e-12
        script=folder/'power.tcl';script.write_text(f'''read_liberty {{{lib}}}
set_cmd_units -power W
read_verilog {{{netlist}}}
link_design automx_cim_readout_seq
create_clock -name clk -period 40 [get_ports clk_i]
read_spef {{{netlist.with_suffix('').with_suffix('.spef')}}}
set_input_transition .1 [all_inputs]
set_load .004 [all_outputs]
read_vcd -scope tb_idle/dut {{{folder/'activity.vcd'}}}
report_power -digits 9
exit
''')
        log=run_command([root/'tools/opensta_current/build/sta','-exit',script],folder,'power.log')
        assert not re.search(r'(?im)^Error:',log)
        match=re.search(r'(?m)^Total\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)',log);power=float(match[4]);assert power>0
        digital.append({'window':label,'duration_s':duration,'readout_w':power,'readout_j':duration*power})
        print('READOUT_'+label.upper(),duration,power,flush=True)
    report={'status':'PASS','power_tool':'OpenSTA 3.1.0 clock-aware VCD','cold_boot_clocks':8192,'cold_boot_s':8192*40e-9,'digital':digital,
      'programming_ownership':{'threshold_writes':304,'resident_readout_weight_rows':4,'scope':'Mapped readout storage/control only. The four O-stage masks represent resident readout state; MHA Q/K/V/O programming, analog calibration acquisition and host transport are separate.'},'analog_idle_dc':powers,'sensor_stride_s':1.28,'analog_always_biased_energy_per_stride_j':powers['monitored_w']*1.28,
      'resident_threshold_source':str(Path(native)/'thresholds.memh') if native else 'synthetic ordered test thresholds','resident_weight_stage':'O','analog_sleep_implemented':False,'scope':'Actual unforced mapped-readout boot, 304-threshold/four-resident-row programming and idle VCD; analog partition DC with retained O weights, PRE_B=0, TRACK=0, SEL=0. External reference and ideal bridge policy retained. No measured analog wake or complete-chip energy claim.'}
    (work/'verification.json').write_text(json.dumps(report,indent=2)+'\n');print('IDLE_BOOT_PASS',json.dumps(powers),flush=True);return report

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--application',type=Path,required=True);p.add_argument('--work',type=Path,required=True);p.add_argument('--core-views',type=Path);p.add_argument('--native',type=Path);a=p.parse_args();run(a.root,a.application,a.work,a.core_views,a.native)
