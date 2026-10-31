.option norvc
.section .text.init
.globl _start
_start:
li s0,0x8003fffc
li s1,305419896
sw s1,0(s0)
fence rw,rw
lw s2,0(s0)
li t6, 305419896
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

