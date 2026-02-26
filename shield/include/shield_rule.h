/*
 * SENTINEL Shield - Rule Engine
 * 
 * Shield rules for traffic filtering
 */

#ifndef SHIELD_RULE_H
#define SHIELD_RULE_H

#include "shield_common.h"

/* Match condition */
typedef struct match_condition {
    match_type_t    type;
    char            pattern[SHIELD_MAX_PATTERN_LEN];
    uint32_t        value;      /* For size comparisons */
    struct match_condition *next;
} match_condition_t;

/* Shield rule */
typedef struct shield_rule {
    uint32_t            number;
    rule_action_t       action;
    rule_direction_t    direction;
    zone_type_t         zone_type;  /* ZONE_TYPE_UNKNOWN = any */
    char                zone_name[SHIELD_MAX_NAME_LEN]; /* Empty = any */
    match_condition_t   *conditions;
    char                remark[SHIELD_MAX_DESC_LEN];
    bool                log_enabled;
    
    /* Statistics */
    uint64_t            matches;
    
    struct shield_rule  *next;
} shield_rule_t;

/* Access list (collection of rules) */
typedef struct access_list {
    uint32_t        number;
    shield_rule_t   *rules;
    uint32_t        rule_count;
    struct access_list *next;
} access_list_t;

/* Rule engine */
typedef struct rule_engine {
    access_list_t   *lists;
    uint32_t        list_count;
} rule_engine_t;

/* Verdict after rule evaluation */
typedef struct rule_verdict {
    rule_action_t   action;
    shield_rule_t   *matched_rule;
    const char      *reason;
} rule_verdict_t;

/* API */
shield_err_t rule_engine_init(rule_engine_t *engine);
void rule_engine_destroy(rule_engine_t *engine);

/* Access list management */
shield_err_t acl_create(rule_engine_t *engine, uint32_t number, 
                        access_list_t **out);
shield_err_t acl_delete(rule_engine_t *engine, uint32_t number);
access_list_t *acl_find(rule_engine_t *engine, uint32_t number);

/* Rule management */
shield_err_t rule_add(access_list_t *acl, uint32_t number,
                      rule_action_t action, rule_direction_t direction,
                      zone_type_t zone_type, const char *zone_name,
                      shield_rule_t **out);
shield_err_t rule_delete(access_list_t *acl, uint32_t number);
shield_rule_t *rule_find(access_list_t *acl, uint32_t number);

/* Match condition */
shield_err_t rule_add_condition(shield_rule_t *rule, match_type_t type,
                                 const char *pattern, uint32_t value);
void rule_clear_conditions(shield_rule_t *rule);

/* Evaluation */
rule_verdict_t rule_evaluate(rule_engine_t *engine, uint32_t acl_number,
                             rule_direction_t direction,
                             zone_type_t zone_type, const char *zone_name,
                             const void *data, size_t data_len);

/* Resequence */
shield_err_t acl_resequence(access_list_t *acl, uint32_t start, uint32_t step);

#endif /* SHIELD_RULE_H */
