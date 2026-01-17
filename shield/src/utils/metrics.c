/**
 * SENTINEL Shield - Prometheus Metrics Implementation
 * 
 * Lightweight metrics collection for C proxy.
 */

#include "metrics.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

/* Global registry */
metrics_registry_t *g_metrics = NULL;

/* Default metrics */
metric_t *metric_requests_total = NULL;
metric_t *metric_requests_active = NULL;
metric_t *metric_auth_success = NULL;
metric_t *metric_auth_failure = NULL;
metric_t *metric_rate_limited = NULL;
histogram_t *metric_request_duration = NULL;

/* Default histogram buckets (latency in seconds) */
static double default_buckets[] = {
    0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0
};

int metrics_init(void) {
    g_metrics = calloc(1, sizeof(metrics_registry_t));
    if (!g_metrics) return -1;
    
    pthread_mutex_init(&g_metrics->registry_lock, NULL);
    
    /* Allocate metric arrays */
    g_metrics->counters = calloc(32, sizeof(metric_t));
    g_metrics->gauges = calloc(16, sizeof(metric_t));
    g_metrics->histograms = calloc(8, sizeof(histogram_t));
    
    if (!g_metrics->counters || !g_metrics->gauges || !g_metrics->histograms) {
        metrics_cleanup();
        return -1;
    }
    
    /* Register default metrics */
    metric_requests_total = counter_register(
        "shield_requests_total",
        "Total number of requests processed"
    );
    
    metric_requests_active = gauge_register(
        "shield_requests_active",
        "Currently active requests"
    );
    
    metric_auth_success = counter_register(
        "shield_auth_success_total",
        "Successful authentications"
    );
    
    metric_auth_failure = counter_register(
        "shield_auth_failure_total",
        "Failed authentications"
    );
    
    metric_rate_limited = counter_register(
        "shield_rate_limited_total",
        "Requests rejected by rate limiter"
    );
    
    metric_request_duration = histogram_register(
        "shield_request_duration_seconds",
        "Request processing time in seconds"
    );
    
    return 0;
}

void metrics_cleanup(void) {
    if (!g_metrics) return;
    
    /* Destroy mutexes */
    for (size_t i = 0; i < g_metrics->counter_count; i++) {
        pthread_mutex_destroy(&g_metrics->counters[i].lock);
    }
    for (size_t i = 0; i < g_metrics->gauge_count; i++) {
        pthread_mutex_destroy(&g_metrics->gauges[i].lock);
    }
    for (size_t i = 0; i < g_metrics->histogram_count; i++) {
        pthread_mutex_destroy(&g_metrics->histograms[i].lock);
    }
    
    free(g_metrics->counters);
    free(g_metrics->gauges);
    free(g_metrics->histograms);
    pthread_mutex_destroy(&g_metrics->registry_lock);
    free(g_metrics);
    g_metrics = NULL;
}

metric_t *counter_register(const char *name, const char *help) {
    if (!g_metrics || g_metrics->counter_count >= 32) return NULL;
    
    pthread_mutex_lock(&g_metrics->registry_lock);
    
    metric_t *m = &g_metrics->counters[g_metrics->counter_count++];
    strncpy(m->name, name, sizeof(m->name) - 1);
    strncpy(m->help, help, sizeof(m->help) - 1);
    m->type = METRIC_COUNTER;
    m->value = 0;
    pthread_mutex_init(&m->lock, NULL);
    
    pthread_mutex_unlock(&g_metrics->registry_lock);
    return m;
}

void counter_inc(metric_t *m) {
    counter_add(m, 1.0);
}

void counter_add(metric_t *m, double value) {
    if (!m) return;
    pthread_mutex_lock(&m->lock);
    m->value += value;
    pthread_mutex_unlock(&m->lock);
}

metric_t *gauge_register(const char *name, const char *help) {
    if (!g_metrics || g_metrics->gauge_count >= 16) return NULL;
    
    pthread_mutex_lock(&g_metrics->registry_lock);
    
    metric_t *m = &g_metrics->gauges[g_metrics->gauge_count++];
    strncpy(m->name, name, sizeof(m->name) - 1);
    strncpy(m->help, help, sizeof(m->help) - 1);
    m->type = METRIC_GAUGE;
    m->value = 0;
    pthread_mutex_init(&m->lock, NULL);
    
    pthread_mutex_unlock(&g_metrics->registry_lock);
    return m;
}

void gauge_set(metric_t *m, double value) {
    if (!m) return;
    pthread_mutex_lock(&m->lock);
    m->value = value;
    pthread_mutex_unlock(&m->lock);
}

void gauge_inc(metric_t *m) {
    if (!m) return;
    pthread_mutex_lock(&m->lock);
    m->value += 1.0;
    pthread_mutex_unlock(&m->lock);
}

void gauge_dec(metric_t *m) {
    if (!m) return;
    pthread_mutex_lock(&m->lock);
    m->value -= 1.0;
    pthread_mutex_unlock(&m->lock);
}

histogram_t *histogram_register(const char *name, const char *help) {
    if (!g_metrics || g_metrics->histogram_count >= 8) return NULL;
    
    pthread_mutex_lock(&g_metrics->registry_lock);
    
    histogram_t *h = &g_metrics->histograms[g_metrics->histogram_count++];
    strncpy(h->name, name, sizeof(h->name) - 1);
    strncpy(h->help, help, sizeof(h->help) - 1);
    memcpy(h->buckets, default_buckets, sizeof(default_buckets));
    memset(h->bucket_counts, 0, sizeof(h->bucket_counts));
    h->sum = 0;
    h->count = 0;
    pthread_mutex_init(&h->lock, NULL);
    
    pthread_mutex_unlock(&g_metrics->registry_lock);
    return h;
}

void histogram_observe(histogram_t *h, double value) {
    if (!h) return;
    
    pthread_mutex_lock(&h->lock);
    
    /* Update bucket counts */
    for (int i = 0; i < 12; i++) {
        if (value <= h->buckets[i]) {
            h->bucket_counts[i]++;
        }
    }
    
    h->sum += value;
    h->count++;
    
    pthread_mutex_unlock(&h->lock);
}

char *metrics_export_prometheus(void) {
    if (!g_metrics) return NULL;
    
    /* Allocate buffer (16KB should be enough) */
    char *buffer = malloc(16384);
    if (!buffer) return NULL;
    
    size_t offset = 0;
    
    /* Export counters */
    for (size_t i = 0; i < g_metrics->counter_count; i++) {
        metric_t *m = &g_metrics->counters[i];
        offset += snprintf(buffer + offset, 16384 - offset,
            "# HELP %s %s\n"
            "# TYPE %s counter\n"
            "%s %.0f\n\n",
            m->name, m->help, m->name, m->name, m->value
        );
    }
    
    /* Export gauges */
    for (size_t i = 0; i < g_metrics->gauge_count; i++) {
        metric_t *m = &g_metrics->gauges[i];
        offset += snprintf(buffer + offset, 16384 - offset,
            "# HELP %s %s\n"
            "# TYPE %s gauge\n"
            "%s %.2f\n\n",
            m->name, m->help, m->name, m->name, m->value
        );
    }
    
    /* Export histograms */
    for (size_t i = 0; i < g_metrics->histogram_count; i++) {
        histogram_t *h = &g_metrics->histograms[i];
        
        offset += snprintf(buffer + offset, 16384 - offset,
            "# HELP %s %s\n"
            "# TYPE %s histogram\n",
            h->name, h->help, h->name
        );
        
        /* Bucket counts (cumulative) */
        uint64_t cumulative = 0;
        for (int b = 0; b < 12; b++) {
            cumulative += h->bucket_counts[b];
            offset += snprintf(buffer + offset, 16384 - offset,
                "%s_bucket{le=\"%.3f\"} %lu\n",
                h->name, h->buckets[b], (unsigned long)cumulative
            );
        }
        
        /* +Inf bucket */
        offset += snprintf(buffer + offset, 16384 - offset,
            "%s_bucket{le=\"+Inf\"} %lu\n",
            h->name, (unsigned long)h->count
        );
        
        /* Sum and count */
        offset += snprintf(buffer + offset, 16384 - offset,
            "%s_sum %.6f\n"
            "%s_count %lu\n\n",
            h->name, h->sum, h->name, (unsigned long)h->count
        );
    }
    
    return buffer;
}

void handle_metrics_request(int client_fd) {
    char *metrics = metrics_export_prometheus();
    if (!metrics) {
        const char *error = "HTTP/1.1 500 Internal Server Error\r\n\r\n";
        write(client_fd, error, strlen(error));
        return;
    }
    
    char header[256];
    int header_len = snprintf(header, sizeof(header),
        "HTTP/1.1 200 OK\r\n"
        "Content-Type: text/plain; charset=utf-8\r\n"
        "Content-Length: %zu\r\n"
        "\r\n",
        strlen(metrics)
    );
    
    write(client_fd, header, header_len);
    write(client_fd, metrics, strlen(metrics));
    
    free(metrics);
}

void handle_health_request(int client_fd) {
    const char *health_json = 
        "{"
        "\"status\":\"healthy\","
        "\"version\":\"3.0.0\","
        "\"components\":{"
        "\"proxy\":\"up\","
        "\"auth\":\"up\","
        "\"rate_limiter\":\"up\""
        "}"
        "}";
    
    char response[512];
    int len = snprintf(response, sizeof(response),
        "HTTP/1.1 200 OK\r\n"
        "Content-Type: application/json\r\n"
        "Content-Length: %zu\r\n"
        "\r\n"
        "%s",
        strlen(health_json), health_json
    );
    
    write(client_fd, response, len);
}
