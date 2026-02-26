/*
 * SENTINEL Shield - Statistics Collector
 * 
 * Collect and report security statistics
 */

#ifndef SHIELD_STATS_H
#define SHIELD_STATS_H

#include "shield_common.h"

/* Time periods */
typedef enum stat_period {
    STAT_PERIOD_MINUTE,
    STAT_PERIOD_HOUR,
    STAT_PERIOD_DAY,
    STAT_PERIOD_WEEK,
    STAT_PERIOD_MONTH,
    STAT_PERIOD_ALL,
} stat_period_t;

/* Counter stats */
typedef struct counter_stats {
    uint64_t        total;
    uint64_t        by_minute[60];
    uint64_t        by_hour[24];
    uint64_t        by_day[7];
} counter_stats_t;

/* Latency stats */
typedef struct latency_stats {
    uint64_t        count;
    uint64_t        sum_us;
    uint64_t        min_us;
    uint64_t        max_us;
    uint64_t        p50_us;
    uint64_t        p90_us;
    uint64_t        p99_us;
} latency_stats_t;

/* Security stats */
typedef struct security_stats {
    /* Requests */
    counter_stats_t requests_total;
    counter_stats_t requests_blocked;
    counter_stats_t requests_allowed;
    
    /* By category */
    uint64_t        by_intent[10];
    uint64_t        by_zone[16];
    
    /* Latency */
    latency_stats_t latency;
    
    /* Alerts */
    uint64_t        alerts_fired;
    uint64_t        alerts_resolved;
    
    /* System */
    uint64_t        uptime_seconds;
    uint64_t        memory_bytes;
} security_stats_t;

/* Stats collector */
typedef struct stats_collector {
    security_stats_t current;
    
    /* Lock for thread safety */
    void            *lock;
    
    /* Start time */
    uint64_t        start_time;
} stats_collector_t;

/* API */
shield_err_t stats_init(stats_collector_t *stats);
void stats_destroy(stats_collector_t *stats);

/* Record */
void stats_record_request(stats_collector_t *stats, bool blocked, 
                           int zone_id, int intent, uint64_t latency_us);
void stats_record_alert(stats_collector_t *stats, bool resolved);

/* Query */
security_stats_t *stats_get(stats_collector_t *stats);
uint64_t stats_get_rate(stats_collector_t *stats, stat_period_t period);
float stats_get_block_rate(stats_collector_t *stats, stat_period_t period);

/* Export */
char *stats_to_json(stats_collector_t *stats);
char *stats_to_prometheus(stats_collector_t *stats);

/* Reset */
void stats_reset(stats_collector_t *stats);

#endif /* SHIELD_STATS_H */
