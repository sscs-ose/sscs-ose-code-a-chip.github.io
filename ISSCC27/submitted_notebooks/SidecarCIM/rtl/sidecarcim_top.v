// sidecarcim_top: dense DCIM core + outlier sidecar + merge.
//   Y[j] = (dcim_dot[j] << S[j]) + sidecar_dot[j]
//   = (golden.dcim_dot(w, x, WBITS, ABITS) << S) + golden.sidecar_dot(idx, val, x, ABITS, VB)
// The sidecar consumes dcim_core's own input bit-plane (xbit) each cycle, so both finish together:
// zero extra compute cycles for outliers (with PIPE_MERGE=0 the latency is ABITS, as for dcim_core).
// PIPE_MERGE=1 adds one output register after the merge: latency ABITS+1, same throughput.
//
// PARAMETERS: N_IN=32, N_OUT=8, WBITS=4, ABITS=4, VB=12, K=2 (spec defaults), USE_LATCH=1
//   (dense storage, see dcim_core), PARALLEL=0 (sidecar datapath, see sidecar).
//   PIPE_MERGE=0 (default): merge is combinational to the y port (the original design, bit for
//   bit). 1 = register y and valid after the merge (+1 cycle latency, same ABITS+1-cycle
//   back-to-back throughput); see PROTOCOL, PIPE_MERGE=1. Reason: post-layout STA (max_ss) of the
//   PIPE_MERGE=0 build shows the worst path S[j] -> barrel shifter -> merge adder -> y port
//   (plus the 6 ns output delay), not the bit-serial loops.
//   VB = spec outlier.weight_bits.
//   CLK_GATE=1 (default): clock-gated storage in the flip-flop build (USE_LATCH=0), see STORAGE.
//   0 = per-bit hold muxes (original). Same port behavior. Needs rtl/icg.v.
//   Measured builds use flip-flop storage with clock-gated rows (USE_LATCH=0, CLK_GATE=1); every
//   measured build sets these. The latch variant (USE_LATCH=1, parameter default) is kept for
//   reference only.
//   SBITS=4 (default): width of the per-column shift S (stored register, s_load_shift port,
//   barrel-shifter select). 4 = the original design bit for bit (S 0..11 at VB=12). 3 = S 0..7
//   only: 3-bit S registers, an 8-position barrel shifter and a narrower merge/y (YTW 26 -> 22).
//   SBITS=3 justified by python/out/srange.json (S<=7 on both models): the encoder's S never
//   exceeds 7 in any column of GPT-2 or Qwen, so SBITS=3 gives bit-identical accuracy.
//   Final build: USE_LATCH=0, CLK_GATE=1, PARALLEL=0, K=2, PIPE_MERGE=1, SBITS=3
//   (flow/sidecarcim_top_ff_pipe_s3).
//
// DERIVED WIDTHS (values: defaults, SBITS=4 | SBITS=3)
//   AW, ROWW, YW as dcim_core (5, 32, 13); JW, SLW, SCW as sidecar (3, 17, 17)
//   SBW  = SBITS                                  stored S per column               (4 | 3)
//   SMAX = min(VB-1, 2^SBITS-1)                   largest legal S                  (11 | 7)
//   YTW  = max(YW + SMAX + 1, SCW) + 1            merged output, signed: dense max
//          7200*2^SMAX needs YW+SMAX bits unsigned, +1 sign, +1 for the signed add (26 | 22)
//   (At SMAX = VB-1 this is the original max(YW+VB, SCW)+1 = golden.merged_width.)
//
// PORTS
//   clk, rst                      in   single clock (rising edge); synchronous active-high reset
//   w_load_en, w_load_addr, w_load_row   in   dense weight row write = dcim_core load_en/addr/row
//   s_load_en                     in   write one sidecar column this cycle
//   s_load_col   [JW-1:0]         in   column j
//   s_load_slots [K*SLW-1:0]      in   = sidecar load_slots (row index low AW bits, value high VB bits)
//   s_load_shift [SBW-1:0]        in   S[j] for that column, written on the same edge.
//                                      Legal S: 0..SMAX (SBITS=4: 0..VB-1 = 0..11, as golden;
//                                      VB..15 may wrap y. SBITS=3: 0..7, every code legal).
//   start                         in   begin one dot product (both paths)
//   x_in [N_IN*ABITS-1:0]         in   x_in[i*ABITS +: ABITS] = x[i]
//   busy, valid                   out  as dcim_core
//   y [N_OUT*YTW-1:0]             out  y[j*YTW +: YTW] = Y[j], signed two's complement
//
// Raw integer only: zero-point correction and all real scaling (sx*sw/2^S) and bias are done
// outside the macro (python/llm_layer.py), the same way for every dense and sidecar design.
//
// PROTOCOL (all inputs sampled at the rising edge)
//   Reset: state LOAD, busy=0, valid=0, y=0, every S[j]=0. Weights and slots are NOT reset
//     (survive rst); S does NOT survive rst. After power-up or rst, rewrite every sidecar column
//     (s_load_* also reloads S); after power-up all N_IN dense rows must be written too.
//     Do not assert either load_en at the rst edge.
//   LOAD: while not busy, dense rows (one per cycle, w_load_*) and sidecar columns (one per cycle,
//     s_load_*) are written; both may load in the same cycle. Loads are ignored while busy.
//   START: an edge with start=1, w_load_en=0, s_load_en=0 and busy=0 starts both paths.
//     start is ignored while either load_en is 1 or busy. It may follow the last load in the next
//     cycle. x_in is sampled only at the start edge. busy=1 after start edge k through k+ABITS-1.
//   DONE: after edge k+ABITS: busy=0, valid=1, y final (merge is combinational on the two
//     registered results). Holds until the next start, a load, or rst. With start held high,
//     valid is high for exactly one cycle per dot product. y meaningful only while valid=1.
//
// PROTOCOL, PIPE_MERGE=1 (loads, start, busy and x_in sampling exactly as above; only valid and
//   y move one edge later). Let cv = the PIPE_MERGE=0 valid (both cores DONE).
//   Output register: at every edge, valid <= cv; if cv=1, y <= merge (the PIPE_MERGE=0 y);
//     if cv=0, y holds. rst clears valid and y.
//   Start accepted at edge k (busy=1 after edges k..k+ABITS-1, as above):
//     after edge k+ABITS:   busy=0, valid=0 (result in the merge stage). A start sampled at the
//                           next edge k+ABITS+1 is accepted (back-to-back).
//     after edge k+ABITS+1: valid=1, y final. Latency start -> valid = ABITS+1 edges.
//   Back-to-back (start held high): starts at edges k, k+ABITS+1, k+2(ABITS+1), ...; valid=1
//     for exactly one cycle after each edge k+n(ABITS+1)+ABITS+1 = while the NEXT dot product
//     is busy (valid and busy may both be 1). Throughput: one dot product per ABITS+1 cycles,
//     same as PIPE_MERGE=0.
//   Idle: with no new start, valid stays 1 and y holds. A load at edge e (or a start) clears cv
//     after e, so valid falls after edge e+1 (one cycle later than PIPE_MERGE=0); y keeps the
//     finished result (the load edge itself still captures the old S and accumulators).
//   Equivalence (outside the rst edge): valid_P1(after edge n) = valid_P0(after edge n-1), and
//     whenever valid_P1=1, y_P1(after edge n) = y_P0(after edge n-1).
// FLOW NOTE: merge = per column a 13->24-bit barrel shifter (S, 12 positions) + 26-bit adder
//   after the accumulators (SBITS=3: 13->20-bit, 8 positions, + 22-bit adder). PIPE_MERGE=0: it drives the y port directly (the post-layout worst path).
//   PIPE_MERGE=1: it ends at a register (reg-to-reg, no output delay); the y port is driven
//   straight from flip-flops, as in dcim_core.
// STORAGE (CG = CLK_GATE when USE_LATCH=0; CG = 0 when USE_LATCH=1, so the latch build is the
//   original design bit for bit):
//   dense weights  dcim_core.CLK_GATE = CG: one clock gate per weight row (en = row write).
//   sidecar slots  sidecar.CLK_GATE = CG: one clock gate per column (en = ld_j).
//   S[j]           CG=1: plain D flip-flops on icg(clk, en = ld_j | rst), D = rst ? 0 : s_load_shift,
//                  ld_j = s_load_en & !busy & s_load_col == j. rst opens the gate, so the
//                  synchronous reset still clears S at the rst edge; rst cannot share the slot
//                  gate because slots must survive rst. CG=0: flip-flops on clk + hold mux.
//   Each sidecar column thus has two gates (slots: ld_j; S: ld_j | rst). Gated flops are written
//   at exactly the edges the original enables selected. Datapath, acc, x lanes, FSM stay on clk.
//   y register (PIPE_MERGE=1 only, N_OUT*YTW = 208 bits; 176 at SBITS=3): CG=1: plain D flip-flops on one
//                  icg(clk, en = cv | rst), D = rst ? 0 : merge (loads once per dot product
//                  in back-to-back use). CG=0: flip-flops on clk + hold mux. valid: one flop on clk.
module sidecarcim_top #(
  parameter N_IN      = 32,
  parameter N_OUT     = 8,
  parameter WBITS     = 4,
  parameter ABITS     = 4,
  parameter VB        = 12,
  parameter K         = 2,
  parameter USE_LATCH = 1,
  parameter PARALLEL  = 0,
  parameter CLK_GATE  = 1,
  parameter PIPE_MERGE = 0,
  parameter SBITS     = 4
) (
  input  wire                                         clk,
  input  wire                                         rst,
  input  wire                                         w_load_en,
  input  wire [$clog2(N_IN)-1:0]                      w_load_addr,
  input  wire [N_OUT*WBITS-1:0]                       w_load_row,
  input  wire                                         s_load_en,
  input  wire [((N_OUT > 1) ? $clog2(N_OUT) : 1)-1:0] s_load_col,
  input  wire [K*($clog2(N_IN)+VB)-1:0]               s_load_slots,
  input  wire [SBITS-1:0]                             s_load_shift,
  input  wire                                         start,
  input  wire [N_IN*ABITS-1:0]                        x_in,
  output wire                                         busy,
  output wire                                         valid,
  // N_OUT*YTW, YTW = max(YW + SMAX + 1, SCW) + 1 (written out: no localparams in the port list)
  output wire [N_OUT*((($clog2(N_IN*((1<<WBITS)-1)*((1<<ABITS)-1)+1) +
                        ((((1<<SBITS)-1) < (VB-1)) ? ((1<<SBITS)-1) : (VB-1)) + 1) >
                       (VB + $clog2(K*((1<<ABITS)-1)+1))) ?
                      ($clog2(N_IN*((1<<WBITS)-1)*((1<<ABITS)-1)+1) +
                       ((((1<<SBITS)-1) < (VB-1)) ? ((1<<SBITS)-1) : (VB-1)) + 2) :
                      (VB + $clog2(K*((1<<ABITS)-1)+1) + 1))-1:0] y
);
  localparam JW   = (N_OUT > 1) ? $clog2(N_OUT) : 1;
  localparam YW   = $clog2(N_IN * ((1 << WBITS) - 1) * ((1 << ABITS) - 1) + 1);
  localparam SCW  = VB + $clog2(K * ((1 << ABITS) - 1) + 1);
  localparam SBW  = SBITS;
  localparam SMAX = (((1 << SBITS) - 1) < (VB - 1)) ? ((1 << SBITS) - 1) : (VB - 1);
  localparam YTW  = ((YW + SMAX + 1 > SCW) ? YW + SMAX + 1 : SCW) + 1;
  localparam CG  = (USE_LATCH == 0) ? CLK_GATE : 0;   // gating in the flip-flop build only

  wire                 st = start & ~w_load_en & ~s_load_en;
  wire                 d_busy, d_valid, s_busy, s_valid;
  wire [N_IN-1:0]      xbit;
  wire [N_OUT*YW-1:0]  yd;
  wire [N_OUT*SCW-1:0] ys;

  dcim_core #(.N_IN(N_IN), .N_OUT(N_OUT), .WBITS(WBITS), .ABITS(ABITS), .USE_LATCH(USE_LATCH),
              .CLK_GATE(CG)) u_dense (
    .clk(clk), .rst(rst), .load_en(w_load_en), .load_addr(w_load_addr), .load_row(w_load_row),
    .start(st), .x_in(x_in), .busy(d_busy), .valid(d_valid), .y(yd), .xbit(xbit));

  sidecar #(.N_IN(N_IN), .N_OUT(N_OUT), .ABITS(ABITS), .VB(VB), .K(K), .PARALLEL(PARALLEL),
            .CLK_GATE(CG)) u_side (
    .clk(clk), .rst(rst), .load_en(s_load_en), .load_col(s_load_col), .load_slots(s_load_slots),
    .start(st), .x_in(x_in), .xbit(xbit), .busy(s_busy), .valid(s_valid), .y(ys));

  wire cv = d_valid & s_valid;        // both cores DONE
  assign busy  = d_busy | s_busy;     // equal by construction

  // S per column, loaded with the sidecar column
  wire [N_OUT*SBW-1:0] sh;
  genvar c;
  generate
    for (c = 0; c < N_OUT; c = c + 1) begin : g_sh
      localparam [JW-1:0] CA = c;
      wire          ld = s_load_en && !s_busy && s_load_col == CA;
      reg [SBW-1:0] s_r;
      if (CG != 0) begin : g_cg
        wire gclk;                        // pulses on this column's load edge and on rst edges
        icg u_icg (.clk(clk), .en(ld | rst), .gclk(gclk));
        always @(posedge gclk)
          if (rst) s_r <= {SBW{1'b0}};
          else     s_r <= s_load_shift;
      end else begin : g_ff
        always @(posedge clk)
          if (rst) s_r <= {SBW{1'b0}};
          else if (ld) s_r <= s_load_shift;
      end
      assign sh[c*SBW +: SBW] = s_r;
    end
  endgenerate

  // merge: (dense << S) + sidecar, in YTW-bit two's complement
  reg [N_OUT*YTW-1:0] ym;
  reg [YTW-1:0]       dz, se;
  integer j;
  always @(*) begin
    for (j = 0; j < N_OUT; j = j + 1) begin
      dz = {YTW{1'b0}};
      dz[YW-1:0] = yd[j*YW +: YW];
      se = {{(YTW-SCW){ys[j*SCW + SCW-1]}}, ys[j*SCW +: SCW]};
      ym[j*YTW +: YTW] = (dz << sh[j*SBW +: SBW]) + se;
    end
  end

  // output: combinational (PIPE_MERGE=0) or one register stage after the merge (PIPE_MERGE=1)
  generate
    if (PIPE_MERGE != 0) begin : g_pipe
      reg [N_OUT*YTW-1:0] y_q;
      reg                 v_q;
      always @(posedge clk)
        if (rst) v_q <= 1'b0;
        else     v_q <= cv;
      if (CG != 0) begin : g_cg
        wire gclk;                        // pulses on result edges (cv) and on rst edges
        icg u_icg (.clk(clk), .en(cv | rst), .gclk(gclk));
        always @(posedge gclk)
          if (rst) y_q <= {(N_OUT*YTW){1'b0}};
          else     y_q <= ym;
      end else begin : g_ff
        always @(posedge clk)
          if (rst)     y_q <= {(N_OUT*YTW){1'b0}};
          else if (cv) y_q <= ym;
      end
      assign y     = y_q;
      assign valid = v_q;
    end else begin : g_comb
      assign y     = ym;
      assign valid = cv;
    end
  endgenerate
endmodule
