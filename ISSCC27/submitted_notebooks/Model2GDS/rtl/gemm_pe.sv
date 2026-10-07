// Phase 1 signed INT8 output-stationary processing element.
// Contract: docs/PHASE1_MICROARCHITECTURE.md.
module gemm_pe (
    input  logic clk,
    input  logic rst,
    input  logic clear,
    input  logic signed [7:0] a_in,
    input  logic signed [7:0] b_in,
    input  logic a_valid,
    input  logic b_valid,
    input  logic a_last,
    input  logic b_last,
    output logic signed [7:0] a_out,
    output logic signed [7:0] b_out,
    output logic a_out_valid,
    output logic b_out_valid,
    output logic a_out_last,
    output logic b_out_last,
    output logic signed [31:0] accumulator,
    output logic result_valid
);
    logic signed [15:0] product;
    logic signed [31:0] extended_product;
    assign product = a_in * b_in;
    assign extended_product = {{16{product[15]}}, product};

    always_ff @(posedge clk) begin
        if (rst || clear) begin
            a_out <= '0;
            b_out <= '0;
            a_out_valid <= 1'b0;
            b_out_valid <= 1'b0;
            a_out_last <= 1'b0;
            b_out_last <= 1'b0;
            accumulator <= '0;
            result_valid <= 1'b0;
        end else begin
            a_out <= a_valid ? a_in : 8'sd0;
            b_out <= b_valid ? b_in : 8'sd0;
            a_out_valid <= a_valid;
            b_out_valid <= b_valid;
            a_out_last <= a_valid && a_last;
            b_out_last <= b_valid && b_last;
            if (a_valid && b_valid) begin
                // The 32-bit destination implements modulo-2^32 wrap.
                accumulator <= accumulator + extended_product;
                if (a_last && b_last)
                    result_valid <= 1'b1;
            end
        end
    end
endmodule
