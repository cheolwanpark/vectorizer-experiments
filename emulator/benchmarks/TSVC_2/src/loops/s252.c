#include <math.h>
#include "../common.h"
#include "../array_defs.h"
#include "../single_support.h"
#include "../tsvc_measure.h"


real_t s252(struct args_t * func_args)
{

//    scalar and array expansion
//    loop with ambiguous scalar temporary

    initialise_arrays(__func__);
    gettimeofday(&func_args->t1, NULL);

    real_t t, s;
    for (int nl = 0; nl < iterations; nl++) {
        t = (real_t) 0.;
        for (int i = 0; i < LEN_1D; i++) {
            s = b[i] * c[i];
            a[i] = s + t;
            t = s;
        }
        dummy(a, b, c, d, e, aa, bb, cc, 0.);
    }

    gettimeofday(&func_args->t2, NULL);
    return calc_checksum(__func__);
}

const char *tsvc_loop_name(void) { return "s252"; }

real_t tsvc_entry(struct args_t *func_args) { return s252(func_args); }

void *tsvc_prepare_args(void) {
    return NULL;
}
