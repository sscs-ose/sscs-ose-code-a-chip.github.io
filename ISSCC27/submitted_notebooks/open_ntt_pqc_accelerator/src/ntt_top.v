// ---------------------------------------------------------------------------
// ntt_top : unified polynomial-multiplication engine (N1)
//
// One datapath (coeff_ram + twiddle_rom + one butterfly) performs every step of
// a lattice polynomial multiply, selected by `op`:
//
//   OP_NTT   (0): forward NTT on region A            (in place)
//   OP_NTTB  (1): forward NTT on region B            (in place)
//   OP_INTT  (2): inverse NTT on region A, incl. n^{-1} scaling
//   OP_PWM   (3): A[i] = A[i] * B[i]  (Montgomery)   point-wise product
//   OP_SCALE (4): A[i] = scale_const * A[i]          region A
//   OP_SCALEB(5): B[i] = scale_const * B[i]          region B
//
// Coefficient memory is 2N deep: region A = [0..N-1], region B = [N..2N-1].
// Multiply-only ops (PWM, SCALE) use the Cooley-Tukey butterfly with a_in = 0,
// so a_out = mod_mul(zeta, b_in). The inverse NTT uses the Gentleman-Sande
// butterfly (mode_gs = 1) with -zeta, then an internal pass scales region A by
// NINV_MONT (= n^{-1} in the Montgomery domain).
//
// A full multiply c = a*b is, in the Montgomery domain:
//   load a->A, b->B; SCALE A,B by R2 (to Montgomery); NTT A; NTT B; PWM;
//   INTT A; SCALE A by 1 (from Montgomery); read A.
//
// RAM/ROM addresses are combinational from the counters (a registered address
// reads one cycle late). Output of the forward NTT is in bit-reversed order,
// matching the golden model.
// ---------------------------------------------------------------------------
module ntt_top #(
    parameter integer WIDTH  = 24,
    parameter integer N      = 256,
    parameter integer LOGN   = 8,
    parameter integer AW     = 9,               // address width for 2N memory
    parameter [WIDTH-1:0] Q      = 24'd8380417,
    parameter [31:0]      QPRIME = 32'd4236238847,
    parameter [WIDTH-1:0] NINV_MONT = 24'd16382 // n^{-1} in Montgomery domain
) (
    input  wire             clk,
    input  wire             rst_n,
    input  wire             start,
    input  wire [2:0]       op,
    input  wire [WIDTH-1:0] scale_const,
    output reg              busy,
    output reg              done,
    output reg  [31:0]      cycles,
    // host coefficient access (valid only when !busy)
    input  wire             cmd_we,
    input  wire [AW-1:0]    cmd_addr,
    input  wire [WIDTH-1:0] cmd_wdata,
    output wire [WIDTH-1:0] cmd_rdata
);
    localparam [2:0] OP_NTT = 3'd0, OP_NTTB = 3'd1, OP_INTT = 3'd2,
                     OP_PWM = 3'd3, OP_SCALE = 3'd4, OP_SCALEB = 3'd5;

    // ---- latched op for the running transform ----
    reg [2:0] cur_op;
    reg       scale_phase;          // INTT's trailing n^{-1} scaling pass

    wire is_intt   = (cur_op == OP_INTT) && !scale_phase;
    wire is_ntt    = (cur_op == OP_NTT) || (cur_op == OP_NTTB);
    wire is_nested = (is_ntt || is_intt);
    wire is_pwm    = (cur_op == OP_PWM);
    wire is_flat   = !is_nested;    // PWM, SCALE, SCALEB, or INTT scale pass

    wire [AW-1:0] off_ntt   = (cur_op == OP_NTTB)  ? N[AW-1:0] : {AW{1'b0}};
    wire [AW-1:0] off_scale = (cur_op == OP_SCALEB) ? N[AW-1:0] : {AW{1'b0}};

    // ---- counters ----
    reg [3:0]    stage;             // transform stage (0..LOGN-1)
    reg [AW-1:0] group;
    reg [AW-1:0] jj;
    reg [8:0]    k;                 // twiddle index (1..N-1)
    reg [AW-1:0] idx;               // flat element index (0..N-1)

    // nested loop geometry (forward vs inverse)
    wire [AW-1:0] len = is_intt ? (9'd1 << stage) : (9'd128 >> stage);
    wire [4:0]    sh  = is_intt ? (stage + 1'b1)  : (LOGN[4:0] - stage);
    wire [AW-1:0] nbase = (group << sh);
    wire [AW-1:0] nj    = nbase + jj;
    wire [AW-1:0] njl   = nj + len;
    wire [AW-1:0] groups_m1 = is_intt ? (((9'd128 >> stage)) - 1'b1)
                                      : (((9'd1   << stage)) - 1'b1);
    wire last_jj    = (jj == len - 1'b1);
    wire last_group = (group == groups_m1);
    wire last_stage = (stage == LOGN[3:0] - 1'b1);
    wire last_flat  = (idx == N[AW-1:0] - 1'b1);

    // ---- FSM ----
    localparam S_IDLE = 3'd0, S_RD = 3'd1, S_CAP = 3'd2,
               S_WAIT = 3'd3, S_WR = 3'd4, S_FIN = 3'd5;
    reg [2:0] state;

    // ---- butterfly ----
    reg              bf_in_valid, bf_mode_gs;
    reg  [WIDTH-1:0] bf_a_in, bf_b_in, bf_zeta;
    wire [WIDTH-1:0] bf_a_out, bf_b_out;
    wire             bf_out_valid;
    butterfly #(.WIDTH(WIDTH), .Q(Q), .QPRIME(QPRIME)) u_bf (
        .clk(clk), .rst_n(rst_n), .in_valid(bf_in_valid), .mode_gs(bf_mode_gs),
        .a_in(bf_a_in), .b_in(bf_b_in), .zeta(bf_zeta),
        .a_out(bf_a_out), .b_out(bf_b_out), .out_valid(bf_out_valid)
    );

    // ---- combinational addressing ----
    // Port A / B addresses for the current element or butterfly.
    wire [AW-1:0] flat_a = is_pwm ? idx :                       // PWM: A[idx]
                           (scale_phase ? idx : (off_scale + idx)); // scale
    wire [AW-1:0] flat_b = N[AW-1:0] + idx;                     // PWM: B[idx]

    wire [AW-1:0] nest_a = off_ntt + nj;
    wire [AW-1:0] nest_b = off_ntt + njl;

    wire [AW-1:0] eng_a_addr = is_flat ? flat_a : nest_a;
    wire [AW-1:0] eng_b_addr = is_flat ? flat_b : nest_b;

    wire eng_wr   = busy && (state == S_WR);
    wire eng_a_we = eng_wr;
    wire eng_b_we = eng_wr && is_nested;   // only nested writes both ports

    wire            a_we    = busy ? eng_a_we   : cmd_we;
    wire [AW-1:0]   a_addr  = busy ? eng_a_addr : cmd_addr;
    wire [WIDTH-1:0] a_wdata = busy ? bf_a_out   : cmd_wdata;
    wire            b_we    = eng_b_we;
    wire [AW-1:0]   b_addr  = eng_b_addr;
    wire [WIDTH-1:0] b_wdata = bf_b_out;
    wire [WIDTH-1:0] ram_a_rdata, ram_b_rdata;

    assign cmd_rdata = ram_a_rdata;

    coeff_ram #(.WIDTH(WIDTH), .DEPTH(2*N), .AW(AW)) u_ram (
        .clk(clk),
        .a_we(a_we), .a_addr(a_addr), .a_wdata(a_wdata), .a_rdata(ram_a_rdata),
        .b_we(b_we), .b_addr(b_addr), .b_wdata(b_wdata), .b_rdata(ram_b_rdata)
    );

    wire [7:0]       rom_addr = k[7:0];
    wire [WIDTH-1:0] rom_rdata;
    twiddle_rom #(.WIDTH(WIDTH), .DEPTH(N), .AW(8)) u_rom (
        .clk(clk), .addr(rom_addr), .rdata(rom_rdata)
    );

    // ---- sequencer ----
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= S_IDLE; busy <= 1'b0; done <= 1'b0; cycles <= 32'd0;
            stage <= 4'd0; group <= {AW{1'b0}}; jj <= {AW{1'b0}};
            k <= 9'd0; idx <= {AW{1'b0}}; scale_phase <= 1'b0;
            bf_in_valid <= 1'b0; bf_mode_gs <= 1'b0; cur_op <= 3'd0;
        end else begin
            bf_in_valid <= 1'b0;
            case (state)
                S_IDLE: begin
                    if (start) begin
                        done   <= 1'b0;
                        busy   <= 1'b1;
                        cycles <= 32'd0;
                        cur_op <= op;
                        scale_phase <= 1'b0;
                        stage  <= 4'd0;
                        group  <= {AW{1'b0}};
                        jj     <= {AW{1'b0}};
                        idx    <= {AW{1'b0}};
                        k      <= (op == OP_INTT) ? 9'd255 : 9'd1;
                        state  <= S_RD;
                    end
                end
                S_RD: begin
                    cycles <= cycles + 1'b1;
                    state  <= S_CAP;
                end
                S_CAP: begin
                    cycles      <= cycles + 1'b1;
                    bf_in_valid <= 1'b1;
                    if (is_nested) begin
                        bf_a_in   <= ram_a_rdata;
                        bf_b_in   <= ram_b_rdata;
                        bf_zeta   <= is_intt ? (Q - rom_rdata) : rom_rdata;
                        bf_mode_gs<= is_intt;
                    end else if (is_pwm) begin
                        bf_a_in   <= {WIDTH{1'b0}};
                        bf_b_in   <= ram_b_rdata;      // B[idx]
                        bf_zeta   <= ram_a_rdata;      // A[idx]
                        bf_mode_gs<= 1'b0;
                    end else begin                     // SCALE / INTT scale pass
                        bf_a_in   <= {WIDTH{1'b0}};
                        bf_b_in   <= ram_a_rdata;      // A[idx]
                        bf_zeta   <= scale_phase ? NINV_MONT : scale_const;
                        bf_mode_gs<= 1'b0;
                    end
                    state <= S_WAIT;
                end
                S_WAIT: begin
                    cycles <= cycles + 1'b1;
                    if (bf_out_valid)
                        state <= S_WR;
                end
                S_WR: begin
                    cycles <= cycles + 1'b1;
                    if (is_nested) begin
                        if (!last_jj) begin
                            jj <= jj + 1'b1; state <= S_RD;
                        end else begin
                            jj <= {AW{1'b0}};
                            k  <= is_intt ? (k - 1'b1) : (k + 1'b1);
                            if (!last_group) begin
                                group <= group + 1'b1; state <= S_RD;
                            end else begin
                                group <= {AW{1'b0}};
                                if (!last_stage) begin
                                    stage <= stage + 1'b1; state <= S_RD;
                                end else if (cur_op == OP_INTT) begin
                                    // start the n^{-1} scaling pass on region A
                                    scale_phase <= 1'b1;
                                    idx <= {AW{1'b0}};
                                    state <= S_RD;
                                end else begin
                                    state <= S_FIN;
                                end
                            end
                        end
                    end else begin  // flat op
                        if (!last_flat) begin
                            idx <= idx + 1'b1; state <= S_RD;
                        end else begin
                            state <= S_FIN;
                        end
                    end
                end
                S_FIN: begin
                    busy <= 1'b0; done <= 1'b1; state <= S_IDLE;
                end
                default: state <= S_IDLE;
            endcase
        end
    end
endmodule
