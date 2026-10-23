// ============================================================================
// ota_gate.v  -  OTA policy-state demo gate
// ============================================================================
// sig_valid, image_hash and expected_hash are supplied by upstream logic.
// This module does not calculate a firmware hash or verify a signature.
module ota_gate (
    input  wire       clk,
    input  wire       rst_n,
    input  wire       puf_session_ok,
    input  wire       sig_valid,
    input  wire       ota_begin,
    input  wire       ota_commit,
    input  wire [31:0] image_hash,
    input  wire [31:0] expected_hash,
    output reg        ota_active,
    output reg        commit_ok,
    output reg        commit_deny,
    output reg [2:0]  status
);
    // status: bit0=idle bit1=active bit2=last_deny
    localparam S_IDLE=0, S_RX=1, S_CHECK=2;

    reg [1:0] st;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            st <= S_IDLE;
            ota_active <= 0;
            commit_ok <= 0;
            commit_deny <= 0;
            status <= 3'b001;
        end else begin
            case (st)
                S_IDLE: begin
                    ota_active <= 0;
                    status <= {commit_deny, 1'b0, 1'b1};
                    if (ota_begin && puf_session_ok) begin
                        commit_ok <= 0;
                        commit_deny <= 0;
                        ota_active <= 1;
                        status <= 3'b010;
                        st <= S_RX;
                    end
                end
                S_RX: begin
                    status <= {commit_deny, 1'b1, 1'b0};
                    if (ota_commit) begin
                        st <= S_CHECK;
                    end
                end
                S_CHECK: begin
                    if (!puf_session_ok || !sig_valid || image_hash !== expected_hash) begin
                        commit_deny <= 1;
                        status <= 3'b101;
                    end else begin
                        commit_ok <= 1;
                        status <= 3'b001;
                    end
                    ota_active <= 0;
                    st <= S_IDLE;
                end
                default: st <= S_IDLE;
            endcase
        end
    end
endmodule
