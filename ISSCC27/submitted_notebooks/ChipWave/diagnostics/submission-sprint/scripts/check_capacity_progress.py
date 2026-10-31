"""Long independent handshake/latency scoreboards for the public progress contracts."""
from __future__ import annotations

import json
import argparse
from pathlib import Path

import capacity_dot
import capacity_memory
from qualify_capacity_tasks import simulate
from study_protocol import digest, write_json

ROOT = Path(__file__).resolve().parents[1]


def memory_bench(*, data_offset=0):
    ports = capacity_memory.PORTS
    declarations = '\n'.join(f'logic {"["+str(w-1)+":0] " if w>1 else ""}{n};' for _, n, w in ports)
    connections = ','.join(f'.{n}({n})' for _, n, _ in ports)
    return f'''`timescale 1ns/1ps
module benchmark_check_tb;
{declarations}
capacity_memory dut({connections});
always #5 clk=~clk;
integer cycle,issued[0:1],delivered[0:1],last_grant,chosen,client;
integer accepted_at[0:1][0:255],due[0:3],pending_at[0:3];
reg [31:0] expected_data[0:1][0:255],mem[0:63],pending_data[0:3];
reg pending[0:3],expected_error[0:1][0:255],pending_error[0:3];
reg [7:0] expected_id[0:1][0:255];
reg previous_response_accepted;
integer max_latency,max_memory_latency,grant_count;
initial begin
 clk=0;rst_n=0;flush=0;req_valid=0;req_write=0;req_addr=0;req_wdata=0;
 req_wstrb=0;req_id=0;rsp_ready=0;m_req_ready=0;
 m_rsp_valid=0;m_rsp_tag=0;m_rsp_rdata=0;m_rsp_err=0;
 previous_response_accepted=0;last_grant=-1;grant_count=0;max_latency=0;max_memory_latency=0;
 for(integer c=0;c<2;c=c+1)begin issued[c]=0;delivered[c]=0;end
 for(integer t=0;t<4;t=t+1)pending[t]=0;
 for(integer a=0;a<64;a=a+1)mem[a]=32'h{0x97410000+data_offset:08x}+a;
 repeat(3)@(negedge clk);#1;rst_n=1;
 for(cycle=0;cycle<6000;cycle=cycle+1)begin
  @(negedge clk);
  // Readiness is sparse but satisfies the published once-per-eight-cycle assumption.
  m_req_ready=(cycle%8==0);rsp_ready[0]=(cycle%8==2);rsp_ready[1]=(cycle%8==5);
  for(integer c=0;c<2;c=c+1)begin
   req_valid[c]=(issued[c]<128);
   req_addr[32*c+:32]=4*((issued[c]+c*3)%16);
   req_wdata[32*c+:32]=32'h{0xad120000+data_offset:08x}+issued[c]*257+c;
   req_write[c]=(issued[c]%3==0);req_wstrb[4*c+:4]=issued[c]%16;
   req_id[8*c+:8]=issued[c];
  end
  if(!m_rsp_valid || previous_response_accepted)begin
   chosen=-1;
   // Newer eligible tags may complete first; order is checked at client delivery.
   for(integer t=0;t<4;t=t+1)if(pending[t] && due[t]<=cycle)chosen=t;
   m_rsp_valid=(chosen>=0);
   if(chosen>=0)begin m_rsp_tag=chosen;m_rsp_rdata=pending_data[chosen];m_rsp_err=pending_error[chosen];end
  end
  @(posedge clk);
  previous_response_accepted=m_rsp_valid && m_rsp_ready;
  if(previous_response_accepted)begin
   if(!pending[m_rsp_tag])$fatal(1,"unowned external response");
   if(cycle-pending_at[m_rsp_tag]>32)$fatal(1,"invalid environment response bound");
   if(cycle-pending_at[m_rsp_tag]>max_memory_latency)max_memory_latency=cycle-pending_at[m_rsp_tag];
   pending[m_rsp_tag]=0;
  end
  for(integer c=0;c<2;c=c+1)begin
   if(rsp_valid[c] && rsp_ready[c])begin
    if(delivered[c]>=issued[c])$fatal(1,"unexpected response");
    if(rsp_rdata[32*c+:32]!==expected_data[c][delivered[c]] ||
       rsp_id[8*c+:8]!==expected_id[c][delivered[c]] ||
       rsp_err[c]!==expected_error[c][delivered[c]])$fatal(1,"data/error/id/order");
    if(cycle-accepted_at[c][delivered[c]]>max_latency)max_latency=cycle-accepted_at[c][delivered[c]];
    delivered[c]=delivered[c]+1;
   end
   if(delivered[c]<issued[c] && cycle-accepted_at[c][delivered[c]]>128)$fatal(1,"128-cycle delivery bound");
  end
  if((|(req_valid & req_ready)) !== (m_req_valid && m_req_ready))$fatal(1,"request handshake mismatch");
  if(m_req_valid && m_req_ready)begin
   if(req_ready!=1 && req_ready!=2)$fatal(1,"request ownership");
   client=req_ready[1]?1:0;
   if(req_valid==3 && last_grant==client)$fatal(1,"round-robin fairness");
   last_grant=client;grant_count=grant_count+1;
   if(m_req_addr!==req_addr[32*client+:32] || m_req_write!==req_write[client] ||
      m_req_wdata!==req_wdata[32*client+:32] || m_req_wstrb!==req_wstrb[4*client+:4])$fatal(1,"request fields");
   if(pending[m_req_tag])$fatal(1,"tag reused before completion");
   pending[m_req_tag]=1;pending_at[m_req_tag]=cycle;due[m_req_tag]=cycle+8+3*m_req_tag;
   pending_data[m_req_tag]=m_req_write?0:mem[m_req_addr[7:2]];
   pending_error[m_req_tag]=(m_req_addr[7:2]==15);
   if(m_req_write)for(integer b=0;b<4;b=b+1)if(m_req_wstrb[b])mem[m_req_addr[7:2]][8*b+:8]=m_req_wdata[8*b+:8];
   expected_data[client][issued[client]]=pending_data[m_req_tag];
   expected_error[client][issued[client]]=pending_error[m_req_tag];
   expected_id[client][issued[client]]=req_id[8*client+:8];
   accepted_at[client][issued[client]]=cycle;issued[client]=issued[client]+1;
  end
  if(delivered[0]==128 && delivered[1]==128)begin
   $display("BENCHMARK_PASS transactions=%0d cycles=%0d max_latency=%0d max_memory_latency=%0d",grant_count,cycle,max_latency,max_memory_latency);$finish;
  end
 end
 $fatal(1,"long progress watchdog");
end
endmodule
'''


def dot_bench(depth, *, data_offset=0):
    # Use an arithmetic oracle over mathematical vectors, independent of RTL queue/buffer state.
    declarations = '\n'.join(f'logic {"["+str(w-1)+":0] " if w>1 else ""}{n};' for _, n, w in capacity_dot.PORTS)
    connections = ','.join(f'.{n}({n})' for _, n, _ in capacity_dot.PORTS)
    groups = []
    for base in range(1, 65, depth):
        lengths = list(range(base, min(base+depth, 65)))
        for index, length in enumerate(lengths):
            groups.append(f'command({length},{length},{sum((((i*17+length+data_offset)%256)-128)*(((i*31+3+data_offset*7)%256)-128) for i in range(length))});')
        for offset in range(0, max(lengths), 4):
            for length in lengths:
                if offset >= length:
                    continue
                vectors = [[(((i*mul+add)%256)-128) for i in range(length)] for mul, add in ((17,length+data_offset),(31,3+data_offset*7))]
                packed = [sum(((v[offset+k] if offset+k<len(v) else 127)&255)<<(8*k) for k in range(4)) for v in vectors]
                groups.append(f"beat({length},32'h{packed[0]:08x},32'h{packed[1]:08x});")
        groups.append('drain();')
    return f'''`timescale 1ns/1ps
module benchmark_check_tb;
{declarations}
capacity_dot dut({connections});
always #5 clk=~clk;
integer cycle,head,tail,max_beat_wait,max_drain_wait;
integer ids[0:63],answers[0:63];
always @(negedge clk)if(rst_n)begin cycle=cycle+1;rsp_ready=(cycle%8==0);end
always @(posedge clk)if(rst_n && rsp_valid && rsp_ready)begin
 if(head>=tail)$fatal(1,"unexpected dot response");
 if(rsp_id!==ids[head][7:0] || rsp_data!==answers[head])$fatal(1,"dot arithmetic/order");
 head=head+1;
end
task command(input integer id,len,answer);
 integer waited;
 begin
  @(negedge clk);cmd_valid=1;cmd_id=id;cmd_len=len;waited=0;
  @(posedge clk);while(!cmd_ready)begin waited=waited+1;if(waited>2)$fatal(1,"command acceptance bound");@(posedge clk);end
  ids[tail]=id;answers[tail]=answer;tail=tail+1;
  @(negedge clk);cmd_valid=0;
 end
endtask
task beat(input integer id,input reg[31:0] a,b);
 integer waited;
 begin
  @(negedge clk);data_valid=1;data_id=id;data_a=a;data_b=b;waited=0;
  @(posedge clk);while(!data_ready)begin waited=waited+1;if(waited>32)$fatal(1,"beat acceptance bound");@(posedge clk);end
  if(waited>max_beat_wait)max_beat_wait=waited;
  @(negedge clk);data_valid=0;
 end
endtask
task drain;
 integer waited;
 begin
  waited=0;
  while(head<tail)begin @(negedge clk);waited=waited+1;if(waited>512)$fatal(1,"512-cycle final retirement bound");end
  if(waited>max_drain_wait)max_drain_wait=waited;
 end
endtask
initial begin
 clk=0;rst_n=0;cmd_valid=0;cmd_id=0;cmd_len=0;data_valid=0;data_id=0;data_a=0;data_b=0;
 cancel_valid=0;cancel_id=0;rsp_ready=0;cycle=0;head=0;tail=0;max_beat_wait=0;max_drain_wait=0;
 repeat(3)@(negedge clk);#1;rst_n=1;
 {chr(10).join(groups)}
 if(head!=64)$fatal(1,"missing lengths");
 $display("BENCHMARK_PASS lengths=64 cycles=%0d max_beat_wait=%0d max_drain_wait=%0d",cycle,max_beat_wait,max_drain_wait);$finish;
end
initial begin #1000000;$fatal(1,"watchdog");end
endmodule
'''


def check():
    rows=[]
    for task in ('A1','A2','B1','B2'):
        out=ROOT/'tasks'/task/'qualification/long-progress-v1'
        out.mkdir(exist_ok=False)
        bench=out/'progress_tb.sv'
        bench.write_text(dot_bench(1 if task=='A1' else 4) if task.startswith('A') else memory_bench())
        source=ROOT/'tasks'/task/'grader/reference.sv'
        row=simulate(source,bench,out/'reference')
        row.update(task=task,checker_sha256=digest(bench),scope='Finite traces under explicit bounded-stall assumptions; not an unbounded liveness proof')
        write_json(out/'qualification.json',row)
        rows.append(row)
        print(json.dumps(dict(task=task,passed=row['passed'])),flush=True)
    result=dict(passed=all(r['passed'] for r in rows),rows=rows,model_calls=0,physical_runs=0)
    write_json(ROOT/'checks/long-progress-v1.json',result)
    return result


def faults():
    rows=[]
    for task in ('A1','A2','B1','B2'):
        prior=ROOT/'tasks'/task/'qualification/long-progress-v1'
        if not json.loads((prior/'qualification.json').read_text())['passed']:
            raise ValueError('Progress reference prerequisite failed')
        output=prior/'faults';output.mkdir(exist_ok=False)
        source=(ROOT/'tasks'/task/'grader/reference.sv').read_text()
        if task.startswith('A'):
            variants={name:source.replace(' end\n always_ff', f'  {signal}=0;\n end\n always_ff',1)
                      for name,signal in [('command_starvation','cmd_ready'),('operand_starvation','data_ready')]}
        else:
            variants={
                'delivery_starvation':source.replace(' end\n always_ff','  rsp_valid=0;\n end\n always_ff',1),
                'fixed_priority':source.replace('client=~last_client & 1;', 'client=0;')}
        for name,code in variants.items():
            assert code!=source
            path=output/(name+'.sv');path.write_text(code)
            row=simulate(path,prior/'progress_tb.sv',output/name)
            row.update(task=task,fault=name,detected=row['compiled'] and row['exit_codes']==[0,1])
            rows.append(row)
    report=dict(passed=all(r['detected'] for r in rows),rows=rows,model_calls=0,physical_runs=0)
    write_json(ROOT/'checks/long-progress-faults-v1.json',report)
    print(json.dumps(dict(passed=report['passed'],compiling_faults_rejected=sum(r['detected'] for r in rows))))
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--faults',action='store_true')
    raise SystemExit(0 if (faults() if parser.parse_args().faults else check())['passed'] else 1)
