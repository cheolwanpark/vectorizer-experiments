#ifndef DLMUL_BENCH_VECTOR_MACROS_H
#define DLMUL_BENCH_VECTOR_MACROS_H

#define DLB_CAT2_INNER(a, b) a##b
#define DLB_CAT2(a, b) DLB_CAT2_INNER(a, b)
#define DLB_CAT3(a, b, c) DLB_CAT2(DLB_CAT2(a, b), c)

#define DLB_F32_T(lmul) DLB_CAT3(vfloat32, lmul, _t)
#define DLB_VSETVL_E32(lmul) DLB_CAT2(__riscv_vsetvl_e32, lmul)
#define DLB_VLE32(lmul) DLB_CAT2(__riscv_vle32_v_f32, lmul)
#define DLB_VSE32(lmul) DLB_CAT2(__riscv_vse32_v_f32, lmul)
#define DLB_VFMV_F(lmul) DLB_CAT2(__riscv_vfmv_v_f_f32, lmul)
#define DLB_VFADD(lmul) DLB_CAT2(__riscv_vfadd_vv_f32, lmul)
#define DLB_VFSUB(lmul) DLB_CAT2(__riscv_vfsub_vv_f32, lmul)
#define DLB_VFMUL(lmul) DLB_CAT2(__riscv_vfmul_vv_f32, lmul)
#define DLB_VFMACC_VF(lmul) DLB_CAT2(__riscv_vfmacc_vf_f32, lmul)

#define DLB_VARIANT_FIXED_M1 1
#define DLB_VARIANT_FIXED_M2 2
#define DLB_VARIANT_FIXED_M4 4
#define DLB_VARIANT_DYN_SAFE 10
#define DLB_VARIANT_DYN_MAIN 20

#endif
