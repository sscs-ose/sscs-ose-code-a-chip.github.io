.option norvc
.section .text.init
.globl _start
_start:
la s0,scratch
li t0,0x90000000
li s1,1648816797
li s2,3425375734
li s3,706947926
li s4,462957512
li s5,328953231
xori s5,s1,-443
and s2,s4,s5
and s2,s3,s2
srai s4,s5,2
or s4,s4,s3
sltu s3,s3,s3
srli s1,s3,7
or s2,s1,s2
beq s1,s1,rand_control_8
addi s3,s3,1
rand_control_8:
xor s3,s3,s3
add s1,s3,s4
sub s1,s2,s4
sltu s4,s3,s2
slt s5,s3,s1
sltu s5,s4,s2
beq s4,s4,rand_control_15
addi s1,s1,1
rand_control_15:
beq s5,s5,rand_control_16
addi s4,s4,1
rand_control_16:
srai s2,s1,26
xor s5,s5,s4
ori s2,s3,-1386
sub s1,s1,s4
addi s1,s5,-913
bne s4,s4,rand_control_22
addi s3,s3,1
rand_control_22:
addi s2,s3,-1165
beq s5,s5,rand_control_24
addi s5,s5,1
rand_control_24:
andi s4,s1,1598
xori s1,s1,737
srai s4,s5,9
srl s3,s2,s3
srli s3,s3,16
xori s2,s2,645
sub s4,s2,s4
sll s3,s3,s5
xor s2,s4,s2
xor s4,s4,s1
slt s4,s2,s3
sub s1,s4,s4
srli s1,s3,12
beq s1,s1,rand_control_38
addi s5,s5,1
rand_control_38:
bne s4,s4,rand_control_39
addi s2,s2,1
rand_control_39:
slli s3,s4,14
slli s4,s1,28
and s5,s4,s3
xor s1,s4,s3
sltu s2,s1,s5
sub s2,s4,s1
slli s5,s3,7
srai s2,s2,13
bne s4,s4,rand_control_48
addi s1,s1,1
rand_control_48:
add s2,s4,s3
slt s2,s3,s4
and s1,s4,s2
sub s5,s5,s5
addi s3,s1,1735
srl s4,s5,s5
slt s2,s2,s2
beq s1,s1,rand_control_56
addi s5,s5,1
rand_control_56:
bne s3,s3,rand_control_57
addi s4,s4,1
rand_control_57:
add s4,s1,s2
ori s5,s3,-1142
ori s4,s1,-1429
beq s4,s4,rand_control_61
addi s3,s3,1
rand_control_61:
sltu s3,s3,s5
srl s2,s3,s3
slli s3,s1,7
andi s3,s5,1336
ori s3,s3,-1378
andi s5,s3,1997
sll s4,s1,s5
xori s5,s2,-1739
beq s4,s4,rand_control_70
addi s4,s4,1
rand_control_70:
srli s3,s4,19
add s5,s5,s2
beq s2,s2,rand_control_73
addi s3,s3,1
rand_control_73:
addi s2,s3,-1692
xor s2,s5,s4
addi s3,s3,1913
xori s1,s5,1070
bne s3,s3,rand_control_78
addi s5,s5,1
rand_control_78:
slt s4,s3,s5
beq s2,s2,rand_control_80
addi s3,s3,1
rand_control_80:
sltu s5,s4,s1
xor s3,s1,s3
and s2,s5,s2
sll s4,s5,s2
xor s4,s2,s2
sub s3,s4,s3
and s5,s3,s1
andi s1,s2,1499
or s2,s5,s4
andi s3,s1,-594
srli s4,s5,25
or s3,s4,s5
sll s2,s2,s1
sub s5,s5,s5
sll s3,s4,s2
srli s3,s5,31
xor s1,s4,s1
slt s4,s2,s1
beq s3,s3,rand_control_99
addi s1,s1,1
rand_control_99:
andi s4,s4,1453
srl s5,s2,s1
or s5,s2,s2
bne s3,s3,rand_control_103
addi s2,s2,1
rand_control_103:
beq s1,s1,rand_control_104
addi s4,s4,1
rand_control_104:
add s2,s4,s4
bne s1,s1,rand_control_106
addi s4,s4,1
rand_control_106:
xor s1,s4,s5
add s2,s5,s1
add s4,s2,s1
sll s4,s2,s5
srli s4,s3,15
beq s2,s2,rand_control_112
addi s2,s2,1
rand_control_112:
ori s3,s2,-241
xor s4,s2,s2
sltu s1,s3,s1
srai s1,s4,6
or s1,s5,s3
slt s3,s2,s3
and s1,s5,s4
xori s4,s5,1904
srai s5,s4,15
slli s3,s4,17
add s5,s5,s1
addi s2,s5,1026
sub s2,s1,s4
sub s3,s2,s4
add s3,s3,s3
sltu s1,s4,s1
or s5,s5,s4
sub s4,s2,s2
sub s1,s5,s2
slli s2,s5,13
sub s2,s4,s4
slli s5,s3,14
xor s3,s2,s2
and s2,s2,s5
ori s5,s2,1374
sltu s5,s4,s4
xori s3,s3,640
sltu s2,s3,s2
xori s5,s4,-77
srai s2,s5,16
or s2,s1,s1
add s2,s5,s3
beq s2,s2,rand_control_145
addi s1,s1,1
rand_control_145:
xor s4,s5,s1
ori s3,s5,-1415
srai s1,s5,14
xor s5,s3,s3
addi s4,s1,935
sub s4,s2,s2
slt s1,s4,s5
srl s4,s2,s4
andi s5,s5,1178
beq s5,s5,rand_control_155
addi s4,s4,1
rand_control_155:
ori s4,s3,-575
sltu s2,s1,s2
ori s3,s4,-1851
srai s3,s2,18
sltu s1,s1,s2
and s5,s1,s3
add s5,s5,s5
addi s3,s1,-2019
and s1,s1,s2
srli s1,s4,14
xori s1,s3,2023
xori s2,s2,-280
slt s3,s5,s1
slt s3,s4,s4
or s5,s2,s3
add s5,s3,s5
slt s1,s1,s2
srli s2,s2,3
bne s5,s5,rand_control_174
addi s2,s2,1
rand_control_174:
and s1,s4,s1
add s4,s4,s3
beq s3,s3,rand_control_177
addi s2,s2,1
rand_control_177:
srli s5,s3,17
addi s4,s1,386
srai s4,s5,3
slli s4,s1,6
addi s5,s4,-1077
slt s2,s2,s5
or s4,s4,s5
andi s3,s1,1510
xori s5,s1,971
bne s5,s5,rand_control_187
addi s1,s1,1
rand_control_187:
andi s3,s1,1453
add s5,s3,s2
addi s5,s3,-143
add s5,s4,s1
sll s4,s4,s2
bne s5,s5,rand_control_193
addi s2,s2,1
rand_control_193:
srli s5,s1,7
xori s4,s1,-1517
bne s3,s3,rand_control_196
addi s1,s1,1
rand_control_196:
slt s5,s2,s3
beq s1,s1,rand_control_198
addi s2,s2,1
rand_control_198:
sll s2,s5,s2
or s2,s3,s3
sll s1,s5,s3
sll s2,s5,s3
beq s4,s4,rand_control_203
addi s5,s5,1
rand_control_203:
andi s4,s2,-685
ori s4,s1,-407
beq s4,s4,rand_control_206
addi s1,s1,1
rand_control_206:
srl s1,s1,s3
slt s2,s5,s3
and s2,s3,s2
sub s4,s3,s5
xori s5,s5,413
srli s5,s1,17
andi s1,s2,-5
srl s4,s2,s2
srl s1,s2,s5
ori s1,s3,-2021
slli s1,s4,5
sub s2,s2,s5
sub s2,s3,s4
and s2,s2,s1
sll s4,s4,s4
sll s2,s4,s1
xor s5,s5,s1
srai s5,s1,17
addi s4,s2,632
slt s3,s2,s4
srli s5,s5,23
and s1,s2,s1
or s3,s1,s5
andi s2,s2,1394
and s2,s5,s2
xor s3,s4,s1
sll s4,s3,s5
beq s4,s4,rand_control_234
addi s2,s2,1
rand_control_234:
add s1,s1,s4
xor s1,s2,s2
ori s4,s3,-1525
srli s3,s3,7
add s4,s5,s4
andi s2,s2,1260
addi s1,s5,778
add s2,s1,s1
srli s4,s4,24
slli s1,s2,23
sll s2,s4,s3
beq s4,s4,rand_control_246
addi s1,s1,1
rand_control_246:
addi s5,s4,854
slli s1,s2,1
sub s5,s3,s5
sll s3,s3,s2
beq s1,s1,rand_control_251
addi s5,s5,1
rand_control_251:
srai s4,s5,11
slli s2,s5,24
addi s5,s5,1524
sub s5,s4,s4
or s4,s2,s1
ori s5,s1,762
sll s4,s3,s4
beq s5,s5,rand_control_259
addi s5,s5,1
rand_control_259:
srl s5,s4,s1
srai s3,s3,13
ori s1,s1,600
beq s5,s5,rand_control_263
addi s2,s2,1
rand_control_263:
srai s3,s4,12
ori s1,s3,-506
or s4,s4,s3
slt s4,s4,s4
sub s5,s3,s5
and s1,s5,s2
slli s1,s1,13
bne s2,s2,rand_control_271
addi s5,s5,1
rand_control_271:
add s4,s2,s1
add s5,s5,s1
slli s4,s2,15
srai s3,s2,6
beq s4,s4,rand_control_276
addi s5,s5,1
rand_control_276:
srli s3,s3,14
slt s1,s5,s2
or s3,s4,s5
sltu s4,s1,s2
xori s1,s5,-2008
srli s1,s5,18
sub s1,s3,s4
ori s4,s2,1909
bne s3,s3,rand_control_285
addi s4,s4,1
rand_control_285:
beq s2,s2,rand_control_286
addi s4,s4,1
rand_control_286:
bne s5,s5,rand_control_287
addi s2,s2,1
rand_control_287:
bne s2,s2,rand_control_288
addi s1,s1,1
rand_control_288:
or s2,s1,s5
xori s1,s1,-1956
xori s4,s2,-1458
srli s2,s2,20
add s1,s4,s2
ori s3,s3,1681
srl s2,s5,s3
sub s5,s2,s1
sub s5,s1,s4
xori s1,s3,1877
slt s5,s4,s5
beq s3,s3,rand_control_300
addi s2,s2,1
rand_control_300:
sltu s4,s3,s1
sll s3,s2,s3
slli s2,s4,27
beq s3,s3,rand_control_304
addi s1,s1,1
rand_control_304:
beq s4,s4,rand_control_305
addi s1,s1,1
rand_control_305:
xori s1,s1,1193
srai s2,s4,26
beq s2,s2,rand_control_308
addi s4,s4,1
rand_control_308:
slt s2,s5,s1
beq s4,s4,rand_control_310
addi s3,s3,1
rand_control_310:
slt s2,s2,s5
beq s1,s1,rand_control_312
addi s4,s4,1
rand_control_312:
srl s3,s3,s5
add s3,s4,s5
bne s2,s2,rand_control_315
addi s4,s4,1
rand_control_315:
srai s5,s4,27
slli s5,s3,12
bne s4,s4,rand_control_318
addi s4,s4,1
rand_control_318:
bne s1,s1,rand_control_319
addi s4,s4,1
rand_control_319:
bne s5,s5,rand_control_320
addi s5,s5,1
rand_control_320:
slli s3,s4,25
and s2,s3,s2
sll s5,s1,s1
ori s2,s2,1465
ori s4,s2,1232
and s3,s4,s4
sll s3,s1,s3
ori s2,s2,1164
srl s2,s3,s3
add s1,s3,s3
add s3,s1,s5
or s5,s5,s5
srli s2,s3,16
and s3,s4,s5
or s4,s3,s1
xori s4,s3,-1742
and s5,s3,s5
add s3,s1,s3
or s1,s2,s5
sll s1,s3,s3
srl s4,s3,s4
slli s2,s3,15
sltu s5,s4,s3
addi s2,s1,1998
or s1,s1,s3
beq s1,s1,rand_control_346
addi s4,s4,1
rand_control_346:
and s1,s4,s1
xori s2,s2,1114
sltu s4,s2,s3
ori s3,s4,1078
ori s5,s1,-1928
or s4,s2,s1
andi s3,s1,373
sltu s5,s5,s1
srli s4,s5,23
sll s1,s4,s1
xori s1,s5,1864
xor s3,s5,s4
or s5,s1,s3
or s5,s4,s1
sub s5,s3,s5
xor s5,s1,s1
srai s3,s3,20
bne s3,s3,rand_control_364
addi s3,s3,1
rand_control_364:
addi s1,s2,-1552
beq s2,s2,rand_control_366
addi s3,s3,1
rand_control_366:
bne s2,s2,rand_control_367
addi s2,s2,1
rand_control_367:
add s5,s4,s4
or s5,s4,s1
srli s2,s4,23
sltu s3,s1,s2
sltu s1,s4,s5
slli s2,s2,11
or s1,s4,s3
xori s2,s1,1556
srl s4,s4,s4
sltu s3,s4,s4
addi s3,s4,775
add s4,s4,s3
srli s3,s4,17
xori s2,s2,-538
addi s1,s4,-706
slt s5,s3,s4
srl s3,s2,s2
srl s5,s1,s4
xor s1,s4,s5
srl s2,s2,s3
srl s4,s5,s3
sub s1,s4,s3
slt s4,s5,s3
add s5,s2,s2
add s1,s5,s5
andi s2,s1,-522
or s5,s3,s2
slli s2,s1,11
sub s2,s1,s4
xor s5,s1,s1
sub s3,s5,s3
andi s4,s4,-698
addi s5,s1,1283
ori s2,s3,20
and s5,s3,s4
beq s2,s2,rand_control_403
addi s3,s3,1
rand_control_403:
srl s1,s1,s1
andi s1,s1,-510
srli s2,s3,11
sub s2,s4,s4
slli s4,s3,20
andi s2,s2,1252
beq s3,s3,rand_control_410
addi s3,s3,1
rand_control_410:
add s3,s5,s2
slli s2,s5,26
srli s2,s3,4
and s1,s2,s1
bne s1,s1,rand_control_415
addi s2,s2,1
rand_control_415:
bne s2,s2,rand_control_416
addi s4,s4,1
rand_control_416:
sltu s2,s4,s3
srl s2,s2,s3
and s3,s2,s4
sub s2,s1,s4
beq s5,s5,rand_control_421
addi s1,s1,1
rand_control_421:
add s3,s5,s1
or s1,s2,s4
srl s2,s5,s2
and s2,s5,s1
or s4,s5,s1
or s2,s4,s3
or s3,s5,s5
andi s2,s4,-215
srli s2,s3,19
and s4,s1,s4
andi s1,s1,779
slli s1,s5,4
xor s2,s1,s3
slli s5,s2,12
srli s4,s5,25
add s5,s5,s2
srai s5,s4,22
srli s1,s2,12
ori s1,s5,1487
sll s1,s3,s3
add s4,s1,s1
andi s5,s4,-131
xor s3,s5,s4
and s3,s1,s4
xori s2,s5,81
beq s2,s2,rand_control_447
addi s1,s1,1
rand_control_447:
beq s2,s2,rand_control_448
addi s3,s3,1
rand_control_448:
sltu s2,s1,s2
sltu s4,s4,s5
srli s5,s2,2
srli s4,s2,7
srli s1,s5,0
sll s4,s2,s2
beq s4,s4,rand_control_455
addi s2,s2,1
rand_control_455:
and s1,s5,s3
srai s2,s2,1
sll s4,s3,s4
add s4,s4,s2
sll s5,s5,s3
slli s3,s3,4
xori s1,s4,1434
sltu s4,s2,s1
srl s5,s5,s1
srai s5,s1,13
sltu s1,s3,s1
srli s1,s2,5
add s3,s3,s4
beq s2,s2,rand_control_469
addi s4,s4,1
rand_control_469:
sub s3,s2,s1
srai s4,s2,16
srl s4,s1,s4
and s1,s4,s2
andi s2,s2,-760
sub s5,s2,s2
and s2,s3,s1
srl s5,s4,s4
add s1,s3,s5
andi s4,s4,306
add s1,s2,s5
slli s4,s5,16
bne s3,s3,rand_control_482
addi s4,s4,1
rand_control_482:
xori s3,s3,208
sll s4,s4,s3
slli s5,s3,0
sub s4,s1,s2
slli s1,s3,17
ori s5,s4,-267
xor s4,s5,s1
addi s5,s4,-1537
srli s3,s1,0
sltu s3,s1,s3
sltu s2,s4,s1
slli s1,s4,31
srai s3,s5,5
slt s4,s2,s4
srl s4,s3,s2
sub s5,s3,s2
slli s2,s5,1
xori s3,s4,919
beq s3,s3,rand_control_501
addi s2,s2,1
rand_control_501:
slt s1,s2,s4
sltu s3,s2,s5
xor s2,s4,s1
beq s4,s4,rand_control_505
addi s4,s4,1
rand_control_505:
srli s4,s3,6
sll s5,s2,s4
srl s4,s4,s1
addi s1,s5,-806
slli s2,s2,1
andi s3,s5,-994
andi s5,s1,1264
slli s1,s3,9
sub s2,s4,s5
addi s5,s2,807
xori s3,s2,-551
sll s3,s4,s1
sltu s3,s2,s5
slli s5,s1,14
sub s3,s2,s5
xori s3,s1,-145
ori s3,s2,-55
xor s1,s5,s3
slli s2,s4,29
srli s4,s4,8
add s3,s3,s3
beq s1,s1,rand_control_527
addi s1,s1,1
rand_control_527:
beq s4,s4,rand_control_528
addi s5,s5,1
rand_control_528:
srl s2,s4,s2
and s1,s1,s3
beq s2,s2,rand_control_531
addi s5,s5,1
rand_control_531:
slli s1,s1,5
xori s1,s3,555
slt s3,s4,s1
or s5,s4,s3
srl s1,s4,s3
xori s4,s4,-1870
add s4,s4,s5
xor s2,s1,s4
srai s3,s3,29
sub s3,s5,s2
sll s4,s4,s2
srl s5,s2,s4
srai s2,s3,10
slli s5,s1,18
ori s5,s1,792
sll s4,s1,s4
or s5,s1,s1
slli s2,s2,8
andi s2,s1,-694
slli s4,s1,25
bne s4,s4,rand_control_552
addi s1,s1,1
rand_control_552:
srli s5,s5,2
andi s1,s3,-1692
slli s3,s4,6
slli s3,s5,26
srli s4,s4,26
slli s5,s5,17
srai s4,s1,8
srai s3,s1,2
srl s4,s4,s1
srai s5,s3,0
bne s4,s4,rand_control_563
addi s4,s4,1
rand_control_563:
srai s1,s3,17
or s2,s3,s1
or s3,s2,s5
sltu s4,s2,s3
sub s5,s1,s4
add s1,s3,s4
sltu s5,s3,s2
and s5,s2,s4
srl s3,s3,s4
srli s4,s1,11
slli s4,s1,9
slt s4,s2,s3
sll s3,s5,s1
beq s3,s3,rand_control_577
addi s1,s1,1
rand_control_577:
addi s3,s4,-1843
addi s5,s4,1069
ori s1,s3,1426
sll s3,s2,s1
add s4,s1,s5
sltu s3,s2,s4
ori s5,s3,1310
and s3,s4,s2
srai s3,s1,14
sub s5,s4,s5
xori s5,s1,-694
bne s5,s5,rand_control_589
addi s2,s2,1
rand_control_589:
srai s3,s1,31
add s3,s2,s1
sub s2,s5,s3
srl s1,s2,s2
srli s4,s4,1
add s3,s2,s3
add s5,s2,s1
srli s2,s4,18
and s3,s3,s4
slli s3,s4,7
xor s1,s2,s5
xori s5,s5,-386
ori s5,s2,-1610
xori s3,s1,-240
add s3,s4,s3
beq s2,s2,rand_control_605
addi s1,s1,1
rand_control_605:
or s1,s5,s2
addi s4,s3,1061
sltu s1,s5,s4
xori s2,s1,1540
sub s5,s3,s1
ori s5,s5,1968
ori s3,s4,1472
srl s1,s2,s1
slli s4,s5,15
add s5,s2,s1
sltu s3,s5,s1
sll s4,s1,s1
ori s1,s1,-634
and s2,s5,s2
add s3,s2,s4
srl s3,s5,s2
xori s1,s2,-244
slli s2,s3,13
slli s3,s1,20
xori s1,s3,1534
slt s1,s3,s1
srai s4,s4,4
srli s1,s4,13
add s5,s3,s3
addi s3,s2,990
xor s2,s4,s4
sltu s4,s2,s3
bne s1,s1,rand_control_633
addi s4,s4,1
rand_control_633:
srai s2,s2,24
slt s1,s2,s2
addi s4,s2,-737
add s5,s1,s1
srai s3,s3,28
srli s3,s4,23
slt s2,s2,s4
sll s5,s5,s1
add s3,s1,s5
sub s1,s4,s5
slt s5,s3,s3
sll s1,s5,s1
and s5,s3,s1
xori s5,s1,1393
xori s4,s1,-1823
beq s3,s3,rand_control_649
addi s1,s1,1
rand_control_649:
srl s1,s1,s1
slli s2,s5,5
and s1,s5,s5
beq s5,s5,rand_control_653
addi s2,s2,1
rand_control_653:
slt s3,s3,s2
sltu s4,s2,s4
srli s2,s5,6
srli s2,s1,14
or s1,s3,s2
sltu s2,s5,s5
add s3,s1,s2
sll s5,s5,s5
beq s2,s2,rand_control_662
addi s3,s3,1
rand_control_662:
andi s2,s1,-1510
srai s3,s1,31
xor s3,s3,s5
slt s2,s1,s4
srl s5,s3,s5
srai s4,s3,7
srli s1,s5,19
xor s2,s2,s1
and s5,s3,s3
beq s4,s4,rand_control_672
addi s3,s3,1
rand_control_672:
slt s4,s3,s5
xori s2,s4,1640
addi s2,s3,-1969
srli s3,s5,12
beq s1,s1,rand_control_677
addi s2,s2,1
rand_control_677:
slli s3,s5,12
srli s4,s2,18
add s4,s1,s2
sll s4,s1,s2
xor s4,s5,s2
srai s3,s1,31
or s3,s2,s3
srli s1,s2,21
xor s2,s2,s2
andi s3,s4,-1706
sub s3,s5,s4
ori s4,s2,2034
srli s2,s2,6
xor s5,s3,s4
beq s5,s5,rand_control_692
addi s5,s5,1
rand_control_692:
sll s3,s5,s4
srl s1,s3,s2
sll s2,s4,s2
srai s4,s4,11
srli s2,s4,23
add s4,s4,s2
xor s1,s1,s2
add s1,s2,s2
slli s3,s5,3
xor s2,s5,s1
bne s1,s1,rand_control_703
addi s5,s5,1
rand_control_703:
bne s4,s4,rand_control_704
addi s5,s5,1
rand_control_704:
bne s1,s1,rand_control_705
addi s4,s4,1
rand_control_705:
xori s2,s3,-1018
srli s2,s2,11
xor s4,s2,s5
beq s1,s1,rand_control_709
addi s2,s2,1
rand_control_709:
ori s4,s1,-1089
srl s4,s3,s4
srai s3,s3,2
srai s4,s1,23
srl s1,s4,s2
slt s2,s5,s1
addi s5,s1,1565
xor s1,s5,s1
sub s3,s4,s2
or s4,s3,s5
srai s5,s5,7
sub s5,s4,s3
ori s2,s3,-1308
addi s3,s4,-1945
ori s4,s3,-267
sll s2,s3,s1
xori s5,s3,-602
sub s1,s1,s4
slli s4,s2,3
slli s5,s1,13
and s3,s1,s1
bne s4,s4,rand_control_731
addi s5,s5,1
rand_control_731:
and s5,s5,s1
ori s2,s3,-2001
xor s5,s1,s4
srl s4,s1,s2
srli s5,s3,30
xor s2,s4,s2
slli s1,s1,11
sll s5,s3,s3
beq s5,s5,rand_control_740
addi s2,s2,1
rand_control_740:
xori s5,s4,-1769
slt s1,s4,s5
srai s1,s4,26
addi s3,s4,1551
sltu s2,s4,s5
beq s4,s4,rand_control_746
addi s3,s3,1
rand_control_746:
addi s4,s1,298
addi s2,s4,180
xori s1,s5,1782
srai s3,s4,7
srli s2,s1,3
sltu s1,s1,s2
xor s2,s1,s3
srl s3,s4,s3
xor s5,s2,s5
bne s4,s4,rand_control_756
addi s1,s1,1
rand_control_756:
beq s1,s1,rand_control_757
addi s4,s4,1
rand_control_757:
srli s5,s3,9
xor s2,s5,s5
andi s2,s5,672
bne s3,s3,rand_control_761
addi s5,s5,1
rand_control_761:
srai s2,s5,12
srli s4,s2,0
sltu s4,s1,s2
ori s5,s4,533
slt s2,s1,s3
add s5,s2,s5
and s2,s5,s3
slt s5,s2,s3
sub s1,s5,s2
sltu s3,s1,s5
slli s5,s2,21
beq s1,s1,rand_control_773
addi s3,s3,1
rand_control_773:
add s4,s1,s3
add s2,s4,s4
sll s3,s2,s5
addi s2,s5,-1901
sll s4,s1,s4
sltu s2,s1,s4
sub s2,s1,s4
slt s3,s5,s3
beq s4,s4,rand_control_782
addi s3,s3,1
rand_control_782:
slt s4,s4,s3
xori s4,s5,448
addi s1,s4,495
slt s3,s5,s4
ori s2,s5,621
andi s3,s1,1970
slt s2,s4,s2
bne s4,s4,rand_control_790
addi s4,s4,1
rand_control_790:
sll s1,s1,s5
srl s4,s3,s2
sub s5,s3,s3
xor s3,s3,s2
srl s3,s1,s3
andi s5,s3,1609
srl s1,s5,s5
ori s3,s4,-1410
beq s3,s3,rand_control_799
addi s5,s5,1
rand_control_799:
ori s1,s4,-1356
xori s2,s2,-1307
and s2,s2,s3
add s3,s4,s2
sltu s5,s4,s3
slt s2,s2,s5
xori s5,s3,243
addi s3,s2,1293
sub s3,s5,s2
sltu s2,s3,s3
and s3,s5,s5
sltu s5,s5,s1
beq s3,s3,rand_control_812
addi s2,s2,1
rand_control_812:
srai s2,s5,31
slli s3,s4,13
srl s4,s1,s4
or s5,s3,s2
slli s1,s5,18
ori s1,s3,-1607
beq s3,s3,rand_control_819
addi s5,s5,1
rand_control_819:
add s3,s3,s2
ori s1,s3,-221
srl s4,s4,s4
add s5,s1,s4
add s1,s3,s4
bne s1,s1,rand_control_825
addi s3,s3,1
rand_control_825:
slt s4,s3,s4
and s3,s4,s2
slli s1,s2,19
srai s2,s2,2
andi s3,s5,770
srai s5,s2,27
or s4,s3,s1
srl s1,s1,s4
srl s1,s3,s5
sltu s5,s4,s2
sll s4,s1,s2
andi s2,s4,-483
sltu s4,s3,s5
beq s2,s2,rand_control_839
addi s4,s4,1
rand_control_839:
xori s1,s4,1478
srli s4,s5,10
bne s2,s2,rand_control_842
addi s5,s5,1
rand_control_842:
srli s5,s4,28
addi s4,s4,-171
or s5,s5,s1
beq s5,s5,rand_control_846
addi s4,s4,1
rand_control_846:
beq s1,s1,rand_control_847
addi s4,s4,1
rand_control_847:
sub s4,s5,s2
slli s3,s3,14
xor s3,s5,s3
sll s4,s4,s5
and s1,s5,s2
srl s2,s4,s5
xor s1,s1,s5
ori s5,s4,197
sub s1,s3,s1
srai s4,s3,13
slt s5,s4,s1
sltu s5,s5,s1
xori s1,s2,1089
ori s5,s4,-343
sub s1,s4,s1
slt s1,s5,s5
add s4,s1,s5
beq s3,s3,rand_control_865
addi s2,s2,1
rand_control_865:
srai s5,s3,27
addi s1,s3,383
andi s5,s2,155
slt s5,s1,s2
bne s5,s5,rand_control_870
addi s4,s4,1
rand_control_870:
add s1,s4,s5
sltu s3,s3,s3
and s4,s2,s3
xor s3,s3,s2
sltu s4,s5,s4
slli s3,s4,24
add s5,s4,s1
slli s4,s1,4
slli s1,s2,31
sll s2,s2,s2
sub s2,s3,s1
sll s5,s4,s5
srli s1,s2,15
bne s3,s3,rand_control_884
addi s1,s1,1
rand_control_884:
sub s1,s4,s5
srl s3,s4,s4
srai s4,s2,27
sub s1,s2,s1
srl s3,s5,s4
bne s1,s1,rand_control_890
addi s1,s1,1
rand_control_890:
srl s5,s4,s3
and s4,s5,s1
srl s2,s4,s3
slli s4,s3,27
bne s2,s2,rand_control_895
addi s1,s1,1
rand_control_895:
ori s5,s5,-1756
beq s3,s3,rand_control_897
addi s4,s4,1
rand_control_897:
srai s2,s1,31
sltu s2,s4,s2
srl s5,s3,s4
or s4,s3,s1
addi s5,s4,124
srli s4,s3,15
add s3,s4,s4
andi s5,s5,1320
beq s1,s1,rand_control_906
addi s5,s5,1
rand_control_906:
ori s1,s5,1844
slt s1,s3,s1
or s2,s2,s4
sll s5,s3,s4
sltu s3,s5,s3
sltu s4,s5,s3
bne s2,s2,rand_control_913
addi s1,s1,1
rand_control_913:
srai s5,s2,0
srl s1,s2,s5
sltu s5,s4,s4
srai s3,s5,5
xori s4,s1,512
srl s2,s4,s4
sltu s4,s3,s1
srli s5,s5,31
xori s1,s3,215
slli s4,s5,30
beq s1,s1,rand_control_924
addi s2,s2,1
rand_control_924:
xori s4,s1,-1807
or s1,s4,s1
srai s4,s1,19
sub s1,s4,s2
or s5,s1,s3
ori s3,s2,1223
slt s2,s3,s1
add s1,s5,s1
sltu s4,s4,s4
xori s4,s3,-894
xori s4,s5,-1134
srli s4,s2,11
and s2,s5,s2
xori s3,s4,-1041
ori s4,s2,-1263
sltu s4,s4,s1
slli s1,s2,5
slli s4,s1,14
add s2,s5,s5
sltu s4,s3,s3
srai s4,s1,12
sub s5,s4,s5
beq s1,s1,rand_control_947
addi s3,s3,1
rand_control_947:
sub s4,s3,s1
sub s1,s2,s5
srl s5,s5,s3
slt s2,s2,s4
xor s4,s5,s1
srli s5,s5,17
andi s2,s1,-39
and s3,s5,s5
andi s5,s3,1332
addi s5,s5,-551
sll s3,s3,s3
xori s4,s3,-764
and s3,s4,s5
slt s3,s1,s3
srl s5,s5,s3
slt s5,s1,s4
sub s4,s5,s4
srl s3,s5,s4
bne s1,s1,rand_control_966
addi s3,s3,1
rand_control_966:
or s4,s5,s1
xori s2,s5,-714
slli s4,s1,10
addi s3,s2,1406
xori s2,s3,1
add s4,s2,s4
bne s3,s3,rand_control_973
addi s1,s1,1
rand_control_973:
sltu s4,s4,s1
beq s3,s3,rand_control_975
addi s1,s1,1
rand_control_975:
slli s5,s4,23
sll s2,s5,s2
xor s3,s5,s1
slt s3,s5,s5
slli s5,s2,16
andi s2,s3,1876
xori s3,s1,424
srl s3,s2,s5
add s4,s5,s3
add s3,s3,s4
srai s3,s3,8
xori s5,s3,-1940
srl s2,s1,s5
sltu s3,s2,s5
addi s2,s5,-2011
sub s4,s2,s4
xori s3,s3,-315
slt s3,s1,s1
beq s1,s1,rand_control_994
addi s3,s3,1
rand_control_994:
srai s2,s5,18
xori s4,s5,-928
ori s4,s2,-350
sltu s4,s1,s3
add s3,s1,s1
srl s4,s3,s2
sltu s4,s1,s2
add s5,s2,s2
sll s2,s2,s1
and s4,s3,s3
sltu s5,s4,s4
srli s5,s5,21
sub s3,s3,s1
srli s4,s2,16
sub s1,s4,s4
sub s3,s3,s4
sub s4,s4,s2
sub s4,s2,s5
srl s3,s1,s3
sll s4,s1,s3
and s4,s2,s1
sll s2,s2,s2
addi s5,s3,-1488
ori s2,s5,-779
beq s1,s1,rand_control_1019
addi s5,s5,1
rand_control_1019:
xori s3,s5,-1787
andi s5,s1,-411
and s3,s1,s1
bne s5,s5,rand_control_1023
addi s3,s3,1
rand_control_1023:
xori s3,s4,814
beq s2,s2,rand_control_1025
addi s4,s4,1
rand_control_1025:
sltu s3,s4,s1
addi s3,s1,-657
bne s5,s5,rand_control_1028
addi s4,s4,1
rand_control_1028:
ori s3,s4,-569
xori s2,s4,-1443
xor s4,s1,s2
srli s3,s1,29
addi s3,s2,1366
slli s3,s2,19
xori s5,s5,293
bne s1,s1,rand_control_1036
addi s2,s2,1
rand_control_1036:
ori s2,s1,1952
sltu s5,s5,s2
or s5,s4,s5
slt s4,s3,s4
sub s2,s4,s1
slt s4,s3,s2
slli s5,s3,13
srl s5,s1,s4
slli s2,s4,9
andi s1,s2,-1433
srl s4,s4,s4
xor s2,s3,s1
addi s2,s3,753
slli s1,s2,25
bne s3,s3,rand_control_1051
addi s5,s5,1
rand_control_1051:
slli s2,s3,10
sub s4,s1,s5
add s5,s1,s3
beq s1,s1,rand_control_1055
addi s4,s4,1
rand_control_1055:
addi s1,s1,-1801
andi s5,s4,643
add s5,s4,s5
srai s1,s5,16
sltu s5,s3,s4
slt s3,s2,s5
andi s4,s4,-820
srai s4,s4,9
andi s4,s4,-379
and s3,s1,s3
or s4,s1,s4
srl s3,s3,s5
andi s2,s2,-783
sltu s3,s3,s1
beq s3,s3,rand_control_1070
addi s4,s4,1
rand_control_1070:
sll s2,s5,s3
srli s1,s5,31
xori s4,s5,-769
bne s3,s3,rand_control_1074
addi s1,s1,1
rand_control_1074:
addi s5,s1,-1765
beq s5,s5,rand_control_1076
addi s2,s2,1
rand_control_1076:
ori s2,s1,-177
srli s5,s3,19
sll s3,s4,s5
beq s4,s4,rand_control_1080
addi s1,s1,1
rand_control_1080:
bne s2,s2,rand_control_1081
addi s4,s4,1
rand_control_1081:
srli s4,s3,18
bne s5,s5,rand_control_1083
addi s1,s1,1
rand_control_1083:
beq s5,s5,rand_control_1084
addi s3,s3,1
rand_control_1084:
sltu s4,s5,s2
srli s1,s3,0
srli s4,s1,15
sltu s3,s1,s4
srli s4,s3,17
xor s3,s3,s1
srli s3,s2,16
add s3,s5,s2
xori s2,s5,35
or s1,s3,s1
addi s1,s3,1114
or s5,s2,s5
sub s5,s5,s3
bne s4,s4,rand_control_1098
addi s1,s1,1
rand_control_1098:
xori s1,s1,-1104
slt s5,s4,s3
slt s2,s3,s2
xor s5,s2,s1
srli s3,s1,26
sltu s3,s4,s2
ori s2,s4,-169
sltu s4,s1,s5
srli s1,s3,16
xor s1,s3,s2
srl s3,s3,s5
slli s4,s1,25
sub s5,s3,s5
srl s3,s5,s2
or s4,s5,s5
addi s5,s5,1819
beq s2,s2,rand_control_1115
addi s1,s1,1
rand_control_1115:
andi s2,s5,2043
sll s5,s3,s2
sltu s1,s2,s3
ori s2,s2,-223
addi s1,s4,856
sltu s1,s4,s5
or s1,s4,s5
xori s3,s1,-164
add s3,s3,s1
sltu s5,s1,s3
srl s2,s3,s3
xori s2,s3,707
beq s3,s3,rand_control_1128
addi s2,s2,1
rand_control_1128:
xori s1,s4,433
sll s5,s1,s2
or s5,s2,s5
ori s3,s2,-1068
ori s2,s1,-1286
srai s1,s5,9
ori s4,s3,-681
beq s2,s2,rand_control_1136
addi s3,s3,1
rand_control_1136:
sltu s3,s2,s3
srl s5,s2,s1
sll s5,s4,s2
sll s3,s3,s5
srai s1,s2,0
beq s5,s5,rand_control_1142
addi s3,s3,1
rand_control_1142:
srli s1,s3,0
sll s4,s3,s3
addi s4,s5,437
addi s3,s4,615
sub s4,s3,s2
srli s1,s3,0
andi s2,s5,1580
slt s4,s4,s2
or s4,s3,s4
xori s3,s3,-946
xori s3,s5,-1756
srai s4,s3,6
slt s2,s4,s4
or s4,s1,s5
or s5,s5,s2
sltu s3,s2,s2
sltu s3,s5,s3
addi s5,s5,406
sltu s3,s4,s4
srl s4,s5,s2
or s2,s5,s4
bne s5,s5,rand_control_1164
addi s5,s5,1
rand_control_1164:
sll s3,s5,s4
beq s3,s3,rand_control_1166
addi s1,s1,1
rand_control_1166:
slt s2,s2,s1
addi s3,s5,-263
ori s2,s5,1867
sll s2,s3,s4
xor s1,s2,s5
srai s2,s3,22
and s4,s3,s4
xor s2,s3,s2
xor s5,s4,s5
beq s3,s3,rand_control_1176
addi s1,s1,1
rand_control_1176:
sll s1,s4,s4
sub s5,s4,s5
bne s3,s3,rand_control_1179
addi s2,s2,1
rand_control_1179:
andi s2,s4,535
srl s2,s3,s5
bne s1,s1,rand_control_1182
addi s1,s1,1
rand_control_1182:
slli s3,s2,15
and s3,s1,s2
beq s2,s2,rand_control_1185
addi s5,s5,1
rand_control_1185:
srai s4,s3,17
slli s1,s4,11
beq s5,s5,rand_control_1188
addi s4,s4,1
rand_control_1188:
add s1,s5,s4
addi s2,s1,1572
sltu s5,s1,s3
or s2,s5,s3
srai s4,s4,20
xor s1,s3,s5
andi s1,s5,171
xori s2,s2,-807
slli s2,s3,20
bne s5,s5,rand_control_1198
addi s4,s4,1
rand_control_1198:
bne s1,s1,rand_control_1199
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

