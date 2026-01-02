/*
 * SENTINEL Shield - Session Manager
 * 
 * Track sessions for rate limiting and threat correlation
 */

#ifndef SHIELD_SESSION_H
#define SHIELD_SESSION_H

#include "shield_common.h"

/* Session state */
typedef enum session_state {
    SESSION_STATE_NEW,
    SESSION_STATE_ACTIVE,
    SESSION_STATE_SUSPICIOUS,
    SESSION_STATE_BLOCKED,
} session_state_t;

/* Session */
typedef struct shield_session {
    char            id[64];
    char            source_ip[46];
    uint64_t        created_at;
    uint64_t        last_activity;
    session_state_t state;
    
    /* Counters */
    uint32_t        request_count;
    uint32_t        blocked_count;
    uint32_t        quarantined_count;
    
    /* Threat tracking */
    float           threat_score;
    char            last_threat[128];
    
    struct shield_session *next;
} shield_session_t;

/* Session manager */
typedef struct session_manager {
    shield_session_t    *sessions;
    uint32_t            count;
    uint32_t            max_sessions;
    uint32_t            session_timeout_sec;
    
    /* Statistics */
    uint64_t            total_created;
    uint64_t            total_expired;
} session_manager_t;

/* API */
shield_err_t session_manager_init(session_manager_t *mgr, uint32_t max_sessions);
void session_manager_destroy(session_manager_t *mgr);

shield_session_t *session_get_or_create(session_manager_t *mgr, 
                                         const char *session_id,
                                         const char *source_ip);
shield_session_t *session_find(session_manager_t *mgr, const char *session_id);

void session_touch(shield_session_t *session);
void session_record_request(shield_session_t *session, bool blocked, bool quarantined);
void session_add_threat_score(shield_session_t *session, float score, const char *threat);

void session_cleanup_expired(session_manager_t *mgr);
uint32_t session_count_active(session_manager_t *mgr);

#endif /* SHIELD_SESSION_H */
