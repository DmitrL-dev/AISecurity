/*
 * SENTINEL Shield - Syslog Client Implementation
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdarg.h>
#include <time.h>

#include "shield_common.h"
#include "shield_syslog.h"
#include "shield_platform.h"

/* Initialize */
shield_err_t syslog_init(syslog_client_t *client, const char *server, uint16_t port)
{
    if (!client || !server) {
        return SHIELD_ERR_INVALID;
    }
    
    memset(client, 0, sizeof(*client));
    strncpy(client->server, server, sizeof(client->server) - 1);
    client->port = port ? port : 514;
    client->facility = SYSLOG_LOCAL0;
    client->socket = -1;
    
    /* Get hostname */
    if (gethostname(client->hostname, sizeof(client->hostname)) != 0) {
        strncpy(client->hostname, "shield", sizeof(client->hostname) - 1);
    }
    
    strncpy(client->app_name, "sentinel-shield", sizeof(client->app_name) - 1);
    
    return SHIELD_OK;
}

/* Destroy */
void syslog_destroy(syslog_client_t *client)
{
    if (!client) return;
    syslog_disconnect(client);
}

/* Connect */
shield_err_t syslog_connect(syslog_client_t *client)
{
    if (!client) {
        return SHIELD_ERR_INVALID;
    }
    
    platform_network_init();
    
    int type = client->use_tcp ? SOCK_STREAM : SOCK_DGRAM;
    client->socket = socket(AF_INET, type, 0);
    if (client->socket < 0) {
        return SHIELD_ERR_IO;
    }
    
    struct sockaddr_in addr = {
        .sin_family = AF_INET,
        .sin_port = htons(client->port),
    };
    
    if (inet_pton(AF_INET, client->server, &addr.sin_addr) <= 0) {
        struct hostent *host = gethostbyname(client->server);
        if (!host) {
            socket_close(client->socket);
            client->socket = -1;
            return SHIELD_ERR_IO;
        }
        memcpy(&addr.sin_addr, host->h_addr, host->h_length);
    }
    
    if (client->use_tcp) {
        if (connect(client->socket, (struct sockaddr *)&addr, sizeof(addr)) < 0) {
            socket_close(client->socket);
            client->socket = -1;
            return SHIELD_ERR_IO;
        }
    } else {
        /* For UDP, save address for sendto */
        if (connect(client->socket, (struct sockaddr *)&addr, sizeof(addr)) < 0) {
            socket_close(client->socket);
            client->socket = -1;
            return SHIELD_ERR_IO;
        }
    }
    
    client->connected = true;
    
    return SHIELD_OK;
}

/* Disconnect */
void syslog_disconnect(syslog_client_t *client)
{
    if (!client) return;
    
    if (client->socket >= 0) {
        socket_close(client->socket);
        client->socket = -1;
    }
    client->connected = false;
}

/* Set facility */
void syslog_set_facility(syslog_client_t *client, syslog_facility_t facility)
{
    if (client) {
        client->facility = facility;
    }
}

/* Set app name */
void syslog_set_app_name(syslog_client_t *client, const char *name)
{
    if (client && name) {
        strncpy(client->app_name, name, sizeof(client->app_name) - 1);
    }
}

/* Get RFC 5424 timestamp */
static void get_timestamp(char *buf, size_t len)
{
    time_t now = time(NULL);
    struct tm *tm = gmtime(&now);
    strftime(buf, len, "%Y-%m-%dT%H:%M:%SZ", tm);
}

/* Send log */
shield_err_t syslog_send(syslog_client_t *client, syslog_severity_t severity,
                          const char *message)
{
    if (!client || !message) {
        return SHIELD_ERR_INVALID;
    }
    
    /* Auto-connect */
    if (!client->connected) {
        shield_err_t err = syslog_connect(client);
        if (err != SHIELD_OK) return err;
    }
    
    /* Build syslog message (RFC 5424) */
    char timestamp[32];
    get_timestamp(timestamp, sizeof(timestamp));
    
    int priority = (client->facility * 8) + severity;
    
    char syslog_msg[2048];
    int len = snprintf(syslog_msg, sizeof(syslog_msg),
        "<%d>1 %s %s %s - - - %s",
        priority,
        timestamp,
        client->hostname,
        client->app_name,
        message
    );
    
    if (len < 0 || len >= (int)sizeof(syslog_msg)) {
        return SHIELD_ERR_INVALID;
    }
    
    /* Send */
    ssize_t sent = send(client->socket, syslog_msg, len, 0);
    if (sent < 0) {
        client->connected = false;
        return SHIELD_ERR_IO;
    }
    
    return SHIELD_OK;
}

/* Send formatted log */
shield_err_t syslog_sendf(syslog_client_t *client, syslog_severity_t severity,
                           const char *fmt, ...)
{
    if (!client || !fmt) {
        return SHIELD_ERR_INVALID;
    }
    
    char message[1024];
    va_list args;
    va_start(args, fmt);
    vsnprintf(message, sizeof(message), fmt, args);
    va_end(args);
    
    return syslog_send(client, severity, message);
}
