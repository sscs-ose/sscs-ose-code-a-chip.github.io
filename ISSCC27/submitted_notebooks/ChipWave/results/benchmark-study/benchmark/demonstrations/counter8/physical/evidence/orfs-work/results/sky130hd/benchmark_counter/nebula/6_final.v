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
 output [7:0] count;
 input [7:0] load_value;

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
 wire net12;
 wire net13;
 wire net14;
 wire net15;
 wire net16;
 wire net17;
 wire net18;
 wire net19;
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
 wire net20;
 wire net11;
 wire clknet_0_clk;
 wire clknet_1_0__leaf_clk;
 wire clknet_1_1__leaf_clk;

 sky130_fd_sc_hd__inv_1 _060_ (.A(net18),
    .Y(_011_));
 sky130_fd_sc_hd__nand2_1 _062_ (.A(net15),
    .B(net16),
    .Y(_020_));
 sky130_fd_sc_hd__nand2_1 _063_ (.A(net18),
    .B(net17),
    .Y(_021_));
 sky130_fd_sc_hd__nor2_1 _064_ (.A(_020_),
    .B(_021_),
    .Y(_022_));
 sky130_fd_sc_hd__inv_1 _065_ (.A(net12),
    .Y(_023_));
 sky130_fd_sc_hd__nand2_1 _066_ (.A(net14),
    .B(net13),
    .Y(_024_));
 sky130_fd_sc_hd__nor2_1 _067_ (.A(_023_),
    .B(_024_),
    .Y(_025_));
 sky130_fd_sc_hd__nand2_1 _068_ (.A(_022_),
    .B(_025_),
    .Y(_026_));
 sky130_fd_sc_hd__inv_1 _069_ (.A(net19),
    .Y(_027_));
 sky130_fd_sc_hd__nand2_1 _070_ (.A(_026_),
    .B(_027_),
    .Y(_028_));
 sky130_fd_sc_hd__nand3_1 _071_ (.A(_022_),
    .B(_025_),
    .C(net19),
    .Y(_029_));
 sky130_fd_sc_hd__inv_1 _072_ (.A(net1),
    .Y(_013_));
 sky130_fd_sc_hd__nand3_1 _073_ (.A(_028_),
    .B(_029_),
    .C(_014_),
    .Y(_030_));
 sky130_fd_sc_hd__nor2_4 _074_ (.A(net2),
    .B(net1),
    .Y(_031_));
 sky130_fd_sc_hd__a22oi_1 _075_ (.A1(net10),
    .A2(net2),
    .B1(_031_),
    .B2(net19),
    .Y(_032_));
 sky130_fd_sc_hd__nand2_1 _076_ (.A(_030_),
    .B(_032_),
    .Y(_010_));
 sky130_fd_sc_hd__nand2_1 _077_ (.A(_031_),
    .B(net12),
    .Y(_033_));
 sky130_fd_sc_hd__nand2_1 _078_ (.A(net2),
    .B(net3),
    .Y(_034_));
 sky130_fd_sc_hd__o211ai_1 _079_ (.A1(net12),
    .A2(_015_),
    .B1(_033_),
    .C1(_034_),
    .Y(_009_));
 sky130_fd_sc_hd__nand2_1 _080_ (.A(_014_),
    .B(_001_),
    .Y(_035_));
 sky130_fd_sc_hd__nand2_1 _081_ (.A(_031_),
    .B(net13),
    .Y(_036_));
 sky130_fd_sc_hd__nand2_1 _082_ (.A(net2),
    .B(net4),
    .Y(_037_));
 sky130_fd_sc_hd__nor2_4 _083_ (.A(net2),
    .B(_013_),
    .Y(_014_));
 sky130_fd_sc_hd__nand3_1 _084_ (.A(_035_),
    .B(_036_),
    .C(_037_),
    .Y(_008_));
 sky130_fd_sc_hd__xnor2_1 _085_ (.A(net14),
    .B(_002_),
    .Y(_038_));
 sky130_fd_sc_hd__a22oi_1 _086_ (.A1(net2),
    .A2(net5),
    .B1(_031_),
    .B2(net14),
    .Y(_039_));
 sky130_fd_sc_hd__o21ai_1 _087_ (.A1(_015_),
    .A2(_038_),
    .B1(_039_),
    .Y(_007_));
 sky130_fd_sc_hd__nand3_1 _088_ (.A(net14),
    .B(net12),
    .C(net13),
    .Y(_040_));
 sky130_fd_sc_hd__xnor2_1 _089_ (.A(net15),
    .B(_040_),
    .Y(_041_));
 sky130_fd_sc_hd__nand2_1 _090_ (.A(_041_),
    .B(_014_),
    .Y(_042_));
 sky130_fd_sc_hd__a22oi_1 _091_ (.A1(net2),
    .A2(net6),
    .B1(_031_),
    .B2(net15),
    .Y(_043_));
 sky130_fd_sc_hd__nand2_1 _092_ (.A(_042_),
    .B(_043_),
    .Y(_006_));
 sky130_fd_sc_hd__inv_1 _093_ (.A(_002_),
    .Y(_044_));
 sky130_fd_sc_hd__inv_2 _094_ (.A(_014_),
    .Y(_015_));
 sky130_fd_sc_hd__o21bai_1 _095_ (.A1(_044_),
    .A2(_016_),
    .B1_N(net16),
    .Y(_045_));
 sky130_fd_sc_hd__nand4_1 _096_ (.A(net15),
    .B(net14),
    .C(net16),
    .D(_002_),
    .Y(_046_));
 sky130_fd_sc_hd__nand3_1 _097_ (.A(_045_),
    .B(_014_),
    .C(_046_),
    .Y(_047_));
 sky130_fd_sc_hd__a22oi_1 _098_ (.A1(net2),
    .A2(net7),
    .B1(_031_),
    .B2(net16),
    .Y(_048_));
 sky130_fd_sc_hd__nand2_1 _099_ (.A(_047_),
    .B(_048_),
    .Y(_005_));
 sky130_fd_sc_hd__o21bai_1 _100_ (.A1(_020_),
    .A2(_040_),
    .B1_N(net17),
    .Y(_049_));
 sky130_fd_sc_hd__nor2_1 _101_ (.A(_020_),
    .B(_040_),
    .Y(_050_));
 sky130_fd_sc_hd__nand2_1 _102_ (.A(_050_),
    .B(net17),
    .Y(_051_));
 sky130_fd_sc_hd__nand3_1 _103_ (.A(_049_),
    .B(_051_),
    .C(_014_),
    .Y(_052_));
 sky130_fd_sc_hd__a22oi_1 _104_ (.A1(net2),
    .A2(net8),
    .B1(_031_),
    .B2(net17),
    .Y(_053_));
 sky130_fd_sc_hd__nand2_1 _105_ (.A(net15),
    .B(net14),
    .Y(_016_));
 sky130_fd_sc_hd__nand2_1 _106_ (.A(_052_),
    .B(_053_),
    .Y(_004_));
 sky130_fd_sc_hd__nand2_1 _107_ (.A(_018_),
    .B(_002_),
    .Y(_054_));
 sky130_fd_sc_hd__nand3_1 _108_ (.A(_054_),
    .B(net18),
    .C(_014_),
    .Y(_055_));
 sky130_fd_sc_hd__nand4_1 _109_ (.A(_018_),
    .B(_011_),
    .C(_002_),
    .D(_014_),
    .Y(_056_));
 sky130_fd_sc_hd__a22oi_1 _110_ (.A1(net2),
    .A2(net9),
    .B1(_031_),
    .B2(net18),
    .Y(_057_));
 sky130_fd_sc_hd__nand3_1 _111_ (.A(_055_),
    .B(_056_),
    .C(_057_),
    .Y(_003_));
 sky130_fd_sc_hd__nand2_1 _112_ (.A(net17),
    .B(net16),
    .Y(_017_));
 sky130_fd_sc_hd__nor2_2 _113_ (.A(_016_),
    .B(_017_),
    .Y(_018_));
 sky130_fd_sc_hd__nand3_1 _114_ (.A(_018_),
    .B(net19),
    .C(_000_),
    .Y(_019_));
 sky130_fd_sc_hd__nor3_2 _115_ (.A(_011_),
    .B(_015_),
    .C(_019_),
    .Y(_058_));
 sky130_fd_sc_hd__ha_1 _116_ (.A(net12),
    .B(net13),
    .COUT(_000_),
    .SUM(_001_));
 sky130_fd_sc_hd__ha_1 _117_ (.A(net12),
    .B(net13),
    .COUT(_002_),
    .SUM(_059_));
 sky130_fd_sc_hd__clkbuf_4 clkbuf_0_clk (.A(clk),
    .X(clknet_0_clk));
 sky130_fd_sc_hd__clkbuf_4 clkbuf_1_0__f_clk (.A(clknet_0_clk),
    .X(clknet_1_0__leaf_clk));
 sky130_fd_sc_hd__clkbuf_4 clkbuf_1_1__f_clk (.A(clknet_0_clk),
    .X(clknet_1_1__leaf_clk));
 sky130_fd_sc_hd__clkinv_2 clkload0 (.A(clknet_1_1__leaf_clk));
 sky130_fd_sc_hd__dfrtp_1 \count[0]$_DFFE_PN0P_  (.D(_009_),
    .Q(net12),
    .RESET_B(net11),
    .CLK(clknet_1_0__leaf_clk));
 sky130_fd_sc_hd__dfrtp_1 \count[1]$_DFFE_PN0P_  (.D(_008_),
    .Q(net13),
    .RESET_B(net11),
    .CLK(clknet_1_0__leaf_clk));
 sky130_fd_sc_hd__dfrtp_1 \count[2]$_DFFE_PN0P_  (.D(_007_),
    .Q(net14),
    .RESET_B(net11),
    .CLK(clknet_1_0__leaf_clk));
 sky130_fd_sc_hd__dfrtp_1 \count[3]$_DFFE_PN0P_  (.D(_006_),
    .Q(net15),
    .RESET_B(net11),
    .CLK(clknet_1_1__leaf_clk));
 sky130_fd_sc_hd__dfrtp_1 \count[4]$_DFFE_PN0P_  (.D(_005_),
    .Q(net16),
    .RESET_B(net11),
    .CLK(clknet_1_1__leaf_clk));
 sky130_fd_sc_hd__dfrtp_1 \count[5]$_DFFE_PN0P_  (.D(_004_),
    .Q(net17),
    .RESET_B(net11),
    .CLK(clknet_1_1__leaf_clk));
 sky130_fd_sc_hd__dfrtp_1 \count[6]$_DFFE_PN0P_  (.D(_003_),
    .Q(net18),
    .RESET_B(net11),
    .CLK(clknet_1_0__leaf_clk));
 sky130_fd_sc_hd__dfrtp_1 \count[7]$_DFFE_PN0P_  (.D(_010_),
    .Q(net19),
    .RESET_B(net11),
    .CLK(clknet_1_0__leaf_clk));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input1 (.A(en),
    .X(net1));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input10 (.A(load_value[7]),
    .X(net10));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input11 (.A(rst_n),
    .X(net11));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input2 (.A(load),
    .X(net2));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input3 (.A(load_value[0]),
    .X(net3));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input4 (.A(load_value[1]),
    .X(net4));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input5 (.A(load_value[2]),
    .X(net5));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input6 (.A(load_value[3]),
    .X(net6));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input7 (.A(load_value[4]),
    .X(net7));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input8 (.A(load_value[5]),
    .X(net8));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input9 (.A(load_value[6]),
    .X(net9));
 sky130_fd_sc_hd__clkdlybuf4s50_1 output12 (.A(net12),
    .X(count[0]));
 sky130_fd_sc_hd__clkdlybuf4s50_1 output13 (.A(net13),
    .X(count[1]));
 sky130_fd_sc_hd__clkdlybuf4s50_1 output14 (.A(net14),
    .X(count[2]));
 sky130_fd_sc_hd__clkdlybuf4s50_1 output15 (.A(net15),
    .X(count[3]));
 sky130_fd_sc_hd__clkdlybuf4s50_1 output16 (.A(net16),
    .X(count[4]));
 sky130_fd_sc_hd__clkdlybuf4s50_1 output17 (.A(net17),
    .X(count[5]));
 sky130_fd_sc_hd__clkdlybuf4s50_1 output18 (.A(net18),
    .X(count[6]));
 sky130_fd_sc_hd__clkdlybuf4s50_1 output19 (.A(net19),
    .X(count[7]));
 sky130_fd_sc_hd__clkdlybuf4s50_1 output20 (.A(net20),
    .X(overflow));
 sky130_fd_sc_hd__dfrtp_1 \overflow$_DFF_PN0_  (.D(_058_),
    .Q(net20),
    .RESET_B(net11),
    .CLK(clknet_1_0__leaf_clk));
endmodule
