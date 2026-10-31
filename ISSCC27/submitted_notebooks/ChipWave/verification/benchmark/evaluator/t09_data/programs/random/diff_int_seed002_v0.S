.option norvc
.section .text.init
.globl _start
_start:
la s0,scratch
li t0,0x90000000
li s1,2936084559
li s2,3100361772
li s3,1875488150
li s4,3991281443
li s5,1403174445
andi s3,s1,-1062
bne s3,s3,rand_control_1
addi s1,s1,1
rand_control_1:
xor s5,s4,s1
srli s4,s3,24
srai s3,s4,10
or s3,s1,s5
add s1,s3,s4
slt s5,s2,s1
andi s5,s5,106
add s2,s1,s5
sltu s5,s2,s1
add s3,s2,s4
srai s1,s3,20
add s3,s5,s3
srl s2,s4,s4
add s1,s1,s3
srli s4,s4,2
add s5,s2,s1
andi s1,s3,-534
addi s3,s1,-407
addi s1,s5,-1999
bne s4,s4,rand_control_21
addi s3,s3,1
rand_control_21:
srai s1,s2,10
andi s4,s1,1171
sub s1,s5,s5
srli s4,s3,12
sub s1,s5,s3
slli s1,s3,26
srli s4,s2,15
xori s3,s4,-1165
add s2,s2,s4
xori s2,s5,1532
srl s1,s1,s2
andi s1,s4,-914
add s4,s1,s3
add s5,s4,s4
add s1,s4,s5
xori s1,s3,-1337
srai s4,s4,26
beq s2,s2,rand_control_39
addi s2,s2,1
rand_control_39:
sub s1,s5,s1
sltu s5,s4,s1
or s5,s2,s5
beq s1,s1,rand_control_43
addi s4,s4,1
rand_control_43:
or s5,s2,s2
sub s3,s5,s1
srai s2,s1,19
andi s3,s3,-1239
xor s3,s3,s2
xori s3,s5,181
slt s2,s3,s3
ori s2,s2,-1500
bne s5,s5,rand_control_52
addi s1,s1,1
rand_control_52:
addi s4,s1,-806
and s2,s2,s2
xori s3,s5,1679
add s2,s4,s4
slt s2,s3,s1
srli s2,s3,6
srl s2,s2,s2
add s3,s4,s3
srli s5,s2,9
sub s3,s3,s3
sll s2,s5,s5
slt s4,s2,s3
srli s3,s3,17
beq s3,s3,rand_control_66
addi s3,s3,1
rand_control_66:
and s4,s5,s5
xori s3,s5,1532
xori s4,s5,915
srl s1,s5,s2
and s1,s2,s1
or s5,s2,s2
xor s1,s1,s4
sll s2,s4,s3
srai s1,s2,14
bne s5,s5,rand_control_76
addi s2,s2,1
rand_control_76:
and s5,s1,s5
xor s5,s2,s1
sub s4,s2,s4
add s3,s5,s1
ori s4,s2,-1622
and s1,s1,s5
andi s4,s2,-887
srai s2,s2,10
srli s5,s2,23
sll s1,s1,s4
bne s3,s3,rand_control_87
addi s4,s4,1
rand_control_87:
slli s5,s3,1
andi s4,s5,558
andi s2,s3,1400
and s1,s3,s2
add s3,s5,s1
slt s1,s5,s3
and s2,s1,s2
beq s4,s4,rand_control_95
addi s3,s3,1
rand_control_95:
slli s4,s5,18
sub s3,s4,s1
sltu s5,s5,s3
sltu s1,s2,s5
xori s5,s2,-467
srli s1,s1,28
beq s2,s2,rand_control_102
addi s5,s5,1
rand_control_102:
srl s5,s4,s3
and s3,s3,s4
srl s2,s1,s2
bne s1,s1,rand_control_106
addi s5,s5,1
rand_control_106:
sltu s5,s3,s3
bne s3,s3,rand_control_108
addi s2,s2,1
rand_control_108:
sub s3,s3,s5
xor s3,s3,s2
xori s5,s2,1840
sll s1,s5,s3
xor s3,s2,s5
sltu s3,s1,s3
andi s5,s3,-1826
sub s4,s5,s2
xori s5,s3,1696
addi s1,s1,-600
sll s5,s5,s5
srl s4,s3,s4
slli s3,s3,24
and s1,s4,s3
xori s1,s2,-706
beq s1,s1,rand_control_124
addi s5,s5,1
rand_control_124:
sll s5,s3,s5
beq s3,s3,rand_control_126
addi s1,s1,1
rand_control_126:
or s3,s5,s5
ori s3,s3,-1128
bne s2,s2,rand_control_129
addi s2,s2,1
rand_control_129:
sltu s4,s3,s5
srli s2,s3,30
add s1,s1,s5
beq s1,s1,rand_control_133
addi s2,s2,1
rand_control_133:
add s4,s3,s2
srli s2,s1,30
srl s3,s2,s3
andi s3,s3,918
sub s5,s4,s5
xori s5,s5,1243
xor s2,s1,s4
slli s1,s4,29
sll s2,s1,s3
xor s1,s1,s5
srli s5,s5,2
sltu s5,s3,s3
srai s1,s2,1
srai s5,s1,18
and s1,s2,s3
srli s1,s1,9
beq s4,s4,rand_control_150
addi s1,s1,1
rand_control_150:
srli s5,s4,17
slli s2,s2,25
and s3,s4,s5
and s4,s5,s1
slli s4,s3,25
slli s3,s2,20
srli s3,s5,29
or s4,s2,s5
slt s3,s4,s2
andi s1,s4,-476
add s2,s4,s5
xori s4,s4,-716
xori s4,s5,-1661
sub s5,s5,s1
bne s5,s5,rand_control_165
addi s2,s2,1
rand_control_165:
beq s2,s2,rand_control_166
addi s5,s5,1
rand_control_166:
xor s1,s4,s5
xori s4,s2,-1472
xor s5,s3,s3
srli s3,s1,26
bne s4,s4,rand_control_171
addi s3,s3,1
rand_control_171:
xor s2,s1,s1
sub s4,s5,s2
bne s5,s5,rand_control_174
addi s3,s3,1
rand_control_174:
srai s5,s2,16
or s1,s3,s4
xor s4,s2,s5
andi s3,s1,-1858
xor s3,s3,s3
sll s4,s2,s4
xori s5,s3,1306
addi s3,s4,402
srli s3,s5,14
bne s2,s2,rand_control_184
addi s5,s5,1
rand_control_184:
add s4,s1,s3
srli s4,s3,17
andi s4,s1,535
srl s1,s2,s1
slli s4,s4,4
addi s5,s4,-594
sll s1,s4,s3
srli s4,s4,9
sll s3,s2,s1
slt s1,s4,s3
xor s1,s2,s3
srai s4,s2,29
srli s4,s5,30
slt s4,s5,s5
srai s4,s2,12
addi s1,s4,-853
srl s2,s4,s3
andi s3,s1,1524
sltu s1,s5,s1
andi s1,s1,747
sltu s1,s4,s2
andi s3,s2,-380
sll s5,s1,s1
srai s2,s4,2
slli s5,s1,9
srai s5,s2,3
xori s5,s3,80
ori s3,s3,994
srl s2,s2,s5
srl s2,s4,s1
beq s1,s1,rand_control_215
addi s4,s4,1
rand_control_215:
srli s5,s1,13
sltu s1,s1,s3
or s4,s1,s1
srl s5,s1,s4
xor s2,s2,s3
beq s4,s4,rand_control_221
addi s4,s4,1
rand_control_221:
slli s3,s5,28
slt s4,s4,s3
sub s3,s2,s4
sltu s2,s1,s1
ori s3,s5,816
or s1,s3,s3
xor s4,s1,s4
xor s2,s1,s1
srai s4,s2,14
srl s5,s1,s4
or s3,s4,s2
andi s5,s2,424
xor s2,s5,s3
beq s5,s5,rand_control_235
addi s4,s4,1
rand_control_235:
addi s2,s4,-220
xor s5,s3,s2
srai s3,s1,0
slli s4,s1,2
andi s1,s4,1157
addi s5,s1,1138
addi s2,s5,-1705
ori s4,s1,191
beq s2,s2,rand_control_244
addi s5,s5,1
rand_control_244:
sub s1,s3,s2
srli s5,s3,28
srli s2,s1,3
xor s3,s2,s5
slli s5,s4,19
add s5,s5,s1
and s5,s5,s3
or s5,s3,s1
ori s4,s2,-1798
srai s4,s5,14
srai s1,s2,11
beq s3,s3,rand_control_256
addi s5,s5,1
rand_control_256:
slli s2,s1,15
bne s3,s3,rand_control_258
addi s3,s3,1
rand_control_258:
or s4,s3,s5
xori s4,s1,-1872
srai s1,s4,31
xor s1,s3,s4
addi s5,s1,1379
srai s2,s5,7
sll s3,s1,s2
beq s3,s3,rand_control_266
addi s5,s5,1
rand_control_266:
add s3,s5,s3
srai s4,s5,21
ori s2,s2,200
slt s3,s3,s2
sub s3,s2,s2
bne s1,s1,rand_control_272
addi s5,s5,1
rand_control_272:
or s1,s3,s1
srai s3,s5,28
or s1,s4,s2
sll s4,s4,s5
srl s3,s4,s1
xori s3,s2,-56
srl s1,s1,s2
srli s4,s2,20
sltu s4,s4,s2
ori s4,s2,177
slli s2,s2,29
bne s1,s1,rand_control_284
addi s2,s2,1
rand_control_284:
andi s1,s4,-1707
srl s4,s4,s3
srl s4,s4,s4
slt s3,s1,s2
slli s5,s4,28
sub s5,s1,s5
andi s2,s3,-306
addi s5,s1,-509
add s3,s4,s2
bne s2,s2,rand_control_294
addi s4,s4,1
rand_control_294:
and s5,s2,s4
bne s3,s3,rand_control_296
addi s4,s4,1
rand_control_296:
slt s3,s5,s5
addi s4,s4,-867
srai s4,s3,19
beq s3,s3,rand_control_300
addi s5,s5,1
rand_control_300:
srl s3,s5,s2
bne s3,s3,rand_control_302
addi s2,s2,1
rand_control_302:
sltu s5,s5,s5
sll s2,s5,s4
xor s4,s1,s1
sltu s3,s3,s1
slt s3,s3,s2
addi s5,s2,-56
srli s4,s5,20
slt s3,s2,s1
slli s3,s4,3
or s3,s3,s4
sltu s3,s2,s4
sltu s2,s2,s3
sltu s1,s4,s5
sltu s1,s2,s5
bne s4,s4,rand_control_317
addi s5,s5,1
rand_control_317:
beq s2,s2,rand_control_318
addi s3,s3,1
rand_control_318:
bne s2,s2,rand_control_319
addi s5,s5,1
rand_control_319:
xori s3,s4,-1099
andi s4,s5,1642
sll s1,s2,s2
xor s3,s3,s1
and s4,s3,s4
slli s5,s3,14
srl s5,s2,s4
sub s5,s2,s1
xori s5,s4,15
slli s1,s1,12
xori s3,s2,395
andi s1,s3,220
srli s4,s4,2
or s3,s2,s1
xori s2,s5,-1662
and s2,s1,s5
slt s3,s5,s2
sltu s1,s5,s1
bne s5,s5,rand_control_338
addi s4,s4,1
rand_control_338:
xori s4,s5,2026
sub s1,s2,s1
srai s4,s1,28
sub s2,s5,s5
srli s2,s2,25
srai s2,s2,2
andi s3,s1,18
srai s2,s2,19
xor s2,s5,s1
bne s4,s4,rand_control_348
addi s3,s3,1
rand_control_348:
or s3,s5,s1
xori s4,s3,1911
slt s5,s3,s2
srl s1,s5,s3
or s2,s5,s3
ori s5,s1,-1176
srl s1,s5,s3
bne s5,s5,rand_control_356
addi s3,s3,1
rand_control_356:
and s4,s1,s3
slt s3,s1,s3
beq s1,s1,rand_control_359
addi s3,s3,1
rand_control_359:
add s4,s4,s1
bne s2,s2,rand_control_361
addi s4,s4,1
rand_control_361:
srai s2,s1,24
srai s2,s4,12
ori s4,s3,1311
slt s3,s2,s1
add s1,s4,s5
srai s2,s1,20
slt s2,s1,s5
srl s3,s3,s3
srl s5,s1,s1
srl s1,s3,s2
sltu s2,s4,s2
xori s2,s1,-877
sub s2,s1,s3
srai s5,s4,5
ori s4,s2,1886
and s5,s4,s5
and s1,s4,s3
sub s3,s3,s2
andi s2,s3,1291
xor s1,s2,s4
ori s1,s1,-1726
ori s5,s2,-776
beq s4,s4,rand_control_384
addi s5,s5,1
rand_control_384:
or s4,s1,s3
srai s4,s1,12
sll s1,s4,s1
bne s3,s3,rand_control_388
addi s5,s5,1
rand_control_388:
sltu s5,s3,s3
srai s3,s2,10
srli s4,s3,3
bne s2,s2,rand_control_392
addi s5,s5,1
rand_control_392:
bne s3,s3,rand_control_393
addi s5,s5,1
rand_control_393:
ori s5,s4,822
xori s4,s5,-1585
slt s1,s3,s2
srl s3,s3,s2
sltu s5,s4,s3
srl s2,s2,s1
beq s3,s3,rand_control_400
addi s4,s4,1
rand_control_400:
beq s2,s2,rand_control_401
addi s5,s5,1
rand_control_401:
xori s4,s3,-574
xor s1,s1,s1
slli s4,s3,28
and s2,s2,s1
xor s4,s4,s3
ori s2,s1,982
slt s5,s4,s5
beq s2,s2,rand_control_409
addi s2,s2,1
rand_control_409:
or s4,s3,s4
srl s3,s3,s4
beq s2,s2,rand_control_412
addi s3,s3,1
rand_control_412:
srl s4,s5,s1
srai s1,s1,11
addi s1,s3,1591
and s5,s2,s3
bne s3,s3,rand_control_417
addi s5,s5,1
rand_control_417:
ori s4,s1,-888
bne s1,s1,rand_control_419
addi s3,s3,1
rand_control_419:
andi s4,s4,948
add s4,s5,s1
beq s1,s1,rand_control_422
addi s2,s2,1
rand_control_422:
andi s3,s1,1054
beq s3,s3,rand_control_424
addi s4,s4,1
rand_control_424:
xor s4,s3,s4
sll s2,s5,s4
beq s4,s4,rand_control_427
addi s5,s5,1
rand_control_427:
xori s3,s4,241
beq s4,s4,rand_control_429
addi s5,s5,1
rand_control_429:
srli s3,s4,28
and s1,s3,s1
slt s4,s2,s1
addi s4,s1,938
slt s1,s1,s5
sll s3,s1,s2
slt s2,s1,s2
beq s3,s3,rand_control_437
addi s1,s1,1
rand_control_437:
or s1,s5,s5
or s3,s2,s5
slli s4,s5,18
sltu s2,s4,s4
beq s2,s2,rand_control_442
addi s5,s5,1
rand_control_442:
xori s2,s5,39
slt s1,s3,s4
add s5,s3,s4
sub s3,s3,s3
add s3,s2,s1
addi s5,s5,-978
srli s1,s1,31
and s3,s1,s3
srl s4,s3,s4
xori s2,s4,-1112
addi s3,s5,912
and s2,s4,s1
and s3,s4,s1
bne s4,s4,rand_control_456
addi s3,s3,1
rand_control_456:
addi s2,s4,11
add s4,s5,s2
beq s3,s3,rand_control_459
addi s1,s1,1
rand_control_459:
slt s2,s3,s4
sub s4,s1,s4
slli s1,s5,26
sltu s5,s4,s1
sltu s4,s3,s2
addi s1,s2,-1120
slt s2,s2,s5
slt s4,s1,s5
or s4,s5,s3
beq s4,s4,rand_control_469
addi s5,s5,1
rand_control_469:
addi s1,s2,5
slli s2,s2,7
srai s5,s2,7
slli s2,s2,17
sll s3,s5,s2
andi s1,s4,-1275
and s2,s4,s3
beq s5,s5,rand_control_477
addi s3,s3,1
rand_control_477:
slli s2,s2,10
sub s5,s5,s4
ori s1,s3,-1859
srl s2,s2,s1
ori s1,s5,1658
sub s1,s3,s5
ori s2,s1,391
addi s1,s1,-1793
slli s2,s1,27
sub s2,s2,s3
xor s3,s3,s4
srai s3,s1,11
add s3,s2,s2
xor s1,s2,s5
srai s2,s2,6
sub s1,s4,s1
andi s1,s4,-181
xor s1,s2,s3
ori s5,s1,483
srli s3,s4,13
and s1,s5,s1
srli s4,s1,5
beq s4,s4,rand_control_500
addi s2,s2,1
rand_control_500:
sltu s4,s1,s5
ori s4,s5,906
andi s2,s3,-2010
bne s2,s2,rand_control_504
addi s2,s2,1
rand_control_504:
bne s2,s2,rand_control_505
addi s5,s5,1
rand_control_505:
srl s1,s5,s5
sub s4,s1,s4
xor s4,s4,s1
sub s3,s2,s1
srl s4,s2,s5
srli s5,s4,19
slt s3,s1,s4
srl s1,s5,s3
add s1,s2,s4
or s3,s5,s5
sll s1,s3,s2
andi s2,s3,-701
beq s4,s4,rand_control_518
addi s1,s1,1
rand_control_518:
sltu s1,s2,s5
sll s1,s5,s3
addi s5,s3,1014
slt s3,s2,s4
srl s5,s4,s1
xor s3,s3,s3
add s2,s2,s3
sll s2,s5,s4
sub s4,s4,s2
xori s5,s2,-1764
slt s2,s4,s1
srl s2,s4,s2
sub s1,s5,s1
srl s2,s1,s3
and s2,s5,s1
bne s4,s4,rand_control_534
addi s2,s2,1
rand_control_534:
slli s4,s3,23
beq s1,s1,rand_control_536
addi s4,s4,1
rand_control_536:
slt s1,s4,s1
add s5,s3,s5
andi s1,s1,461
addi s3,s1,1909
andi s3,s3,-1396
addi s4,s3,1336
ori s1,s4,-959
slli s3,s4,26
ori s3,s1,1816
srl s5,s1,s4
andi s2,s4,-835
or s1,s4,s5
srli s3,s3,1
slli s1,s1,8
sltu s3,s5,s4
xori s2,s1,966
add s3,s3,s5
addi s1,s3,-848
slt s5,s4,s3
srl s1,s5,s4
sub s1,s1,s4
slt s1,s2,s2
sub s4,s4,s3
bne s2,s2,rand_control_560
addi s4,s4,1
rand_control_560:
ori s2,s3,2028
sltu s5,s5,s3
xor s5,s5,s4
ori s5,s3,1703
srai s1,s3,13
xori s4,s5,765
andi s1,s1,1489
slt s5,s4,s1
xor s2,s3,s2
sub s4,s1,s5
srli s3,s3,19
xor s5,s4,s2
slt s5,s3,s5
beq s2,s2,rand_control_574
addi s2,s2,1
rand_control_574:
beq s3,s3,rand_control_575
addi s3,s3,1
rand_control_575:
and s5,s5,s3
or s5,s1,s2
sub s5,s2,s3
xori s4,s1,780
slli s3,s3,3
bne s2,s2,rand_control_581
addi s5,s5,1
rand_control_581:
srli s1,s4,29
xor s4,s4,s5
xor s1,s2,s3
srl s1,s5,s2
srl s1,s2,s1
bne s5,s5,rand_control_587
addi s3,s3,1
rand_control_587:
slt s2,s3,s4
slt s1,s5,s1
and s5,s5,s3
srli s3,s4,7
slt s2,s3,s2
slli s3,s2,31
xori s5,s3,332
sll s1,s5,s3
slli s5,s1,10
add s4,s1,s3
srai s5,s4,16
xori s5,s2,1276
bne s2,s2,rand_control_600
addi s4,s4,1
rand_control_600:
andi s2,s3,1540
sub s4,s1,s3
or s5,s5,s5
andi s1,s2,-266
or s1,s1,s2
add s1,s5,s5
srai s1,s3,24
slt s1,s4,s1
slt s5,s4,s1
and s5,s3,s5
srl s5,s5,s4
or s5,s4,s1
add s3,s3,s2
add s5,s1,s1
slli s4,s1,9
xor s3,s1,s4
or s4,s1,s1
slli s4,s5,0
addi s5,s4,872
bne s2,s2,rand_control_620
addi s5,s5,1
rand_control_620:
slt s1,s3,s3
xori s2,s3,1756
andi s2,s2,1559
sub s5,s5,s3
srl s3,s2,s1
xor s2,s3,s1
sltu s1,s5,s1
slli s5,s3,25
ori s1,s3,1862
addi s4,s5,-68
sltu s5,s5,s3
and s1,s4,s3
sll s5,s2,s5
ori s1,s5,-1899
slli s1,s2,9
or s3,s1,s1
sll s4,s1,s2
or s3,s2,s3
sll s5,s2,s1
sltu s1,s4,s4
srl s4,s3,s3
xor s5,s1,s2
sub s2,s3,s5
srli s1,s4,19
beq s4,s4,rand_control_645
addi s3,s3,1
rand_control_645:
slli s4,s1,16
ori s4,s5,170
and s4,s3,s2
add s1,s3,s4
srl s5,s5,s4
or s2,s3,s4
bne s4,s4,rand_control_652
addi s1,s1,1
rand_control_652:
andi s1,s1,-1519
slli s4,s3,2
addi s3,s2,-981
srl s3,s3,s2
srli s4,s5,31
add s2,s1,s1
xor s5,s1,s3
srai s1,s1,19
sltu s5,s5,s1
sltu s5,s1,s3
ori s1,s1,1372
beq s4,s4,rand_control_664
addi s4,s4,1
rand_control_664:
slli s2,s3,23
srai s3,s4,14
slt s1,s1,s4
srai s3,s2,29
srli s1,s1,18
srai s2,s3,8
or s2,s5,s5
ori s4,s3,-1974
and s2,s3,s3
sub s4,s3,s2
sub s2,s5,s4
sub s3,s1,s2
beq s1,s1,rand_control_677
addi s3,s3,1
rand_control_677:
xori s3,s3,-1282
slli s3,s5,5
xor s1,s1,s1
addi s5,s5,-1124
bne s5,s5,rand_control_682
addi s3,s3,1
rand_control_682:
bne s2,s2,rand_control_683
addi s3,s3,1
rand_control_683:
addi s4,s5,-2010
xor s1,s4,s4
add s4,s3,s1
srai s2,s4,11
sub s2,s1,s5
beq s4,s4,rand_control_689
addi s3,s3,1
rand_control_689:
andi s1,s3,610
slt s5,s3,s4
srai s2,s2,26
xori s3,s2,1630
sltu s2,s4,s3
or s2,s1,s2
andi s4,s2,-1914
slli s4,s2,16
ori s4,s2,1425
xori s2,s4,-1089
srl s4,s2,s3
slli s4,s3,22
srai s1,s4,12
slli s4,s3,19
or s1,s1,s4
or s1,s3,s4
slt s3,s2,s3
xor s5,s3,s2
xori s1,s5,-1418
xor s1,s2,s4
slt s1,s1,s1
sltu s3,s1,s4
sltu s5,s1,s3
ori s3,s5,1521
bne s4,s4,rand_control_714
addi s1,s1,1
rand_control_714:
sub s1,s3,s2
sll s1,s4,s5
xor s4,s5,s4
xori s4,s3,-57
sub s4,s5,s5
or s3,s1,s2
andi s3,s2,-1949
andi s2,s3,1622
slt s2,s4,s4
srl s4,s4,s4
sll s3,s4,s2
sltu s2,s2,s1
sltu s1,s4,s3
slli s4,s3,13
xor s2,s3,s4
xor s2,s5,s1
and s2,s3,s5
xori s5,s4,1143
xor s2,s5,s1
and s3,s1,s4
andi s5,s4,-1895
xori s4,s5,1240
andi s1,s1,-1992
slli s5,s5,19
or s5,s3,s2
or s5,s4,s1
add s2,s1,s3
srai s3,s3,26
sll s3,s1,s5
sll s4,s3,s5
and s1,s5,s3
beq s2,s2,rand_control_746
addi s1,s1,1
rand_control_746:
ori s5,s4,130
sltu s1,s2,s4
addi s1,s2,1733
slli s5,s1,12
and s2,s5,s5
and s2,s2,s1
sll s2,s1,s2
srli s5,s1,21
sltu s2,s2,s1
bne s1,s1,rand_control_756
addi s5,s5,1
rand_control_756:
and s2,s1,s2
add s3,s4,s4
srl s3,s3,s2
xori s1,s5,1289
add s3,s2,s2
add s1,s5,s4
bne s3,s3,rand_control_763
addi s4,s4,1
rand_control_763:
xor s5,s1,s2
bne s4,s4,rand_control_765
addi s1,s1,1
rand_control_765:
beq s5,s5,rand_control_766
addi s1,s1,1
rand_control_766:
xori s5,s2,1105
sub s5,s1,s1
sub s2,s1,s5
srli s5,s5,5
slli s1,s3,16
add s5,s2,s4
sll s2,s4,s3
add s2,s3,s3
xori s2,s2,-176
slli s4,s2,30
add s2,s3,s5
srli s4,s1,13
sub s3,s2,s4
slt s4,s5,s4
bne s2,s2,rand_control_781
addi s5,s5,1
rand_control_781:
and s1,s3,s3
srli s3,s5,26
beq s5,s5,rand_control_784
addi s4,s4,1
rand_control_784:
and s5,s2,s1
and s3,s1,s1
add s5,s2,s5
srl s1,s5,s5
add s2,s5,s1
sub s4,s4,s3
add s5,s2,s1
slli s4,s2,18
bne s3,s3,rand_control_793
addi s2,s2,1
rand_control_793:
beq s4,s4,rand_control_794
addi s3,s3,1
rand_control_794:
slli s2,s3,20
addi s5,s2,1576
xori s1,s4,-1082
slli s1,s5,31
add s4,s5,s2
sltu s4,s1,s2
sub s3,s3,s3
andi s3,s3,1937
sll s5,s5,s1
xori s3,s1,-1870
ori s2,s5,221
or s5,s4,s1
sll s1,s2,s2
or s2,s3,s5
add s5,s2,s3
sltu s2,s4,s4
sll s4,s5,s2
addi s4,s4,1048
and s3,s4,s5
and s1,s4,s1
addi s3,s5,-1905
srl s5,s5,s3
sltu s1,s3,s3
andi s5,s1,-57
or s2,s5,s2
andi s1,s2,1918
xori s1,s1,-1533
beq s3,s3,rand_control_822
addi s4,s4,1
rand_control_822:
addi s1,s1,952
andi s3,s1,-1547
andi s1,s2,1350
andi s4,s1,-273
andi s5,s2,797
addi s3,s1,-1883
srl s5,s4,s4
ori s1,s3,-1455
bne s3,s3,rand_control_831
addi s3,s3,1
rand_control_831:
bne s5,s5,rand_control_832
addi s3,s3,1
rand_control_832:
or s3,s5,s1
and s5,s1,s2
add s4,s2,s4
addi s4,s2,1335
beq s5,s5,rand_control_837
addi s1,s1,1
rand_control_837:
srli s5,s3,29
add s3,s4,s4
sltu s5,s1,s5
or s5,s4,s5
srai s2,s2,23
andi s4,s4,1015
xor s3,s3,s3
slli s3,s5,9
or s3,s5,s3
xor s2,s3,s1
add s5,s1,s3
slt s5,s3,s1
xori s3,s2,-1485
srai s5,s2,27
slli s3,s5,22
slli s2,s2,24
bne s1,s1,rand_control_854
addi s3,s3,1
rand_control_854:
srl s2,s1,s3
srl s3,s3,s1
sll s1,s1,s4
sll s2,s5,s4
srli s2,s4,11
beq s2,s2,rand_control_860
addi s4,s4,1
rand_control_860:
add s4,s5,s3
srai s5,s3,29
srl s3,s5,s4
slli s3,s1,16
bne s5,s5,rand_control_865
addi s4,s4,1
rand_control_865:
ori s5,s2,282
addi s1,s2,-674
bne s2,s2,rand_control_868
addi s3,s3,1
rand_control_868:
srai s2,s5,28
add s3,s5,s5
ori s5,s2,999
or s5,s3,s1
sub s4,s4,s4
sll s4,s5,s2
srl s1,s4,s3
slt s2,s4,s4
add s2,s4,s4
xor s1,s3,s1
addi s5,s1,920
srai s3,s2,23
bne s5,s5,rand_control_881
addi s3,s3,1
rand_control_881:
ori s5,s4,-1999
sltu s3,s1,s5
or s3,s5,s5
add s5,s1,s5
bne s2,s2,rand_control_886
addi s1,s1,1
rand_control_886:
srl s1,s5,s5
srai s3,s1,17
xor s3,s2,s3
xori s5,s2,270
ori s1,s5,-1631
srli s5,s3,19
bne s1,s1,rand_control_893
addi s3,s3,1
rand_control_893:
or s2,s5,s5
slli s3,s4,0
slt s5,s4,s2
or s5,s1,s5
sll s1,s1,s1
srl s1,s4,s5
sub s3,s3,s1
bne s5,s5,rand_control_901
addi s4,s4,1
rand_control_901:
add s2,s2,s4
add s2,s3,s2
bne s5,s5,rand_control_904
addi s2,s2,1
rand_control_904:
slli s5,s3,13
and s3,s4,s2
xor s3,s3,s2
srl s4,s4,s3
slt s5,s3,s1
bne s5,s5,rand_control_910
addi s3,s3,1
rand_control_910:
ori s5,s1,944
sub s1,s5,s2
and s1,s5,s3
ori s3,s1,1548
srai s1,s4,31
addi s3,s5,-390
beq s5,s5,rand_control_917
addi s2,s2,1
rand_control_917:
xori s3,s2,-398
srli s3,s4,27
ori s4,s3,805
slt s2,s4,s4
slli s2,s5,3
srai s1,s4,31
and s5,s4,s2
beq s2,s2,rand_control_925
addi s3,s3,1
rand_control_925:
sltu s5,s4,s1
addi s5,s3,-1901
and s5,s5,s5
sltu s2,s1,s3
beq s3,s3,rand_control_930
addi s4,s4,1
rand_control_930:
srl s4,s4,s3
xor s4,s4,s2
xor s5,s3,s2
add s3,s4,s1
xor s3,s2,s4
ori s5,s3,1324
bne s5,s5,rand_control_937
addi s3,s3,1
rand_control_937:
bne s1,s1,rand_control_938
addi s1,s1,1
rand_control_938:
and s3,s1,s3
xor s5,s5,s3
addi s2,s3,701
xori s1,s5,-151
xori s2,s5,1763
xor s3,s2,s1
or s5,s1,s3
add s4,s5,s2
sub s1,s3,s2
xor s1,s4,s4
srl s2,s4,s2
sltu s3,s2,s3
add s1,s5,s3
bne s5,s5,rand_control_952
addi s2,s2,1
rand_control_952:
xor s1,s2,s4
sub s1,s1,s2
slt s1,s4,s3
beq s1,s1,rand_control_956
addi s5,s5,1
rand_control_956:
add s5,s4,s3
xor s5,s2,s4
andi s4,s5,-674
andi s2,s3,-1624
bne s3,s3,rand_control_961
addi s1,s1,1
rand_control_961:
xor s4,s1,s4
andi s2,s2,-1435
ori s3,s3,-623
addi s5,s3,873
sll s5,s3,s1
ori s5,s3,1404
beq s1,s1,rand_control_968
addi s1,s1,1
rand_control_968:
sll s2,s4,s2
ori s2,s4,-442
bne s5,s5,rand_control_971
addi s1,s1,1
rand_control_971:
beq s5,s5,rand_control_972
addi s2,s2,1
rand_control_972:
xor s3,s1,s3
slli s1,s1,24
slt s4,s2,s4
addi s4,s3,-1988
srai s1,s1,19
srai s2,s2,7
sltu s3,s2,s3
sltu s4,s2,s4
beq s2,s2,rand_control_981
addi s5,s5,1
rand_control_981:
sll s1,s1,s5
or s3,s1,s4
ori s1,s3,-565
srai s4,s4,29
srai s2,s1,26
xor s2,s1,s1
srl s4,s4,s1
srl s1,s1,s2
addi s3,s2,815
xor s3,s1,s2
sub s5,s1,s2
ori s5,s5,-209
slli s4,s2,22
sll s2,s4,s5
srl s3,s3,s3
beq s2,s2,rand_control_997
addi s5,s5,1
rand_control_997:
add s5,s5,s4
slt s3,s4,s3
slt s5,s3,s5
beq s2,s2,rand_control_1001
addi s4,s4,1
rand_control_1001:
xori s1,s2,-1521
bne s4,s4,rand_control_1003
addi s5,s5,1
rand_control_1003:
sll s4,s4,s1
addi s2,s3,-1988
bne s1,s1,rand_control_1006
addi s3,s3,1
rand_control_1006:
bne s5,s5,rand_control_1007
addi s1,s1,1
rand_control_1007:
xori s4,s3,1559
xori s4,s4,268
or s3,s3,s2
andi s4,s2,1421
srl s1,s2,s5
beq s2,s2,rand_control_1013
addi s1,s1,1
rand_control_1013:
sll s3,s1,s5
srai s1,s1,29
sub s5,s1,s4
sub s1,s3,s5
sll s4,s5,s2
slli s2,s1,18
beq s1,s1,rand_control_1020
addi s1,s1,1
rand_control_1020:
bne s2,s2,rand_control_1021
addi s5,s5,1
rand_control_1021:
slli s1,s4,31
slt s1,s2,s3
ori s2,s2,1597
beq s3,s3,rand_control_1025
addi s4,s4,1
rand_control_1025:
or s5,s3,s1
srai s1,s3,27
srli s2,s5,0
slli s3,s5,8
srai s1,s4,12
addi s2,s5,1955
slli s2,s4,15
xori s1,s2,-469
add s5,s4,s4
xori s1,s1,-1543
xor s3,s1,s2
addi s5,s4,-947
slt s1,s2,s5
srai s2,s4,11
bne s3,s3,rand_control_1040
addi s3,s3,1
rand_control_1040:
sltu s3,s3,s2
srai s5,s3,1
srai s4,s3,18
and s2,s5,s1
andi s1,s2,1265
beq s5,s5,rand_control_1046
addi s5,s5,1
rand_control_1046:
srai s3,s2,27
add s4,s3,s3
bne s3,s3,rand_control_1049
addi s4,s4,1
rand_control_1049:
bne s2,s2,rand_control_1050
addi s5,s5,1
rand_control_1050:
slli s5,s4,10
sltu s2,s1,s4
ori s2,s5,-1184
sll s3,s1,s1
srl s3,s5,s5
sll s1,s3,s5
add s5,s5,s3
and s5,s4,s1
sll s2,s5,s5
xor s4,s1,s1
add s3,s2,s4
andi s3,s1,-1129
sub s1,s2,s2
and s3,s1,s4
slt s1,s1,s4
and s1,s5,s3
slt s2,s4,s1
add s3,s3,s2
srai s4,s4,0
addi s4,s2,-1889
xor s5,s4,s3
srli s5,s3,22
sll s5,s4,s1
addi s3,s2,302
sll s3,s2,s5
slt s2,s4,s3
sll s2,s5,s1
slli s4,s4,16
or s2,s4,s3
sub s5,s5,s1
sub s3,s3,s3
sltu s4,s4,s2
sll s1,s4,s1
sll s5,s2,s3
beq s2,s2,rand_control_1085
addi s1,s1,1
rand_control_1085:
srl s5,s4,s4
add s4,s1,s4
addi s5,s4,-554
andi s5,s5,1990
sll s1,s2,s5
beq s1,s1,rand_control_1091
addi s3,s3,1
rand_control_1091:
or s3,s2,s3
sll s5,s4,s1
xor s2,s4,s5
xor s4,s2,s1
slt s1,s3,s3
add s3,s4,s3
add s4,s3,s1
add s4,s3,s1
srli s4,s1,3
andi s4,s4,1875
xor s3,s5,s5
andi s3,s1,661
andi s4,s3,647
add s5,s1,s3
slt s1,s4,s1
sltu s5,s1,s3
sll s2,s2,s2
ori s5,s2,1847
addi s5,s1,697
srl s4,s5,s5
ori s5,s5,521
addi s3,s4,1108
slli s2,s2,13
add s5,s4,s3
add s5,s5,s1
add s2,s3,s4
srli s2,s2,30
or s5,s2,s5
bne s4,s4,rand_control_1120
addi s5,s5,1
rand_control_1120:
slli s4,s1,29
sub s5,s1,s1
sll s5,s3,s1
srai s1,s4,21
slt s3,s5,s5
beq s1,s1,rand_control_1126
addi s5,s5,1
rand_control_1126:
srl s2,s4,s3
slli s3,s5,13
andi s1,s1,617
ori s3,s5,-1350
add s1,s3,s3
ori s1,s3,722
or s1,s1,s2
srai s4,s3,31
bne s2,s2,rand_control_1135
addi s2,s2,1
rand_control_1135:
srl s3,s3,s5
and s5,s3,s4
beq s3,s3,rand_control_1138
addi s5,s5,1
rand_control_1138:
add s1,s5,s2
sll s1,s5,s2
ori s1,s4,1346
sub s2,s4,s5
srli s3,s2,1
slli s5,s4,27
srli s1,s1,13
sub s2,s1,s3
ori s1,s2,1583
bne s1,s1,rand_control_1148
addi s2,s2,1
rand_control_1148:
xor s4,s1,s3
beq s4,s4,rand_control_1150
addi s1,s1,1
rand_control_1150:
sll s3,s5,s3
sub s4,s4,s4
slli s4,s5,14
addi s4,s1,-1265
and s2,s1,s5
xor s2,s4,s4
sub s1,s4,s3
sll s1,s4,s5
sll s3,s4,s4
sll s4,s3,s2
andi s2,s1,-1802
sltu s4,s2,s2
add s2,s1,s2
srli s5,s2,2
addi s1,s2,1287
xori s5,s4,-514
ori s4,s4,-825
add s2,s1,s4
add s4,s5,s5
bne s4,s4,rand_control_1170
addi s4,s4,1
rand_control_1170:
xori s5,s3,-1185
srl s4,s1,s4
sub s3,s5,s4
sll s5,s5,s4
srl s1,s3,s2
xor s4,s3,s4
xori s1,s2,1163
xor s2,s3,s5
srai s3,s1,0
sll s2,s3,s2
sltu s1,s1,s4
beq s3,s3,rand_control_1182
addi s3,s3,1
rand_control_1182:
addi s4,s1,-41
bne s3,s3,rand_control_1184
addi s5,s5,1
rand_control_1184:
srl s4,s5,s2
sltu s1,s2,s5
ori s2,s2,493
beq s2,s2,rand_control_1188
addi s4,s4,1
rand_control_1188:
srai s1,s4,27
or s5,s5,s4
srai s2,s5,6
slt s2,s3,s3
ori s1,s3,-311
xor s2,s1,s4
xor s3,s2,s1
bne s4,s4,rand_control_1196
addi s1,s1,1
rand_control_1196:
addi s5,s2,-1073
bne s4,s4,rand_control_1198
addi s2,s2,1
rand_control_1198:
sll s2,s5,s5

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

