// chip_core r3 — mk_top.py 2026-10-28 07:35, col_blk = digital/col_blk/out/col_blk, arr = layout/top/strap/arr_w3s_128x64.cdl
// 구조 Verilog. 블록 = LEF macro (place/lef). PG 핀 (VDD VSS vdd vss VPWR VGND VPB VNB) 은 chip_core_pg.tcl 로 잇는다.
// 1'b0 = VSS 에 묶음 (col_blk lo, 배열 wl_106–127): connect_global_net VSS -type tie_lo

module chip_core (SCK, SDI, SLD, RST, SEL_EN, WP, CK, CK3, LAT, LQ1, LQ2, VRAILP, VRAILM, VWH, VWLO, VWL, VBUS_F,
    VBUS_N, IBIAS, VBNC, VBPC, IBIASP, VCM);
  input SCK;
  input SDI;
  input SLD;
  input RST;
  input SEL_EN;
  input WP;
  input CK;
  input CK3;
  input LAT;
  output LQ1;
  output LQ2;
  inout VRAILP;
  inout VRAILM;
  inout VWH;
  inout VWLO;
  inout VWL;
  inout VBUS_F;
  inout VBUS_N;
  inout IBIAS;
  inout VBNC;
  inout VBPC;
  inout IBIASP;
  inout VCM;
  wire row_f_0;
  wire row_f_1;
  wire row_f_2;
  wire row_f_3;
  wire row_f_4;
  wire row_f_5;
  wire row_f_6;
  wire row_f_7;
  wire row_f_8;
  wire row_f_9;
  wire row_f_10;
  wire row_f_11;
  wire row_f_12;
  wire row_f_13;
  wire row_f_14;
  wire row_f_15;
  wire row_f_16;
  wire row_f_17;
  wire row_f_18;
  wire row_f_19;
  wire row_f_20;
  wire row_f_21;
  wire row_f_22;
  wire row_f_23;
  wire row_f_24;
  wire row_f_25;
  wire row_f_26;
  wire row_f_27;
  wire row_f_28;
  wire row_f_29;
  wire row_f_30;
  wire row_f_31;
  wire row_f_32;
  wire row_f_33;
  wire row_f_34;
  wire row_f_35;
  wire row_f_36;
  wire row_f_37;
  wire row_f_38;
  wire row_f_39;
  wire row_f_40;
  wire row_f_41;
  wire row_f_42;
  wire row_f_43;
  wire row_f_44;
  wire row_f_45;
  wire row_f_46;
  wire row_f_47;
  wire row_f_48;
  wire row_f_49;
  wire row_f_50;
  wire row_f_51;
  wire row_f_52;
  wire row_f_53;
  wire row_f_54;
  wire row_f_55;
  wire row_f_56;
  wire row_f_57;
  wire row_f_58;
  wire row_f_59;
  wire row_f_60;
  wire row_f_61;
  wire row_f_62;
  wire row_f_63;
  wire row_f_64;
  wire row_f_65;
  wire row_f_66;
  wire row_f_67;
  wire row_f_68;
  wire row_f_69;
  wire row_f_70;
  wire row_f_71;
  wire row_f_72;
  wire row_f_73;
  wire row_f_74;
  wire row_f_75;
  wire row_f_76;
  wire row_f_77;
  wire row_f_78;
  wire row_f_79;
  wire row_f_80;
  wire row_f_81;
  wire row_f_82;
  wire row_f_83;
  wire row_f_84;
  wire row_f_85;
  wire row_f_86;
  wire row_f_87;
  wire row_f_88;
  wire row_f_89;
  wire row_f_90;
  wire row_f_91;
  wire row_f_92;
  wire row_f_93;
  wire row_f_94;
  wire row_f_95;
  wire row_f_96;
  wire row_f_97;
  wire row_f_98;
  wire row_f_99;
  wire row_f_100;
  wire row_f_101;
  wire row_f_102;
  wire row_f_103;
  wire row_f_104;
  wire row_f_105;
  wire wl_f_0;
  wire wl_f_1;
  wire wl_f_2;
  wire wl_f_3;
  wire wl_f_4;
  wire wl_f_5;
  wire wl_f_6;
  wire wl_f_7;
  wire wl_f_8;
  wire wl_f_9;
  wire wl_f_10;
  wire wl_f_11;
  wire wl_f_12;
  wire wl_f_13;
  wire wl_f_14;
  wire wl_f_15;
  wire wl_f_16;
  wire wl_f_17;
  wire wl_f_18;
  wire wl_f_19;
  wire wl_f_20;
  wire wl_f_21;
  wire wl_f_22;
  wire wl_f_23;
  wire wl_f_24;
  wire wl_f_25;
  wire wl_f_26;
  wire wl_f_27;
  wire wl_f_28;
  wire wl_f_29;
  wire wl_f_30;
  wire wl_f_31;
  wire wl_f_32;
  wire wl_f_33;
  wire wl_f_34;
  wire wl_f_35;
  wire wl_f_36;
  wire wl_f_37;
  wire wl_f_38;
  wire wl_f_39;
  wire wl_f_40;
  wire wl_f_41;
  wire wl_f_42;
  wire wl_f_43;
  wire wl_f_44;
  wire wl_f_45;
  wire wl_f_46;
  wire wl_f_47;
  wire wl_f_48;
  wire wl_f_49;
  wire wl_f_50;
  wire wl_f_51;
  wire wl_f_52;
  wire wl_f_53;
  wire wl_f_54;
  wire wl_f_55;
  wire wl_f_56;
  wire wl_f_57;
  wire wl_f_58;
  wire wl_f_59;
  wire wl_f_60;
  wire wl_f_61;
  wire wl_f_62;
  wire wl_f_63;
  wire wl_f_64;
  wire wl_f_65;
  wire wl_f_66;
  wire wl_f_67;
  wire wl_f_68;
  wire wl_f_69;
  wire wl_f_70;
  wire wl_f_71;
  wire wl_f_72;
  wire wl_f_73;
  wire wl_f_74;
  wire wl_f_75;
  wire wl_f_76;
  wire wl_f_77;
  wire wl_f_78;
  wire wl_f_79;
  wire wl_f_80;
  wire wl_f_81;
  wire wl_f_82;
  wire wl_f_83;
  wire wl_f_84;
  wire wl_f_85;
  wire wl_f_86;
  wire wl_f_87;
  wire wl_f_88;
  wire wl_f_89;
  wire wl_f_90;
  wire wl_f_91;
  wire wl_f_92;
  wire wl_f_93;
  wire wl_f_94;
  wire wl_f_95;
  wire wl_f_96;
  wire wl_f_97;
  wire wl_f_98;
  wire wl_f_99;
  wire wl_f_100;
  wire wl_f_101;
  wire wl_f_102;
  wire wl_f_103;
  wire wl_f_104;
  wire wl_f_105;
  wire col_f_0;
  wire col_f_1;
  wire col_f_2;
  wire col_f_3;
  wire col_f_4;
  wire col_f_5;
  wire col_f_6;
  wire col_f_7;
  wire col_f_8;
  wire col_f_9;
  wire col_f_10;
  wire col_f_11;
  wire col_f_12;
  wire col_f_13;
  wire col_f_14;
  wire col_f_15;
  wire col_f_16;
  wire col_f_17;
  wire col_f_18;
  wire col_f_19;
  wire col_f_20;
  wire col_f_21;
  wire col_f_22;
  wire col_f_23;
  wire col_f_24;
  wire col_f_25;
  wire col_f_26;
  wire col_f_27;
  wire col_f_28;
  wire col_f_29;
  wire col_f_30;
  wire col_f_31;
  wire col_f_32;
  wire col_f_33;
  wire col_f_34;
  wire col_f_35;
  wire col_f_36;
  wire col_f_37;
  wire col_f_38;
  wire col_f_39;
  wire col_f_40;
  wire col_f_41;
  wire col_f_42;
  wire col_f_43;
  wire col_f_44;
  wire col_f_45;
  wire col_f_46;
  wire col_f_47;
  wire col_f_48;
  wire col_f_49;
  wire col_f_50;
  wire col_f_51;
  wire col_f_52;
  wire col_f_53;
  wire col_f_54;
  wire col_f_55;
  wire col_f_56;
  wire col_f_57;
  wire col_f_58;
  wire col_f_59;
  wire col_f_60;
  wire col_f_61;
  wire col_f_62;
  wire col_f_63;
  wire row_n_0;
  wire row_n_1;
  wire row_n_2;
  wire row_n_3;
  wire row_n_4;
  wire row_n_5;
  wire row_n_6;
  wire row_n_7;
  wire row_n_8;
  wire row_n_9;
  wire row_n_10;
  wire row_n_11;
  wire row_n_12;
  wire row_n_13;
  wire row_n_14;
  wire row_n_15;
  wire row_n_16;
  wire row_n_17;
  wire row_n_18;
  wire row_n_19;
  wire row_n_20;
  wire row_n_21;
  wire row_n_22;
  wire row_n_23;
  wire row_n_24;
  wire row_n_25;
  wire row_n_26;
  wire row_n_27;
  wire row_n_28;
  wire row_n_29;
  wire row_n_30;
  wire row_n_31;
  wire row_n_32;
  wire row_n_33;
  wire row_n_34;
  wire row_n_35;
  wire row_n_36;
  wire row_n_37;
  wire row_n_38;
  wire row_n_39;
  wire row_n_40;
  wire row_n_41;
  wire row_n_42;
  wire row_n_43;
  wire row_n_44;
  wire row_n_45;
  wire row_n_46;
  wire row_n_47;
  wire row_n_48;
  wire row_n_49;
  wire row_n_50;
  wire row_n_51;
  wire row_n_52;
  wire row_n_53;
  wire row_n_54;
  wire row_n_55;
  wire row_n_56;
  wire row_n_57;
  wire row_n_58;
  wire row_n_59;
  wire row_n_60;
  wire row_n_61;
  wire row_n_62;
  wire row_n_63;
  wire row_n_64;
  wire row_n_65;
  wire row_n_66;
  wire row_n_67;
  wire row_n_68;
  wire row_n_69;
  wire row_n_70;
  wire row_n_71;
  wire row_n_72;
  wire row_n_73;
  wire row_n_74;
  wire row_n_75;
  wire row_n_76;
  wire row_n_77;
  wire row_n_78;
  wire row_n_79;
  wire row_n_80;
  wire row_n_81;
  wire row_n_82;
  wire row_n_83;
  wire row_n_84;
  wire row_n_85;
  wire row_n_86;
  wire row_n_87;
  wire row_n_88;
  wire row_n_89;
  wire row_n_90;
  wire row_n_91;
  wire row_n_92;
  wire row_n_93;
  wire row_n_94;
  wire row_n_95;
  wire row_n_96;
  wire row_n_97;
  wire row_n_98;
  wire row_n_99;
  wire row_n_100;
  wire row_n_101;
  wire row_n_102;
  wire row_n_103;
  wire row_n_104;
  wire row_n_105;
  wire wl_n_0;
  wire wl_n_1;
  wire wl_n_2;
  wire wl_n_3;
  wire wl_n_4;
  wire wl_n_5;
  wire wl_n_6;
  wire wl_n_7;
  wire wl_n_8;
  wire wl_n_9;
  wire wl_n_10;
  wire wl_n_11;
  wire wl_n_12;
  wire wl_n_13;
  wire wl_n_14;
  wire wl_n_15;
  wire wl_n_16;
  wire wl_n_17;
  wire wl_n_18;
  wire wl_n_19;
  wire wl_n_20;
  wire wl_n_21;
  wire wl_n_22;
  wire wl_n_23;
  wire wl_n_24;
  wire wl_n_25;
  wire wl_n_26;
  wire wl_n_27;
  wire wl_n_28;
  wire wl_n_29;
  wire wl_n_30;
  wire wl_n_31;
  wire wl_n_32;
  wire wl_n_33;
  wire wl_n_34;
  wire wl_n_35;
  wire wl_n_36;
  wire wl_n_37;
  wire wl_n_38;
  wire wl_n_39;
  wire wl_n_40;
  wire wl_n_41;
  wire wl_n_42;
  wire wl_n_43;
  wire wl_n_44;
  wire wl_n_45;
  wire wl_n_46;
  wire wl_n_47;
  wire wl_n_48;
  wire wl_n_49;
  wire wl_n_50;
  wire wl_n_51;
  wire wl_n_52;
  wire wl_n_53;
  wire wl_n_54;
  wire wl_n_55;
  wire wl_n_56;
  wire wl_n_57;
  wire wl_n_58;
  wire wl_n_59;
  wire wl_n_60;
  wire wl_n_61;
  wire wl_n_62;
  wire wl_n_63;
  wire wl_n_64;
  wire wl_n_65;
  wire wl_n_66;
  wire wl_n_67;
  wire wl_n_68;
  wire wl_n_69;
  wire wl_n_70;
  wire wl_n_71;
  wire wl_n_72;
  wire wl_n_73;
  wire wl_n_74;
  wire wl_n_75;
  wire wl_n_76;
  wire wl_n_77;
  wire wl_n_78;
  wire wl_n_79;
  wire wl_n_80;
  wire wl_n_81;
  wire wl_n_82;
  wire wl_n_83;
  wire wl_n_84;
  wire wl_n_85;
  wire wl_n_86;
  wire wl_n_87;
  wire wl_n_88;
  wire wl_n_89;
  wire wl_n_90;
  wire wl_n_91;
  wire wl_n_92;
  wire wl_n_93;
  wire wl_n_94;
  wire wl_n_95;
  wire wl_n_96;
  wire wl_n_97;
  wire wl_n_98;
  wire wl_n_99;
  wire wl_n_100;
  wire wl_n_101;
  wire wl_n_102;
  wire wl_n_103;
  wire wl_n_104;
  wire wl_n_105;
  wire col_n_0;
  wire col_n_1;
  wire col_n_2;
  wire col_n_3;
  wire col_n_4;
  wire col_n_5;
  wire col_n_6;
  wire col_n_7;
  wire col_n_8;
  wire col_n_9;
  wire col_n_10;
  wire col_n_11;
  wire col_n_12;
  wire col_n_13;
  wire col_n_14;
  wire col_n_15;
  wire col_n_16;
  wire col_n_17;
  wire col_n_18;
  wire col_n_19;
  wire col_n_20;
  wire col_n_21;
  wire col_n_22;
  wire col_n_23;
  wire col_n_24;
  wire col_n_25;
  wire col_n_26;
  wire col_n_27;
  wire col_n_28;
  wire col_n_29;
  wire col_n_30;
  wire col_n_31;
  wire col_n_32;
  wire col_n_33;
  wire col_n_34;
  wire col_n_35;
  wire col_n_36;
  wire col_n_37;
  wire col_n_38;
  wire col_n_39;
  wire col_n_40;
  wire col_n_41;
  wire col_n_42;
  wire col_n_43;
  wire col_n_44;
  wire col_n_45;
  wire col_n_46;
  wire col_n_47;
  wire col_n_48;
  wire col_n_49;
  wire col_n_50;
  wire col_n_51;
  wire col_n_52;
  wire col_n_53;
  wire col_n_54;
  wire col_n_55;
  wire col_n_56;
  wire col_n_57;
  wire col_n_58;
  wire col_n_59;
  wire col_n_60;
  wire col_n_61;
  wire col_n_62;
  wire col_n_63;
  wire ga_f_0;
  wire ga_f_1;
  wire ga_f_2;
  wire ga_f_3;
  wire ga_f_4;
  wire ga_f_5;
  wire ga_f_6;
  wire ga_f_7;
  wire ga_f_8;
  wire ga_f_9;
  wire ga_f_10;
  wire ga_f_11;
  wire ga_f_12;
  wire ga_f_13;
  wire ga_f_14;
  wire ga_f_15;
  wire ga_f_16;
  wire ga_f_17;
  wire ga_f_18;
  wire ga_f_19;
  wire ga_f_20;
  wire ga_f_21;
  wire ga_f_22;
  wire ga_f_23;
  wire ga_f_24;
  wire ga_f_25;
  wire ga_f_26;
  wire ga_f_27;
  wire ga_f_28;
  wire ga_f_29;
  wire ga_f_30;
  wire ga_f_31;
  wire ga_f_32;
  wire ga_f_33;
  wire ga_f_34;
  wire ga_f_35;
  wire ga_f_36;
  wire ga_f_37;
  wire ga_f_38;
  wire ga_f_39;
  wire ga_f_40;
  wire ga_f_41;
  wire ga_f_42;
  wire ga_f_43;
  wire ga_f_44;
  wire ga_f_45;
  wire ga_f_46;
  wire ga_f_47;
  wire ga_f_48;
  wire gb_f_0;
  wire gb_f_1;
  wire gb_f_2;
  wire gb_f_3;
  wire gb_f_4;
  wire gb_f_5;
  wire gb_f_6;
  wire gb_f_7;
  wire gb_f_8;
  wire gb_f_9;
  wire gb_f_10;
  wire gb_f_11;
  wire gb_f_12;
  wire gb_f_13;
  wire gb_f_14;
  wire gb_f_15;
  wire gb_f_16;
  wire gb_f_17;
  wire gb_f_18;
  wire gb_f_19;
  wire gb_f_20;
  wire gb_f_21;
  wire gb_f_22;
  wire gb_f_23;
  wire gb_f_24;
  wire gb_f_25;
  wire gb_f_26;
  wire gb_f_27;
  wire gb_f_28;
  wire gb_f_29;
  wire gb_f_30;
  wire gb_f_31;
  wire gb_f_32;
  wire gb_f_33;
  wire gb_f_34;
  wire gb_f_35;
  wire gb_f_36;
  wire gb_f_37;
  wire gb_f_38;
  wire gb_f_39;
  wire gb_f_40;
  wire gb_f_41;
  wire gb_f_42;
  wire gb_f_43;
  wire gb_f_44;
  wire gb_f_45;
  wire gb_f_46;
  wire gb_f_47;
  wire gb_f_48;
  wire READ_f;
  wire ga_n_0;
  wire ga_n_1;
  wire ga_n_2;
  wire ga_n_3;
  wire ga_n_4;
  wire ga_n_5;
  wire ga_n_6;
  wire ga_n_7;
  wire ga_n_8;
  wire ga_n_9;
  wire ga_n_10;
  wire ga_n_11;
  wire ga_n_12;
  wire ga_n_13;
  wire ga_n_14;
  wire ga_n_15;
  wire ga_n_16;
  wire ga_n_17;
  wire ga_n_18;
  wire ga_n_19;
  wire ga_n_20;
  wire ga_n_21;
  wire ga_n_22;
  wire ga_n_23;
  wire ga_n_24;
  wire ga_n_25;
  wire ga_n_26;
  wire ga_n_27;
  wire ga_n_28;
  wire ga_n_29;
  wire ga_n_30;
  wire ga_n_31;
  wire ga_n_32;
  wire ga_n_33;
  wire ga_n_34;
  wire ga_n_35;
  wire ga_n_36;
  wire ga_n_37;
  wire ga_n_38;
  wire ga_n_39;
  wire ga_n_40;
  wire ga_n_41;
  wire ga_n_42;
  wire ga_n_43;
  wire ga_n_44;
  wire ga_n_45;
  wire ga_n_46;
  wire ga_n_47;
  wire ga_n_48;
  wire gb_n_0;
  wire gb_n_1;
  wire gb_n_2;
  wire gb_n_3;
  wire gb_n_4;
  wire gb_n_5;
  wire gb_n_6;
  wire gb_n_7;
  wire gb_n_8;
  wire gb_n_9;
  wire gb_n_10;
  wire gb_n_11;
  wire gb_n_12;
  wire gb_n_13;
  wire gb_n_14;
  wire gb_n_15;
  wire gb_n_16;
  wire gb_n_17;
  wire gb_n_18;
  wire gb_n_19;
  wire gb_n_20;
  wire gb_n_21;
  wire gb_n_22;
  wire gb_n_23;
  wire gb_n_24;
  wire gb_n_25;
  wire gb_n_26;
  wire gb_n_27;
  wire gb_n_28;
  wire gb_n_29;
  wire gb_n_30;
  wire gb_n_31;
  wire gb_n_32;
  wire gb_n_33;
  wire gb_n_34;
  wire gb_n_35;
  wire gb_n_36;
  wire gb_n_37;
  wire gb_n_38;
  wire gb_n_39;
  wire gb_n_40;
  wire gb_n_41;
  wire gb_n_42;
  wire gb_n_43;
  wire gb_n_44;
  wire gb_n_45;
  wire gb_n_46;
  wire gb_n_47;
  wire gb_n_48;
  wire READ_n;
  wire row1_clk_f;
  wire row2_clk_f;
  wire rstb_f;
  wire PROG_f;
  wire VER_f;
  wire SENSE_f;
  wire READb_f;
  wire WRANY_f;
  wire vw_f;
  wire R1_f;
  wire R2_f;
  wire row1_clk_n;
  wire row2_clk_n;
  wire rstb_n;
  wire PROG_n;
  wire VER_n;
  wire SENSE_n;
  wire READb_n;
  wire WRANY_n;
  wire vw_n;
  wire R1_n;
  wire R2_n;
  wire C1_f;
  wire C2_f;
  wire col1_clk_f;
  wire col2_clk_f;
  wire C1_n;
  wire C2_n;
  wire col1_clk_n;
  wire col2_clk_n;
  wire data_clk_f;
  wire dload_f;
  wire data_clk_n;
  wire dload_n;
  wire sp_n_2;
  wire sp_n_1;
  wire sp_n_0;
  wire spb_n_2;
  wire spb_n_1;
  wire spb_n_0;
  wire sm_n_2;
  wire sm_n_1;
  wire sm_n_0;
  wire smb_n_2;
  wire smb_n_1;
  wire smb_n_0;
  wire pol_f;
  wire pol_n;
  wire rd_out_f;
  wire rd_out_b_f;
  wire rd_out_n;
  wire rd_out_b_n;
  wire latb_1;
  wire latb_2;
  wire pref;
  wire nref;

  arr_w3s_128x64 arr_f (
    .row_0(row_f_0),
    .row_1(row_f_1),
    .row_2(row_f_2),
    .row_3(row_f_3),
    .row_4(row_f_4),
    .row_5(row_f_5),
    .row_6(row_f_6),
    .row_7(row_f_7),
    .row_8(row_f_8),
    .row_9(row_f_9),
    .row_10(row_f_10),
    .row_11(row_f_11),
    .row_12(row_f_12),
    .row_13(row_f_13),
    .row_14(row_f_14),
    .row_15(row_f_15),
    .row_16(row_f_16),
    .row_17(row_f_17),
    .row_18(row_f_18),
    .row_19(row_f_19),
    .row_20(row_f_20),
    .row_21(row_f_21),
    .row_22(row_f_22),
    .row_23(row_f_23),
    .row_24(row_f_24),
    .row_25(row_f_25),
    .row_26(row_f_26),
    .row_27(row_f_27),
    .row_28(row_f_28),
    .row_29(row_f_29),
    .row_30(row_f_30),
    .row_31(row_f_31),
    .row_32(row_f_32),
    .row_33(row_f_33),
    .row_34(row_f_34),
    .row_35(row_f_35),
    .row_36(row_f_36),
    .row_37(row_f_37),
    .row_38(row_f_38),
    .row_39(row_f_39),
    .row_40(row_f_40),
    .row_41(row_f_41),
    .row_42(row_f_42),
    .row_43(row_f_43),
    .row_44(row_f_44),
    .row_45(row_f_45),
    .row_46(row_f_46),
    .row_47(row_f_47),
    .row_48(row_f_48),
    .row_49(row_f_49),
    .row_50(row_f_50),
    .row_51(row_f_51),
    .row_52(row_f_52),
    .row_53(row_f_53),
    .row_54(row_f_54),
    .row_55(row_f_55),
    .row_56(row_f_56),
    .row_57(row_f_57),
    .row_58(row_f_58),
    .row_59(row_f_59),
    .row_60(row_f_60),
    .row_61(row_f_61),
    .row_62(row_f_62),
    .row_63(row_f_63),
    .row_64(row_f_64),
    .row_65(row_f_65),
    .row_66(row_f_66),
    .row_67(row_f_67),
    .row_68(row_f_68),
    .row_69(row_f_69),
    .row_70(row_f_70),
    .row_71(row_f_71),
    .row_72(row_f_72),
    .row_73(row_f_73),
    .row_74(row_f_74),
    .row_75(row_f_75),
    .row_76(row_f_76),
    .row_77(row_f_77),
    .row_78(row_f_78),
    .row_79(row_f_79),
    .row_80(row_f_80),
    .row_81(row_f_81),
    .row_82(row_f_82),
    .row_83(row_f_83),
    .row_84(row_f_84),
    .row_85(row_f_85),
    .row_86(row_f_86),
    .row_87(row_f_87),
    .row_88(row_f_88),
    .row_89(row_f_89),
    .row_90(row_f_90),
    .row_91(row_f_91),
    .row_92(row_f_92),
    .row_93(row_f_93),
    .row_94(row_f_94),
    .row_95(row_f_95),
    .row_96(row_f_96),
    .row_97(row_f_97),
    .row_98(row_f_98),
    .row_99(row_f_99),
    .row_100(row_f_100),
    .row_101(row_f_101),
    .row_102(row_f_102),
    .row_103(row_f_103),
    .row_104(row_f_104),
    .row_105(row_f_105),
    .row_106(),
    .row_107(),
    .row_108(),
    .row_109(),
    .row_110(),
    .row_111(),
    .row_112(),
    .row_113(),
    .row_114(),
    .row_115(),
    .row_116(),
    .row_117(),
    .row_118(),
    .row_119(),
    .row_120(),
    .row_121(),
    .row_122(),
    .row_123(),
    .row_124(),
    .row_125(),
    .row_126(),
    .row_127(),
    .wl_0(wl_f_0),
    .wl_1(wl_f_1),
    .wl_2(wl_f_2),
    .wl_3(wl_f_3),
    .wl_4(wl_f_4),
    .wl_5(wl_f_5),
    .wl_6(wl_f_6),
    .wl_7(wl_f_7),
    .wl_8(wl_f_8),
    .wl_9(wl_f_9),
    .wl_10(wl_f_10),
    .wl_11(wl_f_11),
    .wl_12(wl_f_12),
    .wl_13(wl_f_13),
    .wl_14(wl_f_14),
    .wl_15(wl_f_15),
    .wl_16(wl_f_16),
    .wl_17(wl_f_17),
    .wl_18(wl_f_18),
    .wl_19(wl_f_19),
    .wl_20(wl_f_20),
    .wl_21(wl_f_21),
    .wl_22(wl_f_22),
    .wl_23(wl_f_23),
    .wl_24(wl_f_24),
    .wl_25(wl_f_25),
    .wl_26(wl_f_26),
    .wl_27(wl_f_27),
    .wl_28(wl_f_28),
    .wl_29(wl_f_29),
    .wl_30(wl_f_30),
    .wl_31(wl_f_31),
    .wl_32(wl_f_32),
    .wl_33(wl_f_33),
    .wl_34(wl_f_34),
    .wl_35(wl_f_35),
    .wl_36(wl_f_36),
    .wl_37(wl_f_37),
    .wl_38(wl_f_38),
    .wl_39(wl_f_39),
    .wl_40(wl_f_40),
    .wl_41(wl_f_41),
    .wl_42(wl_f_42),
    .wl_43(wl_f_43),
    .wl_44(wl_f_44),
    .wl_45(wl_f_45),
    .wl_46(wl_f_46),
    .wl_47(wl_f_47),
    .wl_48(wl_f_48),
    .wl_49(wl_f_49),
    .wl_50(wl_f_50),
    .wl_51(wl_f_51),
    .wl_52(wl_f_52),
    .wl_53(wl_f_53),
    .wl_54(wl_f_54),
    .wl_55(wl_f_55),
    .wl_56(wl_f_56),
    .wl_57(wl_f_57),
    .wl_58(wl_f_58),
    .wl_59(wl_f_59),
    .wl_60(wl_f_60),
    .wl_61(wl_f_61),
    .wl_62(wl_f_62),
    .wl_63(wl_f_63),
    .wl_64(wl_f_64),
    .wl_65(wl_f_65),
    .wl_66(wl_f_66),
    .wl_67(wl_f_67),
    .wl_68(wl_f_68),
    .wl_69(wl_f_69),
    .wl_70(wl_f_70),
    .wl_71(wl_f_71),
    .wl_72(wl_f_72),
    .wl_73(wl_f_73),
    .wl_74(wl_f_74),
    .wl_75(wl_f_75),
    .wl_76(wl_f_76),
    .wl_77(wl_f_77),
    .wl_78(wl_f_78),
    .wl_79(wl_f_79),
    .wl_80(wl_f_80),
    .wl_81(wl_f_81),
    .wl_82(wl_f_82),
    .wl_83(wl_f_83),
    .wl_84(wl_f_84),
    .wl_85(wl_f_85),
    .wl_86(wl_f_86),
    .wl_87(wl_f_87),
    .wl_88(wl_f_88),
    .wl_89(wl_f_89),
    .wl_90(wl_f_90),
    .wl_91(wl_f_91),
    .wl_92(wl_f_92),
    .wl_93(wl_f_93),
    .wl_94(wl_f_94),
    .wl_95(wl_f_95),
    .wl_96(wl_f_96),
    .wl_97(wl_f_97),
    .wl_98(wl_f_98),
    .wl_99(wl_f_99),
    .wl_100(wl_f_100),
    .wl_101(wl_f_101),
    .wl_102(wl_f_102),
    .wl_103(wl_f_103),
    .wl_104(wl_f_104),
    .wl_105(wl_f_105),
    .wl_106(1'b0),
    .wl_107(1'b0),
    .wl_108(1'b0),
    .wl_109(1'b0),
    .wl_110(1'b0),
    .wl_111(1'b0),
    .wl_112(1'b0),
    .wl_113(1'b0),
    .wl_114(1'b0),
    .wl_115(1'b0),
    .wl_116(1'b0),
    .wl_117(1'b0),
    .wl_118(1'b0),
    .wl_119(1'b0),
    .wl_120(1'b0),
    .wl_121(1'b0),
    .wl_122(1'b0),
    .wl_123(1'b0),
    .wl_124(1'b0),
    .wl_125(1'b0),
    .wl_126(1'b0),
    .wl_127(1'b0),
    .col_0(col_f_0),
    .col_1(col_f_1),
    .col_2(col_f_2),
    .col_3(col_f_3),
    .col_4(col_f_4),
    .col_5(col_f_5),
    .col_6(col_f_6),
    .col_7(col_f_7),
    .col_8(col_f_8),
    .col_9(col_f_9),
    .col_10(col_f_10),
    .col_11(col_f_11),
    .col_12(col_f_12),
    .col_13(col_f_13),
    .col_14(col_f_14),
    .col_15(col_f_15),
    .col_16(col_f_16),
    .col_17(col_f_17),
    .col_18(col_f_18),
    .col_19(col_f_19),
    .col_20(col_f_20),
    .col_21(col_f_21),
    .col_22(col_f_22),
    .col_23(col_f_23),
    .col_24(col_f_24),
    .col_25(col_f_25),
    .col_26(col_f_26),
    .col_27(col_f_27),
    .col_28(col_f_28),
    .col_29(col_f_29),
    .col_30(col_f_30),
    .col_31(col_f_31),
    .col_32(col_f_32),
    .col_33(col_f_33),
    .col_34(col_f_34),
    .col_35(col_f_35),
    .col_36(col_f_36),
    .col_37(col_f_37),
    .col_38(col_f_38),
    .col_39(col_f_39),
    .col_40(col_f_40),
    .col_41(col_f_41),
    .col_42(col_f_42),
    .col_43(col_f_43),
    .col_44(col_f_44),
    .col_45(col_f_45),
    .col_46(col_f_46),
    .col_47(col_f_47),
    .col_48(col_f_48),
    .col_49(col_f_49),
    .col_50(col_f_50),
    .col_51(col_f_51),
    .col_52(col_f_52),
    .col_53(col_f_53),
    .col_54(col_f_54),
    .col_55(col_f_55),
    .col_56(col_f_56),
    .col_57(col_f_57),
    .col_58(col_f_58),
    .col_59(col_f_59),
    .col_60(col_f_60),
    .col_61(col_f_61),
    .col_62(col_f_62),
    .col_63(col_f_63)
  );
  arr_w3s_128x64 arr_n (
    .row_0(row_n_0),
    .row_1(row_n_1),
    .row_2(row_n_2),
    .row_3(row_n_3),
    .row_4(row_n_4),
    .row_5(row_n_5),
    .row_6(row_n_6),
    .row_7(row_n_7),
    .row_8(row_n_8),
    .row_9(row_n_9),
    .row_10(row_n_10),
    .row_11(row_n_11),
    .row_12(row_n_12),
    .row_13(row_n_13),
    .row_14(row_n_14),
    .row_15(row_n_15),
    .row_16(row_n_16),
    .row_17(row_n_17),
    .row_18(row_n_18),
    .row_19(row_n_19),
    .row_20(row_n_20),
    .row_21(row_n_21),
    .row_22(row_n_22),
    .row_23(row_n_23),
    .row_24(row_n_24),
    .row_25(row_n_25),
    .row_26(row_n_26),
    .row_27(row_n_27),
    .row_28(row_n_28),
    .row_29(row_n_29),
    .row_30(row_n_30),
    .row_31(row_n_31),
    .row_32(row_n_32),
    .row_33(row_n_33),
    .row_34(row_n_34),
    .row_35(row_n_35),
    .row_36(row_n_36),
    .row_37(row_n_37),
    .row_38(row_n_38),
    .row_39(row_n_39),
    .row_40(row_n_40),
    .row_41(row_n_41),
    .row_42(row_n_42),
    .row_43(row_n_43),
    .row_44(row_n_44),
    .row_45(row_n_45),
    .row_46(row_n_46),
    .row_47(row_n_47),
    .row_48(row_n_48),
    .row_49(row_n_49),
    .row_50(row_n_50),
    .row_51(row_n_51),
    .row_52(row_n_52),
    .row_53(row_n_53),
    .row_54(row_n_54),
    .row_55(row_n_55),
    .row_56(row_n_56),
    .row_57(row_n_57),
    .row_58(row_n_58),
    .row_59(row_n_59),
    .row_60(row_n_60),
    .row_61(row_n_61),
    .row_62(row_n_62),
    .row_63(row_n_63),
    .row_64(row_n_64),
    .row_65(row_n_65),
    .row_66(row_n_66),
    .row_67(row_n_67),
    .row_68(row_n_68),
    .row_69(row_n_69),
    .row_70(row_n_70),
    .row_71(row_n_71),
    .row_72(row_n_72),
    .row_73(row_n_73),
    .row_74(row_n_74),
    .row_75(row_n_75),
    .row_76(row_n_76),
    .row_77(row_n_77),
    .row_78(row_n_78),
    .row_79(row_n_79),
    .row_80(row_n_80),
    .row_81(row_n_81),
    .row_82(row_n_82),
    .row_83(row_n_83),
    .row_84(row_n_84),
    .row_85(row_n_85),
    .row_86(row_n_86),
    .row_87(row_n_87),
    .row_88(row_n_88),
    .row_89(row_n_89),
    .row_90(row_n_90),
    .row_91(row_n_91),
    .row_92(row_n_92),
    .row_93(row_n_93),
    .row_94(row_n_94),
    .row_95(row_n_95),
    .row_96(row_n_96),
    .row_97(row_n_97),
    .row_98(row_n_98),
    .row_99(row_n_99),
    .row_100(row_n_100),
    .row_101(row_n_101),
    .row_102(row_n_102),
    .row_103(row_n_103),
    .row_104(row_n_104),
    .row_105(row_n_105),
    .row_106(),
    .row_107(),
    .row_108(),
    .row_109(),
    .row_110(),
    .row_111(),
    .row_112(),
    .row_113(),
    .row_114(),
    .row_115(),
    .row_116(),
    .row_117(),
    .row_118(),
    .row_119(),
    .row_120(),
    .row_121(),
    .row_122(),
    .row_123(),
    .row_124(),
    .row_125(),
    .row_126(),
    .row_127(),
    .wl_0(wl_n_0),
    .wl_1(wl_n_1),
    .wl_2(wl_n_2),
    .wl_3(wl_n_3),
    .wl_4(wl_n_4),
    .wl_5(wl_n_5),
    .wl_6(wl_n_6),
    .wl_7(wl_n_7),
    .wl_8(wl_n_8),
    .wl_9(wl_n_9),
    .wl_10(wl_n_10),
    .wl_11(wl_n_11),
    .wl_12(wl_n_12),
    .wl_13(wl_n_13),
    .wl_14(wl_n_14),
    .wl_15(wl_n_15),
    .wl_16(wl_n_16),
    .wl_17(wl_n_17),
    .wl_18(wl_n_18),
    .wl_19(wl_n_19),
    .wl_20(wl_n_20),
    .wl_21(wl_n_21),
    .wl_22(wl_n_22),
    .wl_23(wl_n_23),
    .wl_24(wl_n_24),
    .wl_25(wl_n_25),
    .wl_26(wl_n_26),
    .wl_27(wl_n_27),
    .wl_28(wl_n_28),
    .wl_29(wl_n_29),
    .wl_30(wl_n_30),
    .wl_31(wl_n_31),
    .wl_32(wl_n_32),
    .wl_33(wl_n_33),
    .wl_34(wl_n_34),
    .wl_35(wl_n_35),
    .wl_36(wl_n_36),
    .wl_37(wl_n_37),
    .wl_38(wl_n_38),
    .wl_39(wl_n_39),
    .wl_40(wl_n_40),
    .wl_41(wl_n_41),
    .wl_42(wl_n_42),
    .wl_43(wl_n_43),
    .wl_44(wl_n_44),
    .wl_45(wl_n_45),
    .wl_46(wl_n_46),
    .wl_47(wl_n_47),
    .wl_48(wl_n_48),
    .wl_49(wl_n_49),
    .wl_50(wl_n_50),
    .wl_51(wl_n_51),
    .wl_52(wl_n_52),
    .wl_53(wl_n_53),
    .wl_54(wl_n_54),
    .wl_55(wl_n_55),
    .wl_56(wl_n_56),
    .wl_57(wl_n_57),
    .wl_58(wl_n_58),
    .wl_59(wl_n_59),
    .wl_60(wl_n_60),
    .wl_61(wl_n_61),
    .wl_62(wl_n_62),
    .wl_63(wl_n_63),
    .wl_64(wl_n_64),
    .wl_65(wl_n_65),
    .wl_66(wl_n_66),
    .wl_67(wl_n_67),
    .wl_68(wl_n_68),
    .wl_69(wl_n_69),
    .wl_70(wl_n_70),
    .wl_71(wl_n_71),
    .wl_72(wl_n_72),
    .wl_73(wl_n_73),
    .wl_74(wl_n_74),
    .wl_75(wl_n_75),
    .wl_76(wl_n_76),
    .wl_77(wl_n_77),
    .wl_78(wl_n_78),
    .wl_79(wl_n_79),
    .wl_80(wl_n_80),
    .wl_81(wl_n_81),
    .wl_82(wl_n_82),
    .wl_83(wl_n_83),
    .wl_84(wl_n_84),
    .wl_85(wl_n_85),
    .wl_86(wl_n_86),
    .wl_87(wl_n_87),
    .wl_88(wl_n_88),
    .wl_89(wl_n_89),
    .wl_90(wl_n_90),
    .wl_91(wl_n_91),
    .wl_92(wl_n_92),
    .wl_93(wl_n_93),
    .wl_94(wl_n_94),
    .wl_95(wl_n_95),
    .wl_96(wl_n_96),
    .wl_97(wl_n_97),
    .wl_98(wl_n_98),
    .wl_99(wl_n_99),
    .wl_100(wl_n_100),
    .wl_101(wl_n_101),
    .wl_102(wl_n_102),
    .wl_103(wl_n_103),
    .wl_104(wl_n_104),
    .wl_105(wl_n_105),
    .wl_106(1'b0),
    .wl_107(1'b0),
    .wl_108(1'b0),
    .wl_109(1'b0),
    .wl_110(1'b0),
    .wl_111(1'b0),
    .wl_112(1'b0),
    .wl_113(1'b0),
    .wl_114(1'b0),
    .wl_115(1'b0),
    .wl_116(1'b0),
    .wl_117(1'b0),
    .wl_118(1'b0),
    .wl_119(1'b0),
    .wl_120(1'b0),
    .wl_121(1'b0),
    .wl_122(1'b0),
    .wl_123(1'b0),
    .wl_124(1'b0),
    .wl_125(1'b0),
    .wl_126(1'b0),
    .wl_127(1'b0),
    .col_0(col_n_0),
    .col_1(col_n_1),
    .col_2(col_n_2),
    .col_3(col_n_3),
    .col_4(col_n_4),
    .col_5(col_n_5),
    .col_6(col_n_6),
    .col_7(col_n_7),
    .col_8(col_n_8),
    .col_9(col_n_9),
    .col_10(col_n_10),
    .col_11(col_n_11),
    .col_12(col_n_12),
    .col_13(col_n_13),
    .col_14(col_n_14),
    .col_15(col_n_15),
    .col_16(col_n_16),
    .col_17(col_n_17),
    .col_18(col_n_18),
    .col_19(col_n_19),
    .col_20(col_n_20),
    .col_21(col_n_21),
    .col_22(col_n_22),
    .col_23(col_n_23),
    .col_24(col_n_24),
    .col_25(col_n_25),
    .col_26(col_n_26),
    .col_27(col_n_27),
    .col_28(col_n_28),
    .col_29(col_n_29),
    .col_30(col_n_30),
    .col_31(col_n_31),
    .col_32(col_n_32),
    .col_33(col_n_33),
    .col_34(col_n_34),
    .col_35(col_n_35),
    .col_36(col_n_36),
    .col_37(col_n_37),
    .col_38(col_n_38),
    .col_39(col_n_39),
    .col_40(col_n_40),
    .col_41(col_n_41),
    .col_42(col_n_42),
    .col_43(col_n_43),
    .col_44(col_n_44),
    .col_45(col_n_45),
    .col_46(col_n_46),
    .col_47(col_n_47),
    .col_48(col_n_48),
    .col_49(col_n_49),
    .col_50(col_n_50),
    .col_51(col_n_51),
    .col_52(col_n_52),
    .col_53(col_n_53),
    .col_54(col_n_54),
    .col_55(col_n_55),
    .col_56(col_n_56),
    .col_57(col_n_57),
    .col_58(col_n_58),
    .col_59(col_n_59),
    .col_60(col_n_60),
    .col_61(col_n_61),
    .col_62(col_n_62),
    .col_63(col_n_63)
  );
  input_drive idrv_f (
    .row_0(row_f_0),
    .row_1(row_f_1),
    .row_2(row_f_2),
    .row_3(row_f_3),
    .row_4(row_f_4),
    .row_5(row_f_5),
    .row_6(row_f_6),
    .row_7(row_f_7),
    .row_8(row_f_8),
    .row_9(row_f_9),
    .row_10(row_f_10),
    .row_11(row_f_11),
    .row_12(row_f_12),
    .row_13(row_f_13),
    .row_14(row_f_14),
    .row_15(row_f_15),
    .row_16(row_f_16),
    .row_17(row_f_17),
    .row_18(row_f_18),
    .row_19(row_f_19),
    .row_20(row_f_20),
    .row_21(row_f_21),
    .row_22(row_f_22),
    .row_23(row_f_23),
    .row_24(row_f_24),
    .row_25(row_f_25),
    .row_26(row_f_26),
    .row_27(row_f_27),
    .row_28(row_f_28),
    .row_29(row_f_29),
    .row_30(row_f_30),
    .row_31(row_f_31),
    .row_32(row_f_32),
    .row_33(row_f_33),
    .row_34(row_f_34),
    .row_35(row_f_35),
    .row_36(row_f_36),
    .row_37(row_f_37),
    .row_38(row_f_38),
    .row_39(row_f_39),
    .row_40(row_f_40),
    .row_41(row_f_41),
    .row_42(row_f_42),
    .row_43(row_f_43),
    .row_44(row_f_44),
    .row_45(row_f_45),
    .row_46(row_f_46),
    .row_47(row_f_47),
    .row_48(row_f_48),
    .row_49(row_f_49),
    .row_50(row_f_50),
    .row_51(row_f_51),
    .row_52(row_f_52),
    .row_53(row_f_53),
    .row_54(row_f_54),
    .row_55(row_f_55),
    .row_56(row_f_56),
    .row_57(row_f_57),
    .row_58(row_f_58),
    .row_59(row_f_59),
    .row_60(row_f_60),
    .row_61(row_f_61),
    .row_62(row_f_62),
    .row_63(row_f_63),
    .row_64(row_f_64),
    .row_65(row_f_65),
    .row_66(row_f_66),
    .row_67(row_f_67),
    .row_68(row_f_68),
    .row_69(row_f_69),
    .row_70(row_f_70),
    .row_71(row_f_71),
    .row_72(row_f_72),
    .row_73(row_f_73),
    .row_74(row_f_74),
    .row_75(row_f_75),
    .row_76(row_f_76),
    .row_77(row_f_77),
    .row_78(row_f_78),
    .row_79(row_f_79),
    .row_80(row_f_80),
    .row_81(row_f_81),
    .row_82(row_f_82),
    .row_83(row_f_83),
    .row_84(row_f_84),
    .row_85(row_f_85),
    .row_86(row_f_86),
    .row_87(row_f_87),
    .row_88(row_f_88),
    .row_89(row_f_89),
    .row_90(row_f_90),
    .row_91(row_f_91),
    .row_92(row_f_92),
    .row_93(row_f_93),
    .row_94(row_f_94),
    .row_95(row_f_95),
    .row_96(row_f_96),
    .row_97(row_f_97),
    .row_98(row_f_98),
    .row_99(row_f_99),
    .ga0(ga_f_0),
    .ga1(ga_f_1),
    .ga2(ga_f_2),
    .ga3(ga_f_3),
    .ga4(ga_f_4),
    .ga5(ga_f_5),
    .ga6(ga_f_6),
    .ga7(ga_f_7),
    .ga8(ga_f_8),
    .ga9(ga_f_9),
    .ga10(ga_f_10),
    .ga11(ga_f_11),
    .ga12(ga_f_12),
    .ga13(ga_f_13),
    .ga14(ga_f_14),
    .ga15(ga_f_15),
    .ga16(ga_f_16),
    .ga17(ga_f_17),
    .ga18(ga_f_18),
    .ga19(ga_f_19),
    .ga20(ga_f_20),
    .ga21(ga_f_21),
    .ga22(ga_f_22),
    .ga23(ga_f_23),
    .ga24(ga_f_24),
    .ga25(ga_f_25),
    .ga26(ga_f_26),
    .ga27(ga_f_27),
    .ga28(ga_f_28),
    .ga29(ga_f_29),
    .ga30(ga_f_30),
    .ga31(ga_f_31),
    .ga32(ga_f_32),
    .ga33(ga_f_33),
    .ga34(ga_f_34),
    .ga35(ga_f_35),
    .ga36(ga_f_36),
    .ga37(ga_f_37),
    .ga38(ga_f_38),
    .ga39(ga_f_39),
    .ga40(ga_f_40),
    .ga41(ga_f_41),
    .ga42(ga_f_42),
    .ga43(ga_f_43),
    .ga44(ga_f_44),
    .ga45(ga_f_45),
    .ga46(ga_f_46),
    .ga47(ga_f_47),
    .ga48(ga_f_48),
    .gb0(gb_f_0),
    .gb1(gb_f_1),
    .gb2(gb_f_2),
    .gb3(gb_f_3),
    .gb4(gb_f_4),
    .gb5(gb_f_5),
    .gb6(gb_f_6),
    .gb7(gb_f_7),
    .gb8(gb_f_8),
    .gb9(gb_f_9),
    .gb10(gb_f_10),
    .gb11(gb_f_11),
    .gb12(gb_f_12),
    .gb13(gb_f_13),
    .gb14(gb_f_14),
    .gb15(gb_f_15),
    .gb16(gb_f_16),
    .gb17(gb_f_17),
    .gb18(gb_f_18),
    .gb19(gb_f_19),
    .gb20(gb_f_20),
    .gb21(gb_f_21),
    .gb22(gb_f_22),
    .gb23(gb_f_23),
    .gb24(gb_f_24),
    .gb25(gb_f_25),
    .gb26(gb_f_26),
    .gb27(gb_f_27),
    .gb28(gb_f_28),
    .gb29(gb_f_29),
    .gb30(gb_f_30),
    .gb31(gb_f_31),
    .gb32(gb_f_32),
    .gb33(gb_f_33),
    .gb34(gb_f_34),
    .gb35(gb_f_35),
    .gb36(gb_f_36),
    .gb37(gb_f_37),
    .gb38(gb_f_38),
    .gb39(gb_f_39),
    .gb40(gb_f_40),
    .gb41(gb_f_41),
    .gb42(gb_f_42),
    .gb43(gb_f_43),
    .gb44(gb_f_44),
    .gb45(gb_f_45),
    .gb46(gb_f_46),
    .gb47(gb_f_47),
    .gb48(gb_f_48),
    .READ(READ_f),
    .vrailp(VRAILP),
    .vrailm(VRAILM)
  );
  input_drive idrv_n (
    .row_0(row_n_0),
    .row_1(row_n_1),
    .row_2(row_n_2),
    .row_3(row_n_3),
    .row_4(row_n_4),
    .row_5(row_n_5),
    .row_6(row_n_6),
    .row_7(row_n_7),
    .row_8(row_n_8),
    .row_9(row_n_9),
    .row_10(row_n_10),
    .row_11(row_n_11),
    .row_12(row_n_12),
    .row_13(row_n_13),
    .row_14(row_n_14),
    .row_15(row_n_15),
    .row_16(row_n_16),
    .row_17(row_n_17),
    .row_18(row_n_18),
    .row_19(row_n_19),
    .row_20(row_n_20),
    .row_21(row_n_21),
    .row_22(row_n_22),
    .row_23(row_n_23),
    .row_24(row_n_24),
    .row_25(row_n_25),
    .row_26(row_n_26),
    .row_27(row_n_27),
    .row_28(row_n_28),
    .row_29(row_n_29),
    .row_30(row_n_30),
    .row_31(row_n_31),
    .row_32(row_n_32),
    .row_33(row_n_33),
    .row_34(row_n_34),
    .row_35(row_n_35),
    .row_36(row_n_36),
    .row_37(row_n_37),
    .row_38(row_n_38),
    .row_39(row_n_39),
    .row_40(row_n_40),
    .row_41(row_n_41),
    .row_42(row_n_42),
    .row_43(row_n_43),
    .row_44(row_n_44),
    .row_45(row_n_45),
    .row_46(row_n_46),
    .row_47(row_n_47),
    .row_48(row_n_48),
    .row_49(row_n_49),
    .row_50(row_n_50),
    .row_51(row_n_51),
    .row_52(row_n_52),
    .row_53(row_n_53),
    .row_54(row_n_54),
    .row_55(row_n_55),
    .row_56(row_n_56),
    .row_57(row_n_57),
    .row_58(row_n_58),
    .row_59(row_n_59),
    .row_60(row_n_60),
    .row_61(row_n_61),
    .row_62(row_n_62),
    .row_63(row_n_63),
    .row_64(row_n_64),
    .row_65(row_n_65),
    .row_66(row_n_66),
    .row_67(row_n_67),
    .row_68(row_n_68),
    .row_69(row_n_69),
    .row_70(row_n_70),
    .row_71(row_n_71),
    .row_72(row_n_72),
    .row_73(row_n_73),
    .row_74(row_n_74),
    .row_75(row_n_75),
    .row_76(row_n_76),
    .row_77(row_n_77),
    .row_78(row_n_78),
    .row_79(row_n_79),
    .row_80(row_n_80),
    .row_81(row_n_81),
    .row_82(row_n_82),
    .row_83(row_n_83),
    .row_84(row_n_84),
    .row_85(row_n_85),
    .row_86(row_n_86),
    .row_87(row_n_87),
    .row_88(row_n_88),
    .row_89(row_n_89),
    .row_90(row_n_90),
    .row_91(row_n_91),
    .row_92(row_n_92),
    .row_93(row_n_93),
    .row_94(row_n_94),
    .row_95(row_n_95),
    .row_96(row_n_96),
    .row_97(row_n_97),
    .row_98(row_n_98),
    .row_99(row_n_99),
    .ga0(ga_n_0),
    .ga1(ga_n_1),
    .ga2(ga_n_2),
    .ga3(ga_n_3),
    .ga4(ga_n_4),
    .ga5(ga_n_5),
    .ga6(ga_n_6),
    .ga7(ga_n_7),
    .ga8(ga_n_8),
    .ga9(ga_n_9),
    .ga10(ga_n_10),
    .ga11(ga_n_11),
    .ga12(ga_n_12),
    .ga13(ga_n_13),
    .ga14(ga_n_14),
    .ga15(ga_n_15),
    .ga16(ga_n_16),
    .ga17(ga_n_17),
    .ga18(ga_n_18),
    .ga19(ga_n_19),
    .ga20(ga_n_20),
    .ga21(ga_n_21),
    .ga22(ga_n_22),
    .ga23(ga_n_23),
    .ga24(ga_n_24),
    .ga25(ga_n_25),
    .ga26(ga_n_26),
    .ga27(ga_n_27),
    .ga28(ga_n_28),
    .ga29(ga_n_29),
    .ga30(ga_n_30),
    .ga31(ga_n_31),
    .ga32(ga_n_32),
    .ga33(ga_n_33),
    .ga34(ga_n_34),
    .ga35(ga_n_35),
    .ga36(ga_n_36),
    .ga37(ga_n_37),
    .ga38(ga_n_38),
    .ga39(ga_n_39),
    .ga40(ga_n_40),
    .ga41(ga_n_41),
    .ga42(ga_n_42),
    .ga43(ga_n_43),
    .ga44(ga_n_44),
    .ga45(ga_n_45),
    .ga46(ga_n_46),
    .ga47(ga_n_47),
    .ga48(ga_n_48),
    .gb0(gb_n_0),
    .gb1(gb_n_1),
    .gb2(gb_n_2),
    .gb3(gb_n_3),
    .gb4(gb_n_4),
    .gb5(gb_n_5),
    .gb6(gb_n_6),
    .gb7(gb_n_7),
    .gb8(gb_n_8),
    .gb9(gb_n_9),
    .gb10(gb_n_10),
    .gb11(gb_n_11),
    .gb12(gb_n_12),
    .gb13(gb_n_13),
    .gb14(gb_n_14),
    .gb15(gb_n_15),
    .gb16(gb_n_16),
    .gb17(gb_n_17),
    .gb18(gb_n_18),
    .gb19(gb_n_19),
    .gb20(gb_n_20),
    .gb21(gb_n_21),
    .gb22(gb_n_22),
    .gb23(gb_n_23),
    .gb24(gb_n_24),
    .gb25(gb_n_25),
    .gb26(gb_n_26),
    .gb27(gb_n_27),
    .gb28(gb_n_28),
    .gb29(gb_n_29),
    .gb30(gb_n_30),
    .gb31(gb_n_31),
    .gb32(gb_n_32),
    .gb33(gb_n_33),
    .gb34(gb_n_34),
    .gb35(gb_n_35),
    .gb36(gb_n_36),
    .gb37(gb_n_37),
    .gb38(gb_n_38),
    .gb39(gb_n_39),
    .gb40(gb_n_40),
    .gb41(gb_n_41),
    .gb42(gb_n_42),
    .gb43(gb_n_43),
    .gb44(gb_n_44),
    .gb45(gb_n_45),
    .gb46(gb_n_46),
    .gb47(gb_n_47),
    .gb48(gb_n_48),
    .READ(READ_n),
    .vrailp(VRAILP),
    .vrailm(VRAILM)
  );
  row_blk rowb_f (
    .sdi(SDI),
    .row1_clk(row1_clk_f),
    .row2_clk(row2_clk_f),
    .rstb(rstb_f),
    .sel_en(SEL_EN),
    .PROG(PROG_f),
    .VER(VER_f),
    .SENSE(SENSE_f),
    .READb(READb_f),
    .WRANY(WRANY_f),
    .vw(vw_f),
    .vwl(VWL),
    .vzero(VCM),
    .R1(R1_f),
    .R2(R2_f),
    .row({row_f_105, row_f_104, row_f_103, row_f_102, row_f_101, row_f_100, row_f_99, row_f_98, row_f_97, row_f_96, row_f_95, row_f_94, row_f_93, row_f_92, row_f_91, row_f_90, row_f_89, row_f_88, row_f_87, row_f_86, row_f_85, row_f_84, row_f_83, row_f_82, row_f_81, row_f_80, row_f_79, row_f_78, row_f_77, row_f_76, row_f_75, row_f_74, row_f_73, row_f_72, row_f_71, row_f_70, row_f_69, row_f_68, row_f_67, row_f_66, row_f_65, row_f_64, row_f_63, row_f_62, row_f_61, row_f_60, row_f_59, row_f_58, row_f_57, row_f_56, row_f_55, row_f_54, row_f_53, row_f_52, row_f_51, row_f_50, row_f_49, row_f_48, row_f_47, row_f_46, row_f_45, row_f_44, row_f_43, row_f_42, row_f_41, row_f_40, row_f_39, row_f_38, row_f_37, row_f_36, row_f_35, row_f_34, row_f_33, row_f_32, row_f_31, row_f_30, row_f_29, row_f_28, row_f_27, row_f_26, row_f_25, row_f_24, row_f_23, row_f_22, row_f_21, row_f_20, row_f_19, row_f_18, row_f_17, row_f_16, row_f_15, row_f_14, row_f_13, row_f_12, row_f_11, row_f_10, row_f_9, row_f_8, row_f_7, row_f_6, row_f_5, row_f_4, row_f_3, row_f_2, row_f_1, row_f_0}),
    .wl({wl_f_105, wl_f_104, wl_f_103, wl_f_102, wl_f_101, wl_f_100, wl_f_99, wl_f_98, wl_f_97, wl_f_96, wl_f_95, wl_f_94, wl_f_93, wl_f_92, wl_f_91, wl_f_90, wl_f_89, wl_f_88, wl_f_87, wl_f_86, wl_f_85, wl_f_84, wl_f_83, wl_f_82, wl_f_81, wl_f_80, wl_f_79, wl_f_78, wl_f_77, wl_f_76, wl_f_75, wl_f_74, wl_f_73, wl_f_72, wl_f_71, wl_f_70, wl_f_69, wl_f_68, wl_f_67, wl_f_66, wl_f_65, wl_f_64, wl_f_63, wl_f_62, wl_f_61, wl_f_60, wl_f_59, wl_f_58, wl_f_57, wl_f_56, wl_f_55, wl_f_54, wl_f_53, wl_f_52, wl_f_51, wl_f_50, wl_f_49, wl_f_48, wl_f_47, wl_f_46, wl_f_45, wl_f_44, wl_f_43, wl_f_42, wl_f_41, wl_f_40, wl_f_39, wl_f_38, wl_f_37, wl_f_36, wl_f_35, wl_f_34, wl_f_33, wl_f_32, wl_f_31, wl_f_30, wl_f_29, wl_f_28, wl_f_27, wl_f_26, wl_f_25, wl_f_24, wl_f_23, wl_f_22, wl_f_21, wl_f_20, wl_f_19, wl_f_18, wl_f_17, wl_f_16, wl_f_15, wl_f_14, wl_f_13, wl_f_12, wl_f_11, wl_f_10, wl_f_9, wl_f_8, wl_f_7, wl_f_6, wl_f_5, wl_f_4, wl_f_3, wl_f_2, wl_f_1, wl_f_0})
  );
  row_blk rowb_n (
    .sdi(SDI),
    .row1_clk(row1_clk_n),
    .row2_clk(row2_clk_n),
    .rstb(rstb_n),
    .sel_en(SEL_EN),
    .PROG(PROG_n),
    .VER(VER_n),
    .SENSE(SENSE_n),
    .READb(READb_n),
    .WRANY(WRANY_n),
    .vw(vw_n),
    .vwl(VWL),
    .vzero(VCM),
    .R1(R1_n),
    .R2(R2_n),
    .row({row_n_105, row_n_104, row_n_103, row_n_102, row_n_101, row_n_100, row_n_99, row_n_98, row_n_97, row_n_96, row_n_95, row_n_94, row_n_93, row_n_92, row_n_91, row_n_90, row_n_89, row_n_88, row_n_87, row_n_86, row_n_85, row_n_84, row_n_83, row_n_82, row_n_81, row_n_80, row_n_79, row_n_78, row_n_77, row_n_76, row_n_75, row_n_74, row_n_73, row_n_72, row_n_71, row_n_70, row_n_69, row_n_68, row_n_67, row_n_66, row_n_65, row_n_64, row_n_63, row_n_62, row_n_61, row_n_60, row_n_59, row_n_58, row_n_57, row_n_56, row_n_55, row_n_54, row_n_53, row_n_52, row_n_51, row_n_50, row_n_49, row_n_48, row_n_47, row_n_46, row_n_45, row_n_44, row_n_43, row_n_42, row_n_41, row_n_40, row_n_39, row_n_38, row_n_37, row_n_36, row_n_35, row_n_34, row_n_33, row_n_32, row_n_31, row_n_30, row_n_29, row_n_28, row_n_27, row_n_26, row_n_25, row_n_24, row_n_23, row_n_22, row_n_21, row_n_20, row_n_19, row_n_18, row_n_17, row_n_16, row_n_15, row_n_14, row_n_13, row_n_12, row_n_11, row_n_10, row_n_9, row_n_8, row_n_7, row_n_6, row_n_5, row_n_4, row_n_3, row_n_2, row_n_1, row_n_0}),
    .wl({wl_n_105, wl_n_104, wl_n_103, wl_n_102, wl_n_101, wl_n_100, wl_n_99, wl_n_98, wl_n_97, wl_n_96, wl_n_95, wl_n_94, wl_n_93, wl_n_92, wl_n_91, wl_n_90, wl_n_89, wl_n_88, wl_n_87, wl_n_86, wl_n_85, wl_n_84, wl_n_83, wl_n_82, wl_n_81, wl_n_80, wl_n_79, wl_n_78, wl_n_77, wl_n_76, wl_n_75, wl_n_74, wl_n_73, wl_n_72, wl_n_71, wl_n_70, wl_n_69, wl_n_68, wl_n_67, wl_n_66, wl_n_65, wl_n_64, wl_n_63, wl_n_62, wl_n_61, wl_n_60, wl_n_59, wl_n_58, wl_n_57, wl_n_56, wl_n_55, wl_n_54, wl_n_53, wl_n_52, wl_n_51, wl_n_50, wl_n_49, wl_n_48, wl_n_47, wl_n_46, wl_n_45, wl_n_44, wl_n_43, wl_n_42, wl_n_41, wl_n_40, wl_n_39, wl_n_38, wl_n_37, wl_n_36, wl_n_35, wl_n_34, wl_n_33, wl_n_32, wl_n_31, wl_n_30, wl_n_29, wl_n_28, wl_n_27, wl_n_26, wl_n_25, wl_n_24, wl_n_23, wl_n_22, wl_n_21, wl_n_20, wl_n_19, wl_n_18, wl_n_17, wl_n_16, wl_n_15, wl_n_14, wl_n_13, wl_n_12, wl_n_11, wl_n_10, wl_n_9, wl_n_8, wl_n_7, wl_n_6, wl_n_5, wl_n_4, wl_n_3, wl_n_2, wl_n_1, wl_n_0})
  );
  col_blk colb_f (
    .col({col_f_63, col_f_62, col_f_61, col_f_60, col_f_59, col_f_58, col_f_57, col_f_56, col_f_55, col_f_54, col_f_53, col_f_52, col_f_51, col_f_50, col_f_49, col_f_48, col_f_47, col_f_46, col_f_45, col_f_44, col_f_43, col_f_42, col_f_41, col_f_40, col_f_39, col_f_38, col_f_37, col_f_36, col_f_35, col_f_34, col_f_33, col_f_32, col_f_31, col_f_30, col_f_29, col_f_28, col_f_27, col_f_26, col_f_25, col_f_24, col_f_23, col_f_22, col_f_21, col_f_20, col_f_19, col_f_18, col_f_17, col_f_16, col_f_15, col_f_14, col_f_13, col_f_12, col_f_11, col_f_10, col_f_9, col_f_8, col_f_7, col_f_6, col_f_5, col_f_4, col_f_3, col_f_2, col_f_1, col_f_0}),
    .vw(vw_f),
    .vbus(VBUS_F),
    .C1(C1_f),
    .C2(C2_f),
    .vzero(VCM),
    .vrailp(VRAILP),
    .vrailm(VRAILM),
    .sdi(SDI),
    .rstb(rstb_f),
    .col1_clk(col1_clk_f),
    .col2_clk(col2_clk_f),
    .sel_en(SEL_EN),
    .PROG(PROG_f),
    .VER(VER_f),
    .SENSE(SENSE_f),
    .WRANY(WRANY_f),
    .lo(1'b0),
    .READ(READ_f),
    .READb(READb_f)
  );
  col_blk colb_n (
    .col({col_n_63, col_n_62, col_n_61, col_n_60, col_n_59, col_n_58, col_n_57, col_n_56, col_n_55, col_n_54, col_n_53, col_n_52, col_n_51, col_n_50, col_n_49, col_n_48, col_n_47, col_n_46, col_n_45, col_n_44, col_n_43, col_n_42, col_n_41, col_n_40, col_n_39, col_n_38, col_n_37, col_n_36, col_n_35, col_n_34, col_n_33, col_n_32, col_n_31, col_n_30, col_n_29, col_n_28, col_n_27, col_n_26, col_n_25, col_n_24, col_n_23, col_n_22, col_n_21, col_n_20, col_n_19, col_n_18, col_n_17, col_n_16, col_n_15, col_n_14, col_n_13, col_n_12, col_n_11, col_n_10, col_n_9, col_n_8, col_n_7, col_n_6, col_n_5, col_n_4, col_n_3, col_n_2, col_n_1, col_n_0}),
    .vw(vw_n),
    .vbus(VBUS_N),
    .C1(C1_n),
    .C2(C2_n),
    .vzero(VCM),
    .vrailp(VRAILP),
    .vrailm(VRAILM),
    .sdi(SDI),
    .rstb(rstb_n),
    .col1_clk(col1_clk_n),
    .col2_clk(col2_clk_n),
    .sel_en(SEL_EN),
    .PROG(PROG_n),
    .VER(VER_n),
    .SENSE(SENSE_n),
    .WRANY(WRANY_n),
    .lo(1'b0),
    .READ(READ_n),
    .READb(READb_n)
  );
  data_blk data_f (
    .sdi(SDI),
    .data_clk(data_clk_f),
    .dload(dload_f),
    .READ(READ_f),
    .rstb(rstb_f),
    .ga({ga_f_48, ga_f_47, ga_f_46, ga_f_45, ga_f_44, ga_f_43, ga_f_42, ga_f_41, ga_f_40, ga_f_39, ga_f_38, ga_f_37, ga_f_36, ga_f_35, ga_f_34, ga_f_33, ga_f_32, ga_f_31, ga_f_30, ga_f_29, ga_f_28, ga_f_27, ga_f_26, ga_f_25, ga_f_24, ga_f_23, ga_f_22, ga_f_21, ga_f_20, ga_f_19, ga_f_18, ga_f_17, ga_f_16, ga_f_15, ga_f_14, ga_f_13, ga_f_12, ga_f_11, ga_f_10, ga_f_9, ga_f_8, ga_f_7, ga_f_6, ga_f_5, ga_f_4, ga_f_3, ga_f_2, ga_f_1, ga_f_0}),
    .gb({gb_f_48, gb_f_47, gb_f_46, gb_f_45, gb_f_44, gb_f_43, gb_f_42, gb_f_41, gb_f_40, gb_f_39, gb_f_38, gb_f_37, gb_f_36, gb_f_35, gb_f_34, gb_f_33, gb_f_32, gb_f_31, gb_f_30, gb_f_29, gb_f_28, gb_f_27, gb_f_26, gb_f_25, gb_f_24, gb_f_23, gb_f_22, gb_f_21, gb_f_20, gb_f_19, gb_f_18, gb_f_17, gb_f_16, gb_f_15, gb_f_14, gb_f_13, gb_f_12, gb_f_11, gb_f_10, gb_f_9, gb_f_8, gb_f_7, gb_f_6, gb_f_5, gb_f_4, gb_f_3, gb_f_2, gb_f_1, gb_f_0}),
    .sp(),
    .spb(),
    .sm(),
    .smb()
  );
  data_blk data_n (
    .sdi(SDI),
    .data_clk(data_clk_n),
    .dload(dload_n),
    .READ(READ_n),
    .rstb(rstb_n),
    .ga({ga_n_48, ga_n_47, ga_n_46, ga_n_45, ga_n_44, ga_n_43, ga_n_42, ga_n_41, ga_n_40, ga_n_39, ga_n_38, ga_n_37, ga_n_36, ga_n_35, ga_n_34, ga_n_33, ga_n_32, ga_n_31, ga_n_30, ga_n_29, ga_n_28, ga_n_27, ga_n_26, ga_n_25, ga_n_24, ga_n_23, ga_n_22, ga_n_21, ga_n_20, ga_n_19, ga_n_18, ga_n_17, ga_n_16, ga_n_15, ga_n_14, ga_n_13, ga_n_12, ga_n_11, ga_n_10, ga_n_9, ga_n_8, ga_n_7, ga_n_6, ga_n_5, ga_n_4, ga_n_3, ga_n_2, ga_n_1, ga_n_0}),
    .gb({gb_n_48, gb_n_47, gb_n_46, gb_n_45, gb_n_44, gb_n_43, gb_n_42, gb_n_41, gb_n_40, gb_n_39, gb_n_38, gb_n_37, gb_n_36, gb_n_35, gb_n_34, gb_n_33, gb_n_32, gb_n_31, gb_n_30, gb_n_29, gb_n_28, gb_n_27, gb_n_26, gb_n_25, gb_n_24, gb_n_23, gb_n_22, gb_n_21, gb_n_20, gb_n_19, gb_n_18, gb_n_17, gb_n_16, gb_n_15, gb_n_14, gb_n_13, gb_n_12, gb_n_11, gb_n_10, gb_n_9, gb_n_8, gb_n_7, gb_n_6, gb_n_5, gb_n_4, gb_n_3, gb_n_2, gb_n_1, gb_n_0}),
    .sp({sp_n_2, sp_n_1, sp_n_0}),
    .spb({spb_n_2, spb_n_1, spb_n_0}),
    .sm({sm_n_2, sm_n_1, sm_n_0}),
    .smb({smb_n_2, smb_n_1, smb_n_0})
  );
  wbuf wbuf_f (
    .wp(WP),
    .pol(pol_f),
    .out(vw_f),
    .vwh(VWH),
    .vwl(VWLO)
  );
  wbuf wbuf_n (
    .wp(WP),
    .pol(pol_n),
    .out(vw_n),
    .vwh(VWH),
    .vwl(VWLO)
  );
  tg_n2 rotg_f (
    .a(R2_f),
    .b(VBUS_F),
    .ctl(rd_out_f),
    .ctlb(rd_out_b_f)
  );
  tg_n2 rotg_n (
    .a(R2_n),
    .b(VBUS_N),
    .ctl(rd_out_n),
    .ctlb(rd_out_b_n)
  );
  wu wu1 (
    .fp(R1_f),
    .fm(C1_f),
    .np(R1_n),
    .nm(C1_n),
    .ck(CK),
    .ck3(CK3),
    .lat(LAT),
    .latb(latb_1),
    .lq(LQ1),
    .sen(),
    .absf(),
    .absn(),
    .q1(),
    .q2(),
    .vbn(IBIAS),
    .vbp(IBIASP),
    .vbnc(VBNC),
    .vbpc(VBPC),
    .vcm(VCM)
  );
  wu wu2 (
    .fp(R2_f),
    .fm(C2_f),
    .np(R2_n),
    .nm(C2_n),
    .ck(CK),
    .ck3(CK3),
    .lat(LAT),
    .latb(latb_2),
    .lq(LQ2),
    .sen(),
    .absf(),
    .absn(),
    .q1(),
    .q2(),
    .vbn(IBIAS),
    .vbp(IBIASP),
    .vbnc(VBNC),
    .vbpc(VBPC),
    .vcm(VCM)
  );
  glob_dig glob (
    .sck(SCK),
    .sdi(SDI),
    .sld(SLD),
    .rst(RST),
    .data_clk_f(data_clk_f),
    .data_clk_n(data_clk_n),
    .row1_clk_f(row1_clk_f),
    .row1_clk_n(row1_clk_n),
    .row2_clk_f(row2_clk_f),
    .row2_clk_n(row2_clk_n),
    .col1_clk_f(col1_clk_f),
    .col1_clk_n(col1_clk_n),
    .col2_clk_f(col2_clk_f),
    .col2_clk_n(col2_clk_n),
    .rstb_f(rstb_f),
    .rstb_n(rstb_n),
    .READ_f(READ_f),
    .READ_n(READ_n),
    .READb_f(READb_f),
    .READb_n(READb_n),
    .PROG_f(PROG_f),
    .PROG_n(PROG_n),
    .VER_f(VER_f),
    .VER_n(VER_n),
    .SENSE_f(SENSE_f),
    .SENSE_n(SENSE_n),
    .WRANY_f(WRANY_f),
    .WRANY_n(WRANY_n),
    .dload_f(dload_f),
    .dload_n(dload_n),
    .pol_f(pol_f),
    .pol_n(pol_n),
    .rd_out_f(rd_out_f),
    .rd_out_n(rd_out_n),
    .rd_out_b_f(rd_out_b_f),
    .rd_out_b_n(rd_out_b_n)
  );
  bias_beta bias (
    .vbn(IBIAS),
    .vbp(IBIASP),
    .vbpc(VBPC),
    .pref(pref),
    .nref(nref)
  );
  nudge_inj ninj (
    .yp0(row_n_100),
    .ym0(row_n_101),
    .yp1(row_n_102),
    .ym1(row_n_103),
    .yp2(row_n_104),
    .ym2(row_n_105),
    .pref(pref),
    .nref(nref),
    .sp0(sp_n_0),
    .spb0(spb_n_0),
    .sm0(sm_n_0),
    .smb0(smb_n_0),
    .sp1(sp_n_1),
    .spb1(spb_n_1),
    .sm1(sm_n_1),
    .smb1(smb_n_1),
    .sp2(sp_n_2),
    .spb2(spb_n_2),
    .sm2(sm_n_2),
    .smb2(smb_n_2)
  );
  tp_tl tp_tl (
    .ro_1_en(),
    .ro_1_rstb(),
    .ro_1_out(),
    .kv_hpo0p35_l_1_f1(),
    .kv_hpo0p35_l_1_s1(),
    .kv_hpo0p35_l_1_s2(),
    .kv_hpo0p35_l_1_f2(),
    .kv_hpo1p41_l_1_f1(),
    .kv_hpo1p41_l_1_s1(),
    .kv_hpo1p41_l_1_s2(),
    .kv_hpo1p41_l_1_f2(),
    .kv_xpo0p35_l_1_f1(),
    .kv_xpo0p35_l_1_s1(),
    .kv_xpo0p35_l_1_s2(),
    .kv_xpo0p35_l_1_f2(),
    .kv_xpo1p41_l_1_f1(),
    .kv_xpo1p41_l_1_s1(),
    .kv_xpo1p41_l_1_s2(),
    .kv_xpo1p41_l_1_f2(),
    .kv_nd_l_1_f1(),
    .kv_nd_l_1_s1(),
    .kv_nd_l_1_s2(),
    .kv_nd_l_1_f2(),
    .kv_pd_l_1_f1(),
    .kv_pd_l_1_s1(),
    .kv_pd_l_1_s2(),
    .kv_pd_l_1_f2(),
    .kv_m1_l_1_f1(),
    .kv_m1_l_1_s1(),
    .kv_m1_l_1_s2(),
    .kv_m1_l_1_f2(),
    .kv_m2_l_1_f1(),
    .kv_m2_l_1_s1(),
    .kv_m2_l_1_s2(),
    .kv_m2_l_1_f2(),
    .kv_m3_l_1_f1(),
    .kv_m3_l_1_s1(),
    .kv_m3_l_1_s2(),
    .kv_m3_l_1_f2(),
    .kv_hpo0p35_s_1_f1(),
    .kv_hpo0p35_s_1_s1(),
    .kv_hpo0p35_s_1_s2(),
    .kv_hpo0p35_s_1_f2(),
    .kv_hpo1p41_s_1_f1(),
    .kv_hpo1p41_s_1_s1(),
    .kv_hpo1p41_s_1_s2(),
    .kv_hpo1p41_s_1_f2(),
    .kv_xpo0p35_s_1_f1(),
    .kv_xpo0p35_s_1_s1(),
    .kv_xpo0p35_s_1_s2(),
    .kv_xpo0p35_s_1_f2(),
    .kv_xpo1p41_s_1_f1(),
    .kv_xpo1p41_s_1_s1(),
    .kv_xpo1p41_s_1_s2(),
    .kv_xpo1p41_s_1_f2(),
    .kv_nd_s_1_f1(),
    .kv_nd_s_1_s1(),
    .kv_nd_s_1_s2(),
    .kv_nd_s_1_f2(),
    .kv_pd_s_1_f1(),
    .kv_pd_s_1_s1(),
    .kv_pd_s_1_s2(),
    .kv_pd_s_1_f2(),
    .kv_m1_s_1_f1(),
    .kv_m1_s_1_s1(),
    .kv_m1_s_1_s2(),
    .kv_m1_s_1_f2(),
    .kv_m2_s_1_f1(),
    .kv_m2_s_1_s1(),
    .kv_m2_s_1_s2(),
    .kv_m2_s_1_f2(),
    .kv_m3_s_1_f1(),
    .kv_m3_s_1_s1(),
    .kv_m3_s_1_s2(),
    .kv_m3_s_1_f2(),
    .ch_poly_1_a(),
    .ch_poly_1_b(),
    .ch_ndiff_1_a(),
    .ch_ndiff_1_b(),
    .ch_pdiff_1_a(),
    .ch_pdiff_1_b(),
    .ch_mcon_1_a(),
    .ch_mcon_1_b(),
    .ch_via1_1_a(),
    .ch_via1_1_b(),
    .ch_via2_1_a(),
    .ch_via2_1_b(),
    .ch_poly_2_a(),
    .ch_poly_2_b(),
    .ch_ndiff_2_a(),
    .ch_ndiff_2_b(),
    .ch_pdiff_2_a(),
    .ch_pdiff_2_b(),
    .ch_mcon_2_a(),
    .ch_mcon_2_b(),
    .rr_1_s(),
    .rr_1_te(),
    .rr_1_wl(),
    .rr_2_s(),
    .rr_2_te(),
    .rr_2_wl(),
    .rr_3_s(),
    .rr_3_te(),
    .rr_3_wl(),
    .rr_4_s(),
    .rr_4_te(),
    .rr_4_wl(),
    .nacc_1_s(),
    .nacc_1_d(),
    .nacc_1_g(),
    .nacc_2_s(),
    .nacc_2_d(),
    .nacc_2_g(),
    .pair_1_ns(),
    .pair_1_ng2(),
    .pair_1_nd2(),
    .pair_1_ng1(),
    .pair_1_nd1(),
    .pair_1_pg2(),
    .pair_1_ps(),
    .pair_1_pd2(),
    .pair_1_pd1(),
    .pair_1_pg1(),
    .pair_2_ns(),
    .pair_2_ng2(),
    .pair_2_nd2(),
    .pair_2_ng1(),
    .pair_2_nd1(),
    .pair_2_pg2(),
    .pair_2_ps(),
    .pair_2_pd2(),
    .pair_2_pd1(),
    .pair_2_pg1(),
    .ch_poly_3_a(),
    .ch_poly_3_b(),
    .ch_ndiff_3_a(),
    .ch_ndiff_3_b(),
    .ch_pdiff_3_a(),
    .ch_pdiff_3_b(),
    .ch_mcon_3_a(),
    .ch_mcon_3_b(),
    .ch_via1_2_a(),
    .ch_via1_2_b(),
    .ch_via2_2_a(),
    .ch_via2_2_b(),
    .rr_5_s(),
    .rr_5_te(),
    .rr_5_wl(),
    .nacc_3_s(),
    .nacc_3_d(),
    .nacc_3_g(),
    .rr_6_s(),
    .rr_6_te(),
    .rr_6_wl(),
    .nacc_4_s(),
    .nacc_4_d(),
    .nacc_4_g(),
    .rr_7_s(),
    .rr_7_te(),
    .rr_7_wl(),
    .nacc_5_s(),
    .nacc_5_d(),
    .nacc_5_g(),
    .rr_8_s(),
    .rr_8_te(),
    .rr_8_wl(),
    .nacc_6_s(),
    .nacc_6_d(),
    .nacc_6_g(),
    .rr_9_s(),
    .rr_9_te(),
    .rr_9_wl(),
    .nacc_7_s(),
    .nacc_7_d(),
    .nacc_7_g(),
    .rr_10_s(),
    .rr_10_te(),
    .rr_10_wl(),
    .nacc_8_s(),
    .nacc_8_d(),
    .nacc_8_g(),
    .rr_11_s(),
    .rr_11_te(),
    .rr_11_wl(),
    .nacc_9_s(),
    .nacc_9_d(),
    .nacc_9_g(),
    .rr_12_s(),
    .rr_12_te(),
    .rr_12_wl(),
    .nacc_10_s(),
    .nacc_10_d(),
    .nacc_10_g(),
    .rr_13_s(),
    .rr_13_te(),
    .rr_13_wl(),
    .nacc_11_s(),
    .nacc_11_d(),
    .nacc_11_g()
  );
  tp_br tp_br (
    .ro_1_en(),
    .ro_1_rstb(),
    .ro_1_out(),
    .kv_hpo0p35_s_1_f1(),
    .kv_hpo0p35_s_1_s1(),
    .kv_hpo0p35_s_1_s2(),
    .kv_hpo0p35_s_1_f2(),
    .kv_hpo1p41_s_1_f1(),
    .kv_hpo1p41_s_1_s1(),
    .kv_hpo1p41_s_1_s2(),
    .kv_hpo1p41_s_1_f2(),
    .kv_xpo0p35_s_1_f1(),
    .kv_xpo0p35_s_1_s1(),
    .kv_xpo0p35_s_1_s2(),
    .kv_xpo0p35_s_1_f2(),
    .kv_xpo1p41_s_1_f1(),
    .kv_xpo1p41_s_1_s1(),
    .kv_xpo1p41_s_1_s2(),
    .kv_xpo1p41_s_1_f2(),
    .kv_nd_s_1_f1(),
    .kv_nd_s_1_s1(),
    .kv_nd_s_1_s2(),
    .kv_nd_s_1_f2(),
    .kv_pd_s_1_f1(),
    .kv_pd_s_1_s1(),
    .kv_pd_s_1_s2(),
    .kv_pd_s_1_f2(),
    .kv_m1_s_1_f1(),
    .kv_m1_s_1_s1(),
    .kv_m1_s_1_s2(),
    .kv_m1_s_1_f2(),
    .kv_m2_s_1_f1(),
    .kv_m2_s_1_s1(),
    .kv_m2_s_1_s2(),
    .kv_m2_s_1_f2(),
    .kv_m3_s_1_f1(),
    .kv_m3_s_1_s1(),
    .kv_m3_s_1_s2(),
    .kv_m3_s_1_f2(),
    .kv_hpo0p35_l_1_f1(),
    .kv_hpo0p35_l_1_s1(),
    .kv_hpo0p35_l_1_s2(),
    .kv_hpo0p35_l_1_f2(),
    .kv_hpo1p41_l_1_f1(),
    .kv_hpo1p41_l_1_s1(),
    .kv_hpo1p41_l_1_s2(),
    .kv_hpo1p41_l_1_f2(),
    .kv_xpo0p35_l_1_f1(),
    .kv_xpo0p35_l_1_s1(),
    .kv_xpo0p35_l_1_s2(),
    .kv_xpo0p35_l_1_f2(),
    .kv_xpo1p41_l_1_f1(),
    .kv_xpo1p41_l_1_s1(),
    .kv_xpo1p41_l_1_s2(),
    .kv_xpo1p41_l_1_f2(),
    .kv_nd_l_1_f1(),
    .kv_nd_l_1_s1(),
    .kv_nd_l_1_s2(),
    .kv_nd_l_1_f2(),
    .kv_pd_l_1_f1(),
    .kv_pd_l_1_s1(),
    .kv_pd_l_1_s2(),
    .kv_pd_l_1_f2(),
    .kv_m1_l_1_f1(),
    .kv_m1_l_1_s1(),
    .kv_m1_l_1_s2(),
    .kv_m1_l_1_f2(),
    .kv_m2_l_1_f1(),
    .kv_m2_l_1_s1(),
    .kv_m2_l_1_s2(),
    .kv_m2_l_1_f2(),
    .kv_m3_l_1_f1(),
    .kv_m3_l_1_s1(),
    .kv_m3_l_1_s2(),
    .kv_m3_l_1_f2(),
    .ch_poly_1_a(),
    .ch_poly_1_b(),
    .ch_ndiff_1_a(),
    .ch_ndiff_1_b(),
    .ch_pdiff_1_a(),
    .ch_pdiff_1_b(),
    .ch_mcon_1_a(),
    .ch_mcon_1_b(),
    .ch_via1_1_a(),
    .ch_via1_1_b(),
    .ch_via2_1_a(),
    .ch_via2_1_b(),
    .ch_poly_2_a(),
    .ch_poly_2_b(),
    .ch_ndiff_2_a(),
    .ch_ndiff_2_b(),
    .ch_pdiff_2_a(),
    .ch_pdiff_2_b(),
    .ch_mcon_2_a(),
    .ch_mcon_2_b(),
    .ch_via1_2_a(),
    .ch_via1_2_b(),
    .ch_via2_2_a(),
    .ch_via2_2_b(),
    .ch_poly_3_a(),
    .ch_poly_3_b(),
    .ch_ndiff_3_a(),
    .ch_ndiff_3_b(),
    .ch_pdiff_3_a(),
    .ch_pdiff_3_b(),
    .ch_mcon_3_a(),
    .ch_mcon_3_b(),
    .rr_1_s(),
    .rr_1_te(),
    .rr_1_wl(),
    .rr_2_s(),
    .rr_2_te(),
    .rr_2_wl(),
    .rr_3_s(),
    .rr_3_te(),
    .rr_3_wl(),
    .rr_4_s(),
    .rr_4_te(),
    .rr_4_wl(),
    .nacc_1_s(),
    .nacc_1_d(),
    .nacc_1_g(),
    .nacc_2_s(),
    .nacc_2_d(),
    .nacc_2_g(),
    .pair_1_ns(),
    .pair_1_ng2(),
    .pair_1_nd2(),
    .pair_1_ng1(),
    .pair_1_nd1(),
    .pair_1_pg2(),
    .pair_1_ps(),
    .pair_1_pd2(),
    .pair_1_pd1(),
    .pair_1_pg1(),
    .pair_2_ns(),
    .pair_2_ng2(),
    .pair_2_nd2(),
    .pair_2_ng1(),
    .pair_2_nd1(),
    .pair_2_pg2(),
    .pair_2_ps(),
    .pair_2_pd2(),
    .pair_2_pd1(),
    .pair_2_pg1(),
    .ch_poly_4_a(),
    .ch_poly_4_b(),
    .ch_ndiff_4_a(),
    .ch_ndiff_4_b(),
    .ch_pdiff_4_a(),
    .ch_pdiff_4_b(),
    .ch_mcon_4_a(),
    .ch_mcon_4_b(),
    .ch_via1_3_a(),
    .ch_via1_3_b(),
    .ch_via2_3_a(),
    .ch_via2_3_b(),
    .rr_5_s(),
    .rr_5_te(),
    .rr_5_wl(),
    .nacc_3_s(),
    .nacc_3_d(),
    .nacc_3_g(),
    .pair_3_ns(),
    .pair_3_ng2(),
    .pair_3_nd2(),
    .pair_3_ng1(),
    .pair_3_nd1(),
    .pair_3_pg2(),
    .pair_3_ps(),
    .pair_3_pd2(),
    .pair_3_pd1(),
    .pair_3_pg1(),
    .rr_6_s(),
    .rr_6_te(),
    .rr_6_wl(),
    .nacc_4_s(),
    .nacc_4_d(),
    .nacc_4_g(),
    .pair_4_ns(),
    .pair_4_ng2(),
    .pair_4_nd2(),
    .pair_4_ng1(),
    .pair_4_nd1(),
    .pair_4_pg2(),
    .pair_4_ps(),
    .pair_4_pd2(),
    .pair_4_pd1(),
    .pair_4_pg1(),
    .rr_7_s(),
    .rr_7_te(),
    .rr_7_wl(),
    .nacc_5_s(),
    .nacc_5_d(),
    .nacc_5_g(),
    .pair_5_ns(),
    .pair_5_ng2(),
    .pair_5_nd2(),
    .pair_5_ng1(),
    .pair_5_nd1(),
    .pair_5_pg2(),
    .pair_5_ps(),
    .pair_5_pd2(),
    .pair_5_pd1(),
    .pair_5_pg1(),
    .rr_8_s(),
    .rr_8_te(),
    .rr_8_wl(),
    .nacc_6_s(),
    .nacc_6_d(),
    .nacc_6_g(),
    .pair_6_ns(),
    .pair_6_ng2(),
    .pair_6_nd2(),
    .pair_6_ng1(),
    .pair_6_nd1(),
    .pair_6_pg2(),
    .pair_6_ps(),
    .pair_6_pd2(),
    .pair_6_pd1(),
    .pair_6_pg1()
  );
  tp_bandl tp_bandl (
    .ch_poly_1_a(),
    .ch_poly_1_b(),
    .ch_ndiff_1_a(),
    .ch_ndiff_1_b(),
    .ch_pdiff_1_a(),
    .ch_pdiff_1_b(),
    .ch_mcon_1_a(),
    .ch_mcon_1_b(),
    .ch_via1_1_a(),
    .ch_via1_1_b(),
    .ch_via2_1_a(),
    .ch_via2_1_b(),
    .rr_1_s(),
    .rr_1_te(),
    .rr_1_wl(),
    .rr_2_s(),
    .rr_2_te(),
    .rr_2_wl(),
    .nacc_1_s(),
    .nacc_1_d(),
    .nacc_1_g(),
    .nacc_2_s(),
    .nacc_2_d(),
    .nacc_2_g(),
    .kv_hpo0p35_l_1_f1(),
    .kv_hpo0p35_l_1_s1(),
    .kv_hpo0p35_l_1_s2(),
    .kv_hpo0p35_l_1_f2(),
    .kv_hpo1p41_l_1_f1(),
    .kv_hpo1p41_l_1_s1(),
    .kv_hpo1p41_l_1_s2(),
    .kv_hpo1p41_l_1_f2(),
    .kv_xpo0p35_l_1_f1(),
    .kv_xpo0p35_l_1_s1(),
    .kv_xpo0p35_l_1_s2(),
    .kv_xpo0p35_l_1_f2(),
    .kv_xpo1p41_l_1_f1(),
    .kv_xpo1p41_l_1_s1(),
    .kv_xpo1p41_l_1_s2(),
    .kv_xpo1p41_l_1_f2(),
    .kv_nd_l_1_f1(),
    .kv_nd_l_1_s1(),
    .kv_nd_l_1_s2(),
    .kv_nd_l_1_f2(),
    .kv_pd_l_1_f1(),
    .kv_pd_l_1_s1(),
    .kv_pd_l_1_s2(),
    .kv_pd_l_1_f2(),
    .kv_m1_l_1_f1(),
    .kv_m1_l_1_s1(),
    .kv_m1_l_1_s2(),
    .kv_m1_l_1_f2(),
    .kv_m2_l_1_f1(),
    .kv_m2_l_1_s1(),
    .kv_m2_l_1_s2(),
    .kv_m2_l_1_f2()
  );
  tp_bandr tp_bandr (
    .kv_hpo0p35_l_1_f1(),
    .kv_hpo0p35_l_1_s1(),
    .kv_hpo0p35_l_1_s2(),
    .kv_hpo0p35_l_1_f2(),
    .kv_hpo1p41_l_1_f1(),
    .kv_hpo1p41_l_1_s1(),
    .kv_hpo1p41_l_1_s2(),
    .kv_hpo1p41_l_1_f2(),
    .kv_xpo0p35_l_1_f1(),
    .kv_xpo0p35_l_1_s1(),
    .kv_xpo0p35_l_1_s2(),
    .kv_xpo0p35_l_1_f2(),
    .kv_xpo1p41_l_1_f1(),
    .kv_xpo1p41_l_1_s1(),
    .kv_xpo1p41_l_1_s2(),
    .kv_xpo1p41_l_1_f2(),
    .kv_nd_l_1_f1(),
    .kv_nd_l_1_s1(),
    .kv_nd_l_1_s2(),
    .kv_nd_l_1_f2(),
    .kv_pd_l_1_f1(),
    .kv_pd_l_1_s1(),
    .kv_pd_l_1_s2(),
    .kv_pd_l_1_f2(),
    .kv_m1_l_1_f1(),
    .kv_m1_l_1_s1(),
    .kv_m1_l_1_s2(),
    .kv_m1_l_1_f2(),
    .kv_m2_l_1_f1(),
    .kv_m2_l_1_s1(),
    .kv_m2_l_1_s2(),
    .kv_m2_l_1_f2(),
    .kv_m3_l_1_f1(),
    .kv_m3_l_1_s1(),
    .kv_m3_l_1_s2(),
    .kv_m3_l_1_f2(),
    .ch_poly_1_a(),
    .ch_poly_1_b(),
    .ch_ndiff_1_a(),
    .ch_ndiff_1_b(),
    .ch_pdiff_1_a(),
    .ch_pdiff_1_b(),
    .ch_mcon_1_a(),
    .ch_mcon_1_b(),
    .ch_via1_1_a(),
    .ch_via1_1_b(),
    .ch_via2_1_a(),
    .ch_via2_1_b(),
    .nacc_1_s(),
    .nacc_1_d(),
    .nacc_1_g(),
    .ch_poly_2_a(),
    .ch_poly_2_b(),
    .ch_ndiff_2_a(),
    .ch_ndiff_2_b(),
    .ch_pdiff_2_a(),
    .ch_pdiff_2_b()
  );
  sky130_fd_sc_hvl__inv_2 ilatb1 (
    .A(LAT),
    .Y(latb_1)
  );
  sky130_fd_sc_hvl__inv_2 ilatb2 (
    .A(LAT),
    .Y(latb_2)
  );
endmodule
