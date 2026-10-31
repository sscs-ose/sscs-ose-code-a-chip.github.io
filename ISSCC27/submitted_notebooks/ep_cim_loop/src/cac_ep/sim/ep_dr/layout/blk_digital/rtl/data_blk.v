// data_blk.v — DATA 블록 (반쪽마다 하나): DATA 레지스터 52 + latch 52 + 입력 구동 게이트 98 + nudge 주입기 SW 게이트 12
//   기준 논리: real_circuit/gen_chip_deck3.py 「레지스터」·「입력 구동 게이트」·「nudge 주입기 SW」 줄, chip_lib.py DFFR·and2, wu_lib.py DLATCH
//   DFFR  = 상승 에지 D 플립플롭, 비동기 reset (rst 높음 → q 0) → 여기서는 rstb 낮음 = reset (hvl dfrtp 의 RESET_B)
//   사슬  : q[0] <= sdi, q[k] <= q[k-1] (클록 data_clk). 먼저 넣은 bit 가 끝 (q[51]) 으로 간다
//   DLATCH: dload 높음 = 투명 (dl = q), 낮음 = 유지 (hvl dlxtp). reset 없음
//   입력 i (0..48)   : ga[i] = READ·dl[i], gb[i] = READ·~dl[i]  (입력 구동 NMOS 게이트, 행 2i·2i+1)
//   출력 k (0..2)    : sp[k] = READ·dl[49+k], sm[k] = READ·~dl[49+k], spb·smb = 반대 (주입기 TG 의 en·enb)
module data_blk #(
    parameter NI = 49,               // 입력 (표본 bit)
    parameter NO = 3                 // 출력 (nudge 방향 bit)
) (
    input  wire sdi,
    input  wire data_clk,
    input  wire dload,
    input  wire READ,
    input  wire rstb,
    output wire [NI-1:0] ga,
    output wire [NI-1:0] gb,
    output wire [NO-1:0] sp,
    output wire [NO-1:0] spb,
    output wire [NO-1:0] sm,
    output wire [NO-1:0] smb
);
    localparam N = NI + NO;
    reg [N-1:0] q;
    always @(posedge data_clk or negedge rstb)
        if (!rstb) q <= {N{1'b0}};
        else       q <= {q[N-2:0], sdi};

    reg [N-1:0] dl;
    always @(*)
        if (dload) dl = q;

    assign ga  = {NI{READ}} & dl[NI-1:0];
    assign gb  = {NI{READ}} & ~dl[NI-1:0];
    assign sp  = {NO{READ}} & dl[N-1:NI];
    assign sm  = {NO{READ}} & ~dl[N-1:NI];
    assign spb = ~sp;
    assign smb = ~sm;
endmodule
