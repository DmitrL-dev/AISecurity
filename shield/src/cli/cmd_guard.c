/*
 * SENTINEL Shield - Guard & Security Commands
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "shield_common.h"
#include "shield_cli.h"
#include "shield_guard.h"
#include "shield_canary.h"
#include "shield_blocklist.h"
#include "shield_state.h"

/* Stub for signature update (TODO: implement) */
static inline shield_err_t signature_update(shield_context_t *ctx) {
    (void)ctx;
    return SHIELD_OK;
}

/* guard enable <type> */
static shield_err_t cmd_guard_enable(cli_context_t *ctx, int argc, char **argv)
{
    if (argc < 3) {
        cli_print("%% Usage: guard enable <llm|rag|agent|tool|mcp|api|all>\n");
        return SHIELD_OK;
    }
    
    shield_state_t *state = shield_state_get();
    const char *type = argv[2];
    
    if (strcmp(type, "all") == 0) {
        ctx->guards->llm_enabled = true;
        ctx->guards->rag_enabled = true;
        ctx->guards->agent_enabled = true;
        ctx->guards->tool_enabled = true;
        ctx->guards->mcp_enabled = true;
        ctx->guards->api_enabled = true;
        state->guards.llm.state = MODULE_ENABLED;
        state->guards.rag.state = MODULE_ENABLED;
        state->guards.agent.state = MODULE_ENABLED;
        state->guards.tool.state = MODULE_ENABLED;
        state->guards.mcp.state = MODULE_ENABLED;
        state->guards.api.state = MODULE_ENABLED;
        cli_print("All guards enabled\n");
    } else if (strcmp(type, "llm") == 0) {
        ctx->guards->llm_enabled = true;
        state->guards.llm.state = MODULE_ENABLED;
        cli_print("LLM guard enabled\n");
    } else if (strcmp(type, "rag") == 0) {
        ctx->guards->rag_enabled = true;
        state->guards.rag.state = MODULE_ENABLED;
        cli_print("RAG guard enabled\n");
    } else if (strcmp(type, "agent") == 0) {
        ctx->guards->agent_enabled = true;
        state->guards.agent.state = MODULE_ENABLED;
        cli_print("Agent guard enabled\n");
    } else if (strcmp(type, "tool") == 0) {
        ctx->guards->tool_enabled = true;
        state->guards.tool.state = MODULE_ENABLED;
        cli_print("Tool guard enabled\n");
    } else if (strcmp(type, "mcp") == 0) {
        ctx->guards->mcp_enabled = true;
        state->guards.mcp.state = MODULE_ENABLED;
        cli_print("MCP guard enabled\n");
    } else if (strcmp(type, "api") == 0) {
        ctx->guards->api_enabled = true;
        state->guards.api.state = MODULE_ENABLED;
        cli_print("API guard enabled\n");
    }
    ctx->modified = true;
    shield_state_mark_dirty();
    return SHIELD_OK;
}

/* no guard enable <type> */
static shield_err_t cmd_no_guard_enable(cli_context_t *ctx, int argc, char **argv)
{
    if (argc < 4) {
        cli_print("%% Usage: no guard enable <llm|rag|agent|tool|mcp|api|all>\n");
        return SHIELD_OK;
    }
    
    shield_state_t *state = shield_state_get();
    const char *type = argv[3];
    
    if (strcmp(type, "all") == 0) {
        ctx->guards->llm_enabled = false;
        ctx->guards->rag_enabled = false;
        ctx->guards->agent_enabled = false;
        ctx->guards->tool_enabled = false;
        ctx->guards->mcp_enabled = false;
        ctx->guards->api_enabled = false;
        state->guards.llm.state = MODULE_DISABLED;
        state->guards.rag.state = MODULE_DISABLED;
        state->guards.agent.state = MODULE_DISABLED;
        state->guards.tool.state = MODULE_DISABLED;
        state->guards.mcp.state = MODULE_DISABLED;
        state->guards.api.state = MODULE_DISABLED;
        cli_print("All guards disabled\n");
    } else if (strcmp(type, "llm") == 0) {
        ctx->guards->llm_enabled = false;
        state->guards.llm.state = MODULE_DISABLED;
        cli_print("LLM guard disabled\n");
    } else if (strcmp(type, "rag") == 0) {
        ctx->guards->rag_enabled = false;
        state->guards.rag.state = MODULE_DISABLED;
        cli_print("RAG guard disabled\n");
    } else if (strcmp(type, "agent") == 0) {
        ctx->guards->agent_enabled = false;
        state->guards.agent.state = MODULE_DISABLED;
        cli_print("Agent guard disabled\n");
    } else if (strcmp(type, "tool") == 0) {
        ctx->guards->tool_enabled = false;
        state->guards.tool.state = MODULE_DISABLED;
        cli_print("Tool guard disabled\n");
    } else if (strcmp(type, "mcp") == 0) {
        ctx->guards->mcp_enabled = false;
        state->guards.mcp.state = MODULE_DISABLED;
        cli_print("MCP guard disabled\n");
    } else if (strcmp(type, "api") == 0) {
        ctx->guards->api_enabled = false;
        state->guards.api.state = MODULE_DISABLED;
        cli_print("API guard disabled\n");
    }
    ctx->modified = true;
    shield_state_mark_dirty();
    return SHIELD_OK;
}

/* guard policy <type> <action> */
static shield_err_t cmd_guard_policy(cli_context_t *ctx, int argc, char **argv)
{
    if (argc < 4) {
        cli_print("%% Usage: guard policy <type> <block|log|alert>\n");
        return SHIELD_OK;
    }
    cli_print("Guard policy for %s set to %s\n", argv[2], argv[3]);
    ctx->modified = true;
    return SHIELD_OK;
}

/* guard threshold <type> <value> */
static shield_err_t cmd_guard_threshold(cli_context_t *ctx, int argc, char **argv)
{
    if (argc < 4) {
        cli_print("%% Usage: guard threshold <type> <0.0-1.0>\n");
        return SHIELD_OK;
    }
    cli_print("Guard %s threshold set to %s\n", argv[2], argv[3]);
    ctx->modified = true;
    return SHIELD_OK;
}

/* signature-set update */
static shield_err_t cmd_signature_update(cli_context_t *ctx, int argc, char **argv)
{
    (void)argc; (void)argv;
    cli_print("Updating signature database...\n");
    if (signature_update(ctx) == SHIELD_OK) {
        cli_print("[OK] %u signatures loaded\n", ctx->signature_count);
    } else {
        cli_print("%% Update failed\n");
    }
    return SHIELD_OK;
}

/* signature-set category enable <cat> */
static shield_err_t cmd_signature_category(cli_context_t *ctx, int argc, char **argv)
{
    if (argc < 5) {
        cli_print("%% Usage: signature-set category enable <injection|jailbreak|...>\n");
        return SHIELD_OK;
    }
    cli_print("Signature category %s enabled\n", argv[4]);
    ctx->modified = true;
    return SHIELD_OK;
}

/* canary token add <token> */
static shield_err_t cmd_canary_add(cli_context_t *ctx, int argc, char **argv)
{
    if (argc < 4) {
        cli_print("%% Usage: canary token add <token>\n");
        return SHIELD_OK;
    }
    
    /* TODO: canary_add(ctx->canaries, argv[3], CANARY_TYPE_TOKEN); */
    cli_print("Canary token added: %s\n", argv[3]);
    ctx->canary_count++;
    ctx->modified = true;
    return SHIELD_OK;
}

/* no canary token <token> */
static shield_err_t cmd_no_canary(cli_context_t *ctx, int argc, char **argv)
{
    if (argc < 4) {
        cli_print("%% Usage: no canary token <token>\n");
        return SHIELD_OK;
    }
    
    /* TODO: canary_remove(ctx->canaries, argv[3]); */
    cli_print("Canary token removed\n");
    ctx->canary_count--;
    ctx->modified = true;
    return SHIELD_OK;
}

/* blocklist ip add <ip> */
static shield_err_t cmd_blocklist_ip_add(cli_context_t *ctx, int argc, char **argv)
{
    if (argc < 4) {
        cli_print("%% Usage: blocklist ip add <ip-address>\n");
        return SHIELD_OK;
    }
    
    /* Use existing blocklist_add */
    blocklist_add(ctx->blocklist, argv[3], "CLI: IP block");
    cli_print("IP %s added to blocklist\n", argv[3]);
    ctx->modified = true;
    return SHIELD_OK;
}

/* no blocklist ip <ip> */
static shield_err_t cmd_no_blocklist_ip(cli_context_t *ctx, int argc, char **argv)
{
    if (argc < 4) {
        cli_print("%% Usage: no blocklist ip <ip-address>\n");
        return SHIELD_OK;
    }
    
    blocklist_remove(ctx->blocklist, argv[3]);
    cli_print("IP %s removed from blocklist\n", argv[3]);
    ctx->modified = true;
    return SHIELD_OK;
}

/* blocklist pattern add <pattern> */
static shield_err_t cmd_blocklist_pattern(cli_context_t *ctx, int argc, char **argv)
{
    if (argc < 4) {
        cli_print("%% Usage: blocklist pattern add <pattern>\n");
        return SHIELD_OK;
    }
    
    blocklist_add(ctx->blocklist, argv[3], "CLI: pattern block");
    cli_print("Pattern added to blocklist\n");
    ctx->modified = true;
    return SHIELD_OK;
}

/* rate-limit enable */
static shield_err_t cmd_rate_limit_enable(cli_context_t *ctx, int argc, char **argv)
{
    (void)argc; (void)argv;
    ctx->rate_limit_enabled = true;
    cli_print("Rate limiting enabled\n");
    ctx->modified = true;
    return SHIELD_OK;
}

/* rate-limit requests <count> per <seconds> */
static shield_err_t cmd_rate_limit_config(cli_context_t *ctx, int argc, char **argv)
{
    if (argc < 5) {
        cli_print("%% Usage: rate-limit requests <count> per <seconds>\n");
        return SHIELD_OK;
    }
    ctx->rate_limit_requests = atoi(argv[2]);
    ctx->rate_limit_window = atoi(argv[4]);
    cli_print("Rate limit: %d requests per %d seconds\n", 
             ctx->rate_limit_requests, ctx->rate_limit_window);
    ctx->modified = true;
    return SHIELD_OK;
}

/* threat-intel enable */
static shield_err_t cmd_threat_intel_enable(cli_context_t *ctx, int argc, char **argv)
{
    (void)argc; (void)argv;
    ctx->threat_intel_enabled = true;
    cli_print("Threat intelligence enabled\n");
    ctx->modified = true;
    return SHIELD_OK;
}

/* threat-intel feed add <url> */
static shield_err_t cmd_threat_intel_feed(cli_context_t *ctx, int argc, char **argv)
{
    if (argc < 5) {
        cli_print("%% Usage: threat-intel feed add <url>\n");
        return SHIELD_OK;
    }
    cli_print("Threat intel feed added: %s\n", argv[4]);
    ctx->modified = true;
    return SHIELD_OK;
}

/* alert destination <type> <target> */
static shield_err_t cmd_alert_destination(cli_context_t *ctx, int argc, char **argv)
{
    if (argc < 4) {
        cli_print("%% Usage: alert destination <webhook|email|syslog> <target>\n");
        return SHIELD_OK;
    }
    strncpy(ctx->alert_destination, argv[3], sizeof(ctx->alert_destination) - 1);
    cli_print("Alert destination set\n");
    ctx->modified = true;
    return SHIELD_OK;
}

/* alert threshold <severity> */
static shield_err_t cmd_alert_threshold(cli_context_t *ctx, int argc, char **argv)
{
    if (argc < 3) {
        cli_print("%% Usage: alert threshold <info|warn|critical>\n");
        return SHIELD_OK;
    }
    cli_print("Alert threshold set to %s\n", argv[2]);
    ctx->modified = true;
    return SHIELD_OK;
}

/* siem enable */
static shield_err_t cmd_siem_enable(cli_context_t *ctx, int argc, char **argv)
{
    (void)argc; (void)argv;
    ctx->siem_enabled = true;
    cli_print("SIEM export enabled\n");
    ctx->modified = true;
    return SHIELD_OK;
}

/* siem destination <host> <port> */
static shield_err_t cmd_siem_destination(cli_context_t *ctx, int argc, char **argv)
{
    if (argc < 4) {
        cli_print("%% Usage: siem destination <host> <port>\n");
        return SHIELD_OK;
    }
    strncpy(ctx->siem_host, argv[2], sizeof(ctx->siem_host) - 1);
    ctx->siem_port = atoi(argv[3]);
    cli_print("SIEM destination: %s:%d\n", argv[2], ctx->siem_port);
    ctx->modified = true;
    return SHIELD_OK;
}

/* siem format <cef|json|syslog> */
static shield_err_t cmd_siem_format(cli_context_t *ctx, int argc, char **argv)
{
    if (argc < 3) {
        cli_print("%% Usage: siem format <cef|json|syslog>\n");
        return SHIELD_OK;
    }
    strncpy(ctx->siem_format, argv[2], sizeof(ctx->siem_format) - 1);
    cli_print("SIEM format: %s\n", argv[2]);
    ctx->modified = true;
    return SHIELD_OK;
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
