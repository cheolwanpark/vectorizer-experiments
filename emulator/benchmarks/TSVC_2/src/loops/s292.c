#include <math.h>
#include "../common.h"
#include "../array_defs.h"
#include "../single_support.h"
#include "../tsvc_measure.h"


real_t s292(struct args_t * func_args)
{

//    loop peeling
//    wrap around variable, 2 levels
//    similar to S291

    initialise_arrays(__func__);
    gettimeofday(&func_args->t1, NULL);

    int im1, im2;
    for (int nl = 0; nl < iterations; nl++) {
        im1 = LEN_1D-1;
        im2 = LEN_1D-2;
        for (int i = 0; i < LEN_1D; i++) {
            a[i] = (b[i] + b[im1] + b[im2]) * (real_t).333;
            im2 = im1;
            im1 = i;
        }
        dummy(a, b, c, d, e, aa, bb, cc, 0.);
    }

    gettimeofday(&func_args->t2, NULL);
    return calc_checksum(__func__);
}

const char *tsvc_loop_name(void) { return "s292"; }

real_t tsvc_entry(struct args_t *func_args) { return s292(func_args); }

void *tsvc_prepare_args(void) {
    return NULL;
}
