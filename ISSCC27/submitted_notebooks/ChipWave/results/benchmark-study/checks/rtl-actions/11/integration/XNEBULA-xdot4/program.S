lui x22, 0x80020
addi x22, x22, 0
lui x20, 0x80010
addi x20, x20, 0
lui x10, 0x80808
addi x10, x10, 128
lui x11, 0x80808
addi x11, x11, 128
sw x10, 0(x20)
lw x10, x20, 0
xdot4 x5, x0, x11
add x8, x5, x0
xdot4 x9, x8, x0
beq x9, x0, valid_0
jal x0, bad
valid_0:
sw x8, 0(x22)
jal x0, skip_0
xdot4 x8, x10, x11
sw x8, 0(x22)
skip_0:
lui x10, 0x80808
addi x10, x10, 128
lui x11, 0x7f7f8
addi x11, x11, -129
xdot4 x10, x10, x11
add x8, x10, x0
xdot4 x9, x8, x0
beq x9, x0, valid_1
jal x0, bad
valid_1:
sw x8, 4(x22)
jal x0, skip_1
xdot4 x8, x10, x11
sw x8, 4(x22)
skip_1:
lui x10, 0x4030
addi x10, x10, 513
lui x11, 0x1020
addi x11, x11, 772
xdot4 x11, x10, x11
add x8, x11, x0
xdot4 x9, x8, x0
beq x9, x0, valid_2
jal x0, bad
valid_2:
sw x8, 8(x22)
jal x0, skip_2
xdot4 x8, x10, x11
sw x8, 8(x22)
skip_2:
lui x10, 0x9c3ec
addi x10, x10, -1104
lui x11, 0x7506f
addi x11, x11, -1782
xdot4 x0, x10, x11
addi x8, x0, 37
sw x8, 12(x22)
jal x0, skip_3
xdot4 x8, x10, x11
sw x8, 12(x22)
skip_3:
lui x10, 0x31809
addi x10, x10, -2017
lui x11, 0x932bb
addi x11, x11, 1414
xdot4 x5, x10, x11
add x8, x5, x0
xdot4 x9, x8, x0
beq x9, x0, valid_4
jal x0, bad
valid_4:
sw x8, 16(x22)
jal x0, skip_4
xdot4 x8, x10, x11
sw x8, 16(x22)
skip_4:
lui x10, 0xe10bf
addi x10, x10, -745
lui x11, 0xf56f6
addi x11, x11, 1236
sw x10, 0(x20)
lw x10, x20, 0
xdot4 x10, x10, x11
add x8, x10, x0
xdot4 x9, x8, x0
beq x9, x0, valid_5
jal x0, bad
valid_5:
sw x8, 20(x22)
jal x0, skip_5
xdot4 x8, x10, x11
sw x8, 20(x22)
skip_5:
lui x10, 0xe9404
addi x10, x10, 71
lui x11, 0xb4ade
addi x11, x11, 674
xdot4 x11, x10, x11
add x8, x11, x0
xdot4 x9, x8, x0
beq x9, x0, valid_6
jal x0, bad
valid_6:
sw x8, 24(x22)
jal x0, skip_6
xdot4 x8, x10, x11
sw x8, 24(x22)
skip_6:
lui x10, 0x53f2e
addi x10, x10, -806
lui x11, 0xf4930
addi x11, x11, 1249
xdot4 x0, x10, x11
addi x8, x0, 37
sw x8, 28(x22)
jal x0, skip_7
xdot4 x8, x10, x11
sw x8, 28(x22)
skip_7:
lui x10, 0x793fd
addi x10, x10, 1009
lui x11, 0x18d3a
addi x11, x11, 1459
xdot4 x5, x10, x11
add x8, x5, x0
xdot4 x9, x8, x0
beq x9, x0, valid_8
jal x0, bad
valid_8:
sw x8, 32(x22)
jal x0, skip_8
xdot4 x8, x10, x11
sw x8, 32(x22)
skip_8:
lui x10, 0x6a3bd
addi x10, x10, 1577
lui x11, 0x9f754
addi x11, x11, 494
xdot4 x10, x10, x11
add x8, x10, x0
xdot4 x9, x8, x0
beq x9, x0, valid_9
jal x0, bad
valid_9:
sw x8, 36(x22)
jal x0, skip_9
xdot4 x8, x10, x11
sw x8, 36(x22)
skip_9:
lui x10, 0x9e479
addi x10, x10, -1418
lui x11, 0xb6122
addi x11, x11, -798
sw x10, 0(x20)
lw x10, x20, 0
xdot4 x11, x10, x11
add x8, x11, x0
xdot4 x9, x8, x0
beq x9, x0, valid_10
jal x0, bad
valid_10:
sw x8, 40(x22)
jal x0, skip_10
xdot4 x8, x10, x11
sw x8, 40(x22)
skip_10:
lui x10, 0x9825f
addi x10, x10, -1936
lui x11, 0xdabb
addi x11, x11, -1063
xdot4 x0, x10, x11
addi x8, x0, 37
sw x8, 44(x22)
jal x0, skip_11
xdot4 x8, x10, x11
sw x8, 44(x22)
skip_11:
lui x10, 0xd3dda
addi x10, x10, 948
lui x11, 0xb89c5
addi x11, x11, -594
xdot4 x5, x10, x11
add x8, x5, x0
xdot4 x9, x8, x0
beq x9, x0, valid_12
jal x0, bad
valid_12:
sw x8, 48(x22)
jal x0, skip_12
xdot4 x8, x10, x11
sw x8, 48(x22)
skip_12:
lui x10, 0xe1d17
addi x10, x10, -431
lui x11, 0x3caca
addi x11, x11, 1869
xdot4 x10, x10, x11
add x8, x10, x0
xdot4 x9, x8, x0
beq x9, x0, valid_13
jal x0, bad
valid_13:
sw x8, 52(x22)
jal x0, skip_13
xdot4 x8, x10, x11
sw x8, 52(x22)
skip_13:
lui x10, 0xd7517
addi x10, x10, -368
lui x11, 0x964d6
addi x11, x11, 1591
xdot4 x11, x10, x11
add x8, x11, x0
xdot4 x9, x8, x0
beq x9, x0, valid_14
jal x0, bad
valid_14:
sw x8, 56(x22)
jal x0, skip_14
xdot4 x8, x10, x11
sw x8, 56(x22)
skip_14:
lui x10, 0x12db3
addi x10, x10, 1038
lui x11, 0x4caa
addi x11, x11, -235
sw x10, 0(x20)
lw x10, x20, 0
xdot4 x0, x10, x11
addi x8, x0, 37
sw x8, 60(x22)
jal x0, skip_15
xdot4 x8, x10, x11
sw x8, 60(x22)
skip_15:
lui x10, 0x38a2e
addi x10, x10, -1395
lui x11, 0xb82cb
addi x11, x11, -1054
xdot4 x5, x10, x11
add x8, x5, x0
xdot4 x9, x8, x0
beq x9, x0, valid_16
jal x0, bad
valid_16:
sw x8, 64(x22)
jal x0, skip_16
xdot4 x8, x10, x11
sw x8, 64(x22)
skip_16:
lui x10, 0xba09a
addi x10, x10, 375
lui x11, 0x92fac
addi x11, x11, 1268
xdot4 x10, x0, x11
add x8, x10, x0
xdot4 x9, x8, x0
beq x9, x0, valid_17
jal x0, bad
valid_17:
sw x8, 68(x22)
jal x0, skip_17
xdot4 x8, x10, x11
sw x8, 68(x22)
skip_17:
lui x10, 0xd2e3b
addi x10, x10, -839
lui x11, 0x8e547
addi x11, x11, -1628
xdot4 x11, x10, x11
add x8, x11, x0
xdot4 x9, x8, x0
beq x9, x0, valid_18
jal x0, bad
valid_18:
sw x8, 72(x22)
jal x0, skip_18
xdot4 x8, x10, x11
sw x8, 72(x22)
skip_18:
lui x10, 0x1abfa
addi x10, x10, -1002
lui x11, 0xfd31b
addi x11, x11, 1484
xdot4 x0, x10, x11
addi x8, x0, 37
sw x8, 76(x22)
jal x0, skip_19
xdot4 x8, x10, x11
sw x8, 76(x22)
skip_19:
lui x10, 0x3ffb3
addi x10, x10, -1518
lui x11, 0x999a5
addi x11, x11, 509
sw x10, 0(x20)
lw x10, x20, 0
xdot4 x5, x10, x11
add x8, x5, x0
xdot4 x9, x8, x0
beq x9, x0, valid_20
jal x0, bad
valid_20:
sw x8, 80(x22)
jal x0, skip_20
xdot4 x8, x10, x11
sw x8, 80(x22)
skip_20:
lui x10, 0x21014
addi x10, x10, -2016
lui x11, 0x336fd
addi x11, x11, -1004
xdot4 x10, x10, x11
add x8, x10, x0
xdot4 x9, x8, x0
beq x9, x0, valid_21
jal x0, bad
valid_21:
sw x8, 84(x22)
jal x0, skip_21
xdot4 x8, x10, x11
sw x8, 84(x22)
skip_21:
lui x10, 0x73aaf
addi x10, x10, 1433
lui x11, 0x7d4a1
addi x11, x11, -1432
xdot4 x11, x10, x11
add x8, x11, x0
xdot4 x9, x8, x0
beq x9, x0, valid_22
jal x0, bad
valid_22:
sw x8, 88(x22)
jal x0, skip_22
xdot4 x8, x10, x11
sw x8, 88(x22)
skip_22:
lui x10, 0xba487
addi x10, x10, 528
lui x11, 0x27317
addi x11, x11, 558
xdot4 x0, x10, x11
addi x8, x0, 37
sw x8, 92(x22)
jal x0, skip_23
xdot4 x8, x10, x11
sw x8, 92(x22)
skip_23:
lui x10, 0xbf3f
addi x10, x10, 531
lui x11, 0x23a39
addi x11, x11, -353
xdot4 x5, x10, x11
add x8, x5, x0
xdot4 x9, x8, x0
beq x9, x0, valid_24
jal x0, bad
valid_24:
sw x8, 96(x22)
jal x0, skip_24
xdot4 x8, x10, x11
sw x8, 96(x22)
skip_24:
lui x10, 0xac37f
addi x10, x10, -801
lui x11, 0xad591
addi x11, x11, 790
sw x10, 0(x20)
lw x10, x20, 0
xdot4 x10, x10, x11
add x8, x10, x0
xdot4 x9, x8, x0
beq x9, x0, valid_25
jal x0, bad
valid_25:
sw x8, 100(x22)
jal x0, skip_25
xdot4 x8, x10, x11
sw x8, 100(x22)
skip_25:
lui x10, 0x396a5
addi x10, x10, -388
lui x11, 0x2e2a5
addi x11, x11, -851
xdot4 x11, x10, x11
add x8, x11, x0
xdot4 x9, x8, x0
beq x9, x0, valid_26
jal x0, bad
valid_26:
sw x8, 104(x22)
jal x0, skip_26
xdot4 x8, x10, x11
sw x8, 104(x22)
skip_26:
lui x10, 0x95f46
addi x10, x10, -268
lui x11, 0xe3609
addi x11, x11, -1324
xdot4 x0, x10, x11
addi x8, x0, 37
sw x8, 108(x22)
jal x0, skip_27
xdot4 x8, x10, x11
sw x8, 108(x22)
skip_27:
lui x10, 0x9bcad
addi x10, x10, -1378
lui x11, 0xbee99
addi x11, x11, -1058
xdot4 x5, x10, x11
add x8, x5, x0
xdot4 x9, x8, x0
beq x9, x0, valid_28
jal x0, bad
valid_28:
sw x8, 112(x22)
jal x0, skip_28
xdot4 x8, x10, x11
sw x8, 112(x22)
skip_28:
lui x10, 0x5353e
addi x10, x10, -788
lui x11, 0x659b2
addi x11, x11, 1428
xdot4 x10, x10, x11
add x8, x10, x0
xdot4 x9, x8, x0
beq x9, x0, valid_29
jal x0, bad
valid_29:
sw x8, 116(x22)
jal x0, skip_29
xdot4 x8, x10, x11
sw x8, 116(x22)
skip_29:
lui x10, 0x6ad54
addi x10, x10, -1832
lui x11, 0xc18c0
addi x11, x11, -447
sw x10, 0(x20)
lw x10, x20, 0
xdot4 x11, x10, x11
add x8, x11, x0
xdot4 x9, x8, x0
beq x9, x0, valid_30
jal x0, bad
valid_30:
sw x8, 120(x22)
jal x0, skip_30
xdot4 x8, x10, x11
sw x8, 120(x22)
skip_30:
lui x10, 0xac387
addi x10, x10, -518
lui x11, 0x56e79
addi x11, x11, -421
xdot4 x0, x10, x11
addi x8, x0, 37
sw x8, 124(x22)
jal x0, skip_31
xdot4 x8, x10, x11
sw x8, 124(x22)
skip_31:
lui x10, 0xba1f4
addi x10, x10, 266
lui x11, 0xb7239
addi x11, x11, -1253
xdot4 x5, x10, x11
add x8, x5, x0
xdot4 x9, x8, x0
beq x9, x0, valid_32
jal x0, bad
valid_32:
sw x8, 128(x22)
jal x0, skip_32
xdot4 x8, x10, x11
sw x8, 128(x22)
skip_32:
lui x10, 0x7854c
addi x10, x10, 132
lui x11, 0xcd376
addi x11, x11, 1377
xdot4 x10, x10, x11
add x8, x10, x0
xdot4 x9, x8, x0
beq x9, x0, valid_33
jal x0, bad
valid_33:
sw x8, 132(x22)
jal x0, skip_33
xdot4 x8, x10, x11
sw x8, 132(x22)
skip_33:
lui x10, 0xedc53
addi x10, x10, 2014
lui x11, 0x975e3
addi x11, x11, -1223
xdot4 x11, x0, x11
add x8, x11, x0
xdot4 x9, x8, x0
beq x9, x0, valid_34
jal x0, bad
valid_34:
sw x8, 136(x22)
jal x0, skip_34
xdot4 x8, x10, x11
sw x8, 136(x22)
skip_34:
lui x10, 0x8f989
addi x10, x10, 1861
lui x11, 0x7990f
addi x11, x11, -596
sw x10, 0(x20)
lw x10, x20, 0
xdot4 x0, x10, x11
addi x8, x0, 37
sw x8, 140(x22)
jal x0, skip_35
xdot4 x8, x10, x11
sw x8, 140(x22)
skip_35:
lui x10, 0x79a89
addi x10, x10, 789
lui x11, 0x6e63f
addi x11, x11, -1523
xdot4 x5, x10, x11
add x8, x5, x0
xdot4 x9, x8, x0
beq x9, x0, valid_36
jal x0, bad
valid_36:
sw x8, 144(x22)
jal x0, skip_36
xdot4 x8, x10, x11
sw x8, 144(x22)
skip_36:
lui x10, 0x7541d
addi x10, x10, -72
lui x11, 0xfadc5
addi x11, x11, -580
xdot4 x10, x10, x11
add x8, x10, x0
xdot4 x9, x8, x0
beq x9, x0, valid_37
jal x0, bad
valid_37:
sw x8, 148(x22)
jal x0, skip_37
xdot4 x8, x10, x11
sw x8, 148(x22)
skip_37:
lui x10, 0xe452f
addi x10, x10, -1123
lui x11, 0x65422
addi x11, x11, 1103
xdot4 x11, x10, x11
add x8, x11, x0
xdot4 x9, x8, x0
beq x9, x0, valid_38
jal x0, bad
valid_38:
sw x8, 152(x22)
jal x0, skip_38
xdot4 x8, x10, x11
sw x8, 152(x22)
skip_38:
lui x10, 0x3e7c3
addi x10, x10, 657
lui x11, 0xebc05
addi x11, x11, 16
xdot4 x0, x10, x11
addi x8, x0, 37
sw x8, 156(x22)
jal x0, skip_39
xdot4 x8, x10, x11
sw x8, 156(x22)
skip_39:
lui x10, 0xbb7c2
addi x10, x10, 1726
lui x11, 0xcaf50
addi x11, x11, 378
sw x10, 0(x20)
lw x10, x20, 0
xdot4 x5, x10, x11
add x8, x5, x0
xdot4 x9, x8, x0
beq x9, x0, valid_40
jal x0, bad
valid_40:
sw x8, 160(x22)
jal x0, skip_40
xdot4 x8, x10, x11
sw x8, 160(x22)
skip_40:
lui x10, 0x4e530
addi x10, x10, -236
lui x11, 0x2a6a
addi x11, x11, 820
xdot4 x10, x10, x11
add x8, x10, x0
xdot4 x9, x8, x0
beq x9, x0, valid_41
jal x0, bad
valid_41:
sw x8, 164(x22)
jal x0, skip_41
xdot4 x8, x10, x11
sw x8, 164(x22)
skip_41:
lui x10, 0xd6d6c
addi x10, x10, 591
lui x11, 0x25eff
addi x11, x11, -1976
xdot4 x11, x10, x11
add x8, x11, x0
xdot4 x9, x8, x0
beq x9, x0, valid_42
jal x0, bad
valid_42:
sw x8, 168(x22)
jal x0, skip_42
xdot4 x8, x10, x11
sw x8, 168(x22)
skip_42:
lui x10, 0xb00ab
addi x10, x10, 1839
lui x11, 0x6b30e
addi x11, x11, 766
xdot4 x0, x10, x11
addi x8, x0, 37
sw x8, 172(x22)
jal x0, skip_43
xdot4 x8, x10, x11
sw x8, 172(x22)
skip_43:
lui x10, 0xd190f
addi x10, x10, -1581
lui x11, 0x3c416
addi x11, x11, 1658
xdot4 x5, x10, x11
add x8, x5, x0
xdot4 x9, x8, x0
beq x9, x0, valid_44
jal x0, bad
valid_44:
sw x8, 176(x22)
jal x0, skip_44
xdot4 x8, x10, x11
sw x8, 176(x22)
skip_44:
lui x10, 0x1a3bd
addi x10, x10, 321
lui x11, 0x9a295
addi x11, x11, 142
sw x10, 0(x20)
lw x10, x20, 0
xdot4 x10, x10, x11
add x8, x10, x0
xdot4 x9, x8, x0
beq x9, x0, valid_45
jal x0, bad
valid_45:
sw x8, 180(x22)
jal x0, skip_45
xdot4 x8, x10, x11
sw x8, 180(x22)
skip_45:
lui x10, 0xa4db0
addi x10, x10, -1650
lui x11, 0xc0fe4
addi x11, x11, -589
xdot4 x11, x10, x11
add x8, x11, x0
xdot4 x9, x8, x0
beq x9, x0, valid_46
jal x0, bad
valid_46:
sw x8, 184(x22)
jal x0, skip_46
xdot4 x8, x10, x11
sw x8, 184(x22)
skip_46:
lui x10, 0xbcb2
addi x10, x10, 917
lui x11, 0xa4c80
addi x11, x11, 203
xdot4 x0, x10, x11
addi x8, x0, 37
sw x8, 188(x22)
jal x0, skip_47
xdot4 x8, x10, x11
sw x8, 188(x22)
skip_47:
lui x10, 0xfc710
addi x10, x10, 1761
lui x11, 0x72ad9
addi x11, x11, 1826
xdot4 x5, x10, x11
add x8, x5, x0
xdot4 x9, x8, x0
beq x9, x0, valid_48
jal x0, bad
valid_48:
sw x8, 192(x22)
jal x0, skip_48
xdot4 x8, x10, x11
sw x8, 192(x22)
skip_48:
lui x10, 0xab3b4
addi x10, x10, 1964
lui x11, 0xedc1c
addi x11, x11, -738
xdot4 x10, x10, x11
add x8, x10, x0
xdot4 x9, x8, x0
beq x9, x0, valid_49
jal x0, bad
valid_49:
sw x8, 196(x22)
jal x0, skip_49
xdot4 x8, x10, x11
sw x8, 196(x22)
skip_49:
lui x10, 0x11fe1
addi x10, x10, -94
lui x11, 0x78c02
addi x11, x11, 323
sw x10, 0(x20)
lw x10, x20, 0
xdot4 x11, x10, x11
add x8, x11, x0
xdot4 x9, x8, x0
beq x9, x0, valid_50
jal x0, bad
valid_50:
sw x8, 200(x22)
jal x0, skip_50
xdot4 x8, x10, x11
sw x8, 200(x22)
skip_50:
lui x10, 0xfc9cf
addi x10, x10, 107
lui x11, 0x8b97f
addi x11, x11, -1874
xdot4 x0, x0, x11
addi x8, x0, 37
sw x8, 204(x22)
jal x0, skip_51
xdot4 x8, x10, x11
sw x8, 204(x22)
skip_51:
lui x10, 0x7394d
addi x10, x10, 950
lui x11, 0x2430f
addi x11, x11, -166
xdot4 x5, x10, x11
add x8, x5, x0
xdot4 x9, x8, x0
beq x9, x0, valid_52
jal x0, bad
valid_52:
sw x8, 208(x22)
jal x0, skip_52
xdot4 x8, x10, x11
sw x8, 208(x22)
skip_52:
lui x10, 0xff1e0
addi x10, x10, 94
lui x11, 0x87564
addi x11, x11, -1876
xdot4 x10, x10, x11
add x8, x10, x0
xdot4 x9, x8, x0
beq x9, x0, valid_53
jal x0, bad
valid_53:
sw x8, 212(x22)
jal x0, skip_53
xdot4 x8, x10, x11
sw x8, 212(x22)
skip_53:
lui x10, 0x67b4
addi x10, x10, -571
lui x11, 0x6d206
addi x11, x11, 986
xdot4 x11, x10, x11
add x8, x11, x0
xdot4 x9, x8, x0
beq x9, x0, valid_54
jal x0, bad
valid_54:
sw x8, 216(x22)
jal x0, skip_54
xdot4 x8, x10, x11
sw x8, 216(x22)
skip_54:
lui x10, 0xe6d7e
addi x10, x10, -1447
lui x11, 0xc4023
addi x11, x11, -85
sw x10, 0(x20)
lw x10, x20, 0
xdot4 x0, x10, x11
addi x8, x0, 37
sw x8, 220(x22)
jal x0, skip_55
xdot4 x8, x10, x11
sw x8, 220(x22)
skip_55:
lui x10, 0xce07c
addi x10, x10, 191
lui x11, 0x68bb
addi x11, x11, 1223
xdot4 x5, x10, x11
add x8, x5, x0
xdot4 x9, x8, x0
beq x9, x0, valid_56
jal x0, bad
valid_56:
sw x8, 224(x22)
jal x0, skip_56
xdot4 x8, x10, x11
sw x8, 224(x22)
skip_56:
lui x10, 0xf43c4
addi x10, x10, 430
lui x11, 0x6bb68
addi x11, x11, 41
xdot4 x10, x10, x11
add x8, x10, x0
xdot4 x9, x8, x0
beq x9, x0, valid_57
jal x0, bad
valid_57:
sw x8, 228(x22)
jal x0, skip_57
xdot4 x8, x10, x11
sw x8, 228(x22)
skip_57:
lui x10, 0x34391
addi x10, x10, 1809
lui x11, 0x5fdb9
addi x11, x11, -468
xdot4 x11, x10, x11
add x8, x11, x0
xdot4 x9, x8, x0
beq x9, x0, valid_58
jal x0, bad
valid_58:
sw x8, 232(x22)
jal x0, skip_58
xdot4 x8, x10, x11
sw x8, 232(x22)
skip_58:
lui x10, 0x32744
addi x10, x10, 1252
lui x11, 0xdc148
addi x11, x11, 626
xdot4 x0, x10, x11
addi x8, x0, 37
sw x8, 236(x22)
jal x0, skip_59
xdot4 x8, x10, x11
sw x8, 236(x22)
skip_59:
lui x10, 0xe9206
addi x10, x10, -84
lui x11, 0xd3443
addi x11, x11, 783
sw x10, 0(x20)
lw x10, x20, 0
xdot4 x5, x10, x11
add x8, x5, x0
xdot4 x9, x8, x0
beq x9, x0, valid_60
jal x0, bad
valid_60:
sw x8, 240(x22)
jal x0, skip_60
xdot4 x8, x10, x11
sw x8, 240(x22)
skip_60:
lui x10, 0xd7626
addi x10, x10, 1755
lui x11, 0x3b414
addi x11, x11, 1249
xdot4 x10, x10, x11
add x8, x10, x0
xdot4 x9, x8, x0
beq x9, x0, valid_61
jal x0, bad
valid_61:
sw x8, 244(x22)
jal x0, skip_61
xdot4 x8, x10, x11
sw x8, 244(x22)
skip_61:
lui x10, 0x9f0c
addi x10, x10, 557
lui x11, 0xb3569
addi x11, x11, 865
xdot4 x11, x10, x11
add x8, x11, x0
xdot4 x9, x8, x0
beq x9, x0, valid_62
jal x0, bad
valid_62:
sw x8, 248(x22)
jal x0, skip_62
xdot4 x8, x10, x11
sw x8, 248(x22)
skip_62:
lui x10, 0xff5a4
addi x10, x10, -529
lui x11, 0x7aa97
addi x11, x11, 1251
xdot4 x0, x10, x11
addi x8, x0, 37
sw x8, 252(x22)
jal x0, skip_63
xdot4 x8, x10, x11
sw x8, 252(x22)
skip_63:
lui x10, 0xfc0ee
addi x10, x10, 1295
lui x11, 0x12310
addi x11, x11, 1006
xdot4 x5, x10, x11
add x8, x5, x0
xdot4 x9, x8, x0
beq x9, x0, valid_64
jal x0, bad
valid_64:
sw x8, 256(x22)
jal x0, skip_64
xdot4 x8, x10, x11
sw x8, 256(x22)
skip_64:
lui x10, 0x4bec4
addi x10, x10, 441
lui x11, 0xb9729
addi x11, x11, 866
sw x10, 0(x20)
lw x10, x20, 0
xdot4 x10, x10, x11
add x8, x10, x0
xdot4 x9, x8, x0
beq x9, x0, valid_65
jal x0, bad
valid_65:
sw x8, 260(x22)
jal x0, skip_65
xdot4 x8, x10, x11
sw x8, 260(x22)
skip_65:
lui x10, 0xa053
addi x10, x10, -1172
lui x11, 0x37a41
addi x11, x11, 90
xdot4 x11, x10, x11
add x8, x11, x0
xdot4 x9, x8, x0
beq x9, x0, valid_66
jal x0, bad
valid_66:
sw x8, 264(x22)
jal x0, skip_66
xdot4 x8, x10, x11
sw x8, 264(x22)
skip_66:
lui x10, 0x4b685
addi x10, x10, -263
lui x11, 0x27b75
addi x11, x11, 1737
xdot4 x0, x10, x11
addi x8, x0, 37
sw x8, 268(x22)
jal x0, skip_67
xdot4 x8, x10, x11
sw x8, 268(x22)
skip_67:
lui x10, 0x802a9
addi x10, x10, -374
lui x11, 0xd529e
addi x11, x11, -1931
xdot4 x5, x0, x11
add x8, x5, x0
xdot4 x9, x8, x0
beq x9, x0, valid_68
jal x0, bad
valid_68:
sw x8, 272(x22)
jal x0, skip_68
xdot4 x8, x10, x11
sw x8, 272(x22)
skip_68:
lui x10, 0x75f88
addi x10, x10, 740
lui x11, 0xbac0f
addi x11, x11, -726
xdot4 x10, x10, x11
add x8, x10, x0
xdot4 x9, x8, x0
beq x9, x0, valid_69
jal x0, bad
valid_69:
sw x8, 276(x22)
jal x0, skip_69
xdot4 x8, x10, x11
sw x8, 276(x22)
skip_69:
lui x10, 0x25416
addi x10, x10, 1663
lui x11, 0xcdb3c
addi x11, x11, -663
sw x10, 0(x20)
lw x10, x20, 0
xdot4 x11, x10, x11
add x8, x11, x0
xdot4 x9, x8, x0
beq x9, x0, valid_70
jal x0, bad
valid_70:
sw x8, 280(x22)
jal x0, skip_70
xdot4 x8, x10, x11
sw x8, 280(x22)
skip_70:
lui x10, 0x8d50f
addi x10, x10, -1572
lui x11, 0x5c458
addi x11, x11, -56
xdot4 x0, x10, x11
addi x8, x0, 37
sw x8, 284(x22)
jal x0, skip_71
xdot4 x8, x10, x11
sw x8, 284(x22)
skip_71:
lui x10, 0x67434
addi x10, x10, 1584
lui x11, 0xcc86f
addi x11, x11, 443
xdot4 x5, x10, x11
add x8, x5, x0
xdot4 x9, x8, x0
beq x9, x0, valid_72
jal x0, bad
valid_72:
sw x8, 288(x22)
jal x0, skip_72
xdot4 x8, x10, x11
sw x8, 288(x22)
skip_72:
lui x10, 0xd5cf0
addi x10, x10, -353
lui x11, 0xc0f94
addi x11, x11, -685
xdot4 x10, x10, x11
add x8, x10, x0
xdot4 x9, x8, x0
beq x9, x0, valid_73
jal x0, bad
valid_73:
sw x8, 292(x22)
jal x0, skip_73
xdot4 x8, x10, x11
sw x8, 292(x22)
skip_73:
lui x10, 0x25092
addi x10, x10, 1806
lui x11, 0xda1d5
addi x11, x11, 197
xdot4 x11, x10, x11
add x8, x11, x0
xdot4 x9, x8, x0
beq x9, x0, valid_74
jal x0, bad
valid_74:
sw x8, 296(x22)
jal x0, skip_74
xdot4 x8, x10, x11
sw x8, 296(x22)
skip_74:
lui x10, 0xa4d3e
addi x10, x10, 253
lui x11, 0x16b1e
addi x11, x11, 618
sw x10, 0(x20)
lw x10, x20, 0
xdot4 x0, x10, x11
addi x8, x0, 37
sw x8, 300(x22)
jal x0, skip_75
xdot4 x8, x10, x11
sw x8, 300(x22)
skip_75:
lui x10, 0xb0e0e
addi x10, x10, 1946
lui x11, 0x8a0c3
addi x11, x11, -513
xdot4 x5, x10, x11
add x8, x5, x0
xdot4 x9, x8, x0
beq x9, x0, valid_76
jal x0, bad
valid_76:
sw x8, 304(x22)
jal x0, skip_76
xdot4 x8, x10, x11
sw x8, 304(x22)
skip_76:
lui x10, 0xafa50
addi x10, x10, 649
lui x11, 0x8b156
addi x11, x11, 1892
xdot4 x10, x10, x11
add x8, x10, x0
xdot4 x9, x8, x0
beq x9, x0, valid_77
jal x0, bad
valid_77:
sw x8, 308(x22)
jal x0, skip_77
xdot4 x8, x10, x11
sw x8, 308(x22)
skip_77:
lui x10, 0x9e77f
addi x10, x10, -531
lui x11, 0xf0879
addi x11, x11, 220
xdot4 x11, x10, x11
add x8, x11, x0
xdot4 x9, x8, x0
beq x9, x0, valid_78
jal x0, bad
valid_78:
sw x8, 312(x22)
jal x0, skip_78
xdot4 x8, x10, x11
sw x8, 312(x22)
skip_78:
lui x10, 0xa4528
addi x10, x10, -1627
lui x11, 0xae1cf
addi x11, x11, -782
xdot4 x0, x10, x11
addi x8, x0, 37
sw x8, 316(x22)
jal x0, skip_79
xdot4 x8, x10, x11
sw x8, 316(x22)
skip_79:
lui x10, 0x2392
addi x10, x10, -857
lui x11, 0xb6a05
addi x11, x11, 1223
sw x10, 0(x20)
lw x10, x20, 0
xdot4 x5, x10, x11
add x8, x5, x0
xdot4 x9, x8, x0
beq x9, x0, valid_80
jal x0, bad
valid_80:
sw x8, 320(x22)
jal x0, skip_80
xdot4 x8, x10, x11
sw x8, 320(x22)
skip_80:
lui x10, 0x72c92
addi x10, x10, 624
lui x11, 0xd9b70
addi x11, x11, -647
xdot4 x10, x10, x11
add x8, x10, x0
xdot4 x9, x8, x0
beq x9, x0, valid_81
jal x0, bad
valid_81:
sw x8, 324(x22)
jal x0, skip_81
xdot4 x8, x10, x11
sw x8, 324(x22)
skip_81:
lui x10, 0x3110a
addi x10, x10, 1166
lui x11, 0x96883
addi x11, x11, 1893
xdot4 x11, x10, x11
add x8, x11, x0
xdot4 x9, x8, x0
beq x9, x0, valid_82
jal x0, bad
valid_82:
sw x8, 328(x22)
jal x0, skip_82
xdot4 x8, x10, x11
sw x8, 328(x22)
skip_82:
lui x10, 0xcb7d7
addi x10, x10, 1294
lui x11, 0x75ee9
addi x11, x11, -1348
xdot4 x0, x10, x11
addi x8, x0, 37
sw x8, 332(x22)
jal x0, skip_83
xdot4 x8, x10, x11
sw x8, 332(x22)
skip_83:
lui x10, 0xc2698
addi x10, x10, -1525
lui x11, 0x1160e
addi x11, x11, -1134
xdot4 x5, x10, x11
add x8, x5, x0
xdot4 x9, x8, x0
beq x9, x0, valid_84
jal x0, bad
valid_84:
sw x8, 336(x22)
jal x0, skip_84
xdot4 x8, x10, x11
sw x8, 336(x22)
skip_84:
lui x10, 0x89492
addi x10, x10, -1612
lui x11, 0xbc07a
addi x11, x11, -1314
sw x10, 0(x20)
lw x10, x20, 0
xdot4 x10, x0, x11
add x8, x10, x0
xdot4 x9, x8, x0
beq x9, x0, valid_85
jal x0, bad
valid_85:
sw x8, 340(x22)
jal x0, skip_85
xdot4 x8, x10, x11
sw x8, 340(x22)
skip_85:
lui x10, 0x97802
addi x10, x10, 503
lui x11, 0x64411
addi x11, x11, -1266
xdot4 x11, x10, x11
add x8, x11, x0
xdot4 x9, x8, x0
beq x9, x0, valid_86
jal x0, bad
valid_86:
sw x8, 344(x22)
jal x0, skip_86
xdot4 x8, x10, x11
sw x8, 344(x22)
skip_86:
lui x10, 0xc6620
addi x10, x10, -80
lui x11, 0x1e4a1
addi x11, x11, 187
xdot4 x0, x10, x11
addi x8, x0, 37
sw x8, 348(x22)
jal x0, skip_87
xdot4 x8, x10, x11
sw x8, 348(x22)
skip_87:
lui x10, 0xe6e90
addi x10, x10, -1440
lui x11, 0x72987
addi x11, x11, 1391
xdot4 x5, x10, x11
add x8, x5, x0
xdot4 x9, x8, x0
beq x9, x0, valid_88
jal x0, bad
valid_88:
sw x8, 352(x22)
jal x0, skip_88
xdot4 x8, x10, x11
sw x8, 352(x22)
skip_88:
lui x10, 0xf2d70
addi x10, x10, 75
lui x11, 0xa3d8e
addi x11, x11, 1623
xdot4 x10, x10, x11
add x8, x10, x0
xdot4 x9, x8, x0
beq x9, x0, valid_89
jal x0, bad
valid_89:
sw x8, 356(x22)
jal x0, skip_89
xdot4 x8, x10, x11
sw x8, 356(x22)
skip_89:
lui x10, 0x964bb
addi x10, x10, 768
lui x11, 0x53e33
addi x11, x11, 1820
sw x10, 0(x20)
lw x10, x20, 0
xdot4 x11, x10, x11
add x8, x11, x0
xdot4 x9, x8, x0
beq x9, x0, valid_90
jal x0, bad
valid_90:
sw x8, 360(x22)
jal x0, skip_90
xdot4 x8, x10, x11
sw x8, 360(x22)
skip_90:
lui x10, 0x4825d
addi x10, x10, -336
lui x11, 0xaf429
addi x11, x11, -667
xdot4 x0, x10, x11
addi x8, x0, 37
sw x8, 364(x22)
jal x0, skip_91
xdot4 x8, x10, x11
sw x8, 364(x22)
skip_91:
lui x10, 0x81081
addi x10, x10, 1065
lui x11, 0x9268a
addi x11, x11, 125
xdot4 x5, x10, x11
add x8, x5, x0
xdot4 x9, x8, x0
beq x9, x0, valid_92
jal x0, bad
valid_92:
sw x8, 368(x22)
jal x0, skip_92
xdot4 x8, x10, x11
sw x8, 368(x22)
skip_92:
lui x10, 0x587c0
addi x10, x10, 908
lui x11, 0x76faf
addi x11, x11, 1791
xdot4 x10, x10, x11
add x8, x10, x0
xdot4 x9, x8, x0
beq x9, x0, valid_93
jal x0, bad
valid_93:
sw x8, 372(x22)
jal x0, skip_93
xdot4 x8, x10, x11
sw x8, 372(x22)
skip_93:
lui x10, 0x7bd98
addi x10, x10, 111
lui x11, 0x62096
addi x11, x11, -668
xdot4 x11, x10, x11
add x8, x11, x0
xdot4 x9, x8, x0
beq x9, x0, valid_94
jal x0, bad
valid_94:
sw x8, 376(x22)
jal x0, skip_94
xdot4 x8, x10, x11
sw x8, 376(x22)
skip_94:
lui x10, 0xd2fe6
addi x10, x10, 263
lui x11, 0xbc05
addi x11, x11, 577
sw x10, 0(x20)
lw x10, x20, 0
xdot4 x0, x10, x11
addi x8, x0, 37
sw x8, 380(x22)
jal x0, skip_95
xdot4 x8, x10, x11
sw x8, 380(x22)
skip_95:
lui x10, 0xaf679
addi x10, x10, -599
lui x11, 0xa4b9f
addi x11, x11, -748
xdot4 x5, x10, x11
add x8, x5, x0
xdot4 x9, x8, x0
beq x9, x0, valid_96
jal x0, bad
valid_96:
sw x8, 384(x22)
jal x0, skip_96
xdot4 x8, x10, x11
sw x8, 384(x22)
skip_96:
lui x10, 0x47087
addi x10, x10, -816
lui x11, 0xd0a2c
addi x11, x11, -845
xdot4 x10, x10, x11
add x8, x10, x0
xdot4 x9, x8, x0
beq x9, x0, valid_97
jal x0, bad
valid_97:
sw x8, 388(x22)
jal x0, skip_97
xdot4 x8, x10, x11
sw x8, 388(x22)
skip_97:
lui x10, 0xb7223
addi x10, x10, -1451
lui x11, 0x37c1c
addi x11, x11, 1824
xdot4 x11, x10, x11
add x8, x11, x0
xdot4 x9, x8, x0
beq x9, x0, valid_98
jal x0, bad
valid_98:
sw x8, 392(x22)
jal x0, skip_98
xdot4 x8, x10, x11
sw x8, 392(x22)
skip_98:
lui x10, 0xe880d
addi x10, x10, -1216
lui x11, 0xe0c3b
addi x11, x11, -991
xdot4 x0, x10, x11
addi x8, x0, 37
sw x8, 396(x22)
jal x0, skip_99
xdot4 x8, x10, x11
sw x8, 396(x22)
skip_99:
lui x10, 0xfce8f
addi x10, x10, 376
lui x11, 0x38928
addi x11, x11, 1260
sw x10, 0(x20)
lw x10, x20, 0
xdot4 x5, x10, x11
add x8, x5, x0
xdot4 x9, x8, x0
beq x9, x0, valid_100
jal x0, bad
valid_100:
sw x8, 400(x22)
jal x0, skip_100
xdot4 x8, x10, x11
sw x8, 400(x22)
skip_100:
lui x10, 0x5c91a
addi x10, x10, -1348
lui x11, 0x4943d
addi x11, x11, -936
xdot4 x10, x10, x11
add x8, x10, x0
xdot4 x9, x8, x0
beq x9, x0, valid_101
jal x0, bad
valid_101:
sw x8, 404(x22)
jal x0, skip_101
xdot4 x8, x10, x11
sw x8, 404(x22)
skip_101:
lui x10, 0xd2d6a
addi x10, x10, 1180
lui x11, 0xd917d
addi x11, x11, 1114
xdot4 x11, x0, x11
add x8, x11, x0
xdot4 x9, x8, x0
beq x9, x0, valid_102
jal x0, bad
valid_102:
sw x8, 408(x22)
jal x0, skip_102
xdot4 x8, x10, x11
sw x8, 408(x22)
skip_102:
lui x10, 0xd4134
addi x10, x10, 110
lui x11, 0xf2f94
addi x11, x11, -1937
xdot4 x0, x10, x11
addi x8, x0, 37
sw x8, 412(x22)
jal x0, skip_103
xdot4 x8, x10, x11
sw x8, 412(x22)
skip_103:
lui x10, 0x9938c
addi x10, x10, -535
lui x11, 0x462ab
addi x11, x11, 1821
xdot4 x5, x10, x11
add x8, x5, x0
xdot4 x9, x8, x0
beq x9, x0, valid_104
jal x0, bad
valid_104:
sw x8, 416(x22)
jal x0, skip_104
xdot4 x8, x10, x11
sw x8, 416(x22)
skip_104:
lui x10, 0xbc991
addi x10, x10, 408
lui x11, 0xa952c
addi x11, x11, -883
sw x10, 0(x20)
lw x10, x20, 0
xdot4 x10, x10, x11
add x8, x10, x0
xdot4 x9, x8, x0
beq x9, x0, valid_105
jal x0, bad
valid_105:
sw x8, 420(x22)
jal x0, skip_105
xdot4 x8, x10, x11
sw x8, 420(x22)
skip_105:
lui x10, 0x8b625
addi x10, x10, -780
lui x11, 0x42ef0
addi x11, x11, 1600
xdot4 x11, x10, x11
add x8, x11, x0
xdot4 x9, x8, x0
beq x9, x0, valid_106
jal x0, bad
valid_106:
sw x8, 424(x22)
jal x0, skip_106
xdot4 x8, x10, x11
sw x8, 424(x22)
skip_106:
lui x10, 0xb7fbb
addi x10, x10, -1257
lui x11, 0x2bde1
addi x11, x11, 2021
xdot4 x0, x10, x11
addi x8, x0, 37
sw x8, 428(x22)
jal x0, skip_107
xdot4 x8, x10, x11
sw x8, 428(x22)
skip_107:
lui x10, 0x90fba
addi x10, x10, -278
lui x11, 0xc72c4
addi x11, x11, -630
xdot4 x5, x10, x11
add x8, x5, x0
xdot4 x9, x8, x0
beq x9, x0, valid_108
jal x0, bad
valid_108:
sw x8, 432(x22)
jal x0, skip_108
xdot4 x8, x10, x11
sw x8, 432(x22)
skip_108:
lui x10, 0xffae7
addi x10, x10, 1199
lui x11, 0x5bbac
addi x11, x11, -242
xdot4 x10, x10, x11
add x8, x10, x0
xdot4 x9, x8, x0
beq x9, x0, valid_109
jal x0, bad
valid_109:
sw x8, 436(x22)
jal x0, skip_109
xdot4 x8, x10, x11
sw x8, 436(x22)
skip_109:
lui x10, 0x96eef
addi x10, x10, 966
lui x11, 0x91dbf
addi x11, x11, -162
sw x10, 0(x20)
lw x10, x20, 0
xdot4 x11, x10, x11
add x8, x11, x0
xdot4 x9, x8, x0
beq x9, x0, valid_110
jal x0, bad
valid_110:
sw x8, 440(x22)
jal x0, skip_110
xdot4 x8, x10, x11
sw x8, 440(x22)
skip_110:
lui x10, 0xe5575
addi x10, x10, 1063
lui x11, 0xdf492
addi x11, x11, 862
xdot4 x0, x10, x11
addi x8, x0, 37
sw x8, 444(x22)
jal x0, skip_111
xdot4 x8, x10, x11
sw x8, 444(x22)
skip_111:
lui x10, 0xf0877
addi x10, x10, 232
lui x11, 0xc3c29
addi x11, x11, -149
xdot4 x5, x10, x11
add x8, x5, x0
xdot4 x9, x8, x0
beq x9, x0, valid_112
jal x0, bad
valid_112:
sw x8, 448(x22)
jal x0, skip_112
xdot4 x8, x10, x11
sw x8, 448(x22)
skip_112:
lui x10, 0xb311b
addi x10, x10, 1963
lui x11, 0xa370f
addi x11, x11, -1261
xdot4 x10, x10, x11
add x8, x10, x0
xdot4 x9, x8, x0
beq x9, x0, valid_113
jal x0, bad
valid_113:
sw x8, 452(x22)
jal x0, skip_113
xdot4 x8, x10, x11
sw x8, 452(x22)
skip_113:
lui x10, 0x44900
addi x10, x10, 1939
lui x11, 0x32251
addi x11, x11, 536
xdot4 x11, x10, x11
add x8, x11, x0
xdot4 x9, x8, x0
beq x9, x0, valid_114
jal x0, bad
valid_114:
sw x8, 456(x22)
jal x0, skip_114
xdot4 x8, x10, x11
sw x8, 456(x22)
skip_114:
lui x10, 0x3b047
addi x10, x10, 458
lui x11, 0xe1505
addi x11, x11, -673
sw x10, 0(x20)
lw x10, x20, 0
xdot4 x0, x10, x11
addi x8, x0, 37
sw x8, 460(x22)
jal x0, skip_115
xdot4 x8, x10, x11
sw x8, 460(x22)
skip_115:
lui x10, 0x9ae44
addi x10, x10, 1208
lui x11, 0x9728b
addi x11, x11, -181
xdot4 x5, x10, x11
add x8, x5, x0
xdot4 x9, x8, x0
beq x9, x0, valid_116
jal x0, bad
valid_116:
sw x8, 464(x22)
jal x0, skip_116
xdot4 x8, x10, x11
sw x8, 464(x22)
skip_116:
lui x10, 0x53ea1
addi x10, x10, 1225
lui x11, 0xecd41
addi x11, x11, -1427
xdot4 x10, x10, x11
add x8, x10, x0
xdot4 x9, x8, x0
beq x9, x0, valid_117
jal x0, bad
valid_117:
sw x8, 468(x22)
jal x0, skip_117
xdot4 x8, x10, x11
sw x8, 468(x22)
skip_117:
lui x10, 0x3253d
addi x10, x10, 1392
lui x11, 0x353c5
addi x11, x11, -1498
xdot4 x11, x10, x11
add x8, x11, x0
xdot4 x9, x8, x0
beq x9, x0, valid_118
jal x0, bad
valid_118:
sw x8, 472(x22)
jal x0, skip_118
xdot4 x8, x10, x11
sw x8, 472(x22)
skip_118:
lui x10, 0x3aa3e
addi x10, x10, 1559
lui x11, 0xd572b
addi x11, x11, -600
xdot4 x0, x0, x11
addi x8, x0, 37
sw x8, 476(x22)
jal x0, skip_119
xdot4 x8, x10, x11
sw x8, 476(x22)
skip_119:
lui x10, 0xb25f5
addi x10, x10, -2048
lui x11, 0xc98f7
addi x11, x11, -1065
sw x10, 0(x20)
lw x10, x20, 0
xdot4 x5, x10, x11
add x8, x5, x0
xdot4 x9, x8, x0
beq x9, x0, valid_120
jal x0, bad
valid_120:
sw x8, 480(x22)
jal x0, skip_120
xdot4 x8, x10, x11
sw x8, 480(x22)
skip_120:
lui x10, 0x52c5
addi x10, x10, -161
lui x11, 0x1fcb2
addi x11, x11, 651
xdot4 x10, x10, x11
add x8, x10, x0
xdot4 x9, x8, x0
beq x9, x0, valid_121
jal x0, bad
valid_121:
sw x8, 484(x22)
jal x0, skip_121
xdot4 x8, x10, x11
sw x8, 484(x22)
skip_121:
lui x10, 0x53f1d
addi x10, x10, 1155
lui x11, 0xeeb5e
addi x11, x11, -1131
xdot4 x11, x10, x11
add x8, x11, x0
xdot4 x9, x8, x0
beq x9, x0, valid_122
jal x0, bad
valid_122:
sw x8, 488(x22)
jal x0, skip_122
xdot4 x8, x10, x11
sw x8, 488(x22)
skip_122:
lui x10, 0x8ed0c
addi x10, x10, -1355
lui x11, 0x150ec
addi x11, x11, -359
xdot4 x0, x10, x11
addi x8, x0, 37
sw x8, 492(x22)
jal x0, skip_123
xdot4 x8, x10, x11
sw x8, 492(x22)
skip_123:
lui x10, 0xe13f0
addi x10, x10, -999
lui x11, 0x47c41
addi x11, x11, -320
xdot4 x5, x10, x11
add x8, x5, x0
xdot4 x9, x8, x0
beq x9, x0, valid_124
jal x0, bad
valid_124:
sw x8, 496(x22)
jal x0, skip_124
xdot4 x8, x10, x11
sw x8, 496(x22)
skip_124:
lui x10, 0x73767
addi x10, x10, -1159
lui x11, 0x63dca
addi x11, x11, 1515
sw x10, 0(x20)
lw x10, x20, 0
xdot4 x10, x10, x11
add x8, x10, x0
xdot4 x9, x8, x0
beq x9, x0, valid_125
jal x0, bad
valid_125:
sw x8, 500(x22)
jal x0, skip_125
xdot4 x8, x10, x11
sw x8, 500(x22)
skip_125:
lui x10, 0x5f296
addi x10, x10, -1048
lui x11, 0x8badf
addi x11, x11, 831
xdot4 x11, x10, x11
add x8, x11, x0
xdot4 x9, x8, x0
beq x9, x0, valid_126
jal x0, bad
valid_126:
sw x8, 504(x22)
jal x0, skip_126
xdot4 x8, x10, x11
sw x8, 504(x22)
skip_126:
lui x10, 0x71c02
addi x10, x10, 1195
lui x11, 0x2b5b4
addi x11, x11, 359
xdot4 x0, x10, x11
addi x8, x0, 37
sw x8, 508(x22)
jal x0, skip_127
xdot4 x8, x10, x11
sw x8, 508(x22)
skip_127:
lui x10, 0x3c439
addi x10, x10, 2019
lui x11, 0x5a7a4
addi x11, x11, -844
xdot4 x5, x10, x11
add x8, x5, x0
xdot4 x9, x8, x0
beq x9, x0, valid_128
jal x0, bad
valid_128:
sw x8, 512(x22)
jal x0, skip_128
xdot4 x8, x10, x11
sw x8, 512(x22)
skip_128:
lui x10, 0x5b3f1
addi x10, x10, -1904
lui x11, 0x98044
addi x11, x11, -1707
xdot4 x10, x10, x11
add x8, x10, x0
xdot4 x9, x8, x0
beq x9, x0, valid_129
jal x0, bad
valid_129:
sw x8, 516(x22)
jal x0, skip_129
xdot4 x8, x10, x11
sw x8, 516(x22)
skip_129:
lui x10, 0xd1368
addi x10, x10, -1458
lui x11, 0x2376d
addi x11, x11, 862
sw x10, 0(x20)
lw x10, x20, 0
xdot4 x11, x10, x11
add x8, x11, x0
xdot4 x9, x8, x0
beq x9, x0, valid_130
jal x0, bad
valid_130:
sw x8, 520(x22)
jal x0, skip_130
xdot4 x8, x10, x11
sw x8, 520(x22)
skip_130:
addi x24, x0, 1
jal x0, complete
bad:
addi x24, x0, 2
complete:
lui x23, 0x8003f
addi x23, x23, 0
sw x24, 0(x23)
halt:
jal x0, halt
