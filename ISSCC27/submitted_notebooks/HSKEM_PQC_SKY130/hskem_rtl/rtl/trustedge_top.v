// TrustEdge top-level: SPI + PUF + OTA (dieu khien qua SPI hub)

module trustedge_top #(
    // Qualification keeps the historical 0x10/0x12 self-tests available.
    // The live DE25 profile removes those duplicated diagnostic engines while
    // retaining the shared NTT/Keccak and complete KeyGen/Encrypt/Decaps path.
    parameter MLKEM_QUALIFICATION_PROFILE = 1'b1,
    parameter ENABLE_INTERNAL_ENTROPY = 1'b0,
    // C4 controls the internal full-K handoff only. C5 deliberately decouples
    // that datapath from the PUF/root/vault profile so the final live image
    // can retain both branches in one SOF.
    parameter DEMO_RELEASE_PROFILE = 1'b0,
    parameter ENABLE_PUF_ROOT_VAULT = 1'b1,
    // Default preserves the fitted FPGA one-round/cycle Keccak engine.  The
    // ASIC wrapper may opt into the bounded row-serialized physical candidate.
    parameter ASIC_KECCAK_SERIAL_ROUND = 1'b0,
    // ASIC-only SHA schedule timing candidate.  Default zero keeps the
    // qualified FPGA datapath and its implementation evidence unchanged.
    parameter ASIC_SHA256_SLIDING_SCHEDULE = 1'b0,
    // ASIC-only reset distribution candidate. Each branch is deliberately
    // cycle-equivalent to core_rst_n; the split changes fanout topology only.
    parameter ASIC_RESET_BRANCHES = 1'b0,
    // Break the synchronous CMD_RESET request from the asynchronous-reset
    // distribution graph with a core-clocked register.  FPGA default remains
    // the frozen direct behavior; the ASIC wrapper enables this boundary.
    parameter ASIC_REGISTERED_SOFT_RESET = 1'b0,
    // Static-ticket provisioning and the old OTA policy-only state machine
    // remain qualification-only. The C5 live image fails both paths closed.
    parameter ENABLE_STATIC_AUTH_PROVISION = 1'b1,
    parameter ENABLE_OTA_POLICY_DEMO = 1'b1
) (

    input  wire        clk,

    input  wire        rst_n,

    input  wire        spi_cs_n,

    input  wire        spi_sck,

    input  wire        spi_mosi,

    output wire        spi_miso,

    output wire        spi_irq,

    input  wire        sig_valid,

    input  wire        provision_enable,
    input  wire        sdm_transport_ready,
    input  wire [7:0]  sdm_transport_error,
    input  wire [63:0] sdm_chip_id,
    input  wire        sdm_crypto_enabled,
    input  wire        sdm_crypto_mem_ready,
    input  wire [7:0]  sdm_crypto_mem_error,
    output wire        crypto_zeroize,

    output wire        ota_commit_ok,

    output wire        ota_commit_deny,

    output wire        enrolled,

    output wire        verify_ok,

    output wire [31:0] device_id,

    output wire        kyber_done,

    output wire        kyber_pass
`ifdef TRUSTEDGE_ASIC_SERVICE_PORTS
    ,
    output wire        session_sample_start_o,
    output wire [7:0]  session_sample_challenge_o,
    input  wire        session_sample_busy_i,
    input  wire        session_sample_done_i,
    input  wire [31:0] session_sample_response_i,
    output wire        entropy_enable_o,
    output wire        entropy_clear_health_o,
    input  wire        entropy_valid_i,
    input  wire [31:0] entropy_data_i,
    input  wire        entropy_ready_i,
    input  wire        entropy_unhealthy_i,
    input  wire [7:0]  entropy_health_code_i,
    input  wire [31:0] entropy_raw_sample_count_i,
    input  wire [15:0] entropy_word_count_i,
    output wire        root_puf_scrub_o,
    output wire        root_puf_start_o,
    output wire [1:0]  root_puf_bank_id_o,
    output wire        root_puf_private_mode_o,
    input  wire        root_puf_busy_i,
    input  wire        root_puf_done_i,
    input  wire [63:0] root_puf_response_i,
    input  wire [15:0] root_puf_min_delta_i,
    input  wire [15:0] root_puf_max_delta_i,
    input  wire [7:0]  root_puf_health_i,
    input  wire [31:0] root_puf_cycles_i,
    input  wire        root_puf_physical_i
`endif

);

    wire puf_enrolled, puf_verify_ok, puf_busy;

    wire puf_enroll_done, puf_verify_done;

    wire [31:0] puf_device_id;
    wire [31:0] puf_expected_nonce;
    wire        ota_active;
    wire        crc_error, reset_pulse;
    reg         reset_pulse_registered;
    wire        core_reset_request = ASIC_REGISTERED_SOFT_RESET ?
                                     reset_pulse_registered : reset_pulse;
    wire        core_rst_n = rst_n & ~core_reset_request;
    (* keep = "true" *) wire core_rst_n_top;
    (* keep = "true" *) wire core_rst_n_entropy;
    (* keep = "true" *) wire core_rst_n_security;
    (* keep = "true" *) wire core_rst_n_vault;
    (* keep = "true" *) wire core_rst_n_hmac;
    (* keep = "true" *) wire core_rst_n_sponge;
    (* keep = "true" *) wire core_rst_n_mlkem_a;
    (* keep = "true" *) wire core_rst_n_mlkem_b;
    wire        hsm_zeroize_pulse;
    wire        hsm_session_grant_pulse;
    wire        hsm_mlkem_bind_consume_pulse;

    // reset_pulse is emitted by a core-clocked frame parser.  In the ASIC
    // profile, register it once before it reaches the high-fanout reset tree;
    // this preserves the one-cycle reset semantics while removing any direct
    // combinational path from the parser FF to downstream async-reset pins.
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            reset_pulse_registered <= 1'b0;
        else
            reset_pulse_registered <= reset_pulse;
    end

    generate
        if (ASIC_RESET_BRANCHES) begin : g_asic_reset_branches
            // Keep every branch functionally identical. Distinct physical
            // drivers must be confirmed in the post-synthesis netlist before
            // this candidate is admitted to place-and-route.
            (* keep = "true" *) wire reset_pulse_n;
`ifdef TRUSTEDGE_ASIC_SKY130_RESET_CELLS
            // The generic gates below are sufficient for simulation and the
            // pre-technology structural check, but ABC may legally merge
            // equivalent fanout cones.  In the SKY130 ORFS profile, bind the
            // leaf drivers to real library cells so each branch remains a
            // physical optimization boundary after technology mapping.
            (* keep = "true" *) sky130_fd_sc_hd__inv_1 u_reset_pulse_inv (
                .A(core_reset_request), .Y(reset_pulse_n));
            (* keep = "true" *) sky130_fd_sc_hd__and2_1 u_top (
                .A(rst_n), .B(reset_pulse_n), .X(core_rst_n_top));
            (* keep = "true" *) sky130_fd_sc_hd__and2_1 u_entropy (
                .A(rst_n), .B(reset_pulse_n), .X(core_rst_n_entropy));
            (* keep = "true" *) sky130_fd_sc_hd__and2_1 u_security (
                .A(rst_n), .B(reset_pulse_n), .X(core_rst_n_security));
            (* keep = "true" *) sky130_fd_sc_hd__and2_1 u_vault (
                .A(rst_n), .B(reset_pulse_n), .X(core_rst_n_vault));
            (* keep = "true" *) sky130_fd_sc_hd__and2_1 u_hmac (
                .A(rst_n), .B(reset_pulse_n), .X(core_rst_n_hmac));
            (* keep = "true" *) sky130_fd_sc_hd__and2_1 u_sponge (
                .A(rst_n), .B(reset_pulse_n), .X(core_rst_n_sponge));
            (* keep = "true" *) sky130_fd_sc_hd__and2_1 u_mlkem_a (
                .A(rst_n), .B(reset_pulse_n), .X(core_rst_n_mlkem_a));
            (* keep = "true" *) sky130_fd_sc_hd__and2_1 u_mlkem_b (
                .A(rst_n), .B(reset_pulse_n), .X(core_rst_n_mlkem_b));
`else
            (* keep = "true" *) not u_reset_pulse_inv (
                reset_pulse_n, core_reset_request);
            (* keep = "true" *) and u_top (
                core_rst_n_top, rst_n, reset_pulse_n);
            (* keep = "true" *) and u_entropy (
                core_rst_n_entropy, rst_n, reset_pulse_n);
            (* keep = "true" *) and u_security (
                core_rst_n_security, rst_n, reset_pulse_n);
            (* keep = "true" *) and u_vault (
                core_rst_n_vault, rst_n, reset_pulse_n);
            (* keep = "true" *) and u_hmac (
                core_rst_n_hmac, rst_n, reset_pulse_n);
            (* keep = "true" *) and u_sponge (
                core_rst_n_sponge, rst_n, reset_pulse_n);
            (* keep = "true" *) and u_mlkem_a (
                core_rst_n_mlkem_a, rst_n, reset_pulse_n);
            (* keep = "true" *) and u_mlkem_b (
                core_rst_n_mlkem_b, rst_n, reset_pulse_n);
`endif
        end else begin : g_single_core_reset
            assign core_rst_n_top     = core_rst_n;
            assign core_rst_n_entropy = core_rst_n;
            assign core_rst_n_security = core_rst_n;
            assign core_rst_n_vault   = core_rst_n;
            assign core_rst_n_hmac    = core_rst_n;
            assign core_rst_n_sponge  = core_rst_n;
            assign core_rst_n_mlkem_a = core_rst_n;
            assign core_rst_n_mlkem_b = core_rst_n;
        end
    endgenerate

    // verify_ok tu puf_top chi xung 1 cycle; giu session cho STATUS/OTA
    reg session_active;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            session_active <= 1'b0;
        else if (reset_pulse || hsm_zeroize_pulse)
            session_active <= 1'b0;
        else if (puf_enroll_done)
            session_active <= 1'b0;
        else if ((puf_verify_done && puf_verify_ok) || hsm_session_grant_pulse)
            session_active <= 1'b1;
    end

    // A trusted session may be opened by the frozen PUF demo path or by the
    // compact HSM-2 attestation path. STATUS keeps enrollment as a separate bit.
    wire puf_session = session_active;
    reg [7:0] verify_fail_count;



    wire        frame_valid;

    wire [7:0]  frame_cmd;

    wire [15:0] frame_pl_len;

    wire [7:0]  frame_pl [0:64];

    wire        cmd_enroll, cmd_verify, ota_begin, ota_commit;
    wire        kyber_start;
    wire        kyber_busy, kyber_done_pulse, kyber_pass_w;
    wire [31:0] kyber_digest;
    wire [15:0] kyber_cycles;
    wire        kyber_ntt_req_start, kyber_ntt_req_we;
    wire [7:0]  kyber_ntt_req_addr;
    wire [15:0] kyber_ntt_req_wdata;
    reg         kyber_done_seen;
    wire        mlkem512_start;
    wire        mlkem512_busy, mlkem512_done_pulse, mlkem512_pass_w;
    wire [7:0]  mlkem512_status;
    wire [31:0] mlkem512_partial_digest, mlkem512_polyvec_digest;
    wire [15:0] mlkem512_cycles;
    wire        mlkem512_ntt_req_start, mlkem512_ntt_req_inverse;
    wire        mlkem512_ntt_req_we;
    wire [7:0]  mlkem512_ntt_req_addr;
    wire [15:0] mlkem512_ntt_req_wdata;
    wire        shared_ntt_busy, shared_ntt_done;
    wire [15:0] shared_ntt_rdata;
    reg [2:0]   shared_ntt_owner;
    wire        mlkem512_kpke_start_bridge;
    wire        mlkem512_kpke_runtime_seed_valid_bridge;
    wire        mlkem512_kpke_invalidate_bridge;
    wire [255:0] mlkem512_kpke_seed_d_bridge;
    wire [255:0] mlkem512_kpke_seed_z_bridge;
    wire [7:0]  mlkem512_kpke_seed_k_bridge;
    wire        mlkem512_kpke_busy, mlkem512_kpke_done_pulse, mlkem512_kpke_pass;
    wire [7:0]  mlkem512_kpke_status;
    wire [31:0] mlkem512_kpke_digest_a, mlkem512_kpke_digest_b;
    wire [15:0] mlkem512_kpke_cycles;
    wire        mlkem512_kpke_ntt_req_start, mlkem512_kpke_ntt_req_we;
    wire [7:0]  mlkem512_kpke_ntt_req_addr;
    wire [15:0] mlkem512_kpke_ntt_req_wdata;
    // Internal-only connection from runtime KeyGen storage to runtime
    // Encrypt.  No signal below is routed into the SPI response protocol.
    wire        mlkem512_runtime_key_ready;
    wire        mlkem512_runtime_z_ready;
    wire [255:0] mlkem512_runtime_z;
    wire [8:0]  mlkem512_runtime_matrix_pair_addr;
    wire [11:0] mlkem512_runtime_matrix_even_data;
    wire [11:0] mlkem512_runtime_matrix_odd_data;
    wire [7:0]  mlkem512_runtime_ekpke_pair_addr;
    wire [23:0] mlkem512_runtime_ekpke_pair_data;
    wire [7:0]  mlkem512_encaps_ekpke_pair_addr;
    wire [7:0]  mlkem512_decaps_ekpke_pair_addr;
    wire [4:0]  mlkem512_decaps_rho_addr;
    wire [7:0]  mlkem512_runtime_dkpke_pair_addr;
    wire [23:0] mlkem512_runtime_dkpke_pair_data;
    wire [4:0]  mlkem512_runtime_rho_addr;
    wire [7:0]  mlkem512_runtime_rho_data;
    wire        mlkem512_encaps_start;
    wire        mlkem512_encaps_runtime_input_valid;
    wire [255:0] mlkem512_encaps_message;
    wire [255:0] mlkem512_encaps_coins;
    wire        mlkem512_encaps_full_start_bridge;
    wire [255:0] mlkem512_encaps_full_message_bridge;
    wire        mlkem512_decaps_reencrypt_start;
    wire        mlkem512_decaps_reencrypt_active;
    wire [255:0] mlkem512_decaps_reencrypt_message;
    wire [255:0] mlkem512_decaps_reencrypt_coins;
    wire        mlkem512_encaps_start_mux = mlkem512_encaps_start |
                                             mlkem512_decaps_reencrypt_start;
    wire        mlkem512_encaps_input_valid_mux =
                    mlkem512_decaps_reencrypt_active ? 1'b1 :
                    mlkem512_encaps_runtime_input_valid;
    wire [255:0] mlkem512_encaps_message_mux =
                    mlkem512_decaps_reencrypt_active ?
                    mlkem512_decaps_reencrypt_message : mlkem512_encaps_message;
    wire [255:0] mlkem512_encaps_coins_mux =
                    mlkem512_decaps_reencrypt_active ?
                    mlkem512_decaps_reencrypt_coins : mlkem512_encaps_coins;
    wire        mlkem512_encaps_busy, mlkem512_encaps_done_pulse, mlkem512_encaps_pass;
    wire [7:0]  mlkem512_encaps_status;
    wire [31:0] mlkem512_encaps_digest_a, mlkem512_encaps_digest_b;
    wire [15:0] mlkem512_encaps_cycles;
    wire        mlkem512_encaps_ntt_req_start;
    wire        mlkem512_encaps_ntt_req_inverse;
    wire        mlkem512_encaps_ntt_req_we;
    wire [7:0]  mlkem512_encaps_ntt_req_addr;
    wire [15:0] mlkem512_encaps_ntt_req_wdata;
    wire [9:0]  mlkem512_decoded_coeff_addr;
    wire [9:0]  mlkem512_decaps_decoded_coeff_addr;
    wire [11:0] mlkem512_decoded_coeff_data;
    wire [9:0]  mlkem512_ciphertext_byte_addr;
    wire [9:0]  mlkem512_decaps_ciphertext_byte_addr;
    wire [7:0]  mlkem512_ciphertext_byte_data;
    reg         mlkem512_runtime_ciphertext_ready;
    reg         mlkem512_ciphertext_import_clear;
    reg         mlkem512_ciphertext_import_valid;
    reg [9:0]   mlkem512_ciphertext_import_addr;
    reg [7:0]   mlkem512_ciphertext_import_data;
    reg         mlkem512_ciphertext_import_start;
    reg         c3_import_compare_source;
    wire [9:0]  mlkem512_ciphertext_imported_bytes;
    wire        mlkem512_ciphertext_import_done;
    wire        mlkem512_ciphertext_import_pass;
    wire        mlkem512_kpke_sponge_start, mlkem512_encaps_sponge_start;
    wire        mlkem512_decaps_sponge_start;
    wire [1:0]  mlkem512_kpke_sponge_mode, mlkem512_encaps_sponge_mode;
    wire [1:0]  mlkem512_decaps_sponge_mode;
    wire [15:0] mlkem512_kpke_sponge_message_len, mlkem512_kpke_sponge_output_len;
    wire [15:0] mlkem512_encaps_sponge_message_len, mlkem512_encaps_sponge_output_len;
    wire [15:0] mlkem512_decaps_sponge_message_len, mlkem512_decaps_sponge_output_len;
    wire        mlkem512_kpke_sponge_in_valid, mlkem512_encaps_sponge_in_valid;
    wire        mlkem512_decaps_sponge_in_valid;
    wire [7:0]  mlkem512_kpke_sponge_in_byte, mlkem512_encaps_sponge_in_byte;
    wire [7:0]  mlkem512_decaps_sponge_in_byte;
    wire        mlkem512_kpke_sponge_out_ready, mlkem512_encaps_sponge_out_ready;
    wire        mlkem512_decaps_sponge_out_ready;
    wire        shared_sponge_in_ready, shared_sponge_out_valid;
    wire [7:0]  shared_sponge_out_byte;
    wire        shared_sponge_out_last, shared_sponge_busy;
    wire        shared_sponge_done, shared_sponge_error;
    wire        mlkem512_decaps_start_bridge;
    wire        mlkem512_decaps_start;
    wire        mlkem512_decaps_busy, mlkem512_decaps_done_pulse, mlkem512_decaps_pass;
    wire [7:0]  mlkem512_decaps_status;
    wire [31:0] mlkem512_decaps_digest_a, mlkem512_decaps_digest_b;
    wire [255:0] mlkem512_selected_shared_secret;
    wire [15:0] mlkem512_decaps_cycles;
    reg         mlkem512_encaps_full_pending;
    wire        mlkem512_encaps_resp_done = mlkem512_encaps_full_pending ?
                                             mlkem512_decaps_done_pulse :
                                             mlkem512_encaps_done_pulse;
    wire        mlkem512_encaps_resp_pass = mlkem512_encaps_full_pending ?
                                             mlkem512_decaps_pass :
                                             mlkem512_encaps_pass;
    wire [7:0]  mlkem512_encaps_resp_status = mlkem512_encaps_full_pending ?
                                                   mlkem512_decaps_status :
                                                   mlkem512_encaps_status;
    wire [31:0] mlkem512_encaps_resp_digest_a = mlkem512_encaps_full_pending ?
                                                     mlkem512_decaps_digest_a :
                                                     mlkem512_encaps_digest_a;
    wire [31:0] mlkem512_encaps_resp_digest_b = mlkem512_encaps_full_pending ?
                                                     mlkem512_decaps_digest_b :
                                                     mlkem512_encaps_digest_b;
    wire [15:0] mlkem512_encaps_resp_cycles = mlkem512_encaps_full_pending ?
                                                   mlkem512_decaps_cycles :
                                                   mlkem512_encaps_cycles;
    wire        mlkem512_decaps_ntt_req_start;
    wire        mlkem512_decaps_ntt_req_inverse;

    // C2A online entropy health source. Raw words remain internal and are not
    // connected to SPI. The bridge receives only health/status counters.
    wire        entropy_word_valid;
    wire [31:0] entropy_word_internal;
    wire        entropy_ready;
    wire        entropy_unhealthy;
    wire [7:0]  entropy_health_code;
    wire [31:0] entropy_raw_samples;
    wire [15:0] entropy_word_count;

`ifdef TRUSTEDGE_ASIC_SERVICE_PORTS
    assign entropy_enable_o = ENABLE_INTERNAL_ENTROPY;
    assign entropy_clear_health_o = hsm_zeroize_pulse;
    assign entropy_word_valid = entropy_valid_i;
    assign entropy_word_internal = entropy_data_i;
    assign entropy_ready = entropy_ready_i;
    assign entropy_unhealthy = entropy_unhealthy_i;
    assign entropy_health_code = entropy_health_code_i;
    assign entropy_raw_samples = entropy_raw_sample_count_i;
    assign entropy_word_count = entropy_word_count_i;
`else
    trng u_c2_entropy_source (
        .clk(clk), .rst_n(core_rst_n_entropy),
        .enable(ENABLE_INTERNAL_ENTROPY),
        .clear_health(hsm_zeroize_pulse),
        .valid(entropy_word_valid), .data(entropy_word_internal),
        .ready(entropy_ready), .unhealthy(entropy_unhealthy),
        .health_code(entropy_health_code),
        .raw_sample_count(entropy_raw_samples),
        .word_count(entropy_word_count)
    );
`endif

    // C2B/C2C live path.  A bridge request starts one health-gated
    // reseed-and-generate operation, then feeds private d/z into KeyGen and
    // private m into the complete Encaps/Decaps chain.  Only counters and a
    // pass/fail result return to SPI.
    wire        c2_run_start_bridge;
    reg         c2_drbg_start;
    wire        c2_drbg_busy, c2_drbg_done, c2_drbg_pass;
    wire [7:0]  c2_drbg_status;
    wire        c2_drbg_seeded, c2_drbg_fresh;
    wire [31:0] c2_drbg_reseed_count, c2_drbg_generate_count;
    wire [255:0] c2_mlkem_d, c2_mlkem_z, c2_mlkem_m;
    wire        c2_sponge_active, c2_sponge_start;
    wire [1:0]  c2_sponge_mode;
    wire [15:0] c2_sponge_message_len, c2_sponge_output_len;
    wire        c2_sponge_in_valid, c2_sponge_out_ready;
    wire [7:0]  c2_sponge_in_byte;
    reg         c2_kpke_start;
    reg         c2_encaps_full_start;
    reg         c2_decaps_start;
    reg         c2_run_busy, c2_run_done, c2_run_pass;
    reg         c2_decaps_verified;
    reg [31:0]  c2_encaps_shared_digest;
    reg [7:0]   c2_run_status;
    reg [15:0]  c2_run_cycles;
    reg [2:0]   c2_run_state;

    // C3 exposes only public ekPKE/ciphertext bytes and forces both objects to
    // cross the ESP32 SPI boundary before the next role may consume them.  A
    // single KeyGen/Encrypt/Decaps datapath is time-multiplexed to protect ALM.
    wire        c3_cmd_valid_bridge;
    wire [3:0]  c3_cmd_bridge;
    wire [4:0]  c3_chunk_index_bridge;
    reg         c3_done, c3_pass;
    reg [7:0]   c3_status;
    reg [255:0] c3_response_data;
    reg [31:0]  c3_digest_a, c3_digest_b;
    reg [15:0]  c3_cycles;
    reg         c3_drbg_start, c3_kpke_start;
    reg         c3_encaps_full_start, c3_decaps_start;
    reg         c3_kpke_invalidate;
    reg         c3_crypto_busy;
    reg         c3_receiver_ready, c3_public_key_ready;
    reg         c3_sender_ready, c3_ciphertext_ready;
    reg [31:0]  c3_sender_shared_digest;
    reg [255:0] c4_sender_shared_secret;
    reg [255:0] c4_receiver_shared_secret;
    reg         c4_sender_secret_valid;
    reg         c4_keypair_ready;
    reg [5:0]   c3_state;
    reg [4:0]   c3_pk_export_chunks, c3_pk_import_chunks;
    reg [4:0]   c3_ct_export_chunks, c3_ct_import_chunks;
    reg [5:0]   c3_chunk_byte;
    reg [9:0]   c3_absolute_byte;
    reg [7:0]   c3_pk_export_pair_addr;
    reg [4:0]   c3_pk_export_rho_addr;
    reg [9:0]   c3_ct_export_addr;
    reg [7:0]   c3_pk_import_pair_addr;
    reg [1:0]   c3_pk_import_lane;
    reg [23:0]  c3_pk_import_word;
    reg [1:0]   c3_pk_export_lane;
    reg [31:0]  c3_pk_export_digest_a, c3_pk_export_digest_b;
    reg [31:0]  c3_pk_import_digest_a, c3_pk_import_digest_b;
    reg         c3_pk_write_valid;
    reg [7:0]   c3_pk_write_addr;
    reg [23:0]  c3_pk_write_data;
`ifdef TRUSTEDGE_ASIC_SRAM
    wire [23:0] c3_pk_pair_q;
`else
    (* ramstyle = "M20K, no_rw_check" *) reg [23:0] c3_pk_pair_ram [0:255];
    reg [23:0]  c3_pk_pair_q;
`endif

    localparam [5:0]
        C3_IDLE=6'd0, C3_KG_DRBG=6'd1, C3_KG_WAIT=6'd2,
        C3_PK_RD_REQ=6'd3, C3_PK_RD_WAIT=6'd4, C3_PK_RD_CAP=6'd5,
        C3_PK_WR_BYTE=6'd6, C3_ENC_DRBG=6'd7, C3_ENC_WAIT=6'd8,
        C3_CT_RD_REQ=6'd9, C3_CT_RD_WAIT=6'd10, C3_CT_RD_CAP=6'd11,
        C3_CT_WR_CLEAR=6'd12, C3_CT_WR_BYTE=6'd13,
        C3_CT_FINAL_START=6'd14, C3_CT_FINAL_WAIT=6'd15,
        C3_DECAP_WAIT=6'd16;

    localparam [3:0]
        C3_OP_RESET=4'h0, C3_OP_KEYGEN=4'h1,
        C3_OP_READ_PK=4'h2, C3_OP_WRITE_PK=4'h3,
        C3_OP_FINAL_PK=4'h4, C3_OP_ENCAPS=4'h5,
        C3_OP_READ_CT=4'h6, C3_OP_WRITE_CT=4'h7,
        C3_OP_FINAL_CT=4'h8, C3_OP_DECAPS=4'h9,
        C3_OP_FINAL_CT_C4=4'hA;

    function automatic [31:0] c3_digest_step_a;
        input [31:0] current; input [7:0] value;
        begin c3_digest_step_a={current[30:0],current[31]}^{24'd0,value}; end
    endfunction
    function automatic [31:0] c3_digest_step_b;
        input [31:0] current; input [7:0] value;
        begin c3_digest_step_b={current[26:0],current[31:27]}+{24'd0,value}; end
    endfunction

    wire [7:0] c3_pk_export_byte = (c3_absolute_byte < 10'd768) ?
        ((c3_pk_export_lane == 2'd0) ? mlkem512_runtime_ekpke_pair_data[7:0] :
         (c3_pk_export_lane == 2'd1) ? mlkem512_runtime_ekpke_pair_data[15:8] :
                                       mlkem512_runtime_ekpke_pair_data[23:16]) :
        mlkem512_runtime_rho_data;
    // The frame payload remains stable until the next complete request. Read
    // the active 32-byte chunk in place instead of duplicating it into a
    // 256-bit bridge register and another 256-bit controller register.
    wire [7:0] c3_chunk_input_byte = frame_pl[3 + c3_chunk_byte];

    localparam [2:0] C2_IDLE       = 3'd0,
                     C2_WAIT_DRBG  = 3'd1,
                     C2_WAIT_KPKE  = 3'd2,
                     C2_WAIT_ENCAPS= 3'd3,
                     C2_WAIT_DECAPS= 3'd4;

    wire        mlkem512_kpke_start = mlkem512_kpke_start_bridge |
                                        c2_kpke_start | c3_kpke_start;
    wire        mlkem512_kpke_runtime_seed_valid =
                                        (c2_run_busy || c3_crypto_busy) ? 1'b1 :
                                        mlkem512_kpke_runtime_seed_valid_bridge;
    wire        mlkem512_kpke_invalidate = mlkem512_kpke_invalidate_bridge |
                                            c2_run_start_bridge |
                                            c3_kpke_invalidate;
    wire [255:0] mlkem512_kpke_seed_d =
                                        (c2_run_busy || c3_crypto_busy) ? c2_mlkem_d :
                                        mlkem512_kpke_seed_d_bridge;
    wire [255:0] mlkem512_kpke_seed_z =
                                        (c2_run_busy || c3_crypto_busy) ? c2_mlkem_z :
                                        mlkem512_kpke_seed_z_bridge;
    wire [7:0]  mlkem512_kpke_seed_k =
                                        (c2_run_busy || c3_crypto_busy) ? 8'd2 :
                                        mlkem512_kpke_seed_k_bridge;
    wire        mlkem512_encaps_full_start = mlkem512_encaps_full_start_bridge |
                                              c2_encaps_full_start |
                                              c3_encaps_full_start;
    wire [255:0] mlkem512_encaps_full_message =
                                              (c2_run_busy || c3_crypto_busy) ? c2_mlkem_m :
                                              mlkem512_encaps_full_message_bridge;
    assign mlkem512_decaps_start = mlkem512_decaps_start_bridge |
                                    c2_decaps_start | c3_decaps_start;
    wire mlkem512_decaps_general_mode =
        (c2_run_busy && (c2_run_state == C2_WAIT_DECAPS)) ||
        (c3_crypto_busy && (c3_state == C3_DECAP_WAIT));

    c2_shake_drbg u_c2_shake_drbg (
        .clk(clk), .rst_n(core_rst_n_entropy), .clear(hsm_zeroize_pulse),
        .run_start(c2_drbg_start | c3_drbg_start),
        .entropy_ready(entropy_ready),
        .entropy_unhealthy(entropy_unhealthy),
        .entropy_valid(entropy_word_valid),
        .entropy_word(entropy_word_internal),
        .busy(c2_drbg_busy), .done(c2_drbg_done), .pass(c2_drbg_pass),
        .status(c2_drbg_status), .seeded(c2_drbg_seeded),
        .fresh(c2_drbg_fresh),
        .reseed_count(c2_drbg_reseed_count),
        .generate_count(c2_drbg_generate_count),
        .mlkem_d(c2_mlkem_d), .mlkem_z(c2_mlkem_z), .mlkem_m(c2_mlkem_m),
        .sponge_active(c2_sponge_active), .sponge_start(c2_sponge_start),
        .sponge_mode(c2_sponge_mode),
        .sponge_message_len(c2_sponge_message_len),
        .sponge_output_len(c2_sponge_output_len),
        .sponge_in_valid(c2_sponge_in_valid),
        .sponge_in_byte(c2_sponge_in_byte),
        .sponge_out_ready(c2_sponge_out_ready),
        .sponge_in_ready(shared_sponge_in_ready),
        .sponge_out_valid(shared_sponge_out_valid),
        .sponge_out_byte(shared_sponge_out_byte),
        .sponge_out_last(shared_sponge_out_last),
        .sponge_busy(shared_sponge_busy),
        .sponge_done(shared_sponge_done),
        .sponge_error(shared_sponge_error)
    );

    always @(posedge clk or negedge core_rst_n_top) begin
        if (!core_rst_n_top) begin
            c2_drbg_start <= 1'b0;
            c2_kpke_start <= 1'b0;
            c2_encaps_full_start <= 1'b0;
            c2_decaps_start <= 1'b0;
            c2_run_busy <= 1'b0;
            c2_run_done <= 1'b0;
            c2_run_pass <= 1'b0;
            c2_run_status <= 8'd0;
            c2_run_cycles <= 16'd0;
            c2_decaps_verified <= 1'b0;
            c2_encaps_shared_digest <= 32'd0;
            c2_run_state <= C2_IDLE;
        end else if (hsm_zeroize_pulse) begin
            c2_drbg_start <= 1'b0;
            c2_kpke_start <= 1'b0;
            c2_encaps_full_start <= 1'b0;
            c2_decaps_start <= 1'b0;
            c2_run_busy <= 1'b0;
            c2_run_done <= 1'b0;
            c2_run_pass <= 1'b0;
            c2_run_status <= 8'd0;
            c2_run_cycles <= 16'd0;
            c2_decaps_verified <= 1'b0;
            c2_encaps_shared_digest <= 32'd0;
            c2_run_state <= C2_IDLE;
        end else begin
            c2_drbg_start <= 1'b0;
            c2_kpke_start <= 1'b0;
            c2_encaps_full_start <= 1'b0;
            c2_decaps_start <= 1'b0;
            c2_run_done <= 1'b0;
            if (c2_run_busy && c2_run_cycles != 16'hFFFF)
                c2_run_cycles <= c2_run_cycles + 16'd1;

            case (c2_run_state)
                C2_IDLE: begin
                    c2_run_busy <= 1'b0;
                    if (c2_run_start_bridge) begin
                        c2_run_cycles <= 16'd0;
                        c2_run_pass <= 1'b0;
                        c2_decaps_verified <= 1'b0;
                        c2_encaps_shared_digest <= 32'd0;
                        if (!entropy_ready || entropy_unhealthy) begin
                            c2_run_done <= 1'b1;
                            c2_run_status <= 8'h01;
                        end else begin
                            c2_run_busy <= 1'b1;
                            c2_drbg_start <= 1'b1;
                            c2_run_state <= C2_WAIT_DRBG;
                        end
                    end
                end

                C2_WAIT_DRBG: begin
                    if (c2_drbg_done) begin
                        if (c2_drbg_pass && c2_drbg_fresh && c2_drbg_seeded) begin
                            c2_kpke_start <= 1'b1;
                            c2_run_state <= C2_WAIT_KPKE;
                        end else begin
                            c2_run_busy <= 1'b0;
                            c2_run_done <= 1'b1;
                            c2_run_status <= c2_drbg_pass ? 8'h03 :
                                             c2_drbg_status;
                            c2_run_state <= C2_IDLE;
                        end
                    end
                end

                C2_WAIT_KPKE: begin
                    if (mlkem512_kpke_done_pulse) begin
                        if (mlkem512_kpke_pass) begin
                            c2_encaps_full_start <= 1'b1;
                            c2_run_state <= C2_WAIT_ENCAPS;
                        end else begin
                            c2_run_busy <= 1'b0;
                            c2_run_done <= 1'b1;
                            c2_run_status <= 8'h04;
                            c2_run_state <= C2_IDLE;
                        end
                    end
                end

                C2_WAIT_ENCAPS: begin
                    if (mlkem512_decaps_done_pulse) begin
                        if (mlkem512_decaps_pass) begin
                            c2_encaps_shared_digest <= mlkem512_decaps_digest_a;
                            c2_decaps_start <= 1'b1;
                            c2_run_state <= C2_WAIT_DECAPS;
                        end else begin
                            c2_run_busy <= 1'b0;
                            c2_run_done <= 1'b1;
                            c2_run_status <= 8'h05;
                            c2_run_state <= C2_IDLE;
                        end
                    end
                end

                C2_WAIT_DECAPS: begin
                    if (mlkem512_decaps_done_pulse) begin
                        c2_decaps_verified <= mlkem512_decaps_pass &&
                            (mlkem512_decaps_digest_a == c2_encaps_shared_digest);
                        c2_run_busy <= 1'b0;
                        c2_run_done <= 1'b1;
                        c2_run_pass <= mlkem512_decaps_pass &&
                            (mlkem512_decaps_digest_a == c2_encaps_shared_digest);
                        c2_run_status <= (mlkem512_decaps_pass &&
                            (mlkem512_decaps_digest_a == c2_encaps_shared_digest)) ?
                            8'hC2 : 8'h06;
                        c2_run_state <= C2_IDLE;
                    end
                end

                default: c2_run_state <= C2_IDLE;
            endcase
        end
    end

    wire c3_internal_pk_read = (c3_state == C3_PK_RD_REQ) ||
                               (c3_state == C3_PK_RD_WAIT) ||
                               (c3_state == C3_PK_RD_CAP);
    wire c3_ct_public_read = (c3_state == C3_CT_RD_REQ) ||
                             (c3_state == C3_CT_RD_WAIT) ||
                             (c3_state == C3_CT_RD_CAP);
    wire c3_use_imported_pk = c3_public_key_ready && c3_crypto_busy &&
                              ((c3_state == C3_ENC_DRBG) ||
                               (c3_state == C3_ENC_WAIT) ||
                               (c3_state == C3_DECAP_WAIT));
    // Decaps temporarily launches the shared Encrypt engine for the mandatory
    // re-encryption check.  During that interval the imported-key RAM must
    // follow Encrypt's address, not Decaps' H(ek) address; otherwise the
    // ciphertext comparison fails and Algorithm 18 selects implicit reject J.
    wire [7:0] c3_pk_crypto_read_addr =
        (mlkem512_decaps_busy && !mlkem512_decaps_reencrypt_active) ?
        mlkem512_decaps_ekpke_pair_addr : mlkem512_encaps_ekpke_pair_addr;

`ifdef TRUSTEDGE_ASIC_SRAM
    // Import writes and crypto reads are phase-exclusive. A write occupies the
    // single physical port; its read output is intentionally not consumed.
    wire [7:0] c3_pk_sram_addr = c3_pk_write_valid ?
        c3_pk_write_addr : c3_pk_crypto_read_addr;
    te_sram_1rw #(
        .WIDTH(24), .DEPTH(256), .ADDR_WIDTH(8)
    ) u_c3_pk_pair_sram (
        .clk(clk), .we(c3_pk_write_valid),
        .addr(c3_pk_sram_addr), .wdata(c3_pk_write_data),
        .rdata(c3_pk_pair_q)
    );
`else
    always @(posedge clk) begin
        c3_pk_pair_q <= c3_pk_pair_ram[c3_pk_crypto_read_addr];
        if (c3_pk_write_valid)
            c3_pk_pair_ram[c3_pk_write_addr] <= c3_pk_write_data;
    end
`endif

    // C3 transaction controller.  Each bridge request completes atomically;
    // chunk ordering and double fingerprints make stale, skipped or modified
    // public transport fail closed before crypto is launched.
    always @(posedge clk or negedge core_rst_n_top) begin
        if (!core_rst_n_top) begin
            c3_done <= 1'b0; c3_pass <= 1'b0; c3_status <= 8'd0;
            c3_response_data <= 256'd0;
            c3_digest_a <= 32'd0; c3_digest_b <= 32'd0; c3_cycles <= 16'd0;
            c3_drbg_start <= 1'b0; c3_kpke_start <= 1'b0;
            c3_encaps_full_start <= 1'b0; c3_decaps_start <= 1'b0;
            c3_kpke_invalidate <= 1'b0; c3_crypto_busy <= 1'b0;
            c3_receiver_ready <= 1'b0; c3_public_key_ready <= 1'b0;
            c3_sender_ready <= 1'b0; c3_ciphertext_ready <= 1'b0;
            c3_sender_shared_digest <= 32'd0; c3_state <= C3_IDLE;
            c3_pk_export_chunks <= 5'd0; c3_pk_import_chunks <= 5'd0;
            c3_ct_export_chunks <= 5'd0; c3_ct_import_chunks <= 5'd0;
            c3_chunk_byte <= 6'd0;
            c3_absolute_byte <= 10'd0; c3_pk_export_pair_addr <= 8'd0;
            c3_pk_export_rho_addr <= 5'd0; c3_ct_export_addr <= 10'd0;
            c3_pk_import_pair_addr <= 8'd0; c3_pk_import_lane <= 2'd0;
            c3_pk_import_word <= 24'd0; c3_pk_export_lane <= 2'd0;
            c3_pk_export_digest_a <= 32'h504B4333;
            c3_pk_export_digest_b <= 32'h45585033;
            c3_pk_import_digest_a <= 32'h504B4333;
            c3_pk_import_digest_b <= 32'h45585033;
            c3_pk_write_valid <= 1'b0; c3_pk_write_addr <= 8'd0;
            c3_pk_write_data <= 24'd0;
            mlkem512_ciphertext_import_clear <= 1'b0;
            mlkem512_ciphertext_import_valid <= 1'b0;
            mlkem512_ciphertext_import_addr <= 10'd0;
            mlkem512_ciphertext_import_data <= 8'd0;
            mlkem512_ciphertext_import_start <= 1'b0;
            c3_import_compare_source <= 1'b1;
        end else if (hsm_zeroize_pulse) begin
            c3_done <= 1'b0; c3_pass <= 1'b0; c3_status <= 8'd0;
            c3_response_data <= 256'd0;
            c3_digest_a <= 32'd0; c3_digest_b <= 32'd0; c3_cycles <= 16'd0;
            c3_drbg_start <= 1'b0; c3_kpke_start <= 1'b0;
            c3_encaps_full_start <= 1'b0; c3_decaps_start <= 1'b0;
            c3_kpke_invalidate <= 1'b1; c3_crypto_busy <= 1'b0;
            c3_receiver_ready <= 1'b0; c3_public_key_ready <= 1'b0;
            c3_sender_ready <= 1'b0; c3_ciphertext_ready <= 1'b0;
            c3_sender_shared_digest <= 32'd0; c3_state <= C3_IDLE;
            c3_pk_export_chunks <= 5'd0; c3_pk_import_chunks <= 5'd0;
            c3_ct_export_chunks <= 5'd0; c3_ct_import_chunks <= 5'd0;
            c3_pk_import_pair_addr <= 8'd0; c3_pk_import_lane <= 2'd0;
            c3_pk_import_word <= 24'd0; c3_pk_export_lane <= 2'd0;
            c3_pk_export_digest_a <= 32'h504B4333;
            c3_pk_export_digest_b <= 32'h45585033;
            c3_pk_import_digest_a <= 32'h504B4333;
            c3_pk_import_digest_b <= 32'h45585033;
            c3_pk_write_valid <= 1'b0;
            mlkem512_ciphertext_import_clear <= 1'b1;
            mlkem512_ciphertext_import_valid <= 1'b0;
            mlkem512_ciphertext_import_start <= 1'b0;
            c3_import_compare_source <= 1'b1;
        end else begin
            c3_done <= 1'b0;
            c3_drbg_start <= 1'b0; c3_kpke_start <= 1'b0;
            c3_encaps_full_start <= 1'b0; c3_decaps_start <= 1'b0;
            c3_kpke_invalidate <= 1'b0; c3_pk_write_valid <= 1'b0;
            mlkem512_ciphertext_import_clear <= 1'b0;
            mlkem512_ciphertext_import_valid <= 1'b0;
            mlkem512_ciphertext_import_start <= 1'b0;
            if (c3_state != C3_IDLE && c3_cycles != 16'hFFFF)
                c3_cycles <= c3_cycles + 16'd1;

            case (c3_state)
                C3_IDLE: begin
                    c3_crypto_busy <= 1'b0;
                    if (c3_cmd_valid_bridge) begin
                        c3_pass <= 1'b0; c3_status <= 8'd0;
                        c3_digest_a <= 32'd0; c3_digest_b <= 32'd0;
                        c3_response_data <= 256'd0; c3_cycles <= 16'd0;
                        case (c3_cmd_bridge)
                            C3_OP_RESET: begin
                                c3_receiver_ready <= 1'b0;
                                c3_public_key_ready <= 1'b0;
                                c3_sender_ready <= 1'b0;
                                c3_ciphertext_ready <= 1'b0;
                                c3_sender_shared_digest <= 32'd0;
                                c3_pk_export_chunks <= 5'd0;
                                c3_pk_import_chunks <= 5'd0;
                                c3_ct_export_chunks <= 5'd0;
                                c3_ct_import_chunks <= 5'd0;
                                c3_pk_import_pair_addr <= 8'd0;
                                c3_pk_import_lane <= 2'd0;
                                c3_pk_import_word <= 24'd0;
                                c3_pk_export_lane <= 2'd0;
                                c3_pk_export_digest_a <= 32'h504B4333;
                                c3_pk_export_digest_b <= 32'h45585033;
                                c3_pk_import_digest_a <= 32'h504B4333;
                                c3_pk_import_digest_b <= 32'h45585033;
                                c3_kpke_invalidate <= 1'b1;
                                mlkem512_ciphertext_import_clear <= 1'b1;
                                c3_pass <= 1'b1; c3_status <= 8'hC3;
                                c3_done <= 1'b1;
                            end
                            C3_OP_KEYGEN: begin
                                if (entropy_ready && !entropy_unhealthy &&
                                    !c2_run_busy) begin
                                    c3_crypto_busy <= 1'b1;
                                    c3_drbg_start <= 1'b1;
                                    c3_state <= C3_KG_DRBG;
                                end else begin
                                    c3_status <= 8'hE1; c3_done <= 1'b1;
                                end
                            end
                            C3_OP_READ_PK: begin
                                if (c3_receiver_ready &&
                                    c3_chunk_index_bridge == c3_pk_export_chunks &&
                                    c3_chunk_index_bridge < 5'd25) begin
                                    c3_chunk_byte <= 6'd0;
                                    c3_absolute_byte <= {c3_chunk_index_bridge,5'd0};
                                    c3_state <= C3_PK_RD_REQ;
                                end else begin
                                    c3_status <= 8'hE2; c3_done <= 1'b1;
                                end
                            end
                            C3_OP_WRITE_PK: begin
                                if (c3_receiver_ready &&
                                    c3_chunk_index_bridge == c3_pk_import_chunks &&
                                    c3_chunk_index_bridge < 5'd25) begin
                                    c3_chunk_byte <= 6'd0;
                                    c3_absolute_byte <= {c3_chunk_index_bridge,5'd0};
                                    c3_state <= C3_PK_WR_BYTE;
                                end else begin
                                    c3_status <= 8'hE3; c3_done <= 1'b1;
                                end
                            end
                            C3_OP_FINAL_PK: begin
                                if (c3_pk_export_chunks == 5'd25 &&
                                    c3_pk_import_chunks == 5'd25 &&
                                    c3_pk_import_lane == 2'd0 &&
                                    c3_pk_export_digest_a == c3_pk_import_digest_a &&
                                    c3_pk_export_digest_b == c3_pk_import_digest_b) begin
                                    c3_public_key_ready <= 1'b1;
                                    c3_pass <= 1'b1; c3_status <= 8'hC3;
                                    c3_digest_a <= c3_pk_import_digest_a;
                                    c3_digest_b <= c3_pk_import_digest_b;
                                end else begin
                                    c3_public_key_ready <= 1'b0;
                                    c3_status <= 8'hE4;
                                end
                                c3_done <= 1'b1;
                            end
                            C3_OP_ENCAPS: begin
                                if (c3_public_key_ready && !c2_run_busy) begin
                                    // Reuse the four transport fingerprints
                                    // after public-key finalization; no need
                                    // for another 128 bits of CT-only state.
                                    c3_pk_export_digest_a <= 32'h43544333;
                                    c3_pk_export_digest_b <= 32'h45585033;
                                    c3_pk_import_digest_a <= 32'h43544333;
                                    c3_pk_import_digest_b <= 32'h45585033;
                                    c3_crypto_busy <= 1'b1;
                                    c3_drbg_start <= 1'b1;
                                    c3_state <= C3_ENC_DRBG;
                                end else begin
                                    c3_status <= 8'hE5; c3_done <= 1'b1;
                                end
                            end
                            C3_OP_READ_CT: begin
                                if (c3_sender_ready &&
                                    c3_chunk_index_bridge == c3_ct_export_chunks &&
                                    c3_chunk_index_bridge < 5'd24) begin
                                    c3_chunk_byte <= 6'd0;
                                    c3_ct_export_addr <= {c3_chunk_index_bridge,5'd0};
                                    c3_state <= C3_CT_RD_REQ;
                                end else begin
                                    c3_status <= 8'hE6; c3_done <= 1'b1;
                                end
                            end
                            C3_OP_WRITE_CT: begin
                                if (c3_sender_ready &&
                                    ((c3_chunk_index_bridge == c3_ct_import_chunks &&
                                      c3_chunk_index_bridge < 5'd24) ||
                                     (c3_chunk_index_bridge == 5'd0 &&
                                      c3_ct_import_chunks == 5'd24))) begin
                                    // A completed 24-chunk object may be
                                    // replaced for a new Decaps attempt.  The
                                    // old implementation left the counter at
                                    // 24 and rejected chunk zero, causing C4
                                    // to reuse stale ciphertext and stale K.
                                    if (c3_chunk_index_bridge == 5'd0) begin
                                        c3_ct_import_chunks <= 5'd0;
                                        c3_pk_import_digest_a <= 32'h43544333;
                                        c3_pk_import_digest_b <= 32'h45585033;
                                        c3_ciphertext_ready <= 1'b0;
                                    end
                                    c3_chunk_byte <= 6'd0;
                                    c3_absolute_byte <= {c3_chunk_index_bridge,5'd0};
                                    c3_state <= (c3_chunk_index_bridge == 5'd0) ?
                                                C3_CT_WR_CLEAR : C3_CT_WR_BYTE;
                                end else begin
                                    c3_status <= 8'hE7; c3_done <= 1'b1;
                                end
                            end
                            C3_OP_FINAL_CT: begin
                                c3_import_compare_source <= 1'b1;
                                if (c3_ct_export_chunks == 5'd24 &&
                                    c3_ct_import_chunks == 5'd24 &&
                                    c3_pk_export_digest_a == c3_pk_import_digest_a &&
                                    c3_pk_export_digest_b == c3_pk_import_digest_b) begin
                                    c3_state <= C3_CT_FINAL_START;
                                end else begin
                                    c3_ciphertext_ready <= 1'b0;
                                    c3_status <= 8'hE8; c3_done <= 1'b1;
                                end
                            end
                            C3_OP_FINAL_CT_C4: begin
                                // C4 deliberately feeds a modified public
                                // ciphertext into Algorithm 18 to prove
                                // implicit rejection and wrong-K denial.  It
                                // still requires a complete ordered 768-byte
                                // import; only the C3 transport fingerprint
                                // equality check is bypassed.  The decoder,
                                // re-encrypt compare and K/J selection remain
                                // active and fail closed.
                                if (DEMO_RELEASE_PROFILE &&
                                    c3_ct_import_chunks == 5'd24) begin
                                    c3_import_compare_source <= 1'b0;
                                    c3_state <= C3_CT_FINAL_START;
                                end else begin
                                    c3_ciphertext_ready <= 1'b0;
                                    c3_status <= 8'hE8; c3_done <= 1'b1;
                                end
                            end
                            C3_OP_DECAPS: begin
                                if (c3_ciphertext_ready && c3_public_key_ready) begin
                                    c3_crypto_busy <= 1'b1;
                                    c3_decaps_start <= 1'b1;
                                    c3_state <= C3_DECAP_WAIT;
                                end else begin
                                    c3_status <= 8'hE9; c3_done <= 1'b1;
                                end
                            end
                            default: begin c3_status <= 8'hEF; c3_done <= 1'b1; end
                        endcase
                    end
                end

                C3_KG_DRBG: if (c2_drbg_done) begin
                    if (c2_drbg_pass && c2_drbg_fresh) begin
                        c3_kpke_start <= 1'b1; c3_state <= C3_KG_WAIT;
                    end else begin
                        c3_crypto_busy <= 1'b0; c3_status <= 8'hD1;
                        c3_done <= 1'b1; c3_state <= C3_IDLE;
                    end
                end
                C3_KG_WAIT: if (mlkem512_kpke_done_pulse) begin
                    c3_crypto_busy <= 1'b0;
                    c3_receiver_ready <= mlkem512_kpke_pass;
                    c3_pass <= mlkem512_kpke_pass;
                    c3_status <= mlkem512_kpke_pass ? 8'hC3 : 8'hD2;
                    c3_digest_a <= mlkem512_kpke_digest_a;
                    c3_digest_b <= mlkem512_kpke_digest_b;
                    c3_done <= 1'b1; c3_state <= C3_IDLE;
                end

                C3_PK_RD_REQ: c3_state <= C3_PK_RD_WAIT;
                C3_PK_RD_WAIT: c3_state <= C3_PK_RD_CAP;
                C3_PK_RD_CAP: begin
                    c3_response_data[c3_chunk_byte*8 +: 8] <= c3_pk_export_byte;
                    c3_pk_export_digest_a <= c3_digest_step_a(
                        c3_pk_export_digest_a, c3_pk_export_byte);
                    c3_pk_export_digest_b <= c3_digest_step_b(
                        c3_pk_export_digest_b, c3_pk_export_byte);
                    if (c3_absolute_byte < 10'd768) begin
                        if (c3_pk_export_lane == 2'd2) begin
                            c3_pk_export_lane <= 2'd0;
                            c3_pk_export_pair_addr <= c3_pk_export_pair_addr + 8'd1;
                        end else begin
                            c3_pk_export_lane <= c3_pk_export_lane + 2'd1;
                        end
                    end else begin
                        c3_pk_export_rho_addr <= c3_pk_export_rho_addr + 5'd1;
                    end
                    if (c3_chunk_byte == 6'd31) begin
                        c3_pk_export_chunks <= c3_pk_export_chunks + 5'd1;
                        c3_pass <= 1'b1; c3_status <= 8'hC3;
                        c3_done <= 1'b1; c3_state <= C3_IDLE;
                    end else begin
                        c3_chunk_byte <= c3_chunk_byte + 6'd1;
                        c3_absolute_byte <= c3_absolute_byte + 10'd1;
                        c3_state <= C3_PK_RD_REQ;
                    end
                end

                C3_PK_WR_BYTE: begin
                    c3_pk_import_digest_a <= c3_digest_step_a(
                        c3_pk_import_digest_a, c3_chunk_input_byte);
                    c3_pk_import_digest_b <= c3_digest_step_b(
                        c3_pk_import_digest_b, c3_chunk_input_byte);
                    if (c3_absolute_byte < 10'd768) begin
                        if (c3_pk_import_lane == 2'd0) begin
                            c3_pk_import_word[7:0] <= c3_chunk_input_byte;
                            c3_pk_import_lane <= 2'd1;
                        end else if (c3_pk_import_lane == 2'd1) begin
                            c3_pk_import_word[15:8] <= c3_chunk_input_byte;
                            c3_pk_import_lane <= 2'd2;
                        end else begin
                            c3_pk_write_valid <= 1'b1;
                            c3_pk_write_addr <= c3_pk_import_pair_addr;
                            c3_pk_write_data <= {c3_chunk_input_byte,
                                                 c3_pk_import_word[15:0]};
                            c3_pk_import_pair_addr <= c3_pk_import_pair_addr + 8'd1;
                            c3_pk_import_lane <= 2'd0;
                        end
                    end
                    if (c3_chunk_byte == 6'd31) begin
                        c3_pk_import_chunks <= c3_pk_import_chunks + 5'd1;
                        c3_pass <= 1'b1; c3_status <= 8'hC3;
                        c3_done <= 1'b1; c3_state <= C3_IDLE;
                    end else begin
                        c3_chunk_byte <= c3_chunk_byte + 6'd1;
                        c3_absolute_byte <= c3_absolute_byte + 10'd1;
                    end
                end

                C3_ENC_DRBG: if (c2_drbg_done) begin
                    if (c2_drbg_pass && c2_drbg_fresh) begin
                        c3_encaps_full_start <= 1'b1; c3_state <= C3_ENC_WAIT;
                    end else begin
                        c3_crypto_busy <= 1'b0; c3_status <= 8'hD3;
                        c3_done <= 1'b1; c3_state <= C3_IDLE;
                    end
                end
                C3_ENC_WAIT: if (mlkem512_decaps_done_pulse) begin
                    c3_crypto_busy <= 1'b0;
                    c3_sender_ready <= mlkem512_decaps_pass;
                    c3_sender_shared_digest <= mlkem512_decaps_digest_a;
                    c3_pass <= mlkem512_decaps_pass;
                    c3_status <= mlkem512_decaps_pass ? 8'hC3 : 8'hD4;
                    c3_digest_a <= mlkem512_decaps_digest_a;
                    c3_digest_b <= mlkem512_decaps_digest_b;
                    c3_done <= 1'b1; c3_state <= C3_IDLE;
                end

                C3_CT_RD_REQ: c3_state <= C3_CT_RD_WAIT;
                C3_CT_RD_WAIT: c3_state <= C3_CT_RD_CAP;
                C3_CT_RD_CAP: begin
                    c3_response_data[c3_chunk_byte*8 +: 8] <=
                        mlkem512_ciphertext_byte_data;
                    c3_pk_export_digest_a <= c3_digest_step_a(
                        c3_pk_export_digest_a, mlkem512_ciphertext_byte_data);
                    c3_pk_export_digest_b <= c3_digest_step_b(
                        c3_pk_export_digest_b, mlkem512_ciphertext_byte_data);
                    if (c3_chunk_byte == 6'd31) begin
                        c3_ct_export_chunks <= c3_ct_export_chunks + 5'd1;
                        c3_pass <= 1'b1; c3_status <= 8'hC3;
                        c3_done <= 1'b1; c3_state <= C3_IDLE;
                    end else begin
                        c3_chunk_byte <= c3_chunk_byte + 6'd1;
                        c3_ct_export_addr <= c3_ct_export_addr + 10'd1;
                        c3_state <= C3_CT_RD_REQ;
                    end
                end

                C3_CT_WR_CLEAR: begin
                    mlkem512_ciphertext_import_clear <= 1'b1;
                    c3_state <= C3_CT_WR_BYTE;
                end
                C3_CT_WR_BYTE: begin
                    mlkem512_ciphertext_import_valid <= 1'b1;
                    mlkem512_ciphertext_import_addr <= c3_absolute_byte;
                    mlkem512_ciphertext_import_data <= c3_chunk_input_byte;
                    c3_pk_import_digest_a <= c3_digest_step_a(
                        c3_pk_import_digest_a, c3_chunk_input_byte);
                    c3_pk_import_digest_b <= c3_digest_step_b(
                        c3_pk_import_digest_b, c3_chunk_input_byte);
                    if (c3_chunk_byte == 6'd31) begin
                        c3_ct_import_chunks <= c3_ct_import_chunks + 5'd1;
                        c3_pass <= 1'b1; c3_status <= 8'hC3;
                        c3_done <= 1'b1; c3_state <= C3_IDLE;
                    end else begin
                        c3_chunk_byte <= c3_chunk_byte + 6'd1;
                        c3_absolute_byte <= c3_absolute_byte + 10'd1;
                    end
                end
                C3_CT_FINAL_START: begin
                    mlkem512_ciphertext_import_start <= 1'b1;
                    c3_state <= C3_CT_FINAL_WAIT;
                end
                C3_CT_FINAL_WAIT: if (mlkem512_ciphertext_import_done) begin
                    c3_ciphertext_ready <= mlkem512_ciphertext_import_pass;
                    c3_pass <= mlkem512_ciphertext_import_pass;
                    c3_status <= mlkem512_ciphertext_import_pass ? 8'hC3 : 8'hD5;
                    c3_digest_a <= c3_pk_import_digest_a;
                    c3_digest_b <= c3_pk_import_digest_b;
                    c3_done <= 1'b1; c3_state <= C3_IDLE;
                end
                C3_DECAP_WAIT: if (mlkem512_decaps_done_pulse) begin
                    c3_crypto_busy <= 1'b0;
                    c3_pass <= mlkem512_decaps_pass &&
                               (mlkem512_decaps_digest_a == c3_sender_shared_digest);
                    c3_status <= (mlkem512_decaps_pass &&
                                  (mlkem512_decaps_digest_a == c3_sender_shared_digest)) ?
                                  8'hC3 : 8'hD6;
                    c3_digest_a <= mlkem512_decaps_digest_a;
                    c3_digest_b <= c3_sender_shared_digest;
                    c3_done <= 1'b1; c3_state <= C3_IDLE;
                end
                default: begin c3_state <= C3_IDLE; c3_status <= 8'hFF; end
            endcase
        end
    end
    wire        mlkem512_decaps_ntt_req_we;
    wire [7:0]  mlkem512_decaps_ntt_req_addr;
    wire [15:0] mlkem512_decaps_ntt_req_wdata;
    wire        hsm_cmd_valid;
    wire [7:0]  hsm_cmd_id, hsm_cmd_arg;
    wire        hsm_done;
    wire [63:0] hsm_response_data;
    wire        hsm_ext_cmd_valid, hsm_ext_header_valid;
    wire [7:0]  hsm_ext_api_version, hsm_ext_subcmd, hsm_ext_flags;
    wire [31:0] hsm_ext_counter;
    wire [7:0]  hsm_ext_data_len;
    wire [255:0] hsm_ext_data;
    wire        hsm_ext_done;
    wire [7:0]  hsm_ext_response_len;
    wire [255:0] hsm_ext_response_data;
    wire        hsm_shell_ext_done;
    wire [7:0]  hsm_shell_ext_response_len;
    wire [255:0] hsm_shell_ext_response_data;
    wire        puf_root_ext_done;
    wire [7:0]  puf_root_ext_response_len;
    wire [255:0] puf_root_ext_response_data;
    wire        puf_vault_ext_done;
    wire [7:0]  puf_vault_ext_response_len;
    wire [255:0] puf_vault_ext_response_data;
    wire        puf_root_ready;
    wire [255:0] puf_root_key;
    wire        puf_vault_load_pulse, puf_vault_stage_pulse;
    wire        puf_vault_clear_pulse, puf_vault_loaded;
    wire [255:0] puf_vault_hmac_key;
    wire        puf_vault_stage_authorized;
    wire        hsm_hmac_req_start, hsm_hmac_req_scrub;
    wire [255:0] hsm_hmac_req_key, hsm_hmac_req_message;
    wire [5:0]  hsm_hmac_req_message_len;
    wire        puf_root_hmac_req_start, puf_root_hmac_req_scrub;
    wire [255:0] puf_root_hmac_req_key, puf_root_hmac_req_message;
    wire [5:0]  puf_root_hmac_req_message_len;
    wire        puf_vault_hmac_req_start, puf_vault_hmac_req_scrub;
    wire [255:0] puf_vault_hmac_req_key, puf_vault_hmac_req_message;
    wire [5:0]  puf_vault_hmac_req_message_len;
    wire        security_hmac_busy, security_hmac_done;
    wire [255:0] security_hmac_digest;
    reg [1:0]   security_hmac_owner;
    // D1 remains modes 0x00..0x07. D2/D3 uses 0x08..0x0D under the
    // unchanged outer 0x3A/0x3B transport and PUF subcommand 0x40.
    wire        puf_root_selected = ENABLE_PUF_ROOT_VAULT &&
                                    hsm_ext_subcmd == 8'h40 &&
                                    hsm_ext_data[255:248] <= 8'h07;
    wire        puf_vault_selected = ENABLE_PUF_ROOT_VAULT &&
                                     hsm_ext_subcmd == 8'h40 &&
                                     hsm_ext_data[255:248] >= 8'h08;
    wire        hsm_key_use_pulse = mlkem512_decaps_done_pulse &&
                                     mlkem512_decaps_pass && puf_session;

    // C4 retains the sender and receiver K values only on internal FPGA
    // registers.  Bind is armed only after the complete C3 transport and an
    // exact 256-bit equality check; reset, zeroize, a new C3 epoch, or bind
    // consumption scrubs the handoff state.
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            c4_sender_shared_secret   <= 256'd0;
            c4_receiver_shared_secret <= 256'd0;
            c4_sender_secret_valid    <= 1'b0;
            c4_keypair_ready          <= 1'b0;
        end else if (reset_pulse || hsm_zeroize_pulse ||
                     hsm_mlkem_bind_consume_pulse ||
                     (c3_cmd_valid_bridge &&
                      ((c3_cmd_bridge == C3_OP_RESET) ||
                       (c3_cmd_bridge == C3_OP_KEYGEN)))) begin
            c4_sender_shared_secret   <= 256'd0;
            c4_receiver_shared_secret <= 256'd0;
            c4_sender_secret_valid    <= 1'b0;
            c4_keypair_ready          <= 1'b0;
        end else if (c3_cmd_valid_bridge &&
                     c3_cmd_bridge == C3_OP_WRITE_CT &&
                     c3_chunk_index_bridge == 5'd0) begin
            // Starting any new receiver ciphertext epoch revokes the old
            // receiver K/bind grant while preserving the Encaps sender K.
            c4_receiver_shared_secret <= 256'd0;
            c4_keypair_ready          <= 1'b0;
        end else begin
            if (DEMO_RELEASE_PROFILE &&
                (c3_state == C3_ENC_WAIT) && mlkem512_decaps_done_pulse &&
                mlkem512_decaps_pass) begin
                c4_sender_shared_secret <= mlkem512_selected_shared_secret;
                c4_sender_secret_valid  <= 1'b1;
                c4_keypair_ready        <= 1'b0;
            end
            if (DEMO_RELEASE_PROFILE &&
                (c3_state == C3_DECAP_WAIT) && mlkem512_decaps_done_pulse &&
                mlkem512_decaps_pass && c4_sender_secret_valid) begin
                c4_receiver_shared_secret <= mlkem512_selected_shared_secret;
                c4_keypair_ready <=
                    (mlkem512_selected_shared_secret == c4_sender_shared_secret);
            end
        end
    end

    wire [7:0]  challenge;

    wire [31:0] nonce;

    wire [31:0] image_hash, expected_hash;
    wire        ota_sig_valid_override_en, ota_sig_valid_override;
    wire        ota_sig_valid = ota_sig_valid_override_en ? ota_sig_valid_override : sig_valid;
    wire        ota_commit_ok_pulse, ota_commit_deny_pulse;
    reg         ota_commit_ok_seen, ota_commit_deny_seen;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            kyber_done_seen <= 1'b0;
        else if (reset_pulse)
            kyber_done_seen <= 1'b0;
        else if (kyber_done_pulse)
            kyber_done_seen <= 1'b1;
    end

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            ota_commit_ok_seen <= 1'b0;
            ota_commit_deny_seen <= 1'b0;
        end else if (reset_pulse) begin
            ota_commit_ok_seen <= 1'b0;
            ota_commit_deny_seen <= 1'b0;
        end else if (ota_begin) begin
            ota_commit_ok_seen <= 1'b0;
            ota_commit_deny_seen <= 1'b0;
        end else if (ota_commit_ok_pulse) begin
            ota_commit_ok_seen <= 1'b1;
            ota_commit_deny_seen <= 1'b0;
        end else if (ota_commit_deny_pulse) begin
            ota_commit_ok_seen <= 1'b0;
            ota_commit_deny_seen <= 1'b1;
        end
    end

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            verify_fail_count <= 8'd0;
        else if (reset_pulse || puf_enroll_done)
            verify_fail_count <= 8'd0;
        else if (puf_verify_done && !puf_verify_ok && verify_fail_count != 8'hFF)
            verify_fail_count <= verify_fail_count + 8'd1;
    end



    wire        ext_tx_load;

    wire [7:0]  ext_tx_len;

    wire [7:0]  ext_tx_buf [0:39];

    puf_top u_puf (

        .clk(clk), .rst_n(core_rst_n_security),

        .cmd_enroll(cmd_enroll), .cmd_verify(cmd_verify),

        .challenge(challenge), .nonce(nonce),

        .busy(puf_busy),

        .enroll_done(puf_enroll_done), .verify_done(puf_verify_done),

        .verify_ok(puf_verify_ok), .enrolled(puf_enrolled),

        .device_id(puf_device_id), .expected_nonce(puf_expected_nonce)
`ifdef TRUSTEDGE_ASIC_SERVICE_PORTS
        ,
        .sample_start_o(session_sample_start_o),
        .sample_challenge_o(session_sample_challenge_o),
        .sample_busy_i(session_sample_busy_i),
        .sample_done_i(session_sample_done_i),
        .sample_response_i(session_sample_response_i)
`endif

    );



    // The legacy Kyber smoke test, ML-KEM polyvec stage and K-PKE preparation
    // stage are mutually exclusive SPI commands.  They share the same
    // iterative NTT datapath so the DE25 build does not pay for extra copies.
    always @(posedge clk or negedge core_rst_n_mlkem_a) begin
        if (!core_rst_n_mlkem_a)
            shared_ntt_owner <= 3'd0;
        else if (kyber_start)
            shared_ntt_owner <= 3'd0;
        else if (mlkem512_start)
            shared_ntt_owner <= 3'd1;
        else if (mlkem512_kpke_start)
            shared_ntt_owner <= 3'd2;
        else if (mlkem512_encaps_full_start)
            shared_ntt_owner <= 3'd4;
        else if (mlkem512_encaps_start_mux)
            shared_ntt_owner <= 3'd3;
        else if (mlkem512_decaps_start)
            shared_ntt_owner <= 3'd4;
    end

    wire        shared_ntt_start = (shared_ntt_owner == 3'd4) ?
                                   mlkem512_decaps_ntt_req_start :
                                   (shared_ntt_owner == 3'd3) ?
                                   mlkem512_encaps_ntt_req_start :
                                   (shared_ntt_owner == 3'd2) ?
                                   mlkem512_kpke_ntt_req_start :
                                   (shared_ntt_owner == 3'd1) ?
                                   mlkem512_ntt_req_start : kyber_ntt_req_start;
    wire        shared_ntt_we = (shared_ntt_owner == 3'd4) ?
                                mlkem512_decaps_ntt_req_we :
                                (shared_ntt_owner == 3'd3) ?
                                mlkem512_encaps_ntt_req_we :
                                (shared_ntt_owner == 3'd2) ?
                                mlkem512_kpke_ntt_req_we :
                                (shared_ntt_owner == 3'd1) ?
                                mlkem512_ntt_req_we : kyber_ntt_req_we;
    wire [7:0]  shared_ntt_addr = (shared_ntt_owner == 3'd4) ?
                                  mlkem512_decaps_ntt_req_addr :
                                  (shared_ntt_owner == 3'd3) ?
                                  mlkem512_encaps_ntt_req_addr :
                                  (shared_ntt_owner == 3'd2) ?
                                  mlkem512_kpke_ntt_req_addr :
                                  (shared_ntt_owner == 3'd1) ?
                                  mlkem512_ntt_req_addr : kyber_ntt_req_addr;
    wire [15:0] shared_ntt_wdata = (shared_ntt_owner == 3'd4) ?
                                   mlkem512_decaps_ntt_req_wdata :
                                   (shared_ntt_owner == 3'd3) ?
                                   mlkem512_encaps_ntt_req_wdata :
                                   (shared_ntt_owner == 3'd2) ?
                                   mlkem512_kpke_ntt_req_wdata :
                                   (shared_ntt_owner == 3'd1) ?
                                   mlkem512_ntt_req_wdata : kyber_ntt_req_wdata;
    wire        shared_ntt_inverse = (shared_ntt_owner == 3'd4) ?
                                     mlkem512_decaps_ntt_req_inverse :
                                     (shared_ntt_owner == 3'd3) ?
                                     mlkem512_encaps_ntt_req_inverse :
                                     (shared_ntt_owner == 3'd1) ?
                                     mlkem512_ntt_req_inverse : 1'b0;

    kyber_ntt_engine u_shared_ntt (
        .clk(clk), .rst_n(core_rst_n_mlkem_a),
        .start(shared_ntt_start),
        .inverse(shared_ntt_inverse),
        .busy(shared_ntt_busy), .done(shared_ntt_done),
        .waddr(shared_ntt_addr), .wdata(shared_ntt_wdata),
        .we(shared_ntt_we),
        .rdata(shared_ntt_rdata), .raddr(shared_ntt_addr)
    );

    assign mlkem512_runtime_ekpke_pair_addr = c3_internal_pk_read ?
                                               c3_pk_export_pair_addr :
                                               (mlkem512_decaps_busy &&
                                                !mlkem512_decaps_reencrypt_active) ?
                                               mlkem512_decaps_ekpke_pair_addr :
                                               mlkem512_encaps_ekpke_pair_addr;
    assign mlkem512_runtime_rho_addr = c3_internal_pk_read ?
                                        c3_pk_export_rho_addr :
                                        mlkem512_decaps_rho_addr;
    assign mlkem512_ciphertext_byte_addr = c3_ct_public_read ?
                                            c3_ct_export_addr :
                                            mlkem512_decaps_ciphertext_byte_addr;
    assign mlkem512_decoded_coeff_addr = mlkem512_decaps_decoded_coeff_addr;
    wire [23:0] mlkem512_crypto_ekpke_pair_data = c3_use_imported_pk ?
                                                  c3_pk_pair_q :
                                                  mlkem512_runtime_ekpke_pair_data;
    // rho is the public 32-byte tail of the same generated key. C3 transports
    // and fingerprints it byte-for-byte, then reuses the already retained
    // KeyGen RAM instead of building a second 256-bit variable-select mux.
    wire [7:0] mlkem512_crypto_rho_data = mlkem512_runtime_rho_data;

    // KeyGen, Encrypt and Decrypt/hash-chain are mutually exclusive SPI
    // operations. Their SHA3/SHAKE controllers time-multiplex one sponge.
    wire shared_sponge_owner_encaps = mlkem512_encaps_busy;
    wire shared_sponge_owner_decaps = mlkem512_decaps_busy &&
                                      !mlkem512_decaps_reencrypt_active;
    keccak_sponge_stream #(
        .SERIAL_ROUND(ASIC_KECCAK_SERIAL_ROUND)
    ) u_shared_mlkem_sponge (
        .clk(clk), .rst_n(core_rst_n_sponge), .zeroize(hsm_zeroize_pulse),
        .start(c2_sponge_active ? c2_sponge_start :
               shared_sponge_owner_decaps ? mlkem512_decaps_sponge_start :
               shared_sponge_owner_encaps ? mlkem512_encaps_sponge_start :
                                             mlkem512_kpke_sponge_start),
        .mode(c2_sponge_active ? c2_sponge_mode :
              shared_sponge_owner_decaps ? mlkem512_decaps_sponge_mode :
              shared_sponge_owner_encaps ? mlkem512_encaps_sponge_mode :
                                            mlkem512_kpke_sponge_mode),
        .message_len(c2_sponge_active ? c2_sponge_message_len :
                     shared_sponge_owner_decaps ? mlkem512_decaps_sponge_message_len :
                     shared_sponge_owner_encaps ? mlkem512_encaps_sponge_message_len :
                                                   mlkem512_kpke_sponge_message_len),
        .output_len(c2_sponge_active ? c2_sponge_output_len :
                    shared_sponge_owner_decaps ? mlkem512_decaps_sponge_output_len :
                    shared_sponge_owner_encaps ? mlkem512_encaps_sponge_output_len :
                                                  mlkem512_kpke_sponge_output_len),
        .in_valid(c2_sponge_active ? c2_sponge_in_valid :
                  shared_sponge_owner_decaps ? mlkem512_decaps_sponge_in_valid :
                  shared_sponge_owner_encaps ? mlkem512_encaps_sponge_in_valid :
                                                mlkem512_kpke_sponge_in_valid),
        .in_byte(c2_sponge_active ? c2_sponge_in_byte :
                 shared_sponge_owner_decaps ? mlkem512_decaps_sponge_in_byte :
                 shared_sponge_owner_encaps ? mlkem512_encaps_sponge_in_byte :
                                               mlkem512_kpke_sponge_in_byte),
        .in_ready(shared_sponge_in_ready),
        .out_valid(shared_sponge_out_valid), .out_byte(shared_sponge_out_byte),
        .out_last(shared_sponge_out_last),
        .out_ready(c2_sponge_active ? c2_sponge_out_ready :
                   shared_sponge_owner_decaps ? mlkem512_decaps_sponge_out_ready :
                   shared_sponge_owner_encaps ? mlkem512_encaps_sponge_out_ready :
                                                 mlkem512_kpke_sponge_out_ready),
        .busy(shared_sponge_busy), .done(shared_sponge_done),
        .error(shared_sponge_error)
    );

    generate
    if (MLKEM_QUALIFICATION_PROFILE) begin : g_qualification_selftests
        kyber_ntt_selftest #(
            .USE_EXTERNAL_NTT(1'b1)
        ) u_kyber_selftest (

        .clk(clk), .rst_n(core_rst_n_mlkem_a),

        .start(kyber_start),

        .busy(kyber_busy), .done(kyber_done_pulse),

        .pass(kyber_pass_w), .digest(kyber_digest),

        .cycles(kyber_cycles),
        .ntt_ext_start(kyber_ntt_req_start),
        .ntt_ext_we(kyber_ntt_req_we),
        .ntt_ext_addr(kyber_ntt_req_addr),
        .ntt_ext_wdata(kyber_ntt_req_wdata),
        .ntt_ext_busy(shared_ntt_busy),
        .ntt_ext_done(shared_ntt_done),
        .ntt_ext_rdata(shared_ntt_rdata)

        );



        mlkem512_runtime_selftest #(
            .USE_EXTERNAL_NTT(1'b1)
        ) u_mlkem512_selftest (

        .clk(clk), .rst_n(core_rst_n_mlkem_a),

        .start(mlkem512_start),

        .busy(mlkem512_busy), .done(mlkem512_done_pulse),

        .pass(mlkem512_pass_w), .status(mlkem512_status),

        .partial_digest(mlkem512_partial_digest),

        .polyvec_digest(mlkem512_polyvec_digest),

        .cycles(mlkem512_cycles),
        .ntt_ext_start(mlkem512_ntt_req_start),
        .ntt_ext_inverse(mlkem512_ntt_req_inverse),
        .ntt_ext_we(mlkem512_ntt_req_we),
        .ntt_ext_addr(mlkem512_ntt_req_addr),
        .ntt_ext_wdata(mlkem512_ntt_req_wdata),
        .ntt_ext_busy(shared_ntt_busy),
        .ntt_ext_done(shared_ntt_done),
        .ntt_ext_rdata(shared_ntt_rdata)

        );
    end else begin : g_live_profile_no_legacy_selftests
        assign kyber_busy = 1'b0;
        assign kyber_done_pulse = 1'b0;
        assign kyber_pass_w = 1'b0;
        assign kyber_digest = 32'd0;
        assign kyber_cycles = 16'd0;
        assign kyber_ntt_req_start = 1'b0;
        assign kyber_ntt_req_we = 1'b0;
        assign kyber_ntt_req_addr = 8'd0;
        assign kyber_ntt_req_wdata = 16'd0;

        assign mlkem512_busy = 1'b0;
        assign mlkem512_done_pulse = 1'b0;
        assign mlkem512_pass_w = 1'b0;
        assign mlkem512_status = 8'd0;
        assign mlkem512_partial_digest = 32'd0;
        assign mlkem512_polyvec_digest = 32'd0;
        assign mlkem512_cycles = 16'd0;
        assign mlkem512_ntt_req_start = 1'b0;
        assign mlkem512_ntt_req_inverse = 1'b0;
        assign mlkem512_ntt_req_we = 1'b0;
        assign mlkem512_ntt_req_addr = 8'd0;
        assign mlkem512_ntt_req_wdata = 16'd0;
    end
    endgenerate



    mlkem512_kpke_partial_selftest #(
        .USE_EXTERNAL_NTT(1'b1),
        .USE_EXTERNAL_SPONGE(1'b1)
    ) u_mlkem512_kpke_partial (

        .clk(clk), .rst_n(core_rst_n_mlkem_a),

        .start(mlkem512_kpke_start),
        .invalidate(mlkem512_kpke_invalidate),
        .runtime_seed_valid(mlkem512_kpke_runtime_seed_valid),
        .runtime_seed_d(mlkem512_kpke_seed_d),
        .runtime_seed_z(mlkem512_kpke_seed_z),
        .runtime_seed_k(mlkem512_kpke_seed_k),

        .busy(mlkem512_kpke_busy), .done(mlkem512_kpke_done_pulse),

        .pass(mlkem512_kpke_pass), .status(mlkem512_kpke_status),

        .digest_a(mlkem512_kpke_digest_a),

        .digest_b(mlkem512_kpke_digest_b),

        .cycles(mlkem512_kpke_cycles),
        .ntt_ext_start(mlkem512_kpke_ntt_req_start),
        .ntt_ext_we(mlkem512_kpke_ntt_req_we),
        .ntt_ext_addr(mlkem512_kpke_ntt_req_addr),
        .ntt_ext_wdata(mlkem512_kpke_ntt_req_wdata),
        .ntt_ext_busy(shared_ntt_busy),
        .ntt_ext_done(shared_ntt_done),
        .ntt_ext_rdata(shared_ntt_rdata),
        .sponge_ext_start(mlkem512_kpke_sponge_start),
        .sponge_ext_mode(mlkem512_kpke_sponge_mode),
        .sponge_ext_message_len(mlkem512_kpke_sponge_message_len),
        .sponge_ext_output_len(mlkem512_kpke_sponge_output_len),
        .sponge_ext_in_valid(mlkem512_kpke_sponge_in_valid),
        .sponge_ext_in_byte(mlkem512_kpke_sponge_in_byte),
        .sponge_ext_out_ready(mlkem512_kpke_sponge_out_ready),
        .sponge_ext_in_ready(shared_sponge_in_ready),
        .sponge_ext_out_valid(shared_sponge_out_valid),
        .sponge_ext_out_byte(shared_sponge_out_byte),
        .sponge_ext_out_last(shared_sponge_out_last),
        .sponge_ext_busy(shared_sponge_busy),
        .sponge_ext_done(shared_sponge_done),
        .sponge_ext_error(shared_sponge_error),
        .matrix_ext_pair_addr(mlkem512_runtime_matrix_pair_addr),
        .matrix_ext_even_data(mlkem512_runtime_matrix_even_data),
        .matrix_ext_odd_data(mlkem512_runtime_matrix_odd_data),
        .ekpke_ext_pair_addr(mlkem512_runtime_ekpke_pair_addr),
        .ekpke_ext_pair_data(mlkem512_runtime_ekpke_pair_data),
        .dkpke_ext_pair_addr(mlkem512_runtime_dkpke_pair_addr),
        .dkpke_ext_pair_data(mlkem512_runtime_dkpke_pair_data),
        .rho_ext_addr(mlkem512_runtime_rho_addr),
        .rho_ext_data(mlkem512_runtime_rho_data),
        .runtime_key_ready(mlkem512_runtime_key_ready),
        .runtime_z_ready(mlkem512_runtime_z_ready),
        .runtime_z(mlkem512_runtime_z)

    );



    mlkem512_kpke_encrypt_selftest #(
        .USE_EXTERNAL_NTT(1'b1),
        .USE_EXTERNAL_SPONGE(1'b1),
        .USE_RUNTIME_KEY_BIND(1'b1)
    ) u_mlkem512_encaps_partial (

        .clk(clk), .rst_n(core_rst_n_mlkem_b),

        .start(mlkem512_encaps_start_mux),
        .runtime_input_valid(mlkem512_encaps_input_valid_mux),
        .runtime_message(mlkem512_encaps_message_mux),
        .runtime_coins(mlkem512_encaps_coins_mux),

        .busy(mlkem512_encaps_busy), .done(mlkem512_encaps_done_pulse),

        .pass(mlkem512_encaps_pass), .status(mlkem512_encaps_status),

        .ciphertext_digest(mlkem512_encaps_digest_a),

        .audit_digest(mlkem512_encaps_digest_b),
        .cycles(mlkem512_encaps_cycles),
        .ntt_ext_start(mlkem512_encaps_ntt_req_start),
        .ntt_ext_inverse(mlkem512_encaps_ntt_req_inverse),
        .ntt_ext_we(mlkem512_encaps_ntt_req_we),
        .ntt_ext_addr(mlkem512_encaps_ntt_req_addr),
        .ntt_ext_wdata(mlkem512_encaps_ntt_req_wdata),
        .ntt_ext_busy(shared_ntt_busy),
        .ntt_ext_done(shared_ntt_done),
        .ntt_ext_rdata(shared_ntt_rdata),
        .sponge_ext_start(mlkem512_encaps_sponge_start),
        .sponge_ext_mode(mlkem512_encaps_sponge_mode),
        .sponge_ext_message_len(mlkem512_encaps_sponge_message_len),
        .sponge_ext_output_len(mlkem512_encaps_sponge_output_len),
        .sponge_ext_in_valid(mlkem512_encaps_sponge_in_valid),
        .sponge_ext_in_byte(mlkem512_encaps_sponge_in_byte),
        .sponge_ext_out_ready(mlkem512_encaps_sponge_out_ready),
        .sponge_ext_in_ready(shared_sponge_in_ready),
        .sponge_ext_out_valid(shared_sponge_out_valid),
        .sponge_ext_out_byte(shared_sponge_out_byte),
        .sponge_ext_out_last(shared_sponge_out_last),
        .sponge_ext_busy(shared_sponge_busy),
        .sponge_ext_done(shared_sponge_done),
        .sponge_ext_error(shared_sponge_error),
        .runtime_key_ready(mlkem512_runtime_key_ready),
        .matrix_ext_pair_addr(mlkem512_runtime_matrix_pair_addr),
        .matrix_ext_even_data(mlkem512_runtime_matrix_even_data),
        .matrix_ext_odd_data(mlkem512_runtime_matrix_odd_data),
        .ekpke_ext_pair_addr(mlkem512_encaps_ekpke_pair_addr),
        .ekpke_ext_pair_data(mlkem512_crypto_ekpke_pair_data),
        .ciphertext_read_addr(mlkem512_ciphertext_byte_addr),
        .ciphertext_read_data(mlkem512_ciphertext_byte_data),
        .decoded_read_addr(mlkem512_decoded_coeff_addr),
        .decoded_read_data(mlkem512_decoded_coeff_data),
        .ciphertext_import_clear(mlkem512_ciphertext_import_clear),
        .ciphertext_import_valid(mlkem512_ciphertext_import_valid),
        .ciphertext_import_addr(mlkem512_ciphertext_import_addr),
        .ciphertext_import_data(mlkem512_ciphertext_import_data),
        .ciphertext_import_start(mlkem512_ciphertext_import_start),
        .ciphertext_import_compare_source(c3_import_compare_source),
        .ciphertext_imported_bytes(mlkem512_ciphertext_imported_bytes),
        .ciphertext_import_done(mlkem512_ciphertext_import_done),
        .ciphertext_import_pass(mlkem512_ciphertext_import_pass)

    );

    // A runtime ciphertext becomes consumable only after the complete codec
    // and decode/decompress audit passes.  KeyGen/reset invalidates the old
    // image so K-PKE.Decrypt cannot silently mix epochs.
    always @(posedge clk or negedge core_rst_n_mlkem_b) begin
        if (!core_rst_n_mlkem_b)
            mlkem512_runtime_ciphertext_ready <= 1'b0;
        else if (mlkem512_kpke_start || mlkem512_kpke_invalidate ||
                 mlkem512_encaps_full_start ||
                 mlkem512_ciphertext_import_clear ||
                 (mlkem512_encaps_start && mlkem512_encaps_runtime_input_valid))
            mlkem512_runtime_ciphertext_ready <= 1'b0;
        else if (mlkem512_ciphertext_import_done)
            mlkem512_runtime_ciphertext_ready <= mlkem512_ciphertext_import_pass;
        else if (mlkem512_encaps_done_pulse)
            mlkem512_runtime_ciphertext_ready <= mlkem512_encaps_pass &&
                                                 mlkem512_encaps_input_valid_mux;
    end

    // The unchanged 0x16 response opcode serves legacy KAT/runtime Encrypt
    // and the 32-byte Stage 3.22 Encaps flow.  Retain the selected producer
    // until another 0x16/0x18 request begins; this avoids a one-cycle done
    // pulse race between the controller and the SPI bridge.
    always @(posedge clk or negedge core_rst_n_mlkem_b) begin
        if (!core_rst_n_mlkem_b)
            mlkem512_encaps_full_pending <= 1'b0;
        else if (mlkem512_encaps_full_start_bridge)
            mlkem512_encaps_full_pending <= 1'b1;
        else if (mlkem512_encaps_start || mlkem512_decaps_start)
            mlkem512_encaps_full_pending <= 1'b0;
    end



    mlkem512_decaps_partial_selftest u_mlkem512_decaps_partial (

        .clk(clk), .rst_n(core_rst_n_mlkem_b),

        .start(mlkem512_decaps_start),
        .encaps_start(mlkem512_encaps_full_start),
        .general_runtime_mode(mlkem512_decaps_general_mode),
        .encaps_message(mlkem512_encaps_full_message),
        .runtime_key_ready(mlkem512_runtime_key_ready),
        .runtime_z_ready(mlkem512_runtime_z_ready),
        .runtime_z(mlkem512_runtime_z),
        .ciphertext_ready(mlkem512_runtime_ciphertext_ready),
        .dkpke_ext_pair_addr(mlkem512_runtime_dkpke_pair_addr),
        .dkpke_ext_pair_data(mlkem512_runtime_dkpke_pair_data),
        .ekpke_ext_pair_addr(mlkem512_decaps_ekpke_pair_addr),
        .ekpke_ext_pair_data(mlkem512_crypto_ekpke_pair_data),
        .rho_ext_addr(mlkem512_decaps_rho_addr),
        .rho_ext_data(mlkem512_crypto_rho_data),
        .ciphertext_ext_addr(mlkem512_decaps_ciphertext_byte_addr),
        .ciphertext_ext_data(mlkem512_ciphertext_byte_data),
        .decoded_ext_addr(mlkem512_decaps_decoded_coeff_addr),
        .decoded_ext_data(mlkem512_decoded_coeff_data),
        .ntt_ext_start(mlkem512_decaps_ntt_req_start),
        .ntt_ext_inverse(mlkem512_decaps_ntt_req_inverse),
        .ntt_ext_we(mlkem512_decaps_ntt_req_we),
        .ntt_ext_addr(mlkem512_decaps_ntt_req_addr),
        .ntt_ext_wdata(mlkem512_decaps_ntt_req_wdata),
        .ntt_ext_busy(shared_ntt_busy),
        .ntt_ext_done(shared_ntt_done),
        .ntt_ext_rdata(shared_ntt_rdata),
        .sponge_ext_start(mlkem512_decaps_sponge_start),
        .sponge_ext_mode(mlkem512_decaps_sponge_mode),
        .sponge_ext_message_len(mlkem512_decaps_sponge_message_len),
        .sponge_ext_output_len(mlkem512_decaps_sponge_output_len),
        .sponge_ext_in_valid(mlkem512_decaps_sponge_in_valid),
        .sponge_ext_in_byte(mlkem512_decaps_sponge_in_byte),
        .sponge_ext_out_ready(mlkem512_decaps_sponge_out_ready),
        .sponge_ext_in_ready(shared_sponge_in_ready),
        .sponge_ext_out_valid(shared_sponge_out_valid),
        .sponge_ext_out_byte(shared_sponge_out_byte),
        .sponge_ext_out_last(shared_sponge_out_last),
        .sponge_ext_busy(shared_sponge_busy),
        .sponge_ext_done(shared_sponge_done),
        .sponge_ext_error(shared_sponge_error),
        .reencrypt_start(mlkem512_decaps_reencrypt_start),
        .reencrypt_active(mlkem512_decaps_reencrypt_active),
        .reencrypt_message(mlkem512_decaps_reencrypt_message),
        .reencrypt_coins(mlkem512_decaps_reencrypt_coins),
        .reencrypt_busy(mlkem512_encaps_busy),
        .reencrypt_done(mlkem512_encaps_done_pulse),
        .reencrypt_pass(mlkem512_encaps_pass),

        .busy(mlkem512_decaps_busy), .done(mlkem512_decaps_done_pulse),

        .pass(mlkem512_decaps_pass), .status(mlkem512_decaps_status),

        .selected_shared_secret(mlkem512_selected_shared_secret),

        .valid_shared_digest(mlkem512_decaps_digest_a),

        .corrupt_shared_digest(mlkem512_decaps_digest_b),

        .cycles(mlkem512_decaps_cycles)

    );

    // HSM commands, PUF-root reconstruction and vault sealing are serialized
    // by the SPI bridge.  Time-multiplex their HMAC work onto one iterative
    // SHA-256 engine instead of placing three identical ~3k-ALM instances.
    localparam [1:0] SECURITY_HMAC_NONE  = 2'd0,
                     SECURITY_HMAC_HSM   = 2'd1,
                     SECURITY_HMAC_ROOT  = 2'd2,
                     SECURITY_HMAC_VAULT = 2'd3;
    wire security_hmac_start = hsm_hmac_req_start |
                               puf_root_hmac_req_start |
                               puf_vault_hmac_req_start;
    wire security_hmac_scrub = hsm_hmac_req_scrub |
                               puf_root_hmac_req_scrub |
                               puf_vault_hmac_req_scrub;
    wire [1:0] security_hmac_requester = hsm_hmac_req_start ?
                                          SECURITY_HMAC_HSM :
                                         puf_root_hmac_req_start ?
                                          SECURITY_HMAC_ROOT :
                                         puf_vault_hmac_req_start ?
                                          SECURITY_HMAC_VAULT :
                                          SECURITY_HMAC_NONE;
    wire [255:0] security_hmac_key = hsm_hmac_req_start ?
                                      hsm_hmac_req_key :
                                     puf_root_hmac_req_start ?
                                      puf_root_hmac_req_key :
                                      puf_vault_hmac_req_key;
    wire [255:0] security_hmac_message = hsm_hmac_req_start ?
                                          hsm_hmac_req_message :
                                         puf_root_hmac_req_start ?
                                          puf_root_hmac_req_message :
                                          puf_vault_hmac_req_message;
    wire [5:0] security_hmac_message_len = hsm_hmac_req_start ?
                                            hsm_hmac_req_message_len :
                                           puf_root_hmac_req_start ?
                                            puf_root_hmac_req_message_len :
                                            puf_vault_hmac_req_message_len;

    always @(posedge clk or negedge core_rst_n_hmac) begin
        if (!core_rst_n_hmac)
            security_hmac_owner <= SECURITY_HMAC_NONE;
        else if (security_hmac_scrub)
            security_hmac_owner <= SECURITY_HMAC_NONE;
        else if (security_hmac_start && !security_hmac_busy)
            security_hmac_owner <= security_hmac_requester;
        else if (security_hmac_done)
            security_hmac_owner <= SECURITY_HMAC_NONE;
    end

    hmac_sha256_fixed #(
        .SHA256_SLIDING_SCHEDULE(ASIC_SHA256_SLIDING_SCHEDULE)
    ) u_security_hmac (
        .clk(clk), .rst_n(core_rst_n_hmac), .scrub(security_hmac_scrub),
        .start(security_hmac_start), .key(security_hmac_key),
        .message(security_hmac_message),
        .message_len(security_hmac_message_len),
        .busy(security_hmac_busy), .done(security_hmac_done),
        .digest(security_hmac_digest)
    );

    hsm_shell #(
        .ENABLE_MLKEM_K_CHANNEL(DEMO_RELEASE_PROFILE),
        .ENABLE_STATIC_AUTH_PROVISION(ENABLE_STATIC_AUTH_PROVISION),
        .EXTERNAL_HMAC(1'b1)
    ) u_hsm_shell (
        .clk(clk), .rst_n(core_rst_n_security),
        .session_valid(session_active),
        .device_id(puf_device_id),
        .provision_enable(provision_enable),
        .sdm_transport_ready(sdm_transport_ready),
        .sdm_transport_error(sdm_transport_error),
        .sdm_chip_id(sdm_chip_id),
        .sdm_crypto_enabled(sdm_crypto_enabled),
        .sdm_crypto_mem_ready(sdm_crypto_mem_ready),
        .sdm_crypto_mem_error(sdm_crypto_mem_error),
        .cmd_valid(hsm_cmd_valid),
        .cmd_id(hsm_cmd_id), .cmd_arg(hsm_cmd_arg),
        .key_use_pulse(hsm_key_use_pulse),
        .puf_vault_load_pulse(puf_vault_load_pulse),
        .puf_vault_stage_pulse(puf_vault_stage_pulse),
        .puf_vault_clear_pulse(puf_vault_clear_pulse),
        .puf_vault_key(puf_vault_hmac_key),
        .puf_vault_stage_authorized(puf_vault_stage_authorized),
        .done(hsm_done), .response_data(hsm_response_data),
        .ext_cmd_valid(hsm_ext_cmd_valid && !puf_root_selected &&
                       !puf_vault_selected),
        .ext_header_valid(hsm_ext_header_valid),
        .ext_mlkem_pass(c4_keypair_ready),
        .ext_mlkem_key_valid(c4_keypair_ready),
        .ext_mlkem_sender_key(c4_sender_shared_secret),
        .ext_mlkem_receiver_key(c4_receiver_shared_secret),
        .ext_api_version(hsm_ext_api_version),
        .ext_subcmd(hsm_ext_subcmd),
        .ext_flags(hsm_ext_flags),
        .ext_counter(hsm_ext_counter),
        .ext_data_len(hsm_ext_data_len),
        .ext_data(hsm_ext_data),
        .ext_done(hsm_shell_ext_done),
        .ext_response_len(hsm_shell_ext_response_len),
        .ext_response_data(hsm_shell_ext_response_data),
        .session_grant_pulse(hsm_session_grant_pulse),
        .mlkem_bind_consume_pulse(hsm_mlkem_bind_consume_pulse),
        .zeroize_pulse(hsm_zeroize_pulse),
        .hmac_req_start(hsm_hmac_req_start),
        .hmac_req_scrub(hsm_hmac_req_scrub),
        .hmac_req_key(hsm_hmac_req_key),
        .hmac_req_message(hsm_hmac_req_message),
        .hmac_req_message_len(hsm_hmac_req_message_len),
        .hmac_rsp_busy(security_hmac_busy &&
                       security_hmac_owner == SECURITY_HMAC_HSM),
        .hmac_rsp_done(security_hmac_done &&
                       security_hmac_owner == SECURITY_HMAC_HSM),
        .hmac_rsp_digest(security_hmac_digest)
    );

    // HSM-4D1 keeps the private PUF response/root outside the generic HSM
    // response mux.  Subcommand 0x40 exposes only helper chunks and status;
    // the former D0 raw-sample mode is blocked in this artifact.
    generate
    // Keep the historical generate label because qualification testbenches
    // use it as a stable hierarchy path; C5 also enables this branch live.
    if (ENABLE_PUF_ROOT_VAULT) begin : g_qualification_puf_vault
    puf_root_service #(.EXTERNAL_HMAC(1'b1)) u_puf_root_service (
        .clk(clk), .rst_n(core_rst_n_vault),
        .cmd_valid(hsm_ext_cmd_valid && puf_root_selected),
        .header_valid(hsm_ext_header_valid),
        .provision_enable(provision_enable),
        .zeroize(hsm_zeroize_pulse),
        .transport_ready(sdm_transport_ready),
        .transport_error(sdm_transport_error),
        .chip_id(sdm_chip_id),
        .api_version(hsm_ext_api_version),
        .subcmd(hsm_ext_subcmd),
        .flags(hsm_ext_flags),
        .counter(hsm_ext_counter),
        .data_len(hsm_ext_data_len),
        .data(hsm_ext_data),
        .done(puf_root_ext_done),
        .response_len(puf_root_ext_response_len),
        .response_data(puf_root_ext_response_data),
        .root_ready(puf_root_ready),
        .root_key(puf_root_key),
        .hmac_req_start(puf_root_hmac_req_start),
        .hmac_req_scrub(puf_root_hmac_req_scrub),
        .hmac_req_key(puf_root_hmac_req_key),
        .hmac_req_message(puf_root_hmac_req_message),
        .hmac_req_message_len(puf_root_hmac_req_message_len),
        .hmac_rsp_busy(security_hmac_busy &&
                       security_hmac_owner == SECURITY_HMAC_ROOT),
        .hmac_rsp_done(security_hmac_done &&
                       security_hmac_owner == SECURITY_HMAC_ROOT),
        .hmac_rsp_digest(security_hmac_digest)
`ifdef TRUSTEDGE_ASIC_SERVICE_PORTS
        ,
        .measure_scrub_o(root_puf_scrub_o),
        .measure_start_o(root_puf_start_o),
        .measure_bank_id_o(root_puf_bank_id_o),
        .measure_private_mode_o(root_puf_private_mode_o),
        .measure_busy_i(root_puf_busy_i),
        .measure_done_i(root_puf_done_i),
        .measure_response_i(root_puf_response_i),
        .measure_min_delta_i(root_puf_min_delta_i),
        .measure_max_delta_i(root_puf_max_delta_i),
        .measure_health_i(root_puf_health_i),
        .measure_cycles_i(root_puf_cycles_i),
        .measure_physical_i(root_puf_physical_i)
`endif
    );

    puf_vault_service #(.EXTERNAL_HMAC(1'b1)) u_puf_vault_service (
        .clk(clk), .rst_n(core_rst_n_vault),
        .cmd_valid(hsm_ext_cmd_valid && puf_vault_selected),
        .header_valid(hsm_ext_header_valid),
        .provision_enable(provision_enable),
        .zeroize(hsm_zeroize_pulse),
        .transport_ready(sdm_transport_ready),
        .transport_error(sdm_transport_error),
        .chip_id(sdm_chip_id),
        .api_version(hsm_ext_api_version),
        .subcmd(hsm_ext_subcmd),
        .flags(hsm_ext_flags),
        .counter(hsm_ext_counter),
        .data_len(hsm_ext_data_len),
        .data(hsm_ext_data),
        .root_ready(puf_root_ready),
        .root_key(puf_root_key),
        .vault_stage_authorized(puf_vault_stage_authorized),
        .done(puf_vault_ext_done),
        .response_len(puf_vault_ext_response_len),
        .response_data(puf_vault_ext_response_data),
        .vault_load_pulse(puf_vault_load_pulse),
        .vault_stage_pulse(puf_vault_stage_pulse),
        .vault_clear_pulse(puf_vault_clear_pulse),
        .vault_loaded(puf_vault_loaded),
        .vault_hmac_key(puf_vault_hmac_key),
        .hmac_req_start(puf_vault_hmac_req_start),
        .hmac_req_scrub(puf_vault_hmac_req_scrub),
        .hmac_req_key(puf_vault_hmac_req_key),
        .hmac_req_message(puf_vault_hmac_req_message),
        .hmac_req_message_len(puf_vault_hmac_req_message_len),
        .hmac_rsp_busy(security_hmac_busy &&
                       security_hmac_owner == SECURITY_HMAC_VAULT),
        .hmac_rsp_done(security_hmac_done &&
                       security_hmac_owner == SECURITY_HMAC_VAULT),
        .hmac_rsp_digest(security_hmac_digest)
    );
    end else begin : g_no_puf_root_vault
        assign puf_root_ext_done = 1'b0;
        assign puf_root_ext_response_len = 8'd0;
        assign puf_root_ext_response_data = 256'd0;
        assign puf_root_ready = 1'b0;
        assign puf_root_key = 256'd0;
        assign puf_vault_ext_done = 1'b0;
        assign puf_vault_ext_response_len = 8'd0;
        assign puf_vault_ext_response_data = 256'd0;
        assign puf_vault_load_pulse = 1'b0;
        assign puf_vault_stage_pulse = 1'b0;
        assign puf_vault_clear_pulse = 1'b0;
        assign puf_vault_loaded = 1'b0;
        assign puf_vault_hmac_key = 256'd0;
        assign puf_root_hmac_req_start = 1'b0;
        assign puf_root_hmac_req_scrub = 1'b0;
        assign puf_root_hmac_req_key = 256'd0;
        assign puf_root_hmac_req_message = 256'd0;
        assign puf_root_hmac_req_message_len = 6'd0;
        assign puf_vault_hmac_req_start = 1'b0;
        assign puf_vault_hmac_req_scrub = 1'b0;
        assign puf_vault_hmac_req_key = 256'd0;
        assign puf_vault_hmac_req_message = 256'd0;
        assign puf_vault_hmac_req_message_len = 6'd0;
    end
    endgenerate

    assign hsm_ext_done = puf_root_selected ? puf_root_ext_done :
                          puf_vault_selected ? puf_vault_ext_done :
                          hsm_shell_ext_done;
    assign hsm_ext_response_len = puf_root_selected ?
                                  puf_root_ext_response_len :
                                  puf_vault_selected ?
                                  puf_vault_ext_response_len :
                                  hsm_shell_ext_response_len;
    assign hsm_ext_response_data = puf_root_selected ?
                                   puf_root_ext_response_data :
                                   puf_vault_selected ?
                                   puf_vault_ext_response_data :
                                   hsm_shell_ext_response_data;

    assign crypto_zeroize = hsm_zeroize_pulse;



    spi_slave #(.MAX_PAYLOAD(65)) u_spi (

        .clk(clk), .rst_n(rst_n),

        .cs_n(spi_cs_n), .sck(spi_sck), .mosi(spi_mosi), .miso(spi_miso),

        .irq(spi_irq),

        .enrolled(puf_enrolled), .session_valid(puf_session),

        .ota_pending(ota_active),
        .ota_ok_seen(ota_commit_ok_seen),
        .ota_deny_seen(ota_commit_deny_seen),
        .verify_fail_count(verify_fail_count),

        .frame_valid(frame_valid), .frame_cmd(frame_cmd),

        .frame_pl_len(frame_pl_len), .frame_pl(frame_pl),

        .crc_error(crc_error), .reset_pulse(reset_pulse),

        .ext_tx_load(ext_tx_load), .ext_tx_len(ext_tx_len), .ext_tx_buf(ext_tx_buf)

    );



    spi_command_bridge #(
        .MAX_PAYLOAD(65),
        .ENABLE_LEGACY_MLKEM_SELFTESTS(MLKEM_QUALIFICATION_PROFILE),
        .ENABLE_INTERNAL_ENTROPY(ENABLE_INTERNAL_ENTROPY),
        .ENABLE_C3_TRANSPORT(ENABLE_INTERNAL_ENTROPY),
        .ENABLE_OTA_POLICY_DEMO(ENABLE_OTA_POLICY_DEMO)
    ) u_bridge (

        .clk(clk), .rst_n(core_rst_n_top),

        .frame_valid(frame_valid), .frame_cmd(frame_cmd),

        .frame_pl_len(frame_pl_len), .frame_pl(frame_pl),

        .cmd_enroll(cmd_enroll), .cmd_verify(cmd_verify),

        .challenge(challenge), .nonce(nonce),

        .ota_begin(ota_begin), .ota_commit(ota_commit),

        .image_hash(image_hash), .expected_hash(expected_hash),
        .ota_sig_valid_override_en(ota_sig_valid_override_en),
        .ota_sig_valid_override(ota_sig_valid_override),
        .kyber_start(kyber_start),
        .mlkem512_start(mlkem512_start),
        .mlkem512_kpke_start(mlkem512_kpke_start_bridge),
        .mlkem512_kpke_runtime_seed_valid(mlkem512_kpke_runtime_seed_valid_bridge),
        .mlkem512_kpke_invalidate(mlkem512_kpke_invalidate_bridge),
        .mlkem512_kpke_seed_d(mlkem512_kpke_seed_d_bridge),
        .mlkem512_kpke_seed_z(mlkem512_kpke_seed_z_bridge),
        .mlkem512_kpke_seed_k(mlkem512_kpke_seed_k_bridge),
        .mlkem512_encaps_start(mlkem512_encaps_start),
        .mlkem512_encaps_runtime_input_valid(mlkem512_encaps_runtime_input_valid),
        .mlkem512_encaps_message(mlkem512_encaps_message),
        .mlkem512_encaps_coins(mlkem512_encaps_coins),
        .mlkem512_encaps_full_start(mlkem512_encaps_full_start_bridge),
        .mlkem512_encaps_full_message(mlkem512_encaps_full_message_bridge),
        .mlkem512_decaps_start(mlkem512_decaps_start_bridge),
        .entropy_ready(entropy_ready),
        .entropy_unhealthy(entropy_unhealthy),
        .entropy_health_code(entropy_health_code),
        .entropy_raw_samples(entropy_raw_samples),
        .entropy_word_count(entropy_word_count),
        .c2_run_start(c2_run_start_bridge),
        .c2_run_done(c2_run_done),
        .c2_run_pass(c2_run_pass),
        .c2_run_status(c2_run_status),
        .c2_reseed_count(c2_drbg_reseed_count[15:0]),
        .c2_generate_count(c2_drbg_generate_count[15:0]),
        .c2_fresh(c2_drbg_fresh),
        .c2_decaps_verified(c2_decaps_verified),
        .c2_run_cycles(c2_run_cycles),
        .c3_cmd_valid(c3_cmd_valid_bridge),
        .c3_cmd(c3_cmd_bridge),
        .c3_chunk_index(c3_chunk_index_bridge),
        .c3_done(c3_done), .c3_pass(c3_pass), .c3_status(c3_status),
        .c3_response_data(c3_response_data),
        .c3_digest_a(c3_digest_a), .c3_digest_b(c3_digest_b),
        .c3_cycles(c3_cycles),
        .kyber_done(kyber_done_pulse),
        .kyber_pass(kyber_pass_w),
        .kyber_digest(kyber_digest),
        .kyber_cycles(kyber_cycles),
        .mlkem512_done(mlkem512_done_pulse),
        .mlkem512_pass(mlkem512_pass_w),
        .mlkem512_status(mlkem512_status),
        .mlkem512_partial_digest(mlkem512_partial_digest),
        .mlkem512_polyvec_digest(mlkem512_polyvec_digest),
        .mlkem512_cycles(mlkem512_cycles),
        .mlkem512_kpke_done(mlkem512_kpke_done_pulse),
        .mlkem512_kpke_pass(mlkem512_kpke_pass),
        .mlkem512_kpke_status(mlkem512_kpke_status),
        .mlkem512_kpke_digest_a(mlkem512_kpke_digest_a),
        .mlkem512_kpke_digest_b(mlkem512_kpke_digest_b),
        .mlkem512_kpke_cycles(mlkem512_kpke_cycles),
        .mlkem512_encaps_done(mlkem512_encaps_resp_done),
        .mlkem512_encaps_pass(mlkem512_encaps_resp_pass),
        .mlkem512_encaps_status(mlkem512_encaps_resp_status),
        .mlkem512_encaps_digest_a(mlkem512_encaps_resp_digest_a),
        .mlkem512_encaps_digest_b(mlkem512_encaps_resp_digest_b),
        .mlkem512_encaps_cycles(mlkem512_encaps_resp_cycles),
        .mlkem512_decaps_done(mlkem512_decaps_done_pulse),
        .mlkem512_decaps_pass(mlkem512_decaps_pass),
        .mlkem512_decaps_status(mlkem512_decaps_status),
        .mlkem512_decaps_digest_a(mlkem512_decaps_digest_a),
        .mlkem512_decaps_digest_b(mlkem512_decaps_digest_b),
        .mlkem512_decaps_cycles(mlkem512_decaps_cycles),
        .hsm_cmd_valid(hsm_cmd_valid),
        .hsm_cmd_id(hsm_cmd_id),
        .hsm_cmd_arg(hsm_cmd_arg),
        .hsm_done(hsm_done),
        .hsm_response_data(hsm_response_data),
        .hsm_ext_cmd_valid(hsm_ext_cmd_valid),
        .hsm_ext_header_valid(hsm_ext_header_valid),
        .hsm_ext_api_version(hsm_ext_api_version),
        .hsm_ext_subcmd(hsm_ext_subcmd),
        .hsm_ext_flags(hsm_ext_flags),
        .hsm_ext_counter(hsm_ext_counter),
        .hsm_ext_data_len(hsm_ext_data_len),
        .hsm_ext_data(hsm_ext_data),
        .hsm_ext_done(hsm_ext_done),
        .hsm_ext_response_len(hsm_ext_response_len),
        .hsm_ext_response_data(hsm_ext_response_data),

        .enroll_done(puf_enroll_done), .verify_done(puf_verify_done),

        .verify_ok(puf_verify_ok), .device_id(puf_device_id),
        .cs_active(!spi_cs_n),
        .ext_tx_load(ext_tx_load), .ext_tx_len(ext_tx_len), .ext_tx_buf(ext_tx_buf)

    );



    generate
    if (ENABLE_OTA_POLICY_DEMO) begin : g_qualification_ota_policy_demo
    ota_gate u_ota (

        .clk(clk), .rst_n(core_rst_n_top),

        .puf_session_ok(puf_session),

        .sig_valid(ota_sig_valid),

        .ota_begin(ota_begin), .ota_commit(ota_commit),

        .image_hash(image_hash), .expected_hash(expected_hash),

        .ota_active(ota_active), .commit_ok(ota_commit_ok_pulse),

        .commit_deny(ota_commit_deny_pulse), .status()

    );
    end else begin : g_live_no_ota_policy_demo
        // The live profile removes the historical policy-only OTA block.  Keep
        // every observable status bit fail-closed instead of leaving the
        // removed block's output as an undriven net for synthesis to resolve.
        assign ota_active = 1'b0;
        assign ota_commit_ok_pulse = 1'b0;
        assign ota_commit_deny_pulse = 1'b0;
    end
    endgenerate



    assign enrolled  = puf_enrolled;

    assign verify_ok = session_active;

    assign device_id = puf_device_id;

    assign kyber_done = kyber_done_seen;

    assign kyber_pass = kyber_pass_w;

    assign ota_commit_ok = ota_commit_ok_seen;

    assign ota_commit_deny = ota_commit_deny_seen;

endmodule
