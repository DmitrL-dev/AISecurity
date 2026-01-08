/*
 * SENTINEL IMMUNE — RCU-style Double Buffer Implementation
 * 
 * Lock-free read path using atomic pointer swap and epoch tracking.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <pthread.h>
#include <unistd.h>

#include "rcu_buffer.h"

/* ==================== Internal Structures ==================== */

/* Single buffer slot */
typedef struct {
    void       *data;       /* Element array */
    size_t      count;      /* Number of elements */
} buffer_slot_t;

struct rcu_buffer {
    /* Double buffer */
    buffer_slot_t   buffers[2];
    _Atomic int     active;     /* 0 or 1 */
    
    /* Configuration */
    size_t          elem_size;
    size_t          capacity;
    
    /* Epoch for grace period */
    _Atomic uint64_t epoch;
    
    /* Reader tracking */
    _Atomic int     reader_count;
    _Atomic uint64_t reader_epochs[RCU_MAX_READERS];
    
    /* Writer lock */
    pthread_mutex_t writer_lock;
};

/* ==================== Lifecycle ==================== */

rcu_buffer_t*
rcu_create(size_t elem_size, size_t capacity)
{
    if (elem_size == 0 || capacity == 0) {
        return NULL;
    }
    
    rcu_buffer_t *buf = calloc(1, sizeof(rcu_buffer_t));
    if (!buf) return NULL;
    
    buf->elem_size = elem_size;
    buf->capacity = capacity;
    
    /* Allocate both buffers */
    buf->buffers[0].data = calloc(capacity, elem_size);
    buf->buffers[1].data = calloc(capacity, elem_size);
    
    if (!buf->buffers[0].data || !buf->buffers[1].data) {
        free(buf->buffers[0].data);
        free(buf->buffers[1].data);
        free(buf);
        return NULL;
    }
    
    atomic_store(&buf->active, 0);
    atomic_store(&buf->epoch, 1);
    atomic_store(&buf->reader_count, 0);
    
    for (int i = 0; i < RCU_MAX_READERS; i++) {
        atomic_store(&buf->reader_epochs[i], 0);
    }
    
    pthread_mutex_init(&buf->writer_lock, NULL);
    
    return buf;
}

void
rcu_destroy(rcu_buffer_t *buf)
{
    if (!buf) return;
    
    /* Wait for readers */
    rcu_synchronize(buf);
    
    free(buf->buffers[0].data);
    free(buf->buffers[1].data);
    pthread_mutex_destroy(&buf->writer_lock);
    
    memset(buf, 0, sizeof(*buf));
    free(buf);
}

/* ==================== Reader Operations ==================== */

/* Thread-local reader slot */
static __thread int tls_reader_slot = -1;

void
rcu_read_lock(rcu_buffer_t *buf)
{
    if (!buf) return;
    
    /* Get or allocate reader slot */
    if (tls_reader_slot < 0) {
        tls_reader_slot = atomic_fetch_add(&buf->reader_count, 1);
        if (tls_reader_slot >= RCU_MAX_READERS) {
            /* Fallback - reuse slot 0 */
            tls_reader_slot = 0;
        }
    }
    
    /* Record current epoch */
    uint64_t current_epoch = atomic_load(&buf->epoch);
    atomic_store(&buf->reader_epochs[tls_reader_slot], current_epoch);
    
    /* Memory barrier */
    atomic_thread_fence(memory_order_acquire);
}

void*
rcu_dereference(rcu_buffer_t *buf)
{
    if (!buf) return NULL;
    
    int active = atomic_load(&buf->active);
    return buf->buffers[active].data;
}

size_t
rcu_count(rcu_buffer_t *buf)
{
    if (!buf) return 0;
    
    int active = atomic_load(&buf->active);
    return buf->buffers[active].count;
}

void
rcu_read_unlock(rcu_buffer_t *buf)
{
    if (!buf) return;
    
    /* Memory barrier */
    atomic_thread_fence(memory_order_release);
    
    /* Clear epoch (reader done) */
    if (tls_reader_slot >= 0 && tls_reader_slot < RCU_MAX_READERS) {
        atomic_store(&buf->reader_epochs[tls_reader_slot], 0);
    }
}

void
rcu_for_each(rcu_buffer_t *buf, rcu_reader_fn fn, void *user)
{
    if (!buf || !fn) return;
    
    rcu_read_lock(buf);
    
    void *data = rcu_dereference(buf);
    size_t count = rcu_count(buf);
    
    for (size_t i = 0; i < count; i++) {
        void *elem = (char *)data + (i * buf->elem_size);
        fn(elem, user);
    }
    
    rcu_read_unlock(buf);
}

/* ==================== Writer Operations ==================== */

void*
rcu_get_standby(rcu_buffer_t *buf)
{
    if (!buf) return NULL;
    
    int standby = 1 - atomic_load(&buf->active);
    return buf->buffers[standby].data;
}

void
rcu_set_standby_count(rcu_buffer_t *buf, size_t count)
{
    if (!buf) return;
    
    int standby = 1 - atomic_load(&buf->active);
    buf->buffers[standby].count = count;
}

void
rcu_copy_to_standby(rcu_buffer_t *buf)
{
    if (!buf) return;
    
    pthread_mutex_lock(&buf->writer_lock);
    
    int active = atomic_load(&buf->active);
    int standby = 1 - active;
    
    /* Copy data */
    memcpy(buf->buffers[standby].data, 
           buf->buffers[active].data,
           buf->buffers[active].count * buf->elem_size);
    buf->buffers[standby].count = buf->buffers[active].count;
    
    pthread_mutex_unlock(&buf->writer_lock);
}

void
rcu_swap(rcu_buffer_t *buf)
{
    if (!buf) return;
    
    pthread_mutex_lock(&buf->writer_lock);
    
    /* Increment epoch */
    atomic_fetch_add(&buf->epoch, 1);
    
    /* Memory barrier before swap */
    atomic_thread_fence(memory_order_seq_cst);
    
    /* Atomic swap */
    int old_active = atomic_load(&buf->active);
    atomic_store(&buf->active, 1 - old_active);
    
    /* Memory barrier after swap */
    atomic_thread_fence(memory_order_seq_cst);
    
    pthread_mutex_unlock(&buf->writer_lock);
}

void
rcu_synchronize(rcu_buffer_t *buf)
{
    if (!buf) return;
    
    /* Get epoch before swap */
    uint64_t old_epoch = atomic_load(&buf->epoch) - 1;
    
    /* Wait for all readers from old epoch to finish */
    int max_readers = atomic_load(&buf->reader_count);
    if (max_readers > RCU_MAX_READERS) {
        max_readers = RCU_MAX_READERS;
    }
    
    int max_spins = 10000;
    
    while (max_spins-- > 0) {
        bool all_clear = true;
        
        for (int i = 0; i < max_readers; i++) {
            uint64_t reader_epoch = atomic_load(&buf->reader_epochs[i]);
            if (reader_epoch != 0 && reader_epoch <= old_epoch) {
                all_clear = false;
                break;
            }
        }
        
        if (all_clear) {
            return;
        }
        
        /* Brief sleep */
        usleep(100);
    }
    
    /* Timeout - log warning but continue */
    fprintf(stderr, "[RCU] Warning: synchronize timeout\n");
}

uint64_t
rcu_epoch(rcu_buffer_t *buf)
{
    if (!buf) return 0;
    return atomic_load(&buf->epoch);
}

/* ==================== Statistics ==================== */

int
rcu_reader_count(rcu_buffer_t *buf)
{
    if (!buf) return 0;
    
    int count = 0;
    int max_readers = atomic_load(&buf->reader_count);
    if (max_readers > RCU_MAX_READERS) {
        max_readers = RCU_MAX_READERS;
    }
    
    for (int i = 0; i < max_readers; i++) {
        if (atomic_load(&buf->reader_epochs[i]) != 0) {
            count++;
        }
    }
    
    return count;
}
