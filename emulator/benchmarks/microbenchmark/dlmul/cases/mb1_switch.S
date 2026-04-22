#include "config.inc"

    .section .text
    .align 2
    .globl dlmul_case_entry
dlmul_case_entry:
    li t6, SWITCH_OUTER_ITERS
1:
    li a0, SWITCH_FIRST_AVL
    vsetvli t0, a0, e32, SWITCH_FROM_LMUL, ta, ma
    vmv.v.i v0, 1

    li a0, SWITCH_SECOND_AVL
    vsetvli t1, a0, e32, SWITCH_TO_LMUL, ta, ma
    vadd.vv v0, v0, v0

    addi t6, t6, -1
    bnez t6, 1b
    ret
