.option norvc
.section .text.init
.globl _start
_start:
la s1,word
li s2,2147483648
lw s0,0(s1)
beq s0,s2,load_branch_ok
j fail
load_branch_ok:

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
word: .word 2147483648

