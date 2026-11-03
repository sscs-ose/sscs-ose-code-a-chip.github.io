module benchmark_counter (clk,
    en,
    load,
    overflow,
    rst_n,
    count,
    load_value);
 input clk;
 input en;
 input load;
 output overflow;
 input rst_n;
 output [15:0] count;
 input [15:0] load_value;

 wire _000_;
 wire _001_;
 wire _002_;
 wire _003_;
 wire _004_;
 wire _005_;
 wire _006_;
 wire _007_;
 wire _008_;
 wire _009_;
 wire _010_;
 wire _011_;
 wire _012_;
 wire _013_;
 wire _014_;
 wire _015_;
 wire _016_;
 wire _017_;
 wire _018_;
 wire _019_;
 wire _020_;
 wire _021_;
 wire _022_;
 wire _023_;
 wire _024_;
 wire _025_;
 wire _026_;
 wire _027_;
 wire _028_;
 wire _029_;
 wire _030_;
 wire _031_;
 wire _032_;
 wire _033_;
 wire _034_;
 wire _035_;
 wire _036_;
 wire _037_;
 wire _038_;
 wire _039_;
 wire _040_;
 wire _041_;
 wire _042_;
 wire _043_;
 wire _044_;
 wire _045_;
 wire _046_;
 wire _047_;
 wire _048_;
 wire _049_;
 wire _050_;
 wire _051_;
 wire _052_;
 wire _053_;
 wire _054_;
 wire _055_;
 wire _056_;
 wire _057_;
 wire _058_;
 wire _059_;
 wire _060_;
 wire _061_;
 wire _062_;
 wire _063_;
 wire _064_;
 wire _065_;
 wire _066_;
 wire _067_;
 wire _068_;
 wire _069_;
 wire _070_;
 wire _071_;
 wire _072_;
 wire _073_;
 wire _074_;
 wire _075_;
 wire _076_;
 wire _078_;
 wire _079_;
 wire _080_;
 wire _081_;
 wire _082_;
 wire _083_;
 wire _084_;
 wire _085_;
 wire _086_;
 wire _087_;
 wire _088_;
 wire _089_;
 wire _090_;
 wire _091_;
 wire _092_;
 wire _093_;
 wire _094_;
 wire _095_;
 wire _096_;
 wire _097_;
 wire _098_;
 wire _099_;
 wire _100_;
 wire _101_;
 wire _102_;
 wire _103_;
 wire _104_;
 wire _105_;
 wire _106_;
 wire _107_;
 wire _108_;
 wire _109_;
 wire _110_;
 wire _111_;
 wire _113_;
 wire _114_;
 wire _115_;
 wire _117_;
 wire _118_;
 wire _119_;
 wire net20;
 wire net21;
 wire net22;
 wire net23;
 wire net24;
 wire net25;
 wire net26;
 wire net27;
 wire net28;
 wire net29;
 wire net30;
 wire net31;
 wire net32;
 wire net33;
 wire net34;
 wire net35;
 wire net1;
 wire net2;
 wire net3;
 wire net4;
 wire net5;
 wire net6;
 wire net7;
 wire net8;
 wire net9;
 wire net10;
 wire net11;
 wire net12;
 wire net13;
 wire net14;
 wire net15;
 wire net16;
 wire net17;
 wire net18;
 wire net36;
 wire net19;
 wire clknet_0_clk;
 wire clknet_1_0__leaf_clk;
 wire clknet_1_1__leaf_clk;

 sky130_fd_sc_hd__nand3_1 _120_ (.A(net25),
    .B(net24),
    .C(net23),
    .Y(_076_));
 sky130_fd_sc_hd__nand2_1 _122_ (.A(net34),
    .B(net35),
    .Y(_086_));
 sky130_fd_sc_hd__nor2_1 _123_ (.A(_096_),
    .B(_059_),
    .Y(_060_));
 sky130_fd_sc_hd__nand3_1 _124_ (.A(_041_),
    .B(net24),
    .C(_060_),
    .Y(_061_));
 sky130_fd_sc_hd__nor2_1 _125_ (.A(_094_),
    .B(_097_),
    .Y(_062_));
 sky130_fd_sc_hd__nand3_1 _126_ (.A(_030_),
    .B(_062_),
    .C(_060_),
    .Y(_063_));
 sky130_fd_sc_hd__inv_1 _127_ (.A(net24),
    .Y(_064_));
 sky130_fd_sc_hd__nand2_1 _128_ (.A(_063_),
    .B(_064_),
    .Y(_065_));
 sky130_fd_sc_hd__nand3_1 _129_ (.A(_061_),
    .B(_118_),
    .C(_065_),
    .Y(_066_));
 sky130_fd_sc_hd__a22oi_1 _130_ (.A1(net2),
    .A2(net7),
    .B1(_109_),
    .B2(net24),
    .Y(_067_));
 sky130_fd_sc_hd__nand2_1 _131_ (.A(_066_),
    .B(_067_),
    .Y(_003_));
 sky130_fd_sc_hd__nand2_1 _132_ (.A(net24),
    .B(net23),
    .Y(_068_));
 sky130_fd_sc_hd__nand2_1 _133_ (.A(net21),
    .B(net22),
    .Y(_087_));
 sky130_fd_sc_hd__nor2_1 _134_ (.A(_084_),
    .B(_068_),
    .Y(_069_));
 sky130_fd_sc_hd__nand3_1 _135_ (.A(_033_),
    .B(_088_),
    .C(_069_),
    .Y(_070_));
 sky130_fd_sc_hd__inv_1 _136_ (.A(net25),
    .Y(_071_));
 sky130_fd_sc_hd__nand2_1 _137_ (.A(_070_),
    .B(_071_),
    .Y(_072_));
 sky130_fd_sc_hd__nand4_1 _138_ (.A(_033_),
    .B(_088_),
    .C(_069_),
    .D(net25),
    .Y(_073_));
 sky130_fd_sc_hd__nand3_1 _139_ (.A(_072_),
    .B(_073_),
    .C(_118_),
    .Y(_074_));
 sky130_fd_sc_hd__a22oi_1 _140_ (.A1(net2),
    .A2(net8),
    .B1(_109_),
    .B2(net25),
    .Y(_075_));
 sky130_fd_sc_hd__nand2_1 _141_ (.A(_074_),
    .B(_075_),
    .Y(_002_));
 sky130_fd_sc_hd__nor2_2 _142_ (.A(_086_),
    .B(_087_),
    .Y(_088_));
 sky130_fd_sc_hd__nand3_2 _143_ (.A(_082_),
    .B(_085_),
    .C(_088_),
    .Y(_089_));
 sky130_fd_sc_hd__nor3_1 _144_ (.A(_076_),
    .B(_080_),
    .C(_089_),
    .Y(_119_));
 sky130_fd_sc_hd__inv_2 _145_ (.A(net2),
    .Y(_090_));
 sky130_fd_sc_hd__nand2_1 _146_ (.A(_090_),
    .B(net22),
    .Y(_091_));
 sky130_fd_sc_hd__nor2_1 _147_ (.A(_091_),
    .B(_076_),
    .Y(_092_));
 sky130_fd_sc_hd__nand2_2 _148_ (.A(net30),
    .B(net29),
    .Y(_093_));
 sky130_fd_sc_hd__nand2_1 _149_ (.A(net32),
    .B(net31),
    .Y(_094_));
 sky130_fd_sc_hd__inv_1 _150_ (.A(net26),
    .Y(_078_));
 sky130_fd_sc_hd__nor2_4 _151_ (.A(_093_),
    .B(_094_),
    .Y(_095_));
 sky130_fd_sc_hd__nand2_1 _152_ (.A(net35),
    .B(net21),
    .Y(_096_));
 sky130_fd_sc_hd__nand2_2 _153_ (.A(net33),
    .B(net34),
    .Y(_097_));
 sky130_fd_sc_hd__nor2_2 _154_ (.A(_096_),
    .B(_097_),
    .Y(_098_));
 sky130_fd_sc_hd__inv_4 _155_ (.A(net20),
    .Y(_099_));
 sky130_fd_sc_hd__nand2_1 _156_ (.A(net27),
    .B(net28),
    .Y(_100_));
 sky130_fd_sc_hd__nor2_4 _157_ (.A(_099_),
    .B(_100_),
    .Y(_101_));
 sky130_fd_sc_hd__nand4_1 _158_ (.A(_092_),
    .B(_095_),
    .C(_098_),
    .D(_101_),
    .Y(_102_));
 sky130_fd_sc_hd__a21oi_1 _159_ (.A1(net9),
    .A2(net2),
    .B1(_079_),
    .Y(_103_));
 sky130_fd_sc_hd__nand2_1 _160_ (.A(_102_),
    .B(_103_),
    .Y(_104_));
 sky130_fd_sc_hd__nor2_1 _161_ (.A(net2),
    .B(_078_),
    .Y(_079_));
 sky130_fd_sc_hd__inv_2 _162_ (.A(_098_),
    .Y(_105_));
 sky130_fd_sc_hd__nand2_4 _163_ (.A(_095_),
    .B(_101_),
    .Y(_106_));
 sky130_fd_sc_hd__nor2_4 _164_ (.A(_105_),
    .B(_106_),
    .Y(_107_));
 sky130_fd_sc_hd__nand3_1 _165_ (.A(_107_),
    .B(net26),
    .C(_092_),
    .Y(_108_));
 sky130_fd_sc_hd__nor2_4 _166_ (.A(net2),
    .B(net1),
    .Y(_109_));
 sky130_fd_sc_hd__inv_1 _167_ (.A(_109_),
    .Y(_110_));
 sky130_fd_sc_hd__nand3_1 _168_ (.A(_104_),
    .B(_108_),
    .C(_110_),
    .Y(_111_));
 sky130_fd_sc_hd__nand2_1 _170_ (.A(_109_),
    .B(net26),
    .Y(_113_));
 sky130_fd_sc_hd__nand2_1 _171_ (.A(_111_),
    .B(_113_),
    .Y(_017_));
 sky130_fd_sc_hd__nand2_1 _172_ (.A(_079_),
    .B(net1),
    .Y(_080_));
 sky130_fd_sc_hd__nand2_2 _173_ (.A(_090_),
    .B(net1),
    .Y(_114_));
 sky130_fd_sc_hd__nand2_1 _174_ (.A(_109_),
    .B(net20),
    .Y(_115_));
 sky130_fd_sc_hd__nand2_1 _176_ (.A(net2),
    .B(net3),
    .Y(_117_));
 sky130_fd_sc_hd__o211ai_1 _177_ (.A1(net20),
    .A2(_114_),
    .B1(_115_),
    .C1(_117_),
    .Y(_016_));
 sky130_fd_sc_hd__inv_1 _178_ (.A(_114_),
    .Y(_118_));
 sky130_fd_sc_hd__nand2_1 _179_ (.A(_118_),
    .B(_001_),
    .Y(_018_));
 sky130_fd_sc_hd__nand2_1 _180_ (.A(_109_),
    .B(net27),
    .Y(_019_));
 sky130_fd_sc_hd__nand2_1 _181_ (.A(net2),
    .B(net10),
    .Y(_020_));
 sky130_fd_sc_hd__nand3_1 _182_ (.A(_018_),
    .B(_019_),
    .C(_020_),
    .Y(_015_));
 sky130_fd_sc_hd__nand3_2 _183_ (.A(net29),
    .B(net28),
    .C(_000_),
    .Y(_081_));
 sky130_fd_sc_hd__nand2_1 _184_ (.A(net1),
    .B(_000_),
    .Y(_021_));
 sky130_fd_sc_hd__xor2_1 _185_ (.A(net28),
    .B(_021_),
    .X(_022_));
 sky130_fd_sc_hd__nor2_1 _186_ (.A(net11),
    .B(_090_),
    .Y(_023_));
 sky130_fd_sc_hd__a21oi_1 _187_ (.A1(_022_),
    .A2(_090_),
    .B1(_023_),
    .Y(_014_));
 sky130_fd_sc_hd__nand2_1 _188_ (.A(_101_),
    .B(net1),
    .Y(_024_));
 sky130_fd_sc_hd__xor2_1 _189_ (.A(net29),
    .B(_024_),
    .X(_025_));
 sky130_fd_sc_hd__nor2_1 _190_ (.A(net12),
    .B(_090_),
    .Y(_026_));
 sky130_fd_sc_hd__a21oi_1 _191_ (.A1(_025_),
    .A2(_090_),
    .B1(_026_),
    .Y(_013_));
 sky130_fd_sc_hd__xor2_1 _192_ (.A(net30),
    .B(_081_),
    .X(_027_));
 sky130_fd_sc_hd__a22oi_1 _193_ (.A1(net2),
    .A2(net13),
    .B1(_109_),
    .B2(net30),
    .Y(_028_));
 sky130_fd_sc_hd__inv_1 _194_ (.A(_081_),
    .Y(_082_));
 sky130_fd_sc_hd__o21ai_1 _195_ (.A1(_114_),
    .A2(_027_),
    .B1(_028_),
    .Y(_012_));
 sky130_fd_sc_hd__nand3_1 _196_ (.A(net20),
    .B(net27),
    .C(net28),
    .Y(_029_));
 sky130_fd_sc_hd__nor2_1 _197_ (.A(_093_),
    .B(_029_),
    .Y(_030_));
 sky130_fd_sc_hd__xnor2_1 _198_ (.A(net31),
    .B(_030_),
    .Y(_031_));
 sky130_fd_sc_hd__a22oi_1 _199_ (.A1(net2),
    .A2(net14),
    .B1(_109_),
    .B2(net31),
    .Y(_032_));
 sky130_fd_sc_hd__o21ai_1 _200_ (.A1(_114_),
    .A2(_031_),
    .B1(_032_),
    .Y(_011_));
 sky130_fd_sc_hd__nor2_2 _201_ (.A(_083_),
    .B(_081_),
    .Y(_033_));
 sky130_fd_sc_hd__xnor2_1 _202_ (.A(net32),
    .B(_033_),
    .Y(_034_));
 sky130_fd_sc_hd__a22oi_1 _203_ (.A1(net2),
    .A2(net15),
    .B1(_109_),
    .B2(net32),
    .Y(_035_));
 sky130_fd_sc_hd__o21ai_1 _204_ (.A1(_114_),
    .A2(_034_),
    .B1(_035_),
    .Y(_010_));
 sky130_fd_sc_hd__nand2_1 _205_ (.A(net30),
    .B(net31),
    .Y(_083_));
 sky130_fd_sc_hd__xor2_1 _206_ (.A(net33),
    .B(_106_),
    .X(_036_));
 sky130_fd_sc_hd__a22oi_1 _207_ (.A1(net2),
    .A2(net16),
    .B1(_109_),
    .B2(net33),
    .Y(_037_));
 sky130_fd_sc_hd__o21ai_1 _208_ (.A1(_114_),
    .A2(_036_),
    .B1(_037_),
    .Y(_009_));
 sky130_fd_sc_hd__nand2_1 _209_ (.A(_082_),
    .B(_085_),
    .Y(_038_));
 sky130_fd_sc_hd__xor2_1 _210_ (.A(net34),
    .B(_038_),
    .X(_039_));
 sky130_fd_sc_hd__a22oi_1 _211_ (.A1(net2),
    .A2(net17),
    .B1(_109_),
    .B2(net34),
    .Y(_040_));
 sky130_fd_sc_hd__o21ai_1 _212_ (.A1(_114_),
    .A2(_039_),
    .B1(_040_),
    .Y(_008_));
 sky130_fd_sc_hd__nor2_4 _213_ (.A(_097_),
    .B(_106_),
    .Y(_041_));
 sky130_fd_sc_hd__nor2_1 _214_ (.A(net35),
    .B(_041_),
    .Y(_042_));
 sky130_fd_sc_hd__nand2_1 _215_ (.A(_041_),
    .B(net35),
    .Y(_043_));
 sky130_fd_sc_hd__nand2_1 _216_ (.A(net32),
    .B(net33),
    .Y(_084_));
 sky130_fd_sc_hd__nand2_1 _217_ (.A(_043_),
    .B(_118_),
    .Y(_044_));
 sky130_fd_sc_hd__a22oi_1 _218_ (.A1(net2),
    .A2(net18),
    .B1(_109_),
    .B2(net35),
    .Y(_045_));
 sky130_fd_sc_hd__o21ai_2 _219_ (.A1(_042_),
    .A2(_044_),
    .B1(_045_),
    .Y(_007_));
 sky130_fd_sc_hd__a31oi_1 _220_ (.A1(_033_),
    .A2(_098_),
    .A3(net32),
    .B1(_114_),
    .Y(_046_));
 sky130_fd_sc_hd__o21bai_1 _221_ (.A1(_086_),
    .A2(_038_),
    .B1_N(net21),
    .Y(_047_));
 sky130_fd_sc_hd__nand2_1 _222_ (.A(_046_),
    .B(_047_),
    .Y(_048_));
 sky130_fd_sc_hd__a22oi_1 _223_ (.A1(net2),
    .A2(net4),
    .B1(_109_),
    .B2(net21),
    .Y(_049_));
 sky130_fd_sc_hd__nand2_1 _224_ (.A(_048_),
    .B(_049_),
    .Y(_006_));
 sky130_fd_sc_hd__o21bai_1 _225_ (.A1(_105_),
    .A2(_106_),
    .B1_N(net22),
    .Y(_050_));
 sky130_fd_sc_hd__nand2_1 _226_ (.A(_107_),
    .B(net22),
    .Y(_051_));
 sky130_fd_sc_hd__nor2_2 _227_ (.A(_083_),
    .B(_084_),
    .Y(_085_));
 sky130_fd_sc_hd__nand3_1 _228_ (.A(_050_),
    .B(_051_),
    .C(_118_),
    .Y(_052_));
 sky130_fd_sc_hd__a22oi_1 _229_ (.A1(net2),
    .A2(net5),
    .B1(_109_),
    .B2(net22),
    .Y(_053_));
 sky130_fd_sc_hd__nand2_1 _230_ (.A(_052_),
    .B(_053_),
    .Y(_005_));
 sky130_fd_sc_hd__inv_1 _231_ (.A(net23),
    .Y(_054_));
 sky130_fd_sc_hd__nor2_1 _232_ (.A(_054_),
    .B(_089_),
    .Y(_055_));
 sky130_fd_sc_hd__nand2_1 _233_ (.A(_089_),
    .B(_054_),
    .Y(_056_));
 sky130_fd_sc_hd__nand2_1 _234_ (.A(_056_),
    .B(_118_),
    .Y(_057_));
 sky130_fd_sc_hd__a22oi_1 _235_ (.A1(net2),
    .A2(net6),
    .B1(_109_),
    .B2(net23),
    .Y(_058_));
 sky130_fd_sc_hd__o21ai_1 _236_ (.A1(_055_),
    .A2(_057_),
    .B1(_058_),
    .Y(_004_));
 sky130_fd_sc_hd__nand2_1 _237_ (.A(net22),
    .B(net23),
    .Y(_059_));
 sky130_fd_sc_hd__ha_1 _238_ (.A(net20),
    .B(net27),
    .COUT(_000_),
    .SUM(_001_));
 sky130_fd_sc_hd__clkbuf_4 clkbuf_0_clk (.A(clk),
    .X(clknet_0_clk));
 sky130_fd_sc_hd__clkbuf_4 clkbuf_1_0__f_clk (.A(clknet_0_clk),
    .X(clknet_1_0__leaf_clk));
 sky130_fd_sc_hd__clkbuf_4 clkbuf_1_1__f_clk (.A(clknet_0_clk),
    .X(clknet_1_1__leaf_clk));
 sky130_fd_sc_hd__clkbuf_1 clkload0 (.A(clknet_1_1__leaf_clk));
 sky130_fd_sc_hd__dfrtp_1 \count[0]$_DFFE_PN0P_  (.D(_016_),
    .Q(net20),
    .RESET_B(net19),
    .CLK(clknet_1_0__leaf_clk));
 sky130_fd_sc_hd__dfrtp_1 \count[10]$_DFFE_PN0P_  (.D(_006_),
    .Q(net21),
    .RESET_B(net19),
    .CLK(clknet_1_1__leaf_clk));
 sky130_fd_sc_hd__dfrtp_1 \count[11]$_DFFE_PN0P_  (.D(_005_),
    .Q(net22),
    .RESET_B(net19),
    .CLK(clknet_1_1__leaf_clk));
 sky130_fd_sc_hd__dfrtp_1 \count[12]$_DFFE_PN0P_  (.D(_004_),
    .Q(net23),
    .RESET_B(net19),
    .CLK(clknet_1_1__leaf_clk));
 sky130_fd_sc_hd__dfrtp_1 \count[13]$_DFFE_PN0P_  (.D(_003_),
    .Q(net24),
    .RESET_B(net19),
    .CLK(clknet_1_1__leaf_clk));
 sky130_fd_sc_hd__dfrtp_1 \count[14]$_DFFE_PN0P_  (.D(_002_),
    .Q(net25),
    .RESET_B(net19),
    .CLK(clknet_1_1__leaf_clk));
 sky130_fd_sc_hd__dfrtp_1 \count[15]$_DFFE_PN0P_  (.D(_017_),
    .Q(net26),
    .RESET_B(net19),
    .CLK(clknet_1_1__leaf_clk));
 sky130_fd_sc_hd__dfrtp_1 \count[1]$_DFFE_PN0P_  (.D(_015_),
    .Q(net27),
    .RESET_B(net19),
    .CLK(clknet_1_0__leaf_clk));
 sky130_fd_sc_hd__dfrtp_1 \count[2]$_DFFE_PN0P_  (.D(_014_),
    .Q(net28),
    .RESET_B(net19),
    .CLK(clknet_1_0__leaf_clk));
 sky130_fd_sc_hd__dfrtp_1 \count[3]$_DFFE_PN0P_  (.D(_013_),
    .Q(net29),
    .RESET_B(net19),
    .CLK(clknet_1_0__leaf_clk));
 sky130_fd_sc_hd__dfrtp_1 \count[4]$_DFFE_PN0P_  (.D(_012_),
    .Q(net30),
    .RESET_B(net19),
    .CLK(clknet_1_0__leaf_clk));
 sky130_fd_sc_hd__dfrtp_1 \count[5]$_DFFE_PN0P_  (.D(_011_),
    .Q(net31),
    .RESET_B(net19),
    .CLK(clknet_1_0__leaf_clk));
 sky130_fd_sc_hd__dfrtp_1 \count[6]$_DFFE_PN0P_  (.D(_010_),
    .Q(net32),
    .RESET_B(net19),
    .CLK(clknet_1_0__leaf_clk));
 sky130_fd_sc_hd__dfrtp_1 \count[7]$_DFFE_PN0P_  (.D(_009_),
    .Q(net33),
    .RESET_B(net19),
    .CLK(clknet_1_0__leaf_clk));
 sky130_fd_sc_hd__dfrtp_1 \count[8]$_DFFE_PN0P_  (.D(_008_),
    .Q(net34),
    .RESET_B(net19),
    .CLK(clknet_1_0__leaf_clk));
 sky130_fd_sc_hd__dfrtp_1 \count[9]$_DFFE_PN0P_  (.D(_007_),
    .Q(net35),
    .RESET_B(net19),
    .CLK(clknet_1_1__leaf_clk));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input1 (.A(en),
    .X(net1));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input10 (.A(load_value[1]),
    .X(net10));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input11 (.A(load_value[2]),
    .X(net11));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input12 (.A(load_value[3]),
    .X(net12));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input13 (.A(load_value[4]),
    .X(net13));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input14 (.A(load_value[5]),
    .X(net14));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input15 (.A(load_value[6]),
    .X(net15));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input16 (.A(load_value[7]),
    .X(net16));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input17 (.A(load_value[8]),
    .X(net17));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input18 (.A(load_value[9]),
    .X(net18));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input19 (.A(rst_n),
    .X(net19));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input2 (.A(load),
    .X(net2));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input3 (.A(load_value[0]),
    .X(net3));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input4 (.A(load_value[10]),
    .X(net4));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input5 (.A(load_value[11]),
    .X(net5));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input6 (.A(load_value[12]),
    .X(net6));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input7 (.A(load_value[13]),
    .X(net7));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input8 (.A(load_value[14]),
    .X(net8));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input9 (.A(load_value[15]),
    .X(net9));
 sky130_fd_sc_hd__clkdlybuf4s50_1 output20 (.A(net20),
    .X(count[0]));
 sky130_fd_sc_hd__clkdlybuf4s50_1 output21 (.A(net21),
    .X(count[10]));
 sky130_fd_sc_hd__clkdlybuf4s50_1 output22 (.A(net22),
    .X(count[11]));
 sky130_fd_sc_hd__clkdlybuf4s50_1 output23 (.A(net23),
    .X(count[12]));
 sky130_fd_sc_hd__clkdlybuf4s50_1 output24 (.A(net24),
    .X(count[13]));
 sky130_fd_sc_hd__clkdlybuf4s50_1 output25 (.A(net25),
    .X(count[14]));
 sky130_fd_sc_hd__clkdlybuf4s50_1 output26 (.A(net26),
    .X(count[15]));
 sky130_fd_sc_hd__clkdlybuf4s50_1 output27 (.A(net27),
    .X(count[1]));
 sky130_fd_sc_hd__clkdlybuf4s50_1 output28 (.A(net28),
    .X(count[2]));
 sky130_fd_sc_hd__clkdlybuf4s50_1 output29 (.A(net29),
    .X(count[3]));
 sky130_fd_sc_hd__clkdlybuf4s50_1 output30 (.A(net30),
    .X(count[4]));
 sky130_fd_sc_hd__clkdlybuf4s50_1 output31 (.A(net31),
    .X(count[5]));
 sky130_fd_sc_hd__clkdlybuf4s50_1 output32 (.A(net32),
    .X(count[6]));
 sky130_fd_sc_hd__clkdlybuf4s50_1 output33 (.A(net33),
    .X(count[7]));
 sky130_fd_sc_hd__clkdlybuf4s50_1 output34 (.A(net34),
    .X(count[8]));
 sky130_fd_sc_hd__clkdlybuf4s50_1 output35 (.A(net35),
    .X(count[9]));
 sky130_fd_sc_hd__clkdlybuf4s50_1 output36 (.A(net36),
    .X(overflow));
 sky130_fd_sc_hd__dfrtp_1 \overflow$_DFF_PN0_  (.D(_119_),
    .Q(net36),
    .RESET_B(net19),
    .CLK(clknet_1_1__leaf_clk));
endmodule
