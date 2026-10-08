// ============================================================================
// puf_top.v  -  RoPUF + fuzzy extractor + anti-replay
// ============================================================================
module puf_top #(
    parameter integer ID_BITS = 32
) (
    input  wire                clk,
    input  wire                rst_n,
    input  wire                cmd_enroll,
    input  wire                cmd_verify,
    input  wire [7:0]          challenge,
    input  wire [31:0]         nonce,
    output reg                 busy,
    output reg                 enroll_done,
    output reg                 verify_done,
    output reg                 verify_ok,
    output reg                 enrolled,
    output reg  [ID_BITS-1:0]  device_id,
    output reg  [31:0]         expected_nonce
`ifdef TRUSTEDGE_ASIC_SERVICE_PORTS
    ,
    output wire                sample_start_o,
    output wire [7:0]          sample_challenge_o,
    input  wire                sample_busy_i,
    input  wire                sample_done_i,
    input  wire [ID_BITS-1:0]  sample_response_i
`endif
);
    reg        puf_start;
    wire       puf_busy;
    wire       puf_done;
    wire [31:0] puf_raw;

    reg        fe_enroll;
    reg        fe_verify;
    reg        fe_valid_pulse;
    wire       fe_enroll_done;
    wire       fe_verify_done;
    wire       fe_match;
    wire       fe_enrolled;
    wire [31:0] fe_id;

    reg [1:0]  round;
    reg [2:0]  st;
    reg        puf_done_q;
    localparam ST_IDLE=0, ST_PUF=1, ST_WAIT=2, ST_FINISH=3;

`ifdef TRUSTEDGE_ASIC_SERVICE_PORTS
    // The ASIC digital core retains enrollment, majority vote and anti-replay.
    // Only the raw challenge sampler crosses the physical-service boundary.
    assign sample_start_o = puf_start;
    assign sample_challenge_o = challenge;
    assign puf_busy = sample_busy_i;
    assign puf_done = sample_done_i;
    assign puf_raw = sample_response_i;
`else
    ropuf_core #(.RESPONSE_BITS(ID_BITS), .SAMPLE_CYCLES(24)) u_ropuf (
        .clk(clk), .rst_n(rst_n),
        .start(puf_start), .challenge(challenge),
        .busy(puf_busy), .done(puf_done), .response(puf_raw)
    );
`endif

    fuzzy_extractor #(.ID_BITS(ID_BITS)) u_fe (
        .clk(clk), .rst_n(rst_n),
        .enroll_cmd(fe_enroll),
        .verify_cmd(fe_verify),
        .raw_sample(puf_raw),
        .sample_valid(fe_valid_pulse),
        .enroll_done(fe_enroll_done),
        .verify_done(fe_verify_done),
        .verify_match(fe_match),
        .enrolled(fe_enrolled),
        .device_id(fe_id)
    );

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            st             <= ST_IDLE;
            busy           <= 0;
            puf_start      <= 0;
            fe_enroll      <= 0;
            fe_verify      <= 0;
            fe_valid_pulse <= 0;
            round          <= 0;
            enroll_done    <= 0;
            verify_done    <= 0;
            verify_ok      <= 0;
            enrolled       <= 0;
            device_id      <= 0;
            expected_nonce <= 32'd0;
            puf_done_q     <= 0;
        end else begin
            puf_start      <= 0;
            fe_valid_pulse <= 0;
            enroll_done    <= 0;
            verify_done    <= 0;
            verify_ok      <= 0;
            puf_done_q     <= puf_done;

            case (st)
                ST_IDLE: begin
                    busy <= 0;
                    if (cmd_enroll) begin
                        busy      <= 1;
                        fe_enroll <= 1;
                        fe_verify <= 0;
                        round     <= 0;
                        st        <= ST_PUF;
                    end else if (cmd_verify) begin
                        if (nonce == expected_nonce && enrolled) begin
                            busy      <= 1;
                            fe_enroll <= 0;
                            fe_verify <= 1;
                            round     <= 0;
                            st        <= ST_PUF;
                        end else begin
                            verify_done <= 1;
                            verify_ok   <= 0;
                        end
                    end
                end
                ST_PUF: begin
`ifdef TRUSTEDGE_ASIC_SERVICE_PORTS
                    // A completion may coincide with busy dropping.  Give the
                    // completion edge priority so no fourth sampler request is
                    // launched and discarded between majority-vote rounds.
                    if (puf_done && !puf_done_q) begin
                        puf_start <= 1'b0;
                        st <= ST_WAIT;
                    end else if (!puf_busy && !puf_start) begin
                        puf_start <= 1'b1;
                    end
`else
                    if (!puf_busy && !puf_start)
                        puf_start <= 1;
                    if (puf_done && !puf_done_q)
                        st <= ST_WAIT;
`endif
                end
                ST_WAIT: begin
                    fe_valid_pulse <= 1;
                    if (round == 2'd2)
                        st <= ST_FINISH;
                    else begin
                        round <= round + 2'd1;
                        st    <= ST_PUF;
                    end
                end
                ST_FINISH: begin
                    if (fe_enroll_done) begin
                        enrolled    <= 1;
                        device_id   <= fe_id;
                        enroll_done <= 1;
                        expected_nonce <= expected_nonce + 1;
                        fe_enroll <= 0;
                        fe_verify <= 0;
                        busy <= 0;
                        st   <= ST_IDLE;
                    end else if (fe_verify_done) begin
                        verify_done <= 1;
                        verify_ok   <= fe_match;
                        if (fe_match)
                            expected_nonce <= expected_nonce + 1;
                        fe_enroll <= 0;
                        fe_verify <= 0;
                        busy <= 0;
                        st   <= ST_IDLE;
                    end
                end
                default: st <= ST_IDLE;
            endcase
        end
    end
endmodule
