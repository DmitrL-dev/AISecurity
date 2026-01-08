/*
 * SENTINEL IMMUNE — Bloom Filter
 * 
 * High-performance probabilistic data structure for fast
 * pattern pre-filtering. Used to quickly reject inputs
 * that definitely don't match any pattern.
 * 
 * Features:
 * - MurmurHash3 for hashing
 * - Configurable false positive rate
 * - Cache-friendly sequential memory layout
 * - Thread-safe reads (not writes)
 */

#ifndef IMMUNE_BLOOM_FILTER_H
#define IMMUNE_BLOOM_FILTER_H

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>

/* Default parameters */
#define BLOOM_DEFAULT_ITEMS     10000
#define BLOOM_DEFAULT_FPR       0.01    /* 1% false positive rate */

/* Bloom filter handle (opaque) */
typedef struct bloom_filter bloom_filter_t;

/* Configuration */
typedef struct {
    size_t expected_items;      /* Expected number of items */
    double false_positive_rate; /* Desired FPR (default: 0.01) */
    int    hash_count;          /* Number of hash functions (0 = auto) */
} bloom_config_t;

/* Statistics */
typedef struct {
    size_t items_count;     /* Items added */
    size_t bits_total;      /* Total bits in filter */
    size_t bits_set;        /* Bits set to 1 */
    double fill_ratio;      /* bits_set / bits_total */
    double estimated_fpr;   /* Actual FPR based on fill ratio */
    int    hash_count;      /* Number of hash functions */
    size_t memory_bytes;    /* Memory usage */
} bloom_stats_t;

/* === Configuration === */

/**
 * Initialize configuration with defaults.
 * @param config Configuration to initialize
 */
void bloom_config_init(bloom_config_t *config);

/* === Lifecycle === */

/**
 * Create new Bloom filter.
 * @param config Configuration (NULL for defaults)
 * @return Filter handle or NULL on error
 */
bloom_filter_t* bloom_create(const bloom_config_t *config);

/**
 * Create filter by specifying bits and hash count directly.
 * @param bits Number of bits
 * @param hash_count Number of hash functions
 * @return Filter handle or NULL on error
 */
bloom_filter_t* bloom_create_raw(size_t bits, int hash_count);

/**
 * Destroy filter and free memory.
 * @param filter Filter to destroy
 */
void bloom_destroy(bloom_filter_t *filter);

/**
 * Clear all bits (reset filter).
 * @param filter Filter to clear
 */
void bloom_clear(bloom_filter_t *filter);

/* === Operations === */

/**
 * Add item to filter.
 * @param filter Filter
 * @param data Item data
 * @param len Data length
 */
void bloom_add(bloom_filter_t *filter, const void *data, size_t len);

/**
 * Add null-terminated string to filter.
 * @param filter Filter
 * @param str String to add
 */
void bloom_add_string(bloom_filter_t *filter, const char *str);

/**
 * Check if item is possibly in filter.
 * @param filter Filter
 * @param data Item data
 * @param len Data length
 * @return true if possibly present, false if definitely not present
 */
bool bloom_check(const bloom_filter_t *filter, const void *data, size_t len);

/**
 * Check if string is possibly in filter.
 * @param filter Filter
 * @param str String to check
 * @return true if possibly present, false if definitely not present
 */
bool bloom_check_string(const bloom_filter_t *filter, const char *str);

/* === Statistics === */

/**
 * Get filter statistics.
 * @param filter Filter
 * @param stats Output statistics
 */
void bloom_stats(const bloom_filter_t *filter, bloom_stats_t *stats);

/**
 * Get current estimated false positive rate.
 * @param filter Filter
 * @return Estimated FPR based on current fill ratio
 */
double bloom_current_fpr(const bloom_filter_t *filter);

/* === Serialization === */

/**
 * Save filter to file.
 * @param filter Filter to save
 * @param path File path
 * @return 0 on success, -1 on error
 */
int bloom_save(const bloom_filter_t *filter, const char *path);

/**
 * Load filter from file.
 * @param path File path
 * @return Filter handle or NULL on error
 */
bloom_filter_t* bloom_load(const char *path);

/**
 * Get serialized size.
 * @param filter Filter
 * @return Size in bytes
 */
size_t bloom_serialize_size(const bloom_filter_t *filter);

/* === MurmurHash3 === */

/**
 * MurmurHash3 32-bit hash function.
 * @param data Data to hash
 * @param len Data length
 * @param seed Hash seed
 * @return 32-bit hash value
 */
uint32_t murmur3_32(const void *data, size_t len, uint32_t seed);

#endif /* IMMUNE_BLOOM_FILTER_H */
