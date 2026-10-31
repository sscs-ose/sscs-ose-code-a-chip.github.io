.option norvc
.section .text.init
.globl _start
_start:
li s0,0x100
csrw mscratch,s0
csrrsi s1,mscratch,0
li t6, 256
bne s1, t6, fail
csrr s2,mscratch
li t6, 256
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

