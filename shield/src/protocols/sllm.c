/**
 * @file sllm.c
 * @brief SENTINEL LLM Forward Proxy Protocol Implementation
 * 
 * Full proxy flow: Ingress Analysis → LLM Forward → Egress Analysis
 * Supports OpenAI, Gemini, Anthropic, Ollama and custom endpoints.
 * 
 * @author SENTINEL Team
 * @version 1.0.0
 * @date January 2026
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <errno.h>

#ifdef _WIN32
    #include <winsock2.h>
    #include <ws2tcpip.h>
    #pragma comment(lib, "ws2_32.lib")
#else
            #include <netdb.h>
            #define closesocket close
#endif

#include "protocols/sllm.h"
#include "shield_string_safe.h"

/* Simple logging macros */
#define SHIELD_LOG_INFO(...)  fprintf(stderr, "[INFO]  " __VA_ARGS__), fprintf(stderr, "\n")
#define SHIELD_LOG_WARN(...)  fprintf(stderr, "[WARN]  " __VA_ARGS__), fprintf(stderr, "\n")

/* ========================================================================= */
/*                              GLOBALS                                       */
/* ========================================================================= */

static sllm_config_t g_sllm_config;
static bool g_sllm_initialized = false;

/* ========================================================================= */
/*                              HELPERS                                       */
/* ========================================================================= */

static double get_time_ms(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return ts.tv_sec * 1000.0 + ts.tv_nsec / 1000000.0;
}

static char *strdup_safe(const char *s) {
    if (!s) return NULL;
    size_t len = strlen(s) + 1;
    char *copy = malloc(len);
    if (copy) memcpy(copy, s, len);
    return copy;
}

/**
 * @brief Simple HTTP POST using raw sockets
 */
static shield_err_t http_post(const char *host, int port, const char *path,
                               const char *headers, const char *body,
                               char **response, size_t *response_len) {
    int sock;
    struct sockaddr_in server_addr;
    struct hostent *server;
    
    /* Create socket */
    sock = socket(AF_INET, SOCK_STREAM, 0);
    if (sock < 0) {
        return SHIELD_ERR_NETWORK;
    }
    
    /* Resolve hostname */
    server = gethostbyname(host);
    if (!server) {
        closesocket(sock);
        return SHIELD_ERR_NETWORK;
    }
    
    /* Setup address */
    memset(&server_addr, 0, sizeof(server_addr));
    server_addr.sin_family = AF_INET;
    memcpy(&server_addr.sin_addr.s_addr, server->h_addr, server->h_length);
    server_addr.sin_port = htons(port);
    
    /* Connect */
    if (connect(sock, (struct sockaddr *)&server_addr, sizeof(server_addr)) < 0) {
        closesocket(sock);
        return SHIELD_ERR_NETWORK;
    }
    
    /* Build HTTP request */
    size_t body_len = body ? strlen(body) : 0;
    size_t req_size = 4096 + body_len;
    char *request = malloc(req_size);
    if (!request) {
        closesocket(sock);
        return SHIELD_ERR_MEMORY;
    }
    
    snprintf(request, req_size,
        "POST %s HTTP/1.1\r\n"
        "Host: %s\r\n"
        "Content-Type: application/json\r\n"
        "Content-Length: %zu\r\n"
        "%s"
        "\r\n"
        "%s",
        path, host, body_len, headers ? headers : "", body ? body : "");
    
    /* Send request */
    if (send(sock, request, strlen(request), 0) < 0) {
        free(request);
        closesocket(sock);
        return SHIELD_ERR_NETWORK;
    }
    free(request);
    
    /* Receive response */
    size_t capacity = 16384;
    size_t received = 0;
    char *buffer = malloc(capacity);
    if (!buffer) {
        closesocket(sock);
        return SHIELD_ERR_MEMORY;
    }
    
    ssize_t n;
    while ((n = recv(sock, buffer + received, capacity - received - 1, 0)) > 0) {
        received += n;
        if (received >= capacity - 1) {
            capacity *= 2;
            if (capacity > SLLM_MAX_RESPONSE_LEN) break;
            char *new_buf = realloc(buffer, capacity);
            if (!new_buf) {
                free(buffer);
                closesocket(sock);
                return SHIELD_ERR_MEMORY;
            }
            buffer = new_buf;
        }
    }
    buffer[received] = '\0';
    
    closesocket(sock);
    
    /* Find body (after \r\n\r\n) */
    char *body_start = strstr(buffer, "\r\n\r\n");
    if (body_start) {
        body_start += 4;
        *response = strdup_safe(body_start);
        *response_len = strlen(body_start);
    } else {
        *response = buffer;
        *response_len = received;
        return SHIELD_OK;
    }
    
    free(buffer);
    return SHIELD_OK;
}

/* ========================================================================= */
/*                          JSON BUILDING                                     */
/* ========================================================================= */

shield_err_t sllm_build_openai_body(const sllm_request_t *req, 
                                     char **body, 
                                     size_t *body_len) {
    /* Build JSON for OpenAI API */
    size_t capacity = 4096;
    for (int i = 0; i < req->message_count; i++) {
        capacity += req->messages[i].content_len + 100;
    }
    
    char *json = malloc(capacity);
    if (!json) return SHIELD_ERR_MEMORY;
    
    int offset = snprintf(json, capacity, 
        "{\"model\":\"%s\",\"messages\":[",
        req->model[0] ? req->model : "gpt-4");
    
    for (int i = 0; i < req->message_count; i++) {
        if (i > 0) json[offset++] = ',';
        offset += snprintf(json + offset, capacity - offset,
            "{\"role\":\"%s\",\"content\":\"%s\"}",
            req->messages[i].role,
            req->messages[i].content);
    }
    
    offset += snprintf(json + offset, capacity - offset, "]}");
    
    *body = json;
    *body_len = offset;
    return SHIELD_OK;
}

shield_err_t sllm_build_gemini_body(const sllm_request_t *req,
                                     char **body,
                                     size_t *body_len) {
    /* Build JSON for Gemini API */
    size_t capacity = 4096;
    for (int i = 0; i < req->message_count; i++) {
        capacity += req->messages[i].content_len + 100;
    }
    
    char *json = malloc(capacity);
    if (!json) return SHIELD_ERR_MEMORY;
    
    int offset = snprintf(json, capacity, "{\"contents\":[");
    
    for (int i = 0; i < req->message_count; i++) {
        if (i > 0) json[offset++] = ',';
        const char *gemini_role = strcmp(req->messages[i].role, "assistant") == 0 
            ? "model" : "user";
        offset += snprintf(json + offset, capacity - offset,
            "{\"role\":\"%s\",\"parts\":[{\"text\":\"%s\"}]}",
            gemini_role,
            req->messages[i].content);
    }
    
    offset += snprintf(json + offset, capacity - offset, "]}");
    
    *body = json;
    *body_len = offset;
    return SHIELD_OK;
}

shield_err_t sllm_build_anthropic_body(const sllm_request_t *req,
                                        char **body,
                                        size_t *body_len) {
    /* Build JSON for Anthropic API */
    size_t capacity = 4096;
    for (int i = 0; i < req->message_count; i++) {
        capacity += req->messages[i].content_len + 100;
    }
    
    char *json = malloc(capacity);
    if (!json) return SHIELD_ERR_MEMORY;
    
    int offset = snprintf(json, capacity, 
        "{\"model\":\"%s\",\"max_tokens\":%d,\"messages\":[",
        req->model[0] ? req->model : "claude-3-sonnet-20240229",
        req->max_tokens > 0 ? req->max_tokens : 4096);
    
    for (int i = 0; i < req->message_count; i++) {
        /* Skip system messages in messages array */
        if (strcmp(req->messages[i].role, "system") == 0) continue;
        if (i > 0) json[offset++] = ',';
        offset += snprintf(json + offset, capacity - offset,
            "{\"role\":\"%s\",\"content\":\"%s\"}",
            req->messages[i].role,
            req->messages[i].content);
    }
    
    offset += snprintf(json + offset, capacity - offset, "]}");
    
    *body = json;
    *body_len = offset;
    return SHIELD_OK;
}

/* ========================================================================= */
/*                          JSON PARSING                                      */
/* ========================================================================= */

static char *extract_json_string(const char *json, const char *key) {
    char pattern[128];
    snprintf(pattern, sizeof(pattern), "\"%s\":\"", key);
    
    const char *start = strstr(json, pattern);
    if (!start) return NULL;
    
    start += strlen(pattern);
    const char *end = strchr(start, '"');
    if (!end) return NULL;
    
    size_t len = end - start;
    char *value = malloc(len + 1);
    if (!value) return NULL;
    
    memcpy(value, start, len);
    value[len] = '\0';
    return value;
}

shield_err_t sllm_parse_openai_response(const char *raw, 
                                         char **content,
                                         size_t *content_len) {
    /* Parse: {"choices":[{"message":{"content":"..."}}]} */
    const char *content_start = strstr(raw, "\"content\":\"");
    if (!content_start) {
        *content = strdup_safe(raw);
        *content_len = strlen(raw);
        return SHIELD_OK;
    }
    
    content_start += 11;
    const char *content_end = content_start;
    
    /* Find closing quote, handling escapes */
    while (*content_end) {
        if (*content_end == '\\' && *(content_end + 1)) {
            content_end += 2;
            continue;
        }
        if (*content_end == '"') break;
        content_end++;
    }
    
    size_t len = content_end - content_start;
    *content = malloc(len + 1);
    if (!*content) return SHIELD_ERR_MEMORY;
    
    memcpy(*content, content_start, len);
    (*content)[len] = '\0';
    *content_len = len;
    
    return SHIELD_OK;
}

shield_err_t sllm_parse_gemini_response(const char *raw,
                                         char **content,
                                         size_t *content_len) {
    /* Parse: {"candidates":[{"content":{"parts":[{"text":"..."}]}}]} */
    const char *text_start = strstr(raw, "\"text\":\"");
    if (!text_start) {
        *content = strdup_safe(raw);
        *content_len = strlen(raw);
        return SHIELD_OK;
    }
    
    text_start += 8;
    const char *text_end = text_start;
    
    while (*text_end) {
        if (*text_end == '\\' && *(text_end + 1)) {
            text_end += 2;
            continue;
        }
        if (*text_end == '"') break;
        text_end++;
    }
    
    size_t len = text_end - text_start;
    *content = malloc(len + 1);
    if (!*content) return SHIELD_ERR_MEMORY;
    
    memcpy(*content, text_start, len);
    (*content)[len] = '\0';
    *content_len = len;
    
    return SHIELD_OK;
}

shield_err_t sllm_parse_anthropic_response(const char *raw,
                                            char **content,
                                            size_t *content_len) {
    /* Parse: {"content":[{"text":"..."}]} */
    const char *text_start = strstr(raw, "\"text\":\"");
    if (!text_start) {
        *content = strdup_safe(raw);
        *content_len = strlen(raw);
        return SHIELD_OK;
    }
    
    text_start += 8;
    const char *text_end = text_start;
    
    while (*text_end) {
        if (*text_end == '\\' && *(text_end + 1)) {
            text_end += 2;
            continue;
        }
        if (*text_end == '"') break;
        text_end++;
    }
    
    size_t len = text_end - text_start;
    *content = malloc(len + 1);
    if (!*content) return SHIELD_ERR_MEMORY;
    
    memcpy(*content, text_start, len);
    (*content)[len] = '\0';
    *content_len = len;
    
    return SHIELD_OK;
}

/* ========================================================================= */
/*                          BRAIN COMMUNICATION                               */
/* ========================================================================= */

static shield_err_t call_brain_analyze(const char *content, 
                                        sllm_analysis_t *analysis,
                                        bool is_egress,
                                        const char *original_prompt) {
    /* Default: allow if Brain unavailable */
    analysis->allowed = true;
    analysis->risk_score = 0.0f;
    strncpy(analysis->verdict_reason, "Brain unavailable (default allow)", 
            sizeof(analysis->verdict_reason) - 1);
    
    if (!g_sllm_config.brain_endpoint[0]) {
        return SHIELD_OK;
    }
    
    /* Build SBP request */
    char *body = malloc(strlen(content) + 256);
    if (!body) return SHIELD_ERR_MEMORY;
    
    if (is_egress) {
        snprintf(body, strlen(content) + 256,
            "{\"response\":\"%s\",\"original_prompt\":\"%s\"}",
            content, original_prompt ? original_prompt : "");
    } else {
        snprintf(body, strlen(content) + 256,
            "{\"prompt\":\"%s\"}", content);
    }
    
    /* Call Brain via SBP */
    char *response = NULL;
    size_t response_len = 0;
    
    const char *path = is_egress ? "/analyze_output" : "/analyze";
    
    shield_err_t err = http_post(
        g_sllm_config.brain_endpoint,
        g_sllm_config.brain_port,
        path,
        "Content-Type: application/json\r\n",
        body,
        &response,
        &response_len
    );
    
    free(body);
    
    if (err != SHIELD_OK) {
        return SHIELD_OK; /* Graceful degradation */
    }
    
    /* Parse response */
    char *allowed_str = extract_json_string(response, "allowed");
    if (allowed_str) {
        analysis->allowed = (strcmp(allowed_str, "true") == 0);
        free(allowed_str);
    }
    
    char *risk_str = extract_json_string(response, "risk_score");
    if (risk_str) {
        analysis->risk_score = (float)atof(risk_str);
        free(risk_str);
    }
    
    char *reason = extract_json_string(response, "verdict_reason");
    if (reason) {
        strncpy(analysis->verdict_reason, reason, sizeof(analysis->verdict_reason) - 1);
        free(reason);
    }
    
    free(response);
    return SHIELD_OK;
}

/* ========================================================================= */
/*                          PUBLIC API                                        */
/* ========================================================================= */

shield_err_t sllm_init(const sllm_config_t *config) {
    if (!config) return SHIELD_ERR_INVALID;
    
    memcpy(&g_sllm_config, config, sizeof(sllm_config_t));
    g_sllm_initialized = true;
    
    SHIELD_LOG_INFO("SLLM initialized with %d providers", config->provider_count);
    return SHIELD_OK;
}

void sllm_shutdown(void) {
    g_sllm_initialized = false;
    SHIELD_LOG_INFO("SLLM shutdown");
}

shield_err_t sllm_set_provider(int provider_index) {
    if (provider_index < 0 || provider_index >= g_sllm_config.provider_count) {
        return SHIELD_ERR_INVALID;
    }
    g_sllm_config.active_provider = provider_index;
    return SHIELD_OK;
}

shield_err_t sllm_analyze_ingress(const char *content,
                                   sllm_analysis_t *analysis) {
    if (!content || !analysis) return SHIELD_ERR_INVALID;
    return call_brain_analyze(content, analysis, false, NULL);
}

shield_err_t sllm_analyze_egress(const char *response,
                                  const char *original_prompt,
                                  sllm_analysis_t *analysis) {
    if (!response || !analysis) return SHIELD_ERR_INVALID;
    return call_brain_analyze(response, analysis, true, original_prompt);
}

shield_err_t sllm_forward_to_llm(const sllm_request_t *request,
                                  char **response,
                                  size_t *response_len) {
    if (!g_sllm_initialized) return SHIELD_ERR_INVALID;
    
    sllm_provider_config_t *provider = 
        &g_sllm_config.providers[g_sllm_config.active_provider];
    
    if (!provider->enabled) return SHIELD_ERR_INVALID;
    
    /* Build request body for provider */
    char *body = NULL;
    size_t body_len = 0;
    shield_err_t err;
    
    switch (provider->provider) {
        case SLLM_PROVIDER_OPENAI:
        case SLLM_PROVIDER_OLLAMA:
            err = sllm_build_openai_body(request, &body, &body_len);
            break;
        case SLLM_PROVIDER_GEMINI:
            err = sllm_build_gemini_body(request, &body, &body_len);
            break;
        case SLLM_PROVIDER_ANTHROPIC:
            err = sllm_build_anthropic_body(request, &body, &body_len);
            break;
        default:
            err = sllm_build_openai_body(request, &body, &body_len);
    }
    
    if (err != SHIELD_OK) return err;
    
    /* Build authorization header */
    char headers[512];
    snprintf(headers, sizeof(headers), "Authorization: Bearer %s\r\n",
             provider->api_key);
    
    /* Parse endpoint */
    char host[256];
    char path[256];
    int port = 443;
    
    /* Simple URL parsing */
    const char *url = provider->endpoint;
    if (strncmp(url, "https://", 8) == 0) url += 8;
    else if (strncmp(url, "http://", 7) == 0) { url += 7; port = 80; }
    
    const char *slash = strchr(url, '/');
    if (slash) {
        size_t host_len = slash - url;
        strncpy(host, url, host_len);
        host[host_len] = '\0';
        strncpy(path, slash, sizeof(path) - 1);
    } else {
        strncpy(host, url, sizeof(host) - 1);
        shield_strcopy_s(path, sizeof(path), "/");
    }
    
    /* Make request */
    char *raw_response = NULL;
    size_t raw_len = 0;
    
    err = http_post(host, port, path, headers, body, &raw_response, &raw_len);
    free(body);
    
    if (err != SHIELD_OK) return err;
    
    /* Parse response */
    switch (provider->provider) {
        case SLLM_PROVIDER_OPENAI:
        case SLLM_PROVIDER_OLLAMA:
            err = sllm_parse_openai_response(raw_response, response, response_len);
            break;
        case SLLM_PROVIDER_GEMINI:
            err = sllm_parse_gemini_response(raw_response, response, response_len);
            break;
        case SLLM_PROVIDER_ANTHROPIC:
            err = sllm_parse_anthropic_response(raw_response, response, response_len);
            break;
        default:
            err = sllm_parse_openai_response(raw_response, response, response_len);
    }
    
    free(raw_response);
    return err;
}

shield_err_t sllm_proxy_request(const sllm_request_t *request,
                                 sllm_response_t *response) {
    if (!request || !response) return SHIELD_ERR_INVALID;
    
    memset(response, 0, sizeof(*response));
    double start_time = get_time_ms();
    
    /* Extract last user message for analysis */
    const char *user_message = NULL;
    for (int i = request->message_count - 1; i >= 0; i--) {
        if (strcmp(request->messages[i].role, "user") == 0) {
            user_message = request->messages[i].content;
            break;
        }
    }
    
    if (!user_message) {
        response->status = SLLM_STATUS_CONFIG_ERROR;
        strncpy(response->error_message, "No user message found", 
                sizeof(response->error_message) - 1);
        return SHIELD_ERR_INVALID;
    }
    
    /* 1. INGRESS ANALYSIS */
    if (g_sllm_config.ingress_enabled) {
        shield_err_t err = sllm_analyze_ingress(user_message, 
                                                 &response->ingress_analysis);
        if (err != SHIELD_OK) {
            SHIELD_LOG_WARN("Ingress analysis failed, continuing anyway");
        }
        
        if (!response->ingress_analysis.allowed) {
            response->status = SLLM_STATUS_BLOCKED_INGRESS;
            strncpy(response->error_message, 
                    response->ingress_analysis.verdict_reason,
                    sizeof(response->error_message) - 1);
            response->latency_ms = get_time_ms() - start_time;
            return SHIELD_OK;
        }
    }
    
    /* 2. FORWARD TO LLM */
    char *llm_response = NULL;
    size_t llm_response_len = 0;
    
    shield_err_t err = sllm_forward_to_llm(request, &llm_response, &llm_response_len);
    if (err != SHIELD_OK) {
        response->status = SLLM_STATUS_LLM_ERROR;
        strncpy(response->error_message, "LLM request failed",
                sizeof(response->error_message) - 1);
        response->latency_ms = get_time_ms() - start_time;
        return err;
    }
    
    /* 3. EGRESS ANALYSIS */
    if (g_sllm_config.egress_enabled) {
        err = sllm_analyze_egress(llm_response, user_message,
                                   &response->egress_analysis);
        if (err != SHIELD_OK) {
            SHIELD_LOG_WARN("Egress analysis failed, returning raw response");
        }
        
        if (!response->egress_analysis.allowed) {
            response->status = SLLM_STATUS_BLOCKED_EGRESS;
            strncpy(response->error_message,
                    response->egress_analysis.verdict_reason,
                    sizeof(response->error_message) - 1);
            free(llm_response);
            response->latency_ms = get_time_ms() - start_time;
            return SHIELD_OK;
        }
    }
    
    /* 4. RETURN RESPONSE */
    response->status = SLLM_STATUS_OK;
    response->response_content = llm_response;
    response->response_len = llm_response_len;
    response->latency_ms = get_time_ms() - start_time;
    
    return SHIELD_OK;
}

void sllm_response_free(sllm_response_t *response) {
    if (!response) return;
    free(response->response_content);
    free(response->ingress_analysis.detected_threats);
    free(response->ingress_analysis.anonymized_content);
    free(response->ingress_analysis.sanitized_response);
    free(response->egress_analysis.detected_threats);
    free(response->egress_analysis.anonymized_content);
    free(response->egress_analysis.sanitized_response);
    memset(response, 0, sizeof(*response));
}

void sllm_request_free(sllm_request_t *request) {
    if (!request) return;
    for (int i = 0; i < request->message_count; i++) {
        free(request->messages[i].content);
    }
    free(request->messages);
    memset(request, 0, sizeof(*request));
}

const char *sllm_status_str(sllm_status_t status) {
    switch (status) {
        case SLLM_STATUS_OK: return "OK";
        case SLLM_STATUS_BLOCKED_INGRESS: return "BLOCKED_INGRESS";
        case SLLM_STATUS_BLOCKED_EGRESS: return "BLOCKED_EGRESS";
        case SLLM_STATUS_LLM_ERROR: return "LLM_ERROR";
        case SLLM_STATUS_TIMEOUT: return "TIMEOUT";
        case SLLM_STATUS_NETWORK_ERROR: return "NETWORK_ERROR";
        case SLLM_STATUS_CONFIG_ERROR: return "CONFIG_ERROR";
        default: return "UNKNOWN";
    }
}
