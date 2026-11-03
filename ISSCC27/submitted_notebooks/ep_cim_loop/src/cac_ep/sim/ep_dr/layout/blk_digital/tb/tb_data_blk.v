// tb_data_blk.v — data_blk (RTL 또는 게이트 netlist) 를 SPICE netlist 기준 모형 (tb/ref_data_blk.v, gen_ref.py) 과 맞대 보는 testbench
//   비교: 출력 110 bit (ga 49, gb 49, sp spb sm smb 각 3) 를 자극이 바뀔 때마다 (가라앉은 뒤) 기준 모형과 비교 (X 도 실패)
//   더해서 덱의 쓰임새 확인: bits[51..0] 을 bits[51] 부터 밀고 dload → ga[i] = READ·bits[i], sp[k] = READ·bits[49+k] (gen_chip_deck3 「q_k = bits[k]」)
//   단계: reset (dload 높음) → latch 닫고 무작위 52 bit (출력 유지) → dload (적용) → latch 연 채로 밀기 (출력이 클록마다 따라감)
//         → 덱 순서 확인 20 회 → reset: latch 열림 (출력 0 쪽) / 닫힘 (유지) → READ 무작위 토글
//   끝에 "TB_DATA: PASS" 또는 "TB_DATA: FAIL n"
`timescale 1ns / 1ps
module tb_data_blk;
    localparam NI = 49, NO = 3, N = NI + NO;
    reg sdi = 0, data_clk = 0, dload = 1, READ = 0, rst = 0;
    wire rstb = ~rst;
    wire dload_b = ~dload;
    wire [NI-1:0] ga, gb, rga, rgb;
    wire [NO-1:0] sp, spb, sm, smb, rsp, rspb, rsm, rsmb;

    data_blk dut (.sdi(sdi), .data_clk(data_clk), .dload(dload), .READ(READ), .rstb(rstb),
                  .ga(ga), .gb(gb), .sp(sp), .spb(spb), .sm(sm), .smb(smb));
    ref_data_bus refm (.sdi(sdi), .data_clk(data_clk), .dload(dload), .dload_b(dload_b), .READ(READ), .rst(rst), .rstb(rstb),
                       .ga(rga), .gb(rgb), .sp(rsp), .spb(rspb), .sm(rsm), .smb(rsmb));

    wire [2*NI+4*NO-1:0] got = {ga, gb, sp, spb, sm, smb};
    wire [2*NI+4*NO-1:0] exp = {rga, rgb, rsp, rspb, rsm, rsmb};

    integer nerr = 0, ncmp = 0, nbits = 0, i, j, rep;
    reg [31:0] seed = 32'd20261028;
    reg [N-1:0] bits;

    task cmp(input [8*16-1:0] tag);
        integer b;
        begin
            #20;
            ncmp = ncmp + 1;
            if (got !== exp) begin
                for (b = 0; b < 2 * NI + 4 * NO; b = b + 1)
                    if (got[b] !== exp[b]) begin
                        nerr = nerr + 1;
                        if (nerr <= 20) $display("MISMATCH %0s bit %0d got %b exp %b (READ %b dload %b rst %b)", tag, b, got[b], exp[b], READ, dload, rst);
                    end
            end
        end
    endtask

    task cmp2(input [8*16-1:0] tag);   // READ 0 / 1 둘 다
        begin READ = 0; cmp(tag); READ = 1; cmp(tag); end
    endtask

    task pulse(input b);                // sdi 를 클록 낮을 때 바꾸고 상승 에지. 높은 동안 sdi 를 반대로 (하강 에지에서 잡으면 틀리게)
        begin
            sdi = b; #30;
            data_clk = 1; #20; sdi = ~b; #30; data_clk = 0; #20;
        end
    endtask

    initial begin
        #1 rst = 1; #100;                                    // 0 → 1 (비동기 reset 에지)
        cmp2("reset");
        rst = 0; #20;
        dload = 0; #20;
        for (i = 0; i < N; i = i + 1) begin pulse($random(seed)); READ = $random(seed); cmp("shift_closed"); end
        cmp2("closed_end");
        dload = 1; cmp2("load");
        for (i = 0; i < 3 * N; i = i + 1) begin pulse($random(seed)); READ = $random(seed); cmp("shift_open"); end
        dload = 0; #20;
        // 덱 순서: bits[N-1] 먼저 → 끝에 q[k] = bits[k]
        for (rep = 0; rep < 20; rep = rep + 1) begin
            for (j = 0; j < N; j = j + 1) bits[j] = $random(seed);
            if (rep == 0) bits = {N{1'b0}} | 1'b1;           // 걷는 1: bits[0] 만
            if (rep == 1) bits = {1'b1, {(N-1){1'b0}}};     //          bits[51] 만
            for (j = N - 1; j >= 0; j = j - 1) pulse(bits[j]);
            dload = 1; #10; dload = 0;
            READ = 1; cmp("deck_order");
            for (j = 0; j < N; j = j + 1) begin
                nbits = nbits + 1;
                if (j < NI) begin
                    if (ga[j] !== bits[j] || gb[j] !== ~bits[j]) begin
                        nerr = nerr + 1;
                        if (nerr <= 20) $display("ORDER rep %0d input %0d: ga %b gb %b bit %b", rep, j, ga[j], gb[j], bits[j]);
                    end
                end else if (sp[j-NI] !== bits[j] || sm[j-NI] !== ~bits[j] || spb[j-NI] !== ~bits[j] || smb[j-NI] !== bits[j]) begin
                    nerr = nerr + 1;
                    if (nerr <= 20) $display("ORDER rep %0d out %0d: sp %b sm %b bit %b", rep, j - NI, sp[j-NI], sm[j-NI], bits[j]);
                end
            end
            READ = 0; cmp("deck_read0");
        end
        // reset: latch 닫힘이면 출력 유지 (latch 에는 reset 없음), 열면 0 쪽
        for (i = 0; i < N; i = i + 1) pulse(1'b1);
        dload = 1; #10; dload = 0; cmp2("all_ones");
        #7 rst = 1; #13; cmp2("rst_closed");
        dload = 1; cmp2("rst_open");
        rst = 0; dload = 0; #20;
        for (i = 0; i < 200; i = i + 1) begin
            case ($random(seed) & 3)
                0: pulse($random(seed));
                1: dload = ~dload;
                2: READ = ~READ;
                3: begin #3 rst = ($random(seed) & 7) == 0; end
            endcase
            cmp("random");
        end
        rst = 0;
        $display("TB_DATA: compares %0d (x %0d bits), deck-order bits %0d", ncmp, 2 * NI + 4 * NO, nbits);
        if (nerr == 0) $display("TB_DATA: PASS");
        else $display("TB_DATA: FAIL %0d", nerr);
        $finish;
    end
endmodule
