/*
 * SENTINEL Shield - Fingerprint Engine
 * 
 * Create and match content fingerprints for similarity detection
 */

#ifndef SHIELD_FINGERPRINT_H
#define SHIELD_FINGERPRINT_H

#include "shield_common.h"

/* Fingerprint type */
typedef struct fingerprint {
    uint64_t        simhash;
    uint32_t        minhash[16];
    uint32_t        shingles[32];
    size_t          original_len;
    float           entropy;
    uint8_t         ngram_profile[256];
} fingerprint_t;

/* Fingerprint index */
typedef struct fingerprint_index {
    fingerprint_t   **fingerprints;
    char            **ids;
    int             count;
    int             capacity;
    float           threshold;
} fingerprint_index_t;

/* Match result */
typedef struct fingerprint_match {
    const char      *id;
    float           similarity;
    fingerprint_t   *fingerprint;
} fingerprint_match_t;

/* API */
shield_err_t fingerprint_create(const char *text, size_t len, fingerprint_t *fp);
float fingerprint_similarity(const fingerprint_t *a, const fingerprint_t *b);

/* Index operations */
shield_err_t fingerprint_index_init(fingerprint_index_t *idx, float threshold);
void fingerprint_index_destroy(fingerprint_index_t *idx);

shield_err_t fingerprint_index_add(fingerprint_index_t *idx, const char *id,
                                     const fingerprint_t *fp);
int fingerprint_index_search(fingerprint_index_t *idx, const fingerprint_t *fp,
                               fingerprint_match_t *matches, int max_matches);

/* Helpers */
uint64_t fingerprint_simhash(const char *text, size_t len);
void fingerprint_minhash(const char *text, size_t len, uint32_t *hashes, int count);
float fingerprint_jaccard(const uint32_t *a, const uint32_t *b, int count);

#endif /* SHIELD_FINGERPRINT_H */
