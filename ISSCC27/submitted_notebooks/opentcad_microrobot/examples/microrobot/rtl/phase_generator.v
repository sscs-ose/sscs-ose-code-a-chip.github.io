// Two quarter-cycle-separated outputs from one clock; Apache-2.0.
// Our timing implementation, not extracted from the paper's ASIC.
// DIVIDER_BITS=13 gives f_gait=f_clock/8192. reset_n is an external
// brownout/reset interface; its analog detector is not implemented here.
module phase_generator #(
    parameter integer DIVIDER_BITS = 13
) (
    input wire clk,
    input wire reset_n,
    output wire phase_a,
    output wire phase_b,
    output wire phase_valid
);
    reg [DIVIDER_BITS-1:0] count;
    always @(posedge clk or negedge reset_n) begin
        if (!reset_n)
            count <= {DIVIDER_BITS{1'b0}};
        else
            count <= count + 1'b1;
    end
    assign phase_a = reset_n && !count[DIVIDER_BITS-1];
    assign phase_b = reset_n && (count[DIVIDER_BITS-1] ^ count[DIVIDER_BITS-2]);
    assign phase_valid = reset_n;
endmodule
