// Physical-design binding of the NTT coefficient store to the OpenRAM macro
// used on the HSKEM chip (sky130_sram_1rw_16x256_wpr8), for the block-level
// "ntt_macro" run. It is the 16x256 branch of the chip's macro bindings
// (HSKEM asic/rtl/sky130_sram_macro_bindings.sv): the macro is a black box for
// synthesis, and its 17-bit ports carry one unused spare bit.
// Functional verification uses the behavioural model in te_sram_models.sv.
// SPDX-License-Identifier: Apache-2.0
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

module te_sram_1rw #(
    parameter integer WIDTH = 16,
    parameter integer DEPTH = 256,
    parameter integer ADDR_WIDTH = 8
) (
    input  wire                  clk,
    input  wire                  we,
    input  wire [ADDR_WIDTH-1:0] addr,
    input  wire [WIDTH-1:0]      wdata,
    output wire [WIDTH-1:0]      rdata
);
    wire [16:0] dout0;
    sky130_sram_1rw_16x256_wpr8 u_macro (
        .clk0(clk), .csb0(1'b0), .web0(~we), .wmask0(2'b11),
        .spare_wen0(1'b0), .addr0({1'b0, addr}),
        .din0({1'b0, wdata}), .dout0(dout0)
    );
    assign rdata = dout0[15:0];
endmodule
