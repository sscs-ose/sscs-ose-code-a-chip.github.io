`timescale 1ns/1ps
`ifndef CLOCK_PERIOD_PS
`define CLOCK_PERIOD_PS 100000
`endif
module benchmark_check_tb;
 logic clk=0,rst_n=0;
 integer checks=0;
 always #(`CLOCK_PERIOD_PS/2000.0) clk=~clk;
 task automatic tick; @(posedge clk); #1; endtask
 logic en=0,load=0;logic [15:0] load_value=0;
 wire [15:0] count;wire overflow;
 localparam integer MASK=65535;
 benchmark_counter dut(.*);
 task automatic expect_value(input integer v,input bit event_bit);
  if(count !== 16'(v) || overflow !== event_bit)
   $fatal(1,"counter got %0d/%b expected %0d/%b",count,overflow,v,event_bit);
  checks++;
 endtask
 initial begin
  #1;rst_n=1;#1;rst_n=0;#1;expect_value(0,0);
  @(negedge clk);rst_n=1;
  for(integer i=0;i<8;i++) begin
   @(negedge clk);load=1;en=1;load_value=16'((i*257)&MASK);
   tick();expect_value((i*257)&MASK,0);
   @(negedge clk);load=0;en=0;tick();expect_value((i*257)&MASK,0);
   @(negedge clk);en=1;tick();expect_value(((i*257)+1)&MASK,((i*257)&MASK)==MASK);
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
 initial begin #1000000000;$fatal(1,"BENCHMARK_TIMEOUT");end
endmodule
