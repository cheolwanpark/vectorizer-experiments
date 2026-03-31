/**
 * s000 - Simple Stride-1 Vector Add
 *
 * Experiment 1: LMUL Optimal Value per Hardware
 *
 * Hypothesis: Optimal LMUL depends on VLEN
 *   - XiangShan (VLEN=128): Higher LMUL (4-8) is better
 *   - Saturn (VLEN=512): Medium LMUL (2-4) is optimal
 *   - T1 (VLEN=1024): Lower LMUL (1-2) is optimal
 *
 * TSVC Category: Linear Dependence (Scale=18.22)
 */
#include "common.h"

void kernel(void) {
    for (int i = 0; i < LEN_1D; i++) {
        a[i] = b[i] + c[i];
    }
}
