/*
 * SENTINEL Shield - Statistics Collector Implementation
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#include "shield_stats.h"
#include "shield_timer.h"

/* Initialize */
shield_err_t stats_init(stats_collector_t *stats)
{
    if (!stats) return SHIELD_ERR_INVALID;
    
    memset(stats, 0, sizeof(*stats));
    stats->start_time = time_now_ms();
    
    return SHIELD_OK;
}

/* Destroy */
void stats_destroy(stats_collector_t *stats)
{
    if (!stats) return;
    /* Free lock if allocated */
}

/* Record request */
void stats_record_request(stats_collector_t *stats, bool blocked,
                           int zone_id, int intent, uint64_t latency_us)
{
    if (!stats) return;
    
    time_t now = time(NULL);
    struct tm *tm = localtime(&now);
    
    int minute = tm->tm_min;
    int hour = tm->tm_hour;
    int day = tm->tm_wday;
    
    /* Total */
    stats->current.requests_total.total++;
    stats->current.requests_total.by_minute[minute]++;
    stats->current.requests_total.by_hour[hour]++;
    stats->current.requests_total.by_day[day]++;
    
    /* Blocked/Allowed */
    if (blocked) {
        stats->current.requests_blocked.total++;
        stats->current.requests_blocked.by_minute[minute]++;
        stats->current.requests_blocked.by_hour[hour]++;
        stats->current.requests_blocked.by_day[day]++;
    } else {
        stats->current.requests_allowed.total++;
        stats->current.requests_allowed.by_minute[minute]++;
        stats->current.requests_allowed.by_hour[hour]++;
        stats->current.requests_allowed.by_day[day]++;
    }
    
    /* By zone and intent */
    if (zone_id >= 0 && zone_id < 16) {
        stats->current.by_zone[zone_id]++;
    }
    if (intent >= 0 && intent < 10) {
        stats->current.by_intent[intent]++;
    }
    
    /* Latency */
    stats->current.latency.count++;
    stats->current.latency.sum_us += latency_us;
    
    if (stats->current.latency.count == 1 || 
        latency_us < stats->current.latency.min_us) {
        stats->current.latency.min_us = latency_us;
    }
    if (latency_us > stats->current.latency.max_us) {
        stats->current.latency.max_us = latency_us;
    }
    
    /* Uptime */
    stats->current.uptime_seconds = (time_now_ms() - stats->start_time) / 1000;
}

/* Record alert */
void stats_record_alert(stats_collector_t *stats, bool resolved)
{
    if (!stats) return;
    
    if (resolved) {
        stats->current.alerts_resolved++;
    } else {
        stats->current.alerts_fired++;
    }
}

/* Get stats */
security_stats_t *stats_get(stats_collector_t *stats)
{
    return stats ? &stats->current : NULL;
}

/* Get request rate */
uint64_t stats_get_rate(stats_collector_t *stats, stat_period_t period)
{
    if (!stats) return 0;
    
    switch (period) {
    case STAT_PERIOD_MINUTE: {
        time_t now = time(NULL);
        struct tm *tm = localtime(&now);
        return stats->current.requests_total.by_minute[tm->tm_min];
    }
    case STAT_PERIOD_HOUR: {
        time_t now = time(NULL);
        struct tm *tm = localtime(&now);
        return stats->current.requests_total.by_hour[tm->tm_hour];
    }
    case STAT_PERIOD_DAY: {
        time_t now = time(NULL);
        struct tm *tm = localtime(&now);
        return stats->current.requests_total.by_day[tm->tm_wday];
    }
    case STAT_PERIOD_ALL:
        return stats->current.requests_total.total;
    default:
        return 0;
    }
}

/* Get block rate */
float stats_get_block_rate(stats_collector_t *stats, stat_period_t period)
{
    if (!stats) return 0;
    
    uint64_t total = 0;
    uint64_t blocked = 0;
    
    switch (period) {
    case STAT_PERIOD_MINUTE: {
        time_t now = time(NULL);
        struct tm *tm = localtime(&now);
        int m = tm->tm_min;
        total = stats->current.requests_total.by_minute[m];
        blocked = stats->current.requests_blocked.by_minute[m];
        break;
    }
    case STAT_PERIOD_ALL:
        total = stats->current.requests_total.total;
        blocked = stats->current.requests_blocked.total;
        break;
    default:
        return 0;
    }
    
    return total > 0 ? (float)blocked / total : 0;
}

/* Export to JSON */
char *stats_to_json(stats_collector_t *stats)
{
    if (!stats) return strdup("{}");
    
    char *buf = malloc(4096);
    if (!buf) return NULL;
    
    snprintf(buf, 4096,
        "{"
        "\"uptime\":%lu,"
        "\"requests\":{\"total\":%lu,\"blocked\":%lu,\"allowed\":%lu},"
        "\"alerts\":{\"fired\":%lu,\"resolved\":%lu},"
        "\"latency\":{\"count\":%lu,\"avg_us\":%.0f,\"min_us\":%lu,\"max_us\":%lu}"
        "}",
        (unsigned long)stats->current.uptime_seconds,
        (unsigned long)stats->current.requests_total.total,
        (unsigned long)stats->current.requests_blocked.total,
        (unsigned long)stats->current.requests_allowed.total,
        (unsigned long)stats->current.alerts_fired,
        (unsigned long)stats->current.alerts_resolved,
        (unsigned long)stats->current.latency.count,
        stats->current.latency.count > 0 ?
            (double)stats->current.latency.sum_us / stats->current.latency.count : 0,
        (unsigned long)stats->current.latency.min_us,
        (unsigned long)stats->current.latency.max_us
    );
    
    return buf;
}

/* Export to Prometheus */
char *stats_to_prometheus(stats_collector_t *stats)
{
    if (!stats) return strdup("");
    
    char *buf = malloc(4096);
    if (!buf) return NULL;
    
    snprintf(buf, 4096,
        "# HELP shield_requests_total Total requests processed\n"
        "# TYPE shield_requests_total counter\n"
        "shield_requests_total %lu\n\n"
        "# HELP shield_requests_blocked Total requests blocked\n"
        "# TYPE shield_requests_blocked counter\n"
        "shield_requests_blocked %lu\n\n"
        "# HELP shield_requests_allowed Total requests allowed\n"
        "# TYPE shield_requests_allowed counter\n"
        "shield_requests_allowed %lu\n\n"
        "# HELP shield_uptime_seconds Uptime in seconds\n"
        "# TYPE shield_uptime_seconds gauge\n"
        "shield_uptime_seconds %lu\n\n"
        "# HELP shield_latency_microseconds Average latency\n"
        "# TYPE shield_latency_microseconds gauge\n"
        "shield_latency_avg_us %.0f\n",
        (unsigned long)stats->current.requests_total.total,
        (unsigned long)stats->current.requests_blocked.total,
        (unsigned long)stats->current.requests_allowed.total,
        (unsigned long)stats->current.uptime_seconds,
        stats->current.latency.count > 0 ?
            (double)stats->current.latency.sum_us / stats->current.latency.count : 0
    );
    
    return buf;
}

/* Reset */
void stats_reset(stats_collector_t *stats)
{
    if (!stats) return;
    
    memset(&stats->current, 0, sizeof(stats->current));
    stats->start_time = time_now_ms();
}
