/*
 * SENTINEL Shield - Entropy & Hashing
 */

#ifndef SHIELD_ENTROPY_H
#define SHIELD_ENTROPY_H

#include "shield_common.h"

/* Shannon entropy (bits per byte) */
float calculate_entropy(const uint8_t *data, size_t len);

/* Check if high entropy (likely encoded/encrypted) */
bool is_high_entropy(const uint8_t *data, size_t len, float threshold);

/* SimHash for similarity detection */
uint64_t simhash(const uint8_t *data, size_t len);

/* SimHash Hamming distance */
int simhash_distance(uint64_t a, uint64_t b);

/* Check if similar (within distance threshold) */
bool simhash_similar(uint64_t a, uint64_t b, int max_distance);

/* FNV-1a hash (32-bit) */
uint32_t fnv1a_32(const uint8_t *data, size_t len);

/* FNV-1a hash (64-bit) */
uint64_t fnv1a_64(const uint8_t *data, size_t len);

/* xxHash-style fast hash */
uint64_t fast_hash(const uint8_t *data, size_t len);

/* CRC32 */
uint32_t crc32(const uint8_t *data, size_t len);

#endif /* SHIELD_ENTROPY_H */
