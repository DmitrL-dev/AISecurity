/*
 * SENTINEL Shield - CLI Implementation
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdarg.h>
#include <ctype.h>

#include "shield_common.h"
#include "shield_zone.h"
#include "shield_rule.h"
#include "shield_guard.h"
#include "shield_cli.h"

/* Prompt templates */
static const char *prompts[] = {
    "sentinel> ",           /* EXEC (not enabled) */
    "sentinel# ",           /* EXEC (enabled) */
    "sentinel(config)# ",   /* CONFIG */
    "sentinel(config-zone)# ", /* ZONE */
};

/* Initialize CLI */
shield_err_t cli_init(shield_context_t *ctx)
{
    if (!ctx) {
        return SHIELD_ERR_INVALID;
    }
    
    memset(&ctx->cli, 0, sizeof(ctx->cli));
    ctx->cli.mode = CLI_MODE_EXEC;
    strncpy(ctx->cli.hostname, "sentinel", sizeof(ctx->cli.hostname) - 1);
    ctx->cli.enable_mode = true; /* Start in enable mode */
    ctx->cli.terminal_width = 80;
    ctx->cli.terminal_height = 24;
    ctx->cli.pager_enabled = true;
    
    cli_update_prompt(ctx);
    
    return SHIELD_OK;
}

/* Destroy CLI */
void cli_destroy(shield_context_t *ctx)
{
    if (!ctx) {
        return;
    }
    
    /* Free history */
    for (int i = 0; i < ctx->cli.history_count; i++) {
        free(ctx->cli.history[i]);
    }
}

/* Set mode */
void cli_set_mode(shield_context_t *ctx, cli_mode_t mode)
{
    if (!ctx) {
        return;
    }
    ctx->cli.mode = mode;
    cli_update_prompt(ctx);
}

/* Update prompt */
void cli_update_prompt(shield_context_t *ctx)
{
    if (!ctx) {
        return;
    }
    
    switch (ctx->cli.mode) {
    case CLI_MODE_EXEC:
        if (ctx->cli.enable_mode) {
            snprintf(ctx->cli.prompt, sizeof(ctx->cli.prompt),
                     "%s# ", ctx->cli.hostname);
        } else {
            snprintf(ctx->cli.prompt, sizeof(ctx->cli.prompt),
                     "%s> ", ctx->cli.hostname);
        }
        break;
    case CLI_MODE_CONFIG:
        snprintf(ctx->cli.prompt, sizeof(ctx->cli.prompt),
                 "%s(config)# ", ctx->cli.hostname);
        break;
    case CLI_MODE_ZONE:
        snprintf(ctx->cli.prompt, sizeof(ctx->cli.prompt),
                 "%s(config-zone-%s)# ", ctx->cli.hostname,
                 ctx->cli.current_zone);
        break;
    default:
        snprintf(ctx->cli.prompt, sizeof(ctx->cli.prompt),
                 "%s# ", ctx->cli.hostname);
    }
}

/* Print */
void cli_print(const char *fmt, ...)
{
    va_list args;
    va_start(args, fmt);
    vprintf(fmt, args);
    va_end(args);
}

/* Print error */
void cli_print_error(const char *fmt, ...)
{
    printf("%% ");
    va_list args;
    va_start(args, fmt);
    vprintf(fmt, args);
    va_end(args);
    printf("\n");
}

/* Print table header */
void cli_print_table_header(const char **columns, int count, int *widths)
{
    for (int i = 0; i < count; i++) {
        printf("%-*s ", widths[i], columns[i]);
    }
    printf("\n");
    
    /* Separator */
    int total = 0;
    for (int i = 0; i < count; i++) {
        total += widths[i] + 1;
    }
    for (int i = 0; i < total; i++) {
        printf("-");
    }
    printf("\n");
}

/* Print table row */
void cli_print_table_row(const char **values, int count, int *widths)
{
    for (int i = 0; i < count; i++) {
        printf("%-*s ", widths[i], values[i]);
    }
    printf("\n");
}

/* Print separator */
void cli_print_separator(int width)
{
    for (int i = 0; i < width; i++) {
        printf("-");
    }
    printf("\n");
}

/* Tokenize command line */
static int tokenize(char *line, char **argv, int max_args)
{
    int argc = 0;
    char *token = strtok(line, " \t\n");
    
    while (token && argc < max_args) {
        argv[argc++] = token;
        token = strtok(NULL, " \t\n");
    }
    
    return argc;
}

/* Execute command */
shield_err_t cli_execute(shield_context_t *ctx, const char *line)
{
    if (!ctx || !line) {
        return SHIELD_ERR_INVALID;
    }
    
    /* Copy line for tokenization */
    char buf[SHIELD_MAX_CMD_LEN];
    strncpy(buf, line, sizeof(buf) - 1);
    buf[sizeof(buf) - 1] = '\0';
    
    /* Skip leading whitespace */
    char *p = buf;
    while (*p && isspace(*p)) p++;
    
    /* Empty line or comment */
    if (*p == '\0' || *p == '!' || *p == '#') {
        return SHIELD_OK;
    }
    
    /* Tokenize */
    char *argv[64];
    int argc = tokenize(p, argv, 64);
    
    if (argc == 0) {
        return SHIELD_OK;
    }
    
    /* Find and execute command */
    const char *cmd = argv[0];
    
    /* Global commands */
    if (strcmp(cmd, "enable") == 0) {
        return cmd_enable(ctx, argc, argv);
    }
    if (strcmp(cmd, "disable") == 0) {
        return cmd_disable(ctx, argc, argv);
    }
    if (strcmp(cmd, "config") == 0 || strcmp(cmd, "configure") == 0) {
        return cmd_config(ctx, argc, argv);
    }
    if (strcmp(cmd, "exit") == 0) {
        return cmd_exit(ctx, argc, argv);
    }
    if (strcmp(cmd, "end") == 0) {
        return cmd_end(ctx, argc, argv);
    }
    if (strcmp(cmd, "help") == 0 || strcmp(cmd, "?") == 0) {
        return cmd_help(ctx, argc, argv);
    }
    if (strcmp(cmd, "show") == 0) {
        return cmd_show(ctx, argc, argv);
    }
    if (strcmp(cmd, "zone") == 0) {
        return cmd_zone(ctx, argc, argv);
    }
    if (strcmp(cmd, "shield-rule") == 0) {
        return cmd_shield_rule(ctx, argc, argv);
    }
    if (strcmp(cmd, "apply") == 0) {
        return cmd_apply(ctx, argc, argv);
    }
    if (strcmp(cmd, "write") == 0) {
        return cmd_write(ctx, argc, argv);
    }
    if (strcmp(cmd, "clear") == 0) {
        return cmd_clear(ctx, argc, argv);
    }
    if (strcmp(cmd, "debug") == 0) {
        return cmd_debug(ctx, argc, argv);
    }
    
    /* Zone mode commands */
    if (ctx->cli.mode == CLI_MODE_ZONE) {
        if (strcmp(cmd, "type") == 0) {
            /* zone type command */
            if (argc < 2) {
                cli_print_error("Usage: type <llm|rag|agent|tool|mcp|api|custom>");
                return SHIELD_ERR_INVALID;
            }
            shield_zone_t *zone = zone_find_by_name(ctx->zones, ctx->cli.current_zone);
            if (zone) {
                zone->type = zone_type_from_string(argv[1]);
                ctx->modified = true;
            }
            return SHIELD_OK;
        }
        if (strcmp(cmd, "provider") == 0) {
            if (argc < 2) {
                cli_print_error("Usage: provider <name>");
                return SHIELD_ERR_INVALID;
            }
            shield_zone_t *zone = zone_find_by_name(ctx->zones, ctx->cli.current_zone);
            if (zone) {
                zone_set_provider(zone, argv[1]);
                ctx->modified = true;
            }
            return SHIELD_OK;
        }
        if (strcmp(cmd, "description") == 0) {
            if (argc < 2) {
                cli_print_error("Usage: description <text>");
                return SHIELD_ERR_INVALID;
            }
            shield_zone_t *zone = zone_find_by_name(ctx->zones, ctx->cli.current_zone);
            if (zone) {
                zone_set_description(zone, argv[1]);
                ctx->modified = true;
            }
            return SHIELD_OK;
        }
    }
    
    cli_print_error("Unknown command: %s", cmd);
    return SHIELD_ERR_INVALID;
}

/* Add to history */
void cli_add_history(cli_state_t *cli, const char *line)
{
    if (!cli || !line || strlen(line) == 0) {
        return;
    }
    
    if (cli->history_count >= SHIELD_MAX_HISTORY) {
        /* Remove oldest */
        free(cli->history[0]);
        memmove(cli->history, cli->history + 1,
                (SHIELD_MAX_HISTORY - 1) * sizeof(char *));
        cli->history_count--;
    }
    
    cli->history[cli->history_count++] = strdup(line);
}

/* REPL */
void cli_repl(shield_context_t *ctx)
{
    char line[SHIELD_MAX_CMD_LEN];
    
    while (ctx->running) {
        printf("%s", ctx->cli.prompt);
        fflush(stdout);
        
        if (!fgets(line, sizeof(line), stdin)) {
            break;
        }
        
        /* Remove newline */
        size_t len = strlen(line);
        if (len > 0 && line[len - 1] == '\n') {
            line[len - 1] = '\0';
        }
        
        /* Skip empty */
        if (strlen(line) == 0) {
            continue;
        }
        
        /* Add to history */
        cli_add_history(&ctx->cli, line);
        
        /* Execute */
        cli_execute(ctx, line);
    }
}
