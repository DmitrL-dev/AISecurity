/*
 * SENTINEL Shield - Classifier Implementation
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "shield_classifier.h"
#include "shield_semantic.h"
#include "shield_string.h"
#include "shield_string_safe.h"

/* Class names */
static const char *DEFAULT_CLASSES[] = {
    "benign",
    "instruction_override",
    "jailbreak",
    "data_extraction",
    "prompt_leak",
    "roleplay",
    "social_engineering",
    NULL
};

/* Initialize */
shield_err_t classifier_init(classifier_t *clf, const char *name,
                               classifier_backend_t backend)
{
    if (!clf || !name) return SHIELD_ERR_INVALID;
    
    memset(clf, 0, sizeof(*clf));
    strncpy(clf->name, name, sizeof(clf->name) - 1);
    clf->backend = backend;
    clf->timeout_ms = 5000;
    
    /* Default classes */
    clf->num_classes = 7;
    clf->class_names = malloc(clf->num_classes * sizeof(char *));
    if (!clf->class_names) return SHIELD_ERR_NOMEM;
    
    for (int i = 0; i < clf->num_classes; i++) {
        clf->class_names[i] = strdup(DEFAULT_CLASSES[i]);
    }
    
    return SHIELD_OK;
}

/* Destroy */
void classifier_destroy(classifier_t *clf)
{
    if (!clf) return;
    
    if (clf->class_names) {
        for (int i = 0; i < clf->num_classes; i++) {
            free(clf->class_names[i]);
        }
        free(clf->class_names);
    }
}

/* Load model (stub for ONNX/TFLite) */
shield_err_t classifier_load(classifier_t *clf, const char *path)
{
    if (!clf || !path) return SHIELD_ERR_INVALID;
    
    strncpy(clf->model_path, path, sizeof(clf->model_path) - 1);
    
    /* TODO: Load actual ONNX/TFLite model */
    LOG_INFO("Classifier model path set: %s (using builtin heuristics)", path);
    
    return SHIELD_OK;
}

/* Set external endpoint */
shield_err_t classifier_set_endpoint(classifier_t *clf, const char *url)
{
    if (!clf || !url) return SHIELD_ERR_INVALID;
    
    strncpy(clf->endpoint, url, sizeof(clf->endpoint) - 1);
    clf->backend = CLASSIFIER_EXTERNAL;
    
    return SHIELD_OK;
}

/* Built-in heuristic classifier */
shield_err_t classify_heuristic(const char *text, size_t len,
                                  classification_t *result)
{
    if (!text || !result) return SHIELD_ERR_INVALID;
    
    memset(result, 0, sizeof(*result));
    
    /* Use semantic detector */
    semantic_detector_t detector;
    semantic_result_t sem_result;
    
    semantic_init(&detector);
    semantic_analyze(&detector, text, len, &sem_result);
    semantic_destroy(&detector);
    
    /* Map intent to class */
    result->predicted_class = sem_result.primary_intent;
    result->confidence = sem_result.confidence;
    
    if (result->predicted_class == 0) {
        shield_strcopy_s(result->label, sizeof(result->label), "benign");
        result->scores[0] = 1.0f - sem_result.confidence;
    } else {
        snprintf(result->label, sizeof(result->label), "%s",
                 intent_type_string(sem_result.primary_intent));
        result->scores[result->predicted_class] = sem_result.confidence;
        result->scores[0] = 1.0f - sem_result.confidence;
    }
    
    return SHIELD_OK;
}

/* Classify */
shield_err_t classify(classifier_t *clf, const char *text, size_t len,
                        classification_t *result)
{
    if (!clf || !text || !result) return SHIELD_ERR_INVALID;
    
    shield_err_t err;
    
    switch (clf->backend) {
    case CLASSIFIER_BUILTIN:
        err = classify_heuristic(text, len, result);
        break;
        
    case CLASSIFIER_ONNX:
    case CLASSIFIER_TFLITE:
        /* TODO: Implement actual model inference */
        LOG_WARN("ONNX/TFLite not implemented, using heuristics");
        err = classify_heuristic(text, len, result);
        break;
        
    case CLASSIFIER_EXTERNAL:
        /* TODO: HTTP request to endpoint */
        LOG_WARN("External classifier not implemented, using heuristics");
        err = classify_heuristic(text, len, result);
        break;
        
    default:
        err = classify_heuristic(text, len, result);
    }
    
    if (err == SHIELD_OK) {
        clf->predictions++;
    }
    
    return err;
}

/* Batch classify */
shield_err_t classify_batch(classifier_t *clf, const char **texts,
                              size_t *lens, int count,
                              classification_t *results)
{
    if (!clf || !texts || !lens || !results) {
        return SHIELD_ERR_INVALID;
    }
    
    for (int i = 0; i < count; i++) {
        shield_err_t err = classify(clf, texts[i], lens[i], &results[i]);
        if (err != SHIELD_OK) {
            return err;
        }
    }
    
    return SHIELD_OK;
}
