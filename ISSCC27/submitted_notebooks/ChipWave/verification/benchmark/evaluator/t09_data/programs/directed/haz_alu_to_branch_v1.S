.option norvc
.section .text.init
.globl _start
_start:
li s1,-1
li s2,1
li s3,0
add s0,s1,s2
beq s0,s3,alu_branch_ok
j fail
alu_branch_ok:

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

