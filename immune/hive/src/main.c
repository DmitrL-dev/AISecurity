/*
 * SENTINEL IMMUNE — Hive Daemon
 * 
 * Main entry point for Hive server.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <signal.h>
#include <syslog.h>
#include <getopt.h>
#include <sys/stat.h>
#include <pwd.h>

#include "../include/hive.h"

#define PID_FILE        "/var/run/hived.pid"
#define CONFIG_FILE     "/etc/immune/hive.conf"
#define DATA_DIR        "/var/immune/hive"

/* Global hive context */
static immune_hive_t g_hive;

/* Forward declarations */
void* hive_api_thread(void *arg);
void* hive_network_thread(void *arg);

/* Signal handler */
static void
signal_handler(int sig)
{
    switch (sig) {
    case SIGTERM:
    case SIGINT:
        syslog(LOG_INFO, "Shutdown signal received");
        g_hive.running = false;
        break;
    case SIGHUP:
        syslog(LOG_INFO, "Reload signal received");
        break;
    }
}

/* Create PID file */
static int
create_pidfile(void)
{
    FILE *fp = fopen(PID_FILE, "w");
    if (!fp)
        return -1;
    
    fprintf(fp, "%d\n", getpid());
    fclose(fp);
    return 0;
}

/* Daemonize process */
static int
daemonize(void)
{
    pid_t pid;
    
    pid = fork();
    if (pid < 0)
        exit(EXIT_FAILURE);
    if (pid > 0)
        exit(EXIT_SUCCESS);
    
    if (setsid() < 0)
        exit(EXIT_FAILURE);
    
    signal(SIGCHLD, SIG_IGN);
    signal(SIGHUP, signal_handler);
    signal(SIGTERM, signal_handler);
    signal(SIGINT, signal_handler);
    
    pid = fork();
    if (pid < 0)
        exit(EXIT_FAILURE);
    if (pid > 0)
        exit(EXIT_SUCCESS);
    
    umask(0077);
    chdir("/");
    
    close(STDIN_FILENO);
    close(STDOUT_FILENO);
    close(STDERR_FILENO);
    
    return 0;
}

/* Monitor agents for offline status */
static void*
monitor_thread(void *arg)
{
    immune_hive_t *hive = (immune_hive_t *)arg;
    
    while (hive->running) {
        time_t now = time(NULL);
        
        pthread_mutex_lock(&hive->agents_lock);
        
        for (uint32_t i = 1; i < MAX_AGENTS; i++) {
            if (!hive->agents[i].active)
                continue;
            
            if (hive->agents[i].status == AGENT_STATUS_ONLINE) {
                time_t elapsed = now - hive->agents[i].last_heartbeat;
                
                if (elapsed > HEARTBEAT_TIMEOUT) {
                    hive->agents[i].status = AGENT_STATUS_OFFLINE;
                    hive->stats.agents_online--;
                    hive->stats.agents_offline++;
                    
                    syslog(LOG_WARNING, "Agent %u went offline", i);
                }
            }
        }
        
        pthread_mutex_unlock(&hive->agents_lock);
        
        sleep(30);
    }
    
    return NULL;
}

/* Usage */
static void
usage(const char *prog)
{
    fprintf(stderr, "SENTINEL IMMUNE Hive v%s\n\n", HIVE_VERSION);
    fprintf(stderr, "Usage: %s [options]\n\n", prog);
    fprintf(stderr, "Options:\n");
    fprintf(stderr, "  -d            Don't daemonize (foreground)\n");
    fprintf(stderr, "  -c <file>     Config file (default: %s)\n", CONFIG_FILE);
    fprintf(stderr, "  -D <dir>      Data directory (default: %s)\n", DATA_DIR);
    fprintf(stderr, "  -p <port>     API port (default: 9999)\n");
    fprintf(stderr, "  -a <port>     Agent port (default: 9998)\n");
    fprintf(stderr, "  -v            Verbose logging\n");
    fprintf(stderr, "  -h            Show this help\n");
    exit(EXIT_FAILURE);
}

/* Main */
int
main(int argc, char *argv[])
{
    int foreground = 0;
    int verbose = 0;
    char *config_file = CONFIG_FILE;
    char *data_dir = DATA_DIR;
    uint16_t api_port = 9999;
    uint16_t agent_port = 9998;
    int opt;
    
    /* Parse arguments */
    while ((opt = getopt(argc, argv, "dc:D:p:a:vh")) != -1) {
        switch (opt) {
        case 'd':
            foreground = 1;
            break;
        case 'c':
            config_file = optarg;
            break;
        case 'D':
            data_dir = optarg;
            break;
        case 'p':
            api_port = atoi(optarg);
            break;
        case 'a':
            agent_port = atoi(optarg);
            break;
        case 'v':
            verbose = 1;
            break;
        case 'h':
        default:
            usage(argv[0]);
        }
    }
    
    /* Open syslog */
    openlog("HIVE", LOG_PID | LOG_CONS, 
            foreground ? LOG_USER : LOG_DAEMON);
    
    syslog(LOG_INFO, "SENTINEL IMMUNE Hive v%s starting", HIVE_VERSION);
    
    /* Daemonize unless foreground */
    if (!foreground) {
        if (daemonize() != 0) {
            syslog(LOG_ERR, "Daemonization failed");
            exit(EXIT_FAILURE);
        }
    }
    
    /* Create PID file */
    create_pidfile();
    
    /* Create data directory */
    mkdir(data_dir, 0700);
    
    /* Initialize Hive */
    if (hive_init(&g_hive, data_dir) != 0) {
        syslog(LOG_ERR, "Hive initialization failed");
        exit(EXIT_FAILURE);
    }
    
    g_hive.api_port = api_port;
    g_hive.agent_port = agent_port;
    g_hive.running = true;
    
    syslog(LOG_INFO, "Hive initialized, data_dir=%s", data_dir);
    
    /* Start threads */
    pthread_create(&g_hive.api_thread, NULL, hive_api_thread, &g_hive);
    pthread_create(&g_hive.agent_thread, NULL, hive_network_thread, &g_hive);
    pthread_create(&g_hive.monitor_thread, NULL, monitor_thread, &g_hive);
    
    syslog(LOG_INFO, "Hive ready: API=%d, Agent=%d", api_port, agent_port);
    
    if (foreground) {
        printf("\n");
        printf("=== SENTINEL IMMUNE HIVE ===\n");
        printf("Version:    %s\n", HIVE_VERSION);
        printf("API Port:   %d\n", api_port);
        printf("Agent Port: %d\n", agent_port);
        printf("Data Dir:   %s\n", data_dir);
        printf("============================\n");
        printf("Press Ctrl+C to stop\n\n");
    }
    
    /* Wait for threads */
    pthread_join(g_hive.api_thread, NULL);
    pthread_join(g_hive.agent_thread, NULL);
    pthread_join(g_hive.monitor_thread, NULL);
    
    /* Cleanup */
    hive_shutdown(&g_hive);
    
    unlink(PID_FILE);
    closelog();
    
    return EXIT_SUCCESS;
}
