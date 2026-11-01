`timescale 1ns/1ps
module hullcirq_global_tb;
  reg clk=0, rst=1;
  reg [68:0] config_data=0; reg config_data_valid=0;
  wire config_data_ready; reg [12:0] load_data=0; reg load_data_valid=0;
  wire load_data_ready; wire signed [31:0] output_data;
  wire output_data_valid; reg output_data_ready=0; wire busy,job_done;
  hullcirq_npu2_top dut(.clk(clk),.rst(rst),.config_data(config_data),
    .config_data_valid(config_data_valid),.config_data_ready(config_data_ready),
    .load_data(load_data),.load_data_valid(load_data_valid),.load_data_ready(load_data_ready),
    .output_data(output_data),.output_data_valid(output_data_valid),
    .output_data_ready(output_data_ready),.busy(busy),.job_done(job_done));
  always #25 clk=~clk;
  reg signed [31:0] expected [0:3];
  integer cycles=0, outputs=0, done_count=0, started=0, after_start=0, i;
  reg stalled=0; reg [31:0] held_data=0; reg previous_done=0;
  task fail; input [511:0] message; begin
    $display("HULLCIRQ_FAIL cycle=%0d outputs=%0d %0s",cycles,outputs,message); $finish;
  end endtask
  task send_load; input [12:0] word; integer wait_cycle;
    begin
      @(negedge clk); load_data=word; load_data_valid=1;
      begin : waiting
        for(wait_cycle=0;wait_cycle<2000;wait_cycle=wait_cycle+1) begin
          @(posedge clk);
          if(load_data_ready===1'b1) begin
            @(negedge clk); load_data_valid=0; disable waiting;
          end
        end
        fail("load timeout");
      end
    end
  endtask
  always @(negedge clk) begin
    if(rst) output_data_ready=0;
    else output_data_ready=(cycles%5==1 || cycles%5==3 || cycles%5==4);
  end
  always @(posedge clk) begin
    cycles=cycles+1;
    if(rst) begin outputs=0; done_count=0; started=0; after_start=0;
      stalled=0; previous_done=0;
    end else begin
      if(stalled && (output_data_valid!==1'b1 || output_data!==held_data)) fail("output changed under backpressure");
      if(output_data_valid!==1'b0 && output_data_valid!==1'b1) fail("unknown output valid");
      if(busy!==1'b0 && busy!==1'b1) fail("unknown busy");
      if(job_done!==1'b0 && job_done!==1'b1) fail("unknown job_done");
      if(busy===1'b1 && load_data_ready!==1'b0) fail("loading enabled during job");
      if(config_data_valid===1'b1 && config_data_ready===1'b1) started=1;
      if(started) after_start=after_start+1;
      if(started && after_start>2 && outputs<4 && busy!==1'b1) fail("busy dropped before four outputs");
      if(output_data_valid===1'b1 && output_data_ready===1'b1) begin
        if(!started || outputs>=4) fail("unexpected extra output");
        if(output_data!==expected[outputs]) fail("matrix output mismatch");
        $display("HULLCIRQ_OUTPUT index=%0d value=%0d cycle=%0d",outputs,output_data,cycles);
        outputs=outputs+1;
      end
      if(job_done===1'b1) begin
        if(outputs!=4 || previous_done) fail("premature or repeated completion");
        done_count=done_count+1;
      end
      stalled=(output_data_valid===1'b1 && output_data_ready!==1'b1);
      held_data=output_data; previous_done=job_done;
    end
  end
  initial begin
    expected[0] = 32'hffffffd4;
    expected[1] = 32'h00000038;
    expected[2] = 32'h0000003b;
    expected[3] = 32'h00000009;
    repeat(3) @(negedge clk); rst=0;
    send_load(13'h00f8);
    send_load(13'h0103);
    send_load(13'h0205);
    send_load(13'h0807);
    send_load(13'h09fe);
    send_load(13'h0a04);
    send_load(13'h1006);
    send_load(13'h11ff);
    send_load(13'h12fd);
    send_load(13'h1305);
    send_load(13'h1402);
    send_load(13'h1507);
    @(negedge clk); config_data=69'h1fffffffc000000063; config_data_valid=1;
    begin : config_wait
      for(i=0;i<2000;i=i+1) begin
        @(posedge clk);
        if(config_data_ready===1'b1) begin
          @(negedge clk); config_data_valid=0; disable config_wait;
        end
      end
      fail("configuration timeout");
    end
    begin : finish_wait
      for(i=0;i<12000;i=i+1) begin
        @(negedge clk);
        if(done_count==1) begin
          repeat(12) @(negedge clk);
          if(outputs!=4 || done_count!=1 || busy!==1'b0 || output_data_valid!==1'b0)
            fail("completion did not return to idle");
          // PUBLIC_COMPLETION_CHECK
          $display("HULLCIRQ_GLOBAL_PASS outputs=4 vector_hash=8b52fdd880a7fad416852253888208e291e884cf6993b96280ee380b48f5f9ee"); $finish;
        end
      end
      fail("job timeout");
    end
  end
  initial begin #1000000; fail("watchdog timeout"); end
  initial begin
    $display("HULLCIRQ_ROUTED_FUNCTIONAL_NO_SDF");
    $dumpfile("simulation.vcd");
    $dumpvars(0, clk, rst, config_data, config_data_valid, config_data_ready,
      load_data, load_data_valid, load_data_ready, output_data,
      output_data_valid, output_data_ready, busy, job_done);
  end
endmodule
