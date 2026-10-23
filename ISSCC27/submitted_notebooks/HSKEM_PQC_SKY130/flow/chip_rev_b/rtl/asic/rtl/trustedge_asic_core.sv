// ASIC-V0 functional wrapper. It preserves the live C5/C6 TrustEdge profile
// while replacing board/Intel services with technology-neutral ports.
module trustedge_asic_core #(
    parameter bit ASIC_KECCAK_SERIAL_ROUND = 1'b1,
    parameter bit ASIC_RESET_BRANCHES = 1'b1,
    parameter bit ASIC_SHA256_SLIDING_SCHEDULE = 1'b1,
    parameter bit ASIC_REGISTERED_SOFT_RESET = 1'b1
) (
    input  wire        clk_i,
    input  wire        rst_ni,
    input  wire        spi_cs_ni,
    input  wire        spi_sck_i,
    input  wire        spi_mosi_i,
    output wire        spi_miso_o,
    output wire        spi_irq_o,
    input  wire        sig_valid_i,
    input  wire        provision_enable_i,
    input  wire        platform_ready_i,
    input  wire [7:0]  platform_error_i,
    input  wire [63:0] platform_id_i,
    input  wire        crypto_backend_enabled_i,
    input  wire        crypto_backend_ready_i,
    input  wire [7:0]  crypto_backend_error_i,
    output wire        crypto_backend_zeroize_o,
    output wire        enrolled_o,
    output wire        verify_ok_o,
    output wire [31:0] device_id_o,
    output wire        mlkem_done_o,
    output wire        mlkem_pass_o
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
    wire unused_ota_ok;
    wire unused_ota_deny;
    wire core_rst_n;

    // Reset-domain crossing boundary for the ASIC core.  Assertion remains
    // asynchronous so every state element is forced inactive immediately;
    // release is observed only after two clean clk_i edges.  The raw rst_ni
    // port must not drive any common-core reset pin directly.
    trustedge_asic_reset_sync u_reset_sync (
        .clk_i(clk_i),
        .rst_ni(rst_ni),
        .rst_no(core_rst_n)
    );

    trustedge_top #(
        .MLKEM_QUALIFICATION_PROFILE(1'b0),
        .ENABLE_INTERNAL_ENTROPY(1'b1),
        .DEMO_RELEASE_PROFILE(1'b1),
        .ENABLE_PUF_ROOT_VAULT(1'b1),
        .ASIC_KECCAK_SERIAL_ROUND(ASIC_KECCAK_SERIAL_ROUND),
        .ASIC_SHA256_SLIDING_SCHEDULE(ASIC_SHA256_SLIDING_SCHEDULE),
        .ASIC_RESET_BRANCHES(ASIC_RESET_BRANCHES),
        .ASIC_REGISTERED_SOFT_RESET(ASIC_REGISTERED_SOFT_RESET),
        .ENABLE_STATIC_AUTH_PROVISION(1'b0),
        .ENABLE_OTA_POLICY_DEMO(1'b0)
    ) u_common (
        .clk(clk_i), .rst_n(core_rst_n),
        .spi_cs_n(spi_cs_ni), .spi_sck(spi_sck_i),
        .spi_mosi(spi_mosi_i), .spi_miso(spi_miso_o),
        .spi_irq(spi_irq_o), .sig_valid(sig_valid_i),
        .provision_enable(provision_enable_i),
        .sdm_transport_ready(platform_ready_i),
        .sdm_transport_error(platform_error_i),
        .sdm_chip_id(platform_id_i),
        .sdm_crypto_enabled(crypto_backend_enabled_i),
        .sdm_crypto_mem_ready(crypto_backend_ready_i),
        .sdm_crypto_mem_error(crypto_backend_error_i),
        .crypto_zeroize(crypto_backend_zeroize_o),
        .ota_commit_ok(unused_ota_ok),
        .ota_commit_deny(unused_ota_deny),
        .enrolled(enrolled_o), .verify_ok(verify_ok_o),
        .device_id(device_id_o),
        .kyber_done(mlkem_done_o), .kyber_pass(mlkem_pass_o)
`ifdef TRUSTEDGE_ASIC_SERVICE_PORTS
        ,
        .session_sample_start_o(session_sample_start_o),
        .session_sample_challenge_o(session_sample_challenge_o),
        .session_sample_busy_i(session_sample_busy_i),
        .session_sample_done_i(session_sample_done_i),
        .session_sample_response_i(session_sample_response_i),
        .entropy_enable_o(entropy_enable_o),
        .entropy_clear_health_o(entropy_clear_health_o),
        .entropy_valid_i(entropy_valid_i),
        .entropy_data_i(entropy_data_i),
        .entropy_ready_i(entropy_ready_i),
        .entropy_unhealthy_i(entropy_unhealthy_i),
        .entropy_health_code_i(entropy_health_code_i),
        .entropy_raw_sample_count_i(entropy_raw_sample_count_i),
        .entropy_word_count_i(entropy_word_count_i),
        .root_puf_scrub_o(root_puf_scrub_o),
        .root_puf_start_o(root_puf_start_o),
        .root_puf_bank_id_o(root_puf_bank_id_o),
        .root_puf_private_mode_o(root_puf_private_mode_o),
        .root_puf_busy_i(root_puf_busy_i),
        .root_puf_done_i(root_puf_done_i),
        .root_puf_response_i(root_puf_response_i),
        .root_puf_min_delta_i(root_puf_min_delta_i),
        .root_puf_max_delta_i(root_puf_max_delta_i),
        .root_puf_health_i(root_puf_health_i),
        .root_puf_cycles_i(root_puf_cycles_i),
        .root_puf_physical_i(root_puf_physical_i)
`endif
    );
endmodule

// Async-assert/sync-deassert reset synchronizer.  Keep this module in the ASIC
// shell: the FPGA wrapper has its own device-configuration reset boundary.
module trustedge_asic_reset_sync (
    input  wire clk_i,
    input  wire rst_ni,
    output wire rst_no
);
    (* ASYNC_REG = "TRUE" *) reg [1:0] release_ff;

    always @(posedge clk_i or negedge rst_ni) begin
        if (!rst_ni)
            release_ff <= 2'b00;
        else
            release_ff <= {release_ff[0], 1'b1};
    end

    assign rst_no = release_ff[1];
endmodule
