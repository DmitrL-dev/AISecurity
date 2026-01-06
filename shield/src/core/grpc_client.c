/*
 * SENTINEL Shield - gRPC Client Implementation
 * 
 * gRPC client for Shield-Brain communication in distributed topologies.
 * Uses HTTP/2 and Protocol Buffers.
 * 
 * Note: This is a minimal implementation without external gRPC library.
 * For production, consider integrating grpc-c or nanopb.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdbool.h>
#include "shield_common.h"
#include "shield_brain.h"
#include "shield_string_safe.h"

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

/* ===== gRPC Frame Types ===== */

#define GRPC_FRAME_DATA     0x00
#define GRPC_FRAME_HEADERS  0x01
#define GRPC_FRAME_SETTINGS 0x04
#define GRPC_FRAME_PING     0x06
#define GRPC_FRAME_GOAWAY   0x07

/* ===== Internal State ===== */

static struct {
    bool initialized;
    char endpoint[512];
    char host[256];
    uint16_t port;
    socket_t sock;
} g_grpc = {0};

/* ===== Frame Helpers ===== */

/* Simple protobuf varint encoding */
static size_t encode_varint(uint64_t value, uint8_t *buf) {
    size_t i = 0;
    while (value >= 0x80) {
        buf[i++] = (uint8_t)((value & 0x7F) | 0x80);
        value >>= 7;
    }
    buf[i++] = (uint8_t)value;
    return i;
}

/* Simple protobuf string encoding (field 1 = input, field 2 = engine) */
static size_t encode_analyze_request(const char *input, const char *engine,
                                      uint8_t *buf, size_t buf_size) {
    size_t pos = 0;
    size_t input_len = strlen(input);
    size_t engine_len = engine ? strlen(engine) : 0;
    
    /* Field 1: input (string) - wire type 2 */
    buf[pos++] = 0x0A; /* field 1, wire type 2 */
    pos += encode_varint(input_len, buf + pos);
    if (pos + input_len < buf_size) {
        memcpy(buf + pos, input, input_len);
        pos += input_len;
    }
    
    /* Field 2: engine (string) - wire type 2 */
    if (engine && engine_len > 0) {
        buf[pos++] = 0x12; /* field 2, wire type 2 */
        pos += encode_varint(engine_len, buf + pos);
        if (pos + engine_len < buf_size) {
            memcpy(buf + pos, engine, engine_len);
            pos += engine_len;
        }
    }
    
    return pos;
}

/* ===== Public API ===== */

int grpc_client_init(const char *endpoint)
{
    if (!endpoint) {
        return -1;
    }
    
    shield_strcopy_s(g_grpc.endpoint, sizeof(g_grpc.endpoint), endpoint);
    
    /* Parse endpoint (grpc://host:port) */
    const char *p = endpoint;
    if (strncmp(p, "grpc://", 7) == 0) {
        p += 7;
    }
    
    /* Extract host and port */
    const char *port_start = strchr(p, ':');
    if (port_start) {
        size_t host_len = port_start - p;
        if (host_len < sizeof(g_grpc.host)) {
            strncpy(g_grpc.host, p, host_len);
            g_grpc.host[host_len] = '\0';
        }
        g_grpc.port = (uint16_t)atoi(port_start + 1);
    } else {
        shield_strcopy_s(g_grpc.host, sizeof(g_grpc.host), p);
        g_grpc.port = 50051; /* Default gRPC port */
    }
    
#ifdef _WIN32
    WSADATA wsa;
    if (WSAStartup(MAKEWORD(2, 2), &wsa) != 0) {
        return -1;
    }
#endif
    
    g_grpc.initialized = true;
    g_grpc.sock = SOCKET_ERROR_VAL;
    
    printf("[gRPC] Client initialized: %s:%u\n", g_grpc.host, g_grpc.port);
    return 0;
}

void grpc_client_shutdown(void)
{
    if (g_grpc.sock != SOCKET_ERROR_VAL) {
        close_socket(g_grpc.sock);
        g_grpc.sock = SOCKET_ERROR_VAL;
    }
    
#ifdef _WIN32
    WSACleanup();
#endif
    
    g_grpc.initialized = false;
    printf("[gRPC] Client shutdown\n");
}

bool grpc_client_available(void)
{
    return g_grpc.initialized && g_grpc.host[0] != '\0';
}

/* Connect to gRPC server */
static shield_err_t grpc_connect(void)
{
    if (g_grpc.sock != SOCKET_ERROR_VAL) {
        return SHIELD_OK; /* Already connected */
    }
    
    struct addrinfo hints = {0};
    struct addrinfo *result = NULL;
    hints.ai_family = AF_INET;
    hints.ai_socktype = SOCK_STREAM;
    
    char port_str[8];
    snprintf(port_str, sizeof(port_str), "%u", g_grpc.port);
    
    if (getaddrinfo(g_grpc.host, port_str, &hints, &result) != 0) {
        return SHIELD_ERR_IO;
    }
    
    g_grpc.sock = socket(result->ai_family, result->ai_socktype, result->ai_protocol);
    if (g_grpc.sock == SOCKET_ERROR_VAL) {
        freeaddrinfo(result);
        return SHIELD_ERR_IO;
    }
    
    if (connect(g_grpc.sock, result->ai_addr, (int)result->ai_addrlen) < 0) {
        freeaddrinfo(result);
        close_socket(g_grpc.sock);
        g_grpc.sock = SOCKET_ERROR_VAL;
        return SHIELD_ERR_IO;
    }
    
    freeaddrinfo(result);
    
    /* Send HTTP/2 connection preface */
    const char *preface = "PRI * HTTP/2.0\r\n\r\nSM\r\n\r\n";
    send(g_grpc.sock, preface, (int)strlen(preface), 0);
    
    /* Send SETTINGS frame (empty) */
    uint8_t settings[9] = {0, 0, 0, GRPC_FRAME_SETTINGS, 0, 0, 0, 0, 0};
    send(g_grpc.sock, (char*)settings, 9, 0);
    
    return SHIELD_OK;
}

int grpc_client_analyze(const char *input, const char *engine,
                        brain_result_t *result)
{
    if (!g_grpc.initialized || !input || !result) {
        return -1;
    }
    
    memset(result, 0, sizeof(*result));
    
    /* Connect if needed */
    if (grpc_connect() != SHIELD_OK) {
        /* Fallback: mark as not detected */
        result->detected = false;
        result->confidence = 0.0;
        result->severity = BRAIN_SEVERITY_NONE;
        result->engine_name = "grpc_unavailable";
        result->reason = "gRPC connection failed";
        return -1;
    }
    
    /* Encode request */
    uint8_t proto_buf[4096];
    size_t proto_len = encode_analyze_request(input, engine, proto_buf, sizeof(proto_buf));
    
    /* Build gRPC message (5-byte prefix + protobuf) */
    uint8_t grpc_msg[4096 + 5];
    grpc_msg[0] = 0; /* Compressed flag */
    grpc_msg[1] = (proto_len >> 24) & 0xFF;
    grpc_msg[2] = (proto_len >> 16) & 0xFF;
    grpc_msg[3] = (proto_len >> 8) & 0xFF;
    grpc_msg[4] = proto_len & 0xFF;
    memcpy(grpc_msg + 5, proto_buf, proto_len);
    
    /* Send as HTTP/2 DATA frame */
    /* Note: This is simplified - real gRPC needs proper HEADERS frame first */
    uint8_t frame_header[9];
    size_t payload_len = proto_len + 5;
    frame_header[0] = (payload_len >> 16) & 0xFF;
    frame_header[1] = (payload_len >> 8) & 0xFF;
    frame_header[2] = payload_len & 0xFF;
    frame_header[3] = GRPC_FRAME_DATA;
    frame_header[4] = 0x01; /* END_STREAM */
    frame_header[5] = 0;
    frame_header[6] = 0;
    frame_header[7] = 0;
    frame_header[8] = 1; /* stream ID = 1 */
    
    send(g_grpc.sock, (char*)frame_header, 9, 0);
    send(g_grpc.sock, (char*)grpc_msg, (int)(proto_len + 5), 0);
    
    /* Receive response (simplified) */
    uint8_t recv_buf[4096];
    int received = recv(g_grpc.sock, (char*)recv_buf, sizeof(recv_buf), 0);
    
    if (received > 14) {
        /* Parse gRPC response (very simplified) */
        /* Look for risk_score field in protobuf */
        result->detected = false;
        result->confidence = 0.0;
        result->severity = BRAIN_SEVERITY_NONE;
        result->engine_name = engine ? engine : "grpc_brain";
        
        /* TODO: Proper protobuf parsing */
        /* For now, mark as successful but no threat detected */
    } else {
        result->detected = false;
        result->confidence = 0.0;
        result->severity = BRAIN_SEVERITY_NONE;
        result->engine_name = "grpc_error";
        result->reason = "Invalid gRPC response";
    }
    
    return 0;
}

/* ===== FFI Adapter (same interface as http_client) ===== */

/* These functions provide the same interface expected by brain_ffi.c */
/* They are compiled only when SHIELD_FFI_GRPC is defined */

#ifdef SHIELD_FFI_GRPC

/* Re-export with standard names for brain_ffi.c */
int grpc_ffi_init(const char *endpoint) {
    return grpc_client_init(endpoint);
}

void grpc_ffi_shutdown(void) {
    grpc_client_shutdown();
}

bool grpc_ffi_available(void) {
    return grpc_client_available();
}

int grpc_ffi_analyze(const char *input, const char *engine,
                     brain_result_t *result) {
    return grpc_client_analyze(input, engine, result);
}

#endif /* SHIELD_FFI_GRPC */
