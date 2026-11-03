"""Qualify the independent counter checker before generating a new design."""
from pathlib import Path
import json
import subprocess
import tempfile

from prepare_counter_transfer import bench,prepare

FIXTURE='''module counter(input logic clk,rst_n,en,load,input logic[7:0] load_value,
output logic[7:0] count,output logic overflow);
always_ff @(posedge clk or negedge rst_n) begin
 if(!rst_n)begin count<=0;overflow<=0;end
 else if(load)begin count<=load_value;overflow<=0;end
 else if(en)begin count<=count+8'd1;overflow<=(count==8'd255);end
 else overflow<=0;
end
endmodule
'''


def run():
    mutations={'correct':FIXTURE,
        'increments_while_disabled':FIXTURE.replace('else overflow<=0;','else begin count<=count+8\'d1;overflow<=0;end'),
        'load_loses_priority':FIXTURE.replace('else if(load)','else if(load && !en)'),
        'overflow_off_by_one':FIXTURE.replace("count==8'd255","count==8'd254"),
        'reset_not_asynchronous':FIXTURE.replace('posedge clk or negedge rst_n','posedge clk')}
    rows=[]
    with tempfile.TemporaryDirectory(prefix='chip-counter-checker-') as temporary:
        root=Path(temporary);checker=root/'counter_tb.sv';checker.write_text(bench(True))
        for name,source in mutations.items():
            rtl=root/(name+'.sv');rtl.write_text(source)
            command=['iverilog','-g2012','-s','counter_check_tb','-o',str(root/'sim'),str(rtl),str(checker)]
            subprocess.run(command,check=True,capture_output=True,text=True,timeout=30)
            result=subprocess.run(['vvp',str(root/'sim')],capture_output=True,text=True,timeout=30)
            passed=result.returncode==0 and 'COUNTER_CHECK_PASS checks=2051' in result.stdout
            assert passed==(name=='correct'),(name,result.stdout,result.stderr)
            rows.append({'fixture':name,'passed':passed,'exit_code':result.returncode,'output':result.stdout})
        compiled=prepare(root/'project')
        assert len(compiled.tasks)==3 and len(compiled.feedback_routes)==2
    print(json.dumps({'passed':True,'checks':rows,'task_count':3,'actual_model_calls':0,
                      'scope':'Known fixture and four directed faults qualify the checker; fixture is not supplied to the new-design agents'},indent=2))


if __name__=='__main__':run()
