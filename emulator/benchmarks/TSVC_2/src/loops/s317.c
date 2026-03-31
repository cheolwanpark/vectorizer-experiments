#include <math.h>
#include "../common.h"
#include "../array_defs.h"
#include "../single_support.h"
#include "../tsvc_measure.h"


real_t s317(struct args_t * func_args)
{

//    reductions
//    product reductio vectorize with
//    1. scalar expansion of factor, and product reduction
//    2. closed form solution: q = factor**n

    initialise_arrays(__func__);
    gettimeofday(&func_args->t1, NULL);

    real_t q;
    for (int nl = 0; nl < 5*iterations; nl++) {
        q = (real_t)1.;
        for (int i = 0; i < LEN_1D/2; i++) {
            q *= (real_t).99;
        }
        dummy(a, b, c, d, e, aa, bb, cc, q);
    }

    gettimeofday(&func_args->t2, NULL);
    return q;
}

const char *tsvc_loop_name(void) { return "s317"; }

real_t tsvc_entry(struct args_t *func_args) { return s317(func_args); }

void *tsvc_prepare_args(void) {
    return NULL;
}
