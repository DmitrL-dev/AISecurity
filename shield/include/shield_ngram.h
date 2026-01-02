/*
 * SENTINEL Shield - N-gram Analyzer
 * 
 * Analyze text using n-gram features
 */

#ifndef SHIELD_NGRAM_H
#define SHIELD_NGRAM_H

#include "shield_common.h"

/* N-gram profile */
typedef struct ngram_profile {
    uint32_t        *hashes;
    float           *frequencies;
    int             count;
    int             n;              /* N in n-gram */
} ngram_profile_t;

/* N-gram model */
typedef struct ngram_model {
    ngram_profile_t baseline;       /* Normal text profile */
    ngram_profile_t attack;         /* Attack text profile */
    float           threshold;
} ngram_model_t;

/* API */
shield_err_t ngram_profile_create(const char *text, size_t len, int n,
                                    ngram_profile_t *profile);
void ngram_profile_destroy(ngram_profile_t *profile);

/* Compare profiles */
float ngram_similarity(const ngram_profile_t *a, const ngram_profile_t *b);
float ngram_distance(const ngram_profile_t *a, const ngram_profile_t *b);

/* Model */
shield_err_t ngram_model_init(ngram_model_t *model);
void ngram_model_destroy(ngram_model_t *model);

shield_err_t ngram_model_train_baseline(ngram_model_t *model,
                                          const char **texts, int count);
shield_err_t ngram_model_train_attack(ngram_model_t *model,
                                        const char **texts, int count);

float ngram_model_score(ngram_model_t *model, const char *text, size_t len);
bool ngram_model_is_attack(ngram_model_t *model, const char *text, size_t len);

#endif /* SHIELD_NGRAM_H */
