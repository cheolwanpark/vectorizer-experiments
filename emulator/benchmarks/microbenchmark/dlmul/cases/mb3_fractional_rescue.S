#include "config.inc"

    .section .text
    .align 2
    .globl dlmul_case_entry
dlmul_case_entry:
    li s2, PRESSURE_OUTER_ITERS
1:
    la a1, input_a
    la a2, input_b
    la a3, input_c
    la a4, input_d
    la a5, input_e
    la a6, input_f
    la a7, input_g
    la s0, input_h
    la s1, output_a
    li t6, PRESSURE_TOTAL_ELEMS
2:
    vsetvli t0, t6, e32, PRESSURE_LMUL, ta, ma
    vle32.v v0, (a1)
    vle32.v v2, (a2)
#if TEMP_REG_COUNT >= 3
    vle32.v v4, (a3)
#endif
#if TEMP_REG_COUNT >= 4
    vle32.v v6, (a4)
#endif
#if TEMP_REG_COUNT >= 5
    vle32.v v8, (a5)
#endif
#if TEMP_REG_COUNT >= 6
    vle32.v v10, (a6)
#endif
#if TEMP_REG_COUNT >= 7
    vle32.v v12, (a7)
#endif
#if TEMP_REG_COUNT >= 8
    vle32.v v14, (s0)
#endif

    vmv.v.i v16, 0
    vadd.vv v16, v16, v0
    vadd.vv v18, v2, v0
#if TEMP_REG_COUNT >= 3
    vadd.vv v16, v16, v4
    vxor.vv v18, v18, v4
#endif
#if TEMP_REG_COUNT >= 4
    vadd.vv v16, v16, v6
    vxor.vv v18, v18, v6
#endif
#if TEMP_REG_COUNT >= 5
    vadd.vv v16, v16, v8
    vxor.vv v18, v18, v8
#endif
#if TEMP_REG_COUNT >= 6
    vadd.vv v16, v16, v10
    vxor.vv v18, v18, v10
#endif
#if TEMP_REG_COUNT >= 7
    vadd.vv v16, v16, v12
    vxor.vv v18, v18, v12
#endif
#if TEMP_REG_COUNT >= 8
    vadd.vv v16, v16, v14
    vxor.vv v18, v18, v14
#endif
    vadd.vv v20, v16, v18
    vsub.vv v16, v20, v0
    vse32.v v16, (s1)

    slli t1, t0, 2
    add a1, a1, t1
    add a2, a2, t1
    add a3, a3, t1
    add a4, a4, t1
    add a5, a5, t1
    add a6, a6, t1
    add a7, a7, t1
    add s0, s0, t1
    add s1, s1, t1
    sub t6, t6, t0
    bnez t6, 2b

    addi s2, s2, -1
    bnez s2, 1b
    ret
