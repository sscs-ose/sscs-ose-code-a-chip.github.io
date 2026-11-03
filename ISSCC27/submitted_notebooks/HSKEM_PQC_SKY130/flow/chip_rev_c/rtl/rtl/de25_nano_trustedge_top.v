// Board wrapper for the Terasic DE25-Nano.
// CLOCK1_50, KEY, SW0, LEDR and GPIO_0 assignments are defined in
// quartus/DE25Nano_TrustEdge.qsf from the DE25-Nano User Manual Rev. B.

module de25_nano_trustedge_top (

    input  wire        CLOCK1_50,
    input  wire [1:0]  KEY,
    input  wire        SW0,
    output wire [7:0]  LEDR,

    input  wire        GPIO_0_CS_N,
    input  wire        GPIO_0_SCK,
    input  wire        GPIO_0_MOSI,
    output wire        GPIO_0_MISO,
    output wire        GPIO_0_IRQ

);

    wire        enrolled;
    wire        verify_ok;
    wire        ota_ok;
    wire        ota_deny;
    wire        kyber_done;
    wire        kyber_pass;
    wire        config_reset;
    wire        external_reset_n;
    wire        core_rst_n;
    wire [31:0] dev_id;
    reg  [1:0]  provision_sync;
    wire        sdm_busy;
    wire        sdm_ready;
    wire [7:0]  sdm_error;
    wire [63:0] sdm_chip_id;
    wire [3:0]  sdm_av_address;
    wire        sdm_av_write;
    wire [31:0] sdm_av_writedata;
    wire        sdm_av_read;
    wire [31:0] sdm_av_readdata;
    wire        sdm_av_readdatavalid;
    wire        sdm_av_waitrequest;
    wire        sdm_mailbox_irq;
    wire [3:0]  crypto_axi_awid;
    wire [31:0] crypto_axi_awaddr;
    wire [7:0]  crypto_axi_awlen;
    wire [2:0]  crypto_axi_awsize;
    wire [1:0]  crypto_axi_awburst;
    wire        crypto_axi_awvalid;
    wire        crypto_axi_awready;
    wire [63:0] crypto_axi_wdata;
    wire        crypto_axi_wlast;
    wire        crypto_axi_wready;
    wire        crypto_axi_wvalid;
    wire [7:0]  crypto_axi_wstrb;
    wire [3:0]  crypto_axi_bid;
    wire [1:0]  crypto_axi_bresp;
    wire        crypto_axi_bvalid;
    wire        crypto_axi_bready;
    wire [63:0] crypto_axi_rdata;
    wire [1:0]  crypto_axi_rresp;
    wire        crypto_axi_rlast;
    wire        crypto_axi_rready;
    wire        crypto_axi_rvalid;
    wire [3:0]  crypto_axi_arid;
    wire [31:0] crypto_axi_araddr;
    wire [7:0]  crypto_axi_arlen;
    wire [2:0]  crypto_axi_arsize;
    wire [1:0]  crypto_axi_arburst;
    wire        crypto_axi_arvalid;
    wire        crypto_axi_arready;
    wire [3:0]  crypto_axi_rid;
    wire        crypto_mem_ready;
    wire [7:0]  crypto_mem_error;
    wire        crypto_zeroize;

    de25_nano_reset_release u_reset_release (
        .config_reset(config_reset)
    );

    // KEY[0] is active-low; config_reset is asserted until Agilex 5 user mode.
    // Assertion is asynchronous, but release is synchronized to CLOCK1_50 so
    // the core does not leave reset on an arbitrary clock edge.
    assign external_reset_n = KEY[0] & ~config_reset;

    de25_nano_reset_sync u_reset_sync (
        .clk         (CLOCK1_50),
        .reset_n_in  (external_reset_n),
        .reset_n_out (core_rst_n)
    );

    // SW0 is active-high. Synchronize physical presence before it reaches
    // vault policy; it is an authorization input, not key material or entropy.
    always @(posedge CLOCK1_50 or negedge core_rst_n) begin
        if (!core_rst_n)
            provision_sync <= 2'b00;
        else
            provision_sync <= {provision_sync[0], SW0};
    end

    // GET_CHIPID remains the only SDM command used without the controlled
    // Cryptographic Services command specification. The official Mailbox IP
    // crypto AXI interface is enabled and backed by a scrubbed 16-KiB RAM,
    // but this alone is not a persistent or device-bound key vault.
    sdm_chipid_client u_sdm_chipid_client (
        .clk(CLOCK1_50),
        .rst_n(core_rst_n),
        .avmm_address(sdm_av_address),
        .avmm_write(sdm_av_write),
        .avmm_writedata(sdm_av_writedata),
        .avmm_read(sdm_av_read),
        .avmm_readdata(sdm_av_readdata),
        .avmm_readdatavalid(sdm_av_readdatavalid),
        .avmm_waitrequest(sdm_av_waitrequest),
        .mailbox_irq(sdm_mailbox_irq),
        .busy(sdm_busy),
        .ready(sdm_ready),
        .error_code(sdm_error),
        .chip_id(sdm_chip_id)
    );

    sdm_crypto_axi_ram #(.ADDR_WIDTH(14)) u_sdm_crypto_memory (
        .clk(CLOCK1_50), .rst_n(core_rst_n), .zeroize(crypto_zeroize),
        .s_axi_awid(crypto_axi_awid), .s_axi_awaddr(crypto_axi_awaddr),
        .s_axi_awlen(crypto_axi_awlen), .s_axi_awsize(crypto_axi_awsize),
        .s_axi_awburst(crypto_axi_awburst), .s_axi_awvalid(crypto_axi_awvalid),
        .s_axi_awready(crypto_axi_awready),
        .s_axi_wdata(crypto_axi_wdata), .s_axi_wstrb(crypto_axi_wstrb),
        .s_axi_wlast(crypto_axi_wlast), .s_axi_wvalid(crypto_axi_wvalid),
        .s_axi_wready(crypto_axi_wready),
        .s_axi_bid(crypto_axi_bid), .s_axi_bresp(crypto_axi_bresp),
        .s_axi_bvalid(crypto_axi_bvalid), .s_axi_bready(crypto_axi_bready),
        .s_axi_arid(crypto_axi_arid), .s_axi_araddr(crypto_axi_araddr),
        .s_axi_arlen(crypto_axi_arlen), .s_axi_arsize(crypto_axi_arsize),
        .s_axi_arburst(crypto_axi_arburst), .s_axi_arvalid(crypto_axi_arvalid),
        .s_axi_arready(crypto_axi_arready),
        .s_axi_rid(crypto_axi_rid), .s_axi_rdata(crypto_axi_rdata),
        .s_axi_rresp(crypto_axi_rresp), .s_axi_rlast(crypto_axi_rlast),
        .s_axi_rvalid(crypto_axi_rvalid), .s_axi_rready(crypto_axi_rready),
        .ready(crypto_mem_ready), .error_code(crypto_mem_error)
    );

`ifdef SYNTHESIS
    de25_sdm_mailbox u_sdm_mailbox (
        .in_clk_clk(CLOCK1_50),
        .in_reset_reset(~core_rst_n),
        .axi_in_clk_clk(CLOCK1_50),
        .axi_in_reset_reset(~core_rst_n),
        .avmm_address(sdm_av_address),
        .avmm_write(sdm_av_write),
        .avmm_writedata(sdm_av_writedata),
        .avmm_read(sdm_av_read),
        .avmm_readdata(sdm_av_readdata),
        .avmm_readdatavalid(sdm_av_readdatavalid),
        .avmm_waitrequest(sdm_av_waitrequest),
        .irq_irq(sdm_mailbox_irq),
        .axi_target_awid(crypto_axi_awid),
        .axi_target_awaddr(crypto_axi_awaddr),
        .axi_target_awlen(crypto_axi_awlen),
        .axi_target_awsize(crypto_axi_awsize),
        .axi_target_awburst(crypto_axi_awburst),
        .axi_target_awvalid(crypto_axi_awvalid),
        .axi_target_awready(crypto_axi_awready),
        .axi_target_wdata(crypto_axi_wdata),
        .axi_target_wlast(crypto_axi_wlast),
        .axi_target_wready(crypto_axi_wready),
        .axi_target_wvalid(crypto_axi_wvalid),
        .axi_target_wstrb(crypto_axi_wstrb),
        .axi_target_bid(crypto_axi_bid),
        .axi_target_bresp(crypto_axi_bresp),
        .axi_target_bvalid(crypto_axi_bvalid),
        .axi_target_bready(crypto_axi_bready),
        .axi_target_rdata(crypto_axi_rdata),
        .axi_target_rresp(crypto_axi_rresp),
        .axi_target_rlast(crypto_axi_rlast),
        .axi_target_rready(crypto_axi_rready),
        .axi_target_rvalid(crypto_axi_rvalid),
        .axi_target_arid(crypto_axi_arid),
        .axi_target_araddr(crypto_axi_araddr),
        .axi_target_arlen(crypto_axi_arlen),
        .axi_target_arsize(crypto_axi_arsize),
        .axi_target_arburst(crypto_axi_arburst),
        .axi_target_arvalid(crypto_axi_arvalid),
        .axi_target_arready(crypto_axi_arready),
        .axi_target_rid(crypto_axi_rid)
    );
`else
    // Minimal protocol model for wrapper simulation. The controller has a
    // separate testbench for timeout and malformed-response coverage.
    reg [31:0] sim_sdm_readdata;
    reg        sim_sdm_readdatavalid;
    reg [1:0]  sim_sdm_response_index;
    reg [2:0]  sim_sdm_response_words;

    assign sdm_av_readdata      = sim_sdm_readdata;
    assign sdm_av_readdatavalid = sim_sdm_readdatavalid;
    assign sdm_av_waitrequest   = 1'b0;
    // IER resets to zero in the real IP, so IRQ remains low. The controller
    // must follow the documented ISR polling path rather than depend on IRQ.
    assign sdm_mailbox_irq      = 1'b0;
    assign crypto_axi_awid      = 4'd0;
    assign crypto_axi_awaddr    = 32'd0;
    assign crypto_axi_awlen     = 8'd0;
    assign crypto_axi_awsize    = 3'd3;
    assign crypto_axi_awburst   = 2'b01;
    assign crypto_axi_awvalid   = 1'b0;
    assign crypto_axi_wdata     = 64'd0;
    assign crypto_axi_wlast     = 1'b0;
    assign crypto_axi_wvalid    = 1'b0;
    assign crypto_axi_wstrb     = 8'd0;
    assign crypto_axi_bready    = 1'b0;
    assign crypto_axi_rready    = 1'b0;
    assign crypto_axi_arid      = 4'd0;
    assign crypto_axi_araddr    = 32'd0;
    assign crypto_axi_arlen     = 8'd0;
    assign crypto_axi_arsize    = 3'd3;
    assign crypto_axi_arburst   = 2'b01;
    assign crypto_axi_arvalid   = 1'b0;

    always @(posedge CLOCK1_50 or negedge core_rst_n) begin
        if (!core_rst_n) begin
            sim_sdm_readdata       <= 32'd0;
            sim_sdm_readdatavalid  <= 1'b0;
            sim_sdm_response_index <= 2'd0;
            sim_sdm_response_words <= 3'd0;
        end else begin
            sim_sdm_readdatavalid <= 1'b0;
            if (sdm_av_write && sdm_av_address == 4'd1 &&
                sdm_av_writedata == 32'h0100_0012) begin
                sim_sdm_response_index <= 2'd0;
                sim_sdm_response_words <= 3'd3;
            end
            if (sdm_av_read && sdm_av_address == 4'd2) begin
                sim_sdm_readdata      <= 32'd4;
                sim_sdm_readdatavalid <= 1'b1;
            end else if (sdm_av_read && sdm_av_address == 4'd8) begin
                sim_sdm_readdata      <= {31'd0, (sim_sdm_response_words != 0)};
                sim_sdm_readdatavalid <= 1'b1;
            end else if (sdm_av_read && sdm_av_address == 4'd6) begin
                case (sim_sdm_response_index)
                    2'd0: sim_sdm_readdata <= 32'h0000_000D; // fill=3, SOP
                    2'd1: sim_sdm_readdata <= 32'h0000_0008; // fill=2
                    default: sim_sdm_readdata <= 32'h0000_0006; // fill=1, EOP
                endcase
                sim_sdm_readdatavalid <= 1'b1;
            end else if (sdm_av_read && sdm_av_address == 4'd5) begin
                case (sim_sdm_response_index)
                    2'd0: sim_sdm_readdata <= 32'h0100_2000;
                    2'd1: sim_sdm_readdata <= 32'h89AB_CDEF;
                    default: sim_sdm_readdata <= 32'h0123_4567;
                endcase
                sim_sdm_readdatavalid  <= 1'b1;
                sim_sdm_response_index <= sim_sdm_response_index + 2'd1;
                if (sim_sdm_response_words != 3'd0)
                    sim_sdm_response_words <= sim_sdm_response_words - 3'd1;
            end
        end
    end
`endif

`ifdef TRUSTEDGE_QUALIFICATION_SOF
    localparam C4_DEMO_RELEASE_PROFILE = 1'b0;
    localparam C5_STATIC_AUTH_PROFILE = 1'b1;
    localparam C5_OTA_POLICY_PROFILE = 1'b1;
`else
    localparam C4_DEMO_RELEASE_PROFILE = 1'b1;
    localparam C5_STATIC_AUTH_PROFILE = 1'b0;
    localparam C5_OTA_POLICY_PROFILE = 1'b0;
`endif

    trustedge_top #(
        .MLKEM_QUALIFICATION_PROFILE(1'b0),
        .ENABLE_INTERNAL_ENTROPY(1'b1),
        .DEMO_RELEASE_PROFILE(C4_DEMO_RELEASE_PROFILE),
        .ENABLE_PUF_ROOT_VAULT(1'b1),
        .ENABLE_STATIC_AUTH_PROVISION(C5_STATIC_AUTH_PROFILE),
        .ENABLE_OTA_POLICY_DEMO(C5_OTA_POLICY_PROFILE)
    ) u_core (
        .clk             (CLOCK1_50),
        .rst_n           (core_rst_n),
        .spi_cs_n        (GPIO_0_CS_N),
        .spi_sck         (GPIO_0_SCK),
        .spi_mosi        (GPIO_0_MOSI),
        .spi_miso        (GPIO_0_MISO),
        .spi_irq         (GPIO_0_IRQ),
        .sig_valid       (1'b1),
        .provision_enable(provision_sync[1]),
        .sdm_transport_ready(sdm_ready),
        .sdm_transport_error(sdm_error),
        .sdm_chip_id     (sdm_chip_id),
        .sdm_crypto_enabled(1'b1),
        .sdm_crypto_mem_ready(crypto_mem_ready),
        .sdm_crypto_mem_error(crypto_mem_error),
        .crypto_zeroize  (crypto_zeroize),
        .ota_commit_ok   (ota_ok),
        .ota_commit_deny (ota_deny),
        .enrolled        (enrolled),
        .verify_ok       (verify_ok),
        .device_id       (dev_id),
        .kyber_done      (kyber_done),
        .kyber_pass      (kyber_pass)
    );

    // DE25-Nano FPGA LEDs are active-low: a logic 0 turns an LED on.
    assign LEDR[0] = ~enrolled;
    assign LEDR[1] = ~verify_ok;
    assign LEDR[2] = ~ota_ok;
    assign LEDR[3] = ~ota_deny;
    assign LEDR[4] = ~kyber_done;
    assign LEDR[5] = ~kyber_pass;
    assign LEDR[6] = ~GPIO_0_IRQ;
    // SW0 remains visible on active-low LEDR7 while authorizing vault lifecycle.
    assign LEDR[7] = ~SW0;

endmodule
