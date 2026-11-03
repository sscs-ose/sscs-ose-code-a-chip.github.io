// ============================================================================
// spi_command_bridge.v  -  Decode frame SPI -> PUF / OTA + phan hoi enroll/verify
// ============================================================================
module spi_command_bridge #(
    parameter integer MAX_PAYLOAD = 64,
    parameter ENABLE_LEGACY_MLKEM_SELFTESTS = 1'b1,
    parameter ENABLE_INTERNAL_ENTROPY = 1'b0,
    parameter ENABLE_C3_TRANSPORT = 1'b0,
    parameter ENABLE_OTA_POLICY_DEMO = 1'b1
) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        frame_valid,
    input  wire [7:0]  frame_cmd,
    input  wire [15:0] frame_pl_len,
    input  wire [7:0]  frame_pl [0:MAX_PAYLOAD-1],
    output reg         cmd_enroll,
    output reg         cmd_verify,
    output reg  [7:0]  challenge,
    output reg  [31:0] nonce,
    output reg         ota_begin,
    output reg         ota_commit,
    output reg  [31:0] image_hash,
    output reg  [31:0] expected_hash,
    output reg         ota_sig_valid_override_en,
    output reg         ota_sig_valid_override,
    output reg         kyber_start,
    output reg         mlkem512_start,
    output reg         mlkem512_kpke_start,
    output reg         mlkem512_kpke_runtime_seed_valid,
    output reg         mlkem512_kpke_invalidate,
    output reg [255:0] mlkem512_kpke_seed_d,
    output reg [255:0] mlkem512_kpke_seed_z,
    output reg [7:0]   mlkem512_kpke_seed_k,
    output reg         mlkem512_encaps_start,
    output reg         mlkem512_encaps_runtime_input_valid,
    output reg [255:0] mlkem512_encaps_message,
    output reg [255:0] mlkem512_encaps_coins,
    output reg         mlkem512_encaps_full_start,
    output reg [255:0] mlkem512_encaps_full_message,
    output reg         mlkem512_decaps_start,
    input  wire        entropy_ready,
    input  wire        entropy_unhealthy,
    input  wire [7:0]  entropy_health_code,
    input  wire [31:0] entropy_raw_samples,
    input  wire [15:0] entropy_word_count,
    output reg         c2_run_start,
    input  wire        c2_run_done,
    input  wire        c2_run_pass,
    input  wire [7:0]  c2_run_status,
    input  wire [15:0] c2_reseed_count,
    input  wire [15:0] c2_generate_count,
    input  wire        c2_fresh,
    input  wire        c2_decaps_verified,
    input  wire [15:0] c2_run_cycles,
    output reg         c3_cmd_valid,
    output reg [3:0]   c3_cmd,
    output reg [4:0]   c3_chunk_index,
    input  wire        c3_done,
    input  wire        c3_pass,
    input  wire [7:0]  c3_status,
    input  wire [255:0] c3_response_data,
    input  wire [31:0] c3_digest_a,
    input  wire [31:0] c3_digest_b,
    input  wire [15:0] c3_cycles,
    input  wire        kyber_done,
    input  wire        kyber_pass,
    input  wire [31:0] kyber_digest,
    input  wire [15:0] kyber_cycles,
    input  wire        mlkem512_done,
    input  wire        mlkem512_pass,
    input  wire [7:0]  mlkem512_status,
    input  wire [31:0] mlkem512_partial_digest,
    input  wire [31:0] mlkem512_polyvec_digest,
    input  wire [15:0] mlkem512_cycles,
    input  wire        mlkem512_kpke_done,
    input  wire        mlkem512_kpke_pass,
    input  wire [7:0]  mlkem512_kpke_status,
    input  wire [31:0] mlkem512_kpke_digest_a,
    input  wire [31:0] mlkem512_kpke_digest_b,
    input  wire [15:0] mlkem512_kpke_cycles,
    input  wire        mlkem512_encaps_done,
    input  wire        mlkem512_encaps_pass,
    input  wire [7:0]  mlkem512_encaps_status,
    input  wire [31:0] mlkem512_encaps_digest_a,
    input  wire [31:0] mlkem512_encaps_digest_b,
    input  wire [15:0] mlkem512_encaps_cycles,
    input  wire        mlkem512_decaps_done,
    input  wire        mlkem512_decaps_pass,
    input  wire [7:0]  mlkem512_decaps_status,
    input  wire [31:0] mlkem512_decaps_digest_a,
    input  wire [31:0] mlkem512_decaps_digest_b,
    input  wire [15:0] mlkem512_decaps_cycles,
    output reg         hsm_cmd_valid,
    output reg  [7:0]  hsm_cmd_id,
    output reg  [7:0]  hsm_cmd_arg,
    input  wire        hsm_done,
    input  wire [63:0] hsm_response_data,
    output reg         hsm_ext_cmd_valid,
    output reg         hsm_ext_header_valid,
    output reg  [7:0]  hsm_ext_api_version,
    output reg  [7:0]  hsm_ext_subcmd,
    output reg  [7:0]  hsm_ext_flags,
    output reg  [31:0] hsm_ext_counter,
    output reg  [7:0]  hsm_ext_data_len,
    output reg  [255:0] hsm_ext_data,
    input  wire        hsm_ext_done,
    input  wire [7:0]  hsm_ext_response_len,
    input  wire [255:0] hsm_ext_response_data,
    input  wire        enroll_done,
    input  wire        verify_done,
    input  wire        verify_ok,
    input  wire [31:0] device_id,
    input  wire        cs_active,
    output reg         ext_tx_load,
    output reg  [7:0]  ext_tx_len,
    output reg  [7:0]  ext_tx_buf [0:39]
);
    // Register variable-length HSM extension responses before formatting the
    // outbound frame.  Besides making the service/transport boundary explicit,
    // this prevents the response-source selector, length clamp, CRC chain, and
    // transmit-buffer write from becoming one 50-MHz combinational path.
    reg  [7:0]   hsm_ext_response_len_q;
    reg  [255:0] hsm_ext_response_data_q;
    reg  [7:0]   hsm_ext_safe_len_q;
    reg  [5:0]   hsm_ext_build_index;
    localparam [7:0] SOF              = 8'hA5;
    localparam [7:0] CMD_PUF_ENROLL   = 8'h01;
    localparam [7:0] CMD_PUF_VERIFY   = 8'h03;
    localparam [7:0] CMD_KYBER_NTT_REQ= 8'h10;
    localparam [7:0] CMD_KYBER_NTT_RESP=8'h11;
    localparam [7:0] CMD_MLKEM512_PARTIAL_REQ= 8'h12;
    localparam [7:0] CMD_MLKEM512_PARTIAL_RESP=8'h13;
    localparam [7:0] CMD_MLKEM512_KPKE_REQ= 8'h14;
    localparam [7:0] CMD_MLKEM512_KPKE_RESP=8'h15;
    localparam [7:0] CMD_MLKEM512_ENCAPS_REQ= 8'h16;
    localparam [7:0] CMD_MLKEM512_ENCAPS_RESP=8'h17;
    localparam [7:0] CMD_MLKEM512_DECAPS_REQ= 8'h18;
    localparam [7:0] CMD_MLKEM512_DECAPS_RESP=8'h19;
    localparam [7:0] CMD_OTA_BEGIN    = 8'h20;
    localparam [7:0] CMD_OTA_COMMIT   = 8'h22;
    localparam [7:0] CMD_HSM_GET_INFO = 8'h30;
    localparam [7:0] CMD_HSM_GET_STATUS = 8'h32;
    localparam [7:0] CMD_HSM_KEY_STATUS = 8'h34;
    localparam [7:0] CMD_HSM_ZEROIZE_SESSION = 8'h36;
    localparam [7:0] CMD_HSM_AUDIT_READ = 8'h38;
    localparam [7:0] CMD_HSM_EXT_REQ = 8'h3A;
    localparam [7:0] CMD_HSM_EXT_RESP = 8'h3B;
    localparam [7:0] SUB_MLKEM_SESSION_BIND = 8'h12;

    function [15:0] crc16_byte;
        input [15:0] c;
        input [7:0]  d;
        integer i;
        reg [15:0] x;
        begin
            x = c ^ {d, 8'h00};
            for (i = 0; i < 8; i = i + 1) begin
                if (x[15])
                    x = {x[14:0], 1'b0} ^ 16'h1021;
                else
                    x = {x[14:0], 1'b0};
            end
            crc16_byte = x;
        end
    endfunction

    reg [15:0] crc_acc;
    integer    bi;

    task build_enroll_resp;
        input [31:0] id;
        begin
            ext_tx_buf[0]  = SOF;
            ext_tx_buf[1]  = 8'h02;
            ext_tx_buf[2]  = 8'd0;
            ext_tx_buf[3]  = 8'd16;
            ext_tx_buf[4]  = id[31:24];
            ext_tx_buf[5]  = id[23:16];
            ext_tx_buf[6]  = id[15:8];
            ext_tx_buf[7]  = id[7:0];
            for (bi = 8; bi < 20; bi = bi + 1)
                ext_tx_buf[bi] = 8'd0;
            crc_acc = 16'hFFFF;
            crc_acc = crc16_byte(crc_acc, ext_tx_buf[1]);
            crc_acc = crc16_byte(crc_acc, ext_tx_buf[2]);
            crc_acc = crc16_byte(crc_acc, ext_tx_buf[3]);
            for (bi = 4; bi < 20; bi = bi + 1)
                crc_acc = crc16_byte(crc_acc, ext_tx_buf[bi]);
            ext_tx_buf[20] = crc_acc[15:8];
            ext_tx_buf[21] = crc_acc[7:0];
            ext_tx_len     = 8'd22;
        end
    endtask

    task build_verify_resp;
        input ok;
        begin
            ext_tx_buf[0]  = SOF;
            ext_tx_buf[1]  = 8'h04;
            ext_tx_buf[2]  = 8'd0;
            ext_tx_buf[3]  = 8'd1;
            ext_tx_buf[4]  = ok ? 8'd1 : 8'd0;
            crc_acc = 16'hFFFF;
            crc_acc = crc16_byte(crc_acc, ext_tx_buf[1]);
            crc_acc = crc16_byte(crc_acc, ext_tx_buf[2]);
            crc_acc = crc16_byte(crc_acc, ext_tx_buf[3]);
            crc_acc = crc16_byte(crc_acc, ext_tx_buf[4]);
            ext_tx_buf[5]  = crc_acc[15:8];
            ext_tx_buf[6]  = crc_acc[7:0];
            ext_tx_len     = 8'd7;
        end
    endtask

    task build_kyber_resp;
        input ok;
        input [31:0] dig;
        input [15:0] cyc;
        begin
            ext_tx_buf[0]  = SOF;
            ext_tx_buf[1]  = CMD_KYBER_NTT_RESP;
            ext_tx_buf[2]  = 8'd0;
            ext_tx_buf[3]  = 8'd7;
            ext_tx_buf[4]  = ok ? 8'd1 : 8'd0;
            ext_tx_buf[5]  = dig[31:24];
            ext_tx_buf[6]  = dig[23:16];
            ext_tx_buf[7]  = dig[15:8];
            ext_tx_buf[8]  = dig[7:0];
            ext_tx_buf[9]  = cyc[15:8];
            ext_tx_buf[10] = cyc[7:0];
            crc_acc = 16'hFFFF;
            crc_acc = crc16_byte(crc_acc, ext_tx_buf[1]);
            crc_acc = crc16_byte(crc_acc, ext_tx_buf[2]);
            crc_acc = crc16_byte(crc_acc, ext_tx_buf[3]);
            for (bi = 4; bi < 11; bi = bi + 1)
                crc_acc = crc16_byte(crc_acc, ext_tx_buf[bi]);
            ext_tx_buf[11] = crc_acc[15:8];
            ext_tx_buf[12] = crc_acc[7:0];
            for (bi = 13; bi < 22; bi = bi + 1)
                ext_tx_buf[bi] = 8'd0;
            ext_tx_len     = 8'd13;
        end
    endtask

    task build_mlkem512_resp;
        input ok;
        input [7:0] st;
        input [31:0] pdig;
        input [31:0] vdig;
        input [15:0] cyc;
        begin
            ext_tx_buf[0]  = SOF;
            ext_tx_buf[1]  = CMD_MLKEM512_PARTIAL_RESP;
            ext_tx_buf[2]  = 8'd0;
            ext_tx_buf[3]  = 8'd12;
            ext_tx_buf[4]  = ok ? 8'd1 : 8'd0;
            ext_tx_buf[5]  = st;
            ext_tx_buf[6]  = pdig[31:24];
            ext_tx_buf[7]  = pdig[23:16];
            ext_tx_buf[8]  = pdig[15:8];
            ext_tx_buf[9]  = pdig[7:0];
            ext_tx_buf[10] = vdig[31:24];
            ext_tx_buf[11] = vdig[23:16];
            ext_tx_buf[12] = vdig[15:8];
            ext_tx_buf[13] = vdig[7:0];
            ext_tx_buf[14] = cyc[15:8];
            ext_tx_buf[15] = cyc[7:0];
            crc_acc = 16'hFFFF;
            for (bi = 1; bi < 16; bi = bi + 1)
                crc_acc = crc16_byte(crc_acc, ext_tx_buf[bi]);
            ext_tx_buf[16] = crc_acc[15:8];
            ext_tx_buf[17] = crc_acc[7:0];
            for (bi = 18; bi < 22; bi = bi + 1)
                ext_tx_buf[bi] = 8'd0;
            ext_tx_len     = 8'd18;
        end
    endtask

    task build_mlkem512_stage_resp;
        input [7:0] resp_cmd;
        input ok;
        input [7:0] st;
        input [31:0] dig_a;
        input [31:0] dig_b;
        input [15:0] cyc;
        begin
            ext_tx_buf[0]  = SOF;
            ext_tx_buf[1]  = resp_cmd;
            ext_tx_buf[2]  = 8'd0;
            ext_tx_buf[3]  = 8'd12;
            ext_tx_buf[4]  = ok ? 8'd1 : 8'd0;
            ext_tx_buf[5]  = st;
            ext_tx_buf[6]  = dig_a[31:24];
            ext_tx_buf[7]  = dig_a[23:16];
            ext_tx_buf[8]  = dig_a[15:8];
            ext_tx_buf[9]  = dig_a[7:0];
            ext_tx_buf[10] = dig_b[31:24];
            ext_tx_buf[11] = dig_b[23:16];
            ext_tx_buf[12] = dig_b[15:8];
            ext_tx_buf[13] = dig_b[7:0];
            ext_tx_buf[14] = cyc[15:8];
            ext_tx_buf[15] = cyc[7:0];
            crc_acc = 16'hFFFF;
            for (bi = 1; bi < 16; bi = bi + 1)
                crc_acc = crc16_byte(crc_acc, ext_tx_buf[bi]);
            ext_tx_buf[16] = crc_acc[15:8];
            ext_tx_buf[17] = crc_acc[7:0];
            for (bi = 18; bi < 22; bi = bi + 1)
                ext_tx_buf[bi] = 8'd0;
            ext_tx_len     = 8'd18;
        end
    endtask

    // The largest C3 response carries one 32-byte public chunk plus status
    // and index.  34-byte payload + 4-byte header + CRC fits ext_tx_buf[0:39]
    // exactly and keeps the existing primary 0x14/0x15 opcode pair.
    task build_c3_chunk_resp;
        input ok;
        input [4:0] chunk_index;
        input [255:0] data;
        begin
            ext_tx_buf[0] = SOF;
            ext_tx_buf[1] = CMD_MLKEM512_KPKE_RESP;
            ext_tx_buf[2] = 8'd0;
            ext_tx_buf[3] = 8'd34;
            ext_tx_buf[4] = ok ? 8'd1 : 8'd0;
            ext_tx_buf[5] = {3'd0, chunk_index};
            for (bi = 0; bi < 32; bi = bi + 1)
                ext_tx_buf[6 + bi] = data[bi*8 +: 8];
            crc_acc = 16'hFFFF;
            for (bi = 1; bi < 38; bi = bi + 1)
                crc_acc = crc16_byte(crc_acc, ext_tx_buf[bi]);
            ext_tx_buf[38] = crc_acc[15:8];
            ext_tx_buf[39] = crc_acc[7:0];
            ext_tx_len = 8'd40;
        end
    endtask

    task build_hsm_resp;
        input [7:0] resp_cmd;
        input [63:0] data;
        begin
            ext_tx_buf[0]  = SOF;
            ext_tx_buf[1]  = resp_cmd;
            ext_tx_buf[2]  = 8'd0;
            ext_tx_buf[3]  = 8'd8;
            for (bi = 0; bi < 8; bi = bi + 1)
                ext_tx_buf[4 + bi] = data[63-bi*8 -: 8];
            crc_acc = 16'hFFFF;
            for (bi = 1; bi < 12; bi = bi + 1)
                crc_acc = crc16_byte(crc_acc, ext_tx_buf[bi]);
            ext_tx_buf[12] = crc_acc[15:8];
            ext_tx_buf[13] = crc_acc[7:0];
            for (bi = 14; bi < 22; bi = bi + 1)
                ext_tx_buf[bi] = 8'd0;
            ext_tx_len = 8'd14;
        end
    endtask

    task launch_hsm_ext;
        begin
            hsm_ext_header_valid <= (frame_pl_len >= 16'd7);
            hsm_ext_api_version <= (frame_pl_len >= 16'd1) ? frame_pl[0] : 8'd0;
            hsm_ext_subcmd       <= (frame_pl_len >= 16'd2) ? frame_pl[1] : 8'd0;
            hsm_ext_flags        <= (frame_pl_len >= 16'd3) ? frame_pl[2] : 8'd0;
            hsm_ext_counter      <= (frame_pl_len >= 16'd7) ?
                                    {frame_pl[3], frame_pl[4], frame_pl[5], frame_pl[6]} :
                                    32'd0;
            hsm_ext_data_len     <= (frame_pl_len >= 16'd7) ?
                                    frame_pl_len[7:0] - 8'd7 : 8'd0;
            for (bi = 0; bi < 32; bi = bi + 1)
                hsm_ext_data[255-bi*8 -: 8] <=
                    (frame_pl_len > 16'd7 + bi) ? frame_pl[7 + bi] : 8'd0;
            hsm_ext_cmd_valid <= 1'b1;
        end
    endtask

    localparam [3:0] ST_IDLE=0, ST_WAIT_ENROLL=1, ST_WAIT_VERIFY=2,
                     ST_WAIT_KYBER=3, ST_WAIT_MLKEM512=4,
                     ST_WAIT_MLKEM512_KPKE=5,
                     ST_WAIT_MLKEM512_ENCAPS=6,
                     ST_WAIT_MLKEM512_DECAPS=7,
                     ST_WAIT_HSM=8,
                     ST_WAIT_HSM_EXT=9,
                     ST_WAIT_C2=10,
                     ST_WAIT_C3=11,
                     ST_BUILD_HSM_EXT=12,
                     ST_BUILD_HSM_EXT_DATA=13,
                     ST_BUILD_HSM_EXT_CRC=14,
                     ST_BUILD_HSM_EXT_DONE=15;
    reg [3:0] bridge_st;
    reg [7:0] hsm_resp_cmd;
    reg [3:0] c3_pending_cmd;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            cmd_enroll   <= 1'b0;
            cmd_verify   <= 1'b0;
            challenge    <= 8'h42;
            nonce        <= 32'd0;
            ota_begin    <= 1'b0;
            ota_commit   <= 1'b0;
            image_hash   <= 32'd0;
            expected_hash<= 32'd0;
            ota_sig_valid_override_en <= 1'b0;
            ota_sig_valid_override    <= 1'b1;
            kyber_start <= 1'b0;
            mlkem512_start <= 1'b0;
            mlkem512_kpke_start <= 1'b0;
            mlkem512_kpke_runtime_seed_valid <= 1'b0;
            mlkem512_kpke_invalidate <= 1'b0;
            mlkem512_kpke_seed_d <= 256'd0;
            mlkem512_kpke_seed_z <= 256'd0;
            mlkem512_kpke_seed_k <= 8'd0;
            mlkem512_encaps_start <= 1'b0;
            mlkem512_encaps_runtime_input_valid <= 1'b0;
            mlkem512_encaps_message <= 256'd0;
            mlkem512_encaps_coins <= 256'd0;
            mlkem512_encaps_full_start <= 1'b0;
            mlkem512_encaps_full_message <= 256'd0;
            mlkem512_decaps_start <= 1'b0;
            c2_run_start <= 1'b0;
            c3_cmd_valid <= 1'b0;
            c3_cmd <= 4'd0;
            c3_chunk_index <= 5'd0;
            c3_pending_cmd <= 4'd0;
            hsm_cmd_valid <= 1'b0;
            hsm_cmd_id    <= 8'd0;
            hsm_cmd_arg   <= 8'd0;
            hsm_resp_cmd  <= 8'd0;
            hsm_ext_cmd_valid    <= 1'b0;
            hsm_ext_header_valid <= 1'b0;
            hsm_ext_api_version  <= 8'd0;
            hsm_ext_subcmd       <= 8'd0;
            hsm_ext_response_len_q  <= 8'd0;
            hsm_ext_response_data_q <= 256'd0;
            hsm_ext_safe_len_q      <= 8'd0;
            hsm_ext_build_index     <= 6'd0;
            hsm_ext_flags        <= 8'd0;
            hsm_ext_counter      <= 32'd0;
            hsm_ext_data_len     <= 8'd0;
            hsm_ext_data         <= 256'd0;
            ext_tx_load  <= 1'b0;
            ext_tx_len   <= 8'd0;
            bridge_st    <= ST_IDLE;
        end else begin
            cmd_enroll  <= 1'b0;
            cmd_verify  <= 1'b0;
            ota_begin   <= 1'b0;
            ota_commit  <= 1'b0;
            kyber_start <= 1'b0;
            mlkem512_start <= 1'b0;
            mlkem512_kpke_start <= 1'b0;
            mlkem512_kpke_invalidate <= 1'b0;
            mlkem512_encaps_start <= 1'b0;
            mlkem512_encaps_full_start <= 1'b0;
            mlkem512_decaps_start <= 1'b0;
            c2_run_start <= 1'b0;
            c3_cmd_valid <= 1'b0;
            hsm_cmd_valid <= 1'b0;
            hsm_cmd_id    <= 8'd0;
            hsm_cmd_arg   <= 8'd0;
            hsm_ext_cmd_valid <= 1'b0;
            hsm_ext_header_valid <= 1'b0;
            ext_tx_load <= 1'b0;

            if (frame_valid) begin
                case (frame_cmd)
                    CMD_PUF_ENROLL: begin
                        if (frame_pl_len >= 16'd4) begin
                            nonce <= {frame_pl[0], frame_pl[1], frame_pl[2], frame_pl[3]};
                            if (frame_pl_len >= 16'd5)
                                challenge <= frame_pl[4];
                            else
                                challenge <= 8'h42;
                            cmd_enroll  <= 1'b1;
                            bridge_st   <= ST_WAIT_ENROLL;
                        end
                    end
                    CMD_PUF_VERIFY: begin
                        if (frame_pl_len >= 16'd4) begin
                            nonce <= {frame_pl[0], frame_pl[1], frame_pl[2], frame_pl[3]};
                            if (frame_pl_len >= 16'd5)
                                challenge <= frame_pl[4];
                            else
                                challenge <= 8'h42;
                            cmd_verify  <= 1'b1;
                            bridge_st   <= ST_WAIT_VERIFY;
                        end
                    end
                    CMD_KYBER_NTT_REQ: begin
                        if (ENABLE_LEGACY_MLKEM_SELFTESTS) begin
                            kyber_start <= 1'b1;
                            bridge_st   <= ST_WAIT_KYBER;
                        end else begin
                            build_kyber_resp(1'b0, 32'd0, 16'd0);
                            ext_tx_load <= 1'b1;
                            bridge_st   <= ST_IDLE;
                        end
                    end
                    CMD_MLKEM512_PARTIAL_REQ: begin
                        if (ENABLE_LEGACY_MLKEM_SELFTESTS) begin
                            mlkem512_start <= 1'b1;
                            bridge_st      <= ST_WAIT_MLKEM512;
                        end else begin
                            build_mlkem512_resp(1'b0, 8'd0, 32'd0,
                                                32'd0, 16'd0);
                            ext_tx_load <= 1'b1;
                            bridge_st   <= ST_IDLE;
                        end
                    end
                    CMD_MLKEM512_KPKE_REQ: begin
                        // C2A is a metadata-only health probe.  It never
                        // returns a raw entropy word.  0xC2 is a payload mode
                        // under the existing bounded 0x14/0x15 command pair,
                        // not a new primary opcode.
                        if (ENABLE_C3_TRANSPORT && frame_pl_len >= 16'd2 &&
                            frame_pl[0] == 8'hC3) begin
                            c3_cmd <= frame_pl[1][3:0];
                            c3_pending_cmd <= frame_pl[1][3:0];
                            c3_chunk_index <= (frame_pl_len >= 16'd3) ?
                                              frame_pl[2][4:0] : 5'd0;
                            if (((frame_pl[1] == 8'h02 || frame_pl[1] == 8'h06) &&
                                 frame_pl_len == 16'd3) ||
                                ((frame_pl[1] == 8'h03 || frame_pl[1] == 8'h07) &&
                                 frame_pl_len == 16'd35) ||
                                ((frame_pl[1] == 8'h00 || frame_pl[1] == 8'h01 ||
                                  frame_pl[1] == 8'h04 || frame_pl[1] == 8'h05 ||
                                  frame_pl[1] == 8'h08 || frame_pl[1] == 8'h09 ||
                                  frame_pl[1] == 8'h0A) &&
                                 frame_pl_len == 16'd2)) begin
                                c3_cmd_valid <= 1'b1;
                                bridge_st <= ST_WAIT_C3;
                            end else begin
                                build_mlkem512_stage_resp(
                                    CMD_MLKEM512_KPKE_RESP, 1'b0, 8'hE3,
                                    32'd0, 32'd0, 16'd0);
                                ext_tx_load <= 1'b1;
                                bridge_st <= ST_IDLE;
                            end
                        end else if (ENABLE_INTERNAL_ENTROPY &&
                            frame_pl_len == 16'd1 && frame_pl[0] == 8'hC2) begin
                            build_mlkem512_stage_resp(
                                CMD_MLKEM512_KPKE_RESP,
                                entropy_ready && !entropy_unhealthy,
                                entropy_unhealthy ? entropy_health_code : 8'hC2,
                                entropy_raw_samples,
                                {8'hC2, entropy_health_code, entropy_word_count},
                                16'd0);
                            ext_tx_load <= 1'b1;
                            bridge_st <= ST_IDLE;
                        end else if (ENABLE_INTERNAL_ENTROPY &&
                                    frame_pl_len == 16'd2 &&
                                    frame_pl[0] == 8'hC2 &&
                                    frame_pl[1] == 8'h01) begin
                            c2_run_start <= 1'b1;
                            bridge_st <= ST_WAIT_C2;
                        end else if (frame_pl_len == 16'd0) begin
                            mlkem512_kpke_runtime_seed_valid <= 1'b0;
                            mlkem512_kpke_seed_d <= 256'd0;
                            mlkem512_kpke_seed_z <= 256'd0;
                            mlkem512_kpke_seed_k <= 8'd0;
                            mlkem512_kpke_start <= 1'b1;
                            bridge_st <= ST_WAIT_MLKEM512_KPKE;
                        end else if (frame_pl_len == 16'd65) begin
                            for (bi = 0; bi < 32; bi = bi + 1) begin
                                mlkem512_kpke_seed_d[bi*8 +: 8] <= frame_pl[bi];
                                mlkem512_kpke_seed_z[bi*8 +: 8] <= frame_pl[32 + bi];
                            end
                            mlkem512_kpke_seed_k <= frame_pl[64];
                            mlkem512_kpke_runtime_seed_valid <= 1'b1;
                            mlkem512_kpke_start <= 1'b1;
                            bridge_st <= ST_WAIT_MLKEM512_KPKE;
                        end else begin
                            mlkem512_kpke_runtime_seed_valid <= 1'b0;
                            mlkem512_kpke_seed_d <= 256'd0;
                            mlkem512_kpke_seed_z <= 256'd0;
                            mlkem512_kpke_seed_k <= 8'd0;
                            mlkem512_kpke_invalidate <= 1'b1;
                            build_mlkem512_stage_resp(
                                CMD_MLKEM512_KPKE_RESP, 1'b0, 8'h00,
                                32'd0, 32'd0, 16'd0);
                            ext_tx_load <= 1'b1;
                            bridge_st <= ST_IDLE;
                        end
                    end
                    CMD_MLKEM512_ENCAPS_REQ: begin
                        if (frame_pl_len == 16'd0) begin
                            mlkem512_encaps_runtime_input_valid <= 1'b0;
                            mlkem512_encaps_message <= 256'd0;
                            mlkem512_encaps_coins <= 256'd0;
                            mlkem512_encaps_start <= 1'b1;
                            bridge_st <= ST_WAIT_MLKEM512_ENCAPS;
                        end else if (frame_pl_len == 16'd64) begin
                            for (bi = 0; bi < 32; bi = bi + 1) begin
                                mlkem512_encaps_message[bi*8 +: 8] <= frame_pl[bi];
                                mlkem512_encaps_coins[bi*8 +: 8] <= frame_pl[32 + bi];
                            end
                            mlkem512_encaps_runtime_input_valid <= 1'b1;
                            mlkem512_encaps_start <= 1'b1;
                            bridge_st <= ST_WAIT_MLKEM512_ENCAPS;
                        end else if (frame_pl_len == 16'd32) begin
                            // Stage 3.22 Encaps qualification: the 32-byte message
                            // is public qualification randomness.  G derives
                            // Kbar and Encrypt coins inside the FPGA.
                            for (bi = 0; bi < 32; bi = bi + 1)
                                mlkem512_encaps_full_message[bi*8 +: 8] <= frame_pl[bi];
                            mlkem512_encaps_full_start <= 1'b1;
                            bridge_st <= ST_WAIT_MLKEM512_ENCAPS;
                        end else begin
                            build_mlkem512_stage_resp(
                                CMD_MLKEM512_ENCAPS_RESP, 1'b0, 8'h00,
                                32'd0, 32'd0, 16'd0);
                            ext_tx_load <= 1'b1;
                            bridge_st <= ST_IDLE;
                        end
                    end
                    CMD_MLKEM512_DECAPS_REQ: begin
                        mlkem512_decaps_start <= 1'b1;
                        bridge_st             <= ST_WAIT_MLKEM512_DECAPS;
                    end
                    CMD_OTA_BEGIN: begin
                        if (ENABLE_OTA_POLICY_DEMO && frame_pl_len >= 16'd4) begin
                            // Current OTA demo duplicates the 4-byte payload
                            // into both values. This exercises policy state,
                            // not independent image-hash calculation/checking.
                            expected_hash <= {frame_pl[0], frame_pl[1],
                                            frame_pl[2], frame_pl[3]};
                            image_hash    <= {frame_pl[0], frame_pl[1],
                                            frame_pl[2], frame_pl[3]};
                            if (frame_pl_len >= 16'd5) begin
                                ota_sig_valid_override_en <= 1'b1;
                                ota_sig_valid_override    <= frame_pl[4][0];
                            end else begin
                                ota_sig_valid_override_en <= 1'b0;
                                ota_sig_valid_override    <= 1'b1;
                            end
                            ota_begin <= 1'b1;
                        end
                    end
                    CMD_OTA_COMMIT: begin
                        if (ENABLE_OTA_POLICY_DEMO)
                            ota_commit <= 1'b1;
                    end
                    CMD_HSM_GET_INFO,
                    CMD_HSM_GET_STATUS,
                    CMD_HSM_ZEROIZE_SESSION: begin
                        hsm_cmd_id    <= frame_cmd;
                        hsm_cmd_arg   <= 8'd0;
                        hsm_resp_cmd  <= frame_cmd + 8'd1;
                        hsm_cmd_valid <= 1'b1;
                        bridge_st     <= ST_WAIT_HSM;
                    end
                    CMD_HSM_KEY_STATUS,
                    CMD_HSM_AUDIT_READ: begin
                        hsm_cmd_id    <= frame_cmd;
                        hsm_cmd_arg   <= (frame_pl_len >= 16'd1) ? frame_pl[0] : 8'hFF;
                        hsm_resp_cmd  <= frame_cmd + 8'd1;
                        hsm_cmd_valid <= 1'b1;
                        bridge_st     <= ST_WAIT_HSM;
                    end
                    CMD_HSM_EXT_REQ: begin
                        launch_hsm_ext();
                        bridge_st <= ST_WAIT_HSM_EXT;
                    end
                    default: ;
                endcase
            end

            if (bridge_st == ST_WAIT_ENROLL && enroll_done) begin
                build_enroll_resp(device_id);
                ext_tx_load <= 1'b1;
                bridge_st   <= ST_IDLE;
            end else if (bridge_st == ST_WAIT_VERIFY && verify_done) begin
                build_verify_resp(verify_ok);
                ext_tx_load <= 1'b1;
                bridge_st   <= ST_IDLE;
            end else if (bridge_st == ST_WAIT_KYBER && kyber_done) begin
                build_kyber_resp(kyber_pass, kyber_digest, kyber_cycles);
                ext_tx_load <= 1'b1;
                bridge_st   <= ST_IDLE;
            end else if (bridge_st == ST_WAIT_MLKEM512 && mlkem512_done) begin
                build_mlkem512_resp(mlkem512_pass, mlkem512_status,
                                    mlkem512_partial_digest,
                                    mlkem512_polyvec_digest,
                                    mlkem512_cycles);
                ext_tx_load <= 1'b1;
                bridge_st   <= ST_IDLE;
            end else if (bridge_st == ST_WAIT_MLKEM512_KPKE &&
                         mlkem512_kpke_done) begin
                build_mlkem512_stage_resp(CMD_MLKEM512_KPKE_RESP,
                                          mlkem512_kpke_pass,
                                          mlkem512_kpke_status,
                                          mlkem512_kpke_digest_a,
                                          mlkem512_kpke_digest_b,
                                          mlkem512_kpke_cycles);
                ext_tx_load <= 1'b1;
                bridge_st   <= ST_IDLE;
            end else if (bridge_st == ST_WAIT_MLKEM512_ENCAPS &&
                         mlkem512_encaps_done) begin
                build_mlkem512_stage_resp(CMD_MLKEM512_ENCAPS_RESP,
                                          mlkem512_encaps_pass,
                                          mlkem512_encaps_status,
                                          mlkem512_encaps_digest_a,
                                          mlkem512_encaps_digest_b,
                                          mlkem512_encaps_cycles);
                ext_tx_load <= 1'b1;
                bridge_st   <= ST_IDLE;
            end else if (bridge_st == ST_WAIT_MLKEM512_DECAPS &&
                         mlkem512_decaps_done) begin
                build_mlkem512_stage_resp(CMD_MLKEM512_DECAPS_RESP,
                                          mlkem512_decaps_pass,
                                          mlkem512_decaps_status,
                                          mlkem512_decaps_digest_a,
                                          mlkem512_decaps_digest_b,
                                          mlkem512_decaps_cycles);
                ext_tx_load <= 1'b1;
                bridge_st   <= ST_IDLE;
            end else if (bridge_st == ST_WAIT_HSM && hsm_done) begin
                build_hsm_resp(hsm_resp_cmd, hsm_response_data);
                ext_tx_load <= 1'b1;
                bridge_st   <= ST_IDLE;
            end else if (bridge_st == ST_WAIT_HSM_EXT && hsm_ext_done) begin
                hsm_ext_response_len_q  <= hsm_ext_response_len;
                hsm_ext_response_data_q <= hsm_ext_response_data;
                bridge_st <= ST_BUILD_HSM_EXT;
            end else if (bridge_st == ST_BUILD_HSM_EXT) begin
                hsm_ext_safe_len_q <= (hsm_ext_response_len_q > 8'd32) ?
                                      8'd32 : hsm_ext_response_len_q;
                hsm_ext_build_index <= 6'd0;
                for (bi = 0; bi < 40; bi = bi + 1)
                    ext_tx_buf[bi] = 8'd0;
                ext_tx_buf[0] = SOF;
                ext_tx_buf[1] = CMD_HSM_EXT_RESP;
                ext_tx_buf[2] = 8'd0;
                ext_tx_buf[3] = (hsm_ext_response_len_q > 8'd32) ?
                                8'd32 : hsm_ext_response_len_q;
                crc_acc = crc16_byte(
                               crc16_byte(
                                   crc16_byte(16'hFFFF,
                                              CMD_HSM_EXT_RESP),
                                   8'd0),
                               (hsm_ext_response_len_q > 8'd32) ?
                                8'd32 : hsm_ext_response_len_q);
                bridge_st <= ST_BUILD_HSM_EXT_DATA;
            end else if (bridge_st == ST_BUILD_HSM_EXT_DATA) begin
                if (hsm_ext_build_index < hsm_ext_safe_len_q) begin
                    ext_tx_buf[4 + hsm_ext_build_index] =
                        hsm_ext_response_data_q[255-hsm_ext_build_index*8 -: 8];
                    crc_acc = crc16_byte(
                        crc_acc,
                        hsm_ext_response_data_q[255-hsm_ext_build_index*8 -: 8]);
                    hsm_ext_build_index <= hsm_ext_build_index + 6'd1;
                end else begin
                    bridge_st <= ST_BUILD_HSM_EXT_CRC;
                end
            end else if (bridge_st == ST_BUILD_HSM_EXT_CRC) begin
                ext_tx_buf[4 + hsm_ext_safe_len_q] = crc_acc[15:8];
                ext_tx_buf[5 + hsm_ext_safe_len_q] = crc_acc[7:0];
                ext_tx_len = hsm_ext_safe_len_q + 8'd6;
                bridge_st <= ST_BUILD_HSM_EXT_DONE;
            end else if (bridge_st == ST_BUILD_HSM_EXT_DONE) begin
                ext_tx_load <= 1'b1;
                bridge_st   <= ST_IDLE;
            end else if (bridge_st == ST_WAIT_C2 && c2_run_done) begin
                build_mlkem512_stage_resp(
                    CMD_MLKEM512_KPKE_RESP,
                    c2_run_pass,
                    c2_run_status,
                    {c2_reseed_count, c2_generate_count},
                    {8'hC2, 6'd0, c2_decaps_verified, c2_fresh,
                     entropy_health_code,
                     entropy_word_count[7:0]},
                    c2_run_cycles);
                ext_tx_load <= 1'b1;
                bridge_st <= ST_IDLE;
            end else if (bridge_st == ST_WAIT_C3 && c3_done) begin
                if (c3_pending_cmd == 4'h2 || c3_pending_cmd == 4'h6)
                    build_c3_chunk_resp(c3_pass, c3_chunk_index,
                                        c3_response_data);
                else
                    build_mlkem512_stage_resp(CMD_MLKEM512_KPKE_RESP,
                                              c3_pass, c3_status,
                                              c3_digest_a, c3_digest_b,
                                              c3_cycles);
                ext_tx_load <= 1'b1;
                bridge_st <= ST_IDLE;
            end
        end
    end
endmodule
