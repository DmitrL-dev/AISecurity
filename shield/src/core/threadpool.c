/*
 * SENTINEL Shield - Thread Pool Implementation
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "shield_common.h"
#include "shield_threadpool.h"

/* Platform-specific init */
#ifdef _WIN32

static void mutex_init(mutex_t *m) { InitializeCriticalSection(m); }
static void mutex_destroy(mutex_t *m) { DeleteCriticalSection(m); }
static void mutex_lock(mutex_t *m) { EnterCriticalSection(m); }
static void mutex_unlock(mutex_t *m) { LeaveCriticalSection(m); }

static void cond_init(cond_t *c) { InitializeConditionVariable(c); }
static void cond_destroy(cond_t *c) { (void)c; }
static void cond_wait(cond_t *c, mutex_t *m) { SleepConditionVariableCS(c, m, INFINITE); }
static void cond_signal(cond_t *c) { WakeConditionVariable(c); }
static void cond_broadcast(cond_t *c) { WakeAllConditionVariable(c); }

#else

static void mutex_init(mutex_t *m) { pthread_mutex_init(m, NULL); }
static void mutex_destroy(mutex_t *m) { pthread_mutex_destroy(m); }
static void mutex_lock(mutex_t *m) { pthread_mutex_lock(m); }
static void mutex_unlock(mutex_t *m) { pthread_mutex_unlock(m); }

static void cond_init(cond_t *c) { pthread_cond_init(c, NULL); }
static void cond_destroy(cond_t *c) { pthread_cond_destroy(c); }
static void cond_wait(cond_t *c, mutex_t *m) { pthread_cond_wait(c, m); }
static void cond_signal(cond_t *c) { pthread_cond_signal(c); }
static void cond_broadcast(cond_t *c) { pthread_cond_broadcast(c); }

#endif

/* Worker thread */
#ifdef _WIN32
static DWORD WINAPI worker_thread(void *arg)
#else
static void *worker_thread(void *arg)
#endif
{
    threadpool_t *pool = (threadpool_t *)arg;
    
    while (1) {
        mutex_lock(&pool->lock);
        
        /* Wait for task */
        while (pool->queue_head == NULL && !pool->shutdown) {
            cond_wait(&pool->cond, &pool->lock);
        }
        
        if (pool->shutdown && pool->queue_head == NULL) {
            mutex_unlock(&pool->lock);
            break;
        }
        
        /* Get task */
        task_t *task = pool->queue_head;
        if (task) {
            pool->queue_head = task->next;
            if (pool->queue_head == NULL) {
                pool->queue_tail = NULL;
            }
            pool->queue_size--;
        }
        
        mutex_unlock(&pool->lock);
        
        /* Execute */
        if (task) {
            task->fn(task->arg);
            free(task);
            
            mutex_lock(&pool->lock);
            pool->tasks_completed++;
            mutex_unlock(&pool->lock);
        }
    }
    
#ifdef _WIN32
    return 0;
#else
    return NULL;
#endif
}

/* Initialize */
shield_err_t threadpool_init(threadpool_t *pool, int num_threads)
{
    if (!pool || num_threads <= 0) {
        return SHIELD_ERR_INVALID;
    }
    
    memset(pool, 0, sizeof(*pool));
    
    pool->threads = calloc(num_threads, sizeof(thread_t));
    if (!pool->threads) {
        return SHIELD_ERR_NOMEM;
    }
    
    pool->thread_count = num_threads;
    mutex_init(&pool->lock);
    cond_init(&pool->cond);
    
    /* Start threads */
    for (int i = 0; i < num_threads; i++) {
#ifdef _WIN32
        pool->threads[i] = CreateThread(NULL, 0, worker_thread, pool, 0, NULL);
        if (!pool->threads[i]) {
            threadpool_destroy(pool);
            return SHIELD_ERR_IO;
        }
#else
        if (pthread_create(&pool->threads[i], NULL, worker_thread, pool) != 0) {
            threadpool_destroy(pool);
            return SHIELD_ERR_IO;
        }
#endif
    }
    
    return SHIELD_OK;
}

/* Destroy */
void threadpool_destroy(threadpool_t *pool)
{
    if (!pool) {
        return;
    }
    
    /* Signal shutdown */
    mutex_lock(&pool->lock);
    pool->shutdown = true;
    cond_broadcast(&pool->cond);
    mutex_unlock(&pool->lock);
    
    /* Wait for threads */
    for (int i = 0; i < pool->thread_count; i++) {
        if (pool->threads[i]) {
#ifdef _WIN32
            WaitForSingleObject(pool->threads[i], INFINITE);
            CloseHandle(pool->threads[i]);
#else
            pthread_join(pool->threads[i], NULL);
#endif
        }
    }
    
    /* Free remaining tasks */
    task_t *task = pool->queue_head;
    while (task) {
        task_t *next = task->next;
        free(task);
        task = next;
    }
    
    mutex_destroy(&pool->lock);
    cond_destroy(&pool->cond);
    free(pool->threads);
}

/* Submit task */
shield_err_t threadpool_submit(threadpool_t *pool, task_fn_t fn, void *arg)
{
    if (!pool || !fn) {
        return SHIELD_ERR_INVALID;
    }
    
    task_t *task = calloc(1, sizeof(task_t));
    if (!task) {
        return SHIELD_ERR_NOMEM;
    }
    
    task->fn = fn;
    task->arg = arg;
    
    mutex_lock(&pool->lock);
    
    if (pool->shutdown) {
        mutex_unlock(&pool->lock);
        free(task);
        return SHIELD_ERR_INVALID;
    }
    
    /* Add to queue */
    if (pool->queue_tail) {
        pool->queue_tail->next = task;
    } else {
        pool->queue_head = task;
    }
    pool->queue_tail = task;
    pool->queue_size++;
    
    cond_signal(&pool->cond);
    mutex_unlock(&pool->lock);
    
    return SHIELD_OK;
}

/* Wait for all tasks */
void threadpool_wait(threadpool_t *pool)
{
    if (!pool) {
        return;
    }
    
    /* Simple busy-wait (could be improved with condition variable) */
    while (1) {
        mutex_lock(&pool->lock);
        int size = pool->queue_size;
        mutex_unlock(&pool->lock);
        
        if (size == 0) {
            break;
        }
        
#ifdef _WIN32
        Sleep(10);
#else
        usleep(10000);
#endif
    }
}

/* Queue size */
int threadpool_queue_size(threadpool_t *pool)
{
    if (!pool) {
        return 0;
    }
    
    mutex_lock(&pool->lock);
    int size = pool->queue_size;
    mutex_unlock(&pool->lock);
    
    return size;
}
