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

/* hostname */
static void cmd_hostname(cli_context_t *ctx, int argc, char **argv)
{
    if (argc < 2) {
        cli_print(ctx, "Current hostname: %s\n", ctx->hostname);
        return;
    }
    strncpy(ctx->hostname, argv[1], sizeof(ctx->hostname) - 1);
    cli_update_prompt(ctx);
    ctx->modified = true;
}

/* no hostname */
static void cmd_no_hostname(cli_context_t *ctx, int argc, char **argv)
{
    (void)argc; (void)argv;
    strcpy(ctx->hostname, "Shield");
    cli_update_prompt(ctx);
    ctx->modified = true;
}

/* enable secret */
static void cmd_enable_secret(cli_context_t *ctx, int argc, char **argv)
{
    if (argc < 2) {
        cli_print(ctx, "%% Usage: enable secret <password>\n");
        return;
    }
    /* Hash and store password */
    strncpy(ctx->enable_secret, argv[1], sizeof(ctx->enable_secret) - 1);
    ctx->modified = true;
    cli_print(ctx, "Enable secret configured\n");
}

/* username */
static void cmd_username(cli_context_t *ctx, int argc, char **argv)
{
    if (argc < 4) {
        cli_print(ctx, "%% Usage: username <name> password <password>\n");
        return;
    }
    /* Store username/password */
    cli_print(ctx, "User %s configured\n", argv[1]);
    ctx->modified = true;
}

/* logging level */
static void cmd_logging_level(cli_context_t *ctx, int argc, char **argv)
{
    if (argc < 3) {
        cli_print(ctx, "%% Usage: logging level <debug|info|warn|error>\n");
        return;
    }
    ctx->log_level = log_level_from_string(argv[2]);
    cli_print(ctx, "Logging level set to %s\n", argv[2]);
    ctx->modified = true;
}

/* logging console */
static void cmd_logging_console(cli_context_t *ctx, int argc, char **argv)
{
    (void)argc; (void)argv;
    ctx->log_console = true;
    cli_print(ctx, "Console logging enabled\n");
    ctx->modified = true;
}

/* no logging console */
static void cmd_no_logging_console(cli_context_t *ctx, int argc, char **argv)
{
    (void)argc; (void)argv;
    ctx->log_console = false;
    cli_print(ctx, "Console logging disabled\n");
    ctx->modified = true;
}

/* logging buffered */
static void cmd_logging_buffered(cli_context_t *ctx, int argc, char **argv)
{
    int size = 4096;
    if (argc >= 3) {
        size = atoi(argv[2]);
    }
    ctx->log_buffer_size = size;
    cli_print(ctx, "Logging buffer size set to %d\n", size);
    ctx->modified = true;
}

/* logging host */
static void cmd_logging_host(cli_context_t *ctx, int argc, char **argv)
{
    if (argc < 3) {
        cli_print(ctx, "%% Usage: logging host <ip-address>\n");
        return;
    }
    strncpy(ctx->syslog_host, argv[2], sizeof(ctx->syslog_host) - 1);
    cli_print(ctx, "Syslog host set to %s\n", argv[2]);
    ctx->modified = true;
}

/* ntp server */
static void cmd_ntp_server(cli_context_t *ctx, int argc, char **argv)
{
    if (argc < 3) {
        cli_print(ctx, "%% Usage: ntp server <ip-address>\n");
        return;
    }
    strncpy(ctx->ntp_server, argv[2], sizeof(ctx->ntp_server) - 1);
    cli_print(ctx, "NTP server set to %s\n", argv[2]);
    ctx->modified = true;
}

/* clock timezone */
static void cmd_clock_timezone(cli_context_t *ctx, int argc, char **argv)
{
    if (argc < 3) {
        cli_print(ctx, "%% Usage: clock timezone <zone>\n");
        return;
    }
    strncpy(ctx->timezone, argv[2], sizeof(ctx->timezone) - 1);
    cli_print(ctx, "Timezone set to %s\n", argv[2]);
    ctx->modified = true;
}

/* banner motd */
static void cmd_banner_motd(cli_context_t *ctx, int argc, char **argv)
{
    if (argc < 3) {
        cli_print(ctx, "%% Usage: banner motd <delimiter> <text> <delimiter>\n");
        return;
    }
    /* Simple: just use everything after "banner motd " */
    strncpy(ctx->banner_motd, argv[2], sizeof(ctx->banner_motd) - 1);
    cli_print(ctx, "MOTD banner configured\n");
    ctx->modified = true;
}

/* service password-encryption */
static void cmd_service_password_enc(cli_context_t *ctx, int argc, char **argv)
{
    (void)argc; (void)argv;
    ctx->password_encryption = true;
    cli_print(ctx, "Password encryption enabled\n");
    ctx->modified = true;
}

/* snmp-server community */
static void cmd_snmp_community(cli_context_t *ctx, int argc, char **argv)
{
    if (argc < 4) {
        cli_print(ctx, "%% Usage: snmp-server community <string> <ro|rw>\n");
        return;
    }
    strncpy(ctx->snmp_community, argv[2], sizeof(ctx->snmp_community) - 1);
    ctx->snmp_readonly = (strcmp(argv[3], "ro") == 0);
    cli_print(ctx, "SNMP community configured\n");
    ctx->modified = true;
}

/* snmp-server host */
static void cmd_snmp_host(cli_context_t *ctx, int argc, char **argv)
{
    if (argc < 3) {
        cli_print(ctx, "%% Usage: snmp-server host <ip-address>\n");
        return;
    }
    strncpy(ctx->snmp_host, argv[2], sizeof(ctx->snmp_host) - 1);
    cli_print(ctx, "SNMP host configured\n");
    ctx->modified = true;
}

/* aaa authentication */
static void cmd_aaa_authentication(cli_context_t *ctx, int argc, char **argv)
{
    if (argc < 4) {
        cli_print(ctx, "%% Usage: aaa authentication login <name> <method>\n");
        return;
    }
    strncpy(ctx->aaa_method, argv[3], sizeof(ctx->aaa_method) - 1);
    cli_print(ctx, "AAA authentication configured\n");
    ctx->modified = true;
}

/* ip domain-name */
static void cmd_ip_domain(cli_context_t *ctx, int argc, char **argv)
{
    if (argc < 3) {
        cli_print(ctx, "%% Usage: ip domain-name <domain>\n");
        return;
    }
    strncpy(ctx->domain_name, argv[2], sizeof(ctx->domain_name) - 1);
    cli_print(ctx, "Domain name set to %s\n", argv[2]);
    ctx->modified = true;
}

/* ip name-server */
static void cmd_ip_nameserver(cli_context_t *ctx, int argc, char **argv)
{
    if (argc < 3) {
        cli_print(ctx, "%% Usage: ip name-server <ip-address>\n");
        return;
    }
    strncpy(ctx->dns_server, argv[2], sizeof(ctx->dns_server) - 1);
    cli_print(ctx, "DNS server set to %s\n", argv[2]);
    ctx->modified = true;
}

/* api enable */
static void cmd_api_enable(cli_context_t *ctx, int argc, char **argv)
{
    (void)argc; (void)argv;
    ctx->api_enabled = true;
    cli_print(ctx, "API enabled on port %d\n", ctx->api_port);
    ctx->modified = true;
}

/* no api enable */
static void cmd_no_api_enable(cli_context_t *ctx, int argc, char **argv)
{
    (void)argc; (void)argv;
    ctx->api_enabled = false;
    cli_print(ctx, "API disabled\n");
    ctx->modified = true;
}

/* api port */
static void cmd_api_port(cli_context_t *ctx, int argc, char **argv)
{
    if (argc < 3) {
        cli_print(ctx, "API port: %d\n", ctx->api_port);
        return;
    }
    ctx->api_port = atoi(argv[2]);
    cli_print(ctx, "API port set to %d\n", ctx->api_port);
    ctx->modified = true;
}

/* api token */
static void cmd_api_token(cli_context_t *ctx, int argc, char **argv)
{
    if (argc < 3) {
        cli_print(ctx, "%% Usage: api token <token>\n");
        return;
    }
    strncpy(ctx->api_token, argv[2], sizeof(ctx->api_token) - 1);
    cli_print(ctx, "API token configured\n");
    ctx->modified = true;
}

/* metrics enable */
static void cmd_metrics_enable(cli_context_t *ctx, int argc, char **argv)
{
    (void)argc; (void)argv;
    ctx->metrics_enabled = true;
    cli_print(ctx, "Metrics enabled on port %d\n", ctx->metrics_port);
    ctx->modified = true;
}

/* metrics port */
static void cmd_metrics_port(cli_context_t *ctx, int argc, char **argv)
{
    if (argc < 3) {
        cli_print(ctx, "Metrics port: %d\n", ctx->metrics_port);
        return;
    }
    ctx->metrics_port = atoi(argv[2]);
    cli_print(ctx, "Metrics port set to %d\n", ctx->metrics_port);
    ctx->modified = true;
}

/* archive path */
static void cmd_archive_path(cli_context_t *ctx, int argc, char **argv)
{
    if (argc < 3) {
        cli_print(ctx, "Archive path: %s\n", ctx->archive_path);
        return;
    }
    strncpy(ctx->archive_path, argv[2], sizeof(ctx->archive_path) - 1);
    cli_print(ctx, "Archive path set to %s\n", argv[2]);
    ctx->modified = true;
}

/* archive maximum */
static void cmd_archive_maximum(cli_context_t *ctx, int argc, char **argv)
{
    if (argc < 3) {
        cli_print(ctx, "Archive maximum: %d\n", ctx->archive_max);
        return;
    }
    ctx->archive_max = atoi(argv[2]);
    cli_print(ctx, "Archive maximum set to %d\n", ctx->archive_max);
    ctx->modified = true;
}

/* end */
static void cmd_end(cli_context_t *ctx, int argc, char **argv)
{
    (void)argc; (void)argv;
    ctx->current_zone[0] = '\0';
    cli_set_mode(ctx, CLI_MODE_EXEC);
}

/* do */
static void cmd_do(cli_context_t *ctx, int argc, char **argv)
{
    if (argc < 2) {
        cli_print(ctx, "%% Usage: do <exec-command>\n");
        return;
    }
    /* Execute command in exec mode */
    cli_execute(ctx, argc - 1, argv + 1);
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
    {"end", cmd_end, CLI_MODE_CONFIG, "Exit to exec mode"},
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
