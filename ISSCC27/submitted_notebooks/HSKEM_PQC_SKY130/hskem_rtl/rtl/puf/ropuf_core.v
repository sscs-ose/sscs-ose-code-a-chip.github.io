// ============================================================================
// ropuf_core.v  -  Behavioral RO-PUF response model
// ----------------------------------------------------------------------------
// This synchronous counter model approximates a challenge-dependent response.
// It does NOT infer physical ring oscillators or demonstrate per-device
// manufacturing variation, reliability, or uniqueness on FPGA silicon.
// ============================================================================
module ropuf_core #(
    parameter integer RESPONSE_BITS = 32,
    parameter integer SAMPLE_CYCLES = 64
) (
    input  wire                      clk,
    input  wire                      rst_n,
    input  wire                      start,
    input  wire [7:0]                challenge,
    output reg                       busy,
    output reg                       done,
    output reg [RESPONSE_BITS-1:0]   response
);
    reg [7:0]  sample_cnt;
    reg [4:0]  bit_idx;
    reg [15:0] cnt_a, cnt_b;
    reg        ro_a, ro_b;
    reg [7:0]  period_a, period_b;
    reg [7:0]  ctr_a, ctr_b;

    // Deterministic period model; not a measured manufacturing variation.
    function [7:0] period_for_a;
        input [4:0] idx;
        input [7:0] ch;
        begin
            period_for_a = 8'd8 + {3'b0, idx} + ch[2:0] + 8'd2;
        end
    endfunction

    function [7:0] period_for_b;
        input [4:0] idx;
        input [7:0] ch;
        begin
            period_for_b = 8'd12 + {3'b0, idx} + ch[5:3] + 8'd5;
        end
    endfunction

    localparam [2:0] S_IDLE=0, S_SETUP=1, S_COUNT=2, S_LATCH=3;

    reg [2:0] state;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state     <= S_IDLE;
            busy      <= 1'b0;
            done      <= 1'b0;
            response  <= 0;
            sample_cnt<= 0;
            bit_idx   <= 0;
            cnt_a     <= 0;
            cnt_b     <= 0;
            ro_a      <= 0;
            ro_b      <= 0;
            ctr_a     <= 0;
            ctr_b     <= 0;
        end else begin
            done <= 1'b0;
            case (state)
                S_IDLE: begin
                    busy <= 1'b0;
                    if (start) begin
                        busy      <= 1'b1;
                        bit_idx   <= 0;
                        response  <= 0;
                        state     <= S_SETUP;
                    end
                end
                S_SETUP: begin
                    period_a  <= period_for_a(bit_idx[4:0], challenge);
                    period_b  <= period_for_b(bit_idx[4:0], challenge);
                    sample_cnt<= 0;
                    cnt_a     <= 0;
                    cnt_b     <= 0;
                    ctr_a     <= 0;
                    ctr_b     <= 0;
                    ro_a      <= 0;
                    ro_b      <= 0;
                    state     <= S_COUNT;
                end
                S_COUNT: begin
                    // Synchronous counter approximation of the response path.
                    if (ctr_a >= period_a - 8'd1) begin
                        ctr_a <= 0;
                        ro_a  <= ~ro_a;
                        cnt_a <= cnt_a + 16'd1;
                    end else
                        ctr_a <= ctr_a + 8'd1;

                    if (ctr_b >= period_b - 8'd1) begin
                        ctr_b <= 0;
                        ro_b  <= ~ro_b;
                        cnt_b <= cnt_b + 16'd1;
                    end else
                        ctr_b <= ctr_b + 8'd1;

                    if (sample_cnt + 8'd1 >= SAMPLE_CYCLES) begin
                        sample_cnt <= 0;
                        state      <= S_LATCH;
                    end else
                        sample_cnt <= sample_cnt + 8'd1;
                end
                S_LATCH: begin
                    response[bit_idx[4:0]] <= (cnt_a > cnt_b);
                    if (bit_idx + 5'd1 >= RESPONSE_BITS) begin
                        busy  <= 1'b0;
                        done  <= 1'b1;
                        state <= S_IDLE;
                    end else begin
                        bit_idx <= bit_idx + 5'd1;
                        state   <= S_SETUP;
                    end
                end
                default: state <= S_IDLE;
            endcase
        end
    end
endmodule
