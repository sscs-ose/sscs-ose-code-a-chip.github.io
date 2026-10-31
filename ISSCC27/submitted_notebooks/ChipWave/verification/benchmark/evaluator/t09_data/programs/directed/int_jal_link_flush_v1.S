.option norvc
.section .text.init
.globl _start
_start:
la s1,marker
li s2,165
jal s0,jal_target
jal_after:
sw s2,0(s1)
j fail
jal_target:
la s3,jal_after
bne s0,s3,fail
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

