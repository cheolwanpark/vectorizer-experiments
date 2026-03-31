#include <math.h>
#include "../common.h"
#include "../array_defs.h"
#include "../single_support.h"
#include "../tsvc_measure.h"


real_t s352(struct args_t * func_args)
{

//    loop rerolling
//    unrolled dot product

    initialise_arrays(__func__);
    gettimeofday(&func_args->t1, NULL);

    real_t dot;
    for (int nl = 0; nl < 8*iterations; nl++) {
        dot = (real_t)0.;
        for (int i = 0; i < LEN_1D; i += 5) {
            dot = dot + a[i] * b[i] + a[i + 1] * b[i + 1] + a[i + 2]
                * b[i + 2] + a[i + 3] * b[i + 3] + a[i + 4] * b[i + 4];
        }
        dummy(a, b, c, d, e, aa, bb, cc, dot);
    }

    gettimeofday(&func_args->t2, NULL);
    return dot;
}

const char *tsvc_loop_name(void) { return "s352"; }

real_t tsvc_entry(struct args_t *func_args) { return s352(func_args); }

void *tsvc_prepare_args(void) {
    return NULL;
}
