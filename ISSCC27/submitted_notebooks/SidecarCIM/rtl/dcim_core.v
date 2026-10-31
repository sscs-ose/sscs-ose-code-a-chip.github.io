// dcim_core: dense unsigned DCIM macro, bit-exact with python/golden.py dcim_dot(w, x, WBITS, ABITS).
//
// PARAMETERS (defaults = spec/spec.yaml)
//   N_IN  = 32  dot-product length (rows), must be >= 2
//   N_OUT = 8   output channels (columns)
//   WBITS = 4   weight bits (unsigned)
//   ABITS = 4   activation bits (unsigned)
//   USE_LATCH = 1  weight storage: 1 = level-sensitive latches, 0 = flip-flops.
//                  Both give identical cycle behavior at the ports.
//   CLK_GATE  = 1  flip-flop weight storage (USE_LATCH=0) only: 1 = one clock gate (icg.v) per
//                  weight row, 0 = per-bit hold mux (original). Same port behavior. Ignored
//                  when USE_LATCH=1 (latch storage unchanged). Needs rtl/icg.v when 1.
//
// Measured builds use flip-flop storage with clock-gated rows (USE_LATCH=0, CLK_GATE=1); every
//   measured build (synthesis, layout, PPA) sets these. The latch variant (USE_LATCH=1, still
//   the parameter default) is kept for reference only.
//
// DERIVED WIDTHS (values in parentheses: defaults N_IN=32, N_OUT=8, WBITS=ABITS=4)
//   AW   = $clog2(N_IN)                                  row address width        (5)
//   ROWW = N_OUT*WBITS                                   one weight row           (32)
//   YW   = $clog2(N_IN*(2^WBITS-1)*(2^ABITS-1) + 1)      one output, holds the max
//          sum N_IN*(2^WBITS-1)*(2^ABITS-1) without overflow (32*15*15 = 7200)    (13)
//   All widths and loops follow WBITS and ABITS; nothing assumes WBITS=4 or WBITS=ABITS.
//
// DENSE COMPARISON POINTS (N_IN=32, N_OUT=8, primary build USE_LATCH=0, CLK_GATE=1)
//   point  WBITS ABITS  load_addr load_row x_in  YW  y    xbit  max y   weight FFs  ICGs
//   W4A4     4     4        5        32     128  13  104   32    7200     1024       32
//   W6A4     6     4        5        48     128  15  120   32   30240     1536       32
//   W7A4     7     4        5        56     128  16  128   32   60960     1792       32
//   W8A4     8     4        5        64     128  17  136   32  122400     2048       32
//   W4A8     4     8        5        32     256  17  136   32  122400     1024       32
//   ABITS=4 points: start->valid = 4 edges, 5 cycles back to back. W4A8: 8 edges, 9 cycles.
//   All: weight load 32 cycles (one row per cycle); x_in sampled only at the start edge.
//   (W8A8 = dcim_8bit.v: see its header.)
//
// PORTS
//   clk                     in   single clock, all state changes on rising edge
//   rst                     in   synchronous, active high
//   load_en                 in   write one weight row this cycle
//   load_addr [AW-1:0]      in   row index i (0..N_IN-1)
//   load_row  [ROWW-1:0]    in   load_row[j*WBITS + b] = bit b of w[i][j]  (column 0 in LSBs)
//   start                   in   begin one dot product
//   x_in   [N_IN*ABITS-1:0] in   x_in[i*ABITS +: ABITS] = x[i]  (row 0 in LSBs)
//   busy                    out  1 while computing
//   valid                   out  1 while y holds a finished result
//   y     [N_OUT*YW-1:0]    out  y[j*YW +: YW] = sum_i x[i]*w[i][j]  (column 0 in LSBs)
//   xbit  [N_IN-1:0]        out  input bit-plane consumed at the next edge: while busy=1,
//                                xbit[i] = bit a of x[i], where the edge k+1+n (n = 0..ABITS-1
//                                after start edge k) uses a = ABITS-1-n. Meaningless when busy=0.
//                                Read-only tap for the sidecar (shares the dense bit-plane).
//
// Unsigned codes only: zero-point correction (signed weights/activations) is done outside the
// macro, the same way for all four designs (python/quant.py).
//
// PROTOCOL (all inputs sampled at rising edge of clk)
//   Reset: rst=1 at an edge -> state LOAD, busy=0, valid=0, y=0. Weights are NOT reset:
//     rows written before rst survive it; after power-up they are undefined until every row
//     0..N_IN-1 has been written. A row whose load_en edge comes before the rst edge (even the
//     edge right before) is written. Do not assert load_en at the rst edge itself (undefined).
//   LOAD: while not busy, each edge with load_en=1 writes load_row into row load_addr.
//     One row per cycle, any order; rows keep their value until rewritten.
//     load_en is ignored while busy. Leaving DONE through a load returns to LOAD (valid -> 0).
//   START: an edge with start=1, load_en=0 and busy=0 (state LOAD or DONE) latches the whole
//     x vector from x_in, clears y, and enters COMPUTE. start is ignored while load_en=1 or busy.
//     start may be asserted in the cycle right after the last load_en cycle.
//     x_in only needs to be valid at the start edge.
//   COMPUTE: ABITS cycles, x bits MSB first. At each of the next ABITS edges, for every column j:
//       part_j = sum_b ( popcount_i( w[i][j][b] & x[i][a] ) << b )
//       acc_j  = (acc_j << 1) + part_j            (a = ABITS-1 down to 0)
//     busy goes to 1 at the start edge k itself: busy=1 after edge k through edge k+ABITS-1.
//   DONE: if start is sampled at edge k, then after edge k+ABITS (ABITS cycles): busy=0, valid=1,
//     y = final dot product. y and valid hold until the next accepted start (y cleared, valid 0),
//     a load (valid 0, y keeps its value), or rst. Back-to-back: start may be asserted in DONE.
//   Throughput: ABITS+1 cycles per dot product with start held/re-asserted each time in DONE.
//     With start held high, valid is high for exactly one cycle per dot product.
//
// STORAGE: weights live in N_IN rows of ROWW bits. The write address, data and enable are
//   registered at the rising edge (registered write port): a flip-flop row is written at the
//   edge after its load_en edge, a latch row in the clock-low phase in between.
//   Primary (USE_LATCH=0, CLK_GATE=1): each row is ROWW plain D flip-flops (q <= d) on its own
//   gated clock, icg(clk, en = row write enable); the gate opens only for that one write edge.
//   Only weight rows are gated; the write port, x lanes, accumulators and FSM stay on clk.
//   USE_LATCH=0, CLK_GATE=0: flip-flops on clk with a per-bit enable (hold) mux.
//   Reference (USE_LATCH=1): standard-cell latches; the selected row latch is transparent
//   during the clock-low phase after the write edge (enable = ~clk & row_sel), so data is
//   stable while open.
//   Real DCIM uses custom SRAM bitcells; standard-cell storage is a stated limitation.
module dcim_core #(
  parameter N_IN      = 32,
  parameter N_OUT     = 8,
  parameter WBITS     = 4,
  parameter ABITS     = 4,
  parameter USE_LATCH = 1,
  parameter CLK_GATE  = 1
) (
  input  wire                                                      clk,
  input  wire                                                      rst,
  input  wire                                                      load_en,
  input  wire [$clog2(N_IN)-1:0]                                   load_addr,
  input  wire [N_OUT*WBITS-1:0]                                    load_row,
  input  wire                                                      start,
  input  wire [N_IN*ABITS-1:0]                                     x_in,
  output wire                                                      busy,
  output wire                                                      valid,
  output wire [N_OUT*$clog2(N_IN*((1<<WBITS)-1)*((1<<ABITS)-1)+1)-1:0] y,
  output wire [N_IN-1:0]                                           xbit
);
  localparam AW    = $clog2(N_IN);
  localparam ROWW  = N_OUT * WBITS;
  localparam YW    = $clog2(N_IN * ((1 << WBITS) - 1) * ((1 << ABITS) - 1) + 1);
  localparam PARTW = $clog2(N_IN * ((1 << WBITS) - 1) + 1);   // one-cycle partial sum
  localparam CW    = (ABITS > 1) ? $clog2(ABITS) : 1;          // bit counter
  localparam integer CNT0 = ABITS - 1;

  localparam [1:0] S_LOAD = 2'd0, S_COMP = 2'd1, S_DONE = 2'd2;

  reg  [1:0]            state;
  reg  [CW-1:0]         cnt;      // input bits left minus one
  reg  [N_IN*ABITS-1:0] xs;       // x lanes, shifted left each cycle
  reg  [N_OUT*YW-1:0]   acc;
  reg                   we_q;     // registered write port
  reg  [AW-1:0]         wa_q;
  reg  [ROWW-1:0]       wd_q;

  wire [N_IN*ROWW-1:0]  wflat;    // all weights: row i at [i*ROWW +: ROWW]
  wire                  go = start & ~load_en & (state != S_COMP);

  assign busy  = (state == S_COMP);
  assign valid = (state == S_DONE);
  assign y     = acc;

  // bit-plane tap: MSB of each x lane
  genvar t;
  generate
    for (t = 0; t < N_IN; t = t + 1) begin : g_xbit
      assign xbit[t] = xs[t*ABITS + ABITS-1];
    end
  endgenerate

  // registered write port
  always @(posedge clk) begin
    if (rst) begin
      we_q <= 1'b0;
      wa_q <= {AW{1'b0}};
      wd_q <= {ROWW{1'b0}};
    end else begin
      we_q <= load_en & (state != S_COMP);
      wa_q <= load_addr;
      wd_q <= load_row;
    end
  end

  // weight rows
  genvar r;
  generate
    for (r = 0; r < N_IN; r = r + 1) begin : g_row
      localparam [AW-1:0] RA = r;
      wire           sel = we_q & (wa_q == RA);
      reg [ROWW-1:0] row;
      if (USE_LATCH != 0) begin : g_lat
        wire len = sel & ~clk;            // open in clock-low phase
        /* verilator lint_off LATCH */  // intended storage latch
        always @(*)
          if (len) row = wd_q;
        /* verilator lint_on LATCH */
      end else if (CLK_GATE != 0) begin : g_cg
        wire gclk;                        // pulses only on this row's write edge
        icg u_icg (.clk(clk), .en(sel), .gclk(gclk));
        always @(posedge gclk)
          row <= wd_q;
      end else begin : g_ff
        always @(posedge clk)
          if (sel) row <= wd_q;
      end
      assign wflat[r*ROWW +: ROWW] = row;
    end
  endgenerate

  // AND array, popcount per weight bit, shift-add, shift-accumulate
  reg [N_OUT*YW-1:0] acc_nx;
  reg [PARTW-1:0]    pc, part, one;
  reg [YW-1:0]       pe;
  integer i, j, b;
  always @(*) begin
    for (j = 0; j < N_OUT; j = j + 1) begin
      part = {PARTW{1'b0}};
      for (b = 0; b < WBITS; b = b + 1) begin
        pc = {PARTW{1'b0}};
        for (i = 0; i < N_IN; i = i + 1) begin
          one    = {PARTW{1'b0}};
          one[0] = wflat[i*ROWW + j*WBITS + b] & xs[i*ABITS + ABITS-1];
          pc     = pc + one;
        end
        part = part + (pc << b);
      end
      pe = {YW{1'b0}};
      pe[PARTW-1:0] = part;
      acc_nx[j*YW +: YW] = (acc[j*YW +: YW] << 1) + pe;
    end
  end

  // shift each x lane left by one (next bit to the MSB)
  reg [N_IN*ABITS-1:0] xs_nx;
  integer k;
  always @(*)
    for (k = 0; k < N_IN; k = k + 1)
      xs_nx[k*ABITS +: ABITS] = xs[k*ABITS +: ABITS] << 1;

  // FSM
  always @(posedge clk) begin
    if (rst) begin
      state <= S_LOAD;
      cnt   <= {CW{1'b0}};
      xs    <= {(N_IN*ABITS){1'b0}};
      acc   <= {(N_OUT*YW){1'b0}};
    end else begin
      case (state)
        S_COMP: begin
          acc <= acc_nx;
          xs  <= xs_nx;
          cnt <= cnt - 1'b1;
          if (cnt == {CW{1'b0}}) state <= S_DONE;
        end
        default: begin                  // S_LOAD, S_DONE
          if (go) begin
            state <= S_COMP;
            xs    <= x_in;
            acc   <= {(N_OUT*YW){1'b0}};
            cnt   <= CNT0[CW-1:0];
          end else if (load_en) begin
            state <= S_LOAD;
          end
        end
      endcase
    end
  end
endmodule
