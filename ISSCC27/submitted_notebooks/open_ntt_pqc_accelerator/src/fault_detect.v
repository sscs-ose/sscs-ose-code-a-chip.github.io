// ---------------------------------------------------------------------------
// fault_detect : Real-Time Fault-Injection Attack (FIA) Detector
//
// Protects post-quantum arithmetic against laser fault injection, clock glitching,
// and voltage manipulation attacks by checking residue invariants:
//   Conservation Invariant: (a_in + b_in) mod Q == (a_out + b_out) mod Q
//
// If a fault is injected during execution, `fault_alert` and `tamper_lock` are
// asserted within 1 clock cycle to abort the transform and sanitize registers.
// ---------------------------------------------------------------------------
module fault_detect #(
    parameter integer WIDTH = 24,
    parameter [WIDTH-1:0] Q = 24'd8380417
) (
    input  wire             clk,
    input  wire             rst_n,
    input  wire             check_en,
    input  wire [WIDTH-1:0] a_in,
    input  wire [WIDTH-1:0] b_in,
    input  wire [WIDTH-1:0] a_out,
    input  wire [WIDTH-1:0] b_out,
    output reg              fault_alert,
    output reg              tamper_lock,
    output reg  [31:0]      fault_count
);

    function [WIDTH-1:0] mod_add;
        input [WIDTH-1:0] u, v;
        reg [WIDTH:0] sum;
        begin
            sum = u + v;
            mod_add = (sum >= Q) ? (sum - Q) : sum[WIDTH-1:0];
        end
    endfunction

    wire [WIDTH-1:0] expected_sum = mod_add(a_in, b_in);
    wire [WIDTH-1:0] actual_sum   = mod_add(a_out, b_out);
    wire mismatch = (expected_sum != actual_sum);

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            fault_alert <= 1'b0;
            tamper_lock <= 1'b0;
            fault_count <= 32'd0;
        end else if (check_en) begin
            if (mismatch) begin
                fault_alert <= 1'b1;
                tamper_lock <= 1'b1;
                fault_count <= fault_count + 1'b1;
            end else begin
                fault_alert <= 1'b0;
            end
        end else begin
            fault_alert <= 1'b0;
        end
    end

endmodule
