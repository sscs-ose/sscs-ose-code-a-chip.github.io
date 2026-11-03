// Design-iteration variant of kyber_ntt_engine for the SKY130 single-port
// configuration. It applies the three improvements identified by the
// measurements in the notebook, each behind a parameter so that their costs
// and benefits can be measured separately:
//
//   BARRETT_1C  use the single-subtraction Barrett reducer, whose equivalence
//               to a mod q is proven formally (formal/)
//   PIPE_MUL    register the 12x12 product before Barrett reduction, splitting
//               the critical path at the cost of one cycle per butterfly
//   COEFF_W     width of the coefficient store; 12 bits hold every value in
//               [0, q) because q = 3329 < 2^12
//
// The external interface is unchanged (16-bit data, one-cycle read latency),
// so the same testbench and golden vectors apply. With BARRETT_1C=0,
// PIPE_MUL=0 and COEFF_W=16 the behaviour is cycle-identical to the original
// engine compiled with TRUSTEDGE_ASIC_SRAM.
// SPDX-License-Identifier: Apache-2.0

module kyber_ntt_engine_opt #(
    parameter bit     BARRETT_1C = 1'b1,
    parameter bit     PIPE_MUL   = 1'b1,
    parameter integer COEFF_W    = 12
) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        start,
    input  wire        inverse,
    output reg         busy,
    output reg         done,
    input  wire [7:0]  waddr,
    input  wire [15:0] wdata,
    input  wire        we,
    output wire [15:0] rdata,
    input  wire [7:0]  raddr
);
    localparam [3:0] S_IDLE          = 4'd0,
                     S_FETCH         = 4'd1,
                     S_CAPTURE       = 4'd2,
                     S_CAPTURE_B     = 4'd3,
                     S_MUL           = 4'd4,
                     S_REDUCE        = 4'd5,
                     S_EXEC          = 4'd6,
                     S_WRITE         = 4'd7,
                     S_WRITE_B       = 4'd8,
                     S_SCALE_FETCH   = 4'd9,
                     S_SCALE_CAPTURE = 4'd10,
                     S_SCALE_MUL     = 4'd11,
                     S_SCALE_REDUCE  = 4'd12,
                     S_SCALE_EXEC    = 4'd13,
                     S_SCALE_WRITE   = 4'd14,
                     S_DONE          = 4'd15;

    reg [3:0]  st;
    reg        inverse_q;
    reg [8:0]  len, start_pos, j;
    reg [6:0]  k;
    reg [7:0]  scale_index;
    reg [11:0] coeff_a_q, coeff_b_q, zeta_q, scale_coeff_q;
    reg [11:0] result_lo_q, result_hi_q, scale_result_q;
    reg [11:0] mul_reduced_q;
    reg [23:0] product_q;

    // ---------------------------------------------------------- single-port store
    wire [7:0] pair_addr_b = j[7:0] + len[7:0];
    wire [7:0] ram_addr =
        (st == S_FETCH || st == S_WRITE)           ? j[7:0] :
        (st == S_CAPTURE || st == S_WRITE_B)       ? pair_addr_b :
        (st == S_SCALE_FETCH || st == S_SCALE_WRITE) ? scale_index :
        (we ? waddr : raddr);
    wire ram_we = (st == S_WRITE) || (st == S_WRITE_B) || (st == S_SCALE_WRITE) ||
                  ((st == S_IDLE) && we);
    wire [11:0] ram_wdata =
        (st == S_WRITE)       ? result_lo_q :
        (st == S_WRITE_B)     ? result_hi_q :
        (st == S_SCALE_WRITE) ? scale_result_q : wdata[11:0];
    // External writes keep all 16 bits, exactly as in the original engine;
    // with COEFF_W = 12 only the low 12 bits are stored, which is lossless for
    // canonical coefficients (< q < 2^12).
    wire [15:0] ram_wdata16 = ((st == S_IDLE) && we) ? wdata : {4'd0, ram_wdata};
    wire [COEFF_W-1:0] ram_q;

    te_sram_1rw_model #(.WIDTH(COEFF_W), .DEPTH(256), .ADDR_WIDTH(8)) u_coeff_ram (
        .clk(clk), .we(ram_we), .addr(ram_addr),
        .wdata(ram_wdata16[COEFF_W-1:0]), .rdata(ram_q));

    wire [11:0] ram_q12 = ram_q[11:0];
    assign rdata = {{(16-COEFF_W){1'b0}}, ram_q};

    // ---------------------------------------------------------------- arithmetic
    localparam [12:0] Q13 = 13'd3329;

    wire [15:0] zeta_k = kyber_pkg::kyber_zeta(k);

    wire [12:0] inv_sum_w  = {1'b0, coeff_a_q} + coeff_b_q;
    wire [11:0] inv_sum    = (inv_sum_w >= Q13) ? (inv_sum_w - Q13) : inv_sum_w[11:0];
    wire [12:0] inv_diff_w = {1'b0, coeff_b_q} + Q13 - coeff_a_q;
    wire [11:0] inv_diff   = (inv_diff_w >= Q13) ? (inv_diff_w - Q13) : inv_diff_w[11:0];

    wire        scaling  = (st == S_SCALE_MUL) || (st == S_SCALE_REDUCE);
    wire [11:0] mul_lhs  = scaling ? scale_coeff_q : (inverse_q ? inv_diff : coeff_b_q);
    wire [11:0] mul_rhs  = scaling ? 12'd3303 : zeta_q;
    wire [23:0] mul_product = mul_lhs * mul_rhs;
    wire [23:0] reduce_in   = PIPE_MUL ? product_q : mul_product;
    wire [11:0] mul_reduced;

    generate
        if (BARRETT_1C) begin : g_b1
            barrett_reduce_1c u_red (.a(reduce_in), .r(mul_reduced));
        end else begin : g_b3
            barrett_reduce    u_red (.a(reduce_in), .r(mul_reduced));
        end
    endgenerate

    wire [12:0] fwd_sum_w  = {1'b0, coeff_a_q} + mul_reduced_q;
    wire [11:0] fwd_sum    = (fwd_sum_w >= Q13) ? (fwd_sum_w - Q13) : fwd_sum_w[11:0];
    wire [12:0] fwd_diff_w = {1'b0, coeff_a_q} + Q13 - mul_reduced_q;
    wire [11:0] fwd_diff   = (fwd_diff_w >= Q13) ? (fwd_diff_w - Q13) : fwd_diff_w[11:0];

    // -------------------------------------------------------------------- control
    wire last_in_group = (j + 9'd1 >= start_pos + len);
    wire last_group    = (start_pos + (len << 1) >= 9'd256);

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            st <= S_IDLE; inverse_q <= 1'b0; busy <= 1'b0; done <= 1'b0;
            len <= 9'd128; start_pos <= 9'd0; j <= 9'd0; k <= 7'd1; scale_index <= 8'd0;
            coeff_a_q <= 12'd0; coeff_b_q <= 12'd0; zeta_q <= 12'd0; scale_coeff_q <= 12'd0;
            result_lo_q <= 12'd0; result_hi_q <= 12'd0; scale_result_q <= 12'd0;
            mul_reduced_q <= 12'd0; product_q <= 24'd0;
        end else begin
            done <= 1'b0;
            case (st)
                S_IDLE: begin
                    busy <= 1'b0;
                    if (start) begin
                        inverse_q <= inverse; busy <= 1'b1;
                        len <= inverse ? 9'd2 : 9'd128;
                        start_pos <= 9'd0; j <= 9'd0;
                        k <= inverse ? 7'd127 : 7'd1;
                        st <= S_FETCH;
                    end
                end
                S_FETCH:     st <= S_CAPTURE;
                S_CAPTURE:   begin coeff_a_q <= ram_q12; st <= S_CAPTURE_B; end
                S_CAPTURE_B: begin
                    coeff_b_q <= ram_q12;
                    zeta_q    <= zeta_k[11:0];
                    st <= PIPE_MUL ? S_MUL : S_REDUCE;
                end
                S_MUL:       begin product_q <= mul_product; st <= S_REDUCE; end
                S_REDUCE:    begin mul_reduced_q <= mul_reduced; st <= S_EXEC; end
                S_EXEC: begin
                    if (inverse_q) begin
                        result_lo_q <= inv_sum;  result_hi_q <= mul_reduced_q;
                    end else begin
                        result_lo_q <= fwd_sum;  result_hi_q <= fwd_diff;
                    end
                    st <= S_WRITE;
                end
                S_WRITE: st <= S_WRITE_B;
                S_WRITE_B: begin
                    if (last_in_group) begin
                        if (last_group) begin
                            if (!inverse_q && len == 9'd2) begin
                                st <= S_DONE;
                            end else if (inverse_q && len == 9'd128) begin
                                scale_index <= 8'd0; st <= S_SCALE_FETCH;
                            end else begin
                                len <= inverse_q ? (len << 1) : (len >> 1);
                                start_pos <= 9'd0; j <= 9'd0;
                                k <= inverse_q ? (k - 7'd1) : (k + 7'd1);
                                st <= S_FETCH;
                            end
                        end else begin
                            start_pos <= start_pos + (len << 1);
                            j <= start_pos + (len << 1);
                            k <= inverse_q ? (k - 7'd1) : (k + 7'd1);
                            st <= S_FETCH;
                        end
                    end else begin
                        j <= j + 9'd1; st <= S_FETCH;
                    end
                end
                S_SCALE_FETCH:   st <= S_SCALE_CAPTURE;
                S_SCALE_CAPTURE: begin
                    scale_coeff_q <= ram_q12;
                    st <= PIPE_MUL ? S_SCALE_MUL : S_SCALE_REDUCE;
                end
                S_SCALE_MUL:     begin product_q <= mul_product; st <= S_SCALE_REDUCE; end
                S_SCALE_REDUCE:  begin mul_reduced_q <= mul_reduced; st <= S_SCALE_EXEC; end
                S_SCALE_EXEC:    begin scale_result_q <= mul_reduced_q; st <= S_SCALE_WRITE; end
                S_SCALE_WRITE: begin
                    if (scale_index == 8'd255) st <= S_DONE;
                    else begin scale_index <= scale_index + 8'd1; st <= S_SCALE_FETCH; end
                end
                S_DONE: begin busy <= 1'b0; done <= 1'b1; st <= S_IDLE; end
                default: st <= S_IDLE;
            endcase
        end
    end
endmodule
