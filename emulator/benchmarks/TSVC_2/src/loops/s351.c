#include <math.h>
#include "../common.h"
#include "../array_defs.h"
#include "../single_support.h"
#include "../tsvc_measure.h"


real_t s351(struct args_t * func_args)
{

//    loop rerolling
//    unrolled saxpy

    initialise_arrays(__func__);
    gettimeofday(&func_args->t1, NULL);

    real_t alpha = c[0];
    for (int nl = 0; nl < 8*iterations; nl++) {
        for (int i = 0; i < LEN_1D; i += 5) {
            a[i] += alpha * b[i];
            a[i + 1] += alpha * b[i + 1];
            a[i + 2] += alpha * b[i + 2];
            a[i + 3] += alpha * b[i + 3];
            a[i + 4] += alpha * b[i + 4];
        }
        dummy(a, b, c, d, e, aa, bb, cc, 0.);
    }

    gettimeofday(&func_args->t2, NULL);
    return calc_checksum(__func__);
}

const char *tsvc_loop_name(void) { return "s351"; }

real_t tsvc_entry(struct args_t *func_args) { return s351(func_args); }

void *tsvc_prepare_args(void) {
    return NULL;
}
