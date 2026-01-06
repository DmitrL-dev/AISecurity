/**
 * @file route_metrics.c
 * @brief Prometheus Metrics Route Handler
 * 
 * GET /metrics — Returns Prometheus-formatted metrics.
 * 
 * @author SENTINEL Team
 * @date January 2026
 */

#include "http/http_server.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

/* ============================================================================
 * Metrics State
 * ============================================================================ */

/* These would be updated by actual guard invocations */
static struct {
    unsigned long requests_total;
    unsigned long requests_blocked;
    unsigned long requests_allowed;
    unsigned long requests_suspicious;
    unsigned long guard_llm_triggers;
    unsigned long guard_rag_triggers;
    unsigned long guard_agent_triggers;
    double total_latency_ms;
} metrics = {0};

void route_metrics_increment_request(const char *verdict) {
    metrics.requests_total++;
    if (strcmp(verdict, "BLOCKED") == 0) {
        metrics.requests_blocked++;
    } else if (strcmp(verdict, "ALLOWED") == 0) {
        metrics.requests_allowed++;
    } else if (strcmp(verdict, "SUSPICIOUS") == 0) {
        metrics.requests_suspicious++;
    }
}

void route_metrics_add_latency(double latency_ms) {
    metrics.total_latency_ms += latency_ms;
}

void route_metrics_guard_triggered(const char *guard) {
    if (strcmp(guard, "llm") == 0) metrics.guard_llm_triggers++;
    else if (strcmp(guard, "rag") == 0) metrics.guard_rag_triggers++;
    else if (strcmp(guard, "agent") == 0) metrics.guard_agent_triggers++;
}

/* ============================================================================
 * Route Handler
 * ============================================================================ */

int route_metrics_handler(const http_request_t *request,
                          http_response_t *response,
                          void *user_data) {
    (void)request;
    (void)user_data;
    
    /* Build Prometheus-format metrics */
    char buffer[4096];
    int offset = 0;
    
    /* Header */
    offset += snprintf(buffer + offset, sizeof(buffer) - offset,
        "# HELP shield_requests_total Total number of requests processed\n"
        "# TYPE shield_requests_total counter\n"
        "shield_requests_total %lu\n\n",
        metrics.requests_total);
    
    /* Requests by verdict */
    offset += snprintf(buffer + offset, sizeof(buffer) - offset,
        "# HELP shield_requests_by_verdict Requests by verdict\n"
        "# TYPE shield_requests_by_verdict counter\n"
        "shield_requests_by_verdict{verdict=\"allowed\"} %lu\n"
        "shield_requests_by_verdict{verdict=\"blocked\"} %lu\n"
        "shield_requests_by_verdict{verdict=\"suspicious\"} %lu\n\n",
        metrics.requests_allowed,
        metrics.requests_blocked,
        metrics.requests_suspicious);
    
    /* Guard triggers */
    offset += snprintf(buffer + offset, sizeof(buffer) - offset,
        "# HELP shield_guard_triggers_total Guard trigger counts\n"
        "# TYPE shield_guard_triggers_total counter\n"
        "shield_guard_triggers_total{guard=\"llm\"} %lu\n"
        "shield_guard_triggers_total{guard=\"rag\"} %lu\n"
        "shield_guard_triggers_total{guard=\"agent\"} %lu\n\n",
        metrics.guard_llm_triggers,
        metrics.guard_rag_triggers,
        metrics.guard_agent_triggers);
    
    /* Average latency */
    double avg_latency = metrics.requests_total > 0 
        ? metrics.total_latency_ms / metrics.requests_total 
        : 0.0;
    
    offset += snprintf(buffer + offset, sizeof(buffer) - offset,
        "# HELP shield_latency_avg_ms Average request latency in milliseconds\n"
        "# TYPE shield_latency_avg_ms gauge\n"
        "shield_latency_avg_ms %g\n\n",
        avg_latency);
    
    /* Guards status (1 = enabled, 0 = disabled) */
    offset += snprintf(buffer + offset, sizeof(buffer) - offset,
        "# HELP shield_guard_enabled Guard enabled status\n"
        "# TYPE shield_guard_enabled gauge\n"
        "shield_guard_enabled{guard=\"llm\"} 1\n"
        "shield_guard_enabled{guard=\"rag\"} 1\n"
        "shield_guard_enabled{guard=\"agent\"} 1\n"
        "shield_guard_enabled{guard=\"tool\"} 1\n"
        "shield_guard_enabled{guard=\"mcp\"} 1\n"
        "shield_guard_enabled{guard=\"api\"} 1\n");
    
    /* Set response */
    response->status = HTTP_STATUS_OK;
    response->content_type = "text/plain; version=0.0.4; charset=utf-8";
    http_response_set_body(response, buffer, offset);
    
    return 0;
}

/* ============================================================================
 * Route Registration
 * ============================================================================ */

http_route_t route_metrics = {
    .method = HTTP_METHOD_GET,
    .path = "/metrics",
    .handler = route_metrics_handler,
    .user_data = NULL
};
