// tb_col_ctrl.v — col_ctrl (RTL 또는 게이트 netlist) 를 chip_lib 논리와 맞대 보는 testbench ([digital/tb/tb_row_ctrl.v 사본을 고침])
//   기준 1 (decoder): tb/ref_coll.v = chip_lib.py COLL 의 NAND2·INV 를 그대로 옮긴 모형 (gen_ref_coll.py 가 만듦)
//   기준 2 (token 사슬): 아래 m1·m2 = gen_chip_deck3.py 의 DFFR 사슬 (XF<reg><k> prev <reg>_clk rst rstb <reg>q<k>, prev = sdi → q<k-1>)
//                         를 클록 펄스마다 task 안에서 한 칸씩 미는 모형. reset (rstb 낮음) 은 비동기로 모두 0
//   열 연결: c < 60 이면 t1 = col1q[c], t2 = col2q[c], 남는 열 60–63 은 t1 = t2 = lo (덱의 'lo')
//   검사: 전역 입력 5 개 (sel_en PROG VER SENSE WRANY) 32 조합 × lo 0/1 × 열 64 × 출력 10 을 모형과 비교 (X 도 실패)
//   단계: reset → COL1 무작위 60 bit → COL2 무작위 → 반대 무늬 → token 하나 걷기 (COL1·COL2 각 60 칸) → 비동기 reset
//   끝에 "TB_COL: PASS" 또는 "TB_COL: FAIL n" 을 찍는다
`timescale 1ns / 1ps
module tb_col_ctrl;
    localparam NH = 60, NC = 64, NO = 10;
    reg sdi = 0, col1_clk = 0, col2_clk = 0, rstb = 0;
    reg sel_en = 0, PROG = 0, VER = 0, SENSE = 0, WRANY = 0, lo = 0;
    wire [NC-1:0] wvw, wvwb, wz, wzb, vfy, vfyb, sns1, sns1b, sns2, sns2b;

    col_ctrl dut (.sdi(sdi), .col1_clk(col1_clk), .col2_clk(col2_clk), .rstb(rstb),
        .sel_en(sel_en), .PROG(PROG), .VER(VER), .SENSE(SENSE), .WRANY(WRANY), .lo(lo),
        .wvw(wvw), .wvwb(wvwb), .wz(wz), .wzb(wzb), .vfy(vfy), .vfyb(vfyb),
        .sns1(sns1), .sns1b(sns1b), .sns2(sns2), .sns2b(sns2b));

    // ── 기준 모형
    reg [NH-1:0] m1 = 0;
    reg [NH-1:0] m2 = 0;
    wire [NC-1:0] mt1 = {{(NC-NH){lo}}, m1};
    wire [NC-1:0] mt2 = {{(NC-NH){lo}}, m2};
    wire [NC-1:0] rwvw, rwvwb, rwz, rwzb, rvfy, rvfyb, rsns1, rsns1b, rsns2, rsns2b;
    genvar g;
    generate for (g = 0; g < NC; g = g + 1) begin : g_ref
        ref_coll u (mt1[g], mt2[g], sel_en, PROG, VER, SENSE, WRANY,
                    rwvw[g], rwvwb[g], rwz[g], rwzb[g], rvfy[g], rvfyb[g], rsns1[g], rsns1b[g], rsns2[g], rsns2b[g]);
    end endgenerate

    wire [NO*NC-1:0] got = {wvw, wvwb, wz, wzb, vfy, vfyb, sns1, sns1b, sns2, sns2b};
    wire [NO*NC-1:0] exp = {rwvw, rwvwb, rwz, rwzb, rvfy, rvfyb, rsns1, rsns1b, rsns2, rsns2b};

    integer nerr = 0, ncmp = 0, t1_ones = 0, t1_zeros = 0, t2_ones = 0, t2_zeros = 0;
    integer i, k, c;
    reg [8*8-1:0] onames [0:NO-1];
    initial begin
        onames[0] = "wvw"; onames[1] = "wvwb"; onames[2] = "wz"; onames[3] = "wzb"; onames[4] = "vfy";
        onames[5] = "vfyb"; onames[6] = "sns1"; onames[7] = "sns1b"; onames[8] = "sns2"; onames[9] = "sns2b";
    end

    task set_glob(input [5:0] v);   // {lo, sel_en, PROG, VER, SENSE, WRANY}
        begin {lo, sel_en, PROG, VER, SENSE, WRANY} = v; end
    endtask

    task cmp(input [8*24-1:0] tag);
        integer o, r;
        begin
            #20;
            ncmp = ncmp + 1;
            if (got !== exp) begin
                for (o = 0; o < NO; o = o + 1)
                    for (r = 0; r < NC; r = r + 1)
                        if (got[(NO - 1 - o) * NC + r] !== exp[(NO - 1 - o) * NC + r]) begin
                            nerr = nerr + 1;
                            if (nerr <= 20)
                                $display("MISMATCH %0s glob=%b col %0d %0s got %b exp %b (t1=%b t2=%b)", tag,
                                         {lo, sel_en, PROG, VER, SENSE, WRANY}, r, onames[o],
                                         got[(NO - 1 - o) * NC + r], exp[(NO - 1 - o) * NC + r], mt1[r], mt2[r]);
                        end
            end
        end
    endtask

    task all_glob(input [8*24-1:0] tag);   // lo × 전역 32 조합 = 64
        begin
            for (c = 0; c < 64; c = c + 1) begin set_glob(c[5:0]); cmp(tag); end
            for (k = 0; k < NH; k = k + 1) begin
                if (m1[k]) t1_ones = t1_ones + 1; else t1_zeros = t1_zeros + 1;
                if (m2[k]) t2_ones = t2_ones + 1; else t2_zeros = t2_zeros + 1;
            end
        end
    endtask

    // 클록 펄스 하나: sdi 를 클록 낮을 때 바꾸고, 상승 에지에서 모형도 한 칸 민다 (q0 <= sdi, qk <= q(k-1))
    task pulse1(input b);
        begin
            sdi = b; #30;
            m1 = {m1[NH-2:0], sdi};
            col1_clk = 1; #50; col1_clk = 0; #20;
        end
    endtask
    task pulse2(input b);
        begin
            sdi = b; #30;
            m2 = {m2[NH-2:0], sdi};
            col2_clk = 1; #50; col2_clk = 0; #20;
        end
    endtask

    reg [31:0] seed = 32'd20261028;
    initial begin
        rstb = 0; #100;
        all_glob("reset");
        rstb = 1; #50;
        // COL1 무작위, COL2 는 그대로 (클록 없음)
        for (i = 0; i < NH; i = i + 1) pulse1($random(seed));
        all_glob("col1_rand");
        // COL2 무작위, COL1 은 그대로
        for (i = 0; i < NH; i = i + 1) pulse2($random(seed));
        all_glob("col2_rand");
        // 반대 무늬 (열마다 t = 0 / 1 을 둘 다 보게)
        for (i = 0; i < NH; i = i + 1) pulse1(~m1[NH-1]);
        for (i = 0; i < NH; i = i + 1) pulse2(~m2[NH-1]);
        all_glob("complement");
        // token 하나 걷기 (칩 쓰임새: 한 열만 선택). 칸마다 무작위 전역 조합 + 쓰기·감지 조합
        rstb = 0; #50; m1 = 0; m2 = 0; rstb = 1; #50;
        for (i = 0; i < NH; i = i + 1) begin
            pulse1(i == 0);
            set_glob($random(seed)); cmp("walk1");
            set_glob(6'b011001); cmp("walk1_prog");           // sel_en PROG WRANY
            set_glob(6'b010101); cmp("walk1_ver");            // sel_en VER WRANY
        end
        for (i = 0; i < NH; i = i + 1) begin
            pulse2(i == 0);
            set_glob($random(seed)); cmp("walk2");
            set_glob(6'b010010); cmp("walk2_sense");          // sel_en SENSE
        end
        // 클록 없이 비동기 reset
        for (i = 0; i < NH; i = i + 1) pulse1(1'b1);
        for (i = 0; i < NH; i = i + 1) pulse2(1'b1);
        all_glob("all_ones");
        #7 rstb = 0; m1 = 0; m2 = 0; #13;
        all_glob("async_reset");
        $display("TB_COL: compares %0d (x %0d bits), t1=1 seen %0d, t1=0 %0d, t2=1 %0d, t2=0 %0d",
                 ncmp, NO * NC, t1_ones, t1_zeros, t2_ones, t2_zeros);
        if (nerr == 0 && t1_ones > 0 && t1_zeros > 0 && t2_ones > 0 && t2_zeros > 0) $display("TB_COL: PASS");
        else $display("TB_COL: FAIL %0d", nerr);
        $finish;
    end
endmodule
