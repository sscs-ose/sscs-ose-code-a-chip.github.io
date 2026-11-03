.option norvc
.section .text.init
.globl _start
_start:
li s0,13
li s1,13
beq s0,s1,eq_ok
j fail
eq_ok:
bne s0,s1,fail

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

