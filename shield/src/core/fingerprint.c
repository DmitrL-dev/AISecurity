/*
 * SENTINEL Shield - Fingerprint Engine Implementation
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>

#include "shield_fingerprint.h"
#include "shield_entropy.h"

#define SHINGLE_SIZE 3

/* MurmurHash3 32-bit */
static uint32_t murmurhash3(const void *key, int len, uint32_t seed)
{
    const uint8_t *data = (const uint8_t *)key;
    const int nblocks = len / 4;
    
    uint32_t h1 = seed;
    const uint32_t c1 = 0xcc9e2d51;
    const uint32_t c2 = 0x1b873593;
    
    const uint32_t *blocks = (const uint32_t *)(data + nblocks * 4);
    
    for (int i = -nblocks; i; i++) {
        uint32_t k1 = blocks[i];
        
        k1 *= c1;
        k1 = (k1 << 15) | (k1 >> 17);
        k1 *= c2;
        
        h1 ^= k1;
        h1 = (h1 << 13) | (h1 >> 19);
        h1 = h1 * 5 + 0xe6546b64;
    }
    
    const uint8_t *tail = (const uint8_t *)(data + nblocks * 4);
    uint32_t k1 = 0;
    
    switch (len & 3) {
    case 3: k1 ^= tail[2] << 16; /* fallthrough */
    case 2: k1 ^= tail[1] << 8;  /* fallthrough */
    case 1: k1 ^= tail[0];
            k1 *= c1;
            k1 = (k1 << 15) | (k1 >> 17);
            k1 *= c2;
            h1 ^= k1;
    }
    
    h1 ^= len;
    h1 ^= h1 >> 16;
    h1 *= 0x85ebca6b;
    h1 ^= h1 >> 13;
    h1 *= 0xc2b2ae35;
    h1 ^= h1 >> 16;
    
    return h1;
}

/* Create fingerprint */
shield_err_t fingerprint_create(const char *text, size_t len, fingerprint_t *fp)
{
    if (!text || !fp) {
        return SHIELD_ERR_INVALID;
    }
    
    memset(fp, 0, sizeof(*fp));
    fp->original_len = len;
    
    /* Calculate simhash */
    fp->simhash = simhash((const uint8_t *)text, len);
    
    /* Calculate entropy */
    fp->entropy = calculate_entropy((const uint8_t *)text, len);
    
    /* Generate minhash */
    fingerprint_minhash(text, len, fp->minhash, 16);
    
    /* Generate shingles */
    int shingle_count = 0;
    for (size_t i = 0; i + SHINGLE_SIZE <= len && shingle_count < 32; i++) {
        fp->shingles[shingle_count++] = murmurhash3(text + i, SHINGLE_SIZE, 0);
    }
    
    /* Build n-gram profile */
    for (size_t i = 0; i + 2 <= len; i++) {
        uint8_t idx = (uint8_t)text[i] ^ (uint8_t)text[i + 1];
        if (fp->ngram_profile[idx] < 255) {
            fp->ngram_profile[idx]++;
        }
    }
    
    return SHIELD_OK;
}

/* SimHash for longer texts */
uint64_t fingerprint_simhash(const char *text, size_t len)
{
    return simhash((const uint8_t *)text, len);
}

/* MinHash */
void fingerprint_minhash(const char *text, size_t len, uint32_t *hashes, int count)
{
    if (!text || !hashes || count <= 0) return;
    
    /* Initialize to max */
    for (int i = 0; i < count; i++) {
        hashes[i] = UINT32_MAX;
    }
    
    /* For each shingle, compute multiple hashes */
    for (size_t i = 0; i + SHINGLE_SIZE <= len; i++) {
        for (int h = 0; h < count; h++) {
            uint32_t hash = murmurhash3(text + i, SHINGLE_SIZE, h);
            if (hash < hashes[h]) {
                hashes[h] = hash;
            }
        }
    }
}

/* Jaccard similarity from minhash */
float fingerprint_jaccard(const uint32_t *a, const uint32_t *b, int count)
{
    if (!a || !b || count <= 0) return 0.0f;
    
    int matches = 0;
    for (int i = 0; i < count; i++) {
        if (a[i] == b[i]) matches++;
    }
    
    return (float)matches / count;
}

/* Hamming distance for 64-bit values */
static int hamming_distance(uint64_t a, uint64_t b)
{
    uint64_t diff = a ^ b;
    int count = 0;
    while (diff) {
        count += diff & 1;
        diff >>= 1;
    }
    return count;
}

/* Calculate similarity */
float fingerprint_similarity(const fingerprint_t *a, const fingerprint_t *b)
{
    if (!a || !b) return 0.0f;
    
    /* Combine multiple similarity measures */
    float scores[4];
    float weights[4] = {0.4f, 0.3f, 0.2f, 0.1f};
    
    /* 1. SimHash similarity (Hamming distance) */
    int dist = hamming_distance(a->simhash, b->simhash);
    scores[0] = 1.0f - (dist / 64.0f);
    
    /* 2. MinHash Jaccard */
    scores[1] = fingerprint_jaccard(a->minhash, b->minhash, 16);
    
    /* 3. Shingle overlap */
    int shingle_matches = 0;
    for (int i = 0; i < 32; i++) {
        if (a->shingles[i] == 0) continue;
        for (int j = 0; j < 32; j++) {
            if (a->shingles[i] == b->shingles[j]) {
                shingle_matches++;
                break;
            }
        }
    }
    scores[2] = (float)shingle_matches / 32.0f;
    
    /* 4. N-gram profile cosine similarity */
    float dot = 0, norm_a = 0, norm_b = 0;
    for (int i = 0; i < 256; i++) {
        dot += a->ngram_profile[i] * b->ngram_profile[i];
        norm_a += a->ngram_profile[i] * a->ngram_profile[i];
        norm_b += b->ngram_profile[i] * b->ngram_profile[i];
    }
    if (norm_a > 0 && norm_b > 0) {
        scores[3] = dot / (sqrtf(norm_a) * sqrtf(norm_b));
    } else {
        scores[3] = 0;
    }
    
    /* Weighted combination */
    float total = 0;
    for (int i = 0; i < 4; i++) {
        total += scores[i] * weights[i];
    }
    
    return total;
}

/* Index init */
shield_err_t fingerprint_index_init(fingerprint_index_t *idx, float threshold)
{
    if (!idx) return SHIELD_ERR_INVALID;
    
    memset(idx, 0, sizeof(*idx));
    idx->threshold = threshold > 0 ? threshold : 0.7f;
    idx->capacity = 1000;
    
    idx->fingerprints = calloc(idx->capacity, sizeof(fingerprint_t *));
    idx->ids = calloc(idx->capacity, sizeof(char *));
    
    if (!idx->fingerprints || !idx->ids) {
        free(idx->fingerprints);
        free(idx->ids);
        return SHIELD_ERR_NOMEM;
    }
    
    return SHIELD_OK;
}

/* Index destroy */
void fingerprint_index_destroy(fingerprint_index_t *idx)
{
    if (!idx) return;
    
    for (int i = 0; i < idx->count; i++) {
        free(idx->fingerprints[i]);
        free(idx->ids[i]);
    }
    
    free(idx->fingerprints);
    free(idx->ids);
    
    idx->fingerprints = NULL;
    idx->ids = NULL;
    idx->count = 0;
}

/* Add to index */
shield_err_t fingerprint_index_add(fingerprint_index_t *idx, const char *id,
                                     const fingerprint_t *fp)
{
    if (!idx || !id || !fp) return SHIELD_ERR_INVALID;
    
    if (idx->count >= idx->capacity) {
        /* Resize */
        int new_cap = idx->capacity * 2;
        fingerprint_t **new_fps = realloc(idx->fingerprints,
                                            new_cap * sizeof(fingerprint_t *));
        char **new_ids = realloc(idx->ids, new_cap * sizeof(char *));
        
        if (!new_fps || !new_ids) {
            return SHIELD_ERR_NOMEM;
        }
        
        idx->fingerprints = new_fps;
        idx->ids = new_ids;
        idx->capacity = new_cap;
    }
    
    fingerprint_t *copy = malloc(sizeof(fingerprint_t));
    if (!copy) return SHIELD_ERR_NOMEM;
    
    memcpy(copy, fp, sizeof(fingerprint_t));
    idx->fingerprints[idx->count] = copy;
    idx->ids[idx->count] = strdup(id);
    idx->count++;
    
    return SHIELD_OK;
}

/* Search index */
int fingerprint_index_search(fingerprint_index_t *idx, const fingerprint_t *fp,
                               fingerprint_match_t *matches, int max_matches)
{
    if (!idx || !fp || !matches) return 0;
    
    int found = 0;
    
    for (int i = 0; i < idx->count && found < max_matches; i++) {
        float sim = fingerprint_similarity(fp, idx->fingerprints[i]);
        
        if (sim >= idx->threshold) {
            matches[found].id = idx->ids[i];
            matches[found].similarity = sim;
            matches[found].fingerprint = idx->fingerprints[i];
            found++;
        }
    }
    
    /* Sort by similarity (simple bubble sort for small results) */
    for (int i = 0; i < found - 1; i++) {
        for (int j = 0; j < found - i - 1; j++) {
            if (matches[j].similarity < matches[j + 1].similarity) {
                fingerprint_match_t tmp = matches[j];
                matches[j] = matches[j + 1];
                matches[j + 1] = tmp;
            }
        }
    }
    
    return found;
}
