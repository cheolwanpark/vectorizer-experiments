#ifndef BUFFER_ELEMS
#define BUFFER_ELEMS 256
#endif

#ifndef BUFFER_BYTES
#define BUFFER_BYTES (BUFFER_ELEMS * 4)
#endif

#ifndef SWITCH_FROM_LMUL
#define SWITCH_FROM_LMUL m1
#endif

#ifndef SWITCH_TO_LMUL
#define SWITCH_TO_LMUL m4
#endif

#ifndef SWITCH_FIRST_AVL
#define SWITCH_FIRST_AVL 64
#endif

#ifndef SWITCH_SECOND_AVL
#define SWITCH_SECOND_AVL 64
#endif

#ifndef SWITCH_OUTER_ITERS
#define SWITCH_OUTER_ITERS 256
#endif

#ifndef MEM_LMUL
#define MEM_LMUL m1
#endif

#ifndef MEM_TOTAL_ELEMS
#define MEM_TOTAL_ELEMS 256
#endif

#ifndef MEM_OUTER_ITERS
#define MEM_OUTER_ITERS 64
#endif

#ifndef PRESSURE_LMUL
#define PRESSURE_LMUL m1
#endif

#ifndef PRESSURE_TOTAL_ELEMS
#define PRESSURE_TOTAL_ELEMS 64
#endif

#ifndef PRESSURE_OUTER_ITERS
#define PRESSURE_OUTER_ITERS 48
#endif

#ifndef TEMP_REG_COUNT
#define TEMP_REG_COUNT 4
#endif

#ifndef PHASE1_LMUL
#define PHASE1_LMUL m8
#endif

#ifndef PHASE2_LMUL
#define PHASE2_LMUL m1
#endif

#ifndef PHASE1_TOTAL_ELEMS
#define PHASE1_TOTAL_ELEMS 256
#endif

#ifndef PHASE2_TOTAL_ELEMS
#define PHASE2_TOTAL_ELEMS 64
#endif

#ifndef PHASE_OUTER_ITERS
#define PHASE_OUTER_ITERS 48
#endif
