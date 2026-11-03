// col_ctrl.v — 열 제어 디지털 (배열마다 하나): COL1 token 60 + COL2 token 60 + 열 decoder (COLL) 64
//   기준 논리: real_circuit/chip_lib.py (DFFR, COLL), 연결 = real_circuit/gen_chip_deck3.py 228–281 줄
//   DFFR = 상승 에지 D 플립플롭, 비동기 reset (rst 높음 → q 0) → 여기서는 rstb 낮음 = reset (hvl dfrtp 의 RESET_B)
//   사슬: q[0] <= sdi, q[k] <= q[k-1]. COL1 은 col1_clk, COL2 는 col2_clk 로 민다 (둘 다 sdi 에서 들어옴)
//   열 c (hidden, c < NH): t1 = col1q[c], t2 = col2q[c].  남는 열 (c >= NH): t1 = t2 = lo
//   lo = 입력 핀 (칩에서는 VSS 레벨 상수, 덱의 "Vlo lo 0 -2.5"). 상수 tie 셀 (conb_1) 은 LVS 가 깨져 쓰지 않으므로 핀으로 받는다
module col_ctrl #(
    parameter NH = 60,               // hidden 열 (token 이 있는 열)
    parameter NC = 64                // 전체 열
) (
    input  wire sdi,
    input  wire col1_clk,
    input  wire col2_clk,
    input  wire rstb,
    input  wire sel_en,
    input  wire PROG,
    input  wire VER,
    input  wire SENSE,
    input  wire WRANY,
    input  wire lo,
    output wire [NC-1:0] wvw,  output wire [NC-1:0] wvwb,
    output wire [NC-1:0] wz,   output wire [NC-1:0] wzb,
    output wire [NC-1:0] vfy,  output wire [NC-1:0] vfyb,
    output wire [NC-1:0] sns1, output wire [NC-1:0] sns1b,
    output wire [NC-1:0] sns2, output wire [NC-1:0] sns2b
);
    reg [NH-1:0] col1q;
    reg [NH-1:0] col2q;

    always @(posedge col1_clk or negedge rstb)
        if (!rstb) col1q <= {NH{1'b0}};
        else       col1q <= {col1q[NH-2:0], sdi};

    always @(posedge col2_clk or negedge rstb)
        if (!rstb) col2q <= {NH{1'b0}};
        else       col2q <= {col2q[NH-2:0], sdi};

    wire [NC-1:0] t1 = {{(NC-NH){lo}}, col1q};
    wire [NC-1:0] t2 = {{(NC-NH){lo}}, col2q};

    genvar c;
    generate
        for (c = 0; c < NC; c = c + 1) begin : g_col
            coll u_coll (
                .t1(t1[c]), .t2(t2[c]), .sel_en(sel_en), .PROG(PROG), .VER(VER), .SENSE(SENSE), .WRANY(WRANY),
                .wvw(wvw[c]), .wvwb(wvwb[c]), .wz(wz[c]), .wzb(wzb[c]), .vfy(vfy[c]), .vfyb(vfyb[c]),
                .sns1(sns1[c]), .sns1b(sns1b[c]), .sns2(sns2[c]), .sns2b(sns2b[c]));
        end
    endgenerate
endmodule
