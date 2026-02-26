/*
 * SENTINEL Shield - ML Classifier Interface
 * 
 * Interface for ML-based classification (pluggable backends)
 */

#ifndef SHIELD_CLASSIFIER_H
#define SHIELD_CLASSIFIER_H

#include "shield_common.h"

/* Classification result */
typedef struct classification {
    float           scores[10];     /* Per-class probabilities */
    int             predicted_class;
    float           confidence;
    char            label[64];
} classification_t;

/* Classifier backend */
typedef enum classifier_backend {
    CLASSIFIER_BUILTIN,     /* Built-in heuristics */
    CLASSIFIER_ONNX,        /* ONNX Runtime */
    CLASSIFIER_TFLITE,      /* TensorFlow Lite */
    CLASSIFIER_EXTERNAL,    /* External service */
} classifier_backend_t;

/* Classifier */
typedef struct classifier {
    char            name[64];
    classifier_backend_t backend;
    
    /* Model */
    void            *model;
    char            model_path[256];
    
    /* Classes */
    char            **class_names;
    int             num_classes;
    
    /* External endpoint */
    char            endpoint[256];
    int             timeout_ms;
    
    /* Stats */
    uint64_t        predictions;
    float           avg_latency_ms;
} classifier_t;

/* API */
shield_err_t classifier_init(classifier_t *clf, const char *name,
                               classifier_backend_t backend);
void classifier_destroy(classifier_t *clf);

/* Load model */
shield_err_t classifier_load(classifier_t *clf, const char *path);
shield_err_t classifier_set_endpoint(classifier_t *clf, const char *url);

/* Classify */
shield_err_t classify(classifier_t *clf, const char *text, size_t len,
                        classification_t *result);

/* Batch classify */
shield_err_t classify_batch(classifier_t *clf, const char **texts,
                              size_t *lens, int count,
                              classification_t *results);

/* Built-in heuristic classifier */
shield_err_t classify_heuristic(const char *text, size_t len,
                                  classification_t *result);

#endif /* SHIELD_CLASSIFIER_H */
