.option norvc
.section .text.init
.globl _start
_start:
la s1,marker
li s2,1
la s3,jalr_target
addi s3,s3,1
jalr s0,0(s3)
jalr_after:
sw s2,0(s1)
j fail
jalr_target:
la s4,jalr_after
bne s0,s4,fail
add x0,s2,s2
bne x0,zero,fail
lw s4,0(s1)
li t6, 0
bne s4, t6, fail

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
marker: .word 0

