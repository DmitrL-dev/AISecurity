/*
 * SENTINEL Shield - SAF Protocol Implementation
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#include "shield_common.h"
#include "shield_platform.h"
#include "protocol_saf.h"

#define SAF_BUFFER_SIZE 65536

/* Get current time in milliseconds */
static uint64_t get_time_ms(void)
{
    return platform_time_ms();
}

/* Initialize exporter */
shield_err_t saf_exporter_init(saf_exporter_t *exp, const char *endpoint, uint16_t port)
{
    if (!exp || !endpoint) {
        return SHIELD_ERR_INVALID;
    }
    
    memset(exp, 0, sizeof(*exp));
    strncpy(exp->endpoint, endpoint, sizeof(exp->endpoint) - 1);
    exp->port = port ? port : 4317; /* Default OTLP port */
    exp->socket = -1;
    
    exp->buffer_size = SAF_BUFFER_SIZE;
    exp->buffer = malloc(exp->buffer_size);
    if (!exp->buffer) {
        return SHIELD_ERR_NOMEM;
    }
    
    return SHIELD_OK;
}

/* Destroy exporter */
void saf_exporter_destroy(saf_exporter_t *exp)
{
    if (!exp) {
        return;
    }
    
    saf_disconnect(exp);
    free(exp->buffer);
    exp->buffer = NULL;
}

/* Connect */
shield_err_t saf_connect(saf_exporter_t *exp)
{
    if (!exp) {
        return SHIELD_ERR_INVALID;
    }
    
    platform_network_init();
    
    exp->socket = socket(AF_INET, SOCK_STREAM, 0);
    if (exp->socket < 0) {
        return SHIELD_ERR_IO;
    }
    
    struct sockaddr_in addr = {
        .sin_family = AF_INET,
        .sin_port = htons(exp->port),
    };
    
    if (inet_pton(AF_INET, exp->endpoint, &addr.sin_addr) <= 0) {
        /* Try hostname resolution */
        struct hostent *host = gethostbyname(exp->endpoint);
        if (!host) {
            socket_close(exp->socket);
            return SHIELD_ERR_IO;
        }
        memcpy(&addr.sin_addr, host->h_addr, host->h_length);
    }
    
    if (connect(exp->socket, (struct sockaddr *)&addr, sizeof(addr)) < 0) {
        socket_close(exp->socket);
        exp->socket = -1;
        return SHIELD_ERR_IO;
    }
    
    exp->connected = true;
    LOG_INFO("SAF: Connected to %s:%u", exp->endpoint, exp->port);
    
    return SHIELD_OK;
}

/* Disconnect */
void saf_disconnect(saf_exporter_t *exp)
{
    if (!exp) {
        return;
    }
    
    if (exp->connected && exp->socket >= 0) {
        saf_flush(exp);
        socket_close(exp->socket);
        exp->socket = -1;
        exp->connected = false;
    }
}

/* Send raw message */
static shield_err_t saf_send_raw(saf_exporter_t *exp, saf_msg_type_t type,
                                  const void *payload, size_t payload_len)
{
    if (!exp || !exp->connected) {
        return SHIELD_ERR_IO;
    }
    
    /* Check if fits in buffer */
    size_t msg_size = sizeof(saf_header_t) + payload_len;
    if (exp->buffer_used + msg_size > exp->buffer_size) {
        shield_err_t err = saf_flush(exp);
        if (err != SHIELD_OK) {
            return err;
        }
    }
    
    /* Build header */
    saf_header_t header = {
        .magic = SAF_MAGIC,
        .version = SAF_VERSION,
        .msg_type = (uint16_t)type,
        .payload_len = (uint32_t)payload_len,
        .timestamp_sec = (uint32_t)time(NULL),
    };
    
    /* Add to buffer */
    memcpy(exp->buffer + exp->buffer_used, &header, sizeof(header));
    exp->buffer_used += sizeof(header);
    
    if (payload && payload_len > 0) {
        memcpy(exp->buffer + exp->buffer_used, payload, payload_len);
        exp->buffer_used += payload_len;
    }
    
    exp->sequence++;
    
    return SHIELD_OK;
}

/* Send metric */
shield_err_t saf_send_metric(saf_exporter_t *exp, const saf_metric_t *metric)
{
    if (!exp || !metric) {
        return SHIELD_ERR_INVALID;
    }
    
    saf_metric_t m = *metric;
    if (m.timestamp_ms == 0) {
        m.timestamp_ms = get_time_ms();
    }
    
    return saf_send_raw(exp, SAF_MSG_METRICS, &m, sizeof(m));
}

/* Send event */
shield_err_t saf_send_event(saf_exporter_t *exp, const saf_event_t *event)
{
    if (!exp || !event) {
        return SHIELD_ERR_INVALID;
    }
    
    saf_event_t e = *event;
    if (e.timestamp_ms == 0) {
        e.timestamp_ms = get_time_ms();
    }
    
    return saf_send_raw(exp, SAF_MSG_EVENT, &e, sizeof(e));
}

/* Send alert */
shield_err_t saf_send_alert(saf_exporter_t *exp, const saf_alert_t *alert)
{
    if (!exp || !alert) {
        return SHIELD_ERR_INVALID;
    }
    
    saf_alert_t a = *alert;
    if (a.timestamp_ms == 0) {
        a.timestamp_ms = get_time_ms();
    }
    
    return saf_send_raw(exp, SAF_MSG_ALERT, &a, sizeof(a));
}

/* Send span */
shield_err_t saf_send_span(saf_exporter_t *exp, const saf_span_t *span)
{
    if (!exp || !span) {
        return SHIELD_ERR_INVALID;
    }
    
    return saf_send_raw(exp, SAF_MSG_TRACE_SPAN, span, sizeof(*span));
}

/* Send log */
shield_err_t saf_send_log(saf_exporter_t *exp, const saf_log_t *log)
{
    if (!exp || !log) {
        return SHIELD_ERR_INVALID;
    }
    
    saf_log_t l = *log;
    if (l.timestamp_ms == 0) {
        l.timestamp_ms = get_time_ms();
    }
    
    return saf_send_raw(exp, SAF_MSG_LOG, &l, sizeof(l));
}

/* Flush buffer */
shield_err_t saf_flush(saf_exporter_t *exp)
{
    if (!exp || exp->buffer_used == 0) {
        return SHIELD_OK;
    }
    
    if (!exp->connected || exp->socket < 0) {
        exp->buffer_used = 0;
        exp->errors++;
        return SHIELD_ERR_IO;
    }
    
    ssize_t sent = send(exp->socket, (const char *)exp->buffer, (int)exp->buffer_used, 0);
    if (sent < 0) {
        exp->errors++;
        exp->buffer_used = 0;
        return SHIELD_ERR_IO;
    }
    
    exp->bytes_sent += sent;
    exp->buffer_used = 0;
    
    return SHIELD_OK;
}
