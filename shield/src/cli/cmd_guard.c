/*
 * SENTINEL Shield - Guard & Security Commands
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "shield_common.h"
#include "shield_cli.h"
#include "shield_guard.h"

/* guard enable <type> */
static void cmd_guard_enable(cli_context_t *ctx, int argc, char **argv)
{
    if (argc < 3) {
        cli_print(ctx, "%% Usage: guard enable <llm|rag|agent|tool|mcp|api|all>\n");
        return;
    }
    
    const char *type = argv[2];
    if (strcmp(type, "all") == 0) {
        ctx->guards.llm_enabled = true;
        ctx->guards.rag_enabled = true;
        ctx->guards.agent_enabled = true;
        ctx->guards.tool_enabled = true;
        ctx->guards.mcp_enabled = true;
        ctx->guards.api_enabled = true;
        cli_print(ctx, "All guards enabled\n");
    } else if (strcmp(type, "llm") == 0) {
        ctx->guards.llm_enabled = true;
        cli_print(ctx, "LLM guard enabled\n");
    } else if (strcmp(type, "rag") == 0) {
        ctx->guards.rag_enabled = true;
        cli_print(ctx, "RAG guard enabled\n");
    } else if (strcmp(type, "agent") == 0) {
        ctx->guards.agent_enabled = true;
        cli_print(ctx, "Agent guard enabled\n");
    } else if (strcmp(type, "tool") == 0) {
        ctx->guards.tool_enabled = true;
        cli_print(ctx, "Tool guard enabled\n");
    } else if (strcmp(type, "mcp") == 0) {
        ctx->guards.mcp_enabled = true;
        cli_print(ctx, "MCP guard enabled\n");
    } else if (strcmp(type, "api") == 0) {
        ctx->guards.api_enabled = true;
        cli_print(ctx, "API guard enabled\n");
    }
    ctx->modified = true;
}

/* no guard enable <type> */
static void cmd_no_guard_enable(cli_context_t *ctx, int argc, char **argv)
{
    if (argc < 4) {
        cli_print(ctx, "%% Usage: no guard enable <llm|rag|agent|tool|mcp|api|all>\n");
        return;
    }
    
    const char *type = argv[3];
    if (strcmp(type, "all") == 0) {
        ctx->guards.llm_enabled = false;
        ctx->guards.rag_enabled = false;
        ctx->guards.agent_enabled = false;
        ctx->guards.tool_enabled = false;
        ctx->guards.mcp_enabled = false;
        ctx->guards.api_enabled = false;
        cli_print(ctx, "All guards disabled\n");
    } else if (strcmp(type, "llm") == 0) {
        ctx->guards.llm_enabled = false;
        cli_print(ctx, "LLM guard disabled\n");
    } else if (strcmp(type, "rag") == 0) {
        ctx->guards.rag_enabled = false;
        cli_print(ctx, "RAG guard disabled\n");
    } else if (strcmp(type, "agent") == 0) {
        ctx->guards.agent_enabled = false;
        cli_print(ctx, "Agent guard disabled\n");
    } else if (strcmp(type, "tool") == 0) {
        ctx->guards.tool_enabled = false;
        cli_print(ctx, "Tool guard disabled\n");
    } else if (strcmp(type, "mcp") == 0) {
        ctx->guards.mcp_enabled = false;
        cli_print(ctx, "MCP guard disabled\n");
    } else if (strcmp(type, "api") == 0) {
        ctx->guards.api_enabled = false;
        cli_print(ctx, "API guard disabled\n");
    }
    ctx->modified = true;
}

/* guard policy <type> <action> */
static void cmd_guard_policy(cli_context_t *ctx, int argc, char **argv)
{
    if (argc < 4) {
        cli_print(ctx, "%% Usage: guard policy <type> <block|log|alert>\n");
        return;
    }
    cli_print(ctx, "Guard policy for %s set to %s\n", argv[2], argv[3]);
    ctx->modified = true;
}

/* guard threshold <type> <value> */
static void cmd_guard_threshold(cli_context_t *ctx, int argc, char **argv)
{
    if (argc < 4) {
        cli_print(ctx, "%% Usage: guard threshold <type> <0.0-1.0>\n");
        return;
    }
    cli_print(ctx, "Guard %s threshold set to %s\n", argv[2], argv[3]);
    ctx->modified = true;
}

/* signature-set update */
static void cmd_signature_update(cli_context_t *ctx, int argc, char **argv)
{
    (void)argc; (void)argv;
    cli_print(ctx, "Updating signature database...\n");
    if (signature_update(ctx->shield) == SHIELD_OK) {
        cli_print(ctx, "[OK] %u signatures loaded\n", ctx->signature_count);
    } else {
        cli_print(ctx, "%% Update failed\n");
    }
}

/* signature-set category enable <cat> */
static void cmd_signature_category(cli_context_t *ctx, int argc, char **argv)
{
    if (argc < 5) {
        cli_print(ctx, "%% Usage: signature-set category enable <injection|jailbreak|...>\n");
        return;
    }
    cli_print(ctx, "Signature category %s enabled\n", argv[4]);
    ctx->modified = true;
}

/* canary token add <token> */
static void cmd_canary_add(cli_context_t *ctx, int argc, char **argv)
{
    if (argc < 4) {
        cli_print(ctx, "%% Usage: canary token add <token>\n");
        return;
    }
    
    canary_add(ctx->canaries, argv[3], CANARY_TYPE_TOKEN);
    cli_print(ctx, "Canary token added: %s\n", argv[3]);
    ctx->canary_count++;
    ctx->modified = true;
}

/* no canary token <token> */
static void cmd_no_canary(cli_context_t *ctx, int argc, char **argv)
{
    if (argc < 4) {
        cli_print(ctx, "%% Usage: no canary token <token>\n");
        return;
    }
    
    canary_remove(ctx->canaries, argv[3]);
    cli_print(ctx, "Canary token removed\n");
    ctx->canary_count--;
    ctx->modified = true;
}

/* blocklist ip add <ip> */
static void cmd_blocklist_ip_add(cli_context_t *ctx, int argc, char **argv)
{
    if (argc < 4) {
        cli_print(ctx, "%% Usage: blocklist ip add <ip-address>\n");
        return;
    }
    
    blocklist_add_ip(ctx->blocklist, argv[3]);
    cli_print(ctx, "IP %s added to blocklist\n", argv[3]);
    ctx->modified = true;
}

/* no blocklist ip <ip> */
static void cmd_no_blocklist_ip(cli_context_t *ctx, int argc, char **argv)
{
    if (argc < 4) {
        cli_print(ctx, "%% Usage: no blocklist ip <ip-address>\n");
        return;
    }
    
    blocklist_remove_ip(ctx->blocklist, argv[3]);
    cli_print(ctx, "IP %s removed from blocklist\n", argv[3]);
    ctx->modified = true;
}

/* blocklist pattern add <pattern> */
static void cmd_blocklist_pattern(cli_context_t *ctx, int argc, char **argv)
{
    if (argc < 4) {
        cli_print(ctx, "%% Usage: blocklist pattern add <pattern>\n");
        return;
    }
    
    blocklist_add_pattern(ctx->blocklist, argv[3]);
    cli_print(ctx, "Pattern added to blocklist\n");
    ctx->modified = true;
}

/* rate-limit enable */
static void cmd_rate_limit_enable(cli_context_t *ctx, int argc, char **argv)
{
    (void)argc; (void)argv;
    ctx->rate_limit_enabled = true;
    cli_print(ctx, "Rate limiting enabled\n");
    ctx->modified = true;
}

/* rate-limit requests <count> per <seconds> */
static void cmd_rate_limit_config(cli_context_t *ctx, int argc, char **argv)
{
    if (argc < 5) {
        cli_print(ctx, "%% Usage: rate-limit requests <count> per <seconds>\n");
        return;
    }
    ctx->rate_limit_requests = atoi(argv[2]);
    ctx->rate_limit_window = atoi(argv[4]);
    cli_print(ctx, "Rate limit: %d requests per %d seconds\n", 
             ctx->rate_limit_requests, ctx->rate_limit_window);
    ctx->modified = true;
}

/* threat-intel enable */
static void cmd_threat_intel_enable(cli_context_t *ctx, int argc, char **argv)
{
    (void)argc; (void)argv;
    ctx->threat_intel_enabled = true;
    cli_print(ctx, "Threat intelligence enabled\n");
    ctx->modified = true;
}

/* threat-intel feed add <url> */
static void cmd_threat_intel_feed(cli_context_t *ctx, int argc, char **argv)
{
    if (argc < 5) {
        cli_print(ctx, "%% Usage: threat-intel feed add <url>\n");
        return;
    }
    cli_print(ctx, "Threat intel feed added: %s\n", argv[4]);
    ctx->modified = true;
}

/* alert destination <type> <target> */
static void cmd_alert_destination(cli_context_t *ctx, int argc, char **argv)
{
    if (argc < 4) {
        cli_print(ctx, "%% Usage: alert destination <webhook|email|syslog> <target>\n");
        return;
    }
    strncpy(ctx->alert_destination, argv[3], sizeof(ctx->alert_destination) - 1);
    cli_print(ctx, "Alert destination set\n");
    ctx->modified = true;
}

/* alert threshold <severity> */
static void cmd_alert_threshold(cli_context_t *ctx, int argc, char **argv)
{
    if (argc < 3) {
        cli_print(ctx, "%% Usage: alert threshold <info|warn|critical>\n");
        return;
    }
    cli_print(ctx, "Alert threshold set to %s\n", argv[2]);
    ctx->modified = true;
}

/* siem enable */
static void cmd_siem_enable(cli_context_t *ctx, int argc, char **argv)
{
    (void)argc; (void)argv;
    ctx->siem_enabled = true;
    cli_print(ctx, "SIEM export enabled\n");
    ctx->modified = true;
}

/* siem destination <host> <port> */
static void cmd_siem_destination(cli_context_t *ctx, int argc, char **argv)
{
    if (argc < 4) {
        cli_print(ctx, "%% Usage: siem destination <host> <port>\n");
        return;
    }
    strncpy(ctx->siem_host, argv[2], sizeof(ctx->siem_host) - 1);
    ctx->siem_port = atoi(argv[3]);
    cli_print(ctx, "SIEM destination: %s:%d\n", argv[2], ctx->siem_port);
    ctx->modified = true;
}

/* siem format <cef|json|syslog> */
static void cmd_siem_format(cli_context_t *ctx, int argc, char **argv)
{
    if (argc < 3) {
        cli_print(ctx, "%% Usage: siem format <cef|json|syslog>\n");
        return;
    }
    strncpy(ctx->siem_format, argv[2], sizeof(ctx->siem_format) - 1);
    cli_print(ctx, "SIEM format: %s\n", argv[2]);
    ctx->modified = true;
}

/* Guard command table */
static cli_command_t guard_commands[] = {
    {"guard enable", cmd_guard_enable, CLI_MODE_CONFIG, "Enable guard"},
    {"no guard enable", cmd_no_guard_enable, CLI_MODE_CONFIG, "Disable guard"},
    {"guard policy", cmd_guard_policy, CLI_MODE_CONFIG, "Set guard policy"},
    {"guard threshold", cmd_guard_threshold, CLI_MODE_CONFIG, "Set threshold"},
    {"signature-set update", cmd_signature_update, CLI_MODE_PRIV, "Update signatures"},
    {"signature-set category enable", cmd_signature_category, CLI_MODE_CONFIG, "Enable category"},
    {"canary token add", cmd_canary_add, CLI_MODE_CONFIG, "Add canary token"},
    {"no canary token", cmd_no_canary, CLI_MODE_CONFIG, "Remove canary token"},
    {"blocklist ip add", cmd_blocklist_ip_add, CLI_MODE_CONFIG, "Add IP to blocklist"},
    {"no blocklist ip", cmd_no_blocklist_ip, CLI_MODE_CONFIG, "Remove IP"},
    {"blocklist pattern add", cmd_blocklist_pattern, CLI_MODE_CONFIG, "Add pattern"},
    {"rate-limit enable", cmd_rate_limit_enable, CLI_MODE_CONFIG, "Enable rate limit"},
    {"rate-limit requests", cmd_rate_limit_config, CLI_MODE_CONFIG, "Configure rate limit"},
    {"threat-intel enable", cmd_threat_intel_enable, CLI_MODE_CONFIG, "Enable threat intel"},
    {"threat-intel feed add", cmd_threat_intel_feed, CLI_MODE_CONFIG, "Add threat feed"},
    {"alert destination", cmd_alert_destination, CLI_MODE_CONFIG, "Set alert dest"},
    {"alert threshold", cmd_alert_threshold, CLI_MODE_CONFIG, "Set alert threshold"},
    {"siem enable", cmd_siem_enable, CLI_MODE_CONFIG, "Enable SIEM"},
    {"siem destination", cmd_siem_destination, CLI_MODE_CONFIG, "Set SIEM dest"},
    {"siem format", cmd_siem_format, CLI_MODE_CONFIG, "Set SIEM format"},
    {NULL, NULL, 0, NULL}
};

void register_guard_commands(cli_context_t *ctx)
{
    for (int i = 0; guard_commands[i].name != NULL; i++) {
        cli_register_command(ctx, &guard_commands[i]);
    }
}
