`timescale 1ns / 1ps

module axi_data_memory #(
    parameter AXI_ADDR_WIDTH   = 32,
    parameter AXI_DATA_WIDTH   = 32,
    parameter MEM_SIZE_BYTES   = 256,
    parameter [AXI_ADDR_WIDTH-1:0] BASE_ADDR = 32'h0000_0000
)(
    input  wire                          clk,
    input  wire                          rst,

    // AXI4-Lite Write Address Channel
    input  wire [AXI_ADDR_WIDTH-1:0]     s_axi_awaddr,
    input  wire                          s_axi_awvalid,
    output wire                          s_axi_awready,

    // AXI4-Lite Write Data Channel
    input  wire [AXI_DATA_WIDTH-1:0]     s_axi_wdata,
    input  wire [AXI_DATA_WIDTH/8-1:0]   s_axi_wstrb,
    input  wire                          s_axi_wvalid,
    output wire                          s_axi_wready,

    // AXI4-Lite Write Response Channel
    output reg  [1:0]                    s_axi_bresp,
    output reg                           s_axi_bvalid,
    input  wire                          s_axi_bready,

    // AXI4-Lite Read Address Channel
    input  wire [AXI_ADDR_WIDTH-1:0]     s_axi_araddr,
    input  wire                          s_axi_arvalid,
    output wire                          s_axi_arready,

    // AXI4-Lite Read Data Channel
    output reg  [AXI_DATA_WIDTH-1:0]     s_axi_rdata,
    output reg  [1:0]                    s_axi_rresp,
    output reg                           s_axi_rvalid,
    input  wire                          s_axi_rready
);

    localparam [1:0] AXI_RESP_OKAY   = 2'b00;
    localparam [1:0] AXI_RESP_SLVERR = 2'b10;
    localparam MEM_WORDS = MEM_SIZE_BYTES / 4;

    // 32-bit Word Memory Array
    reg [31:0] memory [0:MEM_WORDS-1];

    // Write Channel Registers
    reg [AXI_ADDR_WIDTH-1:0]   awaddr_reg;
    reg [AXI_DATA_WIDTH-1:0]   wdata_reg;
    reg [AXI_DATA_WIDTH/8-1:0] wstrb_reg;
    reg                        aw_latched;
    reg                        w_latched;

    // Handshake controls
    assign s_axi_awready = !aw_latched && !s_axi_bvalid;
    assign s_axi_wready  = !w_latched  && !s_axi_bvalid;
    assign s_axi_arready = !s_axi_rvalid;

    wire [AXI_ADDR_WIDTH-1:0]   eff_awaddr = aw_latched ? awaddr_reg : s_axi_awaddr;
    wire [AXI_DATA_WIDTH-1:0]   eff_wdata  = w_latched  ? wdata_reg  : s_axi_wdata;
    wire [AXI_DATA_WIDTH/8-1:0] eff_wstrb  = w_latched  ? wstrb_reg  : s_axi_wstrb;

    wire aw_ready_now = (aw_latched || (s_axi_awvalid && s_axi_awready));
    wire w_ready_now  = (w_latched  || (s_axi_wvalid  && s_axi_wready));

    // Address range validation
    wire wr_addr_valid = (eff_awaddr >= BASE_ADDR) &&
                         ((eff_awaddr - BASE_ADDR) < MEM_SIZE_BYTES) &&
                         (eff_awaddr[1:0] == 2'b00);

    wire [31:0] wr_word_idx = (eff_awaddr - BASE_ADDR) >> 2;
    wire        do_write    = aw_ready_now && w_ready_now && !s_axi_bvalid;

    // Integer iterator for simulation initialization
    integer k;
    initial begin
        for (k = 0; k < MEM_WORDS; k = k + 1) begin
            memory[k] = 32'd0;
        end
    end

    // Synchronous Memory Write (Synthesizable Block RAM style)
    always @(posedge clk) begin
        if (do_write && wr_addr_valid) begin
            if (eff_wstrb[0]) memory[wr_word_idx][7:0]   <= eff_wdata[7:0];
            if (eff_wstrb[1]) memory[wr_word_idx][15:8]  <= eff_wdata[15:8];
            if (eff_wstrb[2]) memory[wr_word_idx][23:16] <= eff_wdata[23:16];
            if (eff_wstrb[3]) memory[wr_word_idx][31:24] <= eff_wdata[31:24];
        end
    end

    // Write Control FSM & Buffers
    always @(posedge clk or posedge rst) begin
        if (rst) begin
            awaddr_reg   <= 0;
            wdata_reg    <= 0;
            wstrb_reg    <= 0;
            aw_latched   <= 1'b0;
            w_latched    <= 1'b0;
            s_axi_bvalid <= 1'b0;
            s_axi_bresp  <= AXI_RESP_OKAY;
        end else begin
            // Latch write address if arriving alone
            if (s_axi_awvalid && s_axi_awready && !w_ready_now) begin
                awaddr_reg <= s_axi_awaddr;
                aw_latched <= 1'b1;
            end

            // Latch write data if arriving alone
            if (s_axi_wvalid && s_axi_wready && !aw_ready_now) begin
                wdata_reg <= s_axi_wdata;
                wstrb_reg <= s_axi_wstrb;
                w_latched <= 1'b1;
            end

            // Commit write response once both address and data are ready
            if (do_write) begin
                s_axi_bresp  <= wr_addr_valid ? AXI_RESP_OKAY : AXI_RESP_SLVERR;
                s_axi_bvalid <= 1'b1;
                aw_latched   <= 1'b0;
                w_latched    <= 1'b0;
            end

            // Clear write response upon master acknowledge
            if (s_axi_bvalid && s_axi_bready) begin
                s_axi_bvalid <= 1'b0;
            end
        end
    end

    // Read Logic
    always @(posedge clk or posedge rst) begin
        if (rst) begin
            s_axi_rdata  <= 32'd0;
            s_axi_rresp  <= AXI_RESP_OKAY;
            s_axi_rvalid <= 1'b0;
        end else begin
            if (s_axi_arvalid && s_axi_arready) begin
                if ((s_axi_araddr >= BASE_ADDR) &&
                    ((s_axi_araddr - BASE_ADDR) < MEM_SIZE_BYTES) &&
                    (s_axi_araddr[1:0] == 2'b00)) begin
                    
                    s_axi_rdata  <= memory[(s_axi_araddr - BASE_ADDR) >> 2];
                    s_axi_rresp  <= AXI_RESP_OKAY;
                end else begin
                    s_axi_rdata  <= 32'h0000_0000;
                    s_axi_rresp  <= AXI_RESP_SLVERR;
                end
                s_axi_rvalid <= 1'b1;
            end else if (s_axi_rvalid && s_axi_rready) begin
                s_axi_rvalid <= 1'b0;
            end
        end
    end

endmodule
