    ADDI r1, r0, 0
loop:
    ADDI r1, r1, 1
    OUT  r1
    ADDI r2, r0, 6
delay:
    ADDI r2, r2, -1
    BEQ  r2, r0, loop
    JUMP delay
