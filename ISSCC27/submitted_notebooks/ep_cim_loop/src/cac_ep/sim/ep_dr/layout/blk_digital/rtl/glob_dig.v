// glob_dig.v — 전역 디지털 블록 (칩에 하나): 설정 레지스터 12 bit + latch 12 + 동작 decode + 레지스터 클록 gating·buffer
//   기준 논리: real_circuit/chip_lib.py config_block(buf=True)·global_decode()·CKBUF·DFFR, wu_lib.py DLATCH
//   입력 (패드, 레벨 변환 뒤 5 V 영역): sck sdi sld rst
//   설정 레지스터: cfg_clk = sck·sld 로 민다 (cq[0] <= sdi, cq[k] <= cq[k-1]), rst 높음 = 0 (비동기)
//   latch: sld 낮음 (sldb 높음) = 투명 → 설정 적용. 설정 bit k = CFG[k] (m1 m0 pv pol wu_en rd_out dload ts_data ts_row1 ts_row2 ts_col1 ts_col2)
//   decode (MODE 00 IDLE, 01 FORM, 10 WRITE, 11 READ): READ = m1·m0, WRm = m1·~m0, FORM = ~m1·m0, PROG = FORM + WRm·~pv,
//          VER = WRm·pv, WRANY = PROG + VER, SENSE = READ·wu_en
//   레지스터 클록: <reg>_clk = CKBUF(sck·sldb·ts_<reg>), reg = data row1 row2 col1 col2
//   레이아웃에서 레지스터·decoder 가 반쪽 (free f / nudge n) 마다 한 벌 → 밖으로 나가는 신호마다 반쪽별 출력 (_f, _n) 과 따로 구동 셀
module glob_dig (
    input  wire sck,
    input  wire sdi,
    input  wire sld,
    input  wire rst,
    output wire data_clk_f, output wire data_clk_n,
    output wire row1_clk_f, output wire row1_clk_n,
    output wire row2_clk_f, output wire row2_clk_n,
    output wire col1_clk_f, output wire col1_clk_n,
    output wire col2_clk_f, output wire col2_clk_n,
    output wire rstb_f,     output wire rstb_n,
    output wire READ_f,     output wire READ_n,
    output wire READb_f,    output wire READb_n,
    output wire PROG_f,     output wire PROG_n,
    output wire VER_f,      output wire VER_n,
    output wire SENSE_f,    output wire SENSE_n,
    output wire WRANY_f,    output wire WRANY_n,
    output wire dload_f,    output wire dload_n,
    output wire pol_f,      output wire pol_n,
    output wire rd_out_f,   output wire rd_out_n,
    output wire rd_out_b_f, output wire rd_out_b_n
);
    wire sldb = ~sld;
    wire rstb = ~rst;
    wire cfg_clk = sck & sld;
    wire sck_r = sck & sldb;

    reg [11:0] cq;
    always @(posedge cfg_clk or negedge rstb)
        if (!rstb) cq <= 12'b0;
        else       cq <= {cq[10:0], sdi};

    reg [11:0] cfg;
    always @(*)
        if (sldb) cfg = cq;

    wire m1 = cfg[0], m0 = cfg[1], pv = cfg[2], pol = cfg[3], wu_en = cfg[4], rd_out = cfg[5], dload = cfg[6];
    wire ts_data = cfg[7], ts_row1 = cfg[8], ts_row2 = cfg[9], ts_col1 = cfg[10], ts_col2 = cfg[11];

    wire READ  = m1 & m0;
    wire WRm   = m1 & ~m0;
    wire FORM  = ~m1 & m0;
    wire PROG  = FORM | (WRm & ~pv);
    wire VER   = WRm & pv;
    wire WRANY = PROG | VER;
    wire SENSE = READ & wu_en;

    ckdrv u_ck_data (.a(sck_r), .en(ts_data), .yf(data_clk_f), .yn(data_clk_n));
    ckdrv u_ck_row1 (.a(sck_r), .en(ts_row1), .yf(row1_clk_f), .yn(row1_clk_n));
    ckdrv u_ck_row2 (.a(sck_r), .en(ts_row2), .yf(row2_clk_f), .yn(row2_clk_n));
    ckdrv u_ck_col1 (.a(sck_r), .en(ts_col1), .yf(col1_clk_f), .yn(col1_clk_n));
    ckdrv u_ck_col2 (.a(sck_r), .en(ts_col2), .yf(col2_clk_f), .yn(col2_clk_n));

    obuf8 u_ob_rstb   (.a(rstb),    .yf(rstb_f),     .yn(rstb_n));
    obuf4 u_ob_read   (.a(READ),    .yf(READ_f),     .yn(READ_n));
    obuf4 u_ob_readb  (.a(~READ),   .yf(READb_f),    .yn(READb_n));
    obuf4 u_ob_prog   (.a(PROG),    .yf(PROG_f),     .yn(PROG_n));
    obuf4 u_ob_ver    (.a(VER),     .yf(VER_f),      .yn(VER_n));
    obuf4 u_ob_sense  (.a(SENSE),   .yf(SENSE_f),    .yn(SENSE_n));
    obuf4 u_ob_wrany  (.a(WRANY),   .yf(WRANY_f),    .yn(WRANY_n));
    obuf4 u_ob_dload  (.a(dload),   .yf(dload_f),    .yn(dload_n));
    obuf4 u_ob_pol    (.a(pol),     .yf(pol_f),      .yn(pol_n));
    obuf4 u_ob_rdout  (.a(rd_out),  .yf(rd_out_f),   .yn(rd_out_n));
    obuf4 u_ob_rdoutb (.a(~rd_out), .yf(rd_out_b_f), .yn(rd_out_b_n));
endmodule
