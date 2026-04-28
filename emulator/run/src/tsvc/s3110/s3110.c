/* TSVC_EMULATE_GENERATED: s3110 */
#include "common.h"

extern int *tsvc_ip;
extern int tsvc_n1;
extern int tsvc_n3;
extern real_t tsvc_s1;
extern real_t tsvc_s2;

void kernel(void) {
    //    reductions
    //    if to max with index reductio 2 dimensions
    //    similar to S315


        int xindex, yindex;
        real_t max, chksum;
    max = aa[(0)][0];
    xindex = 0;
    yindex = 0;
    for (int i = 0; i < LEN_2D; i++) {
        for (int j = 0; j < LEN_2D; j++) {
            if (aa[i][j] > max) {
                max = aa[i][j];
                xindex = i;
                yindex = j;
            }
        }
    }
    chksum = max + (real_t) xindex + (real_t) yindex;
}
