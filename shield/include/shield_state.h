/*
 * SENTINEL Shield - Global State Manager
 * 
 * Centralized state for all Shield modules and CLI integration.
 * This is the single source of truth for Shield configuration.
 */

#ifndef SHIELD_STATE_H
#define SHIELD_STATE_H

#include <stdbool.h>
#include <stdint.h>
#include <time.h>

#include "shield_common.h"

/* ===== Module States ===== */

typedef enum module_state {
    MODULE_DISABLED = 0,
    MODULE_ENABLED = 1,
    MODULE_ERROR = 2
} module_state_t;

/* ===== ThreatHunter State ===== */
typedef struct threat_hunter_state {
    module_state_t state;
    float sensitivity;
    bool hunt_ioc;
    bool hunt_behavioral;
    bool hunt_anomaly;
    uint64_t hunts_completed;
    uint64_t threats_found;
    time_t last_hunt;
} threat_hunter_state_t;

/* ===== Watchdog State ===== */
typedef struct watchdog_state {
    module_state_t state;
    bool auto_recovery;
    uint32_t check_interval_ms;
    float system_health;
    uint64_t checks_total;
    uint64_t alerts_raised;
    uint64_t recoveries_attempted;
    time_t last_check;
} watchdog_state_t;

/* ===== Cognitive State ===== */
typedef struct cognitive_state {
    module_state_t state;
    uint64_t scans_performed;
    uint64_t detections;
    float detection_rate;
} cognitive_state_t;

/* ===== PQC State ===== */
typedef struct pqc_state {
    module_state_t state;
    bool kyber_available;
    bool dilithium_available;
    uint64_t keys_generated;
    uint64_t signatures_created;
} pqc_state_t;

/* ===== Guard States ===== */
typedef struct guard_state {
    module_state_t state;
    float threshold;
    rule_action_t default_action;
    uint64_t checks_performed;
    uint64_t threats_blocked;
} guard_state_t;

typedef struct guards_state {
    guard_state_t llm;
    guard_state_t rag;
    guard_state_t agent;
    guard_state_t tool;
    guard_state_t mcp;
    guard_state_t api;
} guards_state_t;

/* ===== Rate Limiting State ===== */
typedef struct rate_limit_state {
    bool enabled;
    uint32_t requests_per_window;
    uint32_t window_seconds;
    uint64_t requests_allowed;
    uint64_t requests_blocked;
} rate_limit_state_t;

/* ===== Blocklist State ===== */
typedef struct blocklist_state {
    bool enabled;
    uint32_t ip_count;
    uint32_t pattern_count;
    uint64_t blocks_total;
} blocklist_state_t;

/* ===== SIEM State ===== */
typedef struct siem_state {
    bool enabled;
    char host[128];
    uint16_t port;
    char format[16];  /* cef, json, syslog */
    uint64_t events_sent;
    uint64_t events_failed;
} siem_state_t;

/* ===== Alerting State ===== */
typedef struct alert_state {
    bool enabled;
    char destination[256];
    char threshold[16];  /* info, warn, critical */
    uint64_t alerts_sent;
} alert_state_t;

/* ===== Brain Connection State ===== */
typedef struct brain_state {
    bool connected;
    char host[128];
    uint16_t port;
    bool tls_enabled;
    uint64_t requests_sent;
    uint64_t requests_failed;
    time_t last_request;
} brain_state_t;

/* ===== System Config ===== */
typedef struct system_config {
    char hostname[64];
    char domain[128];
    char ntp_server[64];
    char dns_server[64];
    char timezone[32];
    log_level_t log_level;
    char syslog_host[64];
    uint32_t log_buffer_size;
    bool password_encryption;
} system_config_t;

/* ===== Debug State ===== */
typedef struct debug_state {
    bool shield;
    bool zone;
    bool rule;
    bool guard;
    bool protocol;
    bool ha;
    bool all;
} debug_state_t;

/* ===== HA Config ===== */
typedef struct ha_config {
    bool enabled;
    char virtual_ip[64];
    uint8_t priority;
    bool preempt;
    uint8_t hello_interval;
    uint8_t hold_time;
    char cluster_name[64];
    bool is_active;
} ha_config_t;

/* ===== API State ===== */
typedef struct api_state {
    bool enabled;
    uint16_t port;
    char token[128];
    bool metrics_enabled;
    uint16_t metrics_port;
    uint64_t requests_handled;
} api_state_t;

/* ===== Global Shield State ===== */
typedef struct shield_state {
    /* Version info */
    char version[32];
    time_t start_time;
    
    /* Modules */
    threat_hunter_state_t threat_hunter;
    watchdog_state_t watchdog;
    cognitive_state_t cognitive;
    pqc_state_t pqc;
    
    /* Guards */
    guards_state_t guards;
    
    /* Security */
    rate_limit_state_t rate_limit;
    blocklist_state_t blocklist;
    siem_state_t siem;
    alert_state_t alerting;
    
    /* Integration */
    brain_state_t brain;
    
    /* System */
    system_config_t config;
    debug_state_t debug;
    ha_config_t ha;
    api_state_t api;
    
    /* Statistics */
    uint64_t total_requests;
    uint64_t total_blocked;
    uint64_t total_allowed;
    
    /* Dirty flag for persistence */
    bool config_modified;
} shield_state_t;

/* ===== Global State Access ===== */

/* Get global state (singleton) */
shield_state_t *shield_state_get(void);

/* Initialize state with defaults */
shield_err_t shield_state_init(void);

/* Reset to defaults */
void shield_state_reset(void);

/* Save state to file */
shield_err_t shield_state_save(const char *path);

/* Load state from file */
shield_err_t shield_state_load(const char *path);

/* Mark config as modified */
void shield_state_mark_dirty(void);

/* Check if config needs saving */
bool shield_state_is_dirty(void);

/* Format state summary for display */
void shield_state_format_summary(char *buffer, size_t buflen);

/* Statistics helpers */
void shield_state_inc_requests(void);
void shield_state_inc_blocked(void);
void shield_state_inc_allowed(void);

#endif /* SHIELD_STATE_H */
