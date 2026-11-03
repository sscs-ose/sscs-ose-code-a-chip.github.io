`timescale 1ns / 1ps

module soc_top #(
    parameter AXI_ADDR_WIDTH   = 32,
    parameter AXI_DATA_WIDTH   = 32,
    parameter FB_WIDTH         = 640,
    parameter FB_HEIGHT        = 480,
    parameter [31:0] DATA_MEM_BASE = 32'h0000_0000,
    parameter [31:0] DATA_MEM_SIZE = 32'h0000_0100, // 256 bytes
    parameter [31:0] VGA_REG_BASE  = 32'h1000_0000,
    parameter [31:0] VGA_REG_SIZE  = 32'h0000_0020, // 32 bytes (covers up to 0x1000_001F)
    parameter [31:0] FB_BASE       = 32'h5000_0000,
    parameter [31:0] FB_SIZE       = 32'h0012_C000, // 640x480x4 bytes
    parameter        PIXEL_SCALE   = 1              // 1: native 640x480, 4: 160x120 (4x pixel replication)
)(
    input  wire        clk,
    input  wire        reset,
    input  wire [3:0]  btn,
    input  wire [3:0]  sw,

    // Physical VGA Output Pins
    output wire        Hsync,
    output wire        Vsync,
    output wire [7:0]  red,
    output wire [7:0]  green,
    output wire [7:0]  blue,

    // Debug & Observability Outputs
    output wire [31:0] pcRegister,
    output wire [31:0] mem_addr,
    output wire [31:0] mem_wdata,
    output wire        mem_write,
    output wire        mem_read,
    output wire        cpu_stall,
    output wire        display_enable
);

    // 1. CPU Datapath & Memory Interface
    wire [31:0] cpu_mem_addr;
    wire [31:0] cpu_mem_wdata;
    wire        cpu_mem_write;
    wire        cpu_mem_read;
    wire [31:0] cpu_mem_rdata;

    assign mem_addr  = cpu_mem_addr;
    assign mem_wdata = cpu_mem_wdata;
    assign mem_write = cpu_mem_write;
    assign mem_read  = cpu_mem_read;

    Datapath u_cpu_datapath (
        .clk        (clk),
        .reset      (reset),
        .stall      (cpu_stall),
        .mem_rdata  (cpu_mem_rdata),
        .pcRegister (pcRegister),
        .mem_addr   (cpu_mem_addr),
        .mem_wdata  (cpu_mem_wdata),
        .mem_write  (cpu_mem_write),
        .mem_read   (cpu_mem_read)
    );

    // 2. RV32I to AXI4-Lite Master Bridge
    wire [AXI_ADDR_WIDTH-1:0]   m_axi_awaddr;
    wire                        m_axi_awvalid;
    wire                        m_axi_awready;
    wire [AXI_DATA_WIDTH-1:0]   m_axi_wdata;
    wire [AXI_DATA_WIDTH/8-1:0] m_axi_wstrb;
    wire                        m_axi_wvalid;
    wire                        m_axi_wready;
    wire [1:0]                  m_axi_bresp;
    wire                        m_axi_bvalid;
    wire                        m_axi_bready;
    wire [AXI_ADDR_WIDTH-1:0]   m_axi_araddr;
    wire                        m_axi_arvalid;
    wire                        m_axi_arready;
    wire [AXI_DATA_WIDTH-1:0]   m_axi_rdata;
    wire [1:0]                  m_axi_rresp;
    wire                        m_axi_rvalid;
    wire                        m_axi_rready;

    rv32i_axi_bridge #(
        .AXI_ADDR_WIDTH(AXI_ADDR_WIDTH),
        .AXI_DATA_WIDTH(AXI_DATA_WIDTH)
    ) u_axi_bridge (
        .clk           (clk),
        .rst           (reset),

        .cpu_mem_addr  (cpu_mem_addr),
        .cpu_mem_wdata (cpu_mem_wdata),
        .cpu_mem_write (cpu_mem_write),
        .cpu_mem_read  (cpu_mem_read),
        .cpu_mem_rdata (cpu_mem_rdata),
        .cpu_stall     (cpu_stall),

        .m_axi_awaddr  (m_axi_awaddr),
        .m_axi_awvalid (m_axi_awvalid),
        .m_axi_awready (m_axi_awready),
        .m_axi_wdata   (m_axi_wdata),
        .m_axi_wstrb   (m_axi_wstrb),
        .m_axi_wvalid  (m_axi_wvalid),
        .m_axi_wready  (m_axi_wready),
        .m_axi_bresp   (m_axi_bresp),
        .m_axi_bvalid  (m_axi_bvalid),
        .m_axi_bready  (m_axi_bready),
        .m_axi_araddr  (m_axi_araddr),
        .m_axi_arvalid (m_axi_arvalid),
        .m_axi_arready (m_axi_arready),
        .m_axi_rdata   (m_axi_rdata),
        .m_axi_rresp   (m_axi_rresp),
        .m_axi_rvalid  (m_axi_rvalid),
        .m_axi_rready  (m_axi_rready)
    );

    // 3. AXI Crossbar Decoder Interconnect
    wire [AXI_ADDR_WIDTH-1:0]   s0_axi_awaddr;
    wire                        s0_axi_awvalid;
    wire                        s0_axi_awready;
    wire [AXI_DATA_WIDTH-1:0]   s0_axi_wdata;
    wire [AXI_DATA_WIDTH/8-1:0] s0_axi_wstrb;
    wire                        s0_axi_wvalid;
    wire                        s0_axi_wready;
    wire [1:0]                  s0_axi_bresp;
    wire                        s0_axi_bvalid;
    wire                        s0_axi_bready;
    wire [AXI_ADDR_WIDTH-1:0]   s0_axi_araddr;
    wire                        s0_axi_arvalid;
    wire                        s0_axi_arready;
    wire [AXI_DATA_WIDTH-1:0]   s0_axi_rdata;
    wire [1:0]                  s0_axi_rresp;
    wire                        s0_axi_rvalid;
    wire                        s0_axi_rready;

    wire [AXI_ADDR_WIDTH-1:0]   s1_axi_awaddr;
    wire                        s1_axi_awvalid;
    wire                        s1_axi_awready;
    wire [AXI_DATA_WIDTH-1:0]   s1_axi_wdata;
    wire [AXI_DATA_WIDTH/8-1:0] s1_axi_wstrb;
    wire                        s1_axi_wvalid;
    wire                        s1_axi_wready;
    wire [1:0]                  s1_axi_bresp;
    wire                        s1_axi_bvalid;
    wire                        s1_axi_bready;
    wire [AXI_ADDR_WIDTH-1:0]   s1_axi_araddr;
    wire                        s1_axi_arvalid;
    wire                        s1_axi_arready;
    wire [AXI_DATA_WIDTH-1:0]   s1_axi_rdata;
    wire [1:0]                  s1_axi_rresp;
    wire                        s1_axi_rvalid;
    wire                        s1_axi_rready;

    axi_decoder #(
        .AXI_ADDR_WIDTH(AXI_ADDR_WIDTH),
        .AXI_DATA_WIDTH(AXI_DATA_WIDTH),
        .DATA_MEM_BASE (DATA_MEM_BASE),
        .DATA_MEM_SIZE (DATA_MEM_SIZE),
        .VGA_REG_BASE  (VGA_REG_BASE),
        .VGA_REG_SIZE  (VGA_REG_SIZE),
        .FB_BASE       (FB_BASE),
        .FB_SIZE       (FB_SIZE)
    ) u_axi_decoder (
        .clk            (clk),
        .rst            (reset),

        // Master Side
        .m_axi_awaddr   (m_axi_awaddr),
        .m_axi_awvalid  (m_axi_awvalid),
        .m_axi_awready  (m_axi_awready),
        .m_axi_wdata    (m_axi_wdata),
        .m_axi_wstrb    (m_axi_wstrb),
        .m_axi_wvalid   (m_axi_wvalid),
        .m_axi_wready   (m_axi_wready),
        .m_axi_bresp    (m_axi_bresp),
        .m_axi_bvalid   (m_axi_bvalid),
        .m_axi_bready   (m_axi_bready),
        .m_axi_araddr   (m_axi_araddr),
        .m_axi_arvalid  (m_axi_arvalid),
        .m_axi_arready  (m_axi_arready),
        .m_axi_rdata    (m_axi_rdata),
        .m_axi_rresp    (m_axi_rresp),
        .m_axi_rvalid   (m_axi_rvalid),
        .m_axi_rready   (m_axi_rready),

        // Slave 0: Data Memory
        .s0_axi_awaddr  (s0_axi_awaddr),
        .s0_axi_awvalid (s0_axi_awvalid),
        .s0_axi_awready (s0_axi_awready),
        .s0_axi_wdata   (s0_axi_wdata),
        .s0_axi_wstrb   (s0_axi_wstrb),
        .s0_axi_wvalid  (s0_axi_wvalid),
        .s0_axi_wready  (s0_axi_wready),
        .s0_axi_bresp   (s0_axi_bresp),
        .s0_axi_bvalid  (s0_axi_bvalid),
        .s0_axi_bready  (s0_axi_bready),
        .s0_axi_araddr  (s0_axi_araddr),
        .s0_axi_arvalid (s0_axi_arvalid),
        .s0_axi_arready (s0_axi_arready),
        .s0_axi_rdata   (s0_axi_rdata),
        .s0_axi_rresp   (s0_axi_rresp),
        .s0_axi_rvalid  (s0_axi_rvalid),
        .s0_axi_rready  (s0_axi_rready),

        // Slave 1: VGA Subsystem
        .s1_axi_awaddr  (s1_axi_awaddr),
        .s1_axi_awvalid (s1_axi_awvalid),
        .s1_axi_awready (s1_axi_awready),
        .s1_axi_wdata   (s1_axi_wdata),
        .s1_axi_wstrb   (s1_axi_wstrb),
        .s1_axi_wvalid  (s1_axi_wvalid),
        .s1_axi_wready  (s1_axi_wready),
        .s1_axi_bresp   (s1_axi_bresp),
        .s1_axi_bvalid  (s1_axi_bvalid),
        .s1_axi_bready  (s1_axi_bready),
        .s1_axi_araddr  (s1_axi_araddr),
        .s1_axi_arvalid (s1_axi_arvalid),
        .s1_axi_arready (s1_axi_arready),
        .s1_axi_rdata   (s1_axi_rdata),
        .s1_axi_rresp   (s1_axi_rresp),
        .s1_axi_rvalid  (s1_axi_rvalid),
        .s1_axi_rready  (s1_axi_rready)
    );

    // 4. Slave 0: AXI4-Lite Data Memory
    axi_data_memory #(
        .AXI_ADDR_WIDTH(AXI_ADDR_WIDTH),
        .AXI_DATA_WIDTH(AXI_DATA_WIDTH),
        .MEM_SIZE_BYTES(DATA_MEM_SIZE),
        .BASE_ADDR     (DATA_MEM_BASE)
    ) u_data_memory (
        .clk           (clk),
        .rst           (reset),

        .s_axi_awaddr  (s0_axi_awaddr),
        .s_axi_awvalid (s0_axi_awvalid),
        .s_axi_awready (s0_axi_awready),
        .s_axi_wdata   (s0_axi_wdata),
        .s_axi_wstrb   (s0_axi_wstrb),
        .s_axi_wvalid  (s0_axi_wvalid),
        .s_axi_wready  (s0_axi_wready),
        .s_axi_bresp   (s0_axi_bresp),
        .s_axi_bvalid  (s0_axi_bvalid),
        .s_axi_bready  (s0_axi_bready),
        .s_axi_araddr  (s0_axi_araddr),
        .s_axi_arvalid (s0_axi_arvalid),
        .s_axi_arready (s0_axi_arready),
        .s_axi_rdata   (s0_axi_rdata),
        .s_axi_rresp   (s0_axi_rresp),
        .s_axi_rvalid  (s0_axi_rvalid),
        .s_axi_rready  (s0_axi_rready)
    );

    // 5. Slave 1: VGA Subsystem
    wire        vga_fb_req;
    wire [20:0] vga_fb_addr;
    wire        vga_video_on;

    wire [18:0] fb_addr;
    wire [31:0] fb_wdata;
    wire [3:0]  fb_we;
    wire        fb_en;
    wire [31:0] fb_rdata;

    vga_registers #(
        .AXI_ADDR_WIDTH   (AXI_ADDR_WIDTH),
        .AXI_DATA_WIDTH   (AXI_DATA_WIDTH),
        .FB_WIDTH_DEFAULT (FB_WIDTH),
        .FB_HEIGHT_DEFAULT(FB_HEIGHT),
        .FB_BASE_DEFAULT  (FB_BASE)
    ) u_vga_registers (
        .clk            (clk),
        .rst            (reset),
        .btn            (btn),
        .sw             (sw),

        .s_axi_awaddr   (s1_axi_awaddr),
        .s_axi_awvalid  (s1_axi_awvalid),
        .s_axi_awready  (s1_axi_awready),
        .s_axi_wdata    (s1_axi_wdata),
        .s_axi_wstrb    (s1_axi_wstrb),
        .s_axi_wvalid   (s1_axi_wvalid),
        .s_axi_wready   (s1_axi_wready),
        .s_axi_bresp    (s1_axi_bresp),
        .s_axi_bvalid   (s1_axi_bvalid),
        .s_axi_bready   (s1_axi_bready),
        .s_axi_araddr   (s1_axi_araddr),
        .s_axi_arvalid  (s1_axi_arvalid),
        .s_axi_arready  (s1_axi_arready),
        .s_axi_rdata    (s1_axi_rdata),
        .s_axi_rresp    (s1_axi_rresp),
        .s_axi_rvalid   (s1_axi_rvalid),
        .s_axi_rready   (s1_axi_rready),

        .vga_fb_req     (vga_fb_req),
        .vga_fb_addr    (vga_fb_addr),
        .vga_video_on   (vga_video_on),
        .display_enable (display_enable),

        .fb_addr        (fb_addr),
        .fb_wdata       (fb_wdata),
        .fb_we          (fb_we),
        .fb_en          (fb_en),
        .fb_rdata       (fb_rdata)
    );

    framebuffer_sram #(
        .FB_WIDTH (FB_WIDTH),
        .FB_HEIGHT(FB_HEIGHT)
    ) u_framebuffer_sram (
        .clk   (clk),
        .en    (fb_en),
        .we    (fb_we),
        .addr  (fb_addr),
        .wdata (fb_wdata),
        .rdata (fb_rdata)
    );

    vga_controller #(
        .PIXEL_SCALE(PIXEL_SCALE)
    ) u_vga_controller (
        .clk            (clk),
        .rst            (reset),

        .display_enable (display_enable),
        .vga_fb_req     (vga_fb_req),
        .vga_fb_addr    (vga_fb_addr),
        .vga_video_on   (vga_video_on),
        .vga_data       (fb_rdata),

        .Hsync          (Hsync),
        .Vsync          (Vsync),
        .red            (red),
        .green          (green),
        .blue           (blue)
    );

endmodule
