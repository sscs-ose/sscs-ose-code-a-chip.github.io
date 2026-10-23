// ============================================================================
// fuzzy_extractor.v  -  Three-sample majority-vote model
// ============================================================================
// This is not a production fuzzy extractor: it has no helper-data scheme,
// entropy extraction, error-correction analysis, or leakage assessment.
module fuzzy_extractor #(
    parameter integer ID_BITS = 32
) (
    input  wire                  clk,
    input  wire                  rst_n,
    input  wire                  enroll_cmd,
    input  wire                  verify_cmd,
    input  wire [ID_BITS-1:0]    raw_sample,
    input  wire                  sample_valid,
    output reg                   enroll_done,
    output reg                   verify_done,
    output reg                   verify_match,
    output reg                   enrolled,
    output reg  [ID_BITS-1:0]    device_id
);
    reg [ID_BITS-1:0] sample0, sample1;
    reg [1:0]         sample_cnt;
    reg [ID_BITS-1:0] final_id;

    integer bi;

    always @(*) begin
        for (bi = 0; bi < ID_BITS; bi = bi + 1) begin
            if (sample_cnt == 2'd2)
                final_id[bi] = (sample0[bi] + sample1[bi] + raw_sample[bi]) >= 2'd2;
            else
                final_id[bi] = 1'b0;
        end
    end

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            sample0     <= 0;
            sample1     <= 0;
            sample_cnt  <= 0;
            enroll_done <= 1'b0;
            verify_done <= 1'b0;
            verify_match<= 1'b0;
            enrolled    <= 1'b0;
            device_id   <= 0;
        end else begin
            enroll_done  <= 1'b0;
            verify_done  <= 1'b0;
            verify_match <= 1'b0;

            if (sample_valid && (enroll_cmd || verify_cmd)) begin
                case (sample_cnt)
                    2'd0: sample0 <= raw_sample;
                    2'd1: sample1 <= raw_sample;
                    2'd2: begin
                        if (enroll_cmd) begin
                            device_id   <= final_id;
                            enrolled    <= 1'b1;
                            enroll_done <= 1'b1;
                        end else begin
                            verify_match <= (final_id == device_id);
                            verify_done  <= 1'b1;
                        end
                        sample_cnt <= 0;
                    end
`ifdef TRUSTEDGE_ASIC_SERVICE_PORTS
                    default: begin
                        // Recover fail-closed from an invalid sample phase.
                        // No enroll/verify completion pulse is emitted.
                        sample_cnt <= 0;
                    end
`endif
                endcase
                if (sample_cnt != 2'd2)
                    sample_cnt <= sample_cnt + 2'd1;
            end
        end
    end
endmodule
