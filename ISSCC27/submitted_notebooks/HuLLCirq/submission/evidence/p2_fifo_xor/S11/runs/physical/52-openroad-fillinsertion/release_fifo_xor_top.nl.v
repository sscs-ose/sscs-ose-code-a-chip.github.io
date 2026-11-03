module release_fifo_xor_top (clk_pipe,
    data_i_ready,
    data_i_valid,
    data_o_ready,
    data_o_valid,
    rst_pipe_n,
    data_i,
    data_o);
 input clk_pipe;
 output data_i_ready;
 input data_i_valid;
 input data_o_ready;
 output data_o_valid;
 input rst_pipe_n;
 input [7:0] data_i;
 output [7:0] data_o;

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
 wire net1;
 wire net2;
 wire net3;
 wire net4;
 wire net5;
 wire net6;
 wire net7;
 wire net8;
 wire net12;
 wire net9;
 wire net13;
 wire net14;
 wire net15;
 wire net16;
 wire net17;
 wire net18;
 wire net19;
 wire net20;
 wire net10;
 wire net21;
 wire net11;
 wire \u_6e6f64655f326266333064306661616565.count[0] ;
 wire \u_6e6f64655f326266333064306661616565.count[1] ;
 wire \u_6e6f64655f326266333064306661616565.head[0] ;
 wire \u_6e6f64655f326266333064306661616565.head[1] ;
 wire \u_6e6f64655f326266333064306661616565.head[2] ;
 wire \u_6e6f64655f326266333064306661616565.head[3] ;
 wire \u_6e6f64655f326266333064306661616565.head[4] ;
 wire \u_6e6f64655f326266333064306661616565.head[5] ;
 wire \u_6e6f64655f326266333064306661616565.head[6] ;
 wire \u_6e6f64655f326266333064306661616565.head[7] ;
 wire \u_6e6f64655f326266333064306661616565.tail[0] ;
 wire \u_6e6f64655f326266333064306661616565.tail[1] ;
 wire \u_6e6f64655f326266333064306661616565.tail[2] ;
 wire \u_6e6f64655f326266333064306661616565.tail[3] ;
 wire \u_6e6f64655f326266333064306661616565.tail[4] ;
 wire \u_6e6f64655f326266333064306661616565.tail[5] ;
 wire \u_6e6f64655f326266333064306661616565.tail[6] ;
 wire \u_6e6f64655f326266333064306661616565.tail[7] ;
 wire net22;
 wire net23;
 wire net24;
 wire clknet_0_clk_pipe;
 wire clknet_1_0__leaf_clk_pipe;
 wire clknet_1_1__leaf_clk_pipe;
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
 wire net36;
 wire net37;
 wire net38;
 wire net39;
 wire net40;
 wire net41;
 wire net42;

 sky130_fd_sc_hd__decap_3 FILLER_0_102 ();
 sky130_fd_sc_hd__decap_3 FILLER_0_105 ();
 sky130_fd_sc_hd__decap_3 FILLER_0_12 ();
 sky130_fd_sc_hd__decap_3 FILLER_0_15 ();
 sky130_fd_sc_hd__decap_3 FILLER_0_18 ();
 sky130_fd_sc_hd__decap_3 FILLER_0_21 ();
 sky130_fd_sc_hd__decap_3 FILLER_0_24 ();
 sky130_fd_sc_hd__fill_1 FILLER_0_27 ();
 sky130_fd_sc_hd__fill_2 FILLER_0_29 ();
 sky130_fd_sc_hd__decap_3 FILLER_0_3 ();
 sky130_fd_sc_hd__decap_3 FILLER_0_39 ();
 sky130_fd_sc_hd__decap_3 FILLER_0_42 ();
 sky130_fd_sc_hd__decap_3 FILLER_0_45 ();
 sky130_fd_sc_hd__decap_3 FILLER_0_57 ();
 sky130_fd_sc_hd__decap_3 FILLER_0_6 ();
 sky130_fd_sc_hd__decap_3 FILLER_0_60 ();
 sky130_fd_sc_hd__decap_3 FILLER_0_63 ();
 sky130_fd_sc_hd__decap_3 FILLER_0_66 ();
 sky130_fd_sc_hd__decap_3 FILLER_0_69 ();
 sky130_fd_sc_hd__fill_1 FILLER_0_72 ();
 sky130_fd_sc_hd__decap_3 FILLER_0_78 ();
 sky130_fd_sc_hd__decap_3 FILLER_0_81 ();
 sky130_fd_sc_hd__decap_3 FILLER_0_9 ();
 sky130_fd_sc_hd__decap_3 FILLER_0_93 ();
 sky130_fd_sc_hd__decap_3 FILLER_0_96 ();
 sky130_fd_sc_hd__decap_3 FILLER_0_99 ();
 sky130_fd_sc_hd__decap_3 FILLER_10_104 ();
 sky130_fd_sc_hd__fill_1 FILLER_10_107 ();
 sky130_fd_sc_hd__decap_3 FILLER_10_11 ();
 sky130_fd_sc_hd__fill_1 FILLER_10_14 ();
 sky130_fd_sc_hd__decap_3 FILLER_10_24 ();
 sky130_fd_sc_hd__fill_1 FILLER_10_27 ();
 sky130_fd_sc_hd__decap_3 FILLER_10_29 ();
 sky130_fd_sc_hd__fill_1 FILLER_10_32 ();
 sky130_fd_sc_hd__decap_3 FILLER_10_50 ();
 sky130_fd_sc_hd__decap_3 FILLER_10_53 ();
 sky130_fd_sc_hd__fill_1 FILLER_10_56 ();
 sky130_fd_sc_hd__decap_3 FILLER_10_68 ();
 sky130_fd_sc_hd__fill_1 FILLER_10_71 ();
 sky130_fd_sc_hd__decap_3 FILLER_10_80 ();
 sky130_fd_sc_hd__fill_1 FILLER_10_83 ();
 sky130_fd_sc_hd__decap_3 FILLER_10_93 ();
 sky130_fd_sc_hd__fill_2 FILLER_10_96 ();
 sky130_fd_sc_hd__decap_3 FILLER_11_24 ();
 sky130_fd_sc_hd__decap_3 FILLER_11_27 ();
 sky130_fd_sc_hd__decap_3 FILLER_11_3 ();
 sky130_fd_sc_hd__decap_3 FILLER_11_30 ();
 sky130_fd_sc_hd__fill_2 FILLER_11_41 ();
 sky130_fd_sc_hd__decap_3 FILLER_11_51 ();
 sky130_fd_sc_hd__fill_2 FILLER_11_54 ();
 sky130_fd_sc_hd__fill_2 FILLER_11_57 ();
 sky130_fd_sc_hd__fill_1 FILLER_11_6 ();
 sky130_fd_sc_hd__decap_3 FILLER_11_65 ();
 sky130_fd_sc_hd__decap_3 FILLER_11_68 ();
 sky130_fd_sc_hd__decap_3 FILLER_11_71 ();
 sky130_fd_sc_hd__fill_1 FILLER_11_74 ();
 sky130_fd_sc_hd__decap_3 FILLER_12_16 ();
 sky130_fd_sc_hd__fill_1 FILLER_12_19 ();
 sky130_fd_sc_hd__decap_3 FILLER_12_29 ();
 sky130_fd_sc_hd__decap_3 FILLER_12_3 ();
 sky130_fd_sc_hd__decap_3 FILLER_12_32 ();
 sky130_fd_sc_hd__decap_3 FILLER_12_35 ();
 sky130_fd_sc_hd__decap_3 FILLER_12_38 ();
 sky130_fd_sc_hd__decap_3 FILLER_12_41 ();
 sky130_fd_sc_hd__decap_3 FILLER_12_44 ();
 sky130_fd_sc_hd__decap_3 FILLER_12_47 ();
 sky130_fd_sc_hd__decap_3 FILLER_12_50 ();
 sky130_fd_sc_hd__decap_3 FILLER_12_53 ();
 sky130_fd_sc_hd__decap_3 FILLER_12_56 ();
 sky130_fd_sc_hd__fill_1 FILLER_12_59 ();
 sky130_fd_sc_hd__fill_2 FILLER_12_6 ();
 sky130_fd_sc_hd__decap_3 FILLER_12_66 ();
 sky130_fd_sc_hd__decap_3 FILLER_12_69 ();
 sky130_fd_sc_hd__decap_3 FILLER_12_72 ();
 sky130_fd_sc_hd__decap_3 FILLER_12_75 ();
 sky130_fd_sc_hd__decap_3 FILLER_12_85 ();
 sky130_fd_sc_hd__fill_1 FILLER_12_88 ();
 sky130_fd_sc_hd__decap_3 FILLER_12_97 ();
 sky130_fd_sc_hd__decap_3 FILLER_13_104 ();
 sky130_fd_sc_hd__fill_1 FILLER_13_107 ();
 sky130_fd_sc_hd__fill_2 FILLER_13_11 ();
 sky130_fd_sc_hd__decap_3 FILLER_13_23 ();
 sky130_fd_sc_hd__decap_3 FILLER_13_26 ();
 sky130_fd_sc_hd__decap_3 FILLER_13_29 ();
 sky130_fd_sc_hd__decap_3 FILLER_13_32 ();
 sky130_fd_sc_hd__decap_3 FILLER_13_35 ();
 sky130_fd_sc_hd__decap_3 FILLER_13_38 ();
 sky130_fd_sc_hd__decap_3 FILLER_13_51 ();
 sky130_fd_sc_hd__fill_2 FILLER_13_54 ();
 sky130_fd_sc_hd__decap_3 FILLER_13_77 ();
 sky130_fd_sc_hd__decap_3 FILLER_13_80 ();
 sky130_fd_sc_hd__decap_3 FILLER_13_91 ();
 sky130_fd_sc_hd__fill_2 FILLER_13_94 ();
 sky130_fd_sc_hd__fill_2 FILLER_14_106 ();
 sky130_fd_sc_hd__decap_3 FILLER_14_24 ();
 sky130_fd_sc_hd__fill_1 FILLER_14_27 ();
 sky130_fd_sc_hd__decap_3 FILLER_14_29 ();
 sky130_fd_sc_hd__decap_3 FILLER_14_3 ();
 sky130_fd_sc_hd__decap_3 FILLER_14_37 ();
 sky130_fd_sc_hd__fill_1 FILLER_14_59 ();
 sky130_fd_sc_hd__fill_1 FILLER_14_6 ();
 sky130_fd_sc_hd__decap_3 FILLER_14_67 ();
 sky130_fd_sc_hd__decap_3 FILLER_14_70 ();
 sky130_fd_sc_hd__decap_3 FILLER_14_73 ();
 sky130_fd_sc_hd__decap_3 FILLER_14_76 ();
 sky130_fd_sc_hd__decap_3 FILLER_14_85 ();
 sky130_fd_sc_hd__fill_1 FILLER_14_88 ();
 sky130_fd_sc_hd__fill_2 FILLER_15_25 ();
 sky130_fd_sc_hd__decap_3 FILLER_15_3 ();
 sky130_fd_sc_hd__fill_1 FILLER_15_47 ();
 sky130_fd_sc_hd__decap_3 FILLER_15_53 ();
 sky130_fd_sc_hd__fill_2 FILLER_15_6 ();
 sky130_fd_sc_hd__decap_3 FILLER_15_80 ();
 sky130_fd_sc_hd__fill_1 FILLER_15_83 ();
 sky130_fd_sc_hd__decap_3 FILLER_16_102 ();
 sky130_fd_sc_hd__decap_3 FILLER_16_105 ();
 sky130_fd_sc_hd__decap_3 FILLER_16_17 ();
 sky130_fd_sc_hd__decap_3 FILLER_16_29 ();
 sky130_fd_sc_hd__decap_3 FILLER_16_3 ();
 sky130_fd_sc_hd__decap_3 FILLER_16_32 ();
 sky130_fd_sc_hd__decap_3 FILLER_16_35 ();
 sky130_fd_sc_hd__decap_3 FILLER_16_38 ();
 sky130_fd_sc_hd__fill_2 FILLER_16_41 ();
 sky130_fd_sc_hd__decap_3 FILLER_16_56 ();
 sky130_fd_sc_hd__decap_3 FILLER_16_59 ();
 sky130_fd_sc_hd__decap_3 FILLER_16_6 ();
 sky130_fd_sc_hd__decap_3 FILLER_16_62 ();
 sky130_fd_sc_hd__decap_3 FILLER_16_81 ();
 sky130_fd_sc_hd__decap_3 FILLER_17_100 ();
 sky130_fd_sc_hd__decap_3 FILLER_17_103 ();
 sky130_fd_sc_hd__fill_2 FILLER_17_106 ();
 sky130_fd_sc_hd__decap_3 FILLER_17_11 ();
 sky130_fd_sc_hd__decap_3 FILLER_17_14 ();
 sky130_fd_sc_hd__decap_3 FILLER_17_17 ();
 sky130_fd_sc_hd__decap_3 FILLER_17_20 ();
 sky130_fd_sc_hd__decap_3 FILLER_17_23 ();
 sky130_fd_sc_hd__fill_2 FILLER_17_26 ();
 sky130_fd_sc_hd__decap_3 FILLER_17_29 ();
 sky130_fd_sc_hd__decap_3 FILLER_17_32 ();
 sky130_fd_sc_hd__decap_3 FILLER_17_35 ();
 sky130_fd_sc_hd__decap_3 FILLER_17_38 ();
 sky130_fd_sc_hd__decap_3 FILLER_17_41 ();
 sky130_fd_sc_hd__decap_3 FILLER_17_44 ();
 sky130_fd_sc_hd__decap_3 FILLER_17_47 ();
 sky130_fd_sc_hd__decap_3 FILLER_17_50 ();
 sky130_fd_sc_hd__decap_3 FILLER_17_53 ();
 sky130_fd_sc_hd__decap_3 FILLER_17_57 ();
 sky130_fd_sc_hd__decap_3 FILLER_17_60 ();
 sky130_fd_sc_hd__decap_3 FILLER_17_63 ();
 sky130_fd_sc_hd__fill_1 FILLER_17_66 ();
 sky130_fd_sc_hd__fill_1 FILLER_17_83 ();
 sky130_fd_sc_hd__decap_3 FILLER_17_85 ();
 sky130_fd_sc_hd__fill_1 FILLER_17_88 ();
 sky130_fd_sc_hd__decap_3 FILLER_17_97 ();
 sky130_fd_sc_hd__decap_3 FILLER_1_100 ();
 sky130_fd_sc_hd__decap_3 FILLER_1_103 ();
 sky130_fd_sc_hd__fill_2 FILLER_1_106 ();
 sky130_fd_sc_hd__decap_3 FILLER_1_12 ();
 sky130_fd_sc_hd__decap_3 FILLER_1_15 ();
 sky130_fd_sc_hd__fill_2 FILLER_1_18 ();
 sky130_fd_sc_hd__decap_3 FILLER_1_3 ();
 sky130_fd_sc_hd__decap_3 FILLER_1_37 ();
 sky130_fd_sc_hd__fill_1 FILLER_1_40 ();
 sky130_fd_sc_hd__fill_1 FILLER_1_55 ();
 sky130_fd_sc_hd__decap_3 FILLER_1_6 ();
 sky130_fd_sc_hd__fill_1 FILLER_1_63 ();
 sky130_fd_sc_hd__decap_3 FILLER_1_72 ();
 sky130_fd_sc_hd__decap_3 FILLER_1_9 ();
 sky130_fd_sc_hd__fill_1 FILLER_1_91 ();
 sky130_fd_sc_hd__fill_1 FILLER_2_107 ();
 sky130_fd_sc_hd__decap_3 FILLER_2_12 ();
 sky130_fd_sc_hd__decap_3 FILLER_2_15 ();
 sky130_fd_sc_hd__fill_2 FILLER_2_18 ();
 sky130_fd_sc_hd__decap_3 FILLER_2_3 ();
 sky130_fd_sc_hd__fill_2 FILLER_2_38 ();
 sky130_fd_sc_hd__fill_1 FILLER_2_57 ();
 sky130_fd_sc_hd__decap_3 FILLER_2_6 ();
 sky130_fd_sc_hd__fill_1 FILLER_2_64 ();
 sky130_fd_sc_hd__fill_2 FILLER_2_82 ();
 sky130_fd_sc_hd__decap_3 FILLER_2_9 ();
 sky130_fd_sc_hd__decap_3 FILLER_3_3 ();
 sky130_fd_sc_hd__fill_1 FILLER_3_31 ();
 sky130_fd_sc_hd__fill_2 FILLER_3_57 ();
 sky130_fd_sc_hd__decap_3 FILLER_3_65 ();
 sky130_fd_sc_hd__decap_3 FILLER_3_68 ();
 sky130_fd_sc_hd__decap_3 FILLER_3_71 ();
 sky130_fd_sc_hd__decap_3 FILLER_3_74 ();
 sky130_fd_sc_hd__decap_3 FILLER_3_77 ();
 sky130_fd_sc_hd__decap_3 FILLER_3_80 ();
 sky130_fd_sc_hd__decap_3 FILLER_3_83 ();
 sky130_fd_sc_hd__decap_3 FILLER_3_86 ();
 sky130_fd_sc_hd__decap_3 FILLER_3_89 ();
 sky130_fd_sc_hd__fill_1 FILLER_4_27 ();
 sky130_fd_sc_hd__fill_2 FILLER_4_3 ();
 sky130_fd_sc_hd__decap_3 FILLER_4_34 ();
 sky130_fd_sc_hd__decap_3 FILLER_4_37 ();
 sky130_fd_sc_hd__decap_3 FILLER_4_40 ();
 sky130_fd_sc_hd__decap_3 FILLER_4_43 ();
 sky130_fd_sc_hd__fill_2 FILLER_4_46 ();
 sky130_fd_sc_hd__decap_3 FILLER_4_68 ();
 sky130_fd_sc_hd__decap_3 FILLER_4_71 ();
 sky130_fd_sc_hd__decap_3 FILLER_4_74 ();
 sky130_fd_sc_hd__decap_3 FILLER_4_77 ();
 sky130_fd_sc_hd__decap_3 FILLER_4_80 ();
 sky130_fd_sc_hd__fill_1 FILLER_4_83 ();
 sky130_fd_sc_hd__decap_3 FILLER_4_85 ();
 sky130_fd_sc_hd__decap_3 FILLER_4_88 ();
 sky130_fd_sc_hd__decap_3 FILLER_4_91 ();
 sky130_fd_sc_hd__decap_3 FILLER_4_94 ();
 sky130_fd_sc_hd__decap_3 FILLER_4_97 ();
 sky130_fd_sc_hd__fill_2 FILLER_5_106 ();
 sky130_fd_sc_hd__decap_3 FILLER_5_19 ();
 sky130_fd_sc_hd__decap_3 FILLER_5_22 ();
 sky130_fd_sc_hd__decap_3 FILLER_5_25 ();
 sky130_fd_sc_hd__decap_3 FILLER_5_28 ();
 sky130_fd_sc_hd__decap_3 FILLER_5_31 ();
 sky130_fd_sc_hd__decap_3 FILLER_5_34 ();
 sky130_fd_sc_hd__decap_3 FILLER_5_37 ();
 sky130_fd_sc_hd__decap_3 FILLER_5_40 ();
 sky130_fd_sc_hd__decap_3 FILLER_5_43 ();
 sky130_fd_sc_hd__decap_3 FILLER_5_46 ();
 sky130_fd_sc_hd__decap_3 FILLER_5_49 ();
 sky130_fd_sc_hd__decap_3 FILLER_5_52 ();
 sky130_fd_sc_hd__fill_1 FILLER_5_55 ();
 sky130_fd_sc_hd__decap_3 FILLER_5_57 ();
 sky130_fd_sc_hd__decap_3 FILLER_5_60 ();
 sky130_fd_sc_hd__decap_3 FILLER_5_63 ();
 sky130_fd_sc_hd__decap_3 FILLER_5_66 ();
 sky130_fd_sc_hd__decap_3 FILLER_5_69 ();
 sky130_fd_sc_hd__decap_3 FILLER_5_72 ();
 sky130_fd_sc_hd__fill_1 FILLER_5_75 ();
 sky130_fd_sc_hd__decap_3 FILLER_6_25 ();
 sky130_fd_sc_hd__decap_3 FILLER_6_29 ();
 sky130_fd_sc_hd__decap_3 FILLER_6_3 ();
 sky130_fd_sc_hd__decap_3 FILLER_6_32 ();
 sky130_fd_sc_hd__fill_1 FILLER_6_35 ();
 sky130_fd_sc_hd__decap_3 FILLER_6_50 ();
 sky130_fd_sc_hd__fill_1 FILLER_6_53 ();
 sky130_fd_sc_hd__fill_2 FILLER_6_6 ();
 sky130_fd_sc_hd__decap_3 FILLER_6_60 ();
 sky130_fd_sc_hd__decap_3 FILLER_6_71 ();
 sky130_fd_sc_hd__fill_2 FILLER_6_82 ();
 sky130_fd_sc_hd__decap_3 FILLER_6_85 ();
 sky130_fd_sc_hd__fill_2 FILLER_6_88 ();
 sky130_fd_sc_hd__fill_2 FILLER_6_98 ();
 sky130_fd_sc_hd__decap_3 FILLER_7_25 ();
 sky130_fd_sc_hd__decap_3 FILLER_7_28 ();
 sky130_fd_sc_hd__decap_3 FILLER_7_3 ();
 sky130_fd_sc_hd__decap_3 FILLER_7_31 ();
 sky130_fd_sc_hd__decap_3 FILLER_7_51 ();
 sky130_fd_sc_hd__fill_2 FILLER_7_54 ();
 sky130_fd_sc_hd__fill_2 FILLER_7_57 ();
 sky130_fd_sc_hd__fill_2 FILLER_7_6 ();
 sky130_fd_sc_hd__decap_3 FILLER_7_90 ();
 sky130_fd_sc_hd__fill_1 FILLER_7_93 ();
 sky130_fd_sc_hd__decap_3 FILLER_8_17 ();
 sky130_fd_sc_hd__decap_3 FILLER_8_29 ();
 sky130_fd_sc_hd__decap_3 FILLER_8_3 ();
 sky130_fd_sc_hd__decap_3 FILLER_8_6 ();
 sky130_fd_sc_hd__decap_3 FILLER_8_68 ();
 sky130_fd_sc_hd__decap_3 FILLER_8_71 ();
 sky130_fd_sc_hd__decap_3 FILLER_8_74 ();
 sky130_fd_sc_hd__decap_3 FILLER_8_77 ();
 sky130_fd_sc_hd__decap_3 FILLER_8_80 ();
 sky130_fd_sc_hd__fill_1 FILLER_8_83 ();
 sky130_fd_sc_hd__decap_3 FILLER_9_24 ();
 sky130_fd_sc_hd__decap_3 FILLER_9_27 ();
 sky130_fd_sc_hd__decap_3 FILLER_9_30 ();
 sky130_fd_sc_hd__fill_2 FILLER_9_33 ();
 sky130_fd_sc_hd__decap_3 FILLER_9_49 ();
 sky130_fd_sc_hd__decap_3 FILLER_9_52 ();
 sky130_fd_sc_hd__fill_1 FILLER_9_55 ();
 sky130_fd_sc_hd__decap_3 FILLER_9_57 ();
 sky130_fd_sc_hd__decap_3 FILLER_9_60 ();
 sky130_fd_sc_hd__decap_3 FILLER_9_63 ();
 sky130_fd_sc_hd__decap_3 FILLER_9_66 ();
 sky130_fd_sc_hd__decap_3 FILLER_9_69 ();
 sky130_fd_sc_hd__decap_3 FILLER_9_72 ();
 sky130_fd_sc_hd__decap_3 FILLER_9_75 ();
 sky130_fd_sc_hd__decap_3 PHY_EDGE_ROW_0_Left_18 ();
 sky130_fd_sc_hd__decap_3 PHY_EDGE_ROW_0_Right_0 ();
 sky130_fd_sc_hd__decap_3 PHY_EDGE_ROW_10_Left_28 ();
 sky130_fd_sc_hd__decap_3 PHY_EDGE_ROW_10_Right_10 ();
 sky130_fd_sc_hd__decap_3 PHY_EDGE_ROW_11_Left_29 ();
 sky130_fd_sc_hd__decap_3 PHY_EDGE_ROW_11_Right_11 ();
 sky130_fd_sc_hd__decap_3 PHY_EDGE_ROW_12_Left_30 ();
 sky130_fd_sc_hd__decap_3 PHY_EDGE_ROW_12_Right_12 ();
 sky130_fd_sc_hd__decap_3 PHY_EDGE_ROW_13_Left_31 ();
 sky130_fd_sc_hd__decap_3 PHY_EDGE_ROW_13_Right_13 ();
 sky130_fd_sc_hd__decap_3 PHY_EDGE_ROW_14_Left_32 ();
 sky130_fd_sc_hd__decap_3 PHY_EDGE_ROW_14_Right_14 ();
 sky130_fd_sc_hd__decap_3 PHY_EDGE_ROW_15_Left_33 ();
 sky130_fd_sc_hd__decap_3 PHY_EDGE_ROW_15_Right_15 ();
 sky130_fd_sc_hd__decap_3 PHY_EDGE_ROW_16_Left_34 ();
 sky130_fd_sc_hd__decap_3 PHY_EDGE_ROW_16_Right_16 ();
 sky130_fd_sc_hd__decap_3 PHY_EDGE_ROW_17_Left_35 ();
 sky130_fd_sc_hd__decap_3 PHY_EDGE_ROW_17_Right_17 ();
 sky130_fd_sc_hd__decap_3 PHY_EDGE_ROW_1_Left_19 ();
 sky130_fd_sc_hd__decap_3 PHY_EDGE_ROW_1_Right_1 ();
 sky130_fd_sc_hd__decap_3 PHY_EDGE_ROW_2_Left_20 ();
 sky130_fd_sc_hd__decap_3 PHY_EDGE_ROW_2_Right_2 ();
 sky130_fd_sc_hd__decap_3 PHY_EDGE_ROW_3_Left_21 ();
 sky130_fd_sc_hd__decap_3 PHY_EDGE_ROW_3_Right_3 ();
 sky130_fd_sc_hd__decap_3 PHY_EDGE_ROW_4_Left_22 ();
 sky130_fd_sc_hd__decap_3 PHY_EDGE_ROW_4_Right_4 ();
 sky130_fd_sc_hd__decap_3 PHY_EDGE_ROW_5_Left_23 ();
 sky130_fd_sc_hd__decap_3 PHY_EDGE_ROW_5_Right_5 ();
 sky130_fd_sc_hd__decap_3 PHY_EDGE_ROW_6_Left_24 ();
 sky130_fd_sc_hd__decap_3 PHY_EDGE_ROW_6_Right_6 ();
 sky130_fd_sc_hd__decap_3 PHY_EDGE_ROW_7_Left_25 ();
 sky130_fd_sc_hd__decap_3 PHY_EDGE_ROW_7_Right_7 ();
 sky130_fd_sc_hd__decap_3 PHY_EDGE_ROW_8_Left_26 ();
 sky130_fd_sc_hd__decap_3 PHY_EDGE_ROW_8_Right_8 ();
 sky130_fd_sc_hd__decap_3 PHY_EDGE_ROW_9_Left_27 ();
 sky130_fd_sc_hd__decap_3 PHY_EDGE_ROW_9_Right_9 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 TAP_TAPCELL_ROW_0_36 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 TAP_TAPCELL_ROW_0_37 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 TAP_TAPCELL_ROW_0_38 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 TAP_TAPCELL_ROW_10_52 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 TAP_TAPCELL_ROW_10_53 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 TAP_TAPCELL_ROW_11_54 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 TAP_TAPCELL_ROW_12_55 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 TAP_TAPCELL_ROW_12_56 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 TAP_TAPCELL_ROW_13_57 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 TAP_TAPCELL_ROW_14_58 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 TAP_TAPCELL_ROW_14_59 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 TAP_TAPCELL_ROW_15_60 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 TAP_TAPCELL_ROW_16_61 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 TAP_TAPCELL_ROW_16_62 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 TAP_TAPCELL_ROW_17_63 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 TAP_TAPCELL_ROW_17_64 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 TAP_TAPCELL_ROW_17_65 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 TAP_TAPCELL_ROW_1_39 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 TAP_TAPCELL_ROW_2_40 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 TAP_TAPCELL_ROW_2_41 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 TAP_TAPCELL_ROW_3_42 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 TAP_TAPCELL_ROW_4_43 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 TAP_TAPCELL_ROW_4_44 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 TAP_TAPCELL_ROW_5_45 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 TAP_TAPCELL_ROW_6_46 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 TAP_TAPCELL_ROW_6_47 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 TAP_TAPCELL_ROW_7_48 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 TAP_TAPCELL_ROW_8_49 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 TAP_TAPCELL_ROW_8_50 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 TAP_TAPCELL_ROW_9_51 ();
 sky130_fd_sc_hd__inv_2 _054_ (.A(\u_6e6f64655f326266333064306661616565.count[1] ),
    .Y(net12));
 sky130_fd_sc_hd__inv_2 _055_ (.A(net24),
    .Y(_029_));
 sky130_fd_sc_hd__or2_2 _056_ (.A(\u_6e6f64655f326266333064306661616565.count[1] ),
    .B(\u_6e6f64655f326266333064306661616565.count[0] ),
    .X(net21));
 sky130_fd_sc_hd__and2_2 _057_ (.A(\u_6e6f64655f326266333064306661616565.head[1] ),
    .B(net22),
    .X(net14));
 sky130_fd_sc_hd__and2_2 _058_ (.A(\u_6e6f64655f326266333064306661616565.head[3] ),
    .B(net22),
    .X(net16));
 sky130_fd_sc_hd__and2_2 _059_ (.A(\u_6e6f64655f326266333064306661616565.head[4] ),
    .B(net22),
    .X(net17));
 sky130_fd_sc_hd__and2_2 _060_ (.A(\u_6e6f64655f326266333064306661616565.head[6] ),
    .B(net22),
    .X(net19));
 sky130_fd_sc_hd__nand2_2 _061_ (.A(\u_6e6f64655f326266333064306661616565.head[0] ),
    .B(net22),
    .Y(net13));
 sky130_fd_sc_hd__nand2_2 _062_ (.A(\u_6e6f64655f326266333064306661616565.head[2] ),
    .B(net22),
    .Y(net15));
 sky130_fd_sc_hd__nand2_2 _063_ (.A(\u_6e6f64655f326266333064306661616565.head[5] ),
    .B(net22),
    .Y(net18));
 sky130_fd_sc_hd__nand2_2 _064_ (.A(\u_6e6f64655f326266333064306661616565.head[7] ),
    .B(net22),
    .Y(net20));
 sky130_fd_sc_hd__nand2b_2 _065_ (.A_N(\u_6e6f64655f326266333064306661616565.count[1] ),
    .B(net9),
    .Y(_030_));
 sky130_fd_sc_hd__o21a_2 _066_ (.A1(\u_6e6f64655f326266333064306661616565.count[1] ),
    .A2(\u_6e6f64655f326266333064306661616565.count[0] ),
    .B1(net10),
    .X(_031_));
 sky130_fd_sc_hd__a21oi_2 _067_ (.A1(net12),
    .A2(net9),
    .B1(_031_),
    .Y(_032_));
 sky130_fd_sc_hd__nand2_2 _068_ (.A(_030_),
    .B(_031_),
    .Y(_033_));
 sky130_fd_sc_hd__nor2_2 _069_ (.A(_030_),
    .B(_031_),
    .Y(_034_));
 sky130_fd_sc_hd__xnor2_2 _070_ (.A(_030_),
    .B(_031_),
    .Y(_035_));
 sky130_fd_sc_hd__xnor2_2 _071_ (.A(\u_6e6f64655f326266333064306661616565.count[0] ),
    .B(_035_),
    .Y(_036_));
 sky130_fd_sc_hd__nor2_2 _072_ (.A(_032_),
    .B(_036_),
    .Y(_037_));
 sky130_fd_sc_hd__mux2_1 _073_ (.A0(\u_6e6f64655f326266333064306661616565.tail[0] ),
    .A1(net1),
    .S(_033_),
    .X(_038_));
 sky130_fd_sc_hd__or3_2 _074_ (.A(_032_),
    .B(_036_),
    .C(_038_),
    .X(_039_));
 sky130_fd_sc_hd__o211a_2 _075_ (.A1(net30),
    .A2(_037_),
    .B1(_039_),
    .C1(net23),
    .X(_000_));
 sky130_fd_sc_hd__mux2_1 _076_ (.A0(\u_6e6f64655f326266333064306661616565.tail[1] ),
    .A1(net2),
    .S(_033_),
    .X(_040_));
 sky130_fd_sc_hd__or3_2 _077_ (.A(_032_),
    .B(_036_),
    .C(_040_),
    .X(_041_));
 sky130_fd_sc_hd__o211a_2 _078_ (.A1(net27),
    .A2(_037_),
    .B1(_041_),
    .C1(net23),
    .X(_001_));
 sky130_fd_sc_hd__mux2_1 _079_ (.A0(\u_6e6f64655f326266333064306661616565.tail[2] ),
    .A1(net3),
    .S(_033_),
    .X(_042_));
 sky130_fd_sc_hd__or3_2 _080_ (.A(_032_),
    .B(_036_),
    .C(_042_),
    .X(_043_));
 sky130_fd_sc_hd__o211a_2 _081_ (.A1(net32),
    .A2(_037_),
    .B1(_043_),
    .C1(net23),
    .X(_002_));
 sky130_fd_sc_hd__mux2_1 _082_ (.A0(\u_6e6f64655f326266333064306661616565.tail[3] ),
    .A1(net4),
    .S(_033_),
    .X(_044_));
 sky130_fd_sc_hd__or3_2 _083_ (.A(_032_),
    .B(_036_),
    .C(_044_),
    .X(_045_));
 sky130_fd_sc_hd__o211a_2 _084_ (.A1(net25),
    .A2(_037_),
    .B1(_045_),
    .C1(net24),
    .X(_003_));
 sky130_fd_sc_hd__mux2_1 _085_ (.A0(\u_6e6f64655f326266333064306661616565.tail[4] ),
    .A1(net5),
    .S(_033_),
    .X(_046_));
 sky130_fd_sc_hd__or3_2 _086_ (.A(_032_),
    .B(_036_),
    .C(_046_),
    .X(_047_));
 sky130_fd_sc_hd__o211a_2 _087_ (.A1(net26),
    .A2(_037_),
    .B1(_047_),
    .C1(net24),
    .X(_004_));
 sky130_fd_sc_hd__mux2_1 _088_ (.A0(\u_6e6f64655f326266333064306661616565.tail[5] ),
    .A1(net6),
    .S(_033_),
    .X(_048_));
 sky130_fd_sc_hd__or3_2 _089_ (.A(_032_),
    .B(_036_),
    .C(_048_),
    .X(_049_));
 sky130_fd_sc_hd__o211a_2 _090_ (.A1(net31),
    .A2(_037_),
    .B1(_049_),
    .C1(net23),
    .X(_005_));
 sky130_fd_sc_hd__mux2_1 _091_ (.A0(\u_6e6f64655f326266333064306661616565.tail[6] ),
    .A1(net7),
    .S(_033_),
    .X(_050_));
 sky130_fd_sc_hd__or3_2 _092_ (.A(_032_),
    .B(_036_),
    .C(_050_),
    .X(_051_));
 sky130_fd_sc_hd__o211a_2 _093_ (.A1(net28),
    .A2(_037_),
    .B1(_051_),
    .C1(net24),
    .X(_006_));
 sky130_fd_sc_hd__mux2_1 _094_ (.A0(\u_6e6f64655f326266333064306661616565.tail[7] ),
    .A1(net8),
    .S(_033_),
    .X(_052_));
 sky130_fd_sc_hd__or3_2 _095_ (.A(_032_),
    .B(_036_),
    .C(_052_),
    .X(_053_));
 sky130_fd_sc_hd__o211a_2 _096_ (.A1(net29),
    .A2(_037_),
    .B1(_053_),
    .C1(net23),
    .X(_007_));
 sky130_fd_sc_hd__and2_2 _097_ (.A(net22),
    .B(_034_),
    .X(_018_));
 sky130_fd_sc_hd__nand2_2 _098_ (.A(net22),
    .B(_034_),
    .Y(_019_));
 sky130_fd_sc_hd__or2_2 _099_ (.A(net37),
    .B(_018_),
    .X(_020_));
 sky130_fd_sc_hd__o211a_2 _100_ (.A1(net1),
    .A2(_019_),
    .B1(_020_),
    .C1(net23),
    .X(_008_));
 sky130_fd_sc_hd__or2_2 _101_ (.A(net41),
    .B(_018_),
    .X(_021_));
 sky130_fd_sc_hd__o211a_2 _102_ (.A1(net2),
    .A2(_019_),
    .B1(_021_),
    .C1(net23),
    .X(_009_));
 sky130_fd_sc_hd__or2_2 _103_ (.A(net40),
    .B(_018_),
    .X(_022_));
 sky130_fd_sc_hd__o211a_2 _104_ (.A1(net3),
    .A2(_019_),
    .B1(_022_),
    .C1(net23),
    .X(_010_));
 sky130_fd_sc_hd__or2_2 _105_ (.A(net35),
    .B(_018_),
    .X(_023_));
 sky130_fd_sc_hd__o211a_2 _106_ (.A1(net4),
    .A2(_019_),
    .B1(_023_),
    .C1(net24),
    .X(_011_));
 sky130_fd_sc_hd__or2_2 _107_ (.A(net38),
    .B(_018_),
    .X(_024_));
 sky130_fd_sc_hd__o211a_2 _108_ (.A1(net5),
    .A2(_019_),
    .B1(_024_),
    .C1(net24),
    .X(_012_));
 sky130_fd_sc_hd__or2_2 _109_ (.A(net42),
    .B(_018_),
    .X(_025_));
 sky130_fd_sc_hd__o211a_2 _110_ (.A1(net6),
    .A2(_019_),
    .B1(_025_),
    .C1(net23),
    .X(_013_));
 sky130_fd_sc_hd__or2_2 _111_ (.A(net39),
    .B(_018_),
    .X(_026_));
 sky130_fd_sc_hd__o211a_2 _112_ (.A1(net7),
    .A2(_019_),
    .B1(_026_),
    .C1(net24),
    .X(_014_));
 sky130_fd_sc_hd__or2_2 _113_ (.A(net36),
    .B(_018_),
    .X(_027_));
 sky130_fd_sc_hd__o211a_2 _114_ (.A1(net8),
    .A2(_019_),
    .B1(_027_),
    .C1(net23),
    .X(_015_));
 sky130_fd_sc_hd__nor2_2 _115_ (.A(_029_),
    .B(_036_),
    .Y(_016_));
 sky130_fd_sc_hd__nor2_2 _116_ (.A(net12),
    .B(net10),
    .Y(_028_));
 sky130_fd_sc_hd__o221a_2 _117_ (.A1(net33),
    .A2(_034_),
    .B1(_028_),
    .B2(\u_6e6f64655f326266333064306661616565.count[0] ),
    .C1(net24),
    .X(_017_));
 sky130_fd_sc_hd__dfxtp_2 _118_ (.CLK(clknet_1_0__leaf_clk_pipe),
    .D(_000_),
    .Q(\u_6e6f64655f326266333064306661616565.head[0] ));
 sky130_fd_sc_hd__dfxtp_2 _119_ (.CLK(clknet_1_1__leaf_clk_pipe),
    .D(_001_),
    .Q(\u_6e6f64655f326266333064306661616565.head[1] ));
 sky130_fd_sc_hd__dfxtp_2 _120_ (.CLK(clknet_1_0__leaf_clk_pipe),
    .D(_002_),
    .Q(\u_6e6f64655f326266333064306661616565.head[2] ));
 sky130_fd_sc_hd__dfxtp_2 _121_ (.CLK(clknet_1_1__leaf_clk_pipe),
    .D(_003_),
    .Q(\u_6e6f64655f326266333064306661616565.head[3] ));
 sky130_fd_sc_hd__dfxtp_2 _122_ (.CLK(clknet_1_1__leaf_clk_pipe),
    .D(_004_),
    .Q(\u_6e6f64655f326266333064306661616565.head[4] ));
 sky130_fd_sc_hd__dfxtp_2 _123_ (.CLK(clknet_1_0__leaf_clk_pipe),
    .D(_005_),
    .Q(\u_6e6f64655f326266333064306661616565.head[5] ));
 sky130_fd_sc_hd__dfxtp_2 _124_ (.CLK(clknet_1_1__leaf_clk_pipe),
    .D(_006_),
    .Q(\u_6e6f64655f326266333064306661616565.head[6] ));
 sky130_fd_sc_hd__dfxtp_2 _125_ (.CLK(clknet_1_0__leaf_clk_pipe),
    .D(_007_),
    .Q(\u_6e6f64655f326266333064306661616565.head[7] ));
 sky130_fd_sc_hd__dfxtp_2 _126_ (.CLK(clknet_1_0__leaf_clk_pipe),
    .D(_008_),
    .Q(\u_6e6f64655f326266333064306661616565.tail[0] ));
 sky130_fd_sc_hd__dfxtp_2 _127_ (.CLK(clknet_1_0__leaf_clk_pipe),
    .D(_009_),
    .Q(\u_6e6f64655f326266333064306661616565.tail[1] ));
 sky130_fd_sc_hd__dfxtp_2 _128_ (.CLK(clknet_1_0__leaf_clk_pipe),
    .D(_010_),
    .Q(\u_6e6f64655f326266333064306661616565.tail[2] ));
 sky130_fd_sc_hd__dfxtp_2 _129_ (.CLK(clknet_1_1__leaf_clk_pipe),
    .D(_011_),
    .Q(\u_6e6f64655f326266333064306661616565.tail[3] ));
 sky130_fd_sc_hd__dfxtp_2 _130_ (.CLK(clknet_1_1__leaf_clk_pipe),
    .D(_012_),
    .Q(\u_6e6f64655f326266333064306661616565.tail[4] ));
 sky130_fd_sc_hd__dfxtp_2 _131_ (.CLK(clknet_1_0__leaf_clk_pipe),
    .D(_013_),
    .Q(\u_6e6f64655f326266333064306661616565.tail[5] ));
 sky130_fd_sc_hd__dfxtp_2 _132_ (.CLK(clknet_1_1__leaf_clk_pipe),
    .D(_014_),
    .Q(\u_6e6f64655f326266333064306661616565.tail[6] ));
 sky130_fd_sc_hd__dfxtp_2 _133_ (.CLK(clknet_1_0__leaf_clk_pipe),
    .D(_015_),
    .Q(\u_6e6f64655f326266333064306661616565.tail[7] ));
 sky130_fd_sc_hd__dfxtp_2 _134_ (.CLK(clknet_1_1__leaf_clk_pipe),
    .D(_016_),
    .Q(\u_6e6f64655f326266333064306661616565.count[0] ));
 sky130_fd_sc_hd__dfxtp_2 _135_ (.CLK(clknet_1_1__leaf_clk_pipe),
    .D(net34),
    .Q(\u_6e6f64655f326266333064306661616565.count[1] ));
 sky130_fd_sc_hd__clkbuf_16 clkbuf_0_clk_pipe (.A(clk_pipe),
    .X(clknet_0_clk_pipe));
 sky130_fd_sc_hd__clkbuf_16 clkbuf_1_0__f_clk_pipe (.A(clknet_0_clk_pipe),
    .X(clknet_1_0__leaf_clk_pipe));
 sky130_fd_sc_hd__clkbuf_16 clkbuf_1_1__f_clk_pipe (.A(clknet_0_clk_pipe),
    .X(clknet_1_1__leaf_clk_pipe));
 sky130_fd_sc_hd__clkdlybuf4s25_1 fanout22 (.A(net21),
    .X(net22));
 sky130_fd_sc_hd__clkdlybuf4s25_1 fanout23 (.A(net11),
    .X(net23));
 sky130_fd_sc_hd__clkdlybuf4s25_1 fanout24 (.A(net11),
    .X(net24));
 sky130_fd_sc_hd__dlygate4sd3_1 hold25 (.A(\u_6e6f64655f326266333064306661616565.head[3] ),
    .X(net25));
 sky130_fd_sc_hd__dlygate4sd3_1 hold26 (.A(\u_6e6f64655f326266333064306661616565.head[4] ),
    .X(net26));
 sky130_fd_sc_hd__dlygate4sd3_1 hold27 (.A(\u_6e6f64655f326266333064306661616565.head[1] ),
    .X(net27));
 sky130_fd_sc_hd__dlygate4sd3_1 hold28 (.A(\u_6e6f64655f326266333064306661616565.head[6] ),
    .X(net28));
 sky130_fd_sc_hd__dlygate4sd3_1 hold29 (.A(\u_6e6f64655f326266333064306661616565.head[7] ),
    .X(net29));
 sky130_fd_sc_hd__dlygate4sd3_1 hold30 (.A(\u_6e6f64655f326266333064306661616565.head[0] ),
    .X(net30));
 sky130_fd_sc_hd__dlygate4sd3_1 hold31 (.A(\u_6e6f64655f326266333064306661616565.head[5] ),
    .X(net31));
 sky130_fd_sc_hd__dlygate4sd3_1 hold32 (.A(\u_6e6f64655f326266333064306661616565.head[2] ),
    .X(net32));
 sky130_fd_sc_hd__dlygate4sd3_1 hold33 (.A(\u_6e6f64655f326266333064306661616565.count[1] ),
    .X(net33));
 sky130_fd_sc_hd__dlygate4sd3_1 hold34 (.A(_017_),
    .X(net34));
 sky130_fd_sc_hd__dlygate4sd3_1 hold35 (.A(\u_6e6f64655f326266333064306661616565.tail[3] ),
    .X(net35));
 sky130_fd_sc_hd__dlygate4sd3_1 hold36 (.A(\u_6e6f64655f326266333064306661616565.tail[7] ),
    .X(net36));
 sky130_fd_sc_hd__dlygate4sd3_1 hold37 (.A(\u_6e6f64655f326266333064306661616565.tail[0] ),
    .X(net37));
 sky130_fd_sc_hd__dlygate4sd3_1 hold38 (.A(\u_6e6f64655f326266333064306661616565.tail[4] ),
    .X(net38));
 sky130_fd_sc_hd__dlygate4sd3_1 hold39 (.A(\u_6e6f64655f326266333064306661616565.tail[6] ),
    .X(net39));
 sky130_fd_sc_hd__dlygate4sd3_1 hold40 (.A(\u_6e6f64655f326266333064306661616565.tail[2] ),
    .X(net40));
 sky130_fd_sc_hd__dlygate4sd3_1 hold41 (.A(\u_6e6f64655f326266333064306661616565.tail[1] ),
    .X(net41));
 sky130_fd_sc_hd__dlygate4sd3_1 hold42 (.A(\u_6e6f64655f326266333064306661616565.tail[5] ),
    .X(net42));
 sky130_fd_sc_hd__clkdlybuf4s25_1 input1 (.A(data_i[0]),
    .X(net1));
 sky130_fd_sc_hd__clkdlybuf4s25_1 input10 (.A(data_o_ready),
    .X(net10));
 sky130_fd_sc_hd__clkdlybuf4s25_1 input11 (.A(rst_pipe_n),
    .X(net11));
 sky130_fd_sc_hd__clkdlybuf4s25_1 input2 (.A(data_i[1]),
    .X(net2));
 sky130_fd_sc_hd__clkdlybuf4s25_1 input3 (.A(data_i[2]),
    .X(net3));
 sky130_fd_sc_hd__clkdlybuf4s25_1 input4 (.A(data_i[3]),
    .X(net4));
 sky130_fd_sc_hd__clkdlybuf4s25_1 input5 (.A(data_i[4]),
    .X(net5));
 sky130_fd_sc_hd__clkdlybuf4s25_1 input6 (.A(data_i[5]),
    .X(net6));
 sky130_fd_sc_hd__clkdlybuf4s25_1 input7 (.A(data_i[6]),
    .X(net7));
 sky130_fd_sc_hd__clkdlybuf4s25_1 input8 (.A(data_i[7]),
    .X(net8));
 sky130_fd_sc_hd__clkdlybuf4s25_1 input9 (.A(data_i_valid),
    .X(net9));
 sky130_fd_sc_hd__clkdlybuf4s25_1 output12 (.A(net12),
    .X(data_i_ready));
 sky130_fd_sc_hd__clkdlybuf4s25_1 output13 (.A(net13),
    .X(data_o[0]));
 sky130_fd_sc_hd__clkdlybuf4s25_1 output14 (.A(net14),
    .X(data_o[1]));
 sky130_fd_sc_hd__clkdlybuf4s25_1 output15 (.A(net15),
    .X(data_o[2]));
 sky130_fd_sc_hd__clkdlybuf4s25_1 output16 (.A(net16),
    .X(data_o[3]));
 sky130_fd_sc_hd__clkdlybuf4s25_1 output17 (.A(net17),
    .X(data_o[4]));
 sky130_fd_sc_hd__clkdlybuf4s25_1 output18 (.A(net18),
    .X(data_o[5]));
 sky130_fd_sc_hd__clkdlybuf4s25_1 output19 (.A(net19),
    .X(data_o[6]));
 sky130_fd_sc_hd__clkdlybuf4s25_1 output20 (.A(net20),
    .X(data_o[7]));
 sky130_fd_sc_hd__clkdlybuf4s25_1 output21 (.A(net21),
    .X(data_o_valid));
endmodule
