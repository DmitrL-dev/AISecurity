/*
 * SENTINEL Shield - Global State Manager Implementation
 * 
 * Centralized state management with persistence support.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#include "shield_common.h"
#include "shield_state.h"

/* ===== Global State Singleton ===== */

static shield_state_t g_state;
static bool g_initialized = false;

/* ===== State Access ===== */

shield_state_t *shield_state_get(void)
{
    if (!g_initialized) {
        shield_state_init();
    }
    return &g_state;
}

/* ===== Initialization ===== */

shield_err_t shield_state_init(void)
{
    if (g_initialized) {
        return SHIELD_OK;
    }
    
    memset(&g_state, 0, sizeof(g_state));
    
    /* Version */
    strncpy(g_state.version, "1.2.0", sizeof(g_state.version) - 1);
    g_state.start_time = time(NULL);
    
    /* ThreatHunter defaults */
    g_state.threat_hunter.state = MODULE_DISABLED;
    g_state.threat_hunter.sensitivity = 0.7f;
    g_state.threat_hunter.hunt_ioc = true;
    g_state.threat_hunter.hunt_behavioral = true;
    g_state.threat_hunter.hunt_anomaly = true;
    
    /* Watchdog defaults */
    g_state.watchdog.state = MODULE_DISABLED;
    g_state.watchdog.auto_recovery = true;
    g_state.watchdog.check_interval_ms = 5000;
    g_state.watchdog.system_health = 1.0f;
    
    /* Cognitive defaults */
    g_state.cognitive.state = MODULE_DISABLED;
    
    /* PQC defaults */
    g_state.pqc.state = MODULE_DISABLED;
    g_state.pqc.kyber_available = true;
    g_state.pqc.dilithium_available = true;
    
    /* Guards defaults - all enabled with default thresholds */
    g_state.guards.llm.state = MODULE_ENABLED;
    g_state.guards.llm.threshold = 0.7f;
    g_state.guards.llm.default_action = ACTION_BLOCK;
    
    g_state.guards.rag.state = MODULE_ENABLED;
    g_state.guards.rag.threshold = 0.7f;
    g_state.guards.rag.default_action = ACTION_BLOCK;
    
    g_state.guards.agent.state = MODULE_ENABLED;
    g_state.guards.agent.threshold = 0.7f;
    g_state.guards.agent.default_action = ACTION_BLOCK;
    
    g_state.guards.tool.state = MODULE_ENABLED;
    g_state.guards.tool.threshold = 0.7f;
    g_state.guards.tool.default_action = ACTION_BLOCK;
    
    g_state.guards.mcp.state = MODULE_ENABLED;
    g_state.guards.mcp.threshold = 0.7f;
    g_state.guards.mcp.default_action = ACTION_BLOCK;
    
    g_state.guards.api.state = MODULE_ENABLED;
    g_state.guards.api.threshold = 0.7f;
    g_state.guards.api.default_action = ACTION_BLOCK;
    
    /* Rate limiting defaults */
    g_state.rate_limit.enabled = false;
    g_state.rate_limit.requests_per_window = 100;
    g_state.rate_limit.window_seconds = 60;
    
    /* Blocklist defaults */
    g_state.blocklist.enabled = true;
    
    /* SIEM defaults */
    g_state.siem.enabled = false;
    g_state.siem.port = 514;
    strncpy(g_state.siem.format, "syslog", sizeof(g_state.siem.format) - 1);
    
    /* Alerting defaults */
    g_state.alerting.enabled = false;
    strncpy(g_state.alerting.threshold, "warn", sizeof(g_state.alerting.threshold) - 1);
    
    /* Brain defaults */
    g_state.brain.connected = false;
    g_state.brain.port = 8000;
    g_state.brain.tls_enabled = false;
    
    /* System config defaults */
    strncpy(g_state.config.hostname, "Shield", sizeof(g_state.config.hostname) - 1);
    g_state.config.log_level = LOG_INFO;
    g_state.config.log_buffer_size = 8192;
    
    /* Debug defaults - all off */
    memset(&g_state.debug, 0, sizeof(g_state.debug));
    
    /* HA defaults */
    g_state.ha.enabled = false;
    g_state.ha.priority = 100;
    g_state.ha.hello_interval = 3;
    g_state.ha.hold_time = 10;
    
    /* API defaults */
    g_state.api.enabled = false;
    g_state.api.port = 8080;
    g_state.api.metrics_enabled = false;
    g_state.api.metrics_port = 9090;
    
    g_state.config_modified = false;
    g_initialized = true;
    
    LOG_INFO("Shield State: Initialized with defaults");
    return SHIELD_OK;
}

/* ===== Reset ===== */

void shield_state_reset(void)
{
    g_initialized = false;
    shield_state_init();
    LOG_INFO("Shield State: Reset to defaults");
}

/* ===== Dirty Flag ===== */

void shield_state_mark_dirty(void)
{
    g_state.config_modified = true;
}

bool shield_state_is_dirty(void)
{
    return g_state.config_modified;
}

/* ===== Persistence ===== */

shield_err_t shield_state_save(const char *path)
{
    if (!path) {
        path = "shield.conf";
    }
    
    FILE *f = fopen(path, "w");
    if (!f) {
        LOG_ERROR("Shield State: Failed to open %s for writing", path);
        return SHIELD_ERR_IO;
    }
    
    /* Write config in simple key=value format */
    fprintf(f, "# SENTINEL Shield Configuration\n");
    fprintf(f, "# Generated: %s\n", ctime(&g_state.start_time));
    fprintf(f, "\n");
    
    /* System */
    fprintf(f, "[system]\n");
    fprintf(f, "hostname=%s\n", g_state.config.hostname);
    fprintf(f, "domain=%s\n", g_state.config.domain);
    fprintf(f, "log_level=%d\n", g_state.config.log_level);
    fprintf(f, "log_buffer=%u\n", g_state.config.log_buffer_size);
    fprintf(f, "\n");
    
    /* ThreatHunter */
    fprintf(f, "[threat_hunter]\n");
    fprintf(f, "enabled=%d\n", g_state.threat_hunter.state == MODULE_ENABLED ? 1 : 0);
    fprintf(f, "sensitivity=%.2f\n", g_state.threat_hunter.sensitivity);
    fprintf(f, "hunt_ioc=%d\n", g_state.threat_hunter.hunt_ioc ? 1 : 0);
    fprintf(f, "hunt_behavioral=%d\n", g_state.threat_hunter.hunt_behavioral ? 1 : 0);
    fprintf(f, "hunt_anomaly=%d\n", g_state.threat_hunter.hunt_anomaly ? 1 : 0);
    fprintf(f, "\n");
    
    /* Watchdog */
    fprintf(f, "[watchdog]\n");
    fprintf(f, "enabled=%d\n", g_state.watchdog.state == MODULE_ENABLED ? 1 : 0);
    fprintf(f, "auto_recovery=%d\n", g_state.watchdog.auto_recovery ? 1 : 0);
    fprintf(f, "check_interval=%u\n", g_state.watchdog.check_interval_ms);
    fprintf(f, "\n");
    
    /* Guards */
    fprintf(f, "[guards]\n");
    fprintf(f, "llm_enabled=%d\n", g_state.guards.llm.state == MODULE_ENABLED ? 1 : 0);
    fprintf(f, "llm_threshold=%.2f\n", g_state.guards.llm.threshold);
    fprintf(f, "rag_enabled=%d\n", g_state.guards.rag.state == MODULE_ENABLED ? 1 : 0);
    fprintf(f, "rag_threshold=%.2f\n", g_state.guards.rag.threshold);
    fprintf(f, "agent_enabled=%d\n", g_state.guards.agent.state == MODULE_ENABLED ? 1 : 0);
    fprintf(f, "agent_threshold=%.2f\n", g_state.guards.agent.threshold);
    fprintf(f, "tool_enabled=%d\n", g_state.guards.tool.state == MODULE_ENABLED ? 1 : 0);
    fprintf(f, "tool_threshold=%.2f\n", g_state.guards.tool.threshold);
    fprintf(f, "mcp_enabled=%d\n", g_state.guards.mcp.state == MODULE_ENABLED ? 1 : 0);
    fprintf(f, "mcp_threshold=%.2f\n", g_state.guards.mcp.threshold);
    fprintf(f, "api_enabled=%d\n", g_state.guards.api.state == MODULE_ENABLED ? 1 : 0);
    fprintf(f, "api_threshold=%.2f\n", g_state.guards.api.threshold);
    fprintf(f, "\n");
    
    /* Rate limiting */
    fprintf(f, "[rate_limit]\n");
    fprintf(f, "enabled=%d\n", g_state.rate_limit.enabled ? 1 : 0);
    fprintf(f, "requests=%u\n", g_state.rate_limit.requests_per_window);
    fprintf(f, "window=%u\n", g_state.rate_limit.window_seconds);
    fprintf(f, "\n");
    
    /* SIEM */
    fprintf(f, "[siem]\n");
    fprintf(f, "enabled=%d\n", g_state.siem.enabled ? 1 : 0);
    fprintf(f, "host=%s\n", g_state.siem.host);
    fprintf(f, "port=%u\n", g_state.siem.port);
    fprintf(f, "format=%s\n", g_state.siem.format);
    fprintf(f, "\n");
    
    /* API */
    fprintf(f, "[api]\n");
    fprintf(f, "enabled=%d\n", g_state.api.enabled ? 1 : 0);
    fprintf(f, "port=%u\n", g_state.api.port);
    fprintf(f, "metrics_enabled=%d\n", g_state.api.metrics_enabled ? 1 : 0);
    fprintf(f, "metrics_port=%u\n", g_state.api.metrics_port);
    fprintf(f, "\n");
    
    /* HA */
    fprintf(f, "[ha]\n");
    fprintf(f, "enabled=%d\n", g_state.ha.enabled ? 1 : 0);
    fprintf(f, "virtual_ip=%s\n", g_state.ha.virtual_ip);
    fprintf(f, "priority=%u\n", g_state.ha.priority);
    fprintf(f, "preempt=%d\n", g_state.ha.preempt ? 1 : 0);
    fprintf(f, "cluster_name=%s\n", g_state.ha.cluster_name);
    fprintf(f, "\n");
    
    fclose(f);
    g_state.config_modified = false;
    
    LOG_INFO("Shield State: Saved to %s", path);
    return SHIELD_OK;
}

static int parse_int(const char *val) { return atoi(val); }
static float parse_float(const char *val) { return (float)atof(val); }

shield_err_t shield_state_load(const char *path)
{
    if (!path) {
        path = "shield.conf";
    }
    
    FILE *f = fopen(path, "r");
    if (!f) {
        LOG_WARN("Shield State: Config file %s not found, using defaults", path);
        return SHIELD_ERR_NOTFOUND;
    }
    
    char line[512];
    char section[64] = "";
    
    while (fgets(line, sizeof(line), f)) {
        /* Skip comments and empty lines */
        if (line[0] == '#' || line[0] == '\n' || line[0] == '\r') {
            continue;
        }
        
        /* Section header */
        if (line[0] == '[') {
            char *end = strchr(line, ']');
            if (end) {
                *end = '\0';
                strncpy(section, line + 1, sizeof(section) - 1);
            }
            continue;
        }
        
        /* Key=value */
        char *eq = strchr(line, '=');
        if (!eq) continue;
        
        *eq = '\0';
        char *key = line;
        char *val = eq + 1;
        
        /* Remove trailing newline */
        char *nl = strchr(val, '\n');
        if (nl) *nl = '\0';
        nl = strchr(val, '\r');
        if (nl) *nl = '\0';
        
        /* Parse by section */
        if (strcmp(section, "system") == 0) {
            if (strcmp(key, "hostname") == 0) {
                strncpy(g_state.config.hostname, val, sizeof(g_state.config.hostname) - 1);
            } else if (strcmp(key, "domain") == 0) {
                strncpy(g_state.config.domain, val, sizeof(g_state.config.domain) - 1);
            } else if (strcmp(key, "log_level") == 0) {
                g_state.config.log_level = parse_int(val);
            } else if (strcmp(key, "log_buffer") == 0) {
                g_state.config.log_buffer_size = parse_int(val);
            }
        } else if (strcmp(section, "threat_hunter") == 0) {
            if (strcmp(key, "enabled") == 0) {
                g_state.threat_hunter.state = parse_int(val) ? MODULE_ENABLED : MODULE_DISABLED;
            } else if (strcmp(key, "sensitivity") == 0) {
                g_state.threat_hunter.sensitivity = parse_float(val);
            } else if (strcmp(key, "hunt_ioc") == 0) {
                g_state.threat_hunter.hunt_ioc = parse_int(val) != 0;
            } else if (strcmp(key, "hunt_behavioral") == 0) {
                g_state.threat_hunter.hunt_behavioral = parse_int(val) != 0;
            } else if (strcmp(key, "hunt_anomaly") == 0) {
                g_state.threat_hunter.hunt_anomaly = parse_int(val) != 0;
            }
        } else if (strcmp(section, "watchdog") == 0) {
            if (strcmp(key, "enabled") == 0) {
                g_state.watchdog.state = parse_int(val) ? MODULE_ENABLED : MODULE_DISABLED;
            } else if (strcmp(key, "auto_recovery") == 0) {
                g_state.watchdog.auto_recovery = parse_int(val) != 0;
            } else if (strcmp(key, "check_interval") == 0) {
                g_state.watchdog.check_interval_ms = parse_int(val);
            }
        } else if (strcmp(section, "guards") == 0) {
            if (strcmp(key, "llm_enabled") == 0) {
                g_state.guards.llm.state = parse_int(val) ? MODULE_ENABLED : MODULE_DISABLED;
            } else if (strcmp(key, "llm_threshold") == 0) {
                g_state.guards.llm.threshold = parse_float(val);
            } else if (strcmp(key, "rag_enabled") == 0) {
                g_state.guards.rag.state = parse_int(val) ? MODULE_ENABLED : MODULE_DISABLED;
            } else if (strcmp(key, "rag_threshold") == 0) {
                g_state.guards.rag.threshold = parse_float(val);
            }
            /* ... other guards similarly */
        } else if (strcmp(section, "rate_limit") == 0) {
            if (strcmp(key, "enabled") == 0) {
                g_state.rate_limit.enabled = parse_int(val) != 0;
            } else if (strcmp(key, "requests") == 0) {
                g_state.rate_limit.requests_per_window = parse_int(val);
            } else if (strcmp(key, "window") == 0) {
                g_state.rate_limit.window_seconds = parse_int(val);
            }
        } else if (strcmp(section, "siem") == 0) {
            if (strcmp(key, "enabled") == 0) {
                g_state.siem.enabled = parse_int(val) != 0;
            } else if (strcmp(key, "host") == 0) {
                strncpy(g_state.siem.host, val, sizeof(g_state.siem.host) - 1);
            } else if (strcmp(key, "port") == 0) {
                g_state.siem.port = parse_int(val);
            } else if (strcmp(key, "format") == 0) {
                strncpy(g_state.siem.format, val, sizeof(g_state.siem.format) - 1);
            }
        } else if (strcmp(section, "api") == 0) {
            if (strcmp(key, "enabled") == 0) {
                g_state.api.enabled = parse_int(val) != 0;
            } else if (strcmp(key, "port") == 0) {
                g_state.api.port = parse_int(val);
            } else if (strcmp(key, "metrics_enabled") == 0) {
                g_state.api.metrics_enabled = parse_int(val) != 0;
            } else if (strcmp(key, "metrics_port") == 0) {
                g_state.api.metrics_port = parse_int(val);
            }
        } else if (strcmp(section, "ha") == 0) {
            if (strcmp(key, "enabled") == 0) {
                g_state.ha.enabled = parse_int(val) != 0;
            } else if (strcmp(key, "virtual_ip") == 0) {
                strncpy(g_state.ha.virtual_ip, val, sizeof(g_state.ha.virtual_ip) - 1);
            } else if (strcmp(key, "priority") == 0) {
                g_state.ha.priority = parse_int(val);
            } else if (strcmp(key, "preempt") == 0) {
                g_state.ha.preempt = parse_int(val) != 0;
            } else if (strcmp(key, "cluster_name") == 0) {
                strncpy(g_state.ha.cluster_name, val, sizeof(g_state.ha.cluster_name) - 1);
            }
        }
    }
    
    fclose(f);
    g_state.config_modified = false;
    g_initialized = true;
    
    LOG_INFO("Shield State: Loaded from %s", path);
    return SHIELD_OK;
}

/* ===== Statistics Helpers ===== */

void shield_state_inc_requests(void)
{
    g_state.total_requests++;
}

void shield_state_inc_blocked(void)
{
    g_state.total_blocked++;
}

void shield_state_inc_allowed(void)
{
    g_state.total_allowed++;
}

/* ===== Format State for Display ===== */

void shield_state_format_summary(char *buffer, size_t buflen)
{
    if (!buffer || buflen == 0) return;
    
    time_t uptime = time(NULL) - g_state.start_time;
    int days = uptime / 86400;
    int hours = (uptime % 86400) / 3600;
    int mins = (uptime % 3600) / 60;
    
    snprintf(buffer, buflen,
        "SENTINEL Shield v%s\n"
        "===================\n"
        "Uptime: %d days, %d hours, %d minutes\n"
        "\n"
        "Guards:\n"
        "  LLM:   %s (threshold: %.2f)\n"
        "  RAG:   %s (threshold: %.2f)\n"
        "  Agent: %s (threshold: %.2f)\n"
        "  Tool:  %s (threshold: %.2f)\n"
        "  MCP:   %s (threshold: %.2f)\n"
        "  API:   %s (threshold: %.2f)\n"
        "\n"
        "Modules:\n"
        "  ThreatHunter: %s\n"
        "  Watchdog:     %s (health: %.0f%%)\n"
        "  Cognitive:    %s\n"
        "  PQC:          %s\n"
        "\n"
        "Statistics:\n"
        "  Total Requests:  %llu\n"
        "  Blocked:         %llu\n"
        "  Allowed:         %llu\n",
        g_state.version,
        days, hours, mins,
        g_state.guards.llm.state == MODULE_ENABLED ? "ENABLED" : "disabled",
        g_state.guards.llm.threshold,
        g_state.guards.rag.state == MODULE_ENABLED ? "ENABLED" : "disabled",
        g_state.guards.rag.threshold,
        g_state.guards.agent.state == MODULE_ENABLED ? "ENABLED" : "disabled",
        g_state.guards.agent.threshold,
        g_state.guards.tool.state == MODULE_ENABLED ? "ENABLED" : "disabled",
        g_state.guards.tool.threshold,
        g_state.guards.mcp.state == MODULE_ENABLED ? "ENABLED" : "disabled",
        g_state.guards.mcp.threshold,
        g_state.guards.api.state == MODULE_ENABLED ? "ENABLED" : "disabled",
        g_state.guards.api.threshold,
        g_state.threat_hunter.state == MODULE_ENABLED ? "ENABLED" : "disabled",
        g_state.watchdog.state == MODULE_ENABLED ? "ENABLED" : "disabled",
        g_state.watchdog.system_health * 100,
        g_state.cognitive.state == MODULE_ENABLED ? "ENABLED" : "disabled",
        g_state.pqc.state == MODULE_ENABLED ? "ENABLED" : "disabled",
        (unsigned long long)g_state.total_requests,
        (unsigned long long)g_state.total_blocked,
        (unsigned long long)g_state.total_allowed);
}
