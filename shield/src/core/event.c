/*
 * SENTINEL Shield - Event System Implementation
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#include "shield_common.h"
#include "shield_event.h"

#define DEFAULT_QUEUE_CAPACITY 256

/* Initialize event bus */
shield_err_t event_bus_init(event_bus_t *bus)
{
    if (!bus) {
        return SHIELD_ERR_INVALID;
    }
    
    memset(bus, 0, sizeof(*bus));
    
    bus->queue_capacity = DEFAULT_QUEUE_CAPACITY;
    bus->queue = calloc(bus->queue_capacity, sizeof(shield_event_t));
    if (!bus->queue) {
        return SHIELD_ERR_NOMEM;
    }
    
    bus->running = true;
    
    return SHIELD_OK;
}

/* Destroy event bus */
void event_bus_destroy(event_bus_t *bus)
{
    if (!bus) {
        return;
    }
    
    /* Free subscribers */
    event_subscriber_t *sub = bus->subscribers;
    while (sub) {
        event_subscriber_t *next = sub->next;
        free(sub);
        sub = next;
    }
    
    free(bus->queue);
    bus->queue = NULL;
    bus->subscribers = NULL;
}

/* Subscribe */
shield_err_t event_subscribe(event_bus_t *bus, event_handler_t handler,
                              void *ctx, event_type_t filter)
{
    if (!bus || !handler) {
        return SHIELD_ERR_INVALID;
    }
    
    event_subscriber_t *sub = calloc(1, sizeof(event_subscriber_t));
    if (!sub) {
        return SHIELD_ERR_NOMEM;
    }
    
    sub->handler = handler;
    sub->ctx = ctx;
    sub->filter = filter;
    
    /* Add to head */
    sub->next = bus->subscribers;
    bus->subscribers = sub;
    bus->subscriber_count++;
    
    return SHIELD_OK;
}

/* Unsubscribe */
shield_err_t event_unsubscribe(event_bus_t *bus, event_handler_t handler)
{
    if (!bus || !handler) {
        return SHIELD_ERR_INVALID;
    }
    
    event_subscriber_t **pp = &bus->subscribers;
    while (*pp) {
        if ((*pp)->handler == handler) {
            event_subscriber_t *sub = *pp;
            *pp = sub->next;
            free(sub);
            bus->subscriber_count--;
            return SHIELD_OK;
        }
        pp = &(*pp)->next;
    }
    
    return SHIELD_ERR_NOTFOUND;
}

/* Publish synchronously */
void event_publish(event_bus_t *bus, const shield_event_t *event)
{
    if (!bus || !event) {
        return;
    }
    
    event_subscriber_t *sub = bus->subscribers;
    while (sub) {
        /* Check filter */
        if (sub->filter == 0 || sub->filter == event->type) {
            sub->handler(event, sub->ctx);
        }
        sub = sub->next;
    }
}

/* Publish async */
shield_err_t event_publish_async(event_bus_t *bus, const shield_event_t *event)
{
    if (!bus || !event) {
        return SHIELD_ERR_INVALID;
    }
    
    if (bus->queue_size >= bus->queue_capacity) {
        return SHIELD_ERR_NOMEM; /* Queue full */
    }
    
    /* Add to queue */
    memcpy(&bus->queue[bus->queue_tail], event, sizeof(*event));
    bus->queue_tail = (bus->queue_tail + 1) % bus->queue_capacity;
    bus->queue_size++;
    
    return SHIELD_OK;
}

/* Process queued events */
int event_process(event_bus_t *bus, int max_events)
{
    if (!bus) {
        return 0;
    }
    
    int processed = 0;
    
    while (bus->queue_size > 0 && processed < max_events) {
        shield_event_t *event = &bus->queue[bus->queue_head];
        event_publish(bus, event);
        
        bus->queue_head = (bus->queue_head + 1) % bus->queue_capacity;
        bus->queue_size--;
        processed++;
    }
    
    return processed;
}

/* Create event */
shield_event_t event_create(event_type_t type, const char *source, const char *message)
{
    shield_event_t event = {0};
    
    event.type = type;
    event.timestamp = (uint64_t)time(NULL);
    
    if (source) {
        strncpy(event.source, source, sizeof(event.source) - 1);
    }
    if (message) {
        strncpy(event.message, message, sizeof(event.message) - 1);
    }
    
    return event;
}

/* Event type name */
const char *event_type_name(event_type_t type)
{
    switch (type) {
    case EVENT_STARTUP: return "STARTUP";
    case EVENT_SHUTDOWN: return "SHUTDOWN";
    case EVENT_CONFIG_RELOAD: return "CONFIG_RELOAD";
    case EVENT_THREAT_DETECTED: return "THREAT_DETECTED";
    case EVENT_REQUEST_BLOCKED: return "REQUEST_BLOCKED";
    case EVENT_REQUEST_ALLOWED: return "REQUEST_ALLOWED";
    case EVENT_REQUEST_QUARANTINED: return "REQUEST_QUARANTINED";
    case EVENT_CANARY_TRIGGERED: return "CANARY_TRIGGERED";
    case EVENT_RATELIMIT_EXCEEDED: return "RATELIMIT_EXCEEDED";
    case EVENT_PEER_JOINED: return "PEER_JOINED";
    case EVENT_PEER_LEFT: return "PEER_LEFT";
    case EVENT_FAILOVER: return "FAILOVER";
    case EVENT_FAILBACK: return "FAILBACK";
    case EVENT_SYNC_COMPLETE: return "SYNC_COMPLETE";
    case EVENT_HEALTH_OK: return "HEALTH_OK";
    case EVENT_HEALTH_DEGRADED: return "HEALTH_DEGRADED";
    case EVENT_HEALTH_CRITICAL: return "HEALTH_CRITICAL";
    default: return "UNKNOWN";
    }
}
