/*
 * SENTINEL Shield - Configuration Parser
 * 
 * Parses Cisco-style configuration files
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>

#include "shield_common.h"
#include "shield_zone.h"
#include "shield_rule.h"
#include "shield_cli.h"

#define MAX_LINE_LEN 4096

/* Parse state */
typedef enum parse_state {
    PARSE_STATE_GLOBAL,
    PARSE_STATE_ZONE,
} parse_state_t;

/* Strip leading/trailing whitespace */
static char *strip(char *str)
{
    if (!str) return NULL;
    
    /* Leading */
    while (*str && isspace(*str)) str++;
    
    /* Trailing */
    size_t len = strlen(str);
    while (len > 0 && isspace(str[len - 1])) {
        str[--len] = '\0';
    }
    
    return str;
}

/* Load configuration from file */
shield_err_t config_load(shield_context_t *ctx, const char *filename)
{
    if (!ctx || !filename) {
        return SHIELD_ERR_INVALID;
    }
    
    FILE *fp = fopen(filename, "r");
    if (!fp) {
        LOG_ERROR("Cannot open config file: %s", filename);
        return SHIELD_ERR_IO;
    }
    
    char line[MAX_LINE_LEN];
    int line_num = 0;
    parse_state_t state = PARSE_STATE_GLOBAL;
    char current_zone[SHIELD_MAX_NAME_LEN] = {0};
    
    while (fgets(line, sizeof(line), fp)) {
        line_num++;
        
        char *p = strip(line);
        
        /* Skip empty lines and comments */
        if (*p == '\0' || *p == '!' || *p == '#') {
            continue;
        }
        
        /* Parse based on state */
        if (state == PARSE_STATE_GLOBAL) {
            /* Hostname */
            if (strncmp(p, "hostname ", 9) == 0) {
                strncpy(ctx->cli.hostname, p + 9, sizeof(ctx->cli.hostname) - 1);
                continue;
            }
            
            /* Zone definition */
            if (strncmp(p, "zone ", 5) == 0) {
                strncpy(current_zone, p + 5, sizeof(current_zone) - 1);
                
                shield_zone_t *zone = zone_find_by_name(ctx->zones, current_zone);
                if (!zone) {
                    zone_create(ctx->zones, current_zone, ZONE_TYPE_UNKNOWN, &zone);
                }
                
                state = PARSE_STATE_ZONE;
                continue;
            }
            
            /* Shield rule */
            if (strncmp(p, "shield-rule ", 12) == 0) {
                /* Parse: shield-rule <num> <action> <dir> <type> [match] [pattern] */
                char *tokens[10];
                int count = 0;
                
                char *tok = strtok(p + 12, " \t");
                while (tok && count < 10) {
                    tokens[count++] = tok;
                    tok = strtok(NULL, " \t\"");
                }
                
                if (count >= 4) {
                    uint32_t num = atoi(tokens[0]);
                    rule_action_t action = action_from_string(tokens[1]);
                    rule_direction_t dir = direction_from_string(tokens[2]);
                    zone_type_t type = zone_type_from_string(tokens[3]);
                    
                    /* Get or create default ACL */
                    access_list_t *acl = acl_find(ctx->rules, 100);
                    if (!acl) {
                        acl_create(ctx->rules, 100, &acl);
                    }
                    
                    shield_rule_t *rule = NULL;
                    rule_add(acl, num, action, dir, type, NULL, &rule);
                    
                    /* Add match condition if present */
                    if (rule && count >= 5) {
                        match_type_t match_type = match_type_from_string(tokens[4]);
                        const char *pattern = count >= 6 ? tokens[5] : "";
                        rule_add_condition(rule, match_type, pattern, 0);
                    }
                }
                continue;
            }
            
            /* Apply zone */
            if (strncmp(p, "apply ", 6) == 0) {
                /* Parse: apply zone <name> in <acl> out <acl> */
                char zone_name[64] = {0};
                uint32_t in_acl = 0, out_acl = 0;
                
                if (sscanf(p, "apply zone %63s in %u out %u", zone_name, &in_acl, &out_acl) >= 2) {
                    shield_zone_t *zone = zone_find_by_name(ctx->zones, zone_name);
                    if (zone) {
                        zone->in_acl = in_acl;
                        zone->out_acl = out_acl;
                    }
                }
                continue;
            }
        }
        else if (state == PARSE_STATE_ZONE) {
            shield_zone_t *zone = zone_find_by_name(ctx->zones, current_zone);
            
            /* Exit zone config */
            if (*p == '!' || strcmp(p, "exit") == 0) {
                state = PARSE_STATE_GLOBAL;
                current_zone[0] = '\0';
                continue;
            }
            
            if (!zone) {
                continue;
            }
            
            /* Type */
            if (strncmp(p, "type ", 5) == 0) {
                zone->type = zone_type_from_string(p + 5);
                continue;
            }
            
            /* Provider */
            if (strncmp(p, "provider ", 9) == 0) {
                zone_set_provider(zone, p + 9);
                continue;
            }
            
            /* Description */
            if (strncmp(p, "description ", 12) == 0) {
                char *desc = p + 12;
                /* Remove quotes */
                if (*desc == '"') desc++;
                size_t len = strlen(desc);
                if (len > 0 && desc[len-1] == '"') desc[len-1] = '\0';
                zone_set_description(zone, desc);
                continue;
            }
            
            /* Shutdown */
            if (strcmp(p, "shutdown") == 0) {
                zone->enabled = false;
                continue;
            }
        }
    }
    
    fclose(fp);
    
    LOG_INFO("Loaded configuration from %s (%d lines)", filename, line_num);
    strncpy(ctx->config_file, filename, sizeof(ctx->config_file) - 1);
    
    return SHIELD_OK;
}

/* Save configuration to file */
shield_err_t config_save(shield_context_t *ctx, const char *filename)
{
    if (!ctx || !filename) {
        return SHIELD_ERR_INVALID;
    }
    
    FILE *fp = fopen(filename, "w");
    if (!fp) {
        LOG_ERROR("Cannot write config file: %s", filename);
        return SHIELD_ERR_IO;
    }
    
    fprintf(fp, "!\n");
    fprintf(fp, "! SENTINEL Shield Configuration\n");
    fprintf(fp, "!\n");
    fprintf(fp, "hostname %s\n", ctx->cli.hostname);
    fprintf(fp, "!\n");
    
    /* Zones */
    if (ctx->zones) {
        shield_zone_t *zone = ctx->zones->zones;
        while (zone) {
            fprintf(fp, "zone %s\n", zone->name);
            fprintf(fp, "  type %s\n", zone_type_to_string(zone->type));
            if (zone->provider[0]) {
                fprintf(fp, "  provider %s\n", zone->provider);
            }
            if (zone->description[0]) {
                fprintf(fp, "  description \"%s\"\n", zone->description);
            }
            if (!zone->enabled) {
                fprintf(fp, "  shutdown\n");
            }
            fprintf(fp, "!\n");
            zone = zone->next;
        }
    }
    
    /* Rules */
    if (ctx->rules) {
        access_list_t *acl = ctx->rules->lists;
        while (acl) {
            shield_rule_t *rule = acl->rules;
            while (rule) {
                fprintf(fp, "shield-rule %u %s %s %s",
                       rule->number,
                       action_to_string(rule->action),
                       direction_to_string(rule->direction),
                       zone_type_to_string(rule->zone_type));
                
                if (rule->conditions) {
                    match_condition_t *cond = rule->conditions;
                    fprintf(fp, " %s", match_type_to_string(cond->type));
                    if (cond->pattern[0]) {
                        fprintf(fp, " \"%s\"", cond->pattern);
                    }
                }
                
                fprintf(fp, "\n");
                rule = rule->next;
            }
            acl = acl->next;
        }
        fprintf(fp, "!\n");
    }
    
    /* Apply zones */
    if (ctx->zones) {
        shield_zone_t *zone = ctx->zones->zones;
        while (zone) {
            if (zone->in_acl || zone->out_acl) {
                fprintf(fp, "apply zone %s in %u out %u\n",
                       zone->name, zone->in_acl, zone->out_acl);
            }
            zone = zone->next;
        }
        fprintf(fp, "!\n");
    }
    
    fprintf(fp, "end\n");
    fclose(fp);
    
    LOG_INFO("Saved configuration to %s", filename);
    ctx->modified = false;
    
    return SHIELD_OK;
}

/* ===== Wrapper Functions (declared in shield_context.h) ===== */

/* Reload configuration from current config file */
shield_err_t shield_reload_config(shield_context_t *ctx)
{
    if (!ctx || !ctx->config_file[0]) {
        return SHIELD_ERR_INVALID;
    }
    
    LOG_INFO("Reloading configuration from %s", ctx->config_file);
    return config_load(ctx, ctx->config_file);
}

/* Save configuration to current config file (or path if specified) */
shield_err_t shield_save_config(shield_context_t *ctx, const char *path)
{
    if (!ctx) {
        return SHIELD_ERR_INVALID;
    }
    
    const char *filename = path ? path : ctx->config_file;
    if (!filename || !filename[0]) {
        LOG_ERROR("No config file specified");
        return SHIELD_ERR_INVALID;
    }
    
    return config_save(ctx, filename);
}
