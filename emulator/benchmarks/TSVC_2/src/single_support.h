#ifndef TSVC_SINGLE_SUPPORT_H
#define TSVC_SINGLE_SUPPORT_H

#include "common.h"

extern int *tsvc_ip;
extern int tsvc_n1;
extern int tsvc_n3;
extern real_t tsvc_s1;
extern real_t tsvc_s2;

void *tsvc_prepare_args(void);
const char *tsvc_loop_name(void);
real_t tsvc_entry(struct args_t *func_args);

#endif
