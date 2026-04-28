#ifndef PARSEC_BAREMETAL_PTHREAD_H
#define PARSEC_BAREMETAL_PTHREAD_H

#ifdef __cplusplus
extern "C" {
#endif

typedef unsigned long pthread_t;

typedef struct {
    int unused;
} pthread_attr_t;

typedef struct {
    int unused;
} pthread_mutex_t;

typedef struct {
    int unused;
} pthread_cond_t;

typedef struct {
    int unused;
} pthread_barrier_t;

#define PTHREAD_MUTEX_INITIALIZER {0}
#define PTHREAD_COND_INITIALIZER {0}

static inline int pthread_attr_init(pthread_attr_t *attr) {
    (void)attr;
    return 0;
}

static inline int pthread_mutex_init(pthread_mutex_t *mutex, const void *attr) {
    (void)mutex;
    (void)attr;
    return 0;
}

static inline int pthread_mutex_destroy(pthread_mutex_t *mutex) {
    (void)mutex;
    return 0;
}

static inline int pthread_mutex_lock(pthread_mutex_t *mutex) {
    (void)mutex;
    return 0;
}

static inline int pthread_mutex_unlock(pthread_mutex_t *mutex) {
    (void)mutex;
    return 0;
}

static inline int pthread_mutex_trylock(pthread_mutex_t *mutex) {
    (void)mutex;
    return 0;
}

static inline int pthread_cond_init(pthread_cond_t *cond, const void *attr) {
    (void)cond;
    (void)attr;
    return 0;
}

static inline int pthread_cond_destroy(pthread_cond_t *cond) {
    (void)cond;
    return 0;
}

static inline int pthread_cond_wait(pthread_cond_t *cond, pthread_mutex_t *mutex) {
    (void)cond;
    (void)mutex;
    return 0;
}

static inline int pthread_cond_broadcast(pthread_cond_t *cond) {
    (void)cond;
    return 0;
}

static inline int pthread_create(
    pthread_t *thread,
    const pthread_attr_t *attr,
    void *(*start_routine)(void *),
    void *arg
) {
    (void)attr;
    if (thread != 0) {
        *thread = 0;
    }
    if (start_routine != 0) {
        (void)start_routine(arg);
    }
    return 0;
}

static inline int pthread_join(pthread_t thread, void **retval) {
    (void)thread;
    (void)retval;
    return 0;
}

#ifdef __cplusplus
}
#endif

#endif
