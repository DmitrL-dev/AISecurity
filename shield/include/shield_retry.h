/*
 * SENTINEL Shield - Retry Logic
 * 
 * Configurable retry with backoff
 */

#ifndef SHIELD_RETRY_H
#define SHIELD_RETRY_H

#include "shield_common.h"

/* Backoff strategy */
typedef enum backoff_type {
    BACKOFF_NONE,           /* No delay */
    BACKOFF_CONSTANT,       /* Fixed delay */
    BACKOFF_LINEAR,         /* Increasing linearly */
    BACKOFF_EXPONENTIAL,    /* Doubling */
    BACKOFF_JITTER,         /* Exponential + random */
} backoff_type_t;

/* Retry policy */
typedef struct retry_policy {
    int             max_attempts;
    backoff_type_t  backoff;
    uint64_t        initial_delay_ms;
    uint64_t        max_delay_ms;
    float           multiplier;
    bool            retry_on_timeout;
} retry_policy_t;

/* Retry context */
typedef struct retry_context {
    retry_policy_t  policy;
    int             attempt;
    uint64_t        current_delay_ms;
    uint64_t        total_delay_ms;
    bool            success;
    int             last_error;
} retry_context_t;

/* API */
void retry_policy_default(retry_policy_t *policy);
void retry_policy_aggressive(retry_policy_t *policy);
void retry_policy_conservative(retry_policy_t *policy);

shield_err_t retry_init(retry_context_t *ctx, const retry_policy_t *policy);
bool retry_should_continue(retry_context_t *ctx);
void retry_wait(retry_context_t *ctx);
void retry_success(retry_context_t *ctx);
void retry_failure(retry_context_t *ctx, int error_code);

/* Helper macro */
#define RETRY_LOOP(ctx) \
    for (retry_init(&(ctx), NULL); retry_should_continue(&(ctx)); retry_wait(&(ctx)))

#endif /* SHIELD_RETRY_H */
