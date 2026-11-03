.option norvc
.section .text.init
.globl _start
_start:
li s0,-1
li s1,1
blt s0,s1,blt_ok
j fail
blt_ok:
bge s0,s1,fail
bge s1,s0,bge_ok
j fail
bge_ok:

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

