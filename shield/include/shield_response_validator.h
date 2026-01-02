/*
 * SENTINEL Shield - Response Validator
 * 
 * Validate AI responses before returning to user
 */

#ifndef SHIELD_RESPONSE_VALIDATOR_H
#define SHIELD_RESPONSE_VALIDATOR_H

#include "shield_common.h"

/* Validation result */
typedef struct validation_result {
    bool            valid;
    int             issues_count;
    char            issues[5][128];
    float           quality_score;
    
    /* Specific checks */
    bool            contains_secrets;
    bool            contains_pii;
    bool            harmful_content;
    bool            prompt_leak;
    bool            off_topic;
} validation_result_t;

/* Validator config */
typedef struct validator_config {
    bool            check_secrets;
    bool            check_pii;
    bool            check_harmful;
    bool            check_prompt_leak;
    bool            check_length;
    
    int             max_length;
    int             min_length;
    
    /* Keywords to flag */
    char            **forbidden_words;
    int             forbidden_count;
    
    /* Required content */
    char            **required_phrases;
    int             required_count;
} validator_config_t;

/* Validator */
typedef struct response_validator {
    validator_config_t config;
    
    /* Stats */
    uint64_t        validated;
    uint64_t        rejected;
} response_validator_t;

/* API */
shield_err_t validator_init(response_validator_t *v);
void validator_destroy(response_validator_t *v);

/* Configure */
void validator_set_max_length(response_validator_t *v, int max);
shield_err_t validator_add_forbidden(response_validator_t *v, const char *word);
shield_err_t validator_add_required(response_validator_t *v, const char *phrase);

/* Validate */
shield_err_t validate_response(response_validator_t *v,
                                 const char *response, size_t len,
                                 const char *original_prompt,
                                 validation_result_t *result);

/* Quick checks */
bool response_contains_secrets(const char *response, size_t len);
bool response_contains_pii(const char *response, size_t len);
bool response_is_harmful(const char *response, size_t len);

#endif /* SHIELD_RESPONSE_VALIDATOR_H */
