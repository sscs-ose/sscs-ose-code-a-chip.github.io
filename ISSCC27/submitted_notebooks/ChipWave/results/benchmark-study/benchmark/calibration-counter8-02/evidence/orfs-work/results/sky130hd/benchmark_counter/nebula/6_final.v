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

 sky130_fd_sc_hd__inv_6 _058_ (.A(net2),
    .Y(_011_));
 sky130_fd_sc_hd__inv_1 _059_ (.A(net15),
    .Y(_019_));
 sky130_fd_sc_hd__nand3_2 _060_ (.A(net12),
    .B(net14),
    .C(net13),
    .Y(_020_));
 sky130_fd_sc_hd__nor2_4 _061_ (.A(_019_),
    .B(_020_),
    .Y(_021_));
 sky130_fd_sc_hd__nand2_2 _062_ (.A(_011_),
    .B(net18),
    .Y(_022_));
 sky130_fd_sc_hd__nor2_2 _063_ (.A(_016_),
    .B(_022_),
    .Y(_023_));
 sky130_fd_sc_hd__nand2_1 _064_ (.A(_021_),
    .B(_023_),
    .Y(_024_));
 sky130_fd_sc_hd__nand2_1 _065_ (.A(net10),
    .B(net2),
    .Y(_025_));
 sky130_fd_sc_hd__a21boi_0 _066_ (.A1(_011_),
    .A2(net19),
    .B1_N(_025_),
    .Y(_026_));
 sky130_fd_sc_hd__nand2_1 _067_ (.A(_024_),
    .B(_026_),
    .Y(_027_));
 sky130_fd_sc_hd__nand3_1 _068_ (.A(_021_),
    .B(net19),
    .C(_023_),
    .Y(_028_));
 sky130_fd_sc_hd__nand3_1 _069_ (.A(_011_),
    .B(net1),
    .C(net19),
    .Y(_012_));
 sky130_fd_sc_hd__nor2_4 _070_ (.A(net2),
    .B(net1),
    .Y(_029_));
 sky130_fd_sc_hd__inv_1 _071_ (.A(_029_),
    .Y(_030_));
 sky130_fd_sc_hd__nand3_1 _072_ (.A(_027_),
    .B(_028_),
    .C(_030_),
    .Y(_031_));
 sky130_fd_sc_hd__nand2_1 _073_ (.A(_029_),
    .B(net19),
    .Y(_032_));
 sky130_fd_sc_hd__nand2_1 _074_ (.A(_031_),
    .B(_032_),
    .Y(_009_));
 sky130_fd_sc_hd__nand2_1 _075_ (.A(_011_),
    .B(net1),
    .Y(_033_));
 sky130_fd_sc_hd__nand2_1 _076_ (.A(_029_),
    .B(net12),
    .Y(_034_));
 sky130_fd_sc_hd__nand2_1 _077_ (.A(net2),
    .B(net3),
    .Y(_035_));
 sky130_fd_sc_hd__o211ai_1 _078_ (.A1(net12),
    .A2(_033_),
    .B1(_034_),
    .C1(_035_),
    .Y(_008_));
 sky130_fd_sc_hd__inv_1 _079_ (.A(_033_),
    .Y(_036_));
 sky130_fd_sc_hd__inv_1 _080_ (.A(_000_),
    .Y(_013_));
 sky130_fd_sc_hd__nand2_1 _081_ (.A(_036_),
    .B(_001_),
    .Y(_037_));
 sky130_fd_sc_hd__nand2_1 _082_ (.A(_029_),
    .B(net13),
    .Y(_038_));
 sky130_fd_sc_hd__nand2_1 _083_ (.A(net2),
    .B(net4),
    .Y(_039_));
 sky130_fd_sc_hd__nand3_1 _084_ (.A(_037_),
    .B(_038_),
    .C(_039_),
    .Y(_007_));
 sky130_fd_sc_hd__nand2_1 _085_ (.A(net1),
    .B(_000_),
    .Y(_040_));
 sky130_fd_sc_hd__xor2_1 _086_ (.A(net14),
    .B(_040_),
    .X(_041_));
 sky130_fd_sc_hd__nor2_1 _087_ (.A(net5),
    .B(_011_),
    .Y(_042_));
 sky130_fd_sc_hd__a21oi_1 _088_ (.A1(_041_),
    .A2(_011_),
    .B1(_042_),
    .Y(_006_));
 sky130_fd_sc_hd__xor2_1 _089_ (.A(net15),
    .B(_020_),
    .X(_043_));
 sky130_fd_sc_hd__a22oi_1 _090_ (.A1(net2),
    .A2(net6),
    .B1(_029_),
    .B2(net15),
    .Y(_044_));
 sky130_fd_sc_hd__nand2_1 _091_ (.A(net15),
    .B(net14),
    .Y(_014_));
 sky130_fd_sc_hd__o21ai_0 _092_ (.A1(_033_),
    .A2(_043_),
    .B1(_044_),
    .Y(_005_));
 sky130_fd_sc_hd__xnor2_1 _093_ (.A(net16),
    .B(_015_),
    .Y(_045_));
 sky130_fd_sc_hd__a22oi_1 _094_ (.A1(net2),
    .A2(net7),
    .B1(_029_),
    .B2(net16),
    .Y(_046_));
 sky130_fd_sc_hd__o21ai_1 _095_ (.A1(_033_),
    .A2(_045_),
    .B1(_046_),
    .Y(_004_));
 sky130_fd_sc_hd__a21oi_1 _096_ (.A1(_021_),
    .A2(_017_),
    .B1(_033_),
    .Y(_047_));
 sky130_fd_sc_hd__nand2_1 _097_ (.A(_021_),
    .B(net16),
    .Y(_048_));
 sky130_fd_sc_hd__inv_1 _098_ (.A(net17),
    .Y(_049_));
 sky130_fd_sc_hd__nand2_1 _099_ (.A(_048_),
    .B(_049_),
    .Y(_050_));
 sky130_fd_sc_hd__nand2_1 _100_ (.A(_047_),
    .B(_050_),
    .Y(_051_));
 sky130_fd_sc_hd__a22oi_1 _101_ (.A1(net2),
    .A2(net8),
    .B1(_029_),
    .B2(net17),
    .Y(_052_));
 sky130_fd_sc_hd__nor2_4 _102_ (.A(_013_),
    .B(_014_),
    .Y(_015_));
 sky130_fd_sc_hd__nand2_1 _103_ (.A(_051_),
    .B(_052_),
    .Y(_003_));
 sky130_fd_sc_hd__a21oi_1 _104_ (.A1(_015_),
    .A2(_017_),
    .B1(net18),
    .Y(_053_));
 sky130_fd_sc_hd__nand2_1 _105_ (.A(_018_),
    .B(_036_),
    .Y(_054_));
 sky130_fd_sc_hd__a22oi_1 _106_ (.A1(net2),
    .A2(net9),
    .B1(_029_),
    .B2(net18),
    .Y(_055_));
 sky130_fd_sc_hd__o21ai_1 _107_ (.A1(_053_),
    .A2(_054_),
    .B1(_055_),
    .Y(_002_));
 sky130_fd_sc_hd__nand2_1 _108_ (.A(net16),
    .B(net17),
    .Y(_016_));
 sky130_fd_sc_hd__inv_1 _109_ (.A(_016_),
    .Y(_017_));
 sky130_fd_sc_hd__nand3_1 _110_ (.A(_015_),
    .B(net18),
    .C(_017_),
    .Y(_018_));
 sky130_fd_sc_hd__nor2_1 _111_ (.A(_012_),
    .B(_018_),
    .Y(_056_));
 sky130_fd_sc_hd__ha_1 _112_ (.A(net12),
    .B(net13),
    .COUT(_000_),
    .SUM(_001_));
 sky130_fd_sc_hd__clkbuf_4 clkbuf_0_clk (.A(clk),
    .X(clknet_0_clk));
 sky130_fd_sc_hd__clkbuf_4 clkbuf_1_0__f_clk (.A(clknet_0_clk),
    .X(clknet_1_0__leaf_clk));
 sky130_fd_sc_hd__clkbuf_4 clkbuf_1_1__f_clk (.A(clknet_0_clk),
    .X(clknet_1_1__leaf_clk));
 sky130_fd_sc_hd__clkbuf_1 clkload0 (.A(clknet_1_1__leaf_clk));
 sky130_fd_sc_hd__dfrtp_1 \count[0]$_DFFE_PN0P_  (.D(_008_),
    .Q(net12),
    .RESET_B(net11),
    .CLK(clknet_1_0__leaf_clk));
 sky130_fd_sc_hd__dfrtp_1 \count[1]$_DFFE_PN0P_  (.D(_007_),
    .Q(net13),
    .RESET_B(net11),
    .CLK(clknet_1_0__leaf_clk));
 sky130_fd_sc_hd__dfrtp_1 \count[2]$_DFFE_PN0P_  (.D(_006_),
    .Q(net14),
    .RESET_B(net11),
    .CLK(clknet_1_0__leaf_clk));
 sky130_fd_sc_hd__dfrtp_1 \count[3]$_DFFE_PN0P_  (.D(_005_),
    .Q(net15),
    .RESET_B(net11),
    .CLK(clknet_1_0__leaf_clk));
 sky130_fd_sc_hd__dfrtp_1 \count[4]$_DFFE_PN0P_  (.D(_004_),
    .Q(net16),
    .RESET_B(net11),
    .CLK(clknet_1_1__leaf_clk));
 sky130_fd_sc_hd__dfrtp_1 \count[5]$_DFFE_PN0P_  (.D(_003_),
    .Q(net17),
    .RESET_B(net11),
    .CLK(clknet_1_1__leaf_clk));
 sky130_fd_sc_hd__dfrtp_1 \count[6]$_DFFE_PN0P_  (.D(_002_),
    .Q(net18),
    .RESET_B(net11),
    .CLK(clknet_1_1__leaf_clk));
 sky130_fd_sc_hd__dfrtp_1 \count[7]$_DFFE_PN0P_  (.D(_009_),
    .Q(net19),
    .RESET_B(net11),
    .CLK(clknet_1_1__leaf_clk));
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
 sky130_fd_sc_hd__dfrtp_1 \overflow$_DFF_PN0_  (.D(_056_),
    .Q(net20),
    .RESET_B(net11),
    .CLK(clknet_1_0__leaf_clk));
endmodule
