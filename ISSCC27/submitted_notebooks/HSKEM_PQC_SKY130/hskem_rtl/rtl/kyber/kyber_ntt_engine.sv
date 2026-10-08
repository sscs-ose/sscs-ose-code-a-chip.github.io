import kyber_pkg::*;

// Shared, area-conscious FIPS 203 NTT/NTT^-1 engine.
//
// The coefficient store is a synchronous true-dual-port RAM so Quartus can
// map the 256x16 array into one M20K instead of thousands of ALMs.  Arithmetic
// remains canonical in [0,q), uses one shared Barrett multiplier/reducer, and
// processes one butterfly at a time.  External reads have one clock of RAM
// latency; clients issue the next read address while consuming the current
// result.
module kyber_ntt_engine (
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
                     S_REDUCE        = 4'd3,
                     S_EXEC          = 4'd4,
                     S_WRITE         = 4'd5,
                     S_SCALE_FETCH   = 4'd6,
                     S_SCALE_CAPTURE = 4'd7,
                     S_SCALE_REDUCE  = 4'd8,
                     S_SCALE_EXEC    = 4'd9,
                     S_SCALE_WRITE   = 4'd10,
                     S_DONE          = 4'd11,
                     S_CAPTURE_B     = 4'd12,
                     S_WRITE_B       = 4'd13;

    reg [3:0] st;
    reg inverse_q;
    reg [8:0] len;
    reg [8:0] start_pos;
    reg [8:0] j;
    reg [6:0] k;
    reg [7:0] scale_index;
    reg [15:0] coeff_a_q;
    reg [15:0] coeff_b_q;
    reg [15:0] zeta_q;
    reg [15:0] result_lo_q;
    reg [15:0] result_hi_q;
    reg [15:0] scale_coeff_q;
    reg [11:0] mul_reduced_q;
    reg [15:0] scale_result_q;

    // One 4096-bit M20K is sufficient for all 256 coefficients.  Do not add
    // asynchronous reads here: that would force this memory back into ALMs.
    // There is no algorithmic same-address read/write: butterfly writes use
    // distinct addresses and read outputs are ignored during writes.  Tell
    // Quartus not to synthesize bypass logic for an unspecified collision.
`ifdef TRUSTEDGE_ASIC_SRAM
    wire [15:0] ram_q_a;
`else
    (* ramstyle = "M20K, no_rw_check" *) reg [15:0] coeff_ram [0:255];
    reg [15:0] ram_q_a;
    reg [15:0] ram_q_b;
`endif

    wire [7:0] pair_addr_a = j[7:0];
    wire [8:0] pair_addr_b_wide = j + len;
    wire [7:0] pair_addr_b = pair_addr_b_wide[7:0];

    wire [7:0] ram_addr_a =
        (st == S_FETCH || st == S_WRITE) ? pair_addr_a :
        (st == S_SCALE_FETCH || st == S_SCALE_WRITE) ? scale_index :
        (we ? waddr : raddr);
    wire [7:0] ram_addr_b =
        (st == S_FETCH || st == S_WRITE) ? pair_addr_b : 8'd0;
    wire ram_we_a = (st == S_WRITE) || (st == S_SCALE_WRITE) ||
                    ((st == S_IDLE) && we);
    wire ram_we_b = (st == S_WRITE);
    wire [15:0] ram_wdata_a =
        (st == S_WRITE) ? result_lo_q :
        (st == S_SCALE_WRITE) ? scale_result_q : wdata;
    wire [15:0] ram_wdata_b = result_hi_q;

`ifdef TRUSTEDGE_ASIC_SRAM
    // The qualified SKY130 path is single-port. Serialize the two butterfly
    // reads and writes in the ASIC-only FSM while the FPGA branch retains its
    // true-dual-port M20K implementation and timing.
    wire [7:0] ram_single_addr =
        (st == S_FETCH || st == S_WRITE) ? pair_addr_a :
        (st == S_CAPTURE || st == S_WRITE_B) ? pair_addr_b :
        (st == S_SCALE_FETCH || st == S_SCALE_WRITE) ? scale_index :
        (we ? waddr : raddr);
    wire ram_single_we = (st == S_WRITE) || (st == S_WRITE_B) ||
                         (st == S_SCALE_WRITE) ||
                         ((st == S_IDLE) && we);
    wire [15:0] ram_single_wdata =
        (st == S_WRITE) ? result_lo_q :
        (st == S_WRITE_B) ? result_hi_q :
        (st == S_SCALE_WRITE) ? scale_result_q : wdata;

    te_sram_1rw #(
        .WIDTH(16),
        .DEPTH(256),
        .ADDR_WIDTH(8)
    ) u_coeff_ram (
        .clk(clk),
        .we(ram_single_we),
        .addr(ram_single_addr),
        .wdata(ram_single_wdata),
        .rdata(ram_q_a)
    );
`else
    // Keep the ports in separate clocked processes.  This is the Quartus
    // true-dual-port inference template; combining both writes in one process
    // makes the 4-Kbit store fall back to thousands of ALMs.
    always @(posedge clk) begin
        if (ram_we_a)
            coeff_ram[ram_addr_a] <= ram_wdata_a;
        ram_q_a <= coeff_ram[ram_addr_a];
    end

    always @(posedge clk) begin
        if (ram_we_b)
            coeff_ram[ram_addr_b] <= ram_wdata_b;
        ram_q_b <= coeff_ram[ram_addr_b];
    end
`endif

    assign rdata = ram_q_a;

    localparam [12:0] Q13 = 13'd3329;

    wire [11:0] coeff_a = coeff_a_q[11:0];
    wire [11:0] coeff_b = coeff_b_q[11:0];
    wire [12:0] inverse_sum_wide = {1'b0, coeff_a} + coeff_b;
    wire [12:0] inverse_sum_reduced_wide = inverse_sum_wide - Q13;
    wire [11:0] inverse_sum =
        (inverse_sum_wide >= Q13) ?
        inverse_sum_reduced_wide[11:0] : inverse_sum_wide[11:0];
    wire [12:0] inverse_diff_wide =
        {1'b0, coeff_b} + Q13 - coeff_a;
    wire [12:0] inverse_diff_reduced_wide = inverse_diff_wide - Q13;
    wire [11:0] inverse_diff =
        (inverse_diff_wide >= Q13) ?
        inverse_diff_reduced_wide[11:0] : inverse_diff_wide[11:0];

    wire scale_active = (st == S_SCALE_REDUCE);
    wire [11:0] mul_lhs = scale_active ? scale_coeff_q[11:0] :
                           (inverse_q ? inverse_diff : coeff_b);
    wire [11:0] mul_rhs = scale_active ? 12'd3303 : zeta_q[11:0];
    wire [23:0] mul_product = mul_lhs * mul_rhs;
    wire [11:0] mul_reduced;

    barrett_reduce u_mul_reduce (
        .a(mul_product),
        .r(mul_reduced)
    );

    wire [12:0] forward_sum_wide = {1'b0, coeff_a} + mul_reduced_q;
    wire [12:0] forward_sum_reduced_wide = forward_sum_wide - Q13;
    wire [11:0] forward_sum =
        (forward_sum_wide >= Q13) ?
        forward_sum_reduced_wide[11:0] : forward_sum_wide[11:0];
    wire [12:0] forward_diff_wide =
        {1'b0, coeff_a} + Q13 - mul_reduced_q;
    wire [12:0] forward_diff_reduced_wide = forward_diff_wide - Q13;
    wire [11:0] forward_diff =
        (forward_diff_wide >= Q13) ?
        forward_diff_reduced_wide[11:0] : forward_diff_wide[11:0];

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            st <= S_IDLE;
            inverse_q <= 1'b0;
            busy <= 1'b0;
            done <= 1'b0;
            len <= 9'd128;
            start_pos <= 9'd0;
            j <= 9'd0;
            k <= 7'd1;
            scale_index <= 8'd0;
            coeff_a_q <= 16'd0;
            coeff_b_q <= 16'd0;
            zeta_q <= 16'd0;
            result_lo_q <= 16'd0;
            result_hi_q <= 16'd0;
            scale_coeff_q <= 16'd0;
            mul_reduced_q <= 12'd0;
            scale_result_q <= 16'd0;
        end else begin
            done <= 1'b0;
            case (st)
                S_IDLE: begin
                    busy <= 1'b0;
                    if (start) begin
                        inverse_q <= inverse;
                        busy <= 1'b1;
                        len <= inverse ? 9'd2 : 9'd128;
                        start_pos <= 9'd0;
                        j <= 9'd0;
                        k <= inverse ? 7'd127 : 7'd1;
                        st <= S_FETCH;
                    end
                end

                // FPGA: FETCH presents both addresses and CAPTURE consumes
                // both outputs. ASIC: FETCH/CAPTURE serialize A then B.
                S_FETCH: st <= S_CAPTURE;

                S_CAPTURE: begin
                    coeff_a_q <= ram_q_a;
`ifdef TRUSTEDGE_ASIC_SRAM
                    st <= S_CAPTURE_B;
`else
                    coeff_b_q <= ram_q_b;
                    zeta_q <= kyber_zeta(k);
                    st <= S_REDUCE;
`endif
                end

`ifdef TRUSTEDGE_ASIC_SRAM
                S_CAPTURE_B: begin
                    coeff_b_q <= ram_q_a;
                    zeta_q <= kyber_zeta(k);
                    st <= S_REDUCE;
                end
`endif

                // Register the long multiplier/Barrett path before the final
                // butterfly add/subtract.  This trades one clock per
                // butterfly for substantially safer 50-MHz timing.
                S_REDUCE: begin
                    mul_reduced_q <= mul_reduced;
                    st <= S_EXEC;
                end

                S_EXEC: begin
                    if (inverse_q) begin
                        result_lo_q <= {4'd0, inverse_sum};
                        result_hi_q <= {4'd0, mul_reduced_q};
                    end else begin
                        result_lo_q <= {4'd0, forward_sum};
                        result_hi_q <= {4'd0, forward_diff};
                    end
                    st <= S_WRITE;
                end

                S_WRITE: begin
`ifdef TRUSTEDGE_ASIC_SRAM
                    st <= S_WRITE_B;
`else
                    if (j + 9'd1 >= start_pos + len) begin
                        if (start_pos + (len << 1) >= 9'd256) begin
                            if ((!inverse_q && len == 9'd2)) begin
                                st <= S_DONE;
                            end else if (inverse_q && len == 9'd128) begin
                                scale_index <= 8'd0;
                                st <= S_SCALE_FETCH;
                            end else begin
                                len <= inverse_q ? (len << 1) : (len >> 1);
                                start_pos <= 9'd0;
                                j <= 9'd0;
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
                        j <= j + 9'd1;
                        st <= S_FETCH;
                    end
`endif
                end

`ifdef TRUSTEDGE_ASIC_SRAM
                S_WRITE_B: begin
                    if (j + 9'd1 >= start_pos + len) begin
                        if (start_pos + (len << 1) >= 9'd256) begin
                            if ((!inverse_q && len == 9'd2)) begin
                                st <= S_DONE;
                            end else if (inverse_q && len == 9'd128) begin
                                scale_index <= 8'd0;
                                st <= S_SCALE_FETCH;
                            end else begin
                                len <= inverse_q ? (len << 1) : (len >> 1);
                                start_pos <= 9'd0;
                                j <= 9'd0;
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
                        j <= j + 9'd1;
                        st <= S_FETCH;
                    end
                end
`endif

                S_SCALE_FETCH: st <= S_SCALE_CAPTURE;

                S_SCALE_CAPTURE: begin
                    scale_coeff_q <= ram_q_a;
                    st <= S_SCALE_REDUCE;
                end

                S_SCALE_REDUCE: begin
                    mul_reduced_q <= mul_reduced;
                    st <= S_SCALE_EXEC;
                end

                S_SCALE_EXEC: begin
                    scale_result_q <= {4'd0, mul_reduced_q};
                    st <= S_SCALE_WRITE;
                end

                S_SCALE_WRITE: begin
                    if (scale_index == 8'd255)
                        st <= S_DONE;
                    else begin
                        scale_index <= scale_index + 8'd1;
                        st <= S_SCALE_FETCH;
                    end
                end

                S_DONE: begin
                    busy <= 1'b0;
                    done <= 1'b1;
                    st <= S_IDLE;
                end

                default: st <= S_IDLE;
            endcase
        end
    end
endmodule
