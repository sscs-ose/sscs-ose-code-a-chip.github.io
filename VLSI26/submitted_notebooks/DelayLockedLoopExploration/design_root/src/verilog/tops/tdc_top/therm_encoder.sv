module thermometer_encoder #(
    parameter STAGES = 8,
    parameter OUT_BITS = $clog2(STAGES)
)(
    input  wire [STAGES-1:0] thermo,
    output reg  [OUT_BITS-1:0] bin
);

    integer i;

    always @(*) begin
        bin = 0;
        for (i = 0; i < STAGES; i = i + 1) begin
            if (thermo[i])
                bin = i;
        end
    end

endmodule