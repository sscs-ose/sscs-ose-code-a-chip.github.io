.option norvc
.section .text.init
.globl _start
_start:
li s0, 7
li s1, -7
add s2,s0,s1
li t6, 0
bne s2, t6, fail
sub s2,s0,s1
li t6, 14
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

