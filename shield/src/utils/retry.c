/*
 * SENTINEL Shield - Retry Implementation
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <math.h>

#include "shield_retry.h"
#include "shield_timer.h"

/* Random jitter (0.5 to 1.5 multiplier) */
static float random_jitter(void)
{
    return 0.5f + (float)(rand() % 100) / 100.0f;
}

/* Default policy */
void retry_policy_default(retry_policy_t *policy)
{
    if (!policy) return;
    
    policy->max_attempts = 3;
    policy->backoff = BACKOFF_EXPONENTIAL;
    policy->initial_delay_ms = 100;
    policy->max_delay_ms = 10000;
    policy->multiplier = 2.0f;
    policy->retry_on_timeout = true;
}

/* Aggressive policy */
void retry_policy_aggressive(retry_policy_t *policy)
{
    if (!policy) return;
    
    policy->max_attempts = 5;
    policy->backoff = BACKOFF_JITTER;
    policy->initial_delay_ms = 50;
    policy->max_delay_ms = 30000;
    policy->multiplier = 2.0f;
    policy->retry_on_timeout = true;
}

/* Conservative policy */
void retry_policy_conservative(retry_policy_t *policy)
{
    if (!policy) return;
    
    policy->max_attempts = 2;
    policy->backoff = BACKOFF_CONSTANT;
    policy->initial_delay_ms = 1000;
    policy->max_delay_ms = 5000;
    policy->multiplier = 1.0f;
    policy->retry_on_timeout = false;
}

/* Initialize */
shield_err_t retry_init(retry_context_t *ctx, const retry_policy_t *policy)
{
    if (!ctx) return SHIELD_ERR_INVALID;
    
    memset(ctx, 0, sizeof(*ctx));
    
    if (policy) {
        ctx->policy = *policy;
    } else {
        retry_policy_default(&ctx->policy);
    }
    
    ctx->current_delay_ms = ctx->policy.initial_delay_ms;
    ctx->attempt = 0;
    
    return SHIELD_OK;
}

/* Should continue */
bool retry_should_continue(retry_context_t *ctx)
{
    if (!ctx) return false;
    if (ctx->success) return false;
    
    return ctx->attempt < ctx->policy.max_attempts;
}

/* Wait between retries */
void retry_wait(retry_context_t *ctx)
{
    if (!ctx || ctx->attempt == 0) {
        if (ctx) ctx->attempt++;
        return;
    }
    
    uint64_t delay = ctx->current_delay_ms;
    
    switch (ctx->policy.backoff) {
    case BACKOFF_NONE:
        delay = 0;
        break;
        
    case BACKOFF_CONSTANT:
        delay = ctx->policy.initial_delay_ms;
        break;
        
    case BACKOFF_LINEAR:
        delay = ctx->policy.initial_delay_ms * ctx->attempt;
        break;
        
    case BACKOFF_EXPONENTIAL:
        delay = (uint64_t)(ctx->policy.initial_delay_ms * 
                          pow(ctx->policy.multiplier, ctx->attempt - 1));
        break;
        
    case BACKOFF_JITTER:
        delay = (uint64_t)(ctx->policy.initial_delay_ms * 
                          pow(ctx->policy.multiplier, ctx->attempt - 1) *
                          random_jitter());
        break;
    }
    
    /* Cap delay */
    if (delay > ctx->policy.max_delay_ms) {
        delay = ctx->policy.max_delay_ms;
    }
    
    ctx->current_delay_ms = delay;
    ctx->total_delay_ms += delay;
    
    if (delay > 0) {
        sleep_ms(delay);
    }
    
    ctx->attempt++;
}

/* Record success */
void retry_success(retry_context_t *ctx)
{
    if (ctx) {
        ctx->success = true;
    }
}

/* Record failure */
void retry_failure(retry_context_t *ctx, int error_code)
{
    if (ctx) {
        ctx->last_error = error_code;
        ctx->success = false;
    }
}
