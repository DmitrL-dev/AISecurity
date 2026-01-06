/*
 * SENTINEL Shield - Extended CLI Commands
 * 
 * Additional commands for HA, metrics, plugins
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "shield_common.h"
#include "shield_cli.h"
#include "shield_ha.h"
#include "shield_health.h"
#include "shield_metrics.h"
#include "shield_plugin.h"
#include "shield_event.h"
#include "shield_canary.h"

/* Forward declarations */
extern ha_cluster_t *g_cluster;
extern health_manager_t *g_health;
extern metrics_registry_t *g_metrics;
extern plugin_manager_t *g_plugins;
extern canary_manager_t *g_canaries;

/*
 * show ha
 */
static shield_err_t cmd_show_ha(cli_context_t *ctx, int argc, char **argv)
{
    (void)argc; (void)argv;
    
    if (!g_cluster) {
        cli_print("HA not configured\n");
        return SHIELD_OK;
    }
    
    const char *role_str;
    switch (ha_get_role(g_cluster)) {
    case HA_ROLE_ACTIVE: role_str = "ACTIVE"; break;
    case HA_ROLE_STANDBY: role_str = "STANDBY"; break;
    default: role_str = "STANDALONE"; break;
    }
    
    const char *state_str;
    switch (ha_get_state(g_cluster)) {
    case HA_STATE_ACTIVE: state_str = "Active"; break;
    case HA_STATE_STANDBY: state_str = "Standby"; break;
    case HA_STATE_SYNC: state_str = "Synchronizing"; break;
    case HA_STATE_FAILED: state_str = "Failed"; break;
    default: state_str = "Unknown"; break;
    }
    
    cli_print("HA Status\n");
    cli_print("  Role:   %s\n", role_str);
    cli_print("  State:  %s\n", state_str);
    cli_print("  Peers:  %d\n", ha_get_peer_count(g_cluster));
    return SHIELD_OK;
}

/*
 * show health
 */
static shield_err_t cmd_show_health(cli_context_t *ctx, int argc, char **argv)
{
    (void)argc; (void)argv;
    
    if (!g_health) {
        cli_print("Health monitoring not configured\n");
        return SHIELD_OK;
    }
    
    health_status_t status = health_get_status(g_health);
    cli_print("Overall Health: %s\n", health_status_string(status));
    cli_print("\n");
    
    char *json = health_export_json(g_health);
    if (json) {
        cli_print("%s\n", json);
        free(json);
    }
    return SHIELD_OK;
}

/*
 * show metrics
 */
static shield_err_t cmd_show_metrics(cli_context_t *ctx, int argc, char **argv)
{
    (void)argc; (void)argv;
    
    if (!g_metrics) {
        cli_print("Metrics not configured\n");
        return SHIELD_OK;
    }
    
    char *metrics = metrics_export_prometheus(g_metrics);
    if (metrics) {
        cli_print("%s\n", metrics);
        free(metrics);
    }
    return SHIELD_OK;
}

/*
 * show plugins
 */
static shield_err_t cmd_show_plugins(cli_context_t *ctx, int argc, char **argv)
{
    (void)argc; (void)argv;
    
    if (!g_plugins) {
        cli_print("Plugin system not configured\n");
        return SHIELD_OK;
    }
    
    cli_print("Loaded Plugins:\n");
    
    plugin_info_t infos[32];
    int count = plugin_list(g_plugins, infos, 32);
    
    if (count == 0) {
        cli_print("  (none)\n");
        return SHIELD_OK;
    }
    
    for (int i = 0; i < count; i++) {
        cli_print("  %s v%s - %s\n",
                  infos[i].name, infos[i].version, infos[i].description);
    }
    return SHIELD_OK;
}

/*
 * show canary
 */
static shield_err_t cmd_show_canary(cli_context_t *ctx, int argc, char **argv)
{
    (void)argc; (void)argv;
    
    if (!g_canaries) {
        cli_print("Canary tokens not configured\n");
        return SHIELD_OK;
    }
    
    cli_print("Canary Tokens: %u\n", g_canaries->count);
    cli_print("\n");
    
    canary_token_t *token = g_canaries->tokens;
    int i = 1;
    while (token && i <= 10) {
        cli_print("  %d. %s\n", i, token->id);
        cli_print("     Value: %s...\n", 
                  strlen(token->value) > 20 ? "..." : token->value);
        cli_print("     Triggers: %lu\n", (unsigned long)token->triggered_count);
        token = token->next;
        i++;
    }
    return SHIELD_OK;
}

/*
 * ha force active
 */
static shield_err_t cmd_ha_force_active(cli_context_t *ctx, int argc, char **argv)
{
    (void)argc; (void)argv;
    
    if (!g_cluster) {
        cli_print("%% HA not configured\n");
        return SHIELD_OK;
    }
    
    ha_force_active(g_cluster);
    cli_print("Forced to ACTIVE\n");
    return SHIELD_OK;
}

/*
 * ha force standby
 */
static shield_err_t cmd_ha_force_standby(cli_context_t *ctx, int argc, char **argv)
{
    (void)argc; (void)argv;
    
    if (!g_cluster) {
        cli_print("%% HA not configured\n");
        return SHIELD_OK;
    }
    
    ha_force_standby(g_cluster);
    cli_print("Forced to STANDBY\n");
    return SHIELD_OK;
}

/*
 * ha sync
 */
static shield_err_t cmd_ha_sync(cli_context_t *ctx, int argc, char **argv)
{
    (void)argc; (void)argv;
    
    if (!g_cluster) {
        cli_print("%% HA not configured\n");
        return SHIELD_OK;
    }
    
    ha_sync_config(g_cluster);
    ha_sync_blocklist(g_cluster);
    ha_sync_sessions(g_cluster);
    cli_print("Sync initiated\n");
    return SHIELD_OK;
}

/*
 * canary create <value> [description]
 */
static shield_err_t cmd_canary_create(cli_context_t *ctx, int argc, char **argv)
{
    if (argc < 3) {
        cli_print("Usage: canary create <value> [description]\n");
        return SHIELD_OK;
    }
    
    if (!g_canaries) {
        cli_print("%% Canary system not configured\n");
        return SHIELD_OK;
    }
    
    canary_token_t *token = NULL;
    const char *desc = argc > 3 ? argv[3] : "CLI created";
    
    shield_err_t err = canary_create(g_canaries, CANARY_TYPE_STRING, argv[2], desc, &token);
    if (err == SHIELD_OK && token) {
        cli_print("Created canary token: %s\n", token->id);
    } else {
        cli_print("%% Failed to create canary token\n");
    }
    return SHIELD_OK;
}

/*
 * canary generate
 */
static shield_err_t cmd_canary_generate(cli_context_t *ctx, int argc, char **argv)
{
    (void)argc; (void)argv;
    
    if (!g_canaries) {
        cli_print("%% Canary system not configured\n");
        return SHIELD_OK;
    }
    
    canary_token_t *token = NULL;
    shield_err_t err = canary_generate(g_canaries, CANARY_TYPE_UUID, &token);
    if (err == SHIELD_OK && token) {
        cli_print("Generated canary token:\n");
        cli_print("  ID:    %s\n", token->id);
        cli_print("  Value: %s\n", token->value);
    } else {
        cli_print("%% Failed to generate canary token\n");
    }
    return SHIELD_OK;
}

/*
 * plugin load <path>
 */
static shield_err_t cmd_plugin_load(cli_context_t *ctx, int argc, char **argv)
{
    if (argc < 3) {
        cli_print("Usage: plugin load <path>\n");
        return SHIELD_OK;
    }
    
    if (!g_plugins) {
        cli_print("%% Plugin system not configured\n");
        return SHIELD_OK;
    }
    
    shield_err_t err = plugin_load(g_plugins, argv[2]);
    if (err == SHIELD_OK) {
        cli_print("Plugin loaded successfully\n");
    } else {
        cli_print("%% Failed to load plugin: %d\n", err);
    }
    return SHIELD_OK;
}

/*
 * plugin unload <name>
 */
static shield_err_t cmd_plugin_unload(cli_context_t *ctx, int argc, char **argv)
{
    if (argc < 3) {
        cli_print("Usage: plugin unload <name>\n");
        return SHIELD_OK;
    }
    
    if (!g_plugins) {
        cli_print("%% Plugin system not configured\n");
        return SHIELD_OK;
    }
    
    shield_err_t err = plugin_unload(g_plugins, argv[2]);
    if (err == SHIELD_OK) {
        cli_print("Plugin unloaded\n");
    } else {
        cli_print("%% Plugin not found\n");
    }
    return SHIELD_OK;
}

/*
 * debug event <type>
 */
static shield_err_t cmd_debug_event(cli_context_t *ctx, int argc, char **argv)
{
    (void)argc; (void)argv;
    cli_print("Event system debug:\n");
    cli_print("  (implementation pending)\n");
    return SHIELD_OK;
}

/* Command table for extended commands */
static cli_command_t extended_commands[] = {
    /* HA */
    {"show ha", cmd_show_ha, CLI_MODE_EXEC, "Display HA cluster status"},
    {"ha force active", cmd_ha_force_active, CLI_MODE_PRIV, "Force this node to ACTIVE"},
    {"ha force standby", cmd_ha_force_standby, CLI_MODE_PRIV, "Force this node to STANDBY"},
    {"ha sync", cmd_ha_sync, CLI_MODE_PRIV, "Trigger HA synchronization"},
    
    /* Health */
    {"show health", cmd_show_health, CLI_MODE_EXEC, "Display health status"},
    
    /* Metrics */
    {"show metrics", cmd_show_metrics, CLI_MODE_EXEC, "Display metrics"},
    
    /* Plugins */
    {"show plugins", cmd_show_plugins, CLI_MODE_EXEC, "List loaded plugins"},
    {"plugin load", cmd_plugin_load, CLI_MODE_CONFIG, "Load a plugin"},
    {"plugin unload", cmd_plugin_unload, CLI_MODE_CONFIG, "Unload a plugin"},
    
    /* Canary */
    {"show canary", cmd_show_canary, CLI_MODE_EXEC, "Display canary tokens"},
    {"canary create", cmd_canary_create, CLI_MODE_CONFIG, "Create canary token"},
    {"canary generate", cmd_canary_generate, CLI_MODE_CONFIG, "Generate random canary"},
    
    /* Debug */
    {"debug event", cmd_debug_event, CLI_MODE_PRIV, "Debug event system"},
    
    {NULL, NULL, 0, NULL}
};

/* Register extended commands */
void register_extended_commands(cli_context_t *ctx)
{
    for (int i = 0; extended_commands[i].name != NULL; i++) {
        cli_register_command(ctx, &extended_commands[i]);
    }
}
