.option norvc
.section .text.init
.globl _start
_start:
la s0,scratch
li t0,0x90000000
li s1,2509231316
li s2,3131145086
li s3,211948689
li s4,2225615689
li s5,786022073
sltu s5,s4,s1
and s5,s3,s1
srai s4,s4,2
srai s2,s1,20
srl s4,s3,s1
xor s5,s3,s1
srli s1,s2,14
add s1,s3,s4
beq s3,s3,rand_control_8
addi s5,s5,1
rand_control_8:
srli s4,s2,27
slt s1,s1,s1
and s5,s1,s1
slli s4,s2,23
srai s3,s1,30
or s4,s3,s4
sll s1,s5,s2
and s3,s2,s1
bne s5,s5,rand_control_17
addi s5,s5,1
rand_control_17:
srai s3,s5,23
or s5,s1,s1
addi s1,s4,-1046
add s5,s5,s2
slt s5,s3,s1
addi s5,s5,318
and s3,s1,s1
xor s5,s2,s1
beq s2,s2,rand_control_26
addi s3,s3,1
rand_control_26:
srli s2,s3,19
ori s5,s3,971
sub s2,s2,s2
beq s2,s2,rand_control_30
addi s4,s4,1
rand_control_30:
xori s4,s4,-1048
ori s4,s1,57
and s4,s1,s5
add s4,s3,s1
ori s3,s4,510
srli s4,s4,13
and s2,s4,s5
beq s2,s2,rand_control_38
addi s5,s5,1
rand_control_38:
xor s5,s2,s1
sll s2,s2,s5
srl s2,s1,s5
andi s3,s5,1374
srl s1,s4,s4
ori s3,s3,-1368
xori s3,s1,-309
slt s4,s1,s5
srl s4,s3,s1
srai s4,s4,7
slli s2,s4,31
bne s4,s4,rand_control_50
addi s5,s5,1
rand_control_50:
beq s3,s3,rand_control_51
addi s5,s5,1
rand_control_51:
sub s3,s5,s1
andi s4,s2,-781
xori s1,s3,-1061
srai s1,s3,2
andi s2,s2,-1998
xor s2,s4,s2
sub s3,s5,s1
and s4,s5,s4
or s5,s1,s4
sub s3,s1,s4
or s4,s2,s1
bne s3,s3,rand_control_63
addi s1,s1,1
rand_control_63:
and s2,s1,s2
slli s1,s3,7
slli s2,s5,13
srl s3,s5,s3
xori s3,s1,-1680
bne s4,s4,rand_control_69
addi s3,s3,1
rand_control_69:
ori s1,s1,1999
xor s3,s4,s5
beq s2,s2,rand_control_72
addi s1,s1,1
rand_control_72:
beq s1,s1,rand_control_73
addi s3,s3,1
rand_control_73:
srl s1,s2,s3
ori s5,s4,1963
slt s1,s1,s4
slli s5,s2,17
sll s1,s3,s3
addi s5,s5,389
slt s3,s1,s1
sll s2,s4,s1
beq s2,s2,rand_control_82
addi s3,s3,1
rand_control_82:
xori s4,s4,-209
beq s4,s4,rand_control_84
addi s2,s2,1
rand_control_84:
sll s5,s4,s4
beq s2,s2,rand_control_86
addi s5,s5,1
rand_control_86:
sub s1,s3,s1
ori s3,s1,1741
andi s2,s3,353
xori s4,s5,-1999
slt s1,s4,s4
sltu s1,s4,s5
and s3,s4,s4
or s4,s4,s5
ori s5,s1,-1053
addi s1,s1,582
sltu s4,s1,s4
srai s3,s1,18
and s5,s2,s3
slt s3,s1,s4
and s5,s3,s4
addi s5,s2,-504
slt s1,s1,s5
slli s3,s3,22
sub s3,s2,s4
sub s5,s3,s1
ori s3,s5,1302
srl s3,s5,s3
xor s5,s2,s5
srli s4,s5,4
srli s5,s3,27
sub s2,s5,s1
bne s2,s2,rand_control_113
addi s1,s1,1
rand_control_113:
slli s1,s3,22
add s5,s5,s4
srli s1,s1,16
or s5,s5,s3
sll s3,s5,s5
xori s3,s2,-1501
addi s1,s2,-1239
bne s2,s2,rand_control_121
addi s1,s1,1
rand_control_121:
add s5,s3,s5
sll s4,s1,s3
srli s3,s1,9
sltu s4,s2,s2
sll s5,s4,s2
xori s1,s1,-984
srl s4,s4,s1
srai s2,s3,3
ori s5,s4,1652
ori s5,s4,311
addi s1,s3,561
xor s3,s4,s2
or s2,s2,s1
beq s3,s3,rand_control_135
addi s4,s4,1
rand_control_135:
srai s1,s5,0
xori s5,s1,1271
bne s1,s1,rand_control_138
addi s1,s1,1
rand_control_138:
srli s1,s4,23
addi s2,s3,389
beq s4,s4,rand_control_141
addi s1,s1,1
rand_control_141:
srl s2,s1,s5
srli s2,s1,10
srai s1,s4,19
srai s5,s3,10
ori s3,s2,-1905
srl s1,s1,s5
bne s4,s4,rand_control_148
addi s5,s5,1
rand_control_148:
ori s3,s2,609
srli s2,s4,13
beq s5,s5,rand_control_151
addi s3,s3,1
rand_control_151:
slt s4,s1,s2
addi s4,s4,185
sub s4,s3,s4
xori s1,s2,-1063
andi s3,s3,-266
beq s5,s5,rand_control_157
addi s2,s2,1
rand_control_157:
sltu s1,s3,s4
xori s2,s5,-896
andi s1,s2,949
bne s1,s1,rand_control_161
addi s5,s5,1
rand_control_161:
sll s5,s3,s4
add s3,s5,s3
or s5,s2,s5
slt s1,s4,s2
xori s4,s1,-170
sll s3,s2,s3
xori s5,s5,-323
bne s1,s1,rand_control_169
addi s2,s2,1
rand_control_169:
sltu s2,s4,s5
bne s4,s4,rand_control_171
addi s3,s3,1
rand_control_171:
sltu s5,s3,s4
sub s4,s2,s1
srl s2,s5,s1
sub s2,s2,s2
slt s2,s2,s3
sltu s4,s2,s2
andi s2,s1,-1116
bne s3,s3,rand_control_179
addi s5,s5,1
rand_control_179:
sltu s3,s2,s3
and s3,s4,s5
srl s1,s3,s3
slt s3,s5,s3
addi s2,s5,1522
xori s3,s4,-1964
bne s2,s2,rand_control_186
addi s5,s5,1
rand_control_186:
or s2,s2,s1
and s3,s5,s1
srli s3,s1,12
srli s1,s3,3
or s1,s2,s1
ori s3,s4,1612
sll s5,s3,s5
and s4,s2,s4
andi s3,s5,-2029
sltu s1,s3,s4
beq s4,s4,rand_control_197
addi s3,s3,1
rand_control_197:
bne s5,s5,rand_control_198
addi s1,s1,1
rand_control_198:
bne s5,s5,rand_control_199
addi s2,s2,1
rand_control_199:
ori s5,s5,981
and s5,s3,s4
sltu s1,s1,s3
xor s3,s5,s3
addi s1,s5,488
srai s5,s2,7
srai s2,s1,14
srli s4,s2,25
and s4,s2,s4
and s4,s4,s3
ori s5,s4,117
sll s2,s2,s5
slt s1,s4,s4
slt s5,s2,s1
addi s1,s5,978
sltu s2,s1,s5
srai s2,s2,7
beq s3,s3,rand_control_217
addi s3,s3,1
rand_control_217:
bne s3,s3,rand_control_218
addi s1,s1,1
rand_control_218:
sub s2,s3,s5
addi s1,s3,244
or s5,s1,s5
ori s2,s1,654
or s1,s2,s4
andi s1,s3,955
xori s3,s3,-1246
addi s4,s1,-1479
beq s2,s2,rand_control_227
addi s1,s1,1
rand_control_227:
ori s5,s5,1377
slli s1,s2,14
and s2,s4,s4
sll s3,s5,s4
andi s2,s2,-156
or s4,s4,s1
beq s5,s5,rand_control_234
addi s4,s4,1
rand_control_234:
bne s4,s4,rand_control_235
addi s5,s5,1
rand_control_235:
xori s3,s5,1270
xori s5,s4,-911
sll s4,s1,s5
addi s2,s2,-866
or s5,s5,s5
bne s4,s4,rand_control_241
addi s3,s3,1
rand_control_241:
bne s2,s2,rand_control_242
addi s4,s4,1
rand_control_242:
xor s4,s5,s2
slt s2,s2,s4
bne s2,s2,rand_control_245
addi s5,s5,1
rand_control_245:
srl s3,s1,s2
srl s2,s5,s1
and s1,s3,s4
andi s4,s5,-1849
sltu s1,s3,s3
beq s5,s5,rand_control_251
addi s4,s4,1
rand_control_251:
sltu s1,s3,s3
slt s2,s3,s1
slli s2,s2,11
srl s1,s3,s4
xori s1,s5,1103
slt s5,s1,s3
slli s3,s2,16
sll s2,s1,s5
srai s2,s4,24
or s4,s3,s4
sltu s2,s3,s4
srli s3,s1,31
sub s2,s4,s5
sub s3,s5,s5
srl s5,s5,s3
xor s3,s3,s4
add s2,s4,s3
ori s2,s4,1796
sub s4,s1,s3
and s2,s4,s1
srl s3,s3,s4
xor s3,s1,s3
sltu s5,s5,s4
sub s5,s5,s2
ori s2,s5,-1202
bne s2,s2,rand_control_277
addi s3,s3,1
rand_control_277:
andi s3,s1,1797
or s5,s3,s2
srl s4,s5,s2
srl s3,s1,s1
or s2,s1,s3
xor s5,s3,s3
and s3,s1,s1
beq s3,s3,rand_control_285
addi s1,s1,1
rand_control_285:
sll s1,s4,s2
xor s2,s1,s4
sltu s3,s5,s2
slli s2,s2,11
srai s1,s4,9
srli s4,s3,11
beq s1,s1,rand_control_292
addi s5,s5,1
rand_control_292:
add s1,s4,s5
xor s2,s4,s1
or s4,s2,s1
and s4,s3,s5
and s5,s1,s1
sll s5,s4,s1
beq s4,s4,rand_control_299
addi s4,s4,1
rand_control_299:
add s2,s1,s1
or s4,s5,s4
slli s3,s1,0
srai s5,s2,1
sub s1,s3,s3
xori s1,s5,1824
slt s1,s2,s5
sltu s2,s4,s5
srli s4,s3,18
sltu s2,s4,s1
srl s5,s2,s3
sll s5,s4,s3
sll s5,s4,s5
add s5,s2,s5
srli s4,s5,29
andi s1,s2,1499
beq s4,s4,rand_control_316
addi s5,s5,1
rand_control_316:
add s5,s2,s5
andi s1,s5,-1277
srl s4,s1,s4
xori s2,s4,662
bne s2,s2,rand_control_321
addi s1,s1,1
rand_control_321:
slli s2,s3,5
addi s4,s4,1813
slt s5,s2,s3
sltu s5,s4,s5
srai s5,s3,1
andi s5,s5,41
andi s3,s2,-724
and s2,s4,s1
srli s5,s2,22
add s2,s3,s1
srli s3,s4,5
srai s3,s4,11
add s2,s1,s4
sub s2,s4,s3
or s1,s5,s1
ori s4,s3,-1549
slli s4,s3,8
addi s5,s2,1675
bne s2,s2,rand_control_340
addi s5,s5,1
rand_control_340:
beq s2,s2,rand_control_341
addi s2,s2,1
rand_control_341:
or s4,s1,s5
sltu s1,s2,s4
srl s5,s4,s2
and s2,s5,s4
andi s5,s5,1251
sltu s3,s2,s1
ori s5,s3,99
xori s5,s1,753
beq s3,s3,rand_control_350
addi s3,s3,1
rand_control_350:
addi s3,s2,787
and s3,s4,s4
slli s1,s3,10
xor s4,s1,s1
sub s3,s5,s1
bne s3,s3,rand_control_356
addi s2,s2,1
rand_control_356:
sub s1,s1,s5
sll s5,s5,s1
slt s5,s3,s4
ori s4,s2,1415
ori s3,s2,-212
sll s2,s1,s1
sub s2,s1,s4
srli s1,s5,9
andi s2,s1,-278
and s3,s1,s2
srl s3,s4,s2
slt s3,s4,s3
bne s3,s3,rand_control_369
addi s2,s2,1
rand_control_369:
xori s2,s5,-1144
srl s5,s1,s4
sltu s4,s2,s3
slt s4,s5,s3
ori s1,s4,54
or s2,s2,s5
and s2,s3,s5
srli s2,s5,14
sll s3,s3,s3
slt s3,s3,s5
beq s1,s1,rand_control_380
addi s3,s3,1
rand_control_380:
srli s5,s5,12
and s3,s1,s5
sub s2,s3,s4
andi s4,s1,1896
sub s5,s3,s5
ori s1,s3,1114
beq s3,s3,rand_control_387
addi s3,s3,1
rand_control_387:
and s5,s3,s2
and s5,s2,s1
slli s1,s5,11
slt s1,s5,s5
sll s2,s2,s1
beq s2,s2,rand_control_393
addi s1,s1,1
rand_control_393:
srli s3,s5,14
xor s5,s3,s2
andi s4,s3,-744
andi s3,s4,987
andi s2,s5,-1306
srli s4,s4,25
beq s2,s2,rand_control_400
addi s3,s3,1
rand_control_400:
xor s5,s3,s5
addi s2,s5,566
bne s2,s2,rand_control_403
addi s1,s1,1
rand_control_403:
srli s2,s1,27
srli s4,s5,23
srl s3,s5,s3
andi s4,s4,132
and s5,s5,s2
and s2,s5,s3
bne s5,s5,rand_control_410
addi s5,s5,1
rand_control_410:
bne s2,s2,rand_control_411
addi s4,s4,1
rand_control_411:
sll s5,s1,s2
add s4,s5,s1
sltu s3,s2,s5
srli s5,s5,25
sub s1,s1,s2
sltu s2,s4,s4
xori s5,s3,-936
addi s5,s5,300
sll s1,s1,s3
bne s1,s1,rand_control_421
addi s3,s3,1
rand_control_421:
xor s5,s2,s4
srli s3,s3,23
xor s4,s4,s1
sub s4,s5,s3
andi s1,s1,373
sub s2,s2,s3
srai s1,s2,28
beq s4,s4,rand_control_429
addi s3,s3,1
rand_control_429:
srli s4,s5,11
xori s5,s1,-764
sub s2,s3,s1
sll s4,s2,s1
srai s3,s2,29
add s5,s3,s3
sub s5,s2,s1
add s5,s1,s5
or s5,s1,s2
or s3,s5,s1
srli s3,s4,18
add s2,s2,s2
or s4,s3,s5
srl s1,s2,s3
srai s2,s4,13
and s1,s3,s1
srli s2,s2,12
sll s4,s3,s1
sll s5,s2,s2
slli s4,s2,1
srli s3,s4,29
addi s5,s5,1828
xor s5,s1,s4
bne s1,s1,rand_control_453
addi s1,s1,1
rand_control_453:
add s2,s1,s5
addi s5,s3,-203
srli s3,s1,31
srli s1,s4,23
sltu s3,s1,s3
srli s3,s3,6
or s3,s5,s3
beq s1,s1,rand_control_461
addi s3,s3,1
rand_control_461:
srli s5,s2,19
xori s4,s3,1039
slli s3,s4,17
and s4,s3,s3
sll s5,s5,s2
xor s5,s5,s3
and s2,s2,s4
srai s2,s2,1
srai s2,s3,11
srl s3,s3,s2
slli s2,s3,24
srli s5,s2,20
xor s2,s5,s5
srl s5,s1,s1
beq s2,s2,rand_control_476
addi s4,s4,1
rand_control_476:
srai s2,s2,18
xori s3,s4,-1054
add s1,s5,s2
srl s2,s3,s3
srli s2,s5,17
slli s3,s5,1
add s2,s3,s1
ori s3,s4,-457
srl s4,s2,s5
ori s5,s4,1645
slli s4,s2,6
xori s2,s1,1362
andi s4,s5,296
slli s3,s1,3
slli s4,s4,28
srai s1,s5,1
ori s2,s3,-2008
xor s3,s2,s1
sub s1,s2,s2
xor s5,s5,s1
bne s5,s5,rand_control_497
addi s5,s5,1
rand_control_497:
slt s4,s3,s3
slt s5,s4,s5
and s3,s5,s4
slli s4,s5,19
sub s2,s4,s4
add s1,s3,s5
srli s4,s1,28
xor s5,s4,s5
sll s3,s4,s2
or s2,s4,s1
srai s4,s2,2
sltu s5,s5,s1
bne s4,s4,rand_control_510
addi s3,s3,1
rand_control_510:
sub s2,s4,s2
sltu s1,s5,s5
slli s3,s3,19
sll s2,s2,s1
sub s2,s4,s2
srl s2,s4,s1
srai s3,s2,22
or s1,s5,s4
xor s3,s1,s1
add s5,s1,s4
srli s1,s2,5
xor s3,s4,s5
or s5,s2,s5
addi s3,s4,878
add s5,s1,s4
and s1,s1,s4
sll s4,s4,s5
slt s3,s1,s5
andi s5,s4,-1389
slt s3,s2,s2
sltu s5,s2,s5
beq s2,s2,rand_control_532
addi s4,s4,1
rand_control_532:
srai s2,s5,25
andi s4,s3,-1564
addi s4,s3,536
add s4,s5,s5
srli s1,s2,25
addi s3,s3,-58
addi s3,s1,1204
srai s4,s1,11
beq s4,s4,rand_control_541
addi s3,s3,1
rand_control_541:
bne s5,s5,rand_control_542
addi s3,s3,1
rand_control_542:
srl s1,s4,s4
sll s5,s4,s3
bne s4,s4,rand_control_545
addi s5,s5,1
rand_control_545:
ori s4,s4,545
srl s2,s1,s3
slli s4,s4,8
srli s3,s3,29
beq s3,s3,rand_control_550
addi s5,s5,1
rand_control_550:
beq s5,s5,rand_control_551
addi s1,s1,1
rand_control_551:
srli s5,s4,8
add s2,s5,s3
sll s3,s5,s4
andi s3,s2,-942
srli s5,s4,17
beq s5,s5,rand_control_557
addi s3,s3,1
rand_control_557:
bne s4,s4,rand_control_558
addi s2,s2,1
rand_control_558:
or s3,s5,s2
sub s3,s3,s2
or s4,s4,s5
xori s1,s3,-772
or s4,s2,s3
sll s1,s2,s3
sll s4,s2,s1
xori s2,s5,-629
bne s3,s3,rand_control_567
addi s5,s5,1
rand_control_567:
xor s3,s2,s2
bne s4,s4,rand_control_569
addi s2,s2,1
rand_control_569:
andi s3,s3,555
srl s4,s4,s4
srai s3,s4,4
andi s3,s5,1298
andi s4,s2,1107
slli s1,s2,26
srl s5,s2,s2
srl s1,s4,s4
ori s3,s5,-298
bne s5,s5,rand_control_579
addi s1,s1,1
rand_control_579:
slt s4,s4,s2
beq s2,s2,rand_control_581
addi s2,s2,1
rand_control_581:
beq s2,s2,rand_control_582
addi s2,s2,1
rand_control_582:
beq s3,s3,rand_control_583
addi s3,s3,1
rand_control_583:
andi s4,s4,-1701
slt s4,s4,s4
and s3,s5,s3
sltu s5,s4,s4
or s5,s1,s2
srli s3,s2,30
slt s5,s5,s2
beq s5,s5,rand_control_591
addi s1,s1,1
rand_control_591:
srai s2,s4,13
slli s2,s4,18
slt s4,s1,s1
andi s4,s2,1772
srli s2,s2,6
addi s1,s2,1259
andi s4,s3,246
srl s1,s5,s2
slt s4,s5,s1
ori s4,s4,-744
sltu s3,s5,s3
srli s3,s1,29
srli s3,s1,25
xor s1,s1,s4
slt s3,s2,s4
beq s4,s4,rand_control_607
addi s2,s2,1
rand_control_607:
sltu s1,s5,s3
add s5,s2,s4
xori s3,s5,1866
slli s4,s3,28
xor s4,s5,s2
andi s4,s5,1515
addi s5,s2,-1596
sub s5,s5,s1
srl s3,s5,s3
slt s3,s1,s4
sub s4,s3,s1
beq s1,s1,rand_control_619
addi s1,s1,1
rand_control_619:
or s3,s4,s2
sub s2,s5,s4
slt s4,s3,s2
xori s3,s1,-506
addi s5,s5,-1295
sub s2,s2,s5
slt s3,s5,s2
srli s1,s5,25
add s1,s3,s4
and s1,s3,s5
slt s4,s5,s4
srli s4,s5,18
andi s4,s1,1503
srli s1,s4,27
sub s1,s1,s2
srai s3,s3,19
add s4,s3,s1
andi s4,s3,483
add s4,s1,s4
srl s3,s5,s4
andi s3,s4,-649
addi s3,s3,-1645
srli s4,s2,21
srli s3,s3,29
slli s4,s3,18
andi s1,s3,-1244
slli s4,s4,4
ori s2,s1,-1328
sltu s5,s5,s4
and s1,s5,s4
andi s2,s2,-462
xori s5,s1,-1131
srl s4,s2,s3
andi s1,s5,-1645
beq s5,s5,rand_control_654
addi s2,s2,1
rand_control_654:
add s3,s5,s5
bne s3,s3,rand_control_656
addi s2,s2,1
rand_control_656:
andi s3,s2,1471
srl s5,s5,s1
srli s1,s2,7
xori s3,s3,-849
add s4,s1,s3
srli s5,s5,23
sltu s2,s1,s2
slli s2,s5,26
sll s5,s4,s4
add s1,s3,s3
xori s1,s1,-1368
sltu s3,s4,s5
bne s1,s1,rand_control_669
addi s2,s2,1
rand_control_669:
beq s1,s1,rand_control_670
addi s4,s4,1
rand_control_670:
slli s1,s2,23
srai s5,s2,15
ori s1,s5,-1871
addi s4,s1,-910
bne s5,s5,rand_control_675
addi s3,s3,1
rand_control_675:
andi s5,s1,1902
add s2,s2,s2
xori s1,s4,-823
xori s3,s2,-584
slt s1,s4,s5
addi s5,s1,-60
beq s3,s3,rand_control_682
addi s3,s3,1
rand_control_682:
sub s2,s3,s2
beq s1,s1,rand_control_684
addi s5,s5,1
rand_control_684:
slli s1,s1,18
slli s5,s3,17
sll s5,s2,s4
sll s3,s4,s3
addi s1,s4,1780
sll s5,s2,s2
srai s5,s5,13
andi s3,s5,1406
sub s4,s3,s5
srl s4,s4,s3
andi s3,s3,956
sll s5,s5,s2
and s5,s3,s1
xor s3,s5,s4
add s5,s4,s4
srai s5,s2,19
srai s2,s3,21
sltu s5,s2,s1
addi s2,s2,1536
andi s5,s3,-347
add s5,s1,s5
sll s4,s3,s5
ori s5,s3,1040
and s5,s3,s3
slt s2,s5,s1
xor s3,s2,s3
slt s3,s3,s5
srli s2,s2,30
sub s1,s1,s5
ori s4,s3,-241
sll s2,s3,s3
ori s5,s3,168
slli s4,s3,20
sll s4,s1,s3
beq s5,s5,rand_control_719
addi s3,s3,1
rand_control_719:
and s3,s3,s4
andi s5,s1,-181
bne s1,s1,rand_control_722
addi s3,s3,1
rand_control_722:
add s3,s5,s1
sub s3,s1,s3
sltu s3,s2,s2
srli s2,s3,28
beq s3,s3,rand_control_727
addi s4,s4,1
rand_control_727:
ori s4,s3,-1155
bne s5,s5,rand_control_729
addi s5,s5,1
rand_control_729:
srli s2,s3,25
slli s4,s2,28
or s2,s1,s2
or s1,s2,s4
srli s3,s4,3
and s5,s2,s2
addi s2,s5,-1260
sll s1,s4,s4
or s2,s4,s4
sll s5,s2,s3
ori s3,s1,-296
xori s5,s3,1268
srli s2,s4,7
slli s1,s4,0
srai s1,s4,29
sltu s5,s4,s5
sub s1,s3,s4
slli s5,s1,8
sll s2,s3,s4
slli s4,s1,22
bne s3,s3,rand_control_750
addi s4,s4,1
rand_control_750:
addi s1,s1,221
slli s4,s1,23
addi s2,s2,455
srai s5,s5,11
add s2,s2,s5
slli s1,s5,4
sub s1,s5,s2
ori s5,s5,-1738
sll s4,s2,s1
slli s2,s2,31
srai s4,s2,27
sll s1,s5,s5
ori s2,s4,529
sll s2,s4,s1
addi s5,s1,1672
xori s3,s1,-400
and s3,s3,s3
sub s3,s5,s1
sll s4,s1,s5
srli s3,s1,4
bne s3,s3,rand_control_771
addi s1,s1,1
rand_control_771:
xor s2,s5,s4
srl s5,s1,s2
add s3,s1,s2
srai s1,s5,30
slt s1,s2,s3
sll s5,s4,s4
srl s4,s3,s1
xor s4,s3,s2
srai s3,s1,5
sll s1,s3,s2
xor s1,s4,s3
slt s5,s5,s3
srl s3,s4,s5
srli s3,s3,11
sub s5,s2,s2
sll s2,s2,s5
beq s5,s5,rand_control_788
addi s2,s2,1
rand_control_788:
beq s2,s2,rand_control_789
addi s1,s1,1
rand_control_789:
and s1,s1,s4
srai s2,s4,23
add s2,s4,s5
addi s3,s1,-180
slli s2,s5,13
addi s1,s1,1779
srli s2,s5,7
or s5,s3,s4
xor s2,s1,s3
beq s3,s3,rand_control_799
addi s1,s1,1
rand_control_799:
and s1,s4,s2
sub s1,s1,s4
beq s5,s5,rand_control_802
addi s5,s5,1
rand_control_802:
sub s5,s4,s5
srai s2,s5,27
bne s5,s5,rand_control_805
addi s4,s4,1
rand_control_805:
or s2,s5,s2
or s1,s5,s5
ori s1,s2,-1905
or s2,s4,s1
sll s2,s2,s4
ori s3,s5,435
xori s2,s1,1659
sub s3,s5,s1
sltu s4,s1,s1
and s1,s1,s4
slli s5,s4,28
add s1,s2,s5
add s3,s1,s1
andi s4,s5,764
beq s4,s4,rand_control_820
addi s3,s3,1
rand_control_820:
xori s2,s2,164
addi s5,s5,-418
andi s5,s3,390
xori s1,s1,1656
bne s1,s1,rand_control_825
addi s2,s2,1
rand_control_825:
slli s2,s4,0
srl s1,s4,s5
xor s5,s5,s3
xori s5,s4,-665
sltu s1,s5,s5
addi s3,s4,-1333
add s1,s2,s4
srai s2,s3,0
srli s5,s3,1
xor s1,s5,s3
slli s3,s1,1
bne s5,s5,rand_control_837
addi s4,s4,1
rand_control_837:
or s4,s1,s2
xor s3,s1,s2
sub s5,s3,s5
srai s4,s5,30
and s5,s1,s3
xor s5,s2,s3
sltu s4,s4,s1
beq s1,s1,rand_control_845
addi s4,s4,1
rand_control_845:
bne s1,s1,rand_control_846
addi s1,s1,1
rand_control_846:
srai s2,s3,24
or s1,s4,s1
slt s2,s2,s5
srai s5,s2,10
xori s4,s1,1039
beq s1,s1,rand_control_852
addi s3,s3,1
rand_control_852:
slt s2,s2,s1
slli s4,s3,4
sltu s5,s4,s3
bne s5,s5,rand_control_856
addi s4,s4,1
rand_control_856:
beq s2,s2,rand_control_857
addi s2,s2,1
rand_control_857:
sub s3,s3,s1
sub s4,s5,s1
slli s5,s4,12
srl s3,s5,s3
srai s5,s2,26
sll s4,s3,s3
sub s3,s1,s2
addi s3,s3,1029
bne s5,s5,rand_control_866
addi s5,s5,1
rand_control_866:
addi s1,s3,144
sltu s1,s5,s3
sltu s5,s1,s5
ori s5,s2,-952
slt s4,s4,s1
slt s5,s1,s3
or s5,s4,s1
andi s3,s2,1349
addi s2,s3,-312
sltu s5,s2,s3
sltu s1,s2,s3
xor s3,s3,s4
slt s2,s5,s2
addi s4,s3,-220
srai s5,s2,14
sll s2,s3,s1
andi s2,s1,1263
beq s5,s5,rand_control_884
addi s3,s3,1
rand_control_884:
xor s1,s3,s1
andi s3,s2,-202
beq s4,s4,rand_control_887
addi s1,s1,1
rand_control_887:
or s5,s1,s4
and s4,s4,s5
sub s1,s1,s1
slt s5,s5,s1
add s2,s4,s1
andi s2,s3,1786
xori s3,s1,1383
slli s2,s2,29
add s1,s3,s4
slt s1,s2,s3
sltu s2,s3,s1
sll s4,s1,s4
beq s1,s1,rand_control_900
addi s1,s1,1
rand_control_900:
sltu s1,s2,s1
xor s3,s2,s3
slt s5,s1,s1
sll s3,s4,s2
srai s4,s5,3
sub s3,s1,s2
srl s3,s4,s1
bne s5,s5,rand_control_908
addi s5,s5,1
rand_control_908:
bne s1,s1,rand_control_909
addi s3,s3,1
rand_control_909:
andi s3,s1,1849
add s4,s5,s2
bne s3,s3,rand_control_912
addi s5,s5,1
rand_control_912:
ori s2,s1,-23
bne s4,s4,rand_control_914
addi s1,s1,1
rand_control_914:
sub s5,s3,s4
and s5,s3,s2
ori s3,s4,-872
srai s2,s2,24
and s4,s5,s1
xor s5,s5,s2
srai s3,s4,28
andi s4,s5,1216
andi s1,s2,1358
sltu s1,s5,s2
andi s1,s3,2029
xor s2,s1,s4
slli s5,s1,30
xori s1,s5,1791
ori s1,s4,-582
xori s4,s5,1409
slt s4,s4,s3
slt s2,s2,s5
xor s2,s3,s4
xori s3,s3,1175
srl s5,s4,s2
beq s1,s1,rand_control_936
addi s5,s5,1
rand_control_936:
slli s3,s4,0
xor s1,s2,s3
ori s5,s4,1648
sub s2,s4,s2
andi s3,s2,-1529
sll s1,s3,s1
andi s1,s1,40
add s2,s4,s2
ori s2,s4,781
slli s2,s3,1
xor s4,s3,s2
bne s3,s3,rand_control_948
addi s3,s3,1
rand_control_948:
addi s2,s5,1846
slt s1,s4,s3
srai s3,s3,30
srl s2,s1,s3
bne s2,s2,rand_control_953
addi s2,s2,1
rand_control_953:
slt s2,s1,s1
and s4,s2,s3
beq s1,s1,rand_control_956
addi s3,s3,1
rand_control_956:
sub s5,s2,s3
slt s5,s3,s3
slli s3,s3,14
sub s3,s5,s5
andi s4,s2,-356
srl s4,s3,s3
bne s4,s4,rand_control_963
addi s1,s1,1
rand_control_963:
slt s4,s4,s1
xor s3,s5,s4
or s1,s1,s2
bne s5,s5,rand_control_967
addi s1,s1,1
rand_control_967:
srl s3,s5,s2
xori s2,s5,1544
andi s2,s5,-1239
slli s1,s5,19
sub s4,s3,s4
and s4,s3,s4
sub s1,s2,s5
srl s2,s5,s3
addi s4,s5,299
srai s3,s4,29
add s3,s4,s3
xor s4,s5,s5
andi s5,s1,-1381
bne s2,s2,rand_control_981
addi s4,s4,1
rand_control_981:
slt s1,s1,s2
ori s3,s2,-750
sub s3,s3,s2
beq s2,s2,rand_control_985
addi s4,s4,1
rand_control_985:
slt s5,s3,s2
sltu s3,s2,s1
srli s3,s5,16
sll s1,s5,s2
xor s4,s2,s3
andi s5,s2,240
add s1,s2,s2
xori s4,s2,1793
sub s2,s1,s2
addi s5,s1,230
slt s1,s4,s1
xor s5,s2,s4
sll s3,s2,s3
slli s1,s5,18
xori s2,s5,857
slli s2,s1,0
sub s2,s4,s4
slli s4,s2,27
add s1,s1,s3
srai s4,s3,5
bne s5,s5,rand_control_1006
addi s2,s2,1
rand_control_1006:
srl s5,s5,s3
bne s4,s4,rand_control_1008
addi s1,s1,1
rand_control_1008:
add s5,s1,s5
add s5,s1,s2
sll s1,s4,s2
slt s2,s5,s5
srli s4,s3,9
ori s5,s3,1823
or s5,s4,s3
or s5,s2,s5
srli s3,s5,30
add s5,s2,s4
srl s2,s4,s5
add s1,s4,s4
srl s4,s1,s3
xori s5,s5,202
sll s3,s1,s1
xori s1,s5,459
ori s1,s5,-1530
ori s2,s4,1389
andi s5,s4,931
slt s5,s2,s3
addi s3,s2,808
srai s2,s3,14
sub s4,s4,s5
beq s4,s4,rand_control_1032
addi s2,s2,1
rand_control_1032:
add s5,s2,s5
xori s4,s4,1460
andi s1,s2,-1432
or s4,s3,s4
srli s1,s1,27
slli s5,s1,13
xori s5,s1,-1249
and s5,s2,s4
beq s2,s2,rand_control_1041
addi s2,s2,1
rand_control_1041:
sll s5,s4,s5
sll s5,s3,s3
sll s3,s2,s5
slli s5,s1,3
sltu s3,s3,s2
xori s3,s2,108
srl s1,s5,s3
slt s2,s5,s2
and s1,s5,s5
bne s3,s3,rand_control_1051
addi s2,s2,1
rand_control_1051:
srai s1,s2,0
beq s2,s2,rand_control_1053
addi s1,s1,1
rand_control_1053:
add s3,s1,s4
srl s1,s3,s1
addi s3,s3,1804
and s4,s5,s5
srl s1,s4,s3
srl s5,s4,s2
ori s2,s1,1741
and s2,s3,s5
sub s1,s2,s1
sltu s3,s4,s5
sltu s5,s3,s3
or s3,s5,s2
and s5,s2,s3
srli s1,s3,5
xor s1,s2,s2
or s3,s5,s4
addi s5,s1,1111
slt s3,s2,s1
sll s2,s4,s3
srai s3,s2,9
and s4,s5,s5
ori s1,s5,-1060
addi s5,s4,623
beq s1,s1,rand_control_1077
addi s3,s3,1
rand_control_1077:
srli s5,s4,14
xori s5,s5,-1757
and s4,s2,s3
add s3,s4,s5
sub s1,s2,s4
xor s4,s3,s2
beq s1,s1,rand_control_1084
addi s4,s4,1
rand_control_1084:
and s4,s2,s2
srl s5,s5,s1
xor s1,s4,s5
slt s5,s4,s2
xori s2,s3,-549
beq s1,s1,rand_control_1090
addi s1,s1,1
rand_control_1090:
sll s1,s5,s2
addi s5,s2,1660
andi s5,s3,-1321
or s4,s1,s4
srli s5,s2,12
srli s5,s3,10
sll s1,s1,s2
addi s1,s4,292
addi s3,s5,0
srl s1,s3,s1
slt s5,s3,s2
or s1,s3,s5
addi s1,s4,1263
srl s3,s3,s5
srli s3,s2,21
slli s4,s3,23
beq s3,s3,rand_control_1107
addi s4,s4,1
rand_control_1107:
beq s3,s3,rand_control_1108
addi s3,s3,1
rand_control_1108:
or s1,s1,s4
xori s1,s2,-1749
ori s5,s5,1707
sll s2,s1,s2
sub s1,s4,s3
sub s1,s3,s5
sub s4,s3,s2
ori s2,s1,-1688
or s2,s5,s3
ori s4,s1,-196
sltu s1,s3,s5
sll s5,s2,s5
sub s2,s1,s1
and s4,s4,s5
andi s4,s1,476
andi s2,s4,-1663
andi s4,s1,1260
srai s5,s1,10
andi s4,s4,1830
srli s2,s5,28
bne s3,s3,rand_control_1129
addi s4,s4,1
rand_control_1129:
srli s4,s1,3
srli s1,s3,21
add s2,s2,s5
beq s4,s4,rand_control_1133
addi s5,s5,1
rand_control_1133:
sll s4,s5,s1
xori s4,s5,-1547
xor s5,s1,s5
srli s1,s3,3
srai s4,s1,10
slli s5,s1,3
and s2,s1,s5
addi s1,s5,-1761
sll s1,s2,s4
addi s3,s1,668
add s2,s1,s5
srli s1,s5,28
sll s4,s4,s3
xor s4,s3,s2
and s5,s5,s4
ori s2,s4,-2036
srai s2,s4,18
slt s1,s5,s2
xor s1,s1,s2
xori s4,s4,1011
xor s1,s1,s1
or s5,s1,s1
addi s2,s2,-1241
ori s3,s2,-1490
ori s1,s2,1490
andi s4,s2,1741
xor s4,s1,s5
sll s1,s4,s3
xori s5,s5,-52
addi s5,s5,-608
ori s1,s5,48
xori s4,s4,670
xor s2,s3,s2
add s5,s3,s3
or s5,s2,s2
bne s4,s4,rand_control_1169
addi s5,s5,1
rand_control_1169:
or s3,s5,s5
bne s1,s1,rand_control_1171
addi s3,s3,1
rand_control_1171:
slli s5,s1,31
slt s5,s5,s3
add s1,s2,s5
sltu s1,s3,s1
sltu s4,s1,s1
add s3,s1,s5
sub s5,s2,s2
srl s3,s1,s5
addi s2,s1,583
ori s5,s5,-520
xor s3,s3,s2
addi s3,s3,1231
add s2,s5,s3
slt s2,s5,s2
xori s3,s3,614
bne s2,s2,rand_control_1187
addi s2,s2,1
rand_control_1187:
or s4,s2,s4
and s4,s3,s3
srli s2,s3,21
andi s3,s1,298
srai s3,s3,9
or s4,s4,s2
and s4,s3,s5
srli s5,s3,14
bne s2,s2,rand_control_1196
addi s1,s1,1
rand_control_1196:
andi s3,s1,-1211
beq s1,s1,rand_control_1198
addi s2,s2,1
rand_control_1198:
andi s1,s2,-606

  li a0, 1
  li a1, 0x8003f000
  sw a0, 0(a1)
.globl halt_pass
halt_pass:
  j halt_pass
fail:
  li a0, 2
  li a1, 0x8003f000
  sw a0, 0(a1)
fail_loop:
  j fail_loop

.section .data
.balign 16
scratch: .space 256

