#include "common.h"

/* Helper extracted from tsvc.c so per-loop builds can link successfully. */
real_t test(real_t* A) {
  real_t s = (real_t)0.0;
  for (int i = 0; i < 4; i++)
    s += A[i];
  return s;
}

real_t f(real_t a, real_t b) {
  return a * b;
}
