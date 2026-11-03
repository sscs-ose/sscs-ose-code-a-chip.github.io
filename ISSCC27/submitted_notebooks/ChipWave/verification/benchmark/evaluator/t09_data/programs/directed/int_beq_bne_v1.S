.option norvc
.section .text.init
.globl _start
_start:
li s0,13
li s1,14
beq s0,s1,fail
bne s0,s1,ne_ok
j fail
ne_ok:

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

