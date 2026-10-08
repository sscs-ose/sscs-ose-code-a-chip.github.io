    ADDI r4, r0, 4
    ADD  r6, r4, r4
    SLL  r6, r6, r4
    ADDI r3, r6, 5
    ADDI r7, r6, 6
    ADDI r5, r6, 7
    ADDI r1, r0, 1
    STORE r1, r5, 0
    STORE r1, r7, 0
loop:

    ADDI r1, r0, 4
    ADDI r2, r0, 4
    SLL  r1, r1, r2
    STORE r1, r3, 0
    ADDI r2, r0, 0
d25:
    ADDI r2, r2, -1
    BEQ  r2, r0, e25
    JUMP d25
e25:

    ADDI r1, r0, 7
    ADDI r1, r1, 1
    ADDI r2, r0, 4
    SLL  r1, r1, r2
    STORE r1, r3, 0
    ADDI r2, r0, 0
d50:
    ADDI r2, r2, -1
    BEQ  r2, r0, e50
    JUMP d50
e50:

    ADDI r1, r0, 7
    ADDI r1, r1, 5
    ADDI r2, r0, 4
    SLL  r1, r1, r2
    STORE r1, r3, 0
    ADDI r2, r0, 0
d75:
    ADDI r2, r2, -1
    BEQ  r2, r0, e75
    JUMP d75
e75:
    JUMP loop
