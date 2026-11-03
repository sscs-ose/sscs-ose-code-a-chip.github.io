// Session logic of hsm_shell in the chip's configuration (internal ML-KEM K channel, internal HMAC), before and
// after rev C.  Built without TRUSTEDGE_REVC it records the rev B behaviour that rev C removes; built with it, the
// rev C behaviour.  Every sealed frame is printed (SEAL_LOG) so that scripts/check_seal_log.py recomputes each tag
// with Python's hmac module, independently of the RTL's SHA-256.
//   S1  binding: epoch = {"SF21", counter} (rev B) or a fresh nonce (rev C)
//   S2  sealing: counter 3 after 1 (a gap) is accepted (rev B) or refused with 0x0C (rev C)
//   S3  receive: a sealed frame is accepted once, its replay refused
//   S4  16 wrong tags: rev B answers 0x0A forever; rev C locks the receive path (0x08) until the next binding
//   S5  a refused binding consumes its counter (rev B) or not (rev C)
//   S6  after a reset the same K and counter give the same epoch, so a frame sealed before the reset is accepted
//       again (rev B); rev C gives a new epoch and refuses the old frame
//   S7  zeroisation clears the lock (rev C)
`timescale 1ns/1ps
module tb_revc_session;
    reg clk = 1'b0, rst_n = 1'b0;
    always #5 clk = ~clk;

    reg          ext_cmd_valid = 1'b0;
    reg  [7:0]   ext_subcmd = 8'd0;
    reg  [31:0]  ext_counter = 32'd0;
    reg  [7:0]   ext_data_len = 8'd0;
    reg  [255:0] ext_data = 256'd0;
    reg          cmd_valid = 1'b0;
    reg  [7:0]   cmd_id = 8'd0;
    reg  [255:0] k_send, k_recv;
    wire         ext_done, done;
    wire [7:0]   ext_response_len;
    wire [255:0] ext_response_data;
    wire [63:0]  response_data;
    wire         puf_vault_stage_authorized, session_grant_pulse, mlkem_bind_consume_pulse, zeroize_pulse;
    wire         hmac_req_start, hmac_req_scrub;
    wire [255:0] hmac_req_key, hmac_req_message;
    wire [5:0]   hmac_req_message_len;
`ifdef TRUSTEDGE_REVC
    reg          nonce_valid = 1'b1;
    reg  [63:0]  nonce;
    wire         nonce_consume;
    always @(posedge clk) if (nonce_consume) nonce <= {$urandom, $urandom};
`endif

    hsm_shell #(.ENABLE_MLKEM_K_CHANNEL(1'b1), .ENABLE_STATIC_AUTH_PROVISION(1'b0), .EXTERNAL_HMAC(1'b0)) dut (
        .clk(clk), .rst_n(rst_n), .session_valid(1'b1), .device_id(32'h48534B32),
        .provision_enable(1'b0), .sdm_transport_ready(1'b0), .sdm_transport_error(8'd0), .sdm_chip_id(64'd0),
        .sdm_crypto_enabled(1'b0), .sdm_crypto_mem_ready(1'b0), .sdm_crypto_mem_error(8'd0),
        .cmd_valid(cmd_valid), .cmd_id(cmd_id), .cmd_arg(8'd0), .key_use_pulse(1'b0),
        .puf_vault_load_pulse(1'b0), .puf_vault_stage_pulse(1'b0), .puf_vault_clear_pulse(1'b0),
        .puf_vault_key(256'd0), .puf_vault_stage_authorized(puf_vault_stage_authorized),
        .done(done), .response_data(response_data),
        .ext_cmd_valid(ext_cmd_valid), .ext_header_valid(1'b1), .ext_mlkem_pass(1'b1),
        .ext_mlkem_key_valid(1'b1), .ext_mlkem_sender_key(k_send), .ext_mlkem_receiver_key(k_recv),
        .ext_api_version(8'h01), .ext_subcmd(ext_subcmd), .ext_flags(8'd0), .ext_counter(ext_counter),
        .ext_data_len(ext_data_len), .ext_data(ext_data),
        .ext_done(ext_done), .ext_response_len(ext_response_len), .ext_response_data(ext_response_data),
        .session_grant_pulse(session_grant_pulse), .mlkem_bind_consume_pulse(mlkem_bind_consume_pulse),
        .zeroize_pulse(zeroize_pulse), .hmac_req_start(hmac_req_start), .hmac_req_scrub(hmac_req_scrub),
        .hmac_req_key(hmac_req_key), .hmac_req_message(hmac_req_message),
        .hmac_req_message_len(hmac_req_message_len),
        .hmac_rsp_busy(1'b0), .hmac_rsp_done(1'b0), .hmac_rsp_digest(256'd0)
`ifdef TRUSTEDGE_REVC
        , .epoch_nonce_valid(nonce_valid), .epoch_nonce(nonce), .epoch_nonce_consume(nonce_consume)
`endif
    );

    integer errors = 0, checks = 0;
    reg [7:0]   res;
    reg [255:0] rsp;
    reg [63:0]  epoch1, epoch2, epoch_r;
    reg [127:0] tag1, tag;
    integer n;

    task ext(input [7:0] sub, input [31:0] ctr, input [7:0] len, input [255:0] data);
        begin
            @(negedge clk);
            ext_subcmd = sub; ext_counter = ctr; ext_data_len = len; ext_data = data; ext_cmd_valid = 1'b1;
            @(negedge clk); ext_cmd_valid = 1'b0;
            while (!ext_done) @(posedge clk);
            #1; rsp = ext_response_data; res = rsp[239:232];
        end
    endtask
    task check(input ok, input [8*72-1:0] name);
        begin
            checks = checks + 1;
            if (ok) $display("  PASS %0s", name);
            else begin errors = errors + 1; $display("  FAIL %0s result=%02h rsp=%064h", name, res, rsp); end
        end
    endtask
    task bind_k(input [31:0] ctr);
        ext(8'h12, ctr, 8'd2, {8'd2, 8'd3, 240'd0});
    endtask
    task seal(input [31:0] ctr, input [63:0] payload);
        begin
            ext(8'h13, ctr, 8'd8, {payload, 192'd0});
            if (res == 8'h00)
                $display("SEAL_LOG K=%064h E=%016h C=%08h P=%016h T=%032h", k_send, dut.session_epoch, ctr, payload,
                         rsp[135:8]);
        end
    endtask
    task secure(input [31:0] ctr, input [63:0] epoch, input [63:0] payload, input [127:0] t);
        ext(8'h20, ctr, 8'd32, {epoch, payload, t});
    endtask
    task zeroize;
        begin
            @(negedge clk); cmd_id = 8'h36; cmd_valid = 1'b1; @(negedge clk); cmd_valid = 1'b0;
            while (!done) @(posedge clk);
        end
    endtask
    task reset;
        begin
            @(negedge clk); rst_n = 1'b0; repeat (3) @(negedge clk); rst_n = 1'b1; repeat (2) @(negedge clk);
        end
    endtask

    initial begin
`ifdef TRUSTEDGE_REVC
        nonce = {$urandom, $urandom};
        $display("tb_revc_session: rev C build");
`else
        $display("tb_revc_session: rev B build");
`endif
        k_send = {$urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom};
        k_recv = k_send;
        reset;

        // S1
        bind_k(32'd10); epoch1 = rsp[135:72];
`ifdef TRUSTEDGE_REVC
        check(res == 8'h00 && epoch1 != {32'h53463231, 32'd10} && epoch1 == dut.session_epoch,
              "S1 bind: epoch is the fresh nonce");
`else
        check(res == 8'h00 && epoch1 == {32'h53463231, 32'd10}, "S1 bind: epoch = SF21 || counter");
`endif
        // S2
        seal(32'd1, 64'h0123456789ABCDEF); tag1 = rsp[135:8];
        check(res == 8'h00, "S2 seal counter 1");
        seal(32'd3, 64'h1111111111111111);
`ifdef TRUSTEDGE_REVC
        check(res == 8'h0C, "S2 seal counter 3 after 1 refused (gap)");
        seal(32'd2, 64'h2222222222222222);
        check(res == 8'h00, "S2 seal counter 2 accepted");
`else
        check(res == 8'h00, "S2 seal counter 3 after 1 accepted (gap)");
`endif
        // S3
        secure(32'd1, epoch1, 64'h0123456789ABCDEF, tag1);
        check(res == 8'h00 && rsp[199:136] == 64'h0123456789ABCDEF, "S3 sealed frame accepted");
`ifdef TRUSTEDGE_REVC
        check(ext_response_len == 8'd20 && rsp[135:120] == 16'd1 && rsp[119:104] == 16'd0 && rsp[103:96] == 8'd0,
              "S3 receive counts: 1 accepted, 0 rejected");
`endif
        secure(32'd1, epoch1, 64'h0123456789ABCDEF, tag1);
        check(res == 8'h07, "S3 replay refused");
        // S4
        for (n = 0; n < 16; n = n + 1) begin
            secure(32'd2 + n, epoch1, 64'h0123456789ABCDEF, tag1 ^ (128'd1 << n));
            if (res != 8'h0A) begin errors = errors + 1; $display("  FAIL S4 wrong tag %0d result=%02h", n, res); end
        end
`ifdef TRUSTEDGE_REVC
        check(rsp[119:104] == 16'd16 && rsp[103:96] == 8'd1, "S4 16th rejected tag sets the lock");
        secure(32'd40, epoch1, 64'h0123456789ABCDEF, tag1);
        check(res == 8'h08, "S4 locked: no further tag is checked");
`else
        secure(32'd40, epoch1, 64'h0123456789ABCDEF, tag1 ^ 128'd1);
        check(res == 8'h0A, "S4 no lock: a 17th guess is still checked");
`endif
        // S5
        k_recv = ~k_send;
        bind_k(32'd20);
        check(res == 8'h09, "S5 binding with mismatched K refused");
        k_recv = k_send;
        bind_k(32'd20);
`ifdef TRUSTEDGE_REVC
        check(res == 8'h00, "S5 the refused binding left counter 20 unused");
        epoch2 = rsp[135:72];
        check(epoch2 != epoch1, "S5 new binding, new epoch");
        secure(32'd41, epoch2, 64'h0123456789ABCDEF, tag1);
        check(res == 8'h0A, "S5 new binding clears the lock");
`else
        check(res == 8'h07, "S5 the refused binding consumed counter 20");
`endif
        // S6
        reset;
        bind_k(32'd10); epoch_r = rsp[135:72];
        secure(32'd1, epoch1, 64'h0123456789ABCDEF, tag1);
`ifdef TRUSTEDGE_REVC
        check(epoch_r != epoch1 && res == 8'h0A, "S6 after reset: new epoch, pre-reset frame refused");
`else
        check(epoch_r == epoch1 && res == 8'h00, "S6 after reset: same epoch, pre-reset frame accepted again");
`endif
        // S7
`ifdef TRUSTEDGE_REVC
        for (n = 0; n < 16; n = n + 1) secure(32'd2 + n, epoch_r, 64'd0, 128'd0);
        secure(32'd30, epoch_r, 64'd0, 128'd0);
        check(res == 8'h08, "S7 locked again");
        zeroize;
        bind_k(32'd11);
        seal(32'd1, 64'hFEDCBA9876543210); tag = rsp[135:8];
        secure(32'd1, dut.session_epoch, 64'hFEDCBA9876543210, tag);
        check(res == 8'h00, "S7 zeroise and rebind: receive path open");
`endif
        $display("TB_REVC_SESSION_RESULT: %0s (%0d checks, %0d errors)", errors == 0 ? "ALL PASS" : "FAIL", checks, errors);
        $finish;
    end
    initial begin #50_000_000; $display("TB_REVC_SESSION_RESULT: TIMEOUT"); $finish; end
endmodule
