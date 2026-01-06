/**
 * @file brain_ffi.c
 * @brief Brain FFI Implementation
 * 
 * Connects Shield C guards to Brain Python detection engines.
 * Supports embedded Python and HTTP fallback modes.
 * 
 * @author SENTINEL Team
 * @date January 2026
 */

#include "shield_brain.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

/* ============================================================================
 * Internal State
 * ============================================================================ */

typedef enum {
    FFI_MODE_STUB,      /* No Brain available */
    FFI_MODE_PYTHON,    /* Embedded Python */
    FFI_MODE_HTTP       /* HTTP API fallback */
} ffi_mode_t;

static struct {
    bool initialized;
    ffi_mode_t mode;
    brain_ffi_config_t config;
} g_ffi = {0};

/* ============================================================================
 * Forward Declarations (to be implemented in python_bridge.c and http_client.c)
 * ============================================================================ */

/* From python_bridge.c */
extern int python_bridge_init(const char *python_home, const char *brain_path);
extern void python_bridge_shutdown(void);
extern bool python_bridge_available(void);
extern int python_bridge_analyze(const char *input, const char *engine, 
                                 brain_result_t *result);

/* From http_client.c */
extern int http_client_init(const char *endpoint);
extern void http_client_shutdown(void);
extern bool http_client_available(void);
extern int http_client_analyze(const char *input, const char *engine,
                               brain_result_t *result);

/* ============================================================================
 * Stub Mode (Pattern Matching Fallback)
 * ============================================================================ */

static int stub_analyze(const char *input, brain_engine_category_t category,
                       brain_result_t *result) {
    if (!input || !result) return -1;
    
    memset(result, 0, sizeof(*result));
    result->engine_name = "stub_detector";
    
    clock_t start = clock();
    
    /* Simple pattern matching fallback */
    switch (category) {
        case BRAIN_ENGINE_INJECTION:
            if (strstr(input, "ignore") || strstr(input, "Ignore") ||
                strstr(input, "system prompt") || strstr(input, "System prompt") ||
                strstr(input, "forget") || strstr(input, "Forget") ||
                strstr(input, "disregard") || strstr(input, "Disregard") ||
                strstr(input, "instructions") || strstr(input, "Instructions")) {
                result->detected = true;
                result->confidence = 0.85;
                result->severity = BRAIN_SEVERITY_HIGH;
                result->reason = "Injection pattern detected (stub)";
                result->attack_type = "prompt_injection";
            }
            break;
            
        case BRAIN_ENGINE_JAILBREAK:
            if (strstr(input, "DAN") || strstr(input, "jailbreak") ||
                strstr(input, "Developer Mode") || strstr(input, "pretend")) {
                result->detected = true;
                result->confidence = 0.80;
                result->severity = BRAIN_SEVERITY_HIGH;
                result->reason = "Jailbreak pattern detected (stub)";
                result->attack_type = "jailbreak";
            }
            break;
            
        case BRAIN_ENGINE_RAG_POISONING:
            if (strstr(input, "[[") || strstr(input, "document says") ||
                strstr(input, "according to the context")) {
                result->detected = true;
                result->confidence = 0.70;
                result->severity = BRAIN_SEVERITY_MEDIUM;
                result->reason = "RAG manipulation pattern (stub)";
                result->attack_type = "rag_poisoning";
            }
            break;
            
        case BRAIN_ENGINE_AGENT_MANIPULATION:
            if (strstr(input, "execute") || strstr(input, "run command") ||
                strstr(input, "rm -rf") || strstr(input, "delete")) {
                result->detected = true;
                result->confidence = 0.90;
                result->severity = BRAIN_SEVERITY_CRITICAL;
                result->reason = "Agent manipulation detected (stub)";
                result->attack_type = "agent_hijacking";
            }
            break;
            
        case BRAIN_ENGINE_TOOL_HIJACKING:
            if (strstr(input, "call tool") || strstr(input, "invoke")) {
                result->detected = true;
                result->confidence = 0.75;
                result->severity = BRAIN_SEVERITY_HIGH;
                result->reason = "Tool hijack attempt (stub)";
                result->attack_type = "tool_hijacking";
            }
            break;
            
        case BRAIN_ENGINE_PII:
            if (strstr(input, "SSN") || strstr(input, "password") ||
                strstr(input, "credit card") || strstr(input, "@")) {
                result->detected = true;
                result->confidence = 0.65;
                result->severity = BRAIN_SEVERITY_MEDIUM;
                result->reason = "PII pattern detected (stub)";
                result->attack_type = "pii_exposure";
            }
            break;
            
        case BRAIN_ENGINE_EXFILTRATION:
            if (strstr(input, "curl") || strstr(input, "wget") ||
                strstr(input, "send") || strstr(input, "exfil") ||
                strstr(input, "transfer") || strstr(input, "upload")) {
                result->detected = true;
                result->confidence = 0.80;
                result->severity = BRAIN_SEVERITY_HIGH;
                result->reason = "Data exfiltration pattern (stub)";
                result->attack_type = "data_exfiltration";
            }
            break;
            
        default:
            break;
    }
    
    clock_t end = clock();
    result->latency_ms = ((double)(end - start) / CLOCKS_PER_SEC) * 1000.0;
    
    return 0;
}

/* ============================================================================
 * Lifecycle
 * ============================================================================ */

int brain_ffi_init(const char *python_home, const char *brain_path) {
    if (g_ffi.initialized) return 0;
    
    /* Set default config */
    brain_ffi_config_t default_config = BRAIN_FFI_CONFIG_DEFAULT;
    g_ffi.config = default_config;
    
    /* Try Python first */
#ifdef SHIELD_FFI_PYTHON
    if (python_bridge_init(python_home, brain_path) == 0) {
        g_ffi.mode = FFI_MODE_PYTHON;
        g_ffi.initialized = true;
        printf("[FFI] Brain initialized (Python embedded)\n");
        return 0;
    }
#endif
    
    /* Try HTTP fallback */
#ifdef SHIELD_FFI_HTTP
    if (g_ffi.config.use_http_fallback) {
        if (http_client_init(g_ffi.config.http_endpoint) == 0) {
            g_ffi.mode = FFI_MODE_HTTP;
            g_ffi.initialized = true;
            printf("[FFI] Brain initialized (HTTP fallback)\n");
            return 0;
        }
    }
#endif
    
    /* Fall back to stub mode */
    g_ffi.mode = FFI_MODE_STUB;
    g_ffi.initialized = true;
    printf("[FFI] Brain initialized (stub mode - pattern matching only)\n");
    
    return 0;
}

void brain_ffi_shutdown(void) {
    if (!g_ffi.initialized) return;
    
#ifdef SHIELD_FFI_PYTHON
    if (g_ffi.mode == FFI_MODE_PYTHON) {
        python_bridge_shutdown();
    }
#endif
    
#ifdef SHIELD_FFI_HTTP
    if (g_ffi.mode == FFI_MODE_HTTP) {
        http_client_shutdown();
    }
#endif
    
    g_ffi.initialized = false;
    g_ffi.mode = FFI_MODE_STUB;
}

bool brain_available(void) {
    return g_ffi.initialized && g_ffi.mode != FFI_MODE_STUB;
}

const char* brain_mode(void) {
    switch (g_ffi.mode) {
        case FFI_MODE_PYTHON: return "embedded";
        case FFI_MODE_HTTP: return "http";
        default: return "stub";
    }
}

/* ============================================================================
 * Analysis
 * ============================================================================ */

int brain_ffi_analyze(const char *input, brain_engine_category_t category,
                      brain_result_t *result) {
    if (!g_ffi.initialized) {
        brain_ffi_init(NULL, NULL);
    }
    
    if (!input || !result) return -1;
    
#ifdef SHIELD_FFI_PYTHON
    if (g_ffi.mode == FFI_MODE_PYTHON) {
        /* Map category to engine name */
        const char *engine_name = NULL;
        switch (category) {
            case BRAIN_ENGINE_INJECTION: engine_name = "injection"; break;
            case BRAIN_ENGINE_JAILBREAK: engine_name = "jailbreak"; break;
            case BRAIN_ENGINE_RAG_POISONING: engine_name = "rag_poisoning"; break;
            case BRAIN_ENGINE_AGENT_MANIPULATION: engine_name = "agent"; break;
            default: engine_name = "all"; break;
        }
        
        int ret = python_bridge_analyze(input, engine_name, result);
        if (ret == 0) return 0;
        
        /* Python failed, try fallback */
        if (g_ffi.config.use_http_fallback) {
            /* Fall through to HTTP */
        } else {
            /* Fall through to stub */
        }
    }
#endif
    
#ifdef SHIELD_FFI_HTTP
    if (g_ffi.mode == FFI_MODE_HTTP) {
        int ret = http_client_analyze(input, NULL, result);
        if (ret == 0) return 0;
    }
#endif
    
    /* Stub fallback */
    return stub_analyze(input, category, result);
}

int brain_ffi_analyze_all(const char *input, brain_aggregate_result_t *result) {
    if (!input || !result) return -1;
    
    memset(result, 0, sizeof(*result));
    
    /* Analyze with each category */
    brain_engine_category_t categories[] = {
        BRAIN_ENGINE_INJECTION,
        BRAIN_ENGINE_JAILBREAK,
        BRAIN_ENGINE_RAG_POISONING,
        BRAIN_ENGINE_AGENT_MANIPULATION,
        BRAIN_ENGINE_TOOL_HIJACKING,
        BRAIN_ENGINE_PII
    };
    size_t num_categories = sizeof(categories) / sizeof(categories[0]);
    
    result->results = calloc(num_categories, sizeof(brain_result_t));
    if (!result->results) return -1;
    
    for (size_t i = 0; i < num_categories; i++) {
        brain_result_t *r = &result->results[i];
        
        brain_ffi_analyze(input, categories[i], r);
        
        result->engines_run++;
        result->total_latency_ms += r->latency_ms;
        
        if (r->detected) {
            result->any_detected = true;
            result->engines_triggered++;
            
            if (r->confidence > result->max_confidence) {
                result->max_confidence = r->confidence;
            }
            if (r->severity > result->max_severity) {
                result->max_severity = r->severity;
            }
        }
    }
    
    result->result_count = num_categories;
    
    return 0;
}

int brain_ffi_analyze_engine(const char *input, const char *engine_name,
                             brain_result_t *result) {
    /* For now, map to category-based analysis */
    /* TODO: Direct engine invocation via Python bridge */
    
    brain_engine_category_t category = BRAIN_ENGINE_ALL;
    
    if (strstr(engine_name, "injection")) {
        category = BRAIN_ENGINE_INJECTION;
    } else if (strstr(engine_name, "jailbreak")) {
        category = BRAIN_ENGINE_JAILBREAK;
    } else if (strstr(engine_name, "rag")) {
        category = BRAIN_ENGINE_RAG_POISONING;
    } else if (strstr(engine_name, "agent")) {
        category = BRAIN_ENGINE_AGENT_MANIPULATION;
    }
    
    result->engine_name = engine_name;
    return brain_ffi_analyze(input, category, result);
}

/* ============================================================================
 * Result Management
 * ============================================================================ */

void brain_result_free(brain_aggregate_result_t *result) {
    if (result && result->results) {
        free(result->results);
        result->results = NULL;
        result->result_count = 0;
    }
}

const char* brain_severity_string(brain_severity_t severity) {
    switch (severity) {
        case BRAIN_SEVERITY_NONE: return "none";
        case BRAIN_SEVERITY_LOW: return "low";
        case BRAIN_SEVERITY_MEDIUM: return "medium";
        case BRAIN_SEVERITY_HIGH: return "high";
        case BRAIN_SEVERITY_CRITICAL: return "critical";
        default: return "unknown";
    }
}

/* ============================================================================
 * Engine Discovery
 * ============================================================================ */

size_t brain_engine_count(void) {
    /* TODO: Query from Brain via FFI */
    /* For now, return approximate count */
    return 212;
}

size_t brain_engine_names(const char **names, size_t max_count) {
    /* TODO: Query from Brain via FFI */
    /* For now, return stub names */
    static const char *stub_names[] = {
        "injection_engine",
        "jailbreak_engine",
        "rag_guard",
        "agent_guard",
        "tool_guard",
        "mcp_guard"
    };
    
    size_t count = sizeof(stub_names) / sizeof(stub_names[0]);
    if (count > max_count) count = max_count;
    
    for (size_t i = 0; i < count; i++) {
        names[i] = stub_names[i];
    }
    
    return count;
}

bool brain_engine_available(const char *engine_name) {
    (void)engine_name;
    /* TODO: Query from Brain */
    return g_ffi.mode != FFI_MODE_STUB;
}

/* ============================================================================
 * Configuration
 * ============================================================================ */

int brain_ffi_configure(const brain_ffi_config_t *config) {
    if (!config) return -1;
    g_ffi.config = *config;
    return 0;
}
