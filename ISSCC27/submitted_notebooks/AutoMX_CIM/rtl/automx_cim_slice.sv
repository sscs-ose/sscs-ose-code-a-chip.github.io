// AutoMX-CIM Phase-2 baseline: one complete K=32 fixed-point projection slice.
//
// Comparison boundary: GROUP_ACC_Q is signed Q*.24 before the E8M0 scale.
// P/N, alpha, beta, col_v and dense residual are ports so a testbench or a
// future SRAM wrapper can load the exact files emitted by automx_cim.export.
`default_nettype none
module automx_cim_slice #(
    parameter int N = 32,
    parameter int M = 32,
    parameter int ACT_W = 5,
    parameter int META_W = 16,
    parameter int META_FRAC = 12,
    parameter int ACC_W = 48
) (
    input  logic signed [ACT_W*N-1:0]       ACT_X2,
    input  logic        [N*M-1:0]           WPOS,
    input  logic        [N*M-1:0]           WNEG,
    input  logic        [META_W*N-1:0]      COL_V_Q,
    input  logic        [META_W*M-1:0]      ALPHA_Q,
    input  logic signed [META_W*M-1:0]      BETA_Q,
    input  logic signed [META_W*N*M-1:0]    RESIDUAL_Q,
    output logic signed [ACC_W*M-1:0]       GROUP_ACC_Q
);
    localparam int ALIGN = META_FRAC;
    localparam longint signed ACC_MAX = (64'sd1 <<< (ACC_W-1)) - 1;
    localparam longint signed ACC_MIN = -(64'sd1 <<< (ACC_W-1));

    integer r;
    integer c;
    longint signed act_value;
    longint signed v_value;
    longint signed alpha_value;
    longint signed beta_value;
    longint signed residual_value;
    longint signed act_sum;
    longint signed base_sum;
    longint signed residual_sum;
    longint signed combined;

    initial begin
        if (N != 32) $fatal(1, "automx_cim_slice baseline requires N=32");
        if (ACC_W > 63) $fatal(1, "ACC_W must fit the signed longint oracle");
    end

    always_comb begin
        GROUP_ACC_Q = '0;
        for (c = 0; c < M; c = c + 1) begin
            act_sum = 0;
            base_sum = 0;
            residual_sum = 0;
            alpha_value = {{(64-META_W){1'b0}}, ALPHA_Q[META_W*c +: META_W]};
            beta_value = $signed({{(64-META_W){BETA_Q[META_W*c + META_W-1]}},
                                  BETA_Q[META_W*c +: META_W]});
            for (r = 0; r < N; r = r + 1) begin
                act_value = $signed({{(64-ACT_W){ACT_X2[ACT_W*r + ACT_W-1]}},
                                     ACT_X2[ACT_W*r +: ACT_W]});
                v_value = {{(64-META_W){1'b0}}, COL_V_Q[META_W*r +: META_W]};
                residual_value = $signed({{(64-META_W){RESIDUAL_Q[META_W*(r*M+c) + META_W-1]}},
                                          RESIDUAL_Q[META_W*(r*M+c) +: META_W]});
                act_sum = act_sum + act_value;
                if (WPOS[r*M+c]) base_sum = base_sum + act_value * v_value;
                if (WNEG[r*M+c]) base_sum = base_sum - act_value * v_value;
                residual_sum = residual_sum + act_value * residual_value;
            end
            combined = alpha_value * base_sum
                     + ((beta_value * act_sum + residual_sum) <<< ALIGN);
            if (combined > ACC_MAX)
                GROUP_ACC_Q[ACC_W*c +: ACC_W] = ACC_MAX[ACC_W-1:0];
            else if (combined < ACC_MIN)
                GROUP_ACC_Q[ACC_W*c +: ACC_W] = ACC_MIN[ACC_W-1:0];
            else
                GROUP_ACC_Q[ACC_W*c +: ACC_W] = combined[ACC_W-1:0];
        end
    end
endmodule
`default_nettype wire
