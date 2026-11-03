"""Full-alphabet random weights/activations and backpressure for the hardware baseline."""
from pathlib import Path
import sys
_ROOT=Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:sys.path.insert(0,str(_ROOT))
import argparse,json,subprocess
import numpy as np
from ip.automx_mha.verify import pack

TB=r'''
`timescale 1ns/1ps
module tb_ternary_backend;
reg clk_i=0,rst_ni=0;always #20 clk_i=~clk_i;
reg cfg_valid_i=0;wire cfg_ready_o;reg [1:0] cfg_row_i=0;
reg [3:0] cfg_wpos_i=0,cfg_wneg_i=0;reg eval_valid_i=0;wire eval_ready_o;
reg [19:0] act_x2_i=0;wire result_valid_o;reg result_ready_i=0;wire [47:0] result_x2_o;
automx_ternary_projection_digital dut(.*);
reg [19:0] activations[0:1023];reg [31:0] weights[0:1023];reg [47:0] expected[0:1023];reg [47:0] held;
integer f,row;string folder;
initial begin
 if(!$value$plusargs("DATA=%s",folder))$fatal(1,"DATA");
 $readmemh({folder,"/activation.memh"},activations);$readmemh({folder,"/weights.memh"},weights);$readmemh({folder,"/expected.memh"},expected);
 repeat(3)@(negedge clk_i);rst_ni=1;@(negedge clk_i);
 if(eval_ready_o)$fatal(1,"unconfigured backend accepted eval");
 cfg_wpos_i=1;cfg_wneg_i=1;#1;if(cfg_ready_o)$fatal(1,"overlapping signs accepted");cfg_wpos_i=0;cfg_wneg_i=0;
 for(f=0;f<1024;f=f+1)begin
  for(row=0;row<4;row=row+1)begin
   cfg_row_i=row;cfg_wpos_i=weights[f][8*row+:4];cfg_wneg_i=weights[f][8*row+4+:4];cfg_valid_i=1;
   do @(posedge clk_i);while(!cfg_ready_o);@(negedge clk_i);cfg_valid_i=0;
  end
  act_x2_i=activations[f];eval_valid_i=1;do @(posedge clk_i);while(!eval_ready_o);
  @(negedge clk_i);eval_valid_i=0;
  wait(result_valid_o);@(negedge clk_i);
  if(result_x2_o!==expected[f])$fatal(1,"sign/add mismatch case=%0d",f);
  held=result_x2_o;repeat(3)begin @(negedge clk_i);if(!result_valid_o || held!==result_x2_o || cfg_ready_o || eval_ready_o)$fatal(1,"backpressure");end
  result_ready_i=1;@(negedge clk_i);result_ready_i=0;
 end
 $display("TERNARY_BACKEND_PASS vectors=1024 output_values=4096 random_weights=1 full_alphabet=1");$finish;
end
initial begin #20000000;$fatal(1,"watchdog");end
endmodule
'''

def verify(root,work):
    root=Path(root).resolve();work=Path(work).resolve();work.mkdir(parents=True,exist_ok=True)
    rng=np.random.default_rng(20261028);alphabet=np.array([-12,-8,-6,-4,-3,-2,-1,0,1,2,3,4,6,8,12])
    acts=rng.choice(alphabet,(1024,4));weights=rng.integers(-1,2,(1024,4,4))
    acts[:3]=np.array([[12]*4,[-12]*4,[0]*4]);weights[0]=1;weights[1]=-1;weights[2]=0
    outputs=np.einsum('br,brc->bc',acts,weights)
    masks=[]
    for w in weights:
        masks.append([sum(int(v>0)<<i for i,v in enumerate(row))|(sum(int(v<0)<<i for i,v in enumerate(row))<<4) for row in w])
    for name,data,bits,width in [('activation',acts,5,5),('weights',masks,8,8),('expected',outputs,12,12)]:
        (work/f'{name}.memh').write_text('\n'.join(f'{pack(a,bits):0{width}x}' for a in data)+'\n')
    (work/'tb.sv').write_text(TB)
    for label,args in [('compile',['iverilog','-g2012','-s','tb_ternary_backend','-o',work/'test.vvp',root/'ip/automx_mha/rtl/automx_mha_ip.sv',root/'ip/automx_mha/rtl/automx_ternary_projection_digital.sv',work/'tb.sv']),('simulation',['vvp',work/'test.vvp','+DATA='+str(work)])]:
        q=subprocess.run(list(map(str,args)),cwd=work,capture_output=True,text=True,timeout=90);(work/f'{label}.log').write_text(q.stdout+q.stderr)
        if q.returncode:raise RuntimeError(q.stdout+q.stderr)
    report={'status':'PASS','vectors':1024,'output_values':4096,'mismatches':0,'activation_alphabet':alphabet.tolist(),'random_weights':True,'backpressure_checked':True,'unconfigured_and_overlapping_masks_rejected':True}
    (work/'verification.json').write_text(json.dumps(report,indent=2)+'\n');print('TERNARY_BASELINE_VERIFIED',json.dumps(report),flush=True);return report

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--work',type=Path,required=True);a=p.parse_args();verify(a.root,a.work)
