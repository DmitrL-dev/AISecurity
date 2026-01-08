/*
 * SENTINEL IMMUNE — Bloom Filter Implementation
 * 
 * High-performance probabilistic data structure.
 * Uses MurmurHash3 for fast, high-quality hashing.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>

#include "bloom_filter.h"

/* ==================== Constants ==================== */

#define BLOOM_MAGIC     0x424C4F4D  /* "BLOM" */
#define BLOOM_VERSION   1

/* ==================== Internal Structure ==================== */

struct bloom_filter {
    uint32_t    magic;
    uint32_t    version;
    size_t      bits;           /* Total bits */
    size_t      bytes;          /* bytes = (bits + 7) / 8 */
    int         hash_count;     /* k hash functions */
    size_t      item_count;     /* Items added */
    size_t      bits_set;       /* Bits set (for stats) */
    uint8_t    *data;           /* Bit array */
};

/* ==================== MurmurHash3 ==================== */

/**
 * MurmurHash3 32-bit implementation.
 * Public domain implementation.
 */
static inline uint32_t
rotl32(uint32_t x, int8_t r)
{
    return (x << r) | (x >> (32 - r));
}

static inline uint32_t
fmix32(uint32_t h)
{
    h ^= h >> 16;
    h *= 0x85ebca6b;
    h ^= h >> 13;
    h *= 0xc2b2ae35;
    h ^= h >> 16;
    return h;
}

uint32_t
murmur3_32(const void *data, size_t len, uint32_t seed)
{
    const uint8_t *bytes = (const uint8_t *)data;
    const int nblocks = len / 4;
    
    uint32_t h1 = seed;
    
    const uint32_t c1 = 0xcc9e2d51;
    const uint32_t c2 = 0x1b873593;
    
    /* Body */
    const uint32_t *blocks = (const uint32_t *)(bytes + nblocks * 4);
    
    for (int i = -nblocks; i; i++) {
        uint32_t k1;
        memcpy(&k1, &blocks[i], sizeof(k1));
        
        k1 *= c1;
        k1 = rotl32(k1, 15);
        k1 *= c2;
        
        h1 ^= k1;
        h1 = rotl32(h1, 13);
        h1 = h1 * 5 + 0xe6546b64;
    }
    
    /* Tail */
    const uint8_t *tail = bytes + nblocks * 4;
    uint32_t k1 = 0;
    
    switch (len & 3) {
    case 3: k1 ^= tail[2] << 16; /* fallthrough */
    case 2: k1 ^= tail[1] << 8;  /* fallthrough */
    case 1: k1 ^= tail[0];
            k1 *= c1;
            k1 = rotl32(k1, 15);
            k1 *= c2;
            h1 ^= k1;
    }
    
    /* Finalization */
    h1 ^= len;
    h1 = fmix32(h1);
    
    return h1;
}

/* ==================== Helper Functions ==================== */

/**
 * Calculate optimal number of bits for given parameters.
 * m = -n * ln(p) / (ln(2))^2
 */
static size_t
calculate_bits(size_t items, double fpr)
{
    if (items == 0) items = 1;
    if (fpr <= 0) fpr = 0.01;
    if (fpr >= 1) fpr = 0.99;
    
    double m = -((double)items * log(fpr)) / (log(2.0) * log(2.0));
    return (size_t)ceil(m);
}

/**
 * Calculate optimal number of hash functions.
 * k = (m/n) * ln(2)
 */
static int
calculate_hash_count(size_t bits, size_t items)
{
    if (items == 0) items = 1;
    double k = ((double)bits / (double)items) * log(2.0);
    int result = (int)round(k);
    if (result < 1) result = 1;
    if (result > 16) result = 16;
    return result;
}

/**
 * Get bit at position.
 */
static inline bool
get_bit(const bloom_filter_t *bf, size_t pos)
{
    size_t byte_idx = pos / 8;
    uint8_t bit_mask = 1 << (pos % 8);
    return (bf->data[byte_idx] & bit_mask) != 0;
}

/**
 * Set bit at position.
 */
static inline void
set_bit(bloom_filter_t *bf, size_t pos)
{
    size_t byte_idx = pos / 8;
    uint8_t bit_mask = 1 << (pos % 8);
    if (!(bf->data[byte_idx] & bit_mask)) {
        bf->data[byte_idx] |= bit_mask;
        bf->bits_set++;
    }
}

/* ==================== Configuration ==================== */

void
bloom_config_init(bloom_config_t *config)
{
    if (!config) return;
    
    config->expected_items = BLOOM_DEFAULT_ITEMS;
    config->false_positive_rate = BLOOM_DEFAULT_FPR;
    config->hash_count = 0;  /* Auto-calculate */
}

/* ==================== Lifecycle ==================== */

bloom_filter_t*
bloom_create(const bloom_config_t *config)
{
    bloom_config_t default_config;
    
    if (!config) {
        bloom_config_init(&default_config);
        config = &default_config;
    }
    
    /* Calculate optimal parameters */
    size_t bits = calculate_bits(config->expected_items, 
                                 config->false_positive_rate);
    int hash_count = config->hash_count > 0 
                     ? config->hash_count
                     : calculate_hash_count(bits, config->expected_items);
    
    return bloom_create_raw(bits, hash_count);
}

bloom_filter_t*
bloom_create_raw(size_t bits, int hash_count)
{
    if (bits < 8) bits = 8;
    if (hash_count < 1) hash_count = 1;
    if (hash_count > 16) hash_count = 16;
    
    bloom_filter_t *bf = calloc(1, sizeof(bloom_filter_t));
    if (!bf) return NULL;
    
    bf->magic = BLOOM_MAGIC;
    bf->version = BLOOM_VERSION;
    bf->bits = bits;
    bf->bytes = (bits + 7) / 8;
    bf->hash_count = hash_count;
    bf->item_count = 0;
    bf->bits_set = 0;
    
    bf->data = calloc(bf->bytes, 1);
    if (!bf->data) {
        free(bf);
        return NULL;
    }
    
    return bf;
}

void
bloom_destroy(bloom_filter_t *filter)
{
    if (filter) {
        if (filter->data) {
            /* Zero memory before free (security) */
            memset(filter->data, 0, filter->bytes);
            free(filter->data);
        }
        memset(filter, 0, sizeof(*filter));
        free(filter);
    }
}

void
bloom_clear(bloom_filter_t *filter)
{
    if (filter && filter->data) {
        memset(filter->data, 0, filter->bytes);
        filter->item_count = 0;
        filter->bits_set = 0;
    }
}

/* ==================== Operations ==================== */

void
bloom_add(bloom_filter_t *filter, const void *data, size_t len)
{
    if (!filter || !data || len == 0) return;
    
    for (int i = 0; i < filter->hash_count; i++) {
        uint32_t hash = murmur3_32(data, len, (uint32_t)i);
        size_t pos = hash % filter->bits;
        set_bit(filter, pos);
    }
    
    filter->item_count++;
}

void
bloom_add_string(bloom_filter_t *filter, const char *str)
{
    if (!filter || !str) return;
    bloom_add(filter, str, strlen(str));
}

bool
bloom_check(const bloom_filter_t *filter, const void *data, size_t len)
{
    if (!filter || !data || len == 0) return false;
    
    for (int i = 0; i < filter->hash_count; i++) {
        uint32_t hash = murmur3_32(data, len, (uint32_t)i);
        size_t pos = hash % filter->bits;
        if (!get_bit(filter, pos)) {
            return false;  /* Definitely not present */
        }
    }
    
    return true;  /* Possibly present */
}

bool
bloom_check_string(const bloom_filter_t *filter, const char *str)
{
    if (!filter || !str) return false;
    return bloom_check(filter, str, strlen(str));
}

/* ==================== Statistics ==================== */

void
bloom_stats(const bloom_filter_t *filter, bloom_stats_t *stats)
{
    if (!filter || !stats) return;
    
    memset(stats, 0, sizeof(*stats));
    
    stats->items_count = filter->item_count;
    stats->bits_total = filter->bits;
    stats->bits_set = filter->bits_set;
    stats->fill_ratio = (double)filter->bits_set / (double)filter->bits;
    stats->hash_count = filter->hash_count;
    stats->memory_bytes = sizeof(bloom_filter_t) + filter->bytes;
    
    /* Estimated FPR = (1 - e^(-kn/m))^k */
    if (filter->bits > 0 && filter->item_count > 0) {
        double k = filter->hash_count;
        double n = filter->item_count;
        double m = filter->bits;
        double exp_val = exp(-k * n / m);
        stats->estimated_fpr = pow(1.0 - exp_val, k);
    } else {
        stats->estimated_fpr = 0.0;
    }
}

double
bloom_current_fpr(const bloom_filter_t *filter)
{
    bloom_stats_t stats;
    bloom_stats(filter, &stats);
    return stats.estimated_fpr;
}

/* ==================== Serialization ==================== */

/* File format:
 * [magic: 4] [version: 4] [bits: 8] [hash_count: 4] [item_count: 8] [data: bytes]
 */

size_t
bloom_serialize_size(const bloom_filter_t *filter)
{
    if (!filter) return 0;
    return 4 + 4 + 8 + 4 + 8 + filter->bytes;  /* Header + data */
}

int
bloom_save(const bloom_filter_t *filter, const char *path)
{
    if (!filter || !path) return -1;
    
    FILE *fp = fopen(path, "wb");
    if (!fp) return -1;
    
    /* Write header */
    uint32_t magic = BLOOM_MAGIC;
    uint32_t version = BLOOM_VERSION;
    uint64_t bits = filter->bits;
    uint32_t hash_count = filter->hash_count;
    uint64_t item_count = filter->item_count;
    
    if (fwrite(&magic, 4, 1, fp) != 1 ||
        fwrite(&version, 4, 1, fp) != 1 ||
        fwrite(&bits, 8, 1, fp) != 1 ||
        fwrite(&hash_count, 4, 1, fp) != 1 ||
        fwrite(&item_count, 8, 1, fp) != 1) {
        fclose(fp);
        return -1;
    }
    
    /* Write data */
    if (fwrite(filter->data, filter->bytes, 1, fp) != 1) {
        fclose(fp);
        return -1;
    }
    
    fclose(fp);
    return 0;
}

bloom_filter_t*
bloom_load(const char *path)
{
    if (!path) return NULL;
    
    FILE *fp = fopen(path, "rb");
    if (!fp) return NULL;
    
    /* Read header */
    uint32_t magic, version, hash_count;
    uint64_t bits, item_count;
    
    if (fread(&magic, 4, 1, fp) != 1 ||
        fread(&version, 4, 1, fp) != 1 ||
        fread(&bits, 8, 1, fp) != 1 ||
        fread(&hash_count, 4, 1, fp) != 1 ||
        fread(&item_count, 8, 1, fp) != 1) {
        fclose(fp);
        return NULL;
    }
    
    /* Validate */
    if (magic != BLOOM_MAGIC || version > BLOOM_VERSION) {
        fclose(fp);
        return NULL;
    }
    
    /* Create filter */
    bloom_filter_t *bf = bloom_create_raw(bits, hash_count);
    if (!bf) {
        fclose(fp);
        return NULL;
    }
    
    /* Read data */
    if (fread(bf->data, bf->bytes, 1, fp) != 1) {
        bloom_destroy(bf);
        fclose(fp);
        return NULL;
    }
    
    bf->item_count = item_count;
    
    /* Count bits set */
    bf->bits_set = 0;
    for (size_t i = 0; i < bf->bytes; i++) {
        /* Population count */
        uint8_t b = bf->data[i];
        while (b) {
            bf->bits_set += b & 1;
            b >>= 1;
        }
    }
    
    fclose(fp);
    return bf;
}
