// dcim_8bit: uniform 8-bit DCIM baseline = dcim_core with WBITS = ABITS = 8 (no other change).
// Ports, packing and protocol: see dcim_core.v header, with WBITS = ABITS = 8:
//   load_row 64 bits (N_OUT*8), x_in 256 bits (N_IN*8), YW = $clog2(32*255*255+1) = 21,
//   y 168 bits (N_OUT*21), storage 2048 weight bits, start->valid = 8 cycles.
// Weight storage: USE_LATCH (latches / flip-flops) and CLK_GATE (flip-flop build: one clock gate
//   per weight row, default 1; 0 = per-bit hold mux) are passed to dcim_core unchanged; see there.
//   Primary build = flip-flop storage with clock-gated rows (USE_LATCH=0, CLK_GATE=1); the latch
//   variant (USE_LATCH=1, parameter default) is kept for reference.
// Unsigned codes only: zero-point correction is done outside the macro (as for all four designs).
module dcim_8bit #(
  parameter N_IN      = 32,
  parameter N_OUT     = 8,
  parameter USE_LATCH = 1,
  parameter CLK_GATE  = 1
) (
  input  wire                                            clk,
  input  wire                                            rst,
  input  wire                                            load_en,
  input  wire [$clog2(N_IN)-1:0]                         load_addr,
  input  wire [N_OUT*8-1:0]                              load_row,
  input  wire                                            start,
  input  wire [N_IN*8-1:0]                               x_in,
  output wire                                            busy,
  output wire                                            valid,
  output wire [N_OUT*$clog2(N_IN*255*255+1)-1:0]         y,
  output wire [N_IN-1:0]                                 xbit
);
  dcim_core #(.N_IN(N_IN), .N_OUT(N_OUT), .WBITS(8), .ABITS(8), .USE_LATCH(USE_LATCH),
              .CLK_GATE(CLK_GATE)) u_core (
    .clk(clk), .rst(rst), .load_en(load_en), .load_addr(load_addr), .load_row(load_row),
    .start(start), .x_in(x_in), .busy(busy), .valid(valid), .y(y), .xbit(xbit));
endmodule
