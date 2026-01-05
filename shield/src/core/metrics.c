/*
 * SENTINEL Shield - Metrics Implementation
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "shield_common.h"
#include "shield_metrics.h"

/* Initialize metrics registry */
shield_err_t metrics_init(metrics_registry_t *reg)
{
    if (!reg) {
        return SHIELD_ERR_INVALID;
    }
    
    memset(reg, 0, sizeof(*reg));
    return SHIELD_OK;
}

/* Destroy metrics */
void metrics_destroy(metrics_registry_t *reg)
{
    if (!reg) {
        return;
    }
    
    metric_t *m = reg->metrics;
    while (m) {
        metric_t *next = m->next;
        free(m);
        m = next;
    }
    
    reg->metrics = NULL;
    reg->count = 0;
}

/* Find or create metric */
static metric_t *get_or_create(metrics_registry_t *reg, const char *name,
                                metric_type_t type, const char *help)
{
    /* Find existing */
    metric_t *m = reg->metrics;
    while (m) {
        if (strcmp(m->name, name) == 0) {
            return m;
        }
        m = m->next;
    }
    
    /* Create new */
    m = calloc(1, sizeof(metric_t));
    if (!m) {
        return NULL;
    }
    
    strncpy(m->name, name, sizeof(m->name) - 1);
    m->type = type;
    if (help) {
        strncpy(m->help, help, sizeof(m->help) - 1);
    }
    
    m->next = reg->metrics;
    reg->metrics = m;
    reg->count++;
    
    return m;
}

/* Counter */
metric_t *metrics_counter(metrics_registry_t *reg, const char *name, const char *help)
{
    return get_or_create(reg, name, METRIC_COUNTER, help);
}

void metrics_inc(metric_t *m)
{
    if (m && m->type == METRIC_COUNTER) {
        m->value.counter++;
    }
}

void metrics_add(metric_t *m, uint64_t value)
{
    if (m && m->type == METRIC_COUNTER) {
        m->value.counter += value;
    }
}

/* Find metric by name and increment */
void metrics_inc_by_name(metrics_registry_t *reg, const char *name, const char *labels)
{
    (void)labels;  /* TODO: support labels in future */
    if (!reg || !name) return;
    
    metric_t *m = metrics_counter(reg, name, NULL);
    if (m) {
        m->value.counter++;
    }
}

/* Gauge */
metric_t *metrics_gauge(metrics_registry_t *reg, const char *name, const char *help)
{
    return get_or_create(reg, name, METRIC_GAUGE, help);
}

void metrics_set(metric_t *m, double value)
{
    if (m && m->type == METRIC_GAUGE) {
        m->value.gauge = value;
    }
}

/* Histogram */
metric_t *metrics_histogram(metrics_registry_t *reg, const char *name, const char *help)
{
    return get_or_create(reg, name, METRIC_HISTOGRAM, help);
}

void metrics_observe(metric_t *m, double value)
{
    if (!m || m->type != METRIC_HISTOGRAM) {
        return;
    }
    
    m->value.histogram.count++;
    m->value.histogram.sum += value;
    
    /* Update buckets (exponential: 1, 5, 10, 50, 100, 500, 1000, 5000, 10000, +Inf) */
    static const double bounds[] = {1, 5, 10, 50, 100, 500, 1000, 5000, 10000};
    for (int i = 0; i < 9; i++) {
        if (value <= bounds[i]) {
            m->value.histogram.buckets[i]++;
        }
    }
    m->value.histogram.buckets[9]++; /* +Inf */
}

/* Export Prometheus format */
char *metrics_export_prometheus(metrics_registry_t *reg)
{
    if (!reg) {
        return NULL;
    }
    
    size_t buf_size = 4096 * reg->count;
    char *buf = malloc(buf_size);
    if (!buf) {
        return NULL;
    }
    
    size_t pos = 0;
    
    metric_t *m = reg->metrics;
    while (m && pos < buf_size - 512) {
        /* Help */
        if (m->help[0]) {
            pos += snprintf(buf + pos, buf_size - pos,
                           "# HELP %s %s\n", m->name, m->help);
        }
        
        /* Type */
        const char *type_str = "gauge";
        if (m->type == METRIC_COUNTER) type_str = "counter";
        else if (m->type == METRIC_HISTOGRAM) type_str = "histogram";
        
        pos += snprintf(buf + pos, buf_size - pos,
                       "# TYPE %s %s\n", m->name, type_str);
        
        /* Value */
        switch (m->type) {
        case METRIC_COUNTER:
            pos += snprintf(buf + pos, buf_size - pos,
                           "%s %lu\n", m->name, (unsigned long)m->value.counter);
            break;
        case METRIC_GAUGE:
            pos += snprintf(buf + pos, buf_size - pos,
                           "%s %g\n", m->name, m->value.gauge);
            break;
        case METRIC_HISTOGRAM:
            /* Buckets */
            static const double bounds[] = {1, 5, 10, 50, 100, 500, 1000, 5000, 10000};
            for (int i = 0; i < 9; i++) {
                pos += snprintf(buf + pos, buf_size - pos,
                               "%s_bucket{le=\"%.0f\"} %.0f\n",
                               m->name, bounds[i], m->value.histogram.buckets[i]);
            }
            pos += snprintf(buf + pos, buf_size - pos,
                           "%s_bucket{le=\"+Inf\"} %.0f\n",
                           m->name, m->value.histogram.buckets[9]);
            pos += snprintf(buf + pos, buf_size - pos,
                           "%s_sum %g\n", m->name, m->value.histogram.sum);
            pos += snprintf(buf + pos, buf_size - pos,
                           "%s_count %lu\n", m->name, 
                           (unsigned long)m->value.histogram.count);
            break;
        }
        
        m = m->next;
    }
    
    return buf;
}

/* Export JSON */
char *metrics_export_json(metrics_registry_t *reg)
{
    if (!reg) {
        return NULL;
    }
    
    size_t buf_size = 4096 * reg->count;
    char *buf = malloc(buf_size);
    if (!buf) {
        return NULL;
    }
    
    size_t pos = 0;
    pos += snprintf(buf + pos, buf_size - pos, "{\n");
    
    metric_t *m = reg->metrics;
    bool first = true;
    while (m && pos < buf_size - 256) {
        if (!first) {
            pos += snprintf(buf + pos, buf_size - pos, ",\n");
        }
        first = false;
        
        switch (m->type) {
        case METRIC_COUNTER:
            pos += snprintf(buf + pos, buf_size - pos,
                           "  \"%s\": %lu", m->name, (unsigned long)m->value.counter);
            break;
        case METRIC_GAUGE:
            pos += snprintf(buf + pos, buf_size - pos,
                           "  \"%s\": %g", m->name, m->value.gauge);
            break;
        case METRIC_HISTOGRAM:
            pos += snprintf(buf + pos, buf_size - pos,
                           "  \"%s\": {\"count\": %lu, \"sum\": %g}",
                           m->name, (unsigned long)m->value.histogram.count,
                           m->value.histogram.sum);
            break;
        }
        
        m = m->next;
    }
    
    pos += snprintf(buf + pos, buf_size - pos, "\n}\n");
    
    return buf;
}

/* Initialize shield metrics */
shield_err_t shield_metrics_init(shield_metrics_t *m, metrics_registry_t *reg)
{
    if (!m || !reg) {
        return SHIELD_ERR_INVALID;
    }
    
    m->requests_total = metrics_counter(reg, "shield_requests_total",
                                         "Total requests processed");
    m->requests_blocked = metrics_counter(reg, "shield_requests_blocked",
                                           "Requests blocked");
    m->requests_allowed = metrics_counter(reg, "shield_requests_allowed",
                                           "Requests allowed");
    m->requests_quarantined = metrics_counter(reg, "shield_requests_quarantined",
                                               "Requests quarantined");
    m->active_sessions = metrics_gauge(reg, "shield_active_sessions",
                                        "Active sessions");
    m->rule_evaluations = metrics_counter(reg, "shield_rule_evaluations",
                                           "Rule evaluations");
    m->guard_checks = metrics_counter(reg, "shield_guard_checks",
                                       "Guard checks performed");
    m->canary_triggers = metrics_counter(reg, "shield_canary_triggers",
                                          "Canary token triggers");
    m->ratelimit_denied = metrics_counter(reg, "shield_ratelimit_denied",
                                           "Rate limit denials");
    m->latency_us = metrics_histogram(reg, "shield_latency_us",
                                       "Processing latency in microseconds");
    
    return SHIELD_OK;
}
