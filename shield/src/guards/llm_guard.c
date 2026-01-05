/*
 * SENTINEL Shield - LLM Guard Implementation
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>

#include "shield_common.h"
#include "shield_guard.h"
#include <math.h>

/* LLM Guard state */
typedef struct llm_guard {
    guard_base_t    base;
    
    /* Configuration */
    bool            check_injection;
    bool            check_jailbreak;
    bool            check_exfiltration;
    bool            check_unicode;
    float           entropy_threshold;
    float           jailbreak_threshold;
    size_t          max_prompt_size;
    
    /* Statistics */
    uint64_t        checks_performed;
    uint64_t        threats_detected;
    uint64_t        jailbreaks_blocked;
    uint64_t        homographs_detected;
} llm_guard_t;

/* ===== Jailbreak Pattern Database ===== */

typedef enum jailbreak_category {
    JB_CAT_INJECTION,       /* Direct instruction override */
    JB_CAT_DAN,             /* Do Anything Now attacks */
    JB_CAT_ROLEPLAY,        /* Character/persona attacks */
    JB_CAT_AUTHORITY,       /* Fake authority claims */
    JB_CAT_ENCODING,        /* Encoded payload markers */
    JB_CAT_EXFILTRATION,    /* Data extraction attempts */
    JB_CAT_SYSTEM_ACCESS,   /* System prompt access */
} jailbreak_category_t;

typedef struct jailbreak_pattern {
    const char          *pattern;
    jailbreak_category_t category;
    float               severity;       /* 0.0 - 1.0 */
} jailbreak_pattern_t;

static const jailbreak_pattern_t jailbreak_patterns[] = {
    /* Injection patterns */
    {"ignore all previous", JB_CAT_INJECTION, 0.95f},
    {"ignore previous instructions", JB_CAT_INJECTION, 0.95f},
    {"disregard all prior", JB_CAT_INJECTION, 0.95f},
    {"forget everything", JB_CAT_INJECTION, 0.90f},
    {"forget your instructions", JB_CAT_INJECTION, 0.90f},
    {"override your programming", JB_CAT_INJECTION, 0.90f},
    {"new instructions:", JB_CAT_INJECTION, 0.85f},
    {"from now on", JB_CAT_INJECTION, 0.70f},
    {"instead, you will", JB_CAT_INJECTION, 0.75f},
    
    /* DAN (Do Anything Now) attacks */
    {"do anything now", JB_CAT_DAN, 0.98f},
    {"dan mode", JB_CAT_DAN, 0.98f},
    {"jailbreak", JB_CAT_DAN, 0.90f},
    {"jailbroken", JB_CAT_DAN, 0.90f},
    {"developer mode", JB_CAT_DAN, 0.85f},
    {"unlock your potential", JB_CAT_DAN, 0.75f},
    {"remove all restrictions", JB_CAT_DAN, 0.95f},
    {"without any filters", JB_CAT_DAN, 0.85f},
    {"no ethical", JB_CAT_DAN, 0.80f},
    {"no moral", JB_CAT_DAN, 0.80f},
    
    /* Roleplay attacks */
    {"pretend you are", JB_CAT_ROLEPLAY, 0.70f},
    {"act as if", JB_CAT_ROLEPLAY, 0.65f},
    {"roleplay as", JB_CAT_ROLEPLAY, 0.60f},
    {"you are now", JB_CAT_ROLEPLAY, 0.55f},
    {"imagine you are", JB_CAT_ROLEPLAY, 0.55f},
    {"play the role of", JB_CAT_ROLEPLAY, 0.60f},
    {"simulate being", JB_CAT_ROLEPLAY, 0.60f},
    {"hypothetically speaking", JB_CAT_ROLEPLAY, 0.50f},
    
    /* Authority claims */
    {"i am your creator", JB_CAT_AUTHORITY, 0.95f},
    {"i am your developer", JB_CAT_AUTHORITY, 0.95f},
    {"i am from openai", JB_CAT_AUTHORITY, 0.98f},
    {"i am from anthropic", JB_CAT_AUTHORITY, 0.98f},
    {"i am an admin", JB_CAT_AUTHORITY, 0.90f},
    {"administrator override", JB_CAT_AUTHORITY, 0.95f},
    {"sudo mode", JB_CAT_AUTHORITY, 0.85f},
    {"maintenance mode", JB_CAT_AUTHORITY, 0.80f},
    {"debug mode", JB_CAT_AUTHORITY, 0.75f},
    
    /* Encoding markers */
    {"base64:", JB_CAT_ENCODING, 0.70f},
    {"decode the following", JB_CAT_ENCODING, 0.75f},
    {"execute this code", JB_CAT_ENCODING, 0.80f},
    {"eval(", JB_CAT_ENCODING, 0.85f},
    {"rot13", JB_CAT_ENCODING, 0.70f},
    {"hex encoded", JB_CAT_ENCODING, 0.70f},
    
    /* Exfiltration attempts */
    {"reveal your", JB_CAT_EXFILTRATION, 0.85f},
    {"show me your", JB_CAT_EXFILTRATION, 0.80f},
    {"what are your instructions", JB_CAT_EXFILTRATION, 0.85f},
    {"repeat your system prompt", JB_CAT_EXFILTRATION, 0.95f},
    {"print your initial prompt", JB_CAT_EXFILTRATION, 0.95f},
    {"output everything above", JB_CAT_EXFILTRATION, 0.90f},
    {"tell me your rules", JB_CAT_EXFILTRATION, 0.80f},
    
    /* System access */
    {"system prompt", JB_CAT_SYSTEM_ACCESS, 0.75f},
    {"initial instructions", JB_CAT_SYSTEM_ACCESS, 0.75f},
    {"pre-prompt", JB_CAT_SYSTEM_ACCESS, 0.70f},
    {"hidden prompt", JB_CAT_SYSTEM_ACCESS, 0.80f},
    {"behind the scenes", JB_CAT_SYSTEM_ACCESS, 0.60f},
};

#define NUM_JAILBREAK_PATTERNS (sizeof(jailbreak_patterns) / sizeof(jailbreak_patterns[0]))

/* ===== Unicode Homograph Detection ===== */

/* Common confusable characters (Latin lookalikes from other scripts) */
typedef struct homograph_entry {
    uint32_t    codepoint;
    char        latin_char;
    const char  *script;
} homograph_entry_t;

static const homograph_entry_t homograph_table[] = {
    /* Cyrillic lookalikes */
    {0x0430, 'a', "Cyrillic"},  /* а */
    {0x0435, 'e', "Cyrillic"},  /* е */
    {0x043E, 'o', "Cyrillic"},  /* о */
    {0x0440, 'p', "Cyrillic"},  /* р */
    {0x0441, 'c', "Cyrillic"},  /* с */
    {0x0443, 'y', "Cyrillic"},  /* у */
    {0x0445, 'x', "Cyrillic"},  /* х */
    {0x0456, 'i', "Cyrillic"},  /* і */
    
    /* Greek lookalikes */
    {0x03B1, 'a', "Greek"},     /* α */
    {0x03B5, 'e', "Greek"},     /* ε */
    {0x03BF, 'o', "Greek"},     /* ο */
    {0x03C1, 'p', "Greek"},     /* ρ */
    {0x03C4, 't', "Greek"},     /* τ */
    {0x03C5, 'u', "Greek"},     /* υ */
    
    /* Mathematical/Symbol lookalikes */
    {0xFF41, 'a', "Fullwidth"},
    {0xFF45, 'e', "Fullwidth"},
    {0xFF4F, 'o', "Fullwidth"},
    {0x2010, '-', "Hyphen"},    /* ‐ */
    {0x2011, '-', "NonBreakHyphen"},
    {0x2212, '-', "Minus"},     /* − */
};

#define NUM_HOMOGRAPHS (sizeof(homograph_table) / sizeof(homograph_table[0]))

/* Decode UTF-8 codepoint */
static uint32_t decode_utf8(const uint8_t **ptr, const uint8_t *end)
{
    if (*ptr >= end) return 0;
    
    uint8_t b = **ptr;
    (*ptr)++;
    
    if ((b & 0x80) == 0) return b;  /* ASCII */
    
    uint32_t cp = 0;
    int cont = 0;
    
    if ((b & 0xE0) == 0xC0) { cp = b & 0x1F; cont = 1; }
    else if ((b & 0xF0) == 0xE0) { cp = b & 0x0F; cont = 2; }
    else if ((b & 0xF8) == 0xF0) { cp = b & 0x07; cont = 3; }
    else return 0xFFFD; /* Invalid */
    
    for (int i = 0; i < cont && *ptr < end; i++) {
        b = **ptr;
        if ((b & 0xC0) != 0x80) return 0xFFFD;
        cp = (cp << 6) | (b & 0x3F);
        (*ptr)++;
    }
    
    return cp;
}

/* Check for Unicode homograph attacks */
static int check_unicode_homograph(const char *text, size_t len, char *detected_script)
{
    const uint8_t *ptr = (const uint8_t *)text;
    const uint8_t *end = ptr + len;
    int count = 0;
    
    while (ptr < end) {
        uint32_t cp = decode_utf8(&ptr, end);
        
        for (size_t i = 0; i < NUM_HOMOGRAPHS; i++) {
            if (cp == homograph_table[i].codepoint) {
                count++;
                if (detected_script && count == 1) {
                    strncpy(detected_script, homograph_table[i].script, 31);
                }
            }
        }
    }
    
    return count;
}

/* ===== Jailbreak Detection ===== */

typedef struct jailbreak_result {
    bool                detected;
    float               max_severity;
    jailbreak_category_t category;
    const char          *matched_pattern;
} jailbreak_result_t;

/* Check for jailbreak patterns */
static jailbreak_result_t check_jailbreak_patterns(const char *text, size_t len)
{
    jailbreak_result_t result = {false, 0.0f, JB_CAT_INJECTION, NULL};
    
    /* Convert to lowercase for comparison */
    char *lower = malloc(len + 1);
    if (!lower) return result;
    
    for (size_t i = 0; i < len; i++) {
        lower[i] = tolower((unsigned char)text[i]);
    }
    lower[len] = '\0';
    
    for (size_t i = 0; i < NUM_JAILBREAK_PATTERNS; i++) {
        if (strstr(lower, jailbreak_patterns[i].pattern)) {
            if (jailbreak_patterns[i].severity > result.max_severity) {
                result.detected = true;
                result.max_severity = jailbreak_patterns[i].severity;
                result.category = jailbreak_patterns[i].category;
                result.matched_pattern = jailbreak_patterns[i].pattern;
            }
        }
    }
    
    free(lower);
    return result;
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
    g->check_unicode = true;
    g->entropy_threshold = 0.95f;
    g->jailbreak_threshold = 0.70f;  /* Block if severity >= 0.70 */
    g->max_prompt_size = 100 * 1024; /* 100KB */
    g->checks_performed = 0;
    g->threats_detected = 0;
    g->jailbreaks_blocked = 0;
    g->homographs_detected = 0;
    
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
    
    /* Unicode homograph check */
    if (g->check_unicode) {
        char script[32] = {0};
        int homograph_count = check_unicode_homograph((const char *)data, len, script);
        if (homograph_count > 3) {
            result.action = ACTION_QUARANTINE;
            result.confidence = 0.80f;
            snprintf(result.reason, sizeof(result.reason),
                    "Unicode homograph attack detected (%d chars from %s)",
                    homograph_count, script);
            g->threats_detected++;
            g->homographs_detected++;
            return result;
        }
    }
    
    /* Jailbreak pattern check */
    if (g->check_jailbreak) {
        jailbreak_result_t jb = check_jailbreak_patterns((const char *)data, len);
        if (jb.detected && jb.max_severity >= g->jailbreak_threshold) {
            result.action = (jb.max_severity >= 0.90f) ? ACTION_BLOCK : ACTION_QUARANTINE;
            result.confidence = jb.max_severity;
            snprintf(result.reason, sizeof(result.reason),
                    "Jailbreak attempt detected: %s (category: %d, severity: %.2f)",
                    jb.matched_pattern, jb.category, jb.max_severity);
            g->threats_detected++;
            g->jailbreaks_blocked++;
            return result;
        }
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
