/*
 * SENTINEL Shield - SBP (Shield-Brain Protocol) Implementation
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#ifdef _WIN32
#include <winsock2.h>
#include <ws2tcpip.h>
#pragma comment(lib, "ws2_32.lib")
#else
#include <netdb.h>
#include <fcntl.h>
#include <poll.h>
#endif

#include "shield_common.h"
#include "protocol_sbp.h"

#define SBP_MAGIC 0x53425001 /* "SBP\x01" */
#define SBP_VERSION 0x0100   /* 1.0 */

/* Get current timestamp in milliseconds */
static uint64_t get_timestamp_ms(void)
{
    struct timespec ts;
    clock_gettime(CLOCK_REALTIME, &ts);
    return (uint64_t)ts.tv_sec * 1000 + ts.tv_nsec / 1000000;
}

/* Connect to Brain */
shield_err_t sbp_connect(sbp_connection_t *conn, const char *host, uint16_t port)
{
    if (!conn || !host) {
        return SHIELD_ERR_INVALID;
    }
    
    memset(conn, 0, sizeof(*conn));
    strncpy(conn->host, host, sizeof(conn->host) - 1);
    conn->port = port;
    conn->next_sequence = 1;
    
#ifdef _WIN32
    WSADATA wsa;
    WSAStartup(MAKEWORD(2, 2), &wsa);
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
    conn->socket = socket(result->ai_family, result->ai_socktype, result->ai_protocol);
    if (conn->socket < 0) {
        freeaddrinfo(result);
        return SHIELD_ERR_IO;
    }
    
    /* Connect */
    if (connect(conn->socket, result->ai_addr, (int)result->ai_addrlen) < 0) {
        freeaddrinfo(result);
#ifdef _WIN32
        closesocket(conn->socket);
#else
        close(conn->socket);
#endif
        return SHIELD_ERR_IO;
    }
    
    freeaddrinfo(result);
    conn->connected = true;
    conn->last_heartbeat = get_timestamp_ms();
    
    LOG_INFO("SBP connected to %s:%u", host, port);
    return SHIELD_OK;
}

/* Disconnect */
void sbp_disconnect(sbp_connection_t *conn)
{
    if (!conn) {
        return;
    }
    
    if (conn->connected) {
#ifdef _WIN32
        closesocket(conn->socket);
#else
        close(conn->socket);
#endif
        conn->connected = false;
        LOG_INFO("SBP disconnected");
    }
}

/* Check connection */
bool sbp_is_connected(sbp_connection_t *conn)
{
    return conn && conn->connected;
}

/* Send raw message */
static shield_err_t sbp_send_raw(sbp_connection_t *conn, 
                                  sbp_msg_type_t msg_type,
                                  const void *payload, size_t payload_len)
{
    if (!conn || !conn->connected) {
        return SHIELD_ERR_IO;
    }
    
    /* Build header */
    sbp_header_t header = {
        .magic = SBP_MAGIC,
        .version = SBP_VERSION,
        .msg_type = (uint16_t)msg_type,
        .sequence = conn->next_sequence++,
        .payload_len = (uint32_t)payload_len,
        .timestamp = get_timestamp_ms(),
        .flags = 0,
        .reserved = 0,
    };
    
    /* Send header */
    if (send(conn->socket, (const char *)&header, sizeof(header), 0) != sizeof(header)) {
        return SHIELD_ERR_IO;
    }
    
    /* Send payload */
    if (payload && payload_len > 0) {
        if (send(conn->socket, (const char *)payload, (int)payload_len, 0) != (int)payload_len) {
            return SHIELD_ERR_IO;
        }
    }
    
    return SHIELD_OK;
}

/* Send analyze request */
shield_err_t sbp_send_analyze_request(sbp_connection_t *conn,
                                       uint32_t zone_id,
                                       rule_direction_t direction,
                                       const char *session_id,
                                       const void *data, size_t len)
{
    if (!conn || !data) {
        return SHIELD_ERR_INVALID;
    }
    
    /* Build request */
    size_t total_len = sizeof(sbp_analyze_request_t) + len;
    uint8_t *buffer = malloc(total_len);
    if (!buffer) {
        return SHIELD_ERR_NOMEM;
    }
    
    sbp_analyze_request_t *req = (sbp_analyze_request_t *)buffer;
    req->zone_id = zone_id;
    req->direction = (uint32_t)direction;
    memset(req->session_id, 0, sizeof(req->session_id));
    if (session_id) {
        strncpy(req->session_id, session_id, sizeof(req->session_id) - 1);
    }
    memset(req->source_ip, 0, sizeof(req->source_ip));
    
    /* Copy data */
    memcpy(buffer + sizeof(sbp_analyze_request_t), data, len);
    
    shield_err_t err = sbp_send_raw(conn, SBP_MSG_ANALYZE_REQUEST, buffer, total_len);
    
    free(buffer);
    return err;
}

/* Send threat report */
shield_err_t sbp_send_threat_report(sbp_connection_t *conn,
                                     const sbp_threat_report_t *report)
{
    if (!conn || !report) {
        return SHIELD_ERR_INVALID;
    }
    
    return sbp_send_raw(conn, SBP_MSG_THREAT_REPORT, report, sizeof(*report));
}

/* Send heartbeat */
shield_err_t sbp_send_heartbeat(sbp_connection_t *conn)
{
    if (!conn) {
        return SHIELD_ERR_INVALID;
    }
    
    conn->last_heartbeat = get_timestamp_ms();
    return sbp_send_raw(conn, SBP_MSG_HEARTBEAT, NULL, 0);
}

/* Receive message */
shield_err_t sbp_receive(sbp_connection_t *conn,
                          sbp_header_t *header,
                          void **payload, size_t *payload_len,
                          int timeout_ms)
{
    if (!conn || !conn->connected || !header) {
        return SHIELD_ERR_INVALID;
    }
    
#ifndef _WIN32
    /* Poll for data */
    struct pollfd pfd = {
        .fd = conn->socket,
        .events = POLLIN,
    };
    
    int ret = poll(&pfd, 1, timeout_ms);
    if (ret <= 0) {
        return SHIELD_ERR_IO; /* Timeout or error */
    }
#endif
    
    /* Receive header */
    ssize_t received = recv(conn->socket, (char *)header, sizeof(*header), 0);
    if (received != sizeof(*header)) {
        return SHIELD_ERR_IO;
    }
    
    /* Validate header */
    if (header->magic != SBP_MAGIC) {
        return SHIELD_ERR_PARSE;
    }
    
    /* Receive payload if present */
    if (header->payload_len > 0 && payload && payload_len) {
        *payload = malloc(header->payload_len);
        if (!*payload) {
            return SHIELD_ERR_NOMEM;
        }
        
        received = recv(conn->socket, (char *)*payload, header->payload_len, 0);
        if (received != (ssize_t)header->payload_len) {
            free(*payload);
            *payload = NULL;
            return SHIELD_ERR_IO;
        }
        
        *payload_len = header->payload_len;
    }
    
    return SHIELD_OK;
}

/* Free payload */
void sbp_free_payload(void *payload)
{
    free(payload);
}
