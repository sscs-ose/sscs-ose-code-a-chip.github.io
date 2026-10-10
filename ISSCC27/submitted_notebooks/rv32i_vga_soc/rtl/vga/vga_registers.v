`timescale 1ns / 1ps

module vga_registers #(
    parameter AXI_ADDR_WIDTH       = 32,
    parameter AXI_DATA_WIDTH       = 32,
    parameter FB_WIDTH_DEFAULT     = 640,
    parameter FB_HEIGHT_DEFAULT    = 480,
    parameter [AXI_ADDR_WIDTH-1:0] FB_BASE_DEFAULT = 32'h5000_0000
)(
    input  wire                          clk,
    input  wire                          rst,        // Active-high reset
    input  wire [3:0]                    btn,        // Pushbuttons (btn[0..3])
    input  wire [3:0]                    sw,         // Slide switches (sw[0..3])

    // =========================================================================
    // AXI4-Lite Slave Interface (CPU Side)
    // =========================================================================
    // Write Address Channel
    input  wire [AXI_ADDR_WIDTH-1:0]     s_axi_awaddr,
    input  wire                          s_axi_awvalid,
    output reg                           s_axi_awready,

    // Write Data Channel
    input  wire [AXI_DATA_WIDTH-1:0]     s_axi_wdata,
    input  wire [AXI_DATA_WIDTH/8-1:0]   s_axi_wstrb,
    input  wire                          s_axi_wvalid,
    output reg                           s_axi_wready,

    // Write Response Channel
    output reg  [1:0]                    s_axi_bresp,
    output reg                           s_axi_bvalid,
    input  wire                          s_axi_bready,

    // Read Address Channel
    input  wire [AXI_ADDR_WIDTH-1:0]     s_axi_araddr,
    input  wire                          s_axi_arvalid,
    output reg                           s_axi_arready,

    // Read Data Channel
    output reg  [AXI_DATA_WIDTH-1:0]     s_axi_rdata,
    output reg  [1:0]                    s_axi_rresp,
    output reg                           s_axi_rvalid,
    input  wire                          s_axi_rready,

    // =========================================================================
    // VGA Controller Interface (Internal Sideband)
    // =========================================================================
    input  wire                          vga_fb_req,      // VGA requests pixel read
    input  wire [20:0]                   vga_fb_addr,     // VGA pixel byte address
    input  wire                          vga_video_on,    // Active video status
    output wire                          display_enable,  // Driven from VGA_CTRL[0]

    // =========================================================================
    // Single-Port Framebuffer SRAM Control Interface
    // =========================================================================
    output reg  [18:0]                   fb_addr,         // 19-bit word index (307,200 words)
    output reg  [31:0]                   fb_wdata,        // 32-bit pixel write data
    output reg  [3:0]                    fb_we,           // Byte write enable (active high)
    output reg                           fb_en,           // SRAM chip enable
    input  wire [31:0]                   fb_rdata         // Synchronous SRAM read data
);

    // -------------------------------------------------------------------------
    // Constants & Register Offsets
    // -------------------------------------------------------------------------
    localparam [1:0] AXI_RESP_OKAY   = 2'b00;
    localparam [1:0] AXI_RESP_SLVERR = 2'b10;

    localparam [31:0] ADDR_VGA_CTRL   = 32'h1000_0000;
    localparam [31:0] ADDR_VGA_STATUS = 32'h1000_0004;
    localparam [31:0] ADDR_FB_BASE    = 32'h1000_0008;
    localparam [31:0] ADDR_FB_SIZE    = 32'h1000_000C;
    localparam [31:0] ADDR_INPUTS     = 32'h1000_0010; // Read-Only: [3:0]=btn, [7:4]=sw

    localparam FB_MAX_WORDS = FB_WIDTH_DEFAULT * FB_HEIGHT_DEFAULT; // 307,200 words
    localparam FB_MAX_BYTES = FB_MAX_WORDS * 4;                     // 1,228,800 bytes

    // -------------------------------------------------------------------------
    // 1. Memory-Mapped VGA Registers
    // -------------------------------------------------------------------------
    reg [31:0] reg_vga_ctrl;  // [0]: display_enable (RW)
    // FB_BASE is fixed and Read-Only: always returns FB_BASE_DEFAULT (32'h5000_0000)
    wire [31:0] reg_fb_base = FB_BASE_DEFAULT;
    reg [31:0] reg_fb_size;   // [15:0]: width (640), [31:16]: height (480) (RW)

    assign display_enable = reg_vga_ctrl[0];

    // Status: bit 0 = video_on, bit 1 = fb_busy, [5:2] = btn, [9:6] = sw
    wire fb_busy = vga_fb_req;
    wire [31:0] reg_vga_status = {22'd0, sw, btn, fb_busy, vga_video_on};

    // -------------------------------------------------------------------------
    // 2. AXI Write State Machine & Latched Buffers
    // -------------------------------------------------------------------------
    reg [AXI_ADDR_WIDTH-1:0]     awaddr_buf;
    reg [AXI_DATA_WIDTH-1:0]     wdata_buf;
    reg [AXI_DATA_WIDTH/8-1:0]   wstrb_buf;
    reg                          aw_latched;
    reg                          w_latched;

    localparam [1:0] W_IDLE   = 2'b00;
    localparam [1:0] W_FB_REQ = 2'b01;
    localparam [1:0] W_RESP   = 2'b10;

    reg [1:0] wr_state;

    // -------------------------------------------------------------------------
    // 3. AXI Read State Machine & Latched Buffers
    // -------------------------------------------------------------------------
    reg [AXI_ADDR_WIDTH-1:0] araddr_buf;

    localparam [1:0] R_IDLE   = 2'b00;
    localparam [1:0] R_FB_REQ = 2'b01;
    localparam [1:0] R_FB_WAIT= 2'b10;
    localparam [1:0] R_RESP   = 2'b11;

    reg [1:0] rd_state;

    // -------------------------------------------------------------------------
    // 4. Address Decoding Helper Functions
    // -------------------------------------------------------------------------
    function is_reg_addr;
        input [31:0] addr;
        begin
            is_reg_addr = (addr == ADDR_VGA_CTRL   ||
                           addr == ADDR_VGA_STATUS ||
                           addr == ADDR_FB_BASE    ||
                           addr == ADDR_FB_SIZE    ||
                           addr == ADDR_INPUTS);
        end
    endfunction

    function is_fb_addr;
        input [31:0] addr;
        begin
            is_fb_addr = ((addr >= FB_BASE_DEFAULT) &&
                          ((addr - FB_BASE_DEFAULT) < FB_MAX_BYTES) &&
                          (addr[1:0] == 2'b00));
        end
    endfunction

    // Effective write signals to prevent stale buffer access
    wire [AXI_ADDR_WIDTH-1:0] eff_awaddr = aw_latched ? awaddr_buf : s_axi_awaddr;
    wire [AXI_DATA_WIDTH-1:0] eff_wdata  = w_latched  ? wdata_buf  : s_axi_wdata;
    wire [3:0]                eff_wstrb  = w_latched  ? wstrb_buf  : s_axi_wstrb;

    // -------------------------------------------------------------------------
    // 5. Mutually-Exclusive Framebuffer Port Grants
    // Priorities:
    //  1. VGA Display Read (vga_fb_req)
    //  2. CPU Read (rd_state == R_FB_REQ)
    //  3. CPU Write (wr_state == W_FB_REQ)
    // -------------------------------------------------------------------------
    wire grant_vga      = vga_fb_req;
    wire grant_cpu_rd   = !grant_vga && (rd_state == R_FB_REQ);
    wire grant_cpu_wr   = !grant_vga && !grant_cpu_rd && (wr_state == W_FB_REQ);

    // Single-Port SRAM Control Multiplexing (Fixed Base Address 32'h5000_0000)
    always @(*) begin
        if (grant_vga) begin
            fb_en    = 1'b1;
            fb_we    = 4'b0000;
            fb_addr  = vga_fb_addr[20:2];
            fb_wdata = 32'd0;
        end else if (grant_cpu_rd) begin
            fb_en    = 1'b1;
            fb_we    = 4'b0000;
            fb_addr  = (araddr_buf - FB_BASE_DEFAULT) >> 2;
            fb_wdata = 32'd0;
        end else if (grant_cpu_wr) begin
            fb_en    = 1'b1;
            fb_we    = wstrb_buf;
            fb_addr  = (awaddr_buf - FB_BASE_DEFAULT) >> 2;
            fb_wdata = wdata_buf;
        end else begin
            fb_en    = 1'b0;
            fb_we    = 4'b0000;
            fb_addr  = 19'd0;
            fb_wdata = 32'd0;
        end
    end

    // -------------------------------------------------------------------------
    // 6. AXI Write Channel FSM
    // -------------------------------------------------------------------------
    always @(posedge clk or posedge rst) begin
        if (rst) begin
            s_axi_awready <= 1'b1;
            s_axi_wready  <= 1'b1;
            s_axi_bvalid  <= 1'b0;
            s_axi_bresp   <= AXI_RESP_OKAY;
            aw_latched    <= 1'b0;
            w_latched     <= 1'b0;
            awaddr_buf    <= 0;
            wdata_buf     <= 0;
            wstrb_buf     <= 0;
            wr_state      <= W_IDLE;

            reg_vga_ctrl  <= 32'd0;
            reg_fb_size   <= {16'd480, 16'd640};
        end else begin
            // Latch Write Address
            if (s_axi_awvalid && s_axi_awready) begin
                awaddr_buf    <= s_axi_awaddr;
                aw_latched    <= 1'b1;
                s_axi_awready <= 1'b0;
            end

            // Latch Write Data
            if (s_axi_wvalid && s_axi_wready) begin
                wdata_buf    <= s_axi_wdata;
                wstrb_buf    <= s_axi_wstrb;
                w_latched    <= 1'b1;
                s_axi_wready <= 1'b0;
            end

            case (wr_state)
                W_IDLE: begin
                    // When both address and data are presented or buffered
                    if ((aw_latched || (s_axi_awvalid && s_axi_awready)) &&
                        (w_latched  || (s_axi_wvalid  && s_axi_wready))) begin
                        
                        if (is_reg_addr(eff_awaddr)) begin
                            if (eff_awaddr == ADDR_VGA_CTRL) begin
                                if (eff_wstrb[0]) reg_vga_ctrl[7:0]   <= eff_wdata[7:0];
                                if (eff_wstrb[1]) reg_vga_ctrl[15:8]  <= eff_wdata[15:8];
                                if (eff_wstrb[2]) reg_vga_ctrl[23:16] <= eff_wdata[23:16];
                                if (eff_wstrb[3]) reg_vga_ctrl[31:24] <= eff_wdata[31:24];
                                s_axi_bresp  <= AXI_RESP_OKAY;
                            end else if (eff_awaddr == ADDR_FB_BASE) begin
                                // FB_BASE is Read-Only: writes safely ignored, returns OKAY
                                s_axi_bresp  <= AXI_RESP_OKAY;
                            end else if (eff_awaddr == ADDR_FB_SIZE) begin
                                if (eff_wstrb[0]) reg_fb_size[7:0]   <= eff_wdata[7:0];
                                if (eff_wstrb[1]) reg_fb_size[15:8]  <= eff_wdata[15:8];
                                if (eff_wstrb[2]) reg_fb_size[23:16] <= eff_wdata[23:16];
                                if (eff_wstrb[3]) reg_fb_size[31:24] <= eff_wdata[31:24];
                                s_axi_bresp  <= AXI_RESP_OKAY;
                            end else begin
                                // VGA_STATUS is Read-Only: writes safely ignored, returns OKAY
                                s_axi_bresp  <= AXI_RESP_OKAY;
                            end
                            s_axi_bvalid <= 1'b1;
                            wr_state     <= W_RESP;
                        end else if (is_fb_addr(eff_awaddr)) begin
                            wr_state <= W_FB_REQ;
                        end else begin
                            // Invalid Address or unaligned framebuffer address
                            s_axi_bresp  <= AXI_RESP_SLVERR;
                            s_axi_bvalid <= 1'b1;
                            wr_state     <= W_RESP;
                        end
                    end
                end

                W_FB_REQ: begin
                    // Progresses only when real CPU Write grant is active
                    if (grant_cpu_wr) begin
                        s_axi_bresp  <= AXI_RESP_OKAY;
                        s_axi_bvalid <= 1'b1;
                        wr_state     <= W_RESP;
                    end
                end

                W_RESP: begin
                    if (s_axi_bvalid && s_axi_bready) begin
                        s_axi_bvalid  <= 1'b0;
                        aw_latched    <= 1'b0;
                        w_latched     <= 1'b0;
                        s_axi_awready <= 1'b1;
                        s_axi_wready  <= 1'b1;
                        wr_state      <= W_IDLE;
                    end
                end
            endcase
        end
    end

    // -------------------------------------------------------------------------
    // 7. AXI Read Channel FSM
    // -------------------------------------------------------------------------
    always @(posedge clk or posedge rst) begin
        if (rst) begin
            s_axi_arready <= 1'b1;
            s_axi_rvalid  <= 1'b0;
            s_axi_rdata   <= 0;
            s_axi_rresp   <= AXI_RESP_OKAY;
            araddr_buf    <= 0;
            rd_state      <= R_IDLE;
        end else begin
            case (rd_state)
                R_IDLE: begin
                    if (s_axi_arvalid && s_axi_arready) begin
                        araddr_buf    <= s_axi_araddr;
                        s_axi_arready <= 1'b0;

                        if (is_reg_addr(s_axi_araddr)) begin
                            case (s_axi_araddr)
                                ADDR_VGA_CTRL:   s_axi_rdata <= reg_vga_ctrl;
                                ADDR_VGA_STATUS: s_axi_rdata <= reg_vga_status;
                                ADDR_FB_BASE:    s_axi_rdata <= reg_fb_base; // Returns fixed 32'h5000_0000
                                ADDR_FB_SIZE:    s_axi_rdata <= reg_fb_size;
                                ADDR_INPUTS:     s_axi_rdata <= {24'd0, sw, btn};
                                default:         s_axi_rdata <= 32'd0;
                            endcase
                            s_axi_rresp  <= AXI_RESP_OKAY;
                            s_axi_rvalid <= 1'b1;
                            rd_state     <= R_RESP;
                        end else if (is_fb_addr(s_axi_araddr)) begin
                            rd_state <= R_FB_REQ;
                        end else begin
                            // Invalid Address or unaligned framebuffer address
                            s_axi_rdata  <= 32'd0;
                            s_axi_rresp  <= AXI_RESP_SLVERR;
                            s_axi_rvalid <= 1'b1;
                            rd_state     <= R_RESP;
                        end
                    end
                end

                R_FB_REQ: begin
                    // Progresses only when real CPU Read grant is achieved
                    if (grant_cpu_rd) begin
                        rd_state <= R_FB_WAIT;
                    end
                end

                R_FB_WAIT: begin
                    s_axi_rdata  <= fb_rdata;
                    s_axi_rresp  <= AXI_RESP_OKAY;
                    s_axi_rvalid <= 1'b1;
                    rd_state     <= R_RESP;
                end

                R_RESP: begin
                    if (s_axi_rvalid && s_axi_rready) begin
                        s_axi_rvalid  <= 1'b0;
                        s_axi_arready <= 1'b1;
                        rd_state      <= R_IDLE;
                    end
                end
            endcase
        end
    end

endmodule
