/*
 * SENTINEL Shield - Policy Engine
 * 
 * Hierarchical policy management
 */

#ifndef SHIELD_POLICY_H
#define SHIELD_POLICY_H

#include "shield_common.h"

/* Policy priority levels */
typedef enum {
    POLICY_PRIORITY_LOW = 0,
    POLICY_PRIORITY_NORMAL,
    POLICY_PRIORITY_HIGH,
    POLICY_PRIORITY_CRITICAL
} policy_priority_t;

/* Class-map match mode */
typedef enum {
    CLASS_MATCH_ANY,
    CLASS_MATCH_ALL,
} class_match_mode_t;

/* Class-map match entry (uses match_type_t from shield_common.h) */
typedef struct class_match {
    match_type_t        type;
    char                value[256];
    bool                negate;
    struct class_match  *next;
} class_match_t;

/* Class-map */
typedef struct class_map {
    char                name[64];
    class_match_mode_t  mode;
    class_match_t       *matches;
    struct class_map    *next;
} class_map_t;

/* Policy class (inside policy-map) */
typedef struct policy_class {
    char                class_name[64];
    rule_action_t       action;
    bool                log_enabled;
    uint32_t            rate_limit;
    struct policy_class *next;
} policy_class_t;

/* Policy map */
typedef struct policy_map {
    char                name[64];
    policy_class_t      *classes;
    struct policy_map   *next;
} policy_map_t;

/* Policy action */
typedef struct policy_action {
    rule_action_t       action;
    uint32_t            acl_number;
    char                redirect_url[256];
    bool                log_enabled;
    uint32_t            rate_limit;
    struct policy_action *next;
} policy_action_t;

/* Policy match condition */
typedef struct policy_condition {
    match_type_t         type;
    char                pattern[SHIELD_MAX_PATTERN_LEN];
    struct policy_condition *next;
} policy_condition_t;

/* Policy rule */
typedef struct policy_rule {
    uint32_t            number;
    char                name[SHIELD_MAX_NAME_LEN];
    policy_priority_t   priority;
    policy_condition_t  *conditions;
    policy_action_t     *actions;
    bool                enabled;
    uint64_t            matches;
    struct policy_rule  *next;
} policy_rule_t;

/* Policy set */
typedef struct policy_set {
    char                name[SHIELD_MAX_NAME_LEN];
    policy_rule_t       *rules;
    uint32_t            rule_count;
    struct policy_set   *next;
} policy_set_t;

/* Policy engine */
typedef struct policy_engine {
    policy_set_t        *sets;
    uint32_t            set_count;
} policy_engine_t;

/* API */
shield_err_t policy_engine_init(policy_engine_t *engine);
void policy_engine_destroy(policy_engine_t *engine);

shield_err_t policy_set_create(policy_engine_t *engine, const char *name, policy_set_t **out);
shield_err_t policy_set_delete(policy_engine_t *engine, const char *name);
policy_set_t *policy_set_find(policy_engine_t *engine, const char *name);

shield_err_t policy_rule_add(policy_set_t *set, const char *name, policy_priority_t priority, policy_rule_t **out);
shield_err_t policy_rule_delete(policy_set_t *set, uint32_t number);

shield_err_t policy_add_condition(policy_rule_t *rule, match_type_t type, const char *pattern);
shield_err_t policy_add_action(policy_rule_t *rule, rule_action_t action, uint32_t acl);

rule_action_t policy_evaluate(policy_engine_t *engine, const char *set_name,
                              const void *data, size_t data_len);

/* Class-map API */
shield_err_t class_map_create(policy_engine_t *engine, const char *name,
                               class_match_mode_t mode, class_map_t **out);
shield_err_t class_map_delete(policy_engine_t *engine, const char *name);
class_map_t *class_map_find(policy_engine_t *engine, const char *name);
shield_err_t class_map_add_match(class_map_t *cm, match_type_t type,
                                  const char *value, bool negate);

/* Policy-map API */
shield_err_t policy_map_create(policy_engine_t *engine, const char *name, policy_map_t **out);
shield_err_t policy_map_delete(policy_engine_t *engine, const char *name);
policy_map_t *policy_map_find(policy_engine_t *engine, const char *name);
shield_err_t policy_map_add_class(policy_map_t *pm, const char *class_name, policy_class_t **out);
policy_class_t *policy_class_find(policy_map_t *pm, const char *class_name);
shield_err_t policy_class_add_action(policy_class_t *pc, rule_action_t action, policy_action_t **out);

/* Service policy */
shield_err_t service_policy_apply(policy_engine_t *engine, const char *zone,
                                   const char *policy_name, rule_direction_t direction);

#endif /* SHIELD_POLICY_H */
