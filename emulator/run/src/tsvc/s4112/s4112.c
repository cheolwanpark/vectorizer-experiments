/**
 * s4112 - Indirect Addressing (Gather Pattern)
 *
 * Experiment 3: Indexed Load/Store Performance
 *
 * TSVC Original Pattern:
 *   for (int i = 0; i < LEN_1D; i++) {
 *       a[i] += b[ip[i]] * s;
 *   }
 *
 * Hypothesis: Gather performance varies dramatically by hardware
 *   - vluxei32.v (indexed load/gather) is key instruction
 *   - Some hardware has optimized gather units
 *   - Others serialize indexed accesses
 *
 * TSVC Category: Indirect Addressing (Scale=7.86)
 */
#include "common.h"

static const real_t s = 1.5f;

void kernel(void) {
    for (int i = 0; i < LEN_1D; i++) {
        a[i] += b[indx[i]] * s;
    }
}
