.option norvc
.section .text.init
.globl _start
_start:
la s0,scratch
li t0,0x90000000
li s1,3854938584
li s2,1458151247
li s3,352876094
li s4,1932594078
li s5,3897998759
srl s1,s3,s2
sub s1,s5,s5
xori s1,s5,-463
and s3,s4,s4
srli s1,s1,13
xor s3,s4,s4
or s4,s2,s1
or s1,s2,s4
srl s3,s4,s3
srli s5,s5,13
xori s1,s5,-1121
ori s3,s1,-781
srli s5,s1,26
beq s4,s4,rand_control_13
addi s4,s4,1
rand_control_13:
sub s1,s2,s1
slli s4,s5,31
xori s2,s3,-316
addi s4,s5,-1449
srl s3,s4,s4
ori s5,s3,-96
beq s2,s2,rand_control_20
addi s2,s2,1
rand_control_20:
srai s5,s1,9
beq s1,s1,rand_control_22
addi s1,s1,1
rand_control_22:
and s2,s5,s5
sll s3,s3,s1
andi s4,s2,1226
srl s3,s5,s3
srai s1,s2,30
sll s1,s5,s2
add s1,s5,s5
add s4,s5,s2
xori s1,s4,-1226
slli s2,s5,28
bne s2,s2,rand_control_33
addi s3,s3,1
rand_control_33:
add s1,s2,s5
sll s5,s4,s4
or s4,s5,s3
slt s3,s2,s4
xori s1,s5,-1382
srl s2,s3,s4
sltu s4,s5,s3
andi s1,s5,1526
srl s4,s4,s3
beq s4,s4,rand_control_43
addi s5,s5,1
rand_control_43:
sltu s3,s4,s2
addi s2,s4,1275
slli s3,s3,24
xor s3,s2,s5
srai s5,s5,0
or s3,s1,s4
add s5,s4,s1
xori s2,s2,1914
andi s1,s5,1143
srl s3,s4,s4
sltu s3,s2,s5
xori s1,s3,-1108
andi s4,s5,1702
srai s1,s5,2
sll s3,s1,s4
add s4,s4,s3
slli s1,s4,9
and s4,s5,s2
or s1,s3,s1
sll s4,s3,s4
sub s1,s3,s3
beq s4,s4,rand_control_65
addi s5,s5,1
rand_control_65:
addi s2,s3,1882
add s1,s4,s5
slt s1,s2,s1
xor s5,s2,s2
srli s5,s3,8
and s4,s2,s2
sltu s3,s2,s4
slli s3,s1,13
or s4,s2,s1
slli s3,s2,4
sll s1,s1,s1
srl s2,s3,s3
or s4,s3,s4
add s5,s5,s2
and s4,s5,s2
sltu s5,s4,s4
sll s5,s3,s2
or s4,s2,s5
slli s3,s5,25
slt s4,s3,s4
bne s2,s2,rand_control_86
addi s1,s1,1
rand_control_86:
slt s4,s5,s3
andi s3,s2,-588
or s2,s2,s5
xor s5,s2,s4
ori s2,s3,-1551
sll s2,s1,s4
xori s2,s2,510
andi s5,s1,789
addi s4,s1,147
addi s3,s5,-335
srai s3,s1,6
addi s3,s4,148
and s1,s4,s3
or s5,s4,s3
and s3,s4,s5
slt s5,s1,s5
beq s1,s1,rand_control_103
addi s5,s5,1
rand_control_103:
srai s3,s3,16
or s1,s4,s5
and s1,s2,s4
beq s3,s3,rand_control_107
addi s3,s3,1
rand_control_107:
srl s2,s1,s3
xor s2,s5,s5
srl s3,s2,s5
addi s5,s1,180
add s1,s2,s4
sll s5,s3,s1
slli s2,s2,12
bne s5,s5,rand_control_115
addi s3,s3,1
rand_control_115:
ori s1,s1,939
srai s1,s3,4
slli s5,s4,23
xor s5,s4,s3
sltu s1,s5,s3
bne s5,s5,rand_control_121
addi s2,s2,1
rand_control_121:
sub s3,s2,s4
xori s1,s3,-757
and s4,s4,s4
ori s3,s4,1069
or s4,s1,s5
sub s3,s2,s2
ori s3,s1,869
bne s5,s5,rand_control_129
addi s5,s5,1
rand_control_129:
addi s4,s2,-72
beq s2,s2,rand_control_131
addi s2,s2,1
rand_control_131:
and s2,s4,s3
andi s5,s5,1439
beq s5,s5,rand_control_134
addi s3,s3,1
rand_control_134:
srai s2,s2,29
ori s4,s2,865
andi s2,s3,-619
sll s2,s4,s4
xor s3,s3,s1
srl s3,s4,s3
srai s4,s4,17
sll s1,s4,s3
sub s3,s5,s2
slt s2,s5,s4
sub s1,s2,s5
bne s2,s2,rand_control_146
addi s1,s1,1
rand_control_146:
sll s4,s4,s1
bne s5,s5,rand_control_148
addi s4,s4,1
rand_control_148:
add s5,s5,s5
srai s5,s1,30
add s5,s4,s3
beq s4,s4,rand_control_152
addi s1,s1,1
rand_control_152:
andi s5,s5,1758
or s3,s4,s5
and s4,s4,s2
sltu s4,s4,s3
xori s5,s1,-1747
sub s4,s4,s1
srl s5,s2,s3
slt s4,s5,s2
ori s4,s4,-1178
srai s4,s5,3
ori s5,s5,1395
slt s5,s2,s3
srl s1,s1,s1
sltu s4,s4,s4
sltu s3,s4,s2
srli s5,s2,24
sll s2,s1,s4
beq s4,s4,rand_control_170
addi s1,s1,1
rand_control_170:
srl s2,s1,s4
xor s3,s3,s5
and s1,s1,s1
andi s4,s1,974
addi s1,s3,-436
slli s3,s5,7
bne s5,s5,rand_control_177
addi s2,s2,1
rand_control_177:
andi s2,s4,-767
beq s1,s1,rand_control_179
addi s2,s2,1
rand_control_179:
or s1,s4,s5
xor s1,s2,s2
and s5,s3,s2
srai s2,s2,27
bne s1,s1,rand_control_184
addi s1,s1,1
rand_control_184:
xori s2,s3,944
srli s2,s3,30
sll s3,s5,s4
srli s4,s3,5
add s3,s2,s5
sub s5,s2,s3
srli s2,s2,22
srli s1,s1,30
addi s5,s4,629
srai s4,s2,14
slt s4,s4,s4
or s5,s5,s5
xori s3,s2,1816
ori s3,s5,-1482
add s5,s2,s3
beq s3,s3,rand_control_200
addi s2,s2,1
rand_control_200:
or s3,s4,s1
and s3,s1,s3
slt s5,s4,s1
or s4,s2,s1
srli s3,s1,28
xor s1,s2,s1
xori s5,s5,-1212
or s3,s1,s3
andi s1,s1,1842
srli s2,s4,19
sltu s3,s2,s1
ori s2,s5,1949
sll s3,s2,s4
slli s5,s3,21
or s2,s4,s1
xori s5,s4,-132
xor s1,s5,s5
slt s4,s5,s2
srai s4,s1,2
sll s5,s1,s3
slt s2,s5,s1
sll s1,s2,s4
srai s5,s3,13
and s5,s1,s1
ori s4,s2,-820
srai s1,s3,8
xor s2,s3,s4
xor s2,s3,s5
sll s5,s3,s2
slli s1,s4,25
ori s3,s1,-831
and s5,s5,s5
add s2,s3,s2
andi s5,s5,-1794
or s4,s2,s4
srl s3,s5,s5
srai s2,s4,23
xori s5,s5,1616
add s5,s4,s2
beq s4,s4,rand_control_240
addi s5,s5,1
rand_control_240:
and s2,s1,s1
and s2,s3,s1
sll s4,s4,s5
srai s4,s2,1
srl s2,s3,s2
xori s4,s4,-1520
add s4,s3,s4
or s5,s5,s2
srli s2,s3,17
xor s4,s1,s5
xori s5,s5,-908
beq s4,s4,rand_control_252
addi s5,s5,1
rand_control_252:
slli s3,s5,3
and s5,s5,s3
addi s1,s2,40
bne s5,s5,rand_control_256
addi s3,s3,1
rand_control_256:
srl s4,s5,s5
andi s5,s1,514
slt s4,s3,s2
srl s2,s2,s2
andi s4,s4,999
srl s2,s2,s5
ori s5,s1,-957
beq s3,s3,rand_control_264
addi s2,s2,1
rand_control_264:
xori s1,s3,102
andi s3,s1,1721
andi s3,s2,1201
sltu s4,s4,s1
srai s2,s2,27
ori s1,s4,-1960
slli s2,s5,15
beq s3,s3,rand_control_272
addi s1,s1,1
rand_control_272:
andi s4,s3,76
xor s4,s3,s4
addi s5,s3,-1617
beq s1,s1,rand_control_276
addi s4,s4,1
rand_control_276:
xor s4,s1,s5
slli s5,s2,28
or s3,s1,s5
ori s2,s5,1001
sub s5,s1,s5
beq s3,s3,rand_control_282
addi s1,s1,1
rand_control_282:
slt s3,s1,s5
xori s2,s2,1998
srl s4,s3,s2
srai s2,s5,21
bne s5,s5,rand_control_287
addi s5,s5,1
rand_control_287:
and s1,s1,s3
srai s4,s1,27
sll s3,s5,s2
sltu s1,s4,s2
sll s1,s4,s5
xori s3,s4,1563
xor s4,s5,s1
ori s1,s5,-1370
and s1,s5,s5
slt s1,s5,s2
bne s5,s5,rand_control_298
addi s3,s3,1
rand_control_298:
srli s3,s5,20
andi s2,s4,-200
srai s5,s1,29
srli s3,s4,8
addi s3,s2,-921
srai s2,s3,21
add s1,s4,s4
slli s3,s2,20
srli s4,s4,1
sltu s5,s3,s3
bne s2,s2,rand_control_309
addi s3,s3,1
rand_control_309:
bne s3,s3,rand_control_310
addi s5,s5,1
rand_control_310:
bne s5,s5,rand_control_311
addi s5,s5,1
rand_control_311:
sll s4,s5,s4
andi s4,s3,570
slt s4,s2,s2
beq s3,s3,rand_control_315
addi s2,s2,1
rand_control_315:
srli s5,s2,9
ori s4,s4,1159
srai s2,s4,29
slt s3,s4,s2
slli s2,s5,20
srai s1,s5,13
slt s4,s4,s2
srli s5,s3,21
and s3,s5,s3
xor s3,s3,s4
beq s3,s3,rand_control_326
addi s2,s2,1
rand_control_326:
slli s3,s4,13
sltu s5,s3,s2
or s5,s4,s4
add s4,s2,s3
srl s5,s3,s5
xori s4,s5,-26
or s5,s4,s2
slli s3,s2,14
sub s3,s2,s1
add s2,s1,s4
beq s2,s2,rand_control_337
addi s4,s4,1
rand_control_337:
add s3,s2,s4
slli s2,s5,26
beq s5,s5,rand_control_340
addi s2,s2,1
rand_control_340:
sub s3,s4,s1
slli s2,s3,15
sltu s3,s4,s1
or s4,s5,s4
beq s4,s4,rand_control_345
addi s3,s3,1
rand_control_345:
srai s1,s3,8
andi s4,s5,984
andi s4,s2,-1435
xori s5,s3,-363
bne s3,s3,rand_control_350
addi s3,s3,1
rand_control_350:
andi s2,s2,-1498
slt s1,s5,s2
beq s1,s1,rand_control_353
addi s5,s5,1
rand_control_353:
andi s2,s4,391
add s1,s1,s3
beq s5,s5,rand_control_356
addi s2,s2,1
rand_control_356:
sll s5,s4,s4
srli s1,s1,2
addi s2,s5,-133
andi s2,s1,1598
andi s5,s1,1
srl s4,s2,s5
xori s5,s5,1916
and s4,s4,s2
srl s3,s1,s1
srl s1,s1,s3
and s2,s1,s3
xor s1,s5,s5
add s5,s5,s1
and s5,s4,s4
beq s3,s3,rand_control_371
addi s4,s4,1
rand_control_371:
add s4,s5,s3
or s3,s5,s1
slli s1,s3,11
sltu s2,s2,s3
srl s3,s5,s4
slt s5,s4,s3
sub s1,s4,s5
sll s5,s5,s5
xor s5,s4,s2
sltu s5,s4,s2
srl s1,s1,s5
srl s3,s5,s5
srli s1,s4,2
beq s4,s4,rand_control_385
addi s1,s1,1
rand_control_385:
sub s4,s3,s4
or s3,s1,s1
slli s3,s4,30
beq s2,s2,rand_control_389
addi s4,s4,1
rand_control_389:
slli s5,s5,28
slt s5,s2,s1
ori s4,s1,780
xor s4,s5,s5
andi s3,s2,-817
slli s5,s2,5
sll s5,s1,s5
or s3,s3,s3
addi s2,s2,-2012
slli s4,s2,14
bne s3,s3,rand_control_400
addi s2,s2,1
rand_control_400:
sltu s5,s2,s4
bne s2,s2,rand_control_402
addi s3,s3,1
rand_control_402:
srli s5,s1,2
add s5,s4,s3
slli s4,s1,4
srai s3,s4,22
ori s5,s1,613
xor s4,s2,s3
sub s3,s3,s2
andi s4,s3,341
add s4,s1,s1
srli s2,s2,2
andi s1,s5,1942
andi s2,s5,1625
bne s2,s2,rand_control_415
addi s3,s3,1
rand_control_415:
bne s2,s2,rand_control_416
addi s5,s5,1
rand_control_416:
sll s5,s2,s1
bne s1,s1,rand_control_418
addi s3,s3,1
rand_control_418:
add s2,s2,s3
beq s5,s5,rand_control_420
addi s4,s4,1
rand_control_420:
sltu s1,s4,s3
srai s4,s2,14
add s1,s4,s2
andi s1,s2,1960
xor s1,s5,s4
beq s5,s5,rand_control_426
addi s4,s4,1
rand_control_426:
xori s3,s3,-1209
bne s3,s3,rand_control_428
addi s1,s1,1
rand_control_428:
ori s4,s2,-567
xor s5,s1,s4
sub s2,s1,s5
ori s3,s2,1065
srli s5,s5,21
andi s5,s5,1829
ori s4,s4,644
slt s3,s5,s5
andi s1,s5,2007
slt s2,s4,s1
andi s2,s4,-354
srl s1,s5,s5
slli s5,s1,31
add s1,s2,s4
srli s4,s2,5
beq s2,s2,rand_control_444
addi s2,s2,1
rand_control_444:
or s2,s1,s5
addi s5,s4,591
and s5,s3,s1
xori s4,s2,884
beq s5,s5,rand_control_449
addi s2,s2,1
rand_control_449:
slli s3,s5,11
addi s2,s2,558
andi s2,s5,445
slli s2,s4,19
add s4,s3,s5
slli s5,s3,14
xori s2,s2,-792
andi s1,s4,-1986
beq s2,s2,rand_control_458
addi s2,s2,1
rand_control_458:
sltu s2,s1,s4
srli s4,s1,19
add s2,s3,s2
slli s3,s5,13
xor s3,s1,s1
sub s1,s1,s4
sub s5,s5,s3
sltu s5,s5,s3
ori s5,s1,-951
slt s3,s1,s2
and s4,s3,s4
andi s3,s4,976
addi s4,s1,-913
srli s4,s5,23
sub s2,s5,s3
srai s2,s3,17
xori s4,s4,-220
addi s2,s5,-484
sub s5,s4,s4
beq s3,s3,rand_control_478
addi s1,s1,1
rand_control_478:
bne s5,s5,rand_control_479
addi s4,s4,1
rand_control_479:
xor s4,s1,s1
slli s1,s2,4
srl s1,s5,s3
add s2,s5,s5
ori s2,s2,-1254
bne s1,s1,rand_control_485
addi s5,s5,1
rand_control_485:
and s2,s4,s3
beq s5,s5,rand_control_487
addi s2,s2,1
rand_control_487:
sll s5,s3,s1
xor s3,s3,s4
or s3,s5,s2
slli s4,s5,31
slli s3,s2,27
addi s2,s5,1217
xori s4,s5,745
srai s5,s3,16
or s4,s3,s5
add s2,s2,s2
sltu s1,s2,s5
bne s2,s2,rand_control_499
addi s4,s4,1
rand_control_499:
or s2,s1,s4
srai s5,s3,10
andi s1,s5,-1628
xori s3,s4,294
sltu s4,s3,s1
slli s4,s4,12
sll s3,s1,s1
srli s4,s4,22
beq s2,s2,rand_control_508
addi s2,s2,1
rand_control_508:
or s2,s3,s2
xor s2,s4,s5
bne s5,s5,rand_control_511
addi s2,s2,1
rand_control_511:
srl s4,s1,s2
or s3,s5,s1
sltu s3,s4,s3
or s2,s5,s3
slli s1,s1,30
sll s4,s4,s4
sub s1,s3,s4
sltu s4,s3,s3
srli s2,s5,28
and s5,s3,s5
xori s1,s5,-1111
srli s5,s3,14
and s4,s2,s3
beq s1,s1,rand_control_525
addi s3,s3,1
rand_control_525:
andi s3,s3,-1988
xori s2,s2,-1852
ori s5,s1,467
srai s2,s5,15
srl s1,s4,s5
srai s1,s3,28
xori s4,s2,2040
srl s4,s2,s5
beq s4,s4,rand_control_534
addi s1,s1,1
rand_control_534:
srli s4,s1,25
slli s3,s3,13
xori s3,s1,-237
beq s2,s2,rand_control_538
addi s5,s5,1
rand_control_538:
slli s5,s1,8
and s4,s3,s2
srl s5,s1,s5
and s4,s5,s1
slt s1,s5,s3
slt s1,s2,s3
bne s2,s2,rand_control_545
addi s3,s3,1
rand_control_545:
sll s4,s5,s3
slt s2,s3,s3
slli s5,s2,29
sub s5,s2,s2
slt s2,s2,s2
bne s1,s1,rand_control_551
addi s3,s3,1
rand_control_551:
srl s1,s1,s2
andi s2,s5,1860
beq s3,s3,rand_control_554
addi s4,s4,1
rand_control_554:
sltu s3,s3,s2
srai s4,s5,25
xor s4,s1,s2
bne s5,s5,rand_control_558
addi s3,s3,1
rand_control_558:
slli s2,s2,27
slt s5,s5,s3
sll s3,s4,s4
xori s1,s4,-1656
srai s4,s1,12
xori s4,s2,-1575
xori s4,s3,-46
sub s1,s3,s5
ori s5,s1,846
slli s2,s5,18
sltu s5,s3,s5
xor s1,s4,s4
addi s4,s3,-1417
addi s5,s3,1330
add s5,s5,s4
ori s2,s4,-1831
sub s4,s2,s1
slli s2,s2,10
bne s4,s4,rand_control_577
addi s1,s1,1
rand_control_577:
sub s5,s1,s2
xori s2,s2,-1523
xor s2,s3,s4
andi s5,s4,1909
ori s4,s3,-1230
srli s5,s1,0
or s5,s2,s5
sub s4,s3,s2
xori s2,s3,-1741
sll s4,s2,s4
slli s2,s2,26
sll s4,s4,s3
addi s5,s4,-642
srli s2,s4,30
srl s3,s3,s5
srl s1,s1,s2
sub s3,s4,s2
sub s1,s1,s1
sltu s2,s5,s2
sub s5,s3,s1
sll s2,s3,s2
srl s4,s4,s2
add s3,s3,s4
slt s3,s3,s1
addi s3,s5,-872
or s1,s4,s3
sltu s1,s1,s4
sltu s3,s2,s4
and s3,s4,s1
sll s5,s3,s2
addi s3,s4,-1417
bne s2,s2,rand_control_609
addi s5,s5,1
rand_control_609:
andi s4,s3,-560
or s5,s2,s3
xor s1,s5,s5
slli s4,s1,21
bne s1,s1,rand_control_614
addi s4,s4,1
rand_control_614:
beq s3,s3,rand_control_615
addi s4,s4,1
rand_control_615:
xori s3,s3,-398
srai s4,s2,12
sub s1,s2,s4
and s1,s2,s4
or s3,s2,s2
addi s4,s4,1877
bne s5,s5,rand_control_622
addi s2,s2,1
rand_control_622:
ori s2,s1,106
xor s1,s2,s4
or s2,s2,s1
xor s2,s2,s3
slli s3,s2,22
addi s1,s5,-343
or s2,s4,s1
or s3,s2,s4
add s2,s1,s4
or s3,s2,s1
xor s5,s3,s2
slli s4,s2,16
or s1,s5,s4
slt s4,s5,s1
srai s4,s5,7
or s3,s5,s2
slli s4,s2,17
xor s4,s3,s5
slt s4,s5,s1
xori s1,s1,-690
slli s3,s5,20
sltu s1,s2,s5
beq s1,s1,rand_control_645
addi s1,s1,1
rand_control_645:
beq s5,s5,rand_control_646
addi s4,s4,1
rand_control_646:
beq s3,s3,rand_control_647
addi s1,s1,1
rand_control_647:
beq s3,s3,rand_control_648
addi s2,s2,1
rand_control_648:
slt s5,s3,s5
slli s2,s1,9
bne s2,s2,rand_control_651
addi s4,s4,1
rand_control_651:
sub s3,s5,s5
slt s2,s2,s4
srl s1,s2,s3
srli s1,s5,26
srl s2,s1,s3
xori s5,s3,1757
srli s2,s5,25
beq s3,s3,rand_control_659
addi s5,s5,1
rand_control_659:
srai s2,s1,12
addi s3,s3,915
andi s5,s5,-1862
slli s2,s4,28
sll s4,s2,s4
slli s5,s2,16
ori s1,s5,-760
sll s5,s1,s2
beq s2,s2,rand_control_668
addi s4,s4,1
rand_control_668:
xori s2,s1,-2015
xori s5,s1,-1669
srl s3,s4,s2
andi s4,s2,1016
sll s2,s3,s2
sub s4,s1,s3
srli s2,s4,8
xor s1,s3,s1
sltu s1,s3,s1
srai s2,s5,28
addi s1,s2,1905
srli s2,s5,2
bne s4,s4,rand_control_681
addi s4,s4,1
rand_control_681:
slli s3,s3,14
sub s1,s1,s4
add s1,s3,s2
srai s5,s2,2
srai s1,s3,1
addi s2,s5,-621
or s5,s3,s2
slt s5,s1,s5
addi s5,s3,-1997
srli s5,s3,1
slt s5,s5,s3
or s2,s1,s1
sltu s2,s3,s3
sll s1,s1,s1
bne s2,s2,rand_control_696
addi s1,s1,1
rand_control_696:
beq s5,s5,rand_control_697
addi s4,s4,1
rand_control_697:
and s5,s2,s3
beq s4,s4,rand_control_699
addi s1,s1,1
rand_control_699:
srli s2,s2,2
xor s1,s3,s4
slli s3,s5,11
srli s4,s4,15
andi s5,s5,854
add s2,s2,s4
ori s3,s5,423
slt s3,s4,s2
slli s4,s1,31
sltu s5,s3,s1
xor s5,s4,s3
sub s2,s2,s1
slli s4,s5,8
srl s4,s4,s1
slli s1,s1,26
slt s2,s5,s5
bne s4,s4,rand_control_716
addi s2,s2,1
rand_control_716:
slt s1,s1,s5
add s3,s5,s1
srai s4,s3,6
addi s4,s3,-2037
or s1,s4,s2
or s4,s4,s5
sub s1,s5,s1
srl s1,s4,s3
add s3,s5,s3
and s3,s3,s3
or s3,s4,s5
slli s5,s4,23
bne s5,s5,rand_control_729
addi s3,s3,1
rand_control_729:
srli s4,s4,3
slli s1,s2,5
srli s5,s4,18
sll s3,s3,s3
beq s1,s1,rand_control_734
addi s5,s5,1
rand_control_734:
sub s5,s2,s5
add s3,s4,s3
sub s4,s1,s4
add s1,s5,s5
xor s2,s1,s4
slli s2,s2,20
slli s3,s5,8
bne s4,s4,rand_control_742
addi s3,s3,1
rand_control_742:
sub s2,s1,s2
ori s3,s2,111
sltu s3,s1,s3
addi s2,s2,-126
add s1,s1,s4
sub s3,s3,s5
ori s4,s1,-390
addi s4,s2,-1197
and s1,s1,s1
sltu s4,s1,s3
sll s4,s4,s5
srai s3,s2,30
xori s1,s3,592
srai s2,s1,29
addi s1,s1,-1658
ori s3,s3,-1657
sub s1,s5,s1
srli s4,s1,6
ori s1,s3,442
sub s1,s1,s5
or s5,s1,s4
bne s3,s3,rand_control_764
addi s1,s1,1
rand_control_764:
sub s5,s2,s1
srl s1,s5,s4
addi s4,s5,1969
slli s5,s4,25
sll s3,s2,s4
sltu s4,s4,s5
sll s5,s3,s3
slli s4,s2,26
addi s3,s2,1412
add s1,s1,s1
xor s2,s3,s4
srli s1,s5,13
sll s1,s4,s4
srai s4,s3,4
andi s4,s1,-1139
xor s3,s1,s2
ori s3,s3,-1367
andi s5,s3,-793
xor s5,s1,s3
sltu s3,s4,s3
sll s5,s4,s3
sltu s1,s1,s2
and s5,s4,s2
addi s1,s1,-1924
add s5,s4,s3
and s4,s4,s2
xor s2,s2,s4
xor s1,s3,s4
slt s3,s5,s4
and s3,s3,s3
srai s5,s4,10
slt s4,s5,s1
srai s1,s4,11
sll s3,s5,s5
sll s3,s3,s3
add s2,s1,s1
add s4,s1,s5
sll s4,s2,s1
xor s2,s4,s2
srli s4,s2,3
srl s5,s4,s5
add s3,s2,s2
and s3,s2,s4
addi s5,s4,-942
sll s4,s3,s4
add s4,s4,s2
srli s5,s2,12
srai s2,s3,30
srai s4,s3,7
sltu s5,s4,s2
xori s3,s2,565
sll s3,s4,s3
sltu s2,s5,s1
sll s5,s5,s5
addi s3,s4,737
beq s5,s5,rand_control_820
addi s5,s5,1
rand_control_820:
slli s2,s4,28
sll s3,s4,s1
slli s1,s4,13
beq s5,s5,rand_control_824
addi s4,s4,1
rand_control_824:
add s4,s5,s4
srli s4,s5,31
srai s2,s5,10
sltu s4,s3,s4
xori s4,s5,-157
srli s1,s3,29
sll s1,s3,s5
addi s5,s4,-1857
sll s5,s3,s3
srl s3,s2,s4
or s4,s2,s4
slli s4,s5,25
slt s5,s5,s2
sltu s5,s5,s1
srli s5,s2,21
xori s3,s1,-626
slli s2,s4,22
srai s2,s3,7
bne s2,s2,rand_control_843
addi s5,s5,1
rand_control_843:
bne s1,s1,rand_control_844
addi s4,s4,1
rand_control_844:
ori s5,s2,-678
xori s4,s3,-1557
slli s4,s2,16
add s4,s5,s2
srl s5,s5,s2
sll s3,s3,s5
sll s5,s3,s5
addi s1,s5,677
sll s3,s5,s1
and s3,s3,s3
sll s3,s3,s3
sll s5,s1,s1
xor s5,s3,s4
beq s1,s1,rand_control_858
addi s2,s2,1
rand_control_858:
and s5,s2,s1
srl s5,s5,s5
beq s4,s4,rand_control_861
addi s1,s1,1
rand_control_861:
add s4,s5,s1
ori s3,s3,-969
sll s4,s1,s3
sub s2,s1,s1
sltu s4,s1,s4
sll s3,s4,s2
andi s4,s3,385
andi s5,s3,1205
srli s3,s1,21
bne s1,s1,rand_control_871
addi s4,s4,1
rand_control_871:
srli s4,s5,0
bne s5,s5,rand_control_873
addi s3,s3,1
rand_control_873:
beq s1,s1,rand_control_874
addi s2,s2,1
rand_control_874:
beq s1,s1,rand_control_875
addi s5,s5,1
rand_control_875:
ori s4,s4,-1669
sub s5,s4,s3
addi s2,s2,269
xor s1,s4,s3
slli s5,s3,17
or s3,s3,s5
sltu s4,s1,s5
srli s5,s3,10
bne s5,s5,rand_control_884
addi s5,s5,1
rand_control_884:
bne s4,s4,rand_control_885
addi s1,s1,1
rand_control_885:
sltu s2,s3,s5
sub s5,s4,s4
add s3,s4,s4
sub s1,s5,s5
and s5,s5,s5
bne s3,s3,rand_control_891
addi s5,s5,1
rand_control_891:
ori s1,s2,1183
srl s2,s1,s2
add s4,s2,s3
srl s5,s1,s4
and s5,s3,s1
srl s1,s3,s1
xori s5,s1,-1966
sltu s3,s5,s1
sltu s3,s1,s4
bne s3,s3,rand_control_901
addi s4,s4,1
rand_control_901:
bne s5,s5,rand_control_902
addi s1,s1,1
rand_control_902:
sll s5,s5,s4
srai s3,s2,17
srli s3,s1,17
or s5,s3,s3
and s1,s1,s5
add s4,s5,s4
slli s4,s2,11
or s4,s1,s3
sll s1,s1,s4
srl s5,s2,s2
srai s5,s2,14
addi s5,s1,259
sll s3,s5,s3
srl s1,s5,s1
bne s5,s5,rand_control_917
addi s1,s1,1
rand_control_917:
srli s2,s2,17
ori s3,s4,-1904
xor s3,s2,s4
bne s3,s3,rand_control_921
addi s2,s2,1
rand_control_921:
add s3,s4,s4
sub s1,s3,s2
ori s2,s5,-17
sub s2,s3,s1
bne s3,s3,rand_control_926
addi s4,s4,1
rand_control_926:
and s5,s3,s5
ori s4,s5,412
beq s2,s2,rand_control_929
addi s2,s2,1
rand_control_929:
srl s4,s5,s3
srli s4,s1,21
and s3,s2,s2
sub s3,s1,s2
xor s3,s2,s5
xor s1,s5,s2
xor s3,s2,s4
srai s4,s5,28
bne s1,s1,rand_control_938
addi s4,s4,1
rand_control_938:
xori s1,s5,514
andi s5,s5,-1574
srai s3,s3,25
and s4,s1,s3
andi s4,s4,-347
slt s4,s1,s2
beq s3,s3,rand_control_945
addi s4,s4,1
rand_control_945:
add s4,s4,s5
sltu s2,s1,s4
sub s4,s3,s1
srl s3,s3,s1
and s1,s2,s2
srai s1,s3,21
srai s2,s1,28
addi s1,s3,-1526
slli s5,s1,13
xori s5,s1,1980
and s5,s3,s3
sub s2,s1,s1
srl s4,s2,s2
beq s4,s4,rand_control_959
addi s4,s4,1
rand_control_959:
slli s4,s1,9
bne s2,s2,rand_control_961
addi s1,s1,1
rand_control_961:
bne s2,s2,rand_control_962
addi s5,s5,1
rand_control_962:
sltu s5,s1,s4
addi s1,s3,-334
or s2,s3,s1
srli s5,s2,6
sub s5,s4,s2
andi s3,s4,1261
addi s1,s5,38
addi s3,s5,1117
ori s5,s5,-967
andi s5,s3,-1647
srl s1,s3,s1
bne s5,s5,rand_control_974
addi s1,s1,1
rand_control_974:
addi s2,s2,-1610
sltu s3,s1,s2
andi s1,s4,-678
ori s4,s1,-943
beq s4,s4,rand_control_979
addi s5,s5,1
rand_control_979:
ori s5,s2,1620
xori s3,s2,1389
slt s2,s3,s3
add s3,s1,s2
ori s5,s3,-1046
sub s3,s3,s2
addi s4,s4,1109
add s5,s3,s5
addi s4,s4,920
srl s1,s5,s2
ori s5,s5,1995
sll s1,s3,s4
sll s3,s1,s1
slt s4,s3,s4
slli s1,s5,18
sltu s1,s4,s2
and s5,s1,s1
add s1,s5,s5
and s1,s5,s3
bne s4,s4,rand_control_999
addi s4,s4,1
rand_control_999:
sll s5,s2,s1
slt s3,s1,s3
srli s2,s3,17
bne s1,s1,rand_control_1003
addi s4,s4,1
rand_control_1003:
srai s2,s1,26
xor s5,s5,s3
xori s4,s5,-460
sltu s5,s5,s2
bne s4,s4,rand_control_1008
addi s4,s4,1
rand_control_1008:
beq s5,s5,rand_control_1009
addi s4,s4,1
rand_control_1009:
srai s2,s1,27
slli s3,s2,22
bne s1,s1,rand_control_1012
addi s5,s5,1
rand_control_1012:
srai s2,s5,12
or s1,s5,s4
bne s5,s5,rand_control_1015
addi s2,s2,1
rand_control_1015:
srl s1,s3,s1
bne s3,s3,rand_control_1017
addi s4,s4,1
rand_control_1017:
sltu s5,s3,s4
xori s4,s5,1047
xor s5,s1,s4
ori s2,s1,47
srli s5,s5,9
ori s1,s3,683
addi s2,s3,-73
ori s3,s1,-1482
slli s5,s3,22
xor s3,s3,s2
sub s2,s1,s1
xor s2,s2,s1
and s1,s1,s4
xori s1,s1,830
sltu s1,s5,s4
slt s1,s3,s2
add s1,s4,s5
xori s3,s1,1825
sltu s2,s2,s5
ori s3,s4,104
slt s4,s3,s5
beq s3,s3,rand_control_1039
addi s3,s3,1
rand_control_1039:
xori s1,s3,374
bne s4,s4,rand_control_1041
addi s5,s5,1
rand_control_1041:
sub s5,s2,s2
andi s4,s4,-1749
srai s4,s5,20
ori s1,s4,-726
bne s3,s3,rand_control_1046
addi s3,s3,1
rand_control_1046:
andi s2,s1,-401
bne s1,s1,rand_control_1048
addi s2,s2,1
rand_control_1048:
add s3,s3,s4
slt s4,s1,s1
andi s2,s4,-1818
add s4,s4,s1
srai s3,s4,1
sltu s5,s4,s1
addi s2,s2,322
beq s2,s2,rand_control_1056
addi s2,s2,1
rand_control_1056:
bne s2,s2,rand_control_1057
addi s2,s2,1
rand_control_1057:
addi s3,s4,632
andi s5,s4,-1900
bne s2,s2,rand_control_1060
addi s1,s1,1
rand_control_1060:
ori s5,s1,1679
slli s2,s3,22
xor s3,s2,s3
slli s4,s4,7
srl s2,s3,s3
bne s3,s3,rand_control_1066
addi s1,s1,1
rand_control_1066:
addi s4,s3,1842
slli s5,s2,24
srai s1,s4,28
xor s2,s5,s3
srli s1,s3,14
addi s3,s5,-1956
beq s4,s4,rand_control_1073
addi s5,s5,1
rand_control_1073:
addi s5,s1,-1920
andi s3,s3,-309
xor s3,s2,s4
andi s3,s3,-625
sub s2,s1,s4
sltu s5,s3,s3
xor s2,s5,s4
beq s5,s5,rand_control_1081
addi s2,s2,1
rand_control_1081:
ori s3,s1,-1591
ori s2,s5,936
or s5,s3,s1
srli s1,s2,4
addi s5,s1,511
andi s2,s4,-263
srl s4,s3,s5
or s5,s1,s1
xor s2,s2,s3
or s1,s3,s2
sub s2,s5,s4
srai s5,s1,12
xori s2,s3,1985
sll s1,s2,s2
add s5,s1,s4
beq s2,s2,rand_control_1097
addi s1,s1,1
rand_control_1097:
addi s3,s5,307
srli s2,s5,22
slt s2,s1,s3
andi s1,s1,2035
addi s2,s2,1894
andi s4,s3,-1392
or s2,s5,s5
sll s1,s3,s2
slt s2,s5,s3
and s1,s1,s4
sltu s4,s3,s5
srai s5,s3,28
ori s3,s4,-1321
add s5,s1,s5
slli s3,s1,1
slli s5,s1,1
slt s1,s5,s3
srli s3,s2,16
slli s3,s5,16
and s5,s3,s3
slt s2,s5,s1
sll s1,s2,s3
slt s1,s3,s2
srl s2,s2,s3
or s2,s1,s1
or s3,s4,s2
addi s2,s4,-150
or s4,s2,s1
beq s4,s4,rand_control_1126
addi s5,s5,1
rand_control_1126:
srai s4,s2,3
beq s5,s5,rand_control_1128
addi s1,s1,1
rand_control_1128:
addi s4,s4,977
srli s3,s5,11
ori s1,s4,839
or s4,s4,s5
beq s5,s5,rand_control_1133
addi s4,s4,1
rand_control_1133:
srl s4,s1,s3
beq s4,s4,rand_control_1135
addi s1,s1,1
rand_control_1135:
sll s5,s5,s5
srli s4,s1,22
ori s2,s4,-653
xor s3,s5,s1
srai s1,s4,27
andi s5,s3,628
srl s5,s3,s3
andi s2,s1,-14
bne s1,s1,rand_control_1144
addi s3,s3,1
rand_control_1144:
slt s1,s4,s3
and s5,s1,s4
beq s3,s3,rand_control_1147
addi s5,s5,1
rand_control_1147:
sub s4,s4,s1
srl s4,s1,s2
addi s5,s3,247
sltu s3,s4,s1
slli s5,s2,13
bne s1,s1,rand_control_1153
addi s2,s2,1
rand_control_1153:
ori s2,s5,1025
srli s1,s2,8
sltu s2,s5,s5
slt s4,s5,s1
or s3,s5,s5
and s5,s2,s1
add s1,s4,s2
and s2,s5,s2
bne s3,s3,rand_control_1162
addi s4,s4,1
rand_control_1162:
add s5,s1,s3
slli s3,s1,27
sll s1,s1,s2
ori s1,s1,-545
sub s5,s2,s5
add s5,s3,s5
ori s5,s4,1850
srli s2,s2,26
sll s2,s1,s4
addi s5,s1,-288
and s3,s2,s1
sub s3,s2,s4
sltu s5,s1,s2
ori s3,s2,-636
andi s2,s1,903
add s4,s3,s2
or s2,s1,s1
bne s3,s3,rand_control_1180
addi s2,s2,1
rand_control_1180:
add s4,s5,s3
xor s5,s3,s4
srai s5,s4,26
srl s2,s2,s3
srai s5,s4,0
xori s4,s3,1129
sub s5,s1,s4
add s3,s2,s3
beq s4,s4,rand_control_1189
addi s4,s4,1
rand_control_1189:
srl s5,s5,s5
slt s5,s3,s4
add s1,s5,s4
andi s3,s3,205
xor s1,s5,s5
andi s2,s3,-979
beq s1,s1,rand_control_1196
addi s3,s3,1
rand_control_1196:
srli s4,s5,23
bne s3,s3,rand_control_1198
addi s4,s4,1
rand_control_1198:
srli s5,s4,10

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

