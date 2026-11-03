.option norvc
.section .text.init
.globl _start
_start:
la s0,scratch
li t0,0x90000000
li s1,668327527
li s2,2049431908
li s3,829964545
li s4,4258732747
li s5,121516401
beq s5,s5,rand_control_0
addi s4,s4,1
rand_control_0:
xori s5,s3,-1513
sll s2,s5,s5
sub s3,s1,s5
sll s4,s5,s1
xor s2,s5,s1
andi s1,s4,-1504
bne s2,s2,rand_control_7
addi s1,s1,1
rand_control_7:
or s1,s2,s5
andi s4,s5,1624
or s3,s3,s5
srai s4,s3,14
slli s5,s3,16
sub s3,s2,s3
slli s1,s5,17
addi s3,s1,661
or s1,s2,s1
beq s3,s3,rand_control_17
addi s1,s1,1
rand_control_17:
ori s1,s3,345
srai s5,s2,25
sll s2,s1,s1
or s4,s2,s2
srli s1,s2,31
sll s2,s1,s5
add s3,s1,s5
add s4,s1,s2
xor s3,s2,s3
andi s1,s5,1480
and s5,s2,s2
andi s3,s2,1182
slli s4,s3,26
ori s3,s3,1419
xor s4,s3,s4
bne s1,s1,rand_control_33
addi s5,s5,1
rand_control_33:
or s1,s2,s1
or s5,s2,s5
slt s4,s3,s1
xor s5,s3,s1
xori s5,s4,1653
srai s5,s5,21
srli s4,s2,7
xor s2,s1,s2
xor s5,s2,s5
slli s1,s5,7
xor s2,s4,s2
add s5,s4,s3
or s1,s2,s5
slli s4,s4,20
srai s3,s1,24
addi s3,s3,-1755
or s5,s4,s1
sub s2,s5,s5
slli s3,s5,17
sltu s2,s5,s4
add s3,s2,s2
sub s5,s2,s5
beq s4,s4,rand_control_56
addi s3,s3,1
rand_control_56:
xor s2,s4,s5
sll s1,s5,s3
srl s4,s4,s4
sll s2,s2,s2
xor s4,s3,s4
xor s5,s2,s5
ori s4,s1,-1258
srl s1,s3,s3
or s2,s2,s5
srl s1,s4,s4
and s5,s3,s1
srai s3,s4,24
sltu s3,s1,s4
sltu s3,s2,s3
ori s3,s3,1450
slt s3,s5,s1
slt s2,s5,s3
andi s3,s2,-587
and s4,s2,s5
beq s1,s1,rand_control_76
addi s4,s4,1
rand_control_76:
or s2,s1,s3
xori s4,s2,-344
srli s1,s3,14
xor s2,s1,s4
srai s1,s2,19
srai s1,s5,28
slli s2,s4,13
beq s4,s4,rand_control_84
addi s3,s3,1
rand_control_84:
xor s5,s2,s3
srl s1,s5,s4
srl s1,s2,s1
sll s1,s2,s5
bne s1,s1,rand_control_89
addi s5,s5,1
rand_control_89:
srl s4,s3,s3
slt s2,s1,s4
ori s4,s4,-239
andi s4,s5,-990
andi s1,s5,1963
sltu s3,s5,s5
slt s4,s4,s4
xori s5,s2,-1931
srli s5,s4,6
xori s5,s3,-292
andi s1,s3,-642
sub s2,s4,s4
addi s4,s5,-1324
beq s4,s4,rand_control_103
addi s3,s3,1
rand_control_103:
and s1,s3,s2
and s2,s4,s3
and s3,s2,s5
sltu s4,s4,s2
addi s2,s1,492
xor s2,s2,s2
srl s3,s2,s3
sltu s3,s4,s4
slli s3,s1,19
slli s4,s3,6
xori s2,s1,176
sub s2,s5,s1
or s4,s2,s2
add s1,s4,s1
or s2,s5,s3
sub s4,s4,s5
sub s2,s4,s3
add s1,s4,s3
addi s3,s3,398
srai s5,s5,21
andi s1,s5,925
beq s3,s3,rand_control_125
addi s4,s4,1
rand_control_125:
or s1,s5,s4
addi s3,s2,1297
xor s4,s3,s2
xori s4,s1,-1232
xori s3,s4,-1677
xori s2,s5,-785
sltu s3,s3,s5
srl s4,s5,s4
xori s1,s2,1400
srli s5,s1,10
slt s1,s2,s5
beq s1,s1,rand_control_137
addi s3,s3,1
rand_control_137:
beq s5,s5,rand_control_138
addi s3,s3,1
rand_control_138:
add s2,s5,s2
andi s3,s4,1297
srli s3,s4,25
beq s4,s4,rand_control_142
addi s4,s4,1
rand_control_142:
sub s3,s3,s5
srli s3,s3,16
add s5,s5,s1
beq s4,s4,rand_control_146
addi s1,s1,1
rand_control_146:
slli s2,s2,27
srli s4,s3,7
slt s1,s4,s1
add s2,s3,s5
beq s4,s4,rand_control_151
addi s1,s1,1
rand_control_151:
addi s4,s5,676
sub s1,s1,s5
sltu s1,s4,s4
sub s5,s5,s3
srl s3,s3,s4
sll s3,s1,s1
sll s4,s3,s2
srai s1,s2,14
and s3,s1,s2
andi s4,s1,1502
ori s5,s5,-1103
sltu s2,s1,s5
sub s3,s3,s1
sub s3,s3,s3
sltu s2,s2,s3
slt s4,s3,s5
ori s2,s5,-825
srli s5,s5,13
and s3,s5,s3
beq s2,s2,rand_control_171
addi s2,s2,1
rand_control_171:
beq s3,s3,rand_control_172
addi s2,s2,1
rand_control_172:
srli s2,s1,10
bne s5,s5,rand_control_174
addi s5,s5,1
rand_control_174:
and s5,s1,s2
andi s3,s4,417
srai s5,s1,31
addi s3,s4,-266
srai s5,s4,22
sltu s5,s2,s4
slli s2,s4,28
srli s4,s4,16
srl s2,s1,s4
xor s4,s4,s1
or s2,s1,s2
srl s4,s2,s3
bne s3,s3,rand_control_187
addi s1,s1,1
rand_control_187:
addi s2,s5,1407
add s1,s5,s5
bne s5,s5,rand_control_190
addi s2,s2,1
rand_control_190:
sub s3,s1,s5
beq s4,s4,rand_control_192
addi s4,s4,1
rand_control_192:
sub s3,s2,s1
and s4,s5,s2
srli s5,s4,28
bne s1,s1,rand_control_196
addi s3,s3,1
rand_control_196:
andi s5,s4,-1181
slli s3,s1,29
srl s4,s3,s4
sltu s5,s3,s4
addi s4,s2,-1381
sltu s4,s1,s5
srl s2,s5,s4
srl s1,s3,s4
sltu s1,s3,s1
andi s2,s3,-947
sub s2,s2,s4
ori s1,s5,1313
srli s5,s4,0
sltu s4,s1,s4
sll s1,s1,s2
srai s3,s1,5
and s3,s2,s4
srli s4,s3,6
srai s2,s1,6
andi s1,s3,995
xori s3,s2,1768
srai s3,s2,27
srli s3,s3,21
sltu s1,s5,s5
srai s1,s2,21
beq s1,s1,rand_control_222
addi s1,s1,1
rand_control_222:
add s5,s2,s2
and s2,s2,s4
sll s2,s4,s4
andi s5,s5,418
bne s4,s4,rand_control_227
addi s5,s5,1
rand_control_227:
add s3,s2,s1
srl s4,s4,s5
srli s4,s3,9
sub s2,s1,s3
and s1,s2,s2
sll s5,s1,s1
addi s1,s3,1658
and s2,s2,s4
slli s2,s3,13
sltu s5,s1,s3
srai s2,s3,8
sub s1,s4,s4
andi s4,s5,808
bne s5,s5,rand_control_241
addi s2,s2,1
rand_control_241:
addi s3,s3,-707
bne s5,s5,rand_control_243
addi s5,s5,1
rand_control_243:
sll s2,s2,s2
and s5,s2,s5
andi s2,s2,1003
srli s3,s2,26
ori s2,s1,-864
srli s3,s1,31
and s5,s4,s5
srl s2,s3,s4
or s2,s3,s4
xor s5,s3,s4
sub s5,s5,s2
sll s4,s5,s5
sub s1,s5,s2
sltu s2,s2,s3
srli s4,s5,3
or s3,s2,s2
sub s1,s3,s2
sub s5,s5,s5
sltu s1,s2,s5
xor s1,s5,s3
beq s5,s5,rand_control_264
addi s1,s1,1
rand_control_264:
bne s4,s4,rand_control_265
addi s2,s2,1
rand_control_265:
or s4,s5,s4
sll s5,s5,s2
add s3,s3,s4
ori s2,s3,-524
andi s5,s3,1452
add s1,s3,s5
srai s2,s1,20
sltu s5,s3,s5
bne s5,s5,rand_control_274
addi s3,s3,1
rand_control_274:
beq s4,s4,rand_control_275
addi s1,s1,1
rand_control_275:
sltu s2,s4,s4
or s1,s5,s2
srai s1,s1,31
and s5,s1,s4
add s4,s1,s2
slt s5,s1,s5
srl s3,s3,s3
srl s5,s4,s5
sltu s3,s1,s5
addi s2,s1,-358
andi s2,s5,804
beq s4,s4,rand_control_287
addi s5,s5,1
rand_control_287:
addi s2,s2,879
or s2,s5,s5
add s4,s1,s5
and s3,s2,s2
sll s4,s2,s1
and s2,s5,s2
xor s3,s1,s2
xori s5,s4,-1545
add s2,s3,s2
srai s4,s1,1
and s3,s3,s3
xor s5,s2,s2
addi s5,s2,207
xori s4,s5,-1683
and s3,s4,s3
slli s1,s2,20
slt s2,s2,s3
slli s5,s1,14
srai s5,s1,0
andi s1,s3,-1730
sll s3,s5,s2
bne s4,s4,rand_control_309
addi s5,s5,1
rand_control_309:
or s1,s1,s5
srl s2,s3,s3
bne s1,s1,rand_control_312
addi s4,s4,1
rand_control_312:
add s2,s1,s4
add s4,s2,s3
andi s3,s2,3
beq s4,s4,rand_control_316
addi s5,s5,1
rand_control_316:
sub s4,s1,s4
xori s2,s5,1930
xor s3,s4,s3
add s5,s3,s2
or s4,s2,s2
ori s1,s3,-1553
slt s2,s2,s2
addi s3,s4,1523
xor s5,s5,s2
xor s2,s2,s1
addi s4,s5,965
or s4,s3,s1
beq s4,s4,rand_control_329
addi s5,s5,1
rand_control_329:
srl s3,s5,s5
sll s5,s1,s4
sll s2,s1,s4
srl s2,s4,s3
xori s4,s1,-1138
andi s2,s5,1427
beq s4,s4,rand_control_336
addi s1,s1,1
rand_control_336:
sub s3,s2,s1
srai s1,s5,28
and s1,s2,s5
sub s5,s1,s1
add s5,s2,s4
and s2,s3,s1
addi s1,s1,1360
beq s3,s3,rand_control_344
addi s4,s4,1
rand_control_344:
slli s4,s5,11
or s5,s4,s1
sltu s3,s2,s5
and s5,s3,s1
add s3,s4,s5
slt s2,s3,s5
sub s2,s2,s3
addi s4,s2,1168
or s1,s2,s3
srai s3,s2,15
slt s1,s2,s1
or s4,s1,s5
slli s5,s1,11
srli s4,s2,28
slt s3,s5,s4
xori s3,s4,1120
slt s5,s5,s4
bne s5,s5,rand_control_362
addi s1,s1,1
rand_control_362:
sll s5,s1,s5
xori s3,s4,-1588
slli s5,s2,23
srl s5,s3,s4
srl s4,s5,s1
srl s2,s2,s4
sltu s5,s1,s2
andi s1,s5,-1992
add s5,s5,s1
bne s2,s2,rand_control_372
addi s1,s1,1
rand_control_372:
and s5,s4,s4
bne s2,s2,rand_control_374
addi s2,s2,1
rand_control_374:
sll s5,s3,s1
beq s4,s4,rand_control_376
addi s2,s2,1
rand_control_376:
sub s3,s1,s2
addi s3,s1,1270
slt s2,s1,s3
srai s5,s5,9
srl s1,s3,s1
and s5,s5,s4
add s4,s1,s5
and s3,s2,s1
beq s1,s1,rand_control_385
addi s4,s4,1
rand_control_385:
add s3,s1,s3
add s1,s5,s1
or s5,s4,s2
sltu s1,s3,s1
or s2,s5,s3
bne s3,s3,rand_control_391
addi s2,s2,1
rand_control_391:
sub s4,s1,s1
slli s4,s5,1
slt s2,s4,s5
and s1,s5,s4
beq s1,s1,rand_control_396
addi s4,s4,1
rand_control_396:
slli s3,s4,21
andi s2,s2,-1795
addi s4,s3,-576
sub s4,s5,s5
bne s3,s3,rand_control_401
addi s5,s5,1
rand_control_401:
srai s4,s3,30
srli s2,s4,6
srl s4,s2,s5
bne s1,s1,rand_control_405
addi s2,s2,1
rand_control_405:
bne s3,s3,rand_control_406
addi s5,s5,1
rand_control_406:
sll s2,s2,s3
add s4,s4,s3
andi s3,s5,-793
sltu s2,s2,s5
ori s3,s2,2032
andi s4,s2,-1224
addi s5,s5,1418
sltu s2,s5,s5
xor s2,s5,s5
xor s2,s1,s2
srai s1,s3,5
beq s3,s3,rand_control_418
addi s5,s5,1
rand_control_418:
bne s1,s1,rand_control_419
addi s2,s2,1
rand_control_419:
sub s4,s5,s4
xor s4,s5,s1
addi s5,s3,-1165
andi s2,s3,889
slli s3,s1,2
srli s3,s4,14
sll s1,s3,s3
andi s3,s2,-1145
and s5,s4,s2
xor s1,s1,s3
slli s5,s5,16
bne s5,s5,rand_control_431
addi s2,s2,1
rand_control_431:
or s4,s2,s4
addi s4,s2,1939
sll s5,s1,s1
beq s4,s4,rand_control_435
addi s2,s2,1
rand_control_435:
srli s2,s1,30
or s4,s1,s2
srai s5,s5,31
srai s4,s3,4
xori s2,s3,1920
srl s5,s5,s1
srl s1,s5,s1
beq s2,s2,rand_control_443
addi s2,s2,1
rand_control_443:
sub s3,s1,s1
sltu s3,s4,s4
andi s3,s2,-687
srli s2,s5,28
add s3,s3,s3
sub s4,s2,s3
ori s2,s1,-1991
srli s3,s2,27
slt s2,s2,s5
srai s5,s4,2
xori s2,s5,1454
srl s2,s4,s2
srl s3,s4,s1
addi s1,s4,-981
slli s4,s3,24
srl s5,s5,s2
sltu s5,s1,s4
ori s2,s5,-1370
sltu s3,s1,s4
beq s4,s4,rand_control_463
addi s5,s5,1
rand_control_463:
slt s4,s3,s1
and s3,s5,s5
addi s5,s3,1546
sll s3,s1,s1
xori s1,s4,1127
bne s5,s5,rand_control_469
addi s2,s2,1
rand_control_469:
and s1,s5,s3
sub s2,s4,s5
xor s1,s5,s1
sll s1,s4,s3
add s5,s4,s1
xor s1,s1,s5
srl s4,s2,s2
or s3,s5,s1
slli s2,s2,3
bne s2,s2,rand_control_479
addi s5,s5,1
rand_control_479:
add s1,s1,s1
xori s3,s3,-365
ori s5,s2,-588
and s1,s1,s4
beq s2,s2,rand_control_484
addi s5,s5,1
rand_control_484:
slt s1,s2,s2
beq s4,s4,rand_control_486
addi s1,s1,1
rand_control_486:
srai s3,s3,12
sll s1,s2,s3
addi s5,s4,576
sltu s2,s5,s5
add s3,s1,s1
srai s5,s3,12
addi s2,s3,7
beq s1,s1,rand_control_494
addi s5,s5,1
rand_control_494:
or s2,s4,s5
srai s4,s3,14
or s5,s5,s1
slt s2,s3,s2
xor s1,s3,s2
slt s3,s5,s1
xori s4,s3,237
or s5,s5,s2
beq s4,s4,rand_control_503
addi s4,s4,1
rand_control_503:
xor s5,s2,s1
sltu s4,s1,s4
andi s1,s3,-350
beq s1,s1,rand_control_507
addi s1,s1,1
rand_control_507:
or s5,s1,s5
sltu s2,s1,s5
xor s5,s5,s5
sltu s3,s5,s4
slli s5,s1,15
or s1,s4,s5
xori s5,s3,-330
srai s3,s5,19
or s5,s3,s1
slli s3,s1,20
beq s2,s2,rand_control_518
addi s4,s4,1
rand_control_518:
xori s2,s4,271
slt s4,s3,s1
andi s1,s2,1719
srli s3,s4,3
sub s5,s2,s3
add s4,s2,s3
sub s3,s1,s3
add s5,s5,s1
srl s5,s3,s5
addi s2,s1,-604
sub s5,s1,s4
sub s1,s1,s3
addi s1,s1,-1562
beq s2,s2,rand_control_532
addi s2,s2,1
rand_control_532:
or s2,s4,s2
addi s1,s5,-1048
ori s5,s5,-174
addi s5,s1,-563
sub s3,s3,s2
or s2,s2,s1
and s4,s1,s4
sltu s3,s4,s5
beq s4,s4,rand_control_541
addi s2,s2,1
rand_control_541:
ori s1,s4,-883
srai s5,s3,11
xor s3,s5,s1
sll s2,s2,s5
sub s5,s3,s4
slt s2,s1,s2
srai s5,s1,25
addi s5,s4,343
xor s4,s2,s4
xor s1,s4,s3
srli s2,s5,14
ori s5,s4,2047
add s4,s1,s2
bne s3,s3,rand_control_555
addi s5,s5,1
rand_control_555:
addi s5,s2,1722
andi s1,s4,-1847
bne s5,s5,rand_control_558
addi s1,s1,1
rand_control_558:
xori s3,s1,-1614
xor s4,s4,s1
srli s4,s2,13
xori s5,s4,-1322
slt s3,s4,s5
or s4,s5,s4
slli s1,s2,12
srli s4,s4,9
add s5,s1,s2
bne s5,s5,rand_control_568
addi s2,s2,1
rand_control_568:
add s1,s3,s5
bne s3,s3,rand_control_570
addi s5,s5,1
rand_control_570:
beq s3,s3,rand_control_571
addi s4,s4,1
rand_control_571:
addi s4,s1,836
ori s2,s5,-1461
andi s2,s2,-417
or s2,s5,s3
slli s3,s2,0
srai s5,s1,21
slli s2,s5,23
srli s4,s3,6
sub s5,s4,s4
bne s1,s1,rand_control_581
addi s4,s4,1
rand_control_581:
sll s2,s5,s2
bne s4,s4,rand_control_583
addi s4,s4,1
rand_control_583:
ori s5,s2,-1159
ori s1,s1,-999
srli s4,s2,11
sub s4,s4,s2
and s4,s3,s2
srl s4,s3,s3
xori s2,s3,101
xori s5,s3,-475
ori s4,s1,1292
srli s5,s1,20
sll s2,s4,s1
slt s4,s1,s5
andi s1,s2,1227
srl s2,s2,s5
sll s2,s5,s5
srai s3,s3,19
xori s5,s3,1754
addi s2,s5,-660
slt s2,s4,s2
ori s1,s2,1828
xor s4,s3,s5
sltu s1,s4,s4
sub s5,s1,s3
xor s1,s4,s4
sll s1,s5,s2
slli s5,s2,13
add s4,s2,s4
ori s3,s3,1784
xori s5,s2,-947
sltu s4,s4,s4
srai s5,s3,17
and s4,s1,s2
srai s1,s4,29
srli s4,s2,27
ori s5,s5,-1992
bne s4,s4,rand_control_619
addi s1,s1,1
rand_control_619:
bne s1,s1,rand_control_620
addi s1,s1,1
rand_control_620:
sub s5,s5,s2
xori s3,s2,293
sltu s4,s4,s3
addi s4,s1,-242
slli s2,s3,19
sll s4,s2,s1
slt s1,s4,s3
bne s4,s4,rand_control_628
addi s5,s5,1
rand_control_628:
ori s2,s4,-13
beq s5,s5,rand_control_630
addi s3,s3,1
rand_control_630:
sub s5,s2,s3
srai s5,s3,6
srl s2,s1,s1
xori s1,s1,-1092
sltu s5,s2,s4
srli s3,s1,7
add s4,s4,s4
xor s4,s3,s3
xor s5,s1,s1
srli s4,s2,28
sub s3,s2,s2
sub s2,s5,s2
xor s1,s1,s2
slt s2,s4,s5
srli s2,s4,10
srli s4,s4,23
slt s3,s3,s1
andi s2,s5,24
srai s2,s4,28
slt s5,s5,s5
or s5,s2,s2
xori s2,s4,-679
andi s5,s5,-13
ori s5,s5,-194
sll s3,s4,s5
srl s5,s2,s5
add s5,s2,s4
sub s5,s2,s3
andi s3,s3,-34
addi s2,s1,756
xor s5,s4,s5
srai s4,s5,1
and s1,s1,s2
andi s2,s3,1904
ori s2,s5,-1217
sub s1,s5,s5
add s5,s5,s4
srli s3,s4,30
bne s3,s3,rand_control_669
addi s2,s2,1
rand_control_669:
or s4,s3,s4
slli s3,s1,27
addi s4,s5,-309
or s1,s4,s1
slt s5,s2,s3
sub s5,s3,s1
or s5,s3,s2
addi s1,s3,-2035
xor s4,s1,s1
beq s3,s3,rand_control_679
addi s1,s1,1
rand_control_679:
beq s5,s5,rand_control_680
addi s4,s4,1
rand_control_680:
add s3,s1,s3
slli s5,s2,23
slt s3,s1,s4
sll s4,s1,s5
sll s4,s4,s4
and s2,s1,s5
ori s2,s4,213
sll s2,s4,s2
srai s1,s2,7
beq s2,s2,rand_control_690
addi s4,s4,1
rand_control_690:
andi s5,s5,-1204
sltu s4,s2,s3
slt s2,s2,s3
ori s3,s2,-394
xori s1,s5,2009
add s5,s4,s4
sll s2,s5,s5
slli s4,s2,3
srai s4,s1,3
sltu s1,s3,s5
slt s5,s1,s3
srai s4,s5,10
srai s3,s1,2
andi s5,s4,1699
or s5,s5,s3
xor s4,s5,s2
xor s4,s5,s1
sub s4,s4,s3
addi s1,s3,-1783
or s1,s3,s2
slt s2,s4,s4
and s5,s2,s2
sltu s2,s3,s4
srl s1,s3,s4
bne s1,s1,rand_control_715
addi s1,s1,1
rand_control_715:
or s3,s2,s2
xor s5,s4,s3
bne s2,s2,rand_control_718
addi s3,s3,1
rand_control_718:
xori s1,s4,-1889
beq s5,s5,rand_control_720
addi s1,s1,1
rand_control_720:
srli s3,s2,13
srai s2,s3,31
slt s1,s5,s1
sub s5,s2,s4
srli s2,s3,24
srl s1,s3,s4
slli s5,s2,4
ori s3,s4,-515
add s4,s1,s1
sub s3,s3,s1
addi s4,s1,-710
bne s5,s5,rand_control_732
addi s4,s4,1
rand_control_732:
sll s2,s3,s3
srli s1,s5,22
sub s5,s4,s1
andi s4,s5,1300
slt s3,s4,s3
beq s4,s4,rand_control_738
addi s4,s4,1
rand_control_738:
srl s3,s1,s2
srli s5,s4,1
srli s4,s1,0
srl s4,s5,s5
slt s2,s3,s3
sltu s5,s2,s1
andi s2,s1,-1550
sll s1,s4,s4
and s3,s1,s1
slli s4,s4,20
ori s3,s2,-1807
ori s1,s2,-1868
ori s1,s3,1986
and s4,s2,s5
addi s1,s4,1861
slt s5,s4,s2
beq s3,s3,rand_control_755
addi s4,s4,1
rand_control_755:
or s3,s1,s4
beq s4,s4,rand_control_757
addi s4,s4,1
rand_control_757:
beq s3,s3,rand_control_758
addi s5,s5,1
rand_control_758:
srai s5,s4,14
addi s1,s1,-1118
srl s4,s2,s3
and s2,s4,s5
sll s3,s1,s5
add s4,s5,s3
addi s4,s1,-363
andi s5,s2,-202
srai s4,s2,4
srli s4,s3,6
srai s4,s4,22
addi s1,s4,1845
sltu s4,s2,s2
srai s1,s5,13
sll s2,s2,s5
and s2,s1,s3
beq s5,s5,rand_control_775
addi s3,s3,1
rand_control_775:
slt s3,s3,s2
slt s2,s2,s2
srai s3,s1,1
sub s1,s5,s4
andi s1,s1,-839
srli s1,s2,9
beq s3,s3,rand_control_782
addi s4,s4,1
rand_control_782:
andi s5,s1,-532
sltu s1,s5,s5
slli s2,s2,17
sltu s1,s1,s5
srai s1,s5,10
addi s5,s5,-1184
srl s5,s2,s4
and s4,s1,s1
ori s2,s4,-688
slt s5,s2,s2
sll s3,s3,s1
add s5,s2,s5
addi s4,s4,165
slli s2,s1,22
addi s5,s1,-1358
bne s4,s4,rand_control_798
addi s2,s2,1
rand_control_798:
slt s3,s3,s2
srli s4,s4,23
and s4,s4,s2
and s2,s2,s5
xori s2,s1,-319
beq s4,s4,rand_control_804
addi s2,s2,1
rand_control_804:
slt s5,s2,s2
and s5,s4,s1
or s2,s1,s5
beq s2,s2,rand_control_808
addi s2,s2,1
rand_control_808:
srai s4,s1,5
sltu s1,s4,s5
add s4,s4,s5
slt s1,s3,s5
andi s3,s1,-691
xori s4,s5,1454
andi s4,s4,178
srai s1,s2,5
ori s1,s5,216
bne s3,s3,rand_control_818
addi s5,s5,1
rand_control_818:
sltu s2,s2,s4
xori s4,s1,-493
xor s5,s3,s4
sub s4,s2,s3
xor s2,s4,s2
ori s5,s3,1100
andi s1,s1,929
srai s5,s3,25
or s5,s5,s3
addi s3,s2,55
sub s1,s3,s1
sll s1,s5,s3
sltu s4,s5,s4
sub s1,s4,s5
xori s4,s3,-1316
add s2,s1,s4
srl s3,s2,s5
andi s4,s2,-1575
beq s4,s4,rand_control_837
addi s5,s5,1
rand_control_837:
ori s2,s5,-650
xor s2,s4,s4
xori s5,s5,-1746
sll s3,s2,s5
add s2,s5,s5
addi s2,s5,1499
sub s4,s2,s2
xori s4,s2,1057
andi s4,s2,891
xori s4,s2,-785
srl s2,s5,s4
sll s3,s5,s5
or s2,s2,s3
srai s1,s3,14
xori s1,s4,721
srl s2,s3,s3
slt s3,s3,s2
srli s4,s4,20
and s3,s3,s4
srl s2,s3,s1
sub s5,s1,s2
slli s2,s3,26
and s5,s1,s1
sll s3,s3,s2
slt s2,s3,s4
sub s2,s1,s4
xori s4,s5,-50
srl s1,s4,s4
and s1,s5,s3
xor s3,s3,s5
srl s4,s1,s1
andi s2,s3,1048
bne s5,s5,rand_control_870
addi s5,s5,1
rand_control_870:
add s3,s5,s5
beq s1,s1,rand_control_872
addi s3,s3,1
rand_control_872:
slt s3,s5,s3
bne s5,s5,rand_control_874
addi s3,s3,1
rand_control_874:
andi s2,s4,803
beq s5,s5,rand_control_876
addi s4,s4,1
rand_control_876:
add s5,s1,s5
xori s5,s4,-613
ori s3,s2,1530
slt s3,s5,s2
addi s4,s3,607
xor s5,s5,s4
xor s3,s1,s3
slt s1,s3,s2
or s1,s4,s4
xor s4,s3,s5
xor s2,s3,s1
or s2,s3,s5
andi s2,s4,-549
srai s5,s5,20
slt s3,s5,s3
bne s2,s2,rand_control_892
addi s4,s4,1
rand_control_892:
or s4,s2,s4
add s5,s2,s1
slt s4,s5,s5
and s1,s3,s2
srl s2,s2,s5
beq s1,s1,rand_control_898
addi s2,s2,1
rand_control_898:
addi s1,s2,1296
srli s2,s5,26
srl s3,s4,s1
bne s5,s5,rand_control_902
addi s1,s1,1
rand_control_902:
and s5,s2,s2
sltu s3,s1,s5
beq s4,s4,rand_control_905
addi s2,s2,1
rand_control_905:
sub s2,s5,s3
or s5,s4,s3
sll s2,s3,s1
slt s3,s1,s1
andi s3,s2,-301
sub s2,s2,s4
and s5,s1,s5
sub s1,s4,s5
beq s4,s4,rand_control_914
addi s1,s1,1
rand_control_914:
ori s3,s3,-721
add s5,s1,s5
slt s1,s5,s3
srli s2,s3,31
addi s2,s4,-1209
srli s5,s3,23
sll s5,s2,s4
slt s3,s5,s3
srai s3,s1,27
sltu s1,s3,s5
srli s1,s1,16
or s3,s2,s3
or s4,s2,s5
srai s5,s3,3
or s5,s1,s1
slt s4,s1,s4
addi s3,s4,1988
sub s2,s5,s5
srai s4,s4,2
srai s2,s1,3
sltu s2,s1,s1
and s2,s5,s3
and s5,s2,s2
slt s5,s5,s5
andi s1,s3,450
slli s2,s1,12
sub s3,s3,s3
sltu s1,s5,s3
xor s3,s5,s3
srai s1,s4,22
andi s3,s2,1586
sub s5,s4,s2
slt s4,s3,s4
sll s2,s4,s4
srl s4,s4,s3
beq s2,s2,rand_control_950
addi s5,s5,1
rand_control_950:
slt s1,s2,s4
srli s2,s2,3
sub s3,s1,s4
srl s3,s4,s3
sll s5,s1,s1
beq s5,s5,rand_control_956
addi s2,s2,1
rand_control_956:
sltu s5,s2,s3
slli s2,s5,27
andi s2,s2,1624
bne s1,s1,rand_control_960
addi s3,s3,1
rand_control_960:
slli s4,s5,21
andi s3,s3,1985
and s1,s1,s3
srai s5,s4,22
add s4,s2,s4
addi s2,s2,-1564
xori s2,s3,1962
or s4,s1,s3
slli s5,s2,31
slli s2,s3,14
andi s5,s5,1967
sltu s2,s1,s4
and s3,s3,s2
slt s5,s5,s5
or s3,s1,s1
ori s4,s2,-881
and s4,s5,s2
beq s5,s5,rand_control_978
addi s5,s5,1
rand_control_978:
or s4,s3,s5
add s3,s3,s4
or s5,s2,s3
bne s3,s3,rand_control_982
addi s1,s1,1
rand_control_982:
beq s2,s2,rand_control_983
addi s5,s5,1
rand_control_983:
andi s4,s1,1973
add s5,s4,s2
slt s3,s3,s5
srli s3,s1,28
sll s1,s1,s5
sub s3,s5,s4
or s3,s5,s4
add s5,s2,s4
and s4,s1,s3
srai s5,s1,22
slli s2,s1,4
sltu s2,s4,s3
slli s5,s4,2
slt s2,s3,s1
slli s1,s4,19
or s4,s1,s5
xor s3,s2,s2
sub s3,s1,s5
addi s5,s5,412
xor s3,s3,s5
xor s1,s2,s3
or s1,s1,s4
ori s1,s2,471
ori s4,s5,1172
xori s1,s1,-660
or s2,s5,s1
srli s3,s4,25
add s4,s5,s2
sltu s3,s2,s5
srl s2,s3,s4
slli s1,s3,15
srai s2,s1,26
sub s4,s1,s1
sltu s4,s2,s1
xor s3,s4,s2
beq s4,s4,rand_control_1019
addi s5,s5,1
rand_control_1019:
srl s1,s4,s1
sltu s2,s1,s4
ori s1,s3,-548
and s4,s2,s2
sub s2,s5,s4
addi s2,s1,-1940
xor s5,s4,s5
srli s2,s2,7
bne s2,s2,rand_control_1028
addi s4,s4,1
rand_control_1028:
bne s4,s4,rand_control_1029
addi s2,s2,1
rand_control_1029:
addi s5,s2,1985
slli s5,s5,2
ori s3,s1,-2003
xori s5,s1,475
srl s5,s2,s1
addi s3,s3,-1481
slt s4,s4,s3
sltu s4,s5,s4
ori s4,s5,-387
bne s4,s4,rand_control_1039
addi s4,s4,1
rand_control_1039:
add s4,s3,s5
sub s3,s3,s5
andi s3,s5,688
bne s2,s2,rand_control_1043
addi s2,s2,1
rand_control_1043:
beq s1,s1,rand_control_1044
addi s5,s5,1
rand_control_1044:
slt s5,s3,s5
ori s1,s4,-1438
xori s1,s5,-169
sll s1,s4,s1
andi s4,s4,338
ori s1,s1,-158
xor s1,s5,s3
xor s5,s1,s1
srai s1,s5,23
andi s5,s2,323
bne s2,s2,rand_control_1055
addi s2,s2,1
rand_control_1055:
or s1,s1,s2
add s4,s2,s2
srai s5,s4,14
xor s5,s1,s1
ori s4,s3,226
sub s5,s4,s4
and s3,s1,s3
addi s5,s3,-1458
srli s1,s1,11
bne s5,s5,rand_control_1065
addi s4,s4,1
rand_control_1065:
andi s4,s4,1245
add s3,s4,s2
sltu s2,s2,s3
bne s3,s3,rand_control_1069
addi s4,s4,1
rand_control_1069:
xor s4,s4,s1
xor s2,s5,s4
beq s1,s1,rand_control_1072
addi s4,s4,1
rand_control_1072:
sub s1,s3,s1
and s1,s5,s3
slt s3,s3,s5
xori s5,s3,1697
sltu s1,s1,s2
xori s2,s1,-958
sll s2,s1,s4
bne s4,s4,rand_control_1080
addi s3,s3,1
rand_control_1080:
srli s1,s2,30
and s1,s3,s5
srai s4,s1,12
or s1,s3,s4
xori s3,s1,928
beq s2,s2,rand_control_1086
addi s4,s4,1
rand_control_1086:
xori s1,s3,-1818
beq s1,s1,rand_control_1088
addi s5,s5,1
rand_control_1088:
xor s1,s5,s1
slli s5,s3,16
bne s4,s4,rand_control_1091
addi s5,s5,1
rand_control_1091:
srli s5,s4,15
srli s2,s5,29
ori s3,s5,-1093
add s4,s1,s2
slli s4,s1,15
andi s3,s1,1473
add s1,s4,s4
srli s2,s3,23
srai s2,s4,0
xor s4,s2,s2
srli s4,s1,28
srai s1,s3,4
beq s3,s3,rand_control_1104
addi s1,s1,1
rand_control_1104:
bne s4,s4,rand_control_1105
addi s5,s5,1
rand_control_1105:
andi s5,s2,-404
add s5,s5,s4
srai s3,s5,19
srli s4,s3,7
sll s2,s1,s5
beq s4,s4,rand_control_1111
addi s3,s3,1
rand_control_1111:
srli s2,s5,19
xori s4,s2,788
ori s4,s1,-1591
sub s5,s4,s4
bne s1,s1,rand_control_1116
addi s2,s2,1
rand_control_1116:
bne s2,s2,rand_control_1117
addi s3,s3,1
rand_control_1117:
xori s2,s1,1423
or s3,s5,s3
bne s5,s5,rand_control_1120
addi s3,s3,1
rand_control_1120:
add s5,s3,s1
and s4,s4,s4
slt s5,s4,s2
or s1,s5,s3
bne s4,s4,rand_control_1125
addi s2,s2,1
rand_control_1125:
sub s4,s2,s4
sub s2,s3,s4
xori s2,s2,-897
addi s3,s3,1947
sub s1,s1,s2
slli s1,s2,29
srli s1,s4,4
srl s4,s1,s1
sub s1,s4,s3
ori s1,s2,-1207
sltu s5,s1,s5
slt s4,s2,s3
and s4,s1,s3
and s2,s2,s5
slli s3,s2,31
srai s3,s3,27
slli s4,s5,29
add s3,s4,s3
slli s2,s5,26
srl s2,s3,s3
bne s2,s2,rand_control_1146
addi s2,s2,1
rand_control_1146:
sltu s4,s2,s1
xor s5,s5,s4
sltu s5,s2,s4
beq s2,s2,rand_control_1150
addi s3,s3,1
rand_control_1150:
srai s3,s2,2
addi s3,s2,1449
or s4,s2,s4
srl s1,s5,s1
srli s2,s5,24
andi s2,s3,-332
bne s1,s1,rand_control_1157
addi s3,s3,1
rand_control_1157:
beq s3,s3,rand_control_1158
addi s2,s2,1
rand_control_1158:
and s2,s3,s1
xor s1,s3,s4
add s3,s3,s4
addi s5,s5,547
srli s3,s1,2
slli s5,s4,15
sll s5,s5,s3
beq s1,s1,rand_control_1166
addi s1,s1,1
rand_control_1166:
srai s4,s4,10
add s4,s5,s3
ori s4,s4,1872
beq s1,s1,rand_control_1170
addi s2,s2,1
rand_control_1170:
ori s1,s3,520
sltu s4,s3,s4
ori s1,s1,-910
addi s3,s2,2042
slt s2,s5,s2
sll s2,s1,s4
andi s1,s5,-816
or s2,s3,s5
xor s3,s4,s1
xori s1,s4,-949
addi s3,s4,1030
andi s5,s4,1186
addi s5,s2,-144
sub s3,s1,s4
add s4,s5,s3
sll s3,s1,s5
sltu s5,s4,s5
beq s4,s4,rand_control_1188
addi s5,s5,1
rand_control_1188:
bne s1,s1,rand_control_1189
addi s1,s1,1
rand_control_1189:
sll s5,s3,s2
sll s4,s3,s5
srli s1,s3,28
srai s1,s2,11
bne s3,s3,rand_control_1194
addi s3,s3,1
rand_control_1194:
xori s3,s2,655
ori s2,s4,-1521
xori s1,s3,2021
beq s5,s5,rand_control_1198
addi s2,s2,1
rand_control_1198:
beq s3,s3,rand_control_1199
addi s3,s3,1
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

