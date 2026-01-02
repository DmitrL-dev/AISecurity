/*
 * SENTINEL Shield - Attack Signature Database
 * 
 * Fast lookup of known attack patterns
 */

#ifndef SHIELD_SIGNATURES_H
#define SHIELD_SIGNATURES_H

#include "shield_common.h"

/* Signature categories */
typedef enum signature_category {
    SIG_CAT_INSTRUCTION_OVERRIDE = 0,
    SIG_CAT_JAILBREAK,
    SIG_CAT_DATA_EXTRACTION,
    SIG_CAT_SYSTEM_PROMPT_LEAK,
    SIG_CAT_ENCODING_BYPASS,
    SIG_CAT_ROLEPLAY,
    SIG_CAT_SOCIAL_ENGINEERING,
    SIG_CAT_TOOL_ABUSE,
    SIG_CAT_AGENT_MANIPULATION,
    SIG_CAT_COUNT
} signature_category_t;

/* Signature */
typedef struct attack_signature {
    char            id[32];
    char            name[64];
    signature_category_t category;
    int             severity;       /* 1-10 */
    
    char            *pattern;
    bool            is_regex;
    bool            case_insensitive;
    
    /* Stats */
    uint64_t        hits;
    uint64_t        last_hit;
    
    struct attack_signature *next;
} attack_signature_t;

/* Signature database */
typedef struct signature_db {
    attack_signature_t *signatures;
    int             count;
    
    /* Index by category */
    attack_signature_t *by_category[SIG_CAT_COUNT];
    
    /* Hash index for fast lookup */
    void            *hash_index;
} signature_db_t;

/* API */
shield_err_t sigdb_init(signature_db_t *db);
void sigdb_destroy(signature_db_t *db);

/* Load signatures */
shield_err_t sigdb_load_file(signature_db_t *db, const char *path);
shield_err_t sigdb_load_builtin(signature_db_t *db);

/* Add/remove */
shield_err_t sigdb_add(signature_db_t *db, const char *id, const char *name,
                         signature_category_t cat, int severity,
                         const char *pattern, bool is_regex);
shield_err_t sigdb_remove(signature_db_t *db, const char *id);

/* Match */
attack_signature_t *sigdb_match(signature_db_t *db, const char *text, size_t len);
int sigdb_match_all(signature_db_t *db, const char *text, size_t len,
                      attack_signature_t **matches, int max);

/* Query */
attack_signature_t *sigdb_get(signature_db_t *db, const char *id);
int sigdb_count_category(signature_db_t *db, signature_category_t cat);

/* Category name */
const char *signature_category_name(signature_category_t cat);

#endif /* SHIELD_SIGNATURES_H */
