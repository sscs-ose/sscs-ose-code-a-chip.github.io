// B1: formal properties of the session service of hsm_shell, stated on its ports (SymbiYosys, smtbmc).
// The shell runs in the chip's configuration (internal ML-KEM K channel) with the HMAC outside (EXTERNAL_HMAC = 1):
// its busy/done/digest are free inputs, so every property holds for any HMAC timing and any digest.
// Inputs are free in every cycle, except: one reset at the start, one compact command in flight at a time (the
// SPI bridge waits for ext_done in ST_WAIT_HSM_EXT, also before a legacy command), and legacy and compact commands never in
// the same cycle.
//
//   P1  no bit of K reaches the host: two copies that differ only in K give identical SPI responses
//   P2  sealing: a sealed frame's counter exceeds the previous one of the binding (rev B) and
//       is exactly the previous one plus one, starting at 1 (rev C)
//   P3  receiving: an accepted frame carries the epoch of the current binding and a counter above the last accepted
//   P4  (rev C) after RECV_FAIL_LIMIT rejected tags, no frame is accepted until the next binding or zeroisation
//   P5  (rev C) a binding is refused as a replay only if an earlier successful command used that counter or a later one
//   P6  (rev C) a binding succeeds only with a nonce ready, returns that nonce as its epoch and consumes it
`default_nettype none
module hsm_session_props (
    input wire         clk,
    input wire         ext_cmd_valid_i, cmd_valid_i, session_valid,
    input wire [7:0]   cmd_id,
    input wire [7:0]   ext_subcmd, ext_flags, ext_data_len, ext_api_version,
    input wire         ext_header_valid, ext_mlkem_pass, ext_mlkem_key_valid,
    input wire [31:0]  ext_counter,
    input wire [255:0] ext_data,
    input wire [255:0] k_a, k_b,
    input wire         k_match,
    input wire         hmac_rsp_busy, hmac_rsp_done,
    input wire [255:0] hmac_rsp_digest,
    input wire         epoch_nonce_valid,
    input wire [63:0]  epoch_nonce
);
`ifdef REVC_FAIL_LIMIT
    localparam [7:0] FAIL_LIMIT = `REVC_FAIL_LIMIT;
`else
    localparam [7:0] FAIL_LIMIT = 8'd16;
`endif
    reg init = 1'b1;
    always @(posedge clk) init <= 1'b0;
    wire rst_n = !init;

    // one compact command in flight; legacy and compact commands exclusive
    reg busy_q = 1'b0;
    wire ext_done_a;
    always @(posedge clk) if (!rst_n) busy_q <= 1'b0; else if (ext_cmd_valid_i && !busy_q) busy_q <= 1'b1; else if (ext_done_a) busy_q <= 1'b0;
    wire ext_cmd_valid = ext_cmd_valid_i && !busy_q && rst_n;
    wire cmd_valid = cmd_valid_i && !ext_cmd_valid_i && !busy_q && rst_n;   // the bridge waits in ST_WAIT_HSM_EXT

    // copy b sees K' when k_match is low; the ML-KEM handoff keeps sender = receiver in both copies
    wire [255:0] kb = k_match ? k_a : k_b;

    wire [7:0]   len_a, len_b;
    wire [255:0] rsp_a, rsp_b;
    wire [63:0]  lrsp_a, lrsp_b;
    wire         ext_done_b, done_a, done_b;
    wire         nonce_consume_a, nonce_consume_b;

`define SHELL(sfx, KEY) \
    hsm_shell #(.ENABLE_MLKEM_K_CHANNEL(1'b1), .ENABLE_STATIC_AUTH_PROVISION(1'b0), .EXTERNAL_HMAC(1'b1)) u_``sfx ( \
        .clk(clk), .rst_n(rst_n), .session_valid(session_valid), .device_id(32'h48534B32), \
        .provision_enable(1'b0), .sdm_transport_ready(1'b0), .sdm_transport_error(8'd0), .sdm_chip_id(64'd0), \
        .sdm_crypto_enabled(1'b0), .sdm_crypto_mem_ready(1'b0), .sdm_crypto_mem_error(8'd0), \
        .cmd_valid(cmd_valid), .cmd_id(cmd_id), .cmd_arg(8'd0), .key_use_pulse(1'b0), \
        .puf_vault_load_pulse(1'b0), .puf_vault_stage_pulse(1'b0), .puf_vault_clear_pulse(1'b0), \
        .puf_vault_key(256'd0), .puf_vault_stage_authorized(), .done(done_``sfx), .response_data(lrsp_``sfx), \
        .ext_cmd_valid(ext_cmd_valid), .ext_header_valid(ext_header_valid), .ext_mlkem_pass(ext_mlkem_pass), \
        .ext_mlkem_key_valid(ext_mlkem_key_valid), .ext_mlkem_sender_key(KEY), .ext_mlkem_receiver_key(KEY), \
        .ext_api_version(ext_api_version), .ext_subcmd(ext_subcmd), .ext_flags(ext_flags), \
        .ext_counter(ext_counter), .ext_data_len(ext_data_len), .ext_data(ext_data), \
        .ext_done(ext_done_``sfx), .ext_response_len(len_``sfx), .ext_response_data(rsp_``sfx), \
        .session_grant_pulse(), .mlkem_bind_consume_pulse(), .zeroize_pulse(), .hmac_req_start(), \
        .hmac_req_scrub(), .hmac_req_key(), .hmac_req_message(), .hmac_req_message_len(), \
        .hmac_rsp_busy(hmac_rsp_busy), .hmac_rsp_done(hmac_rsp_done), .hmac_rsp_digest(hmac_rsp_digest) \
        `REVC_PORTS(sfx) )
`ifdef TRUSTEDGE_REVC
`define REVC_PORTS(sfx) , .epoch_nonce_valid(epoch_nonce_valid), .epoch_nonce(epoch_nonce), .epoch_nonce_consume(nonce_consume_``sfx)
`else
`define REVC_PORTS(sfx)
    assign nonce_consume_a = 1'b0; assign nonce_consume_b = 1'b0;
`endif
    `SHELL(a, k_a);
`ifdef P1_MITER
    `SHELL(b, kb);
    // P1: identical SPI-visible behaviour for any two keys
    always @(posedge clk) if (rst_n) begin
        assert (ext_done_a == ext_done_b);
        assert (len_a == len_b);
        assert (rsp_a == rsp_b);
        assert (done_a == done_b);
        assert (lrsp_a == lrsp_b);
    end
`endif

    // ---- observers of copy a ----
    wire [7:0]  r_sub = rsp_a[247:240], r_res = rsp_a[239:232];
    wire [31:0] r_ctr = rsp_a[231:200];
    reg  [63:0] req_epoch;            // the epoch field of the command in flight
    reg         in_bind, in_zero;
    always @(posedge clk) if (ext_cmd_valid) req_epoch <= ext_data[255:192];

    reg         bound = 1'b0;         // a binding succeeded since reset/zeroisation
    reg  [63:0] cur_epoch;
    reg         seal_any = 1'b0;  reg [31:0] seal_last;
    reg         recv_any = 1'b0;  reg [31:0] recv_last;
    reg  [7:0]  fails = 8'd0;
    reg         txn_any = 1'b0;   reg [31:0] txn_max;   // highest counter of a successful bind or attestation challenge
    wire ok_bind  = ext_done_a && r_sub == 8'h12 && r_res == 8'h00;
    wire zero     = cmd_valid && cmd_id == 8'h36;
    always @(posedge clk) begin
        if (!rst_n || zero) begin
            bound <= 1'b0; seal_any <= 1'b0; recv_any <= 1'b0; fails <= 8'd0;
        end else if (ok_bind) begin
            bound <= 1'b1; cur_epoch <= rsp_a[135:72]; seal_any <= 1'b0; recv_any <= 1'b0; fails <= 8'd0;
        end else if (ext_done_a && r_sub == 8'h13 && r_res == 8'h00) begin
            seal_any <= 1'b1; seal_last <= r_ctr;
        end else if (ext_done_a && r_sub == 8'h20 && r_res == 8'h00) begin
            recv_any <= 1'b1; recv_last <= r_ctr;
        end else if (ext_done_a && r_sub == 8'h20 && r_res == 8'h0A && req_epoch == cur_epoch) begin
            if (fails != 8'hFF) fails <= fails + 8'd1;
        end
        if (!rst_n) txn_any <= 1'b0;
        else if (ext_done_a && (r_sub == 8'h12 || r_sub == 8'h10) && r_res == 8'h00) begin
            txn_any <= 1'b1; txn_max <= (!txn_any || r_ctr > txn_max) ? r_ctr : txn_max;
        end
    end

    always @(posedge clk) if (rst_n && ext_done_a) begin
        // P2
        if (r_sub == 8'h13 && r_res == 8'h00) begin
            assert (bound);
            if (seal_any) assert (r_ctr > seal_last);
`ifdef TRUSTEDGE_REVC
            assert (r_ctr == (seal_any ? seal_last + 32'd1 : 32'd1));
`endif
        end
        // P3
        if (r_sub == 8'h20 && r_res == 8'h00) begin
            assert (bound && req_epoch == cur_epoch);
            if (recv_any) assert (r_ctr > recv_last);
`ifdef TRUSTEDGE_REVC
            // P4
            assert (fails < FAIL_LIMIT);
`endif
        end
`ifdef TRUSTEDGE_REVC
        // P5
        if (r_sub == 8'h12 && r_res == 8'h07) assert (txn_any && r_ctr <= txn_max);
`endif
    end
`ifdef TRUSTEDGE_REVC
    // P6
    reg        bind_req_nonce_ok; reg [63:0] bind_req_nonce;
    always @(posedge clk) if (ext_cmd_valid) begin bind_req_nonce_ok <= epoch_nonce_valid; bind_req_nonce <= epoch_nonce; end
    always @(posedge clk) if (rst_n && ok_bind) begin
        assert (bind_req_nonce_ok && rsp_a[135:72] == bind_req_nonce);
    end
    reg ok_bind_q = 1'b0;
    always @(posedge clk) ok_bind_q <= ok_bind;
    // the consume pulse comes with the response (both registered on the command's cycle)
    always @(posedge clk) if (rst_n) assert (nonce_consume_a == ok_bind);
`endif

    // reachability, so that the properties are not vacuous
    always @(posedge clk) if (rst_n) begin
        cover (ok_bind);
        cover (ext_done_a && r_sub == 8'h20 && r_res == 8'h00);
        cover (ext_done_a && r_sub == 8'h13 && r_res == 8'h00 && seal_any);
`ifdef TRUSTEDGE_REVC
        cover (ext_done_a && r_sub == 8'h20 && r_res == 8'h08);
`endif
    end
endmodule
