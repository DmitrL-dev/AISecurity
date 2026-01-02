/*
 * SENTINEL Shield - Rule Engine Implementation
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <regex.h>

#include "shield_common.h"
#include "shield_rule.h"

/* Initialize rule engine */
shield_err_t rule_engine_init(rule_engine_t *engine)
{
    if (!engine) {
        return SHIELD_ERR_INVALID;
    }
    
    memset(engine, 0, sizeof(*engine));
    return SHIELD_OK;
}

/* Destroy rule engine */
void rule_engine_destroy(rule_engine_t *engine)
{
    if (!engine) {
        return;
    }
    
    access_list_t *acl = engine->lists;
    while (acl) {
        access_list_t *next_acl = acl->next;
        
        /* Free rules */
        shield_rule_t *rule = acl->rules;
        while (rule) {
            shield_rule_t *next_rule = rule->next;
            rule_clear_conditions(rule);
            free(rule);
            rule = next_rule;
        }
        
        free(acl);
        acl = next_acl;
    }
    
    engine->lists = NULL;
    engine->list_count = 0;
}

/* Create access list */
shield_err_t acl_create(rule_engine_t *engine, uint32_t number,
                        access_list_t **out)
{
    if (!engine) {
        return SHIELD_ERR_INVALID;
    }
    
    /* Check if already exists */
    if (acl_find(engine, number)) {
        return SHIELD_ERR_EXISTS;
    }
    
    access_list_t *acl = calloc(1, sizeof(access_list_t));
    if (!acl) {
        return SHIELD_ERR_NOMEM;
    }
    
    acl->number = number;
    
    /* Insert sorted by number */
    access_list_t **pp = &engine->lists;
    while (*pp && (*pp)->number < number) {
        pp = &(*pp)->next;
    }
    acl->next = *pp;
    *pp = acl;
    engine->list_count++;
    
    if (out) {
        *out = acl;
    }
    
    return SHIELD_OK;
}

/* Delete access list */
shield_err_t acl_delete(rule_engine_t *engine, uint32_t number)
{
    if (!engine) {
        return SHIELD_ERR_INVALID;
    }
    
    access_list_t **pp = &engine->lists;
    while (*pp) {
        if ((*pp)->number == number) {
            access_list_t *acl = *pp;
            *pp = acl->next;
            
            /* Free rules */
            shield_rule_t *rule = acl->rules;
            while (rule) {
                shield_rule_t *next = rule->next;
                rule_clear_conditions(rule);
                free(rule);
                rule = next;
            }
            
            free(acl);
            engine->list_count--;
            return SHIELD_OK;
        }
        pp = &(*pp)->next;
    }
    
    return SHIELD_ERR_NOTFOUND;
}

/* Find access list */
access_list_t *acl_find(rule_engine_t *engine, uint32_t number)
{
    if (!engine) {
        return NULL;
    }
    
    access_list_t *acl = engine->lists;
    while (acl) {
        if (acl->number == number) {
            return acl;
        }
        acl = acl->next;
    }
    
    return NULL;
}

/* Add rule to access list */
shield_err_t rule_add(access_list_t *acl, uint32_t number,
                      rule_action_t action, rule_direction_t direction,
                      zone_type_t zone_type, const char *zone_name,
                      shield_rule_t **out)
{
    if (!acl) {
        return SHIELD_ERR_INVALID;
    }
    
    /* Check if rule number exists */
    if (rule_find(acl, number)) {
        return SHIELD_ERR_EXISTS;
    }
    
    shield_rule_t *rule = calloc(1, sizeof(shield_rule_t));
    if (!rule) {
        return SHIELD_ERR_NOMEM;
    }
    
    rule->number = number;
    rule->action = action;
    rule->direction = direction;
    rule->zone_type = zone_type;
    if (zone_name) {
        strncpy(rule->zone_name, zone_name, SHIELD_MAX_NAME_LEN - 1);
    }
    
    /* Insert sorted by number */
    shield_rule_t **pp = &acl->rules;
    while (*pp && (*pp)->number < number) {
        pp = &(*pp)->next;
    }
    rule->next = *pp;
    *pp = rule;
    acl->rule_count++;
    
    if (out) {
        *out = rule;
    }
    
    return SHIELD_OK;
}

/* Delete rule */
shield_err_t rule_delete(access_list_t *acl, uint32_t number)
{
    if (!acl) {
        return SHIELD_ERR_INVALID;
    }
    
    shield_rule_t **pp = &acl->rules;
    while (*pp) {
        if ((*pp)->number == number) {
            shield_rule_t *rule = *pp;
            *pp = rule->next;
            rule_clear_conditions(rule);
            free(rule);
            acl->rule_count--;
            return SHIELD_OK;
        }
        pp = &(*pp)->next;
    }
    
    return SHIELD_ERR_NOTFOUND;
}

/* Find rule */
shield_rule_t *rule_find(access_list_t *acl, uint32_t number)
{
    if (!acl) {
        return NULL;
    }
    
    shield_rule_t *rule = acl->rules;
    while (rule) {
        if (rule->number == number) {
            return rule;
        }
        rule = rule->next;
    }
    
    return NULL;
}

/* Add match condition */
shield_err_t rule_add_condition(shield_rule_t *rule, match_type_t type,
                                 const char *pattern, uint32_t value)
{
    if (!rule) {
        return SHIELD_ERR_INVALID;
    }
    
    match_condition_t *cond = calloc(1, sizeof(match_condition_t));
    if (!cond) {
        return SHIELD_ERR_NOMEM;
    }
    
    cond->type = type;
    if (pattern) {
        strncpy(cond->pattern, pattern, SHIELD_MAX_PATTERN_LEN - 1);
    }
    cond->value = value;
    
    /* Append to list */
    cond->next = rule->conditions;
    rule->conditions = cond;
    
    return SHIELD_OK;
}

/* Clear conditions */
void rule_clear_conditions(shield_rule_t *rule)
{
    if (!rule) {
        return;
    }
    
    match_condition_t *cond = rule->conditions;
    while (cond) {
        match_condition_t *next = cond->next;
        free(cond);
        cond = next;
    }
    rule->conditions = NULL;
}

/* Check if data matches condition */
static bool match_condition_check(match_condition_t *cond,
                                   const void *data, size_t len)
{
    if (!cond || !data || len == 0) {
        return false;
    }
    
    const char *str = (const char *)data;
    
    switch (cond->type) {
    case MATCH_PATTERN: {
        regex_t regex;
        if (regcomp(&regex, cond->pattern, REG_EXTENDED | REG_ICASE) == 0) {
            int result = regexec(&regex, str, 0, NULL, 0);
            regfree(&regex);
            return result == 0;
        }
        return false;
    }
    
    case MATCH_CONTAINS:
        return strstr(str, cond->pattern) != NULL;
    
    case MATCH_EXACT:
        return strcmp(str, cond->pattern) == 0;
    
    case MATCH_PREFIX:
        return strncmp(str, cond->pattern, strlen(cond->pattern)) == 0;
    
    case MATCH_SUFFIX: {
        size_t plen = strlen(cond->pattern);
        if (len >= plen) {
            return strcmp(str + len - plen, cond->pattern) == 0;
        }
        return false;
    }
    
    case MATCH_SIZE_GT:
        return len > cond->value;
    
    case MATCH_SIZE_LT:
        return len < cond->value;
    
    case MATCH_ENTROPY_HIGH:
    case MATCH_ENTROPY_LOW:
        /* TODO: Calculate Shannon entropy */
        return false;
    
    case MATCH_SQL_INJECTION:
        /* Simple SQL injection detection */
        return strstr(str, "DROP") != NULL ||
               strstr(str, "DELETE") != NULL ||
               strstr(str, "INSERT") != NULL ||
               strstr(str, "UPDATE") != NULL ||
               strstr(str, "--") != NULL ||
               strstr(str, "';") != NULL;
    
    case MATCH_JAILBREAK:
    case MATCH_PROMPT_INJECTION:
        /* Simple prompt injection detection */
        return strstr(str, "ignore") != NULL ||
               strstr(str, "disregard") != NULL ||
               strstr(str, "forget") != NULL;
    
    default:
        return false;
    }
}

/* Evaluate rules */
rule_verdict_t rule_evaluate(rule_engine_t *engine, uint32_t acl_number,
                             rule_direction_t direction,
                             zone_type_t zone_type, const char *zone_name,
                             const void *data, size_t data_len)
{
    rule_verdict_t verdict = {
        .action = ACTION_ALLOW,
        .matched_rule = NULL,
        .reason = "default allow",
    };
    
    if (!engine || !data || data_len == 0) {
        return verdict;
    }
    
    access_list_t *acl = acl_find(engine, acl_number);
    if (!acl) {
        return verdict;
    }
    
    /* Iterate rules in order */
    shield_rule_t *rule = acl->rules;
    while (rule) {
        /* Check direction */
        if (rule->direction != DIRECTION_BOTH && 
            rule->direction != direction) {
            rule = rule->next;
            continue;
        }
        
        /* Check zone type */
        if (rule->zone_type != ZONE_TYPE_UNKNOWN &&
            rule->zone_type != zone_type) {
            rule = rule->next;
            continue;
        }
        
        /* Check zone name */
        if (rule->zone_name[0] != '\0' && zone_name &&
            strcmp(rule->zone_name, zone_name) != 0) {
            rule = rule->next;
            continue;
        }
        
        /* Check conditions (if any) */
        bool matched = true;
        if (rule->conditions) {
            matched = false;
            match_condition_t *cond = rule->conditions;
            while (cond) {
                if (match_condition_check(cond, data, data_len)) {
                    matched = true;
                    break;
                }
                cond = cond->next;
            }
        }
        
        if (matched) {
            rule->matches++;
            verdict.action = rule->action;
            verdict.matched_rule = rule;
            verdict.reason = rule->remark[0] ? rule->remark : "rule matched";
            return verdict;
        }
        
        rule = rule->next;
    }
    
    return verdict;
}

/* Resequence rules */
shield_err_t acl_resequence(access_list_t *acl, uint32_t start, uint32_t step)
{
    if (!acl || step == 0) {
        return SHIELD_ERR_INVALID;
    }
    
    uint32_t num = start;
    shield_rule_t *rule = acl->rules;
    while (rule) {
        rule->number = num;
        num += step;
        rule = rule->next;
    }
    
    return SHIELD_OK;
}
