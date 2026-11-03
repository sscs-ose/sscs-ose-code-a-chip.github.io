// HSM-4D2/D3 academic persistent-vault transport.
//
// This service stays behind the existing HSM extension subcommand 0x40. It
// wraps a private 128-bit vault seed with AES-256-CTR and authenticates the
// complete public 32-byte record with a separately-derived HMAC-SHA-256 key.
// Only the 48-byte encrypted record (record || truncated tag) is exposed to
// ESP32. The root, AES/MAC keys, decrypted seed and HSM key never appear in a
// response. This is a prototype transport, not a production secure element.
module puf_vault_service #(
    parameter EXTERNAL_HMAC = 1'b0
) (
    input wire clk,
    input wire rst_n,
    input wire cmd_valid,
    input wire header_valid,
    input wire provision_enable,
    input wire zeroize,
    input wire transport_ready,
    input wire [7:0] transport_error,
    input wire [63:0] chip_id,
    input wire [7:0] api_version,
    input wire [7:0] subcmd,
    input wire [7:0] flags,
    input wire [31:0] counter,
    input wire [7:0] data_len,
    input wire [255:0] data,
    input wire root_ready,
    input wire [255:0] root_key,
    input wire vault_stage_authorized,
    output reg done,
    output reg [7:0] response_len,
    output reg [255:0] response_data,
    output reg vault_load_pulse,
    output reg vault_stage_pulse,
    output reg vault_clear_pulse,
    output reg vault_loaded,
    output reg [255:0] vault_hmac_key,
    output wire hmac_req_start,
    output wire hmac_req_scrub,
    output wire [255:0] hmac_req_key,
    output wire [255:0] hmac_req_message,
    output wire [5:0] hmac_req_message_len,
    input wire hmac_rsp_busy,
    input wire hmac_rsp_done,
    input wire [255:0] hmac_rsp_digest
);
    localparam [7:0] EXT_API_VERSION = 8'h01;
    localparam [7:0] SUB_PUF_ROOT = 8'h40;
    localparam [7:0] MODE_SEAL = 8'h08;
    localparam [7:0] MODE_READ_BLOB = 8'h09;
    localparam [7:0] MODE_LOAD_BLOB = 8'h0A;
    localparam [7:0] MODE_OPEN = 8'h0B;
    localparam [7:0] MODE_STATUS = 8'h0C;
    localparam [7:0] MODE_CLEAR_BLOB = 8'h0D;
    localparam [7:0] MODE_SEAL_AUTH = 8'h0E;

    localparam [7:0] RESULT_OK = 8'h00;
    localparam [7:0] RESULT_NO_ENTRY = 8'h03;
    localparam [7:0] RESULT_BAD_LENGTH = 8'h04;
    localparam [7:0] RESULT_REPLAY = 8'h07;
    localparam [7:0] RESULT_LOCKED = 8'h08;
    localparam [7:0] RESULT_POLICY_DENIED = 8'h09;
    localparam [7:0] RESULT_AUTH_FAILED = 8'h0A;
    localparam [7:0] RESULT_COUNTER_EXHAUSTED = 8'h0B;
    localparam [7:0] RESULT_BAD_COMMAND = 8'h7F;

    localparam [7:0] BLOB_FORMAT = 8'h01;
    localparam [7:0] BLOB_PREPARED = 8'h00;
    localparam [7:0] BLOB_COMMITTED = 8'h01;
    localparam [31:0] D2_FABRIC_ID = 32'hD0420101;
    localparam [63:0] ENC_LABEL = 64'h54454432454E4320;  // TED2ENC_
    localparam [63:0] MAC_LABEL = 64'h544544324D414320;  // TED2MAC_
    localparam [63:0] SEED_LABEL = 64'h5445443253454544; // TED2SEED
    localparam [63:0] HSM_LABEL = 64'h5445443248534D20;  // TED2HSM_

    localparam [4:0] ST_IDLE = 5'd0,
                     ST_SEAL_ENC_START = 5'd1,
                     ST_SEAL_ENC_WAIT = 5'd2,
                     ST_SEAL_MAC_START = 5'd3,
                     ST_SEAL_MAC_WAIT = 5'd4,
                     ST_SEAL_SEED_START = 5'd5,
                     ST_SEAL_SEED_WAIT = 5'd6,
                     ST_SEAL_AES_START = 5'd7,
                     ST_SEAL_AES_WAIT = 5'd8,
                     ST_SEAL_TAG_START = 5'd9,
                     ST_SEAL_TAG_WAIT = 5'd10,
                     ST_OPEN_MAC_START = 5'd11,
                     ST_OPEN_MAC_WAIT = 5'd12,
                     ST_OPEN_TAG_START = 5'd13,
                     ST_OPEN_TAG_WAIT = 5'd14,
                     ST_OPEN_ENC_START = 5'd15,
                     ST_OPEN_ENC_WAIT = 5'd16,
                     ST_OPEN_AES_START = 5'd17,
                     ST_OPEN_AES_WAIT = 5'd18,
                     ST_OPEN_SEED_START = 5'd19,
                     ST_OPEN_SEED_WAIT = 5'd20,
                     ST_OPEN_HSM_START = 5'd21,
                     ST_OPEN_HSM_WAIT = 5'd22,
                     ST_SEAL_HSM_START = 5'd23,
                     ST_SEAL_HSM_WAIT = 5'd24;
    reg [4:0] state;

    reg [31:0] pending_counter;
    reg [31:0] last_mutating_counter;
    reg last_counter_valid;
    reg [31:0] record_generation;
    reg [63:0] record_iv;
    reg [31:0] record_header;
    reg [127:0] ciphertext_latched;
    reg [127:0] seed_latched;
    reg [255:0] enc_key;
    reg [255:0] mac_key;
    reg [383:0] blob;
    reg blob_valid;
    reg [1:0] blob_load_mask;
    reg seal_authenticated;

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

    reg aes_start;
    reg aes_scrub;
    reg [255:0] aes_key;
    reg [127:0] aes_block;
    wire aes_busy;
    wire aes_done;
    wire [127:0] aes_ciphertext;

    wire root_context_valid = root_ready && transport_ready &&
                              transport_error == 8'd0 && chip_id != 64'd0;
    wire [255:0] blob_record = blob[383:128];
    wire [127:0] blob_tag = blob[127:0];
    wire blob_metadata_ok = blob_record[255:248] == BLOB_FORMAT &&
                            (blob_record[247:240] == BLOB_PREPARED ||
                             blob_record[247:240] == BLOB_COMMITTED) &&
                            blob_record[239:224] == 16'd0;
    wire [31:0] blob_generation = blob_record[223:192];
    wire [63:0] blob_iv = blob_record[191:128];
    wire [127:0] blob_ciphertext = blob_record[127:0];

    assign hmac_req_start = hmac_start;
    assign hmac_req_scrub = hmac_scrub;
    assign hmac_req_key = hmac_key;
    assign hmac_req_message = hmac_message;
    assign hmac_req_message_len = 6'd32;
    assign hmac_busy = EXTERNAL_HMAC ? hmac_rsp_busy : internal_hmac_busy;
    assign hmac_done = EXTERNAL_HMAC ? hmac_rsp_done : internal_hmac_done;
    assign hmac_digest = EXTERNAL_HMAC ? hmac_rsp_digest : internal_hmac_digest;

    generate if (!EXTERNAL_HMAC) begin : g_internal_hmac
    hmac_sha256_fixed u_vault_hmac (
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

    aes256_encrypt_block u_vault_aes (
        .clk(clk), .rst_n(rst_n), .scrub(aes_scrub), .start(aes_start),
        .key(aes_key), .block(aes_block), .busy(aes_busy), .done(aes_done),
        .ciphertext(aes_ciphertext)
    );

    function automatic [255:0] root_context;
        input [63:0] label;
        begin
            // Exactly 256 bits.  Using 128 padding bits made the RHS 288 bits
            // wide and silently truncated the high 32 bits of the domain label.
            root_context = {label, D2_FABRIC_ID, chip_id, 96'd0};
        end
    endfunction

    function automatic [255:0] hsm_context;
        input [127:0] seed;
        begin
            hsm_context = {HSM_LABEL, seed, 64'd0};
        end
    endfunction

    function automatic [127:0] ctr_block;
        input [31:0] generation;
        input [63:0] iv;
        begin
            ctr_block = {32'h54454432, generation, iv}; // "TED2" || gen || IV
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
        input [7:0] mode;
        input [7:0] detail;
        begin
            set_header(result, tx_counter);
            response_data[199:192] <= mode;
            response_data[191:184] <= {7'd0, root_ready};
            response_data[183:176] <= {7'd0, blob_valid};
            response_data[175:168] <= {7'd0, vault_loaded};
            response_data[167:160] <= {5'd0, blob_load_mask};
            response_data[159:152] <= detail;
            response_len <= 8'd14;
            done <= 1'b1;
        end
    endtask

    task automatic scrub_private;
        begin
            hmac_key <= 256'd0;
            hmac_message <= 256'd0;
            hmac_scrub <= 1'b1;
            aes_key <= 256'd0;
            aes_block <= 128'd0;
            aes_scrub <= 1'b1;
            enc_key <= 256'd0;
            mac_key <= 256'd0;
            seed_latched <= 128'd0;
            ciphertext_latched <= 128'd0;
        end
    endtask

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= ST_IDLE;
            pending_counter <= 32'd0;
            last_mutating_counter <= 32'd0;
            last_counter_valid <= 1'b0;
            record_generation <= 32'd0;
            record_iv <= 64'd0;
            record_header <= 32'd0;
            ciphertext_latched <= 128'd0;
            seed_latched <= 128'd0;
            enc_key <= 256'd0;
            mac_key <= 256'd0;
            blob <= 384'd0;
            blob_valid <= 1'b0;
            blob_load_mask <= 2'd0;
            seal_authenticated <= 1'b0;
            hmac_start <= 1'b0;
            hmac_scrub <= 1'b0;
            hmac_key <= 256'd0;
            hmac_message <= 256'd0;
            aes_start <= 1'b0;
            aes_scrub <= 1'b0;
            aes_key <= 256'd0;
            aes_block <= 128'd0;
            done <= 1'b0;
            response_len <= 8'd0;
            response_data <= 256'd0;
            vault_load_pulse <= 1'b0;
            vault_stage_pulse <= 1'b0;
            vault_clear_pulse <= 1'b0;
            vault_loaded <= 1'b0;
            vault_hmac_key <= 256'd0;
        end else if (zeroize) begin
            state <= ST_IDLE;
            pending_counter <= 32'd0;
            record_generation <= 32'd0;
            record_iv <= 64'd0;
            record_header <= 32'd0;
            blob <= 384'd0;
            blob_valid <= 1'b0;
            blob_load_mask <= 2'd0;
            seal_authenticated <= 1'b0;
            hmac_start <= 1'b0;
            aes_start <= 1'b0;
            done <= 1'b0;
            response_len <= 8'd0;
            response_data <= 256'd0;
            vault_load_pulse <= 1'b0;
            vault_stage_pulse <= 1'b0;
            // Do not clear the pre-existing HSM-4C0 volatile vault merely
            // because its generic zeroize command reaches this independent
            // service. Only revoke a vault this D2/D3 service actually loaded.
            vault_clear_pulse <= vault_loaded;
            vault_loaded <= 1'b0;
            vault_hmac_key <= 256'd0;
            scrub_private();
        end else begin
            done <= 1'b0;
            hmac_start <= 1'b0;
            hmac_scrub <= 1'b0;
            aes_start <= 1'b0;
            aes_scrub <= 1'b0;
            vault_load_pulse <= 1'b0;
            vault_stage_pulse <= 1'b0;
            vault_clear_pulse <= 1'b0;

            // The internal staging key is presented for exactly one cycle.
            // The HSM captures it on vault_stage_pulse; it is then scrubbed
            // from this service unless an OPEN intentionally owns the bus.
            if (vault_stage_pulse && !vault_loaded)
                vault_hmac_key <= 256'd0;

            // The PUF service independently revokes root_ready if the SDM
            // context changes. Mirror that boundary here so no old vault key
            // can remain active for the intervening clock.
            if (!root_context_valid && state == ST_IDLE && vault_loaded) begin
                vault_loaded <= 1'b0;
                vault_hmac_key <= 256'd0;
                vault_clear_pulse <= 1'b1;
                scrub_private();
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
                                MODE_SEAL: begin
                                    if (data_len != 8'd14 ||
                                        (data[247:240] != BLOB_PREPARED &&
                                         data[247:240] != BLOB_COMMITTED) ||
                                        data[239:208] == 32'd0 ||
                                        data[207:144] == 64'd0) begin
                                        finish_status(RESULT_BAD_LENGTH, counter,
                                                      MODE_SEAL, 8'd0);
                                    end else if (counter == 32'hFFFF_FFFF) begin
                                        finish_status(RESULT_COUNTER_EXHAUSTED,
                                                      counter, MODE_SEAL, 8'd0);
                                    end else if (last_counter_valid &&
                                                 counter <= last_mutating_counter) begin
                                        finish_status(RESULT_REPLAY, counter,
                                                      MODE_SEAL, 8'd0);
                                    end else if (!provision_enable) begin
                                        finish_status(RESULT_POLICY_DENIED, counter,
                                                      MODE_SEAL, 8'd0);
                                    end else if (!root_context_valid) begin
                                        finish_status(RESULT_LOCKED, counter,
                                                      MODE_SEAL, 8'd0);
                                    end else begin
                                        pending_counter <= counter;
                                        last_mutating_counter <= counter;
                                        last_counter_valid <= 1'b1;
                                        record_header <= {BLOB_FORMAT,
                                                          data[247:240],16'd0};
                                        record_generation <= data[239:208];
                                        record_iv <= data[207:144];
                                        seal_authenticated <= 1'b0;
                                        state <= ST_SEAL_ENC_START;
                                    end
                                end
                                MODE_SEAL_AUTH: begin
                                    if (data_len != 8'd14 ||
                                        (data[247:240] != BLOB_PREPARED &&
                                         data[247:240] != BLOB_COMMITTED) ||
                                        data[239:208] == 32'd0 ||
                                        data[207:144] == 64'd0) begin
                                        finish_status(RESULT_BAD_LENGTH, counter,
                                                      MODE_SEAL_AUTH, 8'd0);
                                    end else if (counter == 32'hFFFF_FFFF) begin
                                        finish_status(RESULT_COUNTER_EXHAUSTED,
                                                      counter, MODE_SEAL_AUTH, 8'd0);
                                    end else if (last_counter_valid &&
                                                 counter <= last_mutating_counter) begin
                                        finish_status(RESULT_REPLAY, counter,
                                                      MODE_SEAL_AUTH, 8'd0);
                                    end else if (!provision_enable ||
                                                 !vault_stage_authorized) begin
                                        finish_status(RESULT_POLICY_DENIED, counter,
                                                      MODE_SEAL_AUTH, 8'd0);
                                    end else if (!root_context_valid) begin
                                        finish_status(RESULT_LOCKED, counter,
                                                      MODE_SEAL_AUTH, 8'd0);
                                    end else begin
                                        pending_counter <= counter;
                                        last_mutating_counter <= counter;
                                        last_counter_valid <= 1'b1;
                                        record_header <= {BLOB_FORMAT,
                                                          data[247:240],16'd0};
                                        record_generation <= data[239:208];
                                        record_iv <= data[207:144];
                                        seal_authenticated <= 1'b1;
                                        state <= ST_SEAL_ENC_START;
                                    end
                                end
                                MODE_READ_BLOB: begin
                                    if (data_len != 8'd2 || data[247:240] > 8'd2) begin
                                        set_header(RESULT_BAD_LENGTH, counter);
                                        response_len <= 8'd7;
                                    end else if (!blob_valid) begin
                                        finish_status(RESULT_NO_ENTRY, counter,
                                                      MODE_READ_BLOB, 8'd0);
                                    end else begin
                                        set_header(RESULT_OK, counter);
                                        response_data[199:192] <= MODE_READ_BLOB;
                                        response_data[191:184] <= data[247:240];
                                        case (data[247:240])
                                            8'd0: response_data[183:56] <= blob[383:256];
                                            8'd1: response_data[183:56] <= blob[255:128];
                                            default: response_data[183:56] <= blob[127:0];
                                        endcase
                                        response_len <= 8'd25;
                                    end
                                    done <= 1'b1;
                                end
                                MODE_LOAD_BLOB: begin
                                    if (data_len != 8'd18 || data[247:240] > 8'd2) begin
                                        finish_status(RESULT_BAD_LENGTH, counter,
                                                      MODE_LOAD_BLOB, 8'd0);
                                    end else if (counter == 32'hFFFF_FFFF) begin
                                        finish_status(RESULT_COUNTER_EXHAUSTED,
                                                      counter, MODE_LOAD_BLOB, 8'd0);
                                    end else if (last_counter_valid &&
                                                 counter <= last_mutating_counter) begin
                                        finish_status(RESULT_REPLAY, counter,
                                                      MODE_LOAD_BLOB, 8'd0);
                                    end else if ((data[247:240] == 8'd0 && blob_load_mask != 2'd0) ||
                                                 (data[247:240] == 8'd1 && blob_load_mask != 2'd1) ||
                                                 (data[247:240] == 8'd2 && blob_load_mask != 2'd3)) begin
                                        finish_status(RESULT_BAD_LENGTH, counter,
                                                      MODE_LOAD_BLOB, 8'h02);
                                    end else begin
                                        case (data[247:240])
                                            8'd0: begin blob[383:256] <= data[239:112]; blob_load_mask <= 2'd1; end
                                            8'd1: begin blob[255:128] <= data[239:112]; blob_load_mask <= 2'd3; end
                                            default: begin
                                                blob[127:0] <= data[239:112];
                                                blob_load_mask <= 2'd3;
                                                blob_valid <= 1'b1;
                                            end
                                        endcase
                                        last_mutating_counter <= counter;
                                        last_counter_valid <= 1'b1;
                                        finish_status(RESULT_OK, counter,
                                                      MODE_LOAD_BLOB, data[247:240]);
                                    end
                                end
                                MODE_OPEN: begin
                                    if (data_len != 8'd1) begin
                                        finish_status(RESULT_BAD_LENGTH, counter,
                                                      MODE_OPEN, 8'd0);
                                    end else if (!root_context_valid) begin
                                        finish_status(RESULT_LOCKED, counter,
                                                      MODE_OPEN, 8'd0);
                                    end else if (!blob_valid || blob_load_mask != 2'd3 ||
                                                 !blob_metadata_ok) begin
                                        vault_loaded <= 1'b0;
                                        vault_hmac_key <= 256'd0;
                                        vault_clear_pulse <= vault_loaded;
                                        finish_status(RESULT_NO_ENTRY, counter,
                                                      MODE_OPEN, 8'd0);
                                    end else begin
                                        pending_counter <= counter;
                                        vault_loaded <= 1'b0;
                                        vault_hmac_key <= 256'd0;
                                        vault_clear_pulse <= vault_loaded;
                                        state <= ST_OPEN_MAC_START;
                                    end
                                end
                                MODE_STATUS: begin
                                    if (data_len != 8'd1)
                                        finish_status(RESULT_BAD_LENGTH, counter,
                                                      MODE_STATUS, 8'd0);
                                    else
                                        finish_status(RESULT_OK, counter,
                                                      MODE_STATUS,
                                                      blob_valid ? blob_record[247:240] : 8'd0);
                                end
                                MODE_CLEAR_BLOB: begin
                                    if (data_len != 8'd1) begin
                                        finish_status(RESULT_BAD_LENGTH, counter,
                                                      MODE_CLEAR_BLOB, 8'd0);
                                    end else begin
                                        blob <= 384'd0;
                                        blob_valid <= 1'b0;
                                        blob_load_mask <= 2'd0;
                                        vault_loaded <= 1'b0;
                                        vault_hmac_key <= 256'd0;
                                        vault_clear_pulse <= vault_loaded;
                                        scrub_private();
                                        finish_status(RESULT_OK, counter,
                                                      MODE_CLEAR_BLOB, 8'd0);
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

                    ST_SEAL_ENC_START: begin
                        hmac_key <= root_key;
                        hmac_message <= root_context(ENC_LABEL);
                        hmac_start <= 1'b1;
                        state <= ST_SEAL_ENC_WAIT;
                    end
                    ST_SEAL_ENC_WAIT: if (hmac_done) begin
                        enc_key <= hmac_digest;
                        hmac_key <= 256'd0;
                        hmac_message <= 256'd0;
                        state <= ST_SEAL_MAC_START;
                    end
                    ST_SEAL_MAC_START: begin
                        hmac_key <= root_key;
                        hmac_message <= root_context(MAC_LABEL);
                        hmac_start <= 1'b1;
                        state <= ST_SEAL_MAC_WAIT;
                    end
                    ST_SEAL_MAC_WAIT: if (hmac_done) begin
                        mac_key <= hmac_digest;
                        hmac_key <= 256'd0;
                        hmac_message <= 256'd0;
                        state <= ST_SEAL_SEED_START;
                    end
                    ST_SEAL_SEED_START: begin
                        hmac_key <= root_key;
                        hmac_message <= root_context(SEED_LABEL);
                        hmac_start <= 1'b1;
                        state <= ST_SEAL_SEED_WAIT;
                    end
                    ST_SEAL_SEED_WAIT: if (hmac_done) begin
                        seed_latched <= hmac_digest[255:128];
                        hmac_key <= 256'd0;
                        hmac_message <= 256'd0;
                        state <= ST_SEAL_AES_START;
                    end
                    ST_SEAL_AES_START: begin
                        aes_key <= enc_key;
                        aes_block <= ctr_block(record_generation, record_iv);
                        aes_start <= 1'b1;
                        state <= ST_SEAL_AES_WAIT;
                    end
                    ST_SEAL_AES_WAIT: if (aes_done) begin
                        ciphertext_latched <= aes_ciphertext ^ seed_latched;
                        aes_key <= 256'd0;
                        aes_block <= 128'd0;
                        state <= ST_SEAL_TAG_START;
                    end
                    ST_SEAL_TAG_START: begin
                        hmac_key <= mac_key;
                        hmac_message <= {record_header, record_generation,
                                         record_iv, ciphertext_latched};
                        hmac_start <= 1'b1;
                        state <= ST_SEAL_TAG_WAIT;
                    end
                    ST_SEAL_TAG_WAIT: if (hmac_done) begin
                        blob <= {record_header, record_generation, record_iv,
                                 ciphertext_latched, hmac_digest[255:128]};
                        blob_valid <= 1'b1;
                        blob_load_mask <= 2'd3;
                        if (seal_authenticated) begin
                            hmac_key <= 256'd0;
                            hmac_message <= 256'd0;
                            state <= ST_SEAL_HSM_START;
                        end else begin
                            state <= ST_IDLE;
                            scrub_private();
                            finish_status(RESULT_OK, pending_counter, MODE_SEAL,
                                          record_header[23:16]);
                        end
                    end

                    ST_SEAL_HSM_START: begin
                        hmac_key <= root_key;
                        hmac_message <= hsm_context(seed_latched);
                        hmac_start <= 1'b1;
                        state <= ST_SEAL_HSM_WAIT;
                    end
                    ST_SEAL_HSM_WAIT: if (hmac_done) begin
                        vault_hmac_key <= hmac_digest;
                        vault_stage_pulse <= 1'b1;
                        seal_authenticated <= 1'b0;
                        state <= ST_IDLE;
                        scrub_private();
                        finish_status(RESULT_OK, pending_counter,
                                      MODE_SEAL_AUTH,
                                      record_header[23:16]);
                    end

                    ST_OPEN_MAC_START: begin
                        hmac_key <= root_key;
                        hmac_message <= root_context(MAC_LABEL);
                        hmac_start <= 1'b1;
                        state <= ST_OPEN_MAC_WAIT;
                    end
                    ST_OPEN_MAC_WAIT: if (hmac_done) begin
                        mac_key <= hmac_digest;
                        hmac_key <= 256'd0;
                        hmac_message <= 256'd0;
                        state <= ST_OPEN_TAG_START;
                    end
                    ST_OPEN_TAG_START: begin
                        hmac_key <= mac_key;
                        hmac_message <= blob_record;
                        hmac_start <= 1'b1;
                        state <= ST_OPEN_TAG_WAIT;
                    end
                    ST_OPEN_TAG_WAIT: if (hmac_done) begin
                        hmac_key <= 256'd0;
                        hmac_message <= 256'd0;
                        if (hmac_digest[255:128] != blob_tag) begin
                            state <= ST_IDLE;
                            vault_loaded <= 1'b0;
                            vault_hmac_key <= 256'd0;
                            vault_clear_pulse <= vault_loaded;
                            scrub_private();
                            finish_status(RESULT_AUTH_FAILED, pending_counter,
                                          MODE_OPEN, 8'h01);
                        end else begin
                            state <= ST_OPEN_ENC_START;
                        end
                    end
                    ST_OPEN_ENC_START: begin
                        hmac_key <= root_key;
                        hmac_message <= root_context(ENC_LABEL);
                        hmac_start <= 1'b1;
                        state <= ST_OPEN_ENC_WAIT;
                    end
                    ST_OPEN_ENC_WAIT: if (hmac_done) begin
                        enc_key <= hmac_digest;
                        hmac_key <= 256'd0;
                        hmac_message <= 256'd0;
                        state <= ST_OPEN_AES_START;
                    end
                    ST_OPEN_AES_START: begin
                        aes_key <= enc_key;
                        aes_block <= ctr_block(blob_generation, blob_iv);
                        aes_start <= 1'b1;
                        state <= ST_OPEN_AES_WAIT;
                    end
                    ST_OPEN_AES_WAIT: if (aes_done) begin
                        seed_latched <= aes_ciphertext ^ blob_ciphertext;
                        aes_key <= 256'd0;
                        aes_block <= 128'd0;
                        state <= ST_OPEN_SEED_START;
                    end
                    ST_OPEN_SEED_START: begin
                        hmac_key <= root_key;
                        hmac_message <= root_context(SEED_LABEL);
                        hmac_start <= 1'b1;
                        state <= ST_OPEN_SEED_WAIT;
                    end
                    ST_OPEN_SEED_WAIT: if (hmac_done) begin
                        hmac_key <= 256'd0;
                        hmac_message <= 256'd0;
                        if (seed_latched != hmac_digest[255:128]) begin
                            state <= ST_IDLE;
                            vault_loaded <= 1'b0;
                            vault_hmac_key <= 256'd0;
                            vault_clear_pulse <= vault_loaded;
                            scrub_private();
                            finish_status(RESULT_AUTH_FAILED, pending_counter,
                                          MODE_OPEN, 8'h02);
                        end else begin
                            state <= ST_OPEN_HSM_START;
                        end
                    end
                    ST_OPEN_HSM_START: begin
                        hmac_key <= root_key;
                        hmac_message <= hsm_context(seed_latched);
                        hmac_start <= 1'b1;
                        state <= ST_OPEN_HSM_WAIT;
                    end
                    ST_OPEN_HSM_WAIT: if (hmac_done) begin
                        vault_hmac_key <= hmac_digest;
                        vault_loaded <= 1'b1;
                        vault_load_pulse <= 1'b1;
                        state <= ST_IDLE;
                        scrub_private();
                        finish_status(RESULT_OK, pending_counter, MODE_OPEN,
                                      blob_record[247:240]);
                    end

                    default: begin
                        state <= ST_IDLE;
                        vault_loaded <= 1'b0;
                        seal_authenticated <= 1'b0;
                        vault_hmac_key <= 256'd0;
                        vault_clear_pulse <= vault_loaded;
                        scrub_private();
                    end
                endcase
            end
        end
    end
endmodule
