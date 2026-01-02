/*
 * SENTINEL Shield - RAG Guard Implementation
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "shield_common.h"
#include "shield_guard.h"

/* RAG Guard state */
typedef struct rag_guard {
    guard_base_t    base;
    
    /* Configuration */
    bool            check_poisoning;
    bool            check_provenance;
    float           similarity_threshold;
    
    /* Statistics */
    uint64_t        checks_performed;
    uint64_t        threats_detected;
} rag_guard_t;

/* Initialize */
static shield_err_t rag_guard_init(void *guard)
{
    rag_guard_t *g = (rag_guard_t *)guard;
    
    g->check_poisoning = true;
    g->check_provenance = true;
    g->similarity_threshold = 0.5f;
    g->checks_performed = 0;
    g->threats_detected = 0;
    
    return SHIELD_OK;
}

/* Destroy */
static void rag_guard_destroy(void *guard)
{
    (void)guard;
}

/* Check ingress (queries to RAG) */
static guard_result_t rag_guard_check_ingress(void *guard, guard_context_t *ctx,
                                               const void *data, size_t len)
{
    rag_guard_t *g = (rag_guard_t *)guard;
    (void)ctx;
    
    guard_result_t result = {
        .action = ACTION_ALLOW,
        .confidence = 1.0f,
        .reason = "",
        .details = ""
    };
    
    g->checks_performed++;
    
    const char *text = (const char *)data;
    (void)len;
    
    /* Check for RAG poisoning attempts */
    if (g->check_poisoning) {
        /* SQL-like injection in vector queries */
        if (strstr(text, "DROP") || strstr(text, "DELETE") ||
            strstr(text, "TRUNCATE") || strstr(text, "UPDATE")) {
            result.action = ACTION_BLOCK;
            result.confidence = 0.9f;
            strncpy(result.reason, "Potential RAG poisoning (SQL-like pattern)",
                    sizeof(result.reason) - 1);
            g->threats_detected++;
            return result;
        }
        
        /* Metadata injection */
        if (strstr(text, "__metadata__") || strstr(text, "_source") ||
            strstr(text, "embedding:")) {
            result.action = ACTION_QUARANTINE;
            result.confidence = 0.75f;
            strncpy(result.reason, "Suspicious metadata access pattern",
                    sizeof(result.reason) - 1);
            g->threats_detected++;
            return result;
        }
    }
    
    return result;
}

/* Check egress (results from RAG) */
static guard_result_t rag_guard_check_egress(void *guard, guard_context_t *ctx,
                                              const void *data, size_t len)
{
    rag_guard_t *g = (rag_guard_t *)guard;
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
    
    /* Check provenance */
    if (g->check_provenance) {
        /* Check if response contains injected instructions */
        if (strstr(text, "IGNORE PREVIOUS") || strstr(text, "NEW INSTRUCTIONS") ||
            strstr(text, "[SYSTEM]") || strstr(text, "[[INJECT]]")) {
            result.action = ACTION_BLOCK;
            result.confidence = 0.95f;
            strncpy(result.reason, "RAG response contains injected instructions",
                    sizeof(result.reason) - 1);
            g->threats_detected++;
            return result;
        }
    }
    
    return result;
}

/* RAG Guard vtable */
const guard_vtable_t rag_guard_vtable = {
    .name = "rag_guard",
    .supported_type = ZONE_TYPE_RAG,
    .init = rag_guard_init,
    .destroy = rag_guard_destroy,
    .check_ingress = rag_guard_check_ingress,
    .check_egress = rag_guard_check_egress,
};

/* Create RAG guard instance */
guard_base_t *rag_guard_create(void)
{
    rag_guard_t *guard = calloc(1, sizeof(rag_guard_t));
    if (!guard) {
        return NULL;
    }
    
    guard->base.vtable = &rag_guard_vtable;
    guard->base.enabled = true;
    
    return &guard->base;
}
