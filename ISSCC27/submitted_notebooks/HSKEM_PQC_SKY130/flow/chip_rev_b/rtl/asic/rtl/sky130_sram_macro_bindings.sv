// M4 ASIC-only binding for 18 audited 1RW SRAM contracts across eight masters.
// This source is deliberately absent from the FPGA and functional-model source sets.
// Functional verification remains on te_sram_1rw_model: the raw OpenRAM
// 8x768 behavioural view is not a valid oracle for logical bit 7.

(* blackbox *) module sky130_sram_1rw_16x256_wpr8 (
    input  wire        clk0,
    input  wire        csb0,
    input  wire        web0,
    input  wire [1:0]  wmask0,
    input  wire        spare_wen0,
    input  wire [8:0]  addr0,
    input  wire [16:0] din0,
    output wire [16:0] dout0
);
endmodule

(* blackbox *) module sky130_sram_1rw_24x256 (
    input  wire        clk0,
    input  wire        csb0,
    input  wire        web0,
    input  wire [2:0]  wmask0,
    input  wire        spare_wen0,
    input  wire [8:0]  addr0,
    input  wire [24:0] din0,
    output wire [24:0] dout0
);
endmodule

(* blackbox *) module sky130_sram_1rw_8x768 (
    input  wire       clk0,
    input  wire       csb0,
    input  wire       web0,
    input  wire       spare_wen0,
    input  wire [9:0] addr0,
    input  wire [8:0] din0,
    output wire [8:0] dout0
);
endmodule

(* blackbox *) module sky130_sram_1rw_24x128 (
    input  wire        clk0,
    input  wire        csb0,
    input  wire        web0,
    input  wire [2:0]  wmask0,
    input  wire        spare_wen0,
    input  wire [7:0]  addr0,
    input  wire [24:0] din0,
    output wire [24:0] dout0
);
endmodule

(* blackbox *) module sky130_sram_1rw_12x256_wpr8 (
    input  wire        clk0,
    input  wire        csb0,
    input  wire        web0,
    input  wire        spare_wen0,
    input  wire [8:0]  addr0,
    input  wire [12:0] din0,
    output wire [12:0] dout0
);
endmodule

(* blackbox *) module sky130_sram_1rw_12x512_wpr8 (
    input  wire        clk0,
    input  wire        csb0,
    input  wire        web0,
    input  wire        spare_wen0,
    input  wire [9:0]  addr0,
    input  wire [12:0] din0,
    output wire [12:0] dout0
);
endmodule

(* blackbox *) module sky130_sram_1rw_12x640_wpr8 (
    input  wire        clk0,
    input  wire        csb0,
    input  wire        web0,
    input  wire        spare_wen0,
    input  wire [9:0]  addr0,
    input  wire [12:0] din0,
    output wire [12:0] dout0
);
endmodule

(* blackbox *) module sky130_sram_1rw_12x768_wpr8 (
    input  wire        clk0,
    input  wire        csb0,
    input  wire        web0,
    input  wire        spare_wen0,
    input  wire [9:0]  addr0,
    input  wire [12:0] din0,
    output wire [12:0] dout0
);
endmodule

// The physical macro LEF/Liberty retain vccd1/vssd1.  They are intentionally
// not logical wrapper ports here; later A3 PDN integration must connect those
// physical PG pins.  This M3 binding does not claim PDN closure.
module te_sram_1rw #(
    parameter integer WIDTH = 32,
    parameter integer DEPTH = 256,
    parameter integer ADDR_WIDTH = 8
) (
    input  wire                  clk,
    input  wire                  we,
    input  wire [ADDR_WIDTH-1:0] addr,
    input  wire [WIDTH-1:0]      wdata,
    output wire [WIDTH-1:0]      rdata
);
    generate
        if ((WIDTH == 12) && (DEPTH == 256) && (ADDR_WIDTH == 8)) begin : g_12x256
            wire [12:0] dout0;
            sky130_sram_1rw_12x256_wpr8 u_macro (
                .clk0(clk), .csb0(1'b0), .web0(~we), .spare_wen0(1'b0),
                .addr0({1'b0, addr}), .din0({1'b0, wdata}), .dout0(dout0)
            );
            assign rdata = dout0[11:0];
        end else if ((WIDTH == 12) && (DEPTH == 512) && (ADDR_WIDTH == 9)) begin : g_12x512
            wire [12:0] dout0;
            sky130_sram_1rw_12x512_wpr8 u_macro (
                .clk0(clk), .csb0(1'b0), .web0(~we), .spare_wen0(1'b0),
                .addr0({1'b0, addr}), .din0({1'b0, wdata}), .dout0(dout0)
            );
            assign rdata = dout0[11:0];
        end else if ((WIDTH == 12) && (DEPTH == 640) && (ADDR_WIDTH == 10)) begin : g_12x640
            wire [12:0] dout0;
            sky130_sram_1rw_12x640_wpr8 u_macro (
                .clk0(clk), .csb0(1'b0), .web0(~we), .spare_wen0(1'b0),
                .addr0(addr), .din0({1'b0, wdata}), .dout0(dout0)
            );
            assign rdata = dout0[11:0];
        end else if ((WIDTH == 12) && (DEPTH == 768) && (ADDR_WIDTH == 10)) begin : g_12x768
            wire [12:0] dout0;
            sky130_sram_1rw_12x768_wpr8 u_macro (
                .clk0(clk), .csb0(1'b0), .web0(~we), .spare_wen0(1'b0),
                .addr0(addr), .din0({1'b0, wdata}), .dout0(dout0)
            );
            assign rdata = dout0[11:0];
        end else if ((WIDTH == 16) && (DEPTH == 256) && (ADDR_WIDTH == 8)) begin : g_16x256
            wire [16:0] dout0;
            sky130_sram_1rw_16x256_wpr8 u_macro (
                .clk0(clk), .csb0(1'b0), .web0(~we), .wmask0(2'b11),
                .spare_wen0(1'b0), .addr0({1'b0, addr}),
                .din0({1'b0, wdata}), .dout0(dout0)
            );
            assign rdata = dout0[15:0];
        end else if ((WIDTH == 24) && (DEPTH == 256) && (ADDR_WIDTH == 8)) begin : g_24x256
            wire [24:0] dout0;
            sky130_sram_1rw_24x256 u_macro (
                .clk0(clk), .csb0(1'b0), .web0(~we), .wmask0(3'b111),
                .spare_wen0(1'b0), .addr0({1'b0, addr}),
                .din0({1'b0, wdata}), .dout0(dout0)
            );
            assign rdata = dout0[23:0];
        end else if ((WIDTH == 8) && (DEPTH == 768) && (ADDR_WIDTH == 10)) begin : g_8x768
            wire [8:0] dout0;
            sky130_sram_1rw_8x768 u_macro (
                .clk0(clk), .csb0(1'b0), .web0(~we), .spare_wen0(1'b0),
                .addr0(addr), .din0({1'b0, wdata}), .dout0(dout0)
            );
            assign rdata = dout0[7:0];
        end else if ((WIDTH == 24) && (DEPTH == 128) && (ADDR_WIDTH == 7)) begin : g_24x128
            wire [24:0] dout0;
            sky130_sram_1rw_24x128 u_macro (
                .clk0(clk), .csb0(1'b0), .web0(~we), .wmask0(3'b111),
                .spare_wen0(1'b0), .addr0({1'b0, addr}),
                .din0({1'b0, wdata}), .dout0(dout0)
            );
            assign rdata = dout0[23:0];
        end else begin : g_unsupported_shape
            // The M3 runner rejects this sentinel.  It prevents a future
            // contract from silently becoming an unqualified macro binding.
            te_sram_1rw_unsupported_shape #(
                .WIDTH(WIDTH), .DEPTH(DEPTH), .ADDR_WIDTH(ADDR_WIDTH)
            ) u_unsupported (
                .clk(clk), .we(we), .addr(addr), .wdata(wdata), .rdata(rdata)
            );
        end
    endgenerate
endmodule

(* blackbox *) module te_sram_1rw_unsupported_shape #(
    parameter integer WIDTH = 32,
    parameter integer DEPTH = 256,
    parameter integer ADDR_WIDTH = 8
) (
    input  wire                  clk,
    input  wire                  we,
    input  wire [ADDR_WIDTH-1:0] addr,
    input  wire [WIDTH-1:0]      wdata,
    output wire [WIDTH-1:0]      rdata
);
endmodule
