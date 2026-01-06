/*
 * SENTINEL Shield - N-gram Implementation
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>
#include <math.h>

#include "shield_ngram.h"
#include "shield_string_safe.h"

#define MAX_NGRAMS 1024

/* FNV-1a hash */
static uint32_t fnv1a(const char *s, size_t len)
{
    uint32_t h = 2166136261u;
    for (size_t i = 0; i < len; i++) {
        h ^= (uint32_t)s[i];
        h *= 16777619u;
    }
    return h;
}

/* Create n-gram profile */
shield_err_t ngram_profile_create(const char *text, size_t len, int n,
                                    ngram_profile_t *profile)
{
    if (!text || !profile || n < 1) return SHIELD_ERR_INVALID;
    
    memset(profile, 0, sizeof(*profile));
    profile->n = n;
    
    if (len < (size_t)n) return SHIELD_OK;
    
    /* Allocate */
    profile->hashes = malloc(MAX_NGRAMS * sizeof(uint32_t));
    profile->frequencies = calloc(MAX_NGRAMS, sizeof(float));
    if (!profile->hashes || !profile->frequencies) {
        free(profile->hashes);
        free(profile->frequencies);
        return SHIELD_ERR_NOMEM;
    }
    
    /* Extract n-grams */
    size_t gram_count = len - n + 1;
    int unique = 0;
    
    for (size_t i = 0; i < gram_count && unique < MAX_NGRAMS; i++) {
        uint32_t h = fnv1a(text + i, n);
        
        /* Check if already seen */
        bool found = false;
        for (int j = 0; j < unique; j++) {
            if (profile->hashes[j] == h) {
                profile->frequencies[j] += 1.0f;
                found = true;
                break;
            }
        }
        
        if (!found) {
            profile->hashes[unique] = h;
            profile->frequencies[unique] = 1.0f;
            unique++;
        }
    }
    
    profile->count = unique;
    
    /* Normalize frequencies */
    float total = 0;
    for (int i = 0; i < unique; i++) {
        total += profile->frequencies[i];
    }
    if (total > 0) {
        for (int i = 0; i < unique; i++) {
            profile->frequencies[i] /= total;
        }
    }
    
    return SHIELD_OK;
}

/* Destroy profile */
void ngram_profile_destroy(ngram_profile_t *profile)
{
    if (!profile) return;
    
    free(profile->hashes);
    free(profile->frequencies);
    memset(profile, 0, sizeof(*profile));
}

/* Compute similarity */
float ngram_similarity(const ngram_profile_t *a, const ngram_profile_t *b)
{
    if (!a || !b || a->count == 0 || b->count == 0) return 0;
    
    float common = 0;
    
    for (int i = 0; i < a->count; i++) {
        for (int j = 0; j < b->count; j++) {
            if (a->hashes[i] == b->hashes[j]) {
                common += fminf(a->frequencies[i], b->frequencies[j]);
            }
        }
    }
    
    return common;
}

/* Compute distance */
float ngram_distance(const ngram_profile_t *a, const ngram_profile_t *b)
{
    return 1.0f - ngram_similarity(a, b);
}

/* Initialize model */
shield_err_t ngram_model_init(ngram_model_t *model)
{
    if (!model) return SHIELD_ERR_INVALID;
    
    memset(model, 0, sizeof(*model));
    model->threshold = 0.5f;
    
    return SHIELD_OK;
}

/* Destroy model */
void ngram_model_destroy(ngram_model_t *model)
{
    if (!model) return;
    
    ngram_profile_destroy(&model->baseline);
    ngram_profile_destroy(&model->attack);
}

/* Train baseline */
shield_err_t ngram_model_train_baseline(ngram_model_t *model,
                                          const char **texts, int count)
{
    if (!model || !texts || count <= 0) return SHIELD_ERR_INVALID;
    
    /* Combine all texts */
    size_t total_len = 0;
    for (int i = 0; i < count; i++) {
        total_len += strlen(texts[i]) + 1;
    }
    
    char *combined = malloc(total_len);
    if (!combined) return SHIELD_ERR_NOMEM;
    
    combined[0] = '\0';
    for (int i = 0; i < count; i++) {
        shield_strcat_s(combined, total_len, texts[i]);
        shield_strcat_s(combined, total_len, " ");
    }
    
    shield_err_t err = ngram_profile_create(combined, strlen(combined), 3, &model->baseline);
    
    free(combined);
    return err;
}

/* Train attack profile */
shield_err_t ngram_model_train_attack(ngram_model_t *model,
                                        const char **texts, int count)
{
    if (!model || !texts || count <= 0) return SHIELD_ERR_INVALID;
    
    size_t total_len = 0;
    for (int i = 0; i < count; i++) {
        total_len += strlen(texts[i]) + 1;
    }
    
    char *combined = malloc(total_len);
    if (!combined) return SHIELD_ERR_NOMEM;
    
    combined[0] = '\0';
    for (int i = 0; i < count; i++) {
        shield_strcat_s(combined, total_len, texts[i]);
        shield_strcat_s(combined, total_len, " ");
    }
    
    shield_err_t err = ngram_profile_create(combined, strlen(combined), 3, &model->attack);
    
    free(combined);
    return err;
}

/* Score text */
float ngram_model_score(ngram_model_t *model, const char *text, size_t len)
{
    if (!model || !text) return 0;
    
    ngram_profile_t profile;
    if (ngram_profile_create(text, len, 3, &profile) != SHIELD_OK) {
        return 0;
    }
    
    float baseline_sim = ngram_similarity(&profile, &model->baseline);
    float attack_sim = ngram_similarity(&profile, &model->attack);
    
    ngram_profile_destroy(&profile);
    
    /* Higher score = more like attack */
    if (baseline_sim + attack_sim == 0) return 0.5f;
    
    return attack_sim / (baseline_sim + attack_sim);
}

/* Check if attack */
bool ngram_model_is_attack(ngram_model_t *model, const char *text, size_t len)
{
    return ngram_model_score(model, text, len) > model->threshold;
}
