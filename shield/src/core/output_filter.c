/*
 * SENTINEL Shield - Output Filter Implementation
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>

#include "shield_output_filter.h"
#include "shield_string.h"

/* PII regex patterns - reserved for future regex engine */
/* Currently using simpler is_ssn(), is_credit_card() functions */
#if 0
static const char *PII_PATTERNS[] = {
    "\\d{3}-\\d{2}-\\d{4}",           /* SSN */
    "\\d{4}[- ]?\\d{4}[- ]?\\d{4}[- ]?\\d{4}",  /* Credit card */
    NULL
};

static const char *SECRET_PATTERNS[] = {
    "sk-[a-zA-Z0-9]{48}",             /* OpenAI key */
    "ghp_[a-zA-Z0-9]{36}",            /* GitHub PAT */
    "AKIA[0-9A-Z]{16}",               /* AWS Access Key */
    "password[\"':]\\s*[\"'][^\"']+", /* Password in config */
    NULL
};
#endif

/* Initialize */
shield_err_t output_filter_init(output_filter_t *filter)
{
    if (!filter) return SHIELD_ERR_INVALID;
    
    memset(filter, 0, sizeof(*filter));
    filter->enabled = true;
    filter->filter_pii = true;
    filter->filter_secrets = true;
    
    return SHIELD_OK;
}

/* Destroy */
void output_filter_destroy(output_filter_t *filter)
{
    if (!filter) return;
    
    filter_rule_t *rule = filter->rules;
    while (rule) {
        filter_rule_t *next = rule->next;
        free(rule);
        rule = next;
    }
    
    filter->rules = NULL;
}

/* Add rule */
shield_err_t filter_add_rule(output_filter_t *filter, const char *name,
                               const char *pattern, redact_type_t type)
{
    if (!filter || !name || !pattern) {
        return SHIELD_ERR_INVALID;
    }
    
    filter_rule_t *rule = calloc(1, sizeof(filter_rule_t));
    if (!rule) return SHIELD_ERR_NOMEM;
    
    strncpy(rule->name, name, sizeof(rule->name) - 1);
    strncpy(rule->pattern, pattern, sizeof(rule->pattern) - 1);
    rule->type = type;
    rule->enabled = true;
    strcpy(rule->replacement, "[REDACTED]");
    
    rule->next = filter->rules;
    filter->rules = rule;
    filter->rule_count++;
    
    return SHIELD_OK;
}

/* Remove rule */
shield_err_t filter_remove_rule(output_filter_t *filter, const char *name)
{
    if (!filter || !name) return SHIELD_ERR_INVALID;
    
    filter_rule_t **pp = &filter->rules;
    while (*pp) {
        if (strcmp((*pp)->name, name) == 0) {
            filter_rule_t *rule = *pp;
            *pp = rule->next;
            free(rule);
            filter->rule_count--;
            return SHIELD_OK;
        }
        pp = &(*pp)->next;
    }
    
    return SHIELD_ERR_NOTFOUND;
}

/* Check for SSN pattern */
static bool is_ssn(const char *s)
{
    /* Format: XXX-XX-XXXX */
    if (strlen(s) < 11) return false;
    
    return isdigit((unsigned char)s[0]) && isdigit((unsigned char)s[1]) &&
           isdigit((unsigned char)s[2]) && s[3] == '-' &&
           isdigit((unsigned char)s[4]) && isdigit((unsigned char)s[5]) &&
           s[6] == '-' && isdigit((unsigned char)s[7]) &&
           isdigit((unsigned char)s[8]) && isdigit((unsigned char)s[9]) &&
           isdigit((unsigned char)s[10]);
}

/* Check for credit card */
static bool is_credit_card(const char *s)
{
    int digits = 0;
    const char *p = s;
    
    while (*p && digits < 20) {
        if (isdigit((unsigned char)*p)) digits++;
        else if (*p != ' ' && *p != '-') break;
        p++;
    }
    
    return digits == 16;
}

/* Check for API key patterns */
static bool is_api_key(const char *s)
{
    if (strncmp(s, "sk-", 3) == 0) return true;
    if (strncmp(s, "ghp_", 4) == 0) return true;
    if (strncmp(s, "AKIA", 4) == 0) return true;
    if (strncmp(s, "Bearer ", 7) == 0) return true;
    
    return false;
}

/* Filter content */
char *filter_content(output_filter_t *filter, const char *content,
                      size_t *out_len, int *redactions)
{
    if (!filter || !content) return NULL;
    
    size_t len = strlen(content);
    char *result = malloc(len * 2 + 1);  /* Extra space for replacements */
    if (!result) return NULL;
    
    int redact_count = 0;
    const char *src = content;
    char *dst = result;
    
    while (*src) {
        bool redacted = false;
        
        /* Check PII */
        if (filter->filter_pii) {
            if (is_ssn(src)) {
                strcpy(dst, "[SSN-REDACTED]");
                dst += 14;
                src += 11;
                redact_count++;
                redacted = true;
            } else if (is_credit_card(src)) {
                strcpy(dst, "[CARD-REDACTED]");
                dst += 15;
                /* Skip the card number */
                while (*src && (isdigit((unsigned char)*src) || *src == ' ' || *src == '-')) {
                    src++;
                }
                redact_count++;
                redacted = true;
            }
        }
        
        /* Check secrets */
        if (!redacted && filter->filter_secrets) {
            if (is_api_key(src)) {
                strcpy(dst, "[KEY-REDACTED]");
                dst += 14;
                /* Skip until whitespace */
                while (*src && !isspace((unsigned char)*src)) {
                    src++;
                }
                redact_count++;
                redacted = true;
            }
        }
        
        /* Check emails */
        if (!redacted && filter->filter_emails) {
            /* Simple email detection */
            const char *at = strchr(src, '@');
            if (at && at > src && at < src + 50) {
                bool has_dot = strchr(at, '.') != NULL;
                if (has_dot) {
                    strcpy(dst, "[EMAIL-REDACTED]");
                    dst += 16;
                    /* Skip email */
                    while (*src && !isspace((unsigned char)*src) && *src != ',' && *src != '>') {
                        src++;
                    }
                    redact_count++;
                    redacted = true;
                }
            }
        }
        
        /* Custom rules */
        if (!redacted) {
            filter_rule_t *rule = filter->rules;
            while (rule && !redacted) {
                if (rule->enabled) {
                    const char *match = strstr(src, rule->pattern);
                    if (match == src) {
                        size_t plen = strlen(rule->pattern);
                        switch (rule->type) {
                        case REDACT_MASK:
                            strcpy(dst, rule->replacement);
                            dst += strlen(rule->replacement);
                            break;
                        case REDACT_REMOVE:
                            /* Skip pattern */
                            break;
                        case REDACT_TRUNCATE:
                            *dst = '\0';
                            goto done;
                        default:
                            strcpy(dst, "[REDACTED]");
                            dst += 10;
                        }
                        src += plen;
                        rule->hits++;
                        redact_count++;
                        redacted = true;
                    }
                }
                rule = rule->next;
            }
        }
        
        if (!redacted) {
            *dst++ = *src++;
        }
    }
    
done:
    *dst = '\0';
    
    if (out_len) *out_len = dst - result;
    if (redactions) *redactions = redact_count;
    
    filter->total_filtered++;
    filter->total_chars_removed += len - (dst - result);
    
    return result;
}

/* Enable PII filtering */
void filter_enable_pii(output_filter_t *filter, bool enable)
{
    if (filter) filter->filter_pii = enable;
}

/* Enable secret filtering */
void filter_enable_secrets(output_filter_t *filter, bool enable)
{
    if (filter) filter->filter_secrets = enable;
}

/* Check if contains sensitive */
bool filter_contains_sensitive(output_filter_t *filter, const char *content)
{
    if (!filter || !content) return false;
    
    const char *p = content;
    while (*p) {
        if (filter->filter_pii) {
            if (is_ssn(p) || is_credit_card(p)) return true;
        }
        if (filter->filter_secrets) {
            if (is_api_key(p)) return true;
        }
        p++;
    }
    
    return false;
}
