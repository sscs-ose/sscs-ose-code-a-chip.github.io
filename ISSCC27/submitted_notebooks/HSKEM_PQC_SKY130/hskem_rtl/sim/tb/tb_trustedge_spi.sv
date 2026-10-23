`timescale 1ns/1ps

// Integrated TB: SPI master -> trustedge_top.
// Covers STATUS, Kyber runtime self-test, PUF enroll/verify, and OTA.
`ifdef TRUSTEDGE_ASIC_SRAM
`define TB_SPI_MATRIX_EVEN(_idx) dut.u_mlkem512_kpke_partial.u_matrix_mac.u_matrix_even_sram.u_model.mem[_idx]
`define TB_SPI_MATRIX_ODD(_idx) dut.u_mlkem512_kpke_partial.u_matrix_mac.u_matrix_odd_sram.u_model.mem[_idx]
`define TB_SPI_EKPKE_PAIR(_idx) dut.u_mlkem512_kpke_partial.u_matrix_mac.u_ekpke_pair_sram.u_model.mem[_idx]
`define TB_SPI_NOISE_EVEN(_idx) dut.u_mlkem512_encaps_partial.u_noise_even_sram.u_model.mem[_idx]
`define TB_SPI_NOISE_ODD(_idx) dut.u_mlkem512_encaps_partial.u_noise_odd_sram.u_model.mem[_idx]
`define TB_SPI_DECODED_COEFF(_idx) dut.u_mlkem512_encaps_partial.u_codec.u_decoded_coeff_sram.u_model.mem[_idx]
`else
`define TB_SPI_MATRIX_EVEN(_idx) dut.u_mlkem512_kpke_partial.u_matrix_mac.matrix_even_ram[_idx]
`define TB_SPI_MATRIX_ODD(_idx) dut.u_mlkem512_kpke_partial.u_matrix_mac.matrix_odd_ram[_idx]
`define TB_SPI_EKPKE_PAIR(_idx) dut.u_mlkem512_kpke_partial.u_matrix_mac.ekpke_pair_ram[_idx]
`define TB_SPI_NOISE_EVEN(_idx) dut.u_mlkem512_encaps_partial.noise_even_ram[_idx]
`define TB_SPI_NOISE_ODD(_idx) dut.u_mlkem512_encaps_partial.noise_odd_ram[_idx]
`define TB_SPI_DECODED_COEFF(_idx) dut.u_mlkem512_encaps_partial.u_codec.decoded_coeff_ram[_idx]
`endif

`ifdef TRUSTEDGE_ASIC_SKY130_RESET_CELLS
// Functional models for the two SKY130 cells instantiated only by the ASIC
// reset-distribution profile.  Physical/timing behavior remains a mapped-flow
// responsibility; these models let the architectural regression exercise the
// same preprocessor branch without pulling a PDK simulation library into it.
module sky130_fd_sc_hd__inv_1 (
    input  wire A,
    output wire Y
);
    assign Y = ~A;
endmodule

module sky130_fd_sc_hd__and2_1 (
    input  wire A,
    input  wire B,
    output wire X
);
    assign X = A & B;
endmodule
`endif

module tb_trustedge_spi;
`ifdef TRUSTEDGE_ASIC_KECCAK_SERIAL_ROUND
    localparam TB_KECCAK_SERIAL_ROUND = 1'b1;
`else
    localparam TB_KECCAK_SERIAL_ROUND = 1'b0;
`endif
`ifdef TRUSTEDGE_ASIC_RESET_BRANCHES
    localparam TB_ASIC_RESET_BRANCHES = 1'b1;
`else
    localparam TB_ASIC_RESET_BRANCHES = 1'b0;
`endif
    // Seven cycles per Keccak round add six clocks for each of 24 rounds.
    // Keep the cycle oracle derived from independently counted sponge
    // permutations instead of copying a measured serial-round cycle value.
    localparam integer KECCAK_EXTRA_CYCLES_PER_PERM =
        TB_KECCAK_SERIAL_ROUND ? 144 : 0;
    localparam integer KPKE_SHARED_PERMUTATIONS = 36;
    localparam integer RUNTIME_ENCRYPT_SHARED_PERMUTATIONS = 7;
    localparam integer ENCAPS_SHARED_PERMUTATIONS = 20;
    localparam integer DECAPS_SHARED_PERMUTATIONS = 26;
`ifdef TRUSTEDGE_ASIC_SRAM
    localparam [15:0] EXPECTED_KYBER_CYCLES = 16'd6789;
    localparam [15:0] EXPECTED_MLKEM512_CYCLES = 16'd29211;
    localparam [15:0] EXPECTED_KPKE_CYCLES = 16'd42339 +
        KPKE_SHARED_PERMUTATIONS * KECCAK_EXTRA_CYCLES_PER_PERM;
    localparam [15:0] EXPECTED_CODEC_CYCLES = 16'd40336;
    localparam [15:0] EXPECTED_RUNTIME_ENCRYPT_CYCLES = 16'd59409 +
        RUNTIME_ENCRYPT_SHARED_PERMUTATIONS *
        KECCAK_EXTRA_CYCLES_PER_PERM;
    localparam integer EXPECTED_ENCAPS_CYCLES_RAW = 64652 +
        ENCAPS_SHARED_PERMUTATIONS * KECCAK_EXTRA_CYCLES_PER_PERM;
    localparam [15:0] EXPECTED_ENCAPS_CYCLES =
        (EXPECTED_ENCAPS_CYCLES_RAW > 65535) ? 16'hFFFF :
        EXPECTED_ENCAPS_CYCLES_RAW;
    localparam integer MLKEM512_WAIT_CYCLES = 34000;
    localparam integer MLKEM_STAGE_WAIT_CYCLES = 50000;
`else
    localparam [15:0] EXPECTED_KYBER_CYCLES = 16'd4997;
    localparam [15:0] EXPECTED_MLKEM512_CYCLES = 16'd22043;
    localparam [15:0] EXPECTED_KPKE_CYCLES = 16'd35171;
    localparam [15:0] EXPECTED_CODEC_CYCLES = 16'd34960;
    localparam [15:0] EXPECTED_RUNTIME_ENCRYPT_CYCLES = 16'd50449;
    localparam [15:0] EXPECTED_ENCAPS_CYCLES = 16'd55692;
    localparam integer MLKEM512_WAIT_CYCLES = 22000;
    localparam integer MLKEM_STAGE_WAIT_CYCLES = 40000;
`endif
    reg clk, rst_n;
    reg spi_cs_n, spi_sck, spi_mosi;
    wire spi_miso;
    wire spi_irq;
    reg sig_valid;
    reg provision_enable;

    wire enrolled, verify_ok, ota_ok, ota_deny;
    wire kyber_done, kyber_pass;
    wire [31:0] device_id;
    wire crypto_zeroize;

    integer errors;
    integer i;
    integer decaps_running_cycles;
    integer decaps_last_cycles;
    integer decaps_valid_latency;
    integer decaps_invalid_latency;
    integer decaps_valid_permutations;
    integer decaps_invalid_permutations;
    reg     decaps_busy_q;
    integer shared_permutation_count;
    integer shared_permutation_before;
    integer shared_permutation_delta;
    integer bound_poly [0:2][0:255];
    reg [7:0] bound_ct [0:767];
    reg [31:0] bound_oracle_a, bound_oracle_b;

    trustedge_top #(
        .ASIC_KECCAK_SERIAL_ROUND(TB_KECCAK_SERIAL_ROUND),
        .ASIC_RESET_BRANCHES(TB_ASIC_RESET_BRANCHES)
    ) dut (
        .clk(clk), .rst_n(rst_n),
        .spi_cs_n(spi_cs_n), .spi_sck(spi_sck),
        .spi_mosi(spi_mosi), .spi_miso(spi_miso),
        .spi_irq(spi_irq),
        .sig_valid(sig_valid),
        .provision_enable(provision_enable),
        .sdm_transport_ready(1'b1),
        .sdm_transport_error(8'h00),
        .sdm_chip_id(64'h0123_4567_89AB_CDEF),
        .sdm_crypto_enabled(1'b1),
        .sdm_crypto_mem_ready(1'b1),
        .sdm_crypto_mem_error(8'h00),
        .crypto_zeroize(crypto_zeroize),
        .ota_commit_ok(ota_ok), .ota_commit_deny(ota_deny),
        .enrolled(enrolled), .verify_ok(verify_ok), .device_id(device_id),
        .kyber_done(kyber_done), .kyber_pass(kyber_pass)
    );

    initial clk = 0;
    always #5 clk = ~clk;

    // The physical candidate is allowed to split fanout, never semantics.
    // This oracle covers power-on reset and every command-generated reset
    // exercised by the integrated SPI regression.
    always @(posedge clk) begin
        if (TB_ASIC_RESET_BRANCHES &&
            ((rst_n === 1'b0) || (rst_n === 1'b1)) &&
            ((dut.reset_pulse === 1'b0) || (dut.reset_pulse === 1'b1)) &&
            ({dut.core_rst_n_top, dut.core_rst_n_entropy,
              dut.core_rst_n_security, dut.core_rst_n_vault,
              dut.core_rst_n_hmac, dut.core_rst_n_sponge,
              dut.core_rst_n_mlkem_a, dut.core_rst_n_mlkem_b} !==
             {8{rst_n & ~dut.reset_pulse}})) begin
            $display("  FAIL reset-branch equivalence: branches=%b expected=%b",
                     {dut.core_rst_n_top, dut.core_rst_n_entropy,
                      dut.core_rst_n_security, dut.core_rst_n_vault,
                      dut.core_rst_n_hmac, dut.core_rst_n_sponge,
                      dut.core_rst_n_mlkem_a, dut.core_rst_n_mlkem_b},
                     rst_n & ~dut.reset_pulse);
            $fatal(1, "ASIC reset branches changed reset semantics");
        end
    end

    // The response cycle field saturates at 16'hFFFF.  Measure the internal
    // Decaps busy interval in the TB as a U1 control-latency property instead
    // of treating the saturated public counter as an equality proof.
    always @(posedge clk) begin
        if (!rst_n) begin
            decaps_running_cycles = 0;
            decaps_last_cycles = 0;
            decaps_busy_q = 1'b0;
            shared_permutation_count = 0;
        end else begin
            if (dut.u_shared_mlkem_sponge.permutation_start)
                shared_permutation_count = shared_permutation_count + 1;
            if (!decaps_busy_q && dut.u_mlkem512_decaps_partial.busy)
                decaps_running_cycles = 1;
            else if (dut.u_mlkem512_decaps_partial.busy)
                decaps_running_cycles = decaps_running_cycles + 1;
            if (decaps_busy_q && !dut.u_mlkem512_decaps_partial.busy)
                decaps_last_cycles = decaps_running_cycles;
            decaps_busy_q = dut.u_mlkem512_decaps_partial.busy;
        end
    end

    function [15:0] crc16_byte(input [15:0] c, input [7:0] d);
        integer i;
        reg [15:0] x;
        begin
            x = c ^ {d, 8'h00};
            for (i = 0; i < 8; i = i + 1)
                x = x[15] ? ({x[14:0], 1'b0} ^ 16'h1021) : {x[14:0], 1'b0};
            crc16_byte = x;
        end
    endfunction

    // Independent arithmetic/packing oracle for the bound-key path.  It
    // reads only the completed KeyGen RAM images and the completed Encrypt
    // PRF RAM image; it does not call the Encrypt datapath combinational
    // operands, multiplier, inverse-NTT engine, or ciphertext codec.
    function integer bound_bitrev7(input integer x);
        integer b;
        begin
            bound_bitrev7 = 0;
            for (b = 0; b < 7; b = b + 1)
                bound_bitrev7 = bound_bitrev7 | (((x >> b) & 1) << (6-b));
        end
    endfunction
    function integer bound_pow_mod(input integer base_in, input integer exp_in);
        integer base, expn, result;
        begin
            base = base_in; expn = exp_in; result = 1;
            while (expn > 0) begin
                if (expn & 1) result = (result * base) % 3329;
                base = (base * base) % 3329;
                expn = expn >> 1;
            end
            bound_pow_mod = result;
        end
    endfunction
    function integer bound_zeta(input integer idx);
        begin bound_zeta = bound_pow_mod(17, bound_bitrev7(idx)); end
    endfunction
    function integer bound_compress(input integer value, input integer bits);
        integer mask;
        begin
            mask = (1 << bits) - 1;
            bound_compress = (((value << bits) + 1664) / 3329) & mask;
        end
    endfunction
    task bound_inverse_ntt(input integer which_poly);
        integer len, start_pos, j, k, z, temp, lo, hi;
        begin
            k = 127;
            for (len = 2; len <= 128; len = len << 1)
                for (start_pos = 0; start_pos < 256;
                     start_pos = start_pos + (len << 1)) begin
                    z = bound_zeta(k); k = k - 1;
                    for (j = start_pos; j < start_pos + len; j = j + 1) begin
                        temp = bound_poly[which_poly][j];
                        lo = (temp + bound_poly[which_poly][j+len]) % 3329;
                        hi = (z * (bound_poly[which_poly][j+len] + 3329 - temp)) % 3329;
                        bound_poly[which_poly][j] = lo;
                        bound_poly[which_poly][j+len] = hi;
                    end
                end
            for (j = 0; j < 256; j = j + 1)
                bound_poly[which_poly][j] = (bound_poly[which_poly][j] * 3303) % 3329;
        end
    endtask
    task build_bound_encrypt_oracle(input [255:0] message_in);
        integer p, coeff, pair, col, gamma, a0, a1, b0, b1;
        integer c0, c1, value0, noise_value, ram_addr, byte_index, sub;
        integer msg_bit;
        reg [23:0] key_pair;
        reg [39:0] packed40;
        reg [9:0] compressed10;
        begin
            for (p = 0; p < 3; p = p + 1) begin
                for (coeff = 0; coeff < 256; coeff = coeff + 1)
                    bound_poly[p][coeff] = 0;
                for (pair = 0; pair < 128; pair = pair + 1) begin
                    gamma = bound_zeta(64 + pair/2);
                    if (pair & 1) gamma = 3329 - gamma;
                    c0 = 0; c1 = 0;
                    for (col = 0; col < 2; col = col + 1) begin
                        if (p < 2) begin
                            // Encrypt consumes A^T: KeyGen RAM is row-major.
                            ram_addr = col*256 + p*128 + pair;
                            a0 = `TB_SPI_MATRIX_EVEN(ram_addr);
                            a1 = `TB_SPI_MATRIX_ODD(ram_addr);
                        end else begin
                            key_pair = `TB_SPI_EKPKE_PAIR(col*128 + pair);
                            a0 = {key_pair[11:8], key_pair[7:0]};
                            a1 = key_pair[23:12];
                        end
                        ram_addr = col*128 + pair;
                        b0 = `TB_SPI_NOISE_EVEN(ram_addr);
                        b1 = `TB_SPI_NOISE_ODD(ram_addr);
                        c0 = (c0 + (a0*b0) % 3329 + (((a1*b1) % 3329) * gamma) % 3329) % 3329;
                        c1 = (c1 + a0*b1 + a1*b0) % 3329;
                    end
                    bound_poly[p][pair*2] = c0;
                    bound_poly[p][pair*2+1] = c1;
                end
                bound_inverse_ntt(p);
                for (coeff = 0; coeff < 256; coeff = coeff + 1) begin
                    ram_addr = (p+2)*128 + coeff/2;
                    noise_value = (coeff & 1) ?
                        `TB_SPI_NOISE_ODD(ram_addr) :
                        `TB_SPI_NOISE_EVEN(ram_addr);
                    msg_bit = (p == 2) && message_in[coeff];
                    value0 = bound_poly[p][coeff] + noise_value + (msg_bit ? 1665 : 0);
                    while (value0 >= 3329) value0 = value0 - 3329;
                    bound_poly[p][coeff] = value0;
                end
            end
            byte_index = 0;
            for (p = 0; p < 2; p = p + 1)
                for (coeff = 0; coeff < 256; coeff = coeff + 4) begin
                    packed40 = 40'd0;
                    for (sub = 0; sub < 4; sub = sub + 1) begin
                        compressed10 = bound_compress(bound_poly[p][coeff+sub], 10);
                        packed40 = packed40 | ({30'd0, compressed10} << (10*sub));
                    end
                    for (sub = 0; sub < 5; sub = sub + 1) begin
                        bound_ct[byte_index] = packed40 >> (8*sub);
                        byte_index = byte_index + 1;
                    end
                end
            for (coeff = 0; coeff < 256; coeff = coeff + 2) begin
                bound_ct[byte_index] = bound_compress(bound_poly[2][coeff], 4) |
                    (bound_compress(bound_poly[2][coeff+1], 4) << 4);
                byte_index = byte_index + 1;
            end
            bound_oracle_a = 32'h43543131; bound_oracle_b = 32'h4B504B45;
            for (coeff = 0; coeff < 768; coeff = coeff + 1) begin
                bound_oracle_a = {bound_oracle_a[30:0], bound_oracle_a[31]} ^ bound_ct[coeff];
                bound_oracle_b = {bound_oracle_b[26:0], bound_oracle_b[31:27]} + bound_ct[coeff];
            end
        end
    endtask

    task spi_delay;
        repeat (8) @(posedge clk);
    endtask

    task spi_xfer_mlkem_runtime_encrypt(
        input [15:0] payload_len,
        input [255:0] message_in,
        input [255:0] coins_in,
        output response_valid_out,
        output ok_out,
        output [7:0] status_out,
        output [31:0] digest_a_out,
        output [31:0] digest_b_out,
        output [15:0] cycles_out
    );
        reg [15:0] crc;
        reg [15:0] rx_crc;
        integer i;
        integer j;
        reg [7:0] payload_byte;
        reg [7:0] rb;
        reg [7:0] rxbuf [0:47];
        begin
            response_valid_out = 1'b0; ok_out = 1'b0;
            status_out = 8'd0; digest_a_out = 32'd0;
            digest_b_out = 32'd0; cycles_out = 16'd0;
            crc = 16'hFFFF;
            spi_cs_n = 1'b0;
            spi_delay;
            spi_write_byte(8'hA5);
            spi_write_byte(8'h16); crc = crc16_byte(crc,8'h16);
            spi_write_byte(payload_len[15:8]); crc=crc16_byte(crc,payload_len[15:8]);
            spi_write_byte(payload_len[7:0]); crc=crc16_byte(crc,payload_len[7:0]);
            for (i=0;i<payload_len;i=i+1) begin
                payload_byte = (i<32) ? message_in[i*8 +: 8] :
                               (i<64) ? coins_in[(i-32)*8 +: 8] : 8'd0;
                spi_write_byte(payload_byte); crc=crc16_byte(crc,payload_byte);
            end
            spi_write_byte(crc[15:8]); spi_write_byte(crc[7:0]);
            if (payload_len == 16'd32)
                repeat (180000) @(posedge clk);
            else
                repeat (70000) @(posedge clk);
            for (i=0;i<48;i=i+1) begin spi_read_byte(rb);rxbuf[i]=rb;end
            for (i=0;i<31;i=i+1) begin
                if(rxbuf[i]===8'hA5 && rxbuf[i+1]===8'h17 &&
                   rxbuf[i+2]===8'd0 && rxbuf[i+3]===8'd12) begin
                    crc=16'hFFFF;
                    for(j=1;j<16;j=j+1) crc=crc16_byte(crc,rxbuf[i+j]);
                    rx_crc={rxbuf[i+16],rxbuf[i+17]};
                    if(crc===rx_crc) begin
                        response_valid_out=1'b1;ok_out=(rxbuf[i+4]==8'd1);
                        status_out=rxbuf[i+5];
                        digest_a_out={rxbuf[i+6],rxbuf[i+7],rxbuf[i+8],rxbuf[i+9]};
                        digest_b_out={rxbuf[i+10],rxbuf[i+11],rxbuf[i+12],rxbuf[i+13]};
                        cycles_out={rxbuf[i+14],rxbuf[i+15]};
                    end
                end
            end
            spi_cs_n=1'b1;repeat(20)@(posedge clk);
        end
    endtask

    task spi_xfer_mlkem_runtime_seed(
        input [15:0] seed_len,
        input [255:0] seed_d,
        input [255:0] seed_z,
        input [7:0] seed_k,
        output response_valid_out,
        output ok_out,
        output [7:0] status_out,
        output [31:0] digest_a_out,
        output [31:0] digest_b_out,
        output [15:0] cycles_out
    );
        reg [15:0] crc;
        reg [15:0] rx_crc;
        integer i;
        integer j;
        reg [7:0] payload_byte;
        reg [7:0] rb;
        reg [7:0] rxbuf [0:47];
        begin
            response_valid_out = 1'b0;
            ok_out = 1'b0;
            status_out = 8'd0;
            digest_a_out = 32'd0;
            digest_b_out = 32'd0;
            cycles_out = 16'd0;
            crc = 16'hFFFF;
            spi_cs_n = 1'b0;
            spi_delay;

            spi_write_byte(8'hA5);
            spi_write_byte(8'h14);
            crc = crc16_byte(crc, 8'h14);
            spi_write_byte(seed_len[15:8]);
            crc = crc16_byte(crc, seed_len[15:8]);
            spi_write_byte(seed_len[7:0]);
            crc = crc16_byte(crc, seed_len[7:0]);
            for (i = 0; i < seed_len; i = i + 1) begin
                payload_byte = (i < 32) ? seed_d[i*8 +: 8] :
                               (i < 64) ? seed_z[(i-32)*8 +: 8] :
                               (i == 64) ? seed_k : 8'd0;
                spi_write_byte(payload_byte);
                crc = crc16_byte(crc, payload_byte);
            end
            spi_write_byte(crc[15:8]);
            spi_write_byte(crc[7:0]);

            repeat (MLKEM_STAGE_WAIT_CYCLES) @(posedge clk);
            for (i = 0; i < 48; i = i + 1) begin
                spi_read_byte(rb);
                rxbuf[i] = rb;
            end

            for (i = 0; i < 31; i = i + 1) begin
                if (rxbuf[i] === 8'hA5 && rxbuf[i + 1] === 8'h15 &&
                    rxbuf[i + 2] === 8'd0 && rxbuf[i + 3] === 8'd12) begin
                    crc = 16'hFFFF;
                    for (j = 1; j < 16; j = j + 1)
                        crc = crc16_byte(crc, rxbuf[i + j]);
                    rx_crc = {rxbuf[i + 16], rxbuf[i + 17]};
                    if (crc === rx_crc) begin
                        response_valid_out = 1'b1;
                        ok_out = (rxbuf[i + 4] == 8'd1);
                        status_out = rxbuf[i + 5];
                        digest_a_out = {rxbuf[i + 6], rxbuf[i + 7],
                                        rxbuf[i + 8], rxbuf[i + 9]};
                        digest_b_out = {rxbuf[i + 10], rxbuf[i + 11],
                                        rxbuf[i + 12], rxbuf[i + 13]};
                        cycles_out = {rxbuf[i + 14], rxbuf[i + 15]};
                    end
                end
            end

            spi_cs_n = 1'b1;
            repeat (20) @(posedge clk);
        end
    endtask

    task spi_xfer_hsm_ext(
        input [7:0] api,
        input [7:0] subcmd,
        input [7:0] flags,
        input [31:0] counter,
        input [7:0] data_len,
        input [255:0] data_in,
        output valid_out,
        output [7:0] response_len_out,
        output [255:0] data_out
    );
        reg [15:0] crc;
        reg [15:0] rx_crc;
        integer i;
        integer j;
        reg [7:0] rb;
        reg [7:0] rxbuf [0:63];
        reg [7:0] response_len;
        begin
            valid_out = 1'b0;
            response_len_out = 8'd0;
            data_out = 256'd0;
            crc = 16'hFFFF;
            spi_cs_n = 1'b0;
            spi_delay;

            spi_write_byte(8'hA5);
            spi_write_byte(8'h3A);
            crc = crc16_byte(crc, 8'h3A);
            spi_write_byte(8'd0);
            crc = crc16_byte(crc, 8'd0);
            spi_write_byte(data_len + 8'd7);
            crc = crc16_byte(crc, data_len + 8'd7);
            spi_write_byte(api);     crc = crc16_byte(crc, api);
            spi_write_byte(subcmd);  crc = crc16_byte(crc, subcmd);
            spi_write_byte(flags);   crc = crc16_byte(crc, flags);
            spi_write_byte(counter[31:24]); crc = crc16_byte(crc, counter[31:24]);
            spi_write_byte(counter[23:16]); crc = crc16_byte(crc, counter[23:16]);
            spi_write_byte(counter[15:8]);  crc = crc16_byte(crc, counter[15:8]);
            spi_write_byte(counter[7:0]);   crc = crc16_byte(crc, counter[7:0]);
            for (i = 0; i < data_len; i = i + 1) begin
                spi_write_byte(data_in[255-i*8 -: 8]);
                crc = crc16_byte(crc, data_in[255-i*8 -: 8]);
            end
            spi_write_byte(crc[15:8]);
            spi_write_byte(crc[7:0]);

            if (subcmd == 8'h40 &&
                (data_in[255:248] == 8'h02 ||
                 data_in[255:248] == 8'h05))
                repeat (250000) @(posedge clk);
            else if (subcmd == 8'h40 && data_len == 8'd2)
                repeat (70000) @(posedge clk);
            else if (subcmd == 8'h37)
                repeat (1200) @(posedge clk);
            else
                repeat (500) @(posedge clk);
            for (i = 0; i < 64; i = i + 1) begin
                spi_read_byte(rb);
                rxbuf[i] = rb;
            end

            for (i = 0; i < 30; i = i + 1) begin
                response_len = rxbuf[i + 3];
                if (rxbuf[i] === 8'hA5 && rxbuf[i + 1] === 8'h3B &&
                    rxbuf[i + 2] === 8'd0 && response_len <= 8'd32 &&
                    i + response_len + 5 < 64) begin
                    crc = 16'hFFFF;
                    for (j = 1; j < 4 + response_len; j = j + 1)
                        crc = crc16_byte(crc, rxbuf[i + j]);
                    rx_crc = {rxbuf[i + 4 + response_len],
                              rxbuf[i + 5 + response_len]};
                    if (crc === rx_crc) begin
                        valid_out = 1'b1;
                        response_len_out = response_len;
                        for (j = 0; j < 32; j = j + 1)
                            data_out[255-j*8 -: 8] =
                                (j < response_len) ? rxbuf[i + 4 + j] : 8'd0;
                    end
                end
            end

            if (!valid_out) begin
                $write("  HSM_EXT subcmd=%02h RX:", subcmd);
                for (i = 0; i < 36; i = i + 1)
                    $write(" %02h", rxbuf[i]);
                $display("");
            end

            spi_cs_n = 1'b1;
            repeat (20) @(posedge clk);
        end
    endtask

    task spi_write_bit(input b);
        begin
            spi_mosi = b;
            spi_delay;
            spi_sck  = 1'b1;
            spi_delay;
            spi_sck  = 1'b0;
            spi_delay;
        end
    endtask

    task spi_read_bit(output b);
        begin
            spi_delay;
            spi_sck = 1'b1;
            spi_delay;
            b = spi_miso;
            spi_sck = 1'b0;
            spi_delay;
        end
    endtask

    task spi_write_byte(input [7:0] data);
        integer i;
        begin
            for (i = 7; i >= 0; i = i - 1)
                spi_write_bit(data[i]);
        end
    endtask

    task spi_read_byte(output [7:0] data);
        integer i;
        reg bitv;
        begin
            data = 8'h00;
            for (i = 7; i >= 0; i = i - 1) begin
                spi_read_bit(bitv);
                data[i] = bitv;
            end
        end
    endtask

    task spi_xfer_frame(
        input [7:0]  cmd,
        input [15:0] plen,
        input [7:0]  p0, input [7:0] p1, input [7:0] p2, input [7:0] p3, input [7:0] p4,
        input integer rx_count,
        output [7:0] status_out,
        output [7:0] verify_fail_out
    );
        reg [15:0] crc;
        integer i;
        reg [7:0] rb;
        reg [7:0] rxbuf [0:63];
        begin
            status_out = 8'h00;
            verify_fail_out = 8'h00;
            crc = 16'hFFFF;
            spi_cs_n = 1'b0;
            spi_delay;

            spi_write_byte(8'hA5);
            spi_write_byte(cmd);
            crc = crc16_byte(crc, cmd);
            spi_write_byte(plen[15:8]);
            crc = crc16_byte(crc, plen[15:8]);
            spi_write_byte(plen[7:0]);
            crc = crc16_byte(crc, plen[7:0]);
            if (plen >= 1) begin spi_write_byte(p0); crc = crc16_byte(crc, p0); end
            if (plen >= 2) begin spi_write_byte(p1); crc = crc16_byte(crc, p1); end
            if (plen >= 3) begin spi_write_byte(p2); crc = crc16_byte(crc, p2); end
            if (plen >= 4) begin spi_write_byte(p3); crc = crc16_byte(crc, p3); end
            if (plen >= 5) begin spi_write_byte(p4); crc = crc16_byte(crc, p4); end
            spi_write_byte(crc[15:8]);
            spi_write_byte(crc[7:0]);

            repeat (400) @(posedge clk);

            for (i = 0; i < rx_count; i = i + 1) begin
                spi_read_byte(rb);
                rxbuf[i] = rb;
            end

            if (rx_count >= 6) begin
                for (i = 0; i < rx_count - 5; i = i + 1) begin
                    if (rxbuf[i] === 8'hA5 && rxbuf[i + 1] === 8'hF0) begin
                        status_out = rxbuf[i + 4];
                        verify_fail_out = rxbuf[i + 5];
                    end
                end
            end

            spi_cs_n = 1'b1;
            repeat (20) @(posedge clk);
        end
    endtask

    task spi_xfer_kyber(
        output ok_out,
        output [31:0] digest_out,
        output [15:0] cycles_out
    );
        reg [15:0] crc;
        reg [15:0] rx_crc;
        integer i;
        integer j;
        reg [7:0] rb;
        reg [7:0] rxbuf [0:31];
        begin
            ok_out = 1'b0;
            digest_out = 32'd0;
            cycles_out = 16'd0;
            crc = 16'hFFFF;

            spi_cs_n = 1'b0;
            spi_delay;

            spi_write_byte(8'hA5);
            spi_write_byte(8'h10);
            crc = crc16_byte(crc, 8'h10);
            spi_write_byte(8'd0);
            crc = crc16_byte(crc, 8'd0);
            spi_write_byte(8'd0);
            crc = crc16_byte(crc, 8'd0);
            spi_write_byte(crc[15:8]);
            spi_write_byte(crc[7:0]);

            repeat (12000) @(posedge clk);

            for (i = 0; i < 32; i = i + 1) begin
                spi_read_byte(rb);
                rxbuf[i] = rb;
            end

            for (i = 0; i < 20; i = i + 1) begin
                if (rxbuf[i] === 8'hA5 &&
                    rxbuf[i + 1] === 8'h11 &&
                    rxbuf[i + 2] === 8'd0 &&
                    rxbuf[i + 3] === 8'd7) begin
                    crc = 16'hFFFF;
                    for (j = 1; j < 11; j = j + 1)
                        crc = crc16_byte(crc, rxbuf[i + j]);
                    rx_crc = {rxbuf[i + 11], rxbuf[i + 12]};
                    if (crc === rx_crc) begin
                        ok_out = (rxbuf[i + 4] == 8'd1);
                        digest_out = {rxbuf[i + 5], rxbuf[i + 6],
                                      rxbuf[i + 7], rxbuf[i + 8]};
                        cycles_out = {rxbuf[i + 9], rxbuf[i + 10]};
                    end
                end
            end

            if (!ok_out) begin
                $write("  KYBER RX:");
                for (i = 0; i < 16; i = i + 1)
                    $write(" %02h", rxbuf[i]);
                $display("");
            end

            spi_cs_n = 1'b1;
            repeat (20) @(posedge clk);
        end
    endtask

    task spi_xfer_mlkem512(
        output ok_out,
        output [7:0] status_out,
        output [31:0] partial_digest_out,
        output [31:0] polyvec_digest_out,
        output [15:0] cycles_out
    );
        reg [15:0] crc;
        reg [15:0] rx_crc;
        integer i;
        integer j;
        reg [7:0] rb;
        reg [7:0] rxbuf [0:47];
        begin
            ok_out = 1'b0;
            status_out = 8'd0;
            partial_digest_out = 32'd0;
            polyvec_digest_out = 32'd0;
            cycles_out = 16'd0;
            crc = 16'hFFFF;

            spi_cs_n = 1'b0;
            spi_delay;

            spi_write_byte(8'hA5);
            spi_write_byte(8'h12);
            crc = crc16_byte(crc, 8'h12);
            spi_write_byte(8'd0);
            crc = crc16_byte(crc, 8'd0);
            spi_write_byte(8'd0);
            crc = crc16_byte(crc, 8'd0);
            spi_write_byte(crc[15:8]);
            spi_write_byte(crc[7:0]);

            repeat (MLKEM512_WAIT_CYCLES) @(posedge clk);

            for (i = 0; i < 48; i = i + 1) begin
                spi_read_byte(rb);
                rxbuf[i] = rb;
            end

            for (i = 0; i < 31; i = i + 1) begin
                if (rxbuf[i] === 8'hA5 &&
                    rxbuf[i + 1] === 8'h13 &&
                    rxbuf[i + 2] === 8'd0 &&
                    rxbuf[i + 3] === 8'd12) begin
                    crc = 16'hFFFF;
                    for (j = 1; j < 16; j = j + 1)
                        crc = crc16_byte(crc, rxbuf[i + j]);
                    rx_crc = {rxbuf[i + 16], rxbuf[i + 17]};
                    if (crc === rx_crc) begin
                        ok_out = (rxbuf[i + 4] == 8'd1);
                        status_out = rxbuf[i + 5];
                        partial_digest_out = {rxbuf[i + 6], rxbuf[i + 7],
                                              rxbuf[i + 8], rxbuf[i + 9]};
                        polyvec_digest_out = {rxbuf[i + 10], rxbuf[i + 11],
                                             rxbuf[i + 12], rxbuf[i + 13]};
                        cycles_out = {rxbuf[i + 14], rxbuf[i + 15]};
                    end
                end
            end

            if (!ok_out) begin
                $write("  MLKEM512 RX:");
                for (i = 0; i < 24; i = i + 1)
                    $write(" %02h", rxbuf[i]);
                $display("");
            end

            spi_cs_n = 1'b1;
            repeat (20) @(posedge clk);
        end
    endtask

    task spi_xfer_mlkem_stage(
        input [7:0] req_cmd,
        input [7:0] resp_cmd,
        output ok_out,
        output [7:0] status_out,
        output [31:0] digest_a_out,
        output [31:0] digest_b_out,
        output [15:0] cycles_out
    );
        reg [15:0] crc;
        reg [15:0] rx_crc;
        integer i;
        integer j;
        reg [7:0] rb;
        reg [7:0] rxbuf [0:47];
        begin
            ok_out = 1'b0;
            status_out = 8'd0;
            digest_a_out = 32'd0;
            digest_b_out = 32'd0;
            cycles_out = 16'd0;
            crc = 16'hFFFF;

            spi_cs_n = 1'b0;
            spi_delay;

            spi_write_byte(8'hA5);
            spi_write_byte(req_cmd);
            crc = crc16_byte(crc, req_cmd);
            spi_write_byte(8'd0);
            crc = crc16_byte(crc, 8'd0);
            spi_write_byte(8'd0);
            crc = crc16_byte(crc, 8'd0);
            spi_write_byte(crc[15:8]);
            spi_write_byte(crc[7:0]);

            // Keep an architecture-specific bounded margin so a missing
            // completion still fails fast.  ASIC 1RW NTT accesses are
            // intentionally serialized and therefore take longer.
            repeat ((req_cmd == 8'h18) ? 120000 :
                    MLKEM_STAGE_WAIT_CYCLES) @(posedge clk);

            for (i = 0; i < 48; i = i + 1) begin
                spi_read_byte(rb);
                rxbuf[i] = rb;
            end

            for (i = 0; i < 31; i = i + 1) begin
                if (rxbuf[i] === 8'hA5 &&
                    rxbuf[i + 1] === resp_cmd &&
                    rxbuf[i + 2] === 8'd0 &&
                    rxbuf[i + 3] === 8'd12) begin
                    crc = 16'hFFFF;
                    for (j = 1; j < 16; j = j + 1)
                        crc = crc16_byte(crc, rxbuf[i + j]);
                    rx_crc = {rxbuf[i + 16], rxbuf[i + 17]};
                    if (crc === rx_crc) begin
                        ok_out = (rxbuf[i + 4] == 8'd1);
                        status_out = rxbuf[i + 5];
                        digest_a_out = {rxbuf[i + 6], rxbuf[i + 7],
                                        rxbuf[i + 8], rxbuf[i + 9]};
                        digest_b_out = {rxbuf[i + 10], rxbuf[i + 11],
                                        rxbuf[i + 12], rxbuf[i + 13]};
                        cycles_out = {rxbuf[i + 14], rxbuf[i + 15]};
                    end
                end
            end

            if (!ok_out) begin
                $write("  MLKEM_STAGE cmd=%02h RX:", req_cmd);
                for (i = 0; i < 24; i = i + 1)
                    $write(" %02h", rxbuf[i]);
                $display("");
            end

            spi_cs_n = 1'b1;
            repeat (20) @(posedge clk);
        end
    endtask

    task spi_xfer_hsm(
        input [7:0] req_cmd,
        input [7:0] resp_cmd,
        input       has_arg,
        input [7:0] arg,
        output      valid_out,
        output [63:0] data_out
    );
        reg [15:0] crc;
        reg [15:0] rx_crc;
        integer i;
        integer j;
        reg [7:0] rb;
        reg [7:0] rxbuf [0:31];
        begin
            valid_out = 1'b0;
            data_out = 64'd0;
            crc = 16'hFFFF;
            spi_cs_n = 1'b0;
            spi_delay;

            spi_write_byte(8'hA5);
            spi_write_byte(req_cmd);
            crc = crc16_byte(crc, req_cmd);
            spi_write_byte(8'd0);
            crc = crc16_byte(crc, 8'd0);
            spi_write_byte(has_arg ? 8'd1 : 8'd0);
            crc = crc16_byte(crc, has_arg ? 8'd1 : 8'd0);
            if (has_arg) begin
                spi_write_byte(arg);
                crc = crc16_byte(crc, arg);
            end
            spi_write_byte(crc[15:8]);
            spi_write_byte(crc[7:0]);

            repeat (500) @(posedge clk);
            for (i = 0; i < 32; i = i + 1) begin
                spi_read_byte(rb);
                rxbuf[i] = rb;
            end

            for (i = 0; i < 19; i = i + 1) begin
                if (rxbuf[i] === 8'hA5 &&
                    rxbuf[i + 1] === resp_cmd &&
                    rxbuf[i + 2] === 8'd0 &&
                    rxbuf[i + 3] === 8'd8) begin
                    crc = 16'hFFFF;
                    for (j = 1; j < 12; j = j + 1)
                        crc = crc16_byte(crc, rxbuf[i + j]);
                    rx_crc = {rxbuf[i + 12], rxbuf[i + 13]};
                    if (crc === rx_crc) begin
                        valid_out = 1'b1;
                        data_out = {rxbuf[i + 4], rxbuf[i + 5],
                                    rxbuf[i + 6], rxbuf[i + 7],
                                    rxbuf[i + 8], rxbuf[i + 9],
                                    rxbuf[i + 10], rxbuf[i + 11]};
                    end
                end
            end

            if (!valid_out) begin
                $write("  HSM cmd=%02h RX:", req_cmd);
                for (i = 0; i < 20; i = i + 1)
                    $write(" %02h", rxbuf[i]);
                $display("");
            end

            spi_cs_n = 1'b1;
            repeat (20) @(posedge clk);
        end
    endtask

    reg [7:0] status_byte;
    reg [7:0] verify_fail_byte;
    reg [7:0] verify_fail_before;
    reg kyber_ok;
    reg [31:0] kyber_digest;
    reg [15:0] kyber_cycles;
    reg mlkem512_ok;
    reg [7:0] mlkem512_status;
    reg [31:0] mlkem512_partial_digest;
    reg [31:0] mlkem512_polyvec_digest;
    reg [15:0] mlkem512_cycles;
    reg mlkem_stage_ok;
    reg mlkem_runtime_response_valid;
    reg [7:0] mlkem_stage_status;
    reg [31:0] mlkem_stage_digest_a;
    reg [31:0] mlkem_stage_digest_b;
    reg [15:0] mlkem_stage_cycles;
    reg [255:0] mlkem_runtime_message;
    reg [11:0] mlkem_corrupt_saved_coeff;
    reg [255:0] mlkem_runtime_coins;
    reg hsm_valid;
    reg [63:0] hsm_data;
    reg hsm_ext_valid;
    reg [7:0] hsm_ext_len;
    reg [255:0] hsm_ext_data;
    reg [127:0] hsm_ext_challenge;
    reg [127:0] hsm_ext_response;
    reg [127:0] hsm_secure_tag;
    reg [63:0] hsm_session_epoch;
    reg [127:0] d1_envelope_hi;
    reg [127:0] d1_envelope_lo;
    reg [255:0] d1_enrolled_root;
    reg [127:0] d2_blob_0;
    reg [127:0] d2_blob_1;
    reg [127:0] d2_blob_2;
    reg [127:0] hsm4g_blob_0;
    reg [127:0] hsm4g_blob_1;
    reg [127:0] hsm4g_blob_2;
    reg [127:0] hsm4g_confirm_before;
    reg [127:0] hsm4g_confirm_after;
    reg [255:0] hsm4g_key_before;
    reg [15:0] hsm_event_before_puf;
    reg saw_ota_ok, saw_ota_deny;

    function automatic [127:0] hsm3_attest_response;
        input [127:0] challenge_in;
        input [31:0] counter_in;
        begin
            // Independent constants from Python hashlib/HMAC-SHA-256 using
            // key 00..1F and canonical message TrustAT1||counter||challenge.
            if (counter_in == 32'd2 &&
                challenge_in == 128'h4B8633CC9A5700DC26AF37BC48D159C1)
                hsm3_attest_response = 128'h26E9AE4F9B39BCC593EA3A5022441829;
            else if (counter_in == 32'd3 &&
                     challenge_in == 128'h970C679A34AE01BB4D5E6F7B91A2B380)
                hsm3_attest_response = 128'h3663B38D11FA2C85BDB9F9CCD68274F7;
            else
                hsm3_attest_response = 128'd0;
        end
    endfunction

    always @(posedge clk) begin
        if (ota_ok)
            saw_ota_ok <= 1'b1;
        if (ota_deny)
            saw_ota_deny <= 1'b1;
    end

    initial begin
        errors = 0;
        saw_ota_ok = 0;
        saw_ota_deny = 0;
        rst_n = 0;
        spi_cs_n = 1'b1;
        spi_sck = 0;
        spi_mosi = 0;
        sig_valid = 1'b1;
        provision_enable = 1'b0;

        #30 rst_n = 1;
        repeat (10) @(posedge clk);

        // Test 1: STATUS before enroll.
        spi_xfer_frame(8'hF0, 16'd0, 8'd0, 8'd0, 8'd0, 8'd0, 8'd0,
                       10, status_byte, verify_fail_byte);
        if (status_byte[0] !== 1'b0) begin
            errors = errors + 1;
            $display("  FAIL t1: expected not enrolled, status=%02h", status_byte);
        end

        // Test 1b: short VERIFY payload must be ignored.
        spi_xfer_frame(8'h03, 16'd0, 8'd0, 8'd0, 8'd0, 8'd0, 8'd0,
                       8, status_byte, verify_fail_byte);
        repeat (20) @(posedge clk);
        if (dut.verify_fail_count !== 8'd0) begin
            errors = errors + 1;
            $display("  FAIL t1b: short verify changed fail counter to %0d",
                     dut.verify_fail_count);
        end

        // Test 1c: Kyber NTT runtime self-test through SPI opcode 0x10.
        spi_xfer_kyber(kyber_ok, kyber_digest, kyber_cycles);
        if (!kyber_ok || kyber_digest !== 32'hFC3B59FC ||
            kyber_cycles !== EXPECTED_KYBER_CYCLES ||
            !kyber_done || !kyber_pass) begin
            errors = errors + 1;
            $display("  FAIL t1c: kyber_ok=%b digest=%08h cycles=%0d done=%b pass=%b",
                     kyber_ok, kyber_digest, kyber_cycles, kyber_done, kyber_pass);
        end

        // Test 1d: ML-KEM-512 partial runtime self-test through SPI opcode 0x12.
        spi_xfer_mlkem512(mlkem512_ok, mlkem512_status,
                          mlkem512_partial_digest, mlkem512_polyvec_digest,
                          mlkem512_cycles);
        if (!mlkem512_ok || mlkem512_status !== 8'hFF ||
            mlkem512_partial_digest !== 32'h67CF55D2 ||
            mlkem512_polyvec_digest !== 32'hA8981500 ||
            mlkem512_cycles !== EXPECTED_MLKEM512_CYCLES) begin
            errors = errors + 1;
            $display("  FAIL t1d: mlkem ok=%b status=%02h pdig=%08h vdig=%08h cycles=%0d",
                     mlkem512_ok, mlkem512_status, mlkem512_partial_digest,
                     mlkem512_polyvec_digest, mlkem512_cycles);
        end
        $display("  INFO fips_ntt_digest=%08h kyber_cycles=%0d polyvec_digest=%08h mlkem_cycles=%0d",
                 kyber_digest, kyber_cycles,
                 mlkem512_polyvec_digest, mlkem512_cycles);

        // Test 1e: K-PKE-preparation primitive self-test through SPI opcode 0x14.
        shared_permutation_before = shared_permutation_count;
        spi_xfer_mlkem_stage(8'h14, 8'h15, mlkem_stage_ok,
                             mlkem_stage_status, mlkem_stage_digest_a,
                             mlkem_stage_digest_b, mlkem_stage_cycles);
        shared_permutation_delta = shared_permutation_count -
                                   shared_permutation_before;
        if (!mlkem_stage_ok || mlkem_stage_status !== 8'hFF ||
            mlkem_stage_digest_a !== 32'hCDDB5B0C ||
            mlkem_stage_digest_b !== 32'h0440B8D1 ||
            mlkem_stage_cycles !== EXPECTED_KPKE_CYCLES ||
            shared_permutation_delta !== KPKE_SHARED_PERMUTATIONS) begin
            errors = errors + 1;
            $display("  FAIL t1e: kpke ok=%b status=%02h dig_a=%08h dig_b=%08h cycles=%0d permutations=%0d",
                     mlkem_stage_ok, mlkem_stage_status,
                     mlkem_stage_digest_a, mlkem_stage_digest_b,
                     mlkem_stage_cycles, shared_permutation_delta);
        end else begin
            $display("  PASS A25 KeyGen cycle oracle cycles=%0d permutations=%0d extra_permutation_cycles=%0d",
                     mlkem_stage_cycles, shared_permutation_delta,
                     KECCAK_EXTRA_CYCLES_PER_PERM);
        end

        // Test 1e1/1e2: the same 0x14 opcode accepts d||z||k. Only G and
        // public ekPKE fingerprints return; private dkPKE/z stay in FPGA.
        spi_xfer_mlkem_runtime_seed(
            16'd65,
            256'h1F1E1D1C1B1A19181716151413121110_0F0E0D0C0B0A09080706050403020100,
            256'hDFDEDDDCDBDAD9D8D7D6D5D4D3D2D1D0_CFCECDCCCBCAC9C8C7C6C5C4C3C2C1C0,
            8'h00, mlkem_runtime_response_valid, mlkem_stage_ok,
            mlkem_stage_status, mlkem_stage_digest_a,
            mlkem_stage_digest_b, mlkem_stage_cycles);
        if (!mlkem_runtime_response_valid || !mlkem_stage_ok ||
            mlkem_stage_status !== 8'hFF ||
            mlkem_stage_digest_a !== 32'h4F47ABB3 ||
            mlkem_stage_digest_b !== 32'hE8923613 ||
            mlkem_stage_cycles !== EXPECTED_KPKE_CYCLES ||
            !dut.mlkem512_runtime_z_ready ||
            dut.mlkem512_runtime_z !==
              256'hDFDEDDDCDBDAD9D8D7D6D5D4D3D2D1D0_CFCECDCCCBCAC9C8C7C6C5C4C3C2C1C0) begin
            errors = errors + 1;
            $display("  FAIL t1e1: runtime seed0 valid=%b ok=%b status=%02h g=%08h ek=%08h cycles=%0d",
                     mlkem_runtime_response_valid, mlkem_stage_ok,
                     mlkem_stage_status, mlkem_stage_digest_a,
                     mlkem_stage_digest_b, mlkem_stage_cycles);
        end

        spi_xfer_mlkem_runtime_seed(
            16'd65,
            256'hFFEEDDCCBBAA99887766554433221100_0123456789ABCDEFFEDCBA9876543210,
            256'hFFFEFDFCFBFAF9F8F7F6F5F4F3F2F1F0_EFEEEDECEBEAE9E8E7E6E5E4E3E2E1E0,
            8'h5A, mlkem_runtime_response_valid, mlkem_stage_ok,
            mlkem_stage_status, mlkem_stage_digest_a,
            mlkem_stage_digest_b, mlkem_stage_cycles);
        if (!mlkem_runtime_response_valid || !mlkem_stage_ok ||
            mlkem_stage_status !== 8'hFF ||
            mlkem_stage_digest_a !== 32'hA56F09BC ||
            mlkem_stage_digest_b !== 32'hF2E3BE64 ||
            mlkem_stage_cycles !== EXPECTED_KPKE_CYCLES ||
            !dut.mlkem512_runtime_z_ready ||
            dut.mlkem512_runtime_z !==
              256'hFFFEFDFCFBFAF9F8F7F6F5F4F3F2F1F0_EFEEEDECEBEAE9E8E7E6E5E4E3E2E1E0) begin
            errors = errors + 1;
            $display("  FAIL t1e2: runtime seed1 valid=%b ok=%b status=%02h g=%08h ek=%08h cycles=%0d",
                     mlkem_runtime_response_valid, mlkem_stage_ok,
                     mlkem_stage_status, mlkem_stage_digest_a,
                     mlkem_stage_digest_b, mlkem_stage_cycles);
        end

        // Any length other than legacy zero or runtime 33 must fail closed
        // with a valid response rather than timing out or using stale seed.
        spi_xfer_mlkem_runtime_seed(
            16'd64, 256'd0, 256'd0, 8'd0,
            mlkem_runtime_response_valid, mlkem_stage_ok,
            mlkem_stage_status, mlkem_stage_digest_a,
            mlkem_stage_digest_b, mlkem_stage_cycles);
        if (!mlkem_runtime_response_valid || mlkem_stage_ok ||
            mlkem_stage_status !== 8'h00 ||
            mlkem_stage_digest_a !== 32'd0 ||
            mlkem_stage_digest_b !== 32'd0 ||
            mlkem_stage_cycles !== 16'd0 ||
            dut.mlkem512_runtime_key_ready ||
            dut.mlkem512_runtime_z_ready ||
            dut.mlkem512_runtime_z !== 256'd0) begin
            errors = errors + 1;
            $display("  FAIL t1e3: malformed runtime length valid=%b ok=%b status=%02h g=%08h ek=%08h cycles=%0d",
                     mlkem_runtime_response_valid, mlkem_stage_ok,
                     mlkem_stage_status, mlkem_stage_digest_a,
                     mlkem_stage_digest_b, mlkem_stage_cycles);
        end
        if (errors == 0)
            $display("  PASS runtime_keygen_spi vectors=2 malformed_len_reject=1 stale_epoch_invalidated=1 public_outputs=g+ekpke_fingerprints dkpke+z=internal_not_exported");

        // HSM-4D1 owns compact subcommand 0x40 in this artifact.  INFO is
        // public, while the former D0 raw-response mode is blocked regardless
        // of physical presence and must not touch HSM audit state.
        hsm_event_before_puf = dut.u_hsm_shell.event_counter;
        spi_xfer_hsm_ext(8'h01, 8'h40, 8'h00, 32'd100, 8'd1,
                         {8'h00, 248'd0}, hsm_ext_valid, hsm_ext_len, hsm_ext_data);
        if (!hsm_ext_valid || hsm_ext_len !== 8'd22 ||
            hsm_ext_data[239:232] !== 8'h00 ||
            hsm_ext_data[191:184] !== 8'd1 ||
            hsm_ext_data[183:176] !== 8'd0 ||
            hsm_ext_data[175:168] !== 8'd192 ||
            hsm_ext_data[167:160] !== 8'd1 ||
            hsm_ext_data[159:152] !== 8'd12 ||
            hsm_ext_data[151:144] !== 8'd16 ||
            hsm_ext_data[143:136] !== 8'd1 ||
            hsm_ext_data[135:104] !== 32'hD0410101 ||
            hsm_ext_data[103:96] !== 8'h11 ||
            hsm_ext_data[95:88] !== 8'h0B ||
            hsm_ext_data[87:80] !== 8'h01) begin
            errors = errors + 1;
            $display("  FAIL hsm4d1-info data=%064h", hsm_ext_data);
        end
        spi_xfer_hsm_ext(8'h01, 8'h40, 8'h00, 32'd101, 8'd2,
                         {8'h01, 8'h00, 240'd0},
                         hsm_ext_valid, hsm_ext_len, hsm_ext_data);
        if (!hsm_ext_valid || hsm_ext_len !== 8'd8 ||
            hsm_ext_data[239:232] !== 8'h7F) begin
            errors = errors + 1;
            $display("  FAIL hsm4d1-raw-blocked-no-presence data=%064h", hsm_ext_data);
        end
        provision_enable = 1'b1;
        spi_xfer_hsm_ext(8'h01, 8'h40, 8'h00, 32'd102, 8'd2,
                         {8'h01, 8'h02, 240'd0},
                         hsm_ext_valid, hsm_ext_len, hsm_ext_data);
        provision_enable = 1'b0;
        if (!hsm_ext_valid || hsm_ext_len !== 8'd8 ||
            hsm_ext_data[239:232] !== 8'h7F ||
            dut.u_hsm_shell.event_counter !== hsm_event_before_puf) begin
            errors = errors + 1;
            $display("  FAIL hsm4d1-raw-blocked-or-isolation data=%064h event_before=%0d event_after=%0d",
                     hsm_ext_data, hsm_event_before_puf,
                     dut.u_hsm_shell.event_counter);
        end

        // Full D1 protocol path through SPI: enroll with SW0, read only the
        // public envelope, clear the volatile root, load two strict chunks and
        // reconstruct the identical internal root.  No response exposes it.
        provision_enable = 1'b1;
        spi_xfer_hsm_ext(8'h01, 8'h40, 8'h00, 32'd103, 8'd1,
                         {8'h02,248'd0},
                         hsm_ext_valid, hsm_ext_len, hsm_ext_data);
        provision_enable = 1'b0;
        if (!hsm_ext_valid || hsm_ext_len !== 8'd12 ||
            hsm_ext_data[239:232] !== 8'h00 || !dut.puf_root_ready) begin
            errors = errors + 1;
            $display("  FAIL hsm4d1-spi-enroll data=%064h", hsm_ext_data);
        end
        d1_enrolled_root = dut.puf_root_key;
        if (hsm_ext_data === d1_enrolled_root) begin
            errors = errors + 1;
            $display("  FAIL hsm4d1-spi-enroll exposed root");
        end

        spi_xfer_hsm_ext(8'h01, 8'h40, 8'h00, 32'd0, 8'd2,
                         {8'h03,8'd0,240'd0},
                         hsm_ext_valid, hsm_ext_len, hsm_ext_data);
        d1_envelope_hi = hsm_ext_data[183:56];
        spi_xfer_hsm_ext(8'h01, 8'h40, 8'h00, 32'd0, 8'd2,
                         {8'h03,8'd1,240'd0},
                         hsm_ext_valid, hsm_ext_len, hsm_ext_data);
        d1_envelope_lo = hsm_ext_data[183:56];
        if (d1_envelope_hi[127:120] !== 8'h01 ||
            d1_envelope_hi[95:64] !== 32'hD0410101 ||
            d1_envelope_lo === 128'd0) begin
            errors = errors + 1;
            $display("  FAIL hsm4d1-spi-public-envelope");
        end

        spi_xfer_hsm_ext(8'h01, 8'h40, 8'h00, 32'd0, 8'd1,
                         {8'h07,248'd0},
                         hsm_ext_valid, hsm_ext_len, hsm_ext_data);
        if (dut.puf_root_ready || dut.puf_root_key !== 256'd0) begin
            errors = errors + 1;
            $display("  FAIL hsm4d1-spi-clear");
        end
        spi_xfer_hsm_ext(8'h01, 8'h40, 8'h00, 32'd104, 8'd18,
                         {8'h04,8'd0,d1_envelope_hi,112'd0},
                         hsm_ext_valid, hsm_ext_len, hsm_ext_data);
        spi_xfer_hsm_ext(8'h01, 8'h40, 8'h00, 32'd105, 8'd18,
                         {8'h04,8'd1,d1_envelope_lo,112'd0},
                         hsm_ext_valid, hsm_ext_len, hsm_ext_data);
        spi_xfer_hsm_ext(8'h01, 8'h40, 8'h00, 32'd106, 8'd1,
                         {8'h05,248'd0},
                         hsm_ext_valid, hsm_ext_len, hsm_ext_data);
        if (!hsm_ext_valid || hsm_ext_data[239:232] !== 8'h00 ||
            !dut.puf_root_ready || dut.puf_root_key !== d1_enrolled_root ||
            hsm_ext_data === d1_enrolled_root ||
            dut.u_hsm_shell.event_counter !== hsm_event_before_puf) begin
            errors = errors + 1;
            $display("  FAIL hsm4d1-spi-restore data=%064h", hsm_ext_data);
        end

        // HSM-4D2/D3 SPI transport: AES-CTR + HMAC EtM remains underneath the
        // established 0x3A/0x3B transport. Only its 48 public encrypted
        // bytes can be read; a modified ciphertext must fail before HSM load.
        spi_xfer_hsm_ext(8'h01, 8'h40, 8'h00, 32'd1, 8'd14,
                         {8'h08,8'h00,32'd1,64'h1122334455667788,144'd0},
                         hsm_ext_valid, hsm_ext_len, hsm_ext_data);
        if (!hsm_ext_valid || hsm_ext_len !== 8'd14 ||
            hsm_ext_data[239:232] !== 8'h09) begin
            errors = errors + 1;
            $display("  FAIL hsm4d2-no-presence data=%064h", hsm_ext_data);
        end
        provision_enable = 1'b1;
        spi_xfer_hsm_ext(8'h01, 8'h40, 8'h00, 32'd2, 8'd14,
                         {8'h08,8'h00,32'd1,64'h1122334455667788,144'd0},
                         hsm_ext_valid, hsm_ext_len, hsm_ext_data);
        provision_enable = 1'b0;
        // SEAL returns a pre-commit blob-valid status snapshot.  Its durable
        // success proof is the subsequent 3-chunk public blob read.
        if (!hsm_ext_valid || hsm_ext_len !== 8'd14 ||
            hsm_ext_data[239:232] !== 8'h00 ||
            hsm_ext_data[199:192] !== 8'h08 ||
            hsm_ext_data[191:184] !== 8'h01 ||
            hsm_ext_data[183:176] !== 8'h00 ||
            dut.g_qualification_puf_vault.u_puf_vault_service.blob_valid !== 1'b1 ||
            dut.g_qualification_puf_vault.u_puf_vault_service.vault_loaded !== 1'b0) begin
            errors = errors + 1;
            $display("  FAIL hsm4d2-seal data=%064h", hsm_ext_data);
        end
        spi_xfer_hsm_ext(8'h01, 8'h40, 8'h00, 32'd0, 8'd2,
                         {8'h09,8'd0,240'd0},
                         hsm_ext_valid, hsm_ext_len, hsm_ext_data);
        d2_blob_0 = hsm_ext_data[183:56];
        spi_xfer_hsm_ext(8'h01, 8'h40, 8'h00, 32'd0, 8'd2,
                         {8'h09,8'd1,240'd0},
                         hsm_ext_valid, hsm_ext_len, hsm_ext_data);
        d2_blob_1 = hsm_ext_data[183:56];
        spi_xfer_hsm_ext(8'h01, 8'h40, 8'h00, 32'd0, 8'd2,
                         {8'h09,8'd2,240'd0},
                         hsm_ext_valid, hsm_ext_len, hsm_ext_data);
        d2_blob_2 = hsm_ext_data[183:56];
        if (d2_blob_0 == 128'd0 || d2_blob_1 == 128'd0 || d2_blob_2 == 128'd0 ||
            d2_blob_0 === d1_enrolled_root[255:128] ||
            d2_blob_1 === d1_enrolled_root[127:0]) begin
            errors = errors + 1;
            $display("  FAIL hsm4d2-public-blob safety");
        end
        spi_xfer_hsm_ext(8'h01, 8'h40, 8'h00, 32'd0, 8'd1,
                         {8'h0D,248'd0}, hsm_ext_valid, hsm_ext_len, hsm_ext_data);
        spi_xfer_hsm_ext(8'h01, 8'h40, 8'h00, 32'd3, 8'd18,
                         {8'h0A,8'd0,d2_blob_0,112'd0},
                         hsm_ext_valid, hsm_ext_len, hsm_ext_data);
        spi_xfer_hsm_ext(8'h01, 8'h40, 8'h00, 32'd4, 8'd18,
                         {8'h0A,8'd1,d2_blob_1 ^ (128'd1 << 8),112'd0},
                         hsm_ext_valid, hsm_ext_len, hsm_ext_data);
        spi_xfer_hsm_ext(8'h01, 8'h40, 8'h00, 32'd5, 8'd18,
                         {8'h0A,8'd2,d2_blob_2,112'd0},
                         hsm_ext_valid, hsm_ext_len, hsm_ext_data);
        spi_xfer_hsm_ext(8'h01, 8'h40, 8'h00, 32'd0, 8'd1,
                         {8'h0B,248'd0}, hsm_ext_valid, hsm_ext_len, hsm_ext_data);
        if (!hsm_ext_valid || hsm_ext_data[239:232] !== 8'h0A ||
            dut.g_qualification_puf_vault.u_puf_vault_service.vault_loaded !== 1'b0) begin
            errors = errors + 1;
            $display("  FAIL hsm4d2-tamper data=%064h", hsm_ext_data);
        end
        spi_xfer_hsm_ext(8'h01, 8'h40, 8'h00, 32'd0, 8'd1,
                         {8'h0D,248'd0}, hsm_ext_valid, hsm_ext_len, hsm_ext_data);
        spi_xfer_hsm_ext(8'h01, 8'h40, 8'h00, 32'd6, 8'd18,
                         {8'h0A,8'd0,d2_blob_0,112'd0},
                         hsm_ext_valid, hsm_ext_len, hsm_ext_data);
        spi_xfer_hsm_ext(8'h01, 8'h40, 8'h00, 32'd7, 8'd18,
                         {8'h0A,8'd1,d2_blob_1,112'd0},
                         hsm_ext_valid, hsm_ext_len, hsm_ext_data);
        spi_xfer_hsm_ext(8'h01, 8'h40, 8'h00, 32'd8, 8'd18,
                         {8'h0A,8'd2,d2_blob_2,112'd0},
                         hsm_ext_valid, hsm_ext_len, hsm_ext_data);
        spi_xfer_hsm_ext(8'h01, 8'h40, 8'h00, 32'd0, 8'd1,
                         {8'h0B,248'd0}, hsm_ext_valid, hsm_ext_len, hsm_ext_data);
        repeat (3) @(posedge clk);
        if (!hsm_ext_valid || hsm_ext_data[239:232] !== 8'h00 ||
            !dut.g_qualification_puf_vault.u_puf_vault_service.vault_loaded ||
            dut.g_qualification_puf_vault.u_puf_vault_service.vault_hmac_key == 256'd0 ||
            !dut.u_hsm_shell.vault_active ||
            dut.u_hsm_shell.vault_hmac_key !==
            dut.g_qualification_puf_vault.u_puf_vault_service.vault_hmac_key) begin
            errors = errors + 1;
            $display("  FAIL hsm4d2-authenticated-restore data=%064h", hsm_ext_data);
        end
        spi_xfer_hsm(8'h36, 8'h37, 1'b0, 8'd0, hsm_valid, hsm_data);
        repeat (3) @(posedge clk);
        if (dut.g_qualification_puf_vault.u_puf_vault_service.vault_loaded ||
            dut.g_qualification_puf_vault.u_puf_vault_service.vault_hmac_key !== 256'd0 ||
            dut.u_hsm_shell.vault_active) begin
            errors = errors + 1;
            $display("  FAIL hsm4d2-zeroize boundary");
        end

        spi_xfer_hsm_ext(8'h01, 8'h10, 8'h00, 32'd1, 8'd0, 256'd0,
                         hsm_ext_valid, hsm_ext_len, hsm_ext_data);
        if (!hsm_ext_valid || hsm_ext_data[239:232] !== 8'h03) begin
            errors = errors + 1;
            $display("  FAIL hsm4-empty challenge result=%02h", hsm_ext_data[239:232]);
        end
        spi_xfer_hsm_ext(8'h01, 8'h30, 8'h00, 32'd1, 8'd32,
                         256'h000102030405060708090A0B0C0D0E0F101112131415161718191A1B1C1D1E1F,
                         hsm_ext_valid, hsm_ext_len, hsm_ext_data);
        if (!hsm_ext_valid || hsm_ext_data[239:232] !== 8'h08) begin
            errors = errors + 1;
            $display("  FAIL hsm4f-direct-lock-no-presence result=%02h", hsm_ext_data[239:232]);
        end
        provision_enable = 1'b1;
        spi_xfer_hsm_ext(8'h01, 8'h30, 8'h00, 32'd1, 8'd32,
                         256'h000102030405060708090A0B0C0D0E0F101112131415161718191A1B1C1D1E1F,
                         hsm_ext_valid, hsm_ext_len, hsm_ext_data);
        if (!hsm_ext_valid || hsm_ext_data[239:232] !== 8'h08) begin
            errors = errors + 1;
            $display("  FAIL hsm4f-direct-lock-presence data=%064h", hsm_ext_data);
        end
        spi_xfer_hsm_ext(8'h01, 8'h33, 8'h00, 32'd1, 8'd32,
                         256'h000102030405060708090A0B0C0D0E0F101112131415161718191A1B1C1D1E1F,
                         hsm_ext_valid, hsm_ext_len, hsm_ext_data);
        if (!hsm_ext_valid || hsm_ext_data[239:232] !== 8'h08 ||
            dut.u_hsm_shell.vault_staged_valid) begin
            errors = errors + 1;
            $display("  FAIL hsm4f-prepare-lock data=%064h", hsm_ext_data);
        end

        // Protocol regression setup: inject the historical public test key
        // only through the already-tested internal D2 restore wires. No SPI
        // command can perform this operation in the synthesized design.
        force dut.puf_vault_hmac_key =
          256'h000102030405060708090A0B0C0D0E0F101112131415161718191A1B1C1D1E1F;
        force dut.puf_vault_load_pulse = 1'b1;
        repeat (2) @(posedge clk);
        force dut.puf_vault_load_pulse = 1'b0;
        repeat (2) @(posedge clk);
        release dut.puf_vault_load_pulse;
        release dut.puf_vault_hmac_key;
        provision_enable = 1'b0;
        spi_xfer_hsm_ext(8'h01, 8'h31, 8'h00, 32'd0, 8'd1,
                         {8'd0, 248'd0}, hsm_ext_valid, hsm_ext_len, hsm_ext_data);
        if (!hsm_ext_valid || hsm_ext_len !== 8'd32 ||
            hsm_ext_data[239:232] !== 8'h00 || hsm_ext_data[191:184] !== 8'h05 ||
            hsm_ext_data[175:168] !== 8'd1 || hsm_ext_data[167:160] !== 8'd0 ||
            hsm_ext_data[119:112] !== 8'd1 || hsm_ext_data[111:104] !== 8'd1 ||
            hsm_ext_data[103:96] !== 8'd0 ||
            hsm_ext_data[95:32] !== 64'h0123_4567_89AB_CDEF ||
            hsm_ext_data[31:24] !== 8'd1 || hsm_ext_data[23:16] !== 8'd1 ||
            hsm_ext_data[15:8] !== 8'd0 || hsm_ext_data[7:0] !== 8'd14) begin
            errors = errors + 1;
            $display("  FAIL hsm4-status data=%064h", hsm_ext_data);
        end

        // Compact HSM-3 flow consumes the internal-only restored vault key.
        spi_xfer_hsm_ext(8'h01, 8'h12, 8'h00, 32'd1, 8'd2,
                         {8'd2, 8'd3, 240'd0},
                         hsm_ext_valid, hsm_ext_len, hsm_ext_data);
        if (!hsm_ext_valid || hsm_ext_data[239:232] !== 8'h09) begin
            errors = errors + 1;
            $display("  FAIL hsm2-a: unauth bind data=%064h", hsm_ext_data);
        end

        spi_xfer_hsm_ext(8'h01, 8'h10, 8'h00, 32'd2, 8'd0, 256'd0,
                         hsm_ext_valid, hsm_ext_len, hsm_ext_data);
        hsm_ext_challenge = hsm_ext_data[199:72];
        hsm_ext_response = hsm3_attest_response(hsm_ext_challenge, 32'd2);
        spi_xfer_hsm_ext(8'h01, 8'h11, 8'h00, 32'd2, 8'd16, 256'd0,
                         hsm_ext_valid, hsm_ext_len, hsm_ext_data);
        if (!hsm_ext_valid || hsm_ext_data[239:232] !== 8'h06) begin
            errors = errors + 1;
            $display("  FAIL hsm2-b: wrong verify result=%02h", hsm_ext_data[239:232]);
        end
        spi_xfer_hsm_ext(8'h01, 8'h11, 8'h00, 32'd2, 8'd16,
                         {hsm_ext_response, 128'd0}, hsm_ext_valid, hsm_ext_len, hsm_ext_data);
        if (!hsm_ext_valid || hsm_ext_data[239:232] !== 8'h05) begin
            errors = errors + 1;
            $display("  FAIL hsm2-c: consumed challenge result=%02h", hsm_ext_data[239:232]);
        end

        spi_xfer_hsm_ext(8'h01, 8'h10, 8'h00, 32'd3, 8'd0, 256'd0,
                         hsm_ext_valid, hsm_ext_len, hsm_ext_data);
        hsm_ext_challenge = hsm_ext_data[199:72];
        hsm_ext_response = hsm3_attest_response(hsm_ext_challenge, 32'd3);
        spi_xfer_hsm_ext(8'h01, 8'h11, 8'h00, 32'd3, 8'd16,
                         {hsm_ext_response, 128'd0}, hsm_ext_valid, hsm_ext_len, hsm_ext_data);
        repeat (5) @(posedge clk);
        if (!hsm_ext_valid || hsm_ext_data[239:232] !== 8'h00 || !verify_ok) begin
            errors = errors + 1;
            $display("  FAIL hsm2-d: positive verify result=%02h session=%b challenge=%032h tag=%032h device=%08h",
                     hsm_ext_data[239:232], verify_ok, hsm_ext_challenge,
                     hsm_ext_response, device_id);
        end
        spi_xfer_hsm_ext(8'h01, 8'h11, 8'h00, 32'd3, 8'd16,
                         {hsm_ext_response, 128'd0}, hsm_ext_valid, hsm_ext_len, hsm_ext_data);
        if (!hsm_ext_valid || hsm_ext_data[239:232] !== 8'h07) begin
            errors = errors + 1;
            $display("  FAIL hsm2-e: replay verify result=%02h", hsm_ext_data[239:232]);
        end

        spi_xfer_mlkem_stage(8'h18, 8'h19, mlkem_stage_ok,
                             mlkem_stage_status, mlkem_stage_digest_a,
                             mlkem_stage_digest_b, mlkem_stage_cycles);
        // Historical stage 0x18 exposes only a fingerprint, so supply the
        // full-key C4 handoff from the TB boundary.  The C3 integration test
        // below obtains these registers from the real Encaps/Decaps path.
        force dut.c4_keypair_ready = 1'b1;
        force dut.c4_sender_shared_secret =
          256'h000102030405060708090A0B0C0D0E0F101112131415161718191A1B1C1D1E1F;
        force dut.c4_receiver_shared_secret =
          256'h000102030405060708090A0B0C0D0E0F101112131415161718191A1B1C1D1E1F;
        spi_xfer_hsm_ext(8'h01, 8'h12, 8'h00, 32'd4, 8'd2,
                         {8'd2, 8'd3, 240'd0},
                         hsm_ext_valid, hsm_ext_len, hsm_ext_data);
        if (!hsm_ext_valid || hsm_ext_len !== 8'd23 || hsm_ext_data[239:232] !== 8'h00 ||
            hsm_ext_data[183:176] !== 8'd2 ||
            hsm_ext_data[175:168] !== 8'd3 ||
            hsm_ext_data[159:152] !== 8'd0 ||
            hsm_ext_data[143:136] !== 8'd1) begin
            errors = errors + 1;
            $display("  FAIL hsm2-f: bind data=%064h", hsm_ext_data);
        end
        hsm_session_epoch = hsm_ext_data[135:72];
        if (hsm_session_epoch !== {32'h53463231, 32'd4}) begin
            errors = errors + 1;
            $display("  FAIL SF2 hsm2-f epoch=%016h", hsm_session_epoch);
        end
        release dut.c4_keypair_ready;
        release dut.c4_sender_shared_secret;
        release dut.c4_receiver_shared_secret;
        spi_xfer_hsm_ext(8'h01, 8'h12, 8'h00, 32'd4, 8'd2,
                         {8'd2, 8'd3, 240'd0},
                         hsm_ext_valid, hsm_ext_len, hsm_ext_data);
        if (!hsm_ext_valid || hsm_ext_data[239:232] !== 8'h07) begin
            errors = errors + 1;
            $display("  FAIL hsm2-g: replay bind result=%02h", hsm_ext_data[239:232]);
        end

        // This SPI profile does not instantiate the C4 internal-K channel,
        // so retain its public test vector while updating its SF2 transcript.
        hsm_secure_tag = 128'h0AE5DE3A7C9EDF74D4A390B1E81AEB19;
        spi_xfer_hsm_ext(8'h01, 8'h20, 8'h00, 32'd5, 8'd32,
                         {hsm_session_epoch, 64'h1122334455667788, hsm_secure_tag},
                         hsm_ext_valid, hsm_ext_len, hsm_ext_data);
        if (!hsm_ext_valid || hsm_ext_data[239:232] !== 8'h00 ||
            hsm_ext_data[199:136] !== 64'h1122334455667788) begin
            errors = errors + 1;
            $display("  FAIL hsm3-secure: data=%064h", hsm_ext_data);
        end
        spi_xfer_hsm_ext(8'h01, 8'h20, 8'h00, 32'd5, 8'd32,
                         {hsm_session_epoch, 64'h1122334455667788, hsm_secure_tag},
                         hsm_ext_valid, hsm_ext_len, hsm_ext_data);
        if (!hsm_ext_valid || hsm_ext_data[239:232] !== 8'h07) begin
            errors = errors + 1;
            $display("  FAIL hsm3-secure-replay result=%02h", hsm_ext_data[239:232]);
        end
        spi_xfer_hsm(8'h36, 8'h37, 1'b0, 8'd0, hsm_valid, hsm_data);
        repeat (5) @(posedge clk);
        if (!hsm_valid || verify_ok) begin
            errors = errors + 1;
            $display("  FAIL hsm2-h: zeroize did not close compact session");
        end
        spi_xfer_hsm_ext(8'h01, 8'h31, 8'h00, 32'd0, 8'd1,
                         {8'd0, 248'd0}, hsm_ext_valid, hsm_ext_len, hsm_ext_data);
        if (!hsm_ext_valid || hsm_ext_data[159:152] !== 8'h01 ||
            hsm_ext_data[135:120] !== 16'd2) begin
            errors = errors + 1;
            $display("  FAIL hsm4-session-zeroize-cleared-vault data=%064h", hsm_ext_data);
        end
        spi_xfer_hsm_ext(8'h01, 8'h32, 8'h00, 32'd2, 8'd1,
                         {8'd0, 248'd0}, hsm_ext_valid, hsm_ext_len, hsm_ext_data);
        if (!hsm_ext_valid || hsm_ext_data[239:232] !== 8'h09) begin
            errors = errors + 1;
            $display("  FAIL hsm4-destroy-no-presence result=%02h", hsm_ext_data[239:232]);
        end
        provision_enable = 1'b1;
        spi_xfer_hsm_ext(8'h01, 8'h32, 8'h00, 32'd2, 8'd1,
                         {8'd0, 248'd0}, hsm_ext_valid, hsm_ext_len, hsm_ext_data);
        provision_enable = 1'b0;
        if (!hsm_ext_valid || hsm_ext_data[239:232] !== 8'h00 ||
            hsm_ext_data[159:152] !== 8'h00) begin
            errors = errors + 1;
            $display("  FAIL hsm4-destroy data=%064h", hsm_ext_data);
        end

        // HSM-4F SPI hardening: both historical plaintext staging paths are
        // permanently locked. Presence cannot reopen them and COMMIT sees no
        // staging entry.
        spi_xfer_frame(8'hFF, 16'd0, 8'd0, 8'd0, 8'd0, 8'd0, 8'd0,
                       4, status_byte, verify_fail_byte);
        repeat (20) @(posedge clk);
        spi_xfer_hsm_ext(8'h01, 8'h33, 8'h00, 32'd1, 8'd32,
                         256'h000102030405060708090A0B0C0D0E0F101112131415161718191A1B1C1D1E1F,
                         hsm_ext_valid, hsm_ext_len, hsm_ext_data);
        if (!hsm_ext_valid || hsm_ext_data[239:232] !== 8'h08) begin
            errors = errors + 1;
            $display("  FAIL hsm4f-prepare-lock-no-presence data=%064h", hsm_ext_data);
        end
        provision_enable = 1'b1;
        spi_xfer_hsm_ext(8'h01, 8'h33, 8'h00, 32'd1, 8'd32,
                         256'h000102030405060708090A0B0C0D0E0F101112131415161718191A1B1C1D1E1F,
                         hsm_ext_valid, hsm_ext_len, hsm_ext_data);
        if (!hsm_ext_valid || hsm_ext_data[239:232] !== 8'h08 ||
            dut.u_hsm_shell.vault_staged_valid ||
            dut.u_hsm_shell.vault_staged_key !== 256'd0) begin
            errors = errors + 1;
            $display("  FAIL hsm4f-prepare-lock-presence data=%064h", hsm_ext_data);
        end
        spi_xfer_hsm_ext(8'h01, 8'h34, 8'h00, 32'd1, 8'd5,
                         {8'd0, 32'd1, 216'd0}, hsm_ext_valid, hsm_ext_len, hsm_ext_data);
        if (hsm_ext_data[239:232] !== 8'h03) begin
            errors = errors + 1;
            $display("  FAIL hsm4f-empty-commit data=%064h", hsm_ext_data);
        end
        // The hardened bus cannot create unauthenticated staging. Inject the
        // otherwise unreachable internal state to verify COMMIT still fails
        // closed if a future backend or fault presents it.
        force dut.u_hsm_shell.vault_staged_valid = 1'b1;
        force dut.u_hsm_shell.vault_staged_authenticated = 1'b0;
        force dut.u_hsm_shell.vault_staged_prepare_counter = 32'd1;
        force dut.u_hsm_shell.vault_staged_key = 256'hDEAD_BEEF;
        spi_xfer_hsm_ext(8'h01, 8'h34, 8'h00, 32'd2, 8'd5,
                         {8'd0, 32'd1, 216'd0}, hsm_ext_valid, hsm_ext_len, hsm_ext_data);
        if (!hsm_ext_valid || hsm_ext_data[239:232] !== 8'h08) begin
            errors = errors + 1;
            $display("TB_SPI_HSM4F_UNAUTH_STAGING_COMMIT_RESULT: FAIL data=%064h", hsm_ext_data);
        end else begin
            $display("TB_SPI_HSM4F_UNAUTH_STAGING_COMMIT_RESULT: PASS");
        end
        release dut.u_hsm_shell.vault_staged_key;
        release dut.u_hsm_shell.vault_staged_prepare_counter;
        release dut.u_hsm_shell.vault_staged_authenticated;
        release dut.u_hsm_shell.vault_staged_valid;
        provision_enable = 1'b0;

        // HSM-4G SPI integration: signed metadata authorizes exactly one PUF
        // vault seal. COMMIT is locked until that internal service stages its
        // key. The public blob must reconstruct the same key after core reset.
        spi_xfer_frame(8'hFF, 16'd0, 8'd0, 8'd0, 8'd0, 8'd0, 8'd0,
                       4, status_byte, verify_fail_byte);
        repeat (20) @(posedge clk);

        // Restore the private PUF root from the already-enrolled public helper.
        provision_enable = 1'b1;
        spi_xfer_hsm_ext(8'h01, 8'h40, 8'h00, 32'd1, 8'd18,
                         {8'h04,8'd0,d1_envelope_hi,112'd0},
                         hsm_ext_valid, hsm_ext_len, hsm_ext_data);
        spi_xfer_hsm_ext(8'h01, 8'h40, 8'h00, 32'd2, 8'd18,
                         {8'h04,8'd1,d1_envelope_lo,112'd0},
                         hsm_ext_valid, hsm_ext_len, hsm_ext_data);
        spi_xfer_hsm_ext(8'h01, 8'h40, 8'h00, 32'd3, 8'd1,
                         {8'h05,248'd0},
                         hsm_ext_valid, hsm_ext_len, hsm_ext_data);
        if (!dut.puf_root_ready) begin
            errors = errors + 1;
            $display("  FAIL hsm4g-root-restore-before-provision");
        end

        provision_enable = 1'b0;
        spi_xfer_hsm_ext(8'h01, 8'h37, 8'h00, 32'd1, 8'd32,
                         {32'h53494731, 8'h00, 8'h05, 8'h21, 8'h01,
                          64'h0123456789ABCDEF,
                          128'h603E3EB01FA94274DB7FF9BF74CD3A7B},
                         hsm_ext_valid, hsm_ext_len, hsm_ext_data);
        if (!hsm_ext_valid || hsm_ext_data[239:232] !== 8'h09) begin
            errors = errors + 1;
            $display("  FAIL hsm4e-no-presence data=%064h", hsm_ext_data);
        end
        provision_enable = 1'b1;
        spi_xfer_hsm_ext(8'h01, 8'h37, 8'h00, 32'd1, 8'd32,
                         {32'h53494731, 8'h00, 8'h05, 8'h21, 8'h01,
                          64'h0123456789ABCDEF, 128'd0},
                         hsm_ext_valid, hsm_ext_len, hsm_ext_data);
        if (!hsm_ext_valid || hsm_ext_data[239:232] !== 8'h0A) begin
            errors = errors + 1;
            $display("  FAIL hsm4e-wrong-tag data=%064h", hsm_ext_data);
        end
        spi_xfer_hsm_ext(8'h01, 8'h37, 8'h00, 32'd1, 8'd32,
                         {32'h53494731, 8'h00, 8'h05, 8'h21, 8'h01,
                          64'h0123456789ABCDEF,
                          128'h603E3EB01FA94274DB7FF9BF74CD3A7B},
                         hsm_ext_valid, hsm_ext_len, hsm_ext_data);
        if (!hsm_ext_valid || hsm_ext_data[239:232] !== 8'h07) begin
            errors = errors + 1;
            $display("  FAIL hsm4e-replay-after-auth-fail data=%064h", hsm_ext_data);
        end
        spi_xfer_hsm_ext(8'h01, 8'h37, 8'h00, 32'd2, 8'd32,
                         {32'h53494731, 8'h00, 8'h05, 8'h21, 8'h01,
                          64'h0123456789ABCDEF,
                          128'h8D9458D4856E5C1AE82AC7A6410EC498},
                         hsm_ext_valid, hsm_ext_len, hsm_ext_data);
        if (!hsm_ext_valid || hsm_ext_len !== 8'd15 ||
            hsm_ext_data[239:232] !== 8'h00 ||
            dut.u_hsm_shell.vault_staged_authenticated !== 1'b1 ||
            dut.u_hsm_shell.vault_staged_puf_bound !== 1'b0 ||
            dut.u_hsm_shell.vault_staged_key !== 256'd0 ||
            !dut.puf_vault_stage_authorized) begin
            errors = errors + 1;
            $display("  FAIL hsm4g-auth-grant data=%064h", hsm_ext_data);
        end

        // Ticket authentication alone cannot publish a key.
        spi_xfer_hsm_ext(8'h01, 8'h34, 8'h00, 32'd3, 8'd5,
                         {8'd0, 32'd2, 216'd0},
                         hsm_ext_valid, hsm_ext_len, hsm_ext_data);
        if (!hsm_ext_valid || hsm_ext_data[239:232] !== 8'h08) begin
            errors = errors + 1;
            $display("  FAIL hsm4g-commit-before-seal data=%064h", hsm_ext_data);
        end


        spi_xfer_hsm_ext(8'h01, 8'h40, 8'h00, 32'd1, 8'd14,
                         {8'h0E,8'h01,32'd1,64'h474B455950455253,144'd0},
                         hsm_ext_valid, hsm_ext_len, hsm_ext_data);
        repeat (3) @(posedge clk);
        if (!hsm_ext_valid || hsm_ext_data[239:232] !== 8'h00 ||
            hsm_ext_data[199:192] !== 8'h0E ||
            !dut.u_hsm_shell.vault_staged_puf_bound ||
            dut.u_hsm_shell.vault_staged_key == 256'd0) begin
            errors = errors + 1;
            $display("  FAIL hsm4g-authenticated-seal data=%064h", hsm_ext_data);
        end
        hsm4g_key_before = dut.u_hsm_shell.vault_staged_key;

        spi_xfer_hsm_ext(8'h01, 8'h40, 8'h00, 32'd0, 8'd2,
                         {8'h09,8'd0,240'd0}, hsm_ext_valid, hsm_ext_len, hsm_ext_data);
        hsm4g_blob_0 = hsm_ext_data[183:56];
        spi_xfer_hsm_ext(8'h01, 8'h40, 8'h00, 32'd0, 8'd2,
                         {8'h09,8'd1,240'd0}, hsm_ext_valid, hsm_ext_len, hsm_ext_data);
        hsm4g_blob_1 = hsm_ext_data[183:56];
        spi_xfer_hsm_ext(8'h01, 8'h40, 8'h00, 32'd0, 8'd2,
                         {8'h09,8'd2,240'd0}, hsm_ext_valid, hsm_ext_len, hsm_ext_data);
        hsm4g_blob_2 = hsm_ext_data[183:56];

        spi_xfer_hsm_ext(8'h01, 8'h34, 8'h00, 32'd3, 8'd5,
                         {8'd0, 32'd2, 216'd0},
                         hsm_ext_valid, hsm_ext_len, hsm_ext_data);
        if (!hsm_ext_valid || hsm_ext_data[239:232] !== 8'h00 ||
            dut.u_hsm_shell.vault_hmac_key !== hsm4g_key_before) begin
            errors = errors + 1;
            $display("  FAIL hsm4g-commit-after-seal data=%064h", hsm_ext_data);
        end
        spi_xfer_hsm_ext(8'h01, 8'h38, 8'h00, 32'd42, 8'd16,
                         {128'h48534D34475F4B45595F434F4E464952,128'd0},
                         hsm_ext_valid, hsm_ext_len, hsm_ext_data);
        hsm4g_confirm_before = hsm_ext_data[199:72];
        if (!hsm_ext_valid || hsm_ext_len !== 8'd23 ||
            hsm_ext_data[239:232] !== 8'h00 || hsm4g_confirm_before == 128'd0) begin
            errors = errors + 1;
            $display("  FAIL hsm4g-confirm-before-reset data=%064h", hsm_ext_data);
        end

        // Reset every volatile FPGA service, restore root and public blob, then
        // compare a one-way confirmation token for the same caller nonce.
        spi_xfer_frame(8'hFF, 16'd0, 8'd0, 8'd0, 8'd0, 8'd0, 8'd0,
                       4, status_byte, verify_fail_byte);
        repeat (20) @(posedge clk);
        spi_xfer_hsm_ext(8'h01, 8'h40, 8'h00, 32'd1, 8'd18,
                         {8'h04,8'd0,d1_envelope_hi,112'd0},
                         hsm_ext_valid, hsm_ext_len, hsm_ext_data);
        spi_xfer_hsm_ext(8'h01, 8'h40, 8'h00, 32'd2, 8'd18,
                         {8'h04,8'd1,d1_envelope_lo,112'd0},
                         hsm_ext_valid, hsm_ext_len, hsm_ext_data);
        spi_xfer_hsm_ext(8'h01, 8'h40, 8'h00, 32'd3, 8'd1,
                         {8'h05,248'd0}, hsm_ext_valid, hsm_ext_len, hsm_ext_data);
        spi_xfer_hsm_ext(8'h01, 8'h40, 8'h00, 32'd1, 8'd18,
                         {8'h0A,8'd0,hsm4g_blob_0,112'd0},
                         hsm_ext_valid, hsm_ext_len, hsm_ext_data);
        spi_xfer_hsm_ext(8'h01, 8'h40, 8'h00, 32'd2, 8'd18,
                         {8'h0A,8'd1,hsm4g_blob_1,112'd0},
                         hsm_ext_valid, hsm_ext_len, hsm_ext_data);
        spi_xfer_hsm_ext(8'h01, 8'h40, 8'h00, 32'd3, 8'd18,
                         {8'h0A,8'd2,hsm4g_blob_2,112'd0},
                         hsm_ext_valid, hsm_ext_len, hsm_ext_data);
        spi_xfer_hsm_ext(8'h01, 8'h40, 8'h00, 32'd0, 8'd1,
                         {8'h0B,248'd0}, hsm_ext_valid, hsm_ext_len, hsm_ext_data);
        repeat (3) @(posedge clk);
        if (!dut.u_hsm_shell.vault_active ||
            dut.u_hsm_shell.vault_hmac_key !== hsm4g_key_before) begin
            errors = errors + 1;
            $display("  FAIL hsm4g-restored-key-internal");
        end
        spi_xfer_hsm_ext(8'h01, 8'h38, 8'h00, 32'd42, 8'd16,
                         {128'h48534D34475F4B45595F434F4E464952,128'd0},
                         hsm_ext_valid, hsm_ext_len, hsm_ext_data);
        hsm4g_confirm_after = hsm_ext_data[199:72];
        if (!hsm_ext_valid || hsm_ext_data[239:232] !== 8'h00 ||
            hsm4g_confirm_after !== hsm4g_confirm_before) begin
            errors = errors + 1;
            $display("TB_SPI_HSM4G_SAME_KEY_RESULT: FAIL before=%032h after=%032h",
                     hsm4g_confirm_before, hsm4g_confirm_after);
        end else begin
            $display("TB_SPI_HSM4G_SAME_KEY_RESULT: PASS token=%032h",
                     hsm4g_confirm_after);
        end

        spi_xfer_hsm_ext(8'h01, 8'h36, 8'h00, 32'd4, 8'd1,
                         {8'd0, 248'd0},
                         hsm_ext_valid, hsm_ext_len, hsm_ext_data);
        if (!hsm_ext_valid || hsm_ext_data[239:232] !== 8'h00 ||
            dut.u_hsm_shell.vault_hmac_key !== 256'd0 ||
            dut.u_hsm_shell.vault_staged_key !== 256'd0 ||
            dut.u_hsm_shell.vault_staged_valid !== 1'b0 ||
            dut.u_hsm_shell.vault_staged_authenticated !== 1'b0 ||
            dut.u_hsm_shell.vault_staged_puf_bound !== 1'b0) begin
            errors = errors + 1;
            $display("  FAIL hsm4e-revoke-scrub data=%064h", hsm_ext_data);
        end
        spi_xfer_hsm_ext(8'h01, 8'h32, 8'h00, 32'd5, 8'd1,
                         {8'd0, 248'd0},
                         hsm_ext_valid, hsm_ext_len, hsm_ext_data);
        provision_enable = 1'b0;
        // Revoking a key restored by the PUF service also clears that service;
        // the HSM therefore reaches EMPTY before a redundant DESTROY.
        if (!hsm_ext_valid || hsm_ext_data[239:232] !== 8'h03) begin
            errors = errors + 1;
            $display("  FAIL hsm4g-redundant-destroy data=%064h", hsm_ext_data);
        end

        // Reset the HSM-2 evidence flow so frozen HSM-1 audit indices remain stable.
        spi_xfer_frame(8'hFF, 16'd0, 8'd0, 8'd0, 8'd0, 8'd0, 8'd0,
                       4, status_byte, verify_fail_byte);
        repeat (20) @(posedge clk);

        // HSM A/B: public info succeeds before auth; key metadata is denied.
        spi_xfer_hsm(8'h30, 8'h31, 1'b0, 8'd0, hsm_valid, hsm_data);
        if (!hsm_valid || hsm_data[63:56] !== 8'h00 ||
            hsm_data[55:48] !== 8'd7 || hsm_data[39:32] !== 8'hFF ||
            hsm_data[47:40] !== 8'd0 || hsm_data[31:24] !== 8'd4 ||
            hsm_data[23:16] !== 8'd0) begin
            errors = errors + 1;
            $display("  FAIL hsm-a: GET_INFO valid=%b data=%016h", hsm_valid, hsm_data);
        end
        spi_xfer_hsm(8'h34, 8'h35, 1'b1, 8'd2, hsm_valid, hsm_data);
        if (!hsm_valid || hsm_data[63:56] !== 8'h01) begin
            errors = errors + 1;
            $display("  FAIL hsm-b: unauth KEY_STATUS result=%02h", hsm_data[63:56]);
        end

        // Test 1f: K-PKE Encrypt arithmetic KAT through legacy opcode 0x16.
        spi_xfer_mlkem_stage(8'h16, 8'h17, mlkem_stage_ok,
                             mlkem_stage_status, mlkem_stage_digest_a,
                             mlkem_stage_digest_b, mlkem_stage_cycles);
        if (!mlkem_stage_ok || mlkem_stage_status !== 8'hFF ||
            mlkem_stage_digest_a !== 32'hCA84F003 ||
            mlkem_stage_digest_b !== 32'h5D4B538C ||
            mlkem_stage_cycles !== EXPECTED_CODEC_CYCLES) begin
            errors = errors + 1;
            $display("  FAIL t1f: ciphertext_codec ok=%b status=%02h digest_a=%08h digest_b=%08h cycles=%0d",
                     mlkem_stage_ok, mlkem_stage_status,
                     mlkem_stage_digest_a, mlkem_stage_digest_b,
                     mlkem_stage_cycles);
        end

        // A runtime Encrypt before a fresh runtime KeyGen is fail-closed.
        // The PUF/HSM checks above include core reset activity, so a prior
        // runtime KeyGen cannot be silently reused across that boundary.
        for (i = 0; i < 32; i = i + 1) begin
            mlkem_runtime_message[i*8 +: 8] = i;
            mlkem_runtime_coins[i*8 +: 8] = i + 32;
        end
        spi_xfer_mlkem_runtime_encrypt(
            16'd64, mlkem_runtime_message, mlkem_runtime_coins,
            mlkem_runtime_response_valid, mlkem_stage_ok,
            mlkem_stage_status, mlkem_stage_digest_a,
            mlkem_stage_digest_b, mlkem_stage_cycles);
        if (!mlkem_runtime_response_valid || mlkem_stage_ok ||
            mlkem_stage_status !== 8'h00 ||
            mlkem_stage_digest_a !== 32'd0 ||
            mlkem_stage_digest_b !== 32'd0 ||
            mlkem_stage_cycles !== 16'd2) begin
            errors = errors + 1;
            $display("  FAIL t1f1 no-key runtime encrypt valid=%b ok=%b status=%02h digest=%08h/%08h cycles=%0d",
                     mlkem_runtime_response_valid, mlkem_stage_ok,
                     mlkem_stage_status, mlkem_stage_digest_a,
                     mlkem_stage_digest_b, mlkem_stage_cycles);
        end else begin
            $display("  PASS runtime_encrypt_no_key_reject status=0 digest=0/0 cycles=2");
        end

        // Load the public runtime seed used by the host qualification and
        // bind the following Encrypt to the resulting internal matrix/ekPKE.
        spi_xfer_mlkem_runtime_seed(
            16'd65,
            256'hFFEEDDCCBBAA99887766554433221100_0123456789ABCDEFFEDCBA9876543210,
            256'hFFFEFDFCFBFAF9F8F7F6F5F4F3F2F1F0_EFEEEDECEBEAE9E8E7E6E5E4E3E2E1E0,
            8'h5A, mlkem_runtime_response_valid, mlkem_stage_ok,
            mlkem_stage_status, mlkem_stage_digest_a,
            mlkem_stage_digest_b, mlkem_stage_cycles);
        if (!mlkem_runtime_response_valid || !mlkem_stage_ok ||
            mlkem_stage_status !== 8'hFF ||
            mlkem_stage_digest_a !== 32'hA56F09BC ||
            mlkem_stage_digest_b !== 32'hF2E3BE64 ||
            mlkem_stage_cycles !== EXPECTED_KPKE_CYCLES ||
            !dut.mlkem512_runtime_key_ready ||
            !dut.mlkem512_runtime_z_ready ||
            dut.mlkem512_runtime_z !==
              256'hFFFEFDFCFBFAF9F8F7F6F5F4F3F2F1F0_EFEEEDECEBEAE9E8E7E6E5E4E3E2E1E0) begin
            errors = errors + 1;
            $display("  FAIL t1f2 runtime key bind preload valid=%b ok=%b status=%02h g=%08h ek=%08h ready=%b cycles=%0d",
                     mlkem_runtime_response_valid, mlkem_stage_ok,
                     mlkem_stage_status, mlkem_stage_digest_a,
                     mlkem_stage_digest_b, dut.mlkem512_runtime_key_ready,
                     mlkem_stage_cycles);
        end

        // Test 1f2: exact 64-byte m||coins runtime path bound to internal
        // KeyGen matrix/ekPKE storage.  Digests come from an independent
        // SHA3/SHAKE/NTT/packing oracle, not from this RTL's RAM contents.
        shared_permutation_before = shared_permutation_count;
        spi_xfer_mlkem_runtime_encrypt(
            16'd64, mlkem_runtime_message, mlkem_runtime_coins,
            mlkem_runtime_response_valid, mlkem_stage_ok,
            mlkem_stage_status, mlkem_stage_digest_a,
            mlkem_stage_digest_b, mlkem_stage_cycles);
        shared_permutation_delta = shared_permutation_count -
                                   shared_permutation_before;
        build_bound_encrypt_oracle(mlkem_runtime_message);
        if (!mlkem_runtime_response_valid || !mlkem_stage_ok ||
            mlkem_stage_status !== 8'hFF ||
            mlkem_stage_digest_a !== bound_oracle_a ||
            mlkem_stage_digest_b !== bound_oracle_b ||
            bound_oracle_a !== 32'h497BF105 ||
            bound_oracle_b !== 32'hA29EEDFA ||
            mlkem_stage_cycles !== EXPECTED_RUNTIME_ENCRYPT_CYCLES ||
            shared_permutation_delta !==
                RUNTIME_ENCRYPT_SHARED_PERMUTATIONS) begin
            errors = errors + 1;
            $display("  FAIL t1f2 bound runtime encrypt valid=%b ok=%b status=%02h digest=%08h/%08h oracle=%08h/%08h cycles=%0d permutations=%0d",
                     mlkem_runtime_response_valid, mlkem_stage_ok,
                     mlkem_stage_status, mlkem_stage_digest_a,
                     mlkem_stage_digest_b, bound_oracle_a, bound_oracle_b,
                     mlkem_stage_cycles, shared_permutation_delta);
        end else begin
            $display("  PASS A25 Encrypt cycle oracle cycles=%0d permutations=%0d extra_permutation_cycles=%0d",
                     mlkem_stage_cycles, shared_permutation_delta,
                     KECCAK_EXTRA_CYCLES_PER_PERM);
        end

        for (i = 0; i < 32; i = i + 1) begin
            mlkem_runtime_message[i*8 +: 8] = 8'hA5 ^ i;
        end
        mlkem_runtime_coins =
            256'hA3907B7C379D2AA882E7339692933B99_C492872FC02A1CE8C407330D9525A021;
        spi_xfer_mlkem_runtime_encrypt(
            16'd64, mlkem_runtime_message, mlkem_runtime_coins,
            mlkem_runtime_response_valid, mlkem_stage_ok,
            mlkem_stage_status, mlkem_stage_digest_a,
            mlkem_stage_digest_b, mlkem_stage_cycles);
        build_bound_encrypt_oracle(mlkem_runtime_message);
        if (!mlkem_runtime_response_valid || !mlkem_stage_ok ||
            mlkem_stage_status !== 8'hFF ||
            mlkem_stage_digest_a !== bound_oracle_a ||
            mlkem_stage_digest_b !== bound_oracle_b ||
            bound_oracle_a !== 32'h838E41A7 ||
            bound_oracle_b !== 32'h340C0118 ||
            mlkem_stage_cycles !== EXPECTED_RUNTIME_ENCRYPT_CYCLES) begin
            errors = errors + 1;
            $display("  FAIL t1f2b bound runtime vector1 valid=%b ok=%b status=%02h digest=%08h/%08h oracle=%08h/%08h cycles=%0d",
                     mlkem_runtime_response_valid, mlkem_stage_ok,
                     mlkem_stage_status, mlkem_stage_digest_a,
                     mlkem_stage_digest_b, bound_oracle_a, bound_oracle_b,
                     mlkem_stage_cycles);
        end else begin
            $display("  PASS runtime_encrypt_bound_keygen_spi transpose=A^T v0=497bf105/a29eedfa v1=838e41a7/340c0118 cycles=%0d codec_decode_roundtrip=1",
                     mlkem_stage_cycles);
        end

        // Stage 3.22: a 32-byte 0x16 qualification request supplies m.  The
        // FPGA derives H(ek), (K,coins)=G(m||H(ek)), reuses the exact Encrypt
        // datapath and returns K directly, matching FIPS 203 Algorithm 17.
        // The fixed fingerprints were independently reproduced with hashlib.
        shared_permutation_before = shared_permutation_count;
        spi_xfer_mlkem_runtime_encrypt(
            16'd32, mlkem_runtime_message, 256'd0,
            mlkem_runtime_response_valid, mlkem_stage_ok,
            mlkem_stage_status, mlkem_stage_digest_a,
            mlkem_stage_digest_b, mlkem_stage_cycles);
        shared_permutation_delta = shared_permutation_count -
                                   shared_permutation_before;
        if (!mlkem_runtime_response_valid || !mlkem_stage_ok ||
            mlkem_stage_status !== 8'hFF ||
            mlkem_stage_digest_a !== 32'h27033E5E ||
            mlkem_stage_digest_b !== 32'hBC3DC488 ||
            mlkem_stage_digest_a === 32'h23B34C51 ||
            mlkem_stage_cycles !== EXPECTED_ENCAPS_CYCLES ||
            shared_permutation_delta !== ENCAPS_SHARED_PERMUTATIONS ||
            dut.u_mlkem512_decaps_partial.h_ek_fp_q !== 32'h2E782439 ||
            dut.u_mlkem512_decaps_partial.g_fp_q !== 32'h55853EBD ||
            !dut.u_mlkem512_decaps_partial.encaps_mode_q) begin
            errors = errors + 1;
            $display("  FAIL runtime_mlkem_encaps_chain_spi valid=%b ok=%b status=%02h ss=%08h hc=%08h cycles=%0d permutations=%0d",
                     mlkem_runtime_response_valid, mlkem_stage_ok,
                     mlkem_stage_status, mlkem_stage_digest_a,
                     mlkem_stage_digest_b, mlkem_stage_cycles,
                     shared_permutation_delta);
        end else begin
            $display("  PASS runtime_mlkem_encaps_fips_flow_spi input_m=32 h_ek=2e782439 g=55853ebd h_c=bc3dc488 k=27033e5e ciphertext_bytes=768 key_source=internal_ekpke raw_export=0 cycles=%0d fips203_alg17_k_direct=1 qualification_only=1 no_validation_claim",
                     mlkem_stage_cycles);
            $display("  PASS A25 Encaps cycle oracle cycles=%0d permutations=%0d extra_permutation_cycles=%0d",
                     mlkem_stage_cycles, shared_permutation_delta,
                     KECCAK_EXTRA_CYCLES_PER_PERM);
        end
        // Any nonzero length other than the 32-byte Encaps input or the
        // 64-byte low-level Encrypt qualification input must fail closed.
        spi_xfer_mlkem_runtime_encrypt(
            16'd63, mlkem_runtime_message, mlkem_runtime_coins,
            mlkem_runtime_response_valid, mlkem_stage_ok,
            mlkem_stage_status, mlkem_stage_digest_a,
            mlkem_stage_digest_b, mlkem_stage_cycles);
        if (!mlkem_runtime_response_valid || mlkem_stage_ok ||
            mlkem_stage_status !== 8'h00 || mlkem_stage_digest_a !== 32'd0 ||
            mlkem_stage_digest_b !== 32'd0 || mlkem_stage_cycles !== 16'd0) begin
            errors = errors + 1;
            $display("  FAIL t1f3 malformed runtime encrypt valid=%b ok=%b status=%02h digest=%08h/%08h cycles=%0d",
                     mlkem_runtime_response_valid, mlkem_stage_ok,
                     mlkem_stage_status, mlkem_stage_digest_a,
                     mlkem_stage_digest_b, mlkem_stage_cycles);
        end else begin
            $display("  PASS runtime_encrypt_spi payload=64 malformed_len_reject=1 message+coins+internal_ekpke_bound=1");
        end

        // A ciphertext may never fall back to the historical compatibility
        // KAT when runtime z is absent. This fault injection proves the
        // runtime path fails closed before any decrypt/KDF operation.
        force dut.mlkem512_runtime_z_ready = 1'b0;
        spi_xfer_mlkem_stage(8'h18, 8'h19, mlkem_stage_ok,
                             mlkem_stage_status, mlkem_stage_digest_a,
                             mlkem_stage_digest_b, mlkem_stage_cycles);
        if (mlkem_stage_ok || mlkem_stage_status !== 8'h00 ||
            mlkem_stage_digest_a !== 32'd0 ||
            mlkem_stage_digest_b !== 32'd0) begin
            errors = errors + 1;
            $display("  FAIL runtime_decaps_missing_z_reject ok=%b status=%02h digest=%08h/%08h cycles=%0d",
                     mlkem_stage_ok, mlkem_stage_status,
                     mlkem_stage_digest_a, mlkem_stage_digest_b,
                     mlkem_stage_cycles);
        end else begin
            $display("  PASS runtime_decaps_missing_z_reject fail_closed=1 raw_z_export=0");
        end
        release dut.mlkem512_runtime_z_ready;

        // Test 1g: bounded Decaps qualification. J(z||c) is always computed,
        // recovered m' and G coins drive Encrypt, then all 768 bytes are
        // compared before constant-time K/J selection. The response does not
        // expose ciphertext validity; the TB checks the private match bit.
        shared_permutation_before = shared_permutation_count;
        spi_xfer_mlkem_stage(8'h18, 8'h19, mlkem_stage_ok,
                             mlkem_stage_status, mlkem_stage_digest_a,
                             mlkem_stage_digest_b, mlkem_stage_cycles);
        decaps_valid_latency = decaps_last_cycles;
        decaps_valid_permutations = shared_permutation_count -
                                    shared_permutation_before;
        if (!mlkem_stage_ok || mlkem_stage_status !== 8'hFF ||
            mlkem_stage_digest_a !== 32'h27033E5E ||
            mlkem_stage_digest_b !== 32'hBC3DC488 ||
            mlkem_stage_digest_a === 32'h23B34C51 ||
            mlkem_stage_digest_a === mlkem_stage_digest_b ||
            mlkem_stage_cycles !== 16'hFFFF ||
            dut.u_mlkem512_decaps_partial.h_ek_fp_q !== 32'h2E782439 ||
            dut.u_mlkem512_decaps_partial.g_fp_q !== 32'h55853EBD ||
            !dut.u_mlkem512_decaps_partial.ciphertext_match_q ||
            dut.u_mlkem512_decaps_partial.compare_diff_q !== 8'h00) begin
            errors = errors + 1;
            $display("  FAIL t1g: decaps ok=%b status=%02h valid=%08h corrupt=%08h cycles=%0d",
                     mlkem_stage_ok, mlkem_stage_status,
                     mlkem_stage_digest_a, mlkem_stage_digest_b,
                     mlkem_stage_cycles);
        end else begin
            $display("  PASS runtime_mlkem_decaps_fips_flow_spi message_digest=45abb036 h_ek=2e782439 h_c=bc3dc488 g=55853ebd k=27033e5e j_computed=1 compare_bytes=768 match=1 cycles_ge_65535 raw_export=0 fips203_alg18_select=1 qualification_only=1 no_validation_claim");
        end

        // Corrupt one private decoded-v coefficient by q/2. The recovered
        // message must change, the full compare must mismatch, and KDF must
        // return the runtime-KeyGen z fallback fingerprint without an error
        // oracle. The z value is checked privately above and never returned.
        mlkem_corrupt_saved_coeff =
            `TB_SPI_DECODED_COEFF(512);
        `TB_SPI_DECODED_COEFF(512) =
            (mlkem_corrupt_saved_coeff + 12'd1665 >= 12'd3329) ?
            mlkem_corrupt_saved_coeff + 12'd1665 - 12'd3329 :
            mlkem_corrupt_saved_coeff + 12'd1665;
        shared_permutation_before = shared_permutation_count;
        spi_xfer_mlkem_stage(8'h18, 8'h19, mlkem_stage_ok,
                             mlkem_stage_status, mlkem_stage_digest_a,
                             mlkem_stage_digest_b, mlkem_stage_cycles);
        decaps_invalid_latency = decaps_last_cycles;
        decaps_invalid_permutations = shared_permutation_count -
                                      shared_permutation_before;
        if (!mlkem_stage_ok || mlkem_stage_status !== 8'hFF ||
            mlkem_stage_digest_a !== 32'h578E4BA1 ||
            mlkem_stage_digest_b !== 32'hBC3DC488 ||
            mlkem_stage_digest_a === 32'h27033E5E ||
            mlkem_stage_digest_a === 32'h0429546C ||
            mlkem_stage_cycles !== 16'hFFFF ||
            dut.u_mlkem512_decaps_partial.ciphertext_match_q !== 1'b0) begin
            errors = errors + 1;
            $display("  FAIL runtime_kpke_decrypt_corrupt_ciphertext_reject ok=%b status=%02h digest=%08h",
                     mlkem_stage_ok, mlkem_stage_status, mlkem_stage_digest_a);
        end else begin
            if (decaps_valid_latency <= 0 ||
                decaps_invalid_latency !== decaps_valid_latency ||
                decaps_valid_permutations !==
                    DECAPS_SHARED_PERMUTATIONS ||
                decaps_invalid_permutations !==
                    decaps_valid_permutations) begin
                errors = errors + 1;
                $display("  FAIL U1 Decaps busy latency valid/invalid %0d/%0d permutations=%0d/%0d",
                         decaps_valid_latency, decaps_invalid_latency,
                         decaps_valid_permutations,
                         decaps_invalid_permutations);
            end else begin
                $display("  PASS U1 Decaps busy latency valid/implicit-rejection=%0d cycles permutations=%0d",
                         decaps_valid_latency,
                         decaps_valid_permutations);
            end
            $display("  PASS runtime_mlkem_decaps_implicit_rejection j_z_c=%08h match=0 compare_bytes=768 z_source=runtime_keygen_internal z_export=0 no_validity_error_oracle=1 fips203_alg18_j=1 qualification_only=1 no_validation_claim",
                     mlkem_stage_digest_a);
        end
        `TB_SPI_DECODED_COEFF(512) =
            mlkem_corrupt_saved_coeff;

        // Test 2: PUF enroll with nonce=0.
        spi_xfer_frame(8'h01, 16'd4, 8'd0, 8'd0, 8'd0, 8'd0, 8'd0,
                       0, status_byte, verify_fail_byte);
        repeat (8000) @(posedge clk);
        if (!enrolled) begin
            errors = errors + 1;
            $display("  FAIL t2: enroll timeout, enrolled=%b", enrolled);
        end

        // Test 3: PUF verify with nonce=1.
        spi_xfer_frame(8'h03, 16'd4, 8'd0, 8'd0, 8'd0, 8'd1, 8'd0,
                       12, status_byte, verify_fail_byte);
        repeat (8000) @(posedge clk);
        if (!verify_ok) begin
            errors = errors + 1;
            $display("  FAIL t3: verify session, verify_ok=%b", verify_ok);
        end
        if (dut.verify_fail_count !== 8'd0) begin
            errors = errors + 1;
            $display("  FAIL t3a: valid verify changed fail counter to %0d",
                     dut.verify_fail_count);
        end

        spi_xfer_frame(8'hF0, 16'd0, 8'd0, 8'd0, 8'd0, 8'd0, 8'd0,
                       32, status_byte, verify_fail_byte);
        if (!enrolled || !verify_ok) begin
            errors = errors + 1;
            $display("  FAIL t3b: session wires enrolled=%b verify_ok=%b",
                     enrolled, verify_ok);
        end
        if (status_byte !== 8'h03 && enrolled && verify_ok)
            $display("  NOTE t3b: STATUS SPI byte=%02h (session wires OK)", status_byte);

        // HSM C: authenticated metadata is visible but raw-export flag is 0.
        spi_xfer_hsm(8'h34, 8'h35, 1'b1, 8'd2, hsm_valid, hsm_data);
        if (!hsm_valid || hsm_data[63:56] !== 8'h00 ||
            hsm_data[55:48] !== 8'd2 || hsm_data[31:24] !== 8'd0 ||
            hsm_data[23:16] !== 8'd1) begin
            errors = errors + 1;
            $display("  FAIL hsm-c: authenticated KEY_STATUS data=%016h", hsm_data);
        end

        // HSM D: authenticated decaps-stage use increments slot 2 usage.
        spi_xfer_mlkem_stage(8'h18, 8'h19, mlkem_stage_ok,
                             mlkem_stage_status, mlkem_stage_digest_a,
                             mlkem_stage_digest_b, mlkem_stage_cycles);
        spi_xfer_hsm(8'h34, 8'h35, 1'b1, 8'd2, hsm_valid, hsm_data);
        if (!hsm_valid || hsm_data[63:56] !== 8'h00 ||
            hsm_data[55:48] !== 8'd2 || hsm_data[15:0] !== 16'd1) begin
            errors = errors + 1;
            $display("  FAIL hsm-d: slot2 usage data=%016h", hsm_data);
        end

        // HSM E: audit index 1 records the pre-auth KEY_STATUS denial.
        spi_xfer_hsm(8'h38, 8'h39, 1'b1, 8'd1, hsm_valid, hsm_data);
        if (!hsm_valid || hsm_data[63:56] !== 8'h00 ||
            hsm_data[31:24] !== 8'h34 || hsm_data[15:8] !== 8'h01) begin
            errors = errors + 1;
            $display("  FAIL hsm-e: AUDIT_READ data=%016h", hsm_data);
        end

        // Test 3c: bad nonce increments fail counter exactly once.
        verify_fail_before = dut.verify_fail_count;
        spi_xfer_frame(8'h03, 16'd4, 8'd0, 8'd0, 8'd0, 8'd1, 8'd0,
                       12, status_byte, verify_fail_byte);
        repeat (20) @(posedge clk);
        spi_xfer_frame(8'hF0, 16'd0, 8'd0, 8'd0, 8'd0, 8'd0, 8'd0,
                       40, status_byte, verify_fail_byte);
        if (dut.verify_fail_count !== (verify_fail_before + 8'd1)) begin
            errors = errors + 1;
            $display("  FAIL t3c: expected one increment from %0d, got %0d",
                     verify_fail_before, dut.verify_fail_count);
        end

        // Test 3d: failed verification saturates instead of wrapping.
        @(negedge clk);
        dut.verify_fail_count = 8'hFE;
        spi_xfer_frame(8'h03, 16'd4, 8'd0, 8'd0, 8'd0, 8'd1, 8'd0,
                       12, status_byte, verify_fail_byte);
        repeat (20) @(posedge clk);
        if (dut.verify_fail_count !== 8'hFF) begin
            errors = errors + 1;
            $display("  FAIL t3d: expected saturated fail counter FF, got %02h",
                     dut.verify_fail_count);
        end

        // Test 4: OTA commit OK.
        spi_xfer_frame(8'h20, 16'd5, 8'hAA, 8'hBB, 8'hCC, 8'hDD, 8'h01,
                       0, status_byte, verify_fail_byte);
        repeat (20) @(posedge clk);
        @(negedge clk);
        spi_xfer_frame(8'h22, 16'd0, 8'd0, 8'd0, 8'd0, 8'd0, 8'd0,
                       0, status_byte, verify_fail_byte);
        repeat (5) @(posedge clk);
        if (!saw_ota_ok) begin
            errors = errors + 1;
            $display("  FAIL t4: expected ota commit_ok");
        end
        if (!ota_ok || ota_deny) begin
            errors = errors + 1;
            $display("  FAIL t4b: expected latched OTA OK only, ota_ok=%b ota_deny=%b",
                     ota_ok, ota_deny);
        end

        // Test 5: OTA deny through payload override immediately after signed OK.
        saw_ota_ok = 0;
        saw_ota_deny = 0;
        sig_valid = 1'b1;
        spi_xfer_frame(8'h20, 16'd5, 8'h11, 8'h22, 8'h33, 8'h44, 8'h00,
                       0, status_byte, verify_fail_byte);
        repeat (20) @(posedge clk);
        if (ota_ok || ota_deny) begin
            errors = errors + 1;
            $display("  FAIL t5a: OTA_BEGIN unsigned did not clear previous result, ota_ok=%b ota_deny=%b",
                     ota_ok, ota_deny);
        end
        @(negedge clk);
        spi_xfer_frame(8'h22, 16'd0, 8'd0, 8'd0, 8'd0, 8'd0, 8'd0,
                       0, status_byte, verify_fail_byte);
        repeat (5) @(posedge clk);
        if (!saw_ota_deny) begin
            errors = errors + 1;
            $display("  FAIL t5: expected ota commit_deny");
        end
        if (ota_ok || !ota_deny) begin
            errors = errors + 1;
            $display("  FAIL t5b: expected latched OTA DENY only, ota_ok=%b ota_deny=%b",
                     ota_ok, ota_deny);
        end
        spi_xfer_frame(8'hF0, 16'd0, 8'd0, 8'd0, 8'd0, 8'd0, 8'd0,
                       20, status_byte, verify_fail_byte);
        if (status_byte[4:3] !== 2'b10) begin
            errors = errors + 1;
            $display("  FAIL t5c: expected STATUS ota_deny_seen=1 ota_ok_seen=0, status=%02h",
                     status_byte);
        end

        // HSM F/G: zeroize closes the session; sensitive command is denied again.
        spi_xfer_hsm(8'h36, 8'h37, 1'b0, 8'd0, hsm_valid, hsm_data);
        repeat (5) @(posedge clk);
        if (!hsm_valid || hsm_data[63:56] !== 8'h00 || verify_ok) begin
            errors = errors + 1;
            $display("  FAIL hsm-f: ZEROIZE data=%016h verify_ok=%b", hsm_data, verify_ok);
        end
        spi_xfer_hsm(8'h34, 8'h35, 1'b1, 8'd0, hsm_valid, hsm_data);
        if (!hsm_valid || hsm_data[63:56] !== 8'h01) begin
            errors = errors + 1;
            $display("  FAIL hsm-g: post-zeroize KEY_STATUS result=%02h", hsm_data[63:56]);
        end

        // Test 6: mirror the ESP32 lab firmware reset/status transaction.
        // The client clocks four dummy bytes after RESET, waits before issuing
        // STATUS, and reads sixteen response bytes.  Keep this exact shape in
        // regression: it catches a lab-only reset/recovery mismatch.
        spi_xfer_frame(8'hFF, 16'd0, 8'd0, 8'd0, 8'd0, 8'd0, 8'd0,
                       4, status_byte, verify_fail_byte);
        repeat (20) @(posedge clk);
        spi_xfer_frame(8'hF0, 16'd0, 8'd0, 8'd0, 8'd0, 8'd0, 8'd0,
                       16, status_byte, verify_fail_byte);
        if (enrolled || verify_ok || ota_ok || ota_deny ||
            kyber_done || kyber_pass || dut.verify_fail_count !== 8'd0 ||
            status_byte[2:0] !== 3'b000) begin
            errors = errors + 1;
            $display("  FAIL t6: reset did not clear state: status=%02h enrolled=%b verify=%b ota_ok=%b ota_deny=%b kyber_done=%b kyber_pass=%b fail=%0d",
                     status_byte, enrolled, verify_ok, ota_ok, ota_deny,
                     kyber_done, kyber_pass, dut.verify_fail_count);
        end

        // Test 6b: an ESP32-only reset restarts its extension counter at one.
        // It must first issue CMD_RESET, after which a previously public D1
        // envelope can be loaded and restored with the low counter sequence.
        // This is the exact boot synchronization path used by firmware 2.6.1.
        repeat (5000) @(posedge clk);
        spi_xfer_hsm_ext(8'h01, 8'h40, 8'h00, 32'd1, 8'd1,
                         {8'h00,248'd0}, hsm_ext_valid, hsm_ext_len, hsm_ext_data);
        if (!hsm_ext_valid || hsm_ext_data[239:232] !== 8'h00) begin
            errors = errors + 1;
            $display("  FAIL t6b: D1 INFO after boot synchronization data=%064h", hsm_ext_data);
        end
        spi_xfer_hsm_ext(8'h01, 8'h40, 8'h00, 32'd2, 8'd2,
                         {8'h01,8'd0,240'd0}, hsm_ext_valid, hsm_ext_len, hsm_ext_data);
        spi_xfer_hsm_ext(8'h01, 8'h40, 8'h00, 32'd3, 8'd1,
                         {8'h07,248'd0}, hsm_ext_valid, hsm_ext_len, hsm_ext_data);
        spi_xfer_hsm_ext(8'h01, 8'h40, 8'h00, 32'd4, 8'd18,
                         {8'h04,8'd0,d1_envelope_hi,112'd0},
                         hsm_ext_valid, hsm_ext_len, hsm_ext_data);
        if (!hsm_ext_valid || hsm_ext_data[239:232] !== 8'h00) begin
            errors = errors + 1;
            $display("  FAIL t6b: D1 load chunk 0 after boot synchronization data=%064h", hsm_ext_data);
        end
        spi_xfer_hsm_ext(8'h01, 8'h40, 8'h00, 32'd5, 8'd18,
                         {8'h04,8'd1,d1_envelope_lo,112'd0},
                         hsm_ext_valid, hsm_ext_len, hsm_ext_data);
        spi_xfer_hsm_ext(8'h01, 8'h40, 8'h00, 32'd6, 8'd1,
                         {8'h05,248'd0}, hsm_ext_valid, hsm_ext_len, hsm_ext_data);
        if (!hsm_ext_valid || hsm_ext_data[239:232] !== 8'h00 ||
            !dut.puf_root_ready || dut.puf_root_key !== d1_enrolled_root) begin
            errors = errors + 1;
            $display("  FAIL t6b: D1 restore after boot synchronization data=%064h", hsm_ext_data);
        end

        // Preserve the final-clean-state contract after the boot-sync test.
        spi_xfer_frame(8'hFF, 16'd0, 8'd0, 8'd0, 8'd0, 8'd0, 8'd0,
                       4, status_byte, verify_fail_byte);
        repeat (20) @(posedge clk);
        if (dut.puf_root_ready || dut.puf_root_key !== 256'd0 ||
            dut.mlkem512_runtime_z_ready ||
            dut.mlkem512_runtime_z !== 256'd0) begin
            errors = errors + 1;
            $display("  FAIL t6c: final reset did not scrub D1 root or ML-KEM z");
        end

        if (errors == 0)
            $display("TB_TRUSTEDGE_SPI_RESULT: ALL PASS (baseline + D1/D2 internal restore + HSM-4E auth + HSM-4F legacy lock)");
        else
            $display("TB_TRUSTEDGE_SPI_RESULT: FAIL (%0d errors)", errors);
        $finish;
    end
endmodule

`undef TB_SPI_MATRIX_EVEN
`undef TB_SPI_MATRIX_ODD
`undef TB_SPI_EKPKE_PAIR
`undef TB_SPI_NOISE_EVEN
`undef TB_SPI_NOISE_ODD
`undef TB_SPI_DECODED_COEFF
