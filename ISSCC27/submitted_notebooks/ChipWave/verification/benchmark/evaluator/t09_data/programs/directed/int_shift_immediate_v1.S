.option norvc
.section .text.init
.globl _start
_start:
li s0,4294967295
slli s1,s0,1
li t6, 4294967294
bne s1, t6, fail
srli s1,s0,1
li t6, 2147483647
bne s1, t6, fail
srai s1,s0,1
li t6, 4294967295
bne s1, t6, fail

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

