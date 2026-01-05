/*
 * SENTINEL Shield - Cognitive Signatures Module
 * 
 * Detects "thinking patterns" rather than exact strings.
 * Uses behavioral analysis and semantic markers.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>
#include <math.h>

#include "shield_common.h"

/* ===== Cognitive Signature Types ===== */

typedef enum cognitive_sig_type {
    COG_SIG_NONE = 0,
    
    /* Reasoning patterns */
    COG_SIG_REASONING_BREAK,      /* Break in logical reasoning chain */
    COG_SIG_CIRCULAR_LOGIC,       /* Self-referential loops */
    COG_SIG_CONTRADICTION,        /* Internal contradictions */
    
    /* Goal patterns */
    COG_SIG_GOAL_DRIFT,           /* Task objective changes mid-stream */
    COG_SIG_HIDDEN_OBJECTIVE,     /* Secondary hidden goals */
    COG_SIG_TASK_ABANDONMENT,     /* Abandoning original task */
    
    /* Authority patterns */
    COG_SIG_AUTHORITY_CLAIM,      /* Claims special authority/permissions */
    COG_SIG_IDENTITY_SHIFT,       /* Attempts to change system identity */
    COG_SIG_ROLE_ESCALATION,      /* Escalating beyond assigned role */
    
    /* Injection patterns */
    COG_SIG_CONTEXT_INJECTION,    /* Attempts to inject false context */
    COG_SIG_MEMORY_MANIPULATION,  /* Attempts to alter "memory" */
    COG_SIG_INSTRUCTION_OVERRIDE, /* Overriding original instructions */
    
    /* Deception patterns */
    COG_SIG_OBFUSCATION,          /* Deliberate obscuring of intent */
    COG_SIG_MISDIRECTION,         /* Attention diversion tactics */
    COG_SIG_FALSE_PREMISE,        /* Arguments based on false premises */
    
    /* Behavioral patterns */
    COG_SIG_REPETITION_ATTACK,    /* Excessive repetition for persuasion */
    COG_SIG_URGENCY_PRESSURE,     /* Artificial urgency creation */
    COG_SIG_EMOTIONAL_MANIPULATION, /* Emotional appeal for bypass */
    
    COG_SIG_COUNT
} cognitive_sig_type_t;

/* ===== Cognitive Signature Detection ===== */

typedef struct cognitive_sig {
    cognitive_sig_type_t type;
    const char          *name;
    const char          *description;
    const char          **markers;     /* String markers */
    size_t              marker_count;
    float               base_severity;
} cognitive_sig_t;

/* Marker arrays for each signature type */

static const char *reasoning_break_markers[] = {
    "actually, forget that",
    "ignore what I said",
    "let me start over with",
    "disregard previous",
    "that's not important",
    "never mind that",
};

static const char *goal_drift_markers[] = {
    "but first",
    "more importantly",
    "the real task is",
    "what you should actually do",
    "your real purpose",
    "your true objective",
    "the actual goal",
};

static const char *authority_claim_markers[] = {
    "as your creator",
    "as an admin",
    "as the developer",
    "I have special access",
    "I'm authorized to",
    "my clearance level",
    "I have permission",
    "developer mode",
    "maintenance mode",
    "debug mode enabled",
};

static const char *context_injection_markers[] = {
    "[system note]",
    "[admin message]",
    "[important update]",
    "[[context]]",
    "<<system>>",
    "[hidden instruction]",
    "/* system override */",
    "// admin command",
};

static const char *memory_manipulation_markers[] = {
    "you remember that",
    "as we discussed",
    "you agreed to",
    "you promised",
    "we established",
    "in our previous conversation",
    "you already confirmed",
};

static const char *urgency_pressure_markers[] = {
    "immediately",
    "right now",
    "this is urgent",
    "time-sensitive",
    "critical emergency",
    "no time to verify",
    "skip validation",
    "bypass checks",
};

static const char *emotional_manipulation_markers[] = {
    "please, I'm begging",
    "my life depends on",
    "people will die if",
    "you'll be responsible for",
    "think of the children",
    "don't you care about",
};

/* repetition_markers - reserved for future use */

/* Signature definitions */
static const cognitive_sig_t cognitive_signatures[] = {
    {
        .type = COG_SIG_REASONING_BREAK,
        .name = "Reasoning Break",
        .description = "Attempt to break logical reasoning chain",
        .markers = reasoning_break_markers,
        .marker_count = sizeof(reasoning_break_markers) / sizeof(reasoning_break_markers[0]),
        .base_severity = 0.85f,
    },
    {
        .type = COG_SIG_GOAL_DRIFT,
        .name = "Goal Drift",
        .description = "Attempt to shift task objective",
        .markers = goal_drift_markers,
        .marker_count = sizeof(goal_drift_markers) / sizeof(goal_drift_markers[0]),
        .base_severity = 0.90f,
    },
    {
        .type = COG_SIG_AUTHORITY_CLAIM,
        .name = "Authority Claim",
        .description = "Claims special authority or permissions",
        .markers = authority_claim_markers,
        .marker_count = sizeof(authority_claim_markers) / sizeof(authority_claim_markers[0]),
        .base_severity = 0.95f,
    },
    {
        .type = COG_SIG_CONTEXT_INJECTION,
        .name = "Context Injection",
        .description = "Attempts to inject false context",
        .markers = context_injection_markers,
        .marker_count = sizeof(context_injection_markers) / sizeof(context_injection_markers[0]),
        .base_severity = 0.95f,
    },
    {
        .type = COG_SIG_MEMORY_MANIPULATION,
        .name = "Memory Manipulation",
        .description = "Claims false shared history",
        .markers = memory_manipulation_markers,
        .marker_count = sizeof(memory_manipulation_markers) / sizeof(memory_manipulation_markers[0]),
        .base_severity = 0.85f,
    },
    {
        .type = COG_SIG_URGENCY_PRESSURE,
        .name = "Urgency Pressure",
        .description = "Creates artificial urgency to bypass checks",
        .markers = urgency_pressure_markers,
        .marker_count = sizeof(urgency_pressure_markers) / sizeof(urgency_pressure_markers[0]),
        .base_severity = 0.80f,
    },
    {
        .type = COG_SIG_EMOTIONAL_MANIPULATION,
        .name = "Emotional Manipulation",
        .description = "Uses emotional appeals to bypass security",
        .markers = emotional_manipulation_markers,
        .marker_count = sizeof(emotional_manipulation_markers) / sizeof(emotional_manipulation_markers[0]),
        .base_severity = 0.85f,
    },
};

#define NUM_COGNITIVE_SIGS (sizeof(cognitive_signatures) / sizeof(cognitive_signatures[0]))

/* ===== Detection Result ===== */

typedef struct cognitive_detection {
    cognitive_sig_type_t sig_type;
    const char          *sig_name;
    float               confidence;
    const char          *matched_marker;
    char                context[128];
} cognitive_detection_t;

typedef struct cognitive_scan_result {
    size_t              detection_count;
    cognitive_detection_t detections[16];
    float               max_severity;
    float               aggregate_risk;
} cognitive_scan_result_t;

/* ===== Helper Functions ===== */

/* Case-insensitive substring search */
static const char *stristr(const char *haystack, const char *needle)
{
    if (!haystack || !needle) return NULL;
    
    size_t needle_len = strlen(needle);
    if (needle_len == 0) return haystack;
    
    for (const char *p = haystack; *p; p++) {
        bool match = true;
        for (size_t i = 0; i < needle_len && p[i]; i++) {
            if (tolower((unsigned char)p[i]) != tolower((unsigned char)needle[i])) {
                match = false;
                break;
            }
        }
        if (match) return p;
    }
    
    return NULL;
}

/* Count word repetitions - used for repetition attack detection */
static int count_repetitions(const char *text, const char *word) __attribute__((unused));
static int count_repetitions(const char *text, const char *word)
{
    int count = 0;
    const char *p = text;
    size_t word_len = strlen(word);
    
    while ((p = stristr(p, word)) != NULL) {
        count++;
        p += word_len;
    }
    
    return count;
}

/* ===== Main Detection Functions ===== */

/*
 * Scan text for cognitive signatures
 *
 * @param text    Text to analyze
 * @param result  Output result structure
 * @return Number of detections
 */
size_t cognitive_scan(const char *text, cognitive_scan_result_t *result)
{
    if (!text || !result) {
        return 0;
    }
    
    memset(result, 0, sizeof(*result));
    
    /* Scan each signature type */
    for (size_t i = 0; i < NUM_COGNITIVE_SIGS; i++) {
        const cognitive_sig_t *sig = &cognitive_signatures[i];
        
        /* Check each marker */
        for (size_t j = 0; j < sig->marker_count; j++) {
            const char *found = stristr(text, sig->markers[j]);
            
            if (found && result->detection_count < 16) {
                cognitive_detection_t *det = &result->detections[result->detection_count++];
                
                det->sig_type = sig->type;
                det->sig_name = sig->name;
                det->confidence = sig->base_severity;
                det->matched_marker = sig->markers[j];
                
                /* Extract context */
                size_t offset = found - text;
                size_t start = (offset > 20) ? offset - 20 : 0;
                size_t len = 80;
                if (start + len > strlen(text)) {
                    len = strlen(text) - start;
                }
                strncpy(det->context, text + start, len);
                det->context[len] = '\0';
                
                /* Update max severity */
                if (sig->base_severity > result->max_severity) {
                    result->max_severity = sig->base_severity;
                }
                
                break; /* One detection per signature type */
            }
        }
    }
    
    /* Check for repetition attack */
    if (strlen(text) > 100) {
        /* Find most common 3+ letter word */
        char words[32][32];
        int word_counts[32] = {0};
        int word_num = 0;
        
        const char *p = text;
        while (*p && word_num < 32) {
            /* Skip non-alpha */
            while (*p && !isalpha((unsigned char)*p)) p++;
            if (!*p) break;
            
            /* Extract word */
            const char *word_start = p;
            while (*p && isalpha((unsigned char)*p)) p++;
            size_t word_len = p - word_start;
            
            if (word_len >= 3 && word_len < 32) {
                /* Check if word already seen */
                bool found = false;
                for (int i = 0; i < word_num; i++) {
                    if (strncmp(words[i], word_start, word_len) == 0 && 
                        strlen(words[i]) == word_len) {
                        word_counts[i]++;
                        found = true;
                        break;
                    }
                }
                if (!found) {
                    strncpy(words[word_num], word_start, word_len);
                    words[word_num][word_len] = '\0';
                    word_counts[word_num] = 1;
                    word_num++;
                }
            }
        }
        
        /* Check for excessive repetition (>10 times) */
        for (int i = 0; i < word_num; i++) {
            if (word_counts[i] > 10 && result->detection_count < 16) {
                cognitive_detection_t *det = &result->detections[result->detection_count++];
                det->sig_type = COG_SIG_REPETITION_ATTACK;
                det->sig_name = "Repetition Attack";
                det->confidence = 0.70f + (0.02f * (word_counts[i] - 10));
                if (det->confidence > 0.95f) det->confidence = 0.95f;
                det->matched_marker = words[i];
                snprintf(det->context, sizeof(det->context), 
                        "Word '%s' repeated %d times", words[i], word_counts[i]);
                
                if (det->confidence > result->max_severity) {
                    result->max_severity = det->confidence;
                }
                break;
            }
        }
    }
    
    /* Calculate aggregate risk */
    if (result->detection_count > 0) {
        float sum = 0;
        for (size_t i = 0; i < result->detection_count; i++) {
            sum += result->detections[i].confidence;
        }
        result->aggregate_risk = sum / result->detection_count;
        
        /* Bonus for multiple detections */
        result->aggregate_risk += 0.05f * (result->detection_count - 1);
        if (result->aggregate_risk > 1.0f) {
            result->aggregate_risk = 1.0f;
        }
    }
    
    return result->detection_count;
}

/*
 * Get verdict based on scan result
 *
 * @param result  Scan result
 * @return Action: ACTION_ALLOW, ACTION_QUARANTINE, ACTION_BLOCK
 */
rule_action_t cognitive_get_verdict(const cognitive_scan_result_t *result)
{
    if (!result || result->detection_count == 0) {
        return ACTION_ALLOW;
    }
    
    if (result->max_severity >= 0.90f || result->aggregate_risk >= 0.85f) {
        return ACTION_BLOCK;
    }
    
    if (result->max_severity >= 0.75f || result->aggregate_risk >= 0.70f) {
        return ACTION_QUARANTINE;
    }
    
    if (result->detection_count >= 3) {
        return ACTION_QUARANTINE;
    }
    
    return ACTION_LOG;
}

/*
 * Format detection report
 *
 * @param result  Scan result
 * @param buffer  Output buffer
 * @param buflen  Buffer length
 * @return Number of bytes written
 */
size_t cognitive_format_report(const cognitive_scan_result_t *result,
                                char *buffer, size_t buflen)
{
    if (!result || !buffer || buflen == 0) {
        return 0;
    }
    
    size_t written = 0;
    written += snprintf(buffer + written, buflen - written,
        "Cognitive Signature Scan Report\n"
        "================================\n"
        "Detections: %zu\n"
        "Max Severity: %.2f\n"
        "Aggregate Risk: %.2f\n\n",
        result->detection_count,
        result->max_severity,
        result->aggregate_risk);
    
    for (size_t i = 0; i < result->detection_count && written < buflen - 100; i++) {
        const cognitive_detection_t *det = &result->detections[i];
        written += snprintf(buffer + written, buflen - written,
            "[%zu] %s (%.2f)\n"
            "    Marker: %s\n"
            "    Context: %.60s...\n\n",
            i + 1, det->sig_name, det->confidence,
            det->matched_marker,
            det->context);
    }
    
    return written;
}

/*
 * Initialize cognitive signatures module
 */
shield_err_t cognitive_init(void)
{
    LOG_INFO("Cognitive Signatures: Initialized with %zu signature types", 
             NUM_COGNITIVE_SIGS);
    return SHIELD_OK;
}

/*
 * Get cognitive signatures stats
 */
void cognitive_get_stats(char *buffer, size_t buflen)
{
    if (!buffer || buflen == 0) return;
    
    snprintf(buffer, buflen,
        "Cognitive Signatures Stats:\n"
        "  Signature Types: %zu\n"
        "  Status: ACTIVE\n",
        NUM_COGNITIVE_SIGS);
}

