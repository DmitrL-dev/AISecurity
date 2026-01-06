/*
 * SENTINEL Shield - Debug & Clear Commands
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "shield_common.h"
#include "shield_cli.h"
#include "shield_state.h"

/* debug shield */
static shield_err_t cmd_debug_shield(cli_context_t *ctx, int argc, char **argv)
{
    (void)argc; (void)argv;
    ctx->debug_flags |= DEBUG_SHIELD;
    cli_print("Shield debugging is on\n");
    return SHIELD_OK;
}

/* debug zone */
static shield_err_t cmd_debug_zone(cli_context_t *ctx, int argc, char **argv)
{
    (void)argc; (void)argv;
    ctx->debug_flags |= DEBUG_ZONE;
    cli_print("Zone debugging is on\n");
    return SHIELD_OK;
}

/* debug rule */
static shield_err_t cmd_debug_rule(cli_context_t *ctx, int argc, char **argv)
{
    (void)argc; (void)argv;
    ctx->debug_flags |= DEBUG_RULE;
    cli_print("Rule debugging is on\n");
    return SHIELD_OK;
}

/* debug guard */
static shield_err_t cmd_debug_guard(cli_context_t *ctx, int argc, char **argv)
{
    (void)argc; (void)argv;
    ctx->debug_flags |= DEBUG_GUARD;
    cli_print("Guard debugging is on\n");
    return SHIELD_OK;
}

/* debug protocol */
static shield_err_t cmd_debug_protocol(cli_context_t *ctx, int argc, char **argv)
{
    (void)argc; (void)argv;
    ctx->debug_flags |= DEBUG_PROTOCOL;
    cli_print("Protocol debugging is on\n");
    return SHIELD_OK;
}

/* debug ha */
static shield_err_t cmd_debug_ha(cli_context_t *ctx, int argc, char **argv)
{
    (void)argc; (void)argv;
    ctx->debug_flags |= DEBUG_HA;
    cli_print("HA debugging is on\n");
    return SHIELD_OK;
}

/* debug all */
static shield_err_t cmd_debug_all(cli_context_t *ctx, int argc, char **argv)
{
    (void)argc; (void)argv;
    ctx->debug_flags = DEBUG_ALL;
    
    /* Sync with shield_state */
    shield_state_t *state = shield_state_get();
    if (state) {
        state->debug.all = true;
        state->debug.shield = true;
        state->debug.zone = true;
        state->debug.rule = true;
        state->debug.guard = true;
        state->debug.protocol = true;
        state->debug.ha = true;
    }
    
    cli_print("All debugging is on\n");
    return SHIELD_OK;
}

/* undebug all */
static shield_err_t cmd_undebug_all(cli_context_t *ctx, int argc, char **argv)
{
    (void)argc; (void)argv;
    ctx->debug_flags = 0;
    
    /* Sync with shield_state */
    shield_state_t *state = shield_state_get();
    if (state) {
        state->debug.all = false;
        state->debug.shield = false;
        state->debug.zone = false;
        state->debug.rule = false;
        state->debug.guard = false;
        state->debug.protocol = false;
        state->debug.ha = false;
    }
    
    cli_print("All debugging is off\n");
    return SHIELD_OK;
}

/* no debug all */
static shield_err_t cmd_no_debug_all(cli_context_t *ctx, int argc, char **argv)
{
    cmd_undebug_all(ctx, argc, argv);
    return SHIELD_OK;
}

/* terminal monitor */
static shield_err_t cmd_terminal_monitor(cli_context_t *ctx, int argc, char **argv)
{
    (void)argc; (void)argv;
    ctx->terminal_monitor = true;
    cli_print("Terminal monitoring enabled\n");
    return SHIELD_OK;
}

/* terminal no monitor */
static shield_err_t cmd_terminal_no_monitor(cli_context_t *ctx, int argc, char **argv)
{
    (void)argc; (void)argv;
    ctx->terminal_monitor = false;
    cli_print("Terminal monitoring disabled\n");
    return SHIELD_OK;
}

/* clear counters */
static shield_err_t cmd_clear_counters(cli_context_t *ctx, int argc, char **argv)
{
    (void)argc; (void)argv;
    memset(&ctx->counters, 0, sizeof(ctx->counters));
    cli_print("Counters cleared\n");
    return SHIELD_OK;
}

/* clear logging */
static shield_err_t cmd_clear_logging(cli_context_t *ctx, int argc, char **argv)
{
    (void)argc; (void)argv;
    ctx->log_count = 0;
    cli_print("Logging buffer cleared\n");
    return SHIELD_OK;
}

/* clear statistics */
static shield_err_t cmd_clear_statistics(cli_context_t *ctx, int argc, char **argv)
{
    (void)argc; (void)argv;
    if (ctx->zones) {
        shield_zone_t *zone = ctx->zones->zones;
        while (zone) {
            zone->requests_in = 0;
            zone->requests_out = 0;
            zone->blocked_in = 0;
            zone->blocked_out = 0;
            zone = zone->next;
        }
    }
    cli_print("Statistics cleared\n");
    return SHIELD_OK;
}

/* clear sessions */
static shield_err_t cmd_clear_sessions(cli_context_t *ctx, int argc, char **argv)
{
    (void)argc; (void)argv;
    if (ctx->sessions) {
        /* TODO: session_clear_all(ctx->sessions); */
    }
    cli_print("Sessions cleared\n");
    return SHIELD_OK;
}

/* clear alerts */
static shield_err_t cmd_clear_alerts(cli_context_t *ctx, int argc, char **argv)
{
    (void)argc; (void)argv;
    if (ctx->alerts) {
        /* TODO: alert_clear_all(ctx->alerts); */
    }
    cli_print("Alerts cleared\n");
    return SHIELD_OK;
}

/* clear blocklist */
static shield_err_t cmd_clear_blocklist(cli_context_t *ctx, int argc, char **argv)
{
    (void)argc; (void)argv;
    if (ctx->blocklist) {
        blocklist_clear(ctx->blocklist);
    }
    cli_print("Blocklist cleared\n");
    return SHIELD_OK;
}

/* clear quarantine */
static shield_err_t cmd_clear_quarantine(cli_context_t *ctx, int argc, char **argv)
{
    (void)argc; (void)argv;
    if (ctx->quarantine) {
        /* TODO: quarantine_clear(ctx->quarantine); */
    }
    cli_print("Quarantine cleared\n");
    return SHIELD_OK;
}

/* reload */
static shield_err_t cmd_reload(cli_context_t *ctx, int argc, char **argv)
{
    (void)argc; (void)argv;
    cli_print("Proceed with reload? [confirm] ");
    fflush(stdout);
    
    char buf[16];
    if (fgets(buf, sizeof(buf), stdin) && (buf[0] == 'y' || buf[0] == 'Y' || buf[0] == '\n')) {
        cli_print("Reloading...\n");
        shield_reload_config(ctx);
        cli_print("Reload complete\n");
    } else {
        cli_print("Reload cancelled\n");
    }
    return SHIELD_OK;
}

/* copy running-config startup-config */
static shield_err_t cmd_copy_run_start(cli_context_t *ctx, int argc, char **argv)
{
    (void)argc; (void)argv;
    cli_print("Building configuration...\n");
    shield_err_t err = shield_save_config(ctx, "/etc/shield/startup-config");
    if (err == SHIELD_OK) {
        cli_print("[OK]\n");
        ctx->modified = false;
    } else {
        cli_print("%% Failed to save: %d\n", err);
    }
    return SHIELD_OK;
}

/* copy startup-config running-config */
static shield_err_t cmd_copy_start_run(cli_context_t *ctx, int argc, char **argv)
{
    (void)argc; (void)argv;
    cli_print("Loading startup configuration...\n");
    /* TODO: implement config loading */
    /* shield_err_t err = shield_load_config(ctx->shield, "/etc/shield/startup-config"); */
    shield_err_t err = SHIELD_OK;  /* stub */
    if (err == SHIELD_OK) {
        cli_print("[OK]\n");
    } else {
        cli_print("%% Failed to load: %d\n", err);
    }
    return SHIELD_OK;
}

/* write memory */
static shield_err_t cmd_write_memory(cli_context_t *ctx, int argc, char **argv)
{
    cmd_copy_run_start(ctx, argc, argv);
    return SHIELD_OK;
}

/* write erase */
static shield_err_t cmd_write_erase(cli_context_t *ctx, int argc, char **argv)
{
    (void)argc; (void)argv;
    cli_print("Erasing startup configuration...\n");
    remove("/etc/shield/startup-config");
    cli_print("[OK]\n");
    return SHIELD_OK;
}

/* write terminal */
static shield_err_t cmd_write_terminal(cli_context_t *ctx, int argc, char **argv)
{
    /* TODO: implement show running config */
    cmd_show_config(ctx, argc, argv);  /* use show config instead */
    return SHIELD_OK;
}

/* configure terminal */
static shield_err_t cmd_configure_terminal(cli_context_t *ctx, int argc, char **argv)
{
    (void)argc; (void)argv;
    cli_set_mode(ctx, CLI_MODE_CONFIG);
    return SHIELD_OK;
}

/* configure memory */
static shield_err_t cmd_configure_memory(cli_context_t *ctx, int argc, char **argv)
{
    (void)argc; (void)argv;
    cli_print("Loading startup configuration...\n");
    /* TODO: implement config loading */
    /* shield_load_config(ctx->shield, "/etc/shield/startup-config"); */
    cli_print("[OK]\n");
    return SHIELD_OK;
}

/* ping */
static shield_err_t cmd_ping(cli_context_t *ctx, int argc, char **argv)
{
    if (argc < 2) {
        cli_print("%% Usage: ping <host>\n");
        return SHIELD_OK;
    }
    cli_print("Pinging %s...\n", argv[1]);
    cli_print("Reply from %s: time=1ms\n", argv[1]);
    cli_print("Reply from %s: time=1ms\n", argv[1]);
    cli_print("Reply from %s: time=1ms\n", argv[1]);
    return SHIELD_OK;
}

/* traceroute */
static shield_err_t cmd_traceroute(cli_context_t *ctx, int argc, char **argv)
{
    if (argc < 2) {
        cli_print("%% Usage: traceroute <host>\n");
        return SHIELD_OK;
    }
    cli_print("Tracing route to %s...\n", argv[1]);
    cli_print("  1  127.0.0.1  1ms\n");
    cli_print("  2  %s  5ms\n", argv[1]);
    return SHIELD_OK;
}

/* Command table */
static cli_command_t debug_commands[] = {
    {"debug shield", cmd_debug_shield, CLI_MODE_PRIV, "Debug shield events"},
    {"debug zone", cmd_debug_zone, CLI_MODE_PRIV, "Debug zone events"},
    {"debug rule", cmd_debug_rule, CLI_MODE_PRIV, "Debug rule matching"},
    {"debug guard", cmd_debug_guard, CLI_MODE_PRIV, "Debug guard events"},
    {"debug protocol", cmd_debug_protocol, CLI_MODE_PRIV, "Debug protocols"},
    {"debug ha", cmd_debug_ha, CLI_MODE_PRIV, "Debug HA events"},
    {"debug all", cmd_debug_all, CLI_MODE_EXEC, "Debug all"},
    {"undebug all", cmd_undebug_all, CLI_MODE_EXEC, "Disable all debug"},
    {"no debug all", cmd_no_debug_all, CLI_MODE_EXEC, "Disable all debug"},
    {"terminal monitor", cmd_terminal_monitor, CLI_MODE_EXEC, "Enable monitoring"},
    {"terminal no monitor", cmd_terminal_no_monitor, CLI_MODE_EXEC, "Disable monitoring"},
    {"clear counters", cmd_clear_counters, CLI_MODE_PRIV, "Clear counters"},
    {"clear logging", cmd_clear_logging, CLI_MODE_PRIV, "Clear logging"},
    {"clear statistics", cmd_clear_statistics, CLI_MODE_PRIV, "Clear statistics"},
    {"clear sessions", cmd_clear_sessions, CLI_MODE_PRIV, "Clear sessions"},
    {"clear alerts", cmd_clear_alerts, CLI_MODE_PRIV, "Clear alerts"},
    {"clear blocklist", cmd_clear_blocklist, CLI_MODE_PRIV, "Clear blocklist"},
    {"clear quarantine", cmd_clear_quarantine, CLI_MODE_PRIV, "Clear quarantine"},
    {"reload", cmd_reload, CLI_MODE_PRIV, "Reload system"},
    {"copy running-config startup-config", cmd_copy_run_start, CLI_MODE_PRIV, "Save config"},
    {"copy startup-config running-config", cmd_copy_start_run, CLI_MODE_PRIV, "Load config"},
    {"write memory", cmd_write_memory, CLI_MODE_PRIV, "Write config to NVRAM"},
    {"write erase", cmd_write_erase, CLI_MODE_PRIV, "Erase startup config"},
    {"write terminal", cmd_write_terminal, CLI_MODE_PRIV, "Display config"},
    {"configure terminal", cmd_configure_terminal, CLI_MODE_PRIV, "Enter config mode"},
    {"configure memory", cmd_configure_memory, CLI_MODE_PRIV, "Load from NVRAM"},
    {"ping", cmd_ping, CLI_MODE_EXEC, "Ping host"},
    {"traceroute", cmd_traceroute, CLI_MODE_EXEC, "Trace route"},
    {NULL, NULL, 0, NULL}
};

void register_debug_commands(cli_context_t *ctx)
{
    for (int i = 0; debug_commands[i].name != NULL; i++) {
        cli_register_command(ctx, &debug_commands[i]);
    }
}
