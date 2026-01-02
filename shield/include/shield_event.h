/*
 * SENTINEL Shield - Event System
 * 
 * Pub/sub event system for internal communication
 */

#ifndef SHIELD_EVENT_H
#define SHIELD_EVENT_H

#include "shield_common.h"

/* Event types */
typedef enum event_type {
    /* Lifecycle */
    EVENT_STARTUP = 1,
    EVENT_SHUTDOWN,
    EVENT_CONFIG_RELOAD,
    
    /* Security */
    EVENT_THREAT_DETECTED = 100,
    EVENT_REQUEST_BLOCKED,
    EVENT_REQUEST_ALLOWED,
    EVENT_REQUEST_QUARANTINED,
    EVENT_CANARY_TRIGGERED,
    EVENT_RATELIMIT_EXCEEDED,
    
    /* HA */
    EVENT_PEER_JOINED = 200,
    EVENT_PEER_LEFT,
    EVENT_FAILOVER,
    EVENT_FAILBACK,
    EVENT_SYNC_COMPLETE,
    
    /* Health */
    EVENT_HEALTH_OK = 300,
    EVENT_HEALTH_DEGRADED,
    EVENT_HEALTH_CRITICAL,
} event_type_t;

/* Event data */
typedef struct shield_event {
    event_type_t    type;
    uint64_t        timestamp;
    char            source[64];
    char            message[256];
    
    /* Optional data */
    union {
        struct {
            char    zone[64];
            char    threat[64];
            float   confidence;
        } threat;
        
        struct {
            char    node_id[64];
            char    address[64];
        } peer;
        
        struct {
            uint64_t total;
            uint64_t blocked;
            uint64_t allowed;
        } stats;
    } data;
} shield_event_t;

/* Event handler callback */
typedef void (*event_handler_t)(const shield_event_t *event, void *ctx);

/* Subscriber */
typedef struct event_subscriber {
    event_handler_t     handler;
    void                *ctx;
    event_type_t        filter;     /* 0 = all events */
    struct event_subscriber *next;
} event_subscriber_t;

/* Event bus */
typedef struct event_bus {
    event_subscriber_t  *subscribers;
    int                 subscriber_count;
    
    /* Queue for async events */
    shield_event_t      *queue;
    int                 queue_head;
    int                 queue_tail;
    int                 queue_size;
    int                 queue_capacity;
    
    bool                running;
} event_bus_t;

/* API */
shield_err_t event_bus_init(event_bus_t *bus);
void event_bus_destroy(event_bus_t *bus);

shield_err_t event_subscribe(event_bus_t *bus, event_handler_t handler,
                              void *ctx, event_type_t filter);
shield_err_t event_unsubscribe(event_bus_t *bus, event_handler_t handler);

/* Publish synchronously (handlers called immediately) */
void event_publish(event_bus_t *bus, const shield_event_t *event);

/* Publish asynchronously (queued for later processing) */
shield_err_t event_publish_async(event_bus_t *bus, const shield_event_t *event);

/* Process queued events */
int event_process(event_bus_t *bus, int max_events);

/* Helper to create events */
shield_event_t event_create(event_type_t type, const char *source, const char *message);

/* Event type name */
const char *event_type_name(event_type_t type);

#endif /* SHIELD_EVENT_H */
