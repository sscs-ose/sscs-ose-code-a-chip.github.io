`timescale 1ns/1ps
`ifndef CLOCK_PERIOD_PS
`define CLOCK_PERIOD_PS 100000
`endif
module benchmark_check_tb;
 logic clk=0,rst_n=0;
 integer checks=0;
 always #(`CLOCK_PERIOD_PS/2000.0) clk=~clk;
 task automatic tick; @(posedge clk); #1; endtask
 logic req_valid=0,rsp_ready=0,kill=0;
 logic [15:0] req_a=0,req_b=0;wire req_ready,rsp_valid;wire [31:0] rsp_data;
 reg [31:0] random_state=20261018;
 benchmark_dot dut(.*);
 task automatic send(input integer serial,input integer cancel_stage);
  integer answer,a,b;reg [15:0] av,bv;
  answer=0;
  for(integer i=0;i<2;i++)begin
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
  if(cancel_stage==3 || cancel_stage==4)begin
   @(negedge clk);req_valid=1;rsp_ready=1;
   if(cancel_stage==3)kill=1;else begin #1;rst_n=0;end
   #1;if(req_ready!==0 || rsp_valid!==0)$fatal(1,"dot response cancellation mask");
   if(cancel_stage==4 && rsp_data!==0)$fatal(1,"dot async response reset");
   tick();if(rsp_valid!==0 || rsp_data!==0)$fatal(1,"dot held response not cancelled");checks++;
   @(negedge clk);req_valid=0;rsp_ready=0;kill=0;rst_n=1;
   repeat(4)begin tick();if(rsp_valid!==0 || req_ready!==1)$fatal(1,"dot cancelled response returned");checks++;end
   return;
  end
  @(negedge clk);req_valid=0;rsp_ready=1;tick();
  if(rsp_valid!==0 || req_ready!==1)$fatal(1,"dot retirement");checks++;
  @(negedge clk);rsp_ready=0;
 endtask
 initial begin
  #1;rst_n=1;#1;rst_n=0;#1;
  if(req_ready!==0 || rsp_valid!==0 || rsp_data!==0)$fatal(1,"dot reset");checks++;
  @(negedge clk);rst_n=1;
  for(integer i=0;i<256;i++)send(i,0);
  send(17,1);send(18,2);send(19,3);send(20,4);
  @(negedge clk);req_valid=1;kill=1;tick();
  if(req_ready!==0 || rsp_valid!==0 || rsp_data!==0)$fatal(1,"dot idle kill");checks++;
  @(negedge clk);req_valid=0;kill=0;#1;rst_n=0;#1;
  if(rsp_valid!==0 || rsp_data!==0)$fatal(1,"dot asynchronous clear");checks++;
  $display("BENCHMARK_PASS dot checks=%0d",checks);$finish;
 end
 initial begin #1000000000;$fatal(1,"BENCHMARK_TIMEOUT");end
endmodule
