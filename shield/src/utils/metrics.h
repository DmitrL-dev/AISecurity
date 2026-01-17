/**
 * SENTINEL Shield - Prometheus Metrics
 * 
 * Lightweight metrics collection for C proxy.
 * Exposes /metrics endpoint in Prometheus text format.
 */

#ifndef SHIELD_METRICS_H
#define SHIELD_METRICS_H

#include <stdint.h>
#include <stddef.h>
#include <pthread.h>

/* Metric types */
typedef enum {
    METRIC_COUNTER,
    METRIC_GAUGE,
    METRIC_HISTOGRAM
} metric_type_t;

/* Single metric */
typedef struct {
    char name[64];
    char help[128];
    metric_type_t type;
    double value;
    pthread_mutex_t lock;
} metric_t;

/* Histogram buckets */
typedef struct {
    char name[64];
    char help[128];
    double buckets[12];
    uint64_t bucket_counts[12];
    double sum;
    uint64_t count;
    pthread_mutex_t lock;
} histogram_t;

/* Metrics registry */
typedef struct {
    metric_t *counters;
    size_t counter_count;
    metric_t *gauges;
    size_t gauge_count;
    histogram_t *histograms;
    size_t histogram_count;
    pthread_mutex_t registry_lock;
} metrics_registry_t;

/* Global registry */
extern metrics_registry_t *g_metrics;

/* Initialize metrics system */
int metrics_init(void);

/* Cleanup metrics */
void metrics_cleanup(void);

/* Counter operations */
metric_t *counter_register(const char *name, const char *help);
void counter_inc(metric_t *m);
void counter_add(metric_t *m, double value);

/* Gauge operations */
metric_t *gauge_register(const char *name, const char *help);
void gauge_set(metric_t *m, double value);
void gauge_inc(metric_t *m);
void gauge_dec(metric_t *m);

/* Histogram operations */
histogram_t *histogram_register(const char *name, const char *help);
void histogram_observe(histogram_t *h, double value);

/* Export metrics in Prometheus format */
char *metrics_export_prometheus(void);

/* Default metrics */
extern metric_t *metric_requests_total;
extern metric_t *metric_requests_active;
extern metric_t *metric_auth_success;
extern metric_t *metric_auth_failure;
extern metric_t *metric_rate_limited;
extern histogram_t *metric_request_duration;

/* HTTP handler */
void handle_metrics_request(int client_fd);
void handle_health_request(int client_fd);

#endif /* SHIELD_METRICS_H */
