    ADDI r4, r0, 4
    ADD  r3, r4, r4
    SLL  r3, r3, r4
    ADDI r3, r3, 3
loop:

    ADDI r1, r0, 4
    ADDI r6, r0, 4
    SLL  r1, r1, r6
    ADDI r1, r1, 7
    ADDI r1, r1, 1
    STORE r1, r3, 0
    ADDI r2, r0, 0
d_H:
    ADDI r2, r2, -1
    BEQ  r2, r0, e_H
    JUMP d_H
e_H:

    ADDI r1, r0, 6
    ADDI r6, r0, 4
    SLL  r1, r1, r6
    ADDI r1, r1, 7
    ADDI r1, r1, 7
    ADDI r1, r1, 1
    STORE r1, r3, 0
    ADDI r2, r0, 0
d_o:
    ADDI r2, r2, -1
    BEQ  r2, r0, e_o
    JUMP d_o
e_o:

    ADDI r1, r0, 6
    ADDI r6, r0, 4
    SLL  r1, r1, r6
    ADDI r1, r1, 7
    ADDI r1, r1, 5
    STORE r1, r3, 0
    ADDI r2, r0, 0
d_l:
    ADDI r2, r2, -1
    BEQ  r2, r0, e_l
    JUMP d_l
e_l:

    ADDI r1, r0, 6
    ADDI r6, r0, 4
    SLL  r1, r1, r6
    ADDI r1, r1, 1
    STORE r1, r3, 0
    ADDI r2, r0, 0
d_a:
    ADDI r2, r2, -1
    BEQ  r2, r0, e_a
    JUMP d_a
e_a:

    ADDI r1, r0, 0
    ADDI r6, r0, 4
    SLL  r1, r1, r6
    ADDI r1, r1, 7
    ADDI r1, r1, 3
    STORE r1, r3, 0
    ADDI r2, r0, 0
d_nl:
    ADDI r2, r2, -1
    BEQ  r2, r0, e_nl
    JUMP d_nl
e_nl:
    JUMP loop
