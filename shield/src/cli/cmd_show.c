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
#include "shield_zone.h"
#include "shield_rule.h"

/* Forward declarations for local helper functions */
static const char* show_format_timestamp(time_t t);
static const char* show_log_level_str(log_level_t level);
static const char* show_zone_type(zone_type_t type);
static const char* show_action_str(rule_action_t action);
static const char* show_direction_str(rule_direction_t dir);
static const char* show_match_type(match_type_t type);
static uint32_t show_count_all_rules(rule_engine_t *rules);

/* Local helper implementations */
static const char* show_format_timestamp(time_t t) {
    static char buf[32];
    struct tm *tm = localtime(&t);
    strftime(buf, sizeof(buf), "%Y-%m-%d %H:%M:%S", tm);
    return buf;
}

static const char* show_log_level_str(log_level_t level) {
    switch(level) {
        case LOG_NONE: return "none";
        case LOG_ERROR: return "error";
        case LOG_WARN: return "warning";
        case LOG_INFO: return "info";
        case LOG_DEBUG: return "debug";
        case LOG_TRACE: return "trace";
        default: return "unknown";
    }
}

static const char* show_zone_type(zone_type_t type) {
    switch(type) {
        case ZONE_TYPE_LLM: return "llm";
        case ZONE_TYPE_RAG: return "rag";
        case ZONE_TYPE_AGENT: return "agent";
        case ZONE_TYPE_TOOL: return "tool";
        case ZONE_TYPE_MCP: return "mcp";
        default: return "unknown";
    }
}

static const char* show_action_str(rule_action_t action) {
    switch(action) {
        case ACTION_ALLOW: return "permit";
        case ACTION_BLOCK: return "deny";
        case ACTION_LOG: return "log";
        case ACTION_QUARANTINE: return "quarantine";
        default: return "unknown";
    }
}

static const char* show_direction_str(rule_direction_t dir) {
    switch(dir) {
        case DIRECTION_INPUT: return "input";
        case DIRECTION_OUTPUT: return "output";
        case DIRECTION_BOTH: return "any";
        default: return "unknown";
    }
}

static const char* show_match_type(match_type_t type) {
    switch(type) {
        case MATCH_PATTERN: return "pattern";
        case MATCH_PROMPT_INJECTION: return "injection";
        case MATCH_JAILBREAK: return "jailbreak";
        case MATCH_DATA_EXFIL: return "exfiltration";
        default: return "any";
    }
}

static uint32_t show_count_all_rules(rule_engine_t *rules) {
    if (!rules) return 0;
    uint32_t count = 0;
    access_list_t *acl = rules->lists;
    while (acl) {
        count += acl->rule_count;
        acl = acl->next;
    }
    return count;
}

/* show running-config */
static void cmd_show_running(cli_context_t *ctx, int argc, char **argv)
{
    (void)argc; (void)argv;
    cli_print("!\n");
    cli_print("! SENTINEL Shield Configuration\n");
    cli_print("! Generated: %s\n", show_format_timestamp(time(NULL)));
    cli_print("!\n");
    cli_print("hostname %s\n", ctx->hostname);
    cli_print("!\n");
    
    /* Show zones */
    if (ctx->zones) {
        shield_zone_t *zone = ctx->zones->zones;
        while (zone) {
            cli_print("zone %s\n", zone->name);
            cli_print("  type %s\n", show_zone_type(zone->type));
            if (zone->provider[0]) cli_print("  provider %s\n", zone->provider);
            if (!zone->enabled) cli_print("  shutdown\n");
            cli_print("!\n");
            zone = zone->next;
        }
    }
    
    cli_print("end\n");
}

/* show startup-config */
static void cmd_show_startup(cli_context_t *ctx, int argc, char **argv)
{
    (void)ctx; (void)argc; (void)argv;
    cli_print("Startup configuration from NVRAM:\n\n");
    FILE *f = fopen("/etc/shield/startup-config", "r");
    if (f) {
        char line[256];
        while (fgets(line, sizeof(line), f)) {
            cli_print("%s", line);
        }
        fclose(f);
    } else {
        cli_print("%% No startup configuration found\n");
    }
}

/* show interfaces */
static void cmd_show_interfaces(cli_context_t *ctx, int argc, char **argv)
{
    (void)ctx; (void)argc; (void)argv;
    cli_print("\nInterface Status:\n");
    cli_print("─────────────────────────────────────────────────────\n");
    cli_print("%-12s %-10s %-15s %-10s\n", "Interface", "Status", "IP Address", "MTU");
    cli_print("%-12s %-10s %-15s %-10d\n", "api0", "up", "0.0.0.0:8080", 1500);
    cli_print("%-12s %-10s %-15s %-10d\n", "metrics0", "up", "0.0.0.0:9090", 1500);
    cli_print("\n");
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
    
    cli_print("Shield uptime is %lu day(s), %lu hour(s), %lu minute(s), %lu second(s)\n",
             (unsigned long)days, (unsigned long)hours, 
             (unsigned long)mins, (unsigned long)secs);
}

/* show memory */
static void cmd_show_memory(cli_context_t *ctx, int argc, char **argv)
{
    (void)argc; (void)argv;
    cli_print("\nMemory Statistics:\n");
    cli_print("─────────────────────────────────────────────────────\n");
    if (ctx->memory_total > 0) {
        cli_print("  Total:     %lu MB\n", (unsigned long)(ctx->memory_total / 1048576));
        cli_print("  Used:      %lu MB (%.1f%%)\n", 
                 (unsigned long)(ctx->memory_used / 1048576),
                 100.0 * ctx->memory_used / ctx->memory_total);
        cli_print("  Free:      %lu MB\n", 
                 (unsigned long)((ctx->memory_total - ctx->memory_used) / 1048576));
    } else {
        cli_print("  Not available\n");
    }
    cli_print("\n");
}

/* show cpu */
static void cmd_show_cpu(cli_context_t *ctx, int argc, char **argv)
{
    (void)argc; (void)argv;
    cli_print("\nCPU Utilization:\n");
    cli_print("─────────────────────────────────────────────────────\n");
    cli_print("  1 minute:  %.1f%%\n", ctx->cpu_1min);
    cli_print("  5 minute:  %.1f%%\n", ctx->cpu_5min);
    cli_print("  15 minute: %.1f%%\n", ctx->cpu_15min);
    cli_print("\n");
}

/* show clock */
static void cmd_show_clock(cli_context_t *ctx, int argc, char **argv)
{
    (void)ctx; (void)argc; (void)argv;
    time_t now = time(NULL);
    struct tm *tm = localtime(&now);
    char buf[64];
    strftime(buf, sizeof(buf), "%H:%M:%S.000 %Z %a %b %d %Y", tm);
    cli_print("%s\n", buf);
}

/* show logging */
static void cmd_show_logging(cli_context_t *ctx, int argc, char **argv)
{
    (void)argc; (void)argv;
    cli_print("\nLogging Configuration:\n");
    cli_print("─────────────────────────────────────────────────────\n");
    cli_print("  Level:        %s\n", show_log_level_str(ctx->log_level));
    cli_print("  Console:      %s\n", ctx->logging_console ? "enabled" : "disabled");
    cli_print("  Buffer size:  %u\n", ctx->logging_buffered_size);
    cli_print("  Log count:    %lu\n", (unsigned long)ctx->log_count);
    cli_print("\n");
}

/* show history */
static void cmd_show_history(cli_context_t *ctx, int argc, char **argv)
{
    (void)argc; (void)argv;
    cli_print("\nCommand history:\n");
    for (int i = 0; i < ctx->cli.history_count && i < 20; i++) {
        if (ctx->cli.history[i]) {
            cli_print("  %3d  %s\n", i + 1, ctx->cli.history[i]);
        }
    }
}

/* show controllers */
static void cmd_show_controllers(cli_context_t *ctx, int argc, char **argv)
{
    (void)argc; (void)argv;
    cli_print("\nShield Controllers:\n");
    cli_print("─────────────────────────────────────────────────────\n");
    cli_print("  Zone Controller:     active\n");
    cli_print("  Rule Controller:     active\n");
    cli_print("  Guard Controller:    active\n");
    cli_print("  Policy Controller:   active\n");
    cli_print("  HA Controller:       %s\n", ctx->ha.enabled ? "active" : "standby");
    cli_print("\n");
}

/* show environment */
static void cmd_show_environment(cli_context_t *ctx, int argc, char **argv)
{
    (void)argc; (void)argv;
    cli_print("\nSystem Environment:\n");
    cli_print("─────────────────────────────────────────────────────\n");
    cli_print("  OS:           %s\n", ctx->os_name[0] ? ctx->os_name : "Linux");
    cli_print("  Kernel:       %s\n", ctx->kernel_version[0] ? ctx->kernel_version : "unknown");
    cli_print("  CPU Cores:    %d\n", ctx->cpu_cores > 0 ? ctx->cpu_cores : 4);
    cli_print("  Total RAM:    %lu MB\n", (unsigned long)(ctx->memory_total / 1048576));
    cli_print("\n");
}

/* show inventory */
static void cmd_show_inventory(cli_context_t *ctx, int argc, char **argv)
{
    (void)argc; (void)argv;
    cli_print("\nShield Inventory:\n");
    cli_print("─────────────────────────────────────────────────────\n");
    cli_print("  Zones:        %u\n", ctx->zones ? ctx->zones->count : 0);
    cli_print("  Rules:        %u\n", ctx->rules ? show_count_all_rules(ctx->rules) : 0);
    cli_print("  Guards:       6 (LLM, RAG, Agent, Tool, MCP, API)\n");
    cli_print("  Protocols:    20\n");
    cli_print("  Signatures:   %u\n", ctx->signature_count);
    cli_print("  Canaries:     %u\n", ctx->canary_count);
    cli_print("\n");
}

/* show counters */
static void cmd_show_counters(cli_context_t *ctx, int argc, char **argv)
{
    (void)argc; (void)argv;
    cli_print("\nShield Counters:\n");
    cli_print("─────────────────────────────────────────────────────\n");
    cli_print("  Requests total:     %lu\n", (unsigned long)ctx->total_requests);
    cli_print("  Requests allowed:   %lu\n", (unsigned long)ctx->allowed_requests);
    cli_print("  Requests blocked:   %lu\n", (unsigned long)ctx->blocked_requests);
    cli_print("\n");
}

/* show debugging */
static void cmd_show_debugging(cli_context_t *ctx, int argc, char **argv)
{
    (void)argc; (void)argv;
    cli_print("\nDebug Status:\n");
    cli_print("─────────────────────────────────────────────────────\n");
    if (ctx->debug_flags == 0) {
        cli_print("  No debugging enabled\n");
    } else {
        if (ctx->debug_flags & DEBUG_SHIELD) cli_print("  Shield debugging: ON\n");
        if (ctx->debug_flags & DEBUG_ZONE) cli_print("  Zone debugging: ON\n");
        if (ctx->debug_flags & DEBUG_RULE) cli_print("  Rule debugging: ON\n");
        if (ctx->debug_flags & DEBUG_GUARD) cli_print("  Guard debugging: ON\n");
        if (ctx->debug_flags & DEBUG_PROTOCOL) cli_print("  Protocol debugging: ON\n");
        if (ctx->debug_flags & DEBUG_HA) cli_print("  HA debugging: ON\n");
    }
    cli_print("\n");
}

/* show users */
static void cmd_show_users(cli_context_t *ctx, int argc, char **argv)
{
    (void)ctx; (void)argc; (void)argv;
    cli_print("\nActive Users:\n");
    cli_print("─────────────────────────────────────────────────────\n");
    cli_print("%-15s %-20s %-15s\n", "Username", "From", "Idle");
    cli_print("%-15s %-20s %-15s\n", "admin", "console", "00:00:00");
}

/* show ip route */
static void cmd_show_ip_route(cli_context_t *ctx, int argc, char **argv)
{
    (void)ctx; (void)argc; (void)argv;
    cli_print("\nRouting Table (zones):\n");
    cli_print("─────────────────────────────────────────────────────\n");
    cli_print("%-20s %-20s %-10s\n", "Zone", "Next Hop", "Metric");
}

/* show processes */
static void cmd_show_processes(cli_context_t *ctx, int argc, char **argv)
{
    (void)ctx; (void)argc; (void)argv;
    cli_print("\nShield Processes:\n");
    cli_print("─────────────────────────────────────────────────────\n");
    cli_print("%-8s %-20s %-10s %-10s\n", "PID", "Name", "CPU%", "Memory");
    cli_print("%-8d %-20s %-10.1f %-10lu\n", 1, "shield-main", 2.5, 50000UL);
    cli_print("%-8d %-20s %-10.1f %-10lu\n", 2, "shield-worker-1", 5.0, 20000UL);
    cli_print("\n");
}

/* show access-lists */
static void cmd_show_access_lists(cli_context_t *ctx, int argc, char **argv)
{
    (void)argc; (void)argv;
    
    if (!ctx->rules || ctx->rules->list_count == 0) {
        cli_print("No access lists configured.\n");
        return;
    }
    
    access_list_t *acl = ctx->rules->lists;
    while (acl) {
        cli_print("\nshield-rule %u (%u entries):\n", acl->number, acl->rule_count);
        
        shield_rule_t *rule = acl->rules;
        while (rule) {
            cli_print("  %5u %s %s zone %s", 
                     rule->number,
                     show_action_str(rule->action),
                     show_direction_str(rule->direction),
                     show_zone_type(rule->zone_type));
            
            if (rule->conditions) {
                cli_print(" match %s", show_match_type(rule->conditions->type));
            }
            
            cli_print(" (%lu matches)\n", (unsigned long)rule->matches);
            rule = rule->next;
        }
        
        acl = acl->next;
    }
}

/* show tech-support (aggregate) */
static void cmd_show_tech_support(cli_context_t *ctx, int argc, char **argv)
{
    (void)argc; (void)argv;
    cli_print("\n========== SENTINEL SHIELD TECH-SUPPORT ==========\n\n");
    
    cmd_show_version(ctx, 0, NULL);
    cmd_show_uptime(ctx, 0, NULL);
    cmd_show_memory(ctx, 0, NULL);
    cmd_show_cpu(ctx, 0, NULL);
    cmd_show_interfaces(ctx, 0, NULL);
    cmd_show_zones(ctx, 0, NULL);
    cmd_show_rules(ctx, 0, NULL);
    cmd_show_stats(ctx, 0, NULL);
    
    cli_print("\n========== END TECH-SUPPORT ==========\n");
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
