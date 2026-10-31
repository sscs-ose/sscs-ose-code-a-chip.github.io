"""Three explicit task families, independent scoreboards and documented fault models."""
from __future__ import annotations


def replace(template, **values):
    for key, value in values.items():
        template = template.replace('@' + key.upper() + '@', str(value))
    return template


def describe(task):
    family = task['family']
    if family == 'counter':
        width = task['width']
        ports = [('in', 'clk', 1), ('in', 'rst_n', 1), ('in', 'en', 1), ('in', 'load', 1),
                 ('in', 'load_value', width), ('out', 'count', width), ('out', 'overflow', 1)]
        contract = f'''Implement benchmark_counter with {width}-bit unsigned count/load_value.
Active-low asynchronous reset immediately clears count and overflow. At each
rising edge, load has priority over en: load sets count=load_value and overflow=0.
Otherwise en increments count modulo 2**{width}, with overflow=1 exactly on a wrap.
With neither load nor en, hold count and clear overflow. No extra clock latency.'''
    elif family == 'fifo':
        width, depth = task['width'], task['depth']
        ports = [('in', 'clk', 1), ('in', 'rst_n', 1), ('in', 'wr_en', 1), ('in', 'rd_en', 1),
                 ('in', 'wr_data', width), ('out', 'rd_data', width), ('out', 'full', 1), ('out', 'empty', 1)]
        contract = f'''Implement benchmark_fifo, {depth} entries of {width} bits, one rising-edge clock.
Active-low asynchronous reset makes the FIFO empty. Read data is the current
head combinationally, and zero when empty. full/empty reflect current occupancy.
At an edge, accept push iff wr_en && !full; accept pop iff rd_en && !empty,
using flags BEFORE the edge. Thus simultaneous read/write on full accepts only
the read; on empty accepts only the write. No fall-through, overwrite or underflow.
Preserve exact insertion order. Memory reset is not required; externally visible
outputs after reset must meet the empty/zero contract.'''
    elif family == 'dot':
        lanes = task['lanes']
        ports = [('in', 'clk', 1), ('in', 'rst_n', 1), ('in', 'req_valid', 1), ('out', 'req_ready', 1),
                 ('in', 'req_a', 8*lanes), ('in', 'req_b', 8*lanes), ('out', 'rsp_valid', 1),
                 ('in', 'rsp_ready', 1), ('out', 'rsp_data', 32), ('in', 'kill', 1)]
        contract = f'''Implement benchmark_dot, a {lanes}-lane signed INT8 dot product with a signed 32-bit sum.
Lane i uses packed bits [8*i +: 8] of req_a/req_b. Each product and the complete
sum are exact; sign-extend the result. Accept only when req_valid && req_ready.
Single outstanding request; req_ready stays low while busy. A request accepted
at edge t produces rsp_valid immediately after edge t+2 (three rising edges
counting the accepting edge). Hold rsp_valid/rsp_data until response handshake.
req_ready is high again AFTER a response-accepting edge; no same-edge bypass.
Active-low asynchronous reset or synchronous kill clears the outstanding work,
rsp_data=0, and returns to idle; kill immediately masks req_ready/rsp_valid.
No response from cancelled work. Inputs may change while busy. Mask ready/valid
while reset is low; rsp_data starts/reset-clears to zero and otherwise holds.'''
    else:
        raise ValueError('Unsupported benchmark family')
    return 'benchmark_' + family, ports, contract


def reference(task):
    if task['family'] == 'counter':
        return replace('''module benchmark_counter(input logic clk,rst_n,en,load,
 input logic [@MSB@:0] load_value, output logic [@MSB@:0] count, output logic overflow);
 always_ff @(posedge clk or negedge rst_n) begin
  if(!rst_n) begin count<='0;overflow<=0;end
  else if(load) begin count<=load_value;overflow<=0;end
  else if(en) begin count<=count+1'b1;overflow<=&count;end
  else overflow<=0;
 end
endmodule
''', msb=task['width']-1)
    if task['family'] == 'fifo':
        return replace('''module benchmark_fifo(input logic clk,rst_n,wr_en,rd_en,
 input logic [@MSB@:0] wr_data,output wire [@MSB@:0] rd_data, output wire full,empty);
 localparam integer DEPTH=@DEPTH@;
 logic [@MSB@:0] storage[0:DEPTH-1];
 logic [@PTRMSB@:0] wptr,rptr;
 logic [@COUNTMSB@:0] used;
 assign full=(used==DEPTH); assign empty=(used==0);
 assign rd_data=empty ? '0 : storage[rptr];
 always_ff @(posedge clk or negedge rst_n) begin
  if(!rst_n) begin wptr<=0;rptr<=0;used<=0;end
  else begin
   if(wr_en && !full) begin storage[wptr]<=wr_data;wptr<=(wptr+1)%DEPTH;end
   if(rd_en && !empty) rptr<=(rptr+1)%DEPTH;
   case({wr_en && !full,rd_en && !empty})
    2'b10: used<=used+1'b1;
    2'b01: used<=used-1'b1;
    default: used<=used;
   endcase
  end
 end
endmodule
''', msb=task['width']-1, depth=task['depth'], ptrmsb=(task['depth']-1).bit_length()-1, countmsb=task['depth'].bit_length()-1)
    lanes = task['lanes']
    terms = ' + '.join(f'$signed({{{{16{{product[{i}][15]}}}}, product[{i}]}})' for i in range(lanes))
    return replace('''module benchmark_dot(input logic clk,rst_n,req_valid,
 output wire req_ready,input logic [@MSB@:0] req_a,req_b,
 output wire rsp_valid,input logic rsp_ready,output logic [31:0] rsp_data,input logic kill);
 localparam IDLE=0, PRODUCTS=1, REDUCE=2, RESPONSE=3;
 logic [1:0] phase;
 logic signed [15:0] product[0:@LAST@];
 assign req_ready=rst_n && !kill && phase==IDLE;
 assign rsp_valid=rst_n && !kill && phase==RESPONSE;
 always_ff @(posedge clk or negedge rst_n) begin
  if(!rst_n) begin phase<=IDLE;rsp_data<=0;for(integer i=0;i<@LANES@;i++)product[i]<=0;end
  else if(kill) begin phase<=IDLE;rsp_data<=0;for(integer i=0;i<@LANES@;i++)product[i]<=0;end
  else case(phase)
   IDLE: if(req_valid) begin
    for(integer i=0;i<@LANES@;i++)product[i]<=$signed(req_a[8*i+:8])*$signed(req_b[8*i+:8]);
    phase<=PRODUCTS;
   end
   PRODUCTS: phase<=REDUCE;
   REDUCE: begin rsp_data<=@TERMS@;phase<=RESPONSE;end
   RESPONSE: if(rsp_ready)phase<=IDLE;
   default: phase<=IDLE;
  endcase
 end
endmodule
''', msb=lanes*8-1, last=lanes-1, lanes=lanes, terms=terms)


HEADER = '''`timescale 1ns/1ps
`ifndef CLOCK_PERIOD_PS
`define CLOCK_PERIOD_PS 100000
`endif
module benchmark_check_tb;
 logic clk=0,rst_n=0;
 integer checks=0;
 always #(`CLOCK_PERIOD_PS/2000.0) clk=~clk;
 task automatic tick; @(posedge clk); #1; endtask
'''
FOOTER = ''' initial begin #1000000000;$fatal(1,"BENCHMARK_TIMEOUT");end
endmodule
'''


def checker(task, full):
    if task['family'] == 'counter':
        body = replace(''' logic en=0,load=0;logic [@MSB@:0] load_value=0;
 wire [@MSB@:0] count;wire overflow;
 localparam integer MASK=@MASK@;
 benchmark_counter dut(.*);
 task automatic expect_value(input integer v,input bit event_bit);
  if(count !== @WIDTH@'(v) || overflow !== event_bit)
   $fatal(1,"counter got %0d/%b expected %0d/%b",count,overflow,v,event_bit);
  checks++;
 endtask
 initial begin
  #1;rst_n=1;#1;rst_n=0;#1;expect_value(0,0);
  @(negedge clk);rst_n=1;
  for(integer i=0;i<@SAMPLES@;i++) begin
   @(negedge clk);load=1;en=1;load_value=@WIDTH@'((i*@STRIDE@)&MASK);
   tick();expect_value((i*@STRIDE@)&MASK,0);
   @(negedge clk);load=0;en=0;tick();expect_value((i*@STRIDE@)&MASK,0);
   @(negedge clk);en=1;tick();expect_value(((i*@STRIDE@)+1)&MASK,((i*@STRIDE@)&MASK)==MASK);
   @(negedge clk);load=1;en=0;load_value=MASK;
   tick();expect_value(MASK,0);
   @(negedge clk);load=0;en=1;tick();expect_value(0,1);
   @(negedge clk);en=0;tick();expect_value(0,0);
  end
  @(negedge clk);load=1;load_value=MASK-1;tick();expect_value(MASK-1,0);
  @(negedge clk);load=0;en=1;tick();expect_value(MASK,0);tick();expect_value(0,1);
  @(negedge clk);#1;rst_n=0;#1;expect_value(0,0);
  $display("BENCHMARK_PASS counter checks=%0d",checks);$finish;
 end
''', msb=task['width']-1, width=task['width'], mask=2**task['width']-1,
                       samples=256 if full else 8, stride=1 if task['width']==8 else 257)
    elif task['family'] == 'fifo':
        body = replace(''' logic wr_en=0,rd_en=0;logic [@MSB@:0] wr_data=0;
 wire [@MSB@:0] rd_data;wire full,empty;
 localparam integer D=@DEPTH@,W=@WIDTH@;
 integer q[0:D-1];integer h=0,t=0,n=0;
 reg [31:0] random_state=@SEED@;
 benchmark_fifo dut(.*);
 task automatic inspect;
  if(full !== (n==D) || empty !== (n==0) || rd_data !== W'((n==0)?0:q[h]))
   $fatal(1,"FIFO n=%0d got full=%b empty=%b head=%h",n,full,empty,rd_data);
  checks++;
 endtask
 task automatic step(input bit push,input bit pop,input integer value);
  bit take_push,take_pop;
  @(negedge clk);wr_en=push;rd_en=pop;wr_data=W'(value);#1;inspect();
  take_push=push && n<D;take_pop=pop && n>0;
  tick();
  if(take_pop)h=(h+1)%D;
  if(take_push)begin q[t]=value&((1<<W)-1);t=(t+1)%D;end
  n=n+integer'(take_push)-integer'(take_pop);inspect();
 endtask
 initial begin
  #1;rst_n=1;#1;rst_n=0;#1;inspect();
  @(negedge clk);rst_n=1;
  repeat(3)begin
   for(integer i=0;i<D;i++)step(1,0,i*31+7);
   step(1,0,999);step(1,1,777);
   for(integer i=0;i<D;i++)step(0,1,0);
   step(0,1,0);step(1,1,123);step(0,1,0);
  end
  for(integer i=0;i<@SAMPLES@;i++)begin
   random_state=random_state*1664525+1013904223;
   step(random_state[30],random_state[29],random_state[23:0]);
  end
  @(negedge clk);wr_en=0;rd_en=0;#1;rst_n=0;h=0;t=0;n=0;#1;inspect();
  $display("BENCHMARK_PASS fifo checks=%0d",checks);$finish;
 end
''', msb=task['width']-1, depth=task['depth'], width=task['width'],
                       seed=20261018 if full else 12345, samples=2048 if full else 32)
    else:
        body = replace(''' logic req_valid=0,rsp_ready=0,kill=0;
 logic [@MSB@:0] req_a=0,req_b=0;wire req_ready,rsp_valid;wire [31:0] rsp_data;
 reg [31:0] random_state=@SEED@;
 benchmark_dot dut(.*);
 task automatic send(input integer serial,input integer cancel_stage);
  integer answer,a,b;reg [@MSB@:0] av,bv;
  answer=0;
  for(integer i=0;i<@LANES@;i++)begin
   random_state=random_state*1664525+1013904223;av[8*i+:8]=random_state[31:24];
   random_state=random_state*1664525+1013904223;bv[8*i+:8]=random_state[31:24];
   if(serial<4)begin av[8*i+:8]=(serial==0 || serial==2)?8'h80:8'h7f;
    bv[8*i+:8]=(serial==0 || serial==3)?8'h80:8'h7f;end
   a=$signed(av[8*i+:8]);b=$signed(bv[8*i+:8]);answer+=a*b;
  end
  @(negedge clk);req_valid=1;req_a=av;req_b=bv;rsp_ready=0;#1;
  if(req_ready!==1 || rsp_valid!==0)$fatal(1,"dot idle handshake");
  tick();if(req_ready!==0 || rsp_valid!==0)$fatal(1,"dot accepted latency");checks++;
  @(negedge clk);req_valid=0;req_a=~av;req_b=~bv;kill=(cancel_stage==1);
  tick();
  if(cancel_stage==1)begin
   if(rsp_valid!==0 || rsp_data!==0)$fatal(1,"dot product cancel");
   @(negedge clk);kill=0;
   tick();if(req_ready!==1 || rsp_valid!==0)$fatal(1,"dot cancelled work escaped");checks++;return;
  end
  if(rsp_valid!==0)$fatal(1,"dot early response");
  @(negedge clk);kill=(cancel_stage==2);tick();
  if(cancel_stage==2)begin
   if(rsp_valid!==0 || rsp_data!==0)$fatal(1,"dot reduction cancel");
   @(negedge clk);kill=0;tick();checks++;return;
  end
  if(rsp_valid!==1 || rsp_data!==32'(answer))$fatal(1,"dot got=%h expected=%h",rsp_data,answer);checks++;
  repeat(1+serial%4)begin
   @(negedge clk);req_valid=1;req_a=~req_a;tick();
   if(rsp_valid!==1 || req_ready!==0 || rsp_data!==32'(answer))$fatal(1,"dot backpressure");checks++;
  end
  @(negedge clk);req_valid=0;rsp_ready=1;tick();
  if(rsp_valid!==0 || req_ready!==1)$fatal(1,"dot retirement");checks++;
  @(negedge clk);rsp_ready=0;
 endtask
 initial begin
  #1;rst_n=1;#1;rst_n=0;#1;
  if(req_ready!==0 || rsp_valid!==0 || rsp_data!==0)$fatal(1,"dot reset");checks++;
  @(negedge clk);rst_n=1;
  for(integer i=0;i<@SAMPLES@;i++)send(i,0);
  send(17,1);send(18,2);
  @(negedge clk);req_valid=1;kill=1;tick();
  if(req_ready!==0 || rsp_valid!==0 || rsp_data!==0)$fatal(1,"dot idle kill");checks++;
  @(negedge clk);req_valid=0;kill=0;#1;rst_n=0;#1;
  if(rsp_valid!==0 || rsp_data!==0)$fatal(1,"dot asynchronous clear");checks++;
  $display("BENCHMARK_PASS dot checks=%0d",checks);$finish;
 end
''', msb=task['lanes']*8-1, lanes=task['lanes'], seed=20261018 if full else 12345, samples=256 if full else 8)
    return HEADER + body + FOOTER


def mutants(task):
    source = reference(task)
    if task['family'] == 'counter':
        edits = [('load_priority', 'else if(load)', 'else if(load && !en)'),
                 ('sticky_overflow', 'else overflow<=0;', 'else overflow<=overflow;'),
                 ('wrong_increment', "count<=count+1'b1", "count<=count+2'd2")]
    elif task['family'] == 'fifo':
        edits = [('early_full', 'used==DEPTH', 'used==DEPTH-1'),
                 ('repeated_head', 'rptr<=(rptr+1)%DEPTH', 'rptr<=rptr'),
                 ('corrupt_payload', 'storage[wptr]<=wr_data', "storage[wptr]<=wr_data ^ 1'b1")]
    else:
        edits = [('unsigned_multiply', '$signed(req_a[8*i+:8])*$signed(req_b[8*i+:8])', 'req_a[8*i+:8]*req_b[8*i+:8]'),
                 ('early_response', 'PRODUCTS: phase<=REDUCE', 'PRODUCTS: phase<=RESPONSE'),
                 ('cancel_ignored', 'else if(kill)', "else if(1'b0)")]
    result = {}
    for name, before, after in edits:
        assert source.count(before) == 1, (name, before)
        result[name] = source.replace(before, after)
    return result
