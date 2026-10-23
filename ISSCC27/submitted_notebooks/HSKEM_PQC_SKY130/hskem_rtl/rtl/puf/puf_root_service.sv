// HSM-4D1 private RO-PUF root reconstruction service.
//
// Compact opcode 0x3A/0x3B and subcommand 0x40 are retained, but D0 raw mode
// 0x01 is intentionally disabled in this artifact.  Only a public 32-byte
// helper envelope and status leave the FPGA; raw/corrected PUF material and the
// volatile root key never enter response_data.
module puf_root_service #(
    parameter EXTERNAL_HMAC = 1'b0
) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire         cmd_valid,
    input  wire         header_valid,
    input  wire         provision_enable,
    input  wire         zeroize,
    input  wire         transport_ready,
    input  wire [7:0]   transport_error,
    input  wire [63:0]  chip_id,
    input  wire [7:0]   api_version,
    input  wire [7:0]   subcmd,
    input  wire [7:0]   flags,
    input  wire [31:0]  counter,
    input  wire [7:0]   data_len,
    input  wire [255:0] data,
    output reg          done,
    output reg  [7:0]   response_len,
    output reg  [255:0] response_data,
    output reg          root_ready,
    output reg  [255:0] root_key,
    output wire         hmac_req_start,
    output wire         hmac_req_scrub,
    output wire [255:0] hmac_req_key,
    output wire [255:0] hmac_req_message,
    output wire [5:0]   hmac_req_message_len,
    input  wire         hmac_rsp_busy,
    input  wire         hmac_rsp_done,
    input  wire [255:0] hmac_rsp_digest
`ifdef TRUSTEDGE_ASIC_SERVICE_PORTS
    ,
    output wire         measure_scrub_o,
    output wire         measure_start_o,
    output wire [1:0]   measure_bank_id_o,
    output wire         measure_private_mode_o,
    input  wire         measure_busy_i,
    input  wire         measure_done_i,
    input  wire [63:0]  measure_response_i,
    input  wire [15:0]  measure_min_delta_i,
    input  wire [15:0]  measure_max_delta_i,
    input  wire [7:0]   measure_health_i,
    input  wire [31:0]  measure_cycles_i,
    input  wire         measure_physical_i
`endif
);
    localparam [7:0] EXT_API_VERSION = 8'h01;
    localparam [7:0] SUB_PUF_ROOT     = 8'h40;
    localparam [7:0] MODE_INFO        = 8'h00;
    localparam [7:0] MODE_RAW_BLOCKED = 8'h01;
    localparam [7:0] MODE_ENROLL      = 8'h02;
    localparam [7:0] MODE_READ_CHUNK  = 8'h03;
    localparam [7:0] MODE_LOAD_CHUNK  = 8'h04;
    localparam [7:0] MODE_RESTORE     = 8'h05;
    localparam [7:0] MODE_STATUS      = 8'h06;
    localparam [7:0] MODE_CLEAR       = 8'h07;

    localparam [7:0] RESULT_OK            = 8'h00;
    localparam [7:0] RESULT_NO_ENTRY      = 8'h03;
    localparam [7:0] RESULT_BAD_LENGTH    = 8'h04;
    localparam [7:0] RESULT_REPLAY        = 8'h07;
    localparam [7:0] RESULT_LOCKED        = 8'h08;
    localparam [7:0] RESULT_POLICY_DENIED = 8'h09;
    localparam [7:0] RESULT_AUTH_FAILED   = 8'h0A;
    localparam [7:0] RESULT_COUNTER_EXHAUSTED = 8'h0B;
    localparam [7:0] RESULT_BAD_COMMAND   = 8'h7F;

    localparam [31:0] FABRIC_ID = 32'hD0410101;
    localparam [7:0] FORMAT_ID = 8'h01;
    localparam [7:0] CODE_ID = 8'h01;       // 12 x extended-Hamming(16)
    localparam [7:0] PAIRING_ID = 8'h11;    // within-bank B offset +17
    localparam [7:0] BANK_MASK = 8'h0B;     // logical banks 0,1,3
    localparam [63:0] ROOT_LABEL = 64'h54454431524F4F54; // "TED1ROOT"
    localparam [63:0] CHECK_LABEL = 64'h5445443143484B31; // "TED1CHK1"

    localparam [3:0] ST_IDLE=4'd0, ST_CAPTURE=4'd1, ST_RESTART=4'd2,
                     ST_PREPARE=4'd3, ST_KDF_WAIT=4'd4,
                     ST_TAG_START=4'd5, ST_TAG_WAIT=4'd6;
    reg [3:0] state;
    reg operation_enroll;
    reg [1:0] capture_step;
    reg [31:0] pending_counter;
    reg [191:0] raw_capture;
    reg [255:0] envelope;
    reg envelope_valid;
    reg [1:0] load_mask;
    reg [31:0] last_mutating_counter;
    reg last_counter_valid;
    reg [4:0] corrected_blocks_latched;
    reg [59:0] helper_latched;
    reg [63:0] chip_id_latched;

    reg engine_start;
    reg engine_scrub;
    reg [1:0] engine_bank;
    wire engine_busy;
    wire engine_done;
    wire [63:0] engine_raw;
    wire [15:0] engine_min_delta;
    wire [15:0] engine_max_delta;
    wire [7:0] engine_health;
    wire engine_physical;
    wire [31:0] engine_cycles;
    wire device_context_valid = transport_ready &&
                                transport_error == 8'd0 &&
                                chip_id != 64'd0;

    reg hmac_start;
    reg hmac_scrub;
    reg [255:0] hmac_key;
    reg [255:0] hmac_message;
    wire hmac_busy;
    wire hmac_done;
    wire [255:0] hmac_digest;
    wire internal_hmac_busy;
    wire internal_hmac_done;
    wire [255:0] internal_hmac_digest;

    wire [59:0] helper_enroll;
    wire [59:0] helper_loaded = envelope[187:128];
    wire [191:0] corrected_response;
    wire [4:0] corrected_blocks;
    wire sketch_uncorrectable;
    wire envelope_metadata_ok = envelope[255:248] == FORMAT_ID &&
                                envelope[247:240] == CODE_ID &&
                                envelope[239:232] == PAIRING_ID &&
                                envelope[231:224] == BANK_MASK &&
                                envelope[223:192] == FABRIC_ID &&
                                envelope[191:188] == 4'd0;
    wire verifier_match = ~|(hmac_digest[255:128] ^ envelope[127:0]);

`ifdef TRUSTEDGE_ASIC_SERVICE_PORTS
    assign measure_scrub_o = engine_scrub;
    assign measure_start_o = engine_start;
    assign measure_bank_id_o = engine_bank;
    assign measure_private_mode_o = 1'b1;
    assign engine_busy = measure_busy_i;
    assign engine_done = measure_done_i;
    assign engine_raw = measure_response_i;
    assign engine_min_delta = measure_min_delta_i;
    assign engine_max_delta = measure_max_delta_i;
    assign engine_health = measure_health_i;
    assign engine_cycles = measure_cycles_i;
    assign engine_physical = measure_physical_i;
`else
    puf_char_engine u_engine (
        .clk(clk), .rst_n(rst_n), .scrub(engine_scrub),
        .start(engine_start), .bank_id(engine_bank),
        .private_mode(1'b1), .busy(engine_busy), .done(engine_done),
        .raw_response(engine_raw), .min_abs_delta(engine_min_delta),
        .max_abs_delta(engine_max_delta), .health_flags(engine_health),
        .physical_backend(engine_physical), .measurement_cycles(engine_cycles)
    );
`endif

    puf_secded_sketch u_sketch (
        .enroll_response(raw_capture), .noisy_response(raw_capture),
        .helper_in(helper_loaded), .helper_enroll(helper_enroll),
        .corrected_response(corrected_response),
        .corrected_blocks(corrected_blocks),
        .uncorrectable(sketch_uncorrectable)
    );

    assign hmac_req_start = hmac_start;
    assign hmac_req_scrub = hmac_scrub;
    assign hmac_req_key = hmac_key;
    assign hmac_req_message = hmac_message;
    assign hmac_req_message_len = 6'd32;
    assign hmac_busy = EXTERNAL_HMAC ? hmac_rsp_busy : internal_hmac_busy;
    assign hmac_done = EXTERNAL_HMAC ? hmac_rsp_done : internal_hmac_done;
    assign hmac_digest = EXTERNAL_HMAC ? hmac_rsp_digest : internal_hmac_digest;

    generate if (!EXTERNAL_HMAC) begin : g_internal_hmac
    hmac_sha256_fixed u_root_hmac (
        .clk(clk), .rst_n(rst_n), .scrub(hmac_scrub), .start(hmac_start),
        .key(hmac_key), .message(hmac_message), .message_len(6'd32),
        .busy(internal_hmac_busy), .done(internal_hmac_done),
        .digest(internal_hmac_digest)
    );
    end else begin : g_no_internal_hmac
        assign internal_hmac_busy = 1'b0;
        assign internal_hmac_done = 1'b0;
        assign internal_hmac_digest = 256'd0;
    end endgenerate

    function automatic [255:0] context_message;
        input [63:0] label_value;
        input [59:0] helper_value;
        begin
            context_message = {label_value, FABRIC_ID,
                               FORMAT_ID, CODE_ID, PAIRING_ID, BANK_MASK,
                               chip_id_latched, 4'd0, helper_value};
        end
    endfunction

    task automatic set_header;
        input [7:0] result;
        input [31:0] tx_counter;
        begin
            response_data <= 256'd0;
            response_data[255:248] <= EXT_API_VERSION;
            response_data[247:240] <= SUB_PUF_ROOT;
            response_data[239:232] <= result;
            response_data[231:200] <= tx_counter;
        end
    endtask

    task automatic finish_status;
        input [7:0] result;
        input [31:0] tx_counter;
        input [7:0] mode_value;
        input [7:0] detail;
        begin
            set_header(result, tx_counter);
            response_data[199:192] <= mode_value;
            response_data[191:184] <= {7'd0, root_ready};
            response_data[183:176] <= {7'd0, envelope_valid};
            response_data[175:168] <= {3'd0, corrected_blocks_latched};
            response_data[167:160] <= detail;
            response_len <= 8'd12;
            done <= 1'b1;
        end
    endtask

    task automatic scrub_operation;
        begin
            raw_capture <= 192'd0;
            hmac_key <= 256'd0;
            hmac_message <= 256'd0;
            hmac_scrub <= 1'b1;
            corrected_blocks_latched <= 5'd0;
            helper_latched <= 60'd0;
            chip_id_latched <= 64'd0;
            engine_scrub <= 1'b1;
        end
    endtask

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= ST_IDLE;
            operation_enroll <= 1'b0;
            capture_step <= 2'd0;
            pending_counter <= 32'd0;
            raw_capture <= 192'd0;
            envelope <= 256'd0;
            envelope_valid <= 1'b0;
            load_mask <= 2'd0;
            last_mutating_counter <= 32'd0;
            last_counter_valid <= 1'b0;
            corrected_blocks_latched <= 5'd0;
            helper_latched <= 60'd0;
            chip_id_latched <= 64'd0;
            engine_start <= 1'b0;
            engine_scrub <= 1'b0;
            engine_bank <= 2'd0;
            hmac_start <= 1'b0;
            hmac_scrub <= 1'b0;
            hmac_key <= 256'd0;
            hmac_message <= 256'd0;
            done <= 1'b0;
            response_len <= 8'd0;
            response_data <= 256'd0;
            root_ready <= 1'b0;
            root_key <= 256'd0;
        end else if (zeroize) begin
            state <= ST_IDLE;
            operation_enroll <= 1'b0;
            capture_step <= 2'd0;
            raw_capture <= 192'd0;
            envelope <= 256'd0;
            envelope_valid <= 1'b0;
            load_mask <= 2'd0;
            corrected_blocks_latched <= 5'd0;
            helper_latched <= 60'd0;
            chip_id_latched <= 64'd0;
            engine_start <= 1'b0;
            engine_scrub <= 1'b1;
            hmac_start <= 1'b0;
            hmac_scrub <= 1'b1;
            hmac_key <= 256'd0;
            hmac_message <= 256'd0;
            done <= 1'b0;
            response_len <= 8'd0;
            response_data <= 256'd0;
            root_ready <= 1'b0;
            root_key <= 256'd0;
        end else begin
            done <= 1'b0;
            engine_start <= 1'b0;
            engine_scrub <= 1'b0;
            hmac_start <= 1'b0;
            hmac_scrub <= 1'b0;

            // SW0 is required for the complete enrollment operation, not just
            // for the first command cycle.  Dropping it aborts and scrubs.
            if (state == ST_IDLE && root_ready &&
                (!device_context_valid || chip_id != chip_id_latched)) begin
                root_ready <= 1'b0;
                root_key <= 256'd0;
                scrub_operation();
            end else if (state != ST_IDLE &&
                (!device_context_valid || chip_id != chip_id_latched)) begin
                state <= ST_IDLE;
                root_ready <= 1'b0;
                root_key <= 256'd0;
                scrub_operation();
                finish_status(RESULT_LOCKED, pending_counter,
                              operation_enroll ? MODE_ENROLL : MODE_RESTORE,
                              8'h80);
            end else if (state != ST_IDLE && operation_enroll &&
                         !provision_enable) begin
                state <= ST_IDLE;
                root_ready <= 1'b0;
                root_key <= 256'd0;
                envelope <= 256'd0;
                envelope_valid <= 1'b0;
                load_mask <= 2'd0;
                scrub_operation();
                finish_status(RESULT_POLICY_DENIED, pending_counter,
                              MODE_ENROLL, 8'h01);
            end else begin
                case (state)
                    ST_IDLE: if (cmd_valid) begin
                        if (!header_valid || api_version != EXT_API_VERSION ||
                            subcmd != SUB_PUF_ROOT || flags != 8'd0) begin
                            set_header(RESULT_BAD_COMMAND, counter);
                            response_len <= 8'd7;
                            done <= 1'b1;
                        end else if (data_len < 8'd1) begin
                            set_header(RESULT_BAD_LENGTH, counter);
                            response_len <= 8'd7;
                            done <= 1'b1;
                        end else begin
                            case (data[255:248])
                                MODE_INFO: begin
                                    if (data_len != 8'd1) begin
                                        set_header(RESULT_BAD_LENGTH, counter);
                                        response_len <= 8'd7;
                                    end else begin
                                        set_header(RESULT_OK, counter);
                                        response_data[199:192] <= MODE_INFO;
                                        response_data[191:184] <= FORMAT_ID;
                                        response_data[183:176] <= {7'd0, engine_physical};
                                        response_data[175:168] <= 8'd192;
                                        response_data[167:160] <= CODE_ID;
                                        response_data[159:152] <= 8'd12;
                                        response_data[151:144] <= 8'd16;
                                        response_data[143:136] <= 8'd1;
                                        response_data[135:104] <= FABRIC_ID;
                                        response_data[103:96] <= PAIRING_ID;
                                        response_data[95:88] <= BANK_MASK;
                                        response_data[87:80] <=
                                            {7'd0, device_context_valid};
                                        response_len <= 8'd22;
                                    end
                                    done <= 1'b1;
                                end

                                MODE_RAW_BLOCKED: begin
                                    // D0 characterization source remains in
                                    // history, but this D1 artifact has no raw
                                    // response command.
                                    set_header(RESULT_BAD_COMMAND, counter);
                                    response_data[199:192] <= MODE_RAW_BLOCKED;
                                    response_len <= 8'd8;
                                    done <= 1'b1;
                                end

                                MODE_ENROLL: begin
                                    if (data_len != 8'd1) begin
                                        set_header(RESULT_BAD_LENGTH, counter);
                                        response_len <= 8'd7;
                                        done <= 1'b1;
                                    end else if (counter == 32'hFFFF_FFFF) begin
                                        finish_status(RESULT_COUNTER_EXHAUSTED, counter,
                                                      MODE_ENROLL, 8'd0);
                                    end else if (!provision_enable) begin
                                        finish_status(RESULT_POLICY_DENIED, counter,
                                                      MODE_ENROLL, 8'd0);
                                    end else if (!device_context_valid) begin
                                        finish_status(RESULT_LOCKED, counter,
                                                      MODE_ENROLL, 8'h80);
                                    end else if (last_counter_valid &&
                                                 counter <= last_mutating_counter) begin
                                        finish_status(RESULT_REPLAY, counter,
                                                      MODE_ENROLL, 8'd0);
                                    end else begin
                                        root_ready <= 1'b0;
                                        root_key <= 256'd0;
                                        envelope <= 256'd0;
                                        envelope_valid <= 1'b0;
                                        load_mask <= 2'd0;
                                        raw_capture <= 192'd0;
                                        operation_enroll <= 1'b1;
                                        capture_step <= 2'd0;
                                        engine_bank <= 2'd0;
                                        engine_start <= 1'b1;
                                        pending_counter <= counter;
                                        chip_id_latched <= chip_id;
                                        last_mutating_counter <= counter;
                                        last_counter_valid <= 1'b1;
                                        state <= ST_CAPTURE;
                                    end
                                end

                                MODE_READ_CHUNK: begin
                                    if (data_len != 8'd2 || data[247:240] > 8'd1) begin
                                        set_header(RESULT_BAD_LENGTH, counter);
                                        response_len <= 8'd7;
                                    end else if (!envelope_valid) begin
                                        set_header(RESULT_NO_ENTRY, counter);
                                        response_len <= 8'd7;
                                    end else begin
                                        set_header(RESULT_OK, counter);
                                        response_data[199:192] <= MODE_READ_CHUNK;
                                        response_data[191:184] <= data[247:240];
                                        if (data[247:240] == 8'd0)
                                            response_data[183:56] <= envelope[255:128];
                                        else
                                            response_data[183:56] <= envelope[127:0];
                                        response_len <= 8'd25;
                                    end
                                    done <= 1'b1;
                                end

                                MODE_LOAD_CHUNK: begin
                                    if (data_len != 8'd18 || data[247:240] > 8'd1) begin
                                        set_header(RESULT_BAD_LENGTH, counter);
                                        response_len <= 8'd7;
                                        done <= 1'b1;
                                    end else if (counter == 32'hFFFF_FFFF) begin
                                        finish_status(RESULT_COUNTER_EXHAUSTED, counter,
                                                      MODE_LOAD_CHUNK, 8'd0);
                                    end else if (last_counter_valid &&
                                                 counter <= last_mutating_counter) begin
                                        finish_status(RESULT_REPLAY, counter,
                                                      MODE_LOAD_CHUNK, 8'd0);
                                    end else if ((data[247:240] == 8'd0 && load_mask != 2'd0) ||
                                                 (data[247:240] == 8'd1 && load_mask != 2'd1)) begin
                                        finish_status(RESULT_BAD_LENGTH, counter,
                                                      MODE_LOAD_CHUNK, 8'h02);
                                    end else begin
                                        if (data[247:240] == 8'd0) begin
                                            envelope[255:128] <= data[239:112];
                                            load_mask <= 2'd1;
                                        end else begin
                                            envelope[127:0] <= data[239:112];
                                            load_mask <= 2'd3;
                                            envelope_valid <= 1'b1;
                                        end
                                        last_mutating_counter <= counter;
                                        last_counter_valid <= 1'b1;
                                        finish_status(RESULT_OK, counter,
                                                      MODE_LOAD_CHUNK,
                                                      {6'd0, data[247:240]});
                                        if (data[247:240] == 8'd1)
                                            response_data[183:176] <= 8'd1;
                                    end
                                end

                                MODE_RESTORE: begin
                                    if (data_len != 8'd1) begin
                                        set_header(RESULT_BAD_LENGTH, counter);
                                        response_len <= 8'd7;
                                        done <= 1'b1;
                                    end else if (counter == 32'hFFFF_FFFF) begin
                                        finish_status(RESULT_COUNTER_EXHAUSTED, counter,
                                                      MODE_RESTORE, 8'd0);
                                    end else if (!envelope_valid || load_mask != 2'd3) begin
                                        finish_status(RESULT_NO_ENTRY, counter,
                                                      MODE_RESTORE, 8'd0);
                                    end else if (!device_context_valid) begin
                                        finish_status(RESULT_LOCKED, counter,
                                                      MODE_RESTORE, 8'h80);
                                    end else if (last_counter_valid &&
                                                 counter <= last_mutating_counter) begin
                                        finish_status(RESULT_REPLAY, counter,
                                                      MODE_RESTORE, 8'd0);
                                    end else begin
                                        root_ready <= 1'b0;
                                        root_key <= 256'd0;
                                        raw_capture <= 192'd0;
                                        operation_enroll <= 1'b0;
                                        capture_step <= 2'd0;
                                        engine_bank <= 2'd0;
                                        engine_start <= 1'b1;
                                        pending_counter <= counter;
                                        chip_id_latched <= chip_id;
                                        last_mutating_counter <= counter;
                                        last_counter_valid <= 1'b1;
                                        state <= ST_CAPTURE;
                                    end
                                end

                                MODE_STATUS: begin
                                    if (data_len != 8'd1)
                                        finish_status(RESULT_BAD_LENGTH, counter,
                                                      MODE_STATUS, 8'd0);
                                    else
                                        finish_status(RESULT_OK, counter,
                                                      MODE_STATUS, {6'd0, load_mask});
                                end

                                MODE_CLEAR: begin
                                    if (data_len != 8'd1) begin
                                        finish_status(RESULT_BAD_LENGTH, counter,
                                                      MODE_CLEAR, 8'd0);
                                    end else begin
                                        root_ready <= 1'b0;
                                        root_key <= 256'd0;
                                        envelope <= 256'd0;
                                        envelope_valid <= 1'b0;
                                        load_mask <= 2'd0;
                                        chip_id_latched <= 64'd0;
                                        scrub_operation();
                                        finish_status(RESULT_OK, counter,
                                                      MODE_CLEAR, 8'd0);
                                        response_data[191:176] <= 16'd0;
                                    end
                                end

                                default: begin
                                    set_header(RESULT_BAD_COMMAND, counter);
                                    response_len <= 8'd7;
                                    done <= 1'b1;
                                end
                            endcase
                        end
                    end

                    ST_CAPTURE: if (engine_done) begin
                        if (engine_health != 8'd0) begin
                            state <= ST_IDLE;
                            root_ready <= 1'b0;
                            root_key <= 256'd0;
                            scrub_operation();
                            finish_status(RESULT_AUTH_FAILED, pending_counter,
                                          operation_enroll ? MODE_ENROLL : MODE_RESTORE,
                                          engine_health);
                        end else begin
                            case (capture_step)
                                2'd0: raw_capture[63:0] <= engine_raw;
                                2'd1: raw_capture[127:64] <= engine_raw;
                                default: raw_capture[191:128] <= engine_raw;
                            endcase
                            if (capture_step == 2'd2) begin
                                engine_scrub <= 1'b1;
                                state <= ST_PREPARE;
                            end else begin
                                capture_step <= capture_step + 2'd1;
                                engine_bank <= (capture_step == 2'd0) ? 2'd1 : 2'd3;
                                state <= ST_RESTART;
                            end
                        end
                    end

                    ST_RESTART: begin
                        engine_start <= 1'b1;
                        state <= ST_CAPTURE;
                    end

                    ST_PREPARE: begin
                        if (!operation_enroll &&
                            (!envelope_metadata_ok || sketch_uncorrectable)) begin
                            state <= ST_IDLE;
                            root_ready <= 1'b0;
                            root_key <= 256'd0;
                            corrected_blocks_latched <= corrected_blocks;
                            scrub_operation();
                            finish_status(RESULT_AUTH_FAILED, pending_counter,
                                          MODE_RESTORE,
                                          sketch_uncorrectable ? 8'h10 : 8'h20);
                        end else begin
                            corrected_blocks_latched <= operation_enroll ?
                                                        5'd0 : corrected_blocks;
                            helper_latched <= operation_enroll ?
                                              helper_enroll : helper_loaded;
                            hmac_key <= operation_enroll ?
                                        {64'd0, raw_capture} :
                                        {64'd0, corrected_response};
                            hmac_message <= context_message(operation_enroll ?
                                                           ROOT_LABEL : ROOT_LABEL,
                                                           operation_enroll ?
                                                           helper_enroll : helper_loaded);
                            hmac_start <= 1'b1;
                            state <= ST_KDF_WAIT;
                        end
                    end

                    ST_KDF_WAIT: begin
                        // The HMAC instance has latched the response.  Scrub the
                        // raw/corrected staging while the digest is computed.
                        raw_capture <= 192'd0;
                        hmac_key <= 256'd0;
                        hmac_message <= 256'd0;
                        if (hmac_done) begin
                            root_key <= hmac_digest;
                            state <= ST_TAG_START;
                        end
                    end

                    ST_TAG_START: begin
                            // Read the derived key back from its volatile FPGA
                            // register before generating the public verifier.
                            // This keeps the retained root state in the actual
                            // synthesized data path instead of as an unused port.
                            hmac_key <= root_key;
                            hmac_message <= context_message(CHECK_LABEL,
                                                           helper_latched);
                            hmac_start <= 1'b1;
                            state <= ST_TAG_WAIT;
                    end

                    ST_TAG_WAIT: begin
                        hmac_key <= 256'd0;
                        hmac_message <= 256'd0;
                        if (hmac_done) begin
                            state <= ST_IDLE;
                            hmac_scrub <= 1'b1;
                            if (operation_enroll) begin
                                envelope <= {FORMAT_ID, CODE_ID, PAIRING_ID,
                                             BANK_MASK, FABRIC_ID, 4'd0,
                                             helper_latched,
                                             hmac_digest[255:128]};
                                envelope_valid <= 1'b1;
                                load_mask <= 2'd3;
                                root_ready <= 1'b1;
                                finish_status(RESULT_OK, pending_counter,
                                              MODE_ENROLL, 8'd0);
                                response_data[191:176] <= 16'h0101;
                            end else if (verifier_match) begin
                                root_ready <= 1'b1;
                                finish_status(RESULT_OK, pending_counter,
                                              MODE_RESTORE, 8'd0);
                                response_data[191:184] <= 8'd1;
                            end else begin
                                root_ready <= 1'b0;
                                root_key <= 256'd0;
                                finish_status(RESULT_AUTH_FAILED, pending_counter,
                                              MODE_RESTORE, 8'h40);
                            end
                        end
                    end

                    default: begin
                        state <= ST_IDLE;
                        root_ready <= 1'b0;
                        root_key <= 256'd0;
                        scrub_operation();
                    end
                endcase
            end
        end
    end
endmodule
