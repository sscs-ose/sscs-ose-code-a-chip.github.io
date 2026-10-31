# After loading, click Load Demo Data to initialize address 8 = 1.
# Six steps: x2=0, x5=1, x6=1; selected SRAM cell (0, 2).
addi x2, x0, 0
lw x5, 8(x2)
add x6, x5, x2
