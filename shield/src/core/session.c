/*
 * SENTINEL Shield - Session Manager Implementation
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#include "shield_common.h"
#include "shield_session.h"

/* Get current time */
static uint64_t get_time_sec(void)
{
    return (uint64_t)time(NULL);
}

/* Initialize session manager */
shield_err_t session_manager_init(session_manager_t *mgr, uint32_t max_sessions)
{
    if (!mgr) {
        return SHIELD_ERR_INVALID;
    }
    
    memset(mgr, 0, sizeof(*mgr));
    mgr->max_sessions = max_sessions > 0 ? max_sessions : 10000;
    mgr->session_timeout_sec = 3600; /* 1 hour default */
    
    return SHIELD_OK;
}

/* Destroy session manager */
void session_manager_destroy(session_manager_t *mgr)
{
    if (!mgr) {
        return;
    }
    
    shield_session_t *session = mgr->sessions;
    while (session) {
        shield_session_t *next = session->next;
        free(session);
        session = next;
    }
    
    mgr->sessions = NULL;
    mgr->count = 0;
}

/* Find session by ID */
shield_session_t *session_find(session_manager_t *mgr, const char *session_id)
{
    if (!mgr || !session_id) {
        return NULL;
    }
    
    shield_session_t *session = mgr->sessions;
    while (session) {
        if (strcmp(session->id, session_id) == 0) {
            return session;
        }
        session = session->next;
    }
    
    return NULL;
}

/* Get or create session */
shield_session_t *session_get_or_create(session_manager_t *mgr,
                                         const char *session_id,
                                         const char *source_ip)
{
    if (!mgr || !session_id) {
        return NULL;
    }
    
    /* Try to find existing */
    shield_session_t *session = session_find(mgr, session_id);
    if (session) {
        session_touch(session);
        return session;
    }
    
    /* Check limit */
    if (mgr->count >= mgr->max_sessions) {
        session_cleanup_expired(mgr);
        if (mgr->count >= mgr->max_sessions) {
            return NULL; /* Still full */
        }
    }
    
    /* Create new */
    session = calloc(1, sizeof(shield_session_t));
    if (!session) {
        return NULL;
    }
    
    strncpy(session->id, session_id, sizeof(session->id) - 1);
    if (source_ip) {
        strncpy(session->source_ip, source_ip, sizeof(session->source_ip) - 1);
    }
    session->created_at = get_time_sec();
    session->last_activity = session->created_at;
    session->state = SESSION_STATE_NEW;
    
    /* Insert at head */
    session->next = mgr->sessions;
    mgr->sessions = session;
    mgr->count++;
    mgr->total_created++;
    
    return session;
}

/* Touch session (update last activity) */
void session_touch(shield_session_t *session)
{
    if (session) {
        session->last_activity = get_time_sec();
        if (session->state == SESSION_STATE_NEW) {
            session->state = SESSION_STATE_ACTIVE;
        }
    }
}

/* Record request */
void session_record_request(shield_session_t *session, bool blocked, bool quarantined)
{
    if (!session) {
        return;
    }
    
    session->request_count++;
    
    if (blocked) {
        session->blocked_count++;
    }
    if (quarantined) {
        session->quarantined_count++;
    }
    
    session_touch(session);
}

/* Add threat score */
void session_add_threat_score(shield_session_t *session, float score, const char *threat)
{
    if (!session) {
        return;
    }
    
    session->threat_score += score;
    
    if (threat) {
        strncpy(session->last_threat, threat, sizeof(session->last_threat) - 1);
    }
    
    /* Auto-block if score too high */
    if (session->threat_score >= 10.0f) {
        session->state = SESSION_STATE_BLOCKED;
    } else if (session->threat_score >= 5.0f) {
        session->state = SESSION_STATE_SUSPICIOUS;
    }
}

/* Cleanup expired sessions */
void session_cleanup_expired(session_manager_t *mgr)
{
    if (!mgr) {
        return;
    }
    
    uint64_t now = get_time_sec();
    
    shield_session_t **pp = &mgr->sessions;
    while (*pp) {
        shield_session_t *session = *pp;
        
        if (now - session->last_activity > mgr->session_timeout_sec) {
            *pp = session->next;
            free(session);
            mgr->count--;
            mgr->total_expired++;
        } else {
            pp = &session->next;
        }
    }
}

/* Count active sessions */
uint32_t session_count_active(session_manager_t *mgr)
{
    if (!mgr) {
        return 0;
    }
    
    uint32_t count = 0;
    uint64_t now = get_time_sec();
    
    shield_session_t *session = mgr->sessions;
    while (session) {
        if (now - session->last_activity < 300) { /* Active in last 5 min */
            count++;
        }
        session = session->next;
    }
    
    return count;
}
