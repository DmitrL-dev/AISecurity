/*
 * SENTINEL Shield - Memory Pool Implementation
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "shield_common.h"
#include "shield_mempool.h"

/* Initialize pool */
shield_err_t mempool_init(mem_pool_t *pool, size_t block_size, int block_count)
{
    if (!pool || block_size == 0 || block_count <= 0) {
        return SHIELD_ERR_INVALID;
    }
    
    /* Ensure minimum block size */
    if (block_size < sizeof(mem_block_t)) {
        block_size = sizeof(mem_block_t);
    }
    
    /* Align to pointer size */
    block_size = (block_size + sizeof(void *) - 1) & ~(sizeof(void *) - 1);
    
    memset(pool, 0, sizeof(*pool));
    pool->block_size = block_size;
    pool->block_count = block_count;
    pool->total_size = block_size * block_count;
    
    /* Allocate memory */
    pool->memory = malloc(pool->total_size);
    if (!pool->memory) {
        return SHIELD_ERR_NOMEM;
    }
    
    memset(pool->memory, 0, pool->total_size);
    
    /* Build free list */
    pool->free_list = NULL;
    for (int i = block_count - 1; i >= 0; i--) {
        mem_block_t *block = (mem_block_t *)((char *)pool->memory + i * block_size);
        block->next = pool->free_list;
        pool->free_list = block;
    }
    
    pool->free_count = block_count;
    
    return SHIELD_OK;
}

/* Destroy pool */
void mempool_destroy(mem_pool_t *pool)
{
    if (!pool) return;
    
    free(pool->memory);
    pool->memory = NULL;
    pool->free_list = NULL;
    pool->free_count = 0;
}

/* Allocate block */
void *mempool_alloc(mem_pool_t *pool)
{
    if (!pool || !pool->free_list) {
        return NULL;
    }
    
    mem_block_t *block = pool->free_list;
    pool->free_list = block->next;
    pool->free_count--;
    pool->allocs++;
    
    memset(block, 0, pool->block_size);
    
    return block;
}

/* Free block */
void mempool_free(mem_pool_t *pool, void *ptr)
{
    if (!pool || !ptr) return;
    
    /* Validate pointer is in pool */
    if (ptr < pool->memory || 
        ptr >= (void *)((char *)pool->memory + pool->total_size)) {
        LOG_WARN("mempool_free: invalid pointer");
        return;
    }
    
    mem_block_t *block = (mem_block_t *)ptr;
    block->next = pool->free_list;
    pool->free_list = block;
    pool->free_count++;
    pool->frees++;
}

/* Get available count */
int mempool_available(mem_pool_t *pool)
{
    return pool ? pool->free_count : 0;
}

/* Reset pool */
void mempool_reset(mem_pool_t *pool)
{
    if (!pool || !pool->memory) return;
    
    /* Rebuild free list */
    pool->free_list = NULL;
    for (int i = pool->block_count - 1; i >= 0; i--) {
        mem_block_t *block = (mem_block_t *)((char *)pool->memory + i * pool->block_size);
        block->next = pool->free_list;
        pool->free_list = block;
    }
    
    pool->free_count = pool->block_count;
}
