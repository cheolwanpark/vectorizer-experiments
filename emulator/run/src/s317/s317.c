/* TSVC_EMULATE_GENERATED: s317 */
#include "common.h"

extern int *tsvc_ip;
extern int tsvc_n1;
extern int tsvc_n3;
extern real_t tsvc_s1;
extern real_t tsvc_s2;

void kernel(void) {
    //    reductions
    //    product reductio vectorize with
    //    1. scalar expansion of factor, and product reduction
    //    2. closed form solution: q = factor**n


        real_t q;
    q = (real_t)1.;
    for (int i = 0; i < LEN_1D/2; i++) {
        q *= (real_t).99;
    }
}
