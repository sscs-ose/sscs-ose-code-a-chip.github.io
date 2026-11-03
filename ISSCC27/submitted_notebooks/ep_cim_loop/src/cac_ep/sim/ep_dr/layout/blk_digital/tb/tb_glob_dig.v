// tb_glob_dig.v — glob_dig (RTL 또는 게이트 netlist) 를 SPICE netlist 기준 모형 (tb/ref_glob_dig.v = chip_lib global_decode + config_block) 과 맞대 보는 testbench
//   비교: 출력 32 개 (반쪽 f·n 둘 다) ↔ 기준 모형 16 개를 자극마다 (가라앉은 뒤) 비교 (X 도 실패). sck 높을 때·낮을 때 둘 다 본다
//   덱 쓰임새 확인 (gen_chip_deck3.py cfg()): 설정 12 bit 를 CFG 끝 (ts_col2) 부터 밀고 sld 내리면 → 출력 = 그 설정의 decode
//     MODE 표 (00 IDLE / 01 FORM / 10 WRITE (pv 0 PROG, 1 VER) / 11 READ), SENSE = READ·wu_en, 클록 = sck·ts (sld 낮을 때만)
//   단계: reset → (m1 m0 pv wu_en) 16 조합 → 무작위 설정 64 개 → ts one-hot 5 개 (클록 펄스) → 밀던 중 reset → 무작위 (규칙 지킴: sld·sdi 는 sck 낮을 때만)
//   끝에 "TB_GLOB: PASS" 또는 "TB_GLOB: FAIL n"
`timescale 1ns / 1ps
module tb_glob_dig;
    reg sck = 0, sdi = 0, sld = 0, rst = 0;
    wire data_clk_f, data_clk_n, row1_clk_f, row1_clk_n, row2_clk_f, row2_clk_n, col1_clk_f, col1_clk_n, col2_clk_f, col2_clk_n;
    wire rstb_f, rstb_n, READ_f, READ_n, READb_f, READb_n, PROG_f, PROG_n, VER_f, VER_n, SENSE_f, SENSE_n, WRANY_f, WRANY_n;
    wire dload_f, dload_n, pol_f, pol_n, rd_out_f, rd_out_n, rd_out_b_f, rd_out_b_n;
    glob_dig dut (.sck(sck), .sdi(sdi), .sld(sld), .rst(rst),
        .data_clk_f(data_clk_f), .data_clk_n(data_clk_n), .row1_clk_f(row1_clk_f), .row1_clk_n(row1_clk_n),
        .row2_clk_f(row2_clk_f), .row2_clk_n(row2_clk_n), .col1_clk_f(col1_clk_f), .col1_clk_n(col1_clk_n),
        .col2_clk_f(col2_clk_f), .col2_clk_n(col2_clk_n), .rstb_f(rstb_f), .rstb_n(rstb_n), .READ_f(READ_f), .READ_n(READ_n),
        .READb_f(READb_f), .READb_n(READb_n), .PROG_f(PROG_f), .PROG_n(PROG_n), .VER_f(VER_f), .VER_n(VER_n),
        .SENSE_f(SENSE_f), .SENSE_n(SENSE_n), .WRANY_f(WRANY_f), .WRANY_n(WRANY_n), .dload_f(dload_f), .dload_n(dload_n),
        .pol_f(pol_f), .pol_n(pol_n), .rd_out_f(rd_out_f), .rd_out_n(rd_out_n), .rd_out_b_f(rd_out_b_f), .rd_out_b_n(rd_out_b_n));

    wire m1, m0, pv, pol, wu_en, rd_out, dload, ts_data, ts_row1, ts_row2, ts_col1, ts_col2;
    wire m1_b, m0_b, pv_b, pol_b, wu_en_b, rd_out_b, dload_b, ts_data_b, ts_row1_b, ts_row2_b, ts_col1_b, ts_col2_b;
    wire READ, READb, PROG, PROGb, VER, VERb, SENSE, WRANY, FORM, rstb, cfg_clk, sck_r, data_clk, row1_clk, row2_clk, col1_clk, col2_clk;
    ref_glob_dig refm (sck, sdi, sld, rst, m1, m0, pv, pol, wu_en, rd_out, dload, ts_data, ts_row1, ts_row2, ts_col1, ts_col2,
        m1_b, m0_b, pv_b, pol_b, wu_en_b, rd_out_b, dload_b, ts_data_b, ts_row1_b, ts_row2_b, ts_col1_b, ts_col2_b,
        READ, READb, PROG, PROGb, VER, VERb, SENSE, WRANY, FORM, rstb, cfg_clk, sck_r, data_clk, row1_clk, row2_clk, col1_clk, col2_clk);

    localparam NS = 16;
    wire [NS-1:0] gf = {data_clk_f, row1_clk_f, row2_clk_f, col1_clk_f, col2_clk_f, rstb_f, READ_f, READb_f, PROG_f, VER_f,
                        SENSE_f, WRANY_f, dload_f, pol_f, rd_out_f, rd_out_b_f};
    wire [NS-1:0] gn = {data_clk_n, row1_clk_n, row2_clk_n, col1_clk_n, col2_clk_n, rstb_n, READ_n, READb_n, PROG_n, VER_n,
                        SENSE_n, WRANY_n, dload_n, pol_n, rd_out_n, rd_out_b_n};
    wire [NS-1:0] ex = {data_clk, row1_clk, row2_clk, col1_clk, col2_clk, rstb, READ, READb, PROG, VER,
                        SENSE, WRANY, dload, pol, rd_out, rd_out_b};
    reg [8*12-1:0] sname [0:NS-1];
    initial begin
        sname[15] = "data_clk"; sname[14] = "row1_clk"; sname[13] = "row2_clk"; sname[12] = "col1_clk"; sname[11] = "col2_clk";
        sname[10] = "rstb"; sname[9] = "READ"; sname[8] = "READb"; sname[7] = "PROG"; sname[6] = "VER"; sname[5] = "SENSE";
        sname[4] = "WRANY"; sname[3] = "dload"; sname[2] = "pol"; sname[1] = "rd_out"; sname[0] = "rd_out_b";
    end

    integer nerr = 0, ncmp = 0, ndeck = 0, nclk = 0, i, k, c;
    reg [31:0] seed = 32'd20261028;
    reg [11:0] cfgv;                       // CFG[k] = cfgv[k]: m1 m0 pv pol wu_en rd_out dload ts_data ts_row1 ts_row2 ts_col1 ts_col2

    task cmp(input [8*16-1:0] tag);
        integer b;
        begin
            #20;
            ncmp = ncmp + 1;
            if (gf !== ex || gn !== ex) begin
                for (b = 0; b < NS; b = b + 1)
                    if (gf[b] !== ex[b] || gn[b] !== ex[b]) begin
                        nerr = nerr + 1;
                        if (nerr <= 20) $display("MISMATCH %0s %0s f %b n %b exp %b (sck %b sld %b rst %b)", tag, sname[b], gf[b], gn[b], ex[b], sck, sld, rst);
                    end
            end
        end
    endtask

    // 덱 쓰임새 확인: 출력이 설정 cfgv 의 decode 와 같은가 (sck 낮음)
    task deck_check(input [8*16-1:0] tag);
        reg rd, wr, fm, pg, ve;
        reg [NS-1:0] want;
        begin
            rd = cfgv[0] & cfgv[1]; wr = cfgv[0] & ~cfgv[1]; fm = ~cfgv[0] & cfgv[1];
            pg = fm | (wr & ~cfgv[2]); ve = wr & cfgv[2];
            want = {5'b0, ~rst, rd, ~rd, pg, ve, rd & cfgv[4], pg | ve, cfgv[6], cfgv[3], cfgv[5], ~cfgv[5]};
            ndeck = ndeck + 1;
            if (gf !== want || gn !== want) begin
                nerr = nerr + 1;
                if (nerr <= 20) $display("DECK %0s cfg %b: f %b n %b want %b", tag, cfgv, gf, gn, want);
            end
        end
    endtask

    task sck_pulse;                        // sck 낮을 때 바꾼 것을 두고 펄스 하나, 높을 때도 비교
        begin
            #10 sck = 1; cmp("sck_high"); #10 sck = 0; cmp("sck_low");
        end
    endtask

    task load_cfg(input [11:0] v, input chk_mid);   // gen_chip_deck3 cfg(): sld 높임 → CFG 끝부터 12 bit → sld 내림
        integer j;
        begin
            sld = 1; cmp("sld_up");
            for (j = 11; j >= 0; j = j - 1) begin
                sdi = v[j];
                #10 sck = 1; cmp("sft_high"); sdi = ~v[j];   // 높은 동안 sdi 를 반대로 (하강 에지에서 잡으면 틀리게)
                #10 sck = 0; cmp("sft_low");
                if (chk_mid) deck_check("hold_mid");         // 미는 동안 latch 닫힘 → 이전 설정 그대로
            end
            sdi = 0; sld = 0; cmp("sld_down");
            cfgv = v;
            deck_check("applied");
        end
    endtask

    task reg_clocks(input integer n);       // sld 낮음: 클록 = sck·ts. 높을 때 기대값도 본다
        integer j;
        reg [4:0] want;
        begin
            for (j = 0; j < n; j = j + 1) begin
                sdi = $random(seed);
                #10 sck = 1; cmp("rclk_high");
                want = cfgv[11:7];               // ts_data ts_row1 ts_row2 ts_col1 ts_col2
                nclk = nclk + 1;
                if ({data_clk_f, row1_clk_f, row2_clk_f, col1_clk_f, col2_clk_f} !== {want[0], want[1], want[2], want[3], want[4]} ||
                    {data_clk_n, row1_clk_n, row2_clk_n, col1_clk_n, col2_clk_n} !== {want[0], want[1], want[2], want[3], want[4]}) begin
                    nerr = nerr + 1;
                    if (nerr <= 20) $display("RCLK ts %b: f %b%b%b%b%b n %b%b%b%b%b", want, data_clk_f, row1_clk_f, row2_clk_f, col1_clk_f, col2_clk_f,
                                             data_clk_n, row1_clk_n, row2_clk_n, col1_clk_n, col2_clk_n);
                end
                #10 sck = 0; cmp("rclk_low");
                deck_check("rclk_low");          // 레지스터를 미는 동안 설정은 그대로
            end
        end
    endtask

    initial begin
        cfgv = 12'b0;
        #1 rst = 1; #100;
        cmp("reset"); deck_check("reset");
        sck_pulse; deck_check("reset_sck");
        rst = 0; #20;
        for (c = 0; c < 16; c = c + 1)                     // m1 m0 pv wu_en 모든 조합, 나머지 무작위
            load_cfg({$random(seed)} & 12'hFE8 | {c[3], c[2], c[1]} | (c[0] << 4) , c < 4);
        for (c = 0; c < 64; c = c + 1) begin load_cfg($random(seed), 0); reg_clocks(2); end
        for (k = 0; k < 5; k = k + 1) begin load_cfg((12'b1 << (7 + k)) | ($random(seed) & 12'h07F), 1); reg_clocks(3); end
        load_cfg(12'hF80, 0); reg_clocks(2);              // ts 다섯 개 모두
        // 밀던 중 reset: 레지스터 0, latch 는 닫혀 이전 설정 유지 → sld 내리면 0 (IDLE)
        load_cfg(12'hFFF, 0);
        sld = 1; cmp("sld_up2");
        sdi = 1; sck_pulse; sck_pulse;
        #3 rst = 1; cmp("rst_mid"); deck_check("rst_mid_hold");
        sld = 0; cmp("rst_apply"); cfgv = 12'b0; deck_check("rst_apply");
        rst = 0; #20;
        // 무작위 (규칙: sld·sdi 는 sck 낮을 때만 바꿈, rst 는 아무 때나)
        for (i = 0; i < 400; i = i + 1) begin
            case ($random(seed) & 3)
                0: begin sdi = $random(seed); cmp("r_sdi"); end
                1: begin sld = ~sld; cmp("r_sld"); end
                2: sck_pulse;
                3: begin #3 rst = ($random(seed) & 7) == 0; cmp("r_rst"); end
            endcase
        end
        $display("TB_GLOB: compares %0d (x %0d signals x 2 halves), deck checks %0d, register-clock checks %0d", ncmp, NS, ndeck, nclk);
        if (nerr == 0) $display("TB_GLOB: PASS");
        else $display("TB_GLOB: FAIL %0d", nerr);
        $finish;
    end
endmodule
