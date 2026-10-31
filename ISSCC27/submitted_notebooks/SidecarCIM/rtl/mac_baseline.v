// mac_baseline: conventional baseline, ONE multiply-accumulate unit + separate weight register file.
// Computes the same result as dcim_core / python/golden.py dcim_dot(w, x, WBITS, ABITS) = x @ w.
//
// PARAMETERS (defaults = spec/spec.yaml)
//   N_IN  = 32  dot-product length (rows), must be >= 2
//   N_OUT = 8   output channels (columns)
//   WBITS = 4   weight bits (unsigned)
//   ABITS = 4   activation bits (unsigned)
//
// DERIVED WIDTHS (identical to dcim_core)
//   AW   = $clog2(N_IN)                                  row address width        (5)
//   ROWW = N_OUT*WBITS                                   one weight row           (32)
//   YW   = $clog2(N_IN*(2^WBITS-1)*(2^ABITS-1) + 1)      one output, holds the max
//          sum 32*15*15 = 7200 without overflow                                   (13)
//
// PORTS (identical to dcim_core, same bit packing)
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
//
// Unsigned codes only: zero-point correction (signed weights/activations) is done outside the
// macro, the same way for all four designs (python/quant.py).
//
// PROTOCOL (all inputs sampled at rising edge of clk; same handshake as dcim_core)
//   Reset: rst=1 at an edge -> state LOAD, busy=0, valid=0, y=0. Weights are NOT reset:
//     rows written before rst survive it; after power-up they are undefined until every row
//     0..N_IN-1 has been written. A row whose load_en edge comes before the rst edge (even the
//     edge right before) is written. Do not assert load_en at the rst edge itself (undefined).
//   LOAD: while not busy, each edge with load_en=1 writes load_row into row load_addr.
//     One row per cycle, any order. load_en is ignored while busy.
//     Leaving DONE through a load returns to LOAD (valid -> 0, y keeps its value).
//   START: an edge with start=1, load_en=0 and busy=0 (state LOAD or DONE) latches the whole
//     x vector from x_in, clears y, and enters COMPUTE. start is ignored while load_en=1 or busy.
//     start may be asserted in the cycle right after the last load_en cycle.
//     x_in only needs to be valid at the start edge.
//   COMPUTE: N_IN*N_OUT cycles (256), one MAC per cycle, order j = 0..N_OUT-1 outer, i = 0..N_IN-1
//     inner: acc += w[i][j] * x[i]. On the last i of column j, y[j] <= acc + product, acc <= 0.
//     During COMPUTE y shows finished columns and zeros; it is only meaningful when valid=1.
//     busy goes to 1 at the start edge k itself: busy=1 after edge k through edge k+N_IN*N_OUT-1.
//   DONE: if start is sampled at edge k, then after edge k + N_IN*N_OUT (256 cycles): busy=0,
//     valid=1, y = final dot product. y and valid hold until the next accepted start, a load, or rst.
//   Throughput: N_IN*N_OUT+1 cycles per dot product with start re-asserted in DONE.
//     With start held high, valid is high for exactly one cycle per dot product.
//
// STORAGE: weights in N_IN rows of flip-flops (register file), read one WBITS weight per cycle
//   through a mux addressed by (i, j). Row i is written at its load_en edge.
//   CLK_GATE = 1 (default): each row is ROWW plain D flip-flops (q <= d) on its own gated clock,
//     icg(clk, en = load_en & !busy & load_addr == i) (rtl/icg.v); the gate opens only for that
//     write edge. CLK_GATE = 0: flip-flops on clk with a per-bit enable (hold) mux (original).
//   Same port behavior either way. Only the register file is gated; x, counters, acc, y stay on clk.
module mac_baseline #(
  parameter N_IN     = 32,
  parameter N_OUT    = 8,
  parameter WBITS    = 4,
  parameter ABITS    = 4,
  parameter CLK_GATE = 1
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
  output wire [N_OUT*$clog2(N_IN*((1<<WBITS)-1)*((1<<ABITS)-1)+1)-1:0] y
);
  localparam AW    = $clog2(N_IN);
  localparam ROWW  = N_OUT * WBITS;
  localparam YW    = $clog2(N_IN * ((1 << WBITS) - 1) * ((1 << ABITS) - 1) + 1);
  localparam JW    = (N_OUT > 1) ? $clog2(N_OUT) : 1;
  localparam PW    = WBITS + ABITS;                 // product width (<= YW when N_IN >= 2)
  localparam integer ILAST = N_IN - 1;
  localparam integer JLAST = N_OUT - 1;

  localparam [1:0] S_LOAD = 2'd0, S_COMP = 2'd1, S_DONE = 2'd2;

  reg  [1:0]            state;
  reg  [AW-1:0]         i;        // row counter
  reg  [JW-1:0]         j;        // column counter
  reg  [N_IN*ABITS-1:0] xq;       // latched x
  reg  [YW-1:0]         acc;
  reg  [N_OUT*YW-1:0]   yq;
  wire [N_IN*ROWW-1:0]  wflat;    // register file: row r at [r*ROWW +: ROWW]

  wire go = start & ~load_en & (state != S_COMP);
  assign busy  = (state == S_COMP);
  assign valid = (state == S_DONE);
  assign y     = yq;

  // register file, one row written per cycle
  genvar r;
  generate
    for (r = 0; r < N_IN; r = r + 1) begin : g_row
      localparam [AW-1:0] RA = r;
      wire           we = load_en && state != S_COMP && load_addr == RA;
      reg [ROWW-1:0] row;
      if (CLK_GATE != 0) begin : g_cg
        wire gclk;                        // pulses only on this row's write edge
        icg u_icg (.clk(clk), .en(we), .gclk(gclk));
        always @(posedge gclk)
          row <= load_row;
      end else begin : g_ff
        always @(posedge clk)
          if (we) row <= load_row;
      end
      assign wflat[r*ROWW +: ROWW] = row;
    end
  endgenerate

  // one MAC: read w[i][j] and x[i], multiply, add
  wire [WBITS-1:0] wsel = wflat[i*ROWW + j*WBITS +: WBITS];
  wire [ABITS-1:0] xsel = xq[i*ABITS +: ABITS];
  wire [PW-1:0]    prod = wsel * xsel;
  reg  [YW-1:0]    pe;
  always @(*) begin
    pe = {YW{1'b0}};
    pe[PW-1:0] = prod;
  end
  wire [YW-1:0] sum = acc + pe;

  wire ilast = (i == ILAST[AW-1:0]);
  wire jlast = (j == JLAST[JW-1:0]);

  // FSM
  always @(posedge clk) begin
    if (rst) begin
      state <= S_LOAD;
      i     <= {AW{1'b0}};
      j     <= {JW{1'b0}};
      xq    <= {(N_IN*ABITS){1'b0}};
      acc   <= {YW{1'b0}};
      yq    <= {(N_OUT*YW){1'b0}};
    end else begin
      case (state)
        S_COMP: begin
          if (ilast) begin
            yq[j*YW +: YW] <= sum;
            acc <= {YW{1'b0}};
            i   <= {AW{1'b0}};
            j   <= j + 1'b1;
            if (jlast) state <= S_DONE;
          end else begin
            acc <= sum;
            i   <= i + 1'b1;
          end
        end
        default: begin                  // S_LOAD, S_DONE
          if (go) begin
            state <= S_COMP;
            xq    <= x_in;
            yq    <= {(N_OUT*YW){1'b0}};
            acc   <= {YW{1'b0}};
            i     <= {AW{1'b0}};
            j     <= {JW{1'b0}};
          end else if (load_en) begin
            state <= S_LOAD;
          end
        end
      endcase
    end
  end
endmodule
