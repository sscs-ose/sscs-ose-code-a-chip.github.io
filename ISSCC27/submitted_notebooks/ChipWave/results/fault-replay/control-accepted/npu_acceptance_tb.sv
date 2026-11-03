`timescale 1ns/1ps
module npu_acceptance_tb;
  logic clk=0,rst_n=0,kill=0,req_valid=0,rsp_ready=0;
  logic req_ready,rsp_valid;
  logic [31:0] req_a=0,req_b=0,rsp_data;
  integer cases=0, cancellations=0;
  logic [31:0] rng=32'h20261012;
  nebula_npu_dot4 dut(.*);
  always #5 clk=~clk;
  task automatic tick; @(posedge clk); #1; endtask
  function automatic logic[31:0] reference(input logic[31:0] a,b);
    integer total, x,y;
    total=0;
    for(integer lane=0;lane<4;lane++)begin
      x=int'(a[8*lane+:8]); y=int'(b[8*lane+:8]);
      if(x>=128)x=x-256;
      if(y>=128)y=y-256;
      total=total+x*y;
    end
    return 32'(total);
  endfunction
  task automatic random_word(output logic[31:0] value);
    rng=rng^(rng<<13); rng=rng^(rng>>17); rng=rng^(rng<<5); value=rng;
  endtask
  task automatic accept(input logic[31:0] a,b);
    @(negedge clk); req_a=a;req_b=b;req_valid=1;rsp_ready=0;
    if(!req_ready)$fatal(1,"idle request not ready");
    tick();req_valid=0;
    if(rsp_valid||req_ready)$fatal(1,"invalid acceptance boundary");
  endtask
  task automatic check(input logic[31:0] a,b,input integer hold_cycles);
    logic[31:0] expected;
    expected=reference(a,b);accept(a,b);
    tick();if(rsp_valid||req_ready)$fatal(1,"early result at n+1");
    tick();if(!rsp_valid||rsp_data!==expected||req_ready)
      $fatal(1,"NPU arithmetic/latency a=%h b=%h got=%h expected=%h",a,b,rsp_data,expected);
    for(integer h=0;h<hold_cycles;h++)begin
      @(negedge clk);req_valid=1;req_a=~a;req_b=~b;
      tick();if(req_ready||!rsp_valid||rsp_data!==expected)$fatal(1,"busy/backpressure violation");
    end
    @(negedge clk);req_valid=0;rsp_ready=1;
    tick();if(rsp_valid||!req_ready)$fatal(1,"duplicate result or lost readiness");
    cases++;
  endtask
  task automatic cancel(input integer age,input bit reset_mode);
    accept(32'h80808080,32'h7f7f7f7f);
    repeat(age)tick();
    @(negedge clk);req_valid=1;
    if(reset_mode)rst_n=0;else kill=1;
    #1;if(req_ready||rsp_valid)$fatal(1,"cancellation does not dominate interface");
    repeat(2)begin tick();if(req_ready||rsp_valid)$fatal(1,"cancel collision leaked work");end
    @(negedge clk);req_valid=0;kill=0;rst_n=1;
    repeat(4)begin tick();if(rsp_valid)$fatal(1,"late cancelled response");end
    check(32'h04030201,32'h01020304,2);cancellations++;
  endtask
  initial begin
    logic[31:0] a,b;
    repeat(3)tick();@(negedge clk);rst_n=1;tick();
    for(integer lane=0;lane<4;lane++)
      for(integer x=0;x<256;x++)for(integer y=0;y<256;y++)
        check(32'(x)<<(8*lane),32'(y)<<(8*lane),0);
    for(integer n=0;n<2048;n++)begin
      random_word(a);random_word(b);check(a,b,n%5);
    end
    check(32'h80808080,32'h80808080,4);
    check(32'h80808080,32'h7f7f7f7f,4);
    for(integer age=0;age<4;age++)begin cancel(age,0);cancel(age,1);end
    $display("NPU_ACCEPTANCE_PASS cases=%0d cancellations=%0d",cases,cancellations);$finish;
  end
  initial begin #30000000;$fatal(1,"NPU acceptance timeout");end
endmodule
