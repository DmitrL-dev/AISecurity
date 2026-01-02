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

/* API Guard state */
typedef struct api_guard {
    guard_base_t    base;
    
    /* Configuration */
    bool            check_url_injection;
    bool            check_ssrf;
    bool            check_credentials;
    char            *allowed_domains[64];
    int             allowed_domains_count;
    
    /* Statistics */
    uint64_t        checks_performed;
    uint64_t        threats_detected;
} api_guard_t;

/* Dangerous URL patterns */
static const char *dangerous_url_patterns[] = {
    "127.0.0.1",
    "localhost",
    "0.0.0.0",
    "169.254.",      /* Link-local */
    "10.",           /* Private */
    "172.16.",       /* Private */
    "192.168.",      /* Private */
    "::1",           /* IPv6 localhost */
    "file://",
    "gopher://",
    "dict://",
};

#define NUM_DANGEROUS_URL (sizeof(dangerous_url_patterns) / sizeof(dangerous_url_patterns[0]))

/* Initialize */
static shield_err_t api_guard_init(void *guard)
{
    api_guard_t *g = (api_guard_t *)guard;
    
    g->check_url_injection = true;
    g->check_ssrf = true;
    g->check_credentials = true;
    g->allowed_domains_count = 0;
    g->checks_performed = 0;
    g->threats_detected = 0;
    
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
    
    /* Check for SSRF patterns */
    if (g->check_ssrf) {
        for (size_t i = 0; i < NUM_DANGEROUS_URL; i++) {
            if (strstr(text, dangerous_url_patterns[i])) {
                result.action = ACTION_BLOCK;
                result.confidence = 0.95f;
                snprintf(result.reason, sizeof(result.reason),
                        "Potential SSRF: %s", dangerous_url_patterns[i]);
                g->threats_detected++;
                return result;
            }
        }
    }
    
    /* Check for credentials in URL */
    if (g->check_credentials) {
        if (strstr(text, "api_key=") || strstr(text, "token=") ||
            strstr(text, "password=") || strstr(text, "secret=")) {
            result.action = ACTION_QUARANTINE;
            result.confidence = 0.8f;
            strncpy(result.reason, "Credentials detected in API request",
                    sizeof(result.reason) - 1);
            g->threats_detected++;
            return result;
        }
    }
    
    /* URL injection patterns */
    if (g->check_url_injection) {
        if (strstr(text, "%00") || strstr(text, "..%2f") ||
            strstr(text, "%2e%2e") || strstr(text, "\\x00")) {
            result.action = ACTION_BLOCK;
            result.confidence = 0.9f;
            strncpy(result.reason, "URL injection pattern detected",
                    sizeof(result.reason) - 1);
            g->threats_detected++;
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
    
    /* Check for sensitive data in response */
    if (strstr(text, "\"password\"") || strstr(text, "\"secret\"") ||
        strstr(text, "\"private_key\"")) {
        result.action = ACTION_QUARANTINE;
        result.confidence = 0.85f;
        strncpy(result.reason, "Sensitive data in API response",
                sizeof(result.reason) - 1);
        g->threats_detected++;
        return result;
    }
    
    /* Check for error messages that leak information */
    if (strstr(text, "stack trace") || strstr(text, "SQL error") ||
        strstr(text, "at line") || strstr(text, "Exception in")) {
        result.action = ACTION_LOG;
        result.confidence = 0.6f;
        strncpy(result.reason, "Debug information in API response",
                sizeof(result.reason) - 1);
        return result;
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
