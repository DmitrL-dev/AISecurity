/*
 * SENTINEL Shield - Circuit Breaker Implementation
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#include "shield_circuit_breaker.h"
#include "shield_timer.h"

/* Initialize */
shield_err_t breaker_init(circuit_breaker_t *breaker, const char *name,
                            int failure_threshold, uint64_t timeout_ms)
{
    if (!breaker || !name) return SHIELD_ERR_INVALID;
    
    memset(breaker, 0, sizeof(*breaker));
    strncpy(breaker->name, name, sizeof(breaker->name) - 1);
    breaker->failure_threshold = failure_threshold > 0 ? failure_threshold : 5;
    breaker->success_threshold = 3;
    breaker->timeout_ms = timeout_ms > 0 ? timeout_ms : 30000;
    breaker->state = BREAKER_CLOSED;
    
    return SHIELD_OK;
}

/* Destroy */
void breaker_destroy(circuit_breaker_t *breaker)
{
    /* Nothing to free */
    (void)breaker;
}

/* Check if request is allowed */
bool breaker_allow(circuit_breaker_t *breaker)
{
    if (!breaker) return true;
    
    breaker->total_requests++;
    
    switch (breaker->state) {
    case BREAKER_CLOSED:
        return true;
        
    case BREAKER_OPEN:
        /* Check if timeout expired */
        if (time_now_ms() - breaker->last_failure_time >= breaker->timeout_ms) {
            breaker->state = BREAKER_HALF_OPEN;
            breaker->last_state_change = time_now_ms();
            breaker->success_count = 0;
            LOG_INFO("Circuit breaker %s: OPEN -> HALF_OPEN", breaker->name);
            return true;  /* Allow one request to test */
        }
        return false;
        
    case BREAKER_HALF_OPEN:
        return true;  /* Allow requests to test recovery */
    }
    
    return true;
}

/* Record success */
void breaker_success(circuit_breaker_t *breaker)
{
    if (!breaker) return;
    
    switch (breaker->state) {
    case BREAKER_CLOSED:
        breaker->failure_count = 0;  /* Reset on success */
        break;
        
    case BREAKER_HALF_OPEN:
        breaker->success_count++;
        if (breaker->success_count >= breaker->success_threshold) {
            breaker->state = BREAKER_CLOSED;
            breaker->last_state_change = time_now_ms();
            breaker->failure_count = 0;
            LOG_INFO("Circuit breaker %s: HALF_OPEN -> CLOSED", breaker->name);
            if (breaker->on_close) {
                breaker->on_close(breaker);
            }
        }
        break;
        
    case BREAKER_OPEN:
        /* Shouldn't happen, but reset anyway */
        break;
    }
}

/* Record failure */
void breaker_failure(circuit_breaker_t *breaker)
{
    if (!breaker) return;
    
    breaker->failure_count++;
    breaker->last_failure_time = time_now_ms();
    
    switch (breaker->state) {
    case BREAKER_CLOSED:
        if (breaker->failure_count >= breaker->failure_threshold) {
            breaker->state = BREAKER_OPEN;
            breaker->last_state_change = time_now_ms();
            LOG_WARN("Circuit breaker %s: CLOSED -> OPEN (failures: %d)",
                     breaker->name, breaker->failure_count);
            if (breaker->on_open) {
                breaker->on_open(breaker);
            }
        }
        break;
        
    case BREAKER_HALF_OPEN:
        /* Single failure in half-open goes back to open */
        breaker->state = BREAKER_OPEN;
        breaker->last_state_change = time_now_ms();
        breaker->success_count = 0;
        LOG_WARN("Circuit breaker %s: HALF_OPEN -> OPEN", breaker->name);
        break;
        
    case BREAKER_OPEN:
        /* Already open */
        break;
    }
}

/* Get state */
breaker_state_t breaker_state(circuit_breaker_t *breaker)
{
    return breaker ? breaker->state : BREAKER_CLOSED;
}

/* State to string */
const char *breaker_state_string(breaker_state_t state)
{
    switch (state) {
    case BREAKER_CLOSED: return "CLOSED";
    case BREAKER_OPEN: return "OPEN";
    case BREAKER_HALF_OPEN: return "HALF_OPEN";
    default: return "UNKNOWN";
    }
}

/* Reset */
void breaker_reset(circuit_breaker_t *breaker)
{
    if (!breaker) return;
    
    breaker->state = BREAKER_CLOSED;
    breaker->failure_count = 0;
    breaker->success_count = 0;
    breaker->last_state_change = time_now_ms();
}

/* Force trip */
void breaker_trip(circuit_breaker_t *breaker)
{
    if (!breaker) return;
    
    breaker->state = BREAKER_OPEN;
    breaker->last_failure_time = time_now_ms();
    breaker->last_state_change = time_now_ms();
    
    if (breaker->on_open) {
        breaker->on_open(breaker);
    }
}
