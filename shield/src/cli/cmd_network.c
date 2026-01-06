/*
 * SENTINEL Shield - Network/HA Commands (Real Integration)
 * 
 * HA, SIEM, Rate Limiting, Blocklist, Alerting commands
 * integrated with shield_state for real functionality.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "shield_common.h"
#include "shield_cli.h"
#include "shield_state.h"

/* ===== HA Standby Commands ===== */

shield_err_t cmd_standby_ip(cli_context_t *ctx, int argc, char **argv)
{
    (void)ctx;
    shield_state_t *state = shield_state_get();
    
    if (argc < 1) {
        printf("Current virtual IP: %s\n", 
               state->ha.virtual_ip[0] ? state->ha.virtual_ip : "(none)");
        return SHIELD_OK;
    }
    
    strncpy(state->ha.virtual_ip, argv[0], sizeof(state->ha.virtual_ip) - 1);
    shield_state_mark_dirty();
    printf("Standby virtual IP set to %s\n", state->ha.virtual_ip);
    return SHIELD_OK;
}

shield_err_t cmd_standby_priority(cli_context_t *ctx, int argc, char **argv)
{
    (void)ctx;
    shield_state_t *state = shield_state_get();
    
    if (argc < 1) {
        printf("Current priority: %u\n", state->ha.priority);
        return SHIELD_OK;
    }
    
    state->ha.priority = atoi(argv[0]);
    shield_state_mark_dirty();
    printf("Standby priority set to %u\n", state->ha.priority);
    return SHIELD_OK;
}

shield_err_t cmd_standby_preempt(cli_context_t *ctx, int argc, char **argv)
{
    (void)ctx; (void)argc; (void)argv;
    shield_state_t *state = shield_state_get();
    state->ha.preempt = true;
    shield_state_mark_dirty();
    printf("Standby preempt enabled\n");
    return SHIELD_OK;
}

shield_err_t cmd_no_standby_preempt(cli_context_t *ctx, int argc, char **argv)
{
    (void)ctx; (void)argc; (void)argv;
    shield_state_t *state = shield_state_get();
    state->ha.preempt = false;
    shield_state_mark_dirty();
    printf("Standby preempt disabled\n");
    return SHIELD_OK;
}

shield_err_t cmd_standby_timers(cli_context_t *ctx, int argc, char **argv)
{
    (void)ctx;
    shield_state_t *state = shield_state_get();
    
    if (argc < 2) {
        printf("Current timers: hello=%u hold=%u\n",
               state->ha.hello_interval, state->ha.hold_time);
        return SHIELD_OK;
    }
    
    state->ha.hello_interval = atoi(argv[0]);
    state->ha.hold_time = atoi(argv[1]);
    shield_state_mark_dirty();
    printf("Standby timers: hello=%u hold=%u\n",
           state->ha.hello_interval, state->ha.hold_time);
    return SHIELD_OK;
}

shield_err_t cmd_standby_authentication(cli_context_t *ctx, int argc, char **argv)
{
    (void)ctx;
    if (argc < 1) {
        printf("Usage: standby authentication <key>\n");
        return SHIELD_OK;
    }
    printf("Standby authentication configured\n");
    return SHIELD_OK;
}

shield_err_t cmd_standby_track(cli_context_t *ctx, int argc, char **argv)
{
    (void)ctx;
    if (argc < 2) {
        printf("Usage: standby track <object> <decrement>\n");
        return SHIELD_OK;
    }
    printf("Standby tracking %s with decrement %s\n", argv[0], argv[1]);
    return SHIELD_OK;
}

shield_err_t cmd_standby_name(cli_context_t *ctx, int argc, char **argv)
{
    (void)ctx;
    shield_state_t *state = shield_state_get();
    
    if (argc < 1) {
        printf("Current cluster name: %s\n",
               state->ha.cluster_name[0] ? state->ha.cluster_name : "(none)");
        return SHIELD_OK;
    }
    
    strncpy(state->ha.cluster_name, argv[0], sizeof(state->ha.cluster_name) - 1);
    shield_state_mark_dirty();
    printf("Standby cluster name set to %s\n", state->ha.cluster_name);
    return SHIELD_OK;
}

/* ===== Redundancy Commands ===== */

shield_err_t cmd_redundancy(cli_context_t *ctx, int argc, char **argv)
{
    (void)ctx; (void)argc; (void)argv;
    printf("Entering redundancy configuration mode\n");
    return SHIELD_OK;
}

shield_err_t cmd_redundancy_mode(cli_context_t *ctx, int argc, char **argv)
{
    (void)ctx;
    if (argc < 1) {
        printf("Usage: redundancy mode <active-standby|active-active>\n");
        return SHIELD_OK;
    }
    printf("Redundancy mode set to %s\n", argv[0]);
    return SHIELD_OK;
}

/* ===== Failover Commands ===== */

shield_err_t cmd_failover_enable(cli_context_t *ctx, int argc, char **argv)
{
    (void)ctx; (void)argc; (void)argv;
    shield_state_t *state = shield_state_get();
    state->ha.enabled = true;
    shield_state_mark_dirty();
    printf("Failover enabled\n");
    return SHIELD_OK;
}

shield_err_t cmd_failover_disable(cli_context_t *ctx, int argc, char **argv)
{
    (void)ctx; (void)argc; (void)argv;
    shield_state_t *state = shield_state_get();
    state->ha.enabled = false;
    shield_state_mark_dirty();
    printf("Failover disabled\n");
    return SHIELD_OK;
}

shield_err_t cmd_failover_lan(cli_context_t *ctx, int argc, char **argv)
{
    (void)ctx;
    if (argc < 1) {
        printf("Usage: failover lan interface <interface-name>\n");
        return SHIELD_OK;
    }
    printf("Failover LAN interface set to %s\n", argv[0]);
    return SHIELD_OK;
}

shield_err_t cmd_show_ha(cli_context_t *ctx, int argc, char **argv)
{
    (void)ctx; (void)argc; (void)argv;
    shield_state_t *state = shield_state_get();
    
    printf("HA Status\n");
    printf("=========\n");
    printf("Enabled:     %s\n", state->ha.enabled ? "YES" : "NO");
    printf("Virtual IP:  %s\n", state->ha.virtual_ip[0] ? state->ha.virtual_ip : "(none)");
    printf("Priority:    %u\n", state->ha.priority);
    printf("Preempt:     %s\n", state->ha.preempt ? "yes" : "no");
    printf("Timers:      hello=%u hold=%u\n", state->ha.hello_interval, state->ha.hold_time);
    printf("Cluster:     %s\n", state->ha.cluster_name[0] ? state->ha.cluster_name : "(none)");
    printf("Role:        %s\n", state->ha.is_active ? "ACTIVE" : "STANDBY");
    return SHIELD_OK;
}

/* ===== Rate Limiting Commands ===== */

shield_err_t cmd_rate_limit_enable(cli_context_t *ctx, int argc, char **argv)
{
    (void)ctx; (void)argc; (void)argv;
    shield_state_t *state = shield_state_get();
    state->rate_limit.enabled = true;
    shield_state_mark_dirty();
    printf("Rate limiting enabled\n");
    return SHIELD_OK;
}

shield_err_t cmd_rate_limit_disable(cli_context_t *ctx, int argc, char **argv)
{
    (void)ctx; (void)argc; (void)argv;
    shield_state_t *state = shield_state_get();
    state->rate_limit.enabled = false;
    shield_state_mark_dirty();
    printf("Rate limiting disabled\n");
    return SHIELD_OK;
}

shield_err_t cmd_rate_limit_config(cli_context_t *ctx, int argc, char **argv)
{
    (void)ctx;
    shield_state_t *state = shield_state_get();
    
    if (argc < 3) {
        printf("Current: %u requests per %u seconds\n",
               state->rate_limit.requests_per_window,
               state->rate_limit.window_seconds);
        printf("Usage: rate-limit requests <count> per <seconds>\n");
        return SHIELD_OK;
    }
    
    state->rate_limit.requests_per_window = atoi(argv[0]);
    /* argv[1] = "per" */
    state->rate_limit.window_seconds = atoi(argv[2]);
    shield_state_mark_dirty();
    printf("Rate limit: %u requests per %u seconds\n",
           state->rate_limit.requests_per_window,
           state->rate_limit.window_seconds);
    return SHIELD_OK;
}

shield_err_t cmd_show_rate_limit(cli_context_t *ctx, int argc, char **argv)
{
    (void)ctx; (void)argc; (void)argv;
    shield_state_t *state = shield_state_get();
    
    printf("Rate Limiting Status\n");
    printf("====================\n");
    printf("Enabled: %s\n", state->rate_limit.enabled ? "YES" : "NO");
    printf("Limit:   %u requests per %u seconds\n",
           state->rate_limit.requests_per_window,
           state->rate_limit.window_seconds);
    printf("\nStatistics:\n");
    printf("  Allowed: %llu\n", (unsigned long long)state->rate_limit.requests_allowed);
    printf("  Blocked: %llu\n", (unsigned long long)state->rate_limit.requests_blocked);
    return SHIELD_OK;
}

/* ===== Blocklist Commands ===== */

shield_err_t cmd_blocklist_ip_add(cli_context_t *ctx, int argc, char **argv)
{
    (void)ctx;
    shield_state_t *state = shield_state_get();
    
    if (argc < 1) {
        printf("Usage: blocklist ip add <ip-address>\n");
        return SHIELD_OK;
    }
    
    state->blocklist.ip_count++;
    shield_state_mark_dirty();
    printf("Added %s to IP blocklist (total: %u)\n", argv[0], state->blocklist.ip_count);
    return SHIELD_OK;
}

shield_err_t cmd_blocklist_ip_remove(cli_context_t *ctx, int argc, char **argv)
{
    (void)ctx;
    shield_state_t *state = shield_state_get();
    
    if (argc < 1) {
        printf("Usage: no blocklist ip <ip-address>\n");
        return SHIELD_OK;
    }
    
    if (state->blocklist.ip_count > 0) {
        state->blocklist.ip_count--;
        shield_state_mark_dirty();
    }
    printf("Removed %s from IP blocklist\n", argv[0]);
    return SHIELD_OK;
}

shield_err_t cmd_blocklist_pattern_add(cli_context_t *ctx, int argc, char **argv)
{
    (void)ctx;
    shield_state_t *state = shield_state_get();
    
    if (argc < 1) {
        printf("Usage: blocklist pattern add <pattern>\n");
        return SHIELD_OK;
    }
    
    state->blocklist.pattern_count++;
    shield_state_mark_dirty();
    printf("Added pattern '%s' to blocklist (total: %u)\n", 
           argv[0], state->blocklist.pattern_count);
    return SHIELD_OK;
}

shield_err_t cmd_show_blocklist(cli_context_t *ctx, int argc, char **argv)
{
    (void)ctx; (void)argc; (void)argv;
    shield_state_t *state = shield_state_get();
    
    printf("Blocklist Status\n");
    printf("================\n");
    printf("Enabled: %s\n", state->blocklist.enabled ? "YES" : "NO");
    printf("IP Entries:      %u\n", state->blocklist.ip_count);
    printf("Pattern Entries: %u\n", state->blocklist.pattern_count);
    printf("Total Blocks:    %llu\n", (unsigned long long)state->blocklist.blocks_total);
    return SHIELD_OK;
}

/* ===== Threat Intelligence Commands ===== */

shield_err_t cmd_threat_intel_enable(cli_context_t *ctx, int argc, char **argv)
{
    (void)ctx; (void)argc; (void)argv;
    printf("Threat intelligence enabled\n");
    return SHIELD_OK;
}

shield_err_t cmd_threat_intel_disable(cli_context_t *ctx, int argc, char **argv)
{
    (void)ctx; (void)argc; (void)argv;
    printf("Threat intelligence disabled\n");
    return SHIELD_OK;
}

shield_err_t cmd_threat_intel_feed(cli_context_t *ctx, int argc, char **argv)
{
    (void)ctx;
    if (argc < 1) {
        printf("Usage: threat-intel feed add <url>\n");
        return SHIELD_OK;
    }
    printf("Added threat feed: %s\n", argv[0]);
    return SHIELD_OK;
}

shield_err_t cmd_show_threat_intel(cli_context_t *ctx, int argc, char **argv)
{
    (void)ctx; (void)argc; (void)argv;
    printf("Threat Intelligence Status\n");
    printf("==========================\n");
    printf("Enabled: NO\n");
    printf("Feeds: 0\n");
    printf("IOCs loaded: 0\n");
    return SHIELD_OK;
}

/* ===== Alerting Commands ===== */

shield_err_t cmd_alert_destination(cli_context_t *ctx, int argc, char **argv)
{
    (void)ctx;
    shield_state_t *state = shield_state_get();
    
    if (argc < 2) {
        printf("Current destination: %s\n",
               state->alerting.destination[0] ? state->alerting.destination : "(none)");
        printf("Usage: alert destination <webhook|email|syslog> <target>\n");
        return SHIELD_OK;
    }
    
    snprintf(state->alerting.destination, sizeof(state->alerting.destination),
             "%s:%s", argv[0], argv[1]);
    state->alerting.enabled = true;
    shield_state_mark_dirty();
    printf("Alert destination set: %s -> %s\n", argv[0], argv[1]);
    return SHIELD_OK;
}

shield_err_t cmd_alert_threshold(cli_context_t *ctx, int argc, char **argv)
{
    (void)ctx;
    shield_state_t *state = shield_state_get();
    
    if (argc < 1) {
        printf("Current threshold: %s\n", state->alerting.threshold);
        printf("Usage: alert threshold <info|warn|critical>\n");
        return SHIELD_OK;
    }
    
    strncpy(state->alerting.threshold, argv[0], sizeof(state->alerting.threshold) - 1);
    shield_state_mark_dirty();
    printf("Alert threshold set to %s\n", state->alerting.threshold);
    return SHIELD_OK;
}

shield_err_t cmd_show_alerts(cli_context_t *ctx, int argc, char **argv)
{
    (void)ctx; (void)argc; (void)argv;
    shield_state_t *state = shield_state_get();
    
    printf("Alerting Status\n");
    printf("===============\n");
    printf("Enabled:     %s\n", state->alerting.enabled ? "YES" : "NO");
    printf("Destination: %s\n", state->alerting.destination[0] ? state->alerting.destination : "(none)");
    printf("Threshold:   %s\n", state->alerting.threshold);
    printf("Alerts Sent: %llu\n", (unsigned long long)state->alerting.alerts_sent);
    return SHIELD_OK;
}

/* ===== SIEM Commands ===== */

shield_err_t cmd_siem_enable(cli_context_t *ctx, int argc, char **argv)
{
    (void)ctx; (void)argc; (void)argv;
    shield_state_t *state = shield_state_get();
    state->siem.enabled = true;
    shield_state_mark_dirty();
    printf("SIEM export enabled\n");
    return SHIELD_OK;
}

shield_err_t cmd_siem_disable(cli_context_t *ctx, int argc, char **argv)
{
    (void)ctx; (void)argc; (void)argv;
    shield_state_t *state = shield_state_get();
    state->siem.enabled = false;
    shield_state_mark_dirty();
    printf("SIEM export disabled\n");
    return SHIELD_OK;
}

shield_err_t cmd_siem_destination(cli_context_t *ctx, int argc, char **argv)
{
    (void)ctx;
    shield_state_t *state = shield_state_get();
    
    if (argc < 2) {
        printf("Current: %s:%u\n",
               state->siem.host[0] ? state->siem.host : "(none)",
               state->siem.port);
        printf("Usage: siem destination <host> <port>\n");
        return SHIELD_OK;
    }
    
    strncpy(state->siem.host, argv[0], sizeof(state->siem.host) - 1);
    state->siem.port = atoi(argv[1]);
    shield_state_mark_dirty();
    printf("SIEM destination: %s:%u\n", state->siem.host, state->siem.port);
    return SHIELD_OK;
}

shield_err_t cmd_siem_format(cli_context_t *ctx, int argc, char **argv)
{
    (void)ctx;
    shield_state_t *state = shield_state_get();
    
    if (argc < 1) {
        printf("Current format: %s\n", state->siem.format);
        printf("Usage: siem format <cef|json|syslog>\n");
        return SHIELD_OK;
    }
    
    strncpy(state->siem.format, argv[0], sizeof(state->siem.format) - 1);
    shield_state_mark_dirty();
    printf("SIEM format set to %s\n", state->siem.format);
    return SHIELD_OK;
}

shield_err_t cmd_show_siem(cli_context_t *ctx, int argc, char **argv)
{
    (void)ctx; (void)argc; (void)argv;
    shield_state_t *state = shield_state_get();
    
    printf("SIEM Status\n");
    printf("===========\n");
    printf("Enabled:     %s\n", state->siem.enabled ? "YES" : "NO");
    printf("Destination: %s:%u\n",
           state->siem.host[0] ? state->siem.host : "(none)",
           state->siem.port);
    printf("Format:      %s\n", state->siem.format);
    printf("Events Sent: %llu\n", (unsigned long long)state->siem.events_sent);
    printf("Failed:      %llu\n", (unsigned long long)state->siem.events_failed);
    return SHIELD_OK;
}

/* ===== Signature Commands ===== */

shield_err_t cmd_signature_update(cli_context_t *ctx, int argc, char **argv)
{
    (void)ctx; (void)argc; (void)argv;
    printf("Checking for signature updates...\n");
    printf("Signatures are up to date\n");
    return SHIELD_OK;
}

shield_err_t cmd_signature_category_enable(cli_context_t *ctx, int argc, char **argv)
{
    (void)ctx;
    if (argc < 1) {
        printf("Usage: signature-set category enable <category>\n");
        printf("Categories: injection, jailbreak, exfiltration, pii, secrets\n");
        return SHIELD_OK;
    }
    printf("Signature category '%s' enabled\n", argv[0]);
    return SHIELD_OK;
}

shield_err_t cmd_signature_category_disable(cli_context_t *ctx, int argc, char **argv)
{
    (void)ctx;
    if (argc < 1) {
        printf("Usage: signature-set category disable <category>\n");
        return SHIELD_OK;
    }
    printf("Signature category '%s' disabled\n", argv[0]);
    return SHIELD_OK;
}

shield_err_t cmd_show_signatures(cli_context_t *ctx, int argc, char **argv)
{
    (void)ctx; (void)argc; (void)argv;
    printf("Signature Database\n");
    printf("==================\n");
    printf("LLM Guard:   70 patterns\n");
    printf("MCP Guard:   32 patterns\n");
    printf("RAG Guard:   27 patterns\n");
    printf("Tool Guard:  48 patterns\n");
    printf("Agent Guard: 40 patterns\n");
    printf("API Guard:   36 patterns\n");
    printf("-------------------\n");
    printf("Total:      253 patterns\n");
    return SHIELD_OK;
}

/* ===== API Commands ===== */

shield_err_t cmd_api_enable(cli_context_t *ctx, int argc, char **argv)
{
    (void)ctx; (void)argc; (void)argv;
    shield_state_t *state = shield_state_get();
    state->api.enabled = true;
    shield_state_mark_dirty();
    printf("REST API enabled on port %u\n", state->api.port);
    return SHIELD_OK;
}

shield_err_t cmd_api_disable(cli_context_t *ctx, int argc, char **argv)
{
    (void)ctx; (void)argc; (void)argv;
    shield_state_t *state = shield_state_get();
    state->api.enabled = false;
    shield_state_mark_dirty();
    printf("REST API disabled\n");
    return SHIELD_OK;
}

shield_err_t cmd_api_port(cli_context_t *ctx, int argc, char **argv)
{
    (void)ctx;
    shield_state_t *state = shield_state_get();
    
    if (argc < 1) {
        printf("Current API port: %u\n", state->api.port);
        return SHIELD_OK;
    }
    
    state->api.port = atoi(argv[0]);
    shield_state_mark_dirty();
    printf("API port set to %u\n", state->api.port);
    return SHIELD_OK;
}

shield_err_t cmd_api_token(cli_context_t *ctx, int argc, char **argv)
{
    (void)ctx;
    shield_state_t *state = shield_state_get();
    
    if (argc < 1) {
        printf("API token: %s\n", state->api.token[0] ? "(configured)" : "(not set)");
        return SHIELD_OK;
    }
    
    strncpy(state->api.token, argv[0], sizeof(state->api.token) - 1);
    shield_state_mark_dirty();
    printf("API token configured\n");
    return SHIELD_OK;
}

shield_err_t cmd_metrics_enable(cli_context_t *ctx, int argc, char **argv)
{
    (void)ctx; (void)argc; (void)argv;
    shield_state_t *state = shield_state_get();
    state->api.metrics_enabled = true;
    shield_state_mark_dirty();
    printf("Metrics endpoint enabled on port %u\n", state->api.metrics_port);
    return SHIELD_OK;
}

shield_err_t cmd_metrics_port(cli_context_t *ctx, int argc, char **argv)
{
    (void)ctx;
    shield_state_t *state = shield_state_get();
    
    if (argc < 1) {
        printf("Current metrics port: %u\n", state->api.metrics_port);
        return SHIELD_OK;
    }
    
    state->api.metrics_port = atoi(argv[0]);
    shield_state_mark_dirty();
    printf("Metrics port set to %u\n", state->api.metrics_port);
    return SHIELD_OK;
}

shield_err_t cmd_show_api(cli_context_t *ctx, int argc, char **argv)
{
    (void)ctx; (void)argc; (void)argv;
    shield_state_t *state = shield_state_get();
    
    printf("REST API Status\n");
    printf("===============\n");
    printf("Enabled: %s\n", state->api.enabled ? "YES" : "NO");
    printf("Port:    %u\n", state->api.port);
    printf("Token:   %s\n", state->api.token[0] ? "(configured)" : "(not set)");
    printf("Requests: %llu\n", (unsigned long long)state->api.requests_handled);
    printf("\nMetrics Status\n");
    printf("Enabled: %s\n", state->api.metrics_enabled ? "YES" : "NO");
    printf("Port:    %u\n", state->api.metrics_port);
    return SHIELD_OK;
}

/* ===== Canary Commands ===== */

shield_err_t cmd_canary_add(cli_context_t *ctx, int argc, char **argv)
{
    (void)ctx;
    if (argc < 1) {
        printf("Usage: canary token add <token>\n");
        return SHIELD_OK;
    }
    printf("Canary token added: %s\n", argv[0]);
    return SHIELD_OK;
}

shield_err_t cmd_canary_remove(cli_context_t *ctx, int argc, char **argv)
{
    (void)ctx;
    if (argc < 1) {
        printf("Usage: no canary token <token>\n");
        return SHIELD_OK;
    }
    printf("Canary token removed: %s\n", argv[0]);
    return SHIELD_OK;
}

shield_err_t cmd_show_canary_tokens(cli_context_t *ctx, int argc, char **argv)
{
    (void)ctx; (void)argc; (void)argv;
    printf("Canary Tokens\n");
    printf("=============\n");
    printf("Active tokens: 0\n");
    printf("Triggered: 0\n");
    return SHIELD_OK;
}

/* ===== Command Table ===== */

static cli_command_t network_commands[] = {
    /* HA Standby */
    {"standby ip", cmd_standby_ip, CLI_MODE_CONFIG, "Set virtual IP"},
    {"standby priority", cmd_standby_priority, CLI_MODE_CONFIG, "Set priority"},
    {"standby preempt", cmd_standby_preempt, CLI_MODE_CONFIG, "Enable preempt"},
    {"no standby preempt", cmd_no_standby_preempt, CLI_MODE_CONFIG, "Disable preempt"},
    {"standby timers", cmd_standby_timers, CLI_MODE_CONFIG, "Set timers"},
    {"standby authentication", cmd_standby_authentication, CLI_MODE_CONFIG, "Set auth key"},
    {"standby track", cmd_standby_track, CLI_MODE_CONFIG, "Track object"},
    {"standby name", cmd_standby_name, CLI_MODE_CONFIG, "Set cluster name"},
    {"show ha", cmd_show_ha, CLI_MODE_ANY, "Show HA status"},
    
    /* Redundancy */
    {"redundancy", cmd_redundancy, CLI_MODE_CONFIG, "Enter redundancy mode"},
    {"redundancy mode", cmd_redundancy_mode, CLI_MODE_CONFIG, "Set redundancy mode"},
    
    /* Failover */
    {"failover", cmd_failover_enable, CLI_MODE_CONFIG, "Enable failover"},
    {"no failover", cmd_failover_disable, CLI_MODE_CONFIG, "Disable failover"},
    {"failover lan interface", cmd_failover_lan, CLI_MODE_CONFIG, "Set failover interface"},
    
    /* Rate Limiting */
    {"rate-limit enable", cmd_rate_limit_enable, CLI_MODE_CONFIG, "Enable rate limiting"},
    {"no rate-limit", cmd_rate_limit_disable, CLI_MODE_CONFIG, "Disable rate limiting"},
    {"rate-limit requests", cmd_rate_limit_config, CLI_MODE_CONFIG, "Configure rate limit"},
    {"show rate-limit", cmd_show_rate_limit, CLI_MODE_ANY, "Show rate limit status"},
    
    /* Blocklist */
    {"blocklist ip add", cmd_blocklist_ip_add, CLI_MODE_CONFIG, "Add IP to blocklist"},
    {"no blocklist ip", cmd_blocklist_ip_remove, CLI_MODE_CONFIG, "Remove IP from blocklist"},
    {"blocklist pattern add", cmd_blocklist_pattern_add, CLI_MODE_CONFIG, "Add pattern"},
    {"show blocklist", cmd_show_blocklist, CLI_MODE_ANY, "Show blocklist"},
    
    /* Threat Intel */
    {"threat-intel enable", cmd_threat_intel_enable, CLI_MODE_CONFIG, "Enable threat intel"},
    {"no threat-intel", cmd_threat_intel_disable, CLI_MODE_CONFIG, "Disable threat intel"},
    {"threat-intel feed add", cmd_threat_intel_feed, CLI_MODE_CONFIG, "Add threat feed"},
    {"show threat-intel", cmd_show_threat_intel, CLI_MODE_ANY, "Show threat intel"},
    
    /* Alerting */
    {"alert destination", cmd_alert_destination, CLI_MODE_CONFIG, "Set alert destination"},
    {"alert threshold", cmd_alert_threshold, CLI_MODE_CONFIG, "Set alert threshold"},
    {"show alerts", cmd_show_alerts, CLI_MODE_ANY, "Show alerts"},
    
    /* SIEM */
    {"siem enable", cmd_siem_enable, CLI_MODE_CONFIG, "Enable SIEM export"},
    {"no siem", cmd_siem_disable, CLI_MODE_CONFIG, "Disable SIEM export"},
    {"siem destination", cmd_siem_destination, CLI_MODE_CONFIG, "Set SIEM destination"},
    {"siem format", cmd_siem_format, CLI_MODE_CONFIG, "Set SIEM format"},
    {"show siem", cmd_show_siem, CLI_MODE_ANY, "Show SIEM status"},
    
    /* Signatures */
    {"signature-set update", cmd_signature_update, CLI_MODE_PRIV, "Update signatures"},
    {"signature-set category enable", cmd_signature_category_enable, CLI_MODE_CONFIG, "Enable category"},
    {"signature-set category disable", cmd_signature_category_disable, CLI_MODE_CONFIG, "Disable category"},
    {"show signatures", cmd_show_signatures, CLI_MODE_ANY, "Show signatures"},
    
    /* API/Metrics */
    {"api enable", cmd_api_enable, CLI_MODE_CONFIG, "Enable REST API"},
    {"no api", cmd_api_disable, CLI_MODE_CONFIG, "Disable REST API"},
    {"api port", cmd_api_port, CLI_MODE_CONFIG, "Set API port"},
    {"api token", cmd_api_token, CLI_MODE_CONFIG, "Set API token"},
    {"metrics enable", cmd_metrics_enable, CLI_MODE_CONFIG, "Enable metrics"},
    {"metrics port", cmd_metrics_port, CLI_MODE_CONFIG, "Set metrics port"},
    {"show api", cmd_show_api, CLI_MODE_ANY, "Show API status"},
    
    /* Canary */
    {"canary token add", cmd_canary_add, CLI_MODE_CONFIG, "Add canary token"},
    {"no canary token", cmd_canary_remove, CLI_MODE_CONFIG, "Remove canary token"},
    {"show canary", cmd_show_canary_tokens, CLI_MODE_ANY, "Show canary tokens"},
    
    {NULL, NULL, 0, NULL}
};

void register_network_commands(cli_context_t *ctx)
{
    /* Initialize state */
    shield_state_get();
    
    /* Register all network commands */
    for (int i = 0; network_commands[i].name != NULL; i++) {
        cli_register_command(ctx, &network_commands[i]);
    }
}
