
// Generated on: Oct 28 2026 01:28:56 CDT (Oct 28 2026 06:28:56 UTC)

// Verification Directory fv/glob_dig 

module glob_dig(sck, sdi, sld, rst, data_clk_f, data_clk_n, row1_clk_f,
     row1_clk_n, row2_clk_f, row2_clk_n, col1_clk_f, col1_clk_n,
     col2_clk_f, col2_clk_n, rstb_f, rstb_n, READ_f, READ_n, READb_f,
     READb_n, PROG_f, PROG_n, VER_f, VER_n, SENSE_f, SENSE_n, WRANY_f,
     WRANY_n, dload_f, dload_n, pol_f, pol_n, rd_out_f, rd_out_n,
     rd_out_b_f, rd_out_b_n);
  input sck, sdi, sld, rst;
  output data_clk_f, data_clk_n, row1_clk_f, row1_clk_n, row2_clk_f,
       row2_clk_n, col1_clk_f, col1_clk_n, col2_clk_f, col2_clk_n,
       rstb_f, rstb_n, READ_f, READ_n, READb_f, READb_n, PROG_f,
       PROG_n, VER_f, VER_n, SENSE_f, SENSE_n, WRANY_f, WRANY_n,
       dload_f, dload_n, pol_f, pol_n, rd_out_f, rd_out_n, rd_out_b_f,
       rd_out_b_n;
  wire sck, sdi, sld, rst;
  wire data_clk_f, data_clk_n, row1_clk_f, row1_clk_n, row2_clk_f,
       row2_clk_n, col1_clk_f, col1_clk_n, col2_clk_f, col2_clk_n,
       rstb_f, rstb_n, READ_f, READ_n, READb_f, READb_n, PROG_f,
       PROG_n, VER_f, VER_n, SENSE_f, SENSE_n, WRANY_f, WRANY_n,
       dload_f, dload_n, pol_f, pol_n, rd_out_f, rd_out_n, rd_out_b_f,
       rd_out_b_n;
  wire [11:0] cfg;
  wire [11:0] cq;
  wire PROG, SENSE, VER, WRANY, n_1, n_2, n_3, n_4;
  wire n_5, n_6, n_7, n_44, rstb, sck_r, sldb, u_ck_col1_nb;
  wire u_ck_col1_nf, u_ck_col1_nn, u_ck_col1_p, u_ck_col2_nb,
       u_ck_col2_nf, u_ck_col2_nn, u_ck_col2_p, u_ck_data_nb;
  wire u_ck_data_nf, u_ck_data_nn, u_ck_data_p, u_ck_row1_nb,
       u_ck_row1_nf, u_ck_row1_nn, u_ck_row1_p, u_ck_row2_nb;
  wire u_ck_row2_nf, u_ck_row2_nn, u_ck_row2_p;
  sky130_fd_sc_hvl__inv_1 g79(.A (n_44), .Y (n_7));
  sky130_fd_sc_hvl__inv_1 g78(.A (cfg[5]), .Y (n_6));
  sky130_fd_sc_hvl__inv_1 g80(.A (rst), .Y (rstb));
  sky130_fd_sc_hvl__inv_1 g75(.A (sld), .Y (sldb));
  sky130_fd_sc_hvl__dlxtp_1 \cfg_reg[11] (.GATE (sldb), .D (cq[11]), .Q
       (cfg[11]));
  sky130_fd_sc_hvl__dfrtp_1 \cq_reg[11] (.RESET_B (rstb), .CLK (n_5),
       .D (cq[10]), .Q (cq[11]));
  sky130_fd_sc_hvl__dlxtp_1 \cfg_reg[10] (.GATE (sldb), .D (cq[10]), .Q
       (cfg[10]));
  sky130_fd_sc_hvl__dfrtp_1 \cq_reg[10] (.RESET_B (rstb), .CLK (n_5),
       .D (cq[9]), .Q (cq[10]));
  sky130_fd_sc_hvl__dlxtp_1 \cfg_reg[9] (.GATE (sldb), .D (cq[9]), .Q
       (cfg[9]));
  sky130_fd_sc_hvl__dfrtp_1 \cq_reg[9] (.RESET_B (rstb), .CLK (n_5), .D
       (cq[8]), .Q (cq[9]));
  sky130_fd_sc_hvl__dlxtp_1 \cfg_reg[8] (.GATE (sldb), .D (cq[8]), .Q
       (cfg[8]));
  sky130_fd_sc_hvl__dfrtp_1 \cq_reg[8] (.RESET_B (rstb), .CLK (n_5), .D
       (cq[7]), .Q (cq[8]));
  sky130_fd_sc_hvl__dlxtp_1 \cfg_reg[7] (.GATE (sldb), .D (cq[7]), .Q
       (cfg[7]));
  sky130_fd_sc_hvl__dfrtp_1 \cq_reg[7] (.RESET_B (rstb), .CLK (n_5), .D
       (cq[6]), .Q (cq[7]));
  sky130_fd_sc_hvl__dlxtp_1 \cfg_reg[6] (.GATE (sldb), .D (cq[6]), .Q
       (cfg[6]));
  sky130_fd_sc_hvl__or2_1 g138__2398(.A (VER), .B (PROG), .X (WRANY));
  sky130_fd_sc_hvl__dlxtp_1 \cfg_reg[5] (.GATE (sldb), .D (cq[5]), .Q
       (cfg[5]));
  sky130_fd_sc_hvl__dfrtp_1 \cq_reg[6] (.RESET_B (rstb), .CLK (n_5), .D
       (cq[5]), .Q (cq[6]));
  sky130_fd_sc_hvl__nor2_1 g141__5107(.A (n_4), .B (n_44), .Y (SENSE));
  sky130_fd_sc_hvl__o22ai_1 g142__6260(.A1 (cfg[1]), .A2 (n_3), .B1
       (cfg[0]), .B2 (n_1), .Y (PROG));
  sky130_fd_sc_hvl__dfrtp_1 \cq_reg[5] (.RESET_B (rstb), .CLK (n_5), .D
       (cq[4]), .Q (cq[5]));
  sky130_fd_sc_hvl__inv_1 g144(.A (cfg[4]), .Y (n_4));
  sky130_fd_sc_hvl__dlxtp_1 \cfg_reg[4] (.GATE (sldb), .D (cq[4]), .Q
       (cfg[4]));
  sky130_fd_sc_hvl__and3_1 g146__4319(.A (n_1), .B (cfg[0]), .C
       (cfg[2]), .X (VER));
  sky130_fd_sc_hvl__dfrtp_1 \cq_reg[4] (.RESET_B (rstb), .CLK (n_5), .D
       (cq[3]), .Q (cq[4]));
  sky130_fd_sc_hvl__dlxtp_1 \cfg_reg[3] (.GATE (sldb), .D (cq[3]), .Q
       (cfg[3]));
  sky130_fd_sc_hvl__nand2_1 g149__8428(.A (cfg[0]), .B (n_2), .Y (n_3));
  sky130_fd_sc_hvl__dfrtp_1 \cq_reg[3] (.RESET_B (rstb), .CLK (n_5), .D
       (cq[2]), .Q (cq[3]));
  sky130_fd_sc_hvl__inv_1 g151(.A (cfg[2]), .Y (n_2));
  sky130_fd_sc_hvl__dlxtp_1 \cfg_reg[2] (.GATE (sldb), .D (cq[2]), .Q
       (cfg[2]));
  sky130_fd_sc_hvl__nand2_1 g153__5526(.A (cfg[1]), .B (cfg[0]), .Y
       (n_44));
  sky130_fd_sc_hvl__dfrtp_1 \cq_reg[2] (.RESET_B (rstb), .CLK (n_5), .D
       (cq[1]), .Q (cq[2]));
  sky130_fd_sc_hvl__inv_1 g155(.A (cfg[1]), .Y (n_1));
  sky130_fd_sc_hvl__dlxtp_1 \cfg_reg[1] (.GATE (sldb), .D (cq[1]), .Q
       (cfg[1]));
  sky130_fd_sc_hvl__dfrtp_1 \cq_reg[1] (.RESET_B (rstb), .CLK (n_5), .D
       (cq[0]), .Q (cq[1]));
  sky130_fd_sc_hvl__dlxtp_1 \cfg_reg[0] (.GATE (sldb), .D (cq[0]), .Q
       (cfg[0]));
  sky130_fd_sc_hvl__dfrtp_1 \cq_reg[0] (.RESET_B (rstb), .CLK (n_5), .D
       (sdi), .Q (cq[0]));
  sky130_fd_sc_hvl__and2_1 g160__6783(.A (sck), .B (sldb), .X (sck_r));
  sky130_fd_sc_hvl__and2_1 g161__3680(.A (sck), .B (sld), .X (n_5));
  sky130_fd_sc_hvl__inv_2 u_ck_col1_u_i0(.A (u_ck_col1_nb), .Y
       (u_ck_col1_p));
  sky130_fd_sc_hvl__inv_4 u_ck_col1_u_if1(.A (u_ck_col1_p), .Y
       (u_ck_col1_nf));
  sky130_fd_sc_hvl__inv_8 u_ck_col1_u_if2(.A (u_ck_col1_nf), .Y
       (col1_clk_f));
  sky130_fd_sc_hvl__inv_4 u_ck_col1_u_in1(.A (u_ck_col1_p), .Y
       (u_ck_col1_nn));
  sky130_fd_sc_hvl__inv_8 u_ck_col1_u_in2(.A (u_ck_col1_nn), .Y
       (col1_clk_n));
  sky130_fd_sc_hvl__nand2_1 u_ck_col1_u_nd(.A (sck_r), .B (cfg[10]), .Y
       (u_ck_col1_nb));
  sky130_fd_sc_hvl__inv_2 u_ck_col2_u_i0(.A (u_ck_col2_nb), .Y
       (u_ck_col2_p));
  sky130_fd_sc_hvl__inv_4 u_ck_col2_u_if1(.A (u_ck_col2_p), .Y
       (u_ck_col2_nf));
  sky130_fd_sc_hvl__inv_8 u_ck_col2_u_if2(.A (u_ck_col2_nf), .Y
       (col2_clk_f));
  sky130_fd_sc_hvl__inv_4 u_ck_col2_u_in1(.A (u_ck_col2_p), .Y
       (u_ck_col2_nn));
  sky130_fd_sc_hvl__inv_8 u_ck_col2_u_in2(.A (u_ck_col2_nn), .Y
       (col2_clk_n));
  sky130_fd_sc_hvl__nand2_1 u_ck_col2_u_nd(.A (sck_r), .B (cfg[11]), .Y
       (u_ck_col2_nb));
  sky130_fd_sc_hvl__inv_2 u_ck_data_u_i0(.A (u_ck_data_nb), .Y
       (u_ck_data_p));
  sky130_fd_sc_hvl__inv_4 u_ck_data_u_if1(.A (u_ck_data_p), .Y
       (u_ck_data_nf));
  sky130_fd_sc_hvl__inv_8 u_ck_data_u_if2(.A (u_ck_data_nf), .Y
       (data_clk_f));
  sky130_fd_sc_hvl__inv_4 u_ck_data_u_in1(.A (u_ck_data_p), .Y
       (u_ck_data_nn));
  sky130_fd_sc_hvl__inv_8 u_ck_data_u_in2(.A (u_ck_data_nn), .Y
       (data_clk_n));
  sky130_fd_sc_hvl__nand2_1 u_ck_data_u_nd(.A (sck_r), .B (cfg[7]), .Y
       (u_ck_data_nb));
  sky130_fd_sc_hvl__inv_2 u_ck_row1_u_i0(.A (u_ck_row1_nb), .Y
       (u_ck_row1_p));
  sky130_fd_sc_hvl__inv_4 u_ck_row1_u_if1(.A (u_ck_row1_p), .Y
       (u_ck_row1_nf));
  sky130_fd_sc_hvl__inv_8 u_ck_row1_u_if2(.A (u_ck_row1_nf), .Y
       (row1_clk_f));
  sky130_fd_sc_hvl__inv_4 u_ck_row1_u_in1(.A (u_ck_row1_p), .Y
       (u_ck_row1_nn));
  sky130_fd_sc_hvl__inv_8 u_ck_row1_u_in2(.A (u_ck_row1_nn), .Y
       (row1_clk_n));
  sky130_fd_sc_hvl__nand2_1 u_ck_row1_u_nd(.A (sck_r), .B (cfg[8]), .Y
       (u_ck_row1_nb));
  sky130_fd_sc_hvl__inv_2 u_ck_row2_u_i0(.A (u_ck_row2_nb), .Y
       (u_ck_row2_p));
  sky130_fd_sc_hvl__inv_4 u_ck_row2_u_if1(.A (u_ck_row2_p), .Y
       (u_ck_row2_nf));
  sky130_fd_sc_hvl__inv_8 u_ck_row2_u_if2(.A (u_ck_row2_nf), .Y
       (row2_clk_f));
  sky130_fd_sc_hvl__inv_4 u_ck_row2_u_in1(.A (u_ck_row2_p), .Y
       (u_ck_row2_nn));
  sky130_fd_sc_hvl__inv_8 u_ck_row2_u_in2(.A (u_ck_row2_nn), .Y
       (row2_clk_n));
  sky130_fd_sc_hvl__nand2_1 u_ck_row2_u_nd(.A (sck_r), .B (cfg[9]), .Y
       (u_ck_row2_nb));
  sky130_fd_sc_hvl__buf_4 u_ob_dload_u_f(.A (cfg[6]), .X (dload_f));
  sky130_fd_sc_hvl__buf_4 u_ob_dload_u_n(.A (cfg[6]), .X (dload_n));
  sky130_fd_sc_hvl__buf_4 u_ob_pol_u_f(.A (cfg[3]), .X (pol_f));
  sky130_fd_sc_hvl__buf_4 u_ob_pol_u_n(.A (cfg[3]), .X (pol_n));
  sky130_fd_sc_hvl__buf_4 u_ob_prog_u_f(.A (PROG), .X (PROG_f));
  sky130_fd_sc_hvl__buf_4 u_ob_prog_u_n(.A (PROG), .X (PROG_n));
  sky130_fd_sc_hvl__buf_4 u_ob_rdout_u_f(.A (cfg[5]), .X (rd_out_f));
  sky130_fd_sc_hvl__buf_4 u_ob_rdout_u_n(.A (cfg[5]), .X (rd_out_n));
  sky130_fd_sc_hvl__buf_4 u_ob_rdoutb_u_f(.A (n_6), .X (rd_out_b_f));
  sky130_fd_sc_hvl__buf_4 u_ob_rdoutb_u_n(.A (n_6), .X (rd_out_b_n));
  sky130_fd_sc_hvl__buf_4 u_ob_read_u_f(.A (n_7), .X (READ_f));
  sky130_fd_sc_hvl__buf_4 u_ob_read_u_n(.A (n_7), .X (READ_n));
  sky130_fd_sc_hvl__buf_4 u_ob_readb_u_f(.A (n_44), .X (READb_f));
  sky130_fd_sc_hvl__buf_4 u_ob_readb_u_n(.A (n_44), .X (READb_n));
  sky130_fd_sc_hvl__buf_8 u_ob_rstb_u_f(.A (rstb), .X (rstb_f));
  sky130_fd_sc_hvl__buf_8 u_ob_rstb_u_n(.A (rstb), .X (rstb_n));
  sky130_fd_sc_hvl__buf_4 u_ob_sense_u_f(.A (SENSE), .X (SENSE_f));
  sky130_fd_sc_hvl__buf_4 u_ob_sense_u_n(.A (SENSE), .X (SENSE_n));
  sky130_fd_sc_hvl__buf_4 u_ob_ver_u_f(.A (VER), .X (VER_f));
  sky130_fd_sc_hvl__buf_4 u_ob_ver_u_n(.A (VER), .X (VER_n));
  sky130_fd_sc_hvl__buf_4 u_ob_wrany_u_f(.A (WRANY), .X (WRANY_f));
  sky130_fd_sc_hvl__buf_4 u_ob_wrany_u_n(.A (WRANY), .X (WRANY_n));
endmodule

