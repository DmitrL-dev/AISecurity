/*
 * SENTINEL Shield - Vectorizer Implementation
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>
#include <math.h>

#include "shield_vectorizer.h"

#define MAX_VOCAB 1024

/* Initialize */
shield_err_t vectorizer_init(vectorizer_t *vec, vectorizer_type_t type, int dimension)
{
    if (!vec) return SHIELD_ERR_INVALID;
    
    memset(vec, 0, sizeof(*vec));
    vec->type = type;
    vec->dimension = dimension > 0 ? dimension : 256;
    vec->min_ngram = 1;
    vec->max_ngram = 2;
    vec->lowercase = true;
    
    return SHIELD_OK;
}

/* Destroy */
void vectorizer_destroy(vectorizer_t *vec)
{
    if (!vec) return;
    
    if (vec->vocab) {
        for (int i = 0; i < vec->vocab_size; i++) {
            free(vec->vocab[i]);
        }
        free(vec->vocab);
    }
    
    free(vec->idf);
}

/* Add word to vocabulary */
shield_err_t vectorizer_add_word(vectorizer_t *vec, const char *word)
{
    if (!vec || !word) return SHIELD_ERR_INVALID;
    
    /* Check if exists */
    for (int i = 0; i < vec->vocab_size; i++) {
        if (strcmp(vec->vocab[i], word) == 0) {
            return SHIELD_OK;  /* Already exists */
        }
    }
    
    /* Add new */
    if (vec->vocab_size >= MAX_VOCAB) {
        return SHIELD_ERR_NOMEM;
    }
    
    if (!vec->vocab) {
        vec->vocab = calloc(MAX_VOCAB, sizeof(char *));
        vec->idf = calloc(MAX_VOCAB, sizeof(float));
        if (!vec->vocab || !vec->idf) return SHIELD_ERR_NOMEM;
    }
    
    vec->vocab[vec->vocab_size] = strdup(word);
    vec->idf[vec->vocab_size] = 1.0f;  /* Default IDF */
    vec->vocab_size++;
    
    return SHIELD_OK;
}

/* Simple tokenizer */
static int tokenize(const char *text, char **tokens, int max_tokens, bool lowercase)
{
    char *copy = strdup(text);
    if (!copy) return 0;
    
    if (lowercase) {
        for (char *p = copy; *p; p++) {
            *p = tolower((unsigned char)*p);
        }
    }
    
    int count = 0;
    char *token = strtok(copy, " \t\n\r.,!?;:\"'()-");
    
    while (token && count < max_tokens) {
        if (strlen(token) > 1) {
            tokens[count++] = strdup(token);
        }
        token = strtok(NULL, " \t\n\r.,!?;:\"'()-");
    }
    
    free(copy);
    return count;
}

/* Fit vocabulary */
shield_err_t vectorizer_fit(vectorizer_t *vec, const char **texts, int count)
{
    if (!vec || !texts || count <= 0) return SHIELD_ERR_INVALID;
    
    char *tokens[256];
    
    for (int i = 0; i < count; i++) {
        int n = tokenize(texts[i], tokens, 256, vec->lowercase);
        
        for (int j = 0; j < n; j++) {
            vectorizer_add_word(vec, tokens[j]);
            free(tokens[j]);
        }
    }
    
    /* Calculate IDF */
    /* (simplified - just use 1.0 for all) */
    
    return SHIELD_OK;
}

/* Hash function for feature hashing */
static uint32_t murmurhash(const char *key, size_t len)
{
    uint32_t h = 0;
    for (size_t i = 0; i < len; i++) {
        h ^= (uint32_t)key[i];
        h *= 0x5bd1e995;
        h ^= h >> 15;
    }
    return h;
}

/* Transform text to vector */
shield_err_t vectorize(vectorizer_t *vec, const char *text, size_t len,
                         text_vector_t *out)
{
    if (!vec || !text || !out) return SHIELD_ERR_INVALID;
    
    out->dimension = vec->dimension;
    out->values = calloc(vec->dimension, sizeof(float));
    if (!out->values) return SHIELD_ERR_NOMEM;
    
    char *tokens[256];
    int n = tokenize(text, tokens, 256, vec->lowercase);
    
    switch (vec->type) {
    case VECTORIZER_BOW:
    case VECTORIZER_TFIDF:
        /* Count occurrences */
        for (int i = 0; i < n; i++) {
            for (int j = 0; j < vec->vocab_size && j < vec->dimension; j++) {
                if (strcmp(tokens[i], vec->vocab[j]) == 0) {
                    out->values[j] += 1.0f;
                    if (vec->type == VECTORIZER_TFIDF) {
                        out->values[j] *= vec->idf[j];
                    }
                }
            }
            free(tokens[i]);
        }
        break;
        
    case VECTORIZER_HASH:
        /* Feature hashing */
        for (int i = 0; i < n; i++) {
            uint32_t h = murmurhash(tokens[i], strlen(tokens[i]));
            int idx = h % vec->dimension;
            out->values[idx] += (h & 1) ? 1.0f : -1.0f;
            free(tokens[i]);
        }
        break;
        
    case VECTORIZER_CHAR:
        /* Character-level features */
        for (size_t i = 0; i < len; i++) {
            unsigned char c = (unsigned char)text[i];
            int idx = c % vec->dimension;
            out->values[idx] += 1.0f;
        }
        for (int i = 0; i < n; i++) free(tokens[i]);
        break;
    }
    
    return SHIELD_OK;
}

/* Free vector */
void vector_free(text_vector_t *vec)
{
    if (vec && vec->values) {
        free(vec->values);
        vec->values = NULL;
    }
}

/* Dot product */
float vector_dot(const text_vector_t *a, const text_vector_t *b)
{
    if (!a || !b || !a->values || !b->values) return 0;
    if (a->dimension != b->dimension) return 0;
    
    float sum = 0;
    for (int i = 0; i < a->dimension; i++) {
        sum += a->values[i] * b->values[i];
    }
    return sum;
}

/* Cosine similarity */
float vector_cosine(const text_vector_t *a, const text_vector_t *b)
{
    if (!a || !b) return 0;
    
    float dot = vector_dot(a, b);
    
    float norm_a = 0, norm_b = 0;
    for (int i = 0; i < a->dimension; i++) {
        norm_a += a->values[i] * a->values[i];
        norm_b += b->values[i] * b->values[i];
    }
    
    norm_a = sqrtf(norm_a);
    norm_b = sqrtf(norm_b);
    
    if (norm_a < 0.0001f || norm_b < 0.0001f) return 0;
    
    return dot / (norm_a * norm_b);
}

/* Euclidean distance */
float vector_euclidean(const text_vector_t *a, const text_vector_t *b)
{
    if (!a || !b || !a->values || !b->values) return INFINITY;
    if (a->dimension != b->dimension) return INFINITY;
    
    float sum = 0;
    for (int i = 0; i < a->dimension; i++) {
        float diff = a->values[i] - b->values[i];
        sum += diff * diff;
    }
    return sqrtf(sum);
}

/* Normalize vector */
void vector_normalize(text_vector_t *vec)
{
    if (!vec || !vec->values) return;
    
    float norm = 0;
    for (int i = 0; i < vec->dimension; i++) {
        norm += vec->values[i] * vec->values[i];
    }
    norm = sqrtf(norm);
    
    if (norm > 0.0001f) {
        for (int i = 0; i < vec->dimension; i++) {
            vec->values[i] /= norm;
        }
        vec->normalized = true;
    }
}
