.section .text.init
.globl _start
_start:
  j reset_vector

trap_vector:
  /* Signal failure if any trap occurs. */
  la t0, tohost
  li t1, 3
  sd t1, 0(t0)
1:
  j 1b

reset_vector:
  /* Park non-zero harts. */
  csrr a0, mhartid
  bnez a0, reset_vector

  /* Basic machine-mode setup. */
  la t0, trap_vector
  csrw mtvec, t0
  csrw satp, zero
  csrw mie, zero

  /* Allow all memory accesses (NAPOT). */
  li t0, 1
  slli t0, t0, 0x35
  addi t0, t0, -1
  csrw pmpaddr0, t0
  li t0, 0x1f
  csrw pmpcfg0, t0

  /* Enable FP + vector state (set to Dirty). */
  li t0, ((3 << 13) | (3 << 9))  /* MSTATUS_FS | MSTATUS_VS */
  csrs mstatus, t0

  la sp, _stack_top

  /* Zero .bss so tohost/fromhost start clean. */
  la t0, _bss_start
  la t1, _bss_end
1:
  beq t0, t1, 2f
  sd zero, 0(t0)
  addi t0, t0, 8
  j 1b
2:
  call main

  /* If main returns, signal success and halt. */
  la t0, tohost
  li t1, 1
  sd t1, 0(t0)
3:
  j 3b
