/*
 * SENTINEL Shield - Timer Implementation
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#include "shield_timer.h"
#include "shield_platform.h"

/* Current time in nanoseconds */
uint64_t time_now_ns(void)
{
#ifdef SHIELD_PLATFORM_WINDOWS
    LARGE_INTEGER freq, count;
    QueryPerformanceFrequency(&freq);
    QueryPerformanceCounter(&count);
    return (uint64_t)(count.QuadPart * 1000000000LL / freq.QuadPart);
#else
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (uint64_t)ts.tv_sec * 1000000000ULL + (uint64_t)ts.tv_nsec;
#endif
}

/* Current time in microseconds */
uint64_t time_now_us(void)
{
    return time_now_ns() / 1000;
}

/* Current time in milliseconds */
uint64_t time_now_ms(void)
{
    return time_now_ns() / 1000000;
}

/* Start timer */
void timer_start(shield_timer_t *timer)
{
    if (!timer) return;
    timer->start_ns = time_now_ns();
    timer->end_ns = 0;
    timer->running = true;
}

/* Stop timer */
void timer_stop(shield_timer_t *timer)
{
    if (!timer || !timer->running) return;
    timer->end_ns = time_now_ns();
    timer->running = false;
}

/* Get elapsed nanoseconds */
uint64_t timer_elapsed_ns(shield_timer_t *timer)
{
    if (!timer) return 0;
    
    if (timer->running) {
        return time_now_ns() - timer->start_ns;
    }
    return timer->end_ns - timer->start_ns;
}

/* Get elapsed microseconds */
uint64_t timer_elapsed_us(shield_timer_t *timer)
{
    return timer_elapsed_ns(timer) / 1000;
}

/* Get elapsed milliseconds */
uint64_t timer_elapsed_ms(shield_timer_t *timer)
{
    return timer_elapsed_ns(timer) / 1000000;
}

/* Set timeout */
void timeout_set(shield_timeout_t *timeout, uint64_t duration_ms,
                  void (*callback)(void *), void *user_data)
{
    if (!timeout) return;
    
    timeout->duration_ms = duration_ms;
    timeout->deadline_ns = time_now_ns() + duration_ms * 1000000;
    timeout->expired = false;
    timeout->callback = callback;
    timeout->user_data = user_data;
}

/* Check timeout */
bool timeout_check(shield_timeout_t *timeout)
{
    if (!timeout) return true;
    
    if (timeout->expired) return true;
    
    if (time_now_ns() >= timeout->deadline_ns) {
        timeout->expired = true;
        if (timeout->callback) {
            timeout->callback(timeout->user_data);
        }
        return true;
    }
    
    return false;
}

/* Reset timeout */
void timeout_reset(shield_timeout_t *timeout)
{
    if (!timeout) return;
    timeout->deadline_ns = time_now_ns() + timeout->duration_ms * 1000000;
    timeout->expired = false;
}

/* Remaining time */
uint64_t timeout_remaining_ms(shield_timeout_t *timeout)
{
    if (!timeout || timeout->expired) return 0;
    
    uint64_t now = time_now_ns();
    if (now >= timeout->deadline_ns) return 0;
    
    return (timeout->deadline_ns - now) / 1000000;
}

/* Sleep milliseconds */
void sleep_ms(uint64_t ms)
{
#ifdef SHIELD_PLATFORM_WINDOWS
    Sleep((DWORD)ms);
#else
    struct timespec ts = {
        .tv_sec = ms / 1000,
        .tv_nsec = (ms % 1000) * 1000000
    };
    nanosleep(&ts, NULL);
#endif
}

/* Sleep microseconds */
void sleep_us(uint64_t us)
{
#ifdef SHIELD_PLATFORM_WINDOWS
    /* Windows doesn't have sub-ms sleep, use busy wait for short durations */
    if (us < 1000) {
        uint64_t end = time_now_us() + us;
        while (time_now_us() < end) {
            /* Busy wait */
        }
    } else {
        Sleep((DWORD)(us / 1000));
    }
#else
    struct timespec ts = {
        .tv_sec = us / 1000000,
        .tv_nsec = (us % 1000000) * 1000
    };
    nanosleep(&ts, NULL);
#endif
}
