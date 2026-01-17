/**
 * SENTINEL Shield - WebSocket Support
 * 
 * RFC 6455 WebSocket protocol implementation for real-time events.
 */

#ifndef SHIELD_WEBSOCKET_H
#define SHIELD_WEBSOCKET_H

#include <stdint.h>
#include <stddef.h>
#include <stdbool.h>
#include <pthread.h>

/* WebSocket opcodes */
typedef enum {
    WS_OPCODE_CONTINUATION = 0x0,
    WS_OPCODE_TEXT = 0x1,
    WS_OPCODE_BINARY = 0x2,
    WS_OPCODE_CLOSE = 0x8,
    WS_OPCODE_PING = 0x9,
    WS_OPCODE_PONG = 0xA,
} ws_opcode_t;

/* Connection states */
typedef enum {
    WS_STATE_CONNECTING,
    WS_STATE_OPEN,
    WS_STATE_CLOSING,
    WS_STATE_CLOSED,
} ws_state_t;

/* WebSocket frame */
typedef struct {
    bool fin;
    ws_opcode_t opcode;
    bool masked;
    uint64_t payload_len;
    uint8_t mask_key[4];
    uint8_t *payload;
} ws_frame_t;

/* WebSocket connection */
typedef struct {
    int fd;
    ws_state_t state;
    char *path;
    char *origin;
    char *protocol;
    void *user_data;
} ws_conn_t;

/* Client list for broadcasting */
typedef struct ws_client {
    ws_conn_t *conn;
    struct ws_client *next;
} ws_client_t;

/* WebSocket server */
typedef struct {
    ws_client_t *clients;
    size_t client_count;
    pthread_mutex_t lock;
} ws_server_t;

/* Event types */
typedef enum {
    WS_EVENT_DETECTION,
    WS_EVENT_ALERT,
    WS_EVENT_STATUS,
    WS_EVENT_METRICS,
} ws_event_type_t;

/* Initialize WebSocket server */
ws_server_t *ws_server_create(void);
void ws_server_destroy(ws_server_t *server);

/* Connection management */
ws_conn_t *ws_accept(int fd, const char *request);
void ws_close(ws_conn_t *conn, uint16_t code, const char *reason);
bool ws_is_upgrade(const char *request);

/* Handshake */
int ws_handshake(int fd, const char *request, char *response, size_t resp_size);
char *ws_compute_accept_key(const char *client_key);

/* Frame operations */
int ws_recv_frame(int fd, ws_frame_t *frame);
int ws_send_frame(int fd, ws_opcode_t opcode, const uint8_t *data, size_t len);
int ws_send_text(ws_conn_t *conn, const char *text);
int ws_send_binary(ws_conn_t *conn, const uint8_t *data, size_t len);
void ws_frame_free(ws_frame_t *frame);

/* Broadcasting */
void ws_broadcast_text(ws_server_t *server, const char *text);
void ws_broadcast_event(ws_server_t *server, ws_event_type_t type, const char *json);

/* Client management */
void ws_add_client(ws_server_t *server, ws_conn_t *conn);
void ws_remove_client(ws_server_t *server, ws_conn_t *conn);

/* Event formatting */
char *ws_format_detection_event(const char *engine, const char *threat, float confidence);
char *ws_format_status_event(const char *status, int active_connections);
char *ws_format_metrics_event(int requests, int detections, float latency_ms);

#endif /* SHIELD_WEBSOCKET_H */
