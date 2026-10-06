// ---------------------------------------------------------------------------
// open_ntt_soc : SoC top-level with PCPI Custom Instruction and DMA (N3)
//
// Interconnects:
//   - PicoRV32 PCPI custom instruction interface
//   - Self-DMA Wishbone Master engine
//   - Shared system SRAM
//   - 2-Master Wishbone Bus Arbiter (CPU master + DMA master)
//   - OpenNTT unified accelerator core
// ---------------------------------------------------------------------------
module open_ntt_soc #(
    parameter integer WIDTH = 24,
    parameter integer N     = 256,
    parameter integer LOGN  = 8,
    parameter integer AW    = 9
) (
    input  wire        clk,
    input  wire        rst_n,

    // PicoRV32 PCPI Interface
    input  wire        pcpi_valid,
    input  wire [31:0] pcpi_insn,
    input  wire [31:0] pcpi_rs1,
    input  wire [31:0] pcpi_rs2,
    output wire        pcpi_wr,
    output wire [31:0] pcpi_rd,
    output wire        pcpi_wait,
    output wire        pcpi_ready,

    // Host MMIO / CPU Wishbone Master Interface
    input  wire        cpu_wb_cyc,
    input  wire        cpu_wb_stb,
    input  wire        cpu_wb_we,
    input  wire [31:0] cpu_wb_addr,
    input  wire [31:0] cpu_wb_wdata,
    output reg  [31:0] cpu_wb_rdata,
    output reg         cpu_wb_ack,

    // Interrupt line
    output wire        irq
);

    // --- Signals between PCPI and Accelerator ---
    wire        acc_start;
    wire [2:0]  acc_op;
    wire [31:0] acc_ptr;
    wire        acc_busy;
    wire        acc_done;
    wire [31:0] acc_cycles;

    // --- DMA Signals ---
    reg         dma_start;
    reg         dma_dir;
    reg  [31:0] dma_sram_addr;
    reg  [AW-1:0] dma_coeff_base;
    wire        dma_busy;
    wire        dma_done;

    wire        dma_wb_cyc, dma_wb_stb, dma_wb_we;
    wire [31:0] dma_wb_addr, dma_wb_wdata;
    wire [31:0] dma_wb_rdata;
    wire        dma_wb_ack;

    wire        dma_ram_we;
    wire [AW-1:0] dma_ram_addr;
    wire [WIDTH-1:0] dma_ram_wdata;
    wire [WIDTH-1:0] dma_ram_rdata;

    // --- OpenNTT Memory Access Multiplexer ---
    wire        core_cmd_we;
    wire [AW-1:0] core_cmd_addr;
    wire [WIDTH-1:0] core_cmd_wdata;
    wire [WIDTH-1:0] core_cmd_rdata;

    assign core_cmd_we    = dma_busy ? dma_ram_we    : (cpu_wb_stb && cpu_wb_we && (cpu_wb_addr[11:10] == 2'b00));
    assign core_cmd_addr  = dma_busy ? dma_ram_addr  : cpu_wb_addr[AW-1:0];
    assign core_cmd_wdata = dma_busy ? dma_ram_wdata : cpu_wb_wdata[WIDTH-1:0];
    assign dma_ram_rdata  = core_cmd_rdata;

    // --- PCPI Decoder ---
    ntt_pcpi u_pcpi (
        .clk(clk),
        .rst_n(rst_n),
        .pcpi_valid(pcpi_valid),
        .pcpi_insn(pcpi_insn),
        .pcpi_rs1(pcpi_rs1),
        .pcpi_rs2(pcpi_rs2),
        .pcpi_wr(pcpi_wr),
        .pcpi_rd(pcpi_rd),
        .pcpi_wait(pcpi_wait),
        .pcpi_ready(pcpi_ready),
        .acc_start(acc_start),
        .acc_op(acc_op),
        .acc_ptr(acc_ptr),
        .acc_done(acc_done),
        .acc_cycles(acc_cycles)
    );

    // --- DMA Engine ---
    ntt_dma #(.WIDTH(WIDTH), .AW(AW), .N(N)) u_dma (
        .clk(clk),
        .rst_n(rst_n),
        .dma_start(dma_start),
        .dma_dir(dma_dir),
        .dma_sram_addr(dma_sram_addr),
        .dma_coeff_base(dma_coeff_base),
        .dma_busy(dma_busy),
        .dma_done(dma_done),
        .wb_cyc(dma_wb_cyc),
        .wb_stb(dma_wb_stb),
        .wb_we(dma_wb_we),
        .wb_addr(dma_wb_addr),
        .wb_wdata(dma_wb_wdata),
        .wb_rdata(dma_wb_rdata),
        .wb_ack(dma_wb_ack),
        .ram_we(dma_ram_we),
        .ram_addr(dma_ram_addr),
        .ram_wdata(dma_ram_wdata),
        .ram_rdata(dma_ram_rdata)
    );

    // --- OpenNTT Top-Level Engine ---
    reg top_start;
    reg [2:0] top_op;

    ntt_top #(
        .WIDTH(WIDTH),
        .N(N),
        .LOGN(LOGN),
        .AW(AW)
    ) u_top (
        .clk(clk),
        .rst_n(rst_n),
        .start(top_start),
        .op(top_op),
        .scale_const(24'd0),
        .busy(acc_busy),
        .done(acc_done),
        .cycles(acc_cycles),
        .cmd_we(core_cmd_we),
        .cmd_addr(core_cmd_addr),
        .cmd_wdata(core_cmd_wdata),
        .cmd_rdata(core_cmd_rdata)
    );

    assign irq = acc_done;

    // --- Shared SRAM Memory Array (Simulated System Memory) ---
    reg [31:0] sram_mem [0:1023];
    reg        sram_ack;
    reg [31:0] sram_rdata;

    // --- Wishbone Arbiter (DMA Master gets priority over CPU on shared SRAM) ---
    wire bus_master_dma = dma_wb_cyc && dma_wb_stb;
    wire active_cyc     = bus_master_dma ? dma_wb_cyc  : cpu_wb_cyc;
    wire active_stb     = bus_master_dma ? dma_wb_stb  : cpu_wb_stb;
    wire active_we      = bus_master_dma ? dma_wb_we   : cpu_wb_we;
    wire [31:0] active_addr = bus_master_dma ? dma_wb_addr : cpu_wb_addr;
    wire [31:0] active_wdata = bus_master_dma ? dma_wb_wdata : cpu_wb_wdata;

    assign dma_wb_ack   = bus_master_dma ? sram_ack : 1'b0;
    assign dma_wb_rdata = sram_rdata;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            sram_ack   <= 1'b0;
            sram_rdata <= 32'd0;
            cpu_wb_ack <= 1'b0;
            cpu_wb_rdata <= 32'd0;
            top_start  <= 1'b0;
            top_op     <= 3'd0;
            dma_start  <= 1'b0;
            dma_dir    <= 1'b0;
            dma_sram_addr <= 32'd0;
            dma_coeff_base <= {AW{1'b0}};
        end else begin
            sram_ack   <= 1'b0;
            cpu_wb_ack <= 1'b0;
            top_start  <= 1'b0;
            dma_start  <= 1'b0;

            // Triggered from PCPI custom instruction
            if (acc_start) begin
                top_op    <= acc_op;
                top_start <= 1'b1;
            end

            // SRAM read/write responding in 1 cycle
            if (active_cyc && active_stb && !sram_ack) begin
                sram_ack <= 1'b1;
                if (active_we) begin
                    sram_mem[active_addr[11:2]] <= active_wdata;
                end
                sram_rdata <= sram_mem[active_addr[11:2]];

                if (!bus_master_dma) begin
                    cpu_wb_ack   <= 1'b1;
                    cpu_wb_rdata <= sram_mem[active_addr[11:2]];
                end
            end
        end
    end

endmodule
