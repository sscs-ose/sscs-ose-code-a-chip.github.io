// ============================================================================
//  add_cells.v -- behavioural models for the nangate45 adder cells used by the
//  ABC mapping (the platform's cells_adders.v is a Yosys techmap file, not a
//  simulation model).
// ============================================================================
`timescale 1ns/1ps
module FA_X1 (A, B, CI, CO, S);
  input  A, B, CI;
  output CO, S;
  assign S  = A ^ B ^ CI;
  assign CO = (A & B) | (A & CI) | (B & CI);
endmodule
