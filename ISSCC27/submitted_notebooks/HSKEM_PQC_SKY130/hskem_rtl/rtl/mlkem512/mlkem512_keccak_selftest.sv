// Streaming rejection sampler for FIPS 203 SampleNTT (Algorithm 7).
// Three input bytes form two 12-bit candidates. Values >= q are rejected;
// accepted coefficients are emitted in order until exactly 256 are produced.
module mlkem512_sample_ntt_parser (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        start,
    input  wire        in_valid,
    input  wire [7:0]  in_byte,
    output reg         coeff0_valid,
    output reg [11:0]  coeff0,
    output reg         coeff1_valid,
    output reg [11:0]  coeff1,
    output reg [8:0]   accepted_count,
    output reg         done
);
    localparam [11:0] Q = 12'd3329;
    reg [1:0] byte_phase;
    reg [7:0] byte0;
    reg [7:0] byte1;

    wire [11:0] candidate0 = {byte1[3:0], byte0};
    wire [11:0] candidate1 = {in_byte, byte1[7:4]};
    wire accept0 = (byte_phase == 2'd2) && in_valid &&
                   !done && (accepted_count < 9'd256) &&
                   (candidate0 < Q);
    wire accept1 = (byte_phase == 2'd2) && in_valid &&
                   !done && ((accepted_count + accept0) < 9'd256) &&
                   (candidate1 < Q);
    wire [9:0] next_count = accepted_count + accept0 + accept1;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            byte_phase <= 2'd0;
            byte0 <= 8'd0;
            byte1 <= 8'd0;
            coeff0_valid <= 1'b0;
            coeff0 <= 12'd0;
            coeff1_valid <= 1'b0;
            coeff1 <= 12'd0;
            accepted_count <= 9'd0;
            done <= 1'b0;
        end else begin
            coeff0_valid <= 1'b0;
            coeff1_valid <= 1'b0;

            if (start) begin
                byte_phase <= 2'd0;
                accepted_count <= 9'd0;
                done <= 1'b0;
            end else if (in_valid && !done) begin
                case (byte_phase)
                    2'd0: begin
                        byte0 <= in_byte;
                        byte_phase <= 2'd1;
                    end
                    2'd1: begin
                        byte1 <= in_byte;
                        byte_phase <= 2'd2;
                    end
                    default: begin
                        coeff0_valid <= accept0;
                        coeff0 <= candidate0;
                        coeff1_valid <= accept1;
                        coeff1 <= candidate1;
                        accepted_count <= next_count[8:0];
                        if (next_count == 10'd256)
                            done <= 1'b1;
                        byte_phase <= 2'd0;
                    end
                endcase
            end
        end
    end
endmodule

// Public SHA3/SHAKE known-answer tests plus a fixed-input K-PKE.KeyGen
// foundation.  It first checks G(d || k) = SHA3-512(d || k) for public
// d=00..1F and k=00, then uses the derived rho/sigma for all four
// SampleNTT(rho || j || i) entries and four PRF_eta1(sigma || nonce) streams.
// One sponge/permutation is reused sequentially; sampled coefficients are
// serialized in pairs and decoded again.  This is a deterministic KeyGen KAT,
// not a general ek/dk API or full K-PKE/ML-KEM implementation.
module mlkem512_keccak_selftest #(
    parameter USE_EXTERNAL_SPONGE = 1'b0
) (
    input  wire       clk,
    input  wire       rst_n,
    input  wire       start,
    input  wire       runtime_seed_valid,
    input  wire [255:0] runtime_seed_d,
    input  wire [7:0] runtime_seed_k,
    output reg        busy,
    output reg        done,
    output reg        pass,
    output reg [31:0] sha3_prefix,
    output reg [31:0] shake_prefix,
    output reg [31:0] matrix_digest,
    output reg [31:0] serial_digest,
    output reg [15:0] cycles,
    output wire       matrix_load0_valid,
    output wire [9:0] matrix_load0_addr,
    output wire [11:0] matrix_load0_data,
    output wire       matrix_load1_valid,
    output wire [9:0] matrix_load1_addr,
    output wire [11:0] matrix_load1_data,
    output wire       noise_load_valid,
    output wire [9:0] noise_load_addr,
    output wire [7:0] noise_load_data,
    output wire       rho_load_valid,
    output wire [4:0] rho_load_addr,
    output wire [7:0] rho_load_data,
    output reg [31:0] prf_digest,
    output reg [31:0] g_digest,
    output wire       sponge_ext_start,
    output wire [1:0] sponge_ext_mode,
    output wire [15:0] sponge_ext_message_len,
    output wire [15:0] sponge_ext_output_len,
    output wire       sponge_ext_in_valid,
    output wire [7:0] sponge_ext_in_byte,
    output wire       sponge_ext_out_ready,
    input  wire       sponge_ext_in_ready,
    input  wire       sponge_ext_out_valid,
    input  wire [7:0] sponge_ext_out_byte,
    input  wire       sponge_ext_out_last,
    input  wire       sponge_ext_busy,
    input  wire       sponge_ext_done,
    input  wire       sponge_ext_error
);
    localparam [255:0] SHA3_256_EMPTY_LE =
        256'h4A43F8804B0AD882FA493BE44DFF80F562D661A05647C15166D71EBFF8C6FFA7;
    localparam [511:0] SHA3_512_EMPTY_LE =
        512'h26CD1D2886857501E3D3B6959D1900F558C53A2C40E9E3114CF9F5F13A12B215A6805C47C1DCD1E05958E24F1682C9976E755A18DC67B5C8C59A3AA2CC739FA6;
    localparam [255:0] SHAKE128_EMPTY_32_LE =
        256'h26EF66FAAC6E1AEB88BCEFF693803BD73E850576504560617D828FE8A42B9C7F;
    localparam [511:0] SHAKE256_EMPTY_64_LE =
        512'hBEC4B7B3AC2E294086B49A47491C82FCF692B5679D0105CB00F2C0D8DDC45DD72F76D56E64270CB5821BB862EA52CD3F24EB3E74EB3F3B23138DA80B2BDDB946;
    localparam [255:0] SHA3_256_ABC_LE =
        256'h3215431145E2BF465B529D3E6E085F85BD90D36B2D175C04B225E24FA75D983A;
    localparam [255:0] SHAKE128_SEQ200_32_LE =
        256'h695DAD792CA9581868C201D6212AF4665C66E0D8B8F806E61A80311ECA34420C;
    localparam [1599:0] SHAKE128_EMPTY_200_LE =
        1600'h77F8238D8B5358EF2DB380B5AEAB9166198B3407DFE927B9DF1994A6FDE17B76A9FCB07CF4EEE7AEEFBDAA140B587A169F844C5E9FCD0700AFA8CC8C364D4723565F76ADCFA7CD17EA20513A0B1ABF1CBCC8102E30049ADF38D5594BCC7BBBEFA559C3AADFD6DFBAB28550436A5ED235889174D9586A91AB752FFA9A1660D2B862DC233C87CCB835E257AEF9E3A1A89C63A3E8584AFA016E682AFDEE0AFB3C10934B0088A9EEB13C26EF66FAAC6E1AEB88BCEFF693803BD73E850576504560617D828FE8A42B9C7F;
    localparam [511:0] SHA3_512_SEQ72_LE =
        512'h076CD21DC2586AAACAD8231C4EC07C64930A61ECFD8EC79CCB465EFC128F23182E5B796ED8E114499579FDBEA0E34E26E1E40601484768AC83A971E9BBF2635D;

    // SHA3-512(00 01 ... 1F || 00), stored so byte zero is at bit zero.
    localparam [511:0] G_DK_LE =
        512'hB5B1B3532EAB2FD223FC55A4E1FD01648B6C650D8A2C51E75B32168358DF4206BA9C1BE8CF0B3D2609987052550D7DC0CA72E3044F91336B10542833E9DEF63F;
    localparam [31:0] EXPECTED_G_DIGEST = 32'h4F47ABB3;
    localparam [31:0] EXPECTED_MATRIX_DIGEST = 32'hF3478550;
    localparam [31:0] EXPECTED_SERIAL_DIGEST = 32'h524390FD;
    localparam [31:0] EXPECTED_PRF_DIGEST = 32'h09102894;
    localparam [31:0] MATRIX_DIGEST_INIT = 32'h4D4C4B35;
    localparam [31:0] SERIAL_DIGEST_INIT = 32'h53455231;
    localparam [31:0] G_DIGEST_INIT = 32'h47454E31;

    localparam [2:0] S_IDLE  = 3'd0,
                     S_START = 3'd1,
                     S_RUN   = 3'd2,
                     S_DONE  = 3'd3;

    reg [2:0] state;
    reg [4:0] test_index;
    reg [15:0] feed_index;
    reg [15:0] output_index;
    reg test_ok;
    reg aggregate_ok;
    reg sponge_start;
    reg parser_start;
    reg sample_pending_valid;
    reg [11:0] sample_pending;
    reg pair_check_pending;
    reg [15:0] pair_coeff [0:1];
    reg serialization_ok;
    reg [7:0] rho_byte [0:31];
    reg [7:0] sigma_byte [0:31];
    reg runtime_seed_valid_q;
    reg [255:0] runtime_seed_d_q;
    reg [7:0] runtime_seed_k_q;

    // Test slots 0..7 are public primitive KATs, 8 is G(d||k), 9..12
    // are A_hat entries, and 13..16 are the four eta1 PRF streams.
    wire g_test = (test_index == 5'd8);
    wire matrix_test = (test_index >= 5'd9) && (test_index <= 5'd12);
    wire prf_test = (test_index >= 5'd13) && (test_index <= 5'd16);
    wire [1:0] matrix_entry = test_index - 5'd9;
    wire [1:0] prf_nonce = test_index - 5'd13;
    wire [1:0] sponge_mode =
        matrix_test ? 2'd2 : prf_test ? 2'd3 : g_test ? 2'd1 :
        (test_index == 5'd0 || test_index == 5'd4) ? 2'd0 :
        (test_index == 5'd1 || test_index == 5'd7) ? 2'd1 :
        (test_index == 5'd2 || test_index == 5'd5 ||
         test_index == 5'd6) ? 2'd2 : 2'd3;
    wire [15:0] sponge_message_len =
        matrix_test ? 16'd34 : prf_test ? 16'd33 : g_test ? 16'd33 :
        (test_index == 5'd4) ? 16'd3 :
        (test_index == 5'd5) ? 16'd200 :
        (test_index == 5'd7) ? 16'd72 : 16'd0;
    wire [15:0] sponge_output_len =
        matrix_test ? 16'd672 : prf_test ? 16'd192 : g_test ? 16'd64 :
        (test_index == 5'd6) ? 16'd200 :
        (test_index == 5'd1 || test_index == 5'd3 ||
         test_index == 5'd7) ? 16'd64 : 16'd32;

    function automatic [7:0] message_byte;
        input [4:0] which_test;
        input [15:0] index;
        reg [1:0] matrix_id;
        begin
            if (which_test >= 5'd13) begin
                if (index < 16'd32)
                    message_byte = sigma_byte[index[4:0]];
                else
                    message_byte = {6'd0, which_test - 5'd13};
            end else if (which_test >= 5'd9) begin
                matrix_id = which_test - 5'd9;
                if (index < 16'd32)
                    message_byte = rho_byte[index[4:0]];
                else if (index == 16'd32)
                    message_byte = {7'd0, matrix_id[0]}; // j
                else
                    message_byte = {7'd0, matrix_id[1]}; // i
            end else if (which_test == 5'd8) begin
                if (index < 16'd32)
                    message_byte = runtime_seed_valid_q ?
                                   runtime_seed_d_q[index*8 +: 8] :
                                   index[7:0];
                else
                    message_byte = runtime_seed_valid_q ?
                                   runtime_seed_k_q : 8'd0;
            end else if (which_test == 5'd4) begin
                case (index)
                    16'd0: message_byte = 8'h61;
                    16'd1: message_byte = 8'h62;
                    default: message_byte = 8'h63;
                endcase
            end else begin
                message_byte = index[7:0];
            end
        end
    endfunction

    function automatic [7:0] expected_byte;
        input [4:0] which_test;
        input [15:0] index;
        begin
            case (which_test)
                5'd0: expected_byte = SHA3_256_EMPTY_LE[index*8 +: 8];
                5'd1: expected_byte = SHA3_512_EMPTY_LE[index*8 +: 8];
                5'd2: expected_byte = SHAKE128_EMPTY_32_LE[index*8 +: 8];
                5'd3: expected_byte = SHAKE256_EMPTY_64_LE[index*8 +: 8];
                5'd4: expected_byte = SHA3_256_ABC_LE[index*8 +: 8];
                5'd5: expected_byte = SHAKE128_SEQ200_32_LE[index*8 +: 8];
                5'd6: expected_byte = SHAKE128_EMPTY_200_LE[index*8 +: 8];
                default: expected_byte = SHA3_512_SEQ72_LE[index*8 +: 8];
            endcase
        end
    endfunction

    function automatic [7:0] expected_g_byte;
        input [15:0] index;
        begin
            expected_g_byte = G_DK_LE[index*8 +: 8];
        end
    endfunction

    function automatic [31:0] digest_step;
        input [31:0] digest_in;
        input [11:0] value;
        begin
            digest_step = {digest_in[30:0], digest_in[31]} ^
                          {20'd0, value};
        end
    endfunction

    function automatic [31:0] byte_digest_step;
        input [31:0] digest_in;
        input [7:0] value;
        begin
            byte_digest_step = {digest_in[30:0], digest_in[31]} ^
                               {24'd0, value};
        end
    endfunction

    wire sponge_in_ready;
    wire sponge_out_valid;
    wire [7:0] sponge_out_byte;
    wire sponge_out_last;
    wire sponge_busy;
    wire sponge_done;
    wire sponge_error;
    wire sponge_in_valid = (state == S_RUN) &&
                           (feed_index < sponge_message_len);
    wire [7:0] sponge_in_byte = message_byte(test_index, feed_index);

    wire parser_coeff0_valid;
    wire [11:0] parser_coeff0;
    wire parser_coeff1_valid;
    wire [11:0] parser_coeff1;
    wire [8:0] parser_accepted_count;
    wire parser_done;

    // Parser valids and accepted_count are registered together. When the
    // valids are visible here, accepted_count already includes this cycle's
    // one or two coefficients, so subtract them to recover the write base.
    wire [8:0] matrix_accepted_before = parser_accepted_count -
        parser_coeff0_valid - parser_coeff1_valid;
    wire [9:0] matrix_load_base =
        {matrix_entry, 8'd0} + {1'b0, matrix_accepted_before};
    assign matrix_load0_valid = matrix_test && parser_coeff0_valid;
    assign matrix_load0_addr = matrix_load_base;
    assign matrix_load0_data = parser_coeff0;
    assign matrix_load1_valid = matrix_test && parser_coeff1_valid;
    assign matrix_load1_addr = matrix_load_base + parser_coeff0_valid;
    assign matrix_load1_data = parser_coeff1;
    assign noise_load_valid = prf_test && sponge_out_valid;
    assign noise_load_addr = (prf_nonce * 10'd192) +
                              output_index[9:0];
    assign noise_load_data = sponge_out_byte;
    assign rho_load_valid = g_test && sponge_out_valid &&
                            (output_index < 16'd32);
    assign rho_load_addr = output_index[4:0];
    assign rho_load_data = sponge_out_byte;

    wire [23:0] pair_bytes;
    wire [15:0] pair_decoded [0:1];

    mlkem512_byte_pack_block #(.D(12), .COEFFS(2), .BYTES(3))
    u_matrix_pack (
        .coeff(pair_coeff),
        .bytes_le(pair_bytes)
    );

    mlkem512_byte_unpack_block #(.D(12), .COEFFS(2), .BYTES(3))
    u_matrix_unpack (
        .bytes_le(pair_bytes),
        .coeff(pair_decoded)
    );

    mlkem512_sample_ntt_parser u_sample_ntt_parser (
        .clk(clk),
        .rst_n(rst_n),
        .start(parser_start),
        .in_valid(sponge_out_valid && matrix_test),
        .in_byte(sponge_out_byte),
        .coeff0_valid(parser_coeff0_valid),
        .coeff0(parser_coeff0),
        .coeff1_valid(parser_coeff1_valid),
        .coeff1(parser_coeff1),
        .accepted_count(parser_accepted_count),
        .done(parser_done)
    );

    assign sponge_ext_start = sponge_start;
    assign sponge_ext_mode = sponge_mode;
    assign sponge_ext_message_len = sponge_message_len;
    assign sponge_ext_output_len = sponge_output_len;
    assign sponge_ext_in_valid = sponge_in_valid;
    assign sponge_ext_in_byte = sponge_in_byte;
    assign sponge_ext_out_ready = 1'b1;

    generate
        if (USE_EXTERNAL_SPONGE) begin : g_external_sponge
            assign sponge_in_ready = sponge_ext_in_ready;
            assign sponge_out_valid = sponge_ext_out_valid;
            assign sponge_out_byte = sponge_ext_out_byte;
            assign sponge_out_last = sponge_ext_out_last;
            assign sponge_busy = sponge_ext_busy;
            assign sponge_done = sponge_ext_done;
            assign sponge_error = sponge_ext_error;
        end else begin : g_private_sponge
            keccak_sponge_stream u_sponge (
                .clk(clk), .rst_n(rst_n), .zeroize(1'b0),
                .start(sponge_start),
                .mode(sponge_mode), .message_len(sponge_message_len),
                .output_len(sponge_output_len), .in_valid(sponge_in_valid),
                .in_byte(sponge_in_byte), .in_ready(sponge_in_ready),
                .out_valid(sponge_out_valid), .out_byte(sponge_out_byte),
                .out_last(sponge_out_last), .out_ready(1'b1),
                .busy(sponge_busy), .done(sponge_done), .error(sponge_error)
            );
        end
    endgenerate

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= S_IDLE;
            test_index <= 4'd0;
            feed_index <= 16'd0;
            output_index <= 16'd0;
            test_ok <= 1'b0;
            aggregate_ok <= 1'b0;
            sponge_start <= 1'b0;
            parser_start <= 1'b0;
            sample_pending_valid <= 1'b0;
            sample_pending <= 12'd0;
            pair_check_pending <= 1'b0;
            pair_coeff[0] <= 16'd0;
            pair_coeff[1] <= 16'd0;
            serialization_ok <= 1'b0;
            busy <= 1'b0;
            done <= 1'b0;
            pass <= 1'b0;
            sha3_prefix <= 32'd0;
            shake_prefix <= 32'd0;
            matrix_digest <= 32'd0;
            serial_digest <= 32'd0;
            prf_digest <= 32'd0;
            g_digest <= 32'd0;
            cycles <= 16'd0;
            runtime_seed_valid_q <= 1'b0;
            runtime_seed_d_q <= 256'd0;
            runtime_seed_k_q <= 8'd0;
        end else begin
            done <= 1'b0;
            sponge_start <= 1'b0;
            parser_start <= 1'b0;
            if (busy && cycles != 16'hFFFF)
                cycles <= cycles + 16'd1;

            // Check every emitted 12-bit serialization pair one cycle after
            // it was registered, then fold all three bytes into a fingerprint.
            if (pair_check_pending) begin
                if ((pair_decoded[0] != pair_coeff[0]) ||
                    (pair_decoded[1] != pair_coeff[1]) ||
                    (pair_decoded[0] >= 16'd3329) ||
                    (pair_decoded[1] >= 16'd3329))
                    serialization_ok <= 1'b0;
                serial_digest <= byte_digest_step(
                    byte_digest_step(
                        byte_digest_step(serial_digest, pair_bytes[7:0]),
                        pair_bytes[15:8]),
                    pair_bytes[23:16]);
                pair_check_pending <= 1'b0;
            end

            // The parser can emit zero, one or two coefficients per triplet.
            // Pair them without a coefficient RAM; matrix entries still run
            // serially through the single SHAKE engine.
            if (parser_coeff0_valid || parser_coeff1_valid) begin
                if (parser_coeff0_valid && parser_coeff1_valid)
                    matrix_digest <= digest_step(
                        digest_step(matrix_digest, parser_coeff0),
                        parser_coeff1);
                else if (parser_coeff0_valid)
                    matrix_digest <= digest_step(matrix_digest, parser_coeff0);
                else
                    matrix_digest <= digest_step(matrix_digest, parser_coeff1);

                if (sample_pending_valid) begin
                    pair_coeff[0] <= {4'd0, sample_pending};
                    pair_coeff[1] <= {4'd0,
                        parser_coeff0_valid ? parser_coeff0 : parser_coeff1};
                    pair_check_pending <= 1'b1;
                    if (parser_coeff0_valid && parser_coeff1_valid) begin
                        sample_pending <= parser_coeff1;
                        sample_pending_valid <= 1'b1;
                    end else begin
                        sample_pending_valid <= 1'b0;
                    end
                end else if (parser_coeff0_valid && parser_coeff1_valid) begin
                    pair_coeff[0] <= {4'd0, parser_coeff0};
                    pair_coeff[1] <= {4'd0, parser_coeff1};
                    pair_check_pending <= 1'b1;
                end else begin
                    sample_pending <= parser_coeff0_valid ?
                                      parser_coeff0 : parser_coeff1;
                    sample_pending_valid <= 1'b1;
                end
            end

            case (state)
                S_IDLE: begin
                    busy <= 1'b0;
                    if (start) begin
                        busy <= 1'b1;
                        pass <= 1'b0;
                        runtime_seed_valid_q <= runtime_seed_valid;
                        runtime_seed_d_q <= runtime_seed_d;
                        runtime_seed_k_q <= runtime_seed_k;
                        test_index <= 4'd0;
                        aggregate_ok <= 1'b1;
                        sha3_prefix <= 32'd0;
                        shake_prefix <= 32'd0;
                        cycles <= 16'd0;
                        state <= S_START;
                    end
                end

                S_START: begin
                    feed_index <= 16'd0;
                    output_index <= 16'd0;
                    test_ok <= 1'b1;
                    sponge_start <= 1'b1;
                    sample_pending_valid <= 1'b0;
                    pair_check_pending <= 1'b0;
                    if (matrix_test)
                        parser_start <= 1'b1;
                    if (test_index == 5'd9) begin
                        matrix_digest <= MATRIX_DIGEST_INIT;
                        serial_digest <= SERIAL_DIGEST_INIT;
                        serialization_ok <= 1'b1;
                    end
                    if (test_index == 5'd13)
                        prf_digest <= 32'h50524631;
                    if (g_test)
                        g_digest <= G_DIGEST_INIT;
                    state <= S_RUN;
                end

                S_RUN: begin
                    if (sponge_in_valid && sponge_in_ready)
                        feed_index <= feed_index + 16'd1;

                    if (sponge_out_valid) begin
                        if (!matrix_test && !prf_test && !g_test &&
                            (sponge_out_byte !=
                             expected_byte(test_index, output_index)))
                            test_ok <= 1'b0;
                        if (g_test && !runtime_seed_valid_q &&
                            (sponge_out_byte != expected_g_byte(output_index)))
                            test_ok <= 1'b0;

                        if (test_index == 5'd0 && output_index < 16'd4)
                            sha3_prefix[31-output_index*8 -: 8] <= sponge_out_byte;
                        if (test_index == 5'd2 && output_index < 16'd4)
                            shake_prefix[31-output_index*8 -: 8] <= sponge_out_byte;
                        if (prf_test)
                            prf_digest <= byte_digest_step(prf_digest,
                                                          sponge_out_byte);
                        if (g_test) begin
                            g_digest <= byte_digest_step(g_digest, sponge_out_byte);
                            if (output_index < 16'd32)
                                rho_byte[output_index[4:0]] <= sponge_out_byte;
                            else
                                sigma_byte[output_index[4:0]] <= sponge_out_byte;
                        end

                        output_index <= output_index + 16'd1;
                    end

                    if (sponge_done) begin
                        if (matrix_test) begin
                            aggregate_ok <= aggregate_ok &&
                                !sponge_error && parser_done &&
                                (parser_accepted_count == 9'd256) &&
                                !sample_pending_valid && !pair_check_pending &&
                                serialization_ok &&
                                (feed_index == sponge_message_len) &&
                                (output_index == sponge_output_len);
                        end else if (prf_test) begin
                            aggregate_ok <= aggregate_ok && !sponge_error &&
                                (feed_index == sponge_message_len) &&
                                (output_index == sponge_output_len);
                        end else begin
                            aggregate_ok <= aggregate_ok && test_ok &&
                                !sponge_error &&
                                (feed_index == sponge_message_len) &&
                                (output_index == sponge_output_len);
                        end

                        if (test_index == 5'd16) begin
                            pass <= aggregate_ok && !sponge_error &&
                                (feed_index == sponge_message_len) &&
                                (output_index == sponge_output_len) &&
                                (runtime_seed_valid_q ||
                                 ((g_digest == EXPECTED_G_DIGEST) &&
                                  (matrix_digest == EXPECTED_MATRIX_DIGEST) &&
                                  (serial_digest == EXPECTED_SERIAL_DIGEST) &&
                                  (prf_digest == EXPECTED_PRF_DIGEST)));
                            state <= S_DONE;
                        end else begin
                            test_index <= test_index + 4'd1;
                            state <= S_START;
                        end
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
