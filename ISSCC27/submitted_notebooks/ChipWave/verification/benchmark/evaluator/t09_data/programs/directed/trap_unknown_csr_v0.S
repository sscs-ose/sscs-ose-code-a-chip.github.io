.option norvc
.section .text.init
.globl _start
_start:
la t5,trap_handler
csrw mtvec,t5
li t0,8
csrs mstatus,t0
la s0,marker
li s1,0x55
fault_here:
csrr s2,0x7c0
sw s1,0(s0)
after_fault:
lw s2,0(s0)
li t6, 0
bne s2, t6, fail
csrr s2,mstatus
li t6,8
and s2,s2,t6
li t6, 8
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
trap_handler:
csrr t2,mcause
li t3,2
bne t2,t3,fail
csrr t2,mtval
la t4,fault_here
lw t3,0(t4)
bne t2,t3,fail
csrr t2,mepc
la t3,fault_here
bne t2,t3,fail
csrr t2,mstatus
li t3,0x88
and t2,t2,t3
li t3,0x80
bne t2,t3,fail
la t2,after_fault
csrw mepc,t2
mret

.section .data
.balign 16
marker: .word 0

