// row_ctrl.v — 행 제어 디지털 블록 (반쪽마다 하나): ROW1 token 100 + ROW2 token 6 + 행 decoder (ROWL) 106
//   기준 논리: real_circuit/chip_lib.py (DFFR, ROWL), real_circuit/gen_chip_deck2.py (레지스터 사슬·행 연결)
//   DFFR = 상승 에지 D 플립플롭, 비동기 reset (rst 높음 → q 0) → 여기서는 rstb 낮음 = reset (hvl dfrtp 의 RESET_B)
//   사슬: q[0] <= sdi, q[k] <= q[k-1]. ROW1 은 row1_clk, ROW2 는 row2_clk 로 민다 (둘 다 sdi 에서 들어옴)
//   행 r 의 token: r < N1 이면 row1q[r], 아니면 row2q[r - N1]
module row_ctrl #(
    parameter N1 = 100,              // ROW1 이 맡는 행 (입력 + bias)
    parameter N2 = 6                 // ROW2 이 맡는 행 (출력)
) (
    input  wire sdi,
    input  wire row1_clk,
    input  wire row2_clk,
    input  wire rstb,
    input  wire sel_en,
    input  wire PROG,
    input  wire VER,
    input  wire SENSE,
    input  wire READb,
    input  wire WRANY,
    output wire [N1+N2-1:0] wsel, output wire [N1+N2-1:0] wselb,
    output wire [N1+N2-1:0] wz,   output wire [N1+N2-1:0] wzb,
    output wire [N1+N2-1:0] sns,  output wire [N1+N2-1:0] snsb,
    output wire [N1+N2-1:0] wlv,  output wire [N1+N2-1:0] wlvb,
    output wire [N1+N2-1:0] wlw,  output wire [N1+N2-1:0] wlwb,
    output wire [N1+N2-1:0] wl0,  output wire [N1+N2-1:0] wl0b
);
    reg [N1-1:0] row1q;
    reg [N2-1:0] row2q;

    always @(posedge row1_clk or negedge rstb)
        if (!rstb) row1q <= {N1{1'b0}};
        else       row1q <= {row1q[N1-2:0], sdi};

    always @(posedge row2_clk or negedge rstb)
        if (!rstb) row2q <= {N2{1'b0}};
        else       row2q <= {row2q[N2-2:0], sdi};

    wire [N1+N2-1:0] tok = {row2q, row1q};   // tok[r] = 행 r 의 token

    genvar r;
    generate
        for (r = 0; r < N1 + N2; r = r + 1) begin : g_row
            rowl u_rowl (
                .t(tok[r]), .sel_en(sel_en), .PROG(PROG), .VER(VER), .SENSE(SENSE), .READb(READb), .WRANY(WRANY),
                .wsel(wsel[r]), .wselb(wselb[r]), .wz(wz[r]), .wzb(wzb[r]), .sns(sns[r]), .snsb(snsb[r]),
                .wlv(wlv[r]), .wlvb(wlvb[r]), .wlw(wlw[r]), .wlwb(wlwb[r]), .wl0(wl0[r]), .wl0b(wl0b[r]));
        end
    endgenerate
endmodule
