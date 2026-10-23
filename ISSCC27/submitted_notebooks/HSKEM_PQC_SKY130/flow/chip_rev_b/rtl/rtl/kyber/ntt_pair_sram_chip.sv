// Chip v2: the two-lane engine's 24 x 128 coefficient store bound to the chip's OpenRAM macro. Same
// wrapper as rtl/ntt_pair_sram_macro.sv of the notebook, without the macro's blackbox declaration, which
// asic/rtl/sky130_sram_macro_bindings.sv already provides. The chip select follows the engine's own
// access requests (csb0 = ~ce), as in the routed block of Section 7.
// SPDX-License-Identifier: Apache-2.0
module ntt_pair_sram (
    input  wire        clk,
    input  wire        ce,
    input  wire        we,
    input  wire [6:0]  addr,
    input  wire [23:0] wdata,
    output wire [23:0] rdata
);
    wire [24:0] dout0;
    sky130_sram_1rw_24x128 u_macro (
        .clk0(clk), .csb0(~ce), .web0(~we), .wmask0(3'b111), .spare_wen0(1'b0),
        .addr0({1'b0, addr}), .din0({1'b0, wdata}), .dout0(dout0));
    assign rdata = dout0[23:0];
endmodule
