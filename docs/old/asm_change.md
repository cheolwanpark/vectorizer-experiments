# Assembly Changes

Source: `artifacts/rvv.sqlite` -> `artifacts/rvv-precise.sqlite`

## s442 default

`38405 -> 7371 cycles` (`5.210x`, precise/rvv `0.192`)

### Before (`rvv.sqlite`)

```asm
	.attribute	4, 16
	.attribute	5, "rv64i2p1_m2p0_a2p1_f2p2_d2p2_c2p0_v1p0_zicsr2p0_zifencei2p0_zmmul1p0_zaamo1p0_zalrsc1p0_zca1p0_zcd1p0_zve32f1p0_zve32x1p0_zve64d1p0_zve64f1p0_zve64x1p0_zvl128b1p0_zvl32b1p0_zvl64b1p0"
	.file	"s442.c"
	.option	push
	.option	arch, +a, +c, +d, +f, +m, +v, +zaamo, +zalrsc, +zca, +zcd, +zicsr, +zifencei, +zmmul, +zve32f, +zve32x, +zve64d, +zve64f, +zve64x, +zvl128b, +zvl32b, +zvl64b
	.text
	.globl	kernel                          # -- Begin function kernel
	.p2align	1
	.type	kernel,@function
kernel:                                 # @kernel
# %bb.0:                                # %entry
	addi	sp, sp, -16
	sd	ra, 8(sp)                       # 8-byte Folded Spill
	sd	s0, 0(sp)                       # 8-byte Folded Spill
	addi	s0, sp, 16
	csrr	a1, vlenb
	lui	a0, 1
	srli	a6, a1, 1
	sub	a0, a0, a6
	divu	a7, a0, a6
	vsetvli	a2, zero, e64, m4, ta, ma
	vid.v	v8
.Lpcrel_hi0:
	auipc	a2, %pcrel_hi(a)
.Lpcrel_hi1:
	auipc	a3, %pcrel_hi(indx)
.Lpcrel_hi2:
	auipc	a4, %pcrel_hi(b)
.Lpcrel_hi3:
	auipc	t0, %pcrel_hi(e)
.Lpcrel_hi4:
	auipc	a5, %pcrel_hi(d)
	addi	a4, a4, %pcrel_lo(.Lpcrel_hi2)
	vmv.v.x	v12, a4
	srli	a4, a1, 3
	slli	a7, a7, 4
	addi	a7, a7, 16
	mul	a0, a7, a4
.Lpcrel_hi5:
	auipc	a4, %pcrel_hi(c)
	slli	a1, a1, 1
	addi	a2, a2, %pcrel_lo(.Lpcrel_hi0)
	addi	a3, a3, %pcrel_lo(.Lpcrel_hi1)
	addi	a7, t0, %pcrel_lo(.Lpcrel_hi3)
	addi	a5, a5, %pcrel_lo(.Lpcrel_hi4)
	add	a0, a0, a2
	addi	a4, a4, %pcrel_lo(.Lpcrel_hi5)
.LBB0_1:                                # %vector.body
                                        # =>This Inner Loop Header: Depth=1
	vl2re32.v	v20, (a3)
	vsetvli	zero, zero, e32, m2, ta, ma
	vmseq.vi	v0, v20, 4
	vsetvli	zero, zero, e64, m4, ta, ma
	vmerge.vxm	v16, v12, a7, v0
	vsetvli	zero, zero, e32, m2, ta, ma
	vmseq.vi	v0, v20, 3
	vsetvli	zero, zero, e64, m4, ta, ma
	vmerge.vxm	v16, v16, a5, v0
	vsetvli	zero, zero, e32, m2, ta, ma
	vmseq.vi	v0, v20, 2
	vl2re32.v	v24, (a2)
	vsetvli	zero, zero, e64, m4, ta, ma
	vmerge.vxm	v16, v16, a4, v0
	vsll.vi	v20, v8, 2
	vadd.vv	v16, v16, v20
	vsetvli	zero, zero, e32, m2, ta, ma
	vluxei64.v	v20, (zero), v16
	vsetvli	zero, zero, e64, m4, ta, ma
	vadd.vx	v8, v8, a6
	vsetvli	zero, zero, e32, m2, ta, ma
	vfmadd.vv	v20, v20, v24
	vs2r.v	v20, (a2)
	add	a2, a2, a1
	add	a3, a3, a1
	bne	a2, a0, .LBB0_1
# %bb.2:                                # %for.end
	addi	sp, s0, -16
	ld	ra, 8(sp)                       # 8-byte Folded Reload
	ld	s0, 0(sp)                       # 8-byte Folded Reload
	addi	sp, sp, 16
	ret
.Lfunc_end0:
	.size	kernel, .Lfunc_end0-kernel
                                        # -- End function
	.option	pop
	.ident	"clang version 22.1.1"
	.section	".note.GNU-stack","",@progbits
```

### After (`rvv-precise.sqlite`)

```asm
	.attribute	4, 16
	.attribute	5, "rv64i2p1_m2p0_a2p1_f2p2_d2p2_c2p0_v1p0_zicsr2p0_zifencei2p0_zmmul1p0_zaamo1p0_zalrsc1p0_zca1p0_zcd1p0_zve32f1p0_zve32x1p0_zve64d1p0_zve64f1p0_zve64x1p0_zvl128b1p0_zvl32b1p0_zvl64b1p0"
	.file	"s442.c"
	.option	push
	.option	arch, +a, +c, +d, +f, +m, +v, +zaamo, +zalrsc, +zca, +zcd, +zicsr, +zifencei, +zmmul, +zve32f, +zve32x, +zve64d, +zve64f, +zve64x, +zvl128b, +zvl32b, +zvl64b
	.text
	.globl	kernel                          # -- Begin function kernel
	.p2align	1
	.type	kernel,@function
kernel:                                 # @kernel
# %bb.0:                                # %entry
	addi	sp, sp, -16
	sd	ra, 8(sp)                       # 8-byte Folded Spill
	sd	s0, 0(sp)                       # 8-byte Folded Spill
	addi	s0, sp, 16
	li	a0, 0
.Lpcrel_hi0:
	auipc	a1, %pcrel_hi(indx)
.Lpcrel_hi1:
	auipc	a3, %pcrel_hi(a)
.Lpcrel_hi2:
	auipc	a4, %pcrel_hi(b)
	li	a6, 2
.Lpcrel_hi3:
	auipc	a5, %pcrel_hi(.Lswitch.table.kernel)
	addi	a2, a1, %pcrel_lo(.Lpcrel_hi0)
	addi	a3, a3, %pcrel_lo(.Lpcrel_hi1)
	addi	a1, a4, %pcrel_lo(.Lpcrel_hi2)
	addi	t0, a5, %pcrel_lo(.Lpcrel_hi3)
	lui	a7, 4
	j	.LBB0_2
.LBB0_1:                                # %for.inc
                                        #   in Loop: Header=BB0_2 Depth=1
	add	a5, a3, a0
	add	a4, a4, a0
	flw	fa5, 0(a5)
	flw	fa4, 0(a4)
	fmadd.s	fa5, fa4, fa4, fa5
	addi	a0, a0, 4
	fsw	fa5, 0(a5)
	beq	a0, a7, .LBB0_4
.LBB0_2:                                # %for.body
                                        # =>This Inner Loop Header: Depth=1
	add	a4, a2, a0
	lw	a5, 0(a4)
	addiw	a5, a5, -2
	mv	a4, a1
	bltu	a6, a5, .LBB0_1
# %bb.3:                                # %switch.lookup
                                        #   in Loop: Header=BB0_2 Depth=1
	slli	a5, a5, 3
	add	a5, a5, t0
	ld	a4, 0(a5)
	j	.LBB0_1
.LBB0_4:                                # %for.end
	addi	sp, s0, -16
	ld	ra, 8(sp)                       # 8-byte Folded Reload
	ld	s0, 0(sp)                       # 8-byte Folded Reload
	addi	sp, sp, 16
	ret
.Lfunc_end0:
	.size	kernel, .Lfunc_end0-kernel
                                        # -- End function
	.option	pop
	.type	.Lswitch.table.kernel,@object   # @switch.table.kernel
	.section	.rodata,"a",@progbits
	.p2align	3, 0x0
.Lswitch.table.kernel:
	.quad	c
	.quad	d
	.quad	e
	.size	.Lswitch.table.kernel, 24

	.ident	"clang version 22.1.1"
	.section	".note.GNU-stack","",@progbits
```

## s111 default

`4902 -> 2155 cycles` (`2.275x`, precise/rvv `0.440`)

### Before (`rvv.sqlite`)

```asm
	.attribute	4, 16
	.attribute	5, "rv64i2p1_m2p0_a2p1_f2p2_d2p2_c2p0_v1p0_zicsr2p0_zifencei2p0_zmmul1p0_zaamo1p0_zalrsc1p0_zca1p0_zcd1p0_zve32f1p0_zve32x1p0_zve64d1p0_zve64f1p0_zve64x1p0_zvl128b1p0_zvl32b1p0_zvl64b1p0"
	.file	"s111.c"
	.option	push
	.option	arch, +a, +c, +d, +f, +m, +v, +zaamo, +zalrsc, +zca, +zcd, +zicsr, +zifencei, +zmmul, +zve32f, +zve32x, +zve64d, +zve64f, +zve64x, +zvl128b, +zvl32b, +zvl64b
	.text
	.globl	kernel                          # -- Begin function kernel
	.p2align	1
	.type	kernel,@function
kernel:                                 # @kernel
# %bb.0:                                # %entry
	addi	sp, sp, -16
	sd	ra, 8(sp)                       # 8-byte Folded Spill
	sd	s0, 0(sp)                       # 8-byte Folded Spill
	addi	s0, sp, 16
	li	a0, 1
.Lpcrel_hi0:
	auipc	a3, %pcrel_hi(a)
	li	t0, 8
.Lpcrel_hi1:
	auipc	a4, %pcrel_hi(b)
	slli	a2, a0, 11
	addi	a6, a3, %pcrel_lo(.Lpcrel_hi0)
	addi	a7, a4, %pcrel_lo(.Lpcrel_hi1)
	li	a5, 1
.LBB0_1:                                # %vector.body
                                        # =>This Inner Loop Header: Depth=1
	vsetvli	a3, a2, e32, m2, ta, ma
	slli	a4, a0, 2
	slli	a1, a5, 2
	add	a4, a4, a6
	add	a1, a1, a7
	addi	t1, a4, -4
	vlse32.v	v8, (a1), t0
	vlse32.v	v10, (t1), t0
	slli	a1, a3, 1
	sub	a2, a2, a3
	add	a0, a0, a1
	vfadd.vv	v8, v10, v8
	vsse32.v	v8, (a4), t0
	add	a5, a5, a1
	bnez	a2, .LBB0_1
# %bb.2:                                # %for.end
	addi	sp, s0, -16
	ld	ra, 8(sp)                       # 8-byte Folded Reload
	ld	s0, 0(sp)                       # 8-byte Folded Reload
	addi	sp, sp, 16
	ret
.Lfunc_end0:
	.size	kernel, .Lfunc_end0-kernel
                                        # -- End function
	.option	pop
	.ident	"clang version 22.1.1"
	.section	".note.GNU-stack","",@progbits
```

### After (`rvv-precise.sqlite`)

```asm
	.attribute	4, 16
	.attribute	5, "rv64i2p1_m2p0_a2p1_f2p2_d2p2_c2p0_v1p0_zicsr2p0_zifencei2p0_zmmul1p0_zaamo1p0_zalrsc1p0_zca1p0_zcd1p0_zve32f1p0_zve32x1p0_zve64d1p0_zve64f1p0_zve64x1p0_zvl128b1p0_zvl32b1p0_zvl64b1p0"
	.file	"s111.c"
	.option	push
	.option	arch, +a, +c, +d, +f, +m, +v, +zaamo, +zalrsc, +zca, +zcd, +zicsr, +zifencei, +zmmul, +zve32f, +zve32x, +zve64d, +zve64f, +zve64x, +zvl128b, +zvl32b, +zvl64b
	.text
	.globl	kernel                          # -- Begin function kernel
	.p2align	1
	.type	kernel,@function
kernel:                                 # @kernel
# %bb.0:                                # %entry
	addi	sp, sp, -16
	sd	ra, 8(sp)                       # 8-byte Folded Spill
	sd	s0, 0(sp)                       # 8-byte Folded Spill
	addi	s0, sp, 16
.Lpcrel_hi0:
	auipc	a0, %pcrel_hi(b)
.Lpcrel_hi1:
	auipc	a1, %pcrel_hi(a+4)
	lui	a2, 4
	addi	a3, a0, %pcrel_lo(.Lpcrel_hi0)
	addi	a0, a1, %pcrel_lo(.Lpcrel_hi1)
	addi	a2, a2, 4
	addi	a1, a3, 4
	add	a2, a2, a3
.LBB0_1:                                # %for.body
                                        # =>This Inner Loop Header: Depth=1
	flw	fa5, -4(a0)
	flw	fa4, 0(a1)
	addi	a1, a1, 8
	fadd.s	fa5, fa5, fa4
	fsw	fa5, 0(a0)
	addi	a0, a0, 8
	bne	a1, a2, .LBB0_1
# %bb.2:                                # %for.end
	addi	sp, s0, -16
	ld	ra, 8(sp)                       # 8-byte Folded Reload
	ld	s0, 0(sp)                       # 8-byte Folded Reload
	addi	sp, sp, 16
	ret
.Lfunc_end0:
	.size	kernel, .Lfunc_end0-kernel
                                        # -- End function
	.option	pop
	.ident	"clang version 22.1.1"
	.section	".note.GNU-stack","",@progbits
```

## s2101 default

`306 -> 136 cycles` (`2.250x`, precise/rvv `0.444`)

### Before (`rvv.sqlite`)

```asm
	.attribute	4, 16
	.attribute	5, "rv64i2p1_m2p0_a2p1_f2p2_d2p2_c2p0_v1p0_zicsr2p0_zifencei2p0_zmmul1p0_zaamo1p0_zalrsc1p0_zca1p0_zcd1p0_zve32f1p0_zve32x1p0_zve64d1p0_zve64f1p0_zve64x1p0_zvl128b1p0_zvl32b1p0_zvl64b1p0"
	.file	"s2101.c"
	.option	push
	.option	arch, +a, +c, +d, +f, +m, +v, +zaamo, +zalrsc, +zca, +zcd, +zicsr, +zifencei, +zmmul, +zve32f, +zve32x, +zve64d, +zve64f, +zve64x, +zvl128b, +zvl32b, +zvl64b
	.text
	.globl	kernel                          # -- Begin function kernel
	.p2align	1
	.type	kernel,@function
kernel:                                 # @kernel
# %bb.0:                                # %entry
	addi	sp, sp, -16
	sd	ra, 8(sp)                       # 8-byte Folded Spill
	sd	s0, 0(sp)                       # 8-byte Folded Spill
	addi	s0, sp, 16
	li	a0, 32
	vsetvli	a1, zero, e64, m4, ta, ma
	vid.v	v8
.Lpcrel_hi0:
	auipc	a1, %pcrel_hi(bb)
.Lpcrel_hi1:
	auipc	a2, %pcrel_hi(cc)
.Lpcrel_hi2:
	auipc	a3, %pcrel_hi(aa)
	addi	a1, a1, %pcrel_lo(.Lpcrel_hi0)
	addi	a2, a2, %pcrel_lo(.Lpcrel_hi1)
	addi	a3, a3, %pcrel_lo(.Lpcrel_hi2)
.LBB0_1:                                # %vector.body
                                        # =>This Inner Loop Header: Depth=1
	vsetvli	a4, a0, e64, m4, ta, ma
	vsll.vi	v12, v8, 7
	vsll.vi	v16, v8, 2
	vadd.vx	v20, v12, a1
	vadd.vx	v24, v12, a2
	vadd.vx	v12, v12, a3
	vadd.vv	v20, v20, v16
	vadd.vv	v24, v24, v16
	vadd.vv	v12, v12, v16
	vsetvli	zero, zero, e32, m2, ta, ma
	vluxei64.v	v16, (zero), v20
	vluxei64.v	v18, (zero), v24
	vluxei64.v	v20, (zero), v12
	sub	a0, a0, a4
	vfmacc.vv	v20, v16, v18
	vsoxei64.v	v20, (zero), v12
	vsetvli	zero, zero, e64, m4, ta, ma
	vadd.vx	v8, v8, a4
	bnez	a0, .LBB0_1
# %bb.2:                                # %for.end
	addi	sp, s0, -16
	ld	ra, 8(sp)                       # 8-byte Folded Reload
	ld	s0, 0(sp)                       # 8-byte Folded Reload
	addi	sp, sp, 16
	ret
.Lfunc_end0:
	.size	kernel, .Lfunc_end0-kernel
                                        # -- End function
	.option	pop
	.ident	"clang version 22.1.1"
	.section	".note.GNU-stack","",@progbits
```

### After (`rvv-precise.sqlite`)

```asm
	.attribute	4, 16
	.attribute	5, "rv64i2p1_m2p0_a2p1_f2p2_d2p2_c2p0_v1p0_zicsr2p0_zifencei2p0_zmmul1p0_zaamo1p0_zalrsc1p0_zca1p0_zcd1p0_zve32f1p0_zve32x1p0_zve64d1p0_zve64f1p0_zve64x1p0_zvl128b1p0_zvl32b1p0_zvl64b1p0"
	.file	"s2101.c"
	.option	push
	.option	arch, +a, +c, +d, +f, +m, +v, +zaamo, +zalrsc, +zca, +zcd, +zicsr, +zifencei, +zmmul, +zve32f, +zve32x, +zve64d, +zve64f, +zve64x, +zvl128b, +zvl32b, +zvl64b
	.text
	.globl	kernel                          # -- Begin function kernel
	.p2align	1
	.type	kernel,@function
kernel:                                 # @kernel
# %bb.0:                                # %entry
	addi	sp, sp, -16
	sd	ra, 8(sp)                       # 8-byte Folded Spill
	sd	s0, 0(sp)                       # 8-byte Folded Spill
	addi	s0, sp, 16
.Lpcrel_hi0:
	auipc	a0, %pcrel_hi(aa)
.Lpcrel_hi1:
	auipc	a1, %pcrel_hi(cc)
.Lpcrel_hi2:
	auipc	a2, %pcrel_hi(bb)
	lui	a3, 1
	addi	a0, a0, %pcrel_lo(.Lpcrel_hi0)
	addi	a1, a1, %pcrel_lo(.Lpcrel_hi1)
	addi	a2, a2, %pcrel_lo(.Lpcrel_hi2)
	addi	a3, a3, 128
	add	a3, a3, a0
.LBB0_1:                                # %for.body
                                        # =>This Inner Loop Header: Depth=1
	flw	fa5, 0(a2)
	flw	fa4, 0(a1)
	flw	fa3, 0(a0)
	fmadd.s	fa5, fa5, fa4, fa3
	fsw	fa5, 0(a0)
	addi	a0, a0, 132
	addi	a1, a1, 132
	addi	a2, a2, 132
	bne	a0, a3, .LBB0_1
# %bb.2:                                # %for.end
	addi	sp, s0, -16
	ld	ra, 8(sp)                       # 8-byte Folded Reload
	ld	s0, 0(sp)                       # 8-byte Folded Reload
	addi	sp, sp, 16
	ret
.Lfunc_end0:
	.size	kernel, .Lfunc_end0-kernel
                                        # -- End function
	.option	pop
	.ident	"clang version 22.1.1"
	.section	".note.GNU-stack","",@progbits
```

## s1115 default

`3532 -> 1871 cycles` (`1.888x`, precise/rvv `0.530`)

### Before (`rvv.sqlite`)

```asm
	.attribute	4, 16
	.attribute	5, "rv64i2p1_m2p0_a2p1_f2p2_d2p2_c2p0_v1p0_zicsr2p0_zifencei2p0_zmmul1p0_zaamo1p0_zalrsc1p0_zca1p0_zcd1p0_zve32f1p0_zve32x1p0_zve64d1p0_zve64f1p0_zve64x1p0_zvl128b1p0_zvl32b1p0_zvl64b1p0"
	.file	"s1115.c"
	.option	push
	.option	arch, +a, +c, +d, +f, +m, +v, +zaamo, +zalrsc, +zca, +zcd, +zicsr, +zifencei, +zmmul, +zve32f, +zve32x, +zve64d, +zve64f, +zve64x, +zvl128b, +zvl32b, +zvl64b
	.text
	.globl	kernel                          # -- Begin function kernel
	.p2align	1
	.type	kernel,@function
kernel:                                 # @kernel
# %bb.0:                                # %entry
	addi	sp, sp, -16
	sd	ra, 8(sp)                       # 8-byte Folded Spill
	sd	s0, 0(sp)                       # 8-byte Folded Spill
	addi	s0, sp, 16
	li	t2, 0
	li	t3, 0
	li	t4, 0
	li	t5, 32
.Lpcrel_hi0:
	auipc	a0, %pcrel_hi(aa)
.Lpcrel_hi1:
	auipc	a1, %pcrel_hi(cc)
.Lpcrel_hi2:
	auipc	a4, %pcrel_hi(bb)
	addi	a6, a0, %pcrel_lo(.Lpcrel_hi0)
	addi	a7, a1, %pcrel_lo(.Lpcrel_hi1)
	addi	t0, a4, %pcrel_lo(.Lpcrel_hi2)
	li	a5, 128
.LBB0_1:                                # %vector.body
                                        # =>This Inner Loop Header: Depth=1
	vsetvli	t1, t5, e32, m2, ta, ma
	slli	a0, t3, 7
	slli	a1, t2, 2
	slli	a4, t4, 7
	add	a0, a0, a6
	add	a1, a1, a7
	add	a4, a4, t0
	vlse32.v	v8, (a0), a5
	vle32.v	v10, (a1)
	vlse32.v	v12, (a4), a5
	addi	a2, a0, 4
	addi	a3, a1, 128
	vfmacc.vv	v12, v8, v10
	vsse32.v	v12, (a0), a5
	vle32.v	v8, (a3)
	addi	a3, a4, 4
	vlse32.v	v10, (a2), a5
	vlse32.v	v12, (a3), a5
	addi	a3, a0, 8
	vfmacc.vv	v12, v10, v8
	vsse32.v	v12, (a2), a5
	addi	a2, a1, 256
	vle32.v	v8, (a2)
	addi	a2, a4, 8
	vlse32.v	v10, (a3), a5
	vlse32.v	v12, (a2), a5
	addi	a2, a0, 12
	vfmacc.vv	v12, v10, v8
	vsse32.v	v12, (a3), a5
	addi	a3, a1, 384
	vle32.v	v8, (a3)
	addi	a3, a4, 12
	vlse32.v	v10, (a2), a5
	vlse32.v	v12, (a3), a5
	addi	a3, a0, 16
	vfmacc.vv	v12, v10, v8
	vsse32.v	v12, (a2), a5
	addi	a2, a1, 512
	vle32.v	v8, (a2)
	addi	a2, a4, 16
	vlse32.v	v10, (a3), a5
	vlse32.v	v12, (a2), a5
	addi	a2, a0, 20
	vfmacc.vv	v12, v10, v8
	vsse32.v	v12, (a3), a5
	addi	a3, a1, 640
	vle32.v	v8, (a3)
	addi	a3, a4, 20
	vlse32.v	v10, (a2), a5
	vlse32.v	v12, (a3), a5
	addi	a3, a0, 24
	vfmacc.vv	v12, v10, v8
	vsse32.v	v12, (a2), a5
	addi	a2, a1, 768
	vle32.v	v8, (a2)
	addi	a2, a4, 24
	vlse32.v	v10, (a3), a5
	vlse32.v	v12, (a2), a5
	addi	a2, a0, 28
	vfmacc.vv	v12, v10, v8
	vsse32.v	v12, (a3), a5
	addi	a3, a1, 896
	vle32.v	v8, (a3)
	addi	a3, a4, 28
	vlse32.v	v10, (a2), a5
	vlse32.v	v12, (a3), a5
	addi	a3, a0, 32
	vfmacc.vv	v12, v10, v8
	vsse32.v	v12, (a2), a5
	addi	a2, a1, 1024
	vle32.v	v8, (a2)
	addi	a2, a4, 32
	vlse32.v	v10, (a3), a5
	vlse32.v	v12, (a2), a5
	addi	a2, a0, 36
	vfmacc.vv	v12, v10, v8
	vsse32.v	v12, (a3), a5
	addi	a3, a1, 1152
	vle32.v	v8, (a3)
	addi	a3, a4, 36
	vlse32.v	v10, (a2), a5
	vlse32.v	v12, (a3), a5
	addi	a3, a0, 40
	vfmacc.vv	v12, v10, v8
	vsse32.v	v12, (a2), a5
	addi	a2, a1, 1280
	vle32.v	v8, (a2)
	addi	a2, a4, 40
	vlse32.v	v10, (a3), a5
	vlse32.v	v12, (a2), a5
	addi	a2, a0, 44
	vfmacc.vv	v12, v10, v8
	vsse32.v	v12, (a3), a5
	addi	a3, a1, 1408
	vle32.v	v8, (a3)
	addi	a3, a4, 44
	vlse32.v	v10, (a2), a5
	vlse32.v	v12, (a3), a5
	addi	a3, a0, 48
	vfmacc.vv	v12, v10, v8
	vsse32.v	v12, (a2), a5
	addi	a2, a1, 1536
	vle32.v	v8, (a2)
	addi	a2, a4, 48
	vlse32.v	v10, (a3), a5
	vlse32.v	v12, (a2), a5
	addi	a2, a0, 52
	vfmacc.vv	v12, v10, v8
	vsse32.v	v12, (a3), a5
	addi	a3, a1, 1664
	vle32.v	v8, (a3)
	addi	a3, a4, 52
	vlse32.v	v10, (a2), a5
	vlse32.v	v12, (a3), a5
	addi	a3, a0, 56
	vfmacc.vv	v12, v10, v8
	vsse32.v	v12, (a2), a5
	addi	a2, a1, 1792
	vle32.v	v8, (a2)
	addi	a2, a4, 56
	vlse32.v	v10, (a3), a5
	vlse32.v	v12, (a2), a5
	addi	a2, a0, 60
	vfmacc.vv	v12, v10, v8
	vsse32.v	v12, (a3), a5
	addi	a3, a1, 1920
	vle32.v	v8, (a3)
	addi	a3, a4, 60
	vlse32.v	v10, (a2), a5
	vlse32.v	v12, (a3), a5
	addi	a3, a0, 64
	addi	a1, a1, 2047
	vfmacc.vv	v12, v10, v8
	vsse32.v	v12, (a2), a5
	addi	a2, a1, 1
	vle32.v	v8, (a2)
	addi	a2, a4, 64
	vlse32.v	v10, (a3), a5
	vlse32.v	v12, (a2), a5
	addi	a2, a0, 68
	vfmacc.vv	v12, v10, v8
	vsse32.v	v12, (a3), a5
	addi	a3, a1, 129
	vle32.v	v8, (a3)
	addi	a3, a4, 68
	vlse32.v	v10, (a2), a5
	vlse32.v	v12, (a3), a5
	addi	a3, a0, 72
	vfmacc.vv	v12, v10, v8
	vsse32.v	v12, (a2), a5
	addi	a2, a1, 257
	vle32.v	v8, (a2)
	addi	a2, a4, 72
	vlse32.v	v10, (a3), a5
	vlse32.v	v12, (a2), a5
	addi	a2, a0, 76
	vfmacc.vv	v12, v10, v8
	vsse32.v	v12, (a3), a5
	addi	a3, a1, 385
	vle32.v	v8, (a3)
	addi	a3, a4, 76
	vlse32.v	v10, (a2), a5
	vlse32.v	v12, (a3), a5
	addi	a3, a0, 80
	vfmacc.vv	v12, v10, v8
	vsse32.v	v12, (a2), a5
	addi	a2, a1, 513
	vle32.v	v8, (a2)
	addi	a2, a4, 80
	vlse32.v	v10, (a3), a5
	vlse32.v	v12, (a2), a5
	addi	a2, a0, 84
	vfmacc.vv	v12, v10, v8
	vsse32.v	v12, (a3), a5
	addi	a3, a1, 641
	vle32.v	v8, (a3)
	addi	a3, a4, 84
	vlse32.v	v10, (a2), a5
	vlse32.v	v12, (a3), a5
	addi	a3, a0, 88
	vfmacc.vv	v12, v10, v8
	vsse32.v	v12, (a2), a5
	addi	a2, a1, 769
	vle32.v	v8, (a2)
	addi	a2, a4, 88
	vlse32.v	v10, (a3), a5
	vlse32.v	v12, (a2), a5
	addi	a2, a0, 92
	vfmacc.vv	v12, v10, v8
	vsse32.v	v12, (a3), a5
	addi	a3, a1, 897
	vle32.v	v8, (a3)
	addi	a3, a4, 92
	vlse32.v	v10, (a2), a5
	vlse32.v	v12, (a3), a5
	addi	a3, a0, 96
	vfmacc.vv	v12, v10, v8
	vsse32.v	v12, (a2), a5
	addi	a2, a1, 1025
	vle32.v	v8, (a2)
	addi	a2, a4, 96
	vlse32.v	v10, (a3), a5
	vlse32.v	v12, (a2), a5
	addi	a2, a0, 100
	vfmacc.vv	v12, v10, v8
	vsse32.v	v12, (a3), a5
	addi	a3, a1, 1153
	vle32.v	v8, (a3)
	addi	a3, a4, 100
	vlse32.v	v10, (a2), a5
	vlse32.v	v12, (a3), a5
	addi	a3, a0, 104
	vfmacc.vv	v12, v10, v8
	vsse32.v	v12, (a2), a5
	addi	a2, a1, 1281
	vle32.v	v8, (a2)
	addi	a2, a4, 104
	vlse32.v	v10, (a3), a5
	vlse32.v	v12, (a2), a5
	addi	a2, a0, 108
	vfmacc.vv	v12, v10, v8
	vsse32.v	v12, (a3), a5
	addi	a3, a1, 1409
	vle32.v	v8, (a3)
	addi	a3, a4, 108
	vlse32.v	v10, (a2), a5
	vlse32.v	v12, (a3), a5
	addi	a3, a0, 112
	vfmacc.vv	v12, v10, v8
	vsse32.v	v12, (a2), a5
	addi	a2, a1, 1537
	vle32.v	v8, (a2)
	addi	a2, a4, 112
	vlse32.v	v10, (a3), a5
	vlse32.v	v12, (a2), a5
	addi	a2, a0, 116
	vfmacc.vv	v12, v10, v8
	vsse32.v	v12, (a3), a5
	addi	a3, a1, 1665
	vle32.v	v8, (a3)
	addi	a3, a4, 116
	vlse32.v	v10, (a2), a5
	vlse32.v	v12, (a3), a5
	addi	a3, a0, 120
	vfmacc.vv	v12, v10, v8
	vsse32.v	v12, (a2), a5
	addi	a2, a1, 1793
	vle32.v	v8, (a2)
	addi	a2, a4, 120
	vlse32.v	v10, (a3), a5
	vlse32.v	v12, (a2), a5
	addi	a0, a0, 124
	addi	a2, a4, 124
	addi	a1, a1, 1921
	vfmacc.vv	v12, v10, v8
	vsse32.v	v12, (a3), a5
	vlse32.v	v8, (a0), a5
	vle32.v	v10, (a1)
	vlse32.v	v12, (a2), a5
	add	t2, t2, t1
	sub	t5, t5, t1
	add	t3, t3, t1
	vfmacc.vv	v12, v8, v10
	vsse32.v	v12, (a0), a5
	add	t4, t4, t1
	bnez	t5, .LBB0_1
# %bb.2:                                # %for.end20
	addi	sp, s0, -16
	ld	ra, 8(sp)                       # 8-byte Folded Reload
	ld	s0, 0(sp)                       # 8-byte Folded Reload
	addi	sp, sp, 16
	ret
.Lfunc_end0:
	.size	kernel, .Lfunc_end0-kernel
                                        # -- End function
	.option	pop
	.ident	"clang version 22.1.1"
	.section	".note.GNU-stack","",@progbits
```

### After (`rvv-precise.sqlite`)

```asm
	.attribute	4, 16
	.attribute	5, "rv64i2p1_m2p0_a2p1_f2p2_d2p2_c2p0_v1p0_zicsr2p0_zifencei2p0_zmmul1p0_zaamo1p0_zalrsc1p0_zca1p0_zcd1p0_zve32f1p0_zve32x1p0_zve64d1p0_zve64f1p0_zve64x1p0_zvl128b1p0_zvl32b1p0_zvl64b1p0"
	.file	"s1115.c"
	.option	push
	.option	arch, +a, +c, +d, +f, +m, +v, +zaamo, +zalrsc, +zca, +zcd, +zicsr, +zifencei, +zmmul, +zve32f, +zve32x, +zve64d, +zve64f, +zve64x, +zvl128b, +zvl32b, +zvl64b
	.text
	.globl	kernel                          # -- Begin function kernel
	.p2align	1
	.type	kernel,@function
kernel:                                 # @kernel
# %bb.0:                                # %entry
	addi	sp, sp, -16
	sd	ra, 8(sp)                       # 8-byte Folded Spill
	sd	s0, 0(sp)                       # 8-byte Folded Spill
	addi	s0, sp, 16
	li	a5, 0
.Lpcrel_hi0:
	auipc	a2, %pcrel_hi(cc+2048)
.Lpcrel_hi1:
	auipc	a3, %pcrel_hi(aa)
.Lpcrel_hi2:
	auipc	a4, %pcrel_hi(bb)
	li	t1, 128
	addi	a2, a2, %pcrel_lo(.Lpcrel_hi0)
	addi	a7, a3, %pcrel_lo(.Lpcrel_hi1)
	addi	t0, a4, %pcrel_lo(.Lpcrel_hi2)
	lui	a6, 1
	vsetivli	zero, 8, e32, m2, ta, ma
.LBB0_1:                                # %for.cond1.preheader
                                        # =>This Inner Loop Header: Depth=1
	add	a0, a7, a5
	addi	a3, a2, -2048
	add	a4, t0, a5
	vle32.v	v8, (a0)
	vlse32.v	v10, (a3), t1
	vle32.v	v12, (a4)
	addi	t2, a2, -1024
	addi	a1, a0, 32
	addi	a3, a4, 32
	vfmacc.vv	v12, v8, v10
	vle32.v	v8, (a1)
	vle32.v	v10, (a3)
	vse32.v	v12, (a0)
	vlse32.v	v12, (t2), t1
	addi	a3, a0, 64
	addi	t2, a4, 64
	vfmacc.vv	v10, v8, v12
	vle32.v	v8, (a3)
	vle32.v	v12, (t2)
	vse32.v	v10, (a1)
	vlse32.v	v10, (a2), t1
	addi	a1, a2, 1024
	addi	a0, a0, 96
	addi	a4, a4, 96
	vfmacc.vv	v12, v8, v10
	vle32.v	v8, (a0)
	vle32.v	v10, (a4)
	vse32.v	v12, (a3)
	vlse32.v	v12, (a1), t1
	addi	a5, a5, 128
	vfmacc.vv	v10, v8, v12
	vse32.v	v10, (a0)
	addi	a2, a2, 4
	bne	a5, a6, .LBB0_1
# %bb.2:                                # %for.end20
	addi	sp, s0, -16
	ld	ra, 8(sp)                       # 8-byte Folded Reload
	ld	s0, 0(sp)                       # 8-byte Folded Reload
	addi	sp, sp, 16
	ret
.Lfunc_end0:
	.size	kernel, .Lfunc_end0-kernel
                                        # -- End function
	.option	pop
	.ident	"clang version 22.1.1"
	.section	".note.GNU-stack","",@progbits
```

## s4117 default

`19099 -> 11691 cycles` (`1.634x`, precise/rvv `0.612`)

### Before (`rvv.sqlite`)

```asm
	.attribute	4, 16
	.attribute	5, "rv64i2p1_m2p0_a2p1_f2p2_d2p2_c2p0_v1p0_zicsr2p0_zifencei2p0_zmmul1p0_zaamo1p0_zalrsc1p0_zca1p0_zcd1p0_zve32f1p0_zve32x1p0_zve64d1p0_zve64f1p0_zve64x1p0_zvl128b1p0_zvl32b1p0_zvl64b1p0"
	.file	"s4117.c"
	.option	push
	.option	arch, +a, +c, +d, +f, +m, +v, +zaamo, +zalrsc, +zca, +zcd, +zicsr, +zifencei, +zmmul, +zve32f, +zve32x, +zve64d, +zve64f, +zve64x, +zvl128b, +zvl32b, +zvl64b
	.text
	.globl	kernel                          # -- Begin function kernel
	.p2align	1
	.type	kernel,@function
kernel:                                 # @kernel
# %bb.0:                                # %entry
	addi	sp, sp, -16
	sd	ra, 8(sp)                       # 8-byte Folded Spill
	sd	s0, 0(sp)                       # 8-byte Folded Spill
	addi	s0, sp, 16
	csrr	a1, vlenb
	lui	a0, 1
	srli	a6, a1, 1
	sub	a0, a0, a6
	divu	a0, a0, a6
	vsetvli	a2, zero, e64, m4, ta, ma
	vid.v	v8
.Lpcrel_hi0:
	auipc	a2, %pcrel_hi(a)
.Lpcrel_hi1:
	auipc	a3, %pcrel_hi(d)
.Lpcrel_hi2:
	auipc	a4, %pcrel_hi(b)
	lui	a7, 524288
	srli	a5, a1, 3
	slli	a0, a0, 4
	addi	a0, a0, 16
	mul	a0, a0, a5
.Lpcrel_hi3:
	auipc	a5, %pcrel_hi(c)
	slli	a1, a1, 1
	addi	a2, a2, %pcrel_lo(.Lpcrel_hi0)
	addi	a3, a3, %pcrel_lo(.Lpcrel_hi1)
	addi	a4, a4, %pcrel_lo(.Lpcrel_hi2)
	addiw	a7, a7, -1
	add	a0, a0, a2
	addi	a5, a5, %pcrel_lo(.Lpcrel_hi3)
.LBB0_1:                                # %vector.body
                                        # =>This Inner Loop Header: Depth=1
	vl2re32.v	v16, (a4)
	vsetvli	zero, zero, e64, m4, ta, ma
	vsrl.vi	v12, v8, 1
	vand.vx	v12, v12, a7
	vsll.vi	v12, v12, 2
	vsetvli	zero, zero, e32, m2, ta, ma
	vluxei64.v	v18, (a5), v12
	vl2re32.v	v12, (a3)
	vsetvli	zero, zero, e64, m4, ta, ma
	vadd.vx	v8, v8, a6
	vsetvli	zero, zero, e32, m2, ta, ma
	vfmadd.vv	v12, v18, v16
	vs2r.v	v12, (a2)
	add	a2, a2, a1
	add	a3, a3, a1
	add	a4, a4, a1
	bne	a2, a0, .LBB0_1
# %bb.2:                                # %for.end
	addi	sp, s0, -16
	ld	ra, 8(sp)                       # 8-byte Folded Reload
	ld	s0, 0(sp)                       # 8-byte Folded Reload
	addi	sp, sp, 16
	ret
.Lfunc_end0:
	.size	kernel, .Lfunc_end0-kernel
                                        # -- End function
	.option	pop
	.ident	"clang version 22.1.1"
	.section	".note.GNU-stack","",@progbits
```

### After (`rvv-precise.sqlite`)

```asm
	.attribute	4, 16
	.attribute	5, "rv64i2p1_m2p0_a2p1_f2p2_d2p2_c2p0_v1p0_zicsr2p0_zifencei2p0_zmmul1p0_zaamo1p0_zalrsc1p0_zca1p0_zcd1p0_zve32f1p0_zve32x1p0_zve64d1p0_zve64f1p0_zve64x1p0_zvl128b1p0_zvl32b1p0_zvl64b1p0"
	.file	"s4117.c"
	.option	push
	.option	arch, +a, +c, +d, +f, +m, +v, +zaamo, +zalrsc, +zca, +zcd, +zicsr, +zifencei, +zmmul, +zve32f, +zve32x, +zve64d, +zve64f, +zve64x, +zvl128b, +zvl32b, +zvl64b
	.text
	.globl	kernel                          # -- Begin function kernel
	.p2align	1
	.type	kernel,@function
kernel:                                 # @kernel
# %bb.0:                                # %entry
	addi	sp, sp, -16
	sd	ra, 8(sp)                       # 8-byte Folded Spill
	sd	s0, 0(sp)                       # 8-byte Folded Spill
	addi	s0, sp, 16
.Lpcrel_hi0:
	auipc	a0, %pcrel_hi(a)
.Lpcrel_hi1:
	auipc	a1, %pcrel_hi(d)
.Lpcrel_hi2:
	auipc	a2, %pcrel_hi(c)
.Lpcrel_hi3:
	auipc	a3, %pcrel_hi(b)
	addi	a0, a0, %pcrel_lo(.Lpcrel_hi0)
	addi	a1, a1, %pcrel_lo(.Lpcrel_hi1)
	addi	a2, a2, %pcrel_lo(.Lpcrel_hi2)
	addi	a3, a3, %pcrel_lo(.Lpcrel_hi3)
	lui	a4, 4
	add	a4, a4, a0
	vsetivli	zero, 2, e32, mf2, ta, ma
.LBB0_1:                                # %vector.body
                                        # =>This Inner Loop Header: Depth=1
	vle32.v	v8, (a3)
	flw	fa5, 0(a2)
	vle32.v	v9, (a1)
	addi	a1, a1, 8
	vfmadd.vf	v9, fa5, v8
	vse32.v	v9, (a0)
	addi	a0, a0, 8
	addi	a2, a2, 4
	addi	a3, a3, 8
	bne	a0, a4, .LBB0_1
# %bb.2:                                # %for.end
	addi	sp, s0, -16
	ld	ra, 8(sp)                       # 8-byte Folded Reload
	ld	s0, 0(sp)                       # 8-byte Folded Reload
	addi	sp, sp, 16
	ret
.Lfunc_end0:
	.size	kernel, .Lfunc_end0-kernel
                                        # -- End function
	.option	pop
	.ident	"clang version 22.1.1"
	.section	".note.GNU-stack","",@progbits
```

## s1232 default

`2194 -> 2088 cycles` (`1.051x`, precise/rvv `0.952`)

### Before (`rvv.sqlite`)

```asm
	.attribute	4, 16
	.attribute	5, "rv64i2p1_m2p0_a2p1_f2p2_d2p2_c2p0_v1p0_zicsr2p0_zifencei2p0_zmmul1p0_zaamo1p0_zalrsc1p0_zca1p0_zcd1p0_zve32f1p0_zve32x1p0_zve64d1p0_zve64f1p0_zve64x1p0_zvl128b1p0_zvl32b1p0_zvl64b1p0"
	.file	"s1232.c"
	.option	push
	.option	arch, +a, +c, +d, +f, +m, +v, +zaamo, +zalrsc, +zca, +zcd, +zicsr, +zifencei, +zmmul, +zve32f, +zve32x, +zve64d, +zve64f, +zve64x, +zvl128b, +zvl32b, +zvl64b
	.text
	.globl	kernel                          # -- Begin function kernel
	.p2align	1
	.type	kernel,@function
kernel:                                 # @kernel
# %bb.0:                                # %entry
	addi	sp, sp, -16
	sd	ra, 8(sp)                       # 8-byte Folded Spill
	sd	s0, 0(sp)                       # 8-byte Folded Spill
	addi	s0, sp, 16
	li	t2, 0
.Lpcrel_hi0:
	auipc	a0, %pcrel_hi(bb)
.Lpcrel_hi1:
	auipc	a1, %pcrel_hi(cc)
.Lpcrel_hi2:
	auipc	a2, %pcrel_hi(aa)
	li	a6, 32
	addi	a7, a0, %pcrel_lo(.Lpcrel_hi0)
	addi	t0, a1, %pcrel_lo(.Lpcrel_hi1)
	addi	t1, a2, %pcrel_lo(.Lpcrel_hi2)
	li	t6, 128
.LBB0_1:                                # %for.cond1.preheader
                                        # =>This Loop Header: Depth=1
                                        #     Child Loop BB0_2 Depth 2
	slli	a4, t2, 2
	add	t3, a7, a4
	add	t4, t0, a4
	add	t5, t1, a4
	sub	a1, a6, t2
	mv	a4, t2
	mv	a2, t2
	mv	a3, t2
.LBB0_2:                                # %vector.body
                                        #   Parent Loop BB0_1 Depth=1
                                        # =>  This Inner Loop Header: Depth=2
	vsetvli	a5, a1, e32, m2, ta, ma
	slli	a0, a4, 7
	add	a0, a0, t3
	vlse32.v	v8, (a0), t6
	slli	a0, a2, 7
	add	a0, a0, t4
	vlse32.v	v10, (a0), t6
	slli	a0, a3, 7
	add	a0, a0, t5
	sub	a1, a1, a5
	add	a4, a4, a5
	add	a2, a2, a5
	vfadd.vv	v8, v8, v10
	vsse32.v	v8, (a0), t6
	add	a3, a3, a5
	bnez	a1, .LBB0_2
# %bb.3:                                # %for.inc14
                                        #   in Loop: Header=BB0_1 Depth=1
	addi	t2, t2, 1
	bne	t2, a6, .LBB0_1
# %bb.4:                                # %for.end16
	addi	sp, s0, -16
	ld	ra, 8(sp)                       # 8-byte Folded Reload
	ld	s0, 0(sp)                       # 8-byte Folded Reload
	addi	sp, sp, 16
	ret
.Lfunc_end0:
	.size	kernel, .Lfunc_end0-kernel
                                        # -- End function
	.option	pop
	.ident	"clang version 22.1.1"
	.section	".note.GNU-stack","",@progbits
```

### After (`rvv-precise.sqlite`)

```asm
	.attribute	4, 16
	.attribute	5, "rv64i2p1_m2p0_a2p1_f2p2_d2p2_c2p0_v1p0_zicsr2p0_zifencei2p0_zmmul1p0_zaamo1p0_zalrsc1p0_zca1p0_zcd1p0_zve32f1p0_zve32x1p0_zve64d1p0_zve64f1p0_zve64x1p0_zvl128b1p0_zvl32b1p0_zvl64b1p0"
	.file	"s1232.c"
	.option	push
	.option	arch, +a, +c, +d, +f, +m, +v, +zaamo, +zalrsc, +zca, +zcd, +zicsr, +zifencei, +zmmul, +zve32f, +zve32x, +zve64d, +zve64f, +zve64x, +zvl128b, +zvl32b, +zvl64b
	.text
	.globl	kernel                          # -- Begin function kernel
	.p2align	1
	.type	kernel,@function
kernel:                                 # @kernel
# %bb.0:                                # %entry
	addi	sp, sp, -16
	sd	ra, 8(sp)                       # 8-byte Folded Spill
	sd	s0, 0(sp)                       # 8-byte Folded Spill
	addi	s0, sp, 16
	li	t2, 0
.Lpcrel_hi0:
	auipc	a0, %pcrel_hi(aa)
.Lpcrel_hi1:
	auipc	a1, %pcrel_hi(cc)
.Lpcrel_hi2:
	auipc	a2, %pcrel_hi(bb)
	addi	t0, a0, %pcrel_lo(.Lpcrel_hi0)
	addi	t1, a1, %pcrel_lo(.Lpcrel_hi1)
	addi	a4, a2, %pcrel_lo(.Lpcrel_hi2)
	lui	a6, 1
	li	a7, 32
	mv	a0, t0
.LBB0_1:                                # %for.cond1.preheader
                                        # =>This Loop Header: Depth=1
                                        #     Child Loop BB0_2 Depth 2
	slli	a1, t2, 2
	add	a1, a1, t0
	add	a5, a1, a6
	mv	a3, a4
	mv	a2, t1
	mv	a1, a0
.LBB0_2:                                # %for.body3
                                        #   Parent Loop BB0_1 Depth=1
                                        # =>  This Inner Loop Header: Depth=2
	flw	fa5, 0(a3)
	flw	fa4, 0(a2)
	fadd.s	fa5, fa5, fa4
	fsw	fa5, 0(a1)
	addi	a1, a1, 128
	addi	a2, a2, 128
	addi	a3, a3, 128
	bne	a1, a5, .LBB0_2
# %bb.3:                                # %for.inc14
                                        #   in Loop: Header=BB0_1 Depth=1
	addi	t2, t2, 1
	addi	a0, a0, 132
	addi	t1, t1, 132
	addi	a4, a4, 132
	bne	t2, a7, .LBB0_1
# %bb.4:                                # %for.end16
	addi	sp, s0, -16
	ld	ra, 8(sp)                       # 8-byte Folded Reload
	ld	s0, 0(sp)                       # 8-byte Folded Reload
	addi	sp, sp, 16
	ret
.Lfunc_end0:
	.size	kernel, .Lfunc_end0-kernel
                                        # -- End function
	.option	pop
	.ident	"clang version 22.1.1"
	.section	".note.GNU-stack","",@progbits
```
