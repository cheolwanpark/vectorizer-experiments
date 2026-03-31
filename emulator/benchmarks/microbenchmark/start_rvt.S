#include "riscv_test.h"

RVTEST_RV64UV
RVTEST_CODE_BEGIN

  /* Set up stack and clear .bss (tohost/fromhost/results). */
  la   sp, _stack_top
  la   t0, _bss_start
  la   t1, _bss_end
1:
  beq  t0, t1, 2f
  sd   zero, 0(t0)
  addi t0, t0, 8
  j    1b
2:
  call main

  /* Signal pass if main returns. */
  RVTEST_PASS

RVTEST_CODE_END

RVTEST_DATA_BEGIN
RVTEST_DATA_END
