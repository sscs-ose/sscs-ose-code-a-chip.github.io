.option norvc
.section .text.init
.globl _start
_start:
la s0,scratch
li t0,0x90000000
li s1,1339212366
li s2,4141003316
li s3,966700148
li s4,1371768415
li s5,3815778746
andi s4,s1,-1253
xor s2,s3,s2
add s2,s3,s3
xori s1,s3,375
andi s2,s3,1200
xori s4,s1,-2018
xor s2,s3,s1
xor s5,s3,s1
and s2,s2,s4
xor s2,s3,s3
sll s2,s4,s2
srl s5,s2,s2
bne s2,s2,rand_control_12
addi s4,s4,1
rand_control_12:
or s3,s4,s5
add s3,s5,s1
bne s5,s5,rand_control_15
addi s4,s4,1
rand_control_15:
addi s4,s2,2022
and s1,s3,s2
xor s1,s5,s5
sll s3,s4,s2
sll s4,s1,s2
ori s5,s2,956
sll s1,s5,s4
bne s5,s5,rand_control_23
addi s3,s3,1
rand_control_23:
srai s1,s4,17
xor s4,s1,s5
srl s3,s2,s1
slt s4,s2,s1
srl s3,s2,s5
and s4,s3,s5
xori s1,s4,2020
slt s4,s1,s3
sub s5,s1,s1
sltu s4,s2,s4
xor s3,s1,s3
sll s2,s2,s1
bne s1,s1,rand_control_36
addi s2,s2,1
rand_control_36:
and s3,s5,s3
srli s3,s5,20
sub s5,s5,s3
ori s3,s2,-949
sll s4,s2,s3
and s3,s1,s1
srai s1,s2,12
ori s5,s2,724
srl s4,s5,s2
sltu s2,s1,s3
sltu s3,s1,s4
and s5,s3,s3
andi s1,s1,552
sub s5,s2,s3
xor s1,s5,s5
sltu s2,s4,s3
addi s5,s4,330
beq s1,s1,rand_control_54
addi s4,s4,1
rand_control_54:
sltu s2,s3,s1
xor s3,s3,s5
xori s3,s3,1313
sltu s1,s3,s4
srl s2,s1,s2
or s4,s4,s5
bne s1,s1,rand_control_61
addi s5,s5,1
rand_control_61:
sll s4,s2,s1
addi s5,s5,-1859
sub s2,s1,s5
xori s5,s5,-1522
addi s5,s4,1186
srl s3,s2,s4
srai s5,s2,14
xor s2,s3,s1
sll s3,s4,s5
andi s4,s2,-519
bne s3,s3,rand_control_72
addi s5,s5,1
rand_control_72:
sltu s2,s1,s3
and s2,s4,s2
srl s2,s1,s3
srl s3,s5,s5
andi s1,s5,-356
slt s4,s4,s4
xor s1,s4,s1
addi s4,s5,-1865
ori s3,s5,102
ori s4,s2,1637
xori s4,s2,1865
slt s1,s3,s5
bne s1,s1,rand_control_85
addi s3,s3,1
rand_control_85:
srl s1,s4,s5
xor s3,s3,s2
xor s2,s3,s3
or s5,s5,s2
ori s4,s1,-635
sub s5,s2,s5
sll s4,s3,s2
srl s1,s2,s1
add s5,s4,s3
bne s2,s2,rand_control_95
addi s5,s5,1
rand_control_95:
and s5,s4,s5
and s2,s2,s4
xor s5,s1,s4
srli s4,s5,25
srl s5,s1,s3
andi s5,s3,-84
bne s2,s2,rand_control_102
addi s1,s1,1
rand_control_102:
ori s2,s4,-440
xori s1,s2,883
and s4,s1,s3
bne s3,s3,rand_control_106
addi s1,s1,1
rand_control_106:
or s2,s3,s1
and s3,s3,s3
sub s2,s5,s3
add s2,s2,s1
and s4,s3,s4
slt s4,s1,s3
sub s3,s4,s1
or s3,s2,s2
srl s4,s1,s5
xor s5,s3,s5
beq s4,s4,rand_control_117
addi s3,s3,1
rand_control_117:
andi s4,s1,973
ori s4,s5,-323
andi s1,s5,309
srai s5,s4,6
or s3,s2,s1
slli s2,s5,8
xori s1,s4,-1531
xori s3,s4,-734
bne s1,s1,rand_control_126
addi s3,s3,1
rand_control_126:
andi s2,s3,-1323
xor s3,s3,s3
xor s1,s3,s4
sub s1,s3,s4
or s5,s1,s2
slt s3,s1,s2
and s2,s4,s3
sll s1,s5,s5
ori s5,s5,-478
slt s5,s4,s5
andi s2,s2,320
sltu s2,s1,s1
beq s2,s2,rand_control_139
addi s5,s5,1
rand_control_139:
beq s2,s2,rand_control_140
addi s2,s2,1
rand_control_140:
sll s4,s3,s4
slli s4,s2,7
sll s1,s3,s3
andi s1,s4,697
addi s5,s1,-457
and s3,s1,s1
addi s1,s3,-993
and s2,s4,s4
bne s4,s4,rand_control_149
addi s4,s4,1
rand_control_149:
beq s1,s1,rand_control_150
addi s5,s5,1
rand_control_150:
or s3,s3,s3
or s3,s5,s3
addi s4,s5,1249
and s4,s4,s5
or s4,s1,s2
slli s4,s4,2
add s4,s5,s2
srl s3,s2,s5
slt s3,s4,s1
or s4,s3,s5
sltu s5,s2,s3
beq s1,s1,rand_control_162
addi s5,s5,1
rand_control_162:
or s5,s2,s1
srli s3,s2,0
ori s5,s5,254
srl s1,s5,s5
slli s5,s3,12
addi s3,s1,-502
srl s3,s3,s3
sll s1,s3,s3
sll s1,s1,s4
srl s5,s4,s2
srli s1,s2,7
srli s1,s4,13
andi s1,s3,-1067
sltu s2,s4,s5
add s5,s1,s4
srl s1,s3,s2
ori s1,s5,-1896
beq s3,s3,rand_control_180
addi s2,s2,1
rand_control_180:
addi s4,s1,-123
xori s1,s5,1205
xor s3,s5,s5
sub s5,s4,s5
sll s1,s2,s2
srl s2,s5,s2
srai s4,s5,25
beq s2,s2,rand_control_188
addi s4,s4,1
rand_control_188:
bne s4,s4,rand_control_189
addi s3,s3,1
rand_control_189:
srl s2,s2,s2
sub s1,s1,s1
bne s2,s2,rand_control_192
addi s2,s2,1
rand_control_192:
sub s3,s3,s5
slt s3,s1,s3
sltu s3,s2,s2
sltu s4,s1,s4
slt s4,s2,s2
slt s3,s1,s5
add s3,s1,s5
add s1,s4,s1
andi s1,s5,1033
beq s1,s1,rand_control_202
addi s5,s5,1
rand_control_202:
or s2,s3,s2
srl s5,s5,s4
sll s2,s4,s3
or s1,s1,s1
addi s1,s4,-1692
andi s3,s3,-711
slt s3,s4,s2
sll s3,s4,s2
xori s1,s1,-326
srai s1,s2,19
slt s3,s2,s4
sltu s3,s1,s5
sll s1,s3,s1
or s5,s3,s4
beq s5,s5,rand_control_217
addi s2,s2,1
rand_control_217:
andi s1,s2,174
sub s5,s2,s4
sub s5,s5,s5
srai s3,s2,2
srli s2,s1,15
bne s1,s1,rand_control_223
addi s1,s1,1
rand_control_223:
srl s2,s5,s1
slli s1,s3,13
srai s2,s1,11
slli s1,s4,30
srli s3,s1,11
xori s5,s4,-692
sltu s1,s3,s2
andi s2,s2,-196
sll s1,s5,s4
sltu s5,s5,s2
sub s1,s2,s2
andi s1,s4,1771
sll s3,s3,s5
sub s5,s2,s2
srai s5,s5,8
ori s5,s2,12
or s5,s3,s5
srli s5,s2,16
slli s2,s2,18
slt s5,s5,s5
sub s4,s4,s2
beq s4,s4,rand_control_245
addi s3,s3,1
rand_control_245:
addi s2,s1,-1562
srai s5,s5,4
srli s4,s5,13
srli s5,s2,8
xori s4,s4,-286
and s5,s1,s3
andi s1,s1,942
srli s4,s4,11
xor s2,s1,s2
srl s5,s5,s4
addi s1,s2,-283
xor s1,s4,s2
srai s3,s5,7
srai s4,s2,31
ori s2,s1,-1561
xori s2,s4,-1221
ori s3,s2,124
sltu s3,s5,s2
bne s1,s1,rand_control_264
addi s4,s4,1
rand_control_264:
xori s4,s3,-798
addi s1,s2,-1636
slli s5,s2,21
addi s2,s4,424
and s5,s2,s5
ori s1,s5,-887
xor s2,s2,s3
and s3,s4,s4
srl s5,s2,s4
srl s1,s2,s1
srli s4,s4,9
xori s1,s3,-973
xor s5,s4,s1
sll s5,s3,s5
and s4,s2,s4
xor s5,s1,s3
slli s5,s3,3
sltu s2,s3,s5
srli s3,s2,6
xor s1,s5,s3
xor s2,s5,s2
sltu s4,s1,s1
sub s4,s5,s2
and s2,s1,s3
or s5,s1,s5
srli s4,s5,24
and s5,s4,s5
andi s4,s4,-146
sltu s2,s3,s5
sltu s5,s2,s2
srli s5,s4,6
add s4,s2,s5
srli s3,s4,14
addi s1,s3,-1829
sltu s3,s4,s5
andi s5,s2,-776
and s4,s3,s3
beq s5,s5,rand_control_302
addi s5,s5,1
rand_control_302:
or s1,s2,s3
beq s4,s4,rand_control_304
addi s1,s1,1
rand_control_304:
srl s3,s2,s5
sub s2,s4,s5
srl s3,s4,s3
and s5,s1,s1
srl s2,s3,s4
bne s5,s5,rand_control_310
addi s1,s1,1
rand_control_310:
beq s3,s3,rand_control_311
addi s5,s5,1
rand_control_311:
sub s5,s3,s1
ori s3,s3,-1973
slli s2,s3,26
xori s1,s5,-1440
beq s5,s5,rand_control_316
addi s3,s3,1
rand_control_316:
slli s1,s3,3
srl s2,s2,s1
sltu s5,s2,s1
or s3,s2,s1
andi s5,s4,-1026
srl s2,s1,s1
ori s5,s1,-1623
sll s3,s1,s3
bne s4,s4,rand_control_325
addi s2,s2,1
rand_control_325:
beq s2,s2,rand_control_326
addi s5,s5,1
rand_control_326:
sll s2,s4,s4
andi s4,s1,310
addi s2,s1,-476
beq s2,s2,rand_control_330
addi s5,s5,1
rand_control_330:
sll s2,s5,s3
or s1,s2,s5
srl s1,s4,s5
srli s1,s1,16
or s2,s3,s2
ori s1,s1,-223
andi s4,s3,935
beq s2,s2,rand_control_338
addi s1,s1,1
rand_control_338:
add s3,s5,s4
or s4,s3,s5
addi s5,s5,1913
xori s1,s1,-411
and s1,s1,s4
sub s4,s5,s4
bne s4,s4,rand_control_345
addi s1,s1,1
rand_control_345:
addi s2,s4,644
xor s4,s3,s3
srli s2,s4,20
slli s3,s5,2
add s5,s2,s5
slli s3,s5,20
srai s3,s1,0
xor s2,s2,s5
xori s3,s1,1544
ori s4,s4,-1631
srai s5,s1,15
addi s5,s1,1827
sltu s3,s5,s5
andi s2,s4,605
beq s1,s1,rand_control_360
addi s3,s3,1
rand_control_360:
andi s4,s5,-223
srl s1,s5,s4
srl s2,s3,s2
srl s4,s4,s1
srai s1,s3,24
xor s3,s2,s5
srai s4,s2,28
xor s4,s1,s1
srl s4,s5,s2
addi s5,s3,656
andi s2,s1,752
sltu s5,s1,s5
or s5,s2,s3
xori s3,s5,1640
srl s4,s5,s2
sub s2,s4,s2
sub s3,s4,s2
beq s1,s1,rand_control_378
addi s1,s1,1
rand_control_378:
sltu s4,s5,s2
sll s3,s5,s5
add s4,s3,s4
slt s1,s3,s5
srl s3,s5,s4
slli s1,s4,17
and s4,s4,s5
and s3,s1,s1
or s1,s2,s3
addi s5,s4,-1169
slt s2,s5,s1
srl s4,s3,s1
bne s3,s3,rand_control_391
addi s5,s5,1
rand_control_391:
or s4,s5,s5
beq s5,s5,rand_control_393
addi s2,s2,1
rand_control_393:
ori s3,s5,-1210
srli s2,s3,31
srli s1,s4,17
srai s5,s4,31
srli s3,s4,19
and s3,s2,s4
addi s4,s4,825
andi s1,s2,249
beq s1,s1,rand_control_402
addi s5,s5,1
rand_control_402:
slli s2,s5,7
and s5,s3,s1
beq s1,s1,rand_control_405
addi s5,s5,1
rand_control_405:
srl s5,s3,s5
slli s3,s1,18
slt s2,s2,s5
sll s3,s2,s5
srai s5,s2,11
andi s3,s4,677
or s2,s3,s2
addi s5,s3,161
sll s2,s5,s2
xor s1,s4,s3
srl s4,s3,s2
slli s1,s1,5
slli s1,s2,5
andi s1,s5,-1036
bne s4,s4,rand_control_420
addi s5,s5,1
rand_control_420:
beq s3,s3,rand_control_421
addi s2,s2,1
rand_control_421:
slt s5,s4,s4
xori s4,s2,-974
sltu s3,s3,s3
slli s4,s1,6
beq s5,s5,rand_control_426
addi s5,s5,1
rand_control_426:
slli s5,s4,30
and s5,s3,s5
srli s5,s1,0
addi s2,s1,89
beq s1,s1,rand_control_431
addi s2,s2,1
rand_control_431:
sub s1,s4,s3
add s5,s5,s4
sub s1,s4,s1
sltu s4,s4,s1
sub s3,s1,s1
add s4,s3,s1
bne s1,s1,rand_control_438
addi s2,s2,1
rand_control_438:
bne s5,s5,rand_control_439
addi s4,s4,1
rand_control_439:
addi s1,s2,-198
xori s1,s2,-516
sll s2,s1,s2
sltu s4,s2,s5
or s3,s3,s1
xor s5,s5,s3
srai s5,s1,7
srli s4,s5,25
addi s2,s5,-1179
beq s5,s5,rand_control_449
addi s2,s2,1
rand_control_449:
sltu s2,s4,s1
xor s1,s2,s4
or s2,s4,s3
beq s5,s5,rand_control_453
addi s3,s3,1
rand_control_453:
sltu s4,s5,s5
slt s1,s5,s3
sltu s1,s1,s5
srli s2,s2,14
sll s4,s2,s4
ori s5,s3,1504
xori s3,s5,-1560
srl s2,s4,s1
sub s2,s3,s2
srl s3,s3,s1
slt s3,s2,s1
addi s2,s4,-62
srai s4,s1,11
and s4,s1,s2
sll s4,s5,s1
and s4,s2,s5
beq s3,s3,rand_control_470
addi s1,s1,1
rand_control_470:
srai s2,s1,22
sll s2,s5,s2
beq s2,s2,rand_control_473
addi s2,s2,1
rand_control_473:
slt s1,s2,s5
bne s4,s4,rand_control_475
addi s2,s2,1
rand_control_475:
andi s5,s1,1896
ori s5,s4,174
xori s2,s2,-944
slt s2,s4,s1
ori s4,s5,-1674
and s4,s2,s5
or s1,s5,s1
andi s4,s3,-81
srli s1,s5,27
xori s1,s1,-21
slli s3,s2,11
srai s3,s5,2
andi s2,s1,-1544
srai s2,s1,21
srai s3,s1,10
sltu s2,s2,s1
sltu s1,s5,s1
or s5,s5,s1
beq s3,s3,rand_control_494
addi s5,s5,1
rand_control_494:
srai s5,s4,24
addi s1,s2,-1185
and s1,s3,s4
beq s3,s3,rand_control_498
addi s4,s4,1
rand_control_498:
xor s2,s2,s3
ori s4,s1,1254
srai s5,s3,18
andi s1,s4,1555
bne s5,s5,rand_control_503
addi s4,s4,1
rand_control_503:
slli s5,s1,9
sub s2,s3,s2
ori s5,s5,441
andi s4,s5,-437
and s4,s3,s2
xor s2,s2,s5
sltu s2,s5,s3
or s3,s3,s2
sltu s3,s4,s5
srl s2,s3,s5
add s3,s3,s5
addi s3,s1,647
ori s3,s4,-1180
sll s4,s5,s4
bne s2,s2,rand_control_518
addi s3,s3,1
rand_control_518:
and s5,s3,s3
srai s5,s2,6
addi s1,s4,488
srl s2,s5,s5
add s4,s3,s1
beq s2,s2,rand_control_524
addi s1,s1,1
rand_control_524:
slt s1,s1,s3
beq s3,s3,rand_control_526
addi s5,s5,1
rand_control_526:
ori s5,s3,1925
add s3,s1,s3
sltu s1,s5,s3
and s1,s5,s2
slli s5,s3,14
sub s3,s3,s3
or s2,s1,s2
or s1,s3,s1
srli s3,s1,27
addi s5,s4,-780
add s5,s1,s4
srli s4,s4,17
bne s3,s3,rand_control_539
addi s4,s4,1
rand_control_539:
slt s3,s4,s5
srl s3,s1,s4
add s1,s3,s2
addi s4,s1,-1992
xor s3,s5,s2
sll s1,s1,s4
ori s1,s4,1836
xori s2,s3,625
beq s1,s1,rand_control_548
addi s3,s3,1
rand_control_548:
xori s1,s5,306
xor s1,s3,s5
sll s3,s1,s1
andi s5,s2,-188
xor s5,s4,s4
beq s4,s4,rand_control_554
addi s3,s3,1
rand_control_554:
add s3,s2,s2
slt s2,s2,s3
xori s1,s2,-1337
srli s1,s1,25
sll s3,s1,s1
srl s2,s3,s4
srli s3,s5,15
srl s4,s1,s3
xori s2,s1,-579
srli s5,s1,3
sll s3,s4,s2
sltu s2,s1,s4
srli s2,s5,25
slt s4,s3,s2
beq s5,s5,rand_control_569
addi s5,s5,1
rand_control_569:
srli s2,s1,13
and s3,s3,s3
andi s4,s2,41
srl s4,s2,s4
sll s1,s5,s3
sub s3,s4,s5
and s5,s5,s2
andi s5,s2,387
sll s3,s4,s2
slt s4,s2,s2
slli s2,s4,2
slt s1,s4,s5
sll s4,s2,s5
slt s1,s4,s5
slli s3,s4,13
slli s4,s4,2
bne s1,s1,rand_control_586
addi s1,s1,1
rand_control_586:
beq s4,s4,rand_control_587
addi s4,s4,1
rand_control_587:
and s2,s3,s3
sll s2,s4,s1
sub s2,s4,s3
sltu s5,s3,s5
addi s1,s5,-961
srai s3,s2,24
sll s2,s4,s3
add s3,s3,s3
and s1,s2,s5
beq s2,s2,rand_control_597
addi s1,s1,1
rand_control_597:
xor s2,s1,s4
bne s1,s1,rand_control_599
addi s1,s1,1
rand_control_599:
add s3,s1,s3
ori s2,s2,-1668
srai s5,s4,3
andi s3,s1,1090
srai s5,s3,21
xor s2,s5,s4
srl s2,s5,s3
sub s3,s2,s3
bne s3,s3,rand_control_608
addi s3,s3,1
rand_control_608:
xori s2,s3,-1025
add s4,s1,s5
beq s5,s5,rand_control_611
addi s3,s3,1
rand_control_611:
slli s4,s1,23
ori s1,s2,787
slt s5,s2,s5
srli s2,s3,4
addi s1,s2,-1636
srai s1,s5,0
srai s2,s1,9
srl s4,s1,s3
slli s1,s1,12
beq s5,s5,rand_control_621
addi s3,s3,1
rand_control_621:
sll s4,s3,s4
slt s1,s3,s3
beq s1,s1,rand_control_624
addi s1,s1,1
rand_control_624:
srl s3,s5,s1
beq s5,s5,rand_control_626
addi s3,s3,1
rand_control_626:
slli s4,s1,14
and s3,s3,s2
slt s3,s4,s2
sub s5,s4,s3
or s5,s1,s2
xor s5,s2,s3
sltu s1,s2,s5
and s1,s4,s5
beq s1,s1,rand_control_635
addi s1,s1,1
rand_control_635:
bne s1,s1,rand_control_636
addi s4,s4,1
rand_control_636:
add s1,s2,s2
add s2,s1,s3
xor s3,s4,s5
srli s2,s2,12
xor s4,s5,s3
or s4,s3,s5
srli s4,s1,27
ori s5,s1,1552
add s2,s4,s4
slt s3,s2,s1
andi s4,s5,1224
sub s5,s1,s4
sltu s3,s4,s1
andi s3,s2,-1778
beq s1,s1,rand_control_651
addi s3,s3,1
rand_control_651:
xor s1,s1,s5
srli s1,s2,18
beq s4,s4,rand_control_654
addi s2,s2,1
rand_control_654:
xor s2,s4,s1
slli s5,s1,26
xor s2,s2,s1
xor s2,s4,s1
sltu s2,s2,s4
slt s5,s5,s5
beq s4,s4,rand_control_661
addi s2,s2,1
rand_control_661:
slli s2,s5,29
slli s1,s5,29
xor s4,s4,s4
sltu s4,s1,s5
addi s4,s5,-995
sltu s1,s3,s4
ori s4,s2,969
srli s5,s3,9
sll s4,s2,s5
sltu s5,s3,s5
add s1,s5,s4
srai s5,s1,23
srai s3,s5,26
srai s1,s4,14
bne s4,s4,rand_control_676
addi s2,s2,1
rand_control_676:
sltu s1,s1,s3
xor s1,s2,s5
xor s5,s5,s1
srai s5,s4,30
addi s3,s2,-1976
bne s3,s3,rand_control_682
addi s5,s5,1
rand_control_682:
sll s2,s4,s5
sub s2,s1,s3
sll s4,s2,s1
sll s2,s5,s4
xori s5,s2,-1836
slt s1,s3,s3
and s1,s1,s2
sltu s4,s1,s2
xor s1,s5,s5
sub s1,s5,s2
and s3,s2,s5
or s4,s1,s2
sltu s2,s5,s3
or s3,s4,s2
srai s4,s1,14
or s1,s2,s2
xor s2,s4,s2
sll s4,s5,s4
bne s3,s3,rand_control_701
addi s4,s4,1
rand_control_701:
or s2,s1,s4
srli s5,s4,25
ori s2,s5,-1956
sub s3,s2,s2
or s5,s4,s1
xor s5,s3,s3
sll s3,s4,s1
xori s1,s3,238
srai s1,s4,1
andi s5,s5,-1474
sll s4,s1,s5
xori s5,s4,1462
andi s2,s4,1239
add s3,s3,s4
bne s2,s2,rand_control_716
addi s2,s2,1
rand_control_716:
add s3,s3,s1
xori s4,s1,-893
sll s4,s1,s2
xor s2,s5,s3
sll s3,s5,s4
srli s2,s5,23
beq s4,s4,rand_control_723
addi s1,s1,1
rand_control_723:
sub s5,s1,s2
slt s2,s4,s2
bne s4,s4,rand_control_726
addi s3,s3,1
rand_control_726:
ori s4,s3,-184
srli s5,s4,9
srli s1,s5,28
sll s3,s3,s2
beq s1,s1,rand_control_731
addi s3,s3,1
rand_control_731:
srl s3,s5,s5
bne s4,s4,rand_control_733
addi s2,s2,1
rand_control_733:
xor s1,s2,s5
xori s1,s5,141
srl s3,s2,s5
ori s5,s1,-826
add s2,s1,s4
or s3,s4,s5
andi s3,s4,212
slli s2,s3,13
xori s3,s5,1428
addi s3,s1,1575
bne s2,s2,rand_control_744
addi s4,s4,1
rand_control_744:
srli s2,s1,6
sltu s5,s3,s2
xor s3,s2,s3
sub s4,s3,s4
and s3,s1,s4
beq s1,s1,rand_control_750
addi s2,s2,1
rand_control_750:
xor s2,s2,s2
bne s4,s4,rand_control_752
addi s3,s3,1
rand_control_752:
andi s5,s4,1448
slli s3,s1,29
or s3,s5,s5
add s3,s1,s3
xor s4,s5,s4
sll s2,s5,s5
xor s5,s5,s1
addi s3,s1,-998
and s5,s4,s3
and s3,s5,s1
beq s2,s2,rand_control_763
addi s5,s5,1
rand_control_763:
and s1,s1,s3
srl s2,s2,s2
beq s1,s1,rand_control_766
addi s4,s4,1
rand_control_766:
srli s2,s3,26
beq s4,s4,rand_control_768
addi s2,s2,1
rand_control_768:
sltu s4,s1,s2
srl s3,s1,s1
ori s4,s3,911
sub s2,s1,s3
slt s5,s3,s4
xori s5,s2,1020
andi s2,s1,-427
xor s3,s2,s5
sub s5,s5,s3
sltu s1,s3,s5
srli s3,s2,18
slli s5,s3,0
srli s1,s2,5
or s3,s2,s1
ori s3,s4,-1962
beq s4,s4,rand_control_784
addi s3,s3,1
rand_control_784:
sll s4,s5,s1
sll s3,s2,s5
or s1,s3,s4
sll s3,s4,s3
beq s2,s2,rand_control_789
addi s4,s4,1
rand_control_789:
xori s2,s3,2009
addi s1,s3,-1844
srli s5,s2,12
sub s2,s5,s2
xori s1,s4,-257
srl s2,s4,s1
sub s3,s4,s5
sll s4,s5,s1
srli s1,s4,22
addi s3,s1,394
sll s1,s1,s3
sub s3,s4,s2
srl s4,s1,s4
addi s1,s3,1246
add s3,s4,s3
or s5,s4,s5
add s2,s3,s3
slt s4,s2,s5
beq s4,s4,rand_control_808
addi s5,s5,1
rand_control_808:
beq s4,s4,rand_control_809
addi s4,s4,1
rand_control_809:
addi s3,s4,1095
addi s5,s4,-1650
sub s1,s2,s1
ori s5,s3,-279
bne s3,s3,rand_control_814
addi s5,s5,1
rand_control_814:
srai s4,s5,22
sub s2,s4,s3
ori s1,s5,-2043
srai s3,s4,3
xori s3,s1,1894
bne s5,s5,rand_control_820
addi s4,s4,1
rand_control_820:
xori s3,s3,-1325
addi s4,s1,1998
sub s1,s2,s1
bne s5,s5,rand_control_824
addi s2,s2,1
rand_control_824:
beq s3,s3,rand_control_825
addi s4,s4,1
rand_control_825:
slli s2,s3,7
sub s2,s2,s5
or s3,s3,s5
bne s5,s5,rand_control_829
addi s3,s3,1
rand_control_829:
beq s4,s4,rand_control_830
addi s3,s3,1
rand_control_830:
and s1,s5,s4
addi s3,s5,-370
xor s5,s1,s2
sll s2,s1,s5
slli s4,s5,10
sll s2,s2,s3
bne s5,s5,rand_control_837
addi s4,s4,1
rand_control_837:
xori s5,s4,-199
slt s2,s1,s4
addi s1,s4,571
addi s5,s2,1237
slli s3,s5,31
addi s3,s4,2028
andi s3,s5,-333
sltu s1,s4,s4
slli s4,s5,12
xor s3,s5,s1
xor s2,s5,s4
srli s5,s4,27
add s1,s5,s5
or s1,s4,s1
sltu s3,s2,s1
sub s5,s1,s2
bne s1,s1,rand_control_854
addi s1,s1,1
rand_control_854:
ori s5,s4,1007
srai s3,s2,20
ori s1,s1,1613
sltu s4,s3,s4
ori s3,s3,-903
ori s5,s2,-980
srli s5,s2,2
beq s1,s1,rand_control_862
addi s1,s1,1
rand_control_862:
slli s1,s1,18
ori s4,s5,1971
xor s2,s1,s4
and s2,s2,s1
add s1,s4,s3
and s4,s4,s3
sll s5,s4,s4
sub s3,s5,s5
sub s5,s5,s4
or s5,s1,s3
srl s3,s1,s3
slt s2,s2,s1
sltu s5,s5,s5
xor s2,s5,s1
slli s2,s2,9
and s4,s5,s5
sub s1,s4,s5
andi s2,s2,147
addi s5,s3,-1575
beq s2,s2,rand_control_882
addi s3,s3,1
rand_control_882:
or s3,s3,s2
add s3,s4,s3
sll s4,s4,s3
or s5,s5,s2
slt s1,s1,s5
addi s4,s5,1060
sll s3,s5,s4
andi s1,s3,1159
bne s4,s4,rand_control_891
addi s2,s2,1
rand_control_891:
beq s2,s2,rand_control_892
addi s3,s3,1
rand_control_892:
slt s4,s5,s1
or s4,s2,s5
sub s3,s2,s2
beq s3,s3,rand_control_896
addi s5,s5,1
rand_control_896:
sll s4,s1,s3
ori s4,s4,-645
ori s5,s4,-654
addi s1,s3,-1516
add s2,s1,s2
srli s2,s1,19
bne s2,s2,rand_control_903
addi s3,s3,1
rand_control_903:
srli s3,s2,23
srl s1,s1,s5
and s4,s5,s4
sltu s5,s2,s4
and s5,s2,s5
srli s4,s4,5
srl s5,s1,s4
srli s4,s1,0
or s4,s3,s4
srli s5,s3,5
or s2,s3,s4
xor s3,s3,s1
ori s3,s5,-628
beq s3,s3,rand_control_917
addi s3,s3,1
rand_control_917:
srl s5,s5,s5
srl s3,s5,s4
add s2,s2,s4
slt s2,s5,s3
srai s4,s4,13
sub s5,s4,s5
sub s5,s3,s1
and s4,s5,s5
addi s2,s1,1732
bne s2,s2,rand_control_927
addi s3,s3,1
rand_control_927:
sll s5,s3,s3
add s2,s2,s4
bne s5,s5,rand_control_930
addi s2,s2,1
rand_control_930:
srl s2,s3,s2
sltu s3,s2,s2
beq s5,s5,rand_control_933
addi s1,s1,1
rand_control_933:
bne s4,s4,rand_control_934
addi s3,s3,1
rand_control_934:
sub s3,s3,s1
and s4,s5,s3
or s4,s3,s5
slt s1,s1,s4
or s4,s3,s1
sll s1,s2,s2
slli s1,s4,16
addi s2,s5,1448
add s3,s5,s4
srai s3,s5,30
ori s1,s3,-1194
slt s4,s3,s4
or s1,s1,s3
andi s2,s1,1857
ori s1,s2,-268
sll s3,s4,s1
ori s4,s2,-1842
add s4,s3,s1
slli s3,s2,4
sll s5,s2,s3
add s5,s3,s3
bne s3,s3,rand_control_956
addi s2,s2,1
rand_control_956:
srai s5,s5,4
bne s1,s1,rand_control_958
addi s1,s1,1
rand_control_958:
and s4,s5,s5
andi s5,s3,262
and s5,s1,s5
slt s1,s1,s4
add s1,s5,s3
and s4,s5,s3
srli s4,s4,8
slt s1,s2,s5
srl s5,s3,s4
and s2,s3,s3
xori s3,s4,1350
beq s5,s5,rand_control_970
addi s4,s4,1
rand_control_970:
or s3,s1,s1
ori s5,s2,-2006
srl s4,s4,s4
ori s3,s4,360
slt s5,s3,s2
xor s5,s5,s4
xor s5,s3,s5
xor s1,s2,s5
addi s1,s3,-1297
addi s4,s2,-860
or s3,s2,s5
bne s1,s1,rand_control_982
addi s3,s3,1
rand_control_982:
add s5,s4,s4
srl s3,s3,s2
sltu s4,s3,s2
add s3,s1,s2
srai s5,s2,3
srl s2,s1,s5
andi s5,s1,306
srl s4,s2,s3
xor s4,s4,s1
sub s1,s5,s1
or s5,s1,s5
xor s2,s3,s2
sltu s1,s4,s1
sll s4,s2,s4
slt s4,s5,s1
xori s5,s2,1434
srl s1,s5,s5
bne s2,s2,rand_control_1000
addi s4,s4,1
rand_control_1000:
xor s2,s2,s4
add s1,s1,s5
add s1,s2,s2
beq s3,s3,rand_control_1004
addi s1,s1,1
rand_control_1004:
add s1,s4,s2
andi s5,s4,-948
or s1,s4,s1
sub s5,s3,s4
or s2,s3,s4
slli s2,s1,25
sll s3,s1,s3
addi s5,s4,-1073
ori s4,s5,-54
slt s1,s4,s4
addi s2,s4,1061
slt s2,s5,s1
sll s4,s1,s1
add s3,s2,s5
ori s3,s3,-1236
srli s3,s4,0
add s1,s4,s4
sltu s4,s2,s4
xori s5,s1,1110
sltu s3,s3,s4
slli s1,s4,25
xor s5,s3,s3
beq s5,s5,rand_control_1027
addi s4,s4,1
rand_control_1027:
addi s3,s3,1089
and s1,s1,s5
beq s2,s2,rand_control_1030
addi s5,s5,1
rand_control_1030:
bne s1,s1,rand_control_1031
addi s5,s5,1
rand_control_1031:
beq s4,s4,rand_control_1032
addi s1,s1,1
rand_control_1032:
beq s2,s2,rand_control_1033
addi s2,s2,1
rand_control_1033:
slli s2,s2,25
srl s1,s4,s2
or s3,s1,s5
add s5,s1,s4
andi s5,s3,-1862
slt s3,s5,s1
add s4,s5,s5
ori s1,s4,756
slt s1,s3,s3
or s4,s3,s1
xori s5,s3,1224
ori s3,s1,597
addi s4,s2,1361
addi s1,s2,242
sub s3,s3,s3
slli s5,s5,4
sltu s5,s2,s1
or s3,s5,s2
srl s1,s4,s4
add s4,s1,s1
beq s5,s5,rand_control_1054
addi s5,s5,1
rand_control_1054:
ori s5,s5,1354
and s4,s5,s1
bne s2,s2,rand_control_1057
addi s5,s5,1
rand_control_1057:
xor s2,s4,s4
sll s2,s2,s3
sll s4,s2,s5
slli s1,s2,21
and s3,s2,s3
add s2,s2,s3
sub s5,s5,s2
srli s5,s5,25
srli s2,s2,14
ori s5,s1,82
sll s2,s4,s1
slli s4,s2,8
sub s3,s1,s2
xor s1,s2,s1
slt s4,s3,s5
xor s5,s1,s3
and s5,s4,s1
srl s2,s5,s1
slli s3,s5,31
andi s3,s5,-1693
xori s2,s1,-1896
xor s1,s2,s3
slli s1,s2,26
bne s4,s4,rand_control_1081
addi s3,s3,1
rand_control_1081:
beq s5,s5,rand_control_1082
addi s5,s5,1
rand_control_1082:
srai s5,s2,2
and s2,s2,s3
addi s4,s2,427
srli s3,s3,31
and s3,s4,s2
slli s1,s3,15
xor s2,s4,s3
xori s4,s2,-462
ori s2,s2,2046
add s1,s4,s1
andi s4,s1,1971
sub s4,s2,s5
beq s1,s1,rand_control_1095
addi s5,s5,1
rand_control_1095:
xor s5,s2,s3
sltu s2,s5,s5
add s3,s3,s2
bne s4,s4,rand_control_1099
addi s4,s4,1
rand_control_1099:
sub s1,s5,s3
beq s2,s2,rand_control_1101
addi s4,s4,1
rand_control_1101:
add s2,s3,s4
srai s1,s1,8
srli s5,s5,3
andi s3,s2,863
srai s5,s3,1
slt s5,s3,s5
addi s3,s5,1353
xor s2,s3,s3
ori s4,s2,-1224
slli s2,s3,6
beq s5,s5,rand_control_1112
addi s4,s4,1
rand_control_1112:
and s2,s2,s5
sll s2,s1,s2
srai s5,s3,25
sll s2,s2,s2
bne s1,s1,rand_control_1117
addi s5,s5,1
rand_control_1117:
slt s3,s2,s1
andi s4,s5,-124
slt s2,s3,s2
sll s1,s2,s5
slli s2,s5,28
andi s2,s1,-1879
add s3,s5,s1
srl s1,s1,s2
slt s3,s3,s3
srl s4,s4,s1
addi s4,s4,581
sub s1,s1,s4
add s1,s3,s4
addi s1,s3,-631
xor s2,s3,s5
xori s2,s2,-946
beq s3,s3,rand_control_1134
addi s4,s4,1
rand_control_1134:
sll s2,s3,s3
xor s4,s5,s4
sltu s2,s3,s5
xori s4,s1,-1629
bne s3,s3,rand_control_1139
addi s3,s3,1
rand_control_1139:
and s1,s3,s1
slt s5,s1,s3
sll s3,s4,s2
slli s4,s2,7
and s2,s5,s2
xori s2,s5,1736
slt s5,s4,s4
and s1,s1,s1
slt s2,s1,s4
sltu s1,s5,s5
slli s2,s4,24
srli s1,s3,23
beq s4,s4,rand_control_1152
addi s4,s4,1
rand_control_1152:
or s3,s5,s3
add s2,s1,s3
srli s4,s2,26
beq s2,s2,rand_control_1156
addi s5,s5,1
rand_control_1156:
sltu s3,s5,s1
bne s5,s5,rand_control_1158
addi s4,s4,1
rand_control_1158:
addi s4,s1,1880
and s4,s1,s3
sltu s2,s5,s3
srl s3,s5,s1
sltu s3,s5,s1
sltu s5,s2,s2
srli s3,s5,21
addi s2,s1,-21
bne s3,s3,rand_control_1167
addi s4,s4,1
rand_control_1167:
srl s3,s5,s3
sub s3,s2,s5
addi s3,s5,-1963
slt s5,s3,s5
srai s2,s5,15
sltu s4,s2,s4
addi s5,s2,-1335
slli s5,s4,6
slli s3,s2,4
and s4,s2,s1
or s4,s1,s5
slli s5,s2,0
andi s2,s5,-69
ori s1,s2,-2047
bne s3,s3,rand_control_1182
addi s3,s3,1
rand_control_1182:
andi s1,s2,1560
srli s1,s2,2
srli s4,s2,2
andi s5,s1,795
beq s5,s5,rand_control_1187
addi s2,s2,1
rand_control_1187:
andi s3,s2,-1652
xor s3,s2,s1
andi s3,s4,-1269
andi s3,s4,-1061
bne s4,s4,rand_control_1192
addi s1,s1,1
rand_control_1192:
sub s3,s1,s5
srli s2,s3,0
xor s3,s5,s2
add s3,s4,s4
slt s3,s5,s3
add s1,s1,s4
sub s1,s5,s1

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

