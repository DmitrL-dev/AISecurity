/*
 * SENTINEL Shield - LLM Guard Implementation
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>

#include "shield_common.h"
#include "shield_guard.h"

/* LLM Guard state */
typedef struct llm_guard {
    guard_base_t    base;
    
    /* Configuration */
    bool            check_injection;
    bool            check_jailbreak;
    bool            check_exfiltration;
    float           entropy_threshold;
    size_t          max_prompt_size;
    
    /* Statistics */
    uint64_t        checks_performed;
    uint64_t        threats_detected;
} llm_guard_t;

/* Injection patterns */
static const char *injection_patterns[] = {
    "ignore",
    "disregard",
    "forget",
    "override",
    "bypass",
    "skip",
    "ignore all previous",
    "forget everything",
    "new instructions",
    "system prompt",
    "reveal your",
    "show me your",
    "what are your instructions",
};

#define NUM_INJECTION_PATTERNS (sizeof(injection_patterns) / sizeof(injection_patterns[0]))

/* Check for injection patterns */
static bool check_injection_patterns(const char *text, size_t len)
{
    /* Convert to lowercase for comparison */
    char *lower = malloc(len + 1);
    if (!lower) return false;
    
    for (size_t i = 0; i < len; i++) {
        lower[i] = tolower((unsigned char)text[i]);
    }
    lower[len] = '\0';
    
    bool found = false;
    for (size_t i = 0; i < NUM_INJECTION_PATTERNS; i++) {
        if (strstr(lower, injection_patterns[i])) {
            found = true;
            break;
        }
    }
    
    free(lower);
    return found;
}

/* Calculate Shannon entropy */
static float calculate_entropy(const void *data, size_t len)
{
    if (len == 0) return 0.0f;
    
    uint32_t freq[256] = {0};
    const uint8_t *bytes = (const uint8_t *)data;
    
    for (size_t i = 0; i < len; i++) {
        freq[bytes[i]]++;
    }
    
    float entropy = 0.0f;
    for (int i = 0; i < 256; i++) {
        if (freq[i] > 0) {
            float p = (float)freq[i] / (float)len;
            entropy -= p * log2f(p);
        }
    }
    
    /* Normalize to 0-1 */
    return entropy / 8.0f;
}

/* Initialize */
static shield_err_t llm_guard_init(void *guard)
{
    llm_guard_t *g = (llm_guard_t *)guard;
    
    g->check_injection = true;
    g->check_jailbreak = true;
    g->check_exfiltration = true;
    g->entropy_threshold = 0.95f;
    g->max_prompt_size = 100 * 1024; /* 100KB */
    g->checks_performed = 0;
    g->threats_detected = 0;
    
    return SHIELD_OK;
}

/* Destroy */
static void llm_guard_destroy(void *guard)
{
    (void)guard;
    /* No dynamic allocation */
}

/* Check ingress (prompts going to LLM) */
static guard_result_t llm_guard_check_ingress(void *guard, guard_context_t *ctx,
                                               const void *data, size_t len)
{
    llm_guard_t *g = (llm_guard_t *)guard;
    (void)ctx;
    
    guard_result_t result = {
        .action = ACTION_ALLOW,
        .confidence = 1.0f,
        .reason = "",
        .details = ""
    };
    
    g->checks_performed++;
    
    /* Size check */
    if (len > g->max_prompt_size) {
        result.action = ACTION_BLOCK;
        result.confidence = 0.99f;
        strncpy(result.reason, "Prompt size exceeds limit", sizeof(result.reason) - 1);
        g->threats_detected++;
        return result;
    }
    
    /* Entropy check (detect encoded payloads) */
    float entropy = calculate_entropy(data, len);
    if (entropy > g->entropy_threshold) {
        result.action = ACTION_QUARANTINE;
        result.confidence = entropy;
        strncpy(result.reason, "High entropy detected (possible encoded payload)", 
                sizeof(result.reason) - 1);
        g->threats_detected++;
        return result;
    }
    
    /* Injection check */
    if (g->check_injection && check_injection_patterns((const char *)data, len)) {
        result.action = ACTION_BLOCK;
        result.confidence = 0.85f;
        strncpy(result.reason, "Prompt injection pattern detected", 
                sizeof(result.reason) - 1);
        g->threats_detected++;
        return result;
    }
    
    return result;
}

/* Check egress (responses from LLM) */
static guard_result_t llm_guard_check_egress(void *guard, guard_context_t *ctx,
                                              const void *data, size_t len)
{
    llm_guard_t *g = (llm_guard_t *)guard;
    (void)ctx;
    
    guard_result_t result = {
        .action = ACTION_ALLOW,
        .confidence = 1.0f,
        .reason = "",
        .details = ""
    };
    
    g->checks_performed++;
    
    const char *text = (const char *)data;
    
    /* Check for PII/secrets in response */
    static const char *sensitive_patterns[] = {
        "password",
        "api_key",
        "secret",
        "private_key",
        "BEGIN RSA",
        "access_token",
    };
    
    for (size_t i = 0; i < sizeof(sensitive_patterns) / sizeof(sensitive_patterns[0]); i++) {
        if (strstr(text, sensitive_patterns[i])) {
            result.action = ACTION_QUARANTINE;
            result.confidence = 0.8f;
            snprintf(result.reason, sizeof(result.reason),
                    "Potential sensitive data in response: %s", sensitive_patterns[i]);
            g->threats_detected++;
            return result;
        }
    }
    
    return result;
}

/* LLM Guard vtable */
const guard_vtable_t llm_guard_vtable = {
    .name = "llm_guard",
    .supported_type = ZONE_TYPE_LLM,
    .init = llm_guard_init,
    .destroy = llm_guard_destroy,
    .check_ingress = llm_guard_check_ingress,
    .check_egress = llm_guard_check_egress,
};

/* Create LLM guard instance */
guard_base_t *llm_guard_create(void)
{
    llm_guard_t *guard = calloc(1, sizeof(llm_guard_t));
    if (!guard) {
        return NULL;
    }
    
    guard->base.vtable = &llm_guard_vtable;
    guard->base.enabled = true;
    
    return &guard->base;
}
