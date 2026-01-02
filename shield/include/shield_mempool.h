/*
 * SENTINEL Shield - Memory Pool
 * 
 * Fixed-size block allocator for performance
 */

#ifndef SHIELD_MEMPOOL_H
#define SHIELD_MEMPOOL_H

#include "shield_common.h"

/* Memory block */
typedef struct mem_block {
    struct mem_block *next;
} mem_block_t;

/* Memory pool */
typedef struct mem_pool {
    void            *memory;
    size_t          total_size;
    size_t          block_size;
    int             block_count;
    int             free_count;
    mem_block_t     *free_list;
    
    /* Stats */
    uint64_t        allocs;
    uint64_t        frees;
} mem_pool_t;

/* API */
shield_err_t mempool_init(mem_pool_t *pool, size_t block_size, int block_count);
void mempool_destroy(mem_pool_t *pool);

void *mempool_alloc(mem_pool_t *pool);
void mempool_free(mem_pool_t *pool, void *ptr);

int mempool_available(mem_pool_t *pool);
void mempool_reset(mem_pool_t *pool);

#endif /* SHIELD_MEMPOOL_H */
