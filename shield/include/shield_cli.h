/*
 * SENTINEL Shield - CLI Interface
 * 
 * Cisco-style command line interface
 */

#ifndef SHIELD_CLI_H
#define SHIELD_CLI_H

#include "shield_common.h"

/* Forward declarations */
struct shield_context;

/* Command handler function */
typedef shield_err_t (*cli_handler_t)(struct shield_context *ctx, 
                                       int argc, char **argv);

/* CLI command definition */
typedef struct cli_command {
    const char      *name;
    const char      *help;
    const char      *usage;
    cli_mode_t      mode;           /* Which mode this command is available */
    cli_handler_t   handler;
    struct cli_command *subcommands;
    int             subcommand_count;
} cli_command_t;

/* CLI state */
typedef struct cli_state {
    cli_mode_t      mode;
    char            prompt[128];
    char            hostname[64];
    char            current_zone[SHIELD_MAX_NAME_LEN];
    bool            enable_mode;
    
    /* History */
    char            *history[SHIELD_MAX_HISTORY];
    int             history_count;
    int             history_pos;
    
    /* Output */
    bool            pager_enabled;
    int             terminal_width;
    int             terminal_height;
} cli_state_t;

/* Shield context (global state) */
typedef struct shield_context {
    cli_state_t         cli;
    struct zone_registry    *zones;
    struct rule_engine      *rules;
    struct guard_registry   *guards;
    
    /* Configuration */
    char                config_file[256];
    bool                modified;
    
    /* Runtime */
    bool                running;
    log_level_t         log_level;
} shield_context_t;

/* CLI API */
shield_err_t cli_init(shield_context_t *ctx);
void cli_destroy(shield_context_t *ctx);

void cli_set_mode(shield_context_t *ctx, cli_mode_t mode);
void cli_update_prompt(shield_context_t *ctx);
void cli_print(const char *fmt, ...);
void cli_print_error(const char *fmt, ...);
void cli_print_table_header(const char **columns, int count, int *widths);
void cli_print_table_row(const char **values, int count, int *widths);
void cli_print_separator(int width);

/* Command execution */
shield_err_t cli_execute(shield_context_t *ctx, const char *line);
shield_err_t cli_execute_file(shield_context_t *ctx, const char *filename);

/* Tab completion */
char **cli_complete(shield_context_t *ctx, const char *text, int start, int end);

/* History */
void cli_add_history(cli_state_t *cli, const char *line);
const char *cli_get_history(cli_state_t *cli, int offset);

/* REPL */
void cli_repl(shield_context_t *ctx);

/* Built-in command handlers */
shield_err_t cmd_enable(shield_context_t *ctx, int argc, char **argv);
shield_err_t cmd_disable(shield_context_t *ctx, int argc, char **argv);
shield_err_t cmd_config(shield_context_t *ctx, int argc, char **argv);
shield_err_t cmd_exit(shield_context_t *ctx, int argc, char **argv);
shield_err_t cmd_end(shield_context_t *ctx, int argc, char **argv);
shield_err_t cmd_help(shield_context_t *ctx, int argc, char **argv);
shield_err_t cmd_show(shield_context_t *ctx, int argc, char **argv);
shield_err_t cmd_zone(shield_context_t *ctx, int argc, char **argv);
shield_err_t cmd_shield_rule(shield_context_t *ctx, int argc, char **argv);
shield_err_t cmd_apply(shield_context_t *ctx, int argc, char **argv);
shield_err_t cmd_write(shield_context_t *ctx, int argc, char **argv);
shield_err_t cmd_clear(shield_context_t *ctx, int argc, char **argv);
shield_err_t cmd_debug(shield_context_t *ctx, int argc, char **argv);

/* Show subcommands */
shield_err_t cmd_show_zones(shield_context_t *ctx, int argc, char **argv);
shield_err_t cmd_show_rules(shield_context_t *ctx, int argc, char **argv);
shield_err_t cmd_show_stats(shield_context_t *ctx, int argc, char **argv);
shield_err_t cmd_show_config(shield_context_t *ctx, int argc, char **argv);
shield_err_t cmd_show_version(shield_context_t *ctx, int argc, char **argv);

#endif /* SHIELD_CLI_H */
