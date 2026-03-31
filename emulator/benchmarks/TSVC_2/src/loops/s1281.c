#include <math.h>
#include "../common.h"
#include "../array_defs.h"
#include "../single_support.h"
#include "../tsvc_measure.h"


real_t s1281(struct args_t * func_args)
{

//    crossing thresholds
//    index set splitting
//    reverse data access

    initialise_arrays(__func__);
    gettimeofday(&func_args->t1, NULL);

    real_t x;
    for (int nl = 0; nl < 4*iterations; nl++) {
        for (int i = 0; i < LEN_1D; i++) {
            x = b[i]*c[i] + a[i]*d[i] + e[i];
            a[i] = x-(real_t)1.0;
            b[i] = x;
        }
        dummy(a, b, c, d, e, aa, bb, cc, 0.);
    }

    gettimeofday(&func_args->t2, NULL);
    return calc_checksum(__func__);
}

const char *tsvc_loop_name(void) { return "s1281"; }

real_t tsvc_entry(struct args_t *func_args) { return s1281(func_args); }

void *tsvc_prepare_args(void) {
    return NULL;
}
