/*
 * SENTINEL Shield - SHSP Protocol Implementation
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#include "shield_common.h"
#include "shield_platform.h"
#include "protocol_shsp.h"

/* Connect to peer */
shield_err_t shsp_connect(shsp_connection_t *conn, const char *address, uint16_t port)
{
    if (!conn || !address) {
        return SHIELD_ERR_INVALID;
    }
    
    memset(conn, 0, sizeof(*conn));
    strncpy(conn->peer_address, address, sizeof(conn->peer_address) - 1);
    conn->peer_port = port ? port : 5400;
    
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
    conn->last_heartbeat_recv = platform_time_ms();
    
    LOG_INFO("SHSP: Connected to %s:%u", address, port);
    
    return SHIELD_OK;
}

/* Disconnect */
void shsp_disconnect(shsp_connection_t *conn)
{
    if (!conn) return;
    
    if (conn->connected && conn->socket >= 0) {
        socket_close(conn->socket);
        conn->socket = -1;
        conn->connected = false;
    }
}

/* Build and send message */
static shield_err_t shsp_send_message(shsp_connection_t *conn, shsp_msg_type_t type,
                                       const void *payload, size_t payload_len,
                                       const char *node_id)
{
    if (!conn || !conn->connected) {
        return SHIELD_ERR_IO;
    }
    
    shsp_header_t header = {
        .magic = SHSP_MAGIC,
        .version = SHSP_VERSION,
        .msg_type = (uint16_t)type,
        .sequence = conn->next_sequence++,
        .payload_len = (uint32_t)payload_len,
    };
    
    if (node_id) {
        strncpy(header.node_id, node_id, sizeof(header.node_id) - 1);
    }
    
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
    
    conn->last_heartbeat_sent = platform_time_ms();
    
    return SHIELD_OK;
}

/* Send heartbeat */
shield_err_t shsp_send_heartbeat(shsp_connection_t *conn, const shsp_heartbeat_t *hb)
{
    if (!conn || !hb) {
        return SHIELD_ERR_INVALID;
    }
    
    return shsp_send_message(conn, SHSP_MSG_HEARTBEAT, hb, sizeof(*hb), NULL);
}

/* Send vote */
shield_err_t shsp_send_vote(shsp_connection_t *conn, const shsp_vote_t *vote)
{
    if (!conn || !vote) {
        return SHIELD_ERR_INVALID;
    }
    
    return shsp_send_message(conn, SHSP_MSG_ELECTION_VOTE, vote, sizeof(*vote), NULL);
}

/* Send state change */
shield_err_t shsp_send_state_change(shsp_connection_t *conn, const shsp_state_change_t *change)
{
    if (!conn || !change) {
        return SHIELD_ERR_INVALID;
    }
    
    return shsp_send_message(conn, SHSP_MSG_STATE_CHANGE, change, sizeof(*change), NULL);
}

/* Receive message */
shield_err_t shsp_receive(shsp_connection_t *conn, shsp_header_t *header,
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
    if (header->magic != SHSP_MAGIC) {
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
    
    conn->last_heartbeat_recv = platform_time_ms();
    
    return SHIELD_OK;
}
