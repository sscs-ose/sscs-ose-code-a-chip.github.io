
// Generated on: Oct 28 2026 01:34:15 CDT (Oct 28 2026 06:34:15 UTC)

// Verification Directory fv/data_blk 

module data_blk(sdi, data_clk, dload, READ, rstb, ga, gb, sp, spb, sm,
     smb);
  input sdi, data_clk, dload, READ, rstb;
  output [48:0] ga, gb;
  output [2:0] sp, spb, sm, smb;
  wire sdi, data_clk, dload, READ, rstb;
  wire [48:0] ga, gb;
  wire [2:0] sp, spb, sm, smb;
  wire [51:0] dl;
  wire [51:0] q;
  wire n_0, n_1, n_2, n_3, n_4, n_5, n_6, n_7;
  wire n_8, n_9, n_10, n_11, n_12, n_13, n_14, n_15;
  wire n_16, n_17, n_18, n_19, n_20, n_21, n_22, n_23;
  wire n_24, n_25, n_26, n_27, n_28, n_29, n_30, n_31;
  wire n_32, n_33, n_34, n_35, n_36, n_37, n_38, n_39;
  wire n_40, n_41, n_42, n_43, n_44, n_45, n_46, n_47;
  wire n_48, n_49, n_50, n_51, n_52, n_53, n_54, n_55;
  wire n_56, n_57, n_58, n_59, n_60, n_61, n_62, n_63;
  wire n_64, n_65, n_66, n_67, n_68, n_69, n_70, n_71;
  wire n_72, n_73, n_74, n_75, n_76, n_77, n_78, n_79;
  wire n_80, n_81, n_82, n_83, n_84, n_85, n_86, n_87;
  wire n_88, n_89, n_90, n_91, n_92, n_93, n_94, n_95;
  wire n_96, n_97, n_98, n_99, n_100, n_101, n_102, n_103;
  wire n_104, n_105, n_106, n_107, n_108, n_109, n_110, n_111;
  wire n_112, n_113, n_114, n_115, n_116, n_117, n_118, n_119;
  wire n_120, n_121, n_122, n_123, n_124, n_125, n_126, n_127;
  wire n_128, n_129, n_130, n_131, n_132, n_133, n_134, n_135;
  wire n_136, n_137, n_138, n_139, n_140, n_141, n_142, n_143;
  wire n_144, n_145, n_146, n_151, n_152;
  sky130_fd_sc_hvl__inv_1 g1161(.A (sm[2]), .Y (smb[2]));
  sky130_fd_sc_hvl__inv_1 g1163(.A (spb[2]), .Y (sp[2]));
  sky130_fd_sc_hvl__nor2_1 g1162__2398(.A (dl[51]), .B (n_152), .Y
       (sm[2]));
  sky130_fd_sc_hvl__nand2_1 g1164__5107(.A (n_151), .B (dl[51]), .Y
       (spb[2]));
  sky130_fd_sc_hvl__inv_1 g1167(.A (spb[1]), .Y (sp[1]));
  sky130_fd_sc_hvl__inv_1 g1166(.A (sm[1]), .Y (smb[1]));
  sky130_fd_sc_hvl__dlxtp_1 \dl_reg[51] (.GATE (dload), .D (q[51]), .Q
       (dl[51]));
  sky130_fd_sc_hvl__nor2_1 g1168__6260(.A (dl[50]), .B (n_152), .Y
       (sm[1]));
  sky130_fd_sc_hvl__nand2_1 g1169__4319(.A (n_151), .B (dl[50]), .Y
       (spb[1]));
  sky130_fd_sc_hvl__inv_1 g1172(.A (sm[0]), .Y (smb[0]));
  sky130_fd_sc_hvl__inv_1 g1173(.A (spb[0]), .Y (sp[0]));
  sky130_fd_sc_hvl__dfrtp_1 \q_reg[51] (.RESET_B (rstb), .CLK
       (data_clk), .D (q[50]), .Q (q[51]));
  sky130_fd_sc_hvl__dlxtp_1 \dl_reg[50] (.GATE (dload), .D (q[50]), .Q
       (dl[50]));
  sky130_fd_sc_hvl__nor2_1 g1174__8428(.A (dl[49]), .B (n_152), .Y
       (sm[0]));
  sky130_fd_sc_hvl__nand2_1 g1175__5526(.A (n_151), .B (dl[49]), .Y
       (spb[0]));
  sky130_fd_sc_hvl__and2_1 g1178__6783(.A (READ), .B (n_144), .X
       (n_146));
  sky130_fd_sc_hvl__dlxtp_1 \dl_reg[49] (.GATE (dload), .D (q[49]), .Q
       (dl[49]));
  sky130_fd_sc_hvl__and2_1 g1179__3680(.A (READ), .B (dl[48]), .X
       (n_145));
  sky130_fd_sc_hvl__dfrtp_1 \q_reg[50] (.RESET_B (rstb), .CLK
       (data_clk), .D (q[49]), .Q (q[50]));
  sky130_fd_sc_hvl__inv_1 g1180(.A (dl[48]), .Y (n_144));
  sky130_fd_sc_hvl__and2_1 g1183__1617(.A (READ), .B (n_141), .X
       (n_143));
  sky130_fd_sc_hvl__dfrtp_1 \q_reg[49] (.RESET_B (rstb), .CLK
       (data_clk), .D (q[48]), .Q (q[49]));
  sky130_fd_sc_hvl__and2_1 g1184__2802(.A (READ), .B (dl[47]), .X
       (n_142));
  sky130_fd_sc_hvl__dlxtp_1 \dl_reg[48] (.GATE (dload), .D (q[48]), .Q
       (dl[48]));
  sky130_fd_sc_hvl__inv_1 g1185(.A (dl[47]), .Y (n_141));
  sky130_fd_sc_hvl__and2_1 g1188__1705(.A (READ), .B (n_137), .X
       (n_140));
  sky130_fd_sc_hvl__and2_1 g1189__5122(.A (READ), .B (dl[46]), .X
       (n_139));
  sky130_fd_sc_hvl__dfrtp_1 \q_reg[48] (.RESET_B (rstb), .CLK
       (data_clk), .D (q[47]), .Q (q[48]));
  sky130_fd_sc_hvl__dlxtp_1 \dl_reg[47] (.GATE (dload), .D (q[47]), .Q
       (dl[47]));
  sky130_fd_sc_hvl__and2_1 g1193__8246(.A (READ), .B (n_134), .X
       (n_138));
  sky130_fd_sc_hvl__inv_1 g1190(.A (dl[46]), .Y (n_137));
  sky130_fd_sc_hvl__and2_1 g1194__7098(.A (READ), .B (dl[45]), .X
       (n_136));
  sky130_fd_sc_hvl__dfrtp_1 \q_reg[47] (.RESET_B (rstb), .CLK
       (data_clk), .D (q[46]), .Q (q[47]));
  sky130_fd_sc_hvl__dlxtp_1 \dl_reg[46] (.GATE (dload), .D (q[46]), .Q
       (dl[46]));
  sky130_fd_sc_hvl__and2_1 g1198__6131(.A (READ), .B (n_131), .X
       (n_135));
  sky130_fd_sc_hvl__inv_1 g1195(.A (dl[45]), .Y (n_134));
  sky130_fd_sc_hvl__and2_1 g1199__1881(.A (READ), .B (dl[44]), .X
       (n_133));
  sky130_fd_sc_hvl__dfrtp_1 \q_reg[46] (.RESET_B (rstb), .CLK
       (data_clk), .D (q[45]), .Q (q[46]));
  sky130_fd_sc_hvl__dlxtp_1 \dl_reg[45] (.GATE (dload), .D (q[45]), .Q
       (dl[45]));
  sky130_fd_sc_hvl__and2_1 g1203__5115(.A (READ), .B (n_129), .X
       (n_132));
  sky130_fd_sc_hvl__inv_1 g1200(.A (dl[44]), .Y (n_131));
  sky130_fd_sc_hvl__dlxtp_1 \dl_reg[44] (.GATE (dload), .D (q[44]), .Q
       (dl[44]));
  sky130_fd_sc_hvl__and2_1 g1204__7482(.A (READ), .B (dl[43]), .X
       (n_130));
  sky130_fd_sc_hvl__dfrtp_1 \q_reg[45] (.RESET_B (rstb), .CLK
       (data_clk), .D (q[44]), .Q (q[45]));
  sky130_fd_sc_hvl__inv_1 g1205(.A (dl[43]), .Y (n_129));
  sky130_fd_sc_hvl__and2_1 g1208__4733(.A (READ), .B (n_126), .X
       (n_128));
  sky130_fd_sc_hvl__dfrtp_1 \q_reg[44] (.RESET_B (rstb), .CLK
       (data_clk), .D (q[43]), .Q (q[44]));
  sky130_fd_sc_hvl__and2_1 g1209__6161(.A (READ), .B (dl[42]), .X
       (n_127));
  sky130_fd_sc_hvl__dlxtp_1 \dl_reg[43] (.GATE (dload), .D (q[43]), .Q
       (dl[43]));
  sky130_fd_sc_hvl__inv_1 g1210(.A (dl[42]), .Y (n_126));
  sky130_fd_sc_hvl__and2_1 g1213__9315(.A (READ), .B (n_123), .X
       (n_125));
  sky130_fd_sc_hvl__dfrtp_1 \q_reg[43] (.RESET_B (rstb), .CLK
       (data_clk), .D (q[42]), .Q (q[43]));
  sky130_fd_sc_hvl__and2_1 g1214__9945(.A (READ), .B (dl[41]), .X
       (n_124));
  sky130_fd_sc_hvl__dlxtp_1 \dl_reg[42] (.GATE (dload), .D (q[42]), .Q
       (dl[42]));
  sky130_fd_sc_hvl__inv_1 g1215(.A (dl[41]), .Y (n_123));
  sky130_fd_sc_hvl__and2_1 g1218__2883(.A (READ), .B (n_119), .X
       (n_122));
  sky130_fd_sc_hvl__and2_1 g1219__2346(.A (READ), .B (dl[40]), .X
       (n_121));
  sky130_fd_sc_hvl__dfrtp_1 \q_reg[42] (.RESET_B (rstb), .CLK
       (data_clk), .D (q[41]), .Q (q[42]));
  sky130_fd_sc_hvl__dlxtp_1 \dl_reg[41] (.GATE (dload), .D (q[41]), .Q
       (dl[41]));
  sky130_fd_sc_hvl__and2_1 g1223__1666(.A (READ), .B (n_116), .X
       (n_120));
  sky130_fd_sc_hvl__inv_1 g1220(.A (dl[40]), .Y (n_119));
  sky130_fd_sc_hvl__and2_1 g1224__7410(.A (READ), .B (dl[39]), .X
       (n_118));
  sky130_fd_sc_hvl__dfrtp_1 \q_reg[41] (.RESET_B (rstb), .CLK
       (data_clk), .D (q[40]), .Q (q[41]));
  sky130_fd_sc_hvl__dlxtp_1 \dl_reg[40] (.GATE (dload), .D (q[40]), .Q
       (dl[40]));
  sky130_fd_sc_hvl__and2_1 g1228__6417(.A (READ), .B (n_113), .X
       (n_117));
  sky130_fd_sc_hvl__inv_1 g1225(.A (dl[39]), .Y (n_116));
  sky130_fd_sc_hvl__and2_1 g1229__5477(.A (READ), .B (dl[38]), .X
       (n_115));
  sky130_fd_sc_hvl__dfrtp_1 \q_reg[40] (.RESET_B (rstb), .CLK
       (data_clk), .D (q[39]), .Q (q[40]));
  sky130_fd_sc_hvl__dlxtp_1 \dl_reg[39] (.GATE (dload), .D (q[39]), .Q
       (dl[39]));
  sky130_fd_sc_hvl__and2_1 g1233__2398(.A (READ), .B (n_110), .X
       (n_114));
  sky130_fd_sc_hvl__inv_1 g1230(.A (dl[38]), .Y (n_113));
  sky130_fd_sc_hvl__and2_1 g1234__5107(.A (READ), .B (dl[37]), .X
       (n_112));
  sky130_fd_sc_hvl__dfrtp_1 \q_reg[39] (.RESET_B (rstb), .CLK
       (data_clk), .D (q[38]), .Q (q[39]));
  sky130_fd_sc_hvl__dlxtp_1 \dl_reg[38] (.GATE (dload), .D (q[38]), .Q
       (dl[38]));
  sky130_fd_sc_hvl__and2_1 g1238__6260(.A (READ), .B (n_107), .X
       (n_111));
  sky130_fd_sc_hvl__inv_1 g1235(.A (dl[37]), .Y (n_110));
  sky130_fd_sc_hvl__and2_1 g1239__4319(.A (READ), .B (dl[36]), .X
       (n_109));
  sky130_fd_sc_hvl__dfrtp_1 \q_reg[38] (.RESET_B (rstb), .CLK
       (data_clk), .D (q[37]), .Q (q[38]));
  sky130_fd_sc_hvl__dlxtp_1 \dl_reg[37] (.GATE (dload), .D (q[37]), .Q
       (dl[37]));
  sky130_fd_sc_hvl__and2_1 g1243__8428(.A (READ), .B (n_104), .X
       (n_108));
  sky130_fd_sc_hvl__inv_1 g1240(.A (dl[36]), .Y (n_107));
  sky130_fd_sc_hvl__and2_1 g1244__5526(.A (READ), .B (dl[35]), .X
       (n_106));
  sky130_fd_sc_hvl__dfrtp_1 \q_reg[37] (.RESET_B (rstb), .CLK
       (data_clk), .D (q[36]), .Q (q[37]));
  sky130_fd_sc_hvl__dlxtp_1 \dl_reg[36] (.GATE (dload), .D (q[36]), .Q
       (dl[36]));
  sky130_fd_sc_hvl__and2_1 g1248__6783(.A (READ), .B (n_102), .X
       (n_105));
  sky130_fd_sc_hvl__inv_1 g1245(.A (dl[35]), .Y (n_104));
  sky130_fd_sc_hvl__dlxtp_1 \dl_reg[35] (.GATE (dload), .D (q[35]), .Q
       (dl[35]));
  sky130_fd_sc_hvl__and2_1 g1249__3680(.A (READ), .B (dl[34]), .X
       (n_103));
  sky130_fd_sc_hvl__dfrtp_1 \q_reg[36] (.RESET_B (rstb), .CLK
       (data_clk), .D (q[35]), .Q (q[36]));
  sky130_fd_sc_hvl__inv_1 g1250(.A (dl[34]), .Y (n_102));
  sky130_fd_sc_hvl__and2_1 g1253__1617(.A (READ), .B (n_99), .X
       (n_101));
  sky130_fd_sc_hvl__dfrtp_1 \q_reg[35] (.RESET_B (rstb), .CLK
       (data_clk), .D (q[34]), .Q (q[35]));
  sky130_fd_sc_hvl__and2_1 g1254__2802(.A (READ), .B (dl[33]), .X
       (n_100));
  sky130_fd_sc_hvl__dlxtp_1 \dl_reg[34] (.GATE (dload), .D (q[34]), .Q
       (dl[34]));
  sky130_fd_sc_hvl__inv_1 g1255(.A (dl[33]), .Y (n_99));
  sky130_fd_sc_hvl__and2_1 g1258__1705(.A (READ), .B (n_96), .X (n_98));
  sky130_fd_sc_hvl__dfrtp_1 \q_reg[34] (.RESET_B (rstb), .CLK
       (data_clk), .D (q[33]), .Q (q[34]));
  sky130_fd_sc_hvl__and2_1 g1259__5122(.A (READ), .B (dl[32]), .X
       (n_97));
  sky130_fd_sc_hvl__dlxtp_1 \dl_reg[33] (.GATE (dload), .D (q[33]), .Q
       (dl[33]));
  sky130_fd_sc_hvl__inv_1 g1260(.A (dl[32]), .Y (n_96));
  sky130_fd_sc_hvl__and2_1 g1263__8246(.A (READ), .B (n_93), .X (n_95));
  sky130_fd_sc_hvl__dfrtp_1 \q_reg[33] (.RESET_B (rstb), .CLK
       (data_clk), .D (q[32]), .Q (q[33]));
  sky130_fd_sc_hvl__and2_1 g1264__7098(.A (READ), .B (dl[31]), .X
       (n_94));
  sky130_fd_sc_hvl__dlxtp_1 \dl_reg[32] (.GATE (dload), .D (q[32]), .Q
       (dl[32]));
  sky130_fd_sc_hvl__inv_1 g1265(.A (dl[31]), .Y (n_93));
  sky130_fd_sc_hvl__and2_1 g1268__6131(.A (READ), .B (n_90), .X (n_92));
  sky130_fd_sc_hvl__dfrtp_1 \q_reg[32] (.RESET_B (rstb), .CLK
       (data_clk), .D (q[31]), .Q (q[32]));
  sky130_fd_sc_hvl__and2_1 g1269__1881(.A (READ), .B (dl[30]), .X
       (n_91));
  sky130_fd_sc_hvl__dlxtp_1 \dl_reg[31] (.GATE (dload), .D (q[31]), .Q
       (dl[31]));
  sky130_fd_sc_hvl__inv_1 g1270(.A (dl[30]), .Y (n_90));
  sky130_fd_sc_hvl__and2_1 g1273__5115(.A (READ), .B (n_87), .X (n_89));
  sky130_fd_sc_hvl__dlxtp_1 \dl_reg[30] (.GATE (dload), .D (q[30]), .Q
       (dl[30]));
  sky130_fd_sc_hvl__and2_1 g1274__7482(.A (READ), .B (dl[29]), .X
       (n_88));
  sky130_fd_sc_hvl__dfrtp_1 \q_reg[31] (.RESET_B (rstb), .CLK
       (data_clk), .D (q[30]), .Q (q[31]));
  sky130_fd_sc_hvl__inv_1 g1275(.A (dl[29]), .Y (n_87));
  sky130_fd_sc_hvl__and2_1 g1278__4733(.A (READ), .B (n_83), .X (n_86));
  sky130_fd_sc_hvl__and2_1 g1279__6161(.A (READ), .B (dl[28]), .X
       (n_85));
  sky130_fd_sc_hvl__dfrtp_1 \q_reg[30] (.RESET_B (rstb), .CLK
       (data_clk), .D (q[29]), .Q (q[30]));
  sky130_fd_sc_hvl__dlxtp_1 \dl_reg[29] (.GATE (dload), .D (q[29]), .Q
       (dl[29]));
  sky130_fd_sc_hvl__and2_1 g1283__9315(.A (READ), .B (n_80), .X (n_84));
  sky130_fd_sc_hvl__inv_1 g1280(.A (dl[28]), .Y (n_83));
  sky130_fd_sc_hvl__and2_1 g1284__9945(.A (READ), .B (dl[27]), .X
       (n_82));
  sky130_fd_sc_hvl__dlxtp_1 \dl_reg[28] (.GATE (dload), .D (q[28]), .Q
       (dl[28]));
  sky130_fd_sc_hvl__dfrtp_1 \q_reg[29] (.RESET_B (rstb), .CLK
       (data_clk), .D (q[28]), .Q (q[29]));
  sky130_fd_sc_hvl__and2_1 g1288__2883(.A (READ), .B (n_77), .X (n_81));
  sky130_fd_sc_hvl__inv_1 g1285(.A (dl[27]), .Y (n_80));
  sky130_fd_sc_hvl__and2_1 g1289__2346(.A (READ), .B (dl[26]), .X
       (n_79));
  sky130_fd_sc_hvl__dfrtp_1 \q_reg[28] (.RESET_B (rstb), .CLK
       (data_clk), .D (q[27]), .Q (q[28]));
  sky130_fd_sc_hvl__dlxtp_1 \dl_reg[27] (.GATE (dload), .D (q[27]), .Q
       (dl[27]));
  sky130_fd_sc_hvl__and2_1 g1293__1666(.A (READ), .B (n_74), .X (n_78));
  sky130_fd_sc_hvl__inv_1 g1290(.A (dl[26]), .Y (n_77));
  sky130_fd_sc_hvl__and2_1 g1294__7410(.A (READ), .B (dl[25]), .X
       (n_76));
  sky130_fd_sc_hvl__dfrtp_1 \q_reg[27] (.RESET_B (rstb), .CLK
       (data_clk), .D (q[26]), .Q (q[27]));
  sky130_fd_sc_hvl__dlxtp_1 \dl_reg[26] (.GATE (dload), .D (q[26]), .Q
       (dl[26]));
  sky130_fd_sc_hvl__and2_1 g1298__6417(.A (READ), .B (n_71), .X (n_75));
  sky130_fd_sc_hvl__inv_1 g1295(.A (dl[25]), .Y (n_74));
  sky130_fd_sc_hvl__and2_1 g1299__5477(.A (READ), .B (dl[24]), .X
       (n_73));
  sky130_fd_sc_hvl__dfrtp_1 \q_reg[26] (.RESET_B (rstb), .CLK
       (data_clk), .D (q[25]), .Q (q[26]));
  sky130_fd_sc_hvl__dlxtp_1 \dl_reg[25] (.GATE (dload), .D (q[25]), .Q
       (dl[25]));
  sky130_fd_sc_hvl__and2_1 g1303__2398(.A (READ), .B (n_68), .X (n_72));
  sky130_fd_sc_hvl__inv_1 g1300(.A (dl[24]), .Y (n_71));
  sky130_fd_sc_hvl__and2_1 g1304__5107(.A (READ), .B (dl[23]), .X
       (n_70));
  sky130_fd_sc_hvl__dfrtp_1 \q_reg[25] (.RESET_B (rstb), .CLK
       (data_clk), .D (q[24]), .Q (q[25]));
  sky130_fd_sc_hvl__dlxtp_1 \dl_reg[24] (.GATE (dload), .D (q[24]), .Q
       (dl[24]));
  sky130_fd_sc_hvl__and2_1 g1308__6260(.A (READ), .B (n_66), .X (n_69));
  sky130_fd_sc_hvl__inv_1 g1305(.A (dl[23]), .Y (n_68));
  sky130_fd_sc_hvl__and2_1 g1309__4319(.A (READ), .B (dl[22]), .X
       (n_67));
  sky130_fd_sc_hvl__dfrtp_1 \q_reg[24] (.RESET_B (rstb), .CLK
       (data_clk), .D (q[23]), .Q (q[24]));
  sky130_fd_sc_hvl__dlxtp_1 \dl_reg[23] (.GATE (dload), .D (q[23]), .Q
       (dl[23]));
  sky130_fd_sc_hvl__inv_1 g1310(.A (dl[22]), .Y (n_66));
  sky130_fd_sc_hvl__and2_1 g1313__8428(.A (READ), .B (n_62), .X (n_65));
  sky130_fd_sc_hvl__and2_1 g1314__5526(.A (READ), .B (dl[21]), .X
       (n_64));
  sky130_fd_sc_hvl__dfrtp_1 \q_reg[23] (.RESET_B (rstb), .CLK
       (data_clk), .D (q[22]), .Q (q[23]));
  sky130_fd_sc_hvl__dlxtp_1 \dl_reg[22] (.GATE (dload), .D (q[22]), .Q
       (dl[22]));
  sky130_fd_sc_hvl__and2_1 g1318__6783(.A (READ), .B (n_59), .X (n_63));
  sky130_fd_sc_hvl__inv_1 g1315(.A (dl[21]), .Y (n_62));
  sky130_fd_sc_hvl__and2_1 g1319__3680(.A (READ), .B (dl[20]), .X
       (n_61));
  sky130_fd_sc_hvl__dfrtp_1 \q_reg[22] (.RESET_B (rstb), .CLK
       (data_clk), .D (q[21]), .Q (q[22]));
  sky130_fd_sc_hvl__dlxtp_1 \dl_reg[21] (.GATE (dload), .D (q[21]), .Q
       (dl[21]));
  sky130_fd_sc_hvl__and2_1 g1323__1617(.A (READ), .B (n_56), .X (n_60));
  sky130_fd_sc_hvl__inv_1 g1320(.A (dl[20]), .Y (n_59));
  sky130_fd_sc_hvl__and2_1 g1324__2802(.A (READ), .B (dl[19]), .X
       (n_58));
  sky130_fd_sc_hvl__dfrtp_1 \q_reg[21] (.RESET_B (rstb), .CLK
       (data_clk), .D (q[20]), .Q (q[21]));
  sky130_fd_sc_hvl__dlxtp_1 \dl_reg[20] (.GATE (dload), .D (q[20]), .Q
       (dl[20]));
  sky130_fd_sc_hvl__and2_1 g1328__1705(.A (READ), .B (n_53), .X (n_57));
  sky130_fd_sc_hvl__inv_1 g1325(.A (dl[19]), .Y (n_56));
  sky130_fd_sc_hvl__and2_1 g1329__5122(.A (READ), .B (dl[18]), .X
       (n_55));
  sky130_fd_sc_hvl__dfrtp_1 \q_reg[20] (.RESET_B (rstb), .CLK
       (data_clk), .D (q[19]), .Q (q[20]));
  sky130_fd_sc_hvl__dlxtp_1 \dl_reg[19] (.GATE (dload), .D (q[19]), .Q
       (dl[19]));
  sky130_fd_sc_hvl__and2_1 g1333__8246(.A (READ), .B (n_50), .X (n_54));
  sky130_fd_sc_hvl__inv_1 g1330(.A (dl[18]), .Y (n_53));
  sky130_fd_sc_hvl__and2_1 g1334__7098(.A (READ), .B (dl[17]), .X
       (n_52));
  sky130_fd_sc_hvl__dfrtp_1 \q_reg[19] (.RESET_B (rstb), .CLK
       (data_clk), .D (q[18]), .Q (q[19]));
  sky130_fd_sc_hvl__dlxtp_1 \dl_reg[18] (.GATE (dload), .D (q[18]), .Q
       (dl[18]));
  sky130_fd_sc_hvl__and2_1 g1338__6131(.A (READ), .B (n_48), .X (n_51));
  sky130_fd_sc_hvl__inv_1 g1335(.A (dl[17]), .Y (n_50));
  sky130_fd_sc_hvl__and2_1 g1339__1881(.A (READ), .B (dl[16]), .X
       (n_49));
  sky130_fd_sc_hvl__dfrtp_1 \q_reg[18] (.RESET_B (rstb), .CLK
       (data_clk), .D (q[17]), .Q (q[18]));
  sky130_fd_sc_hvl__dlxtp_1 \dl_reg[17] (.GATE (dload), .D (q[17]), .Q
       (dl[17]));
  sky130_fd_sc_hvl__inv_1 g1340(.A (dl[16]), .Y (n_48));
  sky130_fd_sc_hvl__and2_1 g1343__5115(.A (READ), .B (n_45), .X (n_47));
  sky130_fd_sc_hvl__dfrtp_1 \q_reg[17] (.RESET_B (rstb), .CLK
       (data_clk), .D (q[16]), .Q (q[17]));
  sky130_fd_sc_hvl__and2_1 g1344__7482(.A (READ), .B (dl[15]), .X
       (n_46));
  sky130_fd_sc_hvl__dlxtp_1 \dl_reg[16] (.GATE (dload), .D (q[16]), .Q
       (dl[16]));
  sky130_fd_sc_hvl__inv_1 g1345(.A (dl[15]), .Y (n_45));
  sky130_fd_sc_hvl__and2_1 g1348__4733(.A (READ), .B (n_42), .X (n_44));
  sky130_fd_sc_hvl__and2_1 g1349__6161(.A (READ), .B (dl[14]), .X
       (n_43));
  sky130_fd_sc_hvl__dfrtp_1 \q_reg[16] (.RESET_B (rstb), .CLK
       (data_clk), .D (q[15]), .Q (q[16]));
  sky130_fd_sc_hvl__dlxtp_1 \dl_reg[15] (.GATE (dload), .D (q[15]), .Q
       (dl[15]));
  sky130_fd_sc_hvl__inv_1 g1350(.A (dl[14]), .Y (n_42));
  sky130_fd_sc_hvl__and2_1 g1353__9315(.A (READ), .B (n_39), .X (n_41));
  sky130_fd_sc_hvl__dfrtp_1 \q_reg[15] (.RESET_B (rstb), .CLK
       (data_clk), .D (q[14]), .Q (q[15]));
  sky130_fd_sc_hvl__and2_1 g1354__9945(.A (READ), .B (dl[13]), .X
       (n_40));
  sky130_fd_sc_hvl__dlxtp_1 \dl_reg[14] (.GATE (dload), .D (q[14]), .Q
       (dl[14]));
  sky130_fd_sc_hvl__inv_1 g1355(.A (dl[13]), .Y (n_39));
  sky130_fd_sc_hvl__and2_1 g1358__2883(.A (READ), .B (n_35), .X (n_38));
  sky130_fd_sc_hvl__dfrtp_1 \q_reg[14] (.RESET_B (rstb), .CLK
       (data_clk), .D (q[13]), .Q (q[14]));
  sky130_fd_sc_hvl__and2_1 g1359__2346(.A (READ), .B (dl[12]), .X
       (n_37));
  sky130_fd_sc_hvl__dlxtp_1 \dl_reg[13] (.GATE (dload), .D (q[13]), .Q
       (dl[13]));
  sky130_fd_sc_hvl__and2_1 g1363__1666(.A (READ), .B (n_33), .X (n_36));
  sky130_fd_sc_hvl__inv_1 g1360(.A (dl[12]), .Y (n_35));
  sky130_fd_sc_hvl__dfrtp_1 \q_reg[13] (.RESET_B (rstb), .CLK
       (data_clk), .D (q[12]), .Q (q[13]));
  sky130_fd_sc_hvl__and2_1 g1364__7410(.A (READ), .B (dl[11]), .X
       (n_34));
  sky130_fd_sc_hvl__dlxtp_1 \dl_reg[12] (.GATE (dload), .D (q[12]), .Q
       (dl[12]));
  sky130_fd_sc_hvl__inv_1 g1365(.A (dl[11]), .Y (n_33));
  sky130_fd_sc_hvl__and2_1 g1368__6417(.A (READ), .B (n_29), .X (n_32));
  sky130_fd_sc_hvl__and2_1 g1369__5477(.A (READ), .B (dl[10]), .X
       (n_31));
  sky130_fd_sc_hvl__dfrtp_1 \q_reg[12] (.RESET_B (rstb), .CLK
       (data_clk), .D (q[11]), .Q (q[12]));
  sky130_fd_sc_hvl__dlxtp_1 \dl_reg[11] (.GATE (dload), .D (q[11]), .Q
       (dl[11]));
  sky130_fd_sc_hvl__and2_1 g1373__2398(.A (READ), .B (n_27), .X (n_30));
  sky130_fd_sc_hvl__inv_1 g1370(.A (dl[10]), .Y (n_29));
  sky130_fd_sc_hvl__dfrtp_1 \q_reg[11] (.RESET_B (rstb), .CLK
       (data_clk), .D (q[10]), .Q (q[11]));
  sky130_fd_sc_hvl__and2_1 g1374__5107(.A (READ), .B (dl[9]), .X
       (n_28));
  sky130_fd_sc_hvl__dlxtp_1 \dl_reg[10] (.GATE (dload), .D (q[10]), .Q
       (dl[10]));
  sky130_fd_sc_hvl__inv_1 g1375(.A (dl[9]), .Y (n_27));
  sky130_fd_sc_hvl__and2_1 g1378__6260(.A (READ), .B (n_23), .X (n_26));
  sky130_fd_sc_hvl__dfrtp_1 \q_reg[10] (.RESET_B (rstb), .CLK
       (data_clk), .D (q[9]), .Q (q[10]));
  sky130_fd_sc_hvl__and2_1 g1379__4319(.A (READ), .B (dl[8]), .X
       (n_25));
  sky130_fd_sc_hvl__dlxtp_1 \dl_reg[9] (.GATE (dload), .D (q[9]), .Q
       (dl[9]));
  sky130_fd_sc_hvl__and2_1 g1383__8428(.A (READ), .B (n_21), .X (n_24));
  sky130_fd_sc_hvl__inv_1 g1380(.A (dl[8]), .Y (n_23));
  sky130_fd_sc_hvl__dfrtp_1 \q_reg[9] (.RESET_B (rstb), .CLK
       (data_clk), .D (q[8]), .Q (q[9]));
  sky130_fd_sc_hvl__and2_1 g1384__5526(.A (READ), .B (dl[7]), .X
       (n_22));
  sky130_fd_sc_hvl__dlxtp_1 \dl_reg[8] (.GATE (dload), .D (q[8]), .Q
       (dl[8]));
  sky130_fd_sc_hvl__inv_1 g1385(.A (dl[7]), .Y (n_21));
  sky130_fd_sc_hvl__and2_1 g1388__6783(.A (READ), .B (n_18), .X (n_20));
  sky130_fd_sc_hvl__dfrtp_1 \q_reg[8] (.RESET_B (rstb), .CLK
       (data_clk), .D (q[7]), .Q (q[8]));
  sky130_fd_sc_hvl__and2_1 g1389__3680(.A (READ), .B (dl[6]), .X
       (n_19));
  sky130_fd_sc_hvl__dlxtp_1 \dl_reg[7] (.GATE (dload), .D (q[7]), .Q
       (dl[7]));
  sky130_fd_sc_hvl__inv_1 g1390(.A (dl[6]), .Y (n_18));
  sky130_fd_sc_hvl__and2_1 g1393__1617(.A (READ), .B (n_15), .X (n_17));
  sky130_fd_sc_hvl__dlxtp_1 \dl_reg[6] (.GATE (dload), .D (q[6]), .Q
       (dl[6]));
  sky130_fd_sc_hvl__and2_1 g1394__2802(.A (READ), .B (dl[5]), .X
       (n_16));
  sky130_fd_sc_hvl__dfrtp_1 \q_reg[7] (.RESET_B (rstb), .CLK
       (data_clk), .D (q[6]), .Q (q[7]));
  sky130_fd_sc_hvl__inv_1 g1395(.A (dl[5]), .Y (n_15));
  sky130_fd_sc_hvl__and2_1 g1398__1705(.A (READ), .B (n_11), .X (n_14));
  sky130_fd_sc_hvl__dfrtp_1 \q_reg[6] (.RESET_B (rstb), .CLK
       (data_clk), .D (q[5]), .Q (q[6]));
  sky130_fd_sc_hvl__and2_1 g1399__5122(.A (READ), .B (dl[4]), .X
       (n_13));
  sky130_fd_sc_hvl__dlxtp_1 \dl_reg[5] (.GATE (dload), .D (q[5]), .Q
       (dl[5]));
  sky130_fd_sc_hvl__and2_1 g1403__8246(.A (READ), .B (n_9), .X (n_12));
  sky130_fd_sc_hvl__inv_1 g1400(.A (dl[4]), .Y (n_11));
  sky130_fd_sc_hvl__dlxtp_1 \dl_reg[4] (.GATE (dload), .D (q[4]), .Q
       (dl[4]));
  sky130_fd_sc_hvl__and2_1 g1404__7098(.A (READ), .B (dl[3]), .X
       (n_10));
  sky130_fd_sc_hvl__dfrtp_1 \q_reg[5] (.RESET_B (rstb), .CLK
       (data_clk), .D (q[4]), .Q (q[5]));
  sky130_fd_sc_hvl__inv_1 g1405(.A (dl[3]), .Y (n_9));
  sky130_fd_sc_hvl__and2_1 g1408__6131(.A (READ), .B (n_6), .X (n_8));
  sky130_fd_sc_hvl__dlxtp_1 \dl_reg[3] (.GATE (dload), .D (q[3]), .Q
       (dl[3]));
  sky130_fd_sc_hvl__and2_1 g1409__1881(.A (READ), .B (dl[2]), .X (n_7));
  sky130_fd_sc_hvl__dfrtp_1 \q_reg[4] (.RESET_B (rstb), .CLK
       (data_clk), .D (q[3]), .Q (q[4]));
  sky130_fd_sc_hvl__inv_1 g1410(.A (dl[2]), .Y (n_6));
  sky130_fd_sc_hvl__and2_1 g1413__5115(.A (READ), .B (n_3), .X (n_5));
  sky130_fd_sc_hvl__and2_1 g1414__7482(.A (READ), .B (dl[1]), .X (n_4));
  sky130_fd_sc_hvl__dfrtp_1 \q_reg[3] (.RESET_B (rstb), .CLK
       (data_clk), .D (q[2]), .Q (q[3]));
  sky130_fd_sc_hvl__dlxtp_1 \dl_reg[2] (.GATE (dload), .D (q[2]), .Q
       (dl[2]));
  sky130_fd_sc_hvl__inv_1 g1415(.A (dl[1]), .Y (n_3));
  sky130_fd_sc_hvl__and2_1 g1418__4733(.A (READ), .B (n_0), .X (n_2));
  sky130_fd_sc_hvl__dlxtp_1 \dl_reg[1] (.GATE (dload), .D (q[1]), .Q
       (dl[1]));
  sky130_fd_sc_hvl__and2_1 g1419__6161(.A (READ), .B (dl[0]), .X (n_1));
  sky130_fd_sc_hvl__dfrtp_1 \q_reg[2] (.RESET_B (rstb), .CLK
       (data_clk), .D (q[1]), .Q (q[2]));
  sky130_fd_sc_hvl__inv_1 g1421(.A (dl[0]), .Y (n_0));
  sky130_fd_sc_hvl__dlxtp_1 \dl_reg[0] (.GATE (dload), .D (q[0]), .Q
       (dl[0]));
  sky130_fd_sc_hvl__dfrtp_1 \q_reg[1] (.RESET_B (rstb), .CLK
       (data_clk), .D (q[0]), .Q (q[1]));
  sky130_fd_sc_hvl__dfrtp_1 \q_reg[0] (.RESET_B (rstb), .CLK
       (data_clk), .D (sdi), .Q (q[0]));
  sky130_fd_sc_hvl__inv_1 g1424(.A (n_152), .Y (n_151));
  sky130_fd_sc_hvl__inv_1 g1425(.A (READ), .Y (n_152));
  sky130_fd_sc_hvl__buf_8 drc_bufs(.A (n_1), .X (ga[0]));
  sky130_fd_sc_hvl__buf_8 drc_bufs1532(.A (n_146), .X (gb[48]));
  sky130_fd_sc_hvl__buf_8 drc_bufs1535(.A (n_145), .X (ga[48]));
  sky130_fd_sc_hvl__buf_8 drc_bufs1538(.A (n_143), .X (gb[47]));
  sky130_fd_sc_hvl__buf_8 drc_bufs1541(.A (n_142), .X (ga[47]));
  sky130_fd_sc_hvl__buf_8 drc_bufs1544(.A (n_140), .X (gb[46]));
  sky130_fd_sc_hvl__buf_8 drc_bufs1547(.A (n_139), .X (ga[46]));
  sky130_fd_sc_hvl__buf_8 drc_bufs1550(.A (n_138), .X (gb[45]));
  sky130_fd_sc_hvl__buf_8 drc_bufs1553(.A (n_136), .X (ga[45]));
  sky130_fd_sc_hvl__buf_8 drc_bufs1556(.A (n_135), .X (gb[44]));
  sky130_fd_sc_hvl__buf_8 drc_bufs1559(.A (n_133), .X (ga[44]));
  sky130_fd_sc_hvl__buf_8 drc_bufs1562(.A (n_132), .X (gb[43]));
  sky130_fd_sc_hvl__buf_8 drc_bufs1565(.A (n_130), .X (ga[43]));
  sky130_fd_sc_hvl__buf_8 drc_bufs1568(.A (n_128), .X (gb[42]));
  sky130_fd_sc_hvl__buf_8 drc_bufs1571(.A (n_127), .X (ga[42]));
  sky130_fd_sc_hvl__buf_8 drc_bufs1574(.A (n_125), .X (gb[41]));
  sky130_fd_sc_hvl__buf_8 drc_bufs1577(.A (n_124), .X (ga[41]));
  sky130_fd_sc_hvl__buf_8 drc_bufs1580(.A (n_122), .X (gb[40]));
  sky130_fd_sc_hvl__buf_8 drc_bufs1583(.A (n_121), .X (ga[40]));
  sky130_fd_sc_hvl__buf_8 drc_bufs1586(.A (n_120), .X (gb[39]));
  sky130_fd_sc_hvl__buf_8 drc_bufs1589(.A (n_118), .X (ga[39]));
  sky130_fd_sc_hvl__buf_8 drc_bufs1592(.A (n_117), .X (gb[38]));
  sky130_fd_sc_hvl__buf_8 drc_bufs1595(.A (n_115), .X (ga[38]));
  sky130_fd_sc_hvl__buf_8 drc_bufs1598(.A (n_114), .X (gb[37]));
  sky130_fd_sc_hvl__buf_8 drc_bufs1601(.A (n_112), .X (ga[37]));
  sky130_fd_sc_hvl__buf_8 drc_bufs1604(.A (n_111), .X (gb[36]));
  sky130_fd_sc_hvl__buf_8 drc_bufs1607(.A (n_109), .X (ga[36]));
  sky130_fd_sc_hvl__buf_8 drc_bufs1610(.A (n_108), .X (gb[35]));
  sky130_fd_sc_hvl__buf_8 drc_bufs1613(.A (n_106), .X (ga[35]));
  sky130_fd_sc_hvl__buf_8 drc_bufs1616(.A (n_105), .X (gb[34]));
  sky130_fd_sc_hvl__buf_8 drc_bufs1619(.A (n_103), .X (ga[34]));
  sky130_fd_sc_hvl__buf_8 drc_bufs1622(.A (n_101), .X (gb[33]));
  sky130_fd_sc_hvl__buf_8 drc_bufs1625(.A (n_100), .X (ga[33]));
  sky130_fd_sc_hvl__buf_8 drc_bufs1628(.A (n_98), .X (gb[32]));
  sky130_fd_sc_hvl__buf_8 drc_bufs1631(.A (n_97), .X (ga[32]));
  sky130_fd_sc_hvl__buf_8 drc_bufs1634(.A (n_95), .X (gb[31]));
  sky130_fd_sc_hvl__buf_8 drc_bufs1637(.A (n_94), .X (ga[31]));
  sky130_fd_sc_hvl__buf_8 drc_bufs1640(.A (n_92), .X (gb[30]));
  sky130_fd_sc_hvl__buf_8 drc_bufs1643(.A (n_91), .X (ga[30]));
  sky130_fd_sc_hvl__buf_8 drc_bufs1646(.A (n_89), .X (gb[29]));
  sky130_fd_sc_hvl__buf_8 drc_bufs1649(.A (n_88), .X (ga[29]));
  sky130_fd_sc_hvl__buf_8 drc_bufs1652(.A (n_86), .X (gb[28]));
  sky130_fd_sc_hvl__buf_8 drc_bufs1655(.A (n_85), .X (ga[28]));
  sky130_fd_sc_hvl__buf_8 drc_bufs1658(.A (n_84), .X (gb[27]));
  sky130_fd_sc_hvl__buf_8 drc_bufs1661(.A (n_82), .X (ga[27]));
  sky130_fd_sc_hvl__buf_8 drc_bufs1664(.A (n_81), .X (gb[26]));
  sky130_fd_sc_hvl__buf_8 drc_bufs1667(.A (n_79), .X (ga[26]));
  sky130_fd_sc_hvl__buf_8 drc_bufs1670(.A (n_78), .X (gb[25]));
  sky130_fd_sc_hvl__buf_8 drc_bufs1673(.A (n_76), .X (ga[25]));
  sky130_fd_sc_hvl__buf_8 drc_bufs1676(.A (n_75), .X (gb[24]));
  sky130_fd_sc_hvl__buf_8 drc_bufs1679(.A (n_73), .X (ga[24]));
  sky130_fd_sc_hvl__buf_8 drc_bufs1682(.A (n_72), .X (gb[23]));
  sky130_fd_sc_hvl__buf_8 drc_bufs1685(.A (n_70), .X (ga[23]));
  sky130_fd_sc_hvl__buf_8 drc_bufs1688(.A (n_69), .X (gb[22]));
  sky130_fd_sc_hvl__buf_8 drc_bufs1691(.A (n_67), .X (ga[22]));
  sky130_fd_sc_hvl__buf_8 drc_bufs1694(.A (n_65), .X (gb[21]));
  sky130_fd_sc_hvl__buf_8 drc_bufs1697(.A (n_64), .X (ga[21]));
  sky130_fd_sc_hvl__buf_8 drc_bufs1700(.A (n_63), .X (gb[20]));
  sky130_fd_sc_hvl__buf_8 drc_bufs1703(.A (n_61), .X (ga[20]));
  sky130_fd_sc_hvl__buf_8 drc_bufs1706(.A (n_60), .X (gb[19]));
  sky130_fd_sc_hvl__buf_8 drc_bufs1709(.A (n_58), .X (ga[19]));
  sky130_fd_sc_hvl__buf_8 drc_bufs1712(.A (n_57), .X (gb[18]));
  sky130_fd_sc_hvl__buf_8 drc_bufs1715(.A (n_55), .X (ga[18]));
  sky130_fd_sc_hvl__buf_8 drc_bufs1718(.A (n_54), .X (gb[17]));
  sky130_fd_sc_hvl__buf_8 drc_bufs1721(.A (n_52), .X (ga[17]));
  sky130_fd_sc_hvl__buf_8 drc_bufs1724(.A (n_51), .X (gb[16]));
  sky130_fd_sc_hvl__buf_8 drc_bufs1727(.A (n_49), .X (ga[16]));
  sky130_fd_sc_hvl__buf_8 drc_bufs1730(.A (n_47), .X (gb[15]));
  sky130_fd_sc_hvl__buf_8 drc_bufs1733(.A (n_46), .X (ga[15]));
  sky130_fd_sc_hvl__buf_8 drc_bufs1736(.A (n_44), .X (gb[14]));
  sky130_fd_sc_hvl__buf_8 drc_bufs1739(.A (n_43), .X (ga[14]));
  sky130_fd_sc_hvl__buf_8 drc_bufs1742(.A (n_41), .X (gb[13]));
  sky130_fd_sc_hvl__buf_8 drc_bufs1745(.A (n_40), .X (ga[13]));
  sky130_fd_sc_hvl__buf_8 drc_bufs1748(.A (n_38), .X (gb[12]));
  sky130_fd_sc_hvl__buf_8 drc_bufs1751(.A (n_37), .X (ga[12]));
  sky130_fd_sc_hvl__buf_8 drc_bufs1754(.A (n_36), .X (gb[11]));
  sky130_fd_sc_hvl__buf_8 drc_bufs1757(.A (n_34), .X (ga[11]));
  sky130_fd_sc_hvl__buf_8 drc_bufs1760(.A (n_32), .X (gb[10]));
  sky130_fd_sc_hvl__buf_8 drc_bufs1763(.A (n_31), .X (ga[10]));
  sky130_fd_sc_hvl__buf_8 drc_bufs1766(.A (n_30), .X (gb[9]));
  sky130_fd_sc_hvl__buf_8 drc_bufs1769(.A (n_28), .X (ga[9]));
  sky130_fd_sc_hvl__buf_8 drc_bufs1772(.A (n_26), .X (gb[8]));
  sky130_fd_sc_hvl__buf_8 drc_bufs1775(.A (n_25), .X (ga[8]));
  sky130_fd_sc_hvl__buf_8 drc_bufs1778(.A (n_24), .X (gb[7]));
  sky130_fd_sc_hvl__buf_8 drc_bufs1781(.A (n_22), .X (ga[7]));
  sky130_fd_sc_hvl__buf_8 drc_bufs1784(.A (n_20), .X (gb[6]));
  sky130_fd_sc_hvl__buf_8 drc_bufs1787(.A (n_19), .X (ga[6]));
  sky130_fd_sc_hvl__buf_8 drc_bufs1790(.A (n_17), .X (gb[5]));
  sky130_fd_sc_hvl__buf_8 drc_bufs1793(.A (n_16), .X (ga[5]));
  sky130_fd_sc_hvl__buf_8 drc_bufs1796(.A (n_14), .X (gb[4]));
  sky130_fd_sc_hvl__buf_8 drc_bufs1799(.A (n_13), .X (ga[4]));
  sky130_fd_sc_hvl__buf_8 drc_bufs1802(.A (n_12), .X (gb[3]));
  sky130_fd_sc_hvl__buf_8 drc_bufs1805(.A (n_10), .X (ga[3]));
  sky130_fd_sc_hvl__buf_8 drc_bufs1808(.A (n_8), .X (gb[2]));
  sky130_fd_sc_hvl__buf_8 drc_bufs1811(.A (n_7), .X (ga[2]));
  sky130_fd_sc_hvl__buf_8 drc_bufs1814(.A (n_5), .X (gb[1]));
  sky130_fd_sc_hvl__buf_8 drc_bufs1817(.A (n_4), .X (ga[1]));
  sky130_fd_sc_hvl__buf_8 drc_bufs1820(.A (n_2), .X (gb[0]));
endmodule

