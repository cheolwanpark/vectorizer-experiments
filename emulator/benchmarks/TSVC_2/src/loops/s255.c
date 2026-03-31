#include <math.h>
#include "../common.h"
#include "../array_defs.h"
#include "../single_support.h"
#include "../tsvc_measure.h"


real_t s255(struct args_t * func_args)
{

//    scalar and array expansion
//    carry around variables, 2 levels

    initialise_arrays(__func__);
    gettimeofday(&func_args->t1, NULL);

    real_t x, y;
    for (int nl = 0; nl < iterations; nl++) {
        x = b[LEN_1D-1];
        y = b[LEN_1D-2];
        for (int i = 0; i < LEN_1D; i++) {
            a[i] = (b[i] + x + y) * (real_t).333;
            y = x;
            x = b[i];
        }
        dummy(a, b, c, d, e, aa, bb, cc, 0.);
    }

    gettimeofday(&func_args->t2, NULL);
    return calc_checksum(__func__);
}

const char *tsvc_loop_name(void) { return "s255"; }

real_t tsvc_entry(struct args_t *func_args) { return s255(func_args); }

void *tsvc_prepare_args(void) {
    return NULL;
}
