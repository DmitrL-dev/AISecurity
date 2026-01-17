/**
 * SENTINEL Shield - WebSocket Implementation
 * 
 * RFC 6455 WebSocket protocol for real-time events.
 */

#include "ws.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <openssl/sha.h>
#include <openssl/bio.h>
#include <openssl/evp.h>
#include <openssl/buffer.h>

/* WebSocket GUID for key computation */
static const char *WS_GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11";

/* Base64 encode */
static char *base64_encode(const unsigned char *data, size_t len) {
    BIO *bio, *b64;
    BUF_MEM *bptr;
    
    b64 = BIO_new(BIO_f_base64());
    bio = BIO_new(BIO_s_mem());
    bio = BIO_push(b64, bio);
    
    BIO_set_flags(bio, BIO_FLAGS_BASE64_NO_NL);
    BIO_write(bio, data, len);
    BIO_flush(bio);
    BIO_get_mem_ptr(bio, &bptr);
    
    char *result = malloc(bptr->length + 1);
    memcpy(result, bptr->data, bptr->length);
    result[bptr->length] = 0;
    
    BIO_free_all(bio);
    return result;
}

ws_server_t *ws_server_create(void) {
    ws_server_t *server = calloc(1, sizeof(ws_server_t));
    if (!server) return NULL;
    
    pthread_mutex_init(&server->lock, NULL);
    return server;
}

void ws_server_destroy(ws_server_t *server) {
    if (!server) return;
    
    pthread_mutex_lock(&server->lock);
    
    ws_client_t *client = server->clients;
    while (client) {
        ws_client_t *next = client->next;
        ws_close(client->conn, 1001, "Server shutdown");
        free(client);
        client = next;
    }
    
    pthread_mutex_unlock(&server->lock);
    pthread_mutex_destroy(&server->lock);
    free(server);
}

bool ws_is_upgrade(const char *request) {
    return strstr(request, "Upgrade: websocket") != NULL ||
           strstr(request, "Upgrade: WebSocket") != NULL;
}

char *ws_compute_accept_key(const char *client_key) {
    /* Concatenate client key with GUID */
    size_t key_len = strlen(client_key) + strlen(WS_GUID);
    char *concat = malloc(key_len + 1);
    sprintf(concat, "%s%s", client_key, WS_GUID);
    
    /* SHA1 hash */
    unsigned char hash[SHA_DIGEST_LENGTH];
    SHA1((unsigned char *)concat, strlen(concat), hash);
    free(concat);
    
    /* Base64 encode */
    return base64_encode(hash, SHA_DIGEST_LENGTH);
}

int ws_handshake(int fd, const char *request, char *response, size_t resp_size) {
    /* Extract Sec-WebSocket-Key */
    const char *key_start = strstr(request, "Sec-WebSocket-Key:");
    if (!key_start) return -1;
    
    key_start += 18;
    while (*key_start == ' ') key_start++;
    
    char client_key[64] = {0};
    int i = 0;
    while (key_start[i] && key_start[i] != '\r' && key_start[i] != '\n' && i < 63) {
        client_key[i] = key_start[i];
        i++;
    }
    
    /* Compute accept key */
    char *accept_key = ws_compute_accept_key(client_key);
    
    /* Build response */
    int len = snprintf(response, resp_size,
        "HTTP/1.1 101 Switching Protocols\r\n"
        "Upgrade: websocket\r\n"
        "Connection: Upgrade\r\n"
        "Sec-WebSocket-Accept: %s\r\n"
        "\r\n",
        accept_key
    );
    
    free(accept_key);
    return len;
}

ws_conn_t *ws_accept(int fd, const char *request) {
    char response[512];
    int len = ws_handshake(fd, request, response, sizeof(response));
    if (len < 0) return NULL;
    
    if (write(fd, response, len) != len) return NULL;
    
    ws_conn_t *conn = calloc(1, sizeof(ws_conn_t));
    conn->fd = fd;
    conn->state = WS_STATE_OPEN;
    
    return conn;
}

void ws_close(ws_conn_t *conn, uint16_t code, const char *reason) {
    if (!conn || conn->state == WS_STATE_CLOSED) return;
    
    conn->state = WS_STATE_CLOSING;
    
    /* Send close frame */
    uint8_t payload[128];
    payload[0] = (code >> 8) & 0xFF;
    payload[1] = code & 0xFF;
    
    size_t reason_len = reason ? strlen(reason) : 0;
    if (reason_len > 0 && reason_len < 125) {
        memcpy(payload + 2, reason, reason_len);
    }
    
    ws_send_frame(conn->fd, WS_OPCODE_CLOSE, payload, 2 + reason_len);
    
    conn->state = WS_STATE_CLOSED;
    close(conn->fd);
    
    free(conn->path);
    free(conn->origin);
    free(conn->protocol);
    free(conn);
}

int ws_recv_frame(int fd, ws_frame_t *frame) {
    uint8_t header[2];
    if (read(fd, header, 2) != 2) return -1;
    
    frame->fin = (header[0] & 0x80) != 0;
    frame->opcode = header[0] & 0x0F;
    frame->masked = (header[1] & 0x80) != 0;
    frame->payload_len = header[1] & 0x7F;
    
    /* Extended payload length */
    if (frame->payload_len == 126) {
        uint8_t ext[2];
        if (read(fd, ext, 2) != 2) return -1;
        frame->payload_len = (ext[0] << 8) | ext[1];
    } else if (frame->payload_len == 127) {
        uint8_t ext[8];
        if (read(fd, ext, 8) != 8) return -1;
        frame->payload_len = 0;
        for (int i = 0; i < 8; i++) {
            frame->payload_len = (frame->payload_len << 8) | ext[i];
        }
    }
    
    /* Read mask key */
    if (frame->masked) {
        if (read(fd, frame->mask_key, 4) != 4) return -1;
    }
    
    /* Read payload */
    frame->payload = malloc(frame->payload_len + 1);
    if (read(fd, frame->payload, frame->payload_len) != (ssize_t)frame->payload_len) {
        free(frame->payload);
        return -1;
    }
    
    /* Unmask */
    if (frame->masked) {
        for (uint64_t i = 0; i < frame->payload_len; i++) {
            frame->payload[i] ^= frame->mask_key[i % 4];
        }
    }
    
    frame->payload[frame->payload_len] = 0;
    return 0;
}

int ws_send_frame(int fd, ws_opcode_t opcode, const uint8_t *data, size_t len) {
    uint8_t header[10];
    size_t header_len = 2;
    
    header[0] = 0x80 | opcode;  /* FIN + opcode */
    
    if (len < 126) {
        header[1] = len;
    } else if (len < 65536) {
        header[1] = 126;
        header[2] = (len >> 8) & 0xFF;
        header[3] = len & 0xFF;
        header_len = 4;
    } else {
        header[1] = 127;
        for (int i = 0; i < 8; i++) {
            header[9 - i] = (len >> (8 * i)) & 0xFF;
        }
        header_len = 10;
    }
    
    if (write(fd, header, header_len) != (ssize_t)header_len) return -1;
    if (len > 0 && write(fd, data, len) != (ssize_t)len) return -1;
    
    return 0;
}

int ws_send_text(ws_conn_t *conn, const char *text) {
    if (!conn || conn->state != WS_STATE_OPEN) return -1;
    return ws_send_frame(conn->fd, WS_OPCODE_TEXT, (const uint8_t *)text, strlen(text));
}

int ws_send_binary(ws_conn_t *conn, const uint8_t *data, size_t len) {
    if (!conn || conn->state != WS_STATE_OPEN) return -1;
    return ws_send_frame(conn->fd, WS_OPCODE_BINARY, data, len);
}

void ws_frame_free(ws_frame_t *frame) {
    if (frame && frame->payload) {
        free(frame->payload);
        frame->payload = NULL;
    }
}

void ws_add_client(ws_server_t *server, ws_conn_t *conn) {
    pthread_mutex_lock(&server->lock);
    
    ws_client_t *client = malloc(sizeof(ws_client_t));
    client->conn = conn;
    client->next = server->clients;
    server->clients = client;
    server->client_count++;
    
    pthread_mutex_unlock(&server->lock);
}

void ws_remove_client(ws_server_t *server, ws_conn_t *conn) {
    pthread_mutex_lock(&server->lock);
    
    ws_client_t **pp = &server->clients;
    while (*pp) {
        if ((*pp)->conn == conn) {
            ws_client_t *to_free = *pp;
            *pp = (*pp)->next;
            free(to_free);
            server->client_count--;
            break;
        }
        pp = &(*pp)->next;
    }
    
    pthread_mutex_unlock(&server->lock);
}

void ws_broadcast_text(ws_server_t *server, const char *text) {
    pthread_mutex_lock(&server->lock);
    
    ws_client_t *client = server->clients;
    while (client) {
        ws_send_text(client->conn, text);
        client = client->next;
    }
    
    pthread_mutex_unlock(&server->lock);
}

void ws_broadcast_event(ws_server_t *server, ws_event_type_t type, const char *json) {
    ws_broadcast_text(server, json);
}

char *ws_format_detection_event(const char *engine, const char *threat, float confidence) {
    char *json = malloc(512);
    snprintf(json, 512,
        "{\"type\":\"detection\",\"engine\":\"%s\",\"threat\":\"%s\",\"confidence\":%.2f}",
        engine, threat, confidence
    );
    return json;
}

char *ws_format_status_event(const char *status, int active_connections) {
    char *json = malloc(256);
    snprintf(json, 256,
        "{\"type\":\"status\",\"status\":\"%s\",\"connections\":%d}",
        status, active_connections
    );
    return json;
}

char *ws_format_metrics_event(int requests, int detections, float latency_ms) {
    char *json = malloc(256);
    snprintf(json, 256,
        "{\"type\":\"metrics\",\"requests\":%d,\"detections\":%d,\"latency_ms\":%.2f}",
        requests, detections, latency_ms
    );
    return json;
}
