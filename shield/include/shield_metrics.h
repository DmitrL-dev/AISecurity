/*
 * SENTINEL Shield - Metrics and Telemetry
 */

#ifndef SHIELD_METRICS_H
#define SHIELD_METRICS_H

#include "shield_common.h"

/* Metric types */
typedef enum metric_type {
    METRIC_COUNTER,
    METRIC_GAUGE,
    METRIC_HISTOGRAM,
} metric_type_t;

/* Single metric */
typedef struct metric {
    char            name[64];
    metric_type_t   type;
    char            help[128];
    
    union {
        uint64_t    counter;
        double      gauge;
        struct {
            uint64_t    count;
            double      sum;
            double      buckets[10];
        } histogram;
    } value;
    
    struct metric *next;
} metric_t;

/* Metrics registry */
typedef struct metrics_registry {
    metric_t    *metrics;
    uint32_t    count;
} metrics_registry_t;

/* API */
shield_err_t metrics_init(metrics_registry_t *reg);
void metrics_destroy(metrics_registry_t *reg);

/* Counter operations */
metric_t *metrics_counter(metrics_registry_t *reg, const char *name, const char *help);
void metrics_inc(metric_t *m);
void metrics_add(metric_t *m, uint64_t value);

/* Gauge operations */
metric_t *metrics_gauge(metrics_registry_t *reg, const char *name, const char *help);
void metrics_set(metric_t *m, double value);

/* Histogram operations */
metric_t *metrics_histogram(metrics_registry_t *reg, const char *name, const char *help);
void metrics_observe(metric_t *m, double value);

/* Export */
char *metrics_export_prometheus(metrics_registry_t *reg);
char *metrics_export_json(metrics_registry_t *reg);

/* Built-in metrics */
typedef struct shield_metrics {
    metric_t    *requests_total;
    metric_t    *requests_blocked;
    metric_t    *requests_allowed;
    metric_t    *requests_quarantined;
    metric_t    *active_sessions;
    metric_t    *rule_evaluations;
    metric_t    *guard_checks;
    metric_t    *canary_triggers;
    metric_t    *ratelimit_denied;
    metric_t    *latency_us;
} shield_metrics_t;

shield_err_t shield_metrics_init(shield_metrics_t *m, metrics_registry_t *reg);

#endif /* SHIELD_METRICS_H */
