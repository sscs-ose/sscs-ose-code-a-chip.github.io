.option norvc
.section .text.init
.globl _start
_start:
la s0,word
li s1,3735928559
sw s1,0(s0)
lw s2,0(s0)
li t6, 3735928559
bne s2, t6, fail

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
word: .word 0x12345678

