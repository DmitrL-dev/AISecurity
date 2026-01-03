/*
 * SENTINEL IMMUNE — Hive Network Module
 * 
 * TCP server for agent connections.
 * Pure C implementation.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <errno.h>
#include <pthread.h>
#include <sys/types.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>

#include "../include/hive.h"
#include "../include/network.h"
#include "../include/protocol.h"

#define BACKLOG         128
#define RECV_BUFFER     4096

/* Client handler thread argument */
typedef struct {
    immune_hive_t   *hive;
    int             client_fd;
    char            client_ip[MAX_IP_LEN];
} client_ctx_t;

/* ==================== Private Functions ==================== */

static void*
handle_client(void *arg)
{
    client_ctx_t *ctx = (client_ctx_t *)arg;
    immune_hive_t *hive = ctx->hive;
    int fd = ctx->client_fd;
    
    uint8_t buffer[RECV_BUFFER];
    ssize_t n;
    
    printf("[NET] Client connected: %s\n", ctx->client_ip);
    
    while ((n = recv(fd, buffer, sizeof(buffer), 0)) > 0) {
        /* Parse protocol message */
        immune_msg_t *msg = (immune_msg_t *)buffer;
        
        if (n < sizeof(immune_msg_t))
            continue;
        
        /* Verify magic */
        if (msg->magic != IMMUNE_MAGIC)
            continue;
        
        /* Handle message by type */
        switch (msg->type) {
        case MSG_REGISTER: {
            /* Agent registration */
            msg_register_t *reg = (msg_register_t *)msg->payload;
            
            uint32_t agent_id = hive_register_agent(
                hive,
                reg->hostname,
                ctx->client_ip,
                reg->os_type
            );
            
            /* Send response */
            immune_msg_t resp;
            resp.magic = IMMUNE_MAGIC;
            resp.type = MSG_REGISTER_ACK;
            resp.length = sizeof(uint32_t);
            memcpy(resp.payload, &agent_id, sizeof(uint32_t));
            
            send(fd, &resp, sizeof(resp), 0);
            break;
        }
        
        case MSG_HEARTBEAT: {
            /* Agent heartbeat */
            uint32_t agent_id = *(uint32_t *)msg->payload;
            hive_agent_heartbeat(hive, agent_id);
            break;
        }
        
        case MSG_THREAT: {
            /* Threat report */
            msg_threat_t *threat = (msg_threat_t *)msg->payload;
            
            /* Create threat event and report */
            threat_event_t event;
            memset(&event, 0, sizeof(event));
            event.agent_id = threat->agent_id;
            event.level = threat->level;
            event.type = threat->type;
            strncpy(event.signature, threat->signature, sizeof(event.signature) - 1);
            
            uint64_t event_id = hive_report_threat(hive, &event);
            
            /* Send response with action */
            immune_msg_t resp;
            resp.magic = IMMUNE_MAGIC;
            resp.type = MSG_THREAT_ACK;
            resp.length = sizeof(msg_threat_ack_t);
            
            msg_threat_ack_t *ack = (msg_threat_ack_t *)resp.payload;
            ack->event_id = event_id;
            ack->action = RESPONSE_BLOCK;  /* Would be from correlation */
            
            send(fd, &resp, sizeof(resp), 0);
            break;
        }
        
        case MSG_SIGNATURE: {
            /* New signature from agent */
            msg_signature_t *sig = (msg_signature_t *)msg->payload;
            
            hive_add_signature(
                hive,
                sig->pattern,
                sig->severity,  /* threat_level_t */
                sig->type       /* threat_type_t */
            );
            break;
        }
        
        case MSG_GET_SIGNATURES: {
            /* Agent requesting signatures */
            /* Would send signature list */
            break;
        }
        
        default:
            fprintf(stderr, "[NET] Unknown message type: %d\n", msg->type);
        }
    }
    
    printf("[NET] Client disconnected: %s\n", ctx->client_ip);
    
    close(fd);
    free(ctx);
    
    pthread_exit(NULL);
    return NULL;
}

/* ==================== Public Functions ==================== */

int
hive_network_start(immune_hive_t *hive, uint16_t port)
{
    int server_fd;
    struct sockaddr_in addr;
    int opt = 1;
    
    /* Create socket */
    server_fd = socket(AF_INET, SOCK_STREAM, 0);
    if (server_fd < 0) {
        perror("[NET] Socket failed");
        return -1;
    }
    
    /* Set options */
    setsockopt(server_fd, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt));
    
    /* Bind */
    addr.sin_family = AF_INET;
    addr.sin_addr.s_addr = INADDR_ANY;
    addr.sin_port = htons(port);
    
    if (bind(server_fd, (struct sockaddr *)&addr, sizeof(addr)) < 0) {
        perror("[NET] Bind failed");
        close(server_fd);
        return -1;
    }
    
    /* Listen */
    if (listen(server_fd, BACKLOG) < 0) {
        perror("[NET] Listen failed");
        close(server_fd);
        return -1;
    }
    
    printf("[NET] Listening on port %d\n", port);
    
    /* Accept loop */
    while (hive->running) {
        struct sockaddr_in client_addr;
        socklen_t client_len = sizeof(client_addr);
        
        int client_fd = accept(server_fd, 
                               (struct sockaddr *)&client_addr,
                               &client_len);
        
        if (client_fd < 0) {
            if (errno == EINTR)
                continue;
            perror("[NET] Accept failed");
            continue;
        }
        
        /* Create context */
        client_ctx_t *ctx = malloc(sizeof(client_ctx_t));
        if (!ctx) {
            close(client_fd);
            continue;
        }
        
        ctx->hive = hive;
        ctx->client_fd = client_fd;
        inet_ntop(AF_INET, &client_addr.sin_addr,
                  ctx->client_ip, sizeof(ctx->client_ip));
        
        /* Spawn handler thread */
        pthread_t thread;
        pthread_create(&thread, NULL, handle_client, ctx);
        pthread_detach(thread);
    }
    
    close(server_fd);
    return 0;
}

void*
hive_network_thread(void *arg)
{
    immune_hive_t *hive = (immune_hive_t *)arg;
    hive_network_start(hive, hive->agent_port);
    return NULL;
}
