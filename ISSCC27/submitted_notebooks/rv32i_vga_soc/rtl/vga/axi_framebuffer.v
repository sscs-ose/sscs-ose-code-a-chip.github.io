`timescale 1ns / 1ps

module axi_framebuffer #(
    parameter int AXI_ADDR_WIDTH = 32,
    parameter int AXI_DATA_WIDTH = 32,
    parameter int FB_WIDTH       = 640,
    parameter int FB_HEIGHT      = 480,
    parameter logic [AXI_ADDR_WIDTH-1:0] FB_BASE_ADDR = 32'h5000_0000
)(
    input  logic                          clk,
    input  logic                          resetn,

    // AXI4 Write Address Channel
    input  logic [AXI_ADDR_WIDTH-1:0]     awaddr,
    input  logic                          awvalid,
    output logic                          awready,

    // AXI4 Write Data Channel
    input  logic [AXI_DATA_WIDTH-1:0]     wdata,
    input  logic [AXI_DATA_WIDTH/8-1:0]   wstrb,
    input  logic                          wvalid,
    output logic                          wready,

    // AXI4 Write Response Channel
    output logic [1:0]                    bresp,
    output logic                          bvalid,
    input  logic                          bready,

    // AXI4 Read Address Channel
    input  logic [AXI_ADDR_WIDTH-1:0]     araddr,
    input  logic                          arvalid,
    output logic                          arready,

    // AXI4 Read Data Channel
    output logic [AXI_DATA_WIDTH-1:0]     rdata,
    output logic [1:0]                    rresp,
    output logic                          rvalid,
    input  logic                          rready,

    // VGA Pixel Read Port (21-bit Byte Offset from pixel_addr_gen)
    input  logic [20:0]                   vga_addr,
    output logic [31:0]                   vga_data
);

    localparam int FB_DEPTH      = FB_WIDTH * FB_HEIGHT;       // 307,200 pixels
    localparam int FB_BYTE_SIZE  = FB_DEPTH * 4;               // 1,228,800 bytes
    localparam logic [1:0] AXI_RESP_OKAY   = 2'b00;
    localparam logic [1:0] AXI_RESP_SLVERR = 2'b10;

    // 32-bit Framebuffer memory (00RRGGBB format per pixel)
    logic [31:0] framebuffer [0:FB_DEPTH-1];

    // AXI Write Channel Buffers & Handshake Flags
    logic [AXI_ADDR_WIDTH-1:0]   awaddr_reg;
    logic [AXI_DATA_WIDTH-1:0]   wdata_reg;
    logic [AXI_DATA_WIDTH/8-1:0] wstrb_reg;
    logic                        aw_hold;
    logic                        w_hold;

    // Handshakes ready when not currently holding uncommitted transactions and not stalled on response
    assign awready = !aw_hold && !bvalid;
    assign wready  = !w_hold  && !bvalid;
    assign arready = !rvalid;

    // AXI Slave FSM & Memory Access
    always_ff @(posedge clk) begin
        if (!resetn) begin
            awaddr_reg <= '0;
            wdata_reg  <= '0;
            wstrb_reg  <= '0;
            aw_hold    <= 1'b0;
            w_hold     <= 1'b0;
            bvalid     <= 1'b0;
            bresp      <= AXI_RESP_OKAY;
            rvalid     <= 1'b0;
            rdata      <= '0;
            rresp      <= AXI_RESP_OKAY;
        end else begin
            // ----------------------------------------------------
            // AXI Write Address Capture
            // ----------------------------------------------------
            if (awvalid && awready) begin
                awaddr_reg <= awaddr;
                aw_hold    <= 1'b1;
            end

            // ----------------------------------------------------
            // AXI Write Data Capture
            // ----------------------------------------------------
            if (wvalid && wready) begin
                wdata_reg <= wdata;
                wstrb_reg <= wstrb;
                w_hold    <= 1'b1;
            end

            // ----------------------------------------------------
            // AXI Write Execution (once both AW and W are captured)
            // ----------------------------------------------------
            if (aw_hold && w_hold && !bvalid) begin
                if ((awaddr_reg >= FB_BASE_ADDR) &&
                    ((awaddr_reg - FB_BASE_ADDR) < FB_BYTE_SIZE) &&
                    (awaddr_reg[1:0] == 2'b00)) begin

                    // 4-byte write strobes (Blue, Green, Red, Unused)
                    if (wstrb_reg[0])
                        framebuffer[(awaddr_reg - FB_BASE_ADDR) >> 2][7:0]   <= wdata_reg[7:0];

                    if (wstrb_reg[1])
                        framebuffer[(awaddr_reg - FB_BASE_ADDR) >> 2][15:8]  <= wdata_reg[15:8];

                    if (wstrb_reg[2])
                        framebuffer[(awaddr_reg - FB_BASE_ADDR) >> 2][23:16] <= wdata_reg[23:16];

                    if (wstrb_reg[3])
                        framebuffer[(awaddr_reg - FB_BASE_ADDR) >> 2][31:24] <= wdata_reg[31:24];

                    bresp <= AXI_RESP_OKAY;
                end else begin
                    bresp <= AXI_RESP_SLVERR;
                end

                bvalid  <= 1'b1;
                aw_hold <= 1'b0;
                w_hold  <= 1'b0;
            end

            // Clear write response upon master acknowledge
            if (bvalid && bready) begin
                bvalid <= 1'b0;
            end

            // ----------------------------------------------------
            // AXI Read Channel Handling
            // ----------------------------------------------------
            if (arvalid && arready) begin
                if ((araddr >= FB_BASE_ADDR) &&
                    ((araddr - FB_BASE_ADDR) < FB_BYTE_SIZE) &&
                    (araddr[1:0] == 2'b00)) begin

                    rdata <= framebuffer[(araddr - FB_BASE_ADDR) >> 2];
                    rresp <= AXI_RESP_OKAY;
                end else begin
                    rdata <= 32'b0;
                    rresp <= AXI_RESP_SLVERR;
                end

                rvalid <= 1'b1;
            end

            // Clear read response upon master acknowledge
            if (rvalid && rready) begin
                rvalid <= 1'b0;
            end
        end
    end

    // ----------------------------------------------------
    // VGA Synchronous Pixel Read Port
    // Converts incoming 21-bit byte offset to pixel index
    // ----------------------------------------------------
    always_ff @(posedge clk) begin
        vga_data <= framebuffer[vga_addr[20:2]];
    end

endmodule
