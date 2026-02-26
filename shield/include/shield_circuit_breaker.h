/*
 * SENTINEL Shield - Circuit Breaker
 * 
 * Prevent cascade failures
 */

#ifndef SHIELD_CIRCUIT_BREAKER_H
#define SHIELD_CIRCUIT_BREAKER_H

#include "shield_common.h"

/* Circuit breaker states */
typedef enum breaker_state {
    BREAKER_CLOSED,         /* Normal operation */
    BREAKER_OPEN,           /* Failing, rejecting requests */
    BREAKER_HALF_OPEN,      /* Testing recovery */
} breaker_state_t;

/* Circuit breaker */
typedef struct circuit_breaker {
    char            name[64];
    breaker_state_t state;
    
    /* Thresholds */
    int             failure_threshold;
    int             success_threshold;
    uint64_t        timeout_ms;
    
    /* Counters */
    int             failure_count;
    int             success_count;
    int             total_requests;
    
    /* Timing */
    uint64_t        last_failure_time;
    uint64_t        last_state_change;
    
    /* Callbacks */
    void            (*on_open)(struct circuit_breaker *);
    void            (*on_close)(struct circuit_breaker *);
    void            *user_data;
} circuit_breaker_t;

/* API */
shield_err_t breaker_init(circuit_breaker_t *breaker, const char *name,
                            int failure_threshold, uint64_t timeout_ms);
void breaker_destroy(circuit_breaker_t *breaker);

/* Use */
bool breaker_allow(circuit_breaker_t *breaker);
void breaker_success(circuit_breaker_t *breaker);
void breaker_failure(circuit_breaker_t *breaker);

/* State */
breaker_state_t breaker_state(circuit_breaker_t *breaker);
const char *breaker_state_string(breaker_state_t state);

/* Manual control */
void breaker_reset(circuit_breaker_t *breaker);
void breaker_trip(circuit_breaker_t *breaker);

#endif /* SHIELD_CIRCUIT_BREAKER_H */
