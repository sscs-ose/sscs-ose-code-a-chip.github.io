`timescale 1ns/1ps
module counter_check_tb;
  logic clk=0,rst_n=0,en=0,load=0;
  logic [7:0] load_value=0;
  wire [7:0] count;
  wire overflow;
  integer value,checks=0;
  counter dut(.*);
  always #5 clk=~clk;
  task automatic tick; @(posedge clk); #1; endtask
  task automatic expect_value(input integer expected,input bit event_bit);
    if(count !== 8'(expected) || overflow !== event_bit)
      $fatal(1,"counter mismatch got=%0d overflow=%b expected=%0d event=%b",count,overflow,expected,event_bit);
    checks++;
  endtask
  initial begin
    #1; rst_n=1; #1; rst_n=0; #1; expect_value(0,0);
    @(negedge clk);rst_n=1;
    for(integer i=0;i<16;i++)begin
      value=(i==0 ? 0 : i==1 ? 1 : i==2 ? 254 : i==3 ? 255 : (i*17)%256);
      @(negedge clk);load=1;en=1;load_value=8'(value);
      tick();expect_value(value,0);
      @(negedge clk);load=0;en=0;
      repeat(2)begin tick();expect_value(value,0);end
      @(negedge clk);en=1;
      tick();expect_value((value+1)%256,value==255);
      tick();expect_value((value+2)%256,value==254);
      @(negedge clk);load=1;en=0;load_value=255;
      tick();expect_value(255,0);
      @(negedge clk);load=0;en=1;
      tick();expect_value(0,1);
      @(negedge clk);en=0;
      tick();expect_value(0,0);
    end
    @(negedge clk);load=1;load_value=93;tick();expect_value(93,0);
    @(negedge clk);#1;rst_n=0;#1;expect_value(0,0);
    $display("COUNTER_CHECK_PASS checks=%0d",checks);$finish;
  end
  initial begin #100000;$fatal(1,"counter timeout");end
endmodule
