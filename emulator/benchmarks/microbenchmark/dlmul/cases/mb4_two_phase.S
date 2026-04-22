#include "config.inc"

    .section .text
    .align 2
    .globl dlmul_case_entry
dlmul_case_entry:
    li s3, PHASE_OUTER_ITERS
1:
    la a1, input_a
    la a2, input_b
    la a3, output_a
    li t6, PHASE1_TOTAL_ELEMS
2:
    vsetvli t0, t6, e32, PHASE1_LMUL, ta, ma
    vle32.v v0, (a1)
    vle32.v v8, (a2)
    vadd.vv v0, v0, v8
    vse32.v v0, (a3)

    slli t1, t0, 2
    add a1, a1, t1
    add a2, a2, t1
    add a3, a3, t1
    sub t6, t6, t0
    bnez t6, 2b

    la a1, input_c
    la a2, input_d
    la a3, output_b
    li t6, PHASE2_TOTAL_ELEMS
3:
    vsetvli t0, t6, e32, PHASE2_LMUL, ta, ma
    vle32.v v0, (a1)
    vle32.v v8, (a2)
    vadd.vv v16, v0, v8
    vxor.vv v24, v16, v0
    vadd.vv v16, v16, v24
    vse32.v v16, (a3)

    slli t1, t0, 2
    add a1, a1, t1
    add a2, a2, t1
    add a3, a3, t1
    sub t6, t6, t0
    bnez t6, 3b

    addi s3, s3, -1
    bnez s3, 1b
    ret
