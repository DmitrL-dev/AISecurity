/*
 * SENTINEL Shield - Show Commands
 * 
 * All "show" commands for displaying system state
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#include "shield_common.h"
#include "shield_cli.h"

/* show running-config */
static void cmd_show_running(cli_context_t *ctx, int argc, char **argv)
{
    (void)argc; (void)argv;
    cli_print(ctx, "!\n");
    cli_print(ctx, "! SENTINEL Shield Configuration\n");
    cli_print(ctx, "! Generated: %s\n", format_timestamp(time(NULL)));
    cli_print(ctx, "!\n");
    cli_print(ctx, "hostname %s\n", ctx->hostname);
    cli_print(ctx, "!\n");
    
    /* Show zones */
    shield_zone_t *zone = ctx->zones->zones;
    while (zone) {
        cli_print(ctx, "zone %s\n", zone->name);
        cli_print(ctx, "  type %s\n", zone_type_to_string(zone->type));
        if (zone->provider[0]) cli_print(ctx, "  provider %s\n", zone->provider);
        if (!zone->enabled) cli_print(ctx, "  shutdown\n");
        cli_print(ctx, "!\n");
        zone = zone->next;
    }
    
    cli_print(ctx, "end\n");
}

/* show startup-config */
static void cmd_show_startup(cli_context_t *ctx, int argc, char **argv)
{
    (void)argc; (void)argv;
    cli_print(ctx, "Startup configuration from NVRAM:\n\n");
    /* Load from file */
    FILE *f = fopen("/etc/shield/startup-config", "r");
    if (f) {
        char line[256];
        while (fgets(line, sizeof(line), f)) {
            cli_print(ctx, "%s", line);
        }
        fclose(f);
    } else {
        cli_print(ctx, "%% No startup configuration found\n");
    }
}

/* show interfaces */
static void cmd_show_interfaces(cli_context_t *ctx, int argc, char **argv)
{
    (void)argc; (void)argv;
    cli_print(ctx, "\nInterface Status:\n");
    cli_print(ctx, "─────────────────────────────────────────────────────\n");
    cli_print(ctx, "%-12s %-10s %-15s %-10s\n", "Interface", "Status", "IP Address", "MTU");
    cli_print(ctx, "%-12s %-10s %-15s %-10s\n", "─────────", "──────", "──────────", "───");
    cli_print(ctx, "%-12s %-10s %-15s %-10d\n", "api0", "up", "0.0.0.0:8080", 1500);
    cli_print(ctx, "%-12s %-10s %-15s %-10d\n", "metrics0", "up", "0.0.0.0:9090", 1500);
    cli_print(ctx, "\n");
}

/* show ip route */
static void cmd_show_ip_route(cli_context_t *ctx, int argc, char **argv)
{
    (void)argc; (void)argv;
    cli_print(ctx, "\nRouting Table (zones):\n");
    cli_print(ctx, "─────────────────────────────────────────────────────\n");
    cli_print(ctx, "%-20s %-20s %-10s\n", "Zone", "Next Hop", "Metric");
}

/* show users */
static void cmd_show_users(cli_context_t *ctx, int argc, char **argv)
{
    (void)argc; (void)argv;
    cli_print(ctx, "\nActive Users:\n");
    cli_print(ctx, "─────────────────────────────────────────────────────\n");
    cli_print(ctx, "%-15s %-20s %-15s\n", "Username", "From", "Idle");
    cli_print(ctx, "%-15s %-20s %-15s\n", "admin", "console", "00:00:00");
}

/* show clock */
static void cmd_show_clock(cli_context_t *ctx, int argc, char **argv)
{
    (void)argc; (void)argv;
    time_t now = time(NULL);
    struct tm *tm = localtime(&now);
    char buf[64];
    strftime(buf, sizeof(buf), "%H:%M:%S.000 %Z %a %b %d %Y", tm);
    cli_print(ctx, "%s\n", buf);
}

/* show uptime */
static void cmd_show_uptime(cli_context_t *ctx, int argc, char **argv)
{
    (void)argc; (void)argv;
    uint64_t uptime = ctx->uptime_seconds;
    uint64_t days = uptime / 86400;
    uint64_t hours = (uptime % 86400) / 3600;
    uint64_t mins = (uptime % 3600) / 60;
    uint64_t secs = uptime % 60;
    
    cli_print(ctx, "Shield uptime is %lu day(s), %lu hour(s), %lu minute(s), %lu second(s)\n",
             (unsigned long)days, (unsigned long)hours, 
             (unsigned long)mins, (unsigned long)secs);
}

/* show memory */
static void cmd_show_memory(cli_context_t *ctx, int argc, char **argv)
{
    (void)argc; (void)argv;
    cli_print(ctx, "\nMemory Statistics:\n");
    cli_print(ctx, "─────────────────────────────────────────────────────\n");
    cli_print(ctx, "  Total:     %lu MB\n", (unsigned long)(ctx->memory_total / 1048576));
    cli_print(ctx, "  Used:      %lu MB (%.1f%%)\n", 
             (unsigned long)(ctx->memory_used / 1048576),
             100.0 * ctx->memory_used / ctx->memory_total);
    cli_print(ctx, "  Free:      %lu MB\n", 
             (unsigned long)((ctx->memory_total - ctx->memory_used) / 1048576));
    cli_print(ctx, "\n");
}

/* show cpu */
static void cmd_show_cpu(cli_context_t *ctx, int argc, char **argv)
{
    (void)argc; (void)argv;
    cli_print(ctx, "\nCPU Utilization:\n");
    cli_print(ctx, "─────────────────────────────────────────────────────\n");
    cli_print(ctx, "  1 minute:  %.1f%%\n", ctx->cpu_1min);
    cli_print(ctx, "  5 minute:  %.1f%%\n", ctx->cpu_5min);
    cli_print(ctx, "  15 minute: %.1f%%\n", ctx->cpu_15min);
    cli_print(ctx, "\n");
}

/* show processes */
static void cmd_show_processes(cli_context_t *ctx, int argc, char **argv)
{
    (void)argc; (void)argv;
    cli_print(ctx, "\nShield Processes:\n");
    cli_print(ctx, "─────────────────────────────────────────────────────\n");
    cli_print(ctx, "%-8s %-20s %-10s %-10s\n", "PID", "Name", "CPU%", "Memory");
    cli_print(ctx, "%-8s %-20s %-10s %-10s\n", "───", "────", "────", "──────");
    cli_print(ctx, "%-8d %-20s %-10.1f %-10lu\n", 1, "shield-main", 2.5, 50000UL);
    cli_print(ctx, "%-8d %-20s %-10.1f %-10lu\n", 2, "shield-worker-1", 5.0, 20000UL);
    cli_print(ctx, "%-8d %-20s %-10.1f %-10lu\n", 3, "shield-worker-2", 4.8, 20000UL);
    cli_print(ctx, "%-8d %-20s %-10.1f %-10lu\n", 4, "shield-worker-3", 5.2, 20000UL);
    cli_print(ctx, "%-8d %-20s %-10.1f %-10lu\n", 5, "shield-worker-4", 4.5, 20000UL);
    cli_print(ctx, "\n");
}

/* show tech-support */
static void cmd_show_tech_support(cli_context_t *ctx, int argc, char **argv)
{
    (void)argc; (void)argv;
    cli_print(ctx, "\n========== SENTINEL SHIELD TECH-SUPPORT ==========\n\n");
    
    cmd_show_version(ctx, 0, NULL);
    cmd_show_uptime(ctx, 0, NULL);
    cmd_show_memory(ctx, 0, NULL);
    cmd_show_cpu(ctx, 0, NULL);
    cmd_show_interfaces(ctx, 0, NULL);
    cmd_show_zones(ctx, 0, NULL);
    cmd_show_rules(ctx, 0, NULL);
    cmd_show_stats(ctx, 0, NULL);
    
    cli_print(ctx, "\n========== END TECH-SUPPORT ==========\n");
}

/* show access-lists */
static void cmd_show_access_lists(cli_context_t *ctx, int argc, char **argv)
{
    (void)argc; (void)argv;
    
    if (!ctx->rules || ctx->rules->list_count == 0) {
        cli_print(ctx, "No access lists configured.\n");
        return;
    }
    
    access_list_t *acl = ctx->rules->lists;
    while (acl) {
        cli_print(ctx, "\nshield-rule %u (%u entries):\n", acl->number, acl->rule_count);
        
        shield_rule_t *rule = acl->rules;
        while (rule) {
            cli_print(ctx, "  %5u %s %s zone %s", 
                     rule->number,
                     action_to_string(rule->action),
                     direction_to_string(rule->direction),
                     zone_type_to_string(rule->zone_type));
            
            if (rule->conditions) {
                cli_print(ctx, " match %s", match_type_to_string(rule->conditions->type));
            }
            
            cli_print(ctx, " (%lu matches)\n", (unsigned long)rule->matches);
            rule = rule->next;
        }
        
        acl = acl->next;
    }
}

/* show logging */
static void cmd_show_logging(cli_context_t *ctx, int argc, char **argv)
{
    (void)argc; (void)argv;
    cli_print(ctx, "\nLogging Configuration:\n");
    cli_print(ctx, "─────────────────────────────────────────────────────\n");
    cli_print(ctx, "  Level:        %s\n", log_level_to_string(ctx->log_level));
    cli_print(ctx, "  Console:      %s\n", ctx->log_console ? "enabled" : "disabled");
    cli_print(ctx, "  Buffer size:  %u\n", ctx->log_buffer_size);
    cli_print(ctx, "  Log count:    %lu\n", (unsigned long)ctx->log_count);
    cli_print(ctx, "\n");
}

/* show history */
static void cmd_show_history(cli_context_t *ctx, int argc, char **argv)
{
    (void)argc; (void)argv;
    cli_print(ctx, "\nCommand history:\n");
    for (int i = 0; i < ctx->history_count && i < 20; i++) {
        cli_print(ctx, "  %3d  %s\n", i + 1, ctx->history[i]);
    }
}

/* show controllers */
static void cmd_show_controllers(cli_context_t *ctx, int argc, char **argv)
{
    (void)argc; (void)argv;
    cli_print(ctx, "\nShield Controllers:\n");
    cli_print(ctx, "─────────────────────────────────────────────────────\n");
    cli_print(ctx, "  Zone Controller:     active\n");
    cli_print(ctx, "  Rule Controller:     active\n");
    cli_print(ctx, "  Guard Controller:    active\n");
    cli_print(ctx, "  Policy Controller:   active\n");
    cli_print(ctx, "  HA Controller:       %s\n", ctx->ha_enabled ? "active" : "standby");
    cli_print(ctx, "\n");
}

/* show environment */
static void cmd_show_environment(cli_context_t *ctx, int argc, char **argv)
{
    (void)argc; (void)argv;
    cli_print(ctx, "\nSystem Environment:\n");
    cli_print(ctx, "─────────────────────────────────────────────────────\n");
    cli_print(ctx, "  OS:           %s\n", ctx->os_name);
    cli_print(ctx, "  Kernel:       %s\n", ctx->kernel_version);
    cli_print(ctx, "  CPU Cores:    %d\n", ctx->cpu_cores);
    cli_print(ctx, "  Total RAM:    %lu MB\n", (unsigned long)(ctx->memory_total / 1048576));
    cli_print(ctx, "\n");
}

/* show inventory */
static void cmd_show_inventory(cli_context_t *ctx, int argc, char **argv)
{
    (void)argc; (void)argv;
    cli_print(ctx, "\nShield Inventory:\n");
    cli_print(ctx, "─────────────────────────────────────────────────────\n");
    cli_print(ctx, "  Zones:        %u\n", ctx->zones ? ctx->zones->count : 0);
    cli_print(ctx, "  Rules:        %u\n", ctx->rules ? count_all_rules(ctx->rules) : 0);
    cli_print(ctx, "  Guards:       6 (LLM, RAG, Agent, Tool, MCP, API)\n");
    cli_print(ctx, "  Protocols:    20\n");
    cli_print(ctx, "  Signatures:   %u\n", ctx->signature_count);
    cli_print(ctx, "  Canaries:     %u\n", ctx->canary_count);
    cli_print(ctx, "\n");
}

/* show counters */
static void cmd_show_counters(cli_context_t *ctx, int argc, char **argv)
{
    (void)argc; (void)argv;
    cli_print(ctx, "\nShield Counters:\n");
    cli_print(ctx, "─────────────────────────────────────────────────────\n");
    cli_print(ctx, "  Requests total:     %lu\n", (unsigned long)ctx->counters.requests_total);
    cli_print(ctx, "  Requests allowed:   %lu\n", (unsigned long)ctx->counters.requests_allowed);
    cli_print(ctx, "  Requests blocked:   %lu\n", (unsigned long)ctx->counters.requests_blocked);
    cli_print(ctx, "  Requests logged:    %lu\n", (unsigned long)ctx->counters.requests_logged);
    cli_print(ctx, "  Bytes processed:    %lu\n", (unsigned long)ctx->counters.bytes_processed);
    cli_print(ctx, "  Alerts generated:   %lu\n", (unsigned long)ctx->counters.alerts_generated);
    cli_print(ctx, "\n");
}

/* show debugging */
static void cmd_show_debugging(cli_context_t *ctx, int argc, char **argv)
{
    (void)argc; (void)argv;
    cli_print(ctx, "\nDebug Status:\n");
    cli_print(ctx, "─────────────────────────────────────────────────────\n");
    if (ctx->debug_flags == 0) {
        cli_print(ctx, "  No debugging enabled\n");
    } else {
        if (ctx->debug_flags & DEBUG_SHIELD) cli_print(ctx, "  Shield debugging: ON\n");
        if (ctx->debug_flags & DEBUG_ZONE) cli_print(ctx, "  Zone debugging: ON\n");
        if (ctx->debug_flags & DEBUG_RULE) cli_print(ctx, "  Rule debugging: ON\n");
        if (ctx->debug_flags & DEBUG_GUARD) cli_print(ctx, "  Guard debugging: ON\n");
        if (ctx->debug_flags & DEBUG_PROTOCOL) cli_print(ctx, "  Protocol debugging: ON\n");
        if (ctx->debug_flags & DEBUG_HA) cli_print(ctx, "  HA debugging: ON\n");
    }
    cli_print(ctx, "\n");
}

/* Show command table */
static cli_command_t show_commands[] = {
    {"show running-config", cmd_show_running, CLI_MODE_ANY, "Show running config"},
    {"show startup-config", cmd_show_startup, CLI_MODE_ANY, "Show startup config"},
    {"show interfaces", cmd_show_interfaces, CLI_MODE_ANY, "Show interfaces"},
    {"show ip route", cmd_show_ip_route, CLI_MODE_ANY, "Show routing table"},
    {"show users", cmd_show_users, CLI_MODE_ANY, "Show active users"},
    {"show clock", cmd_show_clock, CLI_MODE_ANY, "Show system clock"},
    {"show uptime", cmd_show_uptime, CLI_MODE_ANY, "Show uptime"},
    {"show memory", cmd_show_memory, CLI_MODE_ANY, "Show memory statistics"},
    {"show cpu", cmd_show_cpu, CLI_MODE_ANY, "Show CPU utilization"},
    {"show processes", cmd_show_processes, CLI_MODE_ANY, "Show processes"},
    {"show tech-support", cmd_show_tech_support, CLI_MODE_ANY, "Show tech support info"},
    {"show access-lists", cmd_show_access_lists, CLI_MODE_ANY, "Show access lists"},
    {"show logging", cmd_show_logging, CLI_MODE_ANY, "Show logging status"},
    {"show history", cmd_show_history, CLI_MODE_ANY, "Show command history"},
    {"show controllers", cmd_show_controllers, CLI_MODE_ANY, "Show controllers"},
    {"show environment", cmd_show_environment, CLI_MODE_ANY, "Show environment"},
    {"show inventory", cmd_show_inventory, CLI_MODE_ANY, "Show inventory"},
    {"show counters", cmd_show_counters, CLI_MODE_ANY, "Show counters"},
    {"show debugging", cmd_show_debugging, CLI_MODE_ANY, "Show debug status"},
    {NULL, NULL, 0, NULL}
};

/* Register show commands */
void register_show_commands(cli_context_t *ctx)
{
    for (int i = 0; show_commands[i].name != NULL; i++) {
        cli_register_command(ctx, &show_commands[i]);
    }
}
