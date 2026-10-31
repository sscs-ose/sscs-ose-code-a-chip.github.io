.option norvc
.section .text.init
.globl _start
_start:
lui s0,524287
li t6, 2147479552
bne s0, t6, fail
auipc_here:
auipc s1,0
la s2,auipc_here
bne s1,s2,fail

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

