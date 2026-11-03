.option norvc
.section .text.init
.globl _start
_start:
li s1,-1
add x0,s1,s1
addi s0,x0,3
li t6, 3
bne s0, t6, fail

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

