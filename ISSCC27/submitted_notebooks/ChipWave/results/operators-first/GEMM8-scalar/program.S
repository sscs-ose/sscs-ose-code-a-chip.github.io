lui x20, 0x80010
addi x20, x20, 0
lui x21, 0x80010
addi x21, x21, 64
lui x22, 0x80020
addi x22, x22, 0
addi x8, x0, 0
lb x10, x20, 0
lb x11, x21, 0
jal x1, mul8
add x8, x8, x5
lb x10, x20, 1
lb x11, x21, 8
jal x1, mul8
add x8, x8, x5
lb x10, x20, 2
lb x11, x21, 16
jal x1, mul8
add x8, x8, x5
lb x10, x20, 3
lb x11, x21, 24
jal x1, mul8
add x8, x8, x5
lb x10, x20, 4
lb x11, x21, 32
jal x1, mul8
add x8, x8, x5
lb x10, x20, 5
lb x11, x21, 40
jal x1, mul8
add x8, x8, x5
lb x10, x20, 6
lb x11, x21, 48
jal x1, mul8
add x8, x8, x5
lb x10, x20, 7
lb x11, x21, 56
jal x1, mul8
add x8, x8, x5
sw x8, 0(x22)
addi x8, x0, 0
lb x10, x20, 0
lb x11, x21, 1
jal x1, mul8
add x8, x8, x5
lb x10, x20, 1
lb x11, x21, 9
jal x1, mul8
add x8, x8, x5
lb x10, x20, 2
lb x11, x21, 17
jal x1, mul8
add x8, x8, x5
lb x10, x20, 3
lb x11, x21, 25
jal x1, mul8
add x8, x8, x5
lb x10, x20, 4
lb x11, x21, 33
jal x1, mul8
add x8, x8, x5
lb x10, x20, 5
lb x11, x21, 41
jal x1, mul8
add x8, x8, x5
lb x10, x20, 6
lb x11, x21, 49
jal x1, mul8
add x8, x8, x5
lb x10, x20, 7
lb x11, x21, 57
jal x1, mul8
add x8, x8, x5
sw x8, 4(x22)
addi x8, x0, 0
lb x10, x20, 0
lb x11, x21, 2
jal x1, mul8
add x8, x8, x5
lb x10, x20, 1
lb x11, x21, 10
jal x1, mul8
add x8, x8, x5
lb x10, x20, 2
lb x11, x21, 18
jal x1, mul8
add x8, x8, x5
lb x10, x20, 3
lb x11, x21, 26
jal x1, mul8
add x8, x8, x5
lb x10, x20, 4
lb x11, x21, 34
jal x1, mul8
add x8, x8, x5
lb x10, x20, 5
lb x11, x21, 42
jal x1, mul8
add x8, x8, x5
lb x10, x20, 6
lb x11, x21, 50
jal x1, mul8
add x8, x8, x5
lb x10, x20, 7
lb x11, x21, 58
jal x1, mul8
add x8, x8, x5
sw x8, 8(x22)
addi x8, x0, 0
lb x10, x20, 0
lb x11, x21, 3
jal x1, mul8
add x8, x8, x5
lb x10, x20, 1
lb x11, x21, 11
jal x1, mul8
add x8, x8, x5
lb x10, x20, 2
lb x11, x21, 19
jal x1, mul8
add x8, x8, x5
lb x10, x20, 3
lb x11, x21, 27
jal x1, mul8
add x8, x8, x5
lb x10, x20, 4
lb x11, x21, 35
jal x1, mul8
add x8, x8, x5
lb x10, x20, 5
lb x11, x21, 43
jal x1, mul8
add x8, x8, x5
lb x10, x20, 6
lb x11, x21, 51
jal x1, mul8
add x8, x8, x5
lb x10, x20, 7
lb x11, x21, 59
jal x1, mul8
add x8, x8, x5
sw x8, 12(x22)
addi x8, x0, 0
lb x10, x20, 0
lb x11, x21, 4
jal x1, mul8
add x8, x8, x5
lb x10, x20, 1
lb x11, x21, 12
jal x1, mul8
add x8, x8, x5
lb x10, x20, 2
lb x11, x21, 20
jal x1, mul8
add x8, x8, x5
lb x10, x20, 3
lb x11, x21, 28
jal x1, mul8
add x8, x8, x5
lb x10, x20, 4
lb x11, x21, 36
jal x1, mul8
add x8, x8, x5
lb x10, x20, 5
lb x11, x21, 44
jal x1, mul8
add x8, x8, x5
lb x10, x20, 6
lb x11, x21, 52
jal x1, mul8
add x8, x8, x5
lb x10, x20, 7
lb x11, x21, 60
jal x1, mul8
add x8, x8, x5
sw x8, 16(x22)
addi x8, x0, 0
lb x10, x20, 0
lb x11, x21, 5
jal x1, mul8
add x8, x8, x5
lb x10, x20, 1
lb x11, x21, 13
jal x1, mul8
add x8, x8, x5
lb x10, x20, 2
lb x11, x21, 21
jal x1, mul8
add x8, x8, x5
lb x10, x20, 3
lb x11, x21, 29
jal x1, mul8
add x8, x8, x5
lb x10, x20, 4
lb x11, x21, 37
jal x1, mul8
add x8, x8, x5
lb x10, x20, 5
lb x11, x21, 45
jal x1, mul8
add x8, x8, x5
lb x10, x20, 6
lb x11, x21, 53
jal x1, mul8
add x8, x8, x5
lb x10, x20, 7
lb x11, x21, 61
jal x1, mul8
add x8, x8, x5
sw x8, 20(x22)
addi x8, x0, 0
lb x10, x20, 0
lb x11, x21, 6
jal x1, mul8
add x8, x8, x5
lb x10, x20, 1
lb x11, x21, 14
jal x1, mul8
add x8, x8, x5
lb x10, x20, 2
lb x11, x21, 22
jal x1, mul8
add x8, x8, x5
lb x10, x20, 3
lb x11, x21, 30
jal x1, mul8
add x8, x8, x5
lb x10, x20, 4
lb x11, x21, 38
jal x1, mul8
add x8, x8, x5
lb x10, x20, 5
lb x11, x21, 46
jal x1, mul8
add x8, x8, x5
lb x10, x20, 6
lb x11, x21, 54
jal x1, mul8
add x8, x8, x5
lb x10, x20, 7
lb x11, x21, 62
jal x1, mul8
add x8, x8, x5
sw x8, 24(x22)
addi x8, x0, 0
lb x10, x20, 0
lb x11, x21, 7
jal x1, mul8
add x8, x8, x5
lb x10, x20, 1
lb x11, x21, 15
jal x1, mul8
add x8, x8, x5
lb x10, x20, 2
lb x11, x21, 23
jal x1, mul8
add x8, x8, x5
lb x10, x20, 3
lb x11, x21, 31
jal x1, mul8
add x8, x8, x5
lb x10, x20, 4
lb x11, x21, 39
jal x1, mul8
add x8, x8, x5
lb x10, x20, 5
lb x11, x21, 47
jal x1, mul8
add x8, x8, x5
lb x10, x20, 6
lb x11, x21, 55
jal x1, mul8
add x8, x8, x5
lb x10, x20, 7
lb x11, x21, 63
jal x1, mul8
add x8, x8, x5
sw x8, 28(x22)
addi x8, x0, 0
lb x10, x20, 8
lb x11, x21, 0
jal x1, mul8
add x8, x8, x5
lb x10, x20, 9
lb x11, x21, 8
jal x1, mul8
add x8, x8, x5
lb x10, x20, 10
lb x11, x21, 16
jal x1, mul8
add x8, x8, x5
lb x10, x20, 11
lb x11, x21, 24
jal x1, mul8
add x8, x8, x5
lb x10, x20, 12
lb x11, x21, 32
jal x1, mul8
add x8, x8, x5
lb x10, x20, 13
lb x11, x21, 40
jal x1, mul8
add x8, x8, x5
lb x10, x20, 14
lb x11, x21, 48
jal x1, mul8
add x8, x8, x5
lb x10, x20, 15
lb x11, x21, 56
jal x1, mul8
add x8, x8, x5
sw x8, 32(x22)
addi x8, x0, 0
lb x10, x20, 8
lb x11, x21, 1
jal x1, mul8
add x8, x8, x5
lb x10, x20, 9
lb x11, x21, 9
jal x1, mul8
add x8, x8, x5
lb x10, x20, 10
lb x11, x21, 17
jal x1, mul8
add x8, x8, x5
lb x10, x20, 11
lb x11, x21, 25
jal x1, mul8
add x8, x8, x5
lb x10, x20, 12
lb x11, x21, 33
jal x1, mul8
add x8, x8, x5
lb x10, x20, 13
lb x11, x21, 41
jal x1, mul8
add x8, x8, x5
lb x10, x20, 14
lb x11, x21, 49
jal x1, mul8
add x8, x8, x5
lb x10, x20, 15
lb x11, x21, 57
jal x1, mul8
add x8, x8, x5
sw x8, 36(x22)
addi x8, x0, 0
lb x10, x20, 8
lb x11, x21, 2
jal x1, mul8
add x8, x8, x5
lb x10, x20, 9
lb x11, x21, 10
jal x1, mul8
add x8, x8, x5
lb x10, x20, 10
lb x11, x21, 18
jal x1, mul8
add x8, x8, x5
lb x10, x20, 11
lb x11, x21, 26
jal x1, mul8
add x8, x8, x5
lb x10, x20, 12
lb x11, x21, 34
jal x1, mul8
add x8, x8, x5
lb x10, x20, 13
lb x11, x21, 42
jal x1, mul8
add x8, x8, x5
lb x10, x20, 14
lb x11, x21, 50
jal x1, mul8
add x8, x8, x5
lb x10, x20, 15
lb x11, x21, 58
jal x1, mul8
add x8, x8, x5
sw x8, 40(x22)
addi x8, x0, 0
lb x10, x20, 8
lb x11, x21, 3
jal x1, mul8
add x8, x8, x5
lb x10, x20, 9
lb x11, x21, 11
jal x1, mul8
add x8, x8, x5
lb x10, x20, 10
lb x11, x21, 19
jal x1, mul8
add x8, x8, x5
lb x10, x20, 11
lb x11, x21, 27
jal x1, mul8
add x8, x8, x5
lb x10, x20, 12
lb x11, x21, 35
jal x1, mul8
add x8, x8, x5
lb x10, x20, 13
lb x11, x21, 43
jal x1, mul8
add x8, x8, x5
lb x10, x20, 14
lb x11, x21, 51
jal x1, mul8
add x8, x8, x5
lb x10, x20, 15
lb x11, x21, 59
jal x1, mul8
add x8, x8, x5
sw x8, 44(x22)
addi x8, x0, 0
lb x10, x20, 8
lb x11, x21, 4
jal x1, mul8
add x8, x8, x5
lb x10, x20, 9
lb x11, x21, 12
jal x1, mul8
add x8, x8, x5
lb x10, x20, 10
lb x11, x21, 20
jal x1, mul8
add x8, x8, x5
lb x10, x20, 11
lb x11, x21, 28
jal x1, mul8
add x8, x8, x5
lb x10, x20, 12
lb x11, x21, 36
jal x1, mul8
add x8, x8, x5
lb x10, x20, 13
lb x11, x21, 44
jal x1, mul8
add x8, x8, x5
lb x10, x20, 14
lb x11, x21, 52
jal x1, mul8
add x8, x8, x5
lb x10, x20, 15
lb x11, x21, 60
jal x1, mul8
add x8, x8, x5
sw x8, 48(x22)
addi x8, x0, 0
lb x10, x20, 8
lb x11, x21, 5
jal x1, mul8
add x8, x8, x5
lb x10, x20, 9
lb x11, x21, 13
jal x1, mul8
add x8, x8, x5
lb x10, x20, 10
lb x11, x21, 21
jal x1, mul8
add x8, x8, x5
lb x10, x20, 11
lb x11, x21, 29
jal x1, mul8
add x8, x8, x5
lb x10, x20, 12
lb x11, x21, 37
jal x1, mul8
add x8, x8, x5
lb x10, x20, 13
lb x11, x21, 45
jal x1, mul8
add x8, x8, x5
lb x10, x20, 14
lb x11, x21, 53
jal x1, mul8
add x8, x8, x5
lb x10, x20, 15
lb x11, x21, 61
jal x1, mul8
add x8, x8, x5
sw x8, 52(x22)
addi x8, x0, 0
lb x10, x20, 8
lb x11, x21, 6
jal x1, mul8
add x8, x8, x5
lb x10, x20, 9
lb x11, x21, 14
jal x1, mul8
add x8, x8, x5
lb x10, x20, 10
lb x11, x21, 22
jal x1, mul8
add x8, x8, x5
lb x10, x20, 11
lb x11, x21, 30
jal x1, mul8
add x8, x8, x5
lb x10, x20, 12
lb x11, x21, 38
jal x1, mul8
add x8, x8, x5
lb x10, x20, 13
lb x11, x21, 46
jal x1, mul8
add x8, x8, x5
lb x10, x20, 14
lb x11, x21, 54
jal x1, mul8
add x8, x8, x5
lb x10, x20, 15
lb x11, x21, 62
jal x1, mul8
add x8, x8, x5
sw x8, 56(x22)
addi x8, x0, 0
lb x10, x20, 8
lb x11, x21, 7
jal x1, mul8
add x8, x8, x5
lb x10, x20, 9
lb x11, x21, 15
jal x1, mul8
add x8, x8, x5
lb x10, x20, 10
lb x11, x21, 23
jal x1, mul8
add x8, x8, x5
lb x10, x20, 11
lb x11, x21, 31
jal x1, mul8
add x8, x8, x5
lb x10, x20, 12
lb x11, x21, 39
jal x1, mul8
add x8, x8, x5
lb x10, x20, 13
lb x11, x21, 47
jal x1, mul8
add x8, x8, x5
lb x10, x20, 14
lb x11, x21, 55
jal x1, mul8
add x8, x8, x5
lb x10, x20, 15
lb x11, x21, 63
jal x1, mul8
add x8, x8, x5
sw x8, 60(x22)
addi x8, x0, 0
lb x10, x20, 16
lb x11, x21, 0
jal x1, mul8
add x8, x8, x5
lb x10, x20, 17
lb x11, x21, 8
jal x1, mul8
add x8, x8, x5
lb x10, x20, 18
lb x11, x21, 16
jal x1, mul8
add x8, x8, x5
lb x10, x20, 19
lb x11, x21, 24
jal x1, mul8
add x8, x8, x5
lb x10, x20, 20
lb x11, x21, 32
jal x1, mul8
add x8, x8, x5
lb x10, x20, 21
lb x11, x21, 40
jal x1, mul8
add x8, x8, x5
lb x10, x20, 22
lb x11, x21, 48
jal x1, mul8
add x8, x8, x5
lb x10, x20, 23
lb x11, x21, 56
jal x1, mul8
add x8, x8, x5
sw x8, 64(x22)
addi x8, x0, 0
lb x10, x20, 16
lb x11, x21, 1
jal x1, mul8
add x8, x8, x5
lb x10, x20, 17
lb x11, x21, 9
jal x1, mul8
add x8, x8, x5
lb x10, x20, 18
lb x11, x21, 17
jal x1, mul8
add x8, x8, x5
lb x10, x20, 19
lb x11, x21, 25
jal x1, mul8
add x8, x8, x5
lb x10, x20, 20
lb x11, x21, 33
jal x1, mul8
add x8, x8, x5
lb x10, x20, 21
lb x11, x21, 41
jal x1, mul8
add x8, x8, x5
lb x10, x20, 22
lb x11, x21, 49
jal x1, mul8
add x8, x8, x5
lb x10, x20, 23
lb x11, x21, 57
jal x1, mul8
add x8, x8, x5
sw x8, 68(x22)
addi x8, x0, 0
lb x10, x20, 16
lb x11, x21, 2
jal x1, mul8
add x8, x8, x5
lb x10, x20, 17
lb x11, x21, 10
jal x1, mul8
add x8, x8, x5
lb x10, x20, 18
lb x11, x21, 18
jal x1, mul8
add x8, x8, x5
lb x10, x20, 19
lb x11, x21, 26
jal x1, mul8
add x8, x8, x5
lb x10, x20, 20
lb x11, x21, 34
jal x1, mul8
add x8, x8, x5
lb x10, x20, 21
lb x11, x21, 42
jal x1, mul8
add x8, x8, x5
lb x10, x20, 22
lb x11, x21, 50
jal x1, mul8
add x8, x8, x5
lb x10, x20, 23
lb x11, x21, 58
jal x1, mul8
add x8, x8, x5
sw x8, 72(x22)
addi x8, x0, 0
lb x10, x20, 16
lb x11, x21, 3
jal x1, mul8
add x8, x8, x5
lb x10, x20, 17
lb x11, x21, 11
jal x1, mul8
add x8, x8, x5
lb x10, x20, 18
lb x11, x21, 19
jal x1, mul8
add x8, x8, x5
lb x10, x20, 19
lb x11, x21, 27
jal x1, mul8
add x8, x8, x5
lb x10, x20, 20
lb x11, x21, 35
jal x1, mul8
add x8, x8, x5
lb x10, x20, 21
lb x11, x21, 43
jal x1, mul8
add x8, x8, x5
lb x10, x20, 22
lb x11, x21, 51
jal x1, mul8
add x8, x8, x5
lb x10, x20, 23
lb x11, x21, 59
jal x1, mul8
add x8, x8, x5
sw x8, 76(x22)
addi x8, x0, 0
lb x10, x20, 16
lb x11, x21, 4
jal x1, mul8
add x8, x8, x5
lb x10, x20, 17
lb x11, x21, 12
jal x1, mul8
add x8, x8, x5
lb x10, x20, 18
lb x11, x21, 20
jal x1, mul8
add x8, x8, x5
lb x10, x20, 19
lb x11, x21, 28
jal x1, mul8
add x8, x8, x5
lb x10, x20, 20
lb x11, x21, 36
jal x1, mul8
add x8, x8, x5
lb x10, x20, 21
lb x11, x21, 44
jal x1, mul8
add x8, x8, x5
lb x10, x20, 22
lb x11, x21, 52
jal x1, mul8
add x8, x8, x5
lb x10, x20, 23
lb x11, x21, 60
jal x1, mul8
add x8, x8, x5
sw x8, 80(x22)
addi x8, x0, 0
lb x10, x20, 16
lb x11, x21, 5
jal x1, mul8
add x8, x8, x5
lb x10, x20, 17
lb x11, x21, 13
jal x1, mul8
add x8, x8, x5
lb x10, x20, 18
lb x11, x21, 21
jal x1, mul8
add x8, x8, x5
lb x10, x20, 19
lb x11, x21, 29
jal x1, mul8
add x8, x8, x5
lb x10, x20, 20
lb x11, x21, 37
jal x1, mul8
add x8, x8, x5
lb x10, x20, 21
lb x11, x21, 45
jal x1, mul8
add x8, x8, x5
lb x10, x20, 22
lb x11, x21, 53
jal x1, mul8
add x8, x8, x5
lb x10, x20, 23
lb x11, x21, 61
jal x1, mul8
add x8, x8, x5
sw x8, 84(x22)
addi x8, x0, 0
lb x10, x20, 16
lb x11, x21, 6
jal x1, mul8
add x8, x8, x5
lb x10, x20, 17
lb x11, x21, 14
jal x1, mul8
add x8, x8, x5
lb x10, x20, 18
lb x11, x21, 22
jal x1, mul8
add x8, x8, x5
lb x10, x20, 19
lb x11, x21, 30
jal x1, mul8
add x8, x8, x5
lb x10, x20, 20
lb x11, x21, 38
jal x1, mul8
add x8, x8, x5
lb x10, x20, 21
lb x11, x21, 46
jal x1, mul8
add x8, x8, x5
lb x10, x20, 22
lb x11, x21, 54
jal x1, mul8
add x8, x8, x5
lb x10, x20, 23
lb x11, x21, 62
jal x1, mul8
add x8, x8, x5
sw x8, 88(x22)
addi x8, x0, 0
lb x10, x20, 16
lb x11, x21, 7
jal x1, mul8
add x8, x8, x5
lb x10, x20, 17
lb x11, x21, 15
jal x1, mul8
add x8, x8, x5
lb x10, x20, 18
lb x11, x21, 23
jal x1, mul8
add x8, x8, x5
lb x10, x20, 19
lb x11, x21, 31
jal x1, mul8
add x8, x8, x5
lb x10, x20, 20
lb x11, x21, 39
jal x1, mul8
add x8, x8, x5
lb x10, x20, 21
lb x11, x21, 47
jal x1, mul8
add x8, x8, x5
lb x10, x20, 22
lb x11, x21, 55
jal x1, mul8
add x8, x8, x5
lb x10, x20, 23
lb x11, x21, 63
jal x1, mul8
add x8, x8, x5
sw x8, 92(x22)
addi x8, x0, 0
lb x10, x20, 24
lb x11, x21, 0
jal x1, mul8
add x8, x8, x5
lb x10, x20, 25
lb x11, x21, 8
jal x1, mul8
add x8, x8, x5
lb x10, x20, 26
lb x11, x21, 16
jal x1, mul8
add x8, x8, x5
lb x10, x20, 27
lb x11, x21, 24
jal x1, mul8
add x8, x8, x5
lb x10, x20, 28
lb x11, x21, 32
jal x1, mul8
add x8, x8, x5
lb x10, x20, 29
lb x11, x21, 40
jal x1, mul8
add x8, x8, x5
lb x10, x20, 30
lb x11, x21, 48
jal x1, mul8
add x8, x8, x5
lb x10, x20, 31
lb x11, x21, 56
jal x1, mul8
add x8, x8, x5
sw x8, 96(x22)
addi x8, x0, 0
lb x10, x20, 24
lb x11, x21, 1
jal x1, mul8
add x8, x8, x5
lb x10, x20, 25
lb x11, x21, 9
jal x1, mul8
add x8, x8, x5
lb x10, x20, 26
lb x11, x21, 17
jal x1, mul8
add x8, x8, x5
lb x10, x20, 27
lb x11, x21, 25
jal x1, mul8
add x8, x8, x5
lb x10, x20, 28
lb x11, x21, 33
jal x1, mul8
add x8, x8, x5
lb x10, x20, 29
lb x11, x21, 41
jal x1, mul8
add x8, x8, x5
lb x10, x20, 30
lb x11, x21, 49
jal x1, mul8
add x8, x8, x5
lb x10, x20, 31
lb x11, x21, 57
jal x1, mul8
add x8, x8, x5
sw x8, 100(x22)
addi x8, x0, 0
lb x10, x20, 24
lb x11, x21, 2
jal x1, mul8
add x8, x8, x5
lb x10, x20, 25
lb x11, x21, 10
jal x1, mul8
add x8, x8, x5
lb x10, x20, 26
lb x11, x21, 18
jal x1, mul8
add x8, x8, x5
lb x10, x20, 27
lb x11, x21, 26
jal x1, mul8
add x8, x8, x5
lb x10, x20, 28
lb x11, x21, 34
jal x1, mul8
add x8, x8, x5
lb x10, x20, 29
lb x11, x21, 42
jal x1, mul8
add x8, x8, x5
lb x10, x20, 30
lb x11, x21, 50
jal x1, mul8
add x8, x8, x5
lb x10, x20, 31
lb x11, x21, 58
jal x1, mul8
add x8, x8, x5
sw x8, 104(x22)
addi x8, x0, 0
lb x10, x20, 24
lb x11, x21, 3
jal x1, mul8
add x8, x8, x5
lb x10, x20, 25
lb x11, x21, 11
jal x1, mul8
add x8, x8, x5
lb x10, x20, 26
lb x11, x21, 19
jal x1, mul8
add x8, x8, x5
lb x10, x20, 27
lb x11, x21, 27
jal x1, mul8
add x8, x8, x5
lb x10, x20, 28
lb x11, x21, 35
jal x1, mul8
add x8, x8, x5
lb x10, x20, 29
lb x11, x21, 43
jal x1, mul8
add x8, x8, x5
lb x10, x20, 30
lb x11, x21, 51
jal x1, mul8
add x8, x8, x5
lb x10, x20, 31
lb x11, x21, 59
jal x1, mul8
add x8, x8, x5
sw x8, 108(x22)
addi x8, x0, 0
lb x10, x20, 24
lb x11, x21, 4
jal x1, mul8
add x8, x8, x5
lb x10, x20, 25
lb x11, x21, 12
jal x1, mul8
add x8, x8, x5
lb x10, x20, 26
lb x11, x21, 20
jal x1, mul8
add x8, x8, x5
lb x10, x20, 27
lb x11, x21, 28
jal x1, mul8
add x8, x8, x5
lb x10, x20, 28
lb x11, x21, 36
jal x1, mul8
add x8, x8, x5
lb x10, x20, 29
lb x11, x21, 44
jal x1, mul8
add x8, x8, x5
lb x10, x20, 30
lb x11, x21, 52
jal x1, mul8
add x8, x8, x5
lb x10, x20, 31
lb x11, x21, 60
jal x1, mul8
add x8, x8, x5
sw x8, 112(x22)
addi x8, x0, 0
lb x10, x20, 24
lb x11, x21, 5
jal x1, mul8
add x8, x8, x5
lb x10, x20, 25
lb x11, x21, 13
jal x1, mul8
add x8, x8, x5
lb x10, x20, 26
lb x11, x21, 21
jal x1, mul8
add x8, x8, x5
lb x10, x20, 27
lb x11, x21, 29
jal x1, mul8
add x8, x8, x5
lb x10, x20, 28
lb x11, x21, 37
jal x1, mul8
add x8, x8, x5
lb x10, x20, 29
lb x11, x21, 45
jal x1, mul8
add x8, x8, x5
lb x10, x20, 30
lb x11, x21, 53
jal x1, mul8
add x8, x8, x5
lb x10, x20, 31
lb x11, x21, 61
jal x1, mul8
add x8, x8, x5
sw x8, 116(x22)
addi x8, x0, 0
lb x10, x20, 24
lb x11, x21, 6
jal x1, mul8
add x8, x8, x5
lb x10, x20, 25
lb x11, x21, 14
jal x1, mul8
add x8, x8, x5
lb x10, x20, 26
lb x11, x21, 22
jal x1, mul8
add x8, x8, x5
lb x10, x20, 27
lb x11, x21, 30
jal x1, mul8
add x8, x8, x5
lb x10, x20, 28
lb x11, x21, 38
jal x1, mul8
add x8, x8, x5
lb x10, x20, 29
lb x11, x21, 46
jal x1, mul8
add x8, x8, x5
lb x10, x20, 30
lb x11, x21, 54
jal x1, mul8
add x8, x8, x5
lb x10, x20, 31
lb x11, x21, 62
jal x1, mul8
add x8, x8, x5
sw x8, 120(x22)
addi x8, x0, 0
lb x10, x20, 24
lb x11, x21, 7
jal x1, mul8
add x8, x8, x5
lb x10, x20, 25
lb x11, x21, 15
jal x1, mul8
add x8, x8, x5
lb x10, x20, 26
lb x11, x21, 23
jal x1, mul8
add x8, x8, x5
lb x10, x20, 27
lb x11, x21, 31
jal x1, mul8
add x8, x8, x5
lb x10, x20, 28
lb x11, x21, 39
jal x1, mul8
add x8, x8, x5
lb x10, x20, 29
lb x11, x21, 47
jal x1, mul8
add x8, x8, x5
lb x10, x20, 30
lb x11, x21, 55
jal x1, mul8
add x8, x8, x5
lb x10, x20, 31
lb x11, x21, 63
jal x1, mul8
add x8, x8, x5
sw x8, 124(x22)
addi x8, x0, 0
lb x10, x20, 32
lb x11, x21, 0
jal x1, mul8
add x8, x8, x5
lb x10, x20, 33
lb x11, x21, 8
jal x1, mul8
add x8, x8, x5
lb x10, x20, 34
lb x11, x21, 16
jal x1, mul8
add x8, x8, x5
lb x10, x20, 35
lb x11, x21, 24
jal x1, mul8
add x8, x8, x5
lb x10, x20, 36
lb x11, x21, 32
jal x1, mul8
add x8, x8, x5
lb x10, x20, 37
lb x11, x21, 40
jal x1, mul8
add x8, x8, x5
lb x10, x20, 38
lb x11, x21, 48
jal x1, mul8
add x8, x8, x5
lb x10, x20, 39
lb x11, x21, 56
jal x1, mul8
add x8, x8, x5
sw x8, 128(x22)
addi x8, x0, 0
lb x10, x20, 32
lb x11, x21, 1
jal x1, mul8
add x8, x8, x5
lb x10, x20, 33
lb x11, x21, 9
jal x1, mul8
add x8, x8, x5
lb x10, x20, 34
lb x11, x21, 17
jal x1, mul8
add x8, x8, x5
lb x10, x20, 35
lb x11, x21, 25
jal x1, mul8
add x8, x8, x5
lb x10, x20, 36
lb x11, x21, 33
jal x1, mul8
add x8, x8, x5
lb x10, x20, 37
lb x11, x21, 41
jal x1, mul8
add x8, x8, x5
lb x10, x20, 38
lb x11, x21, 49
jal x1, mul8
add x8, x8, x5
lb x10, x20, 39
lb x11, x21, 57
jal x1, mul8
add x8, x8, x5
sw x8, 132(x22)
addi x8, x0, 0
lb x10, x20, 32
lb x11, x21, 2
jal x1, mul8
add x8, x8, x5
lb x10, x20, 33
lb x11, x21, 10
jal x1, mul8
add x8, x8, x5
lb x10, x20, 34
lb x11, x21, 18
jal x1, mul8
add x8, x8, x5
lb x10, x20, 35
lb x11, x21, 26
jal x1, mul8
add x8, x8, x5
lb x10, x20, 36
lb x11, x21, 34
jal x1, mul8
add x8, x8, x5
lb x10, x20, 37
lb x11, x21, 42
jal x1, mul8
add x8, x8, x5
lb x10, x20, 38
lb x11, x21, 50
jal x1, mul8
add x8, x8, x5
lb x10, x20, 39
lb x11, x21, 58
jal x1, mul8
add x8, x8, x5
sw x8, 136(x22)
addi x8, x0, 0
lb x10, x20, 32
lb x11, x21, 3
jal x1, mul8
add x8, x8, x5
lb x10, x20, 33
lb x11, x21, 11
jal x1, mul8
add x8, x8, x5
lb x10, x20, 34
lb x11, x21, 19
jal x1, mul8
add x8, x8, x5
lb x10, x20, 35
lb x11, x21, 27
jal x1, mul8
add x8, x8, x5
lb x10, x20, 36
lb x11, x21, 35
jal x1, mul8
add x8, x8, x5
lb x10, x20, 37
lb x11, x21, 43
jal x1, mul8
add x8, x8, x5
lb x10, x20, 38
lb x11, x21, 51
jal x1, mul8
add x8, x8, x5
lb x10, x20, 39
lb x11, x21, 59
jal x1, mul8
add x8, x8, x5
sw x8, 140(x22)
addi x8, x0, 0
lb x10, x20, 32
lb x11, x21, 4
jal x1, mul8
add x8, x8, x5
lb x10, x20, 33
lb x11, x21, 12
jal x1, mul8
add x8, x8, x5
lb x10, x20, 34
lb x11, x21, 20
jal x1, mul8
add x8, x8, x5
lb x10, x20, 35
lb x11, x21, 28
jal x1, mul8
add x8, x8, x5
lb x10, x20, 36
lb x11, x21, 36
jal x1, mul8
add x8, x8, x5
lb x10, x20, 37
lb x11, x21, 44
jal x1, mul8
add x8, x8, x5
lb x10, x20, 38
lb x11, x21, 52
jal x1, mul8
add x8, x8, x5
lb x10, x20, 39
lb x11, x21, 60
jal x1, mul8
add x8, x8, x5
sw x8, 144(x22)
addi x8, x0, 0
lb x10, x20, 32
lb x11, x21, 5
jal x1, mul8
add x8, x8, x5
lb x10, x20, 33
lb x11, x21, 13
jal x1, mul8
add x8, x8, x5
lb x10, x20, 34
lb x11, x21, 21
jal x1, mul8
add x8, x8, x5
lb x10, x20, 35
lb x11, x21, 29
jal x1, mul8
add x8, x8, x5
lb x10, x20, 36
lb x11, x21, 37
jal x1, mul8
add x8, x8, x5
lb x10, x20, 37
lb x11, x21, 45
jal x1, mul8
add x8, x8, x5
lb x10, x20, 38
lb x11, x21, 53
jal x1, mul8
add x8, x8, x5
lb x10, x20, 39
lb x11, x21, 61
jal x1, mul8
add x8, x8, x5
sw x8, 148(x22)
addi x8, x0, 0
lb x10, x20, 32
lb x11, x21, 6
jal x1, mul8
add x8, x8, x5
lb x10, x20, 33
lb x11, x21, 14
jal x1, mul8
add x8, x8, x5
lb x10, x20, 34
lb x11, x21, 22
jal x1, mul8
add x8, x8, x5
lb x10, x20, 35
lb x11, x21, 30
jal x1, mul8
add x8, x8, x5
lb x10, x20, 36
lb x11, x21, 38
jal x1, mul8
add x8, x8, x5
lb x10, x20, 37
lb x11, x21, 46
jal x1, mul8
add x8, x8, x5
lb x10, x20, 38
lb x11, x21, 54
jal x1, mul8
add x8, x8, x5
lb x10, x20, 39
lb x11, x21, 62
jal x1, mul8
add x8, x8, x5
sw x8, 152(x22)
addi x8, x0, 0
lb x10, x20, 32
lb x11, x21, 7
jal x1, mul8
add x8, x8, x5
lb x10, x20, 33
lb x11, x21, 15
jal x1, mul8
add x8, x8, x5
lb x10, x20, 34
lb x11, x21, 23
jal x1, mul8
add x8, x8, x5
lb x10, x20, 35
lb x11, x21, 31
jal x1, mul8
add x8, x8, x5
lb x10, x20, 36
lb x11, x21, 39
jal x1, mul8
add x8, x8, x5
lb x10, x20, 37
lb x11, x21, 47
jal x1, mul8
add x8, x8, x5
lb x10, x20, 38
lb x11, x21, 55
jal x1, mul8
add x8, x8, x5
lb x10, x20, 39
lb x11, x21, 63
jal x1, mul8
add x8, x8, x5
sw x8, 156(x22)
addi x8, x0, 0
lb x10, x20, 40
lb x11, x21, 0
jal x1, mul8
add x8, x8, x5
lb x10, x20, 41
lb x11, x21, 8
jal x1, mul8
add x8, x8, x5
lb x10, x20, 42
lb x11, x21, 16
jal x1, mul8
add x8, x8, x5
lb x10, x20, 43
lb x11, x21, 24
jal x1, mul8
add x8, x8, x5
lb x10, x20, 44
lb x11, x21, 32
jal x1, mul8
add x8, x8, x5
lb x10, x20, 45
lb x11, x21, 40
jal x1, mul8
add x8, x8, x5
lb x10, x20, 46
lb x11, x21, 48
jal x1, mul8
add x8, x8, x5
lb x10, x20, 47
lb x11, x21, 56
jal x1, mul8
add x8, x8, x5
sw x8, 160(x22)
addi x8, x0, 0
lb x10, x20, 40
lb x11, x21, 1
jal x1, mul8
add x8, x8, x5
lb x10, x20, 41
lb x11, x21, 9
jal x1, mul8
add x8, x8, x5
lb x10, x20, 42
lb x11, x21, 17
jal x1, mul8
add x8, x8, x5
lb x10, x20, 43
lb x11, x21, 25
jal x1, mul8
add x8, x8, x5
lb x10, x20, 44
lb x11, x21, 33
jal x1, mul8
add x8, x8, x5
lb x10, x20, 45
lb x11, x21, 41
jal x1, mul8
add x8, x8, x5
lb x10, x20, 46
lb x11, x21, 49
jal x1, mul8
add x8, x8, x5
lb x10, x20, 47
lb x11, x21, 57
jal x1, mul8
add x8, x8, x5
sw x8, 164(x22)
addi x8, x0, 0
lb x10, x20, 40
lb x11, x21, 2
jal x1, mul8
add x8, x8, x5
lb x10, x20, 41
lb x11, x21, 10
jal x1, mul8
add x8, x8, x5
lb x10, x20, 42
lb x11, x21, 18
jal x1, mul8
add x8, x8, x5
lb x10, x20, 43
lb x11, x21, 26
jal x1, mul8
add x8, x8, x5
lb x10, x20, 44
lb x11, x21, 34
jal x1, mul8
add x8, x8, x5
lb x10, x20, 45
lb x11, x21, 42
jal x1, mul8
add x8, x8, x5
lb x10, x20, 46
lb x11, x21, 50
jal x1, mul8
add x8, x8, x5
lb x10, x20, 47
lb x11, x21, 58
jal x1, mul8
add x8, x8, x5
sw x8, 168(x22)
addi x8, x0, 0
lb x10, x20, 40
lb x11, x21, 3
jal x1, mul8
add x8, x8, x5
lb x10, x20, 41
lb x11, x21, 11
jal x1, mul8
add x8, x8, x5
lb x10, x20, 42
lb x11, x21, 19
jal x1, mul8
add x8, x8, x5
lb x10, x20, 43
lb x11, x21, 27
jal x1, mul8
add x8, x8, x5
lb x10, x20, 44
lb x11, x21, 35
jal x1, mul8
add x8, x8, x5
lb x10, x20, 45
lb x11, x21, 43
jal x1, mul8
add x8, x8, x5
lb x10, x20, 46
lb x11, x21, 51
jal x1, mul8
add x8, x8, x5
lb x10, x20, 47
lb x11, x21, 59
jal x1, mul8
add x8, x8, x5
sw x8, 172(x22)
addi x8, x0, 0
lb x10, x20, 40
lb x11, x21, 4
jal x1, mul8
add x8, x8, x5
lb x10, x20, 41
lb x11, x21, 12
jal x1, mul8
add x8, x8, x5
lb x10, x20, 42
lb x11, x21, 20
jal x1, mul8
add x8, x8, x5
lb x10, x20, 43
lb x11, x21, 28
jal x1, mul8
add x8, x8, x5
lb x10, x20, 44
lb x11, x21, 36
jal x1, mul8
add x8, x8, x5
lb x10, x20, 45
lb x11, x21, 44
jal x1, mul8
add x8, x8, x5
lb x10, x20, 46
lb x11, x21, 52
jal x1, mul8
add x8, x8, x5
lb x10, x20, 47
lb x11, x21, 60
jal x1, mul8
add x8, x8, x5
sw x8, 176(x22)
addi x8, x0, 0
lb x10, x20, 40
lb x11, x21, 5
jal x1, mul8
add x8, x8, x5
lb x10, x20, 41
lb x11, x21, 13
jal x1, mul8
add x8, x8, x5
lb x10, x20, 42
lb x11, x21, 21
jal x1, mul8
add x8, x8, x5
lb x10, x20, 43
lb x11, x21, 29
jal x1, mul8
add x8, x8, x5
lb x10, x20, 44
lb x11, x21, 37
jal x1, mul8
add x8, x8, x5
lb x10, x20, 45
lb x11, x21, 45
jal x1, mul8
add x8, x8, x5
lb x10, x20, 46
lb x11, x21, 53
jal x1, mul8
add x8, x8, x5
lb x10, x20, 47
lb x11, x21, 61
jal x1, mul8
add x8, x8, x5
sw x8, 180(x22)
addi x8, x0, 0
lb x10, x20, 40
lb x11, x21, 6
jal x1, mul8
add x8, x8, x5
lb x10, x20, 41
lb x11, x21, 14
jal x1, mul8
add x8, x8, x5
lb x10, x20, 42
lb x11, x21, 22
jal x1, mul8
add x8, x8, x5
lb x10, x20, 43
lb x11, x21, 30
jal x1, mul8
add x8, x8, x5
lb x10, x20, 44
lb x11, x21, 38
jal x1, mul8
add x8, x8, x5
lb x10, x20, 45
lb x11, x21, 46
jal x1, mul8
add x8, x8, x5
lb x10, x20, 46
lb x11, x21, 54
jal x1, mul8
add x8, x8, x5
lb x10, x20, 47
lb x11, x21, 62
jal x1, mul8
add x8, x8, x5
sw x8, 184(x22)
addi x8, x0, 0
lb x10, x20, 40
lb x11, x21, 7
jal x1, mul8
add x8, x8, x5
lb x10, x20, 41
lb x11, x21, 15
jal x1, mul8
add x8, x8, x5
lb x10, x20, 42
lb x11, x21, 23
jal x1, mul8
add x8, x8, x5
lb x10, x20, 43
lb x11, x21, 31
jal x1, mul8
add x8, x8, x5
lb x10, x20, 44
lb x11, x21, 39
jal x1, mul8
add x8, x8, x5
lb x10, x20, 45
lb x11, x21, 47
jal x1, mul8
add x8, x8, x5
lb x10, x20, 46
lb x11, x21, 55
jal x1, mul8
add x8, x8, x5
lb x10, x20, 47
lb x11, x21, 63
jal x1, mul8
add x8, x8, x5
sw x8, 188(x22)
addi x8, x0, 0
lb x10, x20, 48
lb x11, x21, 0
jal x1, mul8
add x8, x8, x5
lb x10, x20, 49
lb x11, x21, 8
jal x1, mul8
add x8, x8, x5
lb x10, x20, 50
lb x11, x21, 16
jal x1, mul8
add x8, x8, x5
lb x10, x20, 51
lb x11, x21, 24
jal x1, mul8
add x8, x8, x5
lb x10, x20, 52
lb x11, x21, 32
jal x1, mul8
add x8, x8, x5
lb x10, x20, 53
lb x11, x21, 40
jal x1, mul8
add x8, x8, x5
lb x10, x20, 54
lb x11, x21, 48
jal x1, mul8
add x8, x8, x5
lb x10, x20, 55
lb x11, x21, 56
jal x1, mul8
add x8, x8, x5
sw x8, 192(x22)
addi x8, x0, 0
lb x10, x20, 48
lb x11, x21, 1
jal x1, mul8
add x8, x8, x5
lb x10, x20, 49
lb x11, x21, 9
jal x1, mul8
add x8, x8, x5
lb x10, x20, 50
lb x11, x21, 17
jal x1, mul8
add x8, x8, x5
lb x10, x20, 51
lb x11, x21, 25
jal x1, mul8
add x8, x8, x5
lb x10, x20, 52
lb x11, x21, 33
jal x1, mul8
add x8, x8, x5
lb x10, x20, 53
lb x11, x21, 41
jal x1, mul8
add x8, x8, x5
lb x10, x20, 54
lb x11, x21, 49
jal x1, mul8
add x8, x8, x5
lb x10, x20, 55
lb x11, x21, 57
jal x1, mul8
add x8, x8, x5
sw x8, 196(x22)
addi x8, x0, 0
lb x10, x20, 48
lb x11, x21, 2
jal x1, mul8
add x8, x8, x5
lb x10, x20, 49
lb x11, x21, 10
jal x1, mul8
add x8, x8, x5
lb x10, x20, 50
lb x11, x21, 18
jal x1, mul8
add x8, x8, x5
lb x10, x20, 51
lb x11, x21, 26
jal x1, mul8
add x8, x8, x5
lb x10, x20, 52
lb x11, x21, 34
jal x1, mul8
add x8, x8, x5
lb x10, x20, 53
lb x11, x21, 42
jal x1, mul8
add x8, x8, x5
lb x10, x20, 54
lb x11, x21, 50
jal x1, mul8
add x8, x8, x5
lb x10, x20, 55
lb x11, x21, 58
jal x1, mul8
add x8, x8, x5
sw x8, 200(x22)
addi x8, x0, 0
lb x10, x20, 48
lb x11, x21, 3
jal x1, mul8
add x8, x8, x5
lb x10, x20, 49
lb x11, x21, 11
jal x1, mul8
add x8, x8, x5
lb x10, x20, 50
lb x11, x21, 19
jal x1, mul8
add x8, x8, x5
lb x10, x20, 51
lb x11, x21, 27
jal x1, mul8
add x8, x8, x5
lb x10, x20, 52
lb x11, x21, 35
jal x1, mul8
add x8, x8, x5
lb x10, x20, 53
lb x11, x21, 43
jal x1, mul8
add x8, x8, x5
lb x10, x20, 54
lb x11, x21, 51
jal x1, mul8
add x8, x8, x5
lb x10, x20, 55
lb x11, x21, 59
jal x1, mul8
add x8, x8, x5
sw x8, 204(x22)
addi x8, x0, 0
lb x10, x20, 48
lb x11, x21, 4
jal x1, mul8
add x8, x8, x5
lb x10, x20, 49
lb x11, x21, 12
jal x1, mul8
add x8, x8, x5
lb x10, x20, 50
lb x11, x21, 20
jal x1, mul8
add x8, x8, x5
lb x10, x20, 51
lb x11, x21, 28
jal x1, mul8
add x8, x8, x5
lb x10, x20, 52
lb x11, x21, 36
jal x1, mul8
add x8, x8, x5
lb x10, x20, 53
lb x11, x21, 44
jal x1, mul8
add x8, x8, x5
lb x10, x20, 54
lb x11, x21, 52
jal x1, mul8
add x8, x8, x5
lb x10, x20, 55
lb x11, x21, 60
jal x1, mul8
add x8, x8, x5
sw x8, 208(x22)
addi x8, x0, 0
lb x10, x20, 48
lb x11, x21, 5
jal x1, mul8
add x8, x8, x5
lb x10, x20, 49
lb x11, x21, 13
jal x1, mul8
add x8, x8, x5
lb x10, x20, 50
lb x11, x21, 21
jal x1, mul8
add x8, x8, x5
lb x10, x20, 51
lb x11, x21, 29
jal x1, mul8
add x8, x8, x5
lb x10, x20, 52
lb x11, x21, 37
jal x1, mul8
add x8, x8, x5
lb x10, x20, 53
lb x11, x21, 45
jal x1, mul8
add x8, x8, x5
lb x10, x20, 54
lb x11, x21, 53
jal x1, mul8
add x8, x8, x5
lb x10, x20, 55
lb x11, x21, 61
jal x1, mul8
add x8, x8, x5
sw x8, 212(x22)
addi x8, x0, 0
lb x10, x20, 48
lb x11, x21, 6
jal x1, mul8
add x8, x8, x5
lb x10, x20, 49
lb x11, x21, 14
jal x1, mul8
add x8, x8, x5
lb x10, x20, 50
lb x11, x21, 22
jal x1, mul8
add x8, x8, x5
lb x10, x20, 51
lb x11, x21, 30
jal x1, mul8
add x8, x8, x5
lb x10, x20, 52
lb x11, x21, 38
jal x1, mul8
add x8, x8, x5
lb x10, x20, 53
lb x11, x21, 46
jal x1, mul8
add x8, x8, x5
lb x10, x20, 54
lb x11, x21, 54
jal x1, mul8
add x8, x8, x5
lb x10, x20, 55
lb x11, x21, 62
jal x1, mul8
add x8, x8, x5
sw x8, 216(x22)
addi x8, x0, 0
lb x10, x20, 48
lb x11, x21, 7
jal x1, mul8
add x8, x8, x5
lb x10, x20, 49
lb x11, x21, 15
jal x1, mul8
add x8, x8, x5
lb x10, x20, 50
lb x11, x21, 23
jal x1, mul8
add x8, x8, x5
lb x10, x20, 51
lb x11, x21, 31
jal x1, mul8
add x8, x8, x5
lb x10, x20, 52
lb x11, x21, 39
jal x1, mul8
add x8, x8, x5
lb x10, x20, 53
lb x11, x21, 47
jal x1, mul8
add x8, x8, x5
lb x10, x20, 54
lb x11, x21, 55
jal x1, mul8
add x8, x8, x5
lb x10, x20, 55
lb x11, x21, 63
jal x1, mul8
add x8, x8, x5
sw x8, 220(x22)
addi x8, x0, 0
lb x10, x20, 56
lb x11, x21, 0
jal x1, mul8
add x8, x8, x5
lb x10, x20, 57
lb x11, x21, 8
jal x1, mul8
add x8, x8, x5
lb x10, x20, 58
lb x11, x21, 16
jal x1, mul8
add x8, x8, x5
lb x10, x20, 59
lb x11, x21, 24
jal x1, mul8
add x8, x8, x5
lb x10, x20, 60
lb x11, x21, 32
jal x1, mul8
add x8, x8, x5
lb x10, x20, 61
lb x11, x21, 40
jal x1, mul8
add x8, x8, x5
lb x10, x20, 62
lb x11, x21, 48
jal x1, mul8
add x8, x8, x5
lb x10, x20, 63
lb x11, x21, 56
jal x1, mul8
add x8, x8, x5
sw x8, 224(x22)
addi x8, x0, 0
lb x10, x20, 56
lb x11, x21, 1
jal x1, mul8
add x8, x8, x5
lb x10, x20, 57
lb x11, x21, 9
jal x1, mul8
add x8, x8, x5
lb x10, x20, 58
lb x11, x21, 17
jal x1, mul8
add x8, x8, x5
lb x10, x20, 59
lb x11, x21, 25
jal x1, mul8
add x8, x8, x5
lb x10, x20, 60
lb x11, x21, 33
jal x1, mul8
add x8, x8, x5
lb x10, x20, 61
lb x11, x21, 41
jal x1, mul8
add x8, x8, x5
lb x10, x20, 62
lb x11, x21, 49
jal x1, mul8
add x8, x8, x5
lb x10, x20, 63
lb x11, x21, 57
jal x1, mul8
add x8, x8, x5
sw x8, 228(x22)
addi x8, x0, 0
lb x10, x20, 56
lb x11, x21, 2
jal x1, mul8
add x8, x8, x5
lb x10, x20, 57
lb x11, x21, 10
jal x1, mul8
add x8, x8, x5
lb x10, x20, 58
lb x11, x21, 18
jal x1, mul8
add x8, x8, x5
lb x10, x20, 59
lb x11, x21, 26
jal x1, mul8
add x8, x8, x5
lb x10, x20, 60
lb x11, x21, 34
jal x1, mul8
add x8, x8, x5
lb x10, x20, 61
lb x11, x21, 42
jal x1, mul8
add x8, x8, x5
lb x10, x20, 62
lb x11, x21, 50
jal x1, mul8
add x8, x8, x5
lb x10, x20, 63
lb x11, x21, 58
jal x1, mul8
add x8, x8, x5
sw x8, 232(x22)
addi x8, x0, 0
lb x10, x20, 56
lb x11, x21, 3
jal x1, mul8
add x8, x8, x5
lb x10, x20, 57
lb x11, x21, 11
jal x1, mul8
add x8, x8, x5
lb x10, x20, 58
lb x11, x21, 19
jal x1, mul8
add x8, x8, x5
lb x10, x20, 59
lb x11, x21, 27
jal x1, mul8
add x8, x8, x5
lb x10, x20, 60
lb x11, x21, 35
jal x1, mul8
add x8, x8, x5
lb x10, x20, 61
lb x11, x21, 43
jal x1, mul8
add x8, x8, x5
lb x10, x20, 62
lb x11, x21, 51
jal x1, mul8
add x8, x8, x5
lb x10, x20, 63
lb x11, x21, 59
jal x1, mul8
add x8, x8, x5
sw x8, 236(x22)
addi x8, x0, 0
lb x10, x20, 56
lb x11, x21, 4
jal x1, mul8
add x8, x8, x5
lb x10, x20, 57
lb x11, x21, 12
jal x1, mul8
add x8, x8, x5
lb x10, x20, 58
lb x11, x21, 20
jal x1, mul8
add x8, x8, x5
lb x10, x20, 59
lb x11, x21, 28
jal x1, mul8
add x8, x8, x5
lb x10, x20, 60
lb x11, x21, 36
jal x1, mul8
add x8, x8, x5
lb x10, x20, 61
lb x11, x21, 44
jal x1, mul8
add x8, x8, x5
lb x10, x20, 62
lb x11, x21, 52
jal x1, mul8
add x8, x8, x5
lb x10, x20, 63
lb x11, x21, 60
jal x1, mul8
add x8, x8, x5
sw x8, 240(x22)
addi x8, x0, 0
lb x10, x20, 56
lb x11, x21, 5
jal x1, mul8
add x8, x8, x5
lb x10, x20, 57
lb x11, x21, 13
jal x1, mul8
add x8, x8, x5
lb x10, x20, 58
lb x11, x21, 21
jal x1, mul8
add x8, x8, x5
lb x10, x20, 59
lb x11, x21, 29
jal x1, mul8
add x8, x8, x5
lb x10, x20, 60
lb x11, x21, 37
jal x1, mul8
add x8, x8, x5
lb x10, x20, 61
lb x11, x21, 45
jal x1, mul8
add x8, x8, x5
lb x10, x20, 62
lb x11, x21, 53
jal x1, mul8
add x8, x8, x5
lb x10, x20, 63
lb x11, x21, 61
jal x1, mul8
add x8, x8, x5
sw x8, 244(x22)
addi x8, x0, 0
lb x10, x20, 56
lb x11, x21, 6
jal x1, mul8
add x8, x8, x5
lb x10, x20, 57
lb x11, x21, 14
jal x1, mul8
add x8, x8, x5
lb x10, x20, 58
lb x11, x21, 22
jal x1, mul8
add x8, x8, x5
lb x10, x20, 59
lb x11, x21, 30
jal x1, mul8
add x8, x8, x5
lb x10, x20, 60
lb x11, x21, 38
jal x1, mul8
add x8, x8, x5
lb x10, x20, 61
lb x11, x21, 46
jal x1, mul8
add x8, x8, x5
lb x10, x20, 62
lb x11, x21, 54
jal x1, mul8
add x8, x8, x5
lb x10, x20, 63
lb x11, x21, 62
jal x1, mul8
add x8, x8, x5
sw x8, 248(x22)
addi x8, x0, 0
lb x10, x20, 56
lb x11, x21, 7
jal x1, mul8
add x8, x8, x5
lb x10, x20, 57
lb x11, x21, 15
jal x1, mul8
add x8, x8, x5
lb x10, x20, 58
lb x11, x21, 23
jal x1, mul8
add x8, x8, x5
lb x10, x20, 59
lb x11, x21, 31
jal x1, mul8
add x8, x8, x5
lb x10, x20, 60
lb x11, x21, 39
jal x1, mul8
add x8, x8, x5
lb x10, x20, 61
lb x11, x21, 47
jal x1, mul8
add x8, x8, x5
lb x10, x20, 62
lb x11, x21, 55
jal x1, mul8
add x8, x8, x5
lb x10, x20, 63
lb x11, x21, 63
jal x1, mul8
add x8, x8, x5
sw x8, 252(x22)
lui x23, 0x8003f
addi x23, x23, 0
addi x24, x0, 1
sw x24, 0(x23)
halt:
jal x0, halt
mul8:
xor x6, x10, x11
blt x10, x0, neg_a
jal x0, check_b
neg_a:
sub x10, x0, x10
check_b:
blt x11, x0, neg_b
jal x0, mul_start
neg_b:
sub x11, x0, x11
mul_start:
addi x5, x0, 0
addi x28, x0, 8
mul_loop:
andi x7, x11, 1
beq x7, x0, mul_skip
add x5, x5, x10
mul_skip:
slli x10, x10, 1
srli x11, x11, 1
addi x28, x28, -1
bne x28, x0, mul_loop
blt x6, x0, neg_product
jal x0, mul_return
neg_product:
sub x5, x0, x5
mul_return:
jalr x0, x1, 0
