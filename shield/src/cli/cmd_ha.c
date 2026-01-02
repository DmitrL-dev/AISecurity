/*
 * SENTINEL Shield - HA Commands
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "shield_common.h"
#include "shield_cli.h"
#include "shield_ha.h"

/* standby ip */
static void cmd_standby_ip(cli_context_t *ctx, int argc, char **argv)
{
    if (argc < 3) {
        cli_print(ctx, "%% Usage: standby ip <virtual-ip>\n");
        return;
    }
    strncpy(ctx->ha.virtual_ip, argv[2], sizeof(ctx->ha.virtual_ip) - 1);
    ctx->ha.enabled = true;
    cli_print(ctx, "Standby IP set to %s\n", argv[2]);
    ctx->modified = true;
}

/* standby priority */
static void cmd_standby_priority(cli_context_t *ctx, int argc, char **argv)
{
    if (argc < 3) {
        cli_print(ctx, "%% Usage: standby priority <0-255>\n");
        return;
    }
    ctx->ha.priority = atoi(argv[2]);
    cli_print(ctx, "Standby priority set to %d\n", ctx->ha.priority);
    ctx->modified = true;
}

/* standby preempt */
static void cmd_standby_preempt(cli_context_t *ctx, int argc, char **argv)
{
    (void)argc; (void)argv;
    ctx->ha.preempt = true;
    cli_print(ctx, "Standby preempt enabled\n");
    ctx->modified = true;
}

/* no standby preempt */
static void cmd_no_standby_preempt(cli_context_t *ctx, int argc, char **argv)
{
    (void)argc; (void)argv;
    ctx->ha.preempt = false;
    cli_print(ctx, "Standby preempt disabled\n");
    ctx->modified = true;
}

/* standby timers */
static void cmd_standby_timers(cli_context_t *ctx, int argc, char **argv)
{
    if (argc < 4) {
        cli_print(ctx, "%% Usage: standby timers <hello> <hold>\n");
        return;
    }
    ctx->ha.hello_interval = atoi(argv[2]);
    ctx->ha.hold_time = atoi(argv[3]);
    cli_print(ctx, "Standby timers: hello=%d, hold=%d\n", 
             ctx->ha.hello_interval, ctx->ha.hold_time);
    ctx->modified = true;
}

/* standby authentication */
static void cmd_standby_auth(cli_context_t *ctx, int argc, char **argv)
{
    if (argc < 3) {
        cli_print(ctx, "%% Usage: standby authentication <key>\n");
        return;
    }
    strncpy(ctx->ha.auth_key, argv[2], sizeof(ctx->ha.auth_key) - 1);
    cli_print(ctx, "Standby authentication configured\n");
    ctx->modified = true;
}

/* standby track */
static void cmd_standby_track(cli_context_t *ctx, int argc, char **argv)
{
    if (argc < 4) {
        cli_print(ctx, "%% Usage: standby track <object> <decrement>\n");
        return;
    }
    strncpy(ctx->ha.track_object, argv[2], sizeof(ctx->ha.track_object) - 1);
    ctx->ha.track_decrement = atoi(argv[3]);
    cli_print(ctx, "Standby tracking: %s, decrement=%d\n", argv[2], ctx->ha.track_decrement);
    ctx->modified = true;
}

/* standby name */
static void cmd_standby_name(cli_context_t *ctx, int argc, char **argv)
{
    if (argc < 3) {
        cli_print(ctx, "%% Usage: standby name <cluster-name>\n");
        return;
    }
    strncpy(ctx->ha.cluster_name, argv[2], sizeof(ctx->ha.cluster_name) - 1);
    cli_print(ctx, "Standby cluster name: %s\n", argv[2]);
    ctx->modified = true;
}

/* redundancy */
static void cmd_redundancy(cli_context_t *ctx, int argc, char **argv)
{
    (void)argc; (void)argv;
    cli_set_mode(ctx, CLI_MODE_HA);
}

/* redundancy mode */
static void cmd_redundancy_mode(cli_context_t *ctx, int argc, char **argv)
{
    if (argc < 3) {
        cli_print(ctx, "%% Usage: redundancy mode <active-standby|active-active>\n");
        return;
    }
    if (strcmp(argv[2], "active-standby") == 0) {
        ctx->ha.mode = HA_MODE_ACTIVE_STANDBY;
    } else if (strcmp(argv[2], "active-active") == 0) {
        ctx->ha.mode = HA_MODE_ACTIVE_ACTIVE;
    }
    cli_print(ctx, "Redundancy mode: %s\n", argv[2]);
    ctx->modified = true;
}

/* failover */
static void cmd_failover(cli_context_t *ctx, int argc, char **argv)
{
    (void)argc; (void)argv;
    ctx->ha.failover_enabled = true;
    cli_print(ctx, "Failover enabled\n");
    ctx->modified = true;
}

/* no failover */
static void cmd_no_failover(cli_context_t *ctx, int argc, char **argv)
{
    (void)argc; (void)argv;
    ctx->ha.failover_enabled = false;
    cli_print(ctx, "Failover disabled\n");
    ctx->modified = true;
}

/* failover lan interface */
static void cmd_failover_lan(cli_context_t *ctx, int argc, char **argv)
{
    if (argc < 4) {
        cli_print(ctx, "%% Usage: failover lan interface <name>\n");
        return;
    }
    strncpy(ctx->ha.failover_interface, argv[3], sizeof(ctx->ha.failover_interface) - 1);
    cli_print(ctx, "Failover LAN interface: %s\n", argv[3]);
    ctx->modified = true;
}

/* ha sync start */
static void cmd_ha_sync_start(cli_context_t *ctx, int argc, char **argv)
{
    (void)argc; (void)argv;
    cli_print(ctx, "Initiating HA sync...\n");
    if (ctx->ha.enabled) {
        ha_sync_all(ctx->shield);
        cli_print(ctx, "Sync complete\n");
    } else {
        cli_print(ctx, "%% HA not enabled\n");
    }
}

/* HA command table */
static cli_command_t ha_commands[] = {
    {"standby ip", cmd_standby_ip, CLI_MODE_CONFIG, "Set standby IP"},
    {"standby priority", cmd_standby_priority, CLI_MODE_CONFIG, "Set standby priority"},
    {"standby preempt", cmd_standby_preempt, CLI_MODE_CONFIG, "Enable preempt"},
    {"no standby preempt", cmd_no_standby_preempt, CLI_MODE_CONFIG, "Disable preempt"},
    {"standby timers", cmd_standby_timers, CLI_MODE_CONFIG, "Set timers"},
    {"standby authentication", cmd_standby_auth, CLI_MODE_CONFIG, "Set auth key"},
    {"standby track", cmd_standby_track, CLI_MODE_CONFIG, "Set tracking"},
    {"standby name", cmd_standby_name, CLI_MODE_CONFIG, "Set cluster name"},
    {"redundancy", cmd_redundancy, CLI_MODE_CONFIG, "Enter redundancy mode"},
    {"redundancy mode", cmd_redundancy_mode, CLI_MODE_CONFIG, "Set redundancy mode"},
    {"failover", cmd_failover, CLI_MODE_CONFIG, "Enable failover"},
    {"no failover", cmd_no_failover, CLI_MODE_CONFIG, "Disable failover"},
    {"failover lan interface", cmd_failover_lan, CLI_MODE_CONFIG, "Set failover interface"},
    {"ha sync start", cmd_ha_sync_start, CLI_MODE_PRIV, "Start HA sync"},
    {NULL, NULL, 0, NULL}
};

void register_ha_commands(cli_context_t *ctx)
{
    for (int i = 0; ha_commands[i].name != NULL; i++) {
        cli_register_command(ctx, &ha_commands[i]);
    }
}
