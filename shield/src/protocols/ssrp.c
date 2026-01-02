/*
 * SENTINEL Shield - SSRP Protocol Implementation
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#include "shield_common.h"
#include "shield_platform.h"
#include "protocol_ssrp.h"

/* Connect to peer */
shield_err_t ssrp_connect(ssrp_connection_t *conn, const char *address, uint16_t port)
{
    if (!conn || !address) {
        return SHIELD_ERR_INVALID;
    }
    
    memset(conn, 0, sizeof(*conn));
    strncpy(conn->peer_address, address, sizeof(conn->peer_address) - 1);
    conn->peer_port = port ? port : 5401;
    
    platform_network_init();
    
    conn->socket = socket(AF_INET, SOCK_STREAM, 0);
    if (conn->socket < 0) {
        return SHIELD_ERR_IO;
    }
    
    struct sockaddr_in addr = {
        .sin_family = AF_INET,
        .sin_port = htons(conn->peer_port),
    };
    
    if (inet_pton(AF_INET, address, &addr.sin_addr) <= 0) {
        struct hostent *host = gethostbyname(address);
        if (!host) {
            socket_close(conn->socket);
            return SHIELD_ERR_IO;
        }
        memcpy(&addr.sin_addr, host->h_addr, host->h_length);
    }
    
    if (connect(conn->socket, (struct sockaddr *)&addr, sizeof(addr)) < 0) {
        socket_close(conn->socket);
        conn->socket = -1;
        return SHIELD_ERR_IO;
    }
    
    conn->connected = true;
    
    LOG_INFO("SSRP: Connected to %s:%u", address, port);
    
    return SHIELD_OK;
}

/* Disconnect */
void ssrp_disconnect(ssrp_connection_t *conn)
{
    if (!conn) return;
    
    if (conn->connected && conn->socket >= 0) {
        socket_close(conn->socket);
        conn->socket = -1;
        conn->connected = false;
    }
}

/* Send message helper */
static shield_err_t ssrp_send_message(ssrp_connection_t *conn, ssrp_msg_type_t type,
                                       ssrp_state_type_t state_type,
                                       const void *payload, size_t payload_len)
{
    if (!conn || !conn->connected) {
        return SHIELD_ERR_IO;
    }
    
    ssrp_header_t header = {
        .magic = SSRP_MAGIC,
        .version = SSRP_VERSION,
        .msg_type = (uint8_t)type,
        .state_type = (uint8_t)state_type,
        .sequence = conn->next_sequence++,
        .payload_len = (uint32_t)payload_len,
        .timestamp = (uint64_t)time(NULL),
    };
    
    /* Send header */
    ssize_t sent = send(conn->socket, (const char *)&header, sizeof(header), 0);
    if (sent != sizeof(header)) {
        return SHIELD_ERR_IO;
    }
    
    /* Send payload */
    if (payload && payload_len > 0) {
        sent = send(conn->socket, (const char *)payload, (int)payload_len, 0);
        if (sent != (ssize_t)payload_len) {
            return SHIELD_ERR_IO;
        }
    }
    
    return SHIELD_OK;
}

/* Request sync */
shield_err_t ssrp_request_sync(ssrp_connection_t *conn, ssrp_state_type_t type)
{
    ssrp_sync_request_t request = {
        .state_type = type,
        .last_known_seq = 0,
        .full_sync = true,
    };
    
    return ssrp_send_message(conn, SSRP_MSG_SYNC_REQUEST, type,
                              &request, sizeof(request));
}

/* Send delta update */
shield_err_t ssrp_send_delta(ssrp_connection_t *conn, ssrp_state_type_t type,
                              uint8_t operation, const void *key, size_t key_len,
                              const void *value, size_t value_len)
{
    if (!conn || !key) {
        return SHIELD_ERR_INVALID;
    }
    
    /* Build delta entry */
    size_t entry_size = sizeof(ssrp_delta_entry_t) + key_len + value_len;
    uint8_t *buffer = malloc(entry_size);
    if (!buffer) {
        return SHIELD_ERR_NOMEM;
    }
    
    ssrp_delta_entry_t *entry = (ssrp_delta_entry_t *)buffer;
    entry->operation = operation;
    entry->state_type = (uint8_t)type;
    entry->key_len = (uint16_t)key_len;
    entry->value_len = (uint32_t)value_len;
    
    memcpy(buffer + sizeof(ssrp_delta_entry_t), key, key_len);
    if (value && value_len > 0) {
        memcpy(buffer + sizeof(ssrp_delta_entry_t) + key_len, value, value_len);
    }
    
    shield_err_t err = ssrp_send_message(conn, SSRP_MSG_DELTA_UPDATE, type,
                                           buffer, entry_size);
    
    free(buffer);
    return err;
}

/* Receive message */
shield_err_t ssrp_receive(ssrp_connection_t *conn, ssrp_header_t *header,
                           void **payload, int timeout_ms)
{
    if (!conn || !header) {
        return SHIELD_ERR_INVALID;
    }
    
    if (!conn->connected || conn->socket < 0) {
        return SHIELD_ERR_IO;
    }
    
    /* Set receive timeout */
#ifdef SHIELD_PLATFORM_WINDOWS
    DWORD tv = timeout_ms;
    setsockopt(conn->socket, SOL_SOCKET, SO_RCVTIMEO, (const char *)&tv, sizeof(tv));
#else
    struct timeval tv = {
        .tv_sec = timeout_ms / 1000,
        .tv_usec = (timeout_ms % 1000) * 1000,
    };
    setsockopt(conn->socket, SOL_SOCKET, SO_RCVTIMEO, &tv, sizeof(tv));
#endif
    
    /* Receive header */
    ssize_t received = recv(conn->socket, (char *)header, sizeof(*header), MSG_WAITALL);
    if (received != sizeof(*header)) {
        return received == 0 ? SHIELD_ERR_DISCONNECTED : SHIELD_ERR_TIMEOUT;
    }
    
    /* Validate magic */
    if (header->magic != SSRP_MAGIC) {
        return SHIELD_ERR_PARSE;
    }
    
    /* Receive payload if present */
    if (payload && header->payload_len > 0) {
        *payload = malloc(header->payload_len);
        if (!*payload) {
            return SHIELD_ERR_NOMEM;
        }
        
        received = recv(conn->socket, (char *)*payload, header->payload_len, MSG_WAITALL);
        if (received != (ssize_t)header->payload_len) {
            free(*payload);
            *payload = NULL;
            return SHIELD_ERR_IO;
        }
    }
    
    conn->last_sync_time = (uint64_t)time(NULL);
    
    return SHIELD_OK;
}

/* Calculate checksum (FNV-1a based) */
uint64_t ssrp_calculate_checksum(ssrp_state_type_t type, const void *data, size_t len)
{
    uint64_t hash = 14695981039346656037ULL;
    const uint8_t *bytes = (const uint8_t *)data;
    
    /* Include type in checksum */
    hash ^= (uint8_t)type;
    hash *= 1099511628211ULL;
    
    /* Hash data */
    for (size_t i = 0; i < len; i++) {
        hash ^= bytes[i];
        hash *= 1099511628211ULL;
    }
    
    return hash;
}
