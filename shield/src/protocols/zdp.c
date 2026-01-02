/*
 * SENTINEL Shield - ZDP (Zone Discovery Protocol) Implementation
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#ifdef _WIN32
#include <winsock2.h>
#include <ws2tcpip.h>
#else
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <unistd.h>
#include <poll.h>
#endif

#include "shield_common.h"
#include "protocol_zdp.h"

#define ZDP_MAGIC 0x5A445001 /* "ZDP\x01" */
#define ZDP_VERSION 0x0100
#define ZDP_MULTICAST_GROUP "239.255.255.250"
#define ZDP_DEFAULT_TTL 300

/* Get current timestamp */
static uint64_t get_time_sec(void)
{
    return (uint64_t)time(NULL);
}

/* Initialize ZDP */
shield_err_t zdp_init(zdp_discovery_t *disc, uint16_t port)
{
    if (!disc) {
        return SHIELD_ERR_INVALID;
    }
    
    memset(disc, 0, sizeof(*disc));
    disc->port = port ? port : 5350;
    
#ifdef _WIN32
    WSADATA wsa;
    WSAStartup(MAKEWORD(2, 2), &wsa);
#endif
    
    /* Create UDP socket */
    disc->socket = socket(AF_INET, SOCK_DGRAM, 0);
    if (disc->socket < 0) {
        return SHIELD_ERR_IO;
    }
    
    /* Allow reuse */
    int reuse = 1;
    setsockopt(disc->socket, SOL_SOCKET, SO_REUSEADDR, (const char *)&reuse, sizeof(reuse));
    
    /* Bind */
    struct sockaddr_in addr = {
        .sin_family = AF_INET,
        .sin_port = htons(disc->port),
        .sin_addr.s_addr = INADDR_ANY,
    };
    
    if (bind(disc->socket, (struct sockaddr *)&addr, sizeof(addr)) < 0) {
#ifdef _WIN32
        closesocket(disc->socket);
#else
        close(disc->socket);
#endif
        return SHIELD_ERR_IO;
    }
    
    /* Join multicast group */
    struct ip_mreq mreq = {
        .imr_multiaddr.s_addr = inet_addr(ZDP_MULTICAST_GROUP),
        .imr_interface.s_addr = INADDR_ANY,
    };
    setsockopt(disc->socket, IPPROTO_IP, IP_ADD_MEMBERSHIP, (const char *)&mreq, sizeof(mreq));
    
    disc->running = true;
    LOG_INFO("ZDP initialized on port %u", disc->port);
    
    return SHIELD_OK;
}

/* Destroy ZDP */
void zdp_destroy(zdp_discovery_t *disc)
{
    if (!disc) {
        return;
    }
    
    disc->running = false;
    
    if (disc->socket >= 0) {
#ifdef _WIN32
        closesocket(disc->socket);
#else
        close(disc->socket);
#endif
    }
    
    LOG_INFO("ZDP destroyed");
}

/* Send ZDP message */
static shield_err_t zdp_send(zdp_discovery_t *disc, zdp_msg_type_t type,
                              const void *payload, size_t payload_len)
{
    if (!disc || disc->socket < 0) {
        return SHIELD_ERR_INVALID;
    }
    
    size_t total_len = sizeof(zdp_header_t) + payload_len;
    uint8_t *buffer = malloc(total_len);
    if (!buffer) {
        return SHIELD_ERR_NOMEM;
    }
    
    /* Build header */
    zdp_header_t *header = (zdp_header_t *)buffer;
    header->magic = ZDP_MAGIC;
    header->version = ZDP_VERSION;
    header->msg_type = (uint16_t)type;
    header->payload_len = (uint32_t)payload_len;
    header->reserved = 0;
    
    /* Copy payload */
    if (payload && payload_len > 0) {
        memcpy(buffer + sizeof(zdp_header_t), payload, payload_len);
    }
    
    /* Send to multicast */
    struct sockaddr_in dest = {
        .sin_family = AF_INET,
        .sin_port = htons(disc->port),
        .sin_addr.s_addr = inet_addr(ZDP_MULTICAST_GROUP),
    };
    
    ssize_t sent = sendto(disc->socket, (const char *)buffer, (int)total_len, 0,
                          (struct sockaddr *)&dest, sizeof(dest));
    
    free(buffer);
    
    return sent == (ssize_t)total_len ? SHIELD_OK : SHIELD_ERR_IO;
}

/* Announce zone */
shield_err_t zdp_announce(zdp_discovery_t *disc, const zdp_announce_t *zone)
{
    if (!disc || !zone) {
        return SHIELD_ERR_INVALID;
    }
    
    return zdp_send(disc, ZDP_MSG_ANNOUNCE, zone, sizeof(*zone));
}

/* Leave */
shield_err_t zdp_leave(zdp_discovery_t *disc, const char *zone_id)
{
    if (!disc || !zone_id) {
        return SHIELD_ERR_INVALID;
    }
    
    char payload[64];
    strncpy(payload, zone_id, sizeof(payload) - 1);
    
    return zdp_send(disc, ZDP_MSG_LEAVE, payload, sizeof(payload));
}

/* Query zones */
shield_err_t zdp_query(zdp_discovery_t *disc, zone_type_t type, uint32_t caps)
{
    if (!disc) {
        return SHIELD_ERR_INVALID;
    }
    
    zdp_query_t query = {
        .type_filter = type,
        .cap_filter = caps,
    };
    
    return zdp_send(disc, ZDP_MSG_QUERY, &query, sizeof(query));
}

/* Process incoming messages */
shield_err_t zdp_process(zdp_discovery_t *disc, int timeout_ms)
{
    if (!disc || disc->socket < 0) {
        return SHIELD_ERR_INVALID;
    }
    
#ifndef _WIN32
    struct pollfd pfd = {
        .fd = disc->socket,
        .events = POLLIN,
    };
    
    int ret = poll(&pfd, 1, timeout_ms);
    if (ret <= 0) {
        return SHIELD_OK; /* Timeout, not an error */
    }
#endif
    
    char buffer[2048];
    struct sockaddr_in from;
    socklen_t fromlen = sizeof(from);
    
    ssize_t received = recvfrom(disc->socket, buffer, sizeof(buffer), 0,
                                 (struct sockaddr *)&from, &fromlen);
    
    if (received < (ssize_t)sizeof(zdp_header_t)) {
        return SHIELD_OK;
    }
    
    zdp_header_t *header = (zdp_header_t *)buffer;
    
    if (header->magic != ZDP_MAGIC) {
        return SHIELD_OK; /* Not our protocol */
    }
    
    void *payload = buffer + sizeof(zdp_header_t);
    
    switch (header->msg_type) {
    case ZDP_MSG_ANNOUNCE: {
        if (header->payload_len < sizeof(zdp_announce_t)) {
            break;
        }
        
        zdp_announce_t *announce = (zdp_announce_t *)payload;
        
        /* Find or add zone */
        int slot = -1;
        for (int i = 0; i < disc->zone_count; i++) {
            if (strcmp(disc->zones[i].info.zone_id, announce->zone_id) == 0) {
                slot = i;
                break;
            }
        }
        
        if (slot < 0 && disc->zone_count < SHIELD_MAX_ZONES) {
            slot = disc->zone_count++;
        }
        
        if (slot >= 0) {
            memcpy(&disc->zones[slot].info, announce, sizeof(*announce));
            disc->zones[slot].last_seen = get_time_sec();
            disc->zones[slot].active = true;
            
            LOG_DEBUG("ZDP: Discovered zone %s (%s)", 
                     announce->zone_name, announce->zone_id);
        }
        break;
    }
    
    case ZDP_MSG_LEAVE: {
        char *zone_id = (char *)payload;
        
        for (int i = 0; i < disc->zone_count; i++) {
            if (strcmp(disc->zones[i].info.zone_id, zone_id) == 0) {
                disc->zones[i].active = false;
                LOG_DEBUG("ZDP: Zone left %s", zone_id);
                break;
            }
        }
        break;
    }
    
    default:
        break;
    }
    
    return SHIELD_OK;
}

/* Get discovered zones */
int zdp_get_zones(zdp_discovery_t *disc, zdp_announce_t *zones, int max_zones)
{
    if (!disc || !zones) {
        return 0;
    }
    
    int count = 0;
    for (int i = 0; i < disc->zone_count && count < max_zones; i++) {
        if (disc->zones[i].active) {
            memcpy(&zones[count++], &disc->zones[i].info, sizeof(zdp_announce_t));
        }
    }
    
    return count;
}

/* Cleanup expired zones */
void zdp_cleanup_expired(zdp_discovery_t *disc)
{
    if (!disc) {
        return;
    }
    
    uint64_t now = get_time_sec();
    
    for (int i = 0; i < disc->zone_count; i++) {
        if (disc->zones[i].active) {
            uint32_t ttl = disc->zones[i].info.ttl_seconds;
            if (ttl == 0) ttl = ZDP_DEFAULT_TTL;
            
            if (now - disc->zones[i].last_seen > ttl) {
                disc->zones[i].active = false;
                LOG_DEBUG("ZDP: Zone expired %s", disc->zones[i].info.zone_id);
            }
        }
    }
}
