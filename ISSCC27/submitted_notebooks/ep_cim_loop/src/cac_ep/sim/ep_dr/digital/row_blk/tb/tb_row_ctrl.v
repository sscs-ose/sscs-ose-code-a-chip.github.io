// tb_row_ctrl.v — row_ctrl (RTL 또는 게이트 netlist) 를 chip_lib 논리와 맞대 보는 testbench
//   기준 1 (decoder): tb/ref_rowl.v = chip_lib.py ROWL 의 NAND2·NOR2·INV 를 그대로 옮긴 모형 (gen_ref_rowl.py 가 만듦)
//   기준 2 (token 사슬): 아래 m1·m2 = gen_chip_deck2.py 의 DFFR 사슬 (XF<reg><k> prev <reg>_clk rst rstb <reg>q<k>, prev = sdi → q<k-1>)
//                         를 클록 펄스마다 task 안에서 한 칸씩 미는 모형. reset (rstb 낮음) 은 비동기로 모두 0
//   검사: 전역 입력 6 개 (sel_en PROG VER SENSE READb WRANY) 64 조합 × 행 106 × 출력 12 를 모형과 비교 (X 도 실패)
//   단계: reset → ROW1 무작위 100 bit → ROW2 무작위 6 bit → 반대 무늬 → token 하나 걷기 (ROW1 100 칸, ROW2 6 칸) → 클록 없이 reset
//   끝에 "TB_ROW: PASS" 또는 "TB_ROW: FAIL n" 을 찍는다
`timescale 1ns / 1ps
module tb_row_ctrl;
    localparam N1 = 100, N2 = 6, NR = N1 + N2;
    reg sdi = 0, row1_clk = 0, row2_clk = 0, rstb = 0;
    reg sel_en = 0, PROG = 0, VER = 0, SENSE = 0, READb = 1, WRANY = 0;
    wire [NR-1:0] wsel, wselb, wz, wzb, sns, snsb, wlv, wlvb, wlw, wlwb, wl0, wl0b;

    row_ctrl dut (.sdi(sdi), .row1_clk(row1_clk), .row2_clk(row2_clk), .rstb(rstb),
        .sel_en(sel_en), .PROG(PROG), .VER(VER), .SENSE(SENSE), .READb(READb), .WRANY(WRANY),
        .wsel(wsel), .wselb(wselb), .wz(wz), .wzb(wzb), .sns(sns), .snsb(snsb),
        .wlv(wlv), .wlvb(wlvb), .wlw(wlw), .wlwb(wlwb), .wl0(wl0), .wl0b(wl0b));

    // ── 기준 모형
    reg [N1-1:0] m1 = 0;
    reg [N2-1:0] m2 = 0;
    wire [NR-1:0] mt = {m2, m1};
    wire [NR-1:0] rwsel, rwselb, rwz, rwzb, rsns, rsnsb, rwlv, rwlvb, rwlw, rwlwb, rwl0, rwl0b;
    genvar g;
    generate for (g = 0; g < NR; g = g + 1) begin : g_ref
        ref_rowl u (mt[g], sel_en, PROG, VER, SENSE, READb, WRANY,
                    rwsel[g], rwselb[g], rwz[g], rwzb[g], rsns[g], rsnsb[g],
                    rwlv[g], rwlvb[g], rwlw[g], rwlwb[g], rwl0[g], rwl0b[g]);
    end endgenerate

    wire [12*NR-1:0] got = {wsel, wselb, wz, wzb, sns, snsb, wlv, wlvb, wlw, wlwb, wl0, wl0b};
    wire [12*NR-1:0] exp = {rwsel, rwselb, rwz, rwzb, rsns, rsnsb, rwlv, rwlvb, rwlw, rwlwb, rwl0, rwl0b};

    integer nerr = 0, ncmp = 0, ones_seen = 0, zeros_seen = 0;
    integer i, k, c;
    reg [8*12-1:0] onames [0:11];
    initial begin
        onames[0] = "wsel"; onames[1] = "wselb"; onames[2] = "wz"; onames[3] = "wzb"; onames[4] = "sns"; onames[5] = "snsb";
        onames[6] = "wlv"; onames[7] = "wlvb"; onames[8] = "wlw"; onames[9] = "wlwb"; onames[10] = "wl0"; onames[11] = "wl0b";
    end

    task set_glob(input [5:0] v);   // {sel_en, PROG, VER, SENSE, READb, WRANY}
        begin {sel_en, PROG, VER, SENSE, READb, WRANY} = v; end
    endtask

    task cmp(input [8*24-1:0] tag);
        integer o, r;
        begin
            #20;
            ncmp = ncmp + 1;
            if (got !== exp) begin
                for (o = 0; o < 12; o = o + 1)
                    for (r = 0; r < NR; r = r + 1)
                        if (got[(11 - o) * NR + r] !== exp[(11 - o) * NR + r]) begin
                            nerr = nerr + 1;
                            if (nerr <= 20)
                                $display("MISMATCH %0s glob=%b row %0d %0s got %b exp %b (t=%b)", tag,
                                         {sel_en, PROG, VER, SENSE, READb, WRANY}, r, onames[o],
                                         got[(11 - o) * NR + r], exp[(11 - o) * NR + r], mt[r]);
                        end
            end
        end
    endtask

    task all_glob(input [8*24-1:0] tag);   // 전역 64 조합 모두
        begin
            for (c = 0; c < 64; c = c + 1) begin set_glob(c[5:0]); cmp(tag); end
            for (k = 0; k < NR; k = k + 1) if (mt[k]) ones_seen = ones_seen + 1; else zeros_seen = zeros_seen + 1;
        end
    endtask

    // 클록 펄스 하나: sdi 를 클록 낮을 때 바꾸고, 상승 에지에서 모형도 한 칸 민다 (q0 <= sdi, qk <= q(k-1))
    task pulse1(input b);
        begin
            sdi = b; #30;
            m1 = {m1[N1-2:0], sdi};
            row1_clk = 1; #50; row1_clk = 0; #20;
        end
    endtask
    task pulse2(input b);
        begin
            sdi = b; #30;
            m2 = {m2[N2-2:0], sdi};
            row2_clk = 1; #50; row2_clk = 0; #20;
        end
    endtask

    reg [31:0] seed = 32'd20261028;
    initial begin
        rstb = 0; #100;
        all_glob("reset");
        rstb = 1; #50;
        // ROW1 무작위, ROW2 는 그대로 (클록 없음)
        for (i = 0; i < N1; i = i + 1) pulse1($random(seed));
        all_glob("row1_rand");
        // ROW2 무작위, ROW1 은 그대로
        for (i = 0; i < N2; i = i + 1) pulse2($random(seed));
        all_glob("row2_rand");
        // 반대 무늬 (행마다 t = 0 / 1 을 둘 다 보게)
        for (i = 0; i < N1; i = i + 1) pulse1(~m1[N1-1]);
        for (i = 0; i < N2; i = i + 1) pulse2(~m2[N2-1]);
        all_glob("complement");
        // token 하나 걷기 (칩 쓰임새: 한 행만 선택). 칸마다 무작위 전역 조합 2 개
        rstb = 0; #50; m1 = 0; m2 = 0; rstb = 1; #50;
        for (i = 0; i < N1; i = i + 1) begin
            pulse1(i == 0);
            set_glob($random(seed)); cmp("walk1");
            set_glob(6'b110110); cmp("walk1_prog");          // sel_en PROG · READb WRANY
        end
        for (i = 0; i < N2; i = i + 1) begin
            pulse2(i == 0);
            set_glob($random(seed)); cmp("walk2");
            set_glob(6'b100100); cmp("walk2_sense");         // sel_en SENSE
        end
        // 클록 없이 비동기 reset
        for (i = 0; i < N1; i = i + 1) pulse1(1'b1);
        for (i = 0; i < N2; i = i + 1) pulse2(1'b1);
        all_glob("all_ones");
        #7 rstb = 0; m1 = 0; m2 = 0; #13;
        all_glob("async_reset");
        $display("TB_ROW: compares %0d (x %0d bits), token=1 rows seen %0d, token=0 rows seen %0d",
                 ncmp, 12 * NR, ones_seen, zeros_seen);
        if (nerr == 0 && ones_seen > 0 && zeros_seen > 0) $display("TB_ROW: PASS");
        else $display("TB_ROW: FAIL %0d", nerr);
        $finish;
    end
endmodule
