"""Exercise the real readout RTL over all ADC codes, then compare MHA latency."""
from pathlib import Path
import argparse, json, re, subprocess, time
import numpy as np

TB = r'''
`timescale 1ns/1ps
module sky130_fd_sc_hd__buf_1(input A,output X); assign #0.05 X=A; endmodule
module tb_decoder;
reg clk=0,rst=0; always #20 clk=~clk;
automx_cim_readout_seq #(.BOOT_CYCLES(2),.BINARY_DECODE(0)) slow(
 .clk_i(clk),.rst_ni(rst),.cfg_valid_i(1'b0),.cal_valid_i(1'b0),
 .eval_valid_i(1'b0),.act_x2_i(20'd0),.result_ready_i(1'b0),
 .adc_eoc_i(1'b0),.adc_word_i(16'd0));
automx_cim_readout_seq #(.BOOT_CYCLES(2),.BINARY_DECODE(1)) fast(
 .clk_i(clk),.rst_ni(rst),.cfg_valid_i(1'b0),.cal_valid_i(1'b0),
 .eval_valid_i(1'b0),.act_x2_i(20'd0),.result_ready_i(1'b0),
 .adc_eoc_i(1'b0),.adc_word_i(16'd0));
reg [11:0] tables[0:911]; string folder;
integer levels[0:38];integer family,bank,code,j,expected,cycles,fc,sc,total=0;
integer min_fast=99,max_fast=0,fast_clocks=0,slow_clocks=0;
initial begin
 if(!$value$plusargs("DATA=%s",folder))$fatal(1,"DATA required");
 $readmemh({folder,"/thresholds.memh"},tables);
 levels[0]=-24;levels[1]=-20;levels[2]=-18;
 for(j=3;j<=35;j=j+1)levels[j]=j-19;
 levels[36]=18;levels[37]=20;levels[38]=24;
 repeat(3)@(negedge clk);rst=1;repeat(4)@(negedge clk);
 for(family=0;family<3;family=family+1)begin
  for(j=0;j<304;j=j+1)begin
   slow.thresholds[j]=tables[304*family+j];fast.thresholds[j]=tables[304*family+j];
  end
  for(bank=0;bank<8;bank=bank+1)for(code=0;code<4096;code=code+1)begin
   expected=0;for(j=0;j<38;j=j+1)if(code>=tables[304*family+38*bank+j])expected=expected+1;
   slow.state=13;fast.state=13;slow.phase_b=(bank>=4);fast.phase_b=(bank>=4);
   slow.column=bank%4;fast.column=bank%4;
   slow.captured_code=code;fast.captured_code=code;
   slow.decode_index=0;slow.decode_bin=0;
   fast.decode_index=19;fast.decode_bin=0;fast.decode_low=0;fast.decode_high=38;
   slow.result_acc_o=0;fast.result_acc_o=0;
   for(j=0;j<4;j=j+1)begin slow.partial_a[j]=0;fast.partial_a[j]=0;end
   fc=0;sc=0;
   for(cycles=1;cycles<=38;cycles=cycles+1)begin
    @(negedge clk);
    if(!fc && fast.state!=13)begin
     fc=cycles;
     if(fast.decoded!==levels[expected])$fatal(1,"binary mismatch f=%0d bank=%0d code=%0d expected=%0d got=%0d",family,bank,code,levels[expected],fast.decoded);
     if(bank>=4 && $signed(fast.result_acc_o[12*(bank%4)+:12])!=levels[expected])$fatal(1,"binary accumulation mismatch");
     if(bank<4 && $signed(fast.partial_a[bank])!=levels[expected])$fatal(1,"binary partial mismatch");
    end
    if(fc)fast.state=1;
    if(!sc && slow.state!=13)begin
     sc=cycles;if(slow.decoded!==levels[expected])$fatal(1,"baseline mismatch");
    end
    if(!fc && (fast.decode_index>=38 || fast.decode_low>=fast.decode_high))$fatal(1,"invalid binary bounds");
   end
   if(fc<1 || fc>6 || sc!=38)$fatal(1,"cycle bound fast=%0d slow=%0d",fc,sc);
   slow.state=1;fast.state=1;
   if(fc<min_fast)min_fast=fc;if(fc>max_fast)max_fast=fc;
   fast_clocks=fast_clocks+fc;slow_clocks=slow_clocks+sc;total=total+1;
  end
  $display("DECODER_FAMILY_PASS family=%0d codes=4096 banks=8",family);
 end
 $display("DECODER_EXHAUSTIVE_PASS cases=%0d min_fast=%0d max_fast=%0d fast_clocks=%0d slow_clocks=%0d",total,min_fast,max_fast,fast_clocks,slow_clocks);
 $finish;
end
endmodule
'''

def run(command, work, name, timeout=600):
    result=subprocess.run(list(map(str,command)),cwd=work,capture_output=True,text=True,timeout=timeout)
    (work/name).write_text(result.stdout+result.stderr)
    if result.returncode: raise RuntimeError((result.stdout+result.stderr)[-4000:])
    return result.stdout

def verify(root, work):
    root=Path(root).resolve();work=Path(work).resolve();work.mkdir(parents=True,exist_ok=True)
    source_bytes=(root/'rtl/automx_cim_readout_seq.sv').read_bytes()
    (work/'readout_source.sv').write_bytes(source_bytes)
    rng=np.random.default_rng(20261028);tables=[]
    for family in range(3):
        for bank in range(8):
            if family==0: values=100+80*np.arange(38)+bank*3
            elif family==1: values=np.sort(rng.choice(np.arange(4096),38,replace=False))
            else: values=np.arange(38)*4095//37
            assert np.all(np.diff(values)>0)
            tables.extend(values.tolist())
    (work/'thresholds.memh').write_text('\n'.join(f'{x:03x}' for x in tables)+'\n')
    tb=work/'tb_decoder.sv';tb.write_text(TB)
    run(['iverilog','-g2012','-s','tb_decoder','-o',work/'decoder.vvp',root/'rtl/automx_cim_readout_seq.sv',tb],work,'compile.log')
    start=time.monotonic();out=run(['vvp',work/'decoder.vvp','+DATA='+str(work)],work,'exhaustive.log')
    m=re.search(r'DECODER_EXHAUSTIVE_PASS cases=(\d+) min_fast=(\d+) max_fast=(\d+) fast_clocks=(\d+) slow_clocks=(\d+)',out)
    assert m,out
    cases,lo,hi,fast,slow=map(int,m.groups());assert cases==98304 and hi<=6
    report={'status':'PASS','cases':cases,'table_families':3,'banks':8,'codes_per_bank':4096,
            'linear_cycles':38,'binary_min_cycles':lo,'binary_max_cycles':hi,
            'binary_mean_cycles':fast/cases,'elapsed_s':time.monotonic()-start,
            'scope':'Real RTL DECODE state and accumulation; all ADC codes, three independent ordered table families. Full protocols checked by MHA regression.'}
    (work/'equivalence.json').write_text(json.dumps(report,indent=2)+'\n');print(out.strip(),flush=True)
    # One identical integrated MHA frame, actual readout state machine and
    # functional ADC fixture, measured at the same 25 MHz clock for both modes.
    source=(root/'ip/automx_mha/sim/tb_mha_mixed_top.sv').read_text()
    source=source.replace('always #5 clk_i=~clk_i','always #20 clk_i=~clk_i')
    source=source.replace('integer start_conversion;','integer start_conversion; integer tick=0,frame_start; always @(posedge clk_i) tick<=tick+1;')
    source=source.replace('mha_req_act_x2_i=activation[0];','frame_start=tick; mha_req_act_x2_i=activation[0];')
    source=source.replace('if(conversions!=64 || vectors!=8)', '$display("FRAME_LATENCY cycles=%0d",tick-frame_start);\n        if(conversions!=64 || vectors!=8)')
    from ip.automx_mha.verify import verify as mha_verify
    mha_verify(root,work/'mha_regression')
    results=[]
    for mode in (0,1):
        test=work/f'integrated_{mode}.sv'
        test.write_text(source.replace('defparam dut.seq_i.BOOT_CYCLES=2;',f'defparam dut.seq_i.BINARY_DECODE={mode};\n    defparam dut.seq_i.BOOT_CYCLES=2;'))
        exe=work/f'integrated_{mode}.vvp'
        run(['iverilog','-g2012','-s','tb_mha_mixed_top','-o',exe,root/'ip/automx_mha/rtl/automx_mha_ip.sv',root/'rtl/automx_cim_readout_seq.sv',root/'inputs/automx_cim_mixed_signal_proto.sv',root/'inputs/wrapper_blackboxes.sv',test],work,f'integrated_{mode}_compile.log')
        out=run(['vvp',exe,'+DATA='+str(work/'mha_regression')],work,f'integrated_{mode}.log')
        assert 'MHA_CIM_SAR_RTL_TOP_PASS' in out
        cycles=int(re.search(r'FRAME_LATENCY cycles=(\d+)',out)[1])
        results.append({'mode':'binary' if mode else 'linear','cycles':cycles,'latency_us':cycles*.04,'clock_mhz':25,'adc_conversions':64})
    assert (root/'rtl/automx_cim_readout_seq.sv').read_bytes()==source_bytes,'Readout source changed during verification'
    report['readout_source_snapshot']='readout_source.sv'
    report['frame_latency']=results;report['frame_latency_reduction_us']=results[0]['latency_us']-results[1]['latency_us']
    report['latency_scope']='Integrated RTL with identical functional ADC response timing; not a transistor-level frame latency measurement.'
    (work/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
    print('DECODER_AND_FRAME_PASS',json.dumps(report),flush=True)
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--work',type=Path,required=True)
    a=p.parse_args();import sys;sys.path.insert(0,str(a.root.resolve()));verify(a.root,a.work)
