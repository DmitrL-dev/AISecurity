/*
 * SENTINEL Shield - Syslog Client
 */

#ifndef SHIELD_SYSLOG_H
#define SHIELD_SYSLOG_H

#include "shield_common.h"

/* Syslog facility */
typedef enum syslog_facility {
    SYSLOG_KERN = 0,
    SYSLOG_USER = 1,
    SYSLOG_MAIL = 2,
    SYSLOG_DAEMON = 3,
    SYSLOG_AUTH = 4,
    SYSLOG_SYSLOG = 5,
    SYSLOG_LOCAL0 = 16,
    SYSLOG_LOCAL1 = 17,
    SYSLOG_LOCAL2 = 18,
    SYSLOG_LOCAL3 = 19,
    SYSLOG_LOCAL4 = 20,
    SYSLOG_LOCAL5 = 21,
    SYSLOG_LOCAL6 = 22,
    SYSLOG_LOCAL7 = 23,
} syslog_facility_t;

/* Syslog severity */
typedef enum syslog_severity {
    SYSLOG_EMERG = 0,
    SYSLOG_ALERT = 1,
    SYSLOG_CRIT = 2,
    SYSLOG_ERR = 3,
    SYSLOG_WARNING = 4,
    SYSLOG_NOTICE = 5,
    SYSLOG_INFO = 6,
    SYSLOG_DEBUG = 7,
} syslog_severity_t;

/* Syslog client */
typedef struct syslog_client {
    int             socket;
    char            server[256];
    uint16_t        port;
    bool            use_tcp;
    syslog_facility_t facility;
    char            hostname[64];
    char            app_name[64];
    bool            connected;
} syslog_client_t;

/* API */
shield_err_t syslog_init(syslog_client_t *client, const char *server, uint16_t port);
void syslog_destroy(syslog_client_t *client);

shield_err_t syslog_connect(syslog_client_t *client);
void syslog_disconnect(syslog_client_t *client);

void syslog_set_facility(syslog_client_t *client, syslog_facility_t facility);
void syslog_set_app_name(syslog_client_t *client, const char *name);

/* Send log */
shield_err_t syslog_send(syslog_client_t *client, syslog_severity_t severity,
                          const char *message);
shield_err_t syslog_sendf(syslog_client_t *client, syslog_severity_t severity,
                           const char *fmt, ...);

#endif /* SHIELD_SYSLOG_H */
