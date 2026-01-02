/*
 * SENTINEL Shield - Timer Utilities
 * 
 * High-precision timing and timeouts
 */

#ifndef SHIELD_TIMER_H
#define SHIELD_TIMER_H

#include "shield_common.h"

/* Timer handle */
typedef struct shield_timer {
    uint64_t        start_ns;
    uint64_t        end_ns;
    bool            running;
} shield_timer_t;

/* Timeout handle */
typedef struct shield_timeout {
    uint64_t        deadline_ns;
    uint64_t        duration_ms;
    bool            expired;
    void            (*callback)(void *);
    void            *user_data;
} shield_timeout_t;

/* Timer API */
void timer_start(shield_timer_t *timer);
void timer_stop(shield_timer_t *timer);
uint64_t timer_elapsed_ns(shield_timer_t *timer);
uint64_t timer_elapsed_us(shield_timer_t *timer);
uint64_t timer_elapsed_ms(shield_timer_t *timer);

/* Current time */
uint64_t time_now_ns(void);
uint64_t time_now_us(void);
uint64_t time_now_ms(void);

/* Timeout API */
void timeout_set(shield_timeout_t *timeout, uint64_t duration_ms,
                  void (*callback)(void *), void *user_data);
bool timeout_check(shield_timeout_t *timeout);
void timeout_reset(shield_timeout_t *timeout);
uint64_t timeout_remaining_ms(shield_timeout_t *timeout);

/* Sleep */
void sleep_ms(uint64_t ms);
void sleep_us(uint64_t us);

#endif /* SHIELD_TIMER_H */
