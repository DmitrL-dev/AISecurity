/*
 * SENTINEL Shield - Ring Buffer Implementation
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "shield_common.h"
#include "shield_ringbuf.h"

/* Round up to power of 2 */
static size_t next_power_of_2(size_t n)
{
    n--;
    n |= n >> 1;
    n |= n >> 2;
    n |= n >> 4;
    n |= n >> 8;
    n |= n >> 16;
#if SIZE_MAX > 0xFFFFFFFF
    n |= n >> 32;
#endif
    return n + 1;
}

/* Initialize */
shield_err_t ringbuf_init(ring_buffer_t *rb, size_t capacity)
{
    if (!rb || capacity == 0) {
        return SHIELD_ERR_INVALID;
    }
    
    /* Round to power of 2 for fast modulo */
    capacity = next_power_of_2(capacity);
    
    memset(rb, 0, sizeof(*rb));
    rb->data = malloc(capacity);
    if (!rb->data) {
        return SHIELD_ERR_NOMEM;
    }
    
    rb->capacity = capacity;
    rb->mask = capacity - 1;
    
    return SHIELD_OK;
}

/* Destroy */
void ringbuf_destroy(ring_buffer_t *rb)
{
    if (!rb) return;
    
    free(rb->data);
    rb->data = NULL;
    rb->capacity = 0;
}

/* Write data */
size_t ringbuf_write(ring_buffer_t *rb, const void *data, size_t len)
{
    if (!rb || !data || len == 0) {
        return 0;
    }
    
    size_t free_space = ringbuf_free_space(rb);
    if (len > free_space) {
        len = free_space;
    }
    
    if (len == 0) {
        return 0;
    }
    
    const uint8_t *src = (const uint8_t *)data;
    size_t head = rb->head;
    
    /* Copy in one or two parts */
    size_t first_part = rb->capacity - (head & rb->mask);
    if (first_part > len) {
        first_part = len;
    }
    
    memcpy(rb->data + (head & rb->mask), src, first_part);
    
    if (len > first_part) {
        memcpy(rb->data, src + first_part, len - first_part);
    }
    
    /* Memory barrier for multi-threaded use */
    __sync_synchronize();
    
    rb->head = head + len;
    
    return len;
}

/* Read data */
size_t ringbuf_read(ring_buffer_t *rb, void *data, size_t len)
{
    if (!rb || !data) {
        return 0;
    }
    
    size_t available = ringbuf_available(rb);
    if (len > available) {
        len = available;
    }
    
    if (len == 0) {
        return 0;
    }
    
    uint8_t *dst = (uint8_t *)data;
    size_t tail = rb->tail;
    
    /* Copy in one or two parts */
    size_t first_part = rb->capacity - (tail & rb->mask);
    if (first_part > len) {
        first_part = len;
    }
    
    memcpy(dst, rb->data + (tail & rb->mask), first_part);
    
    if (len > first_part) {
        memcpy(dst + first_part, rb->data, len - first_part);
    }
    
    /* Memory barrier */
    __sync_synchronize();
    
    rb->tail = tail + len;
    
    return len;
}

/* Peek without consuming */
size_t ringbuf_peek(ring_buffer_t *rb, void *data, size_t len)
{
    if (!rb || !data) {
        return 0;
    }
    
    size_t available = ringbuf_available(rb);
    if (len > available) {
        len = available;
    }
    
    if (len == 0) {
        return 0;
    }
    
    uint8_t *dst = (uint8_t *)data;
    size_t tail = rb->tail;
    
    size_t first_part = rb->capacity - (tail & rb->mask);
    if (first_part > len) {
        first_part = len;
    }
    
    memcpy(dst, rb->data + (tail & rb->mask), first_part);
    
    if (len > first_part) {
        memcpy(dst + first_part, rb->data, len - first_part);
    }
    
    return len;
}

/* Skip bytes */
void ringbuf_skip(ring_buffer_t *rb, size_t len)
{
    if (!rb) return;
    
    size_t available = ringbuf_available(rb);
    if (len > available) {
        len = available;
    }
    
    rb->tail += len;
}

/* Available data */
size_t ringbuf_available(ring_buffer_t *rb)
{
    if (!rb) return 0;
    return rb->head - rb->tail;
}

/* Free space */
size_t ringbuf_free_space(ring_buffer_t *rb)
{
    if (!rb) return 0;
    return rb->capacity - (rb->head - rb->tail);
}

/* Is empty */
bool ringbuf_is_empty(ring_buffer_t *rb)
{
    return ringbuf_available(rb) == 0;
}

/* Is full */
bool ringbuf_is_full(ring_buffer_t *rb)
{
    return ringbuf_free_space(rb) == 0;
}

/* Clear */
void ringbuf_clear(ring_buffer_t *rb)
{
    if (!rb) return;
    rb->head = 0;
    rb->tail = 0;
}
