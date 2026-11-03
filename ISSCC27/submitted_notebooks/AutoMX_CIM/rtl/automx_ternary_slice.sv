// AutoMX-CIM v0 base datapath: one MXFP4 block x ternary CiROM slice.
//
// ACT_X2 carries signed E2M1 element magnitudes multiplied by two:
// {0, +/-1, +/-2, +/-3, +/-4, +/-6, +/-8, +/-12}.  The caller applies the
// shared E8M0 scale as 2**(scale_e8m0-128), then alpha/beta/residual paths.
// Keeping those metadata paths outside this first slice makes the physical
// P/N array arithmetic independently verifiable.
`default_nettype none
module automx_ternary_slice #(
    parameter int N = 32,
    parameter int M = 32,
    parameter int ACT_W = 5,
    parameter int ACC_W = 16,
    // Flat index is r*M+c, matching the Python exporter KxM row-major image.
    parameter logic [N*M-1:0] WPOS = '0,
    parameter logic [N*M-1:0] WNEG = '0
) (
    input  logic signed [ACT_W*N-1:0] ACT_X2,
    output logic signed [ACC_W*M-1:0] ACC_X2
);
    integer r;
    integer c;
    integer signed sum;
    integer signed act_value;

    always_comb begin
        ACC_X2 = '0;
        for (c = 0; c < M; c = c + 1) begin
            sum = 0;
            for (r = 0; r < N; r = r + 1) begin
                act_value = $signed({{(32-ACT_W){ACT_X2[ACT_W*r + ACT_W-1]}},
                                     ACT_X2[ACT_W*r +: ACT_W]});
                if (WPOS[r*M+c]) sum = sum + act_value;
                if (WNEG[r*M+c]) sum = sum - act_value;
            end
            ACC_X2[ACC_W*c +: ACC_W] = sum[ACC_W-1:0];
        end
    end
endmodule
`default_nettype wire
