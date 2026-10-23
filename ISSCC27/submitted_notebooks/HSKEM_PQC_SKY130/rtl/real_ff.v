// Zero-delay behavioural models of the four flip-flop cells of the routed HSKEM chip, for scripts/real_netlist.py.
// LOAD copies LV into the register (the RTL state at the start of the gate-level window; a register the RTL simulation
// leaves unknown, x or z, is loaded as 0, since a real chip holds some value); simulation only.
// SPDX-License-Identifier: Apache-2.0
`timescale 1ns/1ps
module rf_dfrtp(input CLK, input D, input RESET_B, output reg Q, input LOAD, input LV);
  always @(posedge CLK or negedge RESET_B) if (!RESET_B) Q <= 1'b0; else Q <= D;
  always @(posedge LOAD) Q = (LV === 1'b1) ? 1'b1 : 1'b0;   // an unknown RTL register is loaded as 0
endmodule
module rf_dfstp(input CLK, input D, input SET_B, output reg Q, input LOAD, input LV);
  always @(posedge CLK or negedge SET_B) if (!SET_B) Q <= 1'b1; else Q <= D;
  always @(posedge LOAD) Q = (LV === 1'b1) ? 1'b1 : 1'b0;   // an unknown RTL register is loaded as 0
endmodule
module rf_dfxtp(input CLK, input D, output reg Q, input LOAD, input LV);
  always @(posedge CLK) Q <= D;
  always @(posedge LOAD) Q = (LV === 1'b1) ? 1'b1 : 1'b0;   // an unknown RTL register is loaded as 0
endmodule
module rf_edfxtp(input CLK, input D, input DE, output reg Q, input LOAD, input LV);
  always @(posedge CLK) if (DE) Q <= D;
  always @(posedge LOAD) Q = (LV === 1'b1) ? 1'b1 : 1'b0;   // an unknown RTL register is loaded as 0
endmodule
