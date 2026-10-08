// Physical-design binding of the packed NTT's coefficient store (ntt_pair_sram, 128 x 24 bit) to the
// chip's OpenRAM macro sky130_sram_1rw_24x128 (compile with -D NTT_PAIR_SRAM_MACRO). The macro is a black
// box for synthesis; its 25-bit ports carry one unused spare bit and its address port one unused MSB.
// The chip select is driven by the engine, so idle cycles do not access the array.
// SPDX-License-Identifier: Apache-2.0
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
