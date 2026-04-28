# `db1` Compare

DB: `artifacts/dlmul-bench.sqlite`  
Case in DB: `db1`

`db1` is the independent-control case: the `m4` float stream and the `m2`
e16-to-e32 widening accumulator island do not feed each other. They only join at
the end as independent stores.

| Variant | Phase LMUL (`float / int16 island / final`) | Total elems | Outer iters | Kernel cycles | Total cycles | Wall time |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| `dyn_m4_m2_m4` | `m4 / m2 / m4` | 192 | 32 | 50,132 | 118,207 | 306.11s |
| `fixed_m1` | `m1 / m1 / m1` | 192 | 32 | 88,098 | 194,053 | 475.97s |
| `fixed_m2` | `m2 / m2 / m2` | 192 | 32 | 68,843 | 155,425 | 392.03s |
| `fixed_m4` | `m4 / m4 / m4` | 192 | 32 | 72,830 | 163,319 | 417.01s |

Best fixed variant is `fixed_m2`. `dyn_m4_m2_m4` is faster than `fixed_m2` by:

- kernel cycles: `18,711` (`27.18%`)
- total cycles: `37,218` (`23.95%`)
- wall time: `85.92s` (`21.92%`)

Compared to all fixed variants:

| Fixed variant | Kernel speedup | Kernel cycle reduction | Total cycle reduction | Wall time reduction |
| --- | ---: | ---: | ---: | ---: |
| `fixed_m1` | 1.757x | 43.1% | 39.1% | 35.7% |
| `fixed_m2` | 1.373x | 27.2% | 23.9% | 21.9% |
| `fixed_m4` | 1.453x | 31.2% | 27.6% | 26.6% |

Assembly pattern checks passed for all variants:

- `dyn_m4_m2_m4`: `m4 -> m2 -> m4`
- `fixed_m1`: `m1`
- `fixed_m2`: `m2`
- `fixed_m4`: `m4`

## Why `dyn_m4_m2_m4` Wins Here

The dynamic version keeps the wide float stream at `m4`, but lowers the
widening integer island to `m2`. The integer island creates eight widening
temporaries:

```text
e16,m2 inputs -> e32,m4 accumulators
```

In `fixed_m4`, the same island becomes:

```text
e16,m4 inputs -> e32,m8 accumulators
```

That larger `m8` accumulator footprint is expensive. In `db1`, lowering the
integer island does not block the float stream because there is no data
dependency between the two regions.

The final `m4` restore in the dynamic version is only needed for the float
stores and the `i32,m4` store. It does not have to wait on a dependent value
that feeds more `m4` arithmetic.

## `fixed_m2` Pseudo Code

```text
kernel():
  init real inputs
  init db1_src0, db1_src1, db1_bias

  repeat 32 times:
    loop over 192 elems with LMUL=m2
      float stream:
        load a/b/c/d/e/x as f32,m2
        compute a_out and d_out as f32,m2

      integer widening island:
        load src0/src1/bias as i16,m2
        build 8 widening temporaries as i32,m4
        reduce them into i_out as i32,m4

      store a_out/d_out as f32,m2
      store i_out as i32,m4
```

## `dyn_m4_m2_m4` Pseudo Code

```text
kernel():
  init real inputs
  init db1_src0, db1_src1, db1_bias

  repeat 32 times:
    loop over 192 elems with LMUL=m4
      float stream:
        load a/b/c/d/e/x as f32,m4
        compute a_out and d_out as f32,m4

      independent integer widening island:
        switch/use LMUL=m2
        load src0/src1/bias as i16,m2
        build 8 widening temporaries as i32,m4
        reduce them into i_out as i32,m4

      restore/use LMUL=m4
      store a_out/d_out as f32,m4
      store i_out as i32,m4
```

## `fixed_m2` Source

```c
#elif DLB_BENCH_VARIANT == DLB_VARIANT_FIXED_M2
        size_t vl_base = __riscv_vsetvl_e32m2((size_t)DB1_TOTAL_ELEMS);
        for (int offset = 0; offset < DB1_TOTAL_ELEMS; offset += (int)vl_base) {
            size_t avl = (size_t)(DB1_TOTAL_ELEMS - offset);
            if (avl > vl_base) avl = vl_base;

            vfloat32m2_t va = __riscv_vle32_v_f32m2(&a[offset], avl);
            vfloat32m2_t vb = __riscv_vle32_v_f32m2(&b[offset], avl);
            vfloat32m2_t vc = __riscv_vle32_v_f32m2(&c[offset], avl);
            vfloat32m2_t vd = __riscv_vle32_v_f32m2(&d[offset], avl);
            vfloat32m2_t ve = __riscv_vle32_v_f32m2(&e[offset], avl);
            vfloat32m2_t vx = __riscv_vle32_v_f32m2(&x[offset], avl);
            vfloat32m2_t t0 = __riscv_vfadd_vv_f32m2(va, vb, avl);
            vfloat32m2_t t1 = __riscv_vfmul_vv_f32m2(vc, vd, avl);
            vfloat32m2_t a_out = __riscv_vfmacc_vf_f32m2(t0, 0.25f, t1, avl);
            vfloat32m2_t d_out = __riscv_vfadd_vv_f32m2(a_out, ve, avl);
            d_out = __riscv_vfmacc_vf_f32m2(d_out, 0.125f, vx, avl);

            vint16m2_t x0 = __riscv_vle16_v_i16m2(&db1_src0[offset], avl);
            vint16m2_t x1 = __riscv_vle16_v_i16m2(&db1_src1[offset], avl);
            vint16m2_t xb = __riscv_vle16_v_i16m2(&db1_bias[offset], avl);
            vint32m4_t acc0 = __riscv_vwadd_vv_i32m4(x0, x1, avl);
            vint32m4_t acc1 = __riscv_vwmul_vv_i32m4(x0, x1, avl);
            vint32m4_t acc2 = __riscv_vwadd_vv_i32m4(x1, xb, avl);
            vint32m4_t acc3 = __riscv_vwmul_vv_i32m4(x1, xb, avl);
            vint32m4_t acc4 = __riscv_vwadd_vv_i32m4(x0, xb, avl);
            vint32m4_t acc5 = __riscv_vwmul_vv_i32m4(x0, xb, avl);
            vint32m4_t acc6 = __riscv_vwadd_vv_i32m4(xb, x1, avl);
            vint32m4_t acc7 = __riscv_vwmul_vv_i32m4(xb, x0, avl);
            vint32m4_t i_out = __riscv_vadd_vv_i32m4(acc0, acc1, avl);
            i_out = __riscv_vadd_vv_i32m4(i_out, acc2, avl);
            i_out = __riscv_vadd_vv_i32m4(i_out, acc3, avl);
            i_out = __riscv_vadd_vv_i32m4(i_out, acc4, avl);
            i_out = __riscv_vadd_vv_i32m4(i_out, acc5, avl);
            i_out = __riscv_vadd_vv_i32m4(i_out, acc6, avl);
            i_out = __riscv_vadd_vv_i32m4(i_out, acc7, avl);

            __riscv_vse32_v_f32m2(&a[offset], a_out, avl);
            __riscv_vse32_v_f32m2(&d[offset], d_out, avl);
            __riscv_vse32_v_i32m4(&indx[offset], i_out, avl);
        }
```

## `dyn_m4_m2_m4` Source

```c
#else
        size_t vl4 = __riscv_vsetvl_e32m4((size_t)DB1_TOTAL_ELEMS);
        for (int offset = 0; offset < DB1_TOTAL_ELEMS; offset += (int)vl4) {
            size_t avl = (size_t)(DB1_TOTAL_ELEMS - offset);
            if (avl > vl4) avl = vl4;

            vfloat32m4_t va = __riscv_vle32_v_f32m4(&a[offset], avl);
            vfloat32m4_t vb = __riscv_vle32_v_f32m4(&b[offset], avl);
            vfloat32m4_t vc = __riscv_vle32_v_f32m4(&c[offset], avl);
            vfloat32m4_t vd = __riscv_vle32_v_f32m4(&d[offset], avl);
            vfloat32m4_t ve = __riscv_vle32_v_f32m4(&e[offset], avl);
            vfloat32m4_t vx = __riscv_vle32_v_f32m4(&x[offset], avl);
            vfloat32m4_t t0 = __riscv_vfadd_vv_f32m4(va, vb, avl);
            vfloat32m4_t t1 = __riscv_vfmul_vv_f32m4(vc, vd, avl);
            vfloat32m4_t a_out = __riscv_vfmacc_vf_f32m4(t0, 0.25f, t1, avl);
            vfloat32m4_t d_out = __riscv_vfadd_vv_f32m4(a_out, ve, avl);
            d_out = __riscv_vfmacc_vf_f32m4(d_out, 0.125f, vx, avl);

            vint16m2_t x0 = __riscv_vle16_v_i16m2(&db1_src0[offset], avl);
            vint16m2_t x1 = __riscv_vle16_v_i16m2(&db1_src1[offset], avl);
            vint16m2_t xb = __riscv_vle16_v_i16m2(&db1_bias[offset], avl);
            vint32m4_t acc0 = __riscv_vwadd_vv_i32m4(x0, x1, avl);
            vint32m4_t acc1 = __riscv_vwmul_vv_i32m4(x0, x1, avl);
            vint32m4_t acc2 = __riscv_vwadd_vv_i32m4(x1, xb, avl);
            vint32m4_t acc3 = __riscv_vwmul_vv_i32m4(x1, xb, avl);
            vint32m4_t acc4 = __riscv_vwadd_vv_i32m4(x0, xb, avl);
            vint32m4_t acc5 = __riscv_vwmul_vv_i32m4(x0, xb, avl);
            vint32m4_t acc6 = __riscv_vwadd_vv_i32m4(xb, x1, avl);
            vint32m4_t acc7 = __riscv_vwmul_vv_i32m4(xb, x0, avl);
            vint32m4_t i_out = __riscv_vadd_vv_i32m4(acc0, acc1, avl);
            i_out = __riscv_vadd_vv_i32m4(i_out, acc2, avl);
            i_out = __riscv_vadd_vv_i32m4(i_out, acc3, avl);
            i_out = __riscv_vadd_vv_i32m4(i_out, acc4, avl);
            i_out = __riscv_vadd_vv_i32m4(i_out, acc5, avl);
            i_out = __riscv_vadd_vv_i32m4(i_out, acc6, avl);
            i_out = __riscv_vadd_vv_i32m4(i_out, acc7, avl);

            __riscv_vsetvl_e32m4(avl);
            __riscv_vse32_v_f32m4(&a[offset], a_out, avl);
            __riscv_vse32_v_f32m4(&d[offset], d_out, avl);
            __riscv_vse32_v_i32m4(&indx[offset], i_out, avl);
        }
```
