// sidecar: outlier side path, bit-exact with python/golden.py sidecar_dot(idx, val, x, ABITS, VB).
//   y[j] = sum_s val[s][j] * x[idx[s][j]]   (val signed VB-bit, x unsigned ABITS-bit)
//
// PARAMETERS (defaults = spec/spec.yaml)
//   N_IN  = 32  rows (slot row index range), must be >= 2
//   N_OUT = 8   columns
//   ABITS = 4   activation bits (unsigned)
//   VB    = 12  slot value bits, two's complement (outlier.weight_bits)
//   K     = 2   slots per column (outlier.budget_per_output); sweep K by override
//   PARALLEL = 0  0 = bit-serial (default, shares the dense bit-plane): per cycle, per slot,
//                     select the slot row's bit from xbit, AND with the value, add, shift-accumulate.
//                 1 = ablation: one VB x ABITS multiplier per slot, applied once at the start edge
//                     on x_in; the result is then held. Latency kept at ABITS for a fair comparison
//                     (it could finish in 1 cycle).
//   CLK_GATE = 1  slot storage: 1 = one clock gate (icg.v) per column, 0 = per-bit hold mux
//                 (original). Same port behavior. Needs rtl/icg.v when 1.
//
// DERIVED WIDTHS
//   AW  = $clog2(N_IN)                          slot row index                        (5)
//   JW  = max(1, $clog2(N_OUT))                 column address                        (3)
//   SLW = AW + VB                               one slot                              (17)
//   SCW = VB + $clog2(K*(2^ABITS-1) + 1)        one output, signed; holds +-K*2^(VB-1)*(2^ABITS-1)
//                                               = +-61,440 without overflow            (17)
//
// PORTS
//   clk, rst                    in   single clock (rising edge); synchronous active-high reset
//   load_en                     in   write one column's K slots this cycle
//   load_col   [JW-1:0]         in   column j (0..N_OUT-1)
//   load_slots [K*SLW-1:0]      in   slot s at [s*SLW +: SLW]: row index in the low AW bits,
//                                    value (two's complement) in the high VB bits.
//                                    Unused slot: value 0 (index ignored). Duplicate rows add.
//   start                       in   begin one dot product
//   x_in   [N_IN*ABITS-1:0]     in   x_in[i*ABITS +: ABITS] = x[i]; used only when PARALLEL=1
//                                    (sampled at the start edge)
//   xbit   [N_IN-1:0]           in   bit-plane, used only when PARALLEL=0: sampled at edges
//                                    k+1+n (n = 0..ABITS-1, start at edge k), xbit[i] = bit
//                                    ABITS-1-n of x[i] (MSB first). In sidecarcim_top this is
//                                    dcim_core.xbit, which has exactly this timing.
//   busy, valid                 out  as dcim_core
//   y      [N_OUT*SCW-1:0]      out  y[j*SCW +: SCW], signed two's complement (column 0 in LSBs)
//
// Raw integer only: zero-point correction (-zx*sum(val)) is done outside the macro.
//
// PROTOCOL: identical to dcim_core except a load writes one column (K slots) per cycle.
//   Reset: state LOAD, busy=0, valid=0, y=0. Slots are NOT reset: slots written before rst survive;
//     after power-up every column 0..N_OUT-1 must be written. Do not assert load_en at the rst edge.
//   LOAD: while not busy, each edge with load_en=1 writes load_slots into column load_col
//     (written at that edge, flip-flops). load_en is ignored while busy. A load in DONE -> LOAD.
//   START: an edge with start=1, load_en=0 and busy=0 enters COMPUTE. start may follow the last
//     load in the next cycle. busy=1 after start edge k through edge k+ABITS-1.
//   COMPUTE (PARALLEL=0), at each of edges k+1..k+ABITS, per column j:
//       acc_j = (acc_j << 1) + sum_s ( xbit[idx_s] ? val_s : 0 )
//   DONE: after edge k+ABITS: busy=0, valid=1, y final; holds until the next start, a load, or rst.
//     With start held high, valid is high for exactly one cycle per dot product.
//     y is meaningful only while valid=1.
//
// STORAGE: N_OUT*K*SLW = 272 flip-flops (too few to justify latches), column j written at its
//   load edge (ld_j = load_en & !busy & load_col == j). CLK_GATE=1: column j's K*SLW flip-flops
//   are plain D flip-flops (q <= d) on a gated clock icg(clk, en = ld_j) that opens only for that
//   edge. CLK_GATE=0: flip-flops on clk with a per-bit enable (hold) mux. Datapath, acc and FSM
//   stay on clk.
// HARDWARE per slot (PARALLEL=0): one N_IN:1 mux on xbit, VB AND gates; per column one K-input
//   SCW-bit adder + SCW-bit shift-accumulator.
module sidecar #(
  parameter N_IN     = 32,
  parameter N_OUT    = 8,
  parameter ABITS    = 4,
  parameter VB       = 12,
  parameter K        = 2,
  parameter PARALLEL = 0,
  parameter CLK_GATE = 1
) (
  input  wire                                                clk,
  input  wire                                                rst,
  input  wire                                                load_en,
  input  wire [((N_OUT > 1) ? $clog2(N_OUT) : 1)-1:0]        load_col,
  input  wire [K*($clog2(N_IN)+VB)-1:0]                      load_slots,
  input  wire                                                start,
  /* verilator lint_off UNUSEDSIGNAL */  // only one of x_in / xbit is used, per PARALLEL
  input  wire [N_IN*ABITS-1:0]                               x_in,
  input  wire [N_IN-1:0]                                     xbit,
  /* verilator lint_on UNUSEDSIGNAL */
  output wire                                                busy,
  output wire                                                valid,
  output wire [N_OUT*(VB+$clog2(K*((1<<ABITS)-1)+1))-1:0]    y
);
  localparam AW  = $clog2(N_IN);
  localparam JW  = (N_OUT > 1) ? $clog2(N_OUT) : 1;
  localparam SLW = AW + VB;
  localparam SCW = VB + $clog2(K * ((1 << ABITS) - 1) + 1);
  localparam CW  = (ABITS > 1) ? $clog2(ABITS) : 1;
  localparam integer CNT0 = ABITS - 1;

  localparam [1:0] S_LOAD = 2'd0, S_COMP = 2'd1, S_DONE = 2'd2;

  reg  [1:0]              state;
  reg  [CW-1:0]           cnt;
  reg  [N_OUT*SCW-1:0]    acc;
  wire [N_OUT*K*SLW-1:0]  slots;    // column c at [c*K*SLW +: K*SLW]

  wire go = start & ~load_en & (state != S_COMP);
  assign busy  = (state == S_COMP);
  assign valid = (state == S_DONE);
  assign y     = acc;

  // slot storage, one column per load
  genvar c;
  generate
    for (c = 0; c < N_OUT; c = c + 1) begin : g_col
      localparam [JW-1:0] CA = c;
      wire            ld = load_en && state != S_COMP && load_col == CA;
      reg [K*SLW-1:0] col;
      if (CLK_GATE != 0) begin : g_cg
        wire gclk;                        // pulses only on this column's load edge
        icg u_icg (.clk(clk), .en(ld), .gclk(gclk));
        always @(posedge gclk)
          col <= load_slots;
      end else begin : g_ff
        always @(posedge clk)
          if (ld) col <= load_slots;
      end
      assign slots[c*K*SLW +: K*SLW] = col;
    end
  endgenerate

  // per-column next value: bit-serial step or parallel product
  reg [N_OUT*SCW-1:0] acc_nx;
  reg [SLW-1:0]       sl;
  reg [AW-1:0]        ix;
  reg [SCW-1:0]       v, xe, sum;
  integer j, s;
  always @(*) begin
    for (j = 0; j < N_OUT; j = j + 1) begin
      sum = {SCW{1'b0}};
      for (s = 0; s < K; s = s + 1) begin
        sl = slots[(j*K + s)*SLW +: SLW];
        ix = sl[AW-1:0];
        v  = {{(SCW-VB){sl[SLW-1]}}, sl[SLW-1:AW]};    // sign-extend value
        xe = {SCW{1'b0}};
        if (PARALLEL != 0) begin
          xe[ABITS-1:0] = x_in[ix*ABITS +: ABITS];
          sum = sum + v * xe;                         // mod 2^SCW = signed product
        end else begin
          sum = sum + (xbit[ix] ? v : {SCW{1'b0}});   // AND gate on the value
        end
      end
      if (PARALLEL != 0) acc_nx[j*SCW +: SCW] = sum;
      else               acc_nx[j*SCW +: SCW] = (acc[j*SCW +: SCW] << 1) + sum;
    end
  end

  // FSM
  always @(posedge clk) begin
    if (rst) begin
      state <= S_LOAD;
      cnt   <= {CW{1'b0}};
      acc   <= {(N_OUT*SCW){1'b0}};
    end else begin
      case (state)
        S_COMP: begin
          if (PARALLEL == 0) acc <= acc_nx;
          cnt <= cnt - 1'b1;
          if (cnt == {CW{1'b0}}) state <= S_DONE;
        end
        default: begin                  // S_LOAD, S_DONE
          if (go) begin
            state <= S_COMP;
            acc   <= (PARALLEL != 0) ? acc_nx : {(N_OUT*SCW){1'b0}};
            cnt   <= CNT0[CW-1:0];
          end else if (load_en) begin
            state <= S_LOAD;
          end
        end
      endcase
    end
  end
endmodule
