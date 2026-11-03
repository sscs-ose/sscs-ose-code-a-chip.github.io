// Back-to-back RISC-V M-extension multiplies (MUL, MULH, MULHSU, MULHU) with random 32-bit operands,
// as the PicoRV32 core issues them through its PCPI port.  50 MHz; 300 clock cycles after reset.
`timescale 1ps/1ps
module tb;
  reg clk = 0, resetn = 0, pcpi_valid = 0;
  reg [31:0] pcpi_insn = 0, pcpi_rs1 = 0, pcpi_rs2 = 0;
  wire pcpi_wr, pcpi_wait, pcpi_ready; wire [31:0] pcpi_rd;
  picorv32_pcpi_fast_mul dut(.clk(clk), .resetn(resetn), .pcpi_valid(pcpi_valid), .pcpi_insn(pcpi_insn),
    .pcpi_rs1(pcpi_rs1), .pcpi_rs2(pcpi_rs2), .pcpi_wr(pcpi_wr), .pcpi_rd(pcpi_rd), .pcpi_wait(pcpi_wait),
    .pcpi_ready(pcpi_ready));
  always #10000 clk = ~clk;
  integer i, seed = 7;
  reg [1:0] f3;
  initial begin
    $dumpfile("picorv32_fast_mul.vcd"); $dumpvars(0, tb);
    repeat (3) @(posedge clk);
    #500 resetn = 1;
    for (i = 0; i < 300; i = i + 1) begin
      @(posedge clk); #500;
      pcpi_valid = 1;
      f3 = $random(seed);
      pcpi_insn = {7'b0000001, 10'd0, 1'b0, f3, 5'd0, 7'b0110011};
      pcpi_rs1 = $random(seed); pcpi_rs2 = $random(seed);
    end
    @(posedge clk); $finish;
  end
endmodule
