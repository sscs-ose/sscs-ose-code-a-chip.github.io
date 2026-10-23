module hsm_shell #(
    parameter integer CHALLENGE_TTL_CYCLES = 100_000_000,
    // Compile the C4 internal ML-KEM K channel only into the compact demo
    // revision.  The qualification revision keeps the historical PUF/vault
    // branch and must not pay the area cost of a mutually exclusive demo path.
    parameter ENABLE_MLKEM_K_CHANNEL = 1'b1,
    // C5 live builds disable the synthesis-time HSM-4E ticket credential.
    // Qualification may retain it only for frozen historical regression.
    parameter ENABLE_STATIC_AUTH_PROVISION = 1'b1,
    parameter EXTERNAL_HMAC = 1'b0,
    // Academic HSM-4E trust anchor. It is deliberately outside ESP32
    // firmware, but remains a synthesis-time test credential rather than a
    // production fuse, secure element, or factory key hierarchy.
    parameter [255:0] PROVISION_AUTH_TEST_KEY =
        256'hA4207ACE7E535748418A38F215F3B1AAA34D0EA9EB52138E3B756DF70CBBB8F3
) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire         session_valid,
    input  wire [31:0]  device_id,
    input  wire         provision_enable,
    input  wire         sdm_transport_ready,
    input  wire [7:0]   sdm_transport_error,
    input  wire [63:0]  sdm_chip_id,
    input  wire         sdm_crypto_enabled,
    input  wire         sdm_crypto_mem_ready,
    input  wire [7:0]   sdm_crypto_mem_error,

    // Frozen HSM-1 command interface.
    input  wire         cmd_valid,
    input  wire [7:0]   cmd_id,
    input  wire [7:0]   cmd_arg,
    input  wire         key_use_pulse,
    // D2/D3 restores a validated PUF-wrapped vault record into this existing
    // HSM vault through a one-cycle internal-only path. No key bit traverses
    // the SPI response fabric.
    input  wire         puf_vault_load_pulse,
    input  wire         puf_vault_stage_pulse,
    input  wire         puf_vault_clear_pulse,
    input  wire [255:0] puf_vault_key,
    output wire         puf_vault_stage_authorized,
    output reg          done,
    output reg  [63:0]  response_data,

    // Compact HSM-2 interface carried by SPI opcodes 0x3A/0x3B.
    input  wire         ext_cmd_valid,
    input  wire         ext_header_valid,
    input  wire         ext_mlkem_pass,
    // C4 internal-only K handoff.  These buses terminate in HSM registers and
    // are never selected by the SPI response mux.
    input  wire         ext_mlkem_key_valid,
    input  wire [255:0] ext_mlkem_sender_key,
    input  wire [255:0] ext_mlkem_receiver_key,
    input  wire [7:0]   ext_api_version,
    input  wire [7:0]   ext_subcmd,
    input  wire [7:0]   ext_flags,
    input  wire [31:0]  ext_counter,
    input  wire [7:0]   ext_data_len,
    input  wire [255:0] ext_data,
    output reg          ext_done,
    output reg  [7:0]   ext_response_len,
    output reg  [255:0] ext_response_data,

    output reg          session_grant_pulse,
    output reg          mlkem_bind_consume_pulse,
    output reg          zeroize_pulse,
    output wire         hmac_req_start,
    output wire         hmac_req_scrub,
    output wire [255:0] hmac_req_key,
    output wire [255:0] hmac_req_message,
    output wire [5:0]   hmac_req_message_len,
    input  wire         hmac_rsp_busy,
    input  wire         hmac_rsp_done,
    input  wire [255:0] hmac_rsp_digest
);
    localparam [7:0] CMD_GET_INFO        = 8'h30;
    localparam [7:0] CMD_GET_STATUS      = 8'h32;
    localparam [7:0] CMD_KEY_STATUS      = 8'h34;
    localparam [7:0] CMD_ZEROIZE_SESSION = 8'h36;
    localparam [7:0] CMD_AUDIT_READ      = 8'h38;
    localparam [7:0] CMD_HSM_EXT         = 8'h3A;

    localparam [7:0] EXT_API_VERSION          = 8'h01;
    localparam [7:0] SUB_ATTEST_CHALLENGE     = 8'h10;
    localparam [7:0] SUB_ATTEST_VERIFY        = 8'h11;
    localparam [7:0] SUB_MLKEM_SESSION_BIND   = 8'h12;
    localparam [7:0] SUB_MLKEM_FRAME_SEAL     = 8'h13;
    localparam [7:0] SUB_SECURE_FRAME         = 8'h20;
    localparam [7:0] SUB_VAULT_PROVISION      = 8'h30;
    localparam [7:0] SUB_VAULT_STATUS         = 8'h31;
    localparam [7:0] SUB_VAULT_DESTROY        = 8'h32;
    localparam [7:0] SUB_VAULT_PREPARE        = 8'h33;
    localparam [7:0] SUB_VAULT_COMMIT         = 8'h34;
    localparam [7:0] SUB_VAULT_ABORT          = 8'h35;
    localparam [7:0] SUB_VAULT_REVOKE         = 8'h36;
    localparam [7:0] SUB_AUTH_PROVISION_PREPARE = 8'h37;
    localparam [7:0] SUB_KEY_CONFIRM             = 8'h38;

    localparam [7:0] RESULT_OK                = 8'h00;
    localparam [7:0] RESULT_AUTH_REQUIRED     = 8'h01;
    localparam [7:0] RESULT_INVALID_SLOT      = 8'h02;
    localparam [7:0] RESULT_NO_ENTRY          = 8'h03;
    localparam [7:0] RESULT_BAD_LENGTH        = 8'h04;
    localparam [7:0] RESULT_CHALLENGE_EXPIRED = 8'h05;
    localparam [7:0] RESULT_VERIFY_FAILED     = 8'h06;
    localparam [7:0] RESULT_REPLAY_DETECTED   = 8'h07;
    localparam [7:0] RESULT_LOCKED            = 8'h08;
    localparam [7:0] RESULT_POLICY_DENIED     = 8'h09;
    localparam [7:0] RESULT_AUTH_FAILED       = 8'h0A;
    localparam [7:0] RESULT_COUNTER_EXHAUSTED = 8'h0B;
    localparam [7:0] RESULT_BAD_COMMAND       = 8'h7F;

    localparam [7:0] SLOT_EMPTY  = 8'h00;
    localparam [7:0] SLOT_ACTIVE = 8'h01;
    localparam [7:0] SLOT_REVOKED = 8'h02;
    localparam [2:0] HMAC_NONE=3'd0, HMAC_ATTEST=3'd1,
                     HMAC_SECURE=3'd2, HMAC_CONFIRM=3'd3,
                     HMAC_MLKEM_SEAL=3'd4;

    // HSM-4A volatile vault. The key is never present in a response. It is
    // loaded only while the synchronized physical-presence input is asserted,
    // and is cleared by FPGA reset or an authorized VAULT_DESTROY command.
    reg [255:0] vault_hmac_key;
    reg         vault_active;
    reg [15:0]  vault_version;
    reg [7:0]   vault_state;
    reg [31:0]  last_vault_counter;
    reg         vault_counter_valid;
    // HSM-4C0 two-phase volatile provisioning. Prepared key material is
    // temporary and cannot service HMAC until an atomic commit.
    reg [255:0] vault_staged_key;
    reg         vault_staged_valid;
    reg [31:0]  vault_staged_prepare_counter;
    reg         vault_staged_authenticated;
    // HSM-4G requires the authenticated staging grant to be fulfilled by the
    // PUF vault service.  A provisioning ticket alone can no longer publish
    // its independent HMAC digest as an active key.
    reg         vault_staged_puf_bound;

    reg [15:0] usage_counter [0:3];
    reg [7:0]  audit_cmd      [0:7];
    reg [7:0]  audit_slot     [0:7];
    reg [7:0]  audit_result   [0:7];
    reg [7:0]  audit_usage    [0:7];
    reg [15:0] audit_seq      [0:7];
    reg [2:0]  audit_write_ptr;
    reg [3:0]  audit_count;
    reg [15:0] event_counter;
    reg [7:0]  zeroize_count;
    reg [7:0]  last_result;

    reg [127:0] challenge_state;
    reg [127:0] active_challenge;
    reg [31:0]  active_challenge_counter;
    reg [31:0]  challenge_timer;
    reg [31:0]  last_transaction_counter;
    reg [31:0]  last_verified_counter;
    reg         challenge_active;
    reg         transaction_counter_valid;
    reg         verified_counter_valid;
    reg [7:0]   attest_fail_count;
    reg         attest_lockout;
    reg         replay_seen;
    reg         session_slot_active;
    reg [15:0]  session_key_handle;
    reg [255:0] mlkem_sender_session_key;
    reg [255:0] mlkem_receiver_session_key;
    reg [31:0]  last_seal_counter;
    reg         seal_counter_valid;
    reg [31:0]  last_secure_counter;
    reg         secure_counter_valid;
    // Public, per-bind context identifier.  It is authenticated in every
    // SF2 frame so a captured frame from a prior binding cannot be replayed
    // after a new binding resets the per-session counter.
    reg [63:0]  session_epoch;

    reg         hmac_start;
    wire        hmac_busy;
    wire        hmac_done;
    wire [255:0] hmac_digest;
    reg [255:0] hmac_message;
    reg [5:0]   hmac_message_len;
    reg [2:0]   hmac_pending;
    reg [127:0] hmac_supplied_tag;
    reg [63:0]  hmac_payload;
    reg [31:0]  hmac_counter;

    localparam [1:0] PROV_IDLE=2'd0, PROV_AUTH_WAIT=2'd1,
                     PROV_DERIVE_START=2'd2, PROV_DERIVE_WAIT=2'd3;
    localparam [31:0] PROV_AUTH_DOMAIN   = 32'h54455031; // "TEP1"
    localparam [31:0] PROV_DERIVE_DOMAIN = 32'h54454B31; // "TEK1"
    localparam [31:0] PROV_SIGNER_ID     = 32'h53494731; // "SIG1"
    reg [1:0]   prov_state;
    reg         prov_hmac_start;
    wire        prov_hmac_busy;
    wire        prov_hmac_done;
    wire [255:0] prov_hmac_digest;
    reg [255:0] prov_hmac_message;
    reg [127:0] prov_request;
    reg [127:0] prov_supplied_tag;
    reg [31:0]  prov_counter;

    reg [7:0]   result_now;
    reg [7:0]   slot_now;
    reg [7:0]   slot_type;
    reg [7:0]   slot_permissions;
    reg [7:0]   slot_state;
    reg [2:0]   audit_read_ptr;
    reg [255:0] ext_resp_now;
    reg [7:0]   ext_len_now;
    reg [127:0] challenge_now;
    reg [15:0]  usage_now;
    reg         defer_response;
    integer i;

    function automatic [127:0] make_challenge;
        input [127:0] state_in;
        input [31:0] counter_in;
        input [31:0] device_in;
        reg feedback;
        begin
            feedback = state_in[127] ^ state_in[125] ^
                       state_in[100] ^ state_in[98];
            make_challenge = {state_in[126:0], feedback} ^
                             {4{counter_in}} ^ {4{device_in}};
        end
    endfunction

    function automatic [255:0] make_attest_message;
        input [127:0] challenge_in;
        input [31:0] counter_in;
        begin
            make_attest_message = 256'd0;
            make_attest_message[255:192] = 64'h5472757374415431; // "TrustAT1"
            make_attest_message[191:160] = counter_in;
            make_attest_message[159:32]  = challenge_in;
        end
    endfunction

    function automatic [255:0] make_secure_message;
        input [63:0] payload_in;
        input [31:0] counter_in;
        input [63:0] epoch_in;
        begin
            make_secure_message = 256'd0;
            make_secure_message[255:192] = 64'h5472757374534632; // "TrustSF2"
            make_secure_message[191:128] = epoch_in;
            make_secure_message[127:96]  = counter_in;
            make_secure_message[95:32]   = payload_in;
        end
    endfunction

    function automatic [255:0] make_confirm_message;
        input [127:0] nonce_in;
        begin
            make_confirm_message = {64'h54727573744B4331, nonce_in, 64'd0};
        end
    endfunction

    function automatic [255:0] make_provision_message;
        input [31:0] domain_in;
        input [63:0] chip_id_in;
        input [31:0] counter_in;
        input [127:0] request_in;
        begin
            // 4-byte domain || 8-byte device CHIPID || 4-byte monotonic
            // transaction counter || 16-byte signer/policy/public seed.
            make_provision_message = {domain_in, chip_id_in, counter_in,
                                      request_in};
        end
    endfunction

    wire legacy_zeroize_request = cmd_valid &&
                                  (cmd_id == CMD_ZEROIZE_SESSION);
    wire provision_hmac_scrub = legacy_zeroize_request ||
                                puf_vault_clear_pulse ||
                                puf_vault_load_pulse ||
                                puf_vault_stage_pulse;

    assign puf_vault_stage_authorized = vault_staged_valid &&
                                        vault_staged_authenticated &&
                                        !vault_staged_puf_bound &&
                                        vault_state == SLOT_EMPTY;

    // The SPI bridge admits one deferred HSM request at a time, therefore
    // provisioning and session HMAC operations cannot overlap.  Share the
    // iterative SHA-256 datapath instead of spending a second ~3k-ALM engine.
    // prov_state remains non-idle from start through digest consumption, so
    // key/message selection is stable for the complete operation.
    wire shared_hmac_provision = (prov_state != PROV_IDLE);
    wire shared_hmac_busy;
    wire shared_hmac_done;
    wire [255:0] shared_hmac_digest;
    wire internal_hmac_busy;
    wire internal_hmac_done;
    wire [255:0] internal_hmac_digest;
    assign hmac_req_scrub = legacy_zeroize_request || provision_hmac_scrub;
    assign hmac_req_start = hmac_start || prov_hmac_start;
    assign hmac_req_key = shared_hmac_provision ? PROVISION_AUTH_TEST_KEY :
                          (ENABLE_MLKEM_K_CHANNEL &&
                           hmac_pending == HMAC_MLKEM_SEAL) ? mlkem_sender_session_key :
                          (ENABLE_MLKEM_K_CHANNEL &&
                           hmac_pending == HMAC_SECURE) ? mlkem_receiver_session_key :
                                                        vault_hmac_key;
    assign hmac_req_message = shared_hmac_provision ? prov_hmac_message :
                                                     hmac_message;
    assign hmac_req_message_len = shared_hmac_provision ? 6'd32 :
                                                         hmac_message_len;
    assign shared_hmac_busy = EXTERNAL_HMAC ? hmac_rsp_busy :
                                                internal_hmac_busy;
    assign shared_hmac_done = EXTERNAL_HMAC ? hmac_rsp_done :
                                                internal_hmac_done;
    assign shared_hmac_digest = EXTERNAL_HMAC ? hmac_rsp_digest :
                                                  internal_hmac_digest;

    generate if (!EXTERNAL_HMAC) begin : g_internal_hmac
    hmac_sha256_fixed u_shared_hmac (
        .clk(clk), .rst_n(rst_n),
        .scrub(hmac_req_scrub), .start(hmac_req_start),
        .key(hmac_req_key), .message(hmac_req_message),
        .message_len(hmac_req_message_len),
        .busy(internal_hmac_busy), .done(internal_hmac_done),
        .digest(internal_hmac_digest)
    );
    end else begin : g_no_internal_hmac
        assign internal_hmac_busy = 1'b0;
        assign internal_hmac_done = 1'b0;
        assign internal_hmac_digest = 256'd0;
    end endgenerate
    assign hmac_busy = shared_hmac_busy && !shared_hmac_provision;
    assign hmac_done = shared_hmac_done && !shared_hmac_provision;
    assign hmac_digest = shared_hmac_digest;
    assign prov_hmac_busy = shared_hmac_busy && shared_hmac_provision;
    assign prov_hmac_done = shared_hmac_done && shared_hmac_provision;
    assign prov_hmac_digest = shared_hmac_digest;

    wire hmac_attest_success = hmac_done && (hmac_pending == HMAC_ATTEST) &&
                               (hmac_digest[255:128] == hmac_supplied_tag);

    wire ext_bind_success = ext_cmd_valid && ext_header_valid &&
                            (ext_api_version == EXT_API_VERSION) &&
                            (ext_flags == 8'd0) &&
                            (ext_subcmd == SUB_MLKEM_SESSION_BIND) &&
                            (ext_data_len == 8'd2) &&
                            !(transaction_counter_valid &&
                              ext_counter <= last_transaction_counter) &&
                            (ext_data[255:248] == 8'd2) &&
                            (ext_data[247:240] == 8'd3) && ext_mlkem_pass &&
                            (!ENABLE_MLKEM_K_CHANNEL ||
                             (ext_mlkem_key_valid &&
                              ext_mlkem_sender_key == ext_mlkem_receiver_key));

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            done                       <= 1'b0;
            response_data              <= 64'd0;
            ext_done                   <= 1'b0;
            ext_response_len           <= 8'd0;
            ext_response_data          <= 256'd0;
            session_grant_pulse        <= 1'b0;
            mlkem_bind_consume_pulse   <= 1'b0;
            zeroize_pulse              <= 1'b0;
            audit_write_ptr            <= 3'd0;
            audit_count                <= 4'd0;
            event_counter              <= 16'd0;
            zeroize_count              <= 8'd0;
            last_result                <= RESULT_OK;
            challenge_state            <= 128'hA5C3_19E7_4D2B_806F_1357_9BDF_2468_ACE1;
            active_challenge           <= 128'd0;
            active_challenge_counter   <= 32'd0;
            challenge_timer            <= 32'd0;
            last_transaction_counter   <= 32'd0;
            last_verified_counter      <= 32'd0;
            challenge_active           <= 1'b0;
            transaction_counter_valid  <= 1'b0;
            verified_counter_valid     <= 1'b0;
            attest_fail_count          <= 8'd0;
            attest_lockout             <= 1'b0;
            replay_seen                <= 1'b0;
            session_slot_active        <= 1'b0;
            session_key_handle         <= 16'd0;
            mlkem_sender_session_key   <= 256'd0;
            mlkem_receiver_session_key <= 256'd0;
            last_seal_counter          <= 32'd0;
            seal_counter_valid         <= 1'b0;
            last_secure_counter        <= 32'd0;
            secure_counter_valid       <= 1'b0;
            session_epoch              <= 64'd0;
            hmac_start                 <= 1'b0;
            hmac_message               <= 256'd0;
            hmac_message_len           <= 6'd0;
            hmac_pending               <= HMAC_NONE;
            hmac_supplied_tag          <= 128'd0;
            hmac_payload               <= 64'd0;
            hmac_counter               <= 32'd0;
            vault_hmac_key              <= 256'd0;
            vault_active                <= 1'b0;
            vault_version               <= 16'd0;
            vault_state                 <= SLOT_EMPTY;
            last_vault_counter          <= 32'd0;
            vault_counter_valid         <= 1'b0;
            vault_staged_key            <= 256'd0;
            vault_staged_valid          <= 1'b0;
            vault_staged_prepare_counter<= 32'd0;
            vault_staged_authenticated  <= 1'b0;
            vault_staged_puf_bound      <= 1'b0;
            prov_state                  <= PROV_IDLE;
            prov_hmac_start             <= 1'b0;
            prov_hmac_message           <= 256'd0;
            prov_request                <= 128'd0;
            prov_supplied_tag           <= 128'd0;
            prov_counter                <= 32'd0;
            for (i = 0; i < 4; i = i + 1)
                usage_counter[i] <= 16'd0;
            for (i = 0; i < 8; i = i + 1) begin
                audit_cmd[i]    <= 8'd0;
                audit_slot[i]   <= 8'hFF;
                audit_result[i] <= 8'd0;
                audit_usage[i]  <= 8'd0;
                audit_seq[i]    <= 16'd0;
            end
        end else begin
            done                <= 1'b0;
            ext_done            <= 1'b0;
            hmac_start               <= 1'b0;
            prov_hmac_start          <= 1'b0;
            session_grant_pulse      <= hmac_attest_success || ext_bind_success;
            mlkem_bind_consume_pulse <= ext_bind_success;
            zeroize_pulse            <= legacy_zeroize_request;

            // A failed D2/D3 record verification revokes any previously
            // restored HSM vault before another command can consume it.
            // A successful D2/D3 open then loads an internal derived key
            // without physical presence; authenticity is provided by the
            // PUF-root-bound Encrypt-then-MAC record, not by the ESP32.
            if (puf_vault_clear_pulse) begin
                vault_hmac_key              <= 256'd0;
                vault_active                <= 1'b0;
                vault_state                 <= SLOT_EMPTY;
                vault_version               <= 16'd0;
                vault_staged_key            <= 256'd0;
                vault_staged_valid          <= 1'b0;
                vault_staged_prepare_counter<= 32'd0;
                vault_staged_authenticated  <= 1'b0;
                vault_staged_puf_bound      <= 1'b0;
                prov_state                  <= PROV_IDLE;
                prov_hmac_message           <= 256'd0;
                prov_request                <= 128'd0;
                prov_supplied_tag           <= 128'd0;
                prov_counter                <= 32'd0;
                usage_counter[0]            <= 16'd0;
                challenge_active            <= 1'b0;
                challenge_timer             <= 32'd0;
                session_slot_active         <= 1'b0;
                session_key_handle          <= 16'd0;
                mlkem_sender_session_key    <= 256'd0;
                mlkem_receiver_session_key  <= 256'd0;
                last_seal_counter           <= 32'd0;
                seal_counter_valid          <= 1'b0;
                last_secure_counter         <= 32'd0;
                secure_counter_valid        <= 1'b0;
                session_epoch               <= 64'd0;
            end else if (puf_vault_load_pulse) begin
                vault_hmac_key              <= puf_vault_key;
                vault_active                <= 1'b1;
                vault_state                 <= SLOT_ACTIVE;
                vault_version               <= 16'hD203;
                vault_staged_key            <= 256'd0;
                vault_staged_valid          <= 1'b0;
                vault_staged_prepare_counter<= 32'd0;
                vault_staged_authenticated  <= 1'b0;
                vault_staged_puf_bound      <= 1'b0;
                prov_state                  <= PROV_IDLE;
                prov_hmac_message           <= 256'd0;
                prov_request                <= 128'd0;
                prov_supplied_tag           <= 128'd0;
                prov_counter                <= 32'd0;
                usage_counter[0]            <= 16'd0;
                challenge_active            <= 1'b0;
                challenge_timer             <= 32'd0;
                session_slot_active         <= 1'b0;
                session_key_handle          <= 16'd0;
                mlkem_sender_session_key    <= 256'd0;
                mlkem_receiver_session_key  <= 256'd0;
                last_seal_counter           <= 32'd0;
                seal_counter_valid          <= 1'b0;
                last_secure_counter         <= 32'd0;
                secure_counter_valid        <= 1'b0;
                session_epoch               <= 64'd0;
            end else if (puf_vault_stage_pulse) begin
                // Internal-only handoff after authenticated PUF wrapping.  A
                // pulse without the one-time authorization grant is ignored.
                if (puf_vault_stage_authorized) begin
                    vault_staged_key       <= puf_vault_key;
                    vault_staged_puf_bound <= 1'b1;
                end
            end

            if (challenge_active) begin
                if (challenge_timer >= CHALLENGE_TTL_CYCLES - 1) begin
                    challenge_active <= 1'b0;
                    challenge_timer  <= 32'd0;
                end else begin
                    challenge_timer <= challenge_timer + 32'd1;
                end
            end

            // Slot 2 represents the non-exportable ML-KEM secret placeholder.
            if (key_use_pulse && usage_counter[2] != 16'hFFFF)
                usage_counter[2] <= usage_counter[2] + 16'd1;

            if (cmd_valid) begin
                result_now = RESULT_OK;
                slot_now   = 8'hFF;
                slot_type  = 8'd0;
                slot_permissions = 8'd0;
                slot_state = SLOT_EMPTY;

                case (cmd_id)
                    CMD_GET_INFO: begin
                        // Version 7.0 identifies HSM-4G: authenticated staging
                        // must be fulfilled by the PUF-wrapped same-key path. The
                        // synthesis-time credential remains an academic test
                        // anchor, not a production fuse or factory root.
                        response_data <= {RESULT_OK, 8'd7, 8'd0, 8'hFF,
                                          8'd4, 8'd0, 8'd8, 8'd1};
                    end

                    CMD_GET_STATUS: begin
                        response_data <= {RESULT_OK,
                                          {7'd0, session_valid},
                                          {7'd0, attest_lockout},
                                          {7'd0, replay_seen},
                                          {4'd0, audit_count},
                                          session_slot_active ? SLOT_ACTIVE : SLOT_EMPTY,
                                          zeroize_count,
                                          last_result};
                    end

                    CMD_KEY_STATUS: begin
                        slot_now = cmd_arg;
                        if (!session_valid) begin
                            result_now = RESULT_AUTH_REQUIRED;
                            response_data <= {RESULT_AUTH_REQUIRED, cmd_arg,
                                              8'd0, 8'd0, 8'd0, SLOT_EMPTY,
                                              16'd0};
                        end else if (cmd_arg > 8'd3) begin
                            result_now = RESULT_INVALID_SLOT;
                            response_data <= {RESULT_INVALID_SLOT, cmd_arg,
                                              8'd0, 8'd0, 8'd0, SLOT_EMPTY,
                                              16'd0};
                        end else begin
                            case (cmd_arg[1:0])
                                2'd0: begin
                                    slot_type = (vault_state != SLOT_EMPTY) ? 8'h05 : 8'h00;
                                    slot_permissions = vault_active ? 8'h21 : 8'h00;
                                    slot_state = vault_state;
                                end
                                2'd1: begin
                                    slot_type = 8'h02;
                                    slot_permissions = 8'h02;
                                    slot_state = SLOT_ACTIVE;
                                end
                                2'd2: begin
                                    slot_type = 8'h03;
                                    slot_permissions = 8'h04;
                                    slot_state = SLOT_ACTIVE;
                                end
                                default: begin
                                    slot_type = 8'h04;
                                    slot_permissions = 8'h18;
                                    slot_state = session_slot_active ?
                                                 SLOT_ACTIVE : SLOT_EMPTY;
                                end
                            endcase
                            response_data <= {RESULT_OK, cmd_arg, slot_type,
                                              slot_permissions, 8'd0, slot_state,
                                              usage_counter[cmd_arg[1:0]]};
                        end
                    end

                    CMD_ZEROIZE_SESSION: begin
                        challenge_active     <= 1'b0;
                        challenge_timer      <= 32'd0;
                        session_slot_active  <= 1'b0;
                        session_key_handle   <= 16'd0;
                        mlkem_sender_session_key <= 256'd0;
                        mlkem_receiver_session_key <= 256'd0;
                        last_seal_counter    <= 32'd0;
                        seal_counter_valid   <= 1'b0;
                        last_secure_counter  <= 32'd0;
                        secure_counter_valid <= 1'b0;
                        session_epoch        <= 64'd0;
                        usage_counter[3]     <= 16'd0;
                        vault_staged_key     <= 256'd0;
                        vault_staged_valid   <= 1'b0;
                        vault_staged_prepare_counter <= 32'd0;
                        vault_staged_authenticated <= 1'b0;
                        vault_staged_puf_bound <= 1'b0;
                        prov_state           <= PROV_IDLE;
                        prov_hmac_message    <= 256'd0;
                        prov_request         <= 128'd0;
                        prov_supplied_tag    <= 128'd0;
                        prov_counter         <= 32'd0;
                        if (zeroize_count != 8'hFF)
                            zeroize_count <= zeroize_count + 8'd1;
                        response_data <= {RESULT_OK, 8'd0, SLOT_EMPTY,
                                          zeroize_count + 8'd1, 32'd0};
                    end

                    CMD_AUDIT_READ: begin
                        if (!session_valid) begin
                            result_now = RESULT_AUTH_REQUIRED;
                            response_data <= {RESULT_AUTH_REQUIRED, 56'd0};
                        end else if (cmd_arg >= audit_count) begin
                            result_now = RESULT_NO_ENTRY;
                            response_data <= {RESULT_NO_ENTRY, 56'd0};
                        end else begin
                            if (audit_count == 4'd8)
                                audit_read_ptr = audit_write_ptr + cmd_arg[2:0];
                            else
                                audit_read_ptr = cmd_arg[2:0];
                            response_data <= {RESULT_OK, 8'd1,
                                              audit_seq[audit_read_ptr],
                                              audit_cmd[audit_read_ptr],
                                              audit_slot[audit_read_ptr],
                                              audit_result[audit_read_ptr],
                                              audit_usage[audit_read_ptr]};
                        end
                    end

                    default: begin
                        result_now = RESULT_BAD_COMMAND;
                        response_data <= {RESULT_BAD_COMMAND, 56'd0};
                    end
                endcase

                audit_cmd[audit_write_ptr]    <= cmd_id;
                audit_slot[audit_write_ptr]   <= slot_now;
                audit_result[audit_write_ptr] <= result_now;
                audit_usage[audit_write_ptr]  <= (slot_now <= 8'd3) ?
                                                  usage_counter[slot_now[1:0]][7:0] : 8'd0;
                audit_seq[audit_write_ptr]    <= event_counter;
                audit_write_ptr <= audit_write_ptr + 3'd1;
                if (audit_count != 4'd8)
                    audit_count <= audit_count + 4'd1;
                event_counter <= event_counter + 16'd1;
                last_result   <= result_now;
                done          <= 1'b1;
            end

            // HMAC-backed commands complete asynchronously after four SHA-256
            // compression blocks. The SPI bridge remains in its wait state.
            if (hmac_done && hmac_pending != HMAC_NONE) begin
                ext_resp_now = 256'd0;
                ext_resp_now[255:248] = EXT_API_VERSION;
                ext_resp_now[247:240] = (hmac_pending == HMAC_ATTEST) ?
                                         SUB_ATTEST_VERIFY :
                                         (hmac_pending == HMAC_MLKEM_SEAL) ?
                                         SUB_MLKEM_FRAME_SEAL :
                                         (hmac_pending == HMAC_CONFIRM) ?
                                         SUB_KEY_CONFIRM : SUB_SECURE_FRAME;
                ext_resp_now[231:200] = hmac_counter;
                result_now = RESULT_OK;

                if (hmac_pending == HMAC_ATTEST) begin
                    ext_len_now = 8'd11;
                    if (hmac_digest[255:128] != hmac_supplied_tag) begin
                        if (attest_fail_count >= 8'd2) begin
                            attest_fail_count <= 8'd3;
                            attest_lockout    <= 1'b1;
                            result_now        = RESULT_LOCKED;
                        end else begin
                            attest_fail_count <= attest_fail_count + 8'd1;
                            result_now        = RESULT_VERIFY_FAILED;
                        end
                        ext_resp_now[199:192] = 8'd0;
                        ext_resp_now[191:184] = attest_fail_count + 8'd1;
                        ext_resp_now[183:176] = (attest_fail_count >= 8'd2) ? 8'd1 : 8'd0;
                        ext_resp_now[175:168] = 8'd0;
                    end else begin
                        if (usage_counter[0] != 16'hFFFF)
                            usage_counter[0] <= usage_counter[0] + 16'd1;
                        attest_fail_count      <= 8'd0;
                        last_verified_counter  <= hmac_counter;
                        verified_counter_valid <= 1'b1;
                        ext_resp_now[199:192]  = 8'd1;
                        ext_resp_now[191:184]  = 8'd0;
                        ext_resp_now[183:176]  = 8'd0;
                        ext_resp_now[175:168]  = session_slot_active ? 8'd1 : 8'd0;
                    end
                end else if (hmac_pending == HMAC_MLKEM_SEAL) begin
                    // Sender role returns only the public payload and its
                    // authentication tag.  The 256-bit K remains internal.
                    ext_len_now = 8'd31;
                    ext_resp_now[199:136] = hmac_payload;
                    ext_resp_now[135:8]   = hmac_digest[255:128];
                    last_seal_counter     <= hmac_counter;
                    seal_counter_valid    <= 1'b1;
                end else if (hmac_pending == HMAC_SECURE) begin
                    ext_len_now = 8'd15;
                    if (hmac_digest[255:128] != hmac_supplied_tag) begin
                        result_now = RESULT_AUTH_FAILED;
                    end else begin
                        if (usage_counter[0] != 16'hFFFF)
                            usage_counter[0] <= usage_counter[0] + 16'd1;
                        last_secure_counter  <= hmac_counter;
                        secure_counter_valid <= 1'b1;
                        ext_resp_now[199:136] = hmac_payload;
                    end
                end else begin
                    // Diagnostic key confirmation: return a one-way HMAC of a
                    // caller nonce. Repeating the nonce after restore proves
                    // key continuity without exporting any key bit.
                    ext_len_now = 8'd23;
                    ext_resp_now[199:72] = hmac_digest[255:128];
                end

                ext_resp_now[239:232] = result_now;
                ext_response_data <= ext_resp_now;
                ext_response_len  <= ext_len_now;
                ext_done          <= 1'b1;
                hmac_pending      <= HMAC_NONE;

                audit_cmd[audit_write_ptr]    <= CMD_HSM_EXT;
                audit_slot[audit_write_ptr]   <= (hmac_pending == HMAC_ATTEST) ?
                                                  SUB_ATTEST_VERIFY :
                                                  (hmac_pending == HMAC_MLKEM_SEAL) ?
                                                  SUB_MLKEM_FRAME_SEAL :
                                                  (hmac_pending == HMAC_CONFIRM) ?
                                                  SUB_KEY_CONFIRM : SUB_SECURE_FRAME;
                audit_result[audit_write_ptr] <= result_now;
                audit_usage[audit_write_ptr]  <=
                    (result_now == RESULT_OK && usage_counter[0] != 16'hFFFF) ?
                    usage_counter[0][7:0] + 8'd1 : usage_counter[0][7:0];
                audit_seq[audit_write_ptr]    <= event_counter;
                audit_write_ptr <= audit_write_ptr + 3'd1;
                if (audit_count != 4'd8)
                    audit_count <= audit_count + 4'd1;
                event_counter <= event_counter + 16'd1;
                last_result   <= result_now;
            end

            // HSM-4G keeps the historical two-domain authorization check, but
            // the second digest is no longer publishable key material.  It is
            // only a successful one-time grant for the PUF vault service.
            if (prov_state == PROV_DERIVE_START && !prov_hmac_busy) begin
                prov_hmac_message <= make_provision_message(
                    PROV_DERIVE_DOMAIN, sdm_chip_id, prov_counter, prov_request);
                prov_hmac_start <= 1'b1;
                prov_state <= PROV_DERIVE_WAIT;
            end

            if (prov_hmac_done) begin
                if (prov_state == PROV_AUTH_WAIT) begin
                    if (prov_hmac_digest[255:128] != prov_supplied_tag) begin
                        ext_resp_now = 256'd0;
                        ext_resp_now[255:248] = EXT_API_VERSION;
                        ext_resp_now[247:240] = SUB_AUTH_PROVISION_PREPARE;
                        ext_resp_now[239:232] = RESULT_AUTH_FAILED;
                        ext_resp_now[231:200] = prov_counter;
                        ext_response_data <= ext_resp_now;
                        ext_response_len  <= 8'd7;
                        ext_done          <= 1'b1;
                        prov_state        <= PROV_IDLE;
                        prov_hmac_message <= 256'd0;
                        prov_request      <= 128'd0;
                        prov_supplied_tag <= 128'd0;

                        audit_cmd[audit_write_ptr]    <= CMD_HSM_EXT;
                        audit_slot[audit_write_ptr]   <= SUB_AUTH_PROVISION_PREPARE;
                        audit_result[audit_write_ptr] <= RESULT_AUTH_FAILED;
                        audit_usage[audit_write_ptr]  <= usage_counter[0][7:0];
                        audit_seq[audit_write_ptr]    <= event_counter;
                        audit_write_ptr <= audit_write_ptr + 3'd1;
                        if (audit_count != 4'd8)
                            audit_count <= audit_count + 4'd1;
                        event_counter <= event_counter + 16'd1;
                        last_result   <= RESULT_AUTH_FAILED;
                    end else begin
                        prov_state <= PROV_DERIVE_START;
                    end
                end else if (prov_state == PROV_DERIVE_WAIT) begin
                    vault_staged_key             <= 256'd0;
                    vault_staged_valid           <= 1'b1;
                    vault_staged_authenticated   <= 1'b1;
                    vault_staged_puf_bound       <= 1'b0;
                    vault_staged_prepare_counter <= prov_counter;

                    ext_resp_now = 256'd0;
                    ext_resp_now[255:248] = EXT_API_VERSION;
                    ext_resp_now[247:240] = SUB_AUTH_PROVISION_PREPARE;
                    ext_resp_now[239:232] = RESULT_OK;
                    ext_resp_now[231:200] = prov_counter;
                    ext_resp_now[199:192] = 8'd0;
                    ext_resp_now[191:184] = SLOT_EMPTY;
                    ext_resp_now[183:176] = 8'd1;
                    ext_resp_now[175:168] = 8'd1;
                    ext_resp_now[167:136] = prov_counter;
                    ext_response_data <= ext_resp_now;
                    ext_response_len  <= 8'd15;
                    ext_done          <= 1'b1;
                    prov_state        <= PROV_IDLE;
                    prov_hmac_message <= 256'd0;
                    prov_request      <= 128'd0;
                    prov_supplied_tag <= 128'd0;

                    audit_cmd[audit_write_ptr]    <= CMD_HSM_EXT;
                    audit_slot[audit_write_ptr]   <= SUB_AUTH_PROVISION_PREPARE;
                    audit_result[audit_write_ptr] <= RESULT_OK;
                    audit_usage[audit_write_ptr]  <= usage_counter[0][7:0];
                    audit_seq[audit_write_ptr]    <= event_counter;
                    audit_write_ptr <= audit_write_ptr + 3'd1;
                    if (audit_count != 4'd8)
                        audit_count <= audit_count + 4'd1;
                    event_counter <= event_counter + 16'd1;
                    last_result   <= RESULT_OK;
                end
            end

            // Legacy and compact commands are mutually exclusive at the SPI
            // bridge. Keep the blocks independent so cmd_valid is not also
            // inferred as a synchronous clear for compact-command pulses.
            if (ext_cmd_valid) begin
                ext_resp_now = 256'd0;
                ext_len_now  = 8'd7;
                result_now   = RESULT_OK;
                defer_response = 1'b0;

                ext_resp_now[255:248] = EXT_API_VERSION;
                ext_resp_now[247:240] = ext_subcmd;
                ext_resp_now[231:200] = ext_counter;

                if (!ext_header_valid) begin
                    result_now = RESULT_BAD_LENGTH;
                end else if (ext_api_version != EXT_API_VERSION) begin
                    result_now = RESULT_BAD_COMMAND;
                end else if (ext_flags != 8'd0) begin
                    result_now = RESULT_POLICY_DENIED;
                end else if (hmac_busy || hmac_pending != HMAC_NONE ||
                             prov_hmac_busy || prov_state != PROV_IDLE) begin
                    result_now = RESULT_POLICY_DENIED;
                end else begin
                    case (ext_subcmd)
                        SUB_ATTEST_CHALLENGE: begin
                            if (ext_data_len != 8'd0) begin
                                result_now = RESULT_BAD_LENGTH;
                            end else if (!vault_active) begin
                                result_now = RESULT_NO_ENTRY;
                            end else if (attest_lockout) begin
                                result_now = RESULT_LOCKED;
                            end else if (transaction_counter_valid &&
                                         ext_counter <= last_transaction_counter) begin
                                result_now = RESULT_REPLAY_DETECTED;
                                replay_seen <= 1'b1;
                            end else begin
                                challenge_now = make_challenge(challenge_state,
                                                               ext_counter,
                                                               device_id);
                                challenge_state          <= challenge_now;
                                active_challenge         <= challenge_now;
                                active_challenge_counter <= ext_counter;
                                challenge_active         <= 1'b1;
                                challenge_timer          <= 32'd0;
                                last_transaction_counter <= ext_counter;
                                transaction_counter_valid<= 1'b1;
                                ext_len_now               = 8'd25;
                                ext_resp_now[199:72]      = challenge_now;
                                ext_resp_now[71:56]       = 16'd2000;
                            end
                        end

                        SUB_ATTEST_VERIFY: begin
                            if (ext_data_len != 8'd16) begin
                                result_now = RESULT_BAD_LENGTH;
                            end else if (attest_lockout) begin
                                result_now = RESULT_LOCKED;
                            end else if (verified_counter_valid &&
                                         ext_counter == last_verified_counter &&
                                         !challenge_active) begin
                                result_now = RESULT_REPLAY_DETECTED;
                                replay_seen <= 1'b1;
                            end else if (!challenge_active) begin
                                result_now = RESULT_CHALLENGE_EXPIRED;
                            end else if (ext_counter != active_challenge_counter) begin
                                result_now = RESULT_REPLAY_DETECTED;
                                replay_seen <= 1'b1;
                            end else begin
                                challenge_active <= 1'b0;
                                hmac_message      <= make_attest_message(active_challenge,
                                                                          ext_counter);
                                hmac_message_len  <= 6'd28;
                                hmac_supplied_tag <= ext_data[255:128];
                                hmac_counter      <= ext_counter;
                                hmac_pending      <= HMAC_ATTEST;
                                hmac_start        <= 1'b1;
                                defer_response     = 1'b1;
                            end
                        end

                        SUB_MLKEM_SESSION_BIND: begin
                            if (ext_data_len != 8'd2) begin
                                result_now = RESULT_BAD_LENGTH;
                            end else if (transaction_counter_valid &&
                                         ext_counter <= last_transaction_counter) begin
                                result_now = RESULT_REPLAY_DETECTED;
                                replay_seen <= 1'b1;
                            end else begin
                                last_transaction_counter <= ext_counter;
                                transaction_counter_valid<= 1'b1;
                                if (ext_data[255:248] != 8'd2 ||
                                             ext_data[247:240] != 8'd3 ||
                                             !ext_mlkem_pass ||
                                             (ENABLE_MLKEM_K_CHANNEL &&
                                              (!ext_mlkem_key_valid ||
                                               ext_mlkem_sender_key !=
                                               ext_mlkem_receiver_key))) begin
                                    result_now = RESULT_POLICY_DENIED;
                                end else begin
                                    usage_now = (usage_counter[3] == 16'hFFFF) ?
                                                16'hFFFF : usage_counter[3] + 16'd1;
                                    session_key_handle  <= ext_counter[15:0] ^ 16'hB17D;
                                    session_slot_active <= 1'b1;
                                    if (ENABLE_MLKEM_K_CHANNEL) begin
                                        mlkem_sender_session_key <= ext_mlkem_sender_key;
                                        mlkem_receiver_session_key <= ext_mlkem_receiver_key;
                                    end
                                    last_seal_counter    <= 32'd0;
                                    seal_counter_valid   <= 1'b0;
                                    last_secure_counter  <= 32'd0;
                                    secure_counter_valid <= 1'b0;
                                    // The bind transaction counter is unique
                                    // until reset and becomes a public context
                                    // identifier only after this successful
                                    // full-K binding.  SF2 authenticates it.
                                    session_epoch        <= {32'h53463231, ext_counter};
                                    usage_counter[3]    <= usage_now;
                                    ext_len_now = 8'd23;
                                    ext_resp_now[199:184] = ext_counter[15:0] ^ 16'hB17D;
                                    ext_resp_now[183:176] = 8'd2;
                                    ext_resp_now[175:168] = 8'd3;
                                    ext_resp_now[167:160] = SLOT_ACTIVE;
                                    ext_resp_now[159:152] = 8'd0;
                                    ext_resp_now[151:136] = usage_now;
                                    ext_resp_now[135:72] = {32'h53463231, ext_counter};
                                end
                            end
                        end

                        SUB_MLKEM_FRAME_SEAL: begin
                            if (!ENABLE_MLKEM_K_CHANNEL) begin
                                result_now = RESULT_BAD_COMMAND;
                            end else if (ext_data_len != 8'd8) begin
                                result_now = RESULT_BAD_LENGTH;
                            end else if (!session_valid || !session_slot_active) begin
                                result_now = RESULT_AUTH_REQUIRED;
                            end else if (ext_counter == 32'hFFFF_FFFF) begin
                                result_now = RESULT_COUNTER_EXHAUSTED;
                            end else if (seal_counter_valid &&
                                         ext_counter <= last_seal_counter) begin
                                result_now = RESULT_REPLAY_DETECTED;
                                replay_seen <= 1'b1;
                            end else begin
                                hmac_message      <= make_secure_message(
                                                        ext_data[255:192],
                                                        ext_counter,
                                                        session_epoch);
                                hmac_message_len  <= 6'd28;
                                hmac_payload      <= ext_data[255:192];
                                hmac_counter      <= ext_counter;
                                hmac_pending      <= HMAC_MLKEM_SEAL;
                                hmac_start        <= 1'b1;
                                defer_response    = 1'b1;
                            end
                        end

                        SUB_SECURE_FRAME: begin
                            if (ext_data_len != 8'd32) begin
                                result_now = RESULT_BAD_LENGTH;
                            end else if (!session_valid || !session_slot_active) begin
                                result_now = RESULT_AUTH_REQUIRED;
                            end else if (ext_counter == 32'hFFFF_FFFF) begin
                                result_now = RESULT_COUNTER_EXHAUSTED;
                            end else if (ext_data[255:192] != session_epoch) begin
                                // SF2 never lets the caller select a prior
                                // bind context.  Reject before updating the
                                // replay state; the epoch itself is public.
                                result_now = RESULT_AUTH_FAILED;
                            end else if (secure_counter_valid &&
                                         ext_counter <= last_secure_counter) begin
                                result_now = RESULT_REPLAY_DETECTED;
                                replay_seen <= 1'b1;
                            end else begin
                                hmac_message      <= make_secure_message(ext_data[191:128],
                                                                          ext_counter,
                                                                          ext_data[255:192]);
                                hmac_message_len  <= 6'd28;
                                hmac_supplied_tag <= ext_data[127:0];
                                hmac_payload      <= ext_data[191:128];
                                hmac_counter      <= ext_counter;
                                hmac_pending      <= HMAC_SECURE;
                                hmac_start        <= 1'b1;
                                defer_response     = 1'b1;
                            end
                        end

                        SUB_KEY_CONFIRM: begin
                            if (ext_data_len != 8'd16) begin
                                result_now = RESULT_BAD_LENGTH;
                            end else if (!vault_active) begin
                                result_now = RESULT_NO_ENTRY;
                            end else begin
                                hmac_message      <= make_confirm_message(ext_data[255:128]);
                                hmac_message_len  <= 6'd24;
                                hmac_counter      <= ext_counter;
                                hmac_pending      <= HMAC_CONFIRM;
                                hmac_start        <= 1'b1;
                                defer_response    = 1'b1;
                            end
                        end

                        SUB_VAULT_PROVISION: begin
                            // HSM-4F: permanently close the SPI plaintext-key
                            // injection path. Keep the subcommand number only
                            // so old hosts fail closed instead of being parsed
                            // as an unknown or accidentally reused command.
                            result_now = RESULT_LOCKED;
                        end

                        SUB_VAULT_STATUS: begin
                            if (ext_data_len != 8'd1) begin
                                result_now = RESULT_BAD_LENGTH;
                            end else if (ext_data[255:248] != 8'd0) begin
                                result_now = RESULT_INVALID_SLOT;
                            end else begin
                                ext_len_now = 8'd32;
                                ext_resp_now[199:192] = 8'd0;
                                ext_resp_now[191:184] = (vault_state != SLOT_EMPTY) ? 8'h05 : 8'h00;
                                ext_resp_now[183:176] = vault_active ? 8'h21 : 8'h00;
                                ext_resp_now[175:168] = vault_active ? 8'd1 : 8'd0;
                                ext_resp_now[167:160] = 8'd0;
                                ext_resp_now[159:152] = vault_state;
                                ext_resp_now[151:136] = (vault_state != SLOT_EMPTY) ? vault_version : 16'd0;
                                ext_resp_now[135:120] = (vault_state != SLOT_EMPTY) ? usage_counter[0] : 16'd0;
                                // Public backend metadata only. CHIPID is an
                                // SDM-provided device identifier, never key
                                // material. Backend kind 1 means Agilex SDM
                                // Mailbox transport; ready=0 keeps HSM-4B
                                // explicitly below persistent-vault status.
                                ext_resp_now[119:112] = 8'd1;
                                ext_resp_now[111:104] = {7'd0, sdm_transport_ready};
                                ext_resp_now[103:96]  = sdm_transport_error;
                                ext_resp_now[95:32]   = sdm_chip_id;
                                // HSM-4B1A readiness metadata. These bytes
                                // prove only that the official crypto port is
                                // enabled and its local scratch RAM completed
                                // reset scrubbing; no SDM key command is sent.
                                ext_resp_now[31:24]   = {7'd0, sdm_crypto_enabled};
                                ext_resp_now[23:16]   = {7'd0, sdm_crypto_mem_ready};
                                ext_resp_now[15:8]    = sdm_crypto_mem_error;
                                ext_resp_now[7:0]     = 8'd14; // log2(16 KiB)
                            end
                        end

                        SUB_VAULT_DESTROY: begin
                            if (ext_data_len != 8'd1) begin
                                result_now = RESULT_BAD_LENGTH;
                            end else if (ext_data[255:248] != 8'd0) begin
                                result_now = RESULT_INVALID_SLOT;
                            end else if (ext_counter == 32'hFFFF_FFFF) begin
                                result_now = RESULT_COUNTER_EXHAUSTED;
                            end else if (vault_counter_valid &&
                                         ext_counter <= last_vault_counter) begin
                                result_now = RESULT_REPLAY_DETECTED;
                                replay_seen <= 1'b1;
                            end else if (!provision_enable) begin
                                result_now = RESULT_POLICY_DENIED;
                            end else if (vault_staged_valid) begin
                                result_now = RESULT_POLICY_DENIED;
                            end else if (vault_state == SLOT_EMPTY) begin
                                result_now = RESULT_NO_ENTRY;
                            end else begin
                                vault_hmac_key       <= 256'd0;
                                vault_active         <= 1'b0;
                                vault_state          <= SLOT_EMPTY;
                                vault_version        <= 16'd0;
                                vault_staged_key     <= 256'd0;
                                vault_staged_valid   <= 1'b0;
                                vault_staged_authenticated <= 1'b0;
                                vault_staged_puf_bound <= 1'b0;
                                vault_staged_prepare_counter <= 32'd0;
                                last_vault_counter   <= ext_counter;
                                vault_counter_valid  <= 1'b1;
                                usage_counter[0]     <= 16'd0;
                                challenge_active     <= 1'b0;
                                challenge_timer      <= 32'd0;
                                session_slot_active  <= 1'b0;
                                session_key_handle   <= 16'd0;
                                mlkem_sender_session_key <= 256'd0;
                                mlkem_receiver_session_key <= 256'd0;
                                last_seal_counter    <= 32'd0;
                                seal_counter_valid   <= 1'b0;
                                last_secure_counter  <= 32'd0;
                                secure_counter_valid <= 1'b0;
                                session_epoch        <= 64'd0;
                                zeroize_pulse        <= 1'b1;
                                ext_len_now = 8'd17;
                                ext_resp_now[199:192] = 8'd0;
                                ext_resp_now[191:184] = 8'd0;
                                ext_resp_now[183:176] = 8'd0;
                                ext_resp_now[175:168] = 8'd0;
                                ext_resp_now[167:160] = 8'd0;
                                ext_resp_now[159:152] = SLOT_EMPTY;
                                ext_resp_now[151:136] = 16'd0;
                                ext_resp_now[135:120] = 16'd0;
                            end
                        end

                        SUB_VAULT_PREPARE: begin
                            // HSM-4F: legacy two-phase prepare also carried a
                            // plaintext key over SPI. Authenticated subcommand
                            // 0x37 is now the only external staging entry.
                            result_now = RESULT_LOCKED;
                        end

                        SUB_VAULT_COMMIT: begin
                            if (ext_data_len != 8'd5) begin
                                result_now = RESULT_BAD_LENGTH;
                            end else if (ext_data[255:248] != 8'd0) begin
                                result_now = RESULT_INVALID_SLOT;
                            end else if (ext_counter == 32'hFFFF_FFFF) begin
                                result_now = RESULT_COUNTER_EXHAUSTED;
                            end else if (vault_counter_valid &&
                                         ext_counter <= last_vault_counter) begin
                                result_now = RESULT_REPLAY_DETECTED;
                                replay_seen <= 1'b1;
                            end else if (!provision_enable) begin
                                result_now = RESULT_POLICY_DENIED;
                            end else if (!vault_staged_valid) begin
                                result_now = RESULT_NO_ENTRY;
                            end else if (!vault_staged_authenticated) begin
                                // Defense in depth: even if future code creates
                                // staging through another path, compact COMMIT
                                // cannot publish unauthenticated key material.
                                result_now = RESULT_LOCKED;
                            end else if (!vault_staged_puf_bound) begin
                                result_now = RESULT_LOCKED;
                            end else if (ext_data[247:216] != vault_staged_prepare_counter ||
                                         vault_state != SLOT_EMPTY) begin
                                result_now = RESULT_POLICY_DENIED;
                            end else begin
                                vault_hmac_key       <= vault_staged_key;
                                vault_active         <= 1'b1;
                                vault_state          <= SLOT_ACTIVE;
                                vault_version        <= ext_counter[15:0];
                                vault_staged_key     <= 256'd0;
                                vault_staged_valid   <= 1'b0;
                                vault_staged_authenticated <= 1'b0;
                                vault_staged_puf_bound <= 1'b0;
                                vault_staged_prepare_counter <= 32'd0;
                                last_vault_counter   <= ext_counter;
                                vault_counter_valid  <= 1'b1;
                                usage_counter[0]     <= 16'd0;
                                ext_len_now = 8'd17;
                                ext_resp_now[199:192] = 8'd0;
                                ext_resp_now[191:184] = 8'h05;
                                ext_resp_now[183:176] = 8'h21;
                                ext_resp_now[175:168] = 8'd1;
                                ext_resp_now[167:160] = 8'd0;
                                ext_resp_now[159:152] = SLOT_ACTIVE;
                                ext_resp_now[151:136] = ext_counter[15:0];
                                ext_resp_now[135:120] = 16'd0;
                            end
                        end

                        SUB_VAULT_ABORT: begin
                            if (ext_data_len != 8'd5) begin
                                result_now = RESULT_BAD_LENGTH;
                            end else if (ext_data[255:248] != 8'd0) begin
                                result_now = RESULT_INVALID_SLOT;
                            end else if (ext_counter == 32'hFFFF_FFFF) begin
                                result_now = RESULT_COUNTER_EXHAUSTED;
                            end else if (vault_counter_valid &&
                                         ext_counter <= last_vault_counter) begin
                                result_now = RESULT_REPLAY_DETECTED;
                                replay_seen <= 1'b1;
                            end else if (!provision_enable) begin
                                result_now = RESULT_POLICY_DENIED;
                            end else if (!vault_staged_valid) begin
                                result_now = RESULT_NO_ENTRY;
                            end else if (ext_data[247:216] != vault_staged_prepare_counter) begin
                                result_now = RESULT_POLICY_DENIED;
                            end else begin
                                vault_staged_key     <= 256'd0;
                                vault_staged_valid   <= 1'b0;
                                vault_staged_authenticated <= 1'b0;
                                vault_staged_puf_bound <= 1'b0;
                                vault_staged_prepare_counter <= 32'd0;
                                last_vault_counter   <= ext_counter;
                                vault_counter_valid  <= 1'b1;
                                ext_len_now = 8'd14;
                                ext_resp_now[199:192] = 8'd0;
                                ext_resp_now[191:184] = vault_state;
                                ext_resp_now[183:176] = 8'd0;
                                ext_resp_now[175:144] = ext_data[247:216];
                            end
                        end

                        SUB_VAULT_REVOKE: begin
                            if (ext_data_len != 8'd1) begin
                                result_now = RESULT_BAD_LENGTH;
                            end else if (ext_data[255:248] != 8'd0) begin
                                result_now = RESULT_INVALID_SLOT;
                            end else if (ext_counter == 32'hFFFF_FFFF) begin
                                result_now = RESULT_COUNTER_EXHAUSTED;
                            end else if (vault_counter_valid &&
                                         ext_counter <= last_vault_counter) begin
                                result_now = RESULT_REPLAY_DETECTED;
                                replay_seen <= 1'b1;
                            end else if (!provision_enable) begin
                                result_now = RESULT_POLICY_DENIED;
                            end else if (!vault_active || vault_state != SLOT_ACTIVE) begin
                                result_now = RESULT_NO_ENTRY;
                            end else begin
                                vault_hmac_key       <= 256'd0;
                                vault_active         <= 1'b0;
                                vault_state          <= SLOT_REVOKED;
                                vault_staged_key     <= 256'd0;
                                vault_staged_valid   <= 1'b0;
                                vault_staged_authenticated <= 1'b0;
                                vault_staged_puf_bound <= 1'b0;
                                vault_staged_prepare_counter <= 32'd0;
                                last_vault_counter   <= ext_counter;
                                vault_counter_valid  <= 1'b1;
                                challenge_active     <= 1'b0;
                                challenge_timer      <= 32'd0;
                                session_slot_active  <= 1'b0;
                                session_key_handle   <= 16'd0;
                                mlkem_sender_session_key <= 256'd0;
                                mlkem_receiver_session_key <= 256'd0;
                                last_seal_counter    <= 32'd0;
                                seal_counter_valid   <= 1'b0;
                                last_secure_counter  <= 32'd0;
                                secure_counter_valid <= 1'b0;
                                session_epoch        <= 64'd0;
                                zeroize_pulse        <= 1'b1;
                                ext_len_now = 8'd17;
                                ext_resp_now[199:192] = 8'd0;
                                ext_resp_now[191:184] = 8'h05;
                                ext_resp_now[183:176] = 8'd0;
                                ext_resp_now[175:168] = 8'd0;
                                ext_resp_now[167:160] = 8'd0;
                                ext_resp_now[159:152] = SLOT_REVOKED;
                                ext_resp_now[151:136] = vault_version;
                                ext_resp_now[135:120] = usage_counter[0];
                            end
                        end

                        SUB_AUTH_PROVISION_PREPARE: begin
                            if (!ENABLE_STATIC_AUTH_PROVISION) begin
                                result_now = RESULT_POLICY_DENIED;
                            end else if (ext_data_len != 8'd32) begin
                                result_now = RESULT_BAD_LENGTH;
                            end else if (ext_counter == 32'hFFFF_FFFF) begin
                                result_now = RESULT_COUNTER_EXHAUSTED;
                            end else if (vault_counter_valid &&
                                         ext_counter <= last_vault_counter) begin
                                result_now = RESULT_REPLAY_DETECTED;
                                replay_seen <= 1'b1;
                            end else if (!provision_enable) begin
                                result_now = RESULT_POLICY_DENIED;
                            end else if (!sdm_transport_ready ||
                                         sdm_chip_id == 64'd0) begin
                                result_now = RESULT_POLICY_DENIED;
                            end else if (vault_state != SLOT_EMPTY ||
                                         vault_staged_valid ||
                                         prov_state != PROV_IDLE) begin
                                result_now = RESULT_POLICY_DENIED;
                            end else if (ext_data[255:224] != PROV_SIGNER_ID ||
                                         ext_data[223:216] != 8'd0 ||
                                         ext_data[215:208] != 8'h05 ||
                                         ext_data[207:200] != 8'h21 ||
                                         ext_data[199:192] != 8'h01 ||
                                         ext_data[191:128] == 64'd0) begin
                                result_now = RESULT_POLICY_DENIED;
                            end else begin
                                prov_request      <= ext_data[255:128];
                                prov_supplied_tag <= ext_data[127:0];
                                prov_counter      <= ext_counter;
                                prov_hmac_message <= make_provision_message(
                                    PROV_AUTH_DOMAIN, sdm_chip_id, ext_counter,
                                    ext_data[255:128]);
                                prov_hmac_start   <= 1'b1;
                                prov_state        <= PROV_AUTH_WAIT;
                                last_vault_counter  <= ext_counter;
                                vault_counter_valid <= 1'b1;
                                defer_response      = 1'b1;
                            end
                        end

                        default: result_now = RESULT_BAD_COMMAND;
                    endcase
                end

                if (!defer_response) begin
                    ext_resp_now[239:232] = result_now;
                    ext_response_data <= ext_resp_now;
                    ext_response_len  <= ext_len_now;
                    ext_done          <= 1'b1;

                    audit_cmd[audit_write_ptr]    <= CMD_HSM_EXT;
                    audit_slot[audit_write_ptr]   <= ext_subcmd;
                    audit_result[audit_write_ptr] <= result_now;
                    audit_usage[audit_write_ptr]  <=
                        ((ext_subcmd == SUB_VAULT_PROVISION) ||
                         (ext_subcmd == SUB_VAULT_STATUS) ||
                         (ext_subcmd == SUB_VAULT_DESTROY) ||
                         (ext_subcmd == SUB_VAULT_PREPARE) ||
                         (ext_subcmd == SUB_VAULT_COMMIT) ||
                         (ext_subcmd == SUB_VAULT_ABORT) ||
                         (ext_subcmd == SUB_VAULT_REVOKE) ||
                         (ext_subcmd == SUB_AUTH_PROVISION_PREPARE)) ?
                        usage_counter[0][7:0] : usage_counter[3][7:0];
                    audit_seq[audit_write_ptr]    <= event_counter;
                    audit_write_ptr <= audit_write_ptr + 3'd1;
                    if (audit_count != 4'd8)
                        audit_count <= audit_count + 4'd1;
                    event_counter <= event_counter + 16'd1;
                    last_result   <= result_now;
                end
            end
        end
    end
endmodule
