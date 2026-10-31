"""A-family streaming dot contracts, reference datapath and arithmetic oracle."""
from __future__ import annotations

import random

PORTS = [
    ("in", "clk", 1), ("in", "rst_n", 1), ("in", "cmd_valid", 1),
    ("out", "cmd_ready", 1), ("in", "cmd_id", 8), ("in", "cmd_len", 7),
    ("in", "data_valid", 1), ("out", "data_ready", 1), ("in", "data_id", 8),
    ("in", "data_a", 32), ("in", "data_b", 32),
    ("in", "cancel_valid", 1), ("in", "cancel_id", 8),
    ("out", "rsp_valid", 1), ("in", "rsp_ready", 1),
    ("out", "rsp_id", 8), ("out", "rsp_data", 32)]


def contract(depth):
    return f"""Compute exact signed INT8 dot products of length 1–64, returning
an INT32 two's-complement sum. Up to {depth} commands may be outstanding,
including completed results awaiting acceptance. Commands use unique live
8-bit IDs and return in command acceptance order, excluding canceled commands.
A1 accepts one command. A2 provides four command slots and two operand-beat
buffers so loading can overlap computation; this is double buffering of beats,
not a claim of two whole-vector SRAM banks.

cmd_valid/cmd_ready accepts cmd_id and cmd_len. Operand beats carry data_id and
four little-endian signed bytes each in data_a/data_b. Beats for a command are
in vector order; beats of different commands may interleave. Each accepted beat
contains min(4,remaining_length) useful lanes. Upper lanes of the last beat are
ignored, regardless of their values. Do not infer completion from padding.
Once accepted, a beat is owned by the design. Source valid and payload stay
stable until ready; result valid/id/data stay stable until accepted or canceled.

Active-low reset discards all commands, buffered operands and results. A matching
cancel discards that command, its queued beats and any pending result. Matching
cancel suppresses all command/data/result handshakes that cycle. Unknown cancel
has no effect. Reset takes priority over cancel. No canceled result is returned.
Trailing data for an ID that is no longer live is accepted and ignored; sources
must not mix old trailing data with a new command reusing that ID. Canceled queue
slots can remain reserved until earlier commands retire. Do not reuse live IDs.

With no reset/cancel and response-ready at least once per eight cycles, all
results must retire within 512 cycles after the final beat of every outstanding
command has been accepted. With live-command capacity and no cancel, a command
must be accepted within two cycles. An offered legal data beat for a live
command must be accepted within 32 cycles. These are public progress bounds.
"""


def reference(depth):
    if depth not in (1, 4):
        raise ValueError("A1/A2 support one or four commands")
    banks = 1 if depth == 1 else 2
    return f"""module capacity_dot(
 input logic clk,rst_n,cmd_valid, output logic cmd_ready,
 input logic [7:0] cmd_id, input logic [6:0] cmd_len,
 input logic data_valid, output logic data_ready, input logic [7:0] data_id,
 input logic [31:0] data_a,data_b,
 input logic cancel_valid, input logic [7:0] cancel_id,
 output logic rsp_valid, input logic rsp_ready, output logic [7:0] rsp_id,
 output logic [31:0] rsp_data
);
 localparam integer DEPTH={depth},BANKS={banks};
 logic [DEPTH-1:0] live,done;
 logic [7:0] ids[0:DEPTH-1];
 logic [6:0] lengths[0:DEPTH-1],received[0:DEPTH-1],consumed[0:DEPTH-1];
 logic signed [31:0] accum[0:DEPTH-1];
 logic [1:0] head,tail;
 logic [2:0] qcount;
 logic [BANKS-1:0] full;
 logic [31:0] aa[0:BANKS-1],bb[0:BANKS-1];
 logic [1:0] bank_slot[0:BANKS-1];
 logic [2:0] bank_lanes[0:BANKS-1];
 logic busy,active_bank;
 logic [1:0] lane;
 logic cancel_hit,id_busy,push,pop;
 integer cancel_slot,data_slot,free_bank,pick,active_slot;
 logic signed [7:0] operand_a,operand_b;
 logic signed [15:0] product;
 always_comb begin
  cancel_hit=0;cancel_slot=-1;data_slot=-1;id_busy=0;
  for(integer i=0;i<DEPTH;i=i+1)begin
   if(live[i] && ids[i]==cmd_id)id_busy=1;
   if(live[i] && ids[i]==data_id)data_slot=i;
   if(live[i] && cancel_valid && ids[i]==cancel_id)begin cancel_hit=1;cancel_slot=i;end
  end
  free_bank=-1;pick=-1;
  for(integer b=0;b<BANKS;b=b+1)begin
   if(!full[b] && free_bank<0)free_bank=b;
   if(full[b] && pick<0)pick=b;
  end
  cmd_ready=rst_n && !cancel_hit && qcount<DEPTH && !id_busy && cmd_len>=1 && cmd_len<=64;
  data_ready=0;
  if(rst_n && !cancel_hit)begin
   if(data_slot<0)data_ready=1;
   else data_ready=free_bank>=0 && received[data_slot]<lengths[data_slot];
  end
  rsp_valid=rst_n && !cancel_hit && qcount!=0 && live[head] && done[head];
  rsp_id=ids[head];rsp_data=accum[head];
  push=cmd_valid && cmd_ready;
  pop=rst_n && !cancel_hit && qcount!=0 && (!live[head] || (rsp_valid && rsp_ready));
  active_slot=bank_slot[active_bank];
  operand_a=$signed(aa[active_bank][lane*8+:8]);
  operand_b=$signed(bb[active_bank][lane*8+:8]);
  product=operand_a*operand_b;
 end
 always_ff @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin
   live<=0;done<=0;head<=0;tail<=0;qcount<=0;
   full<=0;busy<=0;active_bank<=0;lane<=0;
   for(integer i=0;i<DEPTH;i=i+1)begin
    ids[i]<=0;lengths[i]<=0;received[i]<=0;consumed[i]<=0;accum[i]<=0;
   end
   for(integer b=0;b<BANKS;b=b+1)begin aa[b]<=0;bb[b]<=0;bank_slot[b]<=0;bank_lanes[b]<=0;end
  end else if(cancel_hit)begin
   live[cancel_slot]<=0;done[cancel_slot]<=0;
   for(integer b=0;b<BANKS;b=b+1)
    if(full[b] && bank_slot[b]==cancel_slot)full[b]<=0;
   if(busy && active_slot==cancel_slot)begin busy<=0;lane<=0;end
  end else begin
   if(push)begin
    live[tail]<=1;done[tail]<=0;ids[tail]<=cmd_id;lengths[tail]<=cmd_len;
    received[tail]<=0;consumed[tail]<=0;accum[tail]<=0;
    tail<=(tail==DEPTH-1)?0:tail+1;
   end
   if(pop)begin live[head]<=0;done[head]<=0;head<=(head==DEPTH-1)?0:head+1;end
   case({{push,pop}})
    2'b10:qcount<=qcount+1;
    2'b01:qcount<=qcount-1;
    default:qcount<=qcount;
   endcase
   if(data_valid && data_ready && data_slot>=0)begin
    full[free_bank]<=1;aa[free_bank]<=data_a;bb[free_bank]<=data_b;
    bank_slot[free_bank]<=data_slot;
    bank_lanes[free_bank]<=(lengths[data_slot]-received[data_slot]>=4)?4:lengths[data_slot]-received[data_slot];
    received[data_slot]<=received[data_slot]+((lengths[data_slot]-received[data_slot]>=4)?4:lengths[data_slot]-received[data_slot]);
   end
   if(!busy && pick>=0)begin busy<=1;active_bank<=pick;lane<=0;end
   else if(busy)begin
    accum[active_slot]<=accum[active_slot]+{{{{16{{product[15]}}}},product}};
    consumed[active_slot]<=consumed[active_slot]+1;
    if(consumed[active_slot]+1==lengths[active_slot])done[active_slot]<=1;
    if(lane+1==bank_lanes[active_bank])begin full[active_bank]<=0;busy<=0;lane<=0;end
    else lane<=lane+1;
   end
  end
 end
endmodule
"""


def mutants(depth):
    src = reference(depth)
    changes = {
        "unsigned_product": ("product=operand_a*operand_b;", "product=$unsigned(operand_a)*$unsigned(operand_b);"),
        "wrong_id": ("ids[tail]<=cmd_id;", "ids[tail]<=cmd_id^8'h01;"),
        "ignore_cancel": ("begin cancel_hit=1;cancel_slot=i;end", "begin cancel_hit=0;cancel_slot=i;end"),
        "drop_backpressured_result": ("(rsp_valid && rsp_ready)", "(rsp_valid)"),
        "bad_sign_extension": ("{{16{product[15]}},product}", "{16'b0,product}"),
        "missing_reset_count": ("qcount<=0;", "qcount<=qcount;"),
    }
    result = {}
    for name, (before, after) in changes.items():
        if src.count(before) != 1:
            raise ValueError("Mutation site changed: " + name)
        result[name] = src.replace(before, after)
    return result


def checker(depth, final=True, *, seed=None):
    rng = random.Random((20261021 if final else 1977) if seed is None else seed)
    declarations = [f"logic {'['+str(w-1)+':0] ' if w>1 else ''}{n};" for _, n, w in PORTS]
    cases = []
    for index, length in enumerate(([1,2,3,4,5,7,16,31,63,64] if final else [1,4,5])):
        a, b = [[rng.randrange(-128, 128) for _ in range(length)] for _ in range(2)]
        if index == 0:
            a, b = [-128], [127]
        total = sum(x*y for x, y in zip(a, b))
        cases.append(f"command({index+1},{length});")
        for offset in range(0, length, 4):
            packed = [sum(((v[offset+k] if offset+k<length else 127)&255) << (8*k)
                          for k in range(4)) for v in (a,b)]
            cases.append(f"beat({index+1},32'h{packed[0]:08x},32'h{packed[1]:08x});")
        cases.append(f"result({index+1},32'h{total&0xffffffff:08x});")
    queued = []
    for i in range(depth):
        queued.append(f"command({100+i},{i+1});")
    for i in range(depth):
        queued.append(f"beat({100+i},32'h01010101,32'h02020202);")
    for i in range(depth):
        queued.append(f"result({100+i},{(i+1)*2});")
    return "\n".join([
        "`timescale 1ns/1ps\nmodule benchmark_check_tb;", *declarations,
        "capacity_dot dut("+",".join(f".{n}({n})" for _,n,_ in PORTS)+");",
        """
 always #5 clk=~clk;
 task command(input integer id,input integer len);
  integer n;
  begin
   @(negedge clk);cmd_valid=1;cmd_id=id;cmd_len=len;n=0;
   @(posedge clk);
   while(!cmd_ready)begin n=n+1;if(n>512)$fatal(1,"command progress");@(posedge clk);end
   @(negedge clk);cmd_valid=0;
  end
 endtask
 task beat(input integer id,input reg[31:0] a,input reg[31:0] b);
  integer n;
  begin
   @(negedge clk);data_valid=1;data_id=id;data_a=a;data_b=b;n=0;
   @(posedge clk);
   while(!data_ready)begin n=n+1;if(n>32)$fatal(1,"beat progress");@(posedge clk);end
   @(negedge clk);data_valid=0;
  end
 endtask
 task result(input integer id,input reg[31:0] expected);
  integer n;
  begin
   n=0;
   while(!rsp_valid)begin @(negedge clk);n=n+1;if(n>512)$fatal(1,"result progress");end
   repeat(4)begin
    @(negedge clk);
    if(!rsp_valid || rsp_id!==id[7:0] || rsp_data!==expected)
     $fatal(1,"arithmetic/order/backpressure id=%0d got=%0d expected=%0d",id,$signed(rsp_data),$signed(expected));
   end
   rsp_ready=1;@(negedge clk);rsp_ready=0;
  end
 endtask
 initial begin
  clk=0;rst_n=0;cmd_valid=0;cmd_id=0;cmd_len=0;
  data_valid=0;data_id=0;data_a=0;data_b=0;cancel_valid=0;cancel_id=0;rsp_ready=0;
  repeat(3)@(negedge clk);rst_n=1;
""", *cases, *queued, """
  // Unknown cancellation cannot affect a live transaction.
  command(210,1);@(negedge clk);cancel_valid=1;cancel_id=211;
  beat(210,32'h7f7f7f03,32'h7f7f7f04);result(210,12);
  @(negedge clk);cancel_valid=0;
  // Cancel buffered work and reuse the ID after the canceled command retires.
  command(220,64);beat(220,32'h01010101,32'h02020202);
  @(negedge clk);cancel_valid=1;cancel_id=220;
  @(negedge clk);cancel_valid=0;
  repeat(12)begin @(negedge clk);if(rsp_valid)$fatal(1,"canceled result");end
  command(220,1);beat(220,32'h03030303,32'h04040404);result(220,12);
  // Reset while a result is pending; no stale output may survive.
  command(230,1);beat(230,32'h01010101,32'h01010101);
  repeat(12)@(negedge clk);rst_n=0;
  repeat(3)@(negedge clk);rst_n=1;
  repeat(4)begin @(negedge clk);if(rsp_valid)$fatal(1,"stale reset result");end
  command(231,1);beat(231,32'h02020202,32'h03030303);result(231,6);
  $display("BENCHMARK_PASS");$finish;
 end
 initial begin #1000000;$fatal(1,"watchdog");end
endmodule
"""])
