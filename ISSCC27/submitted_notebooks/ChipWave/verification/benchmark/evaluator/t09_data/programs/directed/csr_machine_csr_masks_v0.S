.option norvc
.section .text.init
.globl _start
_start:
li s0,0
csrw mstatus,s0
csrr s1,mstatus
li t6, 6144
bne s1, t6, fail
li s0,0x80000003
csrw mtvec,s0
csrr s1,mtvec
li t6, 2147483648
bne s1, t6, fail
csrw mepc,s0
csrr s1,mepc
li t6, 2147483648
bne s1, t6, fail
li s0,0
csrw mcause,s0
csrr s1,mcause
li t6, 0
bne s1, t6, fail
li s0,0
csrw mtval,s0
csrr s1,mtval
li t6, 0
bne s1, t6, fail
li s0,8
csrw mstatus,s0
csrr s1,mstatus
li t6, 6152
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

