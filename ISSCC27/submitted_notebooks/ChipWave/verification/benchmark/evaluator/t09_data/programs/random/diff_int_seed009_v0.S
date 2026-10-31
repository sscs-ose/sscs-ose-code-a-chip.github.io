.option norvc
.section .text.init
.globl _start
_start:
la s0,scratch
li t0,0x90000000
li s1,4014706333
li s2,355841470
li s3,2596483563
li s4,894221863
li s5,2305869653
sll s3,s3,s5
sub s1,s5,s1
beq s3,s3,rand_control_2
addi s1,s1,1
rand_control_2:
beq s4,s4,rand_control_3
addi s4,s4,1
rand_control_3:
xor s3,s5,s5
andi s1,s4,164
slli s5,s1,7
sll s3,s4,s3
ori s3,s5,-455
addi s2,s5,219
srai s1,s1,24
sll s3,s4,s1
and s4,s3,s3
and s3,s3,s5
addi s4,s2,-1170
sll s4,s1,s4
srli s4,s1,17
slli s4,s5,24
srli s1,s3,24
srl s2,s3,s2
and s5,s1,s2
ori s3,s4,-1089
slli s5,s2,22
slt s1,s4,s3
sll s1,s2,s2
xori s1,s4,-555
add s3,s1,s3
srai s1,s4,21
xor s5,s3,s4
slt s2,s2,s1
sll s3,s1,s1
beq s4,s4,rand_control_31
addi s2,s2,1
rand_control_31:
srl s5,s1,s5
slli s2,s2,23
xor s2,s2,s2
sll s5,s2,s3
slt s4,s2,s3
sll s4,s3,s5
slli s3,s3,9
andi s1,s4,-1082
srai s3,s2,24
andi s2,s1,-1672
andi s5,s1,-143
addi s1,s3,-384
slli s1,s2,4
sub s1,s5,s2
addi s5,s3,312
srl s3,s4,s5
srli s3,s2,8
sub s5,s4,s4
ori s5,s2,598
slli s2,s4,5
bne s3,s3,rand_control_52
addi s3,s3,1
rand_control_52:
bne s1,s1,rand_control_53
addi s1,s1,1
rand_control_53:
add s5,s2,s3
xori s1,s4,129
and s4,s1,s5
andi s2,s3,969
sltu s1,s5,s4
and s5,s1,s1
bne s5,s5,rand_control_60
addi s1,s1,1
rand_control_60:
add s1,s3,s3
srai s1,s4,25
ori s3,s3,-1165
xori s3,s3,-304
andi s4,s4,-133
and s5,s2,s1
sub s3,s1,s1
slli s5,s1,31
slli s1,s4,5
andi s5,s4,1265
slli s5,s3,20
add s1,s4,s4
ori s1,s4,364
add s3,s2,s3
addi s2,s2,-818
srai s1,s2,5
slt s5,s1,s4
andi s1,s2,-410
srli s1,s5,16
srai s2,s3,7
xor s5,s2,s1
beq s1,s1,rand_control_82
addi s4,s4,1
rand_control_82:
andi s5,s2,1417
and s1,s3,s4
srli s4,s2,26
srai s5,s2,26
srl s3,s1,s1
and s5,s5,s2
or s4,s1,s5
and s4,s3,s5
srl s1,s4,s5
sll s4,s5,s1
beq s3,s3,rand_control_93
addi s2,s2,1
rand_control_93:
andi s3,s3,-1912
srl s2,s5,s3
srl s1,s4,s2
or s5,s4,s4
bne s5,s5,rand_control_98
addi s5,s5,1
rand_control_98:
andi s2,s1,442
srl s1,s3,s3
sltu s3,s4,s5
srli s1,s3,12
ori s2,s3,-1900
srai s1,s1,4
slt s1,s3,s3
srl s4,s3,s2
srli s5,s1,30
add s2,s4,s5
xori s4,s3,-235
sll s4,s4,s5
sub s5,s3,s3
ori s4,s1,219
and s2,s5,s3
add s4,s1,s4
slli s3,s2,10
sub s2,s1,s4
beq s4,s4,rand_control_117
addi s1,s1,1
rand_control_117:
srl s5,s3,s1
ori s5,s1,-121
sltu s3,s2,s3
addi s2,s4,1595
bne s3,s3,rand_control_122
addi s1,s1,1
rand_control_122:
or s5,s3,s4
add s5,s5,s2
or s4,s5,s3
sltu s2,s1,s4
srli s1,s4,0
addi s1,s1,-1656
sltu s5,s2,s5
beq s5,s5,rand_control_130
addi s4,s4,1
rand_control_130:
xor s3,s1,s3
sltu s3,s5,s5
xor s5,s2,s5
beq s1,s1,rand_control_134
addi s5,s5,1
rand_control_134:
andi s1,s2,1128
slli s3,s1,0
xor s1,s2,s2
beq s1,s1,rand_control_138
addi s3,s3,1
rand_control_138:
xor s4,s4,s5
slli s4,s1,16
srai s4,s5,17
add s3,s2,s3
sll s1,s4,s1
xor s2,s2,s2
xori s2,s2,798
srai s2,s5,11
beq s5,s5,rand_control_147
addi s3,s3,1
rand_control_147:
srai s3,s4,26
slli s1,s1,5
add s5,s5,s2
srli s2,s4,27
sub s3,s4,s3
sll s1,s1,s4
sll s1,s3,s5
sll s3,s3,s5
beq s4,s4,rand_control_156
addi s4,s4,1
rand_control_156:
srai s3,s5,12
srli s4,s3,27
sll s1,s1,s5
beq s5,s5,rand_control_160
addi s4,s4,1
rand_control_160:
andi s1,s5,868
srl s3,s3,s5
srl s1,s5,s2
and s2,s3,s2
xori s2,s5,1064
addi s5,s4,-1219
srai s2,s3,11
add s4,s5,s5
addi s1,s3,1032
and s3,s5,s5
srli s1,s4,18
xor s4,s3,s4
beq s3,s3,rand_control_173
addi s1,s1,1
rand_control_173:
srl s3,s5,s3
add s3,s4,s1
srl s3,s2,s1
sltu s5,s5,s4
sltu s1,s3,s5
sltu s2,s2,s1
sub s3,s4,s4
slli s2,s2,14
ori s2,s4,373
srl s3,s5,s5
sll s5,s5,s5
slli s1,s3,12
addi s5,s3,-16
sltu s4,s2,s1
ori s3,s3,1851
addi s3,s1,-1803
add s1,s3,s5
srl s1,s1,s3
bne s5,s5,rand_control_192
addi s3,s3,1
rand_control_192:
srli s5,s2,13
sll s3,s1,s1
slli s3,s4,5
beq s4,s4,rand_control_196
addi s4,s4,1
rand_control_196:
sll s5,s5,s2
or s2,s5,s2
beq s4,s4,rand_control_199
addi s2,s2,1
rand_control_199:
sub s1,s5,s1
sub s3,s1,s5
srl s4,s4,s3
srai s1,s5,27
sll s1,s4,s1
srl s2,s5,s5
addi s4,s2,1737
sub s5,s1,s5
slt s5,s2,s4
xori s1,s3,1564
slli s4,s3,21
ori s1,s3,1801
xori s5,s2,-1823
sll s4,s4,s5
slt s3,s1,s2
srai s2,s1,27
andi s2,s2,-643
andi s2,s2,-311
sll s5,s4,s1
slli s4,s4,9
bne s4,s4,rand_control_220
addi s4,s4,1
rand_control_220:
xor s2,s4,s4
srli s5,s5,7
or s3,s4,s3
and s5,s2,s2
add s5,s4,s2
srai s2,s4,30
srai s3,s4,31
srai s5,s4,2
xori s2,s1,-52
srai s5,s1,29
beq s2,s2,rand_control_231
addi s4,s4,1
rand_control_231:
xori s4,s4,-1690
srli s1,s4,10
srl s3,s4,s3
srai s4,s4,6
sltu s2,s2,s5
xori s4,s5,702
xor s3,s3,s2
xor s2,s2,s1
srai s1,s5,16
srli s4,s4,4
slt s3,s3,s1
addi s1,s5,-1948
and s5,s5,s2
sltu s4,s3,s3
beq s3,s3,rand_control_246
addi s1,s1,1
rand_control_246:
sub s1,s4,s1
beq s4,s4,rand_control_248
addi s4,s4,1
rand_control_248:
ori s2,s5,294
srli s3,s1,28
xor s4,s2,s4
sltu s5,s3,s1
sll s4,s2,s2
sub s4,s5,s5
sltu s5,s3,s2
slt s3,s5,s3
srl s3,s2,s1
beq s1,s1,rand_control_258
addi s2,s2,1
rand_control_258:
ori s3,s4,-1097
xori s3,s2,1184
slli s2,s5,24
bne s2,s2,rand_control_262
addi s1,s1,1
rand_control_262:
xor s3,s1,s3
beq s5,s5,rand_control_264
addi s5,s5,1
rand_control_264:
srli s1,s1,5
andi s4,s5,363
sll s1,s1,s1
beq s5,s5,rand_control_268
addi s5,s5,1
rand_control_268:
and s4,s4,s1
srai s1,s2,7
ori s3,s1,-465
xor s1,s4,s3
addi s3,s3,1259
sll s4,s5,s3
sltu s1,s1,s1
add s4,s5,s5
and s1,s5,s4
andi s5,s2,1569
xor s4,s4,s5
beq s1,s1,rand_control_280
addi s4,s4,1
rand_control_280:
beq s2,s2,rand_control_281
addi s5,s5,1
rand_control_281:
slli s3,s5,3
ori s4,s1,-1511
srai s3,s5,13
srai s4,s1,9
sltu s1,s5,s3
slli s1,s2,5
add s5,s2,s1
sub s2,s3,s5
addi s3,s3,-1622
sltu s5,s2,s1
srli s2,s2,28
srl s4,s3,s2
beq s5,s5,rand_control_294
addi s4,s4,1
rand_control_294:
add s3,s5,s5
andi s1,s5,1560
sll s2,s1,s1
slt s2,s5,s5
addi s2,s4,-57
addi s1,s2,-586
sub s1,s1,s3
beq s2,s2,rand_control_302
addi s5,s5,1
rand_control_302:
slt s1,s1,s2
andi s2,s2,-484
addi s2,s4,1286
srai s5,s5,6
slt s3,s5,s1
andi s2,s2,1817
sub s3,s2,s3
sltu s4,s3,s2
or s5,s4,s1
sub s4,s4,s4
andi s4,s4,1869
srli s3,s2,26
sub s3,s5,s2
srli s5,s2,28
addi s2,s3,172
srli s2,s2,11
or s5,s2,s1
sltu s2,s1,s3
sll s5,s1,s1
sub s3,s4,s1
srli s4,s1,5
sll s2,s2,s4
bne s4,s4,rand_control_325
addi s2,s2,1
rand_control_325:
sll s3,s2,s4
and s1,s3,s1
add s1,s2,s3
addi s3,s1,-1170
sltu s1,s5,s3
srl s3,s3,s3
srai s5,s1,22
addi s2,s3,-261
srli s2,s3,20
slli s2,s5,6
xor s5,s1,s4
srai s4,s4,2
xor s4,s5,s2
sltu s4,s1,s1
or s1,s1,s1
sltu s2,s1,s4
sll s4,s2,s4
or s2,s5,s1
sltu s3,s1,s3
or s2,s1,s3
addi s5,s2,1270
srl s4,s5,s1
xori s4,s2,-1659
xor s5,s1,s2
xori s2,s4,1911
ori s5,s3,107
or s1,s3,s5
addi s4,s4,-728
slt s5,s2,s1
srl s3,s5,s4
sltu s3,s3,s3
addi s1,s2,-1232
slli s3,s4,31
ori s1,s1,228
ori s2,s1,-458
or s5,s1,s2
add s5,s4,s1
srai s2,s2,26
ori s3,s3,-1940
xori s1,s3,1924
srai s1,s5,7
sub s5,s3,s3
slli s2,s4,18
sltu s4,s1,s5
or s3,s3,s4
sll s4,s5,s1
srli s1,s5,23
slt s3,s5,s4
srli s1,s2,31
beq s5,s5,rand_control_375
addi s2,s2,1
rand_control_375:
add s2,s5,s5
srl s2,s4,s2
slli s4,s4,3
sltu s2,s5,s2
srai s3,s3,29
srli s5,s2,29
sub s5,s1,s5
sub s1,s1,s2
ori s1,s1,437
xori s3,s2,1927
sll s3,s2,s3
addi s4,s4,-576
sub s4,s2,s5
xori s2,s1,-91
add s4,s3,s5
addi s1,s4,1763
bne s4,s4,rand_control_392
addi s3,s3,1
rand_control_392:
xor s3,s5,s1
andi s4,s3,-738
sltu s2,s3,s4
slt s1,s1,s4
andi s1,s3,603
andi s1,s3,-792
xori s2,s4,344
beq s3,s3,rand_control_400
addi s2,s2,1
rand_control_400:
slli s5,s4,26
and s1,s4,s1
add s1,s1,s4
srai s5,s2,9
addi s2,s3,35
bne s1,s1,rand_control_406
addi s2,s2,1
rand_control_406:
addi s4,s2,-57
slli s5,s1,8
ori s2,s5,1487
ori s3,s1,1978
sltu s2,s2,s2
bne s2,s2,rand_control_412
addi s4,s4,1
rand_control_412:
or s3,s5,s1
addi s3,s4,-101
bne s3,s3,rand_control_415
addi s5,s5,1
rand_control_415:
and s4,s5,s5
srli s3,s2,22
srli s4,s4,3
andi s2,s5,1735
addi s1,s3,-1883
slt s1,s5,s4
bne s4,s4,rand_control_422
addi s2,s2,1
rand_control_422:
srli s1,s2,24
add s2,s1,s4
or s2,s2,s4
addi s1,s3,1903
bne s2,s2,rand_control_427
addi s2,s2,1
rand_control_427:
bne s5,s5,rand_control_428
addi s3,s3,1
rand_control_428:
slt s4,s2,s5
ori s5,s3,-1974
beq s5,s5,rand_control_431
addi s1,s1,1
rand_control_431:
slli s4,s5,21
and s3,s1,s5
sll s4,s4,s4
xor s1,s1,s4
andi s5,s3,1633
ori s2,s4,-1966
sll s1,s5,s4
sll s1,s3,s3
slt s4,s2,s2
addi s4,s4,1447
or s5,s4,s4
or s3,s5,s3
slli s1,s1,14
andi s1,s4,1921
xor s5,s3,s4
sub s1,s3,s4
sll s2,s3,s1
sub s3,s3,s1
slli s4,s2,11
addi s4,s1,649
addi s4,s5,684
srai s1,s5,5
xori s2,s4,-1298
or s1,s5,s3
and s1,s2,s2
andi s1,s4,1845
srai s2,s4,29
xor s1,s1,s5
srai s4,s5,31
srl s4,s5,s4
sll s5,s2,s4
add s3,s1,s4
xor s4,s4,s5
slli s5,s1,18
bne s4,s4,rand_control_466
addi s5,s5,1
rand_control_466:
sltu s3,s4,s1
srai s1,s2,21
sub s1,s4,s3
srai s2,s4,31
bne s2,s2,rand_control_471
addi s1,s1,1
rand_control_471:
srai s2,s4,13
add s5,s1,s4
sub s2,s1,s1
ori s5,s1,-1518
xor s2,s5,s2
bne s5,s5,rand_control_477
addi s2,s2,1
rand_control_477:
and s5,s3,s2
sub s5,s4,s3
ori s5,s3,2000
add s2,s1,s4
srl s2,s5,s1
ori s4,s5,-989
addi s3,s5,-105
sltu s3,s3,s1
or s2,s5,s3
ori s3,s4,1477
addi s4,s3,-458
sltu s2,s4,s5
xori s5,s5,-1997
srl s1,s2,s1
srl s4,s2,s1
andi s3,s2,581
beq s3,s3,rand_control_494
addi s3,s3,1
rand_control_494:
xori s2,s3,332
srai s2,s3,6
beq s1,s1,rand_control_497
addi s5,s5,1
rand_control_497:
sub s3,s1,s5
or s3,s4,s3
or s1,s1,s3
srli s5,s2,12
sltu s3,s5,s3
srl s5,s4,s4
srli s1,s4,23
beq s3,s3,rand_control_505
addi s3,s3,1
rand_control_505:
andi s2,s3,-1730
and s5,s2,s1
sll s3,s3,s1
slli s3,s3,4
or s5,s3,s4
sub s5,s1,s1
add s2,s4,s4
or s1,s3,s5
sll s3,s1,s1
srl s2,s2,s2
addi s1,s4,-514
add s3,s5,s1
or s3,s3,s4
beq s5,s5,rand_control_519
addi s1,s1,1
rand_control_519:
and s4,s3,s3
srli s1,s2,15
srl s1,s5,s4
sub s2,s4,s3
bne s3,s3,rand_control_524
addi s3,s3,1
rand_control_524:
srli s2,s2,29
sub s3,s3,s3
bne s1,s1,rand_control_527
addi s3,s3,1
rand_control_527:
andi s5,s2,1464
slli s4,s1,28
xor s2,s3,s2
and s2,s5,s2
andi s3,s2,1110
sub s4,s3,s5
bne s1,s1,rand_control_534
addi s3,s3,1
rand_control_534:
addi s5,s2,-1568
slli s5,s5,21
addi s4,s4,-1098
sltu s5,s1,s2
srl s1,s5,s1
srai s3,s3,0
sub s1,s3,s1
srli s2,s2,14
ori s2,s3,-17
bne s3,s3,rand_control_544
addi s2,s2,1
rand_control_544:
xor s3,s2,s2
slt s3,s5,s4
slli s4,s4,0
add s1,s2,s5
sll s1,s3,s5
sltu s1,s3,s5
addi s3,s1,1318
sub s3,s3,s4
slt s2,s5,s4
xor s5,s3,s1
slt s5,s3,s4
srl s5,s5,s4
addi s1,s2,1262
srli s4,s5,29
or s1,s1,s4
sltu s1,s5,s1
andi s2,s4,743
slt s2,s1,s2
srl s4,s1,s2
xor s4,s4,s5
sub s5,s2,s5
xori s3,s1,347
ori s5,s2,-153
xori s5,s2,1954
xor s1,s3,s3
sltu s5,s5,s3
add s1,s2,s3
xor s3,s2,s5
xor s2,s4,s5
ori s1,s2,-1638
ori s1,s3,-1616
addi s2,s4,-1644
sub s1,s3,s4
bne s5,s5,rand_control_578
addi s2,s2,1
rand_control_578:
srai s1,s5,11
beq s1,s1,rand_control_580
addi s1,s1,1
rand_control_580:
bne s1,s1,rand_control_581
addi s2,s2,1
rand_control_581:
bne s2,s2,rand_control_582
addi s3,s3,1
rand_control_582:
addi s2,s4,-510
or s3,s3,s4
add s4,s4,s4
srai s5,s2,31
sll s1,s5,s1
sub s3,s1,s4
or s2,s3,s1
beq s1,s1,rand_control_590
addi s2,s2,1
rand_control_590:
ori s2,s1,-688
addi s3,s5,-121
slli s3,s2,17
andi s4,s2,-1293
beq s2,s2,rand_control_595
addi s2,s2,1
rand_control_595:
andi s1,s1,11
beq s2,s2,rand_control_597
addi s2,s2,1
rand_control_597:
sltu s2,s1,s4
srl s1,s2,s3
andi s1,s4,1051
addi s2,s1,1982
or s4,s1,s2
xor s5,s3,s2
or s4,s4,s2
addi s4,s3,-917
and s2,s5,s2
srai s5,s3,22
slli s1,s3,12
addi s1,s3,1491
beq s5,s5,rand_control_610
addi s4,s4,1
rand_control_610:
srl s2,s4,s1
slli s4,s1,31
srai s4,s4,9
ori s5,s2,1057
and s4,s5,s3
srli s3,s1,24
srai s1,s4,20
slt s4,s2,s3
xori s4,s2,-1150
and s3,s3,s3
beq s4,s4,rand_control_621
addi s3,s3,1
rand_control_621:
addi s2,s5,0
bne s4,s4,rand_control_623
addi s1,s1,1
rand_control_623:
srl s3,s5,s2
or s1,s4,s1
ori s2,s1,-1879
slt s2,s3,s4
sltu s3,s2,s3
sll s2,s1,s4
or s5,s5,s4
srli s2,s5,11
ori s3,s1,-1839
srai s2,s4,0
ori s2,s3,259
andi s3,s4,-1264
sll s2,s4,s1
slli s4,s1,4
srai s2,s1,17
srai s4,s4,11
xor s4,s1,s2
or s4,s3,s5
slt s3,s3,s2
beq s5,s5,rand_control_643
addi s3,s3,1
rand_control_643:
add s1,s3,s2
and s4,s4,s1
sll s3,s2,s3
and s1,s2,s4
sltu s4,s3,s5
addi s2,s4,-1183
andi s2,s2,-320
xori s2,s5,-1746
srl s1,s1,s4
slt s4,s1,s2
sub s3,s1,s1
beq s4,s4,rand_control_655
addi s2,s2,1
rand_control_655:
srl s5,s3,s1
sltu s2,s1,s3
sll s5,s1,s5
andi s4,s4,-1893
slt s1,s4,s5
or s5,s5,s1
addi s4,s4,763
srl s5,s4,s1
or s3,s1,s5
slt s3,s4,s1
bne s3,s3,rand_control_666
addi s4,s4,1
rand_control_666:
slli s4,s2,20
bne s3,s3,rand_control_668
addi s5,s5,1
rand_control_668:
xor s3,s2,s5
beq s5,s5,rand_control_670
addi s5,s5,1
rand_control_670:
slli s3,s1,21
and s1,s5,s3
srl s5,s1,s2
sub s5,s2,s5
bne s4,s4,rand_control_675
addi s4,s4,1
rand_control_675:
beq s3,s3,rand_control_676
addi s4,s4,1
rand_control_676:
slt s5,s5,s4
bne s4,s4,rand_control_678
addi s2,s2,1
rand_control_678:
bne s3,s3,rand_control_679
addi s2,s2,1
rand_control_679:
ori s5,s4,1931
andi s4,s2,1515
srai s5,s5,31
slt s3,s3,s5
and s5,s2,s3
xori s1,s4,1903
beq s1,s1,rand_control_686
addi s5,s5,1
rand_control_686:
beq s3,s3,rand_control_687
addi s3,s3,1
rand_control_687:
or s4,s2,s3
or s2,s2,s5
slt s2,s1,s1
srli s4,s4,1
srai s1,s4,5
srl s2,s1,s4
or s2,s4,s3
andi s5,s5,-1369
slt s5,s1,s1
andi s1,s4,-1786
and s5,s1,s5
and s5,s4,s3
ori s1,s1,-1058
xor s3,s5,s4
xor s3,s2,s4
srl s5,s2,s3
ori s1,s1,-406
srl s5,s1,s3
beq s1,s1,rand_control_706
addi s4,s4,1
rand_control_706:
bne s3,s3,rand_control_707
addi s5,s5,1
rand_control_707:
sub s3,s4,s2
andi s5,s1,-149
beq s5,s5,rand_control_710
addi s3,s3,1
rand_control_710:
sll s3,s3,s1
slt s5,s5,s3
addi s1,s4,-662
sll s5,s2,s2
and s2,s3,s2
bne s2,s2,rand_control_716
addi s3,s3,1
rand_control_716:
andi s2,s2,-797
andi s1,s2,-1739
srli s4,s5,28
sltu s1,s5,s1
add s4,s4,s4
and s4,s4,s3
sub s1,s1,s2
or s2,s2,s3
ori s4,s2,-1264
sll s3,s2,s2
sll s4,s3,s4
sll s5,s4,s3
sub s1,s2,s2
sltu s4,s3,s1
beq s5,s5,rand_control_731
addi s5,s5,1
rand_control_731:
ori s5,s2,1545
srai s3,s4,1
and s5,s3,s2
ori s3,s5,885
srai s2,s1,7
xor s3,s5,s3
addi s5,s2,284
xori s4,s5,-414
and s4,s1,s3
addi s2,s5,-1298
srli s5,s4,14
srl s3,s3,s4
sub s5,s1,s5
beq s2,s2,rand_control_745
addi s5,s5,1
rand_control_745:
sll s3,s2,s3
beq s2,s2,rand_control_747
addi s1,s1,1
rand_control_747:
andi s5,s5,1338
add s1,s4,s5
beq s5,s5,rand_control_750
addi s5,s5,1
rand_control_750:
srli s1,s2,10
srli s4,s3,8
srli s3,s5,29
slli s5,s3,12
or s1,s3,s3
srl s5,s5,s5
sll s1,s4,s5
srai s2,s2,15
srai s5,s5,20
slli s3,s1,7
beq s1,s1,rand_control_761
addi s2,s2,1
rand_control_761:
or s5,s5,s4
bne s3,s3,rand_control_763
addi s3,s3,1
rand_control_763:
srl s3,s5,s5
sltu s4,s4,s2
xori s1,s3,1578
slt s1,s5,s4
or s5,s1,s5
sll s5,s1,s4
andi s3,s3,15
or s4,s3,s4
sltu s5,s5,s3
sll s3,s3,s4
slt s2,s3,s2
srl s5,s5,s4
add s4,s1,s3
sll s3,s4,s3
add s5,s2,s5
beq s1,s1,rand_control_779
addi s5,s5,1
rand_control_779:
slt s2,s4,s2
slt s2,s1,s1
xori s4,s1,-1175
sll s3,s3,s4
andi s2,s1,1862
and s4,s5,s5
sll s2,s5,s3
xori s2,s5,-672
ori s2,s4,909
ori s1,s3,1254
srli s4,s2,9
slt s5,s2,s2
beq s5,s5,rand_control_792
addi s1,s1,1
rand_control_792:
srl s3,s3,s3
slli s3,s3,19
xori s1,s1,129
bne s4,s4,rand_control_796
addi s2,s2,1
rand_control_796:
slt s1,s2,s2
andi s1,s2,-176
bne s5,s5,rand_control_799
addi s5,s5,1
rand_control_799:
add s4,s1,s1
bne s1,s1,rand_control_801
addi s1,s1,1
rand_control_801:
xor s4,s3,s3
srli s5,s5,20
sub s3,s4,s2
ori s2,s4,1031
xori s5,s1,-141
addi s1,s1,1263
andi s4,s2,-1623
add s3,s2,s3
srai s1,s4,6
andi s4,s3,-518
and s2,s5,s3
and s3,s2,s2
bne s2,s2,rand_control_814
addi s1,s1,1
rand_control_814:
andi s5,s2,-1601
slt s4,s2,s4
srai s5,s2,10
sltu s5,s4,s5
bne s2,s2,rand_control_819
addi s5,s5,1
rand_control_819:
or s3,s1,s4
srl s4,s2,s3
bne s3,s3,rand_control_822
addi s2,s2,1
rand_control_822:
addi s5,s3,129
srai s1,s4,18
addi s3,s4,-1294
or s3,s1,s3
xor s1,s3,s2
and s1,s5,s3
slli s2,s5,19
or s5,s1,s1
and s3,s1,s4
xor s5,s5,s3
bne s1,s1,rand_control_833
addi s2,s2,1
rand_control_833:
sltu s5,s3,s4
ori s2,s5,-371
xori s3,s2,-254
beq s2,s2,rand_control_837
addi s2,s2,1
rand_control_837:
srli s3,s2,2
srai s5,s3,30
srli s5,s5,23
srli s2,s3,11
slt s3,s5,s2
sll s5,s2,s4
andi s3,s4,1417
srai s4,s1,16
sll s3,s4,s2
sub s1,s4,s4
beq s1,s1,rand_control_848
addi s4,s4,1
rand_control_848:
ori s2,s2,590
sub s5,s5,s2
srli s4,s2,27
slt s4,s1,s2
or s5,s2,s5
bne s1,s1,rand_control_854
addi s5,s5,1
rand_control_854:
sll s4,s1,s3
ori s4,s3,-607
add s5,s1,s1
or s1,s5,s1
andi s1,s3,-1769
slli s4,s2,8
slli s4,s5,3
addi s4,s3,1999
xor s2,s2,s2
xori s4,s4,-1417
xor s2,s5,s4
xor s1,s3,s1
srl s1,s1,s2
bne s2,s2,rand_control_868
addi s5,s5,1
rand_control_868:
andi s5,s5,783
addi s1,s4,1074
beq s1,s1,rand_control_871
addi s4,s4,1
rand_control_871:
addi s4,s5,1501
add s1,s3,s5
sltu s4,s1,s1
xor s3,s3,s5
andi s3,s2,1019
xor s5,s3,s4
addi s1,s4,179
slli s3,s3,8
beq s3,s3,rand_control_880
addi s4,s4,1
rand_control_880:
beq s2,s2,rand_control_881
addi s4,s4,1
rand_control_881:
sltu s4,s3,s5
sltu s5,s2,s1
addi s1,s3,328
xori s2,s1,-418
sub s2,s2,s1
sltu s4,s2,s4
or s1,s3,s4
xori s1,s3,-1805
andi s4,s1,1038
xori s1,s4,-992
bne s3,s3,rand_control_892
addi s5,s5,1
rand_control_892:
and s3,s3,s3
addi s5,s3,-73
bne s4,s4,rand_control_895
addi s4,s4,1
rand_control_895:
srai s5,s5,25
srai s2,s5,8
sll s2,s5,s2
slli s5,s4,9
sll s4,s4,s2
add s4,s2,s2
srli s4,s3,28
add s4,s5,s3
xori s1,s4,-1686
sltu s1,s1,s2
and s2,s2,s5
and s3,s5,s1
slt s3,s1,s5
slt s3,s3,s3
beq s4,s4,rand_control_910
addi s1,s1,1
rand_control_910:
slli s1,s4,9
sltu s4,s4,s3
ori s2,s1,-21
and s2,s2,s1
andi s1,s3,-828
slli s4,s1,9
srl s1,s3,s5
xor s3,s5,s1
and s1,s5,s2
and s3,s4,s5
addi s1,s4,-295
ori s4,s4,-23
andi s3,s5,-761
addi s1,s2,1658
sll s1,s3,s1
xor s2,s1,s4
andi s1,s3,456
beq s2,s2,rand_control_928
addi s4,s4,1
rand_control_928:
srli s2,s4,1
slli s3,s5,8
add s3,s4,s1
bne s5,s5,rand_control_932
addi s4,s4,1
rand_control_932:
addi s1,s5,-1517
sub s1,s1,s4
add s5,s2,s1
or s3,s1,s3
and s1,s3,s4
or s4,s4,s1
bne s5,s5,rand_control_939
addi s2,s2,1
rand_control_939:
sub s2,s3,s1
srai s2,s3,15
bne s1,s1,rand_control_942
addi s5,s5,1
rand_control_942:
and s4,s1,s3
addi s3,s5,-651
sub s5,s4,s2
sltu s3,s4,s1
or s4,s2,s3
sltu s2,s3,s1
beq s1,s1,rand_control_949
addi s1,s1,1
rand_control_949:
sll s4,s1,s1
addi s3,s4,-462
sll s3,s4,s5
sub s4,s3,s3
addi s1,s3,-1500
sll s4,s5,s4
srai s5,s5,17
xori s3,s3,1821
xori s4,s2,1679
andi s4,s4,544
andi s1,s3,-2023
srai s4,s3,30
andi s2,s5,-484
bne s3,s3,rand_control_963
addi s2,s2,1
rand_control_963:
ori s5,s1,-1502
srai s5,s1,28
ori s4,s4,618
and s2,s2,s1
and s3,s5,s4
xori s5,s5,-225
andi s2,s1,1181
bne s5,s5,rand_control_971
addi s3,s3,1
rand_control_971:
bne s2,s2,rand_control_972
addi s3,s3,1
rand_control_972:
sltu s3,s5,s2
srl s5,s1,s5
add s3,s4,s2
slli s2,s3,10
srl s5,s3,s2
addi s3,s2,-774
sub s4,s2,s4
sub s1,s4,s2
sub s5,s2,s2
srl s3,s1,s3
beq s5,s5,rand_control_983
addi s3,s3,1
rand_control_983:
slli s4,s4,8
or s5,s2,s5
slli s2,s2,11
sltu s5,s1,s4
and s1,s2,s3
srl s3,s1,s2
ori s4,s5,-333
sub s2,s2,s3
and s3,s2,s3
beq s5,s5,rand_control_993
addi s2,s2,1
rand_control_993:
srli s3,s1,14
or s3,s4,s4
beq s1,s1,rand_control_996
addi s2,s2,1
rand_control_996:
beq s5,s5,rand_control_997
addi s2,s2,1
rand_control_997:
xori s3,s1,-1383
srli s5,s5,3
srl s4,s2,s2
or s4,s4,s5
ori s1,s3,-1188
sltu s3,s4,s1
ori s3,s1,708
xor s5,s4,s5
ori s1,s5,-1462
sltu s2,s2,s1
xor s3,s3,s3
sltu s2,s2,s5
sub s5,s3,s3
slli s5,s2,14
srai s1,s2,8
xori s4,s2,-1492
or s3,s3,s1
add s4,s1,s1
srl s1,s5,s4
srli s3,s5,28
andi s2,s1,-1613
addi s4,s5,-1580
andi s3,s4,1049
beq s3,s3,rand_control_1021
addi s1,s1,1
rand_control_1021:
sll s1,s5,s5
sltu s4,s3,s2
sltu s4,s5,s2
srli s1,s1,1
srli s1,s5,3
add s4,s5,s2
add s4,s3,s4
xori s4,s3,810
andi s5,s4,-1844
or s2,s4,s3
sll s1,s2,s5
srli s2,s3,25
andi s3,s3,461
srl s1,s1,s1
or s4,s3,s3
andi s4,s5,-1851
addi s2,s1,-982
ori s1,s5,1072
beq s1,s1,rand_control_1040
addi s3,s3,1
rand_control_1040:
srai s4,s3,4
srai s5,s3,26
slt s2,s5,s1
slli s1,s5,30
beq s2,s2,rand_control_1045
addi s1,s1,1
rand_control_1045:
sltu s2,s2,s1
bne s5,s5,rand_control_1047
addi s1,s1,1
rand_control_1047:
andi s1,s3,-1281
sub s3,s3,s5
srl s5,s3,s3
sll s3,s2,s5
sll s1,s2,s3
add s1,s1,s1
ori s5,s3,-1424
xori s4,s5,424
add s3,s3,s1
ori s5,s4,-874
andi s3,s2,-547
or s3,s3,s1
andi s1,s4,1855
or s1,s5,s2
addi s2,s1,-296
srli s5,s4,31
xori s5,s4,869
sub s5,s2,s2
srli s2,s3,6
or s2,s2,s1
xor s2,s1,s2
slli s4,s3,14
or s3,s4,s4
and s1,s2,s4
srl s4,s3,s2
ori s5,s3,-988
andi s1,s3,1588
sub s4,s4,s5
or s4,s2,s5
beq s3,s3,rand_control_1077
addi s4,s4,1
rand_control_1077:
addi s5,s2,-763
sltu s5,s4,s5
or s2,s3,s5
bne s1,s1,rand_control_1081
addi s5,s5,1
rand_control_1081:
srl s4,s4,s2
srl s4,s1,s1
and s3,s3,s5
or s3,s2,s4
slli s5,s2,30
sltu s4,s3,s5
slli s1,s3,11
and s4,s1,s5
srl s2,s1,s3
xori s3,s3,-1065
sll s3,s1,s3
or s1,s3,s1
srli s2,s4,5
sll s3,s3,s2
slli s2,s1,26
srl s1,s1,s2
xor s1,s5,s2
srai s2,s3,24
ori s2,s1,1012
add s4,s2,s3
bne s3,s3,rand_control_1102
addi s4,s4,1
rand_control_1102:
xor s5,s3,s3
srli s5,s5,0
srai s4,s3,6
srai s2,s1,19
srl s4,s1,s5
add s2,s4,s1
or s3,s2,s1
srl s5,s5,s3
add s3,s1,s4
beq s3,s3,rand_control_1112
addi s5,s5,1
rand_control_1112:
add s4,s1,s5
srl s4,s3,s4
srli s3,s5,30
slli s2,s1,22
sub s1,s4,s3
slt s2,s2,s1
srai s5,s1,6
ori s3,s3,213
and s2,s1,s2
bne s4,s4,rand_control_1122
addi s2,s2,1
rand_control_1122:
srli s5,s2,16
beq s1,s1,rand_control_1124
addi s4,s4,1
rand_control_1124:
slli s3,s2,31
add s3,s2,s5
beq s1,s1,rand_control_1127
addi s1,s1,1
rand_control_1127:
ori s3,s5,172
sub s3,s1,s3
sltu s5,s4,s5
xori s4,s2,1898
srli s3,s4,15
slt s3,s1,s2
slli s3,s3,29
and s2,s3,s1
bne s1,s1,rand_control_1136
addi s3,s3,1
rand_control_1136:
srli s4,s5,0
andi s3,s2,1068
srai s3,s4,7
ori s4,s4,1295
srai s3,s4,22
slt s3,s3,s1
add s2,s2,s4
sltu s3,s3,s2
xor s4,s1,s4
xori s1,s5,1048
sltu s4,s5,s1
or s5,s2,s2
slli s2,s2,22
xori s3,s1,1452
srl s5,s4,s4
sub s2,s1,s5
sltu s4,s3,s2
slt s4,s2,s4
xori s3,s4,-1742
srai s4,s2,10
srli s1,s5,26
beq s4,s4,rand_control_1158
addi s4,s4,1
rand_control_1158:
sll s3,s2,s5
bne s3,s3,rand_control_1160
addi s4,s4,1
rand_control_1160:
and s4,s3,s2
xor s1,s3,s5
slt s2,s4,s4
srl s2,s4,s5
and s3,s3,s1
beq s4,s4,rand_control_1166
addi s5,s5,1
rand_control_1166:
xori s5,s2,61
xor s1,s3,s3
addi s4,s5,1716
sll s1,s5,s5
addi s4,s5,1288
sll s2,s1,s3
sub s2,s4,s1
addi s2,s2,768
sub s5,s5,s1
add s3,s3,s4
srli s3,s1,2
andi s5,s2,1791
ori s1,s5,2031
bne s3,s3,rand_control_1180
addi s3,s3,1
rand_control_1180:
bne s4,s4,rand_control_1181
addi s1,s1,1
rand_control_1181:
xori s3,s3,551
xor s1,s1,s3
sll s2,s4,s1
beq s4,s4,rand_control_1185
addi s2,s2,1
rand_control_1185:
srl s3,s3,s3
xor s5,s2,s4
addi s3,s2,1993
or s4,s5,s2
ori s1,s5,2046
sub s4,s2,s1
xor s5,s3,s2
beq s1,s1,rand_control_1193
addi s1,s1,1
rand_control_1193:
ori s3,s3,-547
sll s3,s5,s4
add s3,s2,s3
add s3,s1,s1
addi s1,s2,-1929
beq s3,s3,rand_control_1199
addi s5,s5,1
rand_control_1199:

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

