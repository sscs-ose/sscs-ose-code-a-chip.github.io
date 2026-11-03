`timescale 1ns / 1ps

module axi_decoder #(
    parameter AXI_ADDR_WIDTH = 32,
    parameter AXI_DATA_WIDTH = 32,

    // Address Map Parameters
    parameter [31:0] DATA_MEM_BASE = 32'h0000_0000,
    parameter [31:0] DATA_MEM_SIZE = 32'h0000_0100, // 256 bytes default
    parameter [31:0] VGA_REG_BASE  = 32'h1000_0000,
    parameter [31:0] VGA_REG_SIZE  = 32'h0000_0020, // 32 bytes (covers up to 0x1000_001F)
    parameter [31:0] FB_BASE       = 32'h5000_0000,
    parameter [31:0] FB_SIZE       = 32'h0012_C000  // 640x480x4 = 1,228,800 bytes
)(
    input  wire                          clk,
    input  wire                          rst,

    // =========================================================================
    // Master Interface (Connected to RV32I CPU AXI4-Lite Master)
    // =========================================================================
    // Write Address Channel
    input  wire [AXI_ADDR_WIDTH-1:0]     m_axi_awaddr,
    input  wire                          m_axi_awvalid,
    output wire                          m_axi_awready,

    // Write Data Channel
    input  wire [AXI_DATA_WIDTH-1:0]     m_axi_wdata,
    input  wire [AXI_DATA_WIDTH/8-1:0]   m_axi_wstrb,
    input  wire                          m_axi_wvalid,
    output wire                          m_axi_wready,

    // Write Response Channel
    output wire [1:0]                    m_axi_bresp,
    output wire                          m_axi_bvalid,
    input  wire                          m_axi_bready,

    // Read Address Channel
    input  wire [AXI_ADDR_WIDTH-1:0]     m_axi_araddr,
    input  wire                          m_axi_arvalid,
    output wire                          m_axi_arready,

    // Read Data Channel
    output wire [AXI_DATA_WIDTH-1:0]     m_axi_rdata,
    output wire [1:0]                    m_axi_rresp,
    output wire                          m_axi_rvalid,
    input  wire                          m_axi_rready,

    // =========================================================================
    // Slave 0 Interface: Data Memory (RAM)
    // =========================================================================
    output wire [AXI_ADDR_WIDTH-1:0]     s0_axi_awaddr,
    output wire                          s0_axi_awvalid,
    input  wire                          s0_axi_awready,

    output wire [AXI_DATA_WIDTH-1:0]     s0_axi_wdata,
    output wire [AXI_DATA_WIDTH/8-1:0]   s0_axi_wstrb,
    output wire                          s0_axi_wvalid,
    input  wire                          s0_axi_wready,

    input  wire [1:0]                    s0_axi_bresp,
    input  wire                          s0_axi_bvalid,
    output wire                          s0_axi_bready,

    output wire [AXI_ADDR_WIDTH-1:0]     s0_axi_araddr,
    output wire                          s0_axi_arvalid,
    input  wire                          s0_axi_arready,

    input  wire [AXI_DATA_WIDTH-1:0]     s0_axi_rdata,
    input  wire [1:0]                    s0_axi_rresp,
    input  wire                          s0_axi_rvalid,
    output wire                          s0_axi_rready,

    // =========================================================================
    // Slave 1 Interface: VGA Subsystem (vga_registers & Framebuffer)
    // =========================================================================
    output wire [AXI_ADDR_WIDTH-1:0]     s1_axi_awaddr,
    output wire                          s1_axi_awvalid,
    input  wire                          s1_axi_awready,

    output wire [AXI_DATA_WIDTH-1:0]     s1_axi_wdata,
    output wire [AXI_DATA_WIDTH/8-1:0]   s1_axi_wstrb,
    output wire                          s1_axi_wvalid,
    input  wire                          s1_axi_wready,

    input  wire [1:0]                    s1_axi_bresp,
    input  wire                          s1_axi_bvalid,
    output wire                          s1_axi_bready,

    output wire [AXI_ADDR_WIDTH-1:0]     s1_axi_araddr,
    output wire                          s1_axi_arvalid,
    input  wire                          s1_axi_arready,

    input  wire [AXI_DATA_WIDTH-1:0]     s1_axi_rdata,
    input  wire [1:0]                    s1_axi_rresp,
    input  wire                          s1_axi_rvalid,
    output wire                          s1_axi_rready
);

    // -------------------------------------------------------------------------
    // AXI Standard Response Codes
    // -------------------------------------------------------------------------
    localparam [1:0] AXI_RESP_OKAY   = 2'b00;
    localparam [1:0] AXI_RESP_SLVERR = 2'b10;

    // -------------------------------------------------------------------------
    // Slave Target Enumeration
    // -------------------------------------------------------------------------
    localparam [1:0] TARGET_UNMAPPED = 2'b00;
    localparam [1:0] TARGET_SLAVE0   = 2'b01;  // Data Memory (RAM)
    localparam [1:0] TARGET_SLAVE1   = 2'b10;  // VGA Subsystem (vga_registers + Framebuffer)

    // -------------------------------------------------------------------------
    // Address Decoding Logic
    // -------------------------------------------------------------------------
    // Region A: Data Memory (DATA_MEM_BASE to DATA_MEM_BASE + DATA_MEM_SIZE - 1)
    // Region B: VGA MMIO Registers (VGA_REG_BASE to VGA_REG_BASE + VGA_REG_SIZE - 1)
    // Region C: Framebuffer CPU Window (FB_BASE to FB_BASE + FB_SIZE - 1)
    function [1:0] decode_address;
        input [31:0] addr;
        begin
            // Slave 0: Data Memory
            if ((addr >= DATA_MEM_BASE) && (addr < DATA_MEM_BASE + DATA_MEM_SIZE)) begin
                decode_address = TARGET_SLAVE0;
            end
            // Slave 1: VGA Subsystem (MMIO Registers + Framebuffer Range)
            else if (((addr >= VGA_REG_BASE) && (addr < VGA_REG_BASE + VGA_REG_SIZE)) ||
                     ((addr >= FB_BASE)      && (addr < FB_BASE + FB_SIZE))) begin
                decode_address = TARGET_SLAVE1;
            end
            // Unmapped Address Space
            else begin
                decode_address = TARGET_UNMAPPED;
            end
        end
    endfunction

    // -------------------------------------------------------------------------
    // Write Channel Buffers & State Machine
    // Handles AW and W channel independence (AW first, W first, or concurrent)
    // -------------------------------------------------------------------------
    reg [AXI_ADDR_WIDTH-1:0]     awaddr_reg;
    reg [AXI_DATA_WIDTH-1:0]     wdata_reg;
    reg [AXI_DATA_WIDTH/8-1:0]   wstrb_reg;
    reg                          aw_latched;
    reg                          w_latched;
    reg [1:0]                    wr_target_owner;

    localparam [2:0] WR_IDLE       = 3'b000;
    localparam [2:0] WR_ROUTE_S1   = 3'b001;
    localparam [2:0] WR_ROUTE_S0   = 3'b010;
    localparam [2:0] WR_WAIT_RESP  = 3'b011;
    localparam [2:0] WR_UNMAPPED   = 3'b100;

    reg [2:0] wr_state;

    // Effective write signals to eliminate 1-cycle latency when arriving together
    wire [AXI_ADDR_WIDTH-1:0]   eff_awaddr = aw_latched ? awaddr_reg : m_axi_awaddr;
    wire [AXI_DATA_WIDTH-1:0]   eff_wdata  = w_latched  ? wdata_reg  : m_axi_wdata;
    wire [AXI_DATA_WIDTH/8-1:0] eff_wstrb  = w_latched  ? wstrb_reg  : m_axi_wstrb;

    wire [1:0] wr_target_dec = decode_address(eff_awaddr);

    // Master AWREADY and WREADY handshake controls
    assign m_axi_awready = (wr_state == WR_IDLE) && !aw_latched;
    assign m_axi_wready  = (wr_state == WR_IDLE) && !w_latched;

    // Slave 0 Write Channels Routing
    reg s0_awvalid_reg, s0_wvalid_reg;
    assign s0_axi_awaddr  = eff_awaddr;
    assign s0_axi_awvalid = (wr_state == WR_ROUTE_S0) ? s0_awvalid_reg : 1'b0;
    assign s0_axi_wdata   = eff_wdata;
    assign s0_axi_wstrb   = eff_wstrb;
    assign s0_axi_wvalid  = (wr_state == WR_ROUTE_S0) ? s0_wvalid_reg  : 1'b0;
    assign s0_axi_bready  = (wr_state == WR_WAIT_RESP && wr_target_owner == TARGET_SLAVE0) ? m_axi_bready : 1'b0;

    // Slave 1 Write Channels Routing
    reg s1_awvalid_reg, s1_wvalid_reg;
    assign s1_axi_awaddr  = eff_awaddr;
    assign s1_axi_awvalid = (wr_state == WR_ROUTE_S1) ? s1_awvalid_reg : 1'b0;
    assign s1_axi_wdata   = eff_wdata;
    assign s1_axi_wstrb   = eff_wstrb;
    assign s1_axi_wvalid  = (wr_state == WR_ROUTE_S1) ? s1_wvalid_reg  : 1'b0;
    assign s1_axi_bready  = (wr_state == WR_WAIT_RESP && wr_target_owner == TARGET_SLAVE1) ? m_axi_bready : 1'b0;

    // Master Write Response Routing
    reg        unmapped_bvalid_reg;
    reg [1:0]  unmapped_bresp_reg;

    assign m_axi_bvalid = (wr_state == WR_WAIT_RESP && wr_target_owner == TARGET_SLAVE1) ? s1_axi_bvalid :
                          (wr_state == WR_WAIT_RESP && wr_target_owner == TARGET_SLAVE0) ? s0_axi_bvalid :
                          (wr_state == WR_UNMAPPED)                                      ? unmapped_bvalid_reg : 1'b0;

    assign m_axi_bresp  = (wr_state == WR_WAIT_RESP && wr_target_owner == TARGET_SLAVE1) ? s1_axi_bresp :
                          (wr_state == WR_WAIT_RESP && wr_target_owner == TARGET_SLAVE0) ? s0_axi_bresp :
                          (wr_state == WR_UNMAPPED)                                      ? unmapped_bresp_reg : AXI_RESP_SLVERR;

    // Write FSM
    always @(posedge clk or posedge rst) begin
        if (rst) begin
            awaddr_reg          <= 0;
            wdata_reg           <= 0;
            wstrb_reg           <= 0;
            aw_latched          <= 1'b0;
            w_latched           <= 1'b0;
            wr_target_owner     <= TARGET_UNMAPPED;
            s0_awvalid_reg      <= 1'b0;
            s0_wvalid_reg       <= 1'b0;
            s1_awvalid_reg      <= 1'b0;
            s1_wvalid_reg       <= 1'b0;
            unmapped_bvalid_reg <= 1'b0;
            unmapped_bresp_reg  <= AXI_RESP_OKAY;
            wr_state            <= WR_IDLE;
        end else begin
            // Latch Master Write Address
            if (m_axi_awvalid && m_axi_awready) begin
                awaddr_reg <= m_axi_awaddr;
                aw_latched <= 1'b1;
            end

            // Latch Master Write Data
            if (m_axi_wvalid && m_axi_wready) begin
                wdata_reg <= m_axi_wdata;
                wstrb_reg <= m_axi_wstrb;
                w_latched <= 1'b1;
            end

            case (wr_state)
                WR_IDLE: begin
                    // Once both AW and W are available (either latched or live handshaking)
                    if ((aw_latched || (m_axi_awvalid && m_axi_awready)) &&
                        (w_latched  || (m_axi_wvalid  && m_axi_wready))) begin
                        
                        wr_target_owner <= wr_target_dec;

                        if (wr_target_dec == TARGET_SLAVE0) begin
                            s0_awvalid_reg <= 1'b1;
                            s0_wvalid_reg  <= 1'b1;
                            wr_state       <= WR_ROUTE_S0;
                        end else if (wr_target_dec == TARGET_SLAVE1) begin
                            s1_awvalid_reg <= 1'b1;
                            s1_wvalid_reg  <= 1'b1;
                            wr_state       <= WR_ROUTE_S1;
                        end else begin
                            // Unmapped Address: Generate AXI SLVERR
                            unmapped_bvalid_reg <= 1'b1;
                            unmapped_bresp_reg  <= AXI_RESP_SLVERR;
                            wr_state            <= WR_UNMAPPED;
                        end
                    end
                end

                WR_ROUTE_S0: begin
                    // Handshake downstream Slave 0 channels independently
                    if (s0_axi_awready && s0_awvalid_reg) begin
                        s0_awvalid_reg <= 1'b0;
                    end
                    if (s0_axi_wready && s0_wvalid_reg) begin
                        s0_wvalid_reg <= 1'b0;
                    end

                    // Once both downstream handshakes complete, wait for response
                    if ((!s0_awvalid_reg || s0_axi_awready) &&
                        (!s0_wvalid_reg  || s0_axi_wready)) begin
                        wr_state <= WR_WAIT_RESP;
                    end
                end

                WR_ROUTE_S1: begin
                    // Handshake downstream Slave 1 channels independently
                    if (s1_axi_awready && s1_awvalid_reg) begin
                        s1_awvalid_reg <= 1'b0;
                    end
                    if (s1_axi_wready && s1_wvalid_reg) begin
                        s1_wvalid_reg <= 1'b0;
                    end

                    // Once both downstream handshakes complete, wait for response
                    if ((!s1_awvalid_reg || s1_axi_awready) &&
                        (!s1_wvalid_reg  || s1_axi_wready)) begin
                        wr_state <= WR_WAIT_RESP;
                    end
                end

                WR_WAIT_RESP: begin
                    // Hold transaction until CPU master completes B handshake
                    if (m_axi_bvalid && m_axi_bready) begin
                        aw_latched <= 1'b0;
                        w_latched  <= 1'b0;
                        wr_state   <= WR_IDLE;
                    end
                end

                WR_UNMAPPED: begin
                    if (unmapped_bvalid_reg && m_axi_bready) begin
                        unmapped_bvalid_reg <= 1'b0;
                        aw_latched          <= 1'b0;
                        w_latched           <= 1'b0;
                        wr_state            <= WR_IDLE;
                    end
                end
            endcase
        end
    end

    // -------------------------------------------------------------------------
    // Read Channel Buffers & State Machine
    // -------------------------------------------------------------------------
    reg [AXI_ADDR_WIDTH-1:0] araddr_reg;
    reg [1:0]                rd_target_owner;

    localparam [2:0] RD_IDLE       = 3'b000;
    localparam [2:0] RD_ROUTE_S1   = 3'b001;
    localparam [2:0] RD_ROUTE_S0   = 3'b010;
    localparam [2:0] RD_WAIT_RESP  = 3'b011;
    localparam [2:0] RD_UNMAPPED   = 3'b100;

    reg [2:0] rd_state;

    wire [1:0] rd_target_dec = decode_address(m_axi_araddr);

    assign m_axi_arready = (rd_state == RD_IDLE);

    // Slave 0 Read Channel Routing
    reg s0_arvalid_reg;
    assign s0_axi_araddr  = araddr_reg;
    assign s0_axi_arvalid = (rd_state == RD_ROUTE_S0) ? s0_arvalid_reg : 1'b0;
    assign s0_axi_rready  = (rd_state == RD_WAIT_RESP && rd_target_owner == TARGET_SLAVE0) ? m_axi_rready : 1'b0;

    // Slave 1 Read Channel Routing
    reg s1_arvalid_reg;
    assign s1_axi_araddr  = araddr_reg;
    assign s1_axi_arvalid = (rd_state == RD_ROUTE_S1) ? s1_arvalid_reg : 1'b0;
    assign s1_axi_rready  = (rd_state == RD_WAIT_RESP && rd_target_owner == TARGET_SLAVE1) ? m_axi_rready : 1'b0;

    // Master Read Data Routing
    reg        unmapped_rvalid_reg;
    reg [1:0]  unmapped_rresp_reg;
    reg [31:0] unmapped_rdata_reg;

    assign m_axi_rvalid = (rd_state == RD_WAIT_RESP && rd_target_owner == TARGET_SLAVE1) ? s1_axi_rvalid :
                          (rd_state == RD_WAIT_RESP && rd_target_owner == TARGET_SLAVE0) ? s0_axi_rvalid :
                          (rd_state == RD_UNMAPPED)                                      ? unmapped_rvalid_reg : 1'b0;

    assign m_axi_rdata  = (rd_state == RD_WAIT_RESP && rd_target_owner == TARGET_SLAVE1) ? s1_axi_rdata :
                          (rd_state == RD_WAIT_RESP && rd_target_owner == TARGET_SLAVE0) ? s0_axi_rdata :
                          (rd_state == RD_UNMAPPED)                                      ? unmapped_rdata_reg : 32'd0;

    assign m_axi_rresp  = (rd_state == RD_WAIT_RESP && rd_target_owner == TARGET_SLAVE1) ? s1_axi_rresp :
                          (rd_state == RD_WAIT_RESP && rd_target_owner == TARGET_SLAVE0) ? s0_axi_rresp :
                          (rd_state == RD_UNMAPPED)                                      ? unmapped_rresp_reg : AXI_RESP_SLVERR;

    // Read FSM
    always @(posedge clk or posedge rst) begin
        if (rst) begin
            araddr_reg          <= 0;
            rd_target_owner     <= TARGET_UNMAPPED;
            s0_arvalid_reg      <= 1'b0;
            s1_arvalid_reg      <= 1'b0;
            unmapped_rvalid_reg <= 1'b0;
            unmapped_rresp_reg  <= AXI_RESP_OKAY;
            unmapped_rdata_reg  <= 32'd0;
            rd_state            <= RD_IDLE;
        end else begin
            case (rd_state)
                RD_IDLE: begin
                    if (m_axi_arvalid && m_axi_arready) begin
                        araddr_reg      <= m_axi_araddr;
                        rd_target_owner <= rd_target_dec;

                        if (rd_target_dec == TARGET_SLAVE0) begin
                            s0_arvalid_reg <= 1'b1;
                            rd_state       <= RD_ROUTE_S0;
                        end else if (rd_target_dec == TARGET_SLAVE1) begin
                            s1_arvalid_reg <= 1'b1;
                            rd_state       <= RD_ROUTE_S1;
                        end else begin
                            // Unmapped Address: Return SLVERR with 0 data
                            unmapped_rvalid_reg <= 1'b1;
                            unmapped_rresp_reg  <= AXI_RESP_SLVERR;
                            unmapped_rdata_reg  <= 32'h0000_0000;
                            rd_state            <= RD_UNMAPPED;
                        end
                    end
                end

                RD_ROUTE_S0: begin
                    if (s0_axi_arready && s0_arvalid_reg) begin
                        s0_arvalid_reg <= 1'b0;
                        rd_state       <= RD_WAIT_RESP;
                    end
                end

                RD_ROUTE_S1: begin
                    if (s1_axi_arready && s1_arvalid_reg) begin
                        s1_arvalid_reg <= 1'b0;
                        rd_state       <= RD_WAIT_RESP;
                    end
                end

                RD_WAIT_RESP: begin
                    // Hold until master completes R handshake
                    if (m_axi_rvalid && m_axi_rready) begin
                        rd_state <= RD_IDLE;
                    end
                end

                RD_UNMAPPED: begin
                    if (unmapped_rvalid_reg && m_axi_rready) begin
                        unmapped_rvalid_reg <= 1'b0;
                        rd_state            <= RD_IDLE;
                    end
                end
            endcase
        end
    end

endmodule
