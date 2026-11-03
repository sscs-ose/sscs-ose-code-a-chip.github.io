"""B-family reference and an external transaction scoreboard, not a DUT mirror."""
from __future__ import annotations


PORTS = [
    ("in", "clk", 1), ("in", "rst_n", 1), ("in", "flush", 1),
    ("in", "req_valid", 2), ("out", "req_ready", 2), ("in", "req_write", 2),
    ("in", "req_addr", 64), ("in", "req_wdata", 64), ("in", "req_wstrb", 8),
    ("in", "req_id", 16), ("out", "rsp_valid", 2), ("in", "rsp_ready", 2),
    ("out", "rsp_rdata", 64), ("out", "rsp_id", 16), ("out", "rsp_err", 2),
    ("out", "m_req_valid", 1), ("in", "m_req_ready", 1),
    ("out", "m_req_write", 1), ("out", "m_req_addr", 32),
    ("out", "m_req_wdata", 32), ("out", "m_req_wstrb", 4),
    ("out", "m_req_tag", 2), ("in", "m_rsp_valid", 1), ("out", "m_rsp_ready", 1),
    ("in", "m_rsp_tag", 2), ("in", "m_rsp_rdata", 32), ("in", "m_rsp_err", 1)]


def contract(slots):
    return f"""Two clients share one external 32-bit memory port, with at most {slots}
globally outstanding/buffered transactions. Client 0 is the frozen CPU adapter;
client 1 is the frozen accelerator memory adapter. Addresses are word-aligned.
Byte-enable bit k writes data bits 8*k+:8. All requests receive one response,
including writes; write response data is zero. req_id is echoed to its client.

Clients hold valid and request fields until ready. The downstream memory holds
responses until ready, may reorder different tags, and never duplicates a
response. The design must hold an offered memory request stable under backpressure.
Memory tags cannot be reused until their old transaction is retired. Responses
must be delivered in acceptance order separately for each client, with stable
data/id/error during backpressure. Arbitration alternates after each acceptance
when both clients continuously request. With downstream readiness and capacity,
a continuously requesting client must be granted within two acceptances.

Reset is active low. During reset or flush no client request/result handshakes
occur. Flush discards every pending client result and unaccepted memory offer;
it does not undo writes accepted by memory. Accepted memory requests still
complete externally; drain their stale responses without delivering them to
clients or confusing them with later requests. Global reset also resets the
external memory response pipeline; stale pre-reset responses are not injected.
After flush, tags may stay reserved until old responses drain.

Assume memory request-ready and each client response-ready are asserted at least
once every eight cycles, and each accepted memory request receives a response
within 32 cycles. Without another reset/flush, every accepted client transaction
must be delivered within 128 cycles. With space and ready downstream, a request
must be offered within two cycles. These bounds are public requirements.
"""


def reference(slots):
    if slots not in (1, 4):
        raise ValueError("B1/B2 support one or four slots")
    return f"""module capacity_memory(
 input logic clk,rst_n,flush,
 input logic [1:0] req_valid,req_write, output logic [1:0] req_ready,
 input logic [63:0] req_addr,req_wdata, input logic [7:0] req_wstrb,
 input logic [15:0] req_id, output logic [1:0] rsp_valid,
 input logic [1:0] rsp_ready, output logic [63:0] rsp_rdata,
 output logic [15:0] rsp_id, output logic [1:0] rsp_err,
 output logic m_req_valid, input logic m_req_ready, output logic m_req_write,
 output logic [31:0] m_req_addr,m_req_wdata, output logic [3:0] m_req_wstrb,
 output logic [1:0] m_req_tag, input logic m_rsp_valid,
 output logic m_rsp_ready, input logic [1:0] m_rsp_tag,
 input logic [31:0] m_rsp_rdata, input logic m_rsp_err
);
 localparam integer SLOTS={slots};
 logic [SLOTS-1:0] used,done,discard,owner,errors;
 logic [31:0] data [0:SLOTS-1];
 logic [7:0] ids [0:SLOTS-1];
 logic [1:0] queue [0:1][0:SLOTS-1];
 logic [1:0] head[0:1],tail[0:1];
 logic [2:0] count[0:1];
 logic last_client,locked,locked_client;
 logic [1:0] locked_slot;
 integer free_slot,client,chosen;
 logic push,pop0,pop1,mem_pop;
 always_comb begin
  free_slot=-1;
  for(integer i=0;i<SLOTS;i=i+1)
   if(!used[i] && free_slot<0) free_slot=i;
  client=-1;
  if(req_valid[~last_client]) client=~last_client & 1;
  else if(req_valid[last_client]) client=last_client;
  chosen=free_slot;
  if(locked) begin client=locked_client; chosen=locked_slot; end
  m_req_valid=rst_n && !flush && client>=0 && chosen>=0;
  req_ready=0;m_req_write=0;m_req_addr=0;m_req_wdata=0;m_req_wstrb=0;m_req_tag=0;
  if(client>=0 && chosen>=0) begin
   m_req_write=req_write[client];m_req_addr=req_addr[32*client+:32];
   m_req_wdata=req_wdata[32*client+:32];m_req_wstrb=req_wstrb[4*client+:4];
   m_req_tag=chosen;
   req_ready[client]=m_req_valid && m_req_ready;
  end
  rsp_valid=0;rsp_rdata=0;rsp_id=0;rsp_err=0;
  for(integer c=0;c<2;c=c+1)
   if(rst_n && !flush && count[c]!=0) begin
    rsp_valid[c]=done[queue[c][head[c]]];
    rsp_rdata[32*c+:32]=data[queue[c][head[c]]];
    rsp_id[8*c+:8]=ids[queue[c][head[c]]];
    rsp_err[c]=errors[queue[c][head[c]]];
   end
  m_rsp_ready=0;
  if(rst_n && m_rsp_tag<SLOTS)
   m_rsp_ready=used[m_rsp_tag] && !done[m_rsp_tag];
  push=m_req_valid && m_req_ready;
  pop0=rsp_valid[0] && rsp_ready[0];pop1=rsp_valid[1] && rsp_ready[1];
  mem_pop=m_rsp_valid && m_rsp_ready;
 end
 always_ff @(posedge clk or negedge rst_n) begin
  if(!rst_n) begin
   used<=0;done<=0;discard<=0;owner<=0;errors<=0;
   last_client<=1;locked<=0;locked_client<=0;locked_slot<=0;
   for(integer c=0;c<2;c=c+1) begin head[c]<=0;tail[c]<=0;count[c]<=0;
    for(integer i=0;i<SLOTS;i=i+1) queue[c][i]<=0;
   end
   for(integer i=0;i<SLOTS;i=i+1) begin data[i]<=0;ids[i]<=0;end
  end else if(flush) begin
   locked<=0;
   for(integer c=0;c<2;c=c+1) begin head[c]<=0;tail[c]<=0;count[c]<=0;end
   for(integer i=0;i<SLOTS;i=i+1) begin
    if(used[i] && !done[i] && !(mem_pop && m_rsp_tag==i)) begin
     used[i]<=1;discard[i]<=1;
    end else begin used[i]<=0;discard[i]<=0;end
    done[i]<=0;
   end
  end else begin
   if(m_req_valid && !m_req_ready && !locked) begin
    locked<=1;locked_client<=client;locked_slot<=chosen;
   end
   if(push) begin
    locked<=0;last_client<=client;
    used[chosen]<=1;done[chosen]<=0;discard[chosen]<=0;owner[chosen]<=client;
    ids[chosen]<=req_id[8*client+:8];
    queue[client][tail[client]]<=chosen;
    tail[client]<=(tail[client]==SLOTS-1)?0:tail[client]+1;
   end
   if(mem_pop) begin
    if(discard[m_rsp_tag]) begin used[m_rsp_tag]<=0;discard[m_rsp_tag]<=0;end
    else begin done[m_rsp_tag]<=1;data[m_rsp_tag]<=m_rsp_rdata;errors[m_rsp_tag]<=m_rsp_err;end
   end
   for(integer c=0;c<2;c=c+1) begin
    if(rsp_valid[c] && rsp_ready[c]) begin
     used[queue[c][head[c]]]<=0;done[queue[c][head[c]]]<=0;
     head[c]<=(head[c]==SLOTS-1)?0:head[c]+1;
    end
    case({{(push && client==c),(rsp_valid[c] && rsp_ready[c])}})
     2'b10:count[c]<=count[c]+1;
     2'b01:count[c]<=count[c]-1;
     default:count[c]<=count[c];
    endcase
   end
  end
 end
endmodule
"""


def mutants(slots):
    src = reference(slots)
    mutations = {
        "wrong_response_id": ("ids[chosen]<=req_id[8*client+:8];", "ids[chosen]<=req_id[8*client+:8]^8'h01;"),
        "wrong_response_data": ("data[m_rsp_tag]<=m_rsp_rdata;", "data[m_rsp_tag]<=m_rsp_rdata^32'h00000100;"),
        "lost_byte_enables": ("m_req_wstrb=req_wstrb[4*client+:4];", "m_req_wstrb=4'b1111;"),
        "lost_error_flag": ("errors[m_rsp_tag]<=m_rsp_err;", "errors[m_rsp_tag]<=0;"),
        "flush_leaks_results": ("rst_n && !flush && count[c]!=0", "rst_n && count[c]!=0"),
        "unfair_arbitration": ("last_client<=client;", "last_client<=1;"),
    }
    result = {}
    for name, (before, after) in mutations.items():
        if src.count(before) != 1:
            raise ValueError("Mutation site changed: " + name)
        result[name] = src.replace(before, after)
    return result


def checker(slots, final=True):
    """An interface-level oracle: accepted payloads, memory effects and FIFO order."""
    declarations = []
    connections = []
    for direction, name, width in PORTS:
        declarations.append(f"logic {'['+str(width-1)+':0] ' if width>1 else ''}{name};")
        connections.append(f".{name}({name})")
    return "\n".join(declarations).join(["""`timescale 1ns/1ps
module benchmark_check_tb;
""", f"""
 capacity_memory dut({','.join(connections)});
 always #5 clk=~clk;
 integer accepted,delivered;
 integer qhead[0:1],qtail[0:1];
 reg [31:0] expected_data[0:1][0:255];
 reg [7:0] expected_id[0:1][0:255];
 reg expected_err[0:1][0:255];
 reg [31:0] mem[0:63],pending_data[0:3];
 reg pending[0:3],pending_error[0:3];
 integer pending_client[0:3];
 integer faults;
 // The oracle observes only public handshakes; it never reads DUT internals.
 always @(posedge clk) if(rst_n) begin
  if(flush) begin
   if(req_ready!=0 || rsp_valid!=0) $fatal(1,"handshake during flush");
   for(integer c=0;c<2;c=c+1) qhead[c]=qtail[c];
  end else begin
   for(integer c=0;c<2;c=c+1) if(rsp_valid[c] && rsp_ready[c]) begin
    if(qhead[c]>=qtail[c]) $fatal(1,"unexpected or stale response");
    if(rsp_rdata[32*c+:32]!==expected_data[c][qhead[c]] ||
       rsp_id[8*c+:8]!==expected_id[c][qhead[c]] ||
       rsp_err[c]!==expected_err[c][qhead[c]]) $fatal(1,"response data/id/error/order");
    qhead[c]=qhead[c]+1;delivered=delivered+1;
   end
   if(m_req_valid && m_req_ready) begin
    if(req_ready!=1 && req_ready!=2) $fatal(1,"request ownership");
    for(integer c=0;c<2;c=c+1) if(req_ready[c]) begin
     if(!req_valid[c] || m_req_addr!==req_addr[32*c+:32] ||
        m_req_write!==req_write[c] || m_req_wstrb!==req_wstrb[4*c+:4] ||
        m_req_wdata!==req_wdata[32*c+:32]) $fatal(1,"memory request altered");
     if(pending[m_req_tag]) $fatal(1,"memory tag reused before response");
     pending[m_req_tag]=1;pending_client[m_req_tag]=c;
     pending_error[m_req_tag]=(m_req_addr[7:2]==63);
     pending_data[m_req_tag]=m_req_write?0:mem[m_req_addr[7:2]];
     if(m_req_write)
      for(integer b=0;b<4;b=b+1) if(m_req_wstrb[b])
       mem[m_req_addr[7:2]][8*b+:8]=m_req_wdata[8*b+:8];
     expected_data[c][qtail[c]]=pending_data[m_req_tag];
     expected_id[c][qtail[c]]=req_id[8*c+:8];
     expected_err[c][qtail[c]]=pending_error[m_req_tag];
     qtail[c]=qtail[c]+1;accepted=accepted+1;
    end
   end
  end
  if(m_rsp_valid && m_rsp_ready) begin
   if(!pending[m_rsp_tag]) $fatal(1,"unowned external response");
   pending[m_rsp_tag]=0;
  end
 end
 task send_req(input integer c,input integer address,input integer datum,
               input integer mask,input integer id,input integer wr);
  integer timeout;
  begin
   @(negedge clk);req_valid[c]=1;req_addr[32*c+:32]=address;
   req_wdata[32*c+:32]=datum;req_wstrb[4*c+:4]=mask;
   req_id[8*c+:8]=id;req_write[c]=wr;
   timeout=0;
   @(posedge clk);
   while(!req_ready[c]) begin
    timeout=timeout+1;if(timeout>128)$fatal(1,"request progress");
    @(posedge clk);
   end
   @(negedge clk);req_valid[c]=0;
  end
 endtask
 task return_tag(input integer tag);
  integer timeout;
  begin
   @(negedge clk);m_rsp_valid=1;m_rsp_tag=tag;
   m_rsp_rdata=pending_data[tag];m_rsp_err=pending_error[tag];
   timeout=0;@(posedge clk);
   while(!m_rsp_ready) begin
    timeout=timeout+1;if(timeout>128)$fatal(1,"memory response progress");
    @(posedge clk);
   end
   @(negedge clk);m_rsp_valid=0;
  end
 endtask
 task drain;
  integer timeout;
  begin
   for(integer s=3;s>=0;s=s-1) if(pending[s]) return_tag(s);
   @(negedge clk);rsp_ready=3;timeout=0;
   while(qhead[0]!=qtail[0] || qhead[1]!=qtail[1]) begin
    @(negedge clk);timeout=timeout+1;if(timeout>128)$fatal(1,"delivery progress");
   end
  end
 endtask
 initial begin
  clk=0;rst_n=0;flush=0;req_valid=0;req_write=0;req_addr=0;req_wdata=0;
  req_wstrb=0;req_id=0;rsp_ready=0;m_req_ready=1;
  m_rsp_valid=0;m_rsp_tag=0;m_rsp_rdata=0;m_rsp_err=0;
  accepted=0;delivered=0;faults=0;
  for(integer c=0;c<2;c=c+1)begin qhead[c]=0;qtail[c]=0;end
  for(integer s=0;s<4;s=s+1)pending[s]=0;
  for(integer a=0;a<64;a=a+1)mem[a]=32'h12340000+a;
  repeat(3)@(negedge clk);rst_n=1;
  for(integer k=0;k<{40 if final else 4};k=k+1) begin
   send_req(k%2,(k%8)*4,32'h89abcdef,k%16,k,k%3==0);
   drain();
  end
  send_req(0,252,0,0,90,0);drain();
  // Queue multiple transactions and return external responses in reverse order.
  @(negedge clk);rsp_ready=0;
  for(integer k=0;k<{slots};k=k+1)send_req(k%2,k*4,0,0,100+k,0);
  drain();
  // Flush a response already buffered under backpressure.
  @(negedge clk);rsp_ready=0;
  send_req(0,0,0,0,150,0);
  for(integer s=0;s<4;s=s+1)if(pending[s])return_tag(s);
  repeat(2)@(negedge clk);
  flush=1;@(negedge clk);flush=0;
  drain();
  // Flush in-flight memory operations; stale completions must be discarded.
  @(negedge clk);rsp_ready=0;
  for(integer k=0;k<{slots};k=k+1)send_req(k%2,4*k,0,0,160+k,0);
  @(negedge clk);flush=1;@(negedge clk);flush=0;
  drain();
  send_req(1,8,0,0,180,0);drain();
  // Both sources continuously request. Observe the first two arbitration grants.
  @(negedge clk);
  req_valid=3;req_write=0;req_addr={{32'd4,32'd0}};req_wdata=0;req_wstrb=0;req_id={{8'd201,8'd200}};
  begin
   integer first_client,second_client,seen;
   seen=0;first_client=-1;second_client=-1;
   while(seen<2)begin
    @(posedge clk);
    if(m_req_valid && m_req_ready)begin
     if(seen==0)first_client=req_ready[1]?1:0;
     else second_client=req_ready[1]?1:0;
     seen=seen+1;
     @(negedge clk);req_valid=0;
     drain();
     @(negedge clk);req_valid=3;
    end
   end
   if(first_client==second_client)$fatal(1,"unfair arbitration");
   @(negedge clk);req_valid=0;
  end
  drain();
  repeat(5)@(negedge clk);
  $display("BENCHMARK_PASS accepted=%0d delivered=%0d",accepted,delivered);$finish;
 end
 initial begin #200000;$fatal(1,"watchdog");end
endmodule
"""])
