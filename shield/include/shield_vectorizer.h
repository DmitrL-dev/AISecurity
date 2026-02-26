/*
 * SENTINEL Shield - Vectorizer
 * 
 * Convert text to numerical vectors for ML-style analysis
 */

#ifndef SHIELD_VECTORIZER_H
#define SHIELD_VECTORIZER_H

#include "shield_common.h"

/* Vector */
typedef struct text_vector {
    float           *values;
    int             dimension;
    bool            normalized;
} text_vector_t;

/* Vectorizer types */
typedef enum vectorizer_type {
    VECTORIZER_BOW,         /* Bag of words */
    VECTORIZER_TFIDF,       /* TF-IDF */
    VECTORIZER_HASH,        /* Feature hashing */
    VECTORIZER_CHAR,        /* Character-level */
} vectorizer_type_t;

/* Vectorizer */
typedef struct vectorizer {
    vectorizer_type_t type;
    int             dimension;
    
    /* Vocabulary (for BOW/TFIDF) */
    char            **vocab;
    float           *idf;
    int             vocab_size;
    
    /* Parameters */
    int             min_ngram;
    int             max_ngram;
    bool            lowercase;
} vectorizer_t;

/* API */
shield_err_t vectorizer_init(vectorizer_t *vec, vectorizer_type_t type, int dimension);
void vectorizer_destroy(vectorizer_t *vec);

/* Transform */
shield_err_t vectorize(vectorizer_t *vec, const char *text, size_t len,
                         text_vector_t *out);
void vector_free(text_vector_t *vec);

/* Vector operations */
float vector_dot(const text_vector_t *a, const text_vector_t *b);
float vector_cosine(const text_vector_t *a, const text_vector_t *b);
float vector_euclidean(const text_vector_t *a, const text_vector_t *b);
void vector_normalize(text_vector_t *vec);

/* Vocabulary */
shield_err_t vectorizer_fit(vectorizer_t *vec, const char **texts, int count);
shield_err_t vectorizer_add_word(vectorizer_t *vec, const char *word);

#endif /* SHIELD_VECTORIZER_H */
