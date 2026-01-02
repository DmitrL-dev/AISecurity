/*
 * SENTINEL Shield - Embedding Interface
 * 
 * Interface for text embeddings (semantic similarity)
 */

#ifndef SHIELD_EMBEDDING_H
#define SHIELD_EMBEDDING_H

#include "shield_common.h"

/* Embedding vector */
typedef struct embedding {
    float           *vector;
    int             dimension;
    char            model[64];
} embedding_t;

/* Embedding provider */
typedef enum embedding_provider {
    EMBED_BUILTIN,          /* Simple hash-based */
    EMBED_OPENAI,           /* OpenAI embeddings */
    EMBED_HUGGINGFACE,      /* HuggingFace API */
    EMBED_LOCAL,            /* Local model */
} embedding_provider_t;

/* Embedding service */
typedef struct embedding_service {
    embedding_provider_t provider;
    char            api_key[256];
    char            model[64];
    char            endpoint[256];
    int             dimension;
    int             timeout_ms;
    
    /* Cache */
    void            *cache;
    int             cache_size;
} embedding_service_t;

/* API */
shield_err_t embedding_service_init(embedding_service_t *svc,
                                      embedding_provider_t provider);
void embedding_service_destroy(embedding_service_t *svc);

/* Configure */
void embedding_set_api_key(embedding_service_t *svc, const char *key);
void embedding_set_model(embedding_service_t *svc, const char *model);

/* Embed */
shield_err_t embed_text(embedding_service_t *svc, const char *text, size_t len,
                          embedding_t *out);
void embedding_free(embedding_t *emb);

/* Similarity */
float embedding_cosine(const embedding_t *a, const embedding_t *b);
float embedding_euclidean(const embedding_t *a, const embedding_t *b);

/* Built-in simple embedding */
shield_err_t embed_simple(const char *text, size_t len, embedding_t *out);

#endif /* SHIELD_EMBEDDING_H */
