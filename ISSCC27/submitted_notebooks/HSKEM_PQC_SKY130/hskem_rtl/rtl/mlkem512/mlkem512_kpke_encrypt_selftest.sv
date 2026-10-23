import kyber_pkg::*;
import mlkem512_pkg::*;

// One sequential SHAKE256 engine expands coins into the five K-PKE.Encrypt
// noise polynomials: y0/y1 use eta1=3 and e1[0]/e1[1]/e2 use eta2=2.
// Coefficients are emitted in canonical polynomial order and never leave RTL.
module mlkem512_encrypt_prf_stream #(
    parameter USE_EXTERNAL_SPONGE = 1'b0
) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire         start,
    input  wire [255:0] coins,
    output reg          busy,
    output reg          done,
    output reg          pass,
    output reg          coeff_valid,
    output reg [10:0]   coeff_addr,
    output reg [11:0]   coeff_data,
    output reg [31:0]   prf_digest,
    output reg [15:0]   cycles,
    output wire         sponge_ext_start,
    output wire [1:0]   sponge_ext_mode,
    output wire [15:0]  sponge_ext_message_len,
    output wire [15:0]  sponge_ext_output_len,
    output wire         sponge_ext_in_valid,
    output wire [7:0]   sponge_ext_in_byte,
    output wire         sponge_ext_out_ready,
    input  wire         sponge_ext_in_ready,
    input  wire         sponge_ext_out_valid,
    input  wire [7:0]   sponge_ext_out_byte,
    input  wire         sponge_ext_out_last,
    input  wire         sponge_ext_busy,
    input  wire         sponge_ext_done,
    input  wire         sponge_ext_error
);
    // Explicit one-hot encoding prevents a binary state bit from being
    // synthesized as both reset polarity and clock-enable control.
    localparam [5:0] P_IDLE =6'b000001, P_START=6'b000010,
                     P_RUN  =6'b000100, P_EMIT =6'b001000,
                     P_WAIT =6'b010000, P_DONE =6'b100000;
    reg [5:0] state;
    reg [2:0] poly_index;
    reg [5:0] feed_index;
    reg [2:0] block_byte;
    reg [8:0] coeff_index;
    reg [31:0] word_q;
    reg [31:0] block_q;
    reg sponge_start;
    reg sponge_done_seen;

    wire eta1_poly = poly_index < 3'd2;
    wire [15:0] output_len = eta1_poly ? 16'd192 : 16'd128;
    wire [2:0] last_block_byte = eta1_poly ? 3'd2 : 3'd3;
    wire sponge_in_valid = (state == P_RUN) && (feed_index < 6'd33);
    wire [7:0] sponge_in_byte = (feed_index < 6'd32) ?
        coins[feed_index*8 +: 8] : {5'd0, poly_index};
    wire sponge_in_ready;
    wire sponge_out_valid;
    wire [7:0] sponge_out_byte;
    wire sponge_done;
    wire sponge_error;
    wire [31:0] word_with_byte = word_q |
        ({24'd0, sponge_out_byte} << (block_byte * 8));

    wire [15:0] cbd2_coeff [0:7];
    wire [15:0] cbd3_coeff [0:3];
    mlkem512_cbd2_block u_cbd2(.word_le(block_q), .coeff(cbd2_coeff));
    mlkem512_cbd3_block u_cbd3(.word_le(block_q[23:0]), .coeff(cbd3_coeff));

    function automatic [31:0] digest_step;
        input [31:0] current;
        input [7:0] value;
        begin digest_step = {current[30:0], current[31]} ^ {24'd0, value}; end
    endfunction

    assign sponge_ext_start = sponge_start;
    assign sponge_ext_mode = 2'd3;
    assign sponge_ext_message_len = 16'd33;
    assign sponge_ext_output_len = output_len;
    assign sponge_ext_in_valid = sponge_in_valid;
    assign sponge_ext_in_byte = sponge_in_byte;
    assign sponge_ext_out_ready = (state == P_RUN);

    generate
        if (USE_EXTERNAL_SPONGE) begin : g_external_sponge
            assign sponge_in_ready = sponge_ext_in_ready;
            assign sponge_out_valid = sponge_ext_out_valid;
            assign sponge_out_byte = sponge_ext_out_byte;
            assign sponge_done = sponge_ext_done;
            assign sponge_error = sponge_ext_error;
        end else begin : g_private_sponge
            keccak_sponge_stream u_sponge (
                .clk(clk), .rst_n(rst_n), .zeroize(1'b0),
                .start(sponge_start), .mode(2'd3),
                .message_len(16'd33), .output_len(output_len),
                .in_valid(sponge_in_valid), .in_byte(sponge_in_byte),
                .in_ready(sponge_in_ready), .out_valid(sponge_out_valid),
                .out_byte(sponge_out_byte), .out_last(),
                .out_ready(state == P_RUN), .busy(), .done(sponge_done),
                .error(sponge_error)
            );
        end
    endgenerate

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= P_IDLE;
            poly_index <= 3'd0;
            feed_index <= 6'd0;
            block_byte <= 3'd0;
            coeff_index <= 9'd0;
            word_q <= 32'd0;
            block_q <= 32'd0;
            sponge_start <= 1'b0;
            sponge_done_seen <= 1'b0;
            busy <= 1'b0;
            done <= 1'b0;
            pass <= 1'b0;
            coeff_valid <= 1'b0;
            coeff_addr <= 11'd0;
            coeff_data <= 12'd0;
            prf_digest <= 32'd0;
            cycles <= 16'd0;
        end else begin
            done <= 1'b0;
            coeff_valid <= 1'b0;
            sponge_start <= 1'b0;
            if (sponge_done)
                sponge_done_seen <= 1'b1;
            if (busy && cycles != 16'hFFFF)
                cycles <= cycles + 16'd1;
            case (state)
                P_IDLE: begin
                    busy <= 1'b0;
                    if (start) begin
                        busy <= 1'b1;
                        pass <= 1'b0;
                        poly_index <= 3'd0;
                        prf_digest <= 32'h50524645;
                        cycles <= 16'd0;
                        state <= P_START;
                    end
                end
                P_START: begin
                    feed_index <= 6'd0;
                    block_byte <= 3'd0;
                    coeff_index <= 9'd0;
                    word_q <= 32'd0;
                    sponge_done_seen <= 1'b0;
                    sponge_start <= 1'b1;
                    state <= P_RUN;
                end
                P_RUN: begin
                    if (sponge_in_valid && sponge_in_ready)
                        feed_index <= feed_index + 6'd1;
                    if (sponge_out_valid) begin
                        prf_digest <= digest_step(prf_digest, sponge_out_byte);
                        word_q <= word_with_byte;
                        if (block_byte == last_block_byte) begin
                            block_q <= word_with_byte;
                            word_q <= 32'd0;
                            block_byte <= 3'd0;
                            state <= P_EMIT;
                        end else begin
                            block_byte <= block_byte + 3'd1;
                        end
                    end
                end
                P_EMIT: begin
                    coeff_valid <= 1'b1;
                    coeff_addr <= (poly_index * 11'd256) + coeff_index;
                    coeff_data <= eta1_poly ? cbd3_coeff[coeff_index[1:0]][11:0] :
                                              cbd2_coeff[coeff_index[2:0]][11:0];
                    if (coeff_index == 9'd255) begin
                        state <= P_WAIT;
                    end else begin
                        coeff_index <= coeff_index + 9'd1;
                        if ((eta1_poly && (coeff_index[1:0] == 2'd3)) ||
                            (!eta1_poly && (coeff_index[2:0] == 3'd7))) begin
                            state <= P_RUN;
                        end
                    end
                end
                P_WAIT: begin
                    if (sponge_done_seen) begin
                        if (poly_index == 3'd4)
                            state <= P_DONE;
                        else begin
                            poly_index <= poly_index + 3'd1;
                            state <= P_START;
                        end
                    end
                end
                P_DONE: begin
                    busy <= 1'b0;
                    done <= 1'b1;
                    // Reaching the final polynomial/last coefficient already
                    // proves that all 5*256 coefficients were emitted.
                    pass <= !sponge_error && (poly_index == 3'd4) &&
                            (coeff_index == 9'd255);
                    state <= P_IDLE;
                end
                default: begin busy <= 1'b0; pass <= 1'b0; state <= P_IDLE; end
            endcase
        end
    end
endmodule

// K-PKE.Encrypt arithmetic checkpoint.  Legacy zero-length requests retain
// the deterministic public KAT.  A 64-byte runtime request supplies m[32] and
// coins[32]; SHAKE256/CBD then produces y/e1/e2 inside the FPGA.  The public
// A/t operands remain the deterministic KAT for the legacy zero-length KAT.
// When USE_RUNTIME_KEY_BIND is selected, a 64-byte runtime request is bound
// to the matrix and ekPKE coefficient RAM written by the most recent passing
// runtime KeyGen.  Those coefficient ports are internal only: no raw ekPKE
// value reaches the SPI response path.
module mlkem512_kpke_encrypt_selftest #(
    parameter [31:0] EXPECTED_DIGEST_A = 32'hCA84F003,
    parameter [31:0] EXPECTED_DIGEST_B = 32'h5D4B538C,
    parameter USE_EXTERNAL_NTT = 1'b0,
    parameter USE_EXTERNAL_SPONGE = 1'b0,
    parameter USE_RUNTIME_KEY_BIND = 1'b0
) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire         start,
    input  wire         runtime_input_valid,
    input  wire [255:0] runtime_message,
    input  wire [255:0] runtime_coins,
    output reg          busy,
    output reg          done,
    output reg          pass,
    output reg [7:0]    status,
    output reg [31:0]   ciphertext_digest,
    output reg [31:0]   audit_digest,
    output reg [15:0]   cycles,
    output wire         ntt_ext_start,
    output wire         ntt_ext_inverse,
    output wire         ntt_ext_we,
    output wire [7:0]   ntt_ext_addr,
    output wire [15:0]  ntt_ext_wdata,
    input  wire         ntt_ext_busy,
    input  wire         ntt_ext_done,
    input  wire [15:0]  ntt_ext_rdata,
    output wire         sponge_ext_start,
    output wire [1:0]   sponge_ext_mode,
    output wire [15:0]  sponge_ext_message_len,
    output wire [15:0]  sponge_ext_output_len,
    output wire         sponge_ext_in_valid,
    output wire [7:0]   sponge_ext_in_byte,
    output wire         sponge_ext_out_ready,
    input  wire         sponge_ext_in_ready,
    input  wire         sponge_ext_out_valid,
    input  wire [7:0]   sponge_ext_out_byte,
    input  wire         sponge_ext_out_last,
    input  wire         sponge_ext_busy,
    input  wire         sponge_ext_done,
    input  wire         sponge_ext_error,
    // Internal KeyGen RAM read ports.  They are intentionally not connected
    // to the SPI command bridge or response frame.
    input  wire         runtime_key_ready,
    output wire [8:0]   matrix_ext_pair_addr,
    input  wire [11:0]  matrix_ext_even_data,
    input  wire [11:0]  matrix_ext_odd_data,
    output wire [7:0]   ekpke_ext_pair_addr,
    input  wire [23:0]  ekpke_ext_pair_data,
    input  wire [9:0]   ciphertext_read_addr,
    output wire [7:0]   ciphertext_read_data,
    input  wire [9:0]   decoded_read_addr,
    output wire [11:0]  decoded_read_data,
    input  wire         ciphertext_import_clear,
    input  wire         ciphertext_import_valid,
    input  wire [9:0]   ciphertext_import_addr,
    input  wire [7:0]   ciphertext_import_data,
    input  wire         ciphertext_import_start,
    input  wire         ciphertext_import_compare_source,
    output wire [9:0]   ciphertext_imported_bytes,
    output wire         ciphertext_import_done,
    output wire         ciphertext_import_pass
);
    localparam [31:0]
        S_IDLE        =32'h00000001, S_CODEC_CLR   =32'h00000002,
        S_PAIR_INIT   =32'h00000004, S_MUL0        =32'h00000008,
        S_MUL1        =32'h00000010, S_MUL2        =32'h00000020,
        S_MUL3        =32'h00000040, S_MUL4        =32'h00000080,
        S_ACCUM       =32'h00000100, S_NTT_WRITE0  =32'h00000200,
        S_NTT_WRITE1  =32'h00000400, S_INV_START   =32'h00000800,
        S_INV_WAIT    =32'h00001000, S_READ_REQ    =32'h00002000,
        S_READ_WAIT   =32'h00004000, S_READ_LOAD   =32'h00008000,
        S_CODEC_START =32'h00010000, S_CODEC_WAIT  =32'h00020000,
        S_OPERAND     =32'h00040000, S_PRF_START   =32'h00080000,
        S_PRF_WAIT    =32'h00100000, S_Y_FETCH     =32'h00200000,
        S_Y_WAIT      =32'h00400000, S_Y_WRITE0    =32'h00800000,
        S_Y_WRITE1    =32'h01000000, S_Y_NTT_START=32'h02000000,
        S_Y_NTT_WAIT  =32'h04000000, S_Y_READ_REQ  =32'h08000000,
        S_Y_READ_WAIT =32'h10000000, S_Y_READ_CAP  =32'h20000000,
        S_Y_NEXT      =32'h40000000, S_OPERAND_WAIT=32'h80000000;

    localparam [12:0] Q13 = 13'd3329;
    reg [31:0] state;
    reg [1:0] poly_index;
    reg       column_index;
    reg [6:0] pair_index;
    reg [7:0] read_index;
    reg [11:0] p0_q, p1_q, p2_q, p3_q, p4_q;
    reg [11:0] operand_a0_q, operand_a1_q;
    reg [11:0] operand_b0_q, operand_b1_q, gamma_q;
    reg [11:0] accum0_q, accum1_q;
    reg [11:0] result0_q, result1_q;
    reg runtime_valid_q;
    reg runtime_key_bound_q;
    reg [255:0] runtime_message_q, runtime_coins_q;
    reg runtime_prf_ok_q;
    reg operand_wait_q;
    reg y_poly;
    reg [6:0] y_pair;
    reg [7:0] y_read_index;

`ifdef TRUSTEDGE_ASIC_SRAM
    wire [11:0] noise_even_q, noise_odd_q;
`else
    (* ramstyle = "M20K, no_rw_check" *) reg [11:0] noise_even_ram [0:639];
    (* ramstyle = "M20K, no_rw_check" *) reg [11:0] noise_odd_ram [0:639];
    reg [11:0] noise_even_q, noise_odd_q;
`endif
    reg [9:0] noise_read_addr;

    function automatic [11:0] add_mod_q;
        input [11:0] x; input [11:0] y; reg [12:0] sum;
        begin sum={1'b0,x}+{1'b0,y}; add_mod_q=(sum>=Q13)?sum-Q13:sum[11:0]; end
    endfunction
    function automatic [11:0] kat_matrix;
        input [0:0] row; input [0:0] col; input [7:0] idx; integer value;
        begin value=(idx*17+row*257+col*911+3)%3329; kat_matrix=value[11:0]; end
    endfunction
    function automatic [11:0] kat_y_hat;
        input [0:0] col; input [7:0] idx; integer value;
        begin value=(idx*29+col*613+19)%3329; kat_y_hat=value[11:0]; end
    endfunction
    function automatic [11:0] kat_t_hat;
        input [0:0] col; input [7:0] idx; integer value;
        begin value=(idx*43+col*379+23)%3329; kat_t_hat=value[11:0]; end
    endfunction
    function automatic [11:0] kat_noise;
        input [1:0] poly; input [7:0] idx; integer signed delta;
        begin delta=((idx+poly*3)%5)-2; kat_noise=(delta<0)?3329+delta:delta; end
    endfunction

    wire [7:0] coeff_index0 = {pair_index,1'b0};
    wire [7:0] coeff_index1 = {pair_index,1'b1};
    // One synchronous pair read covers both parity banks.  Encrypt holds the
    // address stable for two cycles before capture; see S_OPERAND_WAIT.
    // K-PKE.Encrypt computes u = NTT^-1(A_hat^T o y_hat) + e1.
    // KeyGen stores A in row-major order, so runtime Encrypt must swap the
    // row/column selectors here.  The former A*y addressing was self-
    // consistent with its ciphertext oracle but could not decrypt correctly.
    assign matrix_ext_pair_addr = {column_index, poly_index[0], pair_index};
    assign ekpke_ext_pair_addr = {column_index, pair_index};
    // ekPKE serializes a pair as c0[7:0], c0[11:8]|c1[3:0], c1[11:4].
    // Do not treat its low 12 stored bits as c0: that would splice in the
    // low nibble of c1 and silently corrupt every t-hat multiply.
    wire [11:0] key_operand_a0 = (poly_index<2) ? matrix_ext_even_data :
        {ekpke_ext_pair_data[11:8], ekpke_ext_pair_data[7:0]};
    wire [11:0] key_operand_a1 = (poly_index<2) ? matrix_ext_odd_data :
                                                 ekpke_ext_pair_data[23:12];
    wire [11:0] operand_a0 = runtime_key_bound_q ? key_operand_a0 :
        ((poly_index<2) ? kat_matrix(poly_index[0],column_index,coeff_index0) :
                          kat_t_hat(column_index,coeff_index0));
    wire [11:0] operand_a1 = runtime_key_bound_q ? key_operand_a1 :
        ((poly_index<2) ? kat_matrix(poly_index[0],column_index,coeff_index1) :
                          kat_t_hat(column_index,coeff_index1));
    wire [11:0] legacy_b0 = kat_y_hat(column_index,coeff_index0);
    wire [11:0] legacy_b1 = kat_y_hat(column_index,coeff_index1);
    wire [6:0] gamma_index = 7'd64 + {1'b0,pair_index[6:1]};
    wire [15:0] gamma_full = kyber_zeta(gamma_index);
    wire [11:0] gamma_base = gamma_full[11:0];
    wire [11:0] gamma = pair_index[0] ? (12'd3329-gamma_base) : gamma_base;

    reg [11:0] mul_lhs, mul_rhs;
    always @* begin
        mul_lhs=12'd0; mul_rhs=12'd0;
        case(state)
            S_MUL0: begin mul_lhs=operand_a0_q; mul_rhs=operand_b0_q; end
            S_MUL1: begin mul_lhs=operand_a1_q; mul_rhs=operand_b1_q; end
            S_MUL2: begin mul_lhs=p1_q; mul_rhs=gamma_q; end
            S_MUL3: begin mul_lhs=operand_a0_q; mul_rhs=operand_b1_q; end
            S_MUL4: begin mul_lhs=operand_a1_q; mul_rhs=operand_b0_q; end
            default: begin mul_lhs=12'd0; mul_rhs=12'd0; end
        endcase
    end
    wire [23:0] mul_product=mul_lhs*mul_rhs;
    wire [11:0] mul_reduced;
    barrett_reduce u_reduce(.a(mul_product),.r(mul_reduced));
    wire [11:0] base0=add_mod_q(p0_q,p2_q);
    wire [11:0] base1=add_mod_q(p3_q,p4_q);
    wire [11:0] final0=add_mod_q(accum0_q,base0);
    wire [11:0] final1=add_mod_q(accum1_q,base1);

    wire prf_start=(state==S_PRF_START);
    wire prf_done, prf_pass, prf_coeff_valid;
    wire [10:0] prf_coeff_addr;
    wire [11:0] prf_coeff_data;
    wire [31:0] prf_digest;
    wire [15:0] prf_cycles;
    wire ntt_busy,ntt_done;
    wire [15:0] ntt_rdata;
    mlkem512_encrypt_prf_stream #(
        .USE_EXTERNAL_SPONGE(USE_EXTERNAL_SPONGE)
    ) u_encrypt_prf(
        .clk(clk),.rst_n(rst_n),.start(prf_start),.coins(runtime_coins_q),
        .busy(),.done(prf_done),.pass(prf_pass),
        .coeff_valid(prf_coeff_valid),.coeff_addr(prf_coeff_addr),
        .coeff_data(prf_coeff_data),.prf_digest(prf_digest),.cycles(prf_cycles),
        .sponge_ext_start(sponge_ext_start),.sponge_ext_mode(sponge_ext_mode),
        .sponge_ext_message_len(sponge_ext_message_len),
        .sponge_ext_output_len(sponge_ext_output_len),
        .sponge_ext_in_valid(sponge_ext_in_valid),
        .sponge_ext_in_byte(sponge_ext_in_byte),
        .sponge_ext_out_ready(sponge_ext_out_ready),
        .sponge_ext_in_ready(sponge_ext_in_ready),
        .sponge_ext_out_valid(sponge_ext_out_valid),
        .sponge_ext_out_byte(sponge_ext_out_byte),
        .sponge_ext_out_last(sponge_ext_out_last),
        .sponge_ext_busy(sponge_ext_busy),.sponge_ext_done(sponge_ext_done),
        .sponge_ext_error(sponge_ext_error));

    wire y_phase = (state==S_Y_FETCH)||(state==S_Y_WAIT)||
                   (state==S_Y_WRITE0)||(state==S_Y_WRITE1)||
                   (state==S_Y_NTT_START)||(state==S_Y_NTT_WAIT)||
                   (state==S_Y_READ_REQ)||(state==S_Y_READ_WAIT)||
                   (state==S_Y_READ_CAP)||(state==S_Y_NEXT);
    always @* begin
        if (y_phase)
            noise_read_addr={2'd0,y_poly,y_pair};
        else if ((state==S_READ_REQ)||(state==S_READ_WAIT)||(state==S_READ_LOAD))
            noise_read_addr=(({1'b0,poly_index}+3'd2)*10'd128)+read_index[7:1];
        else
            noise_read_addr=(column_index*10'd128)+pair_index;
    end
`ifndef TRUSTEDGE_ASIC_SRAM
    always @(posedge clk) begin
        noise_even_q <= noise_even_ram[noise_read_addr];
        noise_odd_q <= noise_odd_ram[noise_read_addr];
        if (prf_coeff_valid) begin
            if (prf_coeff_addr[0])
                noise_odd_ram[prf_coeff_addr[10:1]] <= prf_coeff_data;
            else
                noise_even_ram[prf_coeff_addr[10:1]] <= prf_coeff_data;
        end else if (state==S_Y_READ_CAP) begin
            if (y_read_index[0])
                noise_odd_ram[{2'd0,y_poly,y_read_index[7:1]}] <= ntt_rdata[11:0];
            else
                noise_even_ram[{2'd0,y_poly,y_read_index[7:1]}] <= ntt_rdata[11:0];
        end
    end
`else
    // PRF fill, Y-NTT writeback and arithmetic reads are disjoint phases.
    // Write priority therefore preserves the existing synchronous latency
    // while replacing each parity bank with one physical 1RW port.
    wire noise_even_we = (prf_coeff_valid && !prf_coeff_addr[0]) ||
                         ((state == S_Y_READ_CAP) && !y_read_index[0]);
    wire noise_odd_we = (prf_coeff_valid && prf_coeff_addr[0]) ||
                        ((state == S_Y_READ_CAP) && y_read_index[0]);
    wire [9:0] noise_even_waddr = prf_coeff_valid ?
        prf_coeff_addr[10:1] : {2'd0, y_poly, y_read_index[7:1]};
    wire [9:0] noise_odd_waddr = prf_coeff_valid ?
        prf_coeff_addr[10:1] : {2'd0, y_poly, y_read_index[7:1]};
    wire [11:0] noise_mem_wdata = prf_coeff_valid ?
        prf_coeff_data : ntt_rdata[11:0];

    te_sram_1rw #(.WIDTH(12), .DEPTH(640), .ADDR_WIDTH(10))
        u_noise_even_sram (
            .clk(clk), .we(noise_even_we),
            .addr(noise_even_we ? noise_even_waddr : noise_read_addr),
            .wdata(noise_mem_wdata), .rdata(noise_even_q)
        );
    te_sram_1rw #(.WIDTH(12), .DEPTH(640), .ADDR_WIDTH(10))
        u_noise_odd_sram (
            .clk(clk), .we(noise_odd_we),
            .addr(noise_odd_we ? noise_odd_waddr : noise_read_addr),
            .wdata(noise_mem_wdata), .rdata(noise_odd_q)
        );
`endif

    wire y_ntt_write=(state==S_Y_WRITE0)||(state==S_Y_WRITE1);
    wire data_ntt_write=(state==S_NTT_WRITE0)||(state==S_NTT_WRITE1);
    wire ntt_start=(state==S_INV_START)||(state==S_Y_NTT_START);
    wire ntt_we=y_ntt_write||data_ntt_write;
    wire [7:0] ntt_addr = y_ntt_write ?
        ((state==S_Y_WRITE0)?{y_pair,1'b0}:{y_pair,1'b1}) :
        ((state==S_Y_READ_REQ)||(state==S_Y_READ_WAIT)||(state==S_Y_READ_CAP)) ? y_read_index :
        (state==S_NTT_WRITE0)?coeff_index0:
        (state==S_NTT_WRITE1)?coeff_index1:read_index;
    wire [15:0] ntt_wdata = y_ntt_write ?
        ((state==S_Y_WRITE0)?{4'd0,noise_even_q}:{4'd0,noise_odd_q}) :
        (state==S_NTT_WRITE0)?{4'd0,result0_q}:{4'd0,result1_q};
    assign ntt_ext_start=ntt_start;
    assign ntt_ext_inverse=(state==S_INV_START);
    assign ntt_ext_we=ntt_we;
    assign ntt_ext_addr=ntt_addr;
    assign ntt_ext_wdata=ntt_wdata;
    generate
        if(USE_EXTERNAL_NTT) begin:g_external_ntt
            assign ntt_busy=ntt_ext_busy; assign ntt_done=ntt_ext_done;
            assign ntt_rdata=ntt_ext_rdata;
        end else begin:g_private_ntt
            kyber_ntt_engine u_ntt(.clk(clk),.rst_n(rst_n),.start(ntt_start),
                .inverse(ntt_ext_inverse),.busy(ntt_busy),.done(ntt_done),
                .waddr(ntt_addr),.wdata(ntt_wdata),.we(ntt_we),
                .rdata(ntt_rdata),.raddr(ntt_addr));
        end
    endgenerate

    wire [11:0] runtime_noise = read_index[0]?noise_odd_q:noise_even_q;
    wire [11:0] noisy_coeff=add_mod_q(ntt_rdata[11:0],
        runtime_valid_q?runtime_noise:kat_noise(poly_index,read_index));
    wire message_bit=runtime_valid_q ? runtime_message_q[read_index] :
        (read_index[0]^read_index[3]^read_index[5]);
    wire [11:0] message_coeff=message_bit?12'd1665:12'd0;
    wire [11:0] codec_coeff=(poly_index==2)?
        add_mod_q(noisy_coeff,message_coeff):noisy_coeff;
    wire [9:0] codec_index=(poly_index==0)?{2'd0,read_index}:
        (poly_index==1)?(10'd256+read_index):(10'd512+read_index);
    wire codec_load_clear=(state==S_CODEC_CLR);
    wire codec_load_valid=(state==S_READ_LOAD);
    wire codec_start=(state==S_CODEC_START);
    wire codec_busy,codec_done,codec_pass;
    wire [31:0] codec_digest_a,codec_digest_b;
    wire [31:0] codec_decode_digest;
    wire codec_decode_pass;
    wire [15:0] codec_cycles;
    wire [9:0] codec_loaded_coeffs;
    assign ciphertext_import_done = codec_done;
    assign ciphertext_import_pass = codec_pass;
    mlkem512_ciphertext_codec #(.EXPECTED_DIGEST_A(EXPECTED_DIGEST_A),
        .EXPECTED_DIGEST_B(EXPECTED_DIGEST_B)) u_codec(
        .clk(clk),.rst_n(rst_n),.load_clear(codec_load_clear),
        .load_valid(codec_load_valid),.load_index(codec_index),
        .load_coeff(codec_coeff),.check_expected(!runtime_valid_q),
        .import_clear(ciphertext_import_clear),
        .import_valid(ciphertext_import_valid),
        .import_addr(ciphertext_import_addr),
        .import_data(ciphertext_import_data),
        .import_start(ciphertext_import_start),
        .import_compare_source(ciphertext_import_compare_source),
        .start(codec_start),.busy(codec_busy),.done(codec_done),.pass(codec_pass),
        .digest_a(codec_digest_a),.digest_b(codec_digest_b),.cycles(codec_cycles),
        .decode_digest(codec_decode_digest),.decode_pass(codec_decode_pass),
        .loaded_coeffs(codec_loaded_coeffs),.ct_read_addr(ciphertext_read_addr),
        .ct_read_data(ciphertext_read_data),.decoded_read_addr(decoded_read_addr),
        .decoded_read_data(decoded_read_data),
        .imported_bytes(ciphertext_imported_bytes));

    always @(posedge clk or negedge rst_n) begin
        if(!rst_n) begin
            state<=S_IDLE; poly_index<=0; column_index<=0; pair_index<=0;
            read_index<=0; p0_q<=0;p1_q<=0;p2_q<=0;p3_q<=0;p4_q<=0;
            operand_a0_q<=0;operand_a1_q<=0;operand_b0_q<=0;operand_b1_q<=0;
            gamma_q<=0;accum0_q<=0;accum1_q<=0;result0_q<=0;result1_q<=0;
            runtime_valid_q<=0;runtime_key_bound_q<=0;
            runtime_message_q<=0;runtime_coins_q<=0;
            runtime_prf_ok_q<=0;operand_wait_q<=0;
            y_poly<=0;y_pair<=0;y_read_index<=0;
            busy<=0;done<=0;pass<=0;status<=0;ciphertext_digest<=0;
            audit_digest<=0;cycles<=0;
        end else begin
            done<=1'b0;
            if(busy&&cycles!=16'hFFFF) cycles<=cycles+16'd1;
            case(state)
                S_IDLE: begin busy<=0; if(start) begin
                    busy<=1;pass<=0;status<=0;ciphertext_digest<=0;audit_digest<=0;
                    cycles<=0;poly_index<=0;runtime_valid_q<=runtime_input_valid;
                    runtime_key_bound_q<=runtime_input_valid &&
                        USE_RUNTIME_KEY_BIND && runtime_key_ready;
                    runtime_message_q<=runtime_message;runtime_coins_q<=runtime_coins;
                    runtime_prf_ok_q<=!runtime_input_valid ||
                        (!USE_RUNTIME_KEY_BIND) || runtime_key_ready;
                    state<=S_CODEC_CLR; end end
                // A runtime request without an already validated internal
                // KeyGen result is fail-closed; legacy KAT remains available.
                S_CODEC_CLR: begin
                    if (runtime_valid_q && USE_RUNTIME_KEY_BIND &&
                        !runtime_key_bound_q)
                        state<=S_CODEC_WAIT;
                    else
                        state<=runtime_valid_q?S_PRF_START:S_PAIR_INIT;
                end
                S_PRF_START: state<=S_PRF_WAIT;
                S_PRF_WAIT: if(prf_done) begin runtime_prf_ok_q<=prf_pass;
                    y_poly<=0;y_pair<=0;state<=prf_pass?S_Y_FETCH:S_CODEC_WAIT; end
                S_Y_FETCH: state<=S_Y_WAIT;
                S_Y_WAIT: state<=S_Y_WRITE0;
                S_Y_WRITE0: state<=S_Y_WRITE1;
                S_Y_WRITE1: begin if(y_pair==127) state<=S_Y_NTT_START;
                    else begin y_pair<=y_pair+1'b1;state<=S_Y_FETCH;end end
                S_Y_NTT_START: state<=S_Y_NTT_WAIT;
                S_Y_NTT_WAIT: if(ntt_done) begin y_read_index<=0;state<=S_Y_READ_REQ;end
                S_Y_READ_REQ: state<=S_Y_READ_WAIT;
                S_Y_READ_WAIT: state<=S_Y_READ_CAP;
                S_Y_READ_CAP: begin if(y_read_index==255) state<=S_Y_NEXT;
                    else begin y_read_index<=y_read_index+1'b1;state<=S_Y_READ_REQ;end end
                S_Y_NEXT: begin if(!y_poly) begin y_poly<=1;y_pair<=0;state<=S_Y_FETCH;end
                    else begin poly_index<=0;state<=S_PAIR_INIT;end end
                S_PAIR_INIT: begin column_index<=0;pair_index<=0;accum0_q<=0;accum1_q<=0;
                    operand_wait_q<=runtime_key_bound_q;
                    state<=runtime_valid_q?S_OPERAND_WAIT:S_OPERAND;end
                // Runtime PRF RAM already needed one wait state.  Bound-key
                // reads add one further wait so data from the synchronous
                // KeyGen matrix/ekPKE M20Ks cannot be one pair stale.
                S_OPERAND_WAIT: begin
                    if (operand_wait_q)
                        operand_wait_q<=1'b0;
                    else
                        state<=S_OPERAND;
                end
                S_OPERAND: begin operand_a0_q<=operand_a0;operand_a1_q<=operand_a1;
                    operand_b0_q<=runtime_valid_q?noise_even_q:legacy_b0;
                    operand_b1_q<=runtime_valid_q?noise_odd_q:legacy_b1;
                    gamma_q<=gamma;state<=S_MUL0;end
                S_MUL0: begin p0_q<=mul_reduced;state<=S_MUL1;end
                S_MUL1: begin p1_q<=mul_reduced;state<=S_MUL2;end
                S_MUL2: begin p2_q<=mul_reduced;state<=S_MUL3;end
                S_MUL3: begin p3_q<=mul_reduced;state<=S_MUL4;end
                S_MUL4: begin p4_q<=mul_reduced;state<=S_ACCUM;end
                S_ACCUM: begin if(!column_index) begin accum0_q<=base0;accum1_q<=base1;
                    column_index<=1;operand_wait_q<=runtime_key_bound_q;
                    state<=runtime_valid_q?S_OPERAND_WAIT:S_OPERAND;end
                    else begin result0_q<=final0;result1_q<=final1;state<=S_NTT_WRITE0;end end
                S_NTT_WRITE0: state<=S_NTT_WRITE1;
                S_NTT_WRITE1: begin if(pair_index==127) state<=S_INV_START;
                    else begin pair_index<=pair_index+1'b1;column_index<=0;
                    accum0_q<=0;accum1_q<=0;operand_wait_q<=runtime_key_bound_q;
                    state<=runtime_valid_q?S_OPERAND_WAIT:S_OPERAND;end end
                S_INV_START: state<=S_INV_WAIT;
                S_INV_WAIT: if(ntt_done) begin read_index<=0;state<=S_READ_REQ;end
                S_READ_REQ: state<=S_READ_WAIT;
                S_READ_WAIT: state<=S_READ_LOAD;
                S_READ_LOAD: begin if(read_index==255) begin
                    if(poly_index==2) state<=S_CODEC_START;
                    else begin poly_index<=poly_index+1'b1;state<=S_PAIR_INIT;end end
                    else begin read_index<=read_index+1'b1;state<=S_READ_REQ;end end
                S_CODEC_START: state<=S_CODEC_WAIT;
                S_CODEC_WAIT: if(codec_done||(!runtime_prf_ok_q&&runtime_valid_q)) begin
                    busy<=0;done<=1;pass<=codec_done&&codec_pass&&(codec_loaded_coeffs==768)&&runtime_prf_ok_q;
                    status<=(codec_done&&codec_pass&&(codec_loaded_coeffs==768)&&runtime_prf_ok_q)?8'hFF:8'h00;
                    // A rejected no-key request must not repeat stale
                    // ciphertext fingerprints from a preceding KAT.
                    ciphertext_digest<=codec_done ? codec_digest_a : 32'd0;
                    audit_digest<=codec_done ? codec_digest_b : 32'd0;
                    state<=S_IDLE;end
                default: begin busy<=0;done<=1;pass<=0;status<=0;state<=S_IDLE;end
            endcase
        end
    end
endmodule
