.option norvc
.section .text.init
.globl _start
_start:
la s1,words
lw s0,0(s1)
lw s2,4(s1)
add s3,s0,s2
li t6, 0
bne s3, t6, fail

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
words: .word 4294967295,1

