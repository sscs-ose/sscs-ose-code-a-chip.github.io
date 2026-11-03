.option norvc
.section .text.init
.globl _start
_start:
la s0,scratch
li t0,0x90000000
li s1,3214968405
li s2,722476858
li s3,628250416
li s4,2187446886
li s5,2969278521
slli s1,s5,12
slt s3,s4,s5
xori s5,s2,1008
bne s1,s1,rand_control_3
addi s5,s5,1
rand_control_3:
slt s5,s3,s1
beq s2,s2,rand_control_5
addi s5,s5,1
rand_control_5:
and s2,s2,s5
add s4,s3,s3
slt s4,s4,s2
add s4,s4,s4
sll s4,s3,s1
sll s2,s5,s5
slt s5,s5,s4
beq s5,s5,rand_control_13
addi s1,s1,1
rand_control_13:
sltu s2,s3,s1
beq s2,s2,rand_control_15
addi s5,s5,1
rand_control_15:
addi s4,s3,-1163
andi s5,s2,213
slt s5,s4,s5
and s2,s3,s5
xor s5,s3,s1
srl s2,s1,s2
bne s1,s1,rand_control_22
addi s3,s3,1
rand_control_22:
add s1,s5,s3
srai s1,s1,12
slt s5,s3,s4
ori s2,s1,1161
andi s1,s1,364
sub s5,s1,s1
sltu s1,s1,s2
slli s1,s3,31
beq s1,s1,rand_control_31
addi s2,s2,1
rand_control_31:
beq s4,s4,rand_control_32
addi s2,s2,1
rand_control_32:
srai s4,s3,8
slt s2,s3,s5
slt s4,s1,s2
sll s4,s2,s1
sltu s2,s3,s5
sll s5,s2,s3
ori s1,s2,1532
sub s3,s1,s1
sltu s1,s4,s4
slli s3,s4,22
add s1,s5,s1
slli s5,s2,11
ori s3,s2,-1689
srli s5,s1,7
xori s2,s2,607
bne s4,s4,rand_control_48
addi s5,s5,1
rand_control_48:
xori s2,s5,1692
srli s3,s5,0
addi s5,s2,-1604
slt s5,s3,s2
slt s5,s5,s4
xori s5,s4,-1947
srai s2,s5,21
andi s5,s1,1595
ori s5,s4,-807
srl s5,s5,s2
xor s1,s1,s2
xor s4,s2,s4
ori s1,s3,1686
srl s3,s4,s4
ori s5,s4,131
ori s5,s1,1564
slt s3,s1,s3
beq s1,s1,rand_control_66
addi s5,s5,1
rand_control_66:
slt s2,s4,s2
xori s1,s3,850
beq s4,s4,rand_control_69
addi s4,s4,1
rand_control_69:
xori s5,s4,32
srl s3,s1,s4
srl s2,s2,s3
addi s4,s3,1771
sltu s1,s1,s3
slt s1,s4,s5
andi s4,s4,-1973
slt s1,s1,s2
sll s3,s1,s5
xor s5,s3,s5
add s4,s2,s4
sub s4,s4,s3
srli s1,s3,28
or s4,s4,s4
srai s1,s1,6
xor s1,s1,s1
beq s3,s3,rand_control_86
addi s2,s2,1
rand_control_86:
addi s4,s1,672
or s1,s4,s1
beq s1,s1,rand_control_89
addi s3,s3,1
rand_control_89:
and s3,s5,s3
add s1,s1,s5
bne s2,s2,rand_control_92
addi s5,s5,1
rand_control_92:
srl s5,s3,s1
srli s3,s1,13
xori s4,s3,1177
sll s1,s1,s4
slli s4,s1,16
or s5,s2,s2
sll s5,s3,s3
add s4,s5,s3
xor s1,s1,s1
and s1,s5,s2
add s2,s3,s4
andi s1,s1,861
ori s3,s3,-375
ori s2,s5,-974
xor s1,s5,s2
addi s1,s4,1007
sub s4,s3,s2
xor s2,s5,s1
srai s3,s4,5
sub s2,s5,s4
slli s3,s3,1
xor s5,s2,s4
or s5,s3,s2
and s5,s1,s3
sub s5,s3,s3
ori s2,s1,-1728
slt s2,s5,s5
sub s1,s5,s1
xor s3,s3,s3
srai s4,s2,6
bne s1,s1,rand_control_123
addi s4,s4,1
rand_control_123:
ori s5,s2,1584
or s4,s4,s1
add s3,s1,s1
sll s3,s2,s5
sltu s2,s1,s1
addi s2,s2,-782
beq s3,s3,rand_control_130
addi s5,s5,1
rand_control_130:
ori s1,s5,1353
sub s5,s4,s1
srli s2,s3,14
or s5,s4,s4
andi s1,s3,452
xor s4,s1,s5
and s4,s1,s5
andi s2,s2,-1555
srl s3,s3,s1
slli s3,s1,25
sll s1,s3,s3
sltu s2,s4,s2
sltu s2,s5,s5
add s4,s5,s2
srai s1,s5,5
and s2,s2,s2
srli s5,s2,6
slli s3,s1,25
sltu s1,s4,s2
slli s5,s1,8
srl s3,s2,s5
srli s5,s3,17
xor s3,s5,s1
add s2,s3,s2
sll s5,s3,s4
slli s4,s4,13
or s3,s5,s4
addi s4,s5,-768
srai s4,s4,23
andi s1,s1,948
and s4,s2,s2
sub s1,s2,s1
srl s1,s5,s2
sll s1,s1,s5
slli s2,s4,27
sub s3,s5,s1
xori s5,s1,1843
srli s1,s1,23
beq s4,s4,rand_control_169
addi s2,s2,1
rand_control_169:
and s1,s4,s3
or s1,s4,s4
slt s5,s4,s1
sll s2,s5,s5
slli s2,s1,15
ori s5,s2,1077
xori s4,s2,-1760
bne s2,s2,rand_control_177
addi s3,s3,1
rand_control_177:
xori s1,s3,-1649
and s4,s1,s3
beq s3,s3,rand_control_180
addi s5,s5,1
rand_control_180:
and s2,s5,s5
slli s3,s3,4
srai s5,s5,18
bne s3,s3,rand_control_184
addi s5,s5,1
rand_control_184:
or s5,s4,s3
srli s4,s4,14
srli s5,s5,30
slt s4,s4,s5
andi s2,s2,-1061
sltu s5,s4,s3
bne s4,s4,rand_control_191
addi s5,s5,1
rand_control_191:
and s2,s2,s3
xor s4,s3,s2
and s5,s5,s1
slli s1,s3,5
srl s4,s3,s4
xori s4,s2,-470
xor s3,s5,s3
xori s2,s2,-16
addi s4,s5,-1670
bne s1,s1,rand_control_201
addi s1,s1,1
rand_control_201:
xor s1,s4,s2
add s3,s3,s2
andi s5,s4,-930
or s4,s3,s3
add s4,s2,s1
bne s3,s3,rand_control_207
addi s2,s2,1
rand_control_207:
sltu s4,s5,s4
xori s5,s1,-622
sll s2,s5,s3
srai s3,s2,28
bne s3,s3,rand_control_212
addi s3,s3,1
rand_control_212:
xor s1,s2,s1
or s4,s5,s4
sltu s5,s1,s5
ori s3,s5,-1571
ori s2,s4,-1589
srai s3,s5,25
or s1,s4,s4
slli s3,s3,9
xor s4,s3,s5
sub s1,s3,s1
slt s4,s3,s3
add s3,s3,s1
and s1,s3,s2
slli s1,s4,16
sll s4,s5,s1
slt s2,s2,s2
xori s3,s5,1307
srli s5,s1,22
slt s2,s4,s2
srai s2,s2,17
srai s1,s3,26
slli s4,s3,29
beq s4,s4,rand_control_235
addi s3,s3,1
rand_control_235:
addi s4,s3,-1298
sll s2,s4,s3
add s2,s4,s1
addi s3,s1,2040
add s5,s1,s1
add s2,s5,s5
andi s5,s4,-1652
sltu s2,s1,s3
beq s4,s4,rand_control_244
addi s1,s1,1
rand_control_244:
srl s2,s5,s3
addi s5,s1,-1750
slt s5,s4,s1
bne s4,s4,rand_control_248
addi s3,s3,1
rand_control_248:
sll s2,s3,s4
or s1,s5,s1
sltu s5,s1,s1
sltu s2,s3,s3
srai s3,s1,29
slt s2,s5,s3
ori s2,s3,-1467
add s3,s1,s3
ori s4,s4,1928
sltu s4,s4,s1
sub s4,s3,s4
srli s4,s1,8
sub s4,s5,s2
slli s4,s2,23
slli s5,s5,2
andi s5,s4,-280
and s2,s4,s5
ori s5,s5,-1327
slt s3,s5,s2
addi s1,s2,-426
add s3,s4,s4
xor s1,s1,s4
or s3,s4,s2
ori s1,s4,-1415
sltu s4,s4,s2
slt s3,s1,s4
add s4,s1,s3
slt s3,s3,s5
beq s2,s2,rand_control_277
addi s3,s3,1
rand_control_277:
slli s1,s4,5
beq s1,s1,rand_control_279
addi s5,s5,1
rand_control_279:
slli s4,s4,12
srli s4,s2,17
or s2,s4,s4
srli s1,s4,8
xor s5,s5,s3
bne s5,s5,rand_control_285
addi s5,s5,1
rand_control_285:
slt s1,s4,s3
addi s4,s4,-1605
srli s5,s5,14
sll s3,s4,s4
sltu s5,s2,s2
slt s3,s4,s1
bne s2,s2,rand_control_292
addi s2,s2,1
rand_control_292:
add s3,s3,s1
slli s4,s4,13
add s4,s5,s2
sll s2,s4,s2
bne s3,s3,rand_control_297
addi s5,s5,1
rand_control_297:
srli s5,s5,9
slt s3,s3,s5
srli s5,s2,3
sltu s4,s1,s3
sub s5,s3,s1
and s1,s4,s3
slli s3,s2,31
sltu s5,s5,s3
sltu s3,s1,s1
xor s2,s3,s3
slli s1,s2,4
andi s3,s3,1811
ori s4,s2,1283
andi s4,s3,-70
sll s1,s5,s4
xori s1,s1,1767
slli s1,s5,2
andi s5,s3,763
bne s3,s3,rand_control_316
addi s1,s1,1
rand_control_316:
slt s5,s1,s1
add s5,s2,s2
or s1,s3,s1
srli s4,s1,6
srai s4,s3,9
beq s2,s2,rand_control_322
addi s3,s3,1
rand_control_322:
ori s4,s4,1991
sub s3,s2,s2
andi s2,s4,-238
bne s1,s1,rand_control_326
addi s3,s3,1
rand_control_326:
slt s1,s5,s3
and s3,s4,s3
add s5,s2,s3
xor s5,s3,s3
slli s1,s5,14
slli s3,s1,6
beq s5,s5,rand_control_333
addi s3,s3,1
rand_control_333:
srl s4,s4,s1
sll s1,s2,s1
slli s4,s4,30
ori s1,s5,924
add s3,s5,s5
ori s3,s2,941
and s5,s2,s5
srl s1,s1,s2
xor s4,s2,s5
sub s4,s2,s4
slt s3,s5,s3
add s1,s1,s1
xori s4,s3,-990
xori s2,s4,-734
or s5,s3,s3
srli s3,s2,13
ori s5,s3,-1213
addi s5,s4,611
sltu s4,s1,s3
add s4,s5,s1
bne s1,s1,rand_control_354
addi s2,s2,1
rand_control_354:
slt s3,s3,s3
xori s2,s1,643
addi s4,s1,-687
ori s2,s1,-879
addi s5,s1,409
srai s2,s3,19
and s4,s5,s2
sll s4,s3,s4
or s3,s3,s5
srl s1,s5,s3
slt s5,s5,s2
xori s2,s1,1020
add s2,s2,s2
sub s3,s2,s3
xor s4,s3,s1
srl s1,s1,s3
addi s3,s3,-1034
ori s3,s1,1993
and s4,s3,s3
beq s2,s2,rand_control_374
addi s5,s5,1
rand_control_374:
add s5,s1,s1
beq s1,s1,rand_control_376
addi s2,s2,1
rand_control_376:
srli s2,s1,31
sltu s4,s3,s3
or s5,s5,s4
xori s1,s2,-1179
andi s4,s5,19
sll s2,s3,s3
srl s3,s4,s5
beq s3,s3,rand_control_384
addi s2,s2,1
rand_control_384:
bne s5,s5,rand_control_385
addi s5,s5,1
rand_control_385:
addi s5,s3,838
andi s3,s2,-1416
and s2,s3,s5
sltu s3,s4,s3
beq s5,s5,rand_control_390
addi s5,s5,1
rand_control_390:
add s5,s3,s2
xor s4,s2,s3
or s1,s4,s5
or s5,s5,s5
srli s5,s3,9
and s3,s5,s1
xor s3,s3,s1
beq s5,s5,rand_control_398
addi s1,s1,1
rand_control_398:
xori s4,s5,-388
sltu s3,s1,s2
or s4,s1,s5
sll s4,s3,s1
srl s1,s5,s1
srl s1,s5,s2
beq s1,s1,rand_control_405
addi s2,s2,1
rand_control_405:
xor s5,s5,s2
xori s1,s4,1435
andi s3,s4,816
or s4,s4,s2
srl s5,s4,s4
and s1,s1,s3
ori s1,s1,1698
xor s1,s5,s3
or s4,s2,s4
and s4,s4,s3
ori s5,s2,-1200
srli s3,s1,10
addi s2,s1,921
slt s1,s1,s3
srl s4,s4,s5
sub s2,s3,s5
bne s3,s3,rand_control_422
addi s3,s3,1
rand_control_422:
slli s3,s5,12
sub s2,s5,s3
beq s4,s4,rand_control_425
addi s5,s5,1
rand_control_425:
xor s4,s2,s1
sub s2,s4,s2
sltu s4,s4,s1
sltu s5,s4,s3
slt s4,s3,s4
bne s1,s1,rand_control_431
addi s5,s5,1
rand_control_431:
bne s1,s1,rand_control_432
addi s2,s2,1
rand_control_432:
sll s1,s5,s5
add s3,s1,s2
srli s4,s4,5
add s2,s2,s4
slt s5,s5,s2
andi s3,s4,-724
sub s3,s1,s5
beq s5,s5,rand_control_440
addi s4,s4,1
rand_control_440:
slt s2,s5,s5
sub s3,s4,s3
xori s2,s1,-1761
add s3,s4,s1
xori s1,s4,769
beq s1,s1,rand_control_446
addi s4,s4,1
rand_control_446:
bne s3,s3,rand_control_447
addi s2,s2,1
rand_control_447:
andi s2,s2,-360
srai s4,s5,21
slli s4,s4,22
srl s4,s5,s2
slt s4,s4,s1
xori s5,s5,1508
or s1,s1,s1
sltu s2,s5,s3
xori s1,s3,-98
sub s5,s3,s3
slt s5,s4,s5
sltu s4,s4,s2
and s2,s1,s3
srli s3,s3,16
sltu s1,s5,s5
slt s3,s4,s5
sub s5,s4,s1
and s2,s1,s3
andi s3,s2,-1325
and s5,s2,s3
slli s4,s2,1
srli s1,s4,15
bne s3,s3,rand_control_470
addi s5,s5,1
rand_control_470:
srai s5,s3,30
addi s1,s3,-934
slt s2,s4,s1
and s3,s3,s4
srai s1,s3,14
ori s1,s2,1804
srli s2,s2,18
ori s1,s3,1323
addi s2,s3,-1209
sltu s3,s5,s1
add s3,s5,s4
srli s1,s4,6
add s1,s2,s4
ori s1,s1,-1656
or s1,s5,s4
slli s3,s3,4
and s5,s2,s4
srai s2,s5,17
srl s5,s1,s4
xori s2,s1,1187
or s4,s2,s4
sltu s3,s5,s4
and s5,s4,s2
or s5,s5,s4
sll s4,s5,s3
xor s2,s3,s3
andi s1,s4,444
xori s2,s5,-1743
sub s4,s1,s1
srai s4,s1,4
addi s3,s4,2005
sltu s1,s1,s3
bne s3,s3,rand_control_503
addi s1,s1,1
rand_control_503:
addi s4,s4,-1077
sub s2,s5,s1
and s1,s5,s1
add s5,s4,s4
xor s2,s3,s2
bne s4,s4,rand_control_509
addi s2,s2,1
rand_control_509:
slt s1,s2,s3
bne s2,s2,rand_control_511
addi s3,s3,1
rand_control_511:
sltu s4,s1,s2
or s1,s5,s2
andi s5,s2,-1541
add s4,s5,s4
xori s3,s5,-1864
andi s1,s5,973
sll s3,s2,s3
sub s1,s3,s5
slt s4,s5,s5
sltu s3,s3,s5
add s4,s3,s3
slli s1,s3,4
sltu s4,s2,s5
srli s2,s3,7
addi s1,s5,1821
sll s5,s3,s1
sltu s2,s3,s2
sll s3,s2,s5
ori s1,s5,1146
srai s1,s3,20
bne s2,s2,rand_control_532
addi s5,s5,1
rand_control_532:
srai s1,s3,15
sll s5,s3,s1
sltu s1,s1,s1
and s4,s3,s2
beq s3,s3,rand_control_537
addi s3,s3,1
rand_control_537:
beq s5,s5,rand_control_538
addi s1,s1,1
rand_control_538:
or s1,s3,s2
andi s3,s3,1379
add s2,s2,s2
add s1,s3,s1
srl s3,s1,s5
sll s2,s3,s5
bne s1,s1,rand_control_545
addi s2,s2,1
rand_control_545:
slt s3,s2,s5
srli s4,s5,24
bne s5,s5,rand_control_548
addi s5,s5,1
rand_control_548:
slli s5,s4,20
andi s5,s5,1971
bne s4,s4,rand_control_551
addi s4,s4,1
rand_control_551:
andi s1,s3,-1685
or s2,s5,s1
sll s4,s3,s5
sll s1,s5,s3
and s4,s2,s3
and s1,s2,s4
bne s1,s1,rand_control_558
addi s4,s4,1
rand_control_558:
ori s5,s4,1502
srl s2,s1,s2
or s3,s5,s3
srli s2,s4,12
bne s3,s3,rand_control_563
addi s2,s2,1
rand_control_563:
addi s2,s4,-50
slli s4,s5,7
bne s3,s3,rand_control_566
addi s1,s1,1
rand_control_566:
slt s3,s3,s2
bne s2,s2,rand_control_568
addi s1,s1,1
rand_control_568:
ori s1,s4,770
and s5,s2,s1
or s3,s5,s5
beq s1,s1,rand_control_572
addi s3,s3,1
rand_control_572:
srl s2,s5,s3
sltu s4,s4,s2
beq s2,s2,rand_control_575
addi s3,s3,1
rand_control_575:
and s4,s1,s5
sll s1,s1,s5
xor s4,s5,s2
srl s2,s1,s5
andi s2,s2,-1963
bne s2,s2,rand_control_581
addi s3,s3,1
rand_control_581:
sub s2,s3,s2
srl s3,s4,s5
sltu s1,s5,s2
sll s3,s1,s3
addi s3,s1,1837
sub s3,s2,s2
srai s4,s5,5
sltu s5,s3,s4
add s1,s1,s1
addi s5,s4,1438
or s2,s3,s3
and s5,s2,s4
srl s5,s2,s4
and s3,s2,s5
srl s2,s5,s5
add s1,s1,s5
andi s5,s3,-982
and s4,s3,s2
sub s4,s5,s1
slli s4,s2,15
sll s1,s2,s1
sltu s5,s2,s5
sll s5,s1,s3
xor s2,s5,s3
slli s4,s2,2
addi s2,s2,403
beq s5,s5,rand_control_608
addi s2,s2,1
rand_control_608:
andi s5,s5,-1501
andi s5,s1,524
srli s5,s5,29
srai s5,s5,0
beq s5,s5,rand_control_613
addi s2,s2,1
rand_control_613:
or s5,s1,s3
andi s3,s3,-1232
sll s2,s4,s4
srli s2,s5,13
add s3,s3,s3
beq s4,s4,rand_control_619
addi s3,s3,1
rand_control_619:
slli s3,s4,13
andi s3,s3,353
slli s3,s5,21
addi s2,s2,674
slt s3,s2,s4
and s1,s2,s3
or s2,s2,s1
beq s4,s4,rand_control_627
addi s4,s4,1
rand_control_627:
or s1,s2,s2
sll s4,s5,s4
srai s2,s3,27
srai s4,s5,19
ori s2,s1,1479
srl s5,s5,s3
beq s1,s1,rand_control_634
addi s5,s5,1
rand_control_634:
slli s2,s2,23
xori s3,s3,1744
sll s1,s4,s1
add s5,s5,s4
beq s3,s3,rand_control_639
addi s5,s5,1
rand_control_639:
add s3,s1,s2
add s1,s3,s4
and s3,s3,s3
add s1,s4,s5
bne s5,s5,rand_control_644
addi s5,s5,1
rand_control_644:
srl s2,s4,s1
beq s2,s2,rand_control_646
addi s2,s2,1
rand_control_646:
xori s1,s2,1927
ori s5,s4,-1065
bne s2,s2,rand_control_649
addi s3,s3,1
rand_control_649:
sltu s3,s2,s3
sub s5,s4,s1
sll s4,s3,s4
srli s3,s4,4
srai s2,s4,20
and s1,s2,s2
slli s3,s1,9
slli s2,s2,27
srl s5,s2,s3
ori s4,s3,-1290
add s3,s2,s3
xor s3,s4,s3
xor s5,s5,s4
sltu s3,s4,s3
sltu s5,s1,s4
srai s5,s3,17
sltu s2,s2,s4
bne s4,s4,rand_control_667
addi s4,s4,1
rand_control_667:
add s5,s5,s4
bne s4,s4,rand_control_669
addi s1,s1,1
rand_control_669:
bne s5,s5,rand_control_670
addi s2,s2,1
rand_control_670:
beq s5,s5,rand_control_671
addi s3,s3,1
rand_control_671:
srl s5,s4,s4
slt s4,s1,s3
xori s2,s2,779
bne s3,s3,rand_control_675
addi s3,s3,1
rand_control_675:
addi s1,s4,1331
srl s1,s5,s1
slli s2,s5,11
slt s3,s4,s1
sll s1,s1,s4
xori s4,s2,-232
slt s1,s5,s1
andi s4,s2,-1677
sll s1,s4,s3
ori s2,s4,121
sll s3,s5,s2
beq s5,s5,rand_control_687
addi s3,s3,1
rand_control_687:
sltu s2,s2,s4
sub s3,s2,s3
ori s2,s4,1144
and s2,s2,s4
andi s3,s3,1523
slt s3,s5,s1
addi s3,s5,-1243
xori s5,s5,-1274
andi s3,s1,1029
srl s2,s5,s4
xori s1,s2,1384
slt s2,s1,s1
beq s1,s1,rand_control_700
addi s1,s1,1
rand_control_700:
slli s3,s5,25
srai s1,s1,8
srl s5,s5,s1
srli s2,s4,23
srai s5,s1,12
beq s2,s2,rand_control_706
addi s5,s5,1
rand_control_706:
srai s4,s4,0
srai s4,s3,17
srli s1,s1,14
add s3,s5,s3
slt s1,s1,s4
bne s4,s4,rand_control_712
addi s5,s5,1
rand_control_712:
srli s5,s1,23
slli s2,s4,24
and s1,s2,s3
srl s1,s3,s1
sub s3,s1,s2
xor s4,s4,s2
srl s3,s1,s3
bne s4,s4,rand_control_720
addi s5,s5,1
rand_control_720:
add s3,s2,s2
xori s3,s5,1281
sltu s5,s1,s1
and s4,s2,s2
slt s5,s4,s2
and s2,s1,s2
or s1,s4,s1
bne s3,s3,rand_control_728
addi s2,s2,1
rand_control_728:
andi s5,s3,1568
andi s5,s5,1405
and s5,s5,s4
sub s1,s4,s3
xor s3,s5,s2
beq s5,s5,rand_control_734
addi s2,s2,1
rand_control_734:
ori s4,s2,-443
slt s1,s5,s4
sub s4,s3,s5
ori s3,s2,1860
addi s2,s1,882
xor s2,s4,s1
slli s1,s3,31
srl s5,s1,s3
add s1,s3,s5
srli s3,s2,27
ori s3,s3,1514
ori s5,s1,-214
add s1,s1,s4
xor s1,s4,s2
sll s1,s2,s5
sll s1,s1,s3
and s4,s2,s1
ori s4,s5,1933
ori s4,s1,1917
sub s2,s5,s2
sll s3,s3,s2
srai s5,s5,15
beq s5,s5,rand_control_757
addi s5,s5,1
rand_control_757:
beq s3,s3,rand_control_758
addi s2,s2,1
rand_control_758:
or s1,s4,s3
bne s5,s5,rand_control_760
addi s5,s5,1
rand_control_760:
sltu s2,s4,s1
sll s4,s3,s5
srli s1,s2,26
sltu s4,s5,s2
slli s3,s5,27
sltu s1,s2,s1
add s5,s1,s4
bne s4,s4,rand_control_768
addi s2,s2,1
rand_control_768:
bne s2,s2,rand_control_769
addi s1,s1,1
rand_control_769:
sltu s2,s1,s4
or s4,s5,s5
srai s4,s2,7
beq s3,s3,rand_control_773
addi s2,s2,1
rand_control_773:
slli s3,s1,16
slt s4,s5,s1
slt s4,s4,s5
add s4,s5,s4
slt s5,s2,s3
slli s2,s3,14
sub s3,s2,s5
xori s4,s4,-1755
slli s4,s3,15
srli s2,s4,25
bne s1,s1,rand_control_784
addi s1,s1,1
rand_control_784:
or s2,s1,s2
slt s4,s5,s2
or s1,s5,s1
beq s3,s3,rand_control_788
addi s4,s4,1
rand_control_788:
addi s5,s4,257
sub s1,s3,s3
add s1,s2,s3
and s1,s1,s4
sltu s5,s5,s5
sub s3,s1,s3
xor s2,s3,s1
srai s5,s5,24
sll s4,s5,s5
sub s3,s3,s1
sub s1,s5,s2
andi s5,s2,-892
srli s3,s4,16
or s1,s3,s3
and s3,s5,s5
slli s2,s3,11
andi s2,s1,1546
and s1,s4,s5
bne s1,s1,rand_control_807
addi s4,s4,1
rand_control_807:
xor s4,s3,s2
sub s4,s5,s1
srli s2,s4,3
andi s2,s5,820
andi s3,s4,1134
ori s4,s2,1938
addi s5,s2,602
or s1,s4,s4
sltu s4,s2,s1
sub s5,s4,s3
bne s5,s5,rand_control_818
addi s2,s2,1
rand_control_818:
beq s2,s2,rand_control_819
addi s2,s2,1
rand_control_819:
slt s1,s3,s3
addi s1,s3,-138
srai s3,s2,3
slt s2,s5,s3
bne s2,s2,rand_control_824
addi s5,s5,1
rand_control_824:
add s5,s1,s3
bne s1,s1,rand_control_826
addi s5,s5,1
rand_control_826:
and s4,s5,s3
andi s1,s2,761
xor s5,s4,s5
xor s2,s5,s4
xori s3,s5,-255
srli s5,s1,14
ori s5,s5,-1511
slli s2,s2,21
or s3,s4,s4
sltu s4,s4,s4
sub s2,s1,s1
slli s4,s4,9
srai s3,s2,17
ori s3,s1,1177
sll s3,s1,s4
xori s3,s2,853
sll s2,s1,s1
slt s2,s2,s1
or s3,s5,s1
addi s5,s4,-1965
or s4,s3,s1
sub s5,s4,s3
beq s1,s1,rand_control_849
addi s1,s1,1
rand_control_849:
ori s3,s4,-76
slli s5,s2,23
sub s4,s3,s3
addi s3,s2,-392
srl s3,s1,s1
addi s1,s4,1587
srl s5,s5,s4
addi s3,s2,-1494
addi s1,s1,1864
bne s2,s2,rand_control_859
addi s3,s3,1
rand_control_859:
sltu s3,s4,s3
and s4,s2,s2
bne s4,s4,rand_control_862
addi s1,s1,1
rand_control_862:
sltu s2,s1,s5
xori s1,s1,1238
beq s1,s1,rand_control_865
addi s5,s5,1
rand_control_865:
slli s4,s2,5
ori s4,s2,-584
srl s4,s1,s4
srl s5,s1,s1
sltu s2,s5,s2
slli s1,s2,23
slli s3,s1,10
add s2,s2,s4
sltu s1,s4,s1
addi s2,s4,1829
srl s2,s5,s2
add s5,s4,s2
beq s2,s2,rand_control_878
addi s5,s5,1
rand_control_878:
xori s1,s4,614
beq s2,s2,rand_control_880
addi s3,s3,1
rand_control_880:
sub s4,s2,s1
xor s5,s1,s4
srai s4,s4,9
addi s4,s1,-869
beq s4,s4,rand_control_885
addi s2,s2,1
rand_control_885:
or s4,s5,s2
and s4,s5,s2
xor s1,s1,s4
andi s3,s2,-82
and s3,s5,s4
ori s2,s2,199
add s3,s4,s4
srl s5,s3,s5
or s3,s2,s3
sll s2,s3,s4
sltu s3,s3,s3
xor s1,s2,s5
beq s5,s5,rand_control_898
addi s1,s1,1
rand_control_898:
slli s3,s3,24
ori s4,s5,1535
srl s3,s3,s2
beq s4,s4,rand_control_902
addi s2,s2,1
rand_control_902:
sll s2,s3,s1
bne s2,s2,rand_control_904
addi s5,s5,1
rand_control_904:
ori s2,s4,1876
beq s5,s5,rand_control_906
addi s2,s2,1
rand_control_906:
beq s2,s2,rand_control_907
addi s2,s2,1
rand_control_907:
beq s3,s3,rand_control_908
addi s5,s5,1
rand_control_908:
ori s2,s1,1109
ori s1,s1,543
slli s1,s4,0
ori s3,s5,-1604
slt s4,s1,s5
addi s4,s1,202
sltu s4,s2,s3
bne s1,s1,rand_control_916
addi s4,s4,1
rand_control_916:
slt s2,s4,s1
add s3,s5,s1
sltu s4,s3,s2
addi s2,s2,1139
xori s3,s2,-1938
srl s3,s3,s3
slt s1,s4,s3
slt s3,s5,s2
srl s4,s2,s4
slli s2,s2,3
bne s5,s5,rand_control_927
addi s3,s3,1
rand_control_927:
ori s4,s5,-39
sll s1,s1,s3
slli s3,s2,22
andi s3,s4,1090
srli s3,s2,9
and s3,s4,s1
and s3,s4,s1
add s5,s1,s5
xori s1,s1,328
and s1,s3,s3
add s3,s3,s4
bne s2,s2,rand_control_939
addi s1,s1,1
rand_control_939:
or s4,s4,s3
sltu s2,s5,s5
slt s5,s3,s2
andi s1,s1,-1831
andi s3,s1,174
addi s4,s4,-660
sll s4,s1,s1
sltu s3,s2,s2
slli s4,s2,19
srl s3,s1,s1
slli s5,s1,7
andi s1,s2,-530
xori s4,s1,-1557
slli s4,s5,12
sub s4,s3,s2
slt s3,s4,s2
sll s5,s3,s4
bne s3,s3,rand_control_957
addi s5,s5,1
rand_control_957:
addi s3,s4,-1772
beq s3,s3,rand_control_959
addi s2,s2,1
rand_control_959:
sll s3,s4,s4
srl s1,s3,s2
sll s4,s1,s3
beq s4,s4,rand_control_963
addi s5,s5,1
rand_control_963:
andi s2,s5,239
ori s5,s4,-1122
add s2,s2,s5
xori s2,s5,-51
srai s2,s4,27
add s2,s1,s3
slli s3,s2,19
xori s1,s3,50
andi s5,s1,-1148
srai s2,s1,17
and s5,s3,s3
andi s1,s4,1398
xor s2,s2,s4
beq s1,s1,rand_control_977
addi s2,s2,1
rand_control_977:
ori s3,s1,-976
ori s3,s4,1983
add s1,s5,s4
xori s5,s2,-1740
slli s4,s4,5
addi s4,s4,796
xori s3,s1,2
srl s1,s2,s2
srli s4,s2,9
or s5,s4,s5
srli s4,s4,30
and s3,s2,s4
xor s5,s2,s3
beq s1,s1,rand_control_991
addi s4,s4,1
rand_control_991:
and s5,s4,s3
sltu s3,s5,s2
sub s4,s2,s2
ori s3,s3,-23
or s3,s2,s5
beq s5,s5,rand_control_997
addi s1,s1,1
rand_control_997:
andi s5,s3,-142
sub s5,s5,s4
add s2,s2,s5
slli s4,s3,9
srl s5,s3,s5
srli s2,s1,9
addi s2,s4,-1490
ori s4,s1,243
and s3,s3,s2
sltu s4,s1,s2
srli s1,s4,6
add s5,s1,s4
slli s4,s1,13
xori s4,s4,1674
or s4,s2,s4
and s4,s5,s1
xori s1,s1,128
andi s4,s3,-318
and s4,s5,s1
sltu s2,s1,s4
sub s4,s4,s3
or s2,s1,s1
srai s1,s1,20
bne s2,s2,rand_control_1021
addi s3,s3,1
rand_control_1021:
andi s5,s4,-838
addi s1,s2,1445
srl s3,s3,s5
andi s2,s4,1271
addi s4,s2,829
sll s2,s5,s5
slt s4,s2,s2
beq s3,s3,rand_control_1029
addi s1,s1,1
rand_control_1029:
and s2,s4,s2
sub s4,s2,s3
beq s2,s2,rand_control_1032
addi s1,s1,1
rand_control_1032:
addi s5,s3,-1633
add s5,s5,s5
slli s1,s1,4
xori s1,s4,-1072
ori s5,s3,215
sub s4,s3,s1
add s2,s1,s4
slt s5,s1,s3
sub s5,s3,s2
addi s2,s2,1361
xor s3,s1,s2
xor s4,s1,s5
beq s3,s3,rand_control_1045
addi s2,s2,1
rand_control_1045:
sub s4,s4,s2
srai s4,s2,27
and s3,s2,s1
beq s5,s5,rand_control_1049
addi s3,s3,1
rand_control_1049:
andi s2,s3,20
or s3,s2,s3
slli s2,s3,8
srl s2,s4,s1
srli s2,s5,1
sub s5,s4,s1
sll s5,s3,s3
sub s3,s5,s2
ori s3,s2,1797
addi s5,s4,-414
andi s2,s3,807
bne s2,s2,rand_control_1061
addi s4,s4,1
rand_control_1061:
srli s4,s4,17
andi s1,s3,-168
sltu s3,s2,s4
sltu s3,s2,s3
ori s1,s3,-1370
slt s4,s2,s2
slli s1,s1,3
srai s3,s5,28
sub s3,s2,s2
slt s4,s3,s1
ori s2,s2,-1481
xor s2,s5,s3
add s2,s2,s1
xori s5,s2,-1114
srli s5,s1,8
ori s3,s5,395
sll s4,s2,s5
sub s3,s1,s5
bne s2,s2,rand_control_1080
addi s2,s2,1
rand_control_1080:
slt s5,s3,s3
slt s5,s2,s3
srli s4,s1,18
sll s4,s2,s5
srai s4,s1,11
srl s3,s2,s3
srli s1,s2,24
and s1,s1,s2
xor s4,s4,s5
slt s2,s2,s2
srai s5,s2,12
sub s3,s5,s1
xori s4,s5,-1625
andi s2,s4,645
sub s5,s3,s3
addi s3,s3,1036
srl s5,s1,s5
xor s2,s3,s2
beq s4,s4,rand_control_1099
addi s2,s2,1
rand_control_1099:
xori s5,s5,-686
or s5,s4,s2
beq s2,s2,rand_control_1102
addi s4,s4,1
rand_control_1102:
xori s4,s1,549
andi s5,s3,444
srli s5,s4,18
addi s2,s3,-1524
sub s5,s4,s3
sub s2,s4,s4
or s1,s2,s3
addi s2,s4,803
sll s3,s5,s2
sltu s4,s5,s5
andi s3,s5,1749
slli s2,s2,29
and s5,s3,s2
bne s5,s5,rand_control_1116
addi s4,s4,1
rand_control_1116:
andi s2,s4,148
addi s3,s4,-27
sub s1,s5,s2
or s1,s3,s5
add s3,s3,s4
addi s1,s4,-142
srli s1,s4,27
ori s1,s2,-883
xor s2,s4,s5
and s5,s5,s4
xor s1,s5,s4
sll s2,s5,s2
bne s2,s2,rand_control_1129
addi s5,s5,1
rand_control_1129:
xori s3,s4,1040
sll s3,s1,s2
ori s5,s4,-24
sltu s5,s4,s1
srai s2,s4,23
and s1,s5,s2
addi s3,s1,-1658
ori s3,s5,-194
sll s5,s2,s2
beq s2,s2,rand_control_1139
addi s5,s5,1
rand_control_1139:
bne s1,s1,rand_control_1140
addi s5,s5,1
rand_control_1140:
sll s2,s2,s4
xori s3,s5,-1506
ori s1,s1,633
sltu s3,s1,s1
slt s4,s4,s5
xor s3,s2,s1
xori s3,s1,658
sltu s3,s4,s1
sll s4,s5,s5
or s2,s4,s1
ori s2,s4,-1394
add s3,s5,s2
xori s1,s3,-986
beq s1,s1,rand_control_1154
addi s5,s5,1
rand_control_1154:
srl s2,s4,s4
srl s2,s3,s5
srl s2,s5,s2
addi s5,s2,679
sltu s5,s3,s5
sub s5,s5,s4
bne s4,s4,rand_control_1161
addi s4,s4,1
rand_control_1161:
beq s5,s5,rand_control_1162
addi s1,s1,1
rand_control_1162:
xor s3,s3,s4
bne s1,s1,rand_control_1164
addi s5,s5,1
rand_control_1164:
xor s2,s4,s1
srli s1,s2,28
xor s2,s4,s2
andi s2,s2,1385
bne s2,s2,rand_control_1169
addi s5,s5,1
rand_control_1169:
sltu s5,s2,s5
slt s4,s4,s2
and s1,s1,s3
addi s2,s4,1300
slt s4,s4,s5
and s2,s3,s5
xori s4,s3,-1381
bne s3,s3,rand_control_1177
addi s3,s3,1
rand_control_1177:
srli s4,s5,22
bne s3,s3,rand_control_1179
addi s3,s3,1
rand_control_1179:
bne s4,s4,rand_control_1180
addi s4,s4,1
rand_control_1180:
sltu s3,s5,s4
andi s4,s4,1135
andi s3,s3,-213
addi s5,s4,55
ori s5,s2,-783
addi s3,s1,-1330
xor s1,s4,s4
addi s2,s2,993
sub s2,s1,s5
and s5,s2,s2
sub s2,s4,s1
beq s4,s4,rand_control_1192
addi s3,s3,1
rand_control_1192:
srli s3,s4,8
srl s3,s4,s4
sltu s1,s5,s1
sll s2,s1,s5
sub s2,s1,s3
slli s4,s1,25
bne s4,s4,rand_control_1199
addi s4,s4,1
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

