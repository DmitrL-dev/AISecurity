/*
 * SENTINEL Shield - Output Filter
 * 
 * Filter and redact sensitive content in AI responses
 */

#ifndef SHIELD_OUTPUT_FILTER_H
#define SHIELD_OUTPUT_FILTER_H

#include "shield_common.h"

/* Redaction types */
typedef enum redact_type {
    REDACT_MASK,        /* Replace with [REDACTED] */
    REDACT_HASH,        /* Replace with hash */
    REDACT_REMOVE,      /* Remove entirely */
    REDACT_TRUNCATE,    /* Truncate at match */
} redact_type_t;

/* Filter rule */
typedef struct filter_rule {
    char            name[64];
    char            pattern[256];
    redact_type_t   type;
    char            replacement[128];
    bool            case_insensitive;
    bool            enabled;
    int             priority;
    uint64_t        hits;
    struct filter_rule *next;
} filter_rule_t;

/* Output filter */
typedef struct output_filter {
    filter_rule_t   *rules;
    int             rule_count;
    bool            enabled;
    
    /* Built-in patterns */
    bool            filter_pii;         /* SSN, credit cards, etc */
    bool            filter_secrets;     /* API keys, passwords */
    bool            filter_code;        /* Source code blocks */
    bool            filter_urls;        /* External URLs */
    bool            filter_emails;      /* Email addresses */
    bool            filter_phones;      /* Phone numbers */
    
    /* Stats */
    uint64_t        total_filtered;
    uint64_t        total_chars_removed;
} output_filter_t;

/* API */
shield_err_t output_filter_init(output_filter_t *filter);
void output_filter_destroy(output_filter_t *filter);

/* Rules */
shield_err_t filter_add_rule(output_filter_t *filter, const char *name,
                               const char *pattern, redact_type_t type);
shield_err_t filter_remove_rule(output_filter_t *filter, const char *name);

/* Filter content */
char *filter_content(output_filter_t *filter, const char *content,
                      size_t *out_len, int *redactions);

/* Built-in filters */
void filter_enable_pii(output_filter_t *filter, bool enable);
void filter_enable_secrets(output_filter_t *filter, bool enable);

/* Check only (don't modify) */
bool filter_contains_sensitive(output_filter_t *filter, const char *content);

#endif /* SHIELD_OUTPUT_FILTER_H */
