#include <math.h>
#include "../common.h"
#include "../array_defs.h"
#include "../single_support.h"
#include "../tsvc_measure.h"


real_t s124(struct args_t * func_args)
{

//    induction variable recognition
//    induction variable under both sides of if (same value)

    initialise_arrays(__func__);
    gettimeofday(&func_args->t1, NULL);

    int j;
    for (int nl = 0; nl < iterations; nl++) {
        j = -1;
        for (int i = 0; i < LEN_1D; i++) {
            if (b[i] > (real_t)0.) {
                j++;
                a[j] = b[i] + d[i] * e[i];
            } else {
                j++;
                a[j] = c[i] + d[i] * e[i];
            }
        }
        dummy(a, b, c, d, e, aa, bb, cc, 0.);
    }

    gettimeofday(&func_args->t2, NULL);
    return calc_checksum(__func__);
}

const char *tsvc_loop_name(void) { return "s124"; }

real_t tsvc_entry(struct args_t *func_args) { return s124(func_args); }

void *tsvc_prepare_args(void) {
    return NULL;
}
