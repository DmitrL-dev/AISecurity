/*
 * SENTINEL Shield - Guard Interface
 * 
 * Base interface for all guards (LLM, RAG, Agent, Tool, etc.)
 */

#ifndef SHIELD_GUARD_H
#define SHIELD_GUARD_H

#include "shield_common.h"
#include "shield_zone.h"

/* Guard context for evaluation */
typedef struct guard_context {
    shield_zone_t       *zone;
    rule_direction_t    direction;
    const char          *source_id;
    const char          *session_id;
    uint64_t            timestamp;
    void                *user_data;
} guard_context_t;

/* Guard result */
typedef struct guard_result {
    rule_action_t   action;
    float           confidence;
    char            reason[SHIELD_MAX_DESC_LEN];
    char            details[SHIELD_MAX_PATTERN_LEN];
} guard_result_t;

/* Guard interface (virtual table) */
typedef struct guard_vtable {
    const char *name;
    zone_type_t supported_type;
    
    /* Methods */
    shield_err_t (*init)(void *guard);
    void (*destroy)(void *guard);
    guard_result_t (*check_ingress)(void *guard, guard_context_t *ctx,
                                     const void *data, size_t len);
    guard_result_t (*check_egress)(void *guard, guard_context_t *ctx,
                                    const void *data, size_t len);
} guard_vtable_t;

/* Base guard structure */
typedef struct guard_base {
    const guard_vtable_t *vtable;
    bool enabled;
    void *config;
} guard_base_t;

/* Guard registry */
typedef struct guard_registry {
    guard_base_t    *guards[SHIELD_MAX_GUARDS];
    uint32_t        count;
} guard_registry_t;

/* API */
shield_err_t guard_registry_init(guard_registry_t *reg);
void guard_registry_destroy(guard_registry_t *reg);

shield_err_t guard_register(guard_registry_t *reg, guard_base_t *guard);
guard_base_t *guard_find_by_type(guard_registry_t *reg, zone_type_t type);
guard_base_t *guard_find_by_name(guard_registry_t *reg, const char *name);

/* Evaluation */
guard_result_t guard_evaluate(guard_registry_t *reg, guard_context_t *ctx,
                               const void *data, size_t len);

/* Built-in guards declaration (implemented in guards/) */
extern const guard_vtable_t llm_guard_vtable;
extern const guard_vtable_t rag_guard_vtable;
extern const guard_vtable_t agent_guard_vtable;
extern const guard_vtable_t tool_guard_vtable;
extern const guard_vtable_t mcp_guard_vtable;

#endif /* SHIELD_GUARD_H */
