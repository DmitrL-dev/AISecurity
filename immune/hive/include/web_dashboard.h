/*
 * SENTINEL IMMUNE — Web Dashboard
 * 
 * Lightweight HTTP server for Hive monitoring.
 * Uses htmx for reactive UI without heavy JS.
 */

#ifndef IMMUNE_WEB_DASHBOARD_H
#define IMMUNE_WEB_DASHBOARD_H

#include <stdint.h>
#include <stdbool.h>

/* Default configuration */
#define WEB_DEFAULT_PORT    8888
#define WEB_MAX_CONNECTIONS 32

/* Configuration */
typedef struct {
    uint16_t port;
    bool     enable_auth;
    char     auth_token[64];
} web_config_t;

/* === Lifecycle === */
void web_config_init(web_config_t *config);
int  web_start(const web_config_t *config);
void web_stop(void);
bool web_is_running(void);

/* === Handlers (internal) === */
/* These are registered automatically when web_start is called */

#endif /* IMMUNE_WEB_DASHBOARD_H */
