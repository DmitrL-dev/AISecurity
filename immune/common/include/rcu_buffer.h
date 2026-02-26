/*
 * SENTINEL IMMUNE — RCU-style Double Buffer
 * 
 * Lock-free read path for pattern arrays with safe hot reload.
 * Inspired by Linux RCU but simplified for userspace/kmod.
 * 
 * Features:
 * - Double-buffer with atomic swap
 * - Grace period tracking
 * - Lock-free reader path
 */

#ifndef IMMUNE_RCU_BUFFER_H
#define IMMUNE_RCU_BUFFER_H

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdatomic.h>

/* Maximum concurrent readers */
#define RCU_MAX_READERS     256

/* RCU buffer handle */
typedef struct rcu_buffer rcu_buffer_t;

/* Reader callback for iteration */
typedef void (*rcu_reader_fn)(void *data, void *user);

/* === Lifecycle === */

/**
 * Create RCU double buffer.
 * @param elem_size Size of each element
 * @param capacity Number of elements per buffer
 * @return RCU buffer or NULL on error
 */
rcu_buffer_t* rcu_create(size_t elem_size, size_t capacity);

/**
 * Destroy RCU buffer.
 * @param buf Buffer to destroy
 */
void rcu_destroy(rcu_buffer_t *buf);

/* === Reader Operations (Lock-free) === */

/**
 * Enter read-side critical section.
 * Must be paired with rcu_read_unlock().
 * @param buf RCU buffer
 */
void rcu_read_lock(rcu_buffer_t *buf);

/**
 * Get pointer to active buffer data.
 * Only valid between rcu_read_lock/unlock.
 * @param buf RCU buffer
 * @return Pointer to data array
 */
void* rcu_dereference(rcu_buffer_t *buf);

/**
 * Get current element count.
 * Only valid between rcu_read_lock/unlock.
 * @param buf RCU buffer
 * @return Number of elements
 */
size_t rcu_count(rcu_buffer_t *buf);

/**
 * Exit read-side critical section.
 * @param buf RCU buffer
 */
void rcu_read_unlock(rcu_buffer_t *buf);

/**
 * Safe iteration (callback per element).
 * @param buf RCU buffer
 * @param fn Callback function
 * @param user User data for callback
 */
void rcu_for_each(rcu_buffer_t *buf, rcu_reader_fn fn, void *user);

/* === Writer Operations === */

/**
 * Get pointer to standby buffer for modification.
 * Writer should copy active data here before modifying.
 * @param buf RCU buffer
 * @return Pointer to standby data array
 */
void* rcu_get_standby(rcu_buffer_t *buf);

/**
 * Set element count for standby buffer.
 * @param buf RCU buffer
 * @param count New count
 */
void rcu_set_standby_count(rcu_buffer_t *buf, size_t count);

/**
 * Copy active buffer to standby.
 * @param buf RCU buffer
 */
void rcu_copy_to_standby(rcu_buffer_t *buf);

/**
 * Atomic swap active and standby buffers.
 * After this, new readers see updated data.
 * @param buf RCU buffer
 */
void rcu_swap(rcu_buffer_t *buf);

/**
 * Wait for grace period (all old readers finish).
 * Call after rcu_swap before freeing old data.
 * @param buf RCU buffer
 */
void rcu_synchronize(rcu_buffer_t *buf);

/**
 * Get current epoch number.
 * @param buf RCU buffer
 * @return Epoch
 */
uint64_t rcu_epoch(rcu_buffer_t *buf);

/* === Statistics === */

/**
 * Get number of active readers.
 * @param buf RCU buffer
 * @return Reader count
 */
int rcu_reader_count(rcu_buffer_t *buf);

#endif /* IMMUNE_RCU_BUFFER_H */
