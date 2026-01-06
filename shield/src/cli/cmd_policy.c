/*
 * SENTINEL Shield - Policy & class-map Commands
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "shield_common.h"
#include "shield_cli.h"
#include "shield_policy.h"

/* class-map match-any <name> */
static shield_err_t cmd_class_map_any(cli_context_t *ctx, int argc, char **argv)
{
    if (argc < 3) {
        cli_print("%% Usage: class-map match-any <name>\n");
        return SHIELD_OK;
    }
    
    class_map_t *cm = NULL;
    shield_err_t err = class_map_create(ctx->policy_engine, argv[2], CLASS_MATCH_ANY, &cm);
    
    if (err == SHIELD_ERR_EXISTS) {
        cli_print("%% Class-map %s already exists\n", argv[2]);
    } else if (err == SHIELD_OK) {
        strncpy(ctx->current_class_map, argv[2], sizeof(ctx->current_class_map) - 1);
        cli_set_mode(ctx, CLI_MODE_CLASS_MAP);
        ctx->modified = true;
    }
}

/* class-map match-all <name> */
static shield_err_t cmd_class_map_all(cli_context_t *ctx, int argc, char **argv)
{
    if (argc < 3) {
        cli_print("%% Usage: class-map match-all <name>\n");
        return SHIELD_OK;
    }
    
    class_map_t *cm = NULL;
    shield_err_t err = class_map_create(ctx->policy_engine, argv[2], CLASS_MATCH_ALL, &cm);
    
    if (err == SHIELD_OK) {
        strncpy(ctx->current_class_map, argv[2], sizeof(ctx->current_class_map) - 1);
        cli_set_mode(ctx, CLI_MODE_CLASS_MAP);
        ctx->modified = true;
    }
}

/* no class-map <name> */
static shield_err_t cmd_no_class_map(cli_context_t *ctx, int argc, char **argv)
{
    if (argc < 3) {
        cli_print("%% Usage: no class-map <name>\n");
        return SHIELD_OK;
    }
    
    class_map_delete(ctx->policy_engine, argv[2]);
    cli_print("Class-map %s deleted\n", argv[2]);
    ctx->modified = true;
}

/* match injection (class-map submode) */
static shield_err_t cmd_match_injection(cli_context_t *ctx, int argc, char **argv)
{
    (void)argc; (void)argv;
    class_map_t *cm = class_map_find(ctx->policy_engine, ctx->current_class_map);
    if (cm) {
        class_map_add_match(cm, MATCH_PROMPT_INJECTION, "", false);
        cli_print("Match injection added\n");
        ctx->modified = true;
    }
}

/* match jailbreak */
static shield_err_t cmd_match_jailbreak(cli_context_t *ctx, int argc, char **argv)
{
    (void)argc; (void)argv;
    class_map_t *cm = class_map_find(ctx->policy_engine, ctx->current_class_map);
    if (cm) {
        class_map_add_match(cm, MATCH_JAILBREAK, "", false);
        cli_print("Match jailbreak added\n");
        ctx->modified = true;
    }
}

/* match exfiltration */
static shield_err_t cmd_match_exfiltration(cli_context_t *ctx, int argc, char **argv)
{
    (void)argc; (void)argv;
    class_map_t *cm = class_map_find(ctx->policy_engine, ctx->current_class_map);
    if (cm) {
        class_map_add_match(cm, MATCH_DATA_EXFIL, "", false);
        cli_print("Match exfiltration added\n");
        ctx->modified = true;
    }
}

/* match pattern <regex> */
static shield_err_t cmd_match_pattern(cli_context_t *ctx, int argc, char **argv)
{
    if (argc < 3) {
        cli_print("%% Usage: match pattern <regex>\n");
        return SHIELD_OK;
    }
    class_map_t *cm = class_map_find(ctx->policy_engine, ctx->current_class_map);
    if (cm) {
        class_map_add_match(cm, MATCH_PATTERN, argv[2], false);
        cli_print("Match pattern added\n");
        ctx->modified = true;
    }
}

/* match contains <string> */
static shield_err_t cmd_match_contains(cli_context_t *ctx, int argc, char **argv)
{
    if (argc < 3) {
        cli_print("%% Usage: match contains <string>\n");
        return SHIELD_OK;
    }
    class_map_t *cm = class_map_find(ctx->policy_engine, ctx->current_class_map);
    if (cm) {
        class_map_add_match(cm, MATCH_CONTAINS, argv[2], false);
        cli_print("Match contains added\n");
        ctx->modified = true;
    }
}

/* match size greater-than <size> */
static shield_err_t cmd_match_size_gt(cli_context_t *ctx, int argc, char **argv)
{
    if (argc < 4) {
        cli_print("%% Usage: match size greater-than <bytes>\n");
        return SHIELD_OK;
    }
    class_map_t *cm = class_map_find(ctx->policy_engine, ctx->current_class_map);
    if (cm) {
        class_map_add_match(cm, MATCH_SIZE_GT, argv[3], false);
        cli_print("Match size > %s added\n", argv[3]);
        ctx->modified = true;
    }
}

/* match entropy-high */
static shield_err_t cmd_match_entropy(cli_context_t *ctx, int argc, char **argv)
{
    (void)argc; (void)argv;
    class_map_t *cm = class_map_find(ctx->policy_engine, ctx->current_class_map);
    if (cm) {
        class_map_add_match(cm, MATCH_ENTROPY_HIGH, "", false);
        cli_print("Match high entropy added\n");
        ctx->modified = true;
    }
}

/* policy-map <name> */
static shield_err_t cmd_policy_map(cli_context_t *ctx, int argc, char **argv)
{
    if (argc < 2) {
        cli_print("%% Usage: policy-map <name>\n");
        return SHIELD_OK;
    }
    
    policy_map_t *pm = NULL;
    policy_map_create(ctx->policy_engine, argv[1], &pm);
    
    strncpy(ctx->current_policy_map, argv[1], sizeof(ctx->current_policy_map) - 1);
    cli_set_mode(ctx, CLI_MODE_POLICY_MAP);
    ctx->modified = true;
}

/* no policy-map <name> */
static shield_err_t cmd_no_policy_map(cli_context_t *ctx, int argc, char **argv)
{
    if (argc < 3) {
        cli_print("%% Usage: no policy-map <name>\n");
        return SHIELD_OK;
    }
    
    policy_map_delete(ctx->policy_engine, argv[2]);
    cli_print("Policy-map %s deleted\n", argv[2]);
    ctx->modified = true;
}

/* class <name> (policy-map submode) */
static shield_err_t cmd_pm_class(cli_context_t *ctx, int argc, char **argv)
{
    if (argc < 2) {
        cli_print("%% Usage: class <class-name>\n");
        return SHIELD_OK;
    }
    
    policy_map_t *pm = policy_map_find(ctx->policy_engine, ctx->current_policy_map);
    if (pm) {
        policy_class_t *pc = NULL;
        policy_map_add_class(pm, argv[1], &pc);
        strncpy(ctx->current_policy_class, argv[1], sizeof(ctx->current_policy_class) - 1);
        cli_print("Class %s added to policy\n", argv[1]);
        ctx->modified = true;
    }
}

/* block (action in policy class) */
static shield_err_t cmd_action_block(cli_context_t *ctx, int argc, char **argv)
{
    (void)argc; (void)argv;
    policy_map_t *pm = policy_map_find(ctx->policy_engine, ctx->current_policy_map);
    if (pm) {
        policy_class_t *pc = policy_class_find(pm, ctx->current_policy_class);
        if (pc) {
            policy_class_add_action(pc, ACTION_BLOCK, NULL);
            cli_print("Action: block\n");
            ctx->modified = true;
        }
    }
}

/* log */
static shield_err_t cmd_action_log(cli_context_t *ctx, int argc, char **argv)
{
    (void)argc; (void)argv;
    policy_map_t *pm = policy_map_find(ctx->policy_engine, ctx->current_policy_map);
    if (pm) {
        policy_class_t *pc = policy_class_find(pm, ctx->current_policy_class);
        if (pc) {
            policy_action_t *pa = NULL;
            policy_class_add_action(pc, ACTION_LOG, &pa);
            if (pa) pa->log_enabled = true;
            cli_print("Action: log\n");
            ctx->modified = true;
        }
    }
}

/* alert */
static shield_err_t cmd_action_alert(cli_context_t *ctx, int argc, char **argv)
{
    (void)argc; (void)argv;
    policy_map_t *pm = policy_map_find(ctx->policy_engine, ctx->current_policy_map);
    if (pm) {
        policy_class_t *pc = policy_class_find(pm, ctx->current_policy_class);
        if (pc) {
            policy_class_add_action(pc, ACTION_ALERT, NULL);
            cli_print("Action: alert\n");
            ctx->modified = true;
        }
    }
}

/* rate-limit <pps> */
static shield_err_t cmd_action_rate_limit(cli_context_t *ctx, int argc, char **argv)
{
    if (argc < 2) {
        cli_print("%% Usage: rate-limit <pps>\n");
        return SHIELD_OK;
    }
    policy_map_t *pm = policy_map_find(ctx->policy_engine, ctx->current_policy_map);
    if (pm) {
        policy_class_t *pc = policy_class_find(pm, ctx->current_policy_class);
        if (pc) {
            policy_action_t *pa = NULL;
            policy_class_add_action(pc, ACTION_RATE_LIMIT, &pa);
            if (pa) pa->rate_limit = atoi(argv[1]);
            cli_print("Action: rate-limit %s\n", argv[1]);
            ctx->modified = true;
        }
    }
}

/* service-policy input <policy> */
static shield_err_t cmd_service_policy_input(cli_context_t *ctx, int argc, char **argv)
{
    if (argc < 3) {
        cli_print("%% Usage: service-policy input <policy-name>\n");
        return SHIELD_OK;
    }
    
    service_policy_apply(ctx->policy_engine, ctx->current_zone, argv[2], DIRECTION_INPUT);
    cli_print("Service policy %s applied (input)\n", argv[2]);
    ctx->modified = true;
}

/* service-policy output <policy> */
static shield_err_t cmd_service_policy_output(cli_context_t *ctx, int argc, char **argv)
{
    if (argc < 3) {
        cli_print("%% Usage: service-policy output <policy-name>\n");
        return SHIELD_OK;
    }
    
    service_policy_apply(ctx->policy_engine, ctx->current_zone, argv[2], DIRECTION_OUTPUT);
    cli_print("Service policy %s applied (output)\n", argv[2]);
    ctx->modified = true;
}

/* Policy command table */
static cli_command_t policy_commands[] = {
    /* Config mode */
    {"class-map match-any", cmd_class_map_any, CLI_MODE_CONFIG, "Create class-map"},
    {"class-map match-all", cmd_class_map_all, CLI_MODE_CONFIG, "Create class-map"},
    {"no class-map", cmd_no_class_map, CLI_MODE_CONFIG, "Delete class-map"},
    {"policy-map", cmd_policy_map, CLI_MODE_CONFIG, "Create policy-map"},
    {"no policy-map", cmd_no_policy_map, CLI_MODE_CONFIG, "Delete policy-map"},
    
    /* Class-map submode */
    {"match injection", cmd_match_injection, CLI_MODE_CLASS_MAP, "Match injection"},
    {"match jailbreak", cmd_match_jailbreak, CLI_MODE_CLASS_MAP, "Match jailbreak"},
    {"match exfiltration", cmd_match_exfiltration, CLI_MODE_CLASS_MAP, "Match exfiltration"},
    {"match pattern", cmd_match_pattern, CLI_MODE_CLASS_MAP, "Match pattern"},
    {"match contains", cmd_match_contains, CLI_MODE_CLASS_MAP, "Match contains"},
    {"match size greater-than", cmd_match_size_gt, CLI_MODE_CLASS_MAP, "Match size"},
    {"match entropy-high", cmd_match_entropy, CLI_MODE_CLASS_MAP, "Match entropy"},
    
    /* Policy-map submode */
    {"class", cmd_pm_class, CLI_MODE_POLICY_MAP, "Add class"},
    {"block", cmd_action_block, CLI_MODE_POLICY_MAP, "Block action"},
    {"log", cmd_action_log, CLI_MODE_POLICY_MAP, "Log action"},
    {"alert", cmd_action_alert, CLI_MODE_POLICY_MAP, "Alert action"},
    {"rate-limit", cmd_action_rate_limit, CLI_MODE_POLICY_MAP, "Rate limit"},
    
    /* Zone submode */
    {"service-policy input", cmd_service_policy_input, CLI_MODE_ZONE, "Apply input policy"},
    {"service-policy output", cmd_service_policy_output, CLI_MODE_ZONE, "Apply output policy"},
    
    {NULL, NULL, 0, NULL}
};

void register_policy_commands(cli_context_t *ctx)
{
    for (int i = 0; policy_commands[i].name != NULL; i++) {
        cli_register_command(ctx, &policy_commands[i]);
    }
}
