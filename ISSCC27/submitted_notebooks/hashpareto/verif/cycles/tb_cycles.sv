`timescale 1ns/1ps
// A1 cycle-measurement testbench: streams a fixed-length message into sha_top
// (32-bit AXI-Stream in/out, always-valid input, always-ready output) and
// reports total cycles from first input beat to last digest beat.
//
// Run per variant with the *baked* sources in flow/variants/uN/src:
//   iverilog -g2012 -o t.vvp -Ptb.U=$u -Ptb.NBYTES=$n \
//       verif/cycles/tb_cycles.sv flow/variants/u$u/src/*.sv
//   vvp t.vvp
//
// cycles_per_block = same design at NBYTES=B2 minus NBYTES=B1 (B2/64 - B1/64 blocks).
module tb;
  parameter int U = 1;
  parameter int NBYTES = 640;   // multiple of 4

  logic aclk = 0, aresetn = 0;
  logic [31:0] tdata;
  logic [3:0]  tkeep;
  logic        tvalid, tlast, tready_s;
  logic [31:0] mdata;
  logic        mvalid, mlast;

  sha_top #(.UNROLL(U)) dut (
    .aclk(aclk), .aresetn(aresetn), .m_axis_tready(1'b1),
    .m_axis_tdata(mdata), .m_axis_tvalid(mvalid), .m_axis_tlast(mlast),
    .s_axis_tdata(tdata), .s_axis_tkeep(tkeep), .s_axis_tvalid(tvalid),
    .s_axis_tlast(tlast), .s_axis_tready(tready_s)
  );

  always #5 aclk = ~aclk;

  localparam int WORDS = NBYTES / 4;
  int idx = 0;
  int cyc = 0, start = -1, first_out = -1;
  logic [255:0] dig;

  initial begin
    tvalid = 0; tlast = 0; tkeep = 4'hf; tdata = 0;
    #52 aresetn = 1;
  end

  always @(posedge aclk) if (aresetn) begin
    cyc <= cyc + 1;
    if (tvalid && tready_s) begin
      if (start < 0) start <= cyc;
      idx <= idx + 1;
    end
    if (mvalid) begin
      if (first_out < 0) first_out <= cyc;
      dig <= {dig[223:0], mdata};
      if (mlast) begin
        $display("RESULT U=%0d NBYTES=%0d start=%0d out=%0d total_cycles=%0d digest=%h",
                 U, NBYTES, start, first_out, cyc - start, {dig[223:0], mdata});
        $finish;
      end
    end
  end

  always @(negedge aclk) if (aresetn) begin
    if (idx < WORDS) begin
      tvalid <= 1;
      tdata  <= idx * 32'h01010101 + 32'h03020100;
      tkeep  <= 4'hf;
      tlast  <= (idx == WORDS - 1);
    end else begin
      tvalid <= 0;
    end
  end
endmodule
