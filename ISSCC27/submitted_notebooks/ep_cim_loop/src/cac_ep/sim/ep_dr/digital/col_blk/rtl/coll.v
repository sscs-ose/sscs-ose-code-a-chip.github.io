// coll.v — 열 하나의 decoder (real_circuit/chip_lib.py COLL 과 같은 논리)
//   입력: t1 = COL1 token bit, t2 = COL2 token bit, 전역 sel_en·PROG·VER·SENSE·WRANY (= PROG + VER)
//   s   = t1 · sel_en,   s2 = t2 · sel_en
//   wvw  = WRANY · s̄     (선택 안 된 열 → V_W, 쓰기·verify 억제)
//   wz   = PROG · s       (선택 열 → 0 V, 쓰기)
//   vfy  = VER · s        (선택 열 → verify 버스)
//   sns1 = SENSE · s      (감지 → C1),  sns2 = SENSE · s2 (감지 → C2)
//   출력마다 반대 신호 (…b) 도 낸다 (열 MUX 의 TG 가 ctl·ctlb 를 둘 다 받음) → 10 개
module coll (
    input  wire t1,
    input  wire t2,
    input  wire sel_en,
    input  wire PROG,
    input  wire VER,
    input  wire SENSE,
    input  wire WRANY,
    output wire wvw,  output wire wvwb,
    output wire wz,   output wire wzb,
    output wire vfy,  output wire vfyb,
    output wire sns1, output wire sns1b,
    output wire sns2, output wire sns2b
);
    wire s  = t1 & sel_en;
    wire s2 = t2 & sel_en;
    assign wvw   = WRANY & ~s;
    assign wvwb  = ~wvw;
    assign wz    = PROG & s;
    assign wzb   = ~wz;
    assign vfy   = VER & s;
    assign vfyb  = ~vfy;
    assign sns1  = SENSE & s;
    assign sns1b = ~sns1;
    assign sns2  = SENSE & s2;
    assign sns2b = ~sns2;
endmodule
