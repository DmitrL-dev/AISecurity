/*
 * SENTINEL Shield - Policy Engine
 * 
 * Full policy-map, class-map, service-policy implementation
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>

#include "shield_common.h"
#include "shield_semantic.h"

/* Static semantic detector for policy evaluation */
static semantic_detector_t g_semantic_detector;
static bool g_semantic_initialized = false;

/* Forward declarations */
float calculate_entropy(const void *data, size_t len);

/* Note: policy_engine.c has its own type definitions, not using shield_policy.h */

/* ===== Class Map ===== */

/* Match types for class-map */
typedef enum {
    CLASS_MATCH_ANY,        /* match any */
    CLASS_MATCH_ALL,        /* match all (AND) */
} class_match_mode_t;

/* Match condition */
typedef struct class_condition {
    struct class_condition *next;
    match_type_t            type;
    char                    value[256];
    bool                    negate;
} class_condition_t;

/* Class Map */
typedef struct class_map {
    struct class_map       *next;
    char                    name[SHIELD_MAX_NAME_LEN];
    char                    description[256];
    class_match_mode_t      mode;
    class_condition_t      *conditions;
    uint32_t                condition_count;
    uint64_t                match_count;
} class_map_t;

/* ===== Policy Map ===== */

/* Actions for policy-map class */
typedef struct policy_action {
    struct policy_action   *next;
    rule_action_t           action;
    uint32_t                rate_limit;         /* 0 = no limit */
    char                    redirect_zone[SHIELD_MAX_NAME_LEN];
    uint8_t                 set_severity;
    bool                    log_enabled;
    char                    log_message[256];
} policy_action_t;

/* Policy class (reference to class-map + actions) */
typedef struct policy_class {
    struct policy_class    *next;
    char                    class_name[SHIELD_MAX_NAME_LEN];
    class_map_t            *class_ref;
    policy_action_t        *actions;
    uint32_t                action_count;
    uint64_t                hit_count;
} policy_class_t;

/* Policy Map */
typedef struct policy_map {
    struct policy_map      *next;
    char                    name[SHIELD_MAX_NAME_LEN];
    char                    description[256];
    policy_class_t         *classes;
    uint32_t                class_count;
    bool                    enabled;
} policy_map_t;

/* ===== Policy Engine ===== */

typedef struct policy_engine {
    class_map_t            *class_maps;
    uint32_t                class_map_count;
    
    policy_map_t           *policy_maps;
    uint32_t                policy_map_count;
    
    /* Zone to policy bindings */
    struct {
        char zone_name[SHIELD_MAX_NAME_LEN];
        char policy_name[SHIELD_MAX_NAME_LEN];
        rule_direction_t direction;
    } bindings[256];
    uint32_t binding_count;
} policy_engine_t;

/* Evaluation context for policy matching */
typedef struct evaluation_context {
    const char          *zone;
    rule_direction_t    direction;
    const char          *data;
    size_t              data_len;
    const char          *source_ip;
    const char          *user_id;
} evaluation_context_t;

/* Policy result */
typedef struct policy_result {
    rule_action_t       action;
    const char          *policy_name;
    const char          *class_name;
    const char          *reason;
    char                matched_policy[SHIELD_MAX_NAME_LEN];
    char                matched_class[SHIELD_MAX_NAME_LEN];
    char                log_message[256];
    uint32_t            rate_limit;
    uint8_t             severity;
    bool                log;
} policy_result_t;

/* Direction aliases (some code uses INBOUND/OUTBOUND) */
#define DIRECTION_INBOUND  DIRECTION_INPUT
#define DIRECTION_OUTBOUND DIRECTION_OUTPUT

/* Initialize policy engine */
shield_err_t policy_engine_init(policy_engine_t *engine)
{
    if (!engine) return SHIELD_ERR_INVALID;
    memset(engine, 0, sizeof(*engine));
    return SHIELD_OK;
}

/* ===== Class Map Operations ===== */

/* Create class-map */
shield_err_t class_map_create(policy_engine_t *engine, const char *name,
                               class_match_mode_t mode, class_map_t **out)
{
    if (!engine || !name) return SHIELD_ERR_INVALID;
    
    /* Check duplicate */
    class_map_t *cm = engine->class_maps;
    while (cm) {
        if (strcmp(cm->name, name) == 0) return SHIELD_ERR_EXISTS;
        cm = cm->next;
    }
    
    cm = calloc(1, sizeof(class_map_t));
    if (!cm) return SHIELD_ERR_NOMEM;
    
    strncpy(cm->name, name, sizeof(cm->name) - 1);
    cm->mode = mode;
    
    /* Add to list */
    cm->next = engine->class_maps;
    engine->class_maps = cm;
    engine->class_map_count++;
    
    if (out) *out = cm;
    return SHIELD_OK;
}

/* Add match condition to class-map */
shield_err_t class_map_add_match(class_map_t *cm, match_type_t type,
                                  const char *value, bool negate)
{
    if (!cm) return SHIELD_ERR_INVALID;
    
    class_condition_t *cond = calloc(1, sizeof(class_condition_t));
    if (!cond) return SHIELD_ERR_NOMEM;
    
    cond->type = type;
    if (value) strncpy(cond->value, value, sizeof(cond->value) - 1);
    cond->negate = negate;
    
    cond->next = cm->conditions;
    cm->conditions = cond;
    cm->condition_count++;
    
    return SHIELD_OK;
}

/* Evaluate class-map against data */
bool class_map_evaluate(class_map_t *cm, const void *data, size_t len,
                         evaluation_context_t *ctx)
{
    if (!cm || !data) return false;
    
    bool result = (cm->mode == CLASS_MATCH_ALL) ? true : false;
    
    class_condition_t *cond = cm->conditions;
    while (cond) {
        bool match = false;
        
        switch (cond->type) {
        case MATCH_PATTERN:
        case MATCH_CONTAINS:
            match = strstr((const char*)data, cond->value) != NULL;
            break;
            
        case MATCH_SIZE_GT:
            match = len > (size_t)atoi(cond->value);
            break;
            
        case MATCH_SIZE_LT:
            match = len < (size_t)atoi(cond->value);
            break;
            
        case MATCH_JAILBREAK:
        case MATCH_PROMPT_INJECTION:
            /* Initialize semantic detector on first use */
            if (!g_semantic_initialized) {
                semantic_init(&g_semantic_detector);
                g_semantic_initialized = true;
            }
            match = semantic_is_suspicious(&g_semantic_detector, (const char*)data, len);
            break;
            
        case MATCH_ENTROPY_HIGH:
            match = calculate_entropy(data, len) > 0.9f;
            break;
            
        default:
            break;
        }
        
        if (cond->negate) match = !match;
        
        if (cm->mode == CLASS_MATCH_ALL) {
            result = result && match;
            if (!result) break;  /* Short-circuit */
        } else {  /* MATCH_ANY */
            result = result || match;
            if (result) break;  /* Short-circuit */
        }
        
        cond = cond->next;
    }
    
    if (result) cm->match_count++;
    return result;
}

/* Find class-map by name */
class_map_t *class_map_find(policy_engine_t *engine, const char *name)
{
    if (!engine || !name) return NULL;
    
    class_map_t *cm = engine->class_maps;
    while (cm) {
        if (strcmp(cm->name, name) == 0) return cm;
        cm = cm->next;
    }
    return NULL;
}

/* Delete class-map by name */
shield_err_t class_map_delete(policy_engine_t *engine, const char *name)
{
    if (!engine || !name) return SHIELD_ERR_INVALID;
    
    class_map_t *prev = NULL;
    class_map_t *cm = engine->class_maps;
    
    while (cm) {
        if (strcmp(cm->name, name) == 0) {
            /* Unlink from list */
            if (prev) {
                prev->next = cm->next;
            } else {
                engine->class_maps = cm->next;
            }
            engine->class_map_count--;
            
            /* Free conditions */
            class_condition_t *cond = cm->conditions;
            while (cond) {
                class_condition_t *next = cond->next;
                free(cond);
                cond = next;
            }
            
            free(cm);
            return SHIELD_OK;
        }
        prev = cm;
        cm = cm->next;
    }
    
    return SHIELD_ERR_NOTFOUND;
}

/* ===== Policy Map Operations ===== */

/* Create policy-map */
shield_err_t policy_map_create(policy_engine_t *engine, const char *name,
                                policy_map_t **out)
{
    if (!engine || !name) return SHIELD_ERR_INVALID;
    
    /* Check duplicate */
    policy_map_t *pm = engine->policy_maps;
    while (pm) {
        if (strcmp(pm->name, name) == 0) return SHIELD_ERR_EXISTS;
        pm = pm->next;
    }
    
    pm = calloc(1, sizeof(policy_map_t));
    if (!pm) return SHIELD_ERR_NOMEM;
    
    strncpy(pm->name, name, sizeof(pm->name) - 1);
    pm->enabled = true;
    
    pm->next = engine->policy_maps;
    engine->policy_maps = pm;
    engine->policy_map_count++;
    
    if (out) *out = pm;
    return SHIELD_OK;
}

/* Add class to policy-map */
shield_err_t policy_map_add_class(policy_map_t *pm, const char *class_name,
                                   policy_class_t **out)
{
    if (!pm || !class_name) return SHIELD_ERR_INVALID;
    
    policy_class_t *pc = calloc(1, sizeof(policy_class_t));
    if (!pc) return SHIELD_ERR_NOMEM;
    
    strncpy(pc->class_name, class_name, sizeof(pc->class_name) - 1);
    
    pc->next = pm->classes;
    pm->classes = pc;
    pm->class_count++;
    
    if (out) *out = pc;
    return SHIELD_OK;
}

/* Add action to policy class */
shield_err_t policy_class_add_action(policy_class_t *pc, rule_action_t action,
                                      policy_action_t **out)
{
    if (!pc) return SHIELD_ERR_INVALID;
    
    policy_action_t *pa = calloc(1, sizeof(policy_action_t));
    if (!pa) return SHIELD_ERR_NOMEM;
    
    pa->action = action;
    
    pa->next = pc->actions;
    pc->actions = pa;
    pc->action_count++;
    
    if (out) *out = pa;
    return SHIELD_OK;
}

/* Find policy-map by name */
policy_map_t *policy_map_find(policy_engine_t *engine, const char *name)
{
    if (!engine || !name) return NULL;
    
    policy_map_t *pm = engine->policy_maps;
    while (pm) {
        if (strcmp(pm->name, name) == 0) return pm;
        pm = pm->next;
    }
    return NULL;
}

/* Delete policy-map by name */
shield_err_t policy_map_delete(policy_engine_t *engine, const char *name)
{
    if (!engine || !name) return SHIELD_ERR_INVALID;
    
    policy_map_t *prev = NULL;
    policy_map_t *pm = engine->policy_maps;
    
    while (pm) {
        if (strcmp(pm->name, name) == 0) {
            /* Unlink from list */
            if (prev) {
                prev->next = pm->next;
            } else {
                engine->policy_maps = pm->next;
            }
            engine->policy_map_count--;
            
            /* Free classes and actions */
            policy_class_t *pc = pm->classes;
            while (pc) {
                policy_class_t *next_pc = pc->next;
                policy_action_t *pa = pc->actions;
                while (pa) {
                    policy_action_t *next_pa = pa->next;
                    free(pa);
                    pa = next_pa;
                }
                free(pc);
                pc = next_pc;
            }
            
            free(pm);
            return SHIELD_OK;
        }
        prev = pm;
        pm = pm->next;
    }
    
    return SHIELD_ERR_NOTFOUND;
}

/* Find policy-class by name */
policy_class_t *policy_class_find(policy_map_t *pm, const char *class_name)
{
    if (!pm || !class_name) return NULL;
    
    policy_class_t *pc = pm->classes;
    while (pc) {
        if (strcmp(pc->class_name, class_name) == 0) return pc;
        pc = pc->next;
    }
    return NULL;
}

/* ===== Service Policy ===== */

/* Apply policy to zone */
shield_err_t service_policy_apply(policy_engine_t *engine, const char *zone,
                                   const char *policy, rule_direction_t direction)
{
    if (!engine || !zone || !policy) return SHIELD_ERR_INVALID;
    
    if (engine->binding_count >= 256) return SHIELD_ERR_NOMEM;
    
    /* Find policy */
    policy_map_t *pm = engine->policy_maps;
    while (pm) {
        if (strcmp(pm->name, policy) == 0) break;
        pm = pm->next;
    }
    if (!pm) return SHIELD_ERR_NOTFOUND;
    
    /* Add binding */
    uint32_t idx = engine->binding_count++;
    strncpy(engine->bindings[idx].zone_name, zone, SHIELD_MAX_NAME_LEN - 1);
    strncpy(engine->bindings[idx].policy_name, policy, SHIELD_MAX_NAME_LEN - 1);
    engine->bindings[idx].direction = direction;
    
    LOG_INFO("Policy: Applied %s to zone %s (%s)", policy, zone,
             direction == DIRECTION_INBOUND ? "input" : "output");
    
    return SHIELD_OK;
}

/* ===== Policy Evaluation ===== */

/* Evaluate policy for a request */
shield_err_t policy_evaluate(policy_engine_t *engine, const char *zone,
                              rule_direction_t direction, const void *data,
                              size_t len, policy_result_t *result)
{
    if (!engine || !zone || !data || !result) return SHIELD_ERR_INVALID;
    
    memset(result, 0, sizeof(*result));
    result->action = ACTION_ALLOW;
    
    /* Find binding for zone */
    const char *policy_name = NULL;
    for (uint32_t i = 0; i < engine->binding_count; i++) {
        if (strcmp(engine->bindings[i].zone_name, zone) == 0 &&
            engine->bindings[i].direction == direction) {
            policy_name = engine->bindings[i].policy_name;
            break;
        }
    }
    
    if (!policy_name) {
        /* No policy bound, default allow */
        return SHIELD_OK;
    }
    
    /* Find policy-map */
    policy_map_t *pm = engine->policy_maps;
    while (pm) {
        if (strcmp(pm->name, policy_name) == 0) break;
        pm = pm->next;
    }
    
    if (!pm || !pm->enabled) return SHIELD_OK;
    
    /* Evaluate each class in order */
    policy_class_t *pc = pm->classes;
    while (pc) {
        /* Resolve class reference */
        if (!pc->class_ref) {
            class_map_t *cm = engine->class_maps;
            while (cm) {
                if (strcmp(cm->name, pc->class_name) == 0) {
                    pc->class_ref = cm;
                    break;
                }
                cm = cm->next;
            }
        }
        
        if (pc->class_ref && class_map_evaluate(pc->class_ref, data, len, NULL)) {
            pc->hit_count++;
            
            /* Apply actions */
            policy_action_t *pa = pc->actions;
            while (pa) {
                if (pa->action > result->action) {
                    result->action = pa->action;
                }
                if (pa->log_enabled) {
                    result->log = true;
                    strncpy(result->log_message, pa->log_message, 
                            sizeof(result->log_message) - 1);
                }
                if (pa->rate_limit > 0) {
                    result->rate_limit = pa->rate_limit;
                }
                pa = pa->next;
            }
            
            strncpy(result->matched_class, pc->class_name, 
                    sizeof(result->matched_class) - 1);
            strncpy(result->matched_policy, pm->name,
                    sizeof(result->matched_policy) - 1);
            
            break;  /* First match wins */
        }
        
        pc = pc->next;
    }
    
    return SHIELD_OK;
}

/* ===== Cleanup ===== */

void policy_engine_destroy(policy_engine_t *engine)
{
    if (!engine) return;
    
    /* Free class maps */
    class_map_t *cm = engine->class_maps;
    while (cm) {
        class_map_t *next_cm = cm->next;
        
        class_condition_t *cond = cm->conditions;
        while (cond) {
            class_condition_t *next_cond = cond->next;
            free(cond);
            cond = next_cond;
        }
        
        free(cm);
        cm = next_cm;
    }
    
    /* Free policy maps */
    policy_map_t *pm = engine->policy_maps;
    while (pm) {
        policy_map_t *next_pm = pm->next;
        
        policy_class_t *pc = pm->classes;
        while (pc) {
            policy_class_t *next_pc = pc->next;
            
            policy_action_t *pa = pc->actions;
            while (pa) {
                policy_action_t *next_pa = pa->next;
                free(pa);
                pa = next_pa;
            }
            
            free(pc);
            pc = next_pc;
        }
        
        free(pm);
        pm = next_pm;
    }
}

/* ===== CLI Commands ===== */

/* Show class-map */
void policy_show_class_maps(policy_engine_t *engine)
{
    class_map_t *cm = engine->class_maps;
    while (cm) {
        printf("class-map match-%s %s\n",
               cm->mode == CLASS_MATCH_ALL ? "all" : "any",
               cm->name);
        
        class_condition_t *cond = cm->conditions;
        while (cond) {
            printf("  %smatch %s %s\n",
                   cond->negate ? "no " : "",
                   match_type_to_string(cond->type),
                   cond->value);
            cond = cond->next;
        }
        
        printf("  ! matches: %lu\n\n", (unsigned long)cm->match_count);
        cm = cm->next;
    }
}

/* Show policy-map */
void policy_show_policy_maps(policy_engine_t *engine)
{
    policy_map_t *pm = engine->policy_maps;
    while (pm) {
        printf("policy-map %s\n", pm->name);
        
        policy_class_t *pc = pm->classes;
        while (pc) {
            printf("  class %s\n", pc->class_name);
            
            policy_action_t *pa = pc->actions;
            while (pa) {
                printf("    %s", action_to_string(pa->action));
                if (pa->rate_limit > 0) {
                    printf(" rate-limit %u", pa->rate_limit);
                }
                if (pa->log_enabled) {
                    printf(" log");
                }
                printf("\n");
                pa = pa->next;
            }
            
            printf("    ! hits: %lu\n", (unsigned long)pc->hit_count);
            pc = pc->next;
        }
        
        printf("\n");
        pm = pm->next;
    }
}
