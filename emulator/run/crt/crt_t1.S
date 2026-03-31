    .section .text.init
    .globl _start
_start:
    li t0, 0x2200
    csrs mstatus, t0
    csrwi vcsr, 0

    la sp, _stack_top

    la t0, _bss_start
    la t1, _bss_end
1:  beq t0, t1, 2f
    sw zero, 0(t0)
    addi t0, t0, 4
    j 1b
2:
    call main

    li t0, 0x10000000
    li t1, 0xdeadbeef
    sw t1, 0(t0)
3:  j 3b

    .section .bss
    .align 4
    .space 8192
_stack_top:
