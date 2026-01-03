/*
 * SENTINEL IMMUNE — Minimal Hive Demo
 * 
 * Single-file demonstration of Hive functionality.
 * Compiles and runs on DragonFlyBSD/FreeBSD/Linux.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <signal.h>
#include <time.h>
#include <pthread.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>

#define VERSION         "1.0.0"
#define AGENT_PORT      9998
#define MAX_AGENTS      64
#define MAX_THREATS     256

/* Agent info */
typedef struct {
    int         active;
    uint32_t    id;
    char        hostname[64];
    char        ip[32];
    time_t      last_seen;
    int         threats;
} agent_t;

/* Threat event */
typedef struct {
    uint32_t    id;
    uint32_t    agent_id;
    time_t      timestamp;
    char        description[256];
    int         blocked;
} threat_t;

/* Hive state */
static struct {
    int         running;
    agent_t     agents[MAX_AGENTS];
    int         agent_count;
    threat_t    threats[MAX_THREATS];
    int         threat_count;
    pthread_mutex_t lock;
} hive;

/* Signal handler */
static void sighandler(int sig) {
    (void)sig;
    printf("\nHive shutting down...\n");
    hive.running = 0;
}

/* Register new agent */
static uint32_t register_agent(const char *hostname, const char *ip) {
    pthread_mutex_lock(&hive.lock);
    
    if (hive.agent_count >= MAX_AGENTS) {
        pthread_mutex_unlock(&hive.lock);
        return 0;
    }
    
    uint32_t id = hive.agent_count + 1;
    agent_t *a = &hive.agents[hive.agent_count++];
    
    a->active = 1;
    a->id = id;
    strncpy(a->hostname, hostname, sizeof(a->hostname) - 1);
    strncpy(a->ip, ip, sizeof(a->ip) - 1);
    a->last_seen = time(NULL);
    a->threats = 0;
    
    pthread_mutex_unlock(&hive.lock);
    
    printf("[HIVE] Agent registered: id=%u host=%s ip=%s\n", id, hostname, ip);
    return id;
}

/* Report threat */
static uint32_t report_threat(uint32_t agent_id, const char *desc, int blocked) {
    pthread_mutex_lock(&hive.lock);
    
    if (hive.threat_count >= MAX_THREATS) {
        pthread_mutex_unlock(&hive.lock);
        return 0;
    }
    
    uint32_t id = hive.threat_count + 1;
    threat_t *t = &hive.threats[hive.threat_count++];
    
    t->id = id;
    t->agent_id = agent_id;
    t->timestamp = time(NULL);
    strncpy(t->description, desc, sizeof(t->description) - 1);
    t->blocked = blocked;
    
    /* Update agent stats */
    for (int i = 0; i < hive.agent_count; i++) {
        if (hive.agents[i].id == agent_id) {
            hive.agents[i].threats++;
            hive.agents[i].last_seen = time(NULL);
            break;
        }
    }
    
    pthread_mutex_unlock(&hive.lock);
    
    printf("[HIVE] %s THREAT from agent %u: %s\n", 
           blocked ? "BLOCKED" : "DETECTED", agent_id, desc);
    return id;
}

/* Print status */
static void print_status(void) {
    pthread_mutex_lock(&hive.lock);
    
    printf("\n========== IMMUNE HIVE STATUS ==========\n");
    printf("Agents:  %d\n", hive.agent_count);
    printf("Threats: %d\n", hive.threat_count);
    printf("\nAgents:\n");
    for (int i = 0; i < hive.agent_count; i++) {
        agent_t *a = &hive.agents[i];
        printf("  [%u] %s (%s) - %d threats\n", 
               a->id, a->hostname, a->ip, a->threats);
    }
    printf("=========================================\n\n");
    
    pthread_mutex_unlock(&hive.lock);
}

/* Handle client connection */
static void* handle_client(void *arg) {
    int sock = *(int*)arg;
    free(arg);
    
    char buffer[1024];
    ssize_t n = recv(sock, buffer, sizeof(buffer) - 1, 0);
    
    if (n > 0) {
        buffer[n] = '\0';
        
        /* Parse simple text protocol:
         * REGISTER hostname
         * THREAT agent_id description blocked
         * STATUS
         */
        
        if (strncmp(buffer, "REGISTER ", 9) == 0) {
            char *hostname = buffer + 9;
            char *nl = strchr(hostname, '\n');
            if (nl) *nl = '\0';
            
            struct sockaddr_in addr;
            socklen_t len = sizeof(addr);
            getpeername(sock, (struct sockaddr*)&addr, &len);
            
            uint32_t id = register_agent(hostname, inet_ntoa(addr.sin_addr));
            
            char resp[64];
            snprintf(resp, sizeof(resp), "OK %u\n", id);
            send(sock, resp, strlen(resp), 0);
        }
        else if (strncmp(buffer, "THREAT ", 7) == 0) {
            uint32_t agent_id;
            int blocked;
            char desc[256];
            
            if (sscanf(buffer + 7, "%u %d %[^\n]", &agent_id, &blocked, desc) == 3) {
                uint32_t id = report_threat(agent_id, desc, blocked);
                
                char resp[64];
                snprintf(resp, sizeof(resp), "OK %u\n", id);
                send(sock, resp, strlen(resp), 0);
            }
        }
        else if (strncmp(buffer, "STATUS", 6) == 0) {
            print_status();
            send(sock, "OK\n", 3, 0);
        }
    }
    
    close(sock);
    return NULL;
}

/* Server thread */
static void* server_thread(void *arg) {
    (void)arg;
    
    int server = socket(AF_INET, SOCK_STREAM, 0);
    if (server < 0) {
        perror("socket");
        return NULL;
    }
    
    int opt = 1;
    setsockopt(server, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt));
    
    struct sockaddr_in addr = {
        .sin_family = AF_INET,
        .sin_port = htons(AGENT_PORT),
        .sin_addr.s_addr = INADDR_ANY
    };
    
    if (bind(server, (struct sockaddr*)&addr, sizeof(addr)) < 0) {
        perror("bind");
        close(server);
        return NULL;
    }
    
    listen(server, 10);
    printf("[HIVE] Listening on port %d\n", AGENT_PORT);
    
    while (hive.running) {
        struct sockaddr_in client_addr;
        socklen_t len = sizeof(client_addr);
        
        int client = accept(server, (struct sockaddr*)&client_addr, &len);
        if (client < 0) continue;
        
        int *sock = malloc(sizeof(int));
        *sock = client;
        
        pthread_t tid;
        pthread_create(&tid, NULL, handle_client, sock);
        pthread_detach(tid);
    }
    
    close(server);
    return NULL;
}

int main(int argc, char *argv[]) {
    (void)argc; (void)argv;
    
    printf("\n");
    printf("===========================================\n");
    printf("  SENTINEL IMMUNE HIVE v%s\n", VERSION);
    printf("  DragonFlyBSD Edition\n");
    printf("===========================================\n");
    printf("\n");
    
    /* Initialize */
    memset(&hive, 0, sizeof(hive));
    hive.running = 1;
    pthread_mutex_init(&hive.lock, NULL);
    
    signal(SIGINT, sighandler);
    signal(SIGTERM, sighandler);
    
    /* Start server */
    pthread_t tid;
    pthread_create(&tid, NULL, server_thread, NULL);
    
    printf("[HIVE] Ready. Press Ctrl+C to stop.\n");
    printf("[HIVE] Test with: echo 'REGISTER myhost' | nc localhost 9998\n\n");
    
    /* Wait */
    while (hive.running) {
        sleep(1);
    }
    
    pthread_join(tid, NULL);
    pthread_mutex_destroy(&hive.lock);
    
    printf("[HIVE] Shutdown complete.\n");
    return 0;
}
