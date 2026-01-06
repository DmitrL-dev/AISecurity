/*
 * SENTINEL Shield - Main Entry Point
 * 
 * The DMZ your AI deserves.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <signal.h>

#include "sentinel_shield.h"

/* Global context */
static shield_context_t g_ctx;
static volatile bool g_running = true;

/* Signal handler */
static void signal_handler(int signum)
{
    (void)signum;
    g_running = false;
    printf("\nShutting down...\n");
}

/* Print usage */
static void print_usage(const char *prog)
{
    printf("SENTINEL Shield v%s\n\n", SHIELD_VERSION_STRING);
    printf("Usage: %s [OPTIONS]\n\n", prog);
    printf("Options:\n");
    printf("  -c, --config FILE    Configuration file path\n");
    printf("  -d, --daemon         Run as daemon\n");
    printf("  -v, --verbose        Verbose logging\n");
    printf("  -h, --help           Show this help\n");
    printf("  --version            Show version\n");
    printf("  --validate-config    Validate config and exit\n");
    printf("\n");
    printf("Examples:\n");
    printf("  %s -c /etc/shield/config.json\n", prog);
    printf("  %s --validate-config config.json\n", prog);
    printf("\n");
}

/* Print version */
static void print_version(void)
{
    printf("SENTINEL Shield v%s\n", SHIELD_VERSION_STRING);
    printf("Build: %s %s\n", __DATE__, __TIME__);
    printf("Platform: ");
#ifdef SHIELD_PLATFORM_WINDOWS
    printf("Windows\n");
#elif defined(SHIELD_PLATFORM_LINUX)
    printf("Linux\n");
#elif defined(SHIELD_PLATFORM_MACOS)
    printf("macOS\n");
#else
    printf("Unknown\n");
#endif
    printf("\nComponents:\n");
    printf("  - 64 modules\n");
    printf("  - 6 protocols (STP, SBP, ZDP, SHSP, SAF, SSRP)\n");
    printf("  - 6 guards (LLM, RAG, Agent, Tool, MCP, API)\n");
    printf("\n\"We're small, but WE CAN.\"\n");
}

/* Parse arguments */
static int parse_args(int argc, char **argv, char *config_path, bool *daemon, 
                       bool *verbose, bool *validate_only)
{
    *daemon = false;
    *verbose = false;
    *validate_only = false;
    config_path[0] = '\0';
    
    for (int i = 1; i < argc; i++) {
        if (strcmp(argv[i], "-h") == 0 || strcmp(argv[i], "--help") == 0) {
            print_usage(argv[0]);
            return -1;
        }
        else if (strcmp(argv[i], "--version") == 0) {
            print_version();
            return -1;
        }
        else if (strcmp(argv[i], "-c") == 0 || strcmp(argv[i], "--config") == 0) {
            if (i + 1 < argc) {
                strncpy(config_path, argv[++i], sizeof(config_path) - 1);
            } else {
                fprintf(stderr, "Error: -c requires a file path\n");
                return 1;
            }
        }
        else if (strcmp(argv[i], "-d") == 0 || strcmp(argv[i], "--daemon") == 0) {
            *daemon = true;
        }
        else if (strcmp(argv[i], "-v") == 0 || strcmp(argv[i], "--verbose") == 0) {
            *verbose = true;
        }
        else if (strcmp(argv[i], "--validate-config") == 0) {
            *validate_only = true;
        }
        else {
            fprintf(stderr, "Unknown option: %s\n", argv[i]);
            return 1;
        }
    }
    
    return 0;
}

/* Initialize components */
static shield_err_t init_components(void)
{
    shield_err_t err;
    
    /* Initialize TLS */
    err = tls_init();
    if (err != SHIELD_OK) {
        LOG_WARN("TLS initialization failed (non-fatal)");
    }
    
    /* Initialize metrics */
    err = metrics_init(&g_ctx.metrics);
    if (err != SHIELD_OK) {
        LOG_ERROR("Metrics initialization failed");
        return err;
    }
    
    /* Initialize thread pool */
    err = threadpool_create(&g_ctx.pool, 4);
    if (err != SHIELD_OK) {
        LOG_ERROR("Thread pool creation failed");
        return err;
    }
    
    /* Initialize event bus */
    err = event_bus_init(&g_ctx.events);
    if (err != SHIELD_OK) {
        LOG_ERROR("Event bus initialization failed");
        return err;
    }
    
    return SHIELD_OK;
}

/* Run main loop */
static void run_loop(void)
{
    LOG_INFO("SENTINEL Shield running...");
    LOG_INFO("API endpoint: http://0.0.0.0:%d", g_ctx.api_port > 0 ? g_ctx.api_port : 8080);
    LOG_INFO("Metrics endpoint: http://0.0.0.0:%d/metrics", 
             g_ctx.metrics_port > 0 ? g_ctx.metrics_port : 9090);
    LOG_INFO("Press Ctrl+C to stop");
    
    while (g_running) {
        /* Process events */
        event_t event;
        if (event_bus_receive(&g_ctx.events, &event, 1000) == SHIELD_OK) {
            /* Handle event */
            switch (event.type) {
            case EVENT_REQUEST:
                metrics_inc(&g_ctx.metrics, "requests_total");
                break;
            case EVENT_ALERT:
                metrics_inc(&g_ctx.metrics, "alerts_total");
                break;
            default:
                break;
            }
        }
        
        /* Health check */
        health_check(&g_ctx);
    }
}

/* Cleanup */
static void cleanup(void)
{
    LOG_INFO("Cleaning up...");
    
    threadpool_destroy(&g_ctx.pool);
    event_bus_destroy(&g_ctx.events);
    metrics_destroy(&g_ctx.metrics);
    tls_cleanup();
    
    shield_destroy(&g_ctx);
    
    LOG_INFO("Shutdown complete");
}

/* Main entry */
int main(int argc, char **argv)
{
    char config_path[256] = "";
    bool daemon_mode = false;
    bool verbose = false;
    bool validate_only = false;
    
    /* Parse arguments */
    int parse_result = parse_args(argc, argv, config_path, &daemon_mode, 
                                   &verbose, &validate_only);
    if (parse_result != 0) {
        return parse_result < 0 ? 0 : 1;
    }
    
    /* Set up signal handlers */
    signal(SIGINT, signal_handler);
    signal(SIGTERM, signal_handler);
    
    /* Banner */
    printf("\n");
    printf("╔══════════════════════════════════════════════════════════╗\n");
    printf("║                   SENTINEL SHIELD                         ║\n");
    printf("║                      v%s                              ║\n", SHIELD_VERSION_STRING);
    printf("║                                                          ║\n");
    printf("║         The DMZ Your AI Deserves                         ║\n");
    printf("║         \"We're small, but WE CAN.\"                       ║\n");
    printf("╚══════════════════════════════════════════════════════════╝\n");
    printf("\n");
    
    /* Initialize context */
    shield_err_t err = shield_init(&g_ctx);
    if (err != SHIELD_OK) {
        fprintf(stderr, "Failed to initialize Shield: %d\n", err);
        return 1;
    }
    
    /* Load configuration */
    if (config_path[0] != '\0') {
        LOG_INFO("Loading configuration: %s", config_path);
        err = shield_load_config(&g_ctx, config_path);
        if (err != SHIELD_OK) {
            fprintf(stderr, "Failed to load config: %d\n", err);
            shield_destroy(&g_ctx);
            return 1;
        }
        
        if (validate_only) {
            printf("Config validation: OK\n");
            printf("  - Zones: %d defined\n", g_ctx.zone_count);
            printf("  - Rules: %d defined\n", g_ctx.rule_count);
            printf("  - Guards: %d enabled\n", g_ctx.guard_count);
            shield_destroy(&g_ctx);
            return 0;
        }
    } else {
        LOG_INFO("No config file specified, using defaults");
    }
    
    /* Set verbose logging */
    if (verbose) {
        g_ctx.log_level = LOG_LEVEL_DEBUG;
    }
    
    /* Initialize components */
    err = init_components();
    if (err != SHIELD_OK) {
        fprintf(stderr, "Failed to initialize components: %d\n", err);
        shield_destroy(&g_ctx);
        return 1;
    }
    
    /* Daemon mode */
    if (daemon_mode) {
#ifndef SHIELD_PLATFORM_WINDOWS
        if (daemon(0, 0) < 0) {
            perror("daemon");
            return 1;
        }
#else
        LOG_WARN("Daemon mode not supported on Windows");
#endif
    }
    
    /* Run main loop */
    run_loop();
    
    /* Cleanup */
    cleanup();
    
    return 0;
}
