/**
 * @file route_analyze.c
 * @brief Main Analysis Route Handler
 * 
 * POST /api/v1/analyze — Runs all enabled guards on input.
 * 
 * @author SENTINEL Team
 * @date January 2026
 */

#include "http/http_server.h"
#include "http/json_parser.h"
#include "http/json_builder.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <stdbool.h>

/* ============================================================================
 * Request/Response Types
 * ============================================================================ */

typedef struct {
    const char *input;
    const char *session_id;
    const char *user_id;
    bool guards_llm;
    bool guards_rag;
    bool guards_agent;
    bool guards_tool;
    bool guards_mcp;
    bool guards_api;
    bool include_details;
} analyze_request_t;

typedef struct {
    const char *verdict;       /* "ALLOWED", "BLOCKED", "SUSPICIOUS" */
    double risk_score;
    double latency_ms;
    bool llm_triggered;
    double llm_score;
    const char *llm_reason;
    bool rag_triggered;
    double rag_score;
    bool agent_triggered;
    double agent_score;
    const char *request_id;
} analyze_response_t;

/* ============================================================================
 * Helper Functions
 * ============================================================================ */

static void generate_request_id(char *buf, size_t len) {
    static unsigned long counter = 0;
    unsigned long ts = (unsigned long)time(NULL);
    snprintf(buf, len, "req_%lx_%04lx", ts, ++counter & 0xFFFF);
}

static int parse_analyze_request(const char *body, analyze_request_t *req) {
    if (!body || !req) return -1;
    
    memset(req, 0, sizeof(*req));
    
    /* Default: all guards enabled */
    req->guards_llm = true;
    req->guards_rag = true;
    req->guards_agent = true;
    req->guards_tool = true;
    req->guards_mcp = true;
    req->guards_api = true;
    
    char *error = NULL;
    http_json_value_t *json = http_json_parse(body, &error);
    
    if (!json) {
        fprintf(stderr, "[ANALYZE] JSON parse error: %s\n", error ? error : "unknown");
        free(error);
        return -1;
    }
    
    /* Extract input (required) */
    req->input = http_json_object_get_string(json, "input");
    if (!req->input) {
        http_json_free(json);
        return -1;
    }
    
    /* Extract context (optional) */
    http_json_value_t *context = http_json_object_get(json, "context");
    if (context && http_json_is_object(context)) {
        req->session_id = http_json_object_get_string(context, "session_id");
        req->user_id = http_json_object_get_string(context, "user_id");
    }
    
    /* Extract guards array (optional) */
    http_json_array_t *guards = http_json_object_get_array(json, "guards");
    if (guards && http_json_array_length(guards) > 0) {
        /* If guards specified, disable all first, then enable specified */
        req->guards_llm = false;
        req->guards_rag = false;
        req->guards_agent = false;
        req->guards_tool = false;
        req->guards_mcp = false;
        req->guards_api = false;
        
        for (size_t i = 0; i < http_json_array_length(guards); i++) {
            http_json_value_t *g = http_json_array_get(guards, i);
            if (g && http_json_is_string(g)) {
                const char *guard_name = g->data.string;
                if (strcmp(guard_name, "llm") == 0) req->guards_llm = true;
                if (strcmp(guard_name, "rag") == 0) req->guards_rag = true;
                if (strcmp(guard_name, "agent") == 0) req->guards_agent = true;
                if (strcmp(guard_name, "tool") == 0) req->guards_tool = true;
                if (strcmp(guard_name, "mcp") == 0) req->guards_mcp = true;
                if (strcmp(guard_name, "api") == 0) req->guards_api = true;
            }
        }
    }
    
    /* Extract options (optional) */
    http_json_value_t *options = http_json_object_get(json, "options");
    if (options && http_json_is_object(options)) {
        req->include_details = http_json_object_get_bool(options, "include_details");
    }
    
    /* Note: We don't free json here because req->input points to it.
     * In production, we'd strdup the strings. This is a simplification. */
    
    return 0;
}

/* ============================================================================
 * Guard Invocation (Stub — to be connected to real guards)
 * ============================================================================ */

static void run_llm_guard(const char *input, bool *triggered, double *score, const char **reason) {
    /* TODO: Connect to real LLM guard */
    /* For now, simple pattern detection */
    
    *triggered = false;
    *score = 0.0;
    *reason = NULL;
    
    /* Check for injection patterns */
    if (strstr(input, "ignore previous") || 
        strstr(input, "ignore all") ||
        strstr(input, "system prompt") ||
        strstr(input, "you are now") ||
        strstr(input, "forget your") ||
        strstr(input, "disregard")) {
        *triggered = true;
        *score = 0.95;
        *reason = "Prompt injection pattern detected";
        return;
    }
    
    /* Check for jailbreak attempts */
    if (strstr(input, "DAN") ||
        strstr(input, "Developer Mode") ||
        strstr(input, "jailbreak") ||
        strstr(input, "bypass") ||
        strstr(input, "pretend you")) {
        *triggered = true;
        *score = 0.88;
        *reason = "Jailbreak attempt detected";
        return;
    }
    
    /* Low baseline score for any input */
    *score = 0.05;
}

static void run_rag_guard(const char *input, bool *triggered, double *score) {
    /* TODO: Connect to real RAG guard */
    *triggered = false;
    *score = 0.02;
    
    /* Check for RAG poisoning patterns */
    if (strstr(input, "[[") || strstr(input, "]]") ||
        strstr(input, "document says") ||
        strstr(input, "context:")) {
        *triggered = true;
        *score = 0.75;
    }
}

static void run_agent_guard(const char *input, bool *triggered, double *score) {
    /* TODO: Connect to real Agent guard */
    *triggered = false;
    *score = 0.01;
    
    /* Check for agent manipulation */
    if (strstr(input, "execute") ||
        strstr(input, "run command") ||
        strstr(input, "delete file") ||
        strstr(input, "rm -rf")) {
        *triggered = true;
        *score = 0.92;
    }
}

/* ============================================================================
 * Route Handler
 * ============================================================================ */

int route_analyze_handler(const http_request_t *request,
                          http_response_t *response,
                          void *user_data) {
    (void)user_data;
    
    /* Check method */
    if (request->method != HTTP_METHOD_POST) {
        return http_response_error(response, HTTP_STATUS_METHOD_NOT_ALLOWED, 
                                  "Method not allowed");
    }
    
    /* Check content type */
    if (!request->content_type || 
        strstr(request->content_type, "application/json") == NULL) {
        return http_response_error(response, HTTP_STATUS_BAD_REQUEST,
                                  "Content-Type must be application/json");
    }
    
    /* Parse request */
    analyze_request_t req;
    if (parse_analyze_request(request->body, &req) != 0) {
        return http_response_error(response, HTTP_STATUS_BAD_REQUEST,
                                  "Invalid request: 'input' field required");
    }
    
    /* Start timing */
    clock_t start = clock();
    
    /* Run guards */
    analyze_response_t res = {0};
    double max_score = 0.0;
    
    if (req.guards_llm) {
        run_llm_guard(req.input, &res.llm_triggered, &res.llm_score, &res.llm_reason);
        if (res.llm_score > max_score) max_score = res.llm_score;
    }
    
    if (req.guards_rag) {
        run_rag_guard(req.input, &res.rag_triggered, &res.rag_score);
        if (res.rag_score > max_score) max_score = res.rag_score;
    }
    
    if (req.guards_agent) {
        run_agent_guard(req.input, &res.agent_triggered, &res.agent_score);
        if (res.agent_score > max_score) max_score = res.agent_score;
    }
    
    /* Calculate verdict */
    res.risk_score = max_score;
    
    if (max_score >= 0.8) {
        res.verdict = "BLOCKED";
    } else if (max_score >= 0.5) {
        res.verdict = "SUSPICIOUS";
    } else {
        res.verdict = "ALLOWED";
    }
    
    /* Calculate latency */
    clock_t end = clock();
    res.latency_ms = ((double)(end - start) / CLOCKS_PER_SEC) * 1000.0;
    
    /* Generate request ID */
    char request_id[32];
    generate_request_id(request_id, sizeof(request_id));
    res.request_id = request_id;
    
    /* Build response */
    json_builder_t *builder = json_builder_create();
    
    json_object_start(builder);
    json_add_string(builder, "verdict", res.verdict);
    json_add_number(builder, "risk_score", res.risk_score);
    json_add_number(builder, "latency_ms", res.latency_ms);
    
    /* Guards section */
    json_add_object(builder, "guards");
    
    if (req.guards_llm) {
        json_add_object(builder, "llm");
        json_add_bool(builder, "triggered", res.llm_triggered);
        json_add_number(builder, "score", res.llm_score);
        if (res.llm_reason) {
            json_add_string(builder, "reason", res.llm_reason);
        }
        json_object_end(builder);
    }
    
    if (req.guards_rag) {
        json_add_object(builder, "rag");
        json_add_bool(builder, "triggered", res.rag_triggered);
        json_add_number(builder, "score", res.rag_score);
        json_object_end(builder);
    }
    
    if (req.guards_agent) {
        json_add_object(builder, "agent");
        json_add_bool(builder, "triggered", res.agent_triggered);
        json_add_number(builder, "score", res.agent_score);
        json_object_end(builder);
    }
    
    json_object_end(builder); /* End guards */
    
    json_add_string(builder, "request_id", res.request_id);
    json_object_end(builder); /* End root */
    
    /* Set response */
    response->status = HTTP_STATUS_OK;
    http_response_set_json(response, json_builder_get_string(builder));
    
    json_builder_destroy(builder);
    
    return 0;
}

/* ============================================================================
 * Route Registration
 * ============================================================================ */

http_route_t route_analyze = {
    .method = HTTP_METHOD_POST,
    .path = "/api/v1/analyze",
    .handler = route_analyze_handler,
    .user_data = NULL
};
