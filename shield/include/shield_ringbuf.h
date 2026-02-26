/*
 * SENTINEL Shield - Ring Buffer
 * 
 * Lock-free ring buffer for high-performance queuing
 */

#ifndef SHIELD_RINGBUF_H
#define SHIELD_RINGBUF_H

#include "shield_common.h"

/* Ring buffer */
typedef struct ring_buffer {
    uint8_t         *data;
    size_t          capacity;
    size_t          mask;
    volatile size_t head;
    volatile size_t tail;
} ring_buffer_t;

/* API */
shield_err_t ringbuf_init(ring_buffer_t *rb, size_t capacity);
void ringbuf_destroy(ring_buffer_t *rb);

/* Write */
size_t ringbuf_write(ring_buffer_t *rb, const void *data, size_t len);

/* Read */
size_t ringbuf_read(ring_buffer_t *rb, void *data, size_t len);

/* Peek without consuming */
size_t ringbuf_peek(ring_buffer_t *rb, void *data, size_t len);

/* Skip bytes */
void ringbuf_skip(ring_buffer_t *rb, size_t len);

/* Query */
size_t ringbuf_available(ring_buffer_t *rb);
size_t ringbuf_free_space(ring_buffer_t *rb);
bool ringbuf_is_empty(ring_buffer_t *rb);
bool ringbuf_is_full(ring_buffer_t *rb);

/* Reset */
void ringbuf_clear(ring_buffer_t *rb);

#endif /* SHIELD_RINGBUF_H */
