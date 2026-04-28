/**
 * s311 - Sum Reduction
 *
 * Experiment 5: Reduction Performance vs VLEN
 *
 * Hypothesis: Reduction performance doesn't scale linearly with VLEN
 *   - Higher VLEN = deeper reduction tree = higher latency
 *   - But fewer loop iterations = lower loop overhead
 *   - Optimal LMUL varies by VLEN
 *
 * Generated Instructions: vfredosum.vs or vfredusum.vs
 *
 * TSVC Category: Reductions (Scale=11.65)
 */
#include "common.h"

void kernel(void) {
    real_t sum = 0.0f;
    for (int i = 0; i < LEN_1D; i++) {
        sum += a[i];
    }
    // Prevent optimization: store to volatile
    volatile real_t result = sum;
    (void)result;
}
