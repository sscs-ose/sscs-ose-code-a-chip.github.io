`timescale 1ps/1ps

module tdc_top #(
    parameter STAGES = 8
)(
    input  wire clk_in,
    input  wire rst,
    input  wire event_in,

    output wire [$clog2(STAGES)-1:0] tdc_out
);

    // Internal signals
    wire [STAGES-1:0] clk_phases;

    // Tie off control (STATIC delay line for TDC)
    wire shift_left  = 1'b0;
    wire shift_right = 1'b0;

    wire rst_n = ~rst;

    // Delay line (FIXED instantiation)
    nand_dcdl_top #(
        .STAGES(STAGES)
    ) dcdl (
        .clk(clk_in),              // event_in correct port
        .rst_n(rst_n),             // event_in active low reset
        .shift_left(shift_left),   // event_in tied off
        .shift_right(shift_right), // event_in tied off
        .A(clk_in),                // event_in propagate clock
        .phases(clk_phases)        // event_in correct port
    );

    // Sampling
    wire [STAGES-1:0] thermo_code;

    tdc_sampler #(
        .STAGES(STAGES)
    ) sampler (
        .sample_clk(event_in),
        .clk_phases(clk_phases),
        .thermo_code(thermo_code)
    );

    // Encoding
    thermometer_encoder #(
        .STAGES(STAGES)
    ) encoder (
        .thermo(thermo_code),
        .bin(tdc_out)
    );

endmodule