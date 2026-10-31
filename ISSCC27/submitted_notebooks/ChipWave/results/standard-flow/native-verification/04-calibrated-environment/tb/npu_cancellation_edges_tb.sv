`timescale 1ns/1ps
module npu_cancellation_edges_tb;
  logic clk=0,rst_n=0,kill=0,req_valid=0,rsp_ready=0,req_ready,rsp_valid;
  logic [31:0] req_a=0,req_b=0,rsp_data;
  integer cases=0;
  nebula_npu_dot4 dut(.*);
  always #5 clk=~clk;
  task tick; @(posedge clk); #1; endtask
  task fresh;
    @(negedge clk);req_a=32'h04030201;req_b=32'h01020304;req_valid=1;
    #1;if(!req_ready)$fatal(1,"fresh request not ready");
    tick();req_valid=0;
    tick();if(rsp_valid)$fatal(1,"early fresh result");
    tick();if(!rsp_valid||rsp_data!==20)$fatal(1,"fresh result/latency");
    @(negedge clk);rsp_ready=1;tick();rsp_ready=0;
    if(rsp_valid)$fatal(1,"duplicate response");
  endtask
  task cancel(input bit use_reset,input bit consume_boundary);
    if(consume_boundary)begin
      @(negedge clk);req_valid=1;req_a=32'h80808080;req_b=32'h80808080;
      tick();req_valid=0;tick();tick();
      if(!rsp_valid)$fatal(1,"missing response before cancellation");
    end
    @(negedge clk);req_valid=1;rsp_ready=consume_boundary;
    #1;if(use_reset)rst_n=0;else kill=1;
    #1;if(req_ready||rsp_valid)$fatal(1,"async cancellation did not dominate handshake");
    tick();if(req_ready||rsp_valid)$fatal(1,"cancelled handshake leaked");
    @(negedge clk);req_valid=0;rsp_ready=0;rst_n=1;kill=0;
    repeat(4)begin tick();if(rsp_valid)$fatal(1,"cancelled response resurfaced");end
    fresh();cases++;
  endtask
  initial begin
    repeat(3)tick();@(negedge clk);rst_n=1;
    for(integer r=0;r<2;r++)for(integer c=0;c<2;c++)cancel(r!=0,c!=0);
    $display("NPU_CANCEL_EDGES_PASS cases=%0d",cases);$finish;
  end
  initial begin #10000;$fatal(1,"cancellation timeout");end
endmodule
