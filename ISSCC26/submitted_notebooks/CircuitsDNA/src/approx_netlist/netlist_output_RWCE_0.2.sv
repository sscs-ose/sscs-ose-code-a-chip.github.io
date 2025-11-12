module approxMult_signed8x8 (A, B, OUT);
  input  [7:0] A;
  input  [7:0] B;
  output [15:0] OUT;
  wire n12, n13, n14, n15, n3, n4, n5, n6, n7, v0_0, v100_0, v101_0, v102_0, v103_0, v104_0, v105_0, v106_0, v107_0, v108_0, v109_0, v10_0, v110_0, v111_0, v112_0, v113_0, v114_0, v115_0, v116_0, v117_0, v118_0, v119_0, v11_0, v120_0, v121_0, v12_0, v13_0, v14_0, v15_0, v16_0, v17_0, v18_0, v19_0, v1_0, v20_0, v21_0, v22_0, v23_0, v24_0, v25_0, v26_0, v27_0, v28_0, v29_0, v2_0, v30_0, v31_0, v32_0, v33_0, v34_0, v35_0, v36_0, v37_0, v38_0, v39_0, v3_0, v40_0, v41_0, v42_0, v43_0, v44_0, v45_0, v46_0, v47_0, v48_0, v49_0, v4_0, v50_0, v51_0, v52_0, v53_0, v54_0, v55_0, v56_0, v57_0, v58_0, v59_0, v5_0, v60_0, v61_0, v62_0, v63_0, v64_0, v65_0, v66_0, v67_0, v68_0, v69_0, v6_0, v70_0, v71_0, v72_0, v73_0, v74_0, v75_0, v76_0, v77_0, v78_0, v79_0, v7_0, v80_0, v81_0, v82_0, v83_0, v84_0, v85_0, v86_0, v87_0, v88_0, v89_0, v8_0, v90_0, v91_0, v92_0, v93_0, v94_0, v95_0, v96_0, v97_0, v98_0, v99_0, v9_0;

  // Map n0..n7 to A[0..7], n8..n15 to B[0..7]
  assign n0 = A[0];
  assign n1 = A[1];
  assign n2 = A[2];
  assign n3 = A[3];
  assign n4 = A[4];
  assign n5 = A[5];
  assign n6 = A[6];
  assign n7 = A[7];
  assign n8 = B[0];
  assign n9 = B[1];
  assign n10 = B[2];
  assign n11 = B[3];
  assign n12 = B[4];
  assign n13 = B[5];
  assign n14 = B[6];
  assign n15 = B[7];

  gf180mcu_fd_sc_mcu9t5v0__inv_1 _0001_ (
    .I(n5),
    .ZN(v0_0)
  );
  gf180mcu_fd_sc_mcu9t5v0__inv_1 _0002_ (
    .I(n4),
    .ZN(v1_0)
  );
  gf180mcu_fd_sc_mcu9t5v0__inv_1 _0003_ (
    .I(n15),
    .ZN(v2_0)
  );
  gf180mcu_fd_sc_mcu9t5v0__nand2_1 _0004_ (
    .A1(n12),
    .A2(n6),
    .ZN(v3_0)
  );
  gf180mcu_fd_sc_mcu9t5v0__inv_1 _0005_ (
    .I(n7),
    .ZN(v4_0)
  );
  gf180mcu_fd_sc_mcu9t5v0__nand2_1 _0006_ (
    .A1(n5),
    .A2(n13),
    .ZN(v5_0)
  );
  gf180mcu_fd_sc_mcu9t5v0__inv_1 _0007_ (
    .I(v4_0),
    .ZN(v6_0)
  );
  gf180mcu_fd_sc_mcu9t5v0__nand2_1 _0008_ (
    .A1(n3),
    .A2(n14),
    .ZN(v7_0)
  );
  gf180mcu_fd_sc_mcu9t5v0__or2_1 _0009_ (
    .A1(v4_0),
    .A2(n6),
    .Z(v8_0)
  );
  gf180mcu_fd_sc_mcu9t5v0__inv_1 _0010_ (
    .I(v8_0),
    .ZN(v9_0)
  );
  gf180mcu_fd_sc_mcu9t5v0__nand2_1 _0011_ (
    .A1(n5),
    .A2(n14),
    .ZN(v10_0)
  );
  gf180mcu_fd_sc_mcu9t5v0__nand2_1 _0012_ (
    .A1(v1_0),
    .A2(n15),
    .ZN(v11_0)
  );
  gf180mcu_fd_sc_mcu9t5v0__nand2_1 _0013_ (
    .A1(v10_0),
    .A2(v11_0),
    .ZN(v12_0)
  );
  gf180mcu_fd_sc_mcu9t5v0__or2_1 _0014_ (
    .A1(v3_0),
    .A2(n5),
    .Z(v13_0)
  );
  gf180mcu_fd_sc_mcu9t5v0__nand2_1 _0015_ (
    .A1(v5_0),
    .A2(v13_0),
    .ZN(v14_0)
  );
  gf180mcu_fd_sc_mcu9t5v0__xor2_1 _0016_ (
    .A1(v12_0),
    .A2(v14_0),
    .Z(v15_0)
  );
  gf180mcu_fd_sc_mcu9t5v0__inv_1 _0017_ (
    .I(v15_0),
    .ZN(v16_0)
  );
  gf180mcu_fd_sc_mcu9t5v0__or2_1 _0018_ (
    .A1(v3_0),
    .A2(v10_0),
    .Z(v17_0)
  );
  gf180mcu_fd_sc_mcu9t5v0__or2_1 _0019_ (
    .A1(v16_0),
    .A2(v17_0),
    .Z(v18_0)
  );
  gf180mcu_fd_sc_mcu9t5v0__nand2_1 _0020_ (
    .A1(v16_0),
    .A2(v17_0),
    .ZN(v19_0)
  );
  gf180mcu_fd_sc_mcu9t5v0__and2_1 _0021_ (
    .A1(v18_0),
    .A2(v19_0),
    .Z(v20_0)
  );
  gf180mcu_fd_sc_mcu9t5v0__nand2_1 _0022_ (
    .A1(n7),
    .A2(n6),
    .ZN(v21_0)
  );
  gf180mcu_fd_sc_mcu9t5v0__inv_1 _0023_ (
    .I(v21_0),
    .ZN(v22_0)
  );
  gf180mcu_fd_sc_mcu9t5v0__nand2_1 _0024_ (
    .A1(v6_0),
    .A2(n12),
    .ZN(v23_0)
  );
  gf180mcu_fd_sc_mcu9t5v0__nand2_1 _0025_ (
    .A1(v23_0),
    .A2(n7),
    .ZN(v24_0)
  );
  gf180mcu_fd_sc_mcu9t5v0__nand2_1 _0026_ (
    .A1(n13),
    .A2(n6),
    .ZN(v25_0)
  );
  gf180mcu_fd_sc_mcu9t5v0__or2_1 _0027_ (
    .A1(v24_0),
    .A2(v25_0),
    .Z(v26_0)
  );
  gf180mcu_fd_sc_mcu9t5v0__nand2_1 _0028_ (
    .A1(v24_0),
    .A2(v25_0),
    .ZN(v27_0)
  );
  gf180mcu_fd_sc_mcu9t5v0__and2_1 _0029_ (
    .A1(v26_0),
    .A2(v27_0),
    .Z(v28_0)
  );
  gf180mcu_fd_sc_mcu9t5v0__inv_1 _0030_ (
    .I(v28_0),
    .ZN(v29_0)
  );
  gf180mcu_fd_sc_mcu9t5v0__xor2_1 _0031_ (
    .A1(v29_0),
    .A2(v4_0),
    .Z(v30_0)
  );
  gf180mcu_fd_sc_mcu9t5v0__or2_1 _0032_ (
    .A1(v22_0),
    .A2(v30_0),
    .Z(v31_0)
  );
  gf180mcu_fd_sc_mcu9t5v0__nand2_1 _0033_ (
    .A1(v22_0),
    .A2(v30_0),
    .ZN(v32_0)
  );
  gf180mcu_fd_sc_mcu9t5v0__and2_1 _0034_ (
    .A1(v31_0),
    .A2(v32_0),
    .Z(v33_0)
  );
  gf180mcu_fd_sc_mcu9t5v0__xor2_1 _0035_ (
    .A1(v20_0),
    .A2(v33_0),
    .Z(v34_0)
  );
  gf180mcu_fd_sc_mcu9t5v0__xor2_1 _0036_ (
    .A1(v9_0),
    .A2(v34_0),
    .Z(v35_0)
  );
  gf180mcu_fd_sc_mcu9t5v0__inv_1 _0037_ (
    .I(v7_0),
    .ZN(v36_0)
  );
  gf180mcu_fd_sc_mcu9t5v0__or2_1 _0038_ (
    .A1(v35_0),
    .A2(v36_0),
    .Z(v37_0)
  );
  gf180mcu_fd_sc_mcu9t5v0__nand2_1 _0039_ (
    .A1(v35_0),
    .A2(v36_0),
    .ZN(v38_0)
  );
  gf180mcu_fd_sc_mcu9t5v0__and2_1 _0040_ (
    .A1(v37_0),
    .A2(v38_0),
    .Z(v39_0)
  );
  gf180mcu_fd_sc_mcu9t5v0__nand2_1 _0041_ (
    .A1(v7_0),
    .A2(n15),
    .ZN(v40_0)
  );
  gf180mcu_fd_sc_mcu9t5v0__inv_1 _0042_ (
    .I(v40_0),
    .ZN(v41_0)
  );
  gf180mcu_fd_sc_mcu9t5v0__xor2_1 _0043_ (
    .A1(v39_0),
    .A2(v41_0),
    .Z(v42_0)
  );
  gf180mcu_fd_sc_mcu9t5v0__nand2_1 _0044_ (
    .A1(v34_0),
    .A2(v9_0),
    .ZN(v43_0)
  );
  gf180mcu_fd_sc_mcu9t5v0__inv_1 _0045_ (
    .I(v43_0),
    .ZN(v44_0)
  );
  gf180mcu_fd_sc_mcu9t5v0__nand2_1 _0046_ (
    .A1(v12_0),
    .A2(v16_0),
    .ZN(v45_0)
  );
  gf180mcu_fd_sc_mcu9t5v0__nand2_1 _0047_ (
    .A1(v18_0),
    .A2(v45_0),
    .ZN(v46_0)
  );
  gf180mcu_fd_sc_mcu9t5v0__nand2_1 _0048_ (
    .A1(v31_0),
    .A2(v20_0),
    .ZN(v47_0)
  );
  gf180mcu_fd_sc_mcu9t5v0__nand2_1 _0049_ (
    .A1(v47_0),
    .A2(v32_0),
    .ZN(v48_0)
  );
  gf180mcu_fd_sc_mcu9t5v0__nand2_1 _0050_ (
    .A1(n6),
    .A2(n14),
    .ZN(v49_0)
  );
  gf180mcu_fd_sc_mcu9t5v0__nand2_1 _0051_ (
    .A1(v0_0),
    .A2(n15),
    .ZN(v50_0)
  );
  gf180mcu_fd_sc_mcu9t5v0__xor2_1 _0052_ (
    .A1(v49_0),
    .A2(v50_0),
    .Z(v51_0)
  );
  gf180mcu_fd_sc_mcu9t5v0__nand2_1 _0053_ (
    .A1(v32_0),
    .A2(v23_0),
    .ZN(v52_0)
  );
  gf180mcu_fd_sc_mcu9t5v0__xor2_1 _0054_ (
    .A1(v51_0),
    .A2(v52_0),
    .Z(v53_0)
  );
  gf180mcu_fd_sc_mcu9t5v0__inv_1 _0055_ (
    .I(v53_0),
    .ZN(v54_0)
  );
  gf180mcu_fd_sc_mcu9t5v0__inv_1 _0056_ (
    .I(v54_0),
    .ZN(v55_0)
  );
  gf180mcu_fd_sc_mcu9t5v0__nand2_1 _0057_ (
    .A1(v6_0),
    .A2(v28_0),
    .ZN(v56_0)
  );
  gf180mcu_fd_sc_mcu9t5v0__inv_1 _0058_ (
    .I(v56_0),
    .ZN(v57_0)
  );
  gf180mcu_fd_sc_mcu9t5v0__nand2_1 _0059_ (
    .A1(n13),
    .A2(n7),
    .ZN(v58_0)
  );
  gf180mcu_fd_sc_mcu9t5v0__xor2_1 _0060_ (
    .A1(v58_0),
    .A2(v24_0),
    .Z(v59_0)
  );
  gf180mcu_fd_sc_mcu9t5v0__inv_1 _0061_ (
    .I(v59_0),
    .ZN(v60_0)
  );
  gf180mcu_fd_sc_mcu9t5v0__xor2_1 _0062_ (
    .A1(v60_0),
    .A2(v4_0),
    .Z(v61_0)
  );
  gf180mcu_fd_sc_mcu9t5v0__or2_1 _0063_ (
    .A1(v57_0),
    .A2(v61_0),
    .Z(v62_0)
  );
  gf180mcu_fd_sc_mcu9t5v0__nand2_1 _0064_ (
    .A1(v57_0),
    .A2(v60_0),
    .ZN(v63_0)
  );
  gf180mcu_fd_sc_mcu9t5v0__and2_1 _0065_ (
    .A1(v62_0),
    .A2(v63_0),
    .Z(v64_0)
  );
  gf180mcu_fd_sc_mcu9t5v0__xor2_1 _0066_ (
    .A1(v53_0),
    .A2(v64_0),
    .Z(v65_0)
  );
  gf180mcu_fd_sc_mcu9t5v0__xor2_1 _0067_ (
    .A1(v48_0),
    .A2(v65_0),
    .Z(v66_0)
  );
  gf180mcu_fd_sc_mcu9t5v0__xor2_1 _0068_ (
    .A1(v46_0),
    .A2(v66_0),
    .Z(v67_0)
  );
  gf180mcu_fd_sc_mcu9t5v0__xor2_1 _0069_ (
    .A1(v44_0),
    .A2(v67_0),
    .Z(v68_0)
  );
  gf180mcu_fd_sc_mcu9t5v0__inv_1 _0070_ (
    .I(v42_0),
    .ZN(v69_0)
  );
  gf180mcu_fd_sc_mcu9t5v0__and2_1 _0071_ (
    .A1(v69_0),
    .A2(v37_0),
    .Z(v70_0)
  );
  gf180mcu_fd_sc_mcu9t5v0__xor2_1 _0072_ (
    .A1(v68_0),
    .A2(v70_0),
    .Z(v71_0)
  );
  gf180mcu_fd_sc_mcu9t5v0__nand2_1 _0073_ (
    .A1(v52_0),
    .A2(v51_0),
    .ZN(v72_0)
  );
  gf180mcu_fd_sc_mcu9t5v0__inv_1 _0074_ (
    .I(v72_0),
    .ZN(v73_0)
  );
  gf180mcu_fd_sc_mcu9t5v0__nand2_1 _0075_ (
    .A1(v64_0),
    .A2(v55_0),
    .ZN(v74_0)
  );
  gf180mcu_fd_sc_mcu9t5v0__nand2_1 _0076_ (
    .A1(v74_0),
    .A2(v63_0),
    .ZN(v75_0)
  );
  gf180mcu_fd_sc_mcu9t5v0__nand2_1 _0077_ (
    .A1(v58_0),
    .A2(v23_0),
    .ZN(v76_0)
  );
  gf180mcu_fd_sc_mcu9t5v0__inv_1 _0078_ (
    .I(v76_0),
    .ZN(v77_0)
  );
  gf180mcu_fd_sc_mcu9t5v0__nand2_1 _0079_ (
    .A1(n14),
    .A2(n7),
    .ZN(v78_0)
  );
  gf180mcu_fd_sc_mcu9t5v0__inv_1 _0080_ (
    .I(v78_0),
    .ZN(v79_0)
  );
  gf180mcu_fd_sc_mcu9t5v0__or2_1 _0081_ (
    .A1(v2_0),
    .A2(n6),
    .Z(v80_0)
  );
  gf180mcu_fd_sc_mcu9t5v0__xor2_1 _0082_ (
    .A1(v79_0),
    .A2(v80_0),
    .Z(v81_0)
  );
  gf180mcu_fd_sc_mcu9t5v0__or2_1 _0083_ (
    .A1(v77_0),
    .A2(v81_0),
    .Z(v82_0)
  );
  gf180mcu_fd_sc_mcu9t5v0__nand2_1 _0084_ (
    .A1(v77_0),
    .A2(v81_0),
    .ZN(v83_0)
  );
  gf180mcu_fd_sc_mcu9t5v0__and2_1 _0085_ (
    .A1(v82_0),
    .A2(v83_0),
    .Z(v84_0)
  );
  gf180mcu_fd_sc_mcu9t5v0__inv_1 _0086_ (
    .I(v84_0),
    .ZN(v85_0)
  );
  gf180mcu_fd_sc_mcu9t5v0__or2_1 _0087_ (
    .A1(v51_0),
    .A2(v49_0),
    .Z(v86_0)
  );
  gf180mcu_fd_sc_mcu9t5v0__or2_1 _0088_ (
    .A1(v85_0),
    .A2(v86_0),
    .Z(v87_0)
  );
  gf180mcu_fd_sc_mcu9t5v0__nand2_1 _0089_ (
    .A1(v85_0),
    .A2(v86_0),
    .ZN(v88_0)
  );
  gf180mcu_fd_sc_mcu9t5v0__and2_1 _0090_ (
    .A1(v87_0),
    .A2(v88_0),
    .Z(v89_0)
  );
  gf180mcu_fd_sc_mcu9t5v0__xor2_1 _0091_ (
    .A1(v6_0),
    .A2(v89_0),
    .Z(v90_0)
  );
  gf180mcu_fd_sc_mcu9t5v0__xor2_1 _0092_ (
    .A1(v75_0),
    .A2(v90_0),
    .Z(v91_0)
  );
  gf180mcu_fd_sc_mcu9t5v0__xor2_1 _0093_ (
    .A1(v73_0),
    .A2(v91_0),
    .Z(v92_0)
  );
  gf180mcu_fd_sc_mcu9t5v0__nand2_1 _0094_ (
    .A1(v66_0),
    .A2(v46_0),
    .ZN(v93_0)
  );
  gf180mcu_fd_sc_mcu9t5v0__nand2_1 _0095_ (
    .A1(v65_0),
    .A2(v48_0),
    .ZN(v94_0)
  );
  gf180mcu_fd_sc_mcu9t5v0__nand2_1 _0096_ (
    .A1(v93_0),
    .A2(v94_0),
    .ZN(v95_0)
  );
  gf180mcu_fd_sc_mcu9t5v0__or2_1 _0097_ (
    .A1(v92_0),
    .A2(v95_0),
    .Z(v96_0)
  );
  gf180mcu_fd_sc_mcu9t5v0__nand2_1 _0098_ (
    .A1(v92_0),
    .A2(v95_0),
    .ZN(v97_0)
  );
  gf180mcu_fd_sc_mcu9t5v0__and2_1 _0099_ (
    .A1(v96_0),
    .A2(v97_0),
    .Z(v98_0)
  );
  gf180mcu_fd_sc_mcu9t5v0__nand2_1 _0100_ (
    .A1(v70_0),
    .A2(v67_0),
    .ZN(v99_0)
  );
  gf180mcu_fd_sc_mcu9t5v0__nand2_1 _0101_ (
    .A1(v67_0),
    .A2(v44_0),
    .ZN(v100_0)
  );
  gf180mcu_fd_sc_mcu9t5v0__nand2_1 _0102_ (
    .A1(v99_0),
    .A2(v100_0),
    .ZN(v101_0)
  );
  gf180mcu_fd_sc_mcu9t5v0__xor2_1 _0103_ (
    .A1(v98_0),
    .A2(v101_0),
    .Z(v102_0)
  );
  gf180mcu_fd_sc_mcu9t5v0__inv_1 _0104_ (
    .I(v82_0),
    .ZN(v103_0)
  );
  gf180mcu_fd_sc_mcu9t5v0__or2_1 _0105_ (
    .A1(v2_0),
    .A2(n7),
    .Z(v104_0)
  );
  gf180mcu_fd_sc_mcu9t5v0__nand2_1 _0106_ (
    .A1(v82_0),
    .A2(v104_0),
    .ZN(v105_0)
  );
  gf180mcu_fd_sc_mcu9t5v0__xor2_1 _0107_ (
    .A1(v105_0),
    .A2(v76_0),
    .Z(v106_0)
  );
  gf180mcu_fd_sc_mcu9t5v0__xor2_1 _0108_ (
    .A1(v106_0),
    .A2(v6_0),
    .Z(v107_0)
  );
  gf180mcu_fd_sc_mcu9t5v0__nand2_1 _0109_ (
    .A1(v89_0),
    .A2(v6_0),
    .ZN(v108_0)
  );
  gf180mcu_fd_sc_mcu9t5v0__inv_1 _0110_ (
    .I(v108_0),
    .ZN(v109_0)
  );
  gf180mcu_fd_sc_mcu9t5v0__xor2_1 _0111_ (
    .A1(v107_0),
    .A2(v109_0),
    .Z(v110_0)
  );
  gf180mcu_fd_sc_mcu9t5v0__xor2_1 _0112_ (
    .A1(v103_0),
    .A2(v110_0),
    .Z(v111_0)
  );
  gf180mcu_fd_sc_mcu9t5v0__nand2_1 _0113_ (
    .A1(v90_0),
    .A2(v55_0),
    .ZN(v112_0)
  );
  gf180mcu_fd_sc_mcu9t5v0__inv_1 _0114_ (
    .I(v112_0),
    .ZN(v113_0)
  );
  gf180mcu_fd_sc_mcu9t5v0__nand2_1 _0115_ (
    .A1(v101_0),
    .A2(v96_0),
    .ZN(v114_0)
  );
  gf180mcu_fd_sc_mcu9t5v0__nand2_1 _0116_ (
    .A1(v114_0),
    .A2(v97_0),
    .ZN(v115_0)
  );
  gf180mcu_fd_sc_mcu9t5v0__nand2_1 _0117_ (
    .A1(v115_0),
    .A2(n15),
    .ZN(v116_0)
  );
  gf180mcu_fd_sc_mcu9t5v0__nand2_1 _0118_ (
    .A1(v113_0),
    .A2(v81_0),
    .ZN(v117_0)
  );
  gf180mcu_fd_sc_mcu9t5v0__inv_1 _0119_ (
    .I(v111_0),
    .ZN(v118_0)
  );
  gf180mcu_fd_sc_mcu9t5v0__nand2_1 _0120_ (
    .A1(v118_0),
    .A2(v78_0),
    .ZN(v119_0)
  );
  gf180mcu_fd_sc_mcu9t5v0__and2_1 _0121_ (
    .A1(v117_0),
    .A2(v119_0),
    .Z(v120_0)
  );
  gf180mcu_fd_sc_mcu9t5v0__and2_1 _0122_ (
    .A1(v116_0),
    .A2(v120_0),
    .Z(v121_0)
  );

  assign OUT[0] = v96_0;
  assign OUT[1] = n3;
  assign OUT[2] = v102_0;
  assign OUT[3] = n4;
  assign OUT[4] = v73_0;
  assign OUT[5] = v56_0;
  assign OUT[6] = v86_0;
  assign OUT[7] = v47_0;
  assign OUT[8] = v48_0;
  assign OUT[9] = n4;
  assign OUT[10] = v6_0;
  assign OUT[11] = v42_0;
  assign OUT[12] = v71_0;
  assign OUT[13] = v102_0;
  assign OUT[14] = v121_0;
  assign OUT[15] = v121_0;
endmodule
