`timescale 1ns / 1ps

module rv32i_axi_bridge #(
    parameter AXI_ADDR_WIDTH = 32,
    parameter AXI_DATA_WIDTH = 32
)(
    input  wire                          clk,
    input  wire                          rst,

    // =========================================================================
    // Native CPU Memory Interface
    // =========================================================================
    input  wire [31:0]                   cpu_mem_addr,
    input  wire [31:0]                   cpu_mem_wdata,
    input  wire                          cpu_mem_write,
    input  wire                          cpu_mem_read,
    output wire [31:0]                   cpu_mem_rdata,
    output wire                          cpu_stall,

    // =========================================================================
    // AXI4-Lite Master Interface
    // =========================================================================
    // Write Address Channel
    output reg  [AXI_ADDR_WIDTH-1:0]     m_axi_awaddr,
    output reg                           m_axi_awvalid,
    input  wire                          m_axi_awready,

    // Write Data Channel
    output reg  [AXI_DATA_WIDTH-1:0]     m_axi_wdata,
    output reg  [AXI_DATA_WIDTH/8-1:0]   m_axi_wstrb,
    output reg                           m_axi_wvalid,
    input  wire                          m_axi_wready,

    // Write Response Channel
    input  wire [1:0]                    m_axi_bresp,
    input  wire                          m_axi_bvalid,
    output reg                           m_axi_bready,

    // Read Address Channel
    output reg  [AXI_ADDR_WIDTH-1:0]     m_axi_araddr,
    output reg                           m_axi_arvalid,
    input  wire                          m_axi_arready,

    // Read Data Channel
    input  wire [AXI_DATA_WIDTH-1:0]     m_axi_rdata,
    input  wire [1:0]                    m_axi_rresp,
    input  wire                          m_axi_rvalid,
    output reg                           m_axi_rready
);

    localparam [2:0] M_IDLE      = 3'b000;
    localparam [2:0] M_WRITE_ACT = 3'b001;
    localparam [2:0] M_WRITE_RES = 3'b010;
    localparam [2:0] M_READ_ACT  = 3'b011;
    localparam [2:0] M_READ_RES  = 3'b100;

    reg [2:0] state;
    reg [31:0] rdata_buf;

    // Direct forwarding of incoming read data during completion cycle
    assign cpu_mem_rdata = m_axi_rvalid ? m_axi_rdata : rdata_buf;

    // Check if write or read completes in the current cycle
    wire wr_done_now = (state == M_WRITE_ACT && m_axi_bvalid &&
                        (!m_axi_awvalid || m_axi_awready) &&
                        (!m_axi_wvalid  || m_axi_wready)) ||
                       (state == M_WRITE_RES && m_axi_bvalid);

    wire rd_done_now = (state == M_READ_ACT && m_axi_rvalid) ||
                       (state == M_READ_RES && m_axi_rvalid);

    // CPU stall control: stall while memory operation is in flight until completion cycle
    assign cpu_stall = ((state == M_IDLE && (cpu_mem_read || cpu_mem_write)) ||
                        (state != M_IDLE)) && !(wr_done_now || rd_done_now);

    always @(posedge clk or posedge rst) begin
        if (rst) begin
            state         <= M_IDLE;
            m_axi_awaddr  <= 0;
            m_axi_awvalid <= 1'b0;
            m_axi_wdata   <= 0;
            m_axi_wstrb   <= 0;
            m_axi_wvalid  <= 1'b0;
            m_axi_bready  <= 1'b0;
            m_axi_araddr  <= 0;
            m_axi_arvalid <= 1'b0;
            m_axi_rready  <= 1'b0;
            rdata_buf     <= 32'd0;
        end else begin
            case (state)
                M_IDLE: begin
                    if (cpu_mem_write) begin
                        m_axi_awaddr  <= cpu_mem_addr;
                        m_axi_awvalid <= 1'b1;
                        m_axi_wdata   <= cpu_mem_wdata;
                        m_axi_wstrb   <= 4'b1111;
                        m_axi_wvalid  <= 1'b1;
                        m_axi_bready  <= 1'b1;
                        state         <= M_WRITE_ACT;
                    end else if (cpu_mem_read) begin
                        m_axi_araddr  <= cpu_mem_addr;
                        m_axi_arvalid <= 1'b1;
                        m_axi_rready  <= 1'b1;
                        state         <= M_READ_ACT;
                    end
                end

                M_WRITE_ACT: begin
                    // Handshake AW channel
                    if (m_axi_awready && m_axi_awvalid) begin
                        m_axi_awvalid <= 1'b0;
                    end
                    // Handshake W channel
                    if (m_axi_wready && m_axi_wvalid) begin
                        m_axi_wvalid <= 1'b0;
                    end

                    // Once AW & W have been accepted (or completing now)
                    if ((!m_axi_awvalid || m_axi_awready) &&
                        (!m_axi_wvalid  || m_axi_wready)) begin
                        if (m_axi_bvalid) begin
                            // Fast response: B channel also completed
                            m_axi_bready <= 1'b0;
                            state        <= M_IDLE;
                        end else begin
                            state        <= M_WRITE_RES;
                        end
                    end
                end

                M_WRITE_RES: begin
                    if (m_axi_bvalid) begin
                        m_axi_bready <= 1'b0;
                        state        <= M_IDLE;
                    end
                end

                M_READ_ACT: begin
                    // Handshake AR channel
                    if (m_axi_arready && m_axi_arvalid) begin
                        m_axi_arvalid <= 1'b0;
                    end

                    if (m_axi_rvalid) begin
                        rdata_buf    <= m_axi_rdata;
                        m_axi_rready <= 1'b0;
                        state        <= M_IDLE;
                    end else if (!m_axi_arvalid || m_axi_arready) begin
                        state        <= M_READ_RES;
                    end
                end

                M_READ_RES: begin
                    if (m_axi_rvalid) begin
                        rdata_buf    <= m_axi_rdata;
                        m_axi_rready <= 1'b0;
                        state        <= M_IDLE;
                    end
                end
            endcase
        end
    end

endmodule
