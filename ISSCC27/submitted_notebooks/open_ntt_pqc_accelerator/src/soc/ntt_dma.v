// ---------------------------------------------------------------------------
// ntt_dma : Wishbone-Lite Bus Master DMA Engine (N3)
//
// Automatically transfers polynomial vectors between shared system SRAM
// and the OpenNTT internal coefficient RAM, bypassing CPU load/store loops.
// ---------------------------------------------------------------------------
module ntt_dma #(
    parameter integer WIDTH = 24,
    parameter integer AW    = 9,
    parameter integer N     = 256
) (
    input  wire             clk,
    input  wire             rst_n,

    // Control Interface
    input  wire             dma_start,
    input  wire             dma_dir,       // 0: SRAM -> Coeff RAM, 1: Coeff RAM -> SRAM
    input  wire [31:0]      dma_sram_addr, // Byte address in shared SRAM
    input  wire [AW-1:0]    dma_coeff_base,// Offset in Coeff RAM (e.g. 0 or N)
    output reg              dma_busy,
    output reg              dma_done,

    // Wishbone Master Interface
    output reg              wb_cyc,
    output reg              wb_stb,
    output reg              wb_we,
    output reg  [31:0]      wb_addr,
    output reg  [31:0]      wb_wdata,
    input  wire [31:0]      wb_rdata,
    input  wire             wb_ack,

    // Coeff RAM Direct Interface
    output reg              ram_we,
    output reg  [AW-1:0]    ram_addr,
    output reg  [WIDTH-1:0] ram_wdata,
    input  wire [WIDTH-1:0] ram_rdata
);

    reg [AW-1:0] count;
    reg [2:0]    state;

    localparam S_IDLE  = 3'd0,
               S_R_REQ = 3'd1, S_R_ACK = 3'd2, S_R_WR = 3'd3,
               S_W_RD  = 3'd4, S_W_REQ = 3'd5, S_W_ACK = 3'd6;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state     <= S_IDLE;
            dma_busy  <= 1'b0;
            dma_done  <= 1'b0;
            wb_cyc    <= 1'b0;
            wb_stb    <= 1'b0;
            wb_we     <= 1'b0;
            wb_addr   <= 32'd0;
            wb_wdata  <= 32'd0;
            ram_we    <= 1'b0;
            ram_addr  <= {AW{1'b0}};
            ram_wdata <= {WIDTH{1'b0}};
            count     <= {AW{1'b0}};
        end else begin
            dma_done <= 1'b0;
            ram_we   <= 1'b0;

            case (state)
                S_IDLE: begin
                    wb_cyc <= 1'b0;
                    wb_stb <= 1'b0;
                    if (dma_start) begin
                        dma_busy <= 1'b1;
                        count    <= {AW{1'b0}};
                        if (!dma_dir) begin
                            // Read from SRAM -> Write to Coeff RAM
                            wb_addr <= dma_sram_addr;
                            wb_cyc  <= 1'b1;
                            wb_stb  <= 1'b1;
                            wb_we   <= 1'b0;
                            state   <= S_R_ACK;
                        end else begin
                            // Read from Coeff RAM -> Write to SRAM
                            ram_addr <= dma_coeff_base;
                            state    <= S_W_RD;
                        end
                    end else begin
                        dma_busy <= 1'b0;
                    end
                end

                // --- DMA Read from SRAM Path ---
                S_R_ACK: begin
                    if (wb_ack) begin
                        wb_cyc    <= 1'b0;
                        wb_stb    <= 1'b0;
                        ram_we    <= 1'b1;
                        ram_addr  <= dma_coeff_base + count;
                        ram_wdata <= wb_rdata[WIDTH-1:0];
                        if (count == N - 1) begin
                            dma_busy <= 1'b0;
                            dma_done <= 1'b1;
                            state    <= S_IDLE;
                        end else begin
                            count   <= count + 1'b1;
                            wb_addr <= dma_sram_addr + ((count + 1'b1) << 2);
                            wb_cyc  <= 1'b1;
                            wb_stb  <= 1'b1;
                            wb_we   <= 1'b0;
                            state   <= S_R_ACK;
                        end
                    end
                end

                // --- DMA Write to SRAM Path ---
                S_W_RD: begin
                    // 1-cycle latency for Coeff RAM read
                    wb_addr  <= dma_sram_addr + (count << 2);
                    wb_wdata <= {8'h00, ram_rdata};
                    wb_we    <= 1'b1;
                    wb_cyc   <= 1'b1;
                    wb_stb   <= 1'b1;
                    state    <= S_W_ACK;
                end

                S_W_ACK: begin
                    if (wb_ack) begin
                        wb_cyc <= 1'b0;
                        wb_stb <= 1'b0;
                        if (count == N - 1) begin
                            dma_busy <= 1'b0;
                            dma_done <= 1'b1;
                            state    <= S_IDLE;
                        end else begin
                            count    <= count + 1'b1;
                            ram_addr <= dma_coeff_base + count + 1'b1;
                            state    <= S_W_RD;
                        end
                    end
                end

                default: state <= S_IDLE;
            endcase
        end
    end

endmodule
