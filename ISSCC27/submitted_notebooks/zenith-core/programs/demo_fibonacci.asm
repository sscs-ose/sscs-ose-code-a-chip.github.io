    ADDI r1, r0, 0
    ADDI r2, r0, 1
    ADDI r4, r0, 7
    ADD  r4, r4, r4
loop:
    OUT  r1
    ADD  r3, r1, r2
    MOV  r1, r2
    MOV  r2, r3
    ADDI r4, r4, -1
    BEQ  r4, r0, done
    JUMP loop
done:
    JUMP done
