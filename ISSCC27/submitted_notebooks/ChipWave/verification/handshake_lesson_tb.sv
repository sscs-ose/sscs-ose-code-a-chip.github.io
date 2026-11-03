`timescale 1ns/1ps
module benchmark_check_tb;
  reg clk=0, rst_n=1, req_valid=0, rsp_ready=0, kill=0;
  reg [15:0] req_a=16'hfd02, req_b=16'h0504;
  wire req_ready, rsp_valid;
  wire [31:0] rsp_data;
  integer cycle=0, fd;
  benchmark_dot dut(.*);

  // Sample settled signals immediately before the accepting rising edge.
  task step(input string event_name, input bit ready_expected, valid_expected);
    #1;
    if(req_ready !== ready_expected || rsp_valid !== valid_expected)
      $fatal(1,"Handshake mismatch at %s",event_name);
    if(!rst_n && rsp_data !== 32'b0) $fatal(1,"Reset must clear the response");
    if(rsp_valid && $signed(rsp_data) !== -32'sd7)
      $fatal(1,"Signed dot product must be 2*4 + (-3)*5 = -7");
    $fdisplay(fd,"%0d,%s,%0d,%0d,%0d,%0d,%0d,%0d,%0d",
      cycle,event_name,rst_n,req_valid,req_ready,rsp_valid,rsp_ready,kill,$signed(rsp_data));
    #4; clk=1; #5; clk=0; cycle=cycle+1;
  endtask

  initial begin
    #1; rst_n=0;
    fd=$fopen("trace.csv","w");
    if(!fd) $fatal(1,"Cannot create trace");
    $fdisplay(fd,"cycle,event,rst_n,req_valid,req_ready,rsp_valid,rsp_ready,kill,rsp_data");
    $dumpfile("handshake.vcd"); $dumpvars(0,benchmark_check_tb);
    step("reset",0,0);
    rst_n=1; req_valid=1; step("accept A",1,0);
    req_valid=0; step("multiply A",0,0); step("reduce A",0,0);
    step("hold A",0,1); step("hold A again",0,1);
    rsp_ready=1; step("deliver A",0,1);
    rsp_ready=0; req_valid=1; step("accept B",1,0);
    kill=1; rsp_ready=1; step("cancel B blocks new request",0,0);
    kill=0; req_valid=0; rsp_ready=0; step("B discarded",1,0);
    req_valid=1; step("accept C",1,0);
    req_valid=0; step("multiply C",0,0); step("reduce C",0,0);
    step("hold C",0,1);
    kill=1; rsp_ready=1; step("cancel beats delivery",0,0);
    kill=0; rsp_ready=0; step("C discarded",1,0);
    rst_n=0; kill=1; req_valid=1; step("reset wins",0,0);
    $fclose(fd);
    $display("BENCHMARK_PASS: backpressure, signed result, busy/response cancellation, reset");
    $finish;
  end
endmodule
