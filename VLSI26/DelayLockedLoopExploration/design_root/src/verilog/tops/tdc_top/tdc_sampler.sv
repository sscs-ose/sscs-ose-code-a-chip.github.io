module tdc_sampler #(
    parameter STAGES = 8
)(
    input  wire              sample_clk,   // event
    input  wire [STAGES-1:0] clk_phases,
    output reg  [STAGES-1:0] thermo_code
);

    always @(posedge sample_clk) begin
        thermo_code <= clk_phases;
    end

endmodule