`timescale 1ns/1ps
`ifndef CLOCK_PERIOD_PS
`define CLOCK_PERIOD_PS 100000
`endif
module benchmark_check_tb;
 logic clk=0,rst_n=0;
 integer checks=0;
 always #(`CLOCK_PERIOD_PS/2000.0) clk=~clk;
 task automatic tick; @(posedge clk); #1; endtask
 logic wr_en=0,rd_en=0;logic [7:0] wr_data=0;
 wire [7:0] rd_data;wire full,empty;
 localparam integer D=4,W=8;
 integer q[0:D-1];integer h=0,t=0,n=0;
 reg [31:0] random_state=12345;
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
  for(integer i=0;i<32;i++)begin
   random_state=random_state*1664525+1013904223;
   step(random_state[30],random_state[29],random_state[23:0]);
  end
  @(negedge clk);wr_en=0;rd_en=0;#1;rst_n=0;h=0;t=0;n=0;#1;inspect();
  $display("BENCHMARK_PASS fifo checks=%0d",checks);$finish;
 end
 initial begin #1000000000;$fatal(1,"BENCHMARK_TIMEOUT");end
endmodule
