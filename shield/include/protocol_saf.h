/*
 * SENTINEL Shield - SAF (Sentinel Analytics Flow) Protocol
 * 
 * Protocol for streaming analytics data
 */

#ifndef SHIELD_PROTOCOL_SAF_H
#define SHIELD_PROTOCOL_SAF_H

#include "shield_common.h"

#define SAF_MAGIC 0x53414601  /* "SAF\x01" */
#define SAF_VERSION 0x0100

/* SAF Message Types */
typedef enum saf_msg_type {
    /* Metrics */
    SAF_MSG_METRICS = 0x01,
    SAF_MSG_COUNTER = 0x02,
    SAF_MSG_GAUGE = 0x03,
    SAF_MSG_HISTOGRAM = 0x04,
    
    /* Events */
    SAF_MSG_EVENT = 0x10,
    SAF_MSG_ALERT = 0x11,
    
    /* Traces */
    SAF_MSG_TRACE_START = 0x20,
    SAF_MSG_TRACE_SPAN = 0x21,
    SAF_MSG_TRACE_END = 0x22,
    
    /* Logs */
    SAF_MSG_LOG = 0x30,
} saf_msg_type_t;

/* SAF Header (16 bytes) */
typedef struct __attribute__((packed)) saf_header {
    uint32_t    magic;
    uint16_t    version;
    uint16_t    msg_type;
    uint32_t    payload_len;
    uint32_t    timestamp_sec;
} saf_header_t;

/* Metric payload */
typedef struct saf_metric {
    char        name[64];
    char        labels[128];    /* key=value,key=value */
    double      value;
    uint64_t    timestamp_ms;
} saf_metric_t;

/* Event payload */
typedef struct saf_event {
    char        name[64];
    char        source[64];
    char        severity[16];   /* info, warning, error, critical */
    char        message[256];
    uint64_t    timestamp_ms;
} saf_event_t;

/* Alert payload */
typedef struct saf_alert {
    char        rule_name[64];
    char        severity[16];
    char        description[256];
    char        labels[128];
    uint64_t    timestamp_ms;
    bool        firing;         /* true=firing, false=resolved */
} saf_alert_t;

/* Trace span */
typedef struct saf_span {
    char        trace_id[32];
    char        span_id[16];
    char        parent_span_id[16];
    char        operation[64];
    uint64_t    start_time_us;
    uint64_t    duration_us;
    char        status[16];
} saf_span_t;

/* Log entry */
typedef struct saf_log {
    uint64_t    timestamp_ms;
    char        level[8];       /* DEBUG, INFO, WARN, ERROR */
    char        source[64];
    char        message[256];
} saf_log_t;

/* SAF Exporter */
typedef struct saf_exporter {
    int         socket;
    char        endpoint[256];
    uint16_t    port;
    bool        connected;
    uint32_t    sequence;
    
    /* Buffering */
    uint8_t     *buffer;
    size_t      buffer_size;
    size_t      buffer_used;
    
    /* Stats */
    uint64_t    messages_sent;
    uint64_t    bytes_sent;
    uint64_t    errors;
} saf_exporter_t;

/* API */
shield_err_t saf_exporter_init(saf_exporter_t *exp, const char *endpoint, uint16_t port);
void saf_exporter_destroy(saf_exporter_t *exp);

shield_err_t saf_connect(saf_exporter_t *exp);
void saf_disconnect(saf_exporter_t *exp);

/* Send data */
shield_err_t saf_send_metric(saf_exporter_t *exp, const saf_metric_t *metric);
shield_err_t saf_send_event(saf_exporter_t *exp, const saf_event_t *event);
shield_err_t saf_send_alert(saf_exporter_t *exp, const saf_alert_t *alert);
shield_err_t saf_send_span(saf_exporter_t *exp, const saf_span_t *span);
shield_err_t saf_send_log(saf_exporter_t *exp, const saf_log_t *log);

/* Flush buffer */
shield_err_t saf_flush(saf_exporter_t *exp);

#endif /* SHIELD_PROTOCOL_SAF_H */
