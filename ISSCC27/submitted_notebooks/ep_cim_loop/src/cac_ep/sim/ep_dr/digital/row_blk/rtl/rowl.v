// rowl.v — 행 하나의 decoder (chip_lib.py ROWL, v2b 와 같은 논리)
//   입력: t = token bit, 전역 sel_en·PROG (FORM + WRITE-program)·VER·SENSE·READb·WRANY (= PROG + VER)
//   s   = t · sel_en
//   wsel = WRANY · s      (선택 행 → V_W, 쓰기·verify)
//   wz   = WRANY · s̄      (선택 안 된 행 → 0 V, 쓰기·verify)
//   sns  = SENSE · s      (sense 버스)
//   wlv  = READ + VER · s = NAND(READb, NAND(VER, s))   (WL → VDD)
//   wlw  = PROG · s       (WL → V_WL, 선택 쓰기)
//   wl0  = NOR(wlv, wlw)  (WL → VSS)
//   출력마다 반대 신호 (…b) 도 낸다 (행 MUX 의 TG 가 en·enb 를 둘 다 받음) → 12 개
module rowl (
    input  wire t,
    input  wire sel_en,
    input  wire PROG,
    input  wire VER,
    input  wire SENSE,
    input  wire READb,
    input  wire WRANY,
    output wire wsel, output wire wselb,
    output wire wz,   output wire wzb,
    output wire sns,  output wire snsb,
    output wire wlv,  output wire wlvb,
    output wire wlw,  output wire wlwb,
    output wire wl0,  output wire wl0b
);
    wire s = t & sel_en;
    assign wsel  = WRANY & s;
    assign wselb = ~wsel;
    assign wz    = WRANY & ~s;
    assign wzb   = ~wz;
    assign sns   = SENSE & s;
    assign snsb  = ~sns;
    assign wlv   = ~(READb & ~(VER & s));
    assign wlvb  = ~wlv;
    assign wlw   = PROG & s;
    assign wlwb  = ~wlw;
    assign wl0   = ~(wlv | wlw);
    assign wl0b  = ~wl0;
endmodule
