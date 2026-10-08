// Physical-design binding of the Section 7 NTT redesign (kyber_ntt_engine_opt) to the
// chip's OpenRAM macro, for the block-level "ntt_opt_pipe_macro" run. The iteration names its
// store te_sram_1rw_model; this module gives that name the same macro binding that
// rtl/sram_macro_16x256.sv gives te_sram_1rw (compile both files; the black box of the macro
// is declared there). A COEFF_W-bit store occupies the low bits of the 17-bit macro word.
// Functional verification uses the behavioural model in te_sram_models.sv.
// SPDX-License-Identifier: Apache-2.0
module te_sram_1rw_model #(
    parameter integer WIDTH = 12,
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
        .din0({{(17 - WIDTH){1'b0}}, wdata}), .dout0(dout0)
    );
    assign rdata = dout0[WIDTH-1:0];
endmodule
