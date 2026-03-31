#include <math.h>
#include "../common.h"
#include "../array_defs.h"
#include "../single_support.h"
#include "../tsvc_measure.h"


real_t s254(struct args_t * func_args)
{

//    scalar and array expansion
//    carry around variable

    initialise_arrays(__func__);
    gettimeofday(&func_args->t1, NULL);

    real_t x;
    for (int nl = 0; nl < 4*iterations; nl++) {
        x = b[LEN_1D-1];
        for (int i = 0; i < LEN_1D; i++) {
            a[i] = (b[i] + x) * (real_t).5;
            x = b[i];
        }
        dummy(a, b, c, d, e, aa, bb, cc, 0.);
    }

    gettimeofday(&func_args->t2, NULL);
    return calc_checksum(__func__);
}

const char *tsvc_loop_name(void) { return "s254"; }

real_t tsvc_entry(struct args_t *func_args) { return s254(func_args); }

void *tsvc_prepare_args(void) {
    return NULL;
}
