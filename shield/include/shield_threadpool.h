/*
 * SENTINEL Shield - Thread Pool
 * 
 * Worker thread pool for async processing
 */

#ifndef SHIELD_THREADPOOL_H
#define SHIELD_THREADPOOL_H

#include "shield_common.h"

#ifdef _WIN32
    #include <windows.h>
    typedef HANDLE thread_t;
    typedef CRITICAL_SECTION mutex_t;
    typedef CONDITION_VARIABLE cond_t;
#else
    #include <pthread.h>
    typedef pthread_t thread_t;
    typedef pthread_mutex_t mutex_t;
    typedef pthread_cond_t cond_t;
#endif

/* Task function */
typedef void (*task_fn_t)(void *arg);

/* Task */
typedef struct task {
    task_fn_t       fn;
    void            *arg;
    struct task     *next;
} task_t;

/* Thread pool */
typedef struct threadpool {
    thread_t        *threads;
    int             thread_count;
    
    task_t          *queue_head;
    task_t          *queue_tail;
    int             queue_size;
    
    mutex_t         lock;
    cond_t          cond;
    
    bool            shutdown;
    
    uint64_t        tasks_completed;
} threadpool_t;

/* API */
shield_err_t threadpool_init(threadpool_t *pool, int num_threads);
void threadpool_destroy(threadpool_t *pool);

shield_err_t threadpool_submit(threadpool_t *pool, task_fn_t fn, void *arg);
void threadpool_wait(threadpool_t *pool);

int threadpool_queue_size(threadpool_t *pool);

#endif /* SHIELD_THREADPOOL_H */
