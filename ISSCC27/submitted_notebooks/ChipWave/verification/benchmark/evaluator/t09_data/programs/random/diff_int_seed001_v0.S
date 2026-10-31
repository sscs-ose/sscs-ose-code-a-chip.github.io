.option norvc
.section .text.init
.globl _start
_start:
la s0,scratch
li t0,0x90000000
li s1,4009673291
li s2,3988500318
li s3,1030600311
li s4,1428154898
li s5,2057213961
srai s4,s5,5
xori s3,s3,713
add s3,s4,s1
srai s4,s1,2
srl s4,s3,s1
sll s3,s5,s3
andi s4,s1,776
or s4,s2,s3
sll s5,s1,s4
slli s4,s2,19
addi s3,s2,1889
xor s3,s4,s5
slt s2,s5,s1
ori s1,s3,1298
addi s2,s1,-1514
xori s2,s5,-1677
ori s4,s2,-1473
sll s5,s4,s4
slt s2,s3,s2
srli s3,s4,4
xor s5,s5,s4
srai s3,s2,21
andi s4,s4,1866
or s1,s5,s3
bne s1,s1,rand_control_24
addi s5,s5,1
rand_control_24:
or s1,s1,s3
ori s5,s5,1915
slt s2,s5,s2
sltu s3,s1,s1
or s5,s3,s3
srl s1,s2,s5
xor s3,s4,s2
xori s1,s3,-1017
or s4,s5,s2
sub s5,s1,s1
sll s3,s2,s2
sub s5,s2,s4
xori s2,s1,-369
or s3,s3,s4
andi s3,s3,-1185
beq s1,s1,rand_control_40
addi s3,s3,1
rand_control_40:
sub s3,s2,s4
ori s5,s3,1624
and s1,s2,s5
and s5,s2,s3
srl s4,s4,s1
srai s3,s3,16
xori s4,s5,-974
and s5,s5,s2
srl s2,s4,s2
srai s3,s2,4
add s4,s4,s4
sub s5,s5,s2
beq s5,s5,rand_control_53
addi s2,s2,1
rand_control_53:
andi s2,s1,-1624
slli s5,s4,30
beq s5,s5,rand_control_56
addi s1,s1,1
rand_control_56:
slt s2,s2,s3
srl s3,s4,s1
add s1,s2,s2
srli s5,s2,12
sltu s5,s2,s1
bne s1,s1,rand_control_62
addi s4,s4,1
rand_control_62:
slt s4,s1,s2
slt s2,s3,s4
sltu s4,s2,s4
xor s5,s3,s5
beq s1,s1,rand_control_67
addi s5,s5,1
rand_control_67:
addi s4,s4,-693
add s1,s4,s4
slli s1,s4,25
ori s1,s1,791
slli s5,s3,2
or s4,s3,s1
xor s1,s2,s3
and s1,s2,s3
sub s3,s4,s1
ori s3,s5,-408
sub s3,s1,s3
beq s4,s4,rand_control_79
addi s1,s1,1
rand_control_79:
sltu s2,s3,s3
slt s2,s3,s1
and s2,s4,s5
addi s3,s4,-1481
xori s5,s1,1283
or s1,s3,s4
bne s3,s3,rand_control_86
addi s2,s2,1
rand_control_86:
or s4,s3,s5
sll s5,s2,s3
beq s5,s5,rand_control_89
addi s4,s4,1
rand_control_89:
and s1,s1,s1
andi s1,s2,960
add s5,s1,s5
srli s5,s3,10
add s1,s1,s1
sub s2,s4,s1
xor s3,s4,s3
slli s3,s1,6
or s3,s4,s2
beq s2,s2,rand_control_99
addi s4,s4,1
rand_control_99:
and s4,s4,s1
slt s3,s5,s5
or s4,s2,s3
srl s5,s1,s5
sltu s4,s1,s2
add s5,s2,s3
sub s3,s1,s3
add s2,s4,s4
or s5,s2,s3
and s3,s2,s5
beq s4,s4,rand_control_110
addi s2,s2,1
rand_control_110:
andi s2,s2,-1880
sll s4,s3,s2
xor s4,s3,s4
xor s3,s3,s2
srl s3,s5,s3
sll s5,s5,s3
or s3,s4,s2
addi s5,s2,-285
ori s3,s4,1220
sll s4,s4,s1
bne s3,s3,rand_control_121
addi s3,s3,1
rand_control_121:
ori s1,s3,1366
srai s3,s1,12
sltu s5,s2,s4
andi s4,s4,-715
beq s1,s1,rand_control_126
addi s2,s2,1
rand_control_126:
srli s5,s2,11
sll s1,s2,s2
sll s3,s3,s3
beq s5,s5,rand_control_130
addi s1,s1,1
rand_control_130:
or s1,s1,s1
bne s3,s3,rand_control_132
addi s5,s5,1
rand_control_132:
srai s5,s3,21
ori s3,s4,527
srl s5,s3,s3
xori s2,s3,-935
addi s3,s4,1992
srli s3,s2,21
xor s1,s4,s1
sub s4,s2,s3
and s1,s2,s5
and s2,s5,s5
srl s3,s2,s4
xori s3,s2,-459
slli s2,s4,19
sll s4,s3,s5
and s2,s1,s3
bne s5,s5,rand_control_148
addi s3,s3,1
rand_control_148:
xor s2,s5,s3
sll s4,s3,s4
and s4,s4,s1
addi s2,s2,260
srl s4,s1,s1
addi s2,s4,-564
sub s1,s5,s4
xor s2,s4,s3
or s2,s5,s3
slt s5,s1,s5
sll s3,s4,s2
xor s4,s3,s1
and s1,s5,s2
ori s3,s3,-1257
xor s1,s1,s4
srai s5,s3,2
addi s1,s2,1532
sub s2,s2,s4
xor s3,s2,s1
andi s1,s5,1464
and s1,s4,s1
addi s1,s4,-674
sltu s4,s1,s4
srai s2,s1,10
add s5,s1,s3
or s3,s1,s4
xor s4,s4,s1
beq s3,s3,rand_control_176
addi s5,s5,1
rand_control_176:
sltu s3,s5,s1
slt s5,s5,s4
or s2,s3,s3
xori s1,s3,581
bne s4,s4,rand_control_181
addi s3,s3,1
rand_control_181:
andi s4,s3,-246
addi s4,s3,145
ori s1,s2,-1897
sltu s5,s3,s2
srli s4,s2,10
srli s5,s3,31
slli s4,s2,25
add s2,s2,s4
or s4,s1,s1
sll s1,s1,s1
srai s1,s2,19
ori s5,s2,-1799
and s3,s5,s5
srl s3,s2,s2
ori s4,s2,1759
xori s1,s4,-895
sltu s3,s4,s1
srli s5,s1,29
bne s2,s2,rand_control_200
addi s4,s4,1
rand_control_200:
sll s2,s4,s2
bne s5,s5,rand_control_202
addi s1,s1,1
rand_control_202:
or s1,s3,s4
srli s2,s3,14
add s4,s3,s5
addi s4,s2,1862
add s4,s4,s3
xori s2,s3,-958
xor s3,s4,s5
slt s1,s3,s1
xori s5,s5,-1483
sll s3,s5,s3
add s4,s5,s5
addi s4,s4,152
slt s5,s3,s4
srl s4,s3,s2
ori s4,s5,141
sltu s3,s5,s2
bne s3,s3,rand_control_219
addi s3,s3,1
rand_control_219:
slt s5,s2,s1
andi s1,s2,1667
add s5,s3,s4
or s2,s3,s5
ori s3,s4,-976
slt s2,s4,s5
srl s3,s5,s3
srli s2,s4,29
srli s3,s2,0
slt s4,s3,s5
andi s2,s3,81
andi s1,s1,1028
bne s4,s4,rand_control_232
addi s2,s2,1
rand_control_232:
add s3,s1,s2
ori s2,s5,699
srli s5,s1,30
slli s4,s2,19
srli s4,s4,28
srli s5,s5,23
sltu s4,s2,s4
beq s1,s1,rand_control_240
addi s4,s4,1
rand_control_240:
sltu s4,s3,s5
xori s1,s5,-1876
andi s1,s5,-2005
ori s4,s1,970
or s1,s3,s3
sll s1,s4,s3
srai s3,s2,2
or s5,s2,s3
srl s2,s4,s4
andi s2,s2,-766
bne s1,s1,rand_control_251
addi s1,s1,1
rand_control_251:
srli s4,s3,27
sll s1,s1,s2
add s4,s1,s2
ori s3,s5,-505
sltu s2,s1,s5
beq s4,s4,rand_control_257
addi s1,s1,1
rand_control_257:
andi s1,s5,-776
sltu s5,s1,s2
bne s2,s2,rand_control_260
addi s1,s1,1
rand_control_260:
slli s1,s1,13
xor s4,s5,s2
or s2,s2,s4
add s1,s4,s3
addi s1,s1,1653
or s5,s3,s1
or s4,s4,s4
bne s2,s2,rand_control_268
addi s2,s2,1
rand_control_268:
add s5,s5,s2
xor s5,s5,s1
addi s2,s4,1894
and s3,s4,s4
srl s2,s5,s1
beq s4,s4,rand_control_274
addi s2,s2,1
rand_control_274:
sub s2,s4,s1
sltu s4,s5,s4
xori s1,s4,1700
ori s5,s3,362
slt s5,s3,s3
ori s2,s3,1393
xor s5,s3,s1
andi s4,s1,-1245
xori s2,s2,-1457
srai s5,s4,12
srli s1,s3,18
bne s3,s3,rand_control_286
addi s4,s4,1
rand_control_286:
xor s5,s1,s2
slt s1,s3,s1
addi s4,s5,-959
srai s2,s4,20
sub s4,s5,s1
add s2,s4,s3
addi s4,s2,-1784
bne s2,s2,rand_control_294
addi s5,s5,1
rand_control_294:
beq s2,s2,rand_control_295
addi s5,s5,1
rand_control_295:
beq s3,s3,rand_control_296
addi s3,s3,1
rand_control_296:
add s5,s5,s3
srli s2,s4,21
and s2,s1,s1
beq s5,s5,rand_control_300
addi s1,s1,1
rand_control_300:
bne s3,s3,rand_control_301
addi s2,s2,1
rand_control_301:
or s2,s4,s4
ori s4,s4,574
sub s1,s4,s1
add s5,s3,s2
slt s5,s3,s3
andi s2,s2,-1085
xor s3,s3,s1
and s2,s5,s1
srl s5,s5,s4
slli s1,s4,2
and s2,s4,s5
sll s5,s4,s3
xor s5,s5,s1
addi s2,s4,-665
xori s3,s2,1814
add s1,s5,s3
or s3,s2,s5
sll s3,s2,s5
srl s4,s5,s1
srai s3,s5,23
srl s4,s2,s5
slli s3,s1,24
add s2,s1,s1
addi s4,s4,-1796
addi s4,s4,-710
ori s4,s1,-1279
slt s3,s4,s1
and s2,s4,s2
srai s1,s5,15
sll s2,s3,s5
slli s2,s1,21
andi s5,s2,10
and s4,s1,s3
sll s5,s1,s1
andi s2,s1,1906
or s1,s5,s1
addi s2,s1,-1478
ori s3,s4,-1563
ori s3,s1,-1271
slli s3,s1,26
xori s4,s1,-109
bne s5,s5,rand_control_343
addi s2,s2,1
rand_control_343:
srai s2,s3,29
slt s2,s5,s2
slli s1,s2,20
srai s2,s5,20
slli s2,s4,8
andi s4,s4,2038
beq s2,s2,rand_control_350
addi s5,s5,1
rand_control_350:
xor s5,s3,s5
srai s1,s1,16
add s3,s3,s5
ori s2,s4,489
bne s5,s5,rand_control_355
addi s4,s4,1
rand_control_355:
add s5,s4,s1
beq s3,s3,rand_control_357
addi s2,s2,1
rand_control_357:
srai s2,s2,27
slt s2,s5,s1
srai s2,s2,10
beq s2,s2,rand_control_361
addi s1,s1,1
rand_control_361:
ori s2,s1,434
beq s2,s2,rand_control_363
addi s5,s5,1
rand_control_363:
sltu s5,s3,s5
bne s5,s5,rand_control_365
addi s4,s4,1
rand_control_365:
sll s3,s1,s1
or s2,s5,s4
sll s4,s2,s5
sll s4,s4,s4
srai s2,s5,5
andi s4,s1,-1408
bne s5,s5,rand_control_372
addi s3,s3,1
rand_control_372:
sltu s4,s5,s5
sll s4,s5,s3
srl s1,s3,s4
sub s5,s5,s3
bne s1,s1,rand_control_377
addi s1,s1,1
rand_control_377:
beq s4,s4,rand_control_378
addi s5,s5,1
rand_control_378:
beq s2,s2,rand_control_379
addi s1,s1,1
rand_control_379:
addi s2,s1,-1814
addi s1,s4,-312
srli s1,s4,7
slt s2,s1,s1
slt s3,s3,s1
sll s5,s4,s4
slt s2,s5,s4
add s3,s3,s3
add s3,s4,s4
beq s1,s1,rand_control_389
addi s5,s5,1
rand_control_389:
and s4,s1,s2
and s4,s4,s1
srai s1,s5,1
add s3,s4,s1
slt s1,s4,s4
xori s2,s5,505
addi s3,s1,-727
addi s2,s2,1861
srli s4,s4,25
xor s5,s4,s1
xor s4,s5,s5
xor s3,s5,s3
sub s1,s3,s1
xor s2,s1,s3
slli s2,s2,16
xori s1,s3,-967
xori s5,s5,-1408
srli s5,s4,28
or s4,s2,s1
slt s1,s4,s4
add s1,s2,s5
beq s1,s1,rand_control_411
addi s1,s1,1
rand_control_411:
ori s4,s1,242
beq s1,s1,rand_control_413
addi s4,s4,1
rand_control_413:
beq s2,s2,rand_control_414
addi s1,s1,1
rand_control_414:
or s1,s4,s2
srai s2,s4,24
xor s4,s3,s5
bne s4,s4,rand_control_418
addi s3,s3,1
rand_control_418:
srli s5,s2,9
srl s3,s5,s5
sub s4,s3,s5
sll s4,s5,s1
add s1,s1,s3
and s4,s2,s4
sltu s3,s3,s1
or s3,s2,s1
ori s5,s4,-826
xori s3,s3,-301
sub s4,s1,s4
and s5,s5,s4
add s1,s2,s2
sltu s5,s2,s3
sub s1,s1,s5
srl s1,s5,s2
sll s5,s1,s1
sll s4,s1,s3
srai s4,s1,12
srli s1,s2,28
sll s1,s4,s5
beq s2,s2,rand_control_440
addi s5,s5,1
rand_control_440:
sub s2,s1,s4
srli s4,s4,1
beq s3,s3,rand_control_443
addi s3,s3,1
rand_control_443:
xor s2,s2,s1
and s2,s1,s5
andi s5,s1,-1412
xor s2,s5,s5
bne s1,s1,rand_control_448
addi s4,s4,1
rand_control_448:
slt s1,s5,s2
bne s1,s1,rand_control_450
addi s4,s4,1
rand_control_450:
xor s4,s3,s2
bne s1,s1,rand_control_452
addi s4,s4,1
rand_control_452:
xori s4,s1,-829
srli s2,s3,18
andi s4,s4,-1938
and s2,s2,s3
sltu s2,s5,s1
or s3,s3,s5
ori s4,s5,1420
and s5,s2,s5
sltu s3,s4,s2
sll s1,s1,s5
slt s4,s1,s3
ori s3,s2,1870
sub s1,s1,s2
slt s3,s3,s5
xor s1,s5,s1
or s4,s2,s1
srai s4,s4,18
ori s5,s2,-1954
xori s3,s5,-582
andi s2,s2,-1660
or s2,s5,s3
srli s4,s4,23
bne s3,s3,rand_control_475
addi s4,s4,1
rand_control_475:
andi s4,s2,230
bne s5,s5,rand_control_477
addi s1,s1,1
rand_control_477:
beq s2,s2,rand_control_478
addi s3,s3,1
rand_control_478:
srai s3,s1,27
ori s4,s4,1188
bne s5,s5,rand_control_481
addi s4,s4,1
rand_control_481:
srli s3,s4,19
slt s4,s1,s4
add s5,s4,s3
andi s2,s4,1752
and s2,s5,s2
slli s1,s1,1
beq s1,s1,rand_control_488
addi s2,s2,1
rand_control_488:
sll s1,s4,s1
slt s1,s4,s2
xori s3,s1,-12
sltu s4,s5,s4
xori s3,s3,-1732
sltu s3,s1,s3
add s2,s2,s3
sub s3,s3,s2
sub s2,s5,s3
and s1,s5,s5
addi s1,s2,-1009
xori s1,s3,1580
addi s1,s2,1634
beq s4,s4,rand_control_502
addi s3,s3,1
rand_control_502:
bne s4,s4,rand_control_503
addi s1,s1,1
rand_control_503:
or s4,s3,s4
sub s4,s5,s5
srli s2,s1,13
xori s3,s1,1814
sub s1,s3,s2
addi s2,s5,-93
slt s1,s1,s4
ori s4,s4,-353
sll s5,s3,s1
srli s2,s2,29
sub s3,s3,s5
srl s2,s5,s3
andi s1,s1,-259
or s2,s3,s4
add s1,s5,s4
srai s4,s1,30
srl s1,s3,s4
or s5,s4,s4
sltu s4,s1,s3
slt s5,s5,s1
bne s1,s1,rand_control_524
addi s2,s2,1
rand_control_524:
bne s5,s5,rand_control_525
addi s1,s1,1
rand_control_525:
andi s1,s1,-1876
xor s1,s1,s1
sll s1,s1,s1
sll s3,s1,s3
sub s4,s4,s5
sll s5,s3,s3
beq s2,s2,rand_control_532
addi s2,s2,1
rand_control_532:
xori s2,s3,1099
and s1,s2,s1
bne s4,s4,rand_control_535
addi s3,s3,1
rand_control_535:
andi s4,s1,-1578
srli s1,s5,19
or s4,s4,s2
andi s3,s3,-354
beq s5,s5,rand_control_540
addi s2,s2,1
rand_control_540:
and s3,s4,s5
sub s1,s3,s1
or s4,s1,s2
addi s3,s1,-1399
beq s2,s2,rand_control_545
addi s2,s2,1
rand_control_545:
addi s5,s1,0
andi s4,s1,-2042
slt s5,s5,s4
slli s5,s5,26
xori s4,s1,996
and s5,s4,s4
addi s4,s3,-276
beq s1,s1,rand_control_553
addi s4,s4,1
rand_control_553:
or s4,s4,s4
xor s5,s4,s4
xor s2,s4,s4
addi s5,s1,-1007
and s5,s1,s2
or s5,s5,s2
addi s3,s3,246
add s1,s3,s1
or s4,s4,s5
sub s5,s4,s3
slt s4,s3,s4
xori s5,s3,-490
ori s5,s4,-1550
ori s1,s3,-502
and s1,s4,s4
sll s4,s1,s2
xor s5,s3,s5
sub s4,s3,s5
or s3,s2,s2
andi s1,s4,1393
addi s1,s1,1434
sltu s3,s5,s5
sll s3,s4,s5
sltu s2,s3,s1
addi s3,s1,1865
beq s5,s5,rand_control_579
addi s2,s2,1
rand_control_579:
srl s1,s1,s5
xor s3,s1,s4
srl s2,s1,s1
andi s3,s1,-1491
srl s1,s5,s1
addi s5,s3,1832
add s2,s3,s1
or s1,s4,s5
slli s1,s3,14
addi s3,s2,1572
sltu s5,s4,s2
xor s1,s3,s5
xori s4,s4,140
ori s4,s2,-1876
andi s3,s5,-232
srai s2,s4,16
sltu s2,s5,s3
sll s4,s3,s2
slt s4,s5,s5
sub s5,s3,s5
xor s1,s4,s2
srai s1,s2,12
xor s1,s5,s4
srai s5,s5,5
addi s3,s3,293
add s4,s2,s4
ori s1,s5,-994
bne s1,s1,rand_control_607
addi s3,s3,1
rand_control_607:
addi s4,s2,-1635
slt s5,s2,s3
or s1,s5,s5
add s3,s3,s5
addi s1,s4,1272
beq s2,s2,rand_control_613
addi s4,s4,1
rand_control_613:
and s3,s4,s1
slt s2,s5,s5
srli s4,s1,20
sltu s4,s2,s5
beq s3,s3,rand_control_618
addi s1,s1,1
rand_control_618:
beq s3,s3,rand_control_619
addi s1,s1,1
rand_control_619:
srli s5,s4,17
slli s4,s5,3
beq s1,s1,rand_control_622
addi s2,s2,1
rand_control_622:
addi s5,s1,1719
or s5,s4,s1
slli s3,s3,2
add s4,s4,s5
add s5,s2,s3
andi s1,s4,-1977
andi s2,s4,-765
sltu s5,s1,s2
srl s3,s5,s4
addi s3,s4,1198
bne s5,s5,rand_control_633
addi s5,s5,1
rand_control_633:
sub s3,s3,s1
or s1,s1,s1
add s2,s5,s5
slt s3,s2,s4
and s3,s5,s4
sltu s5,s3,s5
sub s3,s3,s4
sll s1,s4,s5
andi s4,s4,737
or s4,s3,s5
srl s1,s1,s3
andi s2,s1,221
srai s5,s3,16
xori s3,s4,1138
or s1,s4,s4
and s5,s1,s4
sub s4,s3,s1
and s4,s3,s1
andi s3,s2,721
sll s4,s1,s2
bne s3,s3,rand_control_654
addi s5,s5,1
rand_control_654:
slli s1,s4,0
and s1,s1,s1
or s2,s2,s5
xori s1,s5,1391
xor s2,s5,s2
or s5,s4,s4
srai s4,s1,31
sll s2,s3,s1
beq s4,s4,rand_control_663
addi s4,s4,1
rand_control_663:
ori s1,s3,1360
ori s3,s1,-1809
xor s2,s3,s3
srl s3,s3,s3
add s5,s3,s3
xori s1,s5,-1615
slt s5,s2,s1
srli s5,s1,5
sll s2,s2,s3
srli s4,s2,28
srli s5,s5,30
slt s1,s4,s2
bne s4,s4,rand_control_676
addi s2,s2,1
rand_control_676:
slli s2,s2,26
or s5,s4,s1
beq s1,s1,rand_control_679
addi s4,s4,1
rand_control_679:
addi s5,s4,-56
slli s3,s4,1
beq s3,s3,rand_control_682
addi s5,s5,1
rand_control_682:
xori s1,s4,-1787
bne s5,s5,rand_control_684
addi s1,s1,1
rand_control_684:
srl s3,s4,s1
andi s4,s2,-1377
srai s1,s4,14
sll s4,s4,s3
srli s2,s3,10
srli s4,s4,15
addi s4,s1,259
slli s5,s2,7
xori s4,s4,698
srai s5,s2,10
xori s3,s2,1851
srli s5,s1,24
sltu s3,s1,s4
sll s3,s3,s1
sll s5,s2,s5
srai s4,s3,5
beq s2,s2,rand_control_701
addi s2,s2,1
rand_control_701:
sltu s3,s1,s2
and s5,s5,s4
srli s4,s5,12
sub s4,s3,s5
sll s3,s2,s2
ori s2,s5,-1928
beq s5,s5,rand_control_708
addi s4,s4,1
rand_control_708:
add s3,s4,s5
sll s1,s3,s1
slt s3,s2,s4
sll s2,s4,s1
or s4,s2,s5
and s4,s2,s1
slt s5,s3,s4
sll s3,s5,s1
sub s3,s4,s1
addi s4,s4,-1961
slt s3,s4,s5
beq s5,s5,rand_control_720
addi s4,s4,1
rand_control_720:
sltu s5,s4,s5
sll s1,s4,s3
add s1,s5,s1
addi s5,s2,-1737
or s4,s2,s4
sub s2,s1,s2
bne s1,s1,rand_control_727
addi s4,s4,1
rand_control_727:
bne s1,s1,rand_control_728
addi s5,s5,1
rand_control_728:
sltu s2,s4,s4
bne s2,s2,rand_control_730
addi s5,s5,1
rand_control_730:
addi s4,s3,-71
bne s1,s1,rand_control_732
addi s1,s1,1
rand_control_732:
sub s5,s4,s4
and s5,s1,s1
bne s4,s4,rand_control_735
addi s5,s5,1
rand_control_735:
beq s5,s5,rand_control_736
addi s1,s1,1
rand_control_736:
slli s1,s4,4
and s5,s4,s2
and s4,s4,s1
addi s1,s5,110
srai s4,s1,13
sll s4,s3,s2
bne s4,s4,rand_control_743
addi s1,s1,1
rand_control_743:
sltu s1,s3,s2
addi s3,s2,-1583
xori s5,s4,1914
srli s4,s2,9
addi s4,s2,-1315
sub s1,s3,s1
sub s3,s2,s2
or s1,s2,s1
or s4,s5,s2
ori s5,s5,1569
xori s3,s3,-1624
bne s4,s4,rand_control_755
addi s5,s5,1
rand_control_755:
sub s5,s1,s3
srli s2,s2,1
sll s3,s1,s2
beq s3,s3,rand_control_759
addi s4,s4,1
rand_control_759:
srl s2,s5,s2
xor s2,s3,s4
xor s2,s2,s4
bne s2,s2,rand_control_763
addi s1,s1,1
rand_control_763:
or s5,s1,s4
srai s1,s1,21
srai s4,s4,9
addi s4,s4,1048
addi s2,s1,333
sltu s2,s5,s5
and s5,s3,s5
or s4,s2,s5
or s1,s3,s4
add s2,s1,s1
sll s3,s1,s1
bne s4,s4,rand_control_775
addi s5,s5,1
rand_control_775:
addi s5,s2,-869
addi s5,s5,41
sltu s2,s2,s2
sltu s5,s5,s1
ori s2,s3,-365
sub s2,s1,s3
srai s4,s5,0
srai s5,s2,23
bne s1,s1,rand_control_784
addi s1,s1,1
rand_control_784:
xor s4,s2,s2
srl s2,s5,s1
sub s5,s2,s5
or s4,s1,s1
srl s3,s5,s4
sll s3,s1,s4
addi s3,s4,1228
or s4,s1,s5
slli s3,s4,23
sub s4,s2,s5
addi s1,s4,1914
sltu s5,s1,s2
xori s3,s4,675
srli s2,s4,8
srai s3,s1,19
add s5,s2,s4
and s4,s5,s5
beq s4,s4,rand_control_802
addi s1,s1,1
rand_control_802:
srli s1,s4,17
sub s5,s1,s3
addi s4,s2,-701
ori s1,s3,1994
srli s4,s3,21
and s1,s4,s1
sub s2,s5,s3
ori s5,s4,166
srl s4,s5,s4
add s4,s3,s4
or s2,s1,s2
xor s1,s3,s3
addi s1,s5,-182
or s1,s5,s3
xor s1,s2,s5
srli s5,s3,19
and s5,s5,s3
sll s1,s1,s3
ori s4,s1,-1467
sltu s5,s1,s1
sub s5,s1,s1
bne s5,s5,rand_control_824
addi s4,s4,1
rand_control_824:
xor s3,s4,s1
ori s3,s2,-1349
srl s4,s1,s3
bne s1,s1,rand_control_828
addi s1,s1,1
rand_control_828:
xor s1,s1,s1
slt s2,s2,s4
srai s3,s4,29
add s1,s1,s1
xor s1,s1,s4
srli s5,s2,14
bne s2,s2,rand_control_835
addi s3,s3,1
rand_control_835:
xori s1,s5,1343
or s4,s1,s1
xor s2,s4,s3
xori s3,s5,779
andi s3,s2,115
xor s5,s4,s2
srai s3,s3,12
beq s2,s2,rand_control_843
addi s3,s3,1
rand_control_843:
beq s4,s4,rand_control_844
addi s3,s3,1
rand_control_844:
add s2,s1,s2
andi s1,s3,1384
add s1,s3,s5
add s3,s5,s4
addi s2,s3,848
bne s3,s3,rand_control_850
addi s5,s5,1
rand_control_850:
srli s5,s1,22
srl s3,s5,s3
srai s2,s2,20
srai s1,s4,13
slli s5,s1,14
srai s2,s4,24
addi s2,s4,1897
and s4,s5,s3
sll s1,s2,s2
srl s3,s2,s3
andi s2,s5,-743
srli s2,s1,8
add s5,s1,s4
srl s4,s2,s3
add s5,s5,s4
and s4,s1,s3
add s1,s5,s5
slli s5,s2,4
srai s1,s3,13
add s4,s2,s5
sltu s2,s1,s4
ori s4,s4,14
bne s3,s3,rand_control_873
addi s1,s1,1
rand_control_873:
ori s2,s4,274
srai s2,s4,27
and s2,s2,s3
sll s3,s2,s4
and s5,s1,s2
xori s4,s4,-1660
xor s2,s2,s5
sub s2,s4,s5
xor s4,s3,s4
or s4,s2,s2
xor s5,s2,s2
or s4,s5,s2
slt s2,s5,s3
srai s4,s1,24
bne s2,s2,rand_control_888
addi s4,s4,1
rand_control_888:
addi s1,s1,915
andi s5,s5,-394
xor s5,s3,s5
sll s4,s3,s1
srl s4,s4,s5
addi s2,s1,1499
bne s2,s2,rand_control_895
addi s3,s3,1
rand_control_895:
or s3,s4,s4
srai s5,s3,3
sltu s1,s2,s4
or s2,s5,s2
add s1,s4,s3
bne s2,s2,rand_control_901
addi s2,s2,1
rand_control_901:
add s3,s5,s1
xor s2,s5,s2
slt s4,s3,s2
srl s4,s2,s2
srai s3,s4,23
slt s4,s1,s4
sub s2,s1,s4
xor s5,s3,s5
xor s5,s1,s5
addi s1,s4,1631
ori s3,s4,-838
srl s3,s2,s3
addi s4,s3,-699
beq s3,s3,rand_control_915
addi s3,s3,1
rand_control_915:
sub s5,s2,s4
bne s2,s2,rand_control_917
addi s1,s1,1
rand_control_917:
sub s5,s3,s3
srai s3,s1,29
xori s1,s4,-1433
srai s5,s4,23
add s1,s3,s5
or s2,s5,s2
bne s2,s2,rand_control_924
addi s2,s2,1
rand_control_924:
beq s3,s3,rand_control_925
addi s5,s5,1
rand_control_925:
sltu s1,s4,s1
slt s3,s2,s4
add s5,s3,s1
sltu s1,s2,s3
srai s4,s1,6
srli s3,s2,30
ori s1,s3,251
xori s3,s5,487
srli s5,s4,13
xor s1,s3,s1
xor s4,s2,s5
sll s5,s3,s1
xori s5,s2,1542
or s5,s5,s2
bne s4,s4,rand_control_940
addi s5,s5,1
rand_control_940:
or s5,s5,s2
srai s2,s3,7
slt s1,s2,s3
add s2,s2,s5
sltu s4,s3,s3
slli s5,s4,9
bne s5,s5,rand_control_947
addi s1,s1,1
rand_control_947:
srai s5,s4,31
and s4,s4,s4
sltu s2,s1,s1
andi s4,s1,430
sll s3,s3,s5
srai s4,s1,3
andi s2,s2,-645
sltu s5,s4,s2
sll s1,s2,s5
bne s1,s1,rand_control_957
addi s1,s1,1
rand_control_957:
ori s4,s4,1586
sub s1,s2,s3
xor s4,s2,s3
beq s4,s4,rand_control_961
addi s4,s4,1
rand_control_961:
srli s3,s5,4
srl s4,s3,s2
xori s2,s3,-1575
slli s5,s2,12
srai s1,s2,19
sltu s2,s4,s3
beq s1,s1,rand_control_968
addi s2,s2,1
rand_control_968:
addi s4,s4,1069
sltu s5,s1,s1
srli s5,s1,11
xor s3,s5,s4
add s1,s5,s4
and s4,s3,s5
add s1,s1,s4
and s5,s4,s2
slt s5,s3,s4
andi s4,s1,325
sll s5,s4,s3
add s4,s4,s2
and s3,s2,s1
xori s4,s1,-398
srli s3,s4,0
beq s4,s4,rand_control_984
addi s1,s1,1
rand_control_984:
bne s4,s4,rand_control_985
addi s3,s3,1
rand_control_985:
srai s1,s5,10
ori s1,s3,-212
beq s3,s3,rand_control_988
addi s4,s4,1
rand_control_988:
srli s4,s1,11
xori s4,s5,1022
bne s3,s3,rand_control_991
addi s2,s2,1
rand_control_991:
or s1,s4,s4
bne s2,s2,rand_control_993
addi s3,s3,1
rand_control_993:
sll s3,s3,s3
srai s2,s3,9
xori s2,s5,-1109
xor s4,s1,s3
srl s4,s1,s3
xori s1,s1,1000
bne s3,s3,rand_control_1000
addi s2,s2,1
rand_control_1000:
slli s3,s5,1
srli s5,s2,14
srai s5,s4,28
add s5,s5,s2
xor s1,s5,s3
sll s1,s4,s3
srli s5,s4,17
sub s4,s5,s1
beq s4,s4,rand_control_1009
addi s4,s4,1
rand_control_1009:
sll s1,s2,s1
bne s4,s4,rand_control_1011
addi s3,s3,1
rand_control_1011:
or s5,s1,s1
xor s3,s3,s1
addi s3,s5,-628
addi s2,s2,-1165
sub s2,s4,s1
ori s2,s4,-1250
slt s3,s4,s2
xori s4,s4,-46
xor s1,s2,s5
xori s5,s4,182
slt s1,s4,s4
bne s5,s5,rand_control_1023
addi s1,s1,1
rand_control_1023:
and s4,s4,s1
andi s2,s4,-874
sltu s3,s2,s3
and s3,s3,s1
srai s1,s5,31
slli s1,s5,25
sll s1,s1,s3
srai s3,s4,8
bne s5,s5,rand_control_1032
addi s3,s3,1
rand_control_1032:
andi s3,s1,1292
and s2,s5,s4
ori s4,s3,1386
and s5,s4,s2
and s5,s1,s1
beq s1,s1,rand_control_1038
addi s2,s2,1
rand_control_1038:
and s2,s4,s1
xori s3,s1,985
addi s1,s4,1441
srai s2,s4,10
addi s3,s3,-1273
beq s5,s5,rand_control_1044
addi s2,s2,1
rand_control_1044:
xori s1,s4,874
slt s1,s5,s4
srai s1,s3,18
sltu s5,s5,s3
or s2,s2,s4
xor s4,s4,s5
xor s2,s1,s2
srli s3,s3,31
sub s2,s4,s1
ori s5,s1,1541
beq s5,s5,rand_control_1055
addi s4,s4,1
rand_control_1055:
ori s1,s4,-1663
add s4,s4,s4
srli s2,s5,15
and s4,s5,s4
add s2,s2,s5
beq s1,s1,rand_control_1061
addi s5,s5,1
rand_control_1061:
and s3,s2,s1
andi s3,s1,1812
andi s2,s3,541
srl s1,s4,s3
and s5,s4,s5
bne s1,s1,rand_control_1067
addi s2,s2,1
rand_control_1067:
andi s1,s1,-1365
sltu s4,s5,s1
slli s1,s3,11
xor s3,s5,s4
or s4,s5,s4
xor s2,s4,s3
beq s3,s3,rand_control_1074
addi s1,s1,1
rand_control_1074:
and s5,s2,s3
slli s4,s4,28
sub s3,s3,s4
bne s2,s2,rand_control_1078
addi s3,s3,1
rand_control_1078:
and s2,s4,s3
xori s4,s3,1197
bne s4,s4,rand_control_1081
addi s1,s1,1
rand_control_1081:
sll s1,s4,s1
sll s4,s5,s5
and s3,s5,s2
slt s5,s5,s4
sll s3,s3,s4
slt s1,s3,s3
add s1,s4,s2
bne s3,s3,rand_control_1089
addi s4,s4,1
rand_control_1089:
sub s5,s5,s1
slt s5,s2,s2
addi s2,s2,-1689
sltu s5,s2,s1
slli s2,s1,31
add s5,s3,s2
bne s2,s2,rand_control_1096
addi s5,s5,1
rand_control_1096:
ori s5,s3,377
srli s5,s2,29
or s1,s4,s4
ori s3,s4,-1146
addi s1,s4,344
or s2,s4,s1
add s2,s4,s5
srai s2,s2,9
and s2,s4,s5
xori s3,s3,-850
and s5,s5,s3
or s3,s1,s3
beq s3,s3,rand_control_1109
addi s4,s4,1
rand_control_1109:
sll s5,s2,s1
add s2,s1,s3
xori s1,s3,1617
xori s1,s2,149
andi s5,s3,1563
srli s2,s4,27
srli s3,s5,31
and s3,s3,s2
bne s3,s3,rand_control_1118
addi s5,s5,1
rand_control_1118:
ori s1,s4,1278
sll s5,s3,s4
beq s4,s4,rand_control_1121
addi s2,s2,1
rand_control_1121:
srai s1,s5,8
srli s4,s2,19
add s3,s5,s5
ori s3,s5,-658
slli s4,s3,4
or s2,s2,s2
sub s1,s4,s1
sltu s2,s1,s2
sltu s4,s3,s1
ori s3,s3,-996
srl s1,s5,s4
slt s5,s1,s2
slli s1,s1,8
srli s5,s4,26
sub s2,s3,s4
or s1,s2,s1
and s4,s2,s2
beq s5,s5,rand_control_1139
addi s4,s4,1
rand_control_1139:
bne s3,s3,rand_control_1140
addi s5,s5,1
rand_control_1140:
beq s5,s5,rand_control_1141
addi s2,s2,1
rand_control_1141:
xor s3,s5,s5
slli s2,s1,30
slt s5,s5,s5
addi s4,s4,1760
srli s4,s1,12
or s2,s5,s2
srai s5,s1,27
slt s4,s5,s5
ori s4,s3,182
sub s4,s2,s1
add s2,s3,s4
bne s4,s4,rand_control_1153
addi s4,s4,1
rand_control_1153:
sub s4,s1,s5
ori s1,s5,-1107
or s2,s1,s3
xori s5,s4,-1683
beq s3,s3,rand_control_1158
addi s3,s3,1
rand_control_1158:
sll s4,s1,s5
andi s5,s5,393
srl s3,s5,s2
xori s3,s2,727
srli s4,s4,28
ori s1,s3,111
add s1,s5,s5
sub s5,s3,s1
andi s5,s3,1896
srl s4,s2,s5
xor s1,s4,s1
and s3,s3,s5
srl s3,s5,s1
ori s3,s3,-13
sub s2,s3,s5
add s4,s1,s3
xori s4,s4,-428
slt s1,s2,s5
beq s4,s4,rand_control_1177
addi s1,s1,1
rand_control_1177:
slli s4,s3,4
bne s2,s2,rand_control_1179
addi s4,s4,1
rand_control_1179:
beq s5,s5,rand_control_1180
addi s4,s4,1
rand_control_1180:
srl s1,s3,s3
sub s5,s2,s5
xori s4,s4,972
or s5,s2,s2
bne s4,s4,rand_control_1185
addi s1,s1,1
rand_control_1185:
slli s5,s2,15
addi s5,s1,-432
andi s2,s4,1954
srli s5,s5,21
srl s1,s5,s5
slt s2,s4,s3
slli s1,s3,18
srli s3,s1,28
beq s5,s5,rand_control_1194
addi s3,s3,1
rand_control_1194:
bne s5,s5,rand_control_1195
addi s1,s1,1
rand_control_1195:
addi s4,s4,-19
srli s3,s5,14
sll s4,s5,s2
srli s2,s3,10

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

