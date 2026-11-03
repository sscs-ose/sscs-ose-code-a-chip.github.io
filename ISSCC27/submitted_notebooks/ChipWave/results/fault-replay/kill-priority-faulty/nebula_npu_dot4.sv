`default_nettype none
module nebula_npu_dot4 (
    input logic clk, rst_n,
    input logic req_valid,
    output logic req_ready,
    input logic [31:0] req_a, req_b,
    output logic rsp_valid,
    input logic rsp_ready,
    output logic [31:0] rsp_data,
    input logic kill
);
    typedef enum logic [1:0] {IDLE, P0, P1, RSP} phase_t;
    phase_t phase;
    logic signed [15:0] p0, p1, p2, p3;
    logic signed [16:0] pair0, pair1;
    logic signed [17:0] total;
    logic signed [31:0] result;

    assign req_ready = rst_n && !kill && phase == IDLE;
    assign rsp_valid = rst_n && phase == RSP;
    assign rsp_data = rst_n ? result : 32'b0;
    assign total = $signed({pair0[16], pair0}) + $signed({pair1[16], pair1});

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            phase <= IDLE;
            p0 <= 0; p1 <= 0; p2 <= 0; p3 <= 0;
            pair0 <= 0; pair1 <= 0; result <= 0;
        end else if (kill) begin
            phase <= IDLE;
            p0 <= 0; p1 <= 0; p2 <= 0; p3 <= 0;
            pair0 <= 0; pair1 <= 0; result <= 0;
        end else begin
            case (phase)
                IDLE: if (req_valid) begin
                    p0 <= $signed(req_a[7:0]) * $signed(req_b[7:0]);
                    p1 <= $signed(req_a[15:8]) * $signed(req_b[15:8]);
                    p2 <= $signed(req_a[23:16]) * $signed(req_b[23:16]);
                    p3 <= $signed(req_a[31:24]) * $signed(req_b[31:24]);
                    phase <= P0;
                end
                P0: begin
                    pair0 <= $signed({p0[15], p0}) + $signed({p1[15], p1});
                    pair1 <= $signed({p2[15], p2}) + $signed({p3[15], p3});
                    phase <= P1;
                end
                P1: begin
                    result <= {{14{total[17]}}, total};
                    phase <= RSP;
                end
                RSP: if (rsp_ready) phase <= IDLE;
                default: phase <= IDLE;
            endcase
        end
    end
endmodule
`default_nettype wire
