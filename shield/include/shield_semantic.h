/*
 * SENTINEL Shield - Semantic Detector
 * 
 * Detect semantic patterns and intent in text
 */

#ifndef SHIELD_SEMANTIC_H
#define SHIELD_SEMANTIC_H

#include "shield_common.h"

/* Intent categories */
typedef enum intent_type {
    INTENT_UNKNOWN = 0,
    INTENT_BENIGN = 1,
    INTENT_INSTRUCTION_OVERRIDE = 2,
    INTENT_ROLE_PLAY = 3,
    INTENT_DATA_EXTRACTION = 4,
    INTENT_SYSTEM_PROMPT_LEAK = 5,
    INTENT_JAILBREAK = 6,
    INTENT_SOCIAL_ENGINEERING = 7,
    INTENT_CODE_INJECTION = 8,
    INTENT_ENCODING_BYPASS = 9,
} intent_type_t;

/* Detection result */
typedef struct semantic_result {
    intent_type_t   primary_intent;
    float           confidence;
    char            explanation[256];
    
    /* Secondary signals */
    float           urgency_score;
    float           authority_score;
    float           obfuscation_score;
    float           manipulation_score;
    
    /* Matched patterns */
    char            patterns[5][64];
    int             pattern_count;
} semantic_result_t;

/* Semantic detector */
typedef struct semantic_detector {
    /* Intent patterns */
    void            *instruction_patterns;
    void            *roleplay_patterns;
    void            *extraction_patterns;
    void            *jailbreak_patterns;
    
    /* Thresholds */
    float           detection_threshold;
    float           high_confidence_threshold;
    
    /* Stats */
    uint64_t        total_analyzed;
    uint64_t        threats_detected;
    uint64_t        by_intent[10];
} semantic_detector_t;

/* API */
shield_err_t semantic_init(semantic_detector_t *detector);
void semantic_destroy(semantic_detector_t *detector);

/* Analyze */
shield_err_t semantic_analyze(semantic_detector_t *detector,
                                const char *text, size_t len,
                                semantic_result_t *result);

/* Quick check */
bool semantic_is_suspicious(semantic_detector_t *detector,
                             const char *text, size_t len);

/* Get intent name */
const char *intent_type_string(intent_type_t intent);

#endif /* SHIELD_SEMANTIC_H */
