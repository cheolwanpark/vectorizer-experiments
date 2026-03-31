#include <math.h>
#include "../common.h"
#include "../array_defs.h"
#include "../single_support.h"
#include "../tsvc_measure.h"


real_t s132(struct args_t * func_args)
{
//    global data flow analysis
//    loop with multiple dimension ambiguous subscripts

    initialise_arrays(__func__);
    gettimeofday(&func_args->t1, NULL);

    int m = 0;
    int j = m;
    int k = m+1;
    for (int nl = 0; nl < 400*iterations; nl++) {
        for (int i= 1; i < LEN_2D; i++) {
            aa[j][i] = aa[k][i-1] + b[i] * c[1];
        }
        dummy(a, b, c, d, e, aa, bb, cc, 0.);
    }

    gettimeofday(&func_args->t2, NULL);
    return calc_checksum(__func__);
}

const char *tsvc_loop_name(void) { return "s132"; }

real_t tsvc_entry(struct args_t *func_args) { return s132(func_args); }

void *tsvc_prepare_args(void) {
    return NULL;
}
