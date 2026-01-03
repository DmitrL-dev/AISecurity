/*
 * SENTINEL IMMUNE — DragonFlyBSD Agent Daemon
 * 
 * Reads kernel events via sysctl and forwards to Hive.
 * 
 * Components:
 * - sysctl reader (kmod stats)
 * - Hive connector (TCP/TLS)
 * - Event processor
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <signal.h>
#include <errno.h>
#include <sys/types.h>
#include <sys/socket.h>
#include <sys/sysctl.h>
#include <netinet/in.h>
#include <netdb.h>
#include <time.h>

/* ==================== Configuration ==================== */

#define AGENT_VERSION       "1.0.0"
#define DEFAULT_HIVE_HOST   "localhost"
#define DEFAULT_HIVE_PORT   9998
#define POLL_INTERVAL_SEC   5
#define RECONNECT_DELAY     10

/* ==================== Structures ==================== */

typedef struct {
    int         enabled;
    int         block_mode;
    int         monitor_network;
    int         monitor_files;
    int         monitor_creds;
    uint64_t    events_total;
    uint64_t    threats_detected;
    uint64_t    threats_blocked;
    int         ring_count;
} kmod_stats_t;

typedef struct {
    char        hive_host[256];
    int         hive_port;
    int         hive_sock;
    int         connected;
    int         running;
    uint32_t    agent_id;
    uint64_t    last_events;
    uint64_t    last_threats;
} agent_state_t;

/* ==================== Globals ==================== */

static agent_state_t g_agent = {
    .hive_host = DEFAULT_HIVE_HOST,
    .hive_port = DEFAULT_HIVE_PORT,
    .hive_sock = -1,
    .connected = 0,
    .running = 1,
    .agent_id = 0,
    .last_events = 0,
    .last_threats = 0
};

/* ==================== Signal Handler ==================== */

static void
signal_handler(int sig)
{
    (void)sig;
    if (g_agent.running == 0) {
        /* Second signal = force exit */
        printf("\nForce exit!\n");
        _exit(1);
    }
    g_agent.running = 0;
    printf("\nIMMUNE Agent: Shutting down (Ctrl+C again to force)...\n");
}

/* ==================== Sysctl Reader ==================== */

static int
read_sysctl_int(const char *name, int *value)
{
    size_t len = sizeof(int);
    if (sysctlbyname(name, value, &len, NULL, 0) < 0) {
        return -1;
    }
    return 0;
}

static int
read_sysctl_uint64(const char *name, uint64_t *value)
{
    size_t len = sizeof(uint64_t);
    if (sysctlbyname(name, value, &len, NULL, 0) < 0) {
        return -1;
    }
    return 0;
}

static int
read_kmod_stats(kmod_stats_t *stats)
{
    memset(stats, 0, sizeof(*stats));
    
    if (read_sysctl_int("security.immune.enabled", &stats->enabled) < 0)
        return -1;
    
    read_sysctl_int("security.immune.block_mode", &stats->block_mode);
    read_sysctl_int("security.immune.monitor_network", &stats->monitor_network);
    read_sysctl_int("security.immune.monitor_files", &stats->monitor_files);
    read_sysctl_int("security.immune.monitor_creds", &stats->monitor_creds);
    read_sysctl_uint64("security.immune.events_total", &stats->events_total);
    read_sysctl_uint64("security.immune.threats_detected", &stats->threats_detected);
    read_sysctl_uint64("security.immune.threats_blocked", &stats->threats_blocked);
    read_sysctl_int("security.immune.ring_count", &stats->ring_count);
    
    return 0;
}

/* ==================== Hive Connection ==================== */

static int
connect_to_hive(void)
{
    struct sockaddr_in addr;
    struct hostent *host;
    
    /* Resolve hostname */
    host = gethostbyname(g_agent.hive_host);
    if (!host) {
        fprintf(stderr, "IMMUNE Agent: Cannot resolve %s\n", g_agent.hive_host);
        return -1;
    }
    
    /* Create socket */
    g_agent.hive_sock = socket(AF_INET, SOCK_STREAM, 0);
    if (g_agent.hive_sock < 0) {
        perror("IMMUNE Agent: socket");
        return -1;
    }
    
    /* Connect */
    memset(&addr, 0, sizeof(addr));
    addr.sin_family = AF_INET;
    addr.sin_port = htons(g_agent.hive_port);
    memcpy(&addr.sin_addr, host->h_addr, host->h_length);
    
    if (connect(g_agent.hive_sock, (struct sockaddr *)&addr, sizeof(addr)) < 0) {
        perror("IMMUNE Agent: connect");
        close(g_agent.hive_sock);
        g_agent.hive_sock = -1;
        return -1;
    }
    
    g_agent.connected = 1;
    printf("IMMUNE Agent: Connected to Hive at %s:%d\n",
           g_agent.hive_host, g_agent.hive_port);
    
    return 0;
}

static void
disconnect_from_hive(void)
{
    if (g_agent.hive_sock >= 0) {
        close(g_agent.hive_sock);
        g_agent.hive_sock = -1;
    }
    g_agent.connected = 0;
}

/* ==================== Event Reporting ==================== */

/* Simple JSON event format */
static int
send_event(const char *event_type, uint64_t count)
{
    if (!g_agent.connected || g_agent.hive_sock < 0)
        return -1;
    
    char buffer[512];
    int len = snprintf(buffer, sizeof(buffer),
        "{\"agent_id\":%u,\"type\":\"%s\",\"count\":%lu,\"time\":%ld}\n",
        g_agent.agent_id, event_type, count, time(NULL));
    
    ssize_t sent = send(g_agent.hive_sock, buffer, len, 0);
    if (sent < 0) {
        perror("IMMUNE Agent: send failed");
        disconnect_from_hive();
        return -1;
    }
    
    return 0;
}

static int
send_registration(void)
{
    if (!g_agent.connected)
        return -1;
    
    char buffer[512];
    char hostname[256] = "unknown";
    gethostname(hostname, sizeof(hostname));
    
    int len = snprintf(buffer, sizeof(buffer),
        "{\"type\":\"register\",\"hostname\":\"%s\",\"version\":\"%s\","
        "\"platform\":\"dragonflybsd\",\"kmod_version\":\"2.2.0\"}\n",
        hostname, AGENT_VERSION);
    
    ssize_t sent = send(g_agent.hive_sock, buffer, len, 0);
    if (sent < 0) {
        perror("IMMUNE Agent: registration failed");
        return -1;
    }
    
    /* Read agent ID response */
    char response[256];
    ssize_t received = recv(g_agent.hive_sock, response, sizeof(response) - 1, 0);
    if (received > 0) {
        response[received] = '\0';
        /* Parse agent_id from response (simplified) */
        char *id_str = strstr(response, "agent_id");
        if (id_str) {
            sscanf(id_str, "agent_id\":%u", &g_agent.agent_id);
        }
    }
    
    printf("IMMUNE Agent: Registered with agent_id=%u\n", g_agent.agent_id);
    return 0;
}

/* ==================== Main Loop ==================== */

static void
agent_loop(void)
{
    kmod_stats_t stats;
    int reconnect_timer = 0;
    
    while (g_agent.running) {
        /* Try to connect if not connected */
        if (!g_agent.connected) {
            if (reconnect_timer <= 0) {
                if (connect_to_hive() == 0) {
                    send_registration();
                } else {
                    reconnect_timer = RECONNECT_DELAY;
                }
            } else {
                reconnect_timer -= POLL_INTERVAL_SEC;
            }
        }
        
        /* Read kmod stats */
        if (read_kmod_stats(&stats) == 0) {
            /* Check for new events */
            if (stats.events_total > g_agent.last_events) {
                uint64_t new_events = stats.events_total - g_agent.last_events;
                printf("IMMUNE Agent: %lu new events (total: %lu)\n",
                       new_events, stats.events_total);
                
                if (g_agent.connected) {
                    send_event("events", new_events);
                }
                
                g_agent.last_events = stats.events_total;
            }
            
            /* Check for new threats */
            if (stats.threats_detected > g_agent.last_threats) {
                uint64_t new_threats = stats.threats_detected - g_agent.last_threats;
                printf("IMMUNE Agent: [ALERT] %lu new threats! (blocked: %lu)\n",
                       new_threats, stats.threats_blocked);
                
                if (g_agent.connected) {
                    send_event("threat", new_threats);
                }
                
                g_agent.last_threats = stats.threats_detected;
            }
        } else {
            fprintf(stderr, "IMMUNE Agent: Cannot read kmod stats. Is kmod loaded?\n");
        }
        
        sleep(POLL_INTERVAL_SEC);
    }
}

/* ==================== Usage ==================== */

static void
usage(const char *prog)
{
    printf("SENTINEL IMMUNE Agent Daemon v%s\n\n", AGENT_VERSION);
    printf("Usage: %s [options]\n", prog);
    printf("Options:\n");
    printf("  -h <host>    Hive hostname (default: %s)\n", DEFAULT_HIVE_HOST);
    printf("  -p <port>    Hive port (default: %d)\n", DEFAULT_HIVE_PORT);
    printf("  -d           Daemonize\n");
    printf("  -v           Verbose output\n");
    printf("  --help       Show this help\n");
    exit(0);
}

/* ==================== Main ==================== */

int
main(int argc, char *argv[])
{
    int daemonize = 0;
    
    /* Parse arguments */
    for (int i = 1; i < argc; i++) {
        if (strcmp(argv[i], "-h") == 0 && i + 1 < argc) {
            strncpy(g_agent.hive_host, argv[++i], sizeof(g_agent.hive_host) - 1);
        } else if (strcmp(argv[i], "-p") == 0 && i + 1 < argc) {
            g_agent.hive_port = atoi(argv[++i]);
        } else if (strcmp(argv[i], "-d") == 0) {
            daemonize = 1;
        } else if (strcmp(argv[i], "--help") == 0) {
            usage(argv[0]);
        }
    }
    
    printf("\n");
    printf("╔═══════════════════════════════════════╗\n");
    printf("║  SENTINEL IMMUNE Agent v%s        ║\n", AGENT_VERSION);
    printf("║  DragonFlyBSD Edition                 ║\n");
    printf("╠═══════════════════════════════════════╣\n");
    printf("║  Hive: %s:%d\n", g_agent.hive_host, g_agent.hive_port);
    printf("╚═══════════════════════════════════════╝\n");
    printf("\n");
    
    /* Check if kmod is loaded */
    kmod_stats_t stats;
    if (read_kmod_stats(&stats) < 0) {
        fprintf(stderr, "ERROR: IMMUNE kmod not loaded!\n");
        fprintf(stderr, "Run: kldload ./immune.ko\n");
        return 1;
    }
    
    printf("IMMUNE Agent: kmod detected (enabled=%d, events=%lu)\n",
           stats.enabled, stats.events_total);
    
    /* Daemonize if requested */
    if (daemonize) {
        if (daemon(0, 0) < 0) {
            perror("daemon");
            return 1;
        }
    }
    
    /* Setup signal handlers */
    signal(SIGINT, signal_handler);
    signal(SIGTERM, signal_handler);
    
    /* Run main loop */
    agent_loop();
    
    /* Cleanup */
    disconnect_from_hive();
    
    printf("IMMUNE Agent: Stopped\n");
    return 0;
}
