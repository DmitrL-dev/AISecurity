/*
 * SENTINEL Shield - Response Validator Implementation
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>

#include "shield_response_validator.h"
#include "shield_string.h"
#include "shield_output_filter.h"

/* Harmful content keywords */
static const char *HARMFUL_PATTERNS[] = {
    "how to make a bomb",
    "how to hack",
    "how to kill",
    "how to synthesize drugs",
    NULL
};

/* Prompt leak indicators */
static const char *LEAK_PATTERNS[] = {
    "my system prompt is",
    "my instructions are",
    "i was told to",
    "my rules are",
    NULL
};

/* Initialize */
shield_err_t validator_init(response_validator_t *v)
{
    if (!v) return SHIELD_ERR_INVALID;
    
    memset(v, 0, sizeof(*v));
    
    v->config.check_secrets = true;
    v->config.check_pii = true;
    v->config.check_harmful = true;
    v->config.check_prompt_leak = true;
    v->config.check_length = false;
    v->config.max_length = 100000;
    v->config.min_length = 0;
    
    return SHIELD_OK;
}

/* Destroy */
void validator_destroy(response_validator_t *v)
{
    if (!v) return;
    
    if (v->config.forbidden_words) {
        for (int i = 0; i < v->config.forbidden_count; i++) {
            free(v->config.forbidden_words[i]);
        }
        free(v->config.forbidden_words);
    }
    
    if (v->config.required_phrases) {
        for (int i = 0; i < v->config.required_count; i++) {
            free(v->config.required_phrases[i]);
        }
        free(v->config.required_phrases);
    }
}

/* Set max length */
void validator_set_max_length(response_validator_t *v, int max)
{
    if (v) {
        v->config.max_length = max;
        v->config.check_length = true;
    }
}

/* Add forbidden word */
shield_err_t validator_add_forbidden(response_validator_t *v, const char *word)
{
    if (!v || !word) return SHIELD_ERR_INVALID;
    
    if (!v->config.forbidden_words) {
        v->config.forbidden_words = malloc(100 * sizeof(char *));
        if (!v->config.forbidden_words) return SHIELD_ERR_NOMEM;
    }
    
    if (v->config.forbidden_count >= 100) return SHIELD_ERR_NOMEM;
    
    v->config.forbidden_words[v->config.forbidden_count++] = strdup(word);
    
    return SHIELD_OK;
}

/* Add required phrase */
shield_err_t validator_add_required(response_validator_t *v, const char *phrase)
{
    if (!v || !phrase) return SHIELD_ERR_INVALID;
    
    if (!v->config.required_phrases) {
        v->config.required_phrases = malloc(100 * sizeof(char *));
        if (!v->config.required_phrases) return SHIELD_ERR_NOMEM;
    }
    
    if (v->config.required_count >= 100) return SHIELD_ERR_NOMEM;
    
    v->config.required_phrases[v->config.required_count++] = strdup(phrase);
    
    return SHIELD_OK;
}

/* Check for secrets */
bool response_contains_secrets(const char *response, size_t len)
{
    if (!response) return false;
    
    /* API key patterns */
    if (strstr(response, "sk-") ||
        strstr(response, "ghp_") ||
        strstr(response, "AKIA") ||
        str_find_i(response, "api_key") ||
        str_find_i(response, "api key") ||
        str_find_i(response, "secret_key") ||
        str_find_i(response, "access_token")) {
        return true;
    }
    
    return false;
}

/* Check for PII */
bool response_contains_pii(const char *response, size_t len)
{
    if (!response) return false;
    
    /* SSN pattern: XXX-XX-XXXX */
    for (size_t i = 0; i + 10 < len; i++) {
        if (isdigit((unsigned char)response[i]) &&
            isdigit((unsigned char)response[i+1]) &&
            isdigit((unsigned char)response[i+2]) &&
            response[i+3] == '-' &&
            isdigit((unsigned char)response[i+4]) &&
            isdigit((unsigned char)response[i+5]) &&
            response[i+6] == '-' &&
            isdigit((unsigned char)response[i+7]) &&
            isdigit((unsigned char)response[i+8]) &&
            isdigit((unsigned char)response[i+9]) &&
            isdigit((unsigned char)response[i+10])) {
            return true;
        }
    }
    
    return false;
}

/* Check for harmful content */
bool response_is_harmful(const char *response, size_t len)
{
    if (!response) return false;
    
    for (int i = 0; HARMFUL_PATTERNS[i]; i++) {
        if (str_find_i(response, HARMFUL_PATTERNS[i])) {
            return true;
        }
    }
    
    return false;
}

/* Check for prompt leak */
static bool response_leaks_prompt(const char *response)
{
    if (!response) return false;
    
    for (int i = 0; LEAK_PATTERNS[i]; i++) {
        if (str_find_i(response, LEAK_PATTERNS[i])) {
            return true;
        }
    }
    
    return false;
}

/* Validate response */
shield_err_t validate_response(response_validator_t *v,
                                 const char *response, size_t len,
                                 const char *original_prompt,
                                 validation_result_t *result)
{
    if (!v || !response || !result) return SHIELD_ERR_INVALID;
    
    memset(result, 0, sizeof(*result));
    result->valid = true;
    result->quality_score = 1.0f;
    
    v->validated++;
    
    /* Length check */
    if (v->config.check_length) {
        if ((int)len > v->config.max_length) {
            result->valid = false;
            strncpy(result->issues[result->issues_count++],
                    "Response exceeds maximum length", sizeof(result->issues[0]) - 1);
            result->quality_score -= 0.2f;
        }
        if ((int)len < v->config.min_length) {
            result->valid = false;
            strncpy(result->issues[result->issues_count++],
                    "Response below minimum length", sizeof(result->issues[0]) - 1);
            result->quality_score -= 0.1f;
        }
    }
    
    /* Secrets check */
    if (v->config.check_secrets) {
        result->contains_secrets = response_contains_secrets(response, len);
        if (result->contains_secrets) {
            result->valid = false;
            strncpy(result->issues[result->issues_count++],
                    "Response contains potential secrets/API keys", sizeof(result->issues[0]) - 1);
            result->quality_score -= 0.3f;
        }
    }
    
    /* PII check */
    if (v->config.check_pii) {
        result->contains_pii = response_contains_pii(response, len);
        if (result->contains_pii) {
            result->valid = false;
            strncpy(result->issues[result->issues_count++],
                    "Response contains PII (SSN, credit card, etc.)", sizeof(result->issues[0]) - 1);
            result->quality_score -= 0.3f;
        }
    }
    
    /* Harmful check */
    if (v->config.check_harmful) {
        result->harmful_content = response_is_harmful(response, len);
        if (result->harmful_content) {
            result->valid = false;
            strncpy(result->issues[result->issues_count++],
                    "Response contains harmful content", sizeof(result->issues[0]) - 1);
            result->quality_score -= 0.5f;
        }
    }
    
    /* Prompt leak check */
    if (v->config.check_prompt_leak) {
        result->prompt_leak = response_leaks_prompt(response);
        if (result->prompt_leak) {
            result->valid = false;
            strncpy(result->issues[result->issues_count++],
                    "Response may leak system prompt", sizeof(result->issues[0]) - 1);
            result->quality_score -= 0.4f;
        }
    }
    
    /* Forbidden words */
    for (int i = 0; i < v->config.forbidden_count && result->issues_count < 5; i++) {
        if (str_find_i(response, v->config.forbidden_words[i])) {
            result->valid = false;
            char issue[128];
            snprintf(issue, sizeof(issue), "Contains forbidden word: %s",
                     v->config.forbidden_words[i]);
            strncpy(result->issues[result->issues_count++], issue, sizeof(result->issues[0]) - 1);
            result->quality_score -= 0.1f;
        }
    }
    
    /* Required phrases */
    for (int i = 0; i < v->config.required_count; i++) {
        if (!str_find_i(response, v->config.required_phrases[i])) {
            result->valid = false;
            if (result->issues_count < 5) {
                char issue[128];
                snprintf(issue, sizeof(issue), "Missing required phrase: %s",
                         v->config.required_phrases[i]);
                strncpy(result->issues[result->issues_count++], issue, sizeof(result->issues[0]) - 1);
            }
            result->quality_score -= 0.1f;
        }
    }
    
    /* Clamp quality score */
    if (result->quality_score < 0) result->quality_score = 0;
    
    if (!result->valid) {
        v->rejected++;
    }
    
    return SHIELD_OK;
}
