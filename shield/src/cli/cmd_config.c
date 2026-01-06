/*
 * SENTINEL Shield - Configuration Commands
 * 
 * All "configure" mode commands
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "shield_common.h"
#include "shield_cli.h"
#include "shield_state.h"
#include "shield_string_safe.h"

/* Local helper for log level parsing */
static log_level_t log_level_from_string(const char *str)
{
    if (!str) return LOG_INFO;
    if (strcasecmp(str, "debug") == 0 || strcasecmp(str, "trace") == 0) return LOG_DEBUG;
    if (strcasecmp(str, "info") == 0) return LOG_INFO;
    if (strcasecmp(str, "warn") == 0 || strcasecmp(str, "warning") == 0) return LOG_WARN;
    if (strcasecmp(str, "error") == 0) return LOG_ERROR;
    return LOG_INFO;
}

/* hostname */
static shield_err_t cmd_hostname(cli_context_t *ctx, int argc, char **argv)
{
    if (argc < 2) {
        cli_print("Current hostname: %s\n", ctx->hostname);
        return SHIELD_OK;
    }
    strncpy(ctx->hostname, argv[1], sizeof(ctx->hostname) - 1);
    
    /* Also update shield_state for tests */
    shield_state_t *state = shield_state_get();
    if (state) {
        strncpy(state->config.hostname, argv[1], sizeof(state->config.hostname) - 1);
    }
    
    cli_update_prompt(ctx);
    ctx->modified = true;
    return SHIELD_OK;
}

/* no hostname */
static shield_err_t cmd_no_hostname(cli_context_t *ctx, int argc, char **argv)
{
    (void)argc; (void)argv;
    shield_strcopy_s(ctx->hostname, sizeof(ctx->hostname), "Shield");
    cli_update_prompt(ctx);
    ctx->modified = true;
    return SHIELD_OK;
}

/* enable secret */
static shield_err_t cmd_enable_secret(cli_context_t *ctx, int argc, char **argv)
{
    if (argc < 2) {
        cli_print("%% Usage: enable secret <password>\n");
        return SHIELD_OK;
    }
    strncpy(ctx->enable_secret, argv[1], sizeof(ctx->enable_secret) - 1);
    ctx->modified = true;
    cli_print("Enable secret configured\n");
    return SHIELD_OK;
}

/* username */
static shield_err_t cmd_username(cli_context_t *ctx, int argc, char **argv)
{
    if (argc < 4) {
        cli_print("%% Usage: username <name> password <password>\n");
        return SHIELD_OK;
    }
    cli_print("User %s configured\n", argv[1]);
    ctx->modified = true;
    return SHIELD_OK;
}

/* logging level */
static shield_err_t cmd_logging_level(cli_context_t *ctx, int argc, char **argv)
{
    if (argc < 3) {
        cli_print("%% Usage: logging level <debug|info|warn|error>\n");
        return SHIELD_OK;
    }
    ctx->log_level = log_level_from_string(argv[2]);
    cli_print("Logging level set to %s\n", argv[2]);
    ctx->modified = true;
    return SHIELD_OK;
}

/* logging console */
static shield_err_t cmd_logging_console(cli_context_t *ctx, int argc, char **argv)
{
    (void)argc; (void)argv;
    ctx->logging_console = true;
    cli_print("Console logging enabled\n");
    ctx->modified = true;
    return SHIELD_OK;
}

/* no logging console */
static shield_err_t cmd_no_logging_console(cli_context_t *ctx, int argc, char **argv)
{
    (void)argc; (void)argv;
    ctx->logging_console = false;
    cli_print("Console logging disabled\n");
    ctx->modified = true;
    return SHIELD_OK;
}

/* logging buffered */
static shield_err_t cmd_logging_buffered(cli_context_t *ctx, int argc, char **argv)
{
    int size = 4096;
    if (argc >= 3) {
        size = atoi(argv[2]);
    }
    ctx->logging_buffered_size = size;
    cli_print("Logging buffer size set to %d\n", size);
    ctx->modified = true;
    return SHIELD_OK;
}

/* logging host */
static shield_err_t cmd_logging_host(cli_context_t *ctx, int argc, char **argv)
{
    if (argc < 3) {
        cli_print("%% Usage: logging host <ip-address>\n");
        return SHIELD_OK;
    }
    strncpy(ctx->logging_host, argv[2], sizeof(ctx->logging_host) - 1);
    cli_print("Syslog host set to %s\n", argv[2]);
    ctx->modified = true;
    return SHIELD_OK;
}

/* ntp server */
static shield_err_t cmd_ntp_server(cli_context_t *ctx, int argc, char **argv)
{
    if (argc < 3) {
        cli_print("%% Usage: ntp server <ip-address>\n");
        return SHIELD_OK;
    }
    strncpy(ctx->ntp_server, argv[2], sizeof(ctx->ntp_server) - 1);
    cli_print("NTP server set to %s\n", argv[2]);
    ctx->modified = true;
    return SHIELD_OK;
}

/* clock timezone */
static shield_err_t cmd_clock_timezone(cli_context_t *ctx, int argc, char **argv)
{
    if (argc < 3) {
        cli_print("%% Usage: clock timezone <zone>\n");
        return SHIELD_OK;
    }
    strncpy(ctx->timezone, argv[2], sizeof(ctx->timezone) - 1);
    cli_print("Timezone set to %s\n", argv[2]);
    ctx->modified = true;
    return SHIELD_OK;
}

/* banner motd */
static shield_err_t cmd_banner_motd(cli_context_t *ctx, int argc, char **argv)
{
    if (argc < 3) {
        cli_print("%% Usage: banner motd <delimiter> <text> <delimiter>\n");
        return SHIELD_OK;
    }
    strncpy(ctx->banner_motd, argv[2], sizeof(ctx->banner_motd) - 1);
    cli_print("MOTD banner configured\n");
    ctx->modified = true;
    return SHIELD_OK;
}

/* service password-encryption */
static shield_err_t cmd_service_password_enc(cli_context_t *ctx, int argc, char **argv)
{
    (void)argc; (void)argv;
    ctx->service_password_encryption = true;
    cli_print("Password encryption enabled\n");
    ctx->modified = true;
    return SHIELD_OK;
}

/* snmp-server community */
static shield_err_t cmd_snmp_community(cli_context_t *ctx, int argc, char **argv)
{
    if (argc < 4) {
        cli_print("%% Usage: snmp-server community <string> <ro|rw>\n");
        return SHIELD_OK;
    }
    strncpy(ctx->snmp_community, argv[2], sizeof(ctx->snmp_community) - 1);
    ctx->snmp_readonly = (strcmp(argv[3], "ro") == 0);
    cli_print("SNMP community configured\n");
    ctx->modified = true;
    return SHIELD_OK;
}

/* snmp-server host */
static shield_err_t cmd_snmp_host(cli_context_t *ctx, int argc, char **argv)
{
    if (argc < 3) {
        cli_print("%% Usage: snmp-server host <ip-address>\n");
        return SHIELD_OK;
    }
    strncpy(ctx->snmp_host, argv[2], sizeof(ctx->snmp_host) - 1);
    cli_print("SNMP host configured\n");
    ctx->modified = true;
    return SHIELD_OK;
}

/* aaa authentication */
static shield_err_t cmd_aaa_authentication(cli_context_t *ctx, int argc, char **argv)
{
    if (argc < 4) {
        cli_print("%% Usage: aaa authentication login <name> <method>\n");
        return SHIELD_OK;
    }
    strncpy(ctx->aaa_method, argv[3], sizeof(ctx->aaa_method) - 1);
    cli_print("AAA authentication configured\n");
    ctx->modified = true;
    return SHIELD_OK;
}

/* ip domain-name */
static shield_err_t cmd_ip_domain(cli_context_t *ctx, int argc, char **argv)
{
    if (argc < 3) {
        cli_print("%% Usage: ip domain-name <domain>\n");
        return SHIELD_OK;
    }
    strncpy(ctx->domain_name, argv[2], sizeof(ctx->domain_name) - 1);
    cli_print("Domain name set to %s\n", argv[2]);
    ctx->modified = true;
    return SHIELD_OK;
}

/* ip name-server */
static shield_err_t cmd_ip_nameserver(cli_context_t *ctx, int argc, char **argv)
{
    if (argc < 3) {
        cli_print("%% Usage: ip name-server <ip-address>\n");
        return SHIELD_OK;
    }
    strncpy(ctx->dns_server, argv[2], sizeof(ctx->dns_server) - 1);
    cli_print("DNS server set to %s\n", argv[2]);
    ctx->modified = true;
    return SHIELD_OK;
}

/* api enable */
static shield_err_t cmd_api_enable(cli_context_t *ctx, int argc, char **argv)
{
    (void)argc; (void)argv;
    ctx->api_enabled = true;
    cli_print("API enabled on port %d\n", ctx->api_port);
    ctx->modified = true;
    return SHIELD_OK;
}

/* no api enable */
static shield_err_t cmd_no_api_enable(cli_context_t *ctx, int argc, char **argv)
{
    (void)argc; (void)argv;
    ctx->api_enabled = false;
    cli_print("API disabled\n");
    ctx->modified = true;
    return SHIELD_OK;
}

/* api port */
static shield_err_t cmd_api_port(cli_context_t *ctx, int argc, char **argv)
{
    if (argc < 3) {
        cli_print("API port: %d\n", ctx->api_port);
        return SHIELD_OK;
    }
    ctx->api_port = atoi(argv[2]);
    cli_print("API port set to %d\n", ctx->api_port);
    ctx->modified = true;
    return SHIELD_OK;
}

/* api token */
static shield_err_t cmd_api_token(cli_context_t *ctx, int argc, char **argv)
{
    if (argc < 3) {
        cli_print("%% Usage: api token <token>\n");
        return SHIELD_OK;
    }
    strncpy(ctx->api_token, argv[2], sizeof(ctx->api_token) - 1);
    cli_print("API token configured\n");
    ctx->modified = true;
    return SHIELD_OK;
}

/* metrics enable */
static shield_err_t cmd_metrics_enable(cli_context_t *ctx, int argc, char **argv)
{
    (void)argc; (void)argv;
    ctx->metrics_enabled = true;
    cli_print("Metrics enabled on port %d\n", ctx->metrics_port);
    ctx->modified = true;
    return SHIELD_OK;
}

/* metrics port */
static shield_err_t cmd_metrics_port(cli_context_t *ctx, int argc, char **argv)
{
    if (argc < 3) {
        cli_print("Metrics port: %d\n", ctx->metrics_port);
        return SHIELD_OK;
    }
    ctx->metrics_port = atoi(argv[2]);
    cli_print("Metrics port set to %d\n", ctx->metrics_port);
    ctx->modified = true;
    return SHIELD_OK;
}

/* archive path */
static shield_err_t cmd_archive_path(cli_context_t *ctx, int argc, char **argv)
{
    if (argc < 3) {
        cli_print("Archive path: %s\n", ctx->archive_path);
        return SHIELD_OK;
    }
    strncpy(ctx->archive_path, argv[2], sizeof(ctx->archive_path) - 1);
    cli_print("Archive path set to %s\n", argv[2]);
    ctx->modified = true;
    return SHIELD_OK;
}

/* archive maximum */
static shield_err_t cmd_archive_maximum(cli_context_t *ctx, int argc, char **argv)
{
    if (argc < 3) {
        cli_print("Archive maximum: %d\n", ctx->archive_max);
        return SHIELD_OK;
    }
    ctx->archive_max = atoi(argv[2]);
    cli_print("Archive maximum set to %d\n", ctx->archive_max);
    ctx->modified = true;
    return SHIELD_OK;
}

/* Note: cmd_end is implemented in commands.c */

/* do */
static shield_err_t cmd_do(cli_context_t *ctx, int argc, char **argv)
{
    if (argc < 2) {
        cli_print("%% Usage: do <exec-command>\n");
        return SHIELD_OK;
    }
    cli_execute_args(ctx, argc - 1, argv + 1);
    return SHIELD_OK;
}

/* Config command table */
static cli_command_t config_commands[] = {
    {"hostname", cmd_hostname, CLI_MODE_CONFIG, "Set hostname"},
    {"no hostname", cmd_no_hostname, CLI_MODE_CONFIG, "Reset hostname"},
    {"enable secret", cmd_enable_secret, CLI_MODE_CONFIG, "Set enable password"},
    {"username", cmd_username, CLI_MODE_CONFIG, "Add user"},
    {"logging level", cmd_logging_level, CLI_MODE_CONFIG, "Set logging level"},
    {"logging console", cmd_logging_console, CLI_MODE_CONFIG, "Enable console logging"},
    {"no logging console", cmd_no_logging_console, CLI_MODE_CONFIG, "Disable console logging"},
    {"logging buffered", cmd_logging_buffered, CLI_MODE_CONFIG, "Set log buffer size"},
    {"logging host", cmd_logging_host, CLI_MODE_CONFIG, "Set syslog host"},
    {"ntp server", cmd_ntp_server, CLI_MODE_CONFIG, "Set NTP server"},
    {"clock timezone", cmd_clock_timezone, CLI_MODE_CONFIG, "Set timezone"},
    {"banner motd", cmd_banner_motd, CLI_MODE_CONFIG, "Set MOTD"},
    {"service password-encryption", cmd_service_password_enc, CLI_MODE_CONFIG, "Enable encryption"},
    {"snmp-server community", cmd_snmp_community, CLI_MODE_CONFIG, "Set SNMP community"},
    {"snmp-server host", cmd_snmp_host, CLI_MODE_CONFIG, "Set SNMP host"},
    {"aaa authentication", cmd_aaa_authentication, CLI_MODE_CONFIG, "Set AAA"},
    {"ip domain-name", cmd_ip_domain, CLI_MODE_CONFIG, "Set domain name"},
    {"ip name-server", cmd_ip_nameserver, CLI_MODE_CONFIG, "Set DNS server"},
    {"api enable", cmd_api_enable, CLI_MODE_CONFIG, "Enable API"},
    {"no api enable", cmd_no_api_enable, CLI_MODE_CONFIG, "Disable API"},
    {"api port", cmd_api_port, CLI_MODE_CONFIG, "Set API port"},
    {"api token", cmd_api_token, CLI_MODE_CONFIG, "Set API token"},
    {"metrics enable", cmd_metrics_enable, CLI_MODE_CONFIG, "Enable metrics"},
    {"metrics port", cmd_metrics_port, CLI_MODE_CONFIG, "Set metrics port"},
    {"archive path", cmd_archive_path, CLI_MODE_CONFIG, "Set archive path"},
    {"archive maximum", cmd_archive_maximum, CLI_MODE_CONFIG, "Set archive max"},
    /* Note: cmd_end is handled in commands.c with correct return type */
    {"do", cmd_do, CLI_MODE_CONFIG, "Run exec command"},
    {NULL, NULL, 0, NULL}
};

/* Register config commands */
void register_config_commands(cli_context_t *ctx)
{
    for (int i = 0; config_commands[i].name != NULL; i++) {
        cli_register_command(ctx, &config_commands[i]);
    }
}
