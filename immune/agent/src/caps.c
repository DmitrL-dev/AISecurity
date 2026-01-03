/*
 * SENTINEL IMMUNE — CAPS Async Messaging
 * 
 * DragonFlyBSD CAPS (Common API for Process Services) integration
 * for async agent-to-hive communication.
 * 
 * Falls back to Unix domain sockets on other platforms.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include <unistd.h>
#include <pthread.h>
#include <sys/socket.h>
#include <sys/un.h>

#ifdef __DragonFly__
#include <sys/caps.h>
#endif

/* ==================== Configuration ==================== */

#define CAPS_SERVICE_NAME   "/immune/hive"
#define UNIX_SOCKET_PATH    "/var/run/immune/hive.sock"
#define MAX_MESSAGE_SIZE    4096
#define MESSAGE_QUEUE_SIZE  1000

/* ==================== Message Types ==================== */

typedef enum {
    MSG_THREAT_REPORT,
    MSG_HEARTBEAT,
    MSG_CONFIG_UPDATE,
    MSG_PATTERN_SYNC,
    MSG_AGENT_STATUS,
    MSG_SCAN_REQUEST,
    MSG_SCAN_RESULT
} message_type_t;

typedef struct {
    message_type_t  type;
    uint32_t        agent_id;
    uint32_t        seq_num;
    uint32_t        payload_len;
    uint64_t        timestamp;
    uint8_t         payload[MAX_MESSAGE_SIZE - 32];
} immune_message_t;

/* ==================== Message Queue ==================== */

typedef struct {
    immune_message_t    messages[MESSAGE_QUEUE_SIZE];
    int                 head;
    int                 tail;
    int                 count;
    pthread_mutex_t     lock;
    pthread_cond_t      not_empty;
    pthread_cond_t      not_full;
} message_queue_t;

static message_queue_t outgoing_queue;
static message_queue_t incoming_queue;
static pthread_t sender_thread;
static pthread_t receiver_thread;
static volatile int caps_running = 0;

/* ==================== Queue Operations ==================== */

static int
queue_init(message_queue_t *q)
{
    q->head = 0;
    q->tail = 0;
    q->count = 0;
    pthread_mutex_init(&q->lock, NULL);
    pthread_cond_init(&q->not_empty, NULL);
    pthread_cond_init(&q->not_full, NULL);
    return 0;
}

static void
queue_destroy(message_queue_t *q)
{
    pthread_mutex_destroy(&q->lock);
    pthread_cond_destroy(&q->not_empty);
    pthread_cond_destroy(&q->not_full);
}

static int
queue_push(message_queue_t *q, const immune_message_t *msg)
{
    pthread_mutex_lock(&q->lock);
    
    while (q->count >= MESSAGE_QUEUE_SIZE && caps_running) {
        pthread_cond_wait(&q->not_full, &q->lock);
    }
    
    if (!caps_running) {
        pthread_mutex_unlock(&q->lock);
        return -1;
    }
    
    memcpy(&q->messages[q->tail], msg, sizeof(immune_message_t));
    q->tail = (q->tail + 1) % MESSAGE_QUEUE_SIZE;
    q->count++;
    
    pthread_cond_signal(&q->not_empty);
    pthread_mutex_unlock(&q->lock);
    
    return 0;
}

static int
queue_pop(message_queue_t *q, immune_message_t *msg)
{
    pthread_mutex_lock(&q->lock);
    
    while (q->count == 0 && caps_running) {
        pthread_cond_wait(&q->not_empty, &q->lock);
    }
    
    if (!caps_running && q->count == 0) {
        pthread_mutex_unlock(&q->lock);
        return -1;
    }
    
    memcpy(msg, &q->messages[q->head], sizeof(immune_message_t));
    q->head = (q->head + 1) % MESSAGE_QUEUE_SIZE;
    q->count--;
    
    pthread_cond_signal(&q->not_full);
    pthread_mutex_unlock(&q->lock);
    
    return 0;
}

/* ==================== CAPS / Socket Backend ==================== */

static int comm_fd = -1;

#ifdef __DragonFly__

/* DragonFlyBSD CAPS implementation */
static int
caps_connect(void)
{
    caps_port_t port = caps_open(CAPS_SERVICE_NAME);
    if (port < 0) {
        fprintf(stderr, "IMMUNE: CAPS open failed: %s\n", strerror(errno));
        return -1;
    }
    comm_fd = port;
    return 0;
}

static int
caps_send(const immune_message_t *msg)
{
    return caps_send_async(comm_fd, msg, sizeof(immune_message_t));
}

static int
caps_receive(immune_message_t *msg)
{
    return caps_recv(comm_fd, msg, sizeof(immune_message_t), 0);
}

#else

/* Unix socket fallback for non-DragonFly */
static int
caps_connect(void)
{
    comm_fd = socket(AF_UNIX, SOCK_STREAM, 0);
    if (comm_fd < 0) {
        fprintf(stderr, "IMMUNE: Socket create failed: %s\n", strerror(errno));
        return -1;
    }
    
    struct sockaddr_un addr;
    memset(&addr, 0, sizeof(addr));
    addr.sun_family = AF_UNIX;
    strncpy(addr.sun_path, UNIX_SOCKET_PATH, sizeof(addr.sun_path) - 1);
    
    if (connect(comm_fd, (struct sockaddr *)&addr, sizeof(addr)) < 0) {
        fprintf(stderr, "IMMUNE: Connect failed: %s\n", strerror(errno));
        close(comm_fd);
        comm_fd = -1;
        return -1;
    }
    
    return 0;
}

static int
caps_send(const immune_message_t *msg)
{
    return send(comm_fd, msg, sizeof(immune_message_t), 0);
}

static int
caps_receive(immune_message_t *msg)
{
    return recv(comm_fd, msg, sizeof(immune_message_t), 0);
}

#endif

/* ==================== Async Threads ==================== */

static void *
sender_loop(void *arg)
{
    (void)arg;
    immune_message_t msg;
    
    while (caps_running) {
        if (queue_pop(&outgoing_queue, &msg) == 0) {
            if (caps_send(&msg) < 0) {
                fprintf(stderr, "IMMUNE: Send failed, reconnecting...\n");
                close(comm_fd);
                sleep(1);
                caps_connect();
            }
        }
    }
    
    return NULL;
}

static void *
receiver_loop(void *arg)
{
    (void)arg;
    immune_message_t msg;
    
    while (caps_running) {
        if (caps_receive(&msg) > 0) {
            queue_push(&incoming_queue, &msg);
        }
    }
    
    return NULL;
}

/* ==================== Public API ==================== */

static uint32_t agent_id = 0;
static uint32_t seq_counter = 0;

int
caps_init(uint32_t id)
{
    agent_id = id;
    
    queue_init(&outgoing_queue);
    queue_init(&incoming_queue);
    
    if (caps_connect() < 0) {
        return -1;
    }
    
    caps_running = 1;
    pthread_create(&sender_thread, NULL, sender_loop, NULL);
    pthread_create(&receiver_thread, NULL, receiver_loop, NULL);
    
    fprintf(stderr, "IMMUNE: CAPS initialized (agent=%u)\n", agent_id);
    return 0;
}

void
caps_shutdown(void)
{
    caps_running = 0;
    
    pthread_cond_broadcast(&outgoing_queue.not_empty);
    pthread_cond_broadcast(&outgoing_queue.not_full);
    pthread_cond_broadcast(&incoming_queue.not_empty);
    pthread_cond_broadcast(&incoming_queue.not_full);
    
    pthread_join(sender_thread, NULL);
    pthread_join(receiver_thread, NULL);
    
    if (comm_fd >= 0) {
        close(comm_fd);
        comm_fd = -1;
    }
    
    queue_destroy(&outgoing_queue);
    queue_destroy(&incoming_queue);
    
    fprintf(stderr, "IMMUNE: CAPS shutdown\n");
}

/*
 * Send threat report asynchronously (non-blocking)
 */
int
caps_report_threat_async(uint32_t threat_level, const char *details)
{
    immune_message_t msg;
    memset(&msg, 0, sizeof(msg));
    
    msg.type = MSG_THREAT_REPORT;
    msg.agent_id = agent_id;
    msg.seq_num = __sync_fetch_and_add(&seq_counter, 1);
    msg.timestamp = time(NULL);
    
    /* Pack threat data */
    msg.payload[0] = (uint8_t)threat_level;
    strncpy((char *)&msg.payload[1], details, MAX_MESSAGE_SIZE - 33);
    msg.payload_len = strlen(details) + 2;
    
    return queue_push(&outgoing_queue, &msg);
}

/*
 * Send heartbeat asynchronously
 */
int
caps_heartbeat_async(void)
{
    immune_message_t msg;
    memset(&msg, 0, sizeof(msg));
    
    msg.type = MSG_HEARTBEAT;
    msg.agent_id = agent_id;
    msg.seq_num = __sync_fetch_and_add(&seq_counter, 1);
    msg.timestamp = time(NULL);
    msg.payload_len = 0;
    
    return queue_push(&outgoing_queue, &msg);
}

/*
 * Check for incoming messages (non-blocking)
 */
int
caps_poll_message(immune_message_t *msg)
{
    pthread_mutex_lock(&incoming_queue.lock);
    
    if (incoming_queue.count == 0) {
        pthread_mutex_unlock(&incoming_queue.lock);
        return 0; /* No message */
    }
    
    memcpy(msg, &incoming_queue.messages[incoming_queue.head], sizeof(immune_message_t));
    incoming_queue.head = (incoming_queue.head + 1) % MESSAGE_QUEUE_SIZE;
    incoming_queue.count--;
    
    pthread_mutex_unlock(&incoming_queue.lock);
    return 1; /* Got message */
}

/*
 * Get queue stats
 */
void
caps_stats(int *pending_out, int *pending_in)
{
    pthread_mutex_lock(&outgoing_queue.lock);
    *pending_out = outgoing_queue.count;
    pthread_mutex_unlock(&outgoing_queue.lock);
    
    pthread_mutex_lock(&incoming_queue.lock);
    *pending_in = incoming_queue.count;
    pthread_mutex_unlock(&incoming_queue.lock);
}
