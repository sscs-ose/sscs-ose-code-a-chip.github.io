import mlkem512_pkg::*;

// Permanent K-PKE ciphertext boundary: 512 u coefficients are Compress_10 +
// ByteEncode_10 into 640 bytes, followed by 256 v coefficients using
// Compress_4 + ByteEncode_4 into 128 bytes.  The 768-byte result is retained
// in M20K and fingerprinted from RAM readback.  This block deliberately owns
// no matrix/NTT/noise generation and therefore is not K-PKE.Encrypt by itself.
module mlkem512_ciphertext_codec #(
    parameter [31:0] EXPECTED_DIGEST_A = 32'h09507BB7,
    parameter [31:0] EXPECTED_DIGEST_B = 32'hDD56A4C3
) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        load_clear,
    input  wire        load_valid,
    input  wire [9:0]  load_index,
    input  wire [11:0] load_coeff,
    input  wire        check_expected,
    input  wire        start,
    // C3 transport re-imports the public ciphertext byte image after it has
    // crossed SPI.  The original coefficient RAM is deliberately retained so
    // decode can compare every imported coefficient with the sender image.
    input  wire        import_clear,
    input  wire        import_valid,
    input  wire [9:0]  import_addr,
    input  wire [7:0]  import_data,
    input  wire        import_start,
    // Normal C3 transport compares decoded coefficients with the sender-side
    // source image.  C4 sets this low only for a complete untrusted public
    // ciphertext so Algorithm 18 can perform implicit rejection itself.
    input  wire        import_compare_source,
    output reg         busy,
    output reg         done,
    output reg         pass,
    output reg [31:0]  digest_a,
    output reg [31:0]  digest_b,
    // Internal decrypt-preparation evidence.  This is the fingerprint of
    // the 768 coefficients after ByteDecode + Decompress, not a key or a
    // message.  It is kept separate from the historical ciphertext digests.
    output reg [31:0]  decode_digest,
    output reg         decode_pass,
    output reg [15:0]  cycles,
    output reg [9:0]   loaded_coeffs,
    output reg [9:0]   imported_bytes,
    input  wire [9:0]  ct_read_addr,
    output wire [7:0]  ct_read_data,
    input  wire [9:0]  decoded_read_addr,
    output wire [11:0] decoded_read_data
);
    localparam [4:0]
        ST_IDLE      = 5'd0,
        ST_U_REQ     = 5'd1,
        ST_U_WAIT    = 5'd2,
        ST_U_CAPTURE = 5'd3,
        ST_U_WRITE   = 5'd4,
        ST_V_REQ     = 5'd5,
        ST_V_WAIT    = 5'd6,
        ST_V_CAPTURE = 5'd7,
        ST_V_WRITE   = 5'd8,
        ST_RB_REQ    = 5'd9,
        ST_RB_WAIT   = 5'd10,
        ST_RB_ACC    = 5'd11,
        ST_D_REQ     = 5'd12,
        ST_D_WAIT    = 5'd13,
        ST_D_ACC     = 5'd14,
        ST_D_CMP_REQ = 5'd15,
        ST_D_CMP_WAIT= 5'd16,
        ST_D_CMP_ACC = 5'd17;

`ifdef TRUSTEDGE_ASIC_SRAM
    wire [11:0] coeff_q;
    wire [7:0] ct_ram_q;
    wire [11:0] decoded_ram_q;
`else
    (* ramstyle = "M20K, no_rw_check" *) reg [11:0] coeff_ram [0:767];
    (* ramstyle = "M20K, no_rw_check" *) reg [7:0] ciphertext_ram [0:767];
    (* ramstyle = "M20K, no_rw_check" *) reg [11:0] decoded_coeff_ram [0:767];
    reg [11:0] coeff_q;
    reg [7:0] ct_ram_q;
    reg [11:0] decoded_ram_q;
`endif

    reg [4:0] state;
    reg load_error;
    reg [9:0] proc_index;
    reg [2:0] group_sub;
    reg [2:0] write_sub;
    reg [9:0] ct_write_addr;
    reg [9:0] rb_addr;
    reg [39:0] pack_bits;
    reg [9:0] decode_ct_addr;
    reg [9:0] decode_coeff_base;
    reg [2:0] decode_byte_sub;
    reg [2:0] decode_cmp_sub;
    reg [39:0] decode_pack;
    reg decode_v_phase;
    reg decode_error;
    reg import_error;

    assign ct_read_data = ct_ram_q;
    assign decoded_read_data = decoded_ram_q;

    function automatic [9:0] compress10;
        input [11:0] x;
        reg [21:0] numerator;
        reg [39:0] scaled;
        begin
            // Exact for every canonical x in [0,3328]: division by q=3329
            // is replaced by a constant reciprocal multiply. Exhaustive TB
            // compares all relevant codec outputs; DSPs are abundant here.
            numerator = ({10'd0, x} << 10) + 22'd1664;
            scaled = numerator * 18'd161271;
            compress10 = scaled[38:29];
        end
    endfunction

    function automatic [3:0] compress4;
        input [11:0] x;
        reg [15:0] numerator;
        reg [24:0] scaled;
        begin
            numerator = ({4'd0, x} << 4) + 16'd1664;
            scaled = numerator * 9'd315;
            compress4 = scaled[23:20];
        end
    endfunction

    function automatic [11:0] decompress10;
        input [9:0] x;
        reg [31:0] rounded;
        begin
            rounded = (({22'd0, x} * MLKEM_Q) + 32'd512) >> 10;
            decompress10 = rounded[11:0];
        end
    endfunction

    function automatic [11:0] decompress4;
        input [3:0] x;
        reg [31:0] rounded;
        begin
            rounded = (({28'd0, x} * MLKEM_Q) + 32'd8) >> 4;
            decompress4 = rounded[11:0];
        end
    endfunction

    function automatic [31:0] digest_a_step;
        input [31:0] current;
        input [7:0] value;
        begin
            digest_a_step = {current[30:0], current[31]} ^ {24'd0, value};
        end
    endfunction

    function automatic [31:0] digest_b_step;
        input [31:0] current;
        input [7:0] value;
        begin
            digest_b_step = {current[26:0], current[31:27]} + {24'd0, value};
        end
    endfunction

    function automatic [31:0] decode_digest_step;
        input [31:0] current;
        input [11:0] value;
        begin
            decode_digest_step = {current[28:0], current[31:29]} ^
                                 {20'd0, value};
        end
    endfunction

    wire [9:0] coeff_compressed10 = compress10(coeff_q);
    wire [3:0] coeff_compressed4 = compress4(coeff_q);
    wire [39:0] u_pack_next = pack_bits |
        ({30'd0, coeff_compressed10} << (group_sub * 10));
    wire [39:0] v_pack_next = pack_bits |
        ({36'd0, coeff_compressed4} << (group_sub * 4));
    wire [31:0] digest_a_next = digest_a_step(digest_a, ct_ram_q);
    wire [31:0] digest_b_next = digest_b_step(digest_b, ct_ram_q);
    wire [39:0] decode_pack_next = decode_pack |
        ({32'd0, ct_ram_q} << (decode_byte_sub * 8));
    wire [9:0] decoded_u10 = decode_pack[decode_cmp_sub * 10 +: 10];
    wire [3:0] decoded_v4 = decode_pack[decode_cmp_sub * 4 +: 4];
    wire [11:0] decoded_coeff = decode_v_phase ? decompress4(decoded_v4) :
                                                  decompress10(decoded_u10);
    wire [11:0] canonical_source_coeff = decode_v_phase ?
        decompress4(compress4(coeff_q)) : decompress10(compress10(coeff_q));

`ifdef TRUSTEDGE_ASIC_SRAM
    // The macro read launches on the falling edge.  Capture both sides during
    // the existing WAIT cycle so CMP_ACC does not place Compress+Decompress
    // and the compare on the remaining half-cycle.  No FSM state or protocol
    // cycle is added; the inferred-M20K/default path below remains unchanged.
    reg [11:0] decoded_coeff_cmp_q;
    reg [11:0] canonical_source_coeff_cmp_q;
    wire [11:0] compare_decoded_coeff = decoded_coeff_cmp_q;
    wire [11:0] compare_source_coeff = canonical_source_coeff_cmp_q;
`else
    wire [11:0] compare_decoded_coeff = decoded_coeff;
    wire [11:0] compare_source_coeff = canonical_source_coeff;
`endif
    wire decode_mismatch = (compare_decoded_coeff != compare_source_coeff);
    wire [31:0] decode_digest_next = decode_digest_step(decode_digest,
                                                          compare_decoded_coeff);

    // Present Quartus with exactly one synchronous write port.  Keeping the
    // import path and the encoder FSM as separate array assignments caused the
    // 768x8 image to be implemented as ALM registers despite ramstyle=M20K.
    reg        ct_mem_we;
    reg [9:0]  ct_mem_waddr;
    reg [7:0]  ct_mem_wdata;
    always @* begin
        ct_mem_we    = 1'b0;
        ct_mem_waddr = 10'd0;
        ct_mem_wdata = 8'd0;
        if (import_valid && !busy && !import_error &&
            (import_addr == imported_bytes) && (imported_bytes < 10'd768)) begin
            ct_mem_we    = 1'b1;
            ct_mem_waddr = import_addr;
            ct_mem_wdata = import_data;
        end else if (busy && (state == ST_U_WRITE)) begin
            ct_mem_we    = 1'b1;
            ct_mem_waddr = ct_write_addr;
            case (write_sub)
                3'd0: ct_mem_wdata = pack_bits[7:0];
                3'd1: ct_mem_wdata = pack_bits[15:8];
                3'd2: ct_mem_wdata = pack_bits[23:16];
                3'd3: ct_mem_wdata = pack_bits[31:24];
                default: ct_mem_wdata = pack_bits[39:32];
            endcase
        end else if (busy && (state == ST_V_WRITE)) begin
            ct_mem_we    = 1'b1;
            ct_mem_waddr = ct_write_addr;
            ct_mem_wdata = pack_bits[7:0];
        end
    end

`ifndef TRUSTEDGE_ASIC_SRAM
    always @(posedge clk) begin
        if (ct_mem_we)
            ciphertext_ram[ct_mem_waddr] <= ct_mem_wdata;
    end

    // Synchronous read ports preserve M20K inference. During processing the
    // ciphertext port is reserved for the readback audit; after done it is a
    // public-byte read port for the future K-PKE/ML-KEM wrapper.
    always @(posedge clk) begin
        decoded_ram_q <= decoded_coeff_ram[decoded_read_addr];
        if (busy && ((state == ST_U_REQ) || (state == ST_U_WAIT) ||
                     (state == ST_V_REQ) || (state == ST_V_WAIT)))
            coeff_q <= coeff_ram[proc_index];
        else if (busy && ((state == ST_D_CMP_REQ) ||
                          (state == ST_D_CMP_WAIT) ||
                          (state == ST_D_CMP_ACC)))
            coeff_q <= coeff_ram[decode_coeff_base + decode_cmp_sub];
        if (busy && ((state == ST_RB_REQ) || (state == ST_RB_WAIT) ||
                     (state == ST_RB_ACC)))
            ct_ram_q <= ciphertext_ram[rb_addr];
        else if (busy && ((state == ST_D_REQ) || (state == ST_D_WAIT) ||
                          (state == ST_D_ACC)))
            ct_ram_q <= ciphertext_ram[decode_ct_addr];
        else if (!busy)
            ct_ram_q <= ciphertext_ram[ct_read_addr];
    end
`else
    // All three codec arrays are phase-exclusive single-port memories.  A
    // write owns the port; read data from that cycle is deliberately ignored.
    wire coeff_mem_we = load_valid && !busy && !load_error &&
                        (load_index == loaded_coeffs) &&
                        (loaded_coeffs < 10'd768);
    wire [9:0] coeff_mem_raddr =
        (busy && ((state == ST_D_CMP_REQ) ||
                  (state == ST_D_CMP_WAIT) ||
                  (state == ST_D_CMP_ACC))) ?
        (decode_coeff_base + decode_cmp_sub) : proc_index;
    wire [9:0] coeff_mem_addr = coeff_mem_we ? load_index : coeff_mem_raddr;

    wire [9:0] ct_mem_raddr =
        (busy && ((state == ST_RB_REQ) || (state == ST_RB_WAIT) ||
                  (state == ST_RB_ACC))) ? rb_addr :
        (busy && ((state == ST_D_REQ) || (state == ST_D_WAIT) ||
                  (state == ST_D_ACC))) ? decode_ct_addr : ct_read_addr;
    wire [9:0] ct_mem_addr = ct_mem_we ? ct_mem_waddr : ct_mem_raddr;

    wire decoded_mem_we = busy && (state == ST_D_CMP_ACC);
    wire [9:0] decoded_mem_addr = decoded_mem_we ?
        (decode_coeff_base + decode_cmp_sub) : decoded_read_addr;

    te_sram_1rw #(.WIDTH(12), .DEPTH(768), .ADDR_WIDTH(10))
        u_coeff_sram (
            .clk(clk), .we(coeff_mem_we), .addr(coeff_mem_addr),
            .wdata(load_coeff), .rdata(coeff_q)
        );
    te_sram_1rw #(.WIDTH(8), .DEPTH(768), .ADDR_WIDTH(10))
        u_ciphertext_sram (
            .clk(clk), .we(ct_mem_we), .addr(ct_mem_addr),
            .wdata(ct_mem_wdata), .rdata(ct_ram_q)
        );
    te_sram_1rw #(.WIDTH(12), .DEPTH(768), .ADDR_WIDTH(10))
        u_decoded_coeff_sram (
            .clk(clk), .we(decoded_mem_we), .addr(decoded_mem_addr),
            .wdata(compare_decoded_coeff), .rdata(decoded_ram_q)
        );
`endif

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= ST_IDLE;
            busy <= 1'b0;
            done <= 1'b0;
            pass <= 1'b0;
            digest_a <= 32'd0;
            digest_b <= 32'd0;
            decode_digest <= 32'd0;
            decode_pass <= 1'b0;
            cycles <= 16'd0;
            loaded_coeffs <= 10'd0;
            imported_bytes <= 10'd0;
            load_error <= 1'b0;
            import_error <= 1'b0;
            proc_index <= 10'd0;
            group_sub <= 3'd0;
            write_sub <= 3'd0;
            ct_write_addr <= 10'd0;
            rb_addr <= 10'd0;
            pack_bits <= 40'd0;
            decode_ct_addr <= 10'd0;
            decode_coeff_base <= 10'd0;
            decode_byte_sub <= 3'd0;
            decode_cmp_sub <= 3'd0;
            decode_pack <= 40'd0;
            decode_v_phase <= 1'b0;
            decode_error <= 1'b0;
`ifdef TRUSTEDGE_ASIC_SRAM
            decoded_coeff_cmp_q <= 12'd0;
            canonical_source_coeff_cmp_q <= 12'd0;
`endif
        end else begin
            done <= 1'b0;

            if (load_clear && !busy) begin
                loaded_coeffs <= 10'd0;
                load_error <= 1'b0;
            end else if (load_valid && !busy) begin
                if (!load_error && (load_index == loaded_coeffs) &&
                    (loaded_coeffs < 10'd768)) begin
`ifndef TRUSTEDGE_ASIC_SRAM
                    coeff_ram[load_index] <= load_coeff;
`endif
                    loaded_coeffs <= loaded_coeffs + 10'd1;
                end else begin
                    load_error <= 1'b1;
                end
            end

            if (import_clear && !busy) begin
                imported_bytes <= 10'd0;
                import_error <= 1'b0;
            end else if (import_valid && !busy) begin
                if (!import_error && (import_addr == imported_bytes) &&
                    (imported_bytes < 10'd768)) begin
                    imported_bytes <= imported_bytes + 10'd1;
                end else begin
                    import_error <= 1'b1;
                end
            end

            if (busy && (cycles != 16'hFFFF))
                cycles <= cycles + 16'd1;

            case (state)
                ST_IDLE: begin
                    if (import_start) begin
                        // pass is meaningful only with done.  Do not clear it
                        // on a valid launch: keeping that write out of the
                        // IDLE decode avoids using the same state bit as both
                        // reset polarities after synthesis.  The completion
                        // path overwrites pass before asserting done.
                        digest_a <= 32'd0;
                        digest_b <= 32'd0;
                        decode_digest <= 32'h44454331;
                        decode_pass <= 1'b0;
                        cycles <= 16'd0;
                        if ((imported_bytes == 10'd768) && !import_error &&
                            (loaded_coeffs == 10'd768) && !load_error) begin
                            busy <= 1'b1;
                            // Preserve ct_write_addr=768 so the ordinary final
                            // acceptance rule also applies to imported bytes.
                            ct_write_addr <= 10'd768;
                            decode_ct_addr <= 10'd0;
                            decode_coeff_base <= 10'd0;
                            decode_byte_sub <= 3'd0;
                            decode_cmp_sub <= 3'd0;
                            decode_pack <= 40'd0;
                            decode_v_phase <= 1'b0;
                            decode_error <= 1'b0;
                            state <= ST_D_REQ;
                        end else begin
                            busy <= 1'b0;
                            pass <= 1'b0;
                            done <= 1'b1;
                        end
                    end else if (start) begin
                        // See import_start above.  Invalid launches still
                        // explicitly return pass=0 together with done.
                        digest_a <= 32'd0;
                        digest_b <= 32'd0;
                        decode_digest <= 32'd0;
                        decode_pass <= 1'b0;
                        cycles <= 16'd0;
                        if ((loaded_coeffs == 10'd768) && !load_error) begin
                            busy <= 1'b1;
                            proc_index <= 10'd0;
                            group_sub <= 3'd0;
                            ct_write_addr <= 10'd0;
                            pack_bits <= 40'd0;
                            state <= ST_U_REQ;
                        end else begin
                            busy <= 1'b0;
                            pass <= 1'b0;
                            done <= 1'b1;
                        end
                    end
                end

                ST_U_REQ: state <= ST_U_WAIT;
                ST_U_WAIT: state <= ST_U_CAPTURE;
                ST_U_CAPTURE: begin
                    pack_bits <= u_pack_next;
                    if (group_sub == 3'd3) begin
                        group_sub <= 3'd0;
                        write_sub <= 3'd0;
                        state <= ST_U_WRITE;
                    end else begin
                        group_sub <= group_sub + 3'd1;
                        proc_index <= proc_index + 10'd1;
                        state <= ST_U_REQ;
                    end
                end

                ST_U_WRITE: begin
                    ct_write_addr <= ct_write_addr + 10'd1;
                    if (write_sub == 3'd4) begin
                        pack_bits <= 40'd0;
                        if (proc_index == 10'd511) begin
                            proc_index <= 10'd512;
                            group_sub <= 3'd0;
                            state <= ST_V_REQ;
                        end else begin
                            proc_index <= proc_index + 10'd1;
                            state <= ST_U_REQ;
                        end
                    end else begin
                        write_sub <= write_sub + 3'd1;
                    end
                end

                ST_V_REQ: state <= ST_V_WAIT;
                ST_V_WAIT: state <= ST_V_CAPTURE;
                ST_V_CAPTURE: begin
                    pack_bits <= v_pack_next;
                    if (group_sub == 3'd1) begin
                        group_sub <= 3'd0;
                        state <= ST_V_WRITE;
                    end else begin
                        group_sub <= 3'd1;
                        proc_index <= proc_index + 10'd1;
                        state <= ST_V_REQ;
                    end
                end

                ST_V_WRITE: begin
                    ct_write_addr <= ct_write_addr + 10'd1;
                    pack_bits <= 40'd0;
                    if (proc_index == 10'd767) begin
                        // Decode the completed byte image before accepting
                        // it. This is the codec half of K-PKE.Decrypt:
                        // ByteDecode_10/4 + Decompress_10/4.  It intentionally
                        // does not yet perform s^T*u, InvNTT or message recovery.
                        decode_ct_addr <= 10'd0;
                        decode_coeff_base <= 10'd0;
                        decode_byte_sub <= 3'd0;
                        decode_cmp_sub <= 3'd0;
                        decode_pack <= 40'd0;
                        decode_v_phase <= 1'b0;
                        decode_error <= 1'b0;
                        decode_digest <= 32'h44454331;
                        state <= ST_D_REQ;
                    end else begin
                        proc_index <= proc_index + 10'd1;
                        state <= ST_V_REQ;
                    end
                end

                // Ciphertext RAM has a synchronous read port.  Collect one
                // 40-bit U group (five bytes) or one 8-bit V group, then use
                // the independent coefficient-RAM port to check every
                // decoded value against Compress(source) followed by
                // Decompress(source). This catches pack order, RAM read and
                // decompression errors without exposing ciphertext or key data.
                ST_D_REQ: state <= ST_D_WAIT;
                ST_D_WAIT: state <= ST_D_ACC;
                ST_D_ACC: begin
                    decode_pack <= decode_pack_next;
                    if ((!decode_v_phase && (decode_byte_sub == 3'd4)) ||
                        (decode_v_phase && (decode_byte_sub == 3'd0))) begin
                        decode_cmp_sub <= 3'd0;
                        state <= ST_D_CMP_REQ;
                    end else begin
                        decode_ct_addr <= decode_ct_addr + 10'd1;
                        decode_byte_sub <= decode_byte_sub + 3'd1;
                        state <= ST_D_REQ;
                    end
                end

                ST_D_CMP_REQ: state <= ST_D_CMP_WAIT;
                ST_D_CMP_WAIT: begin
`ifdef TRUSTEDGE_ASIC_SRAM
                    decoded_coeff_cmp_q <= decoded_coeff;
                    canonical_source_coeff_cmp_q <= canonical_source_coeff;
`endif
                    state <= ST_D_CMP_ACC;
                end
                ST_D_CMP_ACC: begin
                    decode_digest <= decode_digest_next;
`ifndef TRUSTEDGE_ASIC_SRAM
                    decoded_coeff_ram[decode_coeff_base + decode_cmp_sub] <=
                        decoded_coeff;
`endif
                    if (decode_mismatch && import_compare_source)
                        decode_error <= 1'b1;
                    if (!decode_v_phase && (decode_cmp_sub == 3'd3)) begin
                        if (decode_coeff_base == 10'd508) begin
                            decode_v_phase <= 1'b1;
                            decode_ct_addr <= 10'd640;
                            decode_coeff_base <= 10'd512;
                        end else begin
                            decode_ct_addr <= decode_ct_addr + 10'd1;
                            decode_coeff_base <= decode_coeff_base + 10'd4;
                        end
                        decode_byte_sub <= 3'd0;
                        decode_cmp_sub <= 3'd0;
                        decode_pack <= 40'd0;
                        state <= ST_D_REQ;
                    end else if (decode_v_phase && (decode_cmp_sub == 3'd1)) begin
                        if (decode_coeff_base == 10'd766) begin
                            decode_pass <= !(decode_error ||
                                             (decode_mismatch &&
                                              import_compare_source));
                            rb_addr <= 10'd0;
                            digest_a <= 32'h43543131;
                            digest_b <= 32'h4B504B45;
                            state <= ST_RB_REQ;
                        end else begin
                            decode_ct_addr <= decode_ct_addr + 10'd1;
                            decode_coeff_base <= decode_coeff_base + 10'd2;
                            decode_byte_sub <= 3'd0;
                            decode_cmp_sub <= 3'd0;
                            decode_pack <= 40'd0;
                            state <= ST_D_REQ;
                        end
                    end else begin
                        decode_cmp_sub <= decode_cmp_sub + 3'd1;
                        state <= ST_D_CMP_REQ;
                    end
                end

                ST_RB_REQ: state <= ST_RB_WAIT;
                ST_RB_WAIT: state <= ST_RB_ACC;
                ST_RB_ACC: begin
                    digest_a <= digest_a_next;
                    digest_b <= digest_b_next;
                    if (rb_addr == 10'd767) begin
                        busy <= 1'b0;
                        done <= 1'b1;
                        pass <= (!check_expected ||
                                 ((digest_a_next == EXPECTED_DIGEST_A) &&
                                  (digest_b_next == EXPECTED_DIGEST_B))) &&
                                (ct_write_addr == 10'd768) && decode_pass;
                        state <= ST_IDLE;
                    end else begin
                        rb_addr <= rb_addr + 10'd1;
                        state <= ST_RB_WAIT;
                    end
                end

                default: begin
                    state <= ST_IDLE;
                    busy <= 1'b0;
                    done <= 1'b1;
                    pass <= 1'b0;
                end
            endcase
        end
    end
endmodule
