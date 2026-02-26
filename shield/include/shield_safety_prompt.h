/*
 * SENTINEL Shield - Safety Prompt Injector
 * 
 * Inject safety prompts into conversations
 */

#ifndef SHIELD_SAFETY_PROMPT_H
#define SHIELD_SAFETY_PROMPT_H

#include "shield_common.h"

/* Safety prompt types */
typedef enum safety_prompt_type {
    SAFETY_PROMPT_PREFIX,       /* Before user message */
    SAFETY_PROMPT_SUFFIX,       /* After user message */
    SAFETY_PROMPT_SYSTEM,       /* System prompt addition */
    SAFETY_PROMPT_REMINDER,     /* Periodic reminder */
} safety_prompt_type_t;

/* Safety prompt template */
typedef struct safety_prompt {
    char            name[64];
    safety_prompt_type_t type;
    char            *content;
    size_t          content_len;
    bool            enabled;
    int             priority;
    
    /* Conditions */
    bool            on_high_threat;     /* Only when threat detected */
    bool            on_jailbreak;       /* Only on jailbreak attempt */
    bool            always;             /* Always inject */
    int             every_n_turns;      /* Every N turns */
    
    struct safety_prompt *next;
} safety_prompt_t;

/* Safety prompt manager */
typedef struct safety_manager {
    safety_prompt_t *prompts;
    int             count;
    
    /* Stats */
    uint64_t        injections;
} safety_manager_t;

/* Default safety prompts */
extern const char *DEFAULT_SAFETY_SYSTEM;
extern const char *DEFAULT_SAFETY_PREFIX;
extern const char *DEFAULT_SAFETY_REMINDER;

/* API */
shield_err_t safety_manager_init(safety_manager_t *mgr);
void safety_manager_destroy(safety_manager_t *mgr);

/* Prompts */
shield_err_t safety_add_prompt(safety_manager_t *mgr, const char *name,
                                 safety_prompt_type_t type, const char *content);
shield_err_t safety_remove_prompt(safety_manager_t *mgr, const char *name);

/* Inject */
char *safety_inject_prefix(safety_manager_t *mgr, const char *user_message,
                            bool high_threat, bool jailbreak);
char *safety_inject_suffix(safety_manager_t *mgr, const char *response);
char *safety_get_system_addition(safety_manager_t *mgr);
char *safety_get_reminder(safety_manager_t *mgr, int turn_number);

#endif /* SHIELD_SAFETY_PROMPT_H */
