#ifndef DLMUL_BENCH_VECTOR_MACROS_H
#define DLMUL_BENCH_VECTOR_MACROS_H

#define DLB_CAT2_INNER(a, b) a##b
#define DLB_CAT2(a, b) DLB_CAT2_INNER(a, b)
#define DLB_CAT3(a, b, c) DLB_CAT2(DLB_CAT2(a, b), c)

#define DLB_F32_T(lmul) DLB_CAT3(vfloat32, lmul, _t)
#define DLB_I16_T(lmul) DLB_CAT3(vint16, lmul, _t)
#define DLB_I32_T(lmul) DLB_CAT3(vint32, lmul, _t)
#define DLB_VSETVL_E16(lmul) DLB_CAT2(__riscv_vsetvl_e16, lmul)
#define DLB_VSETVL_E32(lmul) DLB_CAT2(__riscv_vsetvl_e32, lmul)
#define DLB_VLE16(lmul) DLB_CAT2(__riscv_vle16_v_i16, lmul)
#define DLB_VLE32_I(lmul) DLB_CAT2(__riscv_vle32_v_i32, lmul)
#define DLB_VLE32(lmul) DLB_CAT2(__riscv_vle32_v_f32, lmul)
#define DLB_VSE32_I(lmul) DLB_CAT2(__riscv_vse32_v_i32, lmul)
#define DLB_VSE32(lmul) DLB_CAT2(__riscv_vse32_v_f32, lmul)
#define DLB_VFMV_F(lmul) DLB_CAT2(__riscv_vfmv_v_f_f32, lmul)
#define DLB_VFADD(lmul) DLB_CAT2(__riscv_vfadd_vv_f32, lmul)
#define DLB_VFSUB(lmul) DLB_CAT2(__riscv_vfsub_vv_f32, lmul)
#define DLB_VFMUL(lmul) DLB_CAT2(__riscv_vfmul_vv_f32, lmul)
#define DLB_VFMACC_VF(lmul) DLB_CAT2(__riscv_vfmacc_vf_f32, lmul)
#define DLB_VFMACC_VV(lmul) DLB_CAT2(__riscv_vfmacc_vv_f32, lmul)
#define DLB_VADD_I32(lmul) DLB_CAT2(__riscv_vadd_vv_i32, lmul)
#define DLB_VWADD_I32(lmul) DLB_CAT2(__riscv_vwadd_vv_i32, lmul)
#define DLB_VWMUL_I32(lmul) DLB_CAT2(__riscv_vwmul_vv_i32, lmul)

#define DLB_VARIANT_FIXED_M1 1
#define DLB_VARIANT_FIXED_M2 2
#define DLB_VARIANT_FIXED_M4 4
#define DLB_VARIANT_FIXED_M8 8
#define DLB_VARIANT_DYN_SAFE 10
#define DLB_VARIANT_DYN_MAIN 20
#define DLB_VARIANT_DYN_M4_M2_M4 42
#define DLB_VARIANT_DYN_M8_M2_M8 82

#endif
