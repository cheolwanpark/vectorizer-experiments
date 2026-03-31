#include <math.h>
#include "../common.h"
#include "../array_defs.h"
#include "../single_support.h"
#include "../tsvc_measure.h"


real_t s312(struct args_t * func_args)
{

//    reductions
//    product reduction

    initialise_arrays(__func__);
    gettimeofday(&func_args->t1, NULL);

    real_t prod;
    for (int nl = 0; nl < 10*iterations; nl++) {
        prod = (real_t)1.;
        for (int i = 0; i < LEN_1D; i++) {
            prod *= a[i];
        }
        dummy(a, b, c, d, e, aa, bb, cc, prod);
    }

    gettimeofday(&func_args->t2, NULL);
    return prod;
}

const char *tsvc_loop_name(void) { return "s312"; }

real_t tsvc_entry(struct args_t *func_args) { return s312(func_args); }

void *tsvc_prepare_args(void) {
    return NULL;
}
