#include "config.inc"

    .section .text
    .align 2
    .globl dlmul_case_entry
dlmul_case_entry:
    li t6, MEM_OUTER_ITERS
1:
    la a1, input_a
    la a2, input_b
    la a3, output_a
    li a0, MEM_TOTAL_ELEMS
2:
    vsetvli t0, a0, e32, MEM_LMUL, ta, ma
    vle32.v v0, (a1)
    vle32.v v8, (a2)
    vadd.vv v0, v0, v8
    vse32.v v0, (a3)

    slli t1, t0, 2
    add a1, a1, t1
    add a2, a2, t1
    add a3, a3, t1
    sub a0, a0, t0
    bnez a0, 2b

    addi t6, t6, -1
    bnez t6, 1b
    ret
