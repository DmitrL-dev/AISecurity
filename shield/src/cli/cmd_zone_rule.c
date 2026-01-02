/*
 * SENTINEL Shield - Zone & Rule Commands
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "shield_common.h"
#include "shield_cli.h"
#include "shield_zone.h"
#include "shield_rule.h"

/* zone <name> */
static void cmd_zone(cli_context_t *ctx, int argc, char **argv)
{
    if (argc < 2) {
        cli_print(ctx, "%% Usage: zone <name>\n");
        return;
    }
    
    const char *name = argv[1];
    shield_zone_t *zone = zone_find_by_name(ctx->zones, name);
    
    if (!zone) {
        zone_create(ctx->zones, name, ZONE_TYPE_UNKNOWN, &zone);
        ctx->modified = true;
    }
    
    strncpy(ctx->current_zone, name, sizeof(ctx->current_zone) - 1);
    cli_set_mode(ctx, CLI_MODE_ZONE);
}

/* no zone <name> */
static void cmd_no_zone(cli_context_t *ctx, int argc, char **argv)
{
    if (argc < 3) {
        cli_print(ctx, "%% Usage: no zone <name>\n");
        return;
    }
    
    zone_delete(ctx->zones, argv[2]);
    cli_print(ctx, "Zone %s deleted\n", argv[2]);
    ctx->modified = true;
}

/* type (zone subcommand) */
static void cmd_zone_type(cli_context_t *ctx, int argc, char **argv)
{
    if (argc < 2) {
        cli_print(ctx, "%% Usage: type <llm|rag|agent|tool|mcp|api>\n");
        return;
    }
    
    shield_zone_t *zone = zone_find_by_name(ctx->zones, ctx->current_zone);
    if (zone) {
        zone->type = zone_type_from_string(argv[1]);
        cli_print(ctx, "Zone type set to %s\n", argv[1]);
        ctx->modified = true;
    }
}

/* provider (zone subcommand) */
static void cmd_zone_provider(cli_context_t *ctx, int argc, char **argv)
{
    if (argc < 2) {
        cli_print(ctx, "%% Usage: provider <name>\n");
        return;
    }
    
    shield_zone_t *zone = zone_find_by_name(ctx->zones, ctx->current_zone);
    if (zone) {
        strncpy(zone->provider, argv[1], sizeof(zone->provider) - 1);
        cli_print(ctx, "Provider set to %s\n", argv[1]);
        ctx->modified = true;
    }
}

/* description (zone subcommand) */
static void cmd_zone_description(cli_context_t *ctx, int argc, char **argv)
{
    if (argc < 2) {
        cli_print(ctx, "%% Usage: description <text>\n");
        return;
    }
    
    shield_zone_t *zone = zone_find_by_name(ctx->zones, ctx->current_zone);
    if (zone) {
        strncpy(zone->description, argv[1], sizeof(zone->description) - 1);
        ctx->modified = true;
    }
}

/* trust-level (zone subcommand) */
static void cmd_zone_trust(cli_context_t *ctx, int argc, char **argv)
{
    if (argc < 2) {
        cli_print(ctx, "%% Usage: trust-level <0-10>\n");
        return;
    }
    
    shield_zone_t *zone = zone_find_by_name(ctx->zones, ctx->current_zone);
    if (zone) {
        zone->trust_level = atoi(argv[1]);
        cli_print(ctx, "Trust level set to %d\n", zone->trust_level);
        ctx->modified = true;
    }
}

/* shutdown (zone subcommand) */
static void cmd_zone_shutdown(cli_context_t *ctx, int argc, char **argv)
{
    (void)argc; (void)argv;
    
    shield_zone_t *zone = zone_find_by_name(ctx->zones, ctx->current_zone);
    if (zone) {
        zone->enabled = false;
        cli_print(ctx, "Zone disabled\n");
        ctx->modified = true;
    }
}

/* no shutdown (zone subcommand) */
static void cmd_zone_no_shutdown(cli_context_t *ctx, int argc, char **argv)
{
    (void)argc; (void)argv;
    
    shield_zone_t *zone = zone_find_by_name(ctx->zones, ctx->current_zone);
    if (zone) {
        zone->enabled = true;
        cli_print(ctx, "Zone enabled\n");
        ctx->modified = true;
    }
}

/* shield-rule <acl#> permit/deny ... */
static void cmd_shield_rule(cli_context_t *ctx, int argc, char **argv)
{
    if (argc < 5) {
        cli_print(ctx, "%% Usage: shield-rule <num> <action> <direction> <zone-type> [match...]\n");
        return;
    }
    
    uint32_t acl_num = 100;  /* Default ACL */
    uint32_t rule_num = atoi(argv[1]);
    rule_action_t action = action_from_string(argv[2]);
    rule_direction_t direction = direction_from_string(argv[3]);
    zone_type_t zone_type = zone_type_from_string(argv[4]);
    
    access_list_t *acl = acl_find(ctx->rules, acl_num);
    if (!acl) {
        acl_create(ctx->rules, acl_num, &acl);
    }
    
    shield_rule_t *rule = NULL;
    shield_err_t err = rule_add(acl, rule_num, action, direction, zone_type, NULL, &rule);
    
    if (err == SHIELD_ERR_EXISTS) {
        cli_print(ctx, "%% Rule %u already exists\n", rule_num);
        return;
    }
    
    /* Add match conditions if provided */
    if (argc >= 6) {
        match_type_t match_type = match_type_from_string(argv[5]);
        const char *pattern = argc >= 7 ? argv[6] : "";
        rule_add_condition(rule, match_type, pattern, 0);
    }
    
    cli_print(ctx, "Rule %u added\n", rule_num);
    ctx->modified = true;
}

/* no shield-rule <num> */
static void cmd_no_shield_rule(cli_context_t *ctx, int argc, char **argv)
{
    if (argc < 3) {
        cli_print(ctx, "%% Usage: no shield-rule <num>\n");
        return;
    }
    
    uint32_t rule_num = atoi(argv[2]);
    access_list_t *acl = acl_find(ctx->rules, 100);
    
    if (acl && rule_delete(acl, rule_num) == SHIELD_OK) {
        cli_print(ctx, "Rule %u deleted\n", rule_num);
        ctx->modified = true;
    } else {
        cli_print(ctx, "%% Rule %u not found\n", rule_num);
    }
}

/* access-list <num> */
static void cmd_access_list(cli_context_t *ctx, int argc, char **argv)
{
    if (argc < 2) {
        cli_print(ctx, "%% Usage: access-list <number>\n");
        return;
    }
    
    uint32_t num = atoi(argv[1]);
    access_list_t *acl = acl_find(ctx->rules, num);
    
    if (!acl) {
        acl_create(ctx->rules, num, &acl);
        cli_print(ctx, "Access list %u created\n", num);
        ctx->modified = true;
    }
    
    ctx->current_acl = num;
}

/* no access-list <num> */
static void cmd_no_access_list(cli_context_t *ctx, int argc, char **argv)
{
    if (argc < 3) {
        cli_print(ctx, "%% Usage: no access-list <number>\n");
        return;
    }
    
    uint32_t num = atoi(argv[2]);
    if (acl_delete(ctx->rules, num) == SHIELD_OK) {
        cli_print(ctx, "Access list %u deleted\n", num);
        ctx->modified = true;
    }
}

/* apply zone <name> in <acl> out <acl> */
static void cmd_apply_zone(cli_context_t *ctx, int argc, char **argv)
{
    if (argc < 4) {
        cli_print(ctx, "%% Usage: apply zone <name> in <acl> [out <acl>]\n");
        return;
    }
    
    const char *zone_name = argv[2];
    shield_zone_t *zone = zone_find_by_name(ctx->zones, zone_name);
    
    if (!zone) {
        cli_print(ctx, "%% Zone %s not found\n", zone_name);
        return;
    }
    
    for (int i = 3; i < argc - 1; i += 2) {
        if (strcmp(argv[i], "in") == 0) {
            zone->in_acl = atoi(argv[i + 1]);
        } else if (strcmp(argv[i], "out") == 0) {
            zone->out_acl = atoi(argv[i + 1]);
        }
    }
    
    cli_print(ctx, "Applied to zone %s: in=%u, out=%u\n", 
             zone_name, zone->in_acl, zone->out_acl);
    ctx->modified = true;
}

/* Zone/Rule command table */
static cli_command_t zone_rule_commands[] = {
    /* Config mode */
    {"zone", cmd_zone, CLI_MODE_CONFIG, "Configure zone"},
    {"no zone", cmd_no_zone, CLI_MODE_CONFIG, "Delete zone"},
    {"shield-rule", cmd_shield_rule, CLI_MODE_CONFIG, "Add shield rule"},
    {"no shield-rule", cmd_no_shield_rule, CLI_MODE_CONFIG, "Delete rule"},
    {"access-list", cmd_access_list, CLI_MODE_CONFIG, "Configure ACL"},
    {"no access-list", cmd_no_access_list, CLI_MODE_CONFIG, "Delete ACL"},
    {"apply zone", cmd_apply_zone, CLI_MODE_CONFIG, "Apply ACL to zone"},
    
    /* Zone submode */
    {"type", cmd_zone_type, CLI_MODE_ZONE, "Set zone type"},
    {"provider", cmd_zone_provider, CLI_MODE_ZONE, "Set provider"},
    {"description", cmd_zone_description, CLI_MODE_ZONE, "Set description"},
    {"trust-level", cmd_zone_trust, CLI_MODE_ZONE, "Set trust level"},
    {"shutdown", cmd_zone_shutdown, CLI_MODE_ZONE, "Disable zone"},
    {"no shutdown", cmd_zone_no_shutdown, CLI_MODE_ZONE, "Enable zone"},
    
    {NULL, NULL, 0, NULL}
};

void register_zone_rule_commands(cli_context_t *ctx)
{
    for (int i = 0; zone_rule_commands[i].name != NULL; i++) {
        cli_register_command(ctx, &zone_rule_commands[i]);
    }
}
