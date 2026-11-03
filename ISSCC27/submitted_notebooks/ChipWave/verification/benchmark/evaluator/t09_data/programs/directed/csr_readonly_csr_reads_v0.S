.option norvc
.section .text.init
.globl _start
_start:
csrr s0,misa
li t6, 1073742080
bne s0, t6, fail
csrr s0,mhartid
li t6, 0
bne s0, t6, fail
csrrc s1,misa,x0
li t6, 1073742080
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

