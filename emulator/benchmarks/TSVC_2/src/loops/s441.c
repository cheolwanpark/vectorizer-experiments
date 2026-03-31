#include <math.h>
#include "../common.h"
#include "../array_defs.h"
#include "../single_support.h"
#include "../tsvc_measure.h"


real_t s441(struct args_t * func_args)
{

//    non-logical if's
//    arithmetic if

    initialise_arrays(__func__);
    gettimeofday(&func_args->t1, NULL);

    for (int nl = 0; nl < iterations; nl++) {
        for (int i = 0; i < LEN_1D; i++) {
            if (d[i] < (real_t)0.) {
                a[i] += b[i] * c[i];
            } else if (d[i] == (real_t)0.) {
                a[i] += b[i] * b[i];
            } else {
                a[i] += c[i] * c[i];
            }
        }
        dummy(a, b, c, d, e, aa, bb, cc, 0.);
    }

    gettimeofday(&func_args->t2, NULL);
    return calc_checksum(__func__);
}

const char *tsvc_loop_name(void) { return "s441"; }

real_t tsvc_entry(struct args_t *func_args) { return s441(func_args); }

void *tsvc_prepare_args(void) {
    return NULL;
}
