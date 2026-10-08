// Sequential FIPS 203 Algorithms 11/12 matrix-vector self-test.
//
// Four SampleNTT polynomials are loaded into two interleaved 512x12 RAM banks.
// Consecutive parser coefficients can therefore be written together while
// each physical bank still has only one write port and one read port.
// The engine consumes four SHAKE256 PRF_eta1 streams derived by G(d || k) and
// nonces 0..3, applies CBD eta1=3 and the shared NTT to s[0..1] and e[0..1],
// stores s_hat/e_hat in parity-banked M20Ks, then evaluates
// A_hat * s_hat + e_hat for k=2 with one multiplier and one reducer.
// The source KAT supplies G(d||k)-derived seeds. The final t_hat and s_hat
// vectors are ByteEncode_12 serialized into internal RAMs in canonical
// ekPKE/dkPKE order. Only fingerprints leave this block; full K-PKE
// Encrypt/Decrypt and a host key-export API remain outside this stage.
import kyber_pkg::*;

module mlkem512_matrix_mac_selftest #(
    parameter [31:0] EXPECTED_DIGEST = 32'hE74D5420,
    parameter [31:0] EXPECTED_SECRET_DIGEST = 32'h30FFBF02,
    parameter [31:0] EXPECTED_ERROR_DIGEST = 32'hEE78DD78,
    parameter [31:0] EXPECTED_EKPKE_DIGEST = 32'h00000000,
    parameter [31:0] EXPECTED_DKPKE_DIGEST = 32'h00000000,
    parameter USE_EXTERNAL_NTT = 1'b0
) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        load_clear,
    input  wire        load0_valid,
    input  wire [9:0]  load0_addr,
    input  wire [11:0] load0_data,
    input  wire        load1_valid,
    input  wire [9:0]  load1_addr,
    input  wire [11:0] load1_data,
    input  wire        noise_load_valid,
    input  wire [9:0]  noise_load_addr,
    input  wire [7:0]  noise_load_data,
    input  wire        rho_load_valid,
    input  wire [4:0]  rho_load_addr,
    input  wire [7:0]  rho_load_data,
    input  wire        check_expected,
    input  wire        start,
    output reg         busy,
    output reg         done,
    output reg         pass,
    output reg [31:0]  digest,
    output reg [31:0]  secret_digest,
    output reg [31:0]  error_digest,
    output reg [31:0]  ekpke_digest,
    output reg [31:0]  dkpke_digest,
    output reg [15:0]  cycles,
    output reg [10:0]  loaded_coeffs,
    output wire        ntt_ext_start,
    output wire        ntt_ext_we,
    output wire [7:0]  ntt_ext_addr,
    output wire [15:0] ntt_ext_wdata,
    input  wire        ntt_ext_busy,
    input  wire        ntt_ext_done,
    input  wire [15:0] ntt_ext_rdata,
    // Internal-only runtime Encrypt readback. These ports never reach SPI.
    // The pair address is {row, column, coefficient_pair}; each bank returns
    // one coefficient, so normal Encrypt reads consume both banks together.
    input  wire [8:0]  matrix_ext_pair_addr,
    output reg [11:0]  matrix_ext_even_data,
    output reg [11:0]  matrix_ext_odd_data,
    input  wire [7:0]  ekpke_ext_pair_addr,
    output reg [23:0]  ekpke_ext_pair_data,
    input  wire [7:0]  dkpke_ext_pair_addr,
    output reg [23:0]  dkpke_ext_pair_data,
    input  wire [4:0]  rho_ext_addr,
    output reg [7:0]   rho_ext_data
);
    localparam [5:0] S_IDLE = 6'd0,
                     S_NOISE_ADDR0 = 6'd1,
                     S_NOISE_WAIT0 = 6'd2,
                     S_NOISE_CAP0 = 6'd3,
                     S_NOISE_WAIT1 = 6'd4,
                     S_NOISE_CAP1 = 6'd5,
                     S_NOISE_WAIT2 = 6'd6,
                     S_NOISE_CAP2 = 6'd7,
                     S_NOISE_WRITE = 6'd8,
                     S_NOISE_START = 6'd9,
                     S_NOISE_NTT_WAIT = 6'd10,
                     S_NOISE_PRIME = 6'd11,
                     S_NOISE_READ = 6'd12,
                     S_NOISE_NEXT = 6'd13,
                     S_FETCH0 = 6'd14,
                     S_WAIT0 = 6'd15,
                     S_CAPTURE0 = 6'd16,
                     S_WAIT1 = 6'd17,
                     S_CAPTURE1 = 6'd18,
                     S_MUL0 = 6'd19,
                     S_MUL1 = 6'd20,
                     S_MUL2 = 6'd21,
                     S_MUL3 = 6'd22,
                     S_MUL4 = 6'd23,
                     S_ACCUMULATE = 6'd24,
                     S_DONE = 6'd25,
                     S_DK_ADDR = 6'd26,
                     S_DK_WAIT = 6'd27,
                     S_DK_CAPTURE = 6'd28,
                     S_RHO_HASH = 6'd29,
                     S_EK_READ_ADDR = 6'd30,
                     S_EK_READ_WAIT = 6'd31,
                     S_EK_HASH = 6'd32,
                     S_DK_READ_ADDR = 6'd33,
                     S_DK_READ_WAIT = 6'd34,
                     S_DK_HASH = 6'd35;

    localparam [31:0] DIGEST_INIT = 32'h4D414331;
    localparam [12:0] Q13 = 13'd3329;

`ifdef TRUSTEDGE_ASIC_SRAM
    wire [11:0] ram_even_q;
    wire [11:0] ram_odd_q;
    wire [11:0] secret_even_q;
    wire [11:0] secret_odd_q;
    wire [11:0] error_even_q;
    wire [11:0] error_odd_q;
    wire [7:0] noise_byte_q;
    wire [23:0] ekpke_pair_q;
    wire [23:0] dkpke_pair_q;
`else
    (* ramstyle = "M20K, no_rw_check" *) reg [11:0] matrix_even_ram [0:511];
    (* ramstyle = "M20K, no_rw_check" *) reg [11:0] matrix_odd_ram [0:511];
    (* ramstyle = "M20K, no_rw_check" *) reg [11:0] secret_even_ram [0:255];
    (* ramstyle = "M20K, no_rw_check" *) reg [11:0] secret_odd_ram [0:255];
    (* ramstyle = "M20K, no_rw_check" *) reg [11:0] error_even_ram [0:255];
    (* ramstyle = "M20K, no_rw_check" *) reg [11:0] error_odd_ram [0:255];
    (* ramstyle = "M20K, no_rw_check" *) reg [7:0] noise_byte_ram [0:767];
    (* ramstyle = "M20K, no_rw_check" *) reg [23:0] ekpke_pair_ram [0:255];
    (* ramstyle = "M20K, no_rw_check" *) reg [23:0] dkpke_pair_ram [0:255];
    reg [11:0] ram_even_q;
    reg [11:0] ram_odd_q;
    reg [11:0] secret_even_q;
    reg [11:0] secret_odd_q;
    reg [11:0] error_even_q;
    reg [11:0] error_odd_q;
    reg [7:0] noise_byte_q;
    reg [23:0] ekpke_pair_q;
    reg [23:0] dkpke_pair_q;
`endif
    reg [7:0] rho_ram [0:31];
    reg [9:0] noise_read_addr;
    reg [9:0] noise_loaded_bytes;
    reg [9:0] read_addr;

    reg [5:0] state;
    reg row_index;
    reg column_index;
    reg [6:0] pair_index;
    reg [11:0] a0_q;
    reg [11:0] a1_q;
    reg [11:0] p0_q;
    reg [11:0] p1_q;
    reg [11:0] p2_q;
    reg [11:0] p3_q;
    reg [11:0] p4_q;
    reg [11:0] accum0_q;
    reg [11:0] accum1_q;
    reg [11:0] secret_b0_q;
    reg [11:0] secret_b1_q;
    reg [1:0]  noise_poly;
    reg [5:0]  noise_word_index;
    reg [1:0]  noise_lane;
    reg [7:0]  noise_byte0_q;
    reg [7:0]  noise_byte1_q;
    reg [7:0]  noise_byte2_q;
    reg [7:0]  noise_index;
    reg [10:0] noise_loaded_coeffs;
    reg [5:0] rho_loaded_bytes;
    reg [4:0] rho_index;
    reg core_ok;
    reg [7:0] serial_pair_index;
    wire [15:0] ntt_rdata;

    wire even_write_valid = (load0_valid && !load0_addr[0]) ||
                            (load1_valid && !load1_addr[0]);
    wire [8:0] even_write_addr = (load0_valid && !load0_addr[0]) ?
                                 load0_addr[9:1] : load1_addr[9:1];
    wire [11:0] even_write_data = (load0_valid && !load0_addr[0]) ?
                                  load0_data : load1_data;
    wire odd_write_valid = (load0_valid && load0_addr[0]) ||
                           (load1_valid && load1_addr[0]);
    wire [8:0] odd_write_addr = (load0_valid && load0_addr[0]) ?
                                load0_addr[9:1] : load1_addr[9:1];
    wire [11:0] odd_write_data = (load0_valid && load0_addr[0]) ?
                                 load0_data : load1_data;
    wire noise_ntt_write_valid = (state == S_NOISE_READ);
    wire [7:0] noise_write_addr = {noise_poly[0], noise_index[7:1]};
    wire [7:0] secret_read_addr = {column_index, pair_index};
    wire [7:0] error_read_addr = {row_index, pair_index};
    wire [23:0] result_pair_bytes;
    wire [23:0] secret_pair_bytes;

`ifndef TRUSTEDGE_ASIC_SRAM
    // One write plus one synchronous read per bank is directly inferable as
    // simple-dual-port M20K RAM.  When both parser outputs are valid their
    // consecutive addresses necessarily target different banks.
    always @(posedge clk) begin
        if (even_write_valid)
            matrix_even_ram[even_write_addr] <= even_write_data;
        if (busy)
            ram_even_q <= matrix_even_ram[read_addr[9:1]];
        else
            matrix_ext_even_data <= matrix_even_ram[matrix_ext_pair_addr];
    end

    // One polynomial is loaded/read at a time, so parity banking provides the
    // two coefficients needed by each basemul without duplicating the NTT.
    always @(posedge clk) begin
        if (noise_ntt_write_valid && !noise_poly[1] && !noise_index[0])
            secret_even_ram[noise_write_addr] <= ntt_rdata[11:0];
        if (state >= S_FETCH0)
            secret_even_q <= secret_even_ram[secret_read_addr];
    end

    always @(posedge clk) begin
        if (noise_ntt_write_valid && !noise_poly[1] && noise_index[0])
            secret_odd_ram[noise_write_addr] <= ntt_rdata[11:0];
        if (state >= S_FETCH0)
            secret_odd_q <= secret_odd_ram[secret_read_addr];
    end

    always @(posedge clk) begin
        if (noise_ntt_write_valid && noise_poly[1] && !noise_index[0])
            error_even_ram[noise_write_addr] <= ntt_rdata[11:0];
        if (state >= S_FETCH0)
            error_even_q <= error_even_ram[error_read_addr];
    end

    always @(posedge clk) begin
        if (noise_ntt_write_valid && noise_poly[1] && noise_index[0])
            error_odd_ram[noise_write_addr] <= ntt_rdata[11:0];
        if (state >= S_FETCH0)
            error_odd_q <= error_odd_ram[error_read_addr];
    end

    always @(posedge clk) begin
        if (noise_load_valid)
            noise_byte_ram[noise_load_addr] <= noise_load_data;
        if (busy)
            noise_byte_q <= noise_byte_ram[noise_read_addr];
    end

    always @(posedge clk) begin
        if (odd_write_valid)
            matrix_odd_ram[odd_write_addr] <= odd_write_data;
        if (busy)
            ram_odd_q <= matrix_odd_ram[read_addr[9:1]];
        else
            matrix_ext_odd_data <= matrix_odd_ram[matrix_ext_pair_addr];
    end

    // Fingerprints are deliberately computed from synchronous RAM readback,
    // not from the write data. This both checks canonical storage order and
    // prevents synthesis from optimizing the serialized key RAMs away.
    always @(posedge clk) begin
        if (busy) begin
            ekpke_pair_q <= ekpke_pair_ram[serial_pair_index];
            dkpke_pair_q <= dkpke_pair_ram[serial_pair_index];
        end else begin
            ekpke_ext_pair_data <= ekpke_pair_ram[ekpke_ext_pair_addr];
            dkpke_ext_pair_data <= dkpke_pair_ram[dkpke_ext_pair_addr];
            rho_ext_data <= rho_ram[rho_ext_addr];
        end
    end
`else
    // The loader, NTT writeback, MAC and serialized readback occupy disjoint
    // phases.  Each bank can therefore use one 1RW port with write priority;
    // read data returned during a write is never consumed.
    wire matrix_even_we = even_write_valid && !busy;
    wire matrix_odd_we = odd_write_valid && !busy;
    wire secret_even_we = noise_ntt_write_valid && !noise_poly[1] &&
                          !noise_index[0];
    wire secret_odd_we = noise_ntt_write_valid && !noise_poly[1] &&
                         noise_index[0];
    wire error_even_we = noise_ntt_write_valid && noise_poly[1] &&
                         !noise_index[0];
    wire error_odd_we = noise_ntt_write_valid && noise_poly[1] &&
                        noise_index[0];
    wire noise_byte_we = noise_load_valid && !busy;
    wire ekpke_pair_we = (state == S_ACCUMULATE) && column_index;
    wire dkpke_pair_we = (state == S_DK_CAPTURE);

    wire [8:0] matrix_even_addr = matrix_even_we ? even_write_addr :
        (busy ? read_addr[9:1] : matrix_ext_pair_addr);
    wire [8:0] matrix_odd_addr = matrix_odd_we ? odd_write_addr :
        (busy ? read_addr[9:1] : matrix_ext_pair_addr);
    wire [7:0] secret_even_addr = secret_even_we ? noise_write_addr :
        secret_read_addr;
    wire [7:0] secret_odd_addr = secret_odd_we ? noise_write_addr :
        secret_read_addr;
    wire [7:0] error_even_addr = error_even_we ? noise_write_addr :
        error_read_addr;
    wire [7:0] error_odd_addr = error_odd_we ? noise_write_addr :
        error_read_addr;
    wire [9:0] noise_byte_addr = noise_byte_we ? noise_load_addr :
        noise_read_addr;
    wire [7:0] ekpke_pair_addr = ekpke_pair_we ?
        {row_index, pair_index} :
        (busy ? serial_pair_index : ekpke_ext_pair_addr);
    wire [7:0] dkpke_pair_addr = dkpke_pair_we ?
        {column_index, pair_index} :
        (busy ? serial_pair_index : dkpke_ext_pair_addr);

    te_sram_1rw #(.WIDTH(12), .DEPTH(512), .ADDR_WIDTH(9))
        u_matrix_even_sram (
            .clk(clk), .we(matrix_even_we), .addr(matrix_even_addr),
            .wdata(even_write_data), .rdata(ram_even_q)
        );
    te_sram_1rw #(.WIDTH(12), .DEPTH(512), .ADDR_WIDTH(9))
        u_matrix_odd_sram (
            .clk(clk), .we(matrix_odd_we), .addr(matrix_odd_addr),
            .wdata(odd_write_data), .rdata(ram_odd_q)
        );
    te_sram_1rw #(.WIDTH(12), .DEPTH(256), .ADDR_WIDTH(8))
        u_secret_even_sram (
            .clk(clk), .we(secret_even_we), .addr(secret_even_addr),
            .wdata(ntt_rdata[11:0]), .rdata(secret_even_q)
        );
    te_sram_1rw #(.WIDTH(12), .DEPTH(256), .ADDR_WIDTH(8))
        u_secret_odd_sram (
            .clk(clk), .we(secret_odd_we), .addr(secret_odd_addr),
            .wdata(ntt_rdata[11:0]), .rdata(secret_odd_q)
        );
    te_sram_1rw #(.WIDTH(12), .DEPTH(256), .ADDR_WIDTH(8))
        u_error_even_sram (
            .clk(clk), .we(error_even_we), .addr(error_even_addr),
            .wdata(ntt_rdata[11:0]), .rdata(error_even_q)
        );
    te_sram_1rw #(.WIDTH(12), .DEPTH(256), .ADDR_WIDTH(8))
        u_error_odd_sram (
            .clk(clk), .we(error_odd_we), .addr(error_odd_addr),
            .wdata(ntt_rdata[11:0]), .rdata(error_odd_q)
        );
    te_sram_1rw #(.WIDTH(8), .DEPTH(768), .ADDR_WIDTH(10))
        u_noise_byte_sram (
            .clk(clk), .we(noise_byte_we), .addr(noise_byte_addr),
            .wdata(noise_load_data), .rdata(noise_byte_q)
        );
    te_sram_1rw #(.WIDTH(24), .DEPTH(256), .ADDR_WIDTH(8))
        u_ekpke_pair_sram (
            .clk(clk), .we(ekpke_pair_we), .addr(ekpke_pair_addr),
            .wdata(result_pair_bytes), .rdata(ekpke_pair_q)
        );
    te_sram_1rw #(.WIDTH(24), .DEPTH(256), .ADDR_WIDTH(8))
        u_dkpke_pair_sram (
            .clk(clk), .we(dkpke_pair_we), .addr(dkpke_pair_addr),
            .wdata(secret_pair_bytes), .rdata(dkpke_pair_q)
        );

    always @* begin
        matrix_ext_even_data = ram_even_q;
        matrix_ext_odd_data = ram_odd_q;
        ekpke_ext_pair_data = ekpke_pair_q;
        dkpke_ext_pair_data = dkpke_pair_q;
    end

    always @(posedge clk) begin
        if (!busy)
            rho_ext_data <= rho_ram[rho_ext_addr];
    end
`endif

    function automatic [11:0] add_mod_q;
        input [11:0] x;
        input [11:0] y;
        reg [12:0] sum;
        begin
            sum = {1'b0, x} + y;
            add_mod_q = (sum >= Q13) ? (sum[11:0] - 12'd3329) :
                                      sum[11:0];
        end
    endfunction

    function automatic [31:0] digest_step;
        input [31:0] current;
        input [11:0] value;
        begin
            digest_step = {current[30:0], current[31]} ^ {20'd0, value};
        end
    endfunction

    function automatic [31:0] byte_digest_step;
        input [31:0] current;
        input [7:0] value;
        begin
            byte_digest_step = {current[30:0], current[31]} ^ {24'd0, value};
        end
    endfunction

    function automatic [23:0] byteencode12_pair;
        input [11:0] c0;
        input [11:0] c1;
        begin
            byteencode12_pair = {c1[11:4], c1[3:0], c0[11:8], c0[7:0]};
        end
    endfunction

    wire [9:0] noise_byte_base = (noise_poly * 10'd192) +
                                  (noise_word_index * 10'd3);
    wire [23:0] noise_word_le = {noise_byte2_q, noise_byte1_q,
                                 noise_byte0_q};
    wire [15:0] cbd_coeff [0:3];
    mlkem512_cbd3_block u_noise_cbd3 (
        .word_le(noise_word_le),
        .coeff(cbd_coeff)
    );
    reg [15:0] noise_cbd_value;
    always @* begin
        case (noise_lane)
            2'd0: noise_cbd_value = cbd_coeff[0];
            2'd1: noise_cbd_value = cbd_coeff[1];
            2'd2: noise_cbd_value = cbd_coeff[2];
            default: noise_cbd_value = cbd_coeff[3];
        endcase
    end

    wire ntt_start = (state == S_NOISE_START);
    wire ntt_we = (state == S_NOISE_WRITE);
    wire [7:0] ntt_addr =
        ((state == S_NOISE_READ) && (noise_index != 8'd255)) ?
        (noise_index + 8'd1) :
        (state == S_NOISE_WRITE) ? {noise_word_index, noise_lane} :
        noise_index;
    wire [15:0] ntt_wdata = noise_cbd_value;
    wire ntt_busy;
    wire ntt_done;
    assign ntt_ext_start = ntt_start;
    assign ntt_ext_we = ntt_we;
    assign ntt_ext_addr = ntt_addr;
    assign ntt_ext_wdata = ntt_wdata;

    generate
        if (USE_EXTERNAL_NTT) begin : g_external_ntt
            assign ntt_busy = ntt_ext_busy;
            assign ntt_done = ntt_ext_done;
            assign ntt_rdata = ntt_ext_rdata;
        end else begin : g_private_ntt
            kyber_ntt_engine u_secret_ntt (
                .clk(clk), .rst_n(rst_n), .start(ntt_start),
                .inverse(1'b0), .busy(ntt_busy), .done(ntt_done),
                .waddr(ntt_addr), .wdata(ntt_wdata), .we(ntt_we),
                .rdata(ntt_rdata), .raddr(ntt_addr)
            );
        end
    endgenerate

    wire [31:0] secret_digest_next =
        digest_step(secret_digest, ntt_rdata[11:0]);
    wire [31:0] error_digest_next =
        digest_step(error_digest, ntt_rdata[11:0]);

    wire [6:0] gamma_index = 7'd64 + {1'b0, pair_index[6:1]};
    wire [15:0] gamma_full = kyber_zeta(gamma_index);
    wire [11:0] gamma_base = gamma_full[11:0];
    wire [11:0] gamma = pair_index[0] ? (12'd3329 - gamma_base) : gamma_base;

    reg [11:0] mul_lhs;
    reg [11:0] mul_rhs;
    always @* begin
        mul_lhs = 12'd0;
        mul_rhs = 12'd0;
        case (state)
            S_MUL0: begin mul_lhs = a0_q; mul_rhs = secret_b0_q; end
            S_MUL1: begin mul_lhs = a1_q; mul_rhs = secret_b1_q; end
            S_MUL2: begin mul_lhs = p1_q; mul_rhs = gamma; end
            S_MUL3: begin mul_lhs = a0_q; mul_rhs = secret_b1_q; end
            S_MUL4: begin mul_lhs = a1_q; mul_rhs = secret_b0_q; end
            default: begin mul_lhs = 12'd0; mul_rhs = 12'd0; end
        endcase
    end

    wire [23:0] mul_product = mul_lhs * mul_rhs;
    wire [11:0] mul_reduced;
    barrett_reduce u_mac_reduce (.a(mul_product), .r(mul_reduced));

    wire [11:0] base_c0 = add_mod_q(p0_q, p2_q);
    wire [11:0] base_c1 = add_mod_q(p3_q, p4_q);
    wire [11:0] final_c0 = column_index ? add_mod_q(accum0_q, base_c0) : base_c0;
    wire [11:0] final_c1 = column_index ? add_mod_q(accum1_q, base_c1) : base_c1;
    wire [11:0] result_c0 = add_mod_q(final_c0, error_even_q);
    wire [11:0] result_c1 = add_mod_q(final_c1, error_odd_q);
    wire [31:0] digest_after_pair =
        digest_step(digest_step(digest, result_c0), result_c1);
    assign result_pair_bytes = byteencode12_pair(result_c0, result_c1);
    assign secret_pair_bytes = byteencode12_pair(secret_even_q, secret_odd_q);
    wire [31:0] ekpke_after_pair = byte_digest_step(
        byte_digest_step(byte_digest_step(ekpke_digest,
                                          ekpke_pair_q[7:0]),
                         ekpke_pair_q[15:8]),
        ekpke_pair_q[23:16]);
    wire [31:0] dkpke_after_pair = byte_digest_step(
        byte_digest_step(byte_digest_step(dkpke_digest,
                                          dkpke_pair_q[7:0]),
                         dkpke_pair_q[15:8]),
        dkpke_pair_q[23:16]);
    wire [31:0] ekpke_after_rho = byte_digest_step(ekpke_digest,
                                                   rho_ram[rho_index]);

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= S_IDLE;
            row_index <= 1'b0;
            column_index <= 1'b0;
            pair_index <= 7'd0;
            read_addr <= 10'd0;
            a0_q <= 12'd0;
            a1_q <= 12'd0;
            p0_q <= 12'd0;
            p1_q <= 12'd0;
            p2_q <= 12'd0;
            p3_q <= 12'd0;
            p4_q <= 12'd0;
            accum0_q <= 12'd0;
            accum1_q <= 12'd0;
            secret_b0_q <= 12'd0;
            secret_b1_q <= 12'd0;
            noise_poly <= 2'd0;
            noise_word_index <= 6'd0;
            noise_lane <= 2'd0;
            noise_byte0_q <= 8'd0;
            noise_byte1_q <= 8'd0;
            noise_byte2_q <= 8'd0;
            noise_index <= 8'd0;
            noise_read_addr <= 10'd0;
            noise_loaded_bytes <= 10'd0;
            noise_loaded_coeffs <= 11'd0;
            rho_loaded_bytes <= 6'd0;
            rho_index <= 5'd0;
            core_ok <= 1'b0;
            serial_pair_index <= 8'd0;
            loaded_coeffs <= 11'd0;
            busy <= 1'b0;
            done <= 1'b0;
            pass <= 1'b0;
            digest <= 32'd0;
            secret_digest <= 32'd0;
            error_digest <= 32'd0;
            ekpke_digest <= 32'd0;
            dkpke_digest <= 32'd0;
            cycles <= 16'd0;
        end else begin
            done <= 1'b0;

            if (load_clear) begin
                loaded_coeffs <= 11'd0;
                noise_loaded_bytes <= 10'd0;
                rho_loaded_bytes <= 6'd0;
            end else begin
                if (!busy && (load0_valid || load1_valid))
                loaded_coeffs <= loaded_coeffs + load0_valid + load1_valid;
                if (!busy && noise_load_valid)
                    noise_loaded_bytes <= noise_loaded_bytes + 10'd1;
                if (!busy && rho_load_valid) begin
                    rho_ram[rho_load_addr] <= rho_load_data;
                    rho_loaded_bytes <= rho_loaded_bytes + 6'd1;
                end
            end

            if (busy && cycles != 16'hFFFF)
                cycles <= cycles + 16'd1;

            case (state)
                S_IDLE: begin
                    busy <= 1'b0;
                    if (start) begin
                        busy <= 1'b1;
                        pass <= 1'b0;
                        digest <= DIGEST_INIT;
                        secret_digest <= 32'h53454331;
                        error_digest <= 32'h45525231;
                        ekpke_digest <= 32'h454B5031;
                        dkpke_digest <= 32'h444B5031;
                        cycles <= 16'd0;
                        noise_poly <= 2'd0;
                        noise_word_index <= 6'd0;
                        noise_lane <= 2'd0;
                        noise_index <= 8'd0;
                        noise_loaded_coeffs <= 11'd0;
                        row_index <= 1'b0;
                        column_index <= 1'b0;
                        pair_index <= 7'd0;
                        accum0_q <= 12'd0;
                        accum1_q <= 12'd0;
                        rho_index <= 5'd0;
                        core_ok <= 1'b0;
                        serial_pair_index <= 8'd0;
                        state <= S_NOISE_ADDR0;
                    end
                end

                S_NOISE_ADDR0: begin
                    noise_read_addr <= noise_byte_base;
                    state <= S_NOISE_WAIT0;
                end
                S_NOISE_WAIT0: state <= S_NOISE_CAP0;
                S_NOISE_CAP0: begin
                    noise_byte0_q <= noise_byte_q;
                    noise_read_addr <= noise_byte_base + 10'd1;
                    state <= S_NOISE_WAIT1;
                end
                S_NOISE_WAIT1: state <= S_NOISE_CAP1;
                S_NOISE_CAP1: begin
                    noise_byte1_q <= noise_byte_q;
                    noise_read_addr <= noise_byte_base + 10'd2;
                    state <= S_NOISE_WAIT2;
                end
                S_NOISE_WAIT2: state <= S_NOISE_CAP2;
                S_NOISE_CAP2: begin
                    noise_byte2_q <= noise_byte_q;
                    noise_lane <= 2'd0;
                    state <= S_NOISE_WRITE;
                end
                S_NOISE_WRITE: begin
                    if (noise_lane == 2'd3) begin
                        noise_lane <= 2'd0;
                        if (noise_word_index == 6'd63) begin
                            noise_word_index <= 6'd0;
                            state <= S_NOISE_START;
                        end else begin
                            noise_word_index <= noise_word_index + 6'd1;
                            noise_read_addr <= noise_byte_base + 10'd3;
                            state <= S_NOISE_WAIT0;
                        end
                    end else begin
                        noise_lane <= noise_lane + 2'd1;
                    end
                end
                S_NOISE_START: state <= S_NOISE_NTT_WAIT;
                S_NOISE_NTT_WAIT: begin
                    if (ntt_done) begin
                        noise_index <= 8'd0;
                        state <= S_NOISE_PRIME;
                    end
                end
                S_NOISE_PRIME: state <= S_NOISE_READ;
                S_NOISE_READ: begin
                    if (noise_poly[1])
                        error_digest <= error_digest_next;
                    else
                        secret_digest <= secret_digest_next;
                    noise_loaded_coeffs <= noise_loaded_coeffs + 11'd1;
                    if (noise_index == 8'd255) begin
                        noise_index <= 8'd0;
                        state <= S_NOISE_NEXT;
                    end else begin
                        noise_index <= noise_index + 8'd1;
                    end
                end
                S_NOISE_NEXT: begin
                    if (noise_poly != 2'd3) begin
                        noise_poly <= noise_poly + 2'd1;
                        noise_word_index <= 6'd0;
                        noise_index <= 8'd0;
                        state <= S_NOISE_ADDR0;
                    end else begin
                        row_index <= 1'b0;
                        column_index <= 1'b0;
                        pair_index <= 7'd0;
                        state <= S_FETCH0;
                    end
                end

                S_FETCH0: begin
                    read_addr <= {row_index, column_index, pair_index, 1'b0};
                    state <= S_WAIT0;
                end
                S_WAIT0: state <= S_CAPTURE0;
                S_CAPTURE0: begin
                    a0_q <= ram_even_q;
                    secret_b0_q <= secret_even_q;
                    secret_b1_q <= secret_odd_q;
                    read_addr <= {row_index, column_index, pair_index, 1'b1};
                    state <= S_WAIT1;
                end
                S_WAIT1: state <= S_CAPTURE1;
                S_CAPTURE1: begin
                    a1_q <= ram_odd_q;
                    state <= S_MUL0;
                end
                S_MUL0: begin p0_q <= mul_reduced; state <= S_MUL1; end
                S_MUL1: begin p1_q <= mul_reduced; state <= S_MUL2; end
                S_MUL2: begin p2_q <= mul_reduced; state <= S_MUL3; end
                S_MUL3: begin p3_q <= mul_reduced; state <= S_MUL4; end
                S_MUL4: begin p4_q <= mul_reduced; state <= S_ACCUMULATE; end

                S_ACCUMULATE: begin
                    if (!column_index) begin
                        accum0_q <= base_c0;
                        accum1_q <= base_c1;
                        column_index <= 1'b1;
                        state <= S_FETCH0;
                    end else begin
                        digest <= digest_after_pair;
`ifndef TRUSTEDGE_ASIC_SRAM
                        ekpke_pair_ram[{row_index, pair_index}] <=
                            result_pair_bytes;
`endif
                        accum0_q <= 12'd0;
                        accum1_q <= 12'd0;
                        column_index <= 1'b0;
                        if (pair_index == 7'd127) begin
                            pair_index <= 7'd0;
                            if (row_index) begin
                                core_ok <= (loaded_coeffs == 11'd1024) &&
                                           (noise_loaded_bytes == 10'd768) &&
                                           (rho_loaded_bytes == 6'd32) &&
                                           (noise_loaded_coeffs == 11'd1024) &&
                                           (!check_expected ||
                                            ((secret_digest == EXPECTED_SECRET_DIGEST) &&
                                             (error_digest == EXPECTED_ERROR_DIGEST) &&
                                             (digest_after_pair == EXPECTED_DIGEST)));
                                column_index <= 1'b0;
                                state <= S_DK_ADDR;
                            end else begin
                                row_index <= 1'b1;
                                state <= S_FETCH0;
                            end
                        end else begin
                            pair_index <= pair_index + 7'd1;
                            state <= S_FETCH0;
                        end
                    end
                end

                S_DK_ADDR: state <= S_DK_WAIT;
                S_DK_WAIT: state <= S_DK_CAPTURE;
                S_DK_CAPTURE: begin
`ifndef TRUSTEDGE_ASIC_SRAM
                    dkpke_pair_ram[{column_index, pair_index}] <=
                        secret_pair_bytes;
`endif
                    if (pair_index == 7'd127) begin
                        pair_index <= 7'd0;
                        if (column_index) begin
                            column_index <= 1'b0;
                            serial_pair_index <= 8'd0;
                            state <= S_EK_READ_ADDR;
                        end else begin
                            column_index <= 1'b1;
                            state <= S_DK_ADDR;
                        end
                    end else begin
                        pair_index <= pair_index + 7'd1;
                        state <= S_DK_ADDR;
                    end
                end

                S_EK_READ_ADDR: state <= S_EK_READ_WAIT;
                S_EK_READ_WAIT: state <= S_EK_HASH;
                S_EK_HASH: begin
                    ekpke_digest <= ekpke_after_pair;
                    if (serial_pair_index == 8'd255) begin
                        serial_pair_index <= 8'd0;
                        rho_index <= 5'd0;
                        state <= S_RHO_HASH;
                    end else begin
                        serial_pair_index <= serial_pair_index + 8'd1;
                        state <= S_EK_READ_ADDR;
                    end
                end

                S_RHO_HASH: begin
                    ekpke_digest <= ekpke_after_rho;
                    if (rho_index == 5'd31) begin
                        serial_pair_index <= 8'd0;
                        state <= S_DK_READ_ADDR;
                    end else begin
                        rho_index <= rho_index + 5'd1;
                    end
                end

                S_DK_READ_ADDR: state <= S_DK_READ_WAIT;
                S_DK_READ_WAIT: state <= S_DK_HASH;
                S_DK_HASH: begin
                    dkpke_digest <= dkpke_after_pair;
                    if (serial_pair_index == 8'd255) begin
                        pass <= core_ok &&
                                (!check_expected ||
                                 ((ekpke_digest == EXPECTED_EKPKE_DIGEST) &&
                                  (dkpke_after_pair == EXPECTED_DKPKE_DIGEST)));
                        state <= S_DONE;
                    end else begin
                        serial_pair_index <= serial_pair_index + 8'd1;
                        state <= S_DK_READ_ADDR;
                    end
                end

                S_DONE: begin
                    busy <= 1'b0;
                    done <= 1'b1;
                    state <= S_IDLE;
                end
                default: state <= S_IDLE;
            endcase
        end
    end
endmodule
