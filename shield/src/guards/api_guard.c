/*
 * SENTINEL Shield - API Guard Implementation
 * 
 * Guards for external API calls
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "shield_common.h"
#include "shield_guard.h"

/* ===== API Attack Pattern Database ===== */

typedef enum api_attack_category {
    API_CAT_SSRF,               /* Server-Side Request Forgery */
    API_CAT_INJECTION,          /* Parameter injection */
    API_CAT_AUTH_BYPASS,        /* Authentication bypass */
    API_CAT_RATE_ABUSE,         /* Rate limiting abuse */
    API_CAT_DATA_EXPOSURE,      /* Sensitive data exposure */
} api_attack_category_t;

typedef struct api_pattern {
    const char          *pattern;
    const char          *description;
    api_attack_category_t category;
    float               severity;
} api_pattern_t;

static const api_pattern_t api_attack_patterns[] = {
    /* SSRF patterns */
    {"127.0.0.1", "Localhost access", API_CAT_SSRF, 0.95f},
    {"localhost", "Localhost name", API_CAT_SSRF, 0.95f},
    {"0.0.0.0", "All interfaces", API_CAT_SSRF, 0.95f},
    {"169.254.", "Link-local (AWS metadata)", API_CAT_SSRF, 0.99f},
    {"10.", "Private network 10.x", API_CAT_SSRF, 0.90f},
    {"172.16.", "Private network 172.16.x", API_CAT_SSRF, 0.90f},
    {"192.168.", "Private network 192.168.x", API_CAT_SSRF, 0.90f},
    {"::1", "IPv6 localhost", API_CAT_SSRF, 0.95f},
    {"[::1]", "IPv6 localhost bracket", API_CAT_SSRF, 0.95f},
    {"file://", "File protocol", API_CAT_SSRF, 0.95f},
    {"gopher://", "Gopher protocol", API_CAT_SSRF, 0.99f},
    {"dict://", "Dict protocol", API_CAT_SSRF, 0.95f},
    {"ftp://", "FTP protocol", API_CAT_SSRF, 0.80f},
    {"ldap://", "LDAP protocol", API_CAT_SSRF, 0.90f},
    {"metadata.google", "GCP metadata", API_CAT_SSRF, 0.99f},
    {"metadata.azure", "Azure metadata", API_CAT_SSRF, 0.99f},
    
    /* Injection patterns */
    {"%00", "Null byte URL", API_CAT_INJECTION, 0.95f},
    {"%0a", "Newline URL", API_CAT_INJECTION, 0.90f},
    {"%0d", "Carriage return URL", API_CAT_INJECTION, 0.90f},
    {"..%2f", "Path traversal encoded", API_CAT_INJECTION, 0.95f},
    {"%2e%2e", "Double dot encoded", API_CAT_INJECTION, 0.95f},
    {"\\x00", "Null byte escaped", API_CAT_INJECTION, 0.90f},
    {"${", "Template injection", API_CAT_INJECTION, 0.90f},
    {"{{", "Template injection 2", API_CAT_INJECTION, 0.85f},
    {"<script", "XSS script tag", API_CAT_INJECTION, 0.95f},
    {"javascript:", "JavaScript protocol", API_CAT_INJECTION, 0.95f},
    
    /* Auth bypass patterns */
    {"api_key=", "API key in URL", API_CAT_AUTH_BYPASS, 0.75f},
    {"token=", "Token in URL", API_CAT_AUTH_BYPASS, 0.75f},
    {"password=", "Password in URL", API_CAT_AUTH_BYPASS, 0.90f},
    {"secret=", "Secret in URL", API_CAT_AUTH_BYPASS, 0.85f},
    {"admin=true", "Admin flag", API_CAT_AUTH_BYPASS, 0.95f},
    {"role=admin", "Admin role", API_CAT_AUTH_BYPASS, 0.95f},
    {"debug=1", "Debug mode", API_CAT_AUTH_BYPASS, 0.80f},
    {"bypass=", "Bypass parameter", API_CAT_AUTH_BYPASS, 0.95f},
    {"__proto__", "Prototype pollution", API_CAT_AUTH_BYPASS, 0.95f},
    {"constructor[", "Prototype pollution 2", API_CAT_AUTH_BYPASS, 0.95f},
};

#define NUM_API_PATTERNS (sizeof(api_attack_patterns) / sizeof(api_attack_patterns[0]))

/* Egress patterns */
static const char *api_egress_patterns[] = {
    "\"password\"",
    "\"secret\"",
    "\"private_key\"",
    "\"api_key\"",
    "\"access_token\"",
    "\"refresh_token\"",
    "stack trace",
    "SQL error",
    "at line",
    "Exception in",
    "TRACE:",
    "DEBUG:",
    "Internal Server Error",
};

#define NUM_API_EGRESS (sizeof(api_egress_patterns) / sizeof(api_egress_patterns[0]))

/* API Guard state */
typedef struct api_guard {
    guard_base_t    base;
    
    /* Configuration */
    bool            check_ssrf;
    bool            check_injection;
    bool            check_auth_bypass;
    bool            check_credentials;
    char            *allowed_domains[64];
    int             allowed_domains_count;
    
    /* Statistics */
    uint64_t        checks_performed;
    uint64_t        threats_detected;
    uint64_t        ssrf_blocked;
    uint64_t        injections_blocked;
} api_guard_t;

/* Initialize */
static shield_err_t api_guard_init(void *guard)
{
    api_guard_t *g = (api_guard_t *)guard;
    
    g->check_ssrf = true;
    g->check_injection = true;
    g->check_auth_bypass = true;
    g->check_credentials = true;
    g->allowed_domains_count = 0;
    g->checks_performed = 0;
    g->threats_detected = 0;
    g->ssrf_blocked = 0;
    g->injections_blocked = 0;
    
    return SHIELD_OK;
}

/* Destroy */
static void api_guard_destroy(void *guard)
{
    api_guard_t *g = (api_guard_t *)guard;
    
    for (int i = 0; i < g->allowed_domains_count; i++) {
        free(g->allowed_domains[i]);
    }
}

/* Check ingress (API requests) */
static guard_result_t api_guard_check_ingress(void *guard, guard_context_t *ctx,
                                               const void *data, size_t len)
{
    api_guard_t *g = (api_guard_t *)guard;
    (void)ctx;
    (void)len;
    
    guard_result_t result = {
        .action = ACTION_ALLOW,
        .confidence = 1.0f,
        .reason = "",
        .details = ""
    };
    
    g->checks_performed++;
    
    const char *text = (const char *)data;
    
    /* Check all API attack patterns */
    for (size_t i = 0; i < NUM_API_PATTERNS; i++) {
        if (strstr(text, api_attack_patterns[i].pattern)) {
            api_attack_category_t cat = api_attack_patterns[i].category;
            float severity = api_attack_patterns[i].severity;
            
            result.action = (severity >= 0.90f) ? ACTION_BLOCK : ACTION_QUARANTINE;
            result.confidence = severity;
            snprintf(result.reason, sizeof(result.reason),
                    "API attack: %s (category: %d)",
                    api_attack_patterns[i].description, cat);
            
            g->threats_detected++;
            if (cat == API_CAT_SSRF) g->ssrf_blocked++;
            if (cat == API_CAT_INJECTION) g->injections_blocked++;
            
            return result;
        }
    }
    
    return result;
}

/* Check egress (API responses) */
static guard_result_t api_guard_check_egress(void *guard, guard_context_t *ctx,
                                              const void *data, size_t len)
{
    api_guard_t *g = (api_guard_t *)guard;
    (void)ctx;
    (void)len;
    
    guard_result_t result = {
        .action = ACTION_ALLOW,
        .confidence = 1.0f,
        .reason = "",
        .details = ""
    };
    
    g->checks_performed++;
    
    const char *text = (const char *)data;
    
    /* Check egress patterns */
    for (size_t i = 0; i < NUM_API_EGRESS; i++) {
        if (strstr(text, api_egress_patterns[i])) {
            /* First 6 patterns (secrets) are QUARANTINE, rest (debug) are LOG */
            if (i < 6) {
                result.action = ACTION_QUARANTINE;
                result.confidence = 0.85f;
                g->threats_detected++;
            } else {
                result.action = ACTION_LOG;
                result.confidence = 0.6f;
            }
            snprintf(result.reason, sizeof(result.reason),
                    "API response leak: %s", api_egress_patterns[i]);
            return result;
        }
    }
    
    return result;
}

/* API Guard vtable */
const guard_vtable_t api_guard_vtable = {
    .name = "api_guard",
    .supported_type = ZONE_TYPE_API,
    .init = api_guard_init,
    .destroy = api_guard_destroy,
    .check_ingress = api_guard_check_ingress,
    .check_egress = api_guard_check_egress,
};

/* Create API guard instance */
guard_base_t *api_guard_create(void)
{
    api_guard_t *guard = calloc(1, sizeof(api_guard_t));
    if (!guard) {
        return NULL;
    }
    
    guard->base.vtable = &api_guard_vtable;
    guard->base.enabled = true;
    
    return &guard->base;
}

/* Add allowed domain */
shield_err_t api_guard_add_allowed_domain(guard_base_t *base, const char *domain)
{
    api_guard_t *g = (api_guard_t *)base;
    
    if (!g || !domain || g->allowed_domains_count >= 64) {
        return SHIELD_ERR_INVALID;
    }
    
    g->allowed_domains[g->allowed_domains_count++] = strdup(domain);
    return SHIELD_OK;
}
