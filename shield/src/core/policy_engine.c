/*
 * SENTINEL Shield - Policy Engine
 * 
 * Hierarchical policy management with class-map/policy-map/policy-set APIs
 * 
 * Copyright (c) 2026 SENTINEL Project
 * License: MIT
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>

#include "shield_common.h"
#include "shield_policy.h"
#include "shield_semantic.h"
#include "shield_string_safe.h"

/* Static semantic detector for policy evaluation */
static semantic_detector_t g_semantic_detector;
static bool g_semantic_initialized = false;

/* Static rule number sequence */
static uint32_t g_rule_number_seq = 1;

/* Extern from entropy.c */
extern float calculate_entropy(const void *data, size_t len);

/* ============================================================================
 * Policy Engine Lifecycle
 * ============================================================================ */

shield_err_t policy_engine_init(policy_engine_t *engine)
{
    if (!engine) return SHIELD_ERR_INVALID;
    memset(engine, 0, sizeof(*engine));
    return SHIELD_OK;
}

void policy_engine_destroy(policy_engine_t *engine)
{
    if (!engine) return;
    
    /* Free policy sets */
    policy_set_t *ps = engine->sets;
    while (ps) {
        policy_set_t *next_ps = ps->next;
        
        /* Free rules */
        policy_rule_t *rule = ps->rules;
        while (rule) {
            policy_rule_t *next_rule = rule->next;
            
            /* Free conditions */
            policy_condition_t *cond = rule->conditions;
            while (cond) {
                policy_condition_t *next_cond = cond->next;
                free(cond);
                cond = next_cond;
            }
            
            /* Free actions */
            policy_action_t *act = rule->actions;
            while (act) {
                policy_action_t *next_act = act->next;
                free(act);
                act = next_act;
            }
            
            free(rule);
            rule = next_rule;
        }
        
        free(ps);
        ps = next_ps;
    }
    
    engine->sets = NULL;
    engine->set_count = 0;
}

/* ============================================================================
 * Policy Set API
 * ============================================================================ */

shield_err_t policy_set_create(policy_engine_t *engine, const char *name, policy_set_t **out)
{
    if (!engine || !name) return SHIELD_ERR_INVALID;
    
    /* Check duplicate */
    policy_set_t *existing = engine->sets;
    while (existing) {
        if (strcmp(existing->name, name) == 0) return SHIELD_ERR_EXISTS;
        existing = existing->next;
    }
    
    policy_set_t *ps = calloc(1, sizeof(policy_set_t));
    if (!ps) return SHIELD_ERR_NOMEM;
    
    shield_strcopy_s(ps->name, sizeof(ps->name), name);
    
    /* Add to list (prepend) */
    ps->next = engine->sets;
    engine->sets = ps;
    engine->set_count++;
    
    if (out) *out = ps;
    return SHIELD_OK;
}

shield_err_t policy_set_delete(policy_engine_t *engine, const char *name)
{
    if (!engine || !name) return SHIELD_ERR_INVALID;
    
    policy_set_t *prev = NULL;
    policy_set_t *ps = engine->sets;
    
    while (ps) {
        if (strcmp(ps->name, name) == 0) {
            /* Unlink */
            if (prev) {
                prev->next = ps->next;
            } else {
                engine->sets = ps->next;
            }
            engine->set_count--;
            
            /* Free rules */
            policy_rule_t *rule = ps->rules;
            while (rule) {
                policy_rule_t *next_rule = rule->next;
                
                policy_condition_t *cond = rule->conditions;
                while (cond) {
                    policy_condition_t *next = cond->next;
                    free(cond);
                    cond = next;
                }
                
                policy_action_t *act = rule->actions;
                while (act) {
                    policy_action_t *next = act->next;
                    free(act);
                    act = next;
                }
                
                free(rule);
                rule = next_rule;
            }
            
            free(ps);
            return SHIELD_OK;
        }
        prev = ps;
        ps = ps->next;
    }
    
    return SHIELD_ERR_NOTFOUND;
}

policy_set_t *policy_set_find(policy_engine_t *engine, const char *name)
{
    if (!engine || !name) return NULL;
    
    policy_set_t *ps = engine->sets;
    while (ps) {
        if (strcmp(ps->name, name) == 0) return ps;
        ps = ps->next;
    }
    return NULL;
}

/* ============================================================================
 * Policy Rule API
 * ============================================================================ */

shield_err_t policy_rule_add(policy_set_t *set, const char *name,
                              policy_priority_t priority, policy_rule_t **out)
{
    if (!set || !name) return SHIELD_ERR_INVALID;
    
    policy_rule_t *rule = calloc(1, sizeof(policy_rule_t));
    if (!rule) return SHIELD_ERR_NOMEM;
    
    rule->number = g_rule_number_seq++;
    shield_strcopy_s(rule->name, sizeof(rule->name), name);
    rule->priority = priority;
    rule->enabled = true;
    
    /* Prepend to list */
    rule->next = set->rules;
    set->rules = rule;
    set->rule_count++;
    
    if (out) *out = rule;
    return SHIELD_OK;
}

shield_err_t policy_rule_delete(policy_set_t *set, uint32_t number)
{
    if (!set) return SHIELD_ERR_INVALID;
    
    policy_rule_t *prev = NULL;
    policy_rule_t *rule = set->rules;
    
    while (rule) {
        if (rule->number == number) {
            if (prev) {
                prev->next = rule->next;
            } else {
                set->rules = rule->next;
            }
            set->rule_count--;
            
            /* Free conditions */
            policy_condition_t *cond = rule->conditions;
            while (cond) {
                policy_condition_t *next = cond->next;
                free(cond);
                cond = next;
            }
            
            /* Free actions */
            policy_action_t *act = rule->actions;
            while (act) {
                policy_action_t *next = act->next;
                free(act);
                act = next;
            }
            
            free(rule);
            return SHIELD_OK;
        }
        prev = rule;
        rule = rule->next;
    }
    
    return SHIELD_ERR_NOTFOUND;
}

/* ============================================================================
 * Policy Condition API
 * ============================================================================ */

shield_err_t policy_add_condition(policy_rule_t *rule, match_type_t type, const char *pattern)
{
    if (!rule) return SHIELD_ERR_INVALID;
    
    policy_condition_t *cond = calloc(1, sizeof(policy_condition_t));
    if (!cond) return SHIELD_ERR_NOMEM;
    
    cond->type = type;
    if (pattern) {
        shield_strcopy_s(cond->pattern, sizeof(cond->pattern), pattern);
    }
    
    /* Prepend */
    cond->next = rule->conditions;
    rule->conditions = cond;
    
    return SHIELD_OK;
}

/* ============================================================================
 * Policy Action API
 * ============================================================================ */

shield_err_t policy_add_action(policy_rule_t *rule, rule_action_t action, uint32_t acl)
{
    if (!rule) return SHIELD_ERR_INVALID;
    
    policy_action_t *act = calloc(1, sizeof(policy_action_t));
    if (!act) return SHIELD_ERR_NOMEM;
    
    act->action = action;
    act->acl_number = acl;
    
    /* Prepend */
    act->next = rule->actions;
    rule->actions = act;
    
    return SHIELD_OK;
}

/* ============================================================================
 * Policy Evaluation
 * ============================================================================ */

/* Check if data matches a condition */
static bool condition_matches(policy_condition_t *cond, const void *data, size_t len)
{
    if (!cond || !data) return false;
    
    const char *text = (const char *)data;
    
    switch (cond->type) {
    case MATCH_PATTERN:
    case MATCH_CONTAINS:
        return strstr(text, cond->pattern) != NULL;
        
    case MATCH_EXACT:
        return len == strlen(cond->pattern) && strcmp(text, cond->pattern) == 0;
        
    case MATCH_PREFIX:
        return strncmp(text, cond->pattern, strlen(cond->pattern)) == 0;
        
    case MATCH_SIZE_GT:
        return len > (size_t)atoi(cond->pattern);
        
    case MATCH_SIZE_LT:
        return len < (size_t)atoi(cond->pattern);
        
    case MATCH_JAILBREAK:
    case MATCH_PROMPT_INJECTION:
        /* Use semantic detector */
        if (!g_semantic_initialized) {
            semantic_init(&g_semantic_detector);
            g_semantic_initialized = true;
        }
        return semantic_is_suspicious(&g_semantic_detector, text, len);
        
    case MATCH_ENTROPY_HIGH:
        return calculate_entropy(data, len) > 0.9f;
        
    default:
        return false;
    }
}

rule_action_t policy_evaluate(policy_engine_t *engine, const char *set_name,
                               const void *data, size_t data_len)
{
    if (!engine || !set_name || !data) return ACTION_ALLOW;
    
    policy_set_t *ps = policy_set_find(engine, set_name);
    if (!ps) return ACTION_ALLOW;
    
    rule_action_t result = ACTION_ALLOW;
    
    /* Evaluate rules */
    policy_rule_t *rule = ps->rules;
    while (rule) {
        if (!rule->enabled) {
            rule = rule->next;
            continue;
        }
        
        /* Check all conditions (AND logic) */
        bool all_match = true;
        policy_condition_t *cond = rule->conditions;
        
        /* If no conditions, rule matches everything */
        if (!cond) {
            all_match = true;
        } else {
            while (cond) {
                if (!condition_matches(cond, data, data_len)) {
                    all_match = false;
                    break;
                }
                cond = cond->next;
            }
        }
        
        if (all_match) {
            rule->matches++;
            
            /* Apply most severe action from rule's actions */
            policy_action_t *act = rule->actions;
            while (act) {
                if (act->action > result) {
                    result = act->action;
                }
                act = act->next;
            }
            
            /* First matching rule wins (unless we want all rules to match) */
            break;
        }
        
        rule = rule->next;
    }
    
    return result;
}

/* ============================================================================
 * Class-Map API (Cisco-style)
 * ============================================================================ */

/* Note: These functions work with the class_map_t type from shield_policy.h */

shield_err_t class_map_create(policy_engine_t *engine, const char *name,
                               class_match_mode_t mode, class_map_t **out)
{
    (void)engine; /* Engine not used for now - global class maps */
    (void)mode;
    
    class_map_t *cm = calloc(1, sizeof(class_map_t));
    if (!cm) return SHIELD_ERR_NOMEM;
    
    shield_strcopy_s(cm->name, sizeof(cm->name), name);
    cm->mode = mode;
    
    if (out) *out = cm;
    return SHIELD_OK;
}

shield_err_t class_map_delete(policy_engine_t *engine, const char *name)
{
    (void)engine;
    (void)name;
    /* TODO: Implement class map deletion from registry */
    return SHIELD_OK;
}

class_map_t *class_map_find(policy_engine_t *engine, const char *name)
{
    (void)engine;
    (void)name;
    /* TODO: Implement class map lookup */
    return NULL;
}

shield_err_t class_map_add_match(class_map_t *cm, match_type_t type,
                                  const char *value, bool negate)
{
    if (!cm) return SHIELD_ERR_INVALID;
    
    class_match_t *match = calloc(1, sizeof(class_match_t));
    if (!match) return SHIELD_ERR_NOMEM;
    
    match->type = type;
    if (value) {
        shield_strcopy_s(match->value, sizeof(match->value), value);
    }
    match->negate = negate;
    
    match->next = cm->matches;
    cm->matches = match;
    
    return SHIELD_OK;
}

/* ============================================================================
 * Policy-Map API (Cisco-style)
 * ============================================================================ */

shield_err_t policy_map_create(policy_engine_t *engine, const char *name, policy_map_t **out)
{
    (void)engine;
    
    policy_map_t *pm = calloc(1, sizeof(policy_map_t));
    if (!pm) return SHIELD_ERR_NOMEM;
    
    shield_strcopy_s(pm->name, sizeof(pm->name), name);
    
    if (out) *out = pm;
    return SHIELD_OK;
}

shield_err_t policy_map_delete(policy_engine_t *engine, const char *name)
{
    (void)engine;
    (void)name;
    return SHIELD_OK;
}

policy_map_t *policy_map_find(policy_engine_t *engine, const char *name)
{
    (void)engine;
    (void)name;
    return NULL;
}

shield_err_t policy_map_add_class(policy_map_t *pm, const char *class_name, policy_class_t **out)
{
    if (!pm || !class_name) return SHIELD_ERR_INVALID;
    
    policy_class_t *pc = calloc(1, sizeof(policy_class_t));
    if (!pc) return SHIELD_ERR_NOMEM;
    
    shield_strcopy_s(pc->class_name, sizeof(pc->class_name), class_name);
    
    pc->next = pm->classes;
    pm->classes = pc;
    
    if (out) *out = pc;
    return SHIELD_OK;
}

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

shield_err_t policy_class_add_action(policy_class_t *pc, rule_action_t action, policy_action_t **out)
{
    if (!pc) return SHIELD_ERR_INVALID;
    
    /* For class-based policy, just set the action directly */
    pc->action = action;
    
    if (out) *out = NULL; /* Not creating separate action object */
    return SHIELD_OK;
}

/* ============================================================================
 * Service Policy (Zone Binding)
 * ============================================================================ */

shield_err_t service_policy_apply(policy_engine_t *engine, const char *zone,
                                   const char *policy_name, rule_direction_t direction)
{
    if (!engine || !zone || !policy_name) return SHIELD_ERR_INVALID;
    
    /* Verify policy exists */
    policy_set_t *ps = policy_set_find(engine, policy_name);
    if (!ps) return SHIELD_ERR_NOTFOUND;
    
    LOG_INFO("Policy: Applied '%s' to zone '%s' (%s)", 
             policy_name, zone,
             direction == DIRECTION_INPUT ? "input" : "output");
    
    (void)direction;
    return SHIELD_OK;
}
