/*
 * SENTINEL Shield - CLI Commands Implementation
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "shield_common.h"
#include "shield_zone.h"
#include "shield_rule.h"
#include "shield_cli.h"

/* enable */
shield_err_t cmd_enable(shield_context_t *ctx, int argc, char **argv)
{
    (void)argc; (void)argv;
    ctx->cli.enable_mode = true;
    cli_update_prompt(ctx);
    return SHIELD_OK;
}

/* disable */
shield_err_t cmd_disable(shield_context_t *ctx, int argc, char **argv)
{
    (void)argc; (void)argv;
    ctx->cli.enable_mode = false;
    cli_update_prompt(ctx);
    return SHIELD_OK;
}

/* config */
shield_err_t cmd_config(shield_context_t *ctx, int argc, char **argv)
{
    (void)argc; (void)argv;
    if (!ctx->cli.enable_mode) {
        cli_print_error("Command not available in user mode");
        return SHIELD_ERR_PERMISSION;
    }
    cli_set_mode(ctx, CLI_MODE_CONFIG);
    return SHIELD_OK;
}

/* exit */
shield_err_t cmd_exit(shield_context_t *ctx, int argc, char **argv)
{
    (void)argc; (void)argv;
    
    switch (ctx->cli.mode) {
    case CLI_MODE_ZONE:
        ctx->cli.current_zone[0] = '\0';
        cli_set_mode(ctx, CLI_MODE_CONFIG);
        break;
    case CLI_MODE_CONFIG:
        cli_set_mode(ctx, CLI_MODE_EXEC);
        break;
    case CLI_MODE_EXEC:
        ctx->running = false;
        break;
    default:
        cli_set_mode(ctx, CLI_MODE_EXEC);
    }
    
    return SHIELD_OK;
}

/* end */
shield_err_t cmd_end(shield_context_t *ctx, int argc, char **argv)
{
    (void)argc; (void)argv;
    ctx->cli.current_zone[0] = '\0';
    cli_set_mode(ctx, CLI_MODE_EXEC);
    return SHIELD_OK;
}

/* help */
shield_err_t cmd_help(shield_context_t *ctx, int argc, char **argv)
{
    (void)argc; (void)argv;
    
    cli_print("\nAvailable commands:\n\n");
    
    if (ctx->cli.mode == CLI_MODE_EXEC) {
        cli_print("  enable         Enter privileged mode\n");
        cli_print("  disable        Exit privileged mode\n");
        cli_print("  config         Enter configuration mode\n");
        cli_print("  show           Show running system information\n");
        cli_print("  exit           Exit the CLI\n");
        cli_print("  help           Show this help\n");
    } else if (ctx->cli.mode == CLI_MODE_CONFIG) {
        cli_print("  zone           Configure a zone\n");
        cli_print("  shield-rule    Add a shield rule\n");
        cli_print("  apply          Apply configuration to zone\n");
        cli_print("  write          Write configuration\n");
        cli_print("  show           Show configuration\n");
        cli_print("  exit           Exit configuration mode\n");
        cli_print("  end            Exit to exec mode\n");
    } else if (ctx->cli.mode == CLI_MODE_ZONE) {
        cli_print("  type           Set zone type\n");
        cli_print("  provider       Set zone provider\n");
        cli_print("  description    Set zone description\n");
        cli_print("  exit           Exit zone configuration\n");
    }
    
    cli_print("\n");
    return SHIELD_OK;
}

/* show */
shield_err_t cmd_show(shield_context_t *ctx, int argc, char **argv)
{
    if (argc < 2) {
        cli_print("show commands:\n");
        cli_print("  show zones     Show configured zones\n");
        cli_print("  show rules     Show shield rules\n");
        cli_print("  show stats     Show statistics\n");
        cli_print("  show config    Show running configuration\n");
        cli_print("  show version   Show version information\n");
        return SHIELD_OK;
    }
    
    const char *what = argv[1];
    
    if (strcmp(what, "zones") == 0) {
        return cmd_show_zones(ctx, argc, argv);
    }
    if (strcmp(what, "rules") == 0) {
        return cmd_show_rules(ctx, argc, argv);
    }
    if (strcmp(what, "stats") == 0) {
        return cmd_show_stats(ctx, argc, argv);
    }
    if (strcmp(what, "config") == 0 || strcmp(what, "running-config") == 0) {
        return cmd_show_config(ctx, argc, argv);
    }
    if (strcmp(what, "version") == 0) {
        return cmd_show_version(ctx, argc, argv);
    }
    
    cli_print_error("Unknown show command: %s", what);
    return SHIELD_ERR_INVALID;
}

/* show zones */
shield_err_t cmd_show_zones(shield_context_t *ctx, int argc, char **argv)
{
    (void)argc; (void)argv;
    
    if (!ctx->zones || ctx->zones->count == 0) {
        cli_print("No zones configured.\n");
        return SHIELD_OK;
    }
    
    const char *columns[] = {"Name", "Type", "Provider", "In-ACL", "Out-ACL", "Status"};
    int widths[] = {20, 10, 15, 8, 8, 8};
    
    cli_print("\n");
    cli_print_table_header(columns, 6, widths);
    
    shield_zone_t *zone = ctx->zones->zones;
    while (zone) {
        char in_acl[16], out_acl[16];
        snprintf(in_acl, sizeof(in_acl), "%u", zone->in_acl);
        snprintf(out_acl, sizeof(out_acl), "%u", zone->out_acl);
        
        const char *values[] = {
            zone->name,
            zone_type_to_string(zone->type),
            zone->provider[0] ? zone->provider : "-",
            zone->in_acl ? in_acl : "-",
            zone->out_acl ? out_acl : "-",
            zone->enabled ? "active" : "disabled"
        };
        
        cli_print_table_row(values, 6, widths);
        zone = zone->next;
    }
    
    cli_print("\nTotal: %u zone(s)\n\n", ctx->zones->count);
    return SHIELD_OK;
}

/* show rules */
shield_err_t cmd_show_rules(shield_context_t *ctx, int argc, char **argv)
{
    uint32_t acl_num = 0;
    if (argc >= 3) {
        acl_num = atoi(argv[2]);
    }
    
    if (!ctx->rules || ctx->rules->list_count == 0) {
        cli_print("No rules configured.\n");
        return SHIELD_OK;
    }
    
    access_list_t *acl = ctx->rules->lists;
    while (acl) {
        if (acl_num != 0 && acl->number != acl_num) {
            acl = acl->next;
            continue;
        }
        
        cli_print("\nshield-rule %u:\n", acl->number);
        
        shield_rule_t *rule = acl->rules;
        while (rule) {
            cli_print("  %5u %s %s %s",
                     rule->number,
                     action_to_string(rule->action),
                     direction_to_string(rule->direction),
                     zone_type_to_string(rule->zone_type));
            
            if (rule->conditions) {
                match_condition_t *cond = rule->conditions;
                cli_print(" %s", match_type_to_string(cond->type));
                if (cond->pattern[0]) {
                    cli_print(" \"%s\"", cond->pattern);
                }
            }
            
            cli_print(" (%lu matches)\n", (unsigned long)rule->matches);
            rule = rule->next;
        }
        
        acl = acl->next;
    }
    
    cli_print("\n");
    return SHIELD_OK;
}

/* show stats */
shield_err_t cmd_show_stats(shield_context_t *ctx, int argc, char **argv)
{
    (void)argc; (void)argv;
    
    uint64_t total_in = 0, total_out = 0;
    uint64_t blocked_in = 0, blocked_out = 0;
    
    if (ctx->zones) {
        shield_zone_t *zone = ctx->zones->zones;
        while (zone) {
            total_in += zone->requests_in;
            total_out += zone->requests_out;
            blocked_in += zone->blocked_in;
            blocked_out += zone->blocked_out;
            zone = zone->next;
        }
    }
    
    uint64_t total = total_in + total_out;
    uint64_t blocked = blocked_in + blocked_out;
    
    cli_print("\nShield Statistics:\n");
    cli_print("------------------\n");
    cli_print("Total requests:     %lu\n", (unsigned long)total);
    cli_print("  Input:            %lu\n", (unsigned long)total_in);
    cli_print("  Output:           %lu\n", (unsigned long)total_out);
    cli_print("Blocked:            %lu (%.1f%%)\n", 
             (unsigned long)blocked,
             total > 0 ? (100.0 * blocked / total) : 0.0);
    cli_print("  Input:            %lu\n", (unsigned long)blocked_in);
    cli_print("  Output:           %lu\n", (unsigned long)blocked_out);
    cli_print("Allowed:            %lu (%.1f%%)\n",
             (unsigned long)(total - blocked),
             total > 0 ? (100.0 * (total - blocked) / total) : 0.0);
    cli_print("\n");
    
    return SHIELD_OK;
}

/* show config */
shield_err_t cmd_show_config(shield_context_t *ctx, int argc, char **argv)
{
    (void)argc; (void)argv;
    
    cli_print("!\n");
    cli_print("! SENTINEL Shield Configuration\n");
    cli_print("! Generated: [timestamp]\n");
    cli_print("!\n");
    cli_print("hostname %s\n", ctx->cli.hostname);
    cli_print("!\n");
    
    /* Zones */
    if (ctx->zones) {
        shield_zone_t *zone = ctx->zones->zones;
        while (zone) {
            cli_print("zone %s\n", zone->name);
            cli_print("  type %s\n", zone_type_to_string(zone->type));
            if (zone->provider[0]) {
                cli_print("  provider %s\n", zone->provider);
            }
            if (zone->description[0]) {
                cli_print("  description \"%s\"\n", zone->description);
            }
            if (!zone->enabled) {
                cli_print("  shutdown\n");
            }
            cli_print("!\n");
            zone = zone->next;
        }
    }
    
    /* Rules */
    if (ctx->rules) {
        access_list_t *acl = ctx->rules->lists;
        while (acl) {
            shield_rule_t *rule = acl->rules;
            while (rule) {
                cli_print("shield-rule %u %s %s %s",
                         rule->number,
                         action_to_string(rule->action),
                         direction_to_string(rule->direction),
                         zone_type_to_string(rule->zone_type));
                
                if (rule->conditions) {
                    match_condition_t *cond = rule->conditions;
                    cli_print(" %s", match_type_to_string(cond->type));
                    if (cond->pattern[0]) {
                        cli_print(" \"%s\"", cond->pattern);
                    }
                }
                
                cli_print("\n");
                rule = rule->next;
            }
            acl = acl->next;
        }
        cli_print("!\n");
    }
    
    cli_print("end\n");
    return SHIELD_OK;
}

/* show version */
shield_err_t cmd_show_version(shield_context_t *ctx, int argc, char **argv)
{
    (void)ctx; (void)argc; (void)argv;
    
    cli_print("\nSENTINEL Shield v%s\n", SHIELD_VERSION_STRING);
    cli_print("Copyright (c) 2026 SENTINEL Project\n");
    cli_print("\n");
    cli_print("Compiled: %s %s\n", __DATE__, __TIME__);
    cli_print("\n");
    
    return SHIELD_OK;
}

/* zone */
shield_err_t cmd_zone(shield_context_t *ctx, int argc, char **argv)
{
    if (ctx->cli.mode != CLI_MODE_CONFIG) {
        cli_print_error("Command only available in config mode");
        return SHIELD_ERR_PERMISSION;
    }
    
    if (argc < 2) {
        cli_print_error("Usage: zone <name> [type <type>]");
        return SHIELD_ERR_INVALID;
    }
    
    const char *name = argv[1];
    zone_type_t type = ZONE_TYPE_UNKNOWN;
    
    /* Parse optional type */
    if (argc >= 4 && strcmp(argv[2], "type") == 0) {
        type = zone_type_from_string(argv[3]);
    }
    
    /* Find or create zone */
    shield_zone_t *zone = zone_find_by_name(ctx->zones, name);
    if (!zone) {
        shield_err_t err = zone_create(ctx->zones, name, type, &zone);
        if (err != SHIELD_OK) {
            cli_print_error("Failed to create zone: %d", err);
            return err;
        }
        ctx->modified = true;
    }
    
    /* Enter zone config mode */
    strncpy(ctx->cli.current_zone, name, SHIELD_MAX_NAME_LEN - 1);
    cli_set_mode(ctx, CLI_MODE_ZONE);
    
    return SHIELD_OK;
}

/* shield-rule */
shield_err_t cmd_shield_rule(shield_context_t *ctx, int argc, char **argv)
{
    if (ctx->cli.mode != CLI_MODE_CONFIG) {
        cli_print_error("Command only available in config mode");
        return SHIELD_ERR_PERMISSION;
    }
    
    if (argc < 5) {
        cli_print_error("Usage: shield-rule <num> <action> <direction> <zone-type> [match...]");
        cli_print_error("  action: block, allow, quarantine, analyze, log");
        cli_print_error("  direction: input, output");
        cli_print_error("  zone-type: llm, rag, agent, tool, mcp, any");
        return SHIELD_ERR_INVALID;
    }
    
    uint32_t num = atoi(argv[1]);
    rule_action_t action = action_from_string(argv[2]);
    rule_direction_t direction = direction_from_string(argv[3]);
    zone_type_t zone_type = zone_type_from_string(argv[4]);
    
    /* Get or create ACL 100 (default) */
    access_list_t *acl = acl_find(ctx->rules, 100);
    if (!acl) {
        acl_create(ctx->rules, 100, &acl);
    }
    
    /* Create rule */
    shield_rule_t *rule = NULL;
    shield_err_t err = rule_add(acl, num, action, direction, zone_type, NULL, &rule);
    if (err != SHIELD_OK) {
        if (err == SHIELD_ERR_EXISTS) {
            cli_print_error("Rule %u already exists", num);
        } else {
            cli_print_error("Failed to create rule: %d", err);
        }
        return err;
    }
    
    /* Parse match conditions */
    if (argc >= 6) {
        match_type_t match_type = match_type_from_string(argv[5]);
        const char *pattern = argc >= 7 ? argv[6] : "";
        rule_add_condition(rule, match_type, pattern, 0);
    }
    
    ctx->modified = true;
    return SHIELD_OK;
}

/* apply */
shield_err_t cmd_apply(shield_context_t *ctx, int argc, char **argv)
{
    if (argc < 4) {
        cli_print_error("Usage: apply zone <name> in <acl> [out <acl>]");
        return SHIELD_ERR_INVALID;
    }
    
    if (strcmp(argv[1], "zone") != 0) {
        cli_print_error("Unknown apply target: %s", argv[1]);
        return SHIELD_ERR_INVALID;
    }
    
    const char *zone_name = argv[2];
    shield_zone_t *zone = zone_find_by_name(ctx->zones, zone_name);
    if (!zone) {
        cli_print_error("Zone not found: %s", zone_name);
        return SHIELD_ERR_NOTFOUND;
    }
    
    /* Parse ACLs */
    for (int i = 3; i < argc - 1; i += 2) {
        if (strcmp(argv[i], "in") == 0) {
            zone->in_acl = atoi(argv[i + 1]);
        } else if (strcmp(argv[i], "out") == 0) {
            zone->out_acl = atoi(argv[i + 1]);
        }
    }
    
    ctx->modified = true;
    cli_print("Applied to zone %s: in=%u, out=%u\n", 
             zone_name, zone->in_acl, zone->out_acl);
    
    return SHIELD_OK;
}

/* write */
shield_err_t cmd_write(shield_context_t *ctx, int argc, char **argv)
{
    (void)argc; (void)argv;
    
    cli_print("Building configuration...\n");
    /* TODO: Write to config file */
    cli_print("[OK]\n");
    ctx->modified = false;
    
    return SHIELD_OK;
}

/* clear */
shield_err_t cmd_clear(shield_context_t *ctx, int argc, char **argv)
{
    if (argc < 2) {
        cli_print_error("Usage: clear <counters|stats|log>");
        return SHIELD_ERR_INVALID;
    }
    
    const char *what = argv[1];
    
    if (strcmp(what, "counters") == 0 || strcmp(what, "stats") == 0) {
        if (ctx->zones) {
            shield_zone_t *zone = ctx->zones->zones;
            while (zone) {
                zone_reset_stats(zone);
                zone = zone->next;
            }
        }
        cli_print("Counters cleared.\n");
        return SHIELD_OK;
    }
    
    cli_print_error("Unknown clear target: %s", what);
    return SHIELD_ERR_INVALID;
}

/* debug */
shield_err_t cmd_debug(shield_context_t *ctx, int argc, char **argv)
{
    if (argc < 2) {
        cli_print_error("Usage: debug <shield|zone|rule>");
        return SHIELD_ERR_INVALID;
    }
    
    ctx->log_level = LOG_DEBUG;
    cli_print("Debug enabled for %s\n", argv[1]);
    
    return SHIELD_OK;
}
