/*
 * SENTINEL IMMUNE — Hive Communication
 * 
 * Agent-to-Hive protocol implementation.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>

#ifdef _WIN32
    #include <winsock2.h>
    #include <ws2tcpip.h>
    #pragma comment(lib, "ws2_32.lib")
    typedef SOCKET socket_t;
    #define SOCKET_INVALID  INVALID_SOCKET
    #define SOCKET_ERROR_   SOCKET_ERROR
    #define close_socket    closesocket
#else
    #include <unistd.h>
    #include <sys/socket.h>
    #include <netinet/in.h>
    #include <arpa/inet.h>
    #include <netdb.h>
    typedef int socket_t;
    #define SOCKET_INVALID  (-1)
    #define SOCKET_ERROR_   (-1)
    #define close_socket    close
#endif

#include "../include/immune.h"

/* Protocol constants */
#define IMMUNE_MAGIC        0x494D4D55  /* "IMMU" */
#define PROTOCOL_VERSION    1

/* Message types */
#define MSG_REGISTER        1
#define MSG_REGISTER_ACK    2
#define MSG_HEARTBEAT       3
#define MSG_THREAT          4
#define MSG_THREAT_ACK      5
#define MSG_SIGNATURE       6
#define MSG_GET_SIGNATURES  7
#define MSG_SIGNATURES      8

/* Message header */
typedef struct __attribute__((packed)) {
    uint32_t    magic;
    uint8_t     version;
    uint8_t     type;
    uint16_t    length;
} msg_header_t;

/* Registration message */
typedef struct __attribute__((packed)) {
    char        hostname[256];
    char        os_type[32];
    char        version[16];
} msg_register_t;

/* Threat message */
typedef struct __attribute__((packed)) {
    uint32_t    agent_id;
    uint8_t     level;
    uint8_t     type;
    char        signature[256];
} msg_threat_t;

/* Connection state */
static socket_t hive_socket = SOCKET_INVALID;
static uint32_t agent_id = 0;

/* ==================== Socket Helpers ==================== */

static int
socket_init(void)
{
#ifdef _WIN32
    WSADATA wsa;
    return WSAStartup(MAKEWORD(2, 2), &wsa);
#else
    return 0;
#endif
}

static void
socket_cleanup(void)
{
#ifdef _WIN32
    WSACleanup();
#endif
}

/* ==================== Hive Communication ==================== */

int
immune_hive_connect(immune_agent_t *agent, const char *address, uint16_t port)
{
    if (!agent || !address)
        return -1;
    
    socket_init();
    
    /* Save connection info */
    strncpy(agent->hive_address, address, sizeof(agent->hive_address) - 1);
    agent->hive_port = port;
    
    /* Create socket */
    hive_socket = socket(AF_INET, SOCK_STREAM, 0);
    if (hive_socket == SOCKET_INVALID) {
        perror("IMMUNE: socket failed");
        return -1;
    }
    
    /* Resolve address */
    struct sockaddr_in addr;
    memset(&addr, 0, sizeof(addr));
    addr.sin_family = AF_INET;
    addr.sin_port = htons(port);
    
    if (inet_pton(AF_INET, address, &addr.sin_addr) <= 0) {
        /* Try DNS resolution */
        struct hostent *he = gethostbyname(address);
        if (!he) {
            close_socket(hive_socket);
            hive_socket = SOCKET_INVALID;
            return -1;
        }
        memcpy(&addr.sin_addr, he->h_addr_list[0], he->h_length);
    }
    
    /* Connect */
    if (connect(hive_socket, (struct sockaddr *)&addr, sizeof(addr)) < 0) {
        perror("IMMUNE: connect failed");
        close_socket(hive_socket);
        hive_socket = SOCKET_INVALID;
        return -1;
    }
    
    printf("IMMUNE: Connected to Hive at %s:%d\n", address, port);
    
    /* Register with Hive */
    return immune_hive_register(agent);
}

int
immune_hive_register(immune_agent_t *agent)
{
    if (!agent || hive_socket == SOCKET_INVALID)
        return -1;
    
    /* Build registration message */
    uint8_t buffer[512];
    msg_header_t *header = (msg_header_t *)buffer;
    msg_register_t *reg = (msg_register_t *)(buffer + sizeof(msg_header_t));
    
    header->magic = IMMUNE_MAGIC;
    header->version = PROTOCOL_VERSION;
    header->type = MSG_REGISTER;
    header->length = sizeof(msg_register_t);
    
    /* Get hostname */
#ifdef _WIN32
    DWORD size = sizeof(reg->hostname);
    GetComputerNameA(reg->hostname, &size);
#else
    gethostname(reg->hostname, sizeof(reg->hostname) - 1);
#endif
    
    strncpy(reg->os_type, IMMUNE_PLATFORM_NAME, sizeof(reg->os_type) - 1);
    strncpy(reg->version, IMMUNE_VERSION_STRING, sizeof(reg->version) - 1);
    
    /* Send */
    size_t msg_len = sizeof(msg_header_t) + sizeof(msg_register_t);
    if (send(hive_socket, (char *)buffer, msg_len, 0) != (int)msg_len) {
        perror("IMMUNE: send failed");
        return -1;
    }
    
    /* Receive response */
    int n = recv(hive_socket, (char *)buffer, sizeof(buffer), 0);
    if (n > 0 && header->magic == IMMUNE_MAGIC && 
        header->type == MSG_REGISTER_ACK) {
        agent_id = *(uint32_t *)(buffer + sizeof(msg_header_t));
        printf("IMMUNE: Registered with Hive, agent_id=%u\n", agent_id);
        return 0;
    }
    
    return -1;
}

int
immune_hive_heartbeat(immune_agent_t *agent)
{
    if (!agent || hive_socket == SOCKET_INVALID || agent_id == 0)
        return -1;
    
    uint8_t buffer[64];
    msg_header_t *header = (msg_header_t *)buffer;
    
    header->magic = IMMUNE_MAGIC;
    header->version = PROTOCOL_VERSION;
    header->type = MSG_HEARTBEAT;
    header->length = sizeof(uint32_t);
    
    memcpy(buffer + sizeof(msg_header_t), &agent_id, sizeof(uint32_t));
    
    size_t msg_len = sizeof(msg_header_t) + sizeof(uint32_t);
    if (send(hive_socket, (char *)buffer, msg_len, 0) != (int)msg_len) {
        return -1;
    }
    
    return 0;
}

int
immune_hive_report_threat(immune_agent_t *agent, scan_result_t *result)
{
    if (!agent || !result || hive_socket == SOCKET_INVALID || agent_id == 0)
        return -1;
    
    if (!result->detected)
        return 0;
    
    uint8_t buffer[512];
    msg_header_t *header = (msg_header_t *)buffer;
    msg_threat_t *threat = (msg_threat_t *)(buffer + sizeof(msg_header_t));
    
    header->magic = IMMUNE_MAGIC;
    header->version = PROTOCOL_VERSION;
    header->type = MSG_THREAT;
    header->length = sizeof(msg_threat_t);
    
    threat->agent_id = agent_id;
    threat->level = result->level;
    threat->type = result->type;
    snprintf(threat->signature, sizeof(threat->signature), 
             "pattern_%u", result->pattern_id);
    
    size_t msg_len = sizeof(msg_header_t) + sizeof(msg_threat_t);
    if (send(hive_socket, (char *)buffer, msg_len, 0) != (int)msg_len) {
        return -1;
    }
    
    /* Wait for response */
    int n = recv(hive_socket, (char *)buffer, sizeof(buffer), 0);
    if (n > 0 && header->magic == IMMUNE_MAGIC && 
        header->type == MSG_THREAT_ACK) {
        /* Response received - could contain action to take */
        return 0;
    }
    
    return -1;
}

int
immune_hive_sync_signatures(immune_agent_t *agent)
{
    if (!agent || hive_socket == SOCKET_INVALID || agent_id == 0)
        return -1;
    
    uint8_t buffer[512];
    msg_header_t *header = (msg_header_t *)buffer;
    
    header->magic = IMMUNE_MAGIC;
    header->version = PROTOCOL_VERSION;
    header->type = MSG_GET_SIGNATURES;
    header->length = 0;
    
    size_t msg_len = sizeof(msg_header_t);
    if (send(hive_socket, (char *)buffer, msg_len, 0) != (int)msg_len) {
        return -1;
    }
    
    /* Receive signatures */
    uint8_t recv_buffer[4096];
    int n = recv(hive_socket, (char *)recv_buffer, sizeof(recv_buffer), 0);
    
    if (n > 0) {
        msg_header_t *resp = (msg_header_t *)recv_buffer;
        
        if (resp->magic == IMMUNE_MAGIC && resp->type == MSG_SIGNATURES) {
            int sig_count = resp->length / 256;  /* Assuming 256 bytes per sig */
            printf("IMMUNE: Received %d signatures from Hive\n", sig_count);
            
            /* Would add signatures to agent->patterns */
            return sig_count;
        }
    }
    
    return 0;
}

/* Disconnect from Hive */
void
immune_hive_disconnect(immune_agent_t *agent)
{
    if (hive_socket != SOCKET_INVALID) {
        close_socket(hive_socket);
        hive_socket = SOCKET_INVALID;
    }
    agent_id = 0;
    socket_cleanup();
    
    printf("IMMUNE: Disconnected from Hive\n");
}
