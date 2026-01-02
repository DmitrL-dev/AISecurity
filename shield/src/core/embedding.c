/*
 * SENTINEL Shield - Embedding Implementation
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>

#include "shield_embedding.h"
#include "shield_hashtable.h"

#define SIMPLE_DIM 64

/* Initialize */
shield_err_t embedding_service_init(embedding_service_t *svc,
                                      embedding_provider_t provider)
{
    if (!svc) return SHIELD_ERR_INVALID;
    
    memset(svc, 0, sizeof(*svc));
    svc->provider = provider;
    svc->timeout_ms = 5000;
    
    switch (provider) {
    case EMBED_BUILTIN:
        svc->dimension = SIMPLE_DIM;
        break;
    case EMBED_OPENAI:
        strcpy(svc->model, "text-embedding-3-small");
        svc->dimension = 1536;
        break;
    default:
        svc->dimension = SIMPLE_DIM;
    }
    
    return SHIELD_OK;
}

/* Destroy */
void embedding_service_destroy(embedding_service_t *svc)
{
    if (!svc) return;
    
    if (svc->cache) {
        ht_destroy((hash_table_t *)svc->cache);
        free(svc->cache);
    }
}

/* Set API key */
void embedding_set_api_key(embedding_service_t *svc, const char *key)
{
    if (svc && key) {
        strncpy(svc->api_key, key, sizeof(svc->api_key) - 1);
    }
}

/* Set model */
void embedding_set_model(embedding_service_t *svc, const char *model)
{
    if (svc && model) {
        strncpy(svc->model, model, sizeof(svc->model) - 1);
    }
}

/* Simple hash-based embedding */
shield_err_t embed_simple(const char *text, size_t len, embedding_t *out)
{
    if (!text || !out) return SHIELD_ERR_INVALID;
    
    out->dimension = SIMPLE_DIM;
    out->vector = calloc(SIMPLE_DIM, sizeof(float));
    if (!out->vector) return SHIELD_ERR_NOMEM;
    
    strcpy(out->model, "builtin-simple");
    
    /* Simple character-based hashing */
    for (size_t i = 0; i < len; i++) {
        unsigned char c = (unsigned char)text[i];
        int idx = (c * (int)(i + 1)) % SIMPLE_DIM;
        out->vector[idx] += 1.0f / (i + 1);
    }
    
    /* Add n-gram features */
    for (size_t i = 0; i + 2 < len; i++) {
        uint32_t h = (uint32_t)text[i] * 31 + (uint32_t)text[i+1] * 7 + (uint32_t)text[i+2];
        int idx = h % SIMPLE_DIM;
        out->vector[idx] += 0.1f;
    }
    
    /* Normalize */
    float norm = 0;
    for (int i = 0; i < SIMPLE_DIM; i++) {
        norm += out->vector[i] * out->vector[i];
    }
    norm = sqrtf(norm);
    
    if (norm > 0) {
        for (int i = 0; i < SIMPLE_DIM; i++) {
            out->vector[i] /= norm;
        }
    }
    
    out->normalized = true;
    
    return SHIELD_OK;
}

/* Embed text */
shield_err_t embed_text(embedding_service_t *svc, const char *text, size_t len,
                          embedding_t *out)
{
    if (!svc || !text || !out) return SHIELD_ERR_INVALID;
    
    switch (svc->provider) {
    case EMBED_BUILTIN:
        return embed_simple(text, len, out);
        
    case EMBED_OPENAI:
    case EMBED_HUGGINGFACE:
    case EMBED_LOCAL:
        /* TODO: Implement API calls */
        LOG_WARN("External embedding not implemented, using builtin");
        return embed_simple(text, len, out);
        
    default:
        return embed_simple(text, len, out);
    }
}

/* Free embedding */
void embedding_free(embedding_t *emb)
{
    if (emb && emb->vector) {
        free(emb->vector);
        emb->vector = NULL;
    }
}

/* Cosine similarity */
float embedding_cosine(const embedding_t *a, const embedding_t *b)
{
    if (!a || !b || !a->vector || !b->vector) return 0;
    if (a->dimension != b->dimension) return 0;
    
    float dot = 0;
    float norm_a = 0;
    float norm_b = 0;
    
    for (int i = 0; i < a->dimension; i++) {
        dot += a->vector[i] * b->vector[i];
        norm_a += a->vector[i] * a->vector[i];
        norm_b += b->vector[i] * b->vector[i];
    }
    
    norm_a = sqrtf(norm_a);
    norm_b = sqrtf(norm_b);
    
    if (norm_a < 0.0001f || norm_b < 0.0001f) return 0;
    
    return dot / (norm_a * norm_b);
}

/* Euclidean distance */
float embedding_euclidean(const embedding_t *a, const embedding_t *b)
{
    if (!a || !b || !a->vector || !b->vector) return INFINITY;
    if (a->dimension != b->dimension) return INFINITY;
    
    float sum = 0;
    
    for (int i = 0; i < a->dimension; i++) {
        float diff = a->vector[i] - b->vector[i];
        sum += diff * diff;
    }
    
    return sqrtf(sum);
}
