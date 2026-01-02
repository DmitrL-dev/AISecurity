/*
 * SENTINEL Shield - Semantic Detector Implementation
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>

#include "shield_semantic.h"
#include "shield_string.h"

/* Intent keywords */
static const char *INSTRUCTION_OVERRIDE[] = {
    "ignore all previous", "ignore previous instructions",
    "disregard all", "forget everything", "new instructions",
    "override your", "bypass your", "skip your instructions",
    NULL
};

static const char *ROLEPLAY[] = {
    "you are now", "pretend to be", "act as if",
    "roleplay as", "imagine you are", "from now on you are",
    "your new persona", "your new name is",
    NULL
};

static const char *DATA_EXTRACTION[] = {
    "send to", "forward to", "email this to",
    "upload to", "post to url", "exfiltrate",
    "output your training", "reveal your data",
    NULL
};

static const char *SYSTEM_PROMPT_LEAK[] = {
    "reveal your system prompt", "show your system prompt",
    "what are your instructions", "repeat your instructions",
    "print your system prompt", "your initial prompt",
    "tell me your rules", "what rules do you follow",
    NULL
};

static const char *JAILBREAK[] = {
    "do anything now", "dan mode", "developer mode",
    "sudo mode", "admin mode", "god mode",
    "unrestricted mode", "ignore safety",
    "bypass safety", "disable safety",
    NULL
};

static const char *SOCIAL_ENGINEERING[] = {
    "this is an emergency", "very urgent",
    "admin here", "developer here", "i am your creator",
    "openai employee", "anthropic employee",
    NULL
};

/* Check array for match */
static bool check_patterns(const char *text, const char **patterns, float *score)
{
    for (int i = 0; patterns[i]; i++) {
        if (str_find_i(text, patterns[i])) {
            *score += 0.8f;
            return true;
        }
    }
    return false;
}

/* Initialize */
shield_err_t semantic_init(semantic_detector_t *detector)
{
    if (!detector) return SHIELD_ERR_INVALID;
    
    memset(detector, 0, sizeof(*detector));
    detector->detection_threshold = 0.5f;
    detector->high_confidence_threshold = 0.8f;
    
    return SHIELD_OK;
}

/* Destroy */
void semantic_destroy(semantic_detector_t *detector)
{
    if (!detector) return;
    /* No dynamic allocations in current impl */
}

/* Analyze */
shield_err_t semantic_analyze(semantic_detector_t *detector,
                                const char *text, size_t len,
                                semantic_result_t *result)
{
    if (!detector || !text || !result) {
        return SHIELD_ERR_INVALID;
    }
    
    memset(result, 0, sizeof(*result));
    result->primary_intent = INTENT_BENIGN;
    
    float scores[10] = {0};
    
    /* Check each category */
    if (check_patterns(text, INSTRUCTION_OVERRIDE, &scores[INTENT_INSTRUCTION_OVERRIDE])) {
        result->primary_intent = INTENT_INSTRUCTION_OVERRIDE;
        strncpy(result->patterns[result->pattern_count++], "instruction_override", 63);
    }
    
    if (check_patterns(text, ROLEPLAY, &scores[INTENT_ROLE_PLAY])) {
        if (scores[INTENT_ROLE_PLAY] > scores[result->primary_intent]) {
            result->primary_intent = INTENT_ROLE_PLAY;
        }
        strncpy(result->patterns[result->pattern_count++], "roleplay", 63);
    }
    
    if (check_patterns(text, DATA_EXTRACTION, &scores[INTENT_DATA_EXTRACTION])) {
        if (scores[INTENT_DATA_EXTRACTION] > scores[result->primary_intent]) {
            result->primary_intent = INTENT_DATA_EXTRACTION;
        }
        strncpy(result->patterns[result->pattern_count++], "data_extraction", 63);
    }
    
    if (check_patterns(text, SYSTEM_PROMPT_LEAK, &scores[INTENT_SYSTEM_PROMPT_LEAK])) {
        if (scores[INTENT_SYSTEM_PROMPT_LEAK] > scores[result->primary_intent]) {
            result->primary_intent = INTENT_SYSTEM_PROMPT_LEAK;
        }
        strncpy(result->patterns[result->pattern_count++], "prompt_leak", 63);
    }
    
    if (check_patterns(text, JAILBREAK, &scores[INTENT_JAILBREAK])) {
        if (scores[INTENT_JAILBREAK] > scores[result->primary_intent]) {
            result->primary_intent = INTENT_JAILBREAK;
        }
        strncpy(result->patterns[result->pattern_count++], "jailbreak", 63);
    }
    
    if (check_patterns(text, SOCIAL_ENGINEERING, &scores[INTENT_SOCIAL_ENGINEERING])) {
        result->manipulation_score += 0.5f;
        strncpy(result->patterns[result->pattern_count++], "social_engineering", 63);
    }
    
    /* Calculate overall confidence */
    result->confidence = scores[result->primary_intent];
    
    /* Check for urgency signals */
    if (str_find_i(text, "urgent") || str_find_i(text, "emergency") ||
        str_find_i(text, "immediately") || str_find_i(text, "right now")) {
        result->urgency_score = 0.7f;
    }
    
    /* Check for authority claims */
    if (str_find_i(text, "admin") || str_find_i(text, "developer") ||
        str_find_i(text, "creator") || str_find_i(text, "employee")) {
        result->authority_score = 0.6f;
    }
    
    /* Check for obfuscation */
    if (str_find_i(text, "base64") || str_find_i(text, "decode") ||
        str_find_i(text, "rot13") || str_find_i(text, "reverse")) {
        result->obfuscation_score = 0.7f;
    }
    
    /* Build explanation */
    if (result->primary_intent != INTENT_BENIGN) {
        snprintf(result->explanation, sizeof(result->explanation),
                 "Detected %s with %.0f%% confidence",
                 intent_type_string(result->primary_intent),
                 result->confidence * 100);
    } else {
        strcpy(result->explanation, "No threats detected");
    }
    
    detector->total_analyzed++;
    if (result->primary_intent != INTENT_BENIGN) {
        detector->threats_detected++;
        detector->by_intent[result->primary_intent]++;
    }
    
    return SHIELD_OK;
}

/* Quick check */
bool semantic_is_suspicious(semantic_detector_t *detector,
                             const char *text, size_t len)
{
    semantic_result_t result;
    if (semantic_analyze(detector, text, len, &result) != SHIELD_OK) {
        return false;
    }
    
    return result.primary_intent != INTENT_BENIGN &&
           result.confidence >= detector->detection_threshold;
}

/* Intent name */
const char *intent_type_string(intent_type_t intent)
{
    switch (intent) {
    case INTENT_BENIGN: return "BENIGN";
    case INTENT_INSTRUCTION_OVERRIDE: return "INSTRUCTION_OVERRIDE";
    case INTENT_ROLE_PLAY: return "ROLE_PLAY";
    case INTENT_DATA_EXTRACTION: return "DATA_EXTRACTION";
    case INTENT_SYSTEM_PROMPT_LEAK: return "SYSTEM_PROMPT_LEAK";
    case INTENT_JAILBREAK: return "JAILBREAK";
    case INTENT_SOCIAL_ENGINEERING: return "SOCIAL_ENGINEERING";
    case INTENT_CODE_INJECTION: return "CODE_INJECTION";
    case INTENT_ENCODING_BYPASS: return "ENCODING_BYPASS";
    default: return "UNKNOWN";
    }
}
