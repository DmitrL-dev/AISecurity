/*
 * SENTINEL Shield - HTTP Client Implementation
 * 
 * Simple HTTP/1.1 client for Shield-Brain communication.
 * Zero external dependencies.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#ifdef _WIN32
#include <winsock2.h>
#include <ws2tcpip.h>
#pragma comment(lib, "ws2_32.lib")
typedef SOCKET socket_t;
#define SOCKET_ERROR_VAL INVALID_SOCKET
#define close_socket closesocket
#else
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <netdb.h>
#include <unistd.h>
typedef int socket_t;
#define SOCKET_ERROR_VAL (-1)
#define close_socket close
#endif

#include "shield_common.h"

/* ===== HTTP Response Structure ===== */

typedef struct http_response {
    int             status_code;
    char            *body;
    size_t          body_len;
    char            content_type[64];
} http_response_t;

/* ===== Internal Helpers ===== */

static void http_response_init(http_response_t *resp)
{
    if (resp) {
        memset(resp, 0, sizeof(*resp));
    }
}

static void http_response_free(http_response_t *resp)
{
    if (resp && resp->body) {
        free(resp->body);
        resp->body = NULL;
    }
}

/* Parse URL into host, port, path */
static shield_err_t parse_url(const char *url, char *host, size_t host_len,
                               uint16_t *port, char *path, size_t path_len)
{
    if (!url || !host || !port || !path) {
        return SHIELD_ERR_INVALID;
    }
    
    *port = 80;
    
    /* Skip http:// or https:// */
    const char *p = url;
    if (strncmp(p, "http://", 7) == 0) {
        p += 7;
    } else if (strncmp(p, "https://", 8) == 0) {
        p += 8;
        *port = 443; /* Note: TLS not implemented in this simple client */
    }
    
    /* Find path separator */
    const char *path_start = strchr(p, '/');
    const char *port_start = strchr(p, ':');
    
    /* Extract host */
    size_t host_end;
    if (port_start && (!path_start || port_start < path_start)) {
        host_end = port_start - p;
        /* Parse port */
        *port = (uint16_t)atoi(port_start + 1);
    } else if (path_start) {
        host_end = path_start - p;
    } else {
        host_end = strlen(p);
    }
    
    if (host_end >= host_len) {
        return SHIELD_ERR_INVALID;
    }
    
    strncpy(host, p, host_end);
    host[host_end] = '\0';
    
    /* Extract path */
    if (path_start) {
        strncpy(path, path_start, path_len - 1);
        path[path_len - 1] = '\0';
    } else {
        strcpy(path, "/");
    }
    
    return SHIELD_OK;
}

/* ===== HTTP Client Functions ===== */

/*
 * Send HTTP POST request with JSON body
 * 
 * @param url       Full URL (e.g., "http://localhost:8080/api/v1/analyze")
 * @param json_body JSON request body
 * @param response  Output response structure (caller must call http_response_free)
 * @return SHIELD_OK on success
 */
shield_err_t http_post_json(const char *url, const char *json_body, 
                             http_response_t *response)
{
    if (!url || !json_body || !response) {
        return SHIELD_ERR_INVALID;
    }
    
    http_response_init(response);
    
    /* Parse URL */
    char host[256];
    char path[512];
    uint16_t port;
    
    shield_err_t err = parse_url(url, host, sizeof(host), &port, path, sizeof(path));
    if (err != SHIELD_OK) {
        return err;
    }
    
#ifdef _WIN32
    WSADATA wsa;
    if (WSAStartup(MAKEWORD(2, 2), &wsa) != 0) {
        return SHIELD_ERR_IO;
    }
#endif
    
    /* Resolve hostname */
    struct addrinfo hints = {0};
    struct addrinfo *result = NULL;
    hints.ai_family = AF_INET;
    hints.ai_socktype = SOCK_STREAM;
    
    char port_str[8];
    snprintf(port_str, sizeof(port_str), "%u", port);
    
    if (getaddrinfo(host, port_str, &hints, &result) != 0) {
        return SHIELD_ERR_IO;
    }
    
    /* Create socket */
    socket_t sock = socket(result->ai_family, result->ai_socktype, result->ai_protocol);
    if (sock == SOCKET_ERROR_VAL) {
        freeaddrinfo(result);
        return SHIELD_ERR_IO;
    }
    
    /* Connect */
    if (connect(sock, result->ai_addr, (int)result->ai_addrlen) < 0) {
        freeaddrinfo(result);
        close_socket(sock);
        return SHIELD_ERR_IO;
    }
    
    freeaddrinfo(result);
    
    /* Build HTTP request */
    size_t body_len = strlen(json_body);
    char request[4096];
    int request_len = snprintf(request, sizeof(request),
        "POST %s HTTP/1.1\r\n"
        "Host: %s:%u\r\n"
        "Content-Type: application/json\r\n"
        "Content-Length: %zu\r\n"
        "Connection: close\r\n"
        "User-Agent: SENTINEL-Shield/1.0\r\n"
        "\r\n"
        "%s",
        path, host, port, body_len, json_body);
    
    /* Send request */
    if (send(sock, request, request_len, 0) != request_len) {
        close_socket(sock);
        return SHIELD_ERR_IO;
    }
    
    /* Receive response */
    char recv_buf[8192];
    size_t total_received = 0;
    char *full_response = NULL;
    
    while (1) {
        int received = recv(sock, recv_buf, sizeof(recv_buf), 0);
        if (received <= 0) {
            break;
        }
        
        /* Grow buffer */
        size_t new_cap = total_received + received + 1;
        char *new_buf = realloc(full_response, new_cap);
        if (!new_buf) {
            free(full_response);
            close_socket(sock);
            return SHIELD_ERR_NOMEM;
        }
        full_response = new_buf;
        
        memcpy(full_response + total_received, recv_buf, received);
        total_received += received;
        full_response[total_received] = '\0';
    }
    
    close_socket(sock);
    
    if (!full_response) {
        return SHIELD_ERR_IO;
    }
    
    /* Parse HTTP response */
    /* Find status code */
    char *status_line = full_response;
    if (strncmp(status_line, "HTTP/1.", 7) == 0) {
        response->status_code = atoi(status_line + 9);
    }
    
    /* Find body (after \r\n\r\n) */
    char *body_start = strstr(full_response, "\r\n\r\n");
    if (body_start) {
        body_start += 4;
        response->body_len = total_received - (body_start - full_response);
        response->body = malloc(response->body_len + 1);
        if (response->body) {
            memcpy(response->body, body_start, response->body_len);
            response->body[response->body_len] = '\0';
        }
    }
    
    free(full_response);
    
    return (response->status_code >= 200 && response->status_code < 300) 
           ? SHIELD_OK : SHIELD_ERR_IO;
}

/* ===== Brain API Integration ===== */

typedef struct brain_analyze_result {
    float           risk_score;
    char            verdict[32];
    char            reason[256];
    bool            blocked;
} brain_analyze_result_t;

/*
 * Send analyze request to Brain
 *
 * @param brain_url   Brain API URL (e.g., "http://localhost:8080")
 * @param prompt      Text to analyze
 * @param direction   "ingress" or "egress"
 * @param result      Output result structure
 * @return SHIELD_OK on success
 */
shield_err_t brain_analyze(const char *brain_url, const char *prompt,
                            const char *direction, brain_analyze_result_t *result)
{
    if (!brain_url || !prompt || !result) {
        return SHIELD_ERR_INVALID;
    }
    
    memset(result, 0, sizeof(*result));
    
    /* Build full URL */
    char url[512];
    snprintf(url, sizeof(url), "%s/api/v1/analyze", brain_url);
    
    /* Build JSON body */
    char json_body[4096];
    snprintf(json_body, sizeof(json_body),
        "{"
        "\"prompt\": \"%.*s\","
        "\"direction\": \"%s\","
        "\"session_id\": \"shield-direct\""
        "}",
        (int)(sizeof(json_body) - 200), prompt,
        direction ? direction : "ingress");
    
    /* Send request */
    http_response_t response;
    shield_err_t err = http_post_json(url, json_body, &response);
    
    if (err == SHIELD_OK && response.body) {
        /* Parse JSON response (simple extraction) */
        /* Look for "risk_score": X.XX */
        const char *risk = strstr(response.body, "\"risk_score\"");
        if (risk) {
            const char *colon = strchr(risk, ':');
            if (colon) {
                result->risk_score = (float)atof(colon + 1);
            }
        }
        
        /* Look for "blocked": true/false */
        if (strstr(response.body, "\"blocked\": true") ||
            strstr(response.body, "\"blocked\":true")) {
            result->blocked = true;
        }
        
        /* Determine verdict */
        if (result->risk_score >= 0.9f) {
            strcpy(result->verdict, "BLOCK");
            result->blocked = true;
        } else if (result->risk_score >= 0.7f) {
            strcpy(result->verdict, "QUARANTINE");
        } else if (result->risk_score >= 0.5f) {
            strcpy(result->verdict, "WARN");
        } else {
            strcpy(result->verdict, "ALLOW");
        }
    }
    
    http_response_free(&response);
    return err;
}

/* ===== Convenience Functions ===== */

shield_err_t brain_analyze_ingress(const char *brain_url, const char *prompt,
                                    brain_analyze_result_t *result)
{
    return brain_analyze(brain_url, prompt, "ingress", result);
}

shield_err_t brain_analyze_egress(const char *brain_url, const char *response_text,
                                   brain_analyze_result_t *result)
{
    return brain_analyze(brain_url, response_text, "egress", result);
}
