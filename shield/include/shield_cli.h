/*
 * SENTINEL Shield - CLI Interface
 * 
 * Cisco-style command line interface
 */

#ifndef SHIELD_CLI_H
#define SHIELD_CLI_H

#include "shield_context.h"

/* CLI uses cli_context_t as alias for shield_context */
typedef shield_context_t cli_context_t;

/* Command handler function */
typedef void (*cli_handler_t)(shield_context_t *ctx, 
                               int argc, char **argv);

/* CLI command definition */
typedef struct cli_command {
    const char      *name;
    cli_handler_t   handler;
    cli_mode_t      mode;           /* Which mode this command is available */
    const char      *help;
} cli_command_t;

/* cli_state_t is defined in shield_context.h */

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
shield_err_t cli_execute_args(shield_context_t *ctx, int argc, char **argv);
shield_err_t cli_execute_file(shield_context_t *ctx, const char *filename);
shield_err_t cli_register_command(shield_context_t *ctx, const cli_command_t *cmd);

/* Tab completion */
char **cli_complete(shield_context_t *ctx, const char *text, int start, int end);

/* History */
void cli_add_history(shield_context_t *ctx, const char *line);
const char *cli_get_history(shield_context_t *ctx, int offset);

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
