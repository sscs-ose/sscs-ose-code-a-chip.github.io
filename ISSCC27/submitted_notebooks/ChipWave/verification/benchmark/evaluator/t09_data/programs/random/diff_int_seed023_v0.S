.option norvc
.section .text.init
.globl _start
_start:
la s0,scratch
li t0,0x90000000
li s1,4046660258
li s2,2790423133
li s3,1152263661
li s4,1057767660
li s5,1511535395
beq s5,s5,rand_control_0
addi s5,s5,1
rand_control_0:
add s5,s1,s1
add s5,s5,s3
slt s3,s5,s1
sub s3,s4,s4
srai s2,s3,18
or s4,s3,s3
srai s4,s3,22
ori s2,s4,-1059
andi s1,s4,-671
slt s2,s1,s5
xori s2,s1,667
beq s5,s5,rand_control_12
addi s2,s2,1
rand_control_12:
srl s4,s2,s4
xori s2,s5,-665
srli s4,s4,9
xor s1,s3,s5
sltu s4,s3,s3
sll s1,s4,s4
srai s4,s2,18
slli s3,s4,8
xori s5,s4,463
beq s1,s1,rand_control_22
addi s3,s3,1
rand_control_22:
beq s2,s2,rand_control_23
addi s3,s3,1
rand_control_23:
addi s2,s2,-1274
beq s2,s2,rand_control_25
addi s1,s1,1
rand_control_25:
srl s3,s5,s4
xor s1,s3,s4
beq s1,s1,rand_control_28
addi s3,s3,1
rand_control_28:
sub s1,s4,s4
srl s2,s2,s2
srli s4,s3,13
sub s2,s1,s1
beq s1,s1,rand_control_33
addi s3,s3,1
rand_control_33:
beq s1,s1,rand_control_34
addi s5,s5,1
rand_control_34:
slt s3,s2,s1
xori s5,s4,-131
sll s1,s1,s5
slli s3,s5,17
andi s2,s1,579
slli s3,s4,6
ori s3,s1,-337
ori s4,s3,-1571
slt s2,s3,s2
srl s4,s5,s5
srl s1,s1,s4
xor s2,s2,s2
bne s1,s1,rand_control_47
addi s5,s5,1
rand_control_47:
slli s3,s4,13
srai s5,s3,10
beq s1,s1,rand_control_50
addi s4,s4,1
rand_control_50:
andi s3,s3,-1974
sll s3,s5,s1
slt s3,s1,s5
ori s1,s1,35
sub s4,s1,s1
srai s3,s3,23
add s1,s5,s1
or s1,s3,s2
slt s5,s5,s4
srai s4,s4,16
addi s4,s4,-1575
xor s1,s1,s5
sltu s4,s5,s5
sltu s5,s2,s2
bne s3,s3,rand_control_65
addi s2,s2,1
rand_control_65:
sltu s3,s1,s2
andi s5,s4,1122
srl s2,s5,s5
srai s2,s3,14
and s2,s2,s3
slt s3,s2,s5
and s2,s3,s4
xor s4,s1,s4
ori s3,s1,479
srli s3,s1,14
slt s3,s3,s4
xor s3,s2,s2
andi s4,s3,896
sltu s5,s4,s5
addi s2,s1,-1150
add s1,s5,s4
and s2,s5,s1
xori s3,s2,268
srli s5,s2,28
add s4,s3,s4
beq s5,s5,rand_control_86
addi s3,s3,1
rand_control_86:
srl s5,s3,s3
bne s5,s5,rand_control_88
addi s3,s3,1
rand_control_88:
sltu s4,s3,s2
slli s3,s2,2
beq s2,s2,rand_control_91
addi s4,s4,1
rand_control_91:
sub s1,s2,s2
sltu s2,s5,s5
xor s4,s3,s1
sltu s3,s1,s5
srl s4,s1,s3
sltu s2,s4,s3
srli s1,s3,23
andi s3,s2,-117
bne s5,s5,rand_control_100
addi s4,s4,1
rand_control_100:
bne s2,s2,rand_control_101
addi s2,s2,1
rand_control_101:
beq s2,s2,rand_control_102
addi s2,s2,1
rand_control_102:
or s2,s5,s4
xor s2,s2,s5
xori s3,s3,950
sll s2,s3,s5
srli s1,s3,14
and s5,s5,s3
sll s1,s2,s2
sltu s1,s5,s1
srl s5,s1,s1
or s3,s2,s1
srli s3,s5,22
srai s3,s3,7
or s3,s5,s4
srai s4,s1,28
srli s5,s1,27
slt s1,s5,s1
addi s5,s1,1880
beq s1,s1,rand_control_120
addi s3,s3,1
rand_control_120:
add s3,s2,s4
sltu s5,s5,s5
srli s1,s3,10
andi s3,s3,-348
sub s5,s5,s2
andi s2,s3,-1259
bne s4,s4,rand_control_127
addi s1,s1,1
rand_control_127:
beq s5,s5,rand_control_128
addi s4,s4,1
rand_control_128:
srai s2,s1,17
ori s5,s3,-333
ori s1,s3,72
beq s1,s1,rand_control_132
addi s2,s2,1
rand_control_132:
sltu s5,s3,s3
or s4,s2,s1
ori s5,s1,568
xor s3,s2,s5
slt s5,s2,s1
bne s2,s2,rand_control_138
addi s1,s1,1
rand_control_138:
or s3,s2,s5
or s4,s3,s5
sll s1,s2,s3
addi s2,s1,1366
add s5,s3,s1
sll s3,s4,s2
srai s5,s3,19
addi s5,s4,-1676
sltu s5,s3,s5
xori s1,s4,-315
sub s2,s1,s2
srl s1,s5,s5
or s4,s4,s2
beq s3,s3,rand_control_152
addi s1,s1,1
rand_control_152:
sll s5,s1,s5
xori s1,s5,-482
slt s2,s5,s1
sub s5,s5,s5
ori s3,s2,1731
ori s2,s2,-622
bne s2,s2,rand_control_159
addi s5,s5,1
rand_control_159:
sub s2,s1,s3
addi s5,s1,1818
xor s3,s1,s5
xor s5,s2,s4
bne s4,s4,rand_control_164
addi s5,s5,1
rand_control_164:
sll s5,s4,s1
addi s1,s1,-801
sll s1,s2,s5
sltu s3,s3,s3
xor s1,s2,s2
srl s2,s3,s2
andi s1,s2,932
sub s2,s5,s1
srl s3,s2,s2
or s1,s2,s5
sub s2,s4,s3
bne s1,s1,rand_control_176
addi s5,s5,1
rand_control_176:
add s1,s3,s4
slli s4,s3,3
sltu s5,s1,s3
addi s3,s2,-160
sll s2,s1,s5
add s1,s4,s4
andi s5,s5,1089
bne s5,s5,rand_control_184
addi s5,s5,1
rand_control_184:
addi s1,s4,1268
srli s4,s1,11
beq s5,s5,rand_control_187
addi s3,s3,1
rand_control_187:
addi s4,s3,-1378
or s3,s5,s2
or s2,s3,s1
srli s1,s2,11
xori s3,s3,-40
srli s5,s2,5
srl s4,s3,s4
slli s1,s2,10
beq s4,s4,rand_control_196
addi s2,s2,1
rand_control_196:
srai s3,s3,20
beq s1,s1,rand_control_198
addi s3,s3,1
rand_control_198:
beq s1,s1,rand_control_199
addi s1,s1,1
rand_control_199:
sll s2,s5,s3
srl s4,s3,s5
and s3,s5,s1
srl s2,s4,s3
xori s1,s5,-784
xor s5,s2,s3
slli s5,s1,1
bne s5,s5,rand_control_207
addi s4,s4,1
rand_control_207:
and s2,s2,s1
xori s1,s5,-1601
xor s4,s2,s1
xori s5,s4,-1784
srli s2,s3,5
srl s5,s4,s3
or s5,s4,s3
xor s3,s2,s1
or s1,s3,s2
bne s4,s4,rand_control_217
addi s5,s5,1
rand_control_217:
xor s3,s2,s1
or s3,s2,s4
beq s4,s4,rand_control_220
addi s2,s2,1
rand_control_220:
xor s3,s5,s1
sltu s1,s2,s3
sub s3,s3,s2
ori s3,s3,-109
bne s2,s2,rand_control_225
addi s3,s3,1
rand_control_225:
and s2,s4,s1
srai s5,s2,25
xori s2,s2,-1523
add s3,s1,s4
ori s4,s5,-754
sltu s2,s2,s3
addi s3,s4,1803
xori s2,s1,26
srai s4,s2,6
beq s3,s3,rand_control_235
addi s2,s2,1
rand_control_235:
srai s2,s5,10
bne s3,s3,rand_control_237
addi s4,s4,1
rand_control_237:
srl s4,s5,s1
slt s5,s3,s1
bne s1,s1,rand_control_240
addi s5,s5,1
rand_control_240:
srli s1,s1,14
or s2,s2,s1
add s2,s1,s1
slt s5,s3,s2
sll s5,s1,s3
slli s2,s4,12
srl s1,s4,s1
and s2,s4,s4
xori s1,s3,-1243
srli s3,s5,23
and s4,s2,s1
sub s1,s4,s3
andi s3,s4,-1717
beq s1,s1,rand_control_254
addi s4,s4,1
rand_control_254:
beq s4,s4,rand_control_255
addi s1,s1,1
rand_control_255:
beq s3,s3,rand_control_256
addi s3,s3,1
rand_control_256:
xori s3,s4,273
slt s2,s2,s3
bne s5,s5,rand_control_259
addi s2,s2,1
rand_control_259:
addi s2,s5,-1188
beq s1,s1,rand_control_261
addi s1,s1,1
rand_control_261:
slli s3,s2,6
slt s1,s4,s4
sub s4,s2,s4
beq s3,s3,rand_control_265
addi s3,s3,1
rand_control_265:
bne s4,s4,rand_control_266
addi s3,s3,1
rand_control_266:
slt s3,s5,s5
bne s3,s3,rand_control_268
addi s4,s4,1
rand_control_268:
and s1,s4,s1
sub s2,s2,s4
srai s2,s5,11
xor s4,s2,s5
bne s1,s1,rand_control_273
addi s1,s1,1
rand_control_273:
addi s4,s3,1813
sub s1,s2,s3
xori s3,s1,-601
beq s3,s3,rand_control_277
addi s5,s5,1
rand_control_277:
and s3,s4,s3
srl s3,s1,s3
sltu s4,s5,s1
xori s5,s1,-1867
sub s4,s5,s1
andi s5,s4,2004
slt s5,s1,s5
sll s1,s2,s2
srl s5,s4,s5
xor s5,s3,s5
ori s4,s1,-1866
and s1,s3,s5
andi s1,s3,179
beq s5,s5,rand_control_291
addi s4,s4,1
rand_control_291:
beq s5,s5,rand_control_292
addi s4,s4,1
rand_control_292:
beq s1,s1,rand_control_293
addi s4,s4,1
rand_control_293:
sltu s2,s3,s2
sll s4,s4,s4
srai s4,s4,0
sltu s4,s5,s4
xor s1,s2,s5
ori s2,s1,1695
slli s5,s2,15
sll s1,s1,s5
xori s3,s1,-1048
xor s2,s1,s3
bne s4,s4,rand_control_304
addi s3,s3,1
rand_control_304:
xor s1,s5,s4
slt s1,s1,s3
xori s4,s2,-1091
srai s3,s2,15
xor s3,s2,s3
slli s5,s4,1
sltu s5,s2,s4
addi s2,s2,-1319
or s5,s5,s4
addi s2,s4,-1423
andi s5,s2,738
andi s2,s5,948
xori s3,s2,730
srli s1,s5,31
bne s3,s3,rand_control_319
addi s4,s4,1
rand_control_319:
xor s1,s1,s4
slli s5,s3,26
slli s5,s2,27
or s5,s3,s4
sub s2,s1,s1
slli s2,s3,13
ori s3,s4,634
slt s3,s3,s4
addi s5,s3,-1352
sll s3,s2,s3
srai s3,s2,21
or s1,s1,s3
srl s3,s1,s1
sub s5,s4,s3
sub s1,s5,s2
add s5,s1,s3
or s2,s5,s4
xor s1,s2,s2
addi s1,s2,667
addi s4,s2,-1205
xor s2,s4,s3
slli s4,s4,10
addi s1,s3,-1395
and s1,s4,s5
sll s3,s3,s5
srl s3,s5,s4
add s5,s5,s1
ori s2,s5,-698
srli s5,s3,27
bne s1,s1,rand_control_349
addi s4,s4,1
rand_control_349:
srli s2,s3,31
xor s1,s3,s4
slli s4,s2,1
xori s4,s4,-1470
andi s2,s5,-1073
srai s2,s5,30
bne s4,s4,rand_control_356
addi s1,s1,1
rand_control_356:
slli s4,s5,6
xori s4,s3,-1579
addi s1,s5,983
or s3,s2,s4
ori s1,s3,-127
and s1,s3,s2
sub s3,s2,s2
beq s1,s1,rand_control_364
addi s2,s2,1
rand_control_364:
xori s4,s2,-1204
and s4,s3,s3
sll s1,s3,s5
addi s4,s4,-1920
srai s3,s3,17
sub s5,s3,s5
bne s2,s2,rand_control_371
addi s3,s3,1
rand_control_371:
andi s4,s1,284
andi s4,s1,-1442
xor s3,s4,s2
srli s4,s3,25
xor s5,s3,s2
addi s1,s4,569
slli s3,s3,8
srli s2,s3,18
add s4,s5,s1
and s3,s3,s3
andi s2,s1,-984
or s3,s2,s3
addi s1,s3,1147
and s2,s1,s3
slli s3,s3,14
xor s2,s2,s2
add s2,s5,s5
beq s3,s3,rand_control_389
addi s4,s4,1
rand_control_389:
xori s1,s3,1704
slt s1,s4,s3
and s4,s4,s3
sltu s4,s1,s5
sub s3,s1,s3
bne s3,s3,rand_control_395
addi s1,s1,1
rand_control_395:
and s4,s2,s1
andi s3,s3,363
srli s5,s4,18
xori s2,s2,248
add s4,s1,s4
andi s5,s3,912
slt s5,s1,s2
srli s5,s1,29
slli s2,s4,1
andi s4,s1,-779
or s5,s5,s1
srl s2,s2,s4
xori s3,s1,-121
srli s4,s3,14
sltu s5,s1,s1
xor s5,s4,s3
bne s1,s1,rand_control_412
addi s3,s3,1
rand_control_412:
slli s3,s1,30
andi s4,s1,-1773
add s3,s4,s5
xor s3,s4,s3
sub s3,s5,s2
andi s3,s2,-25
xori s2,s4,1298
slt s4,s3,s1
xori s2,s5,1357
bne s3,s3,rand_control_422
addi s3,s3,1
rand_control_422:
sub s5,s2,s3
sltu s1,s5,s5
or s5,s2,s2
bne s5,s5,rand_control_426
addi s1,s1,1
rand_control_426:
srli s3,s3,14
bne s1,s1,rand_control_428
addi s5,s5,1
rand_control_428:
sub s2,s1,s1
add s3,s4,s2
beq s3,s3,rand_control_431
addi s3,s3,1
rand_control_431:
or s5,s3,s1
sub s2,s5,s1
sub s5,s2,s5
beq s2,s2,rand_control_435
addi s1,s1,1
rand_control_435:
and s3,s3,s2
srl s2,s4,s4
addi s2,s5,1268
xor s2,s5,s5
sll s1,s5,s5
sll s5,s1,s4
beq s2,s2,rand_control_442
addi s2,s2,1
rand_control_442:
andi s4,s2,-829
xori s2,s4,211
xor s5,s1,s3
andi s5,s5,-824
sltu s4,s3,s1
slli s4,s1,15
add s3,s3,s3
xori s4,s1,-1079
xor s1,s3,s4
sll s1,s1,s3
sub s2,s5,s1
andi s5,s3,32
and s5,s3,s3
slli s2,s4,4
beq s1,s1,rand_control_457
addi s3,s3,1
rand_control_457:
add s3,s3,s5
and s3,s5,s2
slli s5,s2,11
andi s3,s1,-1458
ori s5,s5,90
add s3,s3,s1
sub s2,s2,s5
ori s1,s2,462
xori s1,s2,-1127
srl s1,s4,s4
add s1,s2,s2
addi s2,s3,1287
and s4,s3,s5
add s1,s5,s2
ori s2,s3,1936
add s1,s5,s1
ori s2,s3,-998
and s2,s1,s3
srl s2,s1,s4
slt s1,s3,s3
ori s1,s1,1580
sltu s3,s1,s4
add s5,s2,s4
srli s1,s4,15
addi s1,s4,-1537
srl s2,s3,s5
sltu s5,s4,s2
xori s2,s4,-2012
srl s4,s1,s2
and s4,s3,s1
srli s3,s2,13
bne s1,s1,rand_control_489
addi s5,s5,1
rand_control_489:
sub s1,s5,s3
slli s4,s5,27
sub s1,s4,s5
addi s4,s1,-651
srli s2,s1,3
andi s3,s2,432
bne s4,s4,rand_control_496
addi s2,s2,1
rand_control_496:
xori s1,s4,-1362
srai s1,s3,8
sll s2,s4,s2
and s1,s3,s4
and s2,s3,s4
sub s1,s3,s2
sub s4,s1,s2
slt s4,s3,s3
andi s1,s1,1938
slt s1,s3,s5
srli s4,s5,24
slli s2,s3,19
add s1,s1,s2
sll s2,s3,s4
addi s4,s4,708
slli s4,s4,13
or s2,s1,s1
addi s3,s2,-315
sltu s2,s1,s3
xori s2,s5,2040
andi s2,s2,1127
sub s5,s4,s3
sub s2,s4,s2
beq s2,s2,rand_control_520
addi s5,s5,1
rand_control_520:
srai s2,s4,21
sltu s5,s4,s5
xori s4,s5,1131
bne s5,s5,rand_control_524
addi s5,s5,1
rand_control_524:
bne s3,s3,rand_control_525
addi s1,s1,1
rand_control_525:
bne s3,s3,rand_control_526
addi s2,s2,1
rand_control_526:
sltu s4,s3,s2
addi s2,s4,654
srl s4,s4,s3
ori s3,s3,1387
bne s1,s1,rand_control_531
addi s1,s1,1
rand_control_531:
slt s4,s1,s3
addi s2,s2,-1528
sltu s4,s3,s1
sll s1,s4,s4
andi s4,s4,861
xor s3,s4,s1
slt s2,s2,s3
slli s3,s3,3
sll s1,s2,s1
add s3,s5,s2
add s2,s2,s1
srli s2,s3,25
sll s1,s5,s3
ori s2,s5,1101
addi s1,s5,277
or s3,s2,s5
ori s3,s3,-441
and s3,s1,s5
andi s4,s1,-1746
and s5,s5,s2
xori s1,s1,1033
sltu s3,s4,s5
slli s4,s4,18
xor s1,s2,s5
slt s3,s5,s5
srli s5,s2,25
xor s5,s1,s3
slt s4,s4,s4
ori s4,s2,692
andi s3,s5,-510
beq s4,s4,rand_control_562
addi s1,s1,1
rand_control_562:
srl s2,s1,s5
xor s3,s2,s3
add s5,s3,s2
bne s3,s3,rand_control_566
addi s2,s2,1
rand_control_566:
sub s4,s1,s3
and s5,s1,s1
or s4,s2,s2
sub s5,s5,s1
sltu s1,s1,s5
srl s4,s2,s5
ori s3,s2,-1280
slt s4,s2,s4
or s2,s3,s2
addi s4,s3,-949
slt s1,s2,s5
sltu s1,s1,s2
andi s3,s2,1678
addi s5,s3,898
andi s3,s5,279
xori s4,s3,1706
addi s3,s2,1316
beq s5,s5,rand_control_584
addi s5,s5,1
rand_control_584:
xor s1,s3,s1
add s4,s5,s2
srl s5,s4,s1
sub s1,s3,s2
sll s4,s1,s2
sub s3,s5,s3
or s3,s1,s5
slli s4,s4,31
add s5,s2,s5
beq s2,s2,rand_control_594
addi s4,s4,1
rand_control_594:
srai s2,s1,23
addi s2,s3,-248
sub s3,s1,s1
sub s2,s4,s4
slli s3,s2,13
sll s2,s4,s4
beq s5,s5,rand_control_601
addi s2,s2,1
rand_control_601:
slt s5,s2,s4
beq s3,s3,rand_control_603
addi s3,s3,1
rand_control_603:
or s5,s3,s3
sll s3,s3,s2
andi s4,s4,252
add s5,s2,s5
andi s4,s1,485
xori s4,s4,1629
bne s5,s5,rand_control_610
addi s1,s1,1
rand_control_610:
or s1,s5,s5
xori s5,s4,-1181
xor s2,s5,s1
bne s1,s1,rand_control_614
addi s4,s4,1
rand_control_614:
beq s5,s5,rand_control_615
addi s5,s5,1
rand_control_615:
or s2,s1,s4
add s2,s4,s5
add s5,s5,s3
or s3,s4,s4
xori s4,s5,-767
srl s3,s2,s2
beq s2,s2,rand_control_622
addi s5,s5,1
rand_control_622:
addi s4,s2,-756
bne s3,s3,rand_control_624
addi s2,s2,1
rand_control_624:
srli s4,s4,29
beq s5,s5,rand_control_626
addi s5,s5,1
rand_control_626:
sll s3,s4,s5
sltu s5,s4,s5
sltu s2,s1,s3
beq s4,s4,rand_control_630
addi s5,s5,1
rand_control_630:
srl s3,s3,s2
srai s1,s4,24
beq s4,s4,rand_control_633
addi s2,s2,1
rand_control_633:
sltu s3,s4,s2
andi s2,s4,1325
slt s1,s4,s5
slli s3,s3,10
and s5,s4,s5
sltu s3,s3,s4
xori s5,s3,-644
sltu s5,s4,s3
srli s1,s2,14
slt s3,s1,s3
and s5,s4,s4
bne s2,s2,rand_control_645
addi s2,s2,1
rand_control_645:
beq s5,s5,rand_control_646
addi s5,s5,1
rand_control_646:
and s1,s2,s3
or s1,s3,s2
srai s5,s4,8
slt s1,s4,s4
slli s3,s3,3
sub s3,s2,s4
ori s1,s4,-1389
addi s4,s4,-468
add s5,s5,s3
srli s4,s3,15
sub s1,s1,s1
srli s3,s1,8
srli s4,s1,14
beq s4,s4,rand_control_660
addi s1,s1,1
rand_control_660:
addi s3,s5,250
xor s3,s4,s3
xori s5,s1,1241
slt s4,s5,s2
slt s5,s3,s4
slt s2,s5,s2
andi s3,s1,-574
sll s4,s3,s2
xori s3,s2,-1455
xor s2,s1,s1
srai s1,s2,9
andi s2,s1,-1730
andi s1,s1,1704
bne s4,s4,rand_control_674
addi s1,s1,1
rand_control_674:
or s3,s3,s1
slt s2,s5,s4
or s5,s3,s3
sll s4,s4,s5
addi s4,s4,-1988
add s1,s3,s2
xori s3,s1,-81
andi s3,s5,-1239
slt s3,s1,s3
andi s3,s1,607
xor s2,s3,s3
beq s1,s1,rand_control_686
addi s1,s1,1
rand_control_686:
add s5,s4,s4
srli s5,s1,25
ori s4,s5,-940
ori s4,s3,-1899
xori s3,s5,-258
xori s2,s1,-783
srli s4,s4,2
bne s5,s5,rand_control_694
addi s5,s5,1
rand_control_694:
srli s4,s5,3
xori s2,s3,-813
beq s5,s5,rand_control_697
addi s2,s2,1
rand_control_697:
xor s1,s2,s2
ori s5,s1,-366
srai s1,s3,19
and s3,s5,s5
sltu s1,s5,s3
slli s2,s1,27
slli s2,s5,0
sub s4,s5,s4
add s2,s4,s1
srl s4,s3,s2
addi s3,s3,1733
xori s1,s5,-1402
slli s2,s3,20
slt s1,s4,s5
andi s5,s2,705
addi s4,s3,-2027
beq s4,s4,rand_control_714
addi s5,s5,1
rand_control_714:
andi s1,s4,516
or s3,s1,s3
beq s5,s5,rand_control_717
addi s1,s1,1
rand_control_717:
srl s2,s5,s2
sll s5,s5,s5
slli s4,s4,9
slli s1,s3,23
srai s2,s3,31
and s5,s2,s4
and s5,s3,s2
andi s3,s1,-329
bne s1,s1,rand_control_726
addi s5,s5,1
rand_control_726:
srli s3,s2,3
sltu s3,s2,s5
sll s2,s2,s2
sltu s2,s3,s5
xor s3,s4,s5
bne s4,s4,rand_control_732
addi s3,s3,1
rand_control_732:
bne s5,s5,rand_control_733
addi s4,s4,1
rand_control_733:
sltu s3,s2,s2
andi s4,s2,1812
xori s2,s5,-53
srai s4,s5,3
andi s4,s3,1250
slli s5,s3,8
xor s2,s4,s1
sub s2,s5,s1
srai s4,s4,7
xor s1,s2,s4
addi s5,s1,-374
sltu s4,s2,s4
bne s2,s2,rand_control_746
addi s5,s5,1
rand_control_746:
bne s5,s5,rand_control_747
addi s5,s5,1
rand_control_747:
sll s5,s4,s3
slt s4,s5,s1
slt s3,s5,s1
add s3,s5,s5
srli s3,s1,15
srai s2,s2,10
srai s2,s1,2
srli s5,s2,19
and s1,s2,s4
andi s3,s2,1919
andi s1,s1,-867
bne s4,s4,rand_control_759
addi s5,s5,1
rand_control_759:
ori s3,s5,729
xori s2,s1,1793
or s5,s2,s3
xori s2,s4,-208
xor s1,s5,s2
ori s5,s2,-331
slt s4,s3,s1
srli s5,s4,29
srai s4,s3,12
sltu s3,s4,s1
slli s2,s3,25
ori s2,s4,1357
sll s3,s5,s5
addi s5,s4,1946
srai s4,s2,29
ori s3,s3,-1334
sltu s3,s3,s4
srai s2,s3,4
srli s4,s5,0
srl s1,s3,s5
beq s1,s1,rand_control_780
addi s2,s2,1
rand_control_780:
srli s5,s3,24
srli s1,s2,7
srl s4,s2,s1
or s2,s5,s5
beq s2,s2,rand_control_785
addi s4,s4,1
rand_control_785:
xor s5,s5,s4
slt s3,s2,s5
xori s4,s2,1583
slli s1,s1,22
sll s1,s3,s4
xori s2,s3,1959
and s5,s4,s1
beq s1,s1,rand_control_793
addi s2,s2,1
rand_control_793:
add s4,s3,s3
xor s4,s5,s2
srli s1,s5,16
slli s4,s3,20
sub s3,s1,s1
sltu s1,s4,s4
beq s2,s2,rand_control_800
addi s5,s5,1
rand_control_800:
and s2,s5,s4
srl s1,s1,s3
and s5,s2,s3
sltu s3,s4,s1
addi s2,s1,1453
ori s2,s5,146
sll s2,s1,s5
bne s5,s5,rand_control_808
addi s1,s1,1
rand_control_808:
addi s1,s4,505
add s1,s5,s2
beq s4,s4,rand_control_811
addi s1,s1,1
rand_control_811:
or s5,s1,s1
sll s5,s2,s5
andi s5,s2,-1665
bne s2,s2,rand_control_815
addi s5,s5,1
rand_control_815:
beq s4,s4,rand_control_816
addi s5,s5,1
rand_control_816:
beq s4,s4,rand_control_817
addi s4,s4,1
rand_control_817:
bne s1,s1,rand_control_818
addi s3,s3,1
rand_control_818:
srl s5,s3,s4
sub s1,s5,s2
ori s1,s1,-523
ori s3,s2,1204
srai s5,s5,25
beq s1,s1,rand_control_824
addi s4,s4,1
rand_control_824:
addi s3,s5,-1077
slt s2,s5,s5
and s5,s2,s4
ori s4,s1,-980
xor s3,s2,s1
slli s3,s2,25
xor s3,s4,s2
or s5,s5,s5
slli s3,s1,11
slt s1,s1,s2
slli s1,s5,7
andi s4,s4,-1340
beq s1,s1,rand_control_837
addi s5,s5,1
rand_control_837:
add s3,s1,s4
sll s3,s2,s3
srli s5,s2,11
add s2,s2,s3
srl s4,s4,s1
or s1,s4,s2
add s2,s4,s3
ori s4,s5,1532
xori s5,s3,1171
srai s4,s3,17
or s5,s5,s1
xor s1,s3,s4
add s4,s1,s5
beq s5,s5,rand_control_851
addi s4,s4,1
rand_control_851:
ori s2,s2,1961
xor s1,s2,s5
srl s3,s1,s1
srl s2,s4,s4
srl s1,s3,s3
srli s5,s5,2
slli s3,s4,19
slt s2,s3,s2
sub s4,s1,s1
and s5,s2,s2
beq s5,s5,rand_control_862
addi s1,s1,1
rand_control_862:
srli s2,s3,23
sll s2,s1,s2
xori s1,s3,-1531
ori s3,s3,812
add s2,s1,s1
slli s2,s3,14
sltu s1,s3,s1
srai s3,s5,13
srl s2,s5,s1
beq s1,s1,rand_control_872
addi s2,s2,1
rand_control_872:
addi s1,s4,-1665
addi s2,s4,-1514
slli s3,s1,12
slli s4,s3,2
slli s2,s5,25
xori s3,s3,1961
ori s1,s1,-644
sub s2,s1,s1
xori s1,s2,-176
sll s2,s4,s2
xor s3,s3,s4
sltu s2,s5,s2
beq s2,s2,rand_control_885
addi s2,s2,1
rand_control_885:
slli s2,s4,12
sub s2,s5,s5
xor s4,s4,s4
add s2,s3,s1
sll s2,s1,s3
bne s1,s1,rand_control_891
addi s5,s5,1
rand_control_891:
xor s5,s5,s2
andi s5,s2,-1912
srl s1,s3,s5
srli s3,s2,30
srl s3,s2,s1
srai s1,s2,4
slli s1,s4,7
or s3,s3,s1
add s3,s2,s4
sll s3,s2,s2
srai s5,s1,19
xori s3,s5,-1882
add s1,s4,s5
sub s3,s1,s5
and s5,s4,s2
andi s4,s2,-1107
add s1,s2,s5
and s2,s4,s5
and s3,s1,s3
slt s5,s5,s1
srli s5,s5,27
srl s1,s5,s4
andi s4,s2,-370
srl s1,s2,s1
slt s4,s4,s3
sll s1,s4,s5
sltu s3,s5,s4
bne s5,s5,rand_control_919
addi s2,s2,1
rand_control_919:
beq s2,s2,rand_control_920
addi s3,s3,1
rand_control_920:
sub s2,s4,s2
srli s1,s4,10
and s3,s2,s2
or s1,s1,s5
beq s3,s3,rand_control_925
addi s4,s4,1
rand_control_925:
xori s1,s5,-348
xori s3,s2,-2000
xori s5,s3,-159
or s2,s5,s5
xori s2,s2,-441
add s3,s1,s4
sll s4,s3,s1
add s5,s1,s5
addi s1,s2,-913
srai s5,s3,28
or s1,s3,s3
beq s1,s1,rand_control_937
addi s4,s4,1
rand_control_937:
andi s4,s2,272
sltu s1,s4,s1
andi s3,s4,-769
sltu s4,s4,s5
srl s1,s2,s1
addi s4,s3,-770
add s1,s5,s2
slt s4,s4,s4
srl s1,s5,s1
slli s4,s1,8
sll s4,s1,s2
slt s2,s1,s3
srl s3,s4,s4
or s3,s5,s3
xor s3,s3,s3
sll s5,s1,s1
xor s4,s1,s2
xori s1,s1,753
bne s5,s5,rand_control_956
addi s5,s5,1
rand_control_956:
ori s1,s2,1284
sub s3,s5,s4
beq s4,s4,rand_control_959
addi s4,s4,1
rand_control_959:
addi s3,s3,709
bne s5,s5,rand_control_961
addi s2,s2,1
rand_control_961:
xor s2,s5,s3
xor s5,s5,s5
or s5,s4,s4
and s1,s1,s1
bne s4,s4,rand_control_966
addi s5,s5,1
rand_control_966:
and s4,s3,s2
or s3,s5,s3
srl s5,s4,s2
slt s2,s5,s4
or s3,s5,s1
xor s4,s2,s5
bne s2,s2,rand_control_973
addi s4,s4,1
rand_control_973:
xori s4,s1,352
and s4,s5,s1
xor s5,s4,s5
andi s2,s2,1155
slt s5,s4,s1
srl s3,s3,s5
srl s2,s4,s2
addi s2,s2,-656
srl s1,s4,s2
xor s5,s1,s4
add s1,s2,s2
srl s3,s5,s3
slt s2,s5,s3
beq s3,s3,rand_control_987
addi s4,s4,1
rand_control_987:
xori s3,s4,-778
slt s4,s4,s3
addi s1,s5,-688
srli s3,s3,0
bne s5,s5,rand_control_992
addi s5,s5,1
rand_control_992:
srl s2,s2,s5
slli s5,s5,13
sltu s3,s1,s4
beq s4,s4,rand_control_996
addi s4,s4,1
rand_control_996:
sub s5,s1,s5
sub s5,s5,s3
sltu s3,s3,s1
xor s3,s1,s5
sub s1,s4,s2
srai s5,s2,21
srli s3,s4,14
slt s5,s5,s1
xori s2,s1,-1807
srl s5,s1,s5
sub s3,s4,s4
beq s4,s4,rand_control_1008
addi s2,s2,1
rand_control_1008:
bne s2,s2,rand_control_1009
addi s4,s4,1
rand_control_1009:
andi s1,s4,1055
beq s2,s2,rand_control_1011
addi s1,s1,1
rand_control_1011:
and s4,s5,s4
bne s4,s4,rand_control_1013
addi s3,s3,1
rand_control_1013:
srl s5,s5,s3
xor s4,s4,s1
xori s1,s5,831
slt s4,s3,s3
xori s3,s3,444
slli s3,s5,27
sll s2,s1,s2
xor s4,s3,s2
and s1,s1,s5
srl s1,s2,s1
slli s4,s5,15
beq s2,s2,rand_control_1025
addi s5,s5,1
rand_control_1025:
slt s3,s4,s2
addi s2,s5,-1289
and s2,s5,s1
sll s1,s5,s4
bne s1,s1,rand_control_1030
addi s1,s1,1
rand_control_1030:
srl s2,s1,s1
slt s5,s1,s2
srl s3,s4,s5
add s5,s5,s3
bne s4,s4,rand_control_1035
addi s2,s2,1
rand_control_1035:
slt s1,s2,s3
and s5,s1,s3
ori s2,s2,911
or s1,s2,s3
srai s1,s2,14
sltu s3,s5,s2
andi s1,s4,1406
srli s3,s2,6
bne s4,s4,rand_control_1044
addi s1,s1,1
rand_control_1044:
xor s3,s1,s5
beq s5,s5,rand_control_1046
addi s3,s3,1
rand_control_1046:
beq s4,s4,rand_control_1047
addi s2,s2,1
rand_control_1047:
srli s4,s3,25
and s4,s2,s3
xori s3,s4,-701
add s4,s4,s3
andi s1,s3,-1839
xori s3,s3,1567
and s2,s5,s5
slli s4,s1,26
xori s4,s2,-1263
sub s1,s4,s1
sltu s3,s3,s2
ori s3,s2,-616
addi s1,s1,-258
sll s3,s2,s4
slt s3,s4,s2
andi s4,s5,80
beq s5,s5,rand_control_1064
addi s3,s3,1
rand_control_1064:
sub s1,s3,s5
srai s5,s2,14
sub s3,s3,s5
or s4,s2,s2
sll s4,s2,s4
beq s3,s3,rand_control_1070
addi s4,s4,1
rand_control_1070:
add s4,s2,s2
ori s2,s5,-1162
sll s4,s4,s1
slt s4,s3,s5
sll s3,s1,s1
slt s4,s5,s4
slt s3,s1,s4
sll s2,s2,s5
slt s1,s2,s5
beq s5,s5,rand_control_1080
addi s1,s1,1
rand_control_1080:
slt s3,s1,s2
ori s3,s2,-502
or s5,s4,s4
slt s4,s5,s3
slt s2,s1,s5
slt s4,s1,s5
srli s1,s2,7
srli s3,s4,19
slli s1,s1,5
xori s2,s4,-1184
sll s3,s2,s1
slt s5,s4,s3
sltu s4,s2,s3
slt s5,s1,s1
srli s4,s4,8
xori s1,s1,-1478
addi s3,s1,12
bne s4,s4,rand_control_1098
addi s2,s2,1
rand_control_1098:
srl s2,s4,s5
sltu s4,s2,s1
addi s2,s2,1040
addi s4,s2,1493
slli s1,s3,30
addi s1,s5,501
xori s3,s4,-23
and s5,s4,s3
srai s4,s1,22
andi s2,s1,1181
or s3,s4,s5
bne s5,s5,rand_control_1110
addi s2,s2,1
rand_control_1110:
slli s4,s2,27
andi s5,s4,622
ori s4,s1,329
xor s1,s3,s5
slt s1,s5,s3
add s2,s5,s5
and s1,s5,s4
sub s1,s4,s4
xori s4,s4,-1442
andi s4,s1,1324
and s4,s2,s3
or s3,s3,s3
sll s1,s3,s2
sltu s2,s1,s3
xori s3,s3,-1575
sub s2,s1,s3
sll s3,s1,s5
xor s3,s4,s1
srl s5,s1,s2
sub s2,s2,s3
xor s2,s5,s1
bne s2,s2,rand_control_1132
addi s5,s5,1
rand_control_1132:
sll s3,s2,s4
srli s3,s2,16
srli s1,s1,1
ori s3,s1,297
addi s2,s5,1405
ori s2,s2,-1108
andi s3,s2,-203
slli s4,s5,14
xori s2,s5,1431
bne s1,s1,rand_control_1142
addi s1,s1,1
rand_control_1142:
sub s2,s5,s3
sub s2,s2,s4
bne s3,s3,rand_control_1145
addi s1,s1,1
rand_control_1145:
addi s2,s3,-1978
beq s2,s2,rand_control_1147
addi s1,s1,1
rand_control_1147:
srai s1,s1,8
add s5,s1,s3
or s3,s2,s4
srai s1,s1,15
sltu s2,s3,s2
srai s5,s5,19
and s4,s3,s4
add s5,s1,s4
beq s3,s3,rand_control_1156
addi s3,s3,1
rand_control_1156:
sltu s2,s4,s3
sll s1,s1,s1
or s5,s3,s1
or s4,s4,s2
or s3,s1,s4
andi s2,s1,655
add s3,s2,s4
sll s3,s3,s4
xori s2,s2,-287
srai s5,s3,28
and s3,s1,s2
add s2,s3,s1
beq s5,s5,rand_control_1169
addi s2,s2,1
rand_control_1169:
srl s1,s2,s4
andi s1,s2,317
xori s1,s4,1964
and s2,s5,s1
andi s2,s3,741
or s1,s1,s3
andi s4,s5,-905
addi s4,s5,-1791
slt s1,s4,s5
beq s2,s2,rand_control_1179
addi s3,s3,1
rand_control_1179:
or s3,s4,s3
beq s5,s5,rand_control_1181
addi s2,s2,1
rand_control_1181:
sltu s5,s2,s4
srli s4,s3,19
add s4,s3,s2
bne s1,s1,rand_control_1185
addi s1,s1,1
rand_control_1185:
addi s4,s1,-1166
sub s3,s4,s1
srli s2,s2,30
slli s4,s4,5
or s5,s1,s1
xor s2,s3,s2
addi s5,s4,383
slli s1,s1,29
sll s4,s5,s5
ori s4,s3,799
xori s4,s2,-1290
slli s1,s3,21
xor s5,s1,s3
srl s3,s5,s3

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

