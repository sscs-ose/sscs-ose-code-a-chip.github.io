module release_counter_top (clk_ctr,
    data_in_ready,
    data_in_valid,
    data_out_ready,
    data_out_valid,
    rst_ctr,
    data_in,
    data_out);
 input clk_ctr;
 output data_in_ready;
 input data_in_valid;
 input data_out_ready;
 output data_out_valid;
 input rst_ctr;
 input [3:0] data_in;
 output [3:0] data_out;

 wire _00_;
 wire _01_;
 wire _02_;
 wire _03_;
 wire _04_;
 wire _05_;
 wire _06_;
 wire _07_;
 wire _08_;
 wire _09_;
 wire _10_;
 wire _11_;
 wire _12_;
 wire _13_;
 wire _14_;
 wire _15_;
 wire _16_;
 wire _17_;
 wire _18_;
 wire _19_;
 wire _20_;
 wire _21_;
 wire _22_;
 wire _23_;
 wire net1;
 wire net2;
 wire net3;
 wire net4;
 wire net8;
 wire net5;
 wire net9;
 wire net10;
 wire net11;
 wire net12;
 wire net6;
 wire net13;
 wire net7;
 wire clknet_0_clk_ctr;
 wire clknet_1_0__leaf_clk_ctr;
 wire clknet_1_1__leaf_clk_ctr;
 wire net14;
 wire net15;
 wire net16;
 wire net17;
 wire net18;

 sky130_fd_sc_hd__decap_3 FILLER_0_19 ();
 sky130_fd_sc_hd__fill_1 FILLER_0_27 ();
 sky130_fd_sc_hd__fill_2 FILLER_0_29 ();
 sky130_fd_sc_hd__decap_3 FILLER_0_39 ();
 sky130_fd_sc_hd__decap_3 FILLER_0_42 ();
 sky130_fd_sc_hd__decap_3 FILLER_0_45 ();
 sky130_fd_sc_hd__decap_3 FILLER_0_48 ();
 sky130_fd_sc_hd__decap_3 FILLER_0_51 ();
 sky130_fd_sc_hd__fill_2 FILLER_0_54 ();
 sky130_fd_sc_hd__decap_3 FILLER_0_57 ();
 sky130_fd_sc_hd__decap_3 FILLER_0_60 ();
 sky130_fd_sc_hd__fill_2 FILLER_0_63 ();
 sky130_fd_sc_hd__decap_3 FILLER_10_11 ();
 sky130_fd_sc_hd__decap_3 FILLER_10_14 ();
 sky130_fd_sc_hd__decap_3 FILLER_10_17 ();
 sky130_fd_sc_hd__decap_3 FILLER_10_20 ();
 sky130_fd_sc_hd__decap_3 FILLER_10_23 ();
 sky130_fd_sc_hd__fill_2 FILLER_10_26 ();
 sky130_fd_sc_hd__decap_3 FILLER_10_29 ();
 sky130_fd_sc_hd__decap_3 FILLER_10_32 ();
 sky130_fd_sc_hd__decap_3 FILLER_10_35 ();
 sky130_fd_sc_hd__decap_3 FILLER_10_38 ();
 sky130_fd_sc_hd__decap_3 FILLER_10_41 ();
 sky130_fd_sc_hd__decap_3 FILLER_10_44 ();
 sky130_fd_sc_hd__decap_3 FILLER_10_47 ();
 sky130_fd_sc_hd__decap_3 FILLER_10_50 ();
 sky130_fd_sc_hd__decap_3 FILLER_10_53 ();
 sky130_fd_sc_hd__decap_3 FILLER_10_57 ();
 sky130_fd_sc_hd__decap_3 FILLER_10_60 ();
 sky130_fd_sc_hd__fill_2 FILLER_10_63 ();
 sky130_fd_sc_hd__fill_1 FILLER_1_26 ();
 sky130_fd_sc_hd__decap_3 FILLER_1_35 ();
 sky130_fd_sc_hd__decap_3 FILLER_1_45 ();
 sky130_fd_sc_hd__fill_2 FILLER_1_48 ();
 sky130_fd_sc_hd__decap_3 FILLER_2_17 ();
 sky130_fd_sc_hd__fill_1 FILLER_2_20 ();
 sky130_fd_sc_hd__decap_3 FILLER_2_3 ();
 sky130_fd_sc_hd__decap_3 FILLER_2_6 ();
 sky130_fd_sc_hd__decap_3 FILLER_2_62 ();
 sky130_fd_sc_hd__fill_1 FILLER_3_21 ();
 sky130_fd_sc_hd__fill_1 FILLER_3_3 ();
 sky130_fd_sc_hd__fill_2 FILLER_4_26 ();
 sky130_fd_sc_hd__decap_3 FILLER_4_29 ();
 sky130_fd_sc_hd__decap_3 FILLER_4_3 ();
 sky130_fd_sc_hd__fill_2 FILLER_4_40 ();
 sky130_fd_sc_hd__fill_2 FILLER_4_49 ();
 sky130_fd_sc_hd__decap_3 FILLER_4_59 ();
 sky130_fd_sc_hd__decap_3 FILLER_4_62 ();
 sky130_fd_sc_hd__fill_1 FILLER_5_21 ();
 sky130_fd_sc_hd__fill_1 FILLER_5_49 ();
 sky130_fd_sc_hd__decap_3 FILLER_5_57 ();
 sky130_fd_sc_hd__decap_3 FILLER_5_60 ();
 sky130_fd_sc_hd__fill_2 FILLER_5_63 ();
 sky130_fd_sc_hd__fill_2 FILLER_6_17 ();
 sky130_fd_sc_hd__fill_1 FILLER_6_27 ();
 sky130_fd_sc_hd__fill_1 FILLER_6_29 ();
 sky130_fd_sc_hd__decap_3 FILLER_6_35 ();
 sky130_fd_sc_hd__fill_1 FILLER_7_27 ();
 sky130_fd_sc_hd__fill_1 FILLER_7_3 ();
 sky130_fd_sc_hd__fill_2 FILLER_7_63 ();
 sky130_fd_sc_hd__fill_2 FILLER_8_26 ();
 sky130_fd_sc_hd__decap_3 FILLER_8_29 ();
 sky130_fd_sc_hd__fill_1 FILLER_8_3 ();
 sky130_fd_sc_hd__decap_3 FILLER_8_32 ();
 sky130_fd_sc_hd__fill_2 FILLER_8_35 ();
 sky130_fd_sc_hd__decap_3 FILLER_8_54 ();
 sky130_fd_sc_hd__decap_3 FILLER_9_19 ();
 sky130_fd_sc_hd__decap_3 FILLER_9_22 ();
 sky130_fd_sc_hd__decap_3 FILLER_9_25 ();
 sky130_fd_sc_hd__decap_3 FILLER_9_28 ();
 sky130_fd_sc_hd__decap_3 FILLER_9_3 ();
 sky130_fd_sc_hd__decap_3 FILLER_9_31 ();
 sky130_fd_sc_hd__fill_2 FILLER_9_34 ();
 sky130_fd_sc_hd__fill_2 FILLER_9_43 ();
 sky130_fd_sc_hd__fill_1 FILLER_9_55 ();
 sky130_fd_sc_hd__decap_3 PHY_EDGE_ROW_0_Left_11 ();
 sky130_fd_sc_hd__decap_3 PHY_EDGE_ROW_0_Right_0 ();
 sky130_fd_sc_hd__decap_3 PHY_EDGE_ROW_10_Left_21 ();
 sky130_fd_sc_hd__decap_3 PHY_EDGE_ROW_10_Right_10 ();
 sky130_fd_sc_hd__decap_3 PHY_EDGE_ROW_1_Left_12 ();
 sky130_fd_sc_hd__decap_3 PHY_EDGE_ROW_1_Right_1 ();
 sky130_fd_sc_hd__decap_3 PHY_EDGE_ROW_2_Left_13 ();
 sky130_fd_sc_hd__decap_3 PHY_EDGE_ROW_2_Right_2 ();
 sky130_fd_sc_hd__decap_3 PHY_EDGE_ROW_3_Left_14 ();
 sky130_fd_sc_hd__decap_3 PHY_EDGE_ROW_3_Right_3 ();
 sky130_fd_sc_hd__decap_3 PHY_EDGE_ROW_4_Left_15 ();
 sky130_fd_sc_hd__decap_3 PHY_EDGE_ROW_4_Right_4 ();
 sky130_fd_sc_hd__decap_3 PHY_EDGE_ROW_5_Left_16 ();
 sky130_fd_sc_hd__decap_3 PHY_EDGE_ROW_5_Right_5 ();
 sky130_fd_sc_hd__decap_3 PHY_EDGE_ROW_6_Left_17 ();
 sky130_fd_sc_hd__decap_3 PHY_EDGE_ROW_6_Right_6 ();
 sky130_fd_sc_hd__decap_3 PHY_EDGE_ROW_7_Left_18 ();
 sky130_fd_sc_hd__decap_3 PHY_EDGE_ROW_7_Right_7 ();
 sky130_fd_sc_hd__decap_3 PHY_EDGE_ROW_8_Left_19 ();
 sky130_fd_sc_hd__decap_3 PHY_EDGE_ROW_8_Right_8 ();
 sky130_fd_sc_hd__decap_3 PHY_EDGE_ROW_9_Left_20 ();
 sky130_fd_sc_hd__decap_3 PHY_EDGE_ROW_9_Right_9 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 TAP_TAPCELL_ROW_0_22 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 TAP_TAPCELL_ROW_0_23 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 TAP_TAPCELL_ROW_10_33 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 TAP_TAPCELL_ROW_10_34 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 TAP_TAPCELL_ROW_1_24 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 TAP_TAPCELL_ROW_2_25 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 TAP_TAPCELL_ROW_3_26 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 TAP_TAPCELL_ROW_4_27 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 TAP_TAPCELL_ROW_5_28 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 TAP_TAPCELL_ROW_6_29 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 TAP_TAPCELL_ROW_7_30 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 TAP_TAPCELL_ROW_8_31 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 TAP_TAPCELL_ROW_9_32 ();
 sky130_fd_sc_hd__inv_2 _24_ (.A(net5),
    .Y(_05_));
 sky130_fd_sc_hd__nand2b_2 _25_ (.A_N(net6),
    .B(net15),
    .Y(net8));
 sky130_fd_sc_hd__and2_2 _26_ (.A(net5),
    .B(net8),
    .X(_06_));
 sky130_fd_sc_hd__a21oi_2 _27_ (.A1(net1),
    .A2(_06_),
    .B1(net17),
    .Y(_07_));
 sky130_fd_sc_hd__nand2_2 _28_ (.A(net9),
    .B(net1),
    .Y(_08_));
 sky130_fd_sc_hd__a31o_2 _29_ (.A1(net17),
    .A2(net1),
    .A3(_06_),
    .B1(net7),
    .X(_09_));
 sky130_fd_sc_hd__nor2_2 _30_ (.A(_07_),
    .B(_09_),
    .Y(_00_));
 sky130_fd_sc_hd__and2_2 _31_ (.A(net10),
    .B(net2),
    .X(_10_));
 sky130_fd_sc_hd__xor2_2 _32_ (.A(net10),
    .B(net2),
    .X(_11_));
 sky130_fd_sc_hd__xor2_2 _33_ (.A(_08_),
    .B(_11_),
    .X(_12_));
 sky130_fd_sc_hd__a21oi_2 _34_ (.A1(_06_),
    .A2(_12_),
    .B1(net7),
    .Y(_13_));
 sky130_fd_sc_hd__o21a_2 _35_ (.A1(net16),
    .A2(_06_),
    .B1(_13_),
    .X(_01_));
 sky130_fd_sc_hd__a31o_2 _36_ (.A1(net9),
    .A2(net1),
    .A3(_11_),
    .B1(_10_),
    .X(_14_));
 sky130_fd_sc_hd__and2_2 _37_ (.A(net11),
    .B(net3),
    .X(_15_));
 sky130_fd_sc_hd__nor2_2 _38_ (.A(net11),
    .B(net3),
    .Y(_16_));
 sky130_fd_sc_hd__nor2_2 _39_ (.A(_15_),
    .B(_16_),
    .Y(_17_));
 sky130_fd_sc_hd__xnor2_2 _40_ (.A(_14_),
    .B(_17_),
    .Y(_18_));
 sky130_fd_sc_hd__a21oi_2 _41_ (.A1(_06_),
    .A2(_18_),
    .B1(net7),
    .Y(_19_));
 sky130_fd_sc_hd__o21a_2 _42_ (.A1(net14),
    .A2(_06_),
    .B1(_19_),
    .X(_02_));
 sky130_fd_sc_hd__a21oi_2 _43_ (.A1(_14_),
    .A2(_17_),
    .B1(_15_),
    .Y(_20_));
 sky130_fd_sc_hd__nor2_2 _44_ (.A(net18),
    .B(_06_),
    .Y(_21_));
 sky130_fd_sc_hd__xnor2_2 _45_ (.A(net12),
    .B(net4),
    .Y(_22_));
 sky130_fd_sc_hd__xnor2_2 _46_ (.A(_20_),
    .B(_22_),
    .Y(_23_));
 sky130_fd_sc_hd__a211oi_2 _47_ (.A1(_06_),
    .A2(_23_),
    .B1(_21_),
    .C1(net7),
    .Y(_03_));
 sky130_fd_sc_hd__a21oi_2 _48_ (.A1(_05_),
    .A2(net8),
    .B1(net7),
    .Y(_04_));
 sky130_fd_sc_hd__dfxtp_2 _49_ (.CLK(clknet_1_0__leaf_clk_ctr),
    .D(_00_),
    .Q(net9));
 sky130_fd_sc_hd__dfxtp_2 _50_ (.CLK(clknet_1_1__leaf_clk_ctr),
    .D(_01_),
    .Q(net10));
 sky130_fd_sc_hd__dfxtp_2 _51_ (.CLK(clknet_1_1__leaf_clk_ctr),
    .D(_02_),
    .Q(net11));
 sky130_fd_sc_hd__dfxtp_2 _52_ (.CLK(clknet_1_0__leaf_clk_ctr),
    .D(_03_),
    .Q(net12));
 sky130_fd_sc_hd__dfxtp_2 _53_ (.CLK(clknet_1_0__leaf_clk_ctr),
    .D(_04_),
    .Q(net13));
 sky130_fd_sc_hd__clkbuf_16 clkbuf_0_clk_ctr (.A(clk_ctr),
    .X(clknet_0_clk_ctr));
 sky130_fd_sc_hd__clkbuf_16 clkbuf_1_0__f_clk_ctr (.A(clknet_0_clk_ctr),
    .X(clknet_1_0__leaf_clk_ctr));
 sky130_fd_sc_hd__clkbuf_16 clkbuf_1_1__f_clk_ctr (.A(clknet_0_clk_ctr),
    .X(clknet_1_1__leaf_clk_ctr));
 sky130_fd_sc_hd__clkbuf_4 clkload0 (.A(clknet_1_1__leaf_clk_ctr));
 sky130_fd_sc_hd__dlygate4sd3_1 hold14 (.A(net11),
    .X(net14));
 sky130_fd_sc_hd__dlygate4sd3_1 hold15 (.A(net13),
    .X(net15));
 sky130_fd_sc_hd__dlygate4sd3_1 hold16 (.A(net10),
    .X(net16));
 sky130_fd_sc_hd__dlygate4sd3_1 hold17 (.A(net9),
    .X(net17));
 sky130_fd_sc_hd__dlygate4sd3_1 hold18 (.A(net12),
    .X(net18));
 sky130_fd_sc_hd__clkdlybuf4s25_1 input1 (.A(data_in[0]),
    .X(net1));
 sky130_fd_sc_hd__clkdlybuf4s25_1 input2 (.A(data_in[1]),
    .X(net2));
 sky130_fd_sc_hd__clkdlybuf4s25_1 input3 (.A(data_in[2]),
    .X(net3));
 sky130_fd_sc_hd__clkdlybuf4s25_1 input4 (.A(data_in[3]),
    .X(net4));
 sky130_fd_sc_hd__clkdlybuf4s25_1 input5 (.A(data_in_valid),
    .X(net5));
 sky130_fd_sc_hd__clkdlybuf4s25_1 input6 (.A(data_out_ready),
    .X(net6));
 sky130_fd_sc_hd__clkdlybuf4s25_1 input7 (.A(rst_ctr),
    .X(net7));
 sky130_fd_sc_hd__clkdlybuf4s25_1 output10 (.A(net10),
    .X(data_out[1]));
 sky130_fd_sc_hd__clkdlybuf4s25_1 output11 (.A(net11),
    .X(data_out[2]));
 sky130_fd_sc_hd__clkdlybuf4s25_1 output12 (.A(net12),
    .X(data_out[3]));
 sky130_fd_sc_hd__clkdlybuf4s25_1 output13 (.A(net13),
    .X(data_out_valid));
 sky130_fd_sc_hd__clkdlybuf4s25_1 output8 (.A(net8),
    .X(data_in_ready));
 sky130_fd_sc_hd__clkdlybuf4s25_1 output9 (.A(net9),
    .X(data_out[0]));
endmodule
