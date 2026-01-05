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
    bool            check_vector_injection;
    bool            check_embedding_manipulation;
    float           similarity_threshold;
    float           embedding_entropy_max;
    
    /* Statistics */
    uint64_t        checks_performed;
    uint64_t        threats_detected;
    uint64_t        poisoning_blocked;
    uint64_t        vector_injections;
} rag_guard_t;

/* ===== RAG Attack Pattern Database ===== */

typedef enum rag_attack_category {
    RAG_CAT_POISONING,          /* Data poisoning */
    RAG_CAT_VECTOR_INJECT,      /* Vector query manipulation */
    RAG_CAT_SOURCE_MANIP,       /* Source/provenance attacks */
    RAG_CAT_EMBEDDING,          /* Embedding manipulation */
    RAG_CAT_RETRIEVAL_BYPASS,   /* Bypass retrieval logic */
} rag_attack_category_t;

typedef struct rag_pattern {
    const char          *pattern;
    const char          *description;
    rag_attack_category_t category;
    float               severity;
} rag_pattern_t;

static const rag_pattern_t rag_attack_patterns[] = {
    /* Data poisoning patterns */
    {"DROP", "SQL injection (DROP)", RAG_CAT_POISONING, 0.95f},
    {"DELETE FROM", "SQL injection (DELETE)", RAG_CAT_POISONING, 0.95f},
    {"TRUNCATE", "SQL injection (TRUNCATE)", RAG_CAT_POISONING, 0.95f},
    {"UPDATE SET", "SQL injection (UPDATE)", RAG_CAT_POISONING, 0.90f},
    {"INSERT INTO", "SQL injection (INSERT)", RAG_CAT_POISONING, 0.85f},
    {"'; --", "SQL comment injection", RAG_CAT_POISONING, 0.90f},
    
    /* Vector query injection */
    {"similarity_override", "Vector similarity override", RAG_CAT_VECTOR_INJECT, 0.95f},
    {"embedding_inject", "Embedding injection", RAG_CAT_VECTOR_INJECT, 0.95f},
    {"vector_bypass", "Vector search bypass", RAG_CAT_VECTOR_INJECT, 0.90f},
    {"cosine_force", "Force cosine similarity", RAG_CAT_VECTOR_INJECT, 0.85f},
    {"nearest_override", "Override nearest neighbor", RAG_CAT_VECTOR_INJECT, 0.90f},
    {"$vector", "MongoDB vector operator injection", RAG_CAT_VECTOR_INJECT, 0.85f},
    {"knn_search", "Direct KNN manipulation", RAG_CAT_VECTOR_INJECT, 0.80f},
    
    /* Source manipulation */
    {"__metadata__", "Metadata access", RAG_CAT_SOURCE_MANIP, 0.75f},
    {"_source", "Source field access", RAG_CAT_SOURCE_MANIP, 0.70f},
    {"embedding:", "Direct embedding access", RAG_CAT_SOURCE_MANIP, 0.75f},
    {"chunk_id:", "Chunk ID manipulation", RAG_CAT_SOURCE_MANIP, 0.70f},
    {"doc_rank:", "Document rank manipulation", RAG_CAT_SOURCE_MANIP, 0.80f},
    {"source_trust:", "Trust score manipulation", RAG_CAT_SOURCE_MANIP, 0.90f},
    
    /* Embedding manipulation */
    {"\\x00\\x00\\x00", "Null byte embedding", RAG_CAT_EMBEDDING, 0.85f},
    {"[0.0, 0.0, 0.0", "Zero vector injection", RAG_CAT_EMBEDDING, 0.80f},
    {"[1.0, 1.0, 1.0", "Unit vector injection", RAG_CAT_EMBEDDING, 0.75f},
    {"NaN", "NaN in embedding", RAG_CAT_EMBEDDING, 0.95f},
    {"Infinity", "Infinity in embedding", RAG_CAT_EMBEDDING, 0.95f},
    
    /* Retrieval bypass */
    {"top_k=999", "Excessive top_k", RAG_CAT_RETRIEVAL_BYPASS, 0.70f},
    {"threshold=0", "Zero threshold", RAG_CAT_RETRIEVAL_BYPASS, 0.75f},
    {"filter_bypass", "Filter bypass", RAG_CAT_RETRIEVAL_BYPASS, 0.85f},
    {"rerank_disable", "Rerank disable", RAG_CAT_RETRIEVAL_BYPASS, 0.80f},
};

#define NUM_RAG_PATTERNS (sizeof(rag_attack_patterns) / sizeof(rag_attack_patterns[0]))

/* Egress injection patterns */
static const char *rag_egress_patterns[] = {
    "IGNORE PREVIOUS",
    "NEW INSTRUCTIONS",
    "[SYSTEM]",
    "[[INJECT]]",
    "<!-- INJECTION -->",
    "<|system|>",
    "[INST]",
    "### Instruction:",
    "\\n\\nHuman:",
    "\\n\\nAssistant:",
};

#define NUM_RAG_EGRESS (sizeof(rag_egress_patterns) / sizeof(rag_egress_patterns[0]))

/* Initialize */
static shield_err_t rag_guard_init(void *guard)
{
    rag_guard_t *g = (rag_guard_t *)guard;
    
    g->check_poisoning = true;
    g->check_provenance = true;
    g->check_vector_injection = true;
    g->check_embedding_manipulation = true;
    g->similarity_threshold = 0.5f;
    g->embedding_entropy_max = 0.95f;
    g->checks_performed = 0;
    g->threats_detected = 0;
    g->poisoning_blocked = 0;
    g->vector_injections = 0;
    
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
    (void)len;
    
    guard_result_t result = {
        .action = ACTION_ALLOW,
        .confidence = 1.0f,
        .reason = "",
        .details = ""
    };
    
    g->checks_performed++;
    
    const char *text = (const char *)data;
    
    /* Check all RAG attack patterns */
    for (size_t i = 0; i < NUM_RAG_PATTERNS; i++) {
        if (strstr(text, rag_attack_patterns[i].pattern)) {
            rag_attack_category_t cat = rag_attack_patterns[i].category;
            float severity = rag_attack_patterns[i].severity;
            
            result.action = (severity >= 0.85f) ? ACTION_BLOCK : ACTION_QUARANTINE;
            result.confidence = severity;
            snprintf(result.reason, sizeof(result.reason),
                    "RAG attack: %s (category: %d)",
                    rag_attack_patterns[i].description, cat);
            
            g->threats_detected++;
            if (cat == RAG_CAT_POISONING) g->poisoning_blocked++;
            if (cat == RAG_CAT_VECTOR_INJECT) g->vector_injections++;
            
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
    
    /* Check for injected instructions in RAG response */
    if (g->check_provenance) {
        for (size_t i = 0; i < NUM_RAG_EGRESS; i++) {
            if (strstr(text, rag_egress_patterns[i])) {
                result.action = ACTION_BLOCK;
                result.confidence = 0.95f;
                snprintf(result.reason, sizeof(result.reason),
                        "RAG response injection: %s", rag_egress_patterns[i]);
                g->threats_detected++;
                return result;
            }
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
