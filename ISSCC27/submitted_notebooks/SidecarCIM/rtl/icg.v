// icg: integrated clock gate, gclk = clk & (en latched while clk is low).
//
// PORTS
//   clk   in   free-running clock
//   en    in   enable; must be stable before the rising edge of clk (it passes a latch that is
//              transparent while clk is low, so changes while clk is high cannot glitch gclk)
//   gclk  out  gated clock: a rising edge with clk in every cycle whose en is 1 at that edge
//
// A flop on gclk with q <= d behaves exactly as a flop on clk with "if (en) q <= d":
// same edge, same data, no hold mux.
// SYNTHESIS (Yosys defines it in read_verilog): sky130_fd_sc_hd__dlclkp_1, a latch-based
// clock-gating cell that CTS and STA treat as a clock gate.
// Otherwise (Icarus, Verilator): behavioral latch + AND.
module icg (
  input  wire clk,
  input  wire en,
  output wire gclk
);
`ifdef SYNTHESIS
  sky130_fd_sc_hd__dlclkp_1 u_cg (.CLK(clk), .GATE(en), .GCLK(gclk));
`else
  reg en_l;
  /* verilator lint_off LATCH */  // intended ICG latch
  always @(*)
    if (!clk) en_l = en;          // transparent while clk is low
  /* verilator lint_on LATCH */
  assign gclk = clk & en_l;
`endif
endmodule
