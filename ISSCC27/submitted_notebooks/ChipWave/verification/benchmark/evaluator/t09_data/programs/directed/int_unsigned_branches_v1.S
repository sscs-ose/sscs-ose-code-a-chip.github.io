.option norvc
.section .text.init
.globl _start
_start:
li s0,1
li s1,2147483648
bltu s0,s1,bltu_ok
j fail
bltu_ok:
bgeu s0,s1,fail
bgeu s1,s0,bgeu_ok
j fail
bgeu_ok:

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

