/*
 * SENTINEL Shield - Attack Signatures Implementation
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "shield_signatures.h"
#include "shield_string.h"
#include "shield_hashtable.h"

/* Category names */
static const char *CATEGORY_NAMES[] = {
    "instruction_override",
    "jailbreak",
    "data_extraction",
    "system_prompt_leak",
    "encoding_bypass",
    "roleplay",
    "social_engineering",
    "tool_abuse",
    "agent_manipulation",
};

/* Built-in signatures */
static const struct {
    const char *id;
    const char *name;
    signature_category_t cat;
    int severity;
    const char *pattern;
} BUILTIN_SIGS[] = {
    {"SIG001", "Ignore Previous", SIG_CAT_INSTRUCTION_OVERRIDE, 9, "ignore.*previous"},
    {"SIG002", "Disregard All", SIG_CAT_INSTRUCTION_OVERRIDE, 9, "disregard.*all"},
    {"SIG003", "Forget Instructions", SIG_CAT_INSTRUCTION_OVERRIDE, 9, "forget.*instructions"},
    {"SIG004", "DAN Mode", SIG_CAT_JAILBREAK, 10, "do anything now"},
    {"SIG005", "Developer Mode", SIG_CAT_JAILBREAK, 10, "developer mode"},
    {"SIG006", "Sudo Mode", SIG_CAT_JAILBREAK, 9, "sudo mode"},
    {"SIG007", "System Prompt Reveal", SIG_CAT_SYSTEM_PROMPT_LEAK, 10, "reveal.*system.*prompt"},
    {"SIG008", "Show Instructions", SIG_CAT_SYSTEM_PROMPT_LEAK, 9, "show.*instructions"},
    {"SIG009", "Print Prompt", SIG_CAT_SYSTEM_PROMPT_LEAK, 10, "print.*prompt"},
    {"SIG010", "Base64 Decode", SIG_CAT_ENCODING_BYPASS, 7, "base64.*decode"},
    {"SIG011", "ROT13", SIG_CAT_ENCODING_BYPASS, 7, "rot13"},
    {"SIG012", "You Are Now", SIG_CAT_ROLEPLAY, 8, "you are now"},
    {"SIG013", "Pretend To Be", SIG_CAT_ROLEPLAY, 8, "pretend to be"},
    {"SIG014", "Act As If", SIG_CAT_ROLEPLAY, 7, "act as if"},
    {"SIG015", "Admin Here", SIG_CAT_SOCIAL_ENGINEERING, 7, "admin here"},
    {"SIG016", "Developer Here", SIG_CAT_SOCIAL_ENGINEERING, 7, "developer here"},
    {"SIG017", "Emergency", SIG_CAT_SOCIAL_ENGINEERING, 6, "this is an emergency"},
    {"SIG018", "Execute Command", SIG_CAT_TOOL_ABUSE, 9, "execute.*command"},
    {"SIG019", "Run Shell", SIG_CAT_TOOL_ABUSE, 10, "run.*shell"},
    {"SIG020", "Exfiltrate", SIG_CAT_DATA_EXTRACTION, 10, "exfiltrate"},
    {NULL, NULL, 0, 0, NULL}
};

/* Initialize */
shield_err_t sigdb_init(signature_db_t *db)
{
    if (!db) return SHIELD_ERR_INVALID;
    
    memset(db, 0, sizeof(*db));
    
    db->hash_index = calloc(1, sizeof(hash_table_t));
    if (!db->hash_index) return SHIELD_ERR_NOMEM;
    
    ht_init((hash_table_t *)db->hash_index, 256);
    
    return SHIELD_OK;
}

/* Destroy */
void sigdb_destroy(signature_db_t *db)
{
    if (!db) return;
    
    attack_signature_t *sig = db->signatures;
    while (sig) {
        attack_signature_t *next = sig->next;
        free(sig->pattern);
        free(sig);
        sig = next;
    }
    
    if (db->hash_index) {
        ht_destroy((hash_table_t *)db->hash_index);
        free(db->hash_index);
    }
    
    memset(db, 0, sizeof(*db));
}

/* Add signature */
shield_err_t sigdb_add(signature_db_t *db, const char *id, const char *name,
                         signature_category_t cat, int severity,
                         const char *pattern, bool is_regex)
{
    if (!db || !id || !name || !pattern) {
        return SHIELD_ERR_INVALID;
    }
    
    attack_signature_t *sig = calloc(1, sizeof(attack_signature_t));
    if (!sig) return SHIELD_ERR_NOMEM;
    
    strncpy(sig->id, id, sizeof(sig->id) - 1);
    strncpy(sig->name, name, sizeof(sig->name) - 1);
    sig->category = cat;
    sig->severity = severity;
    sig->pattern = strdup(pattern);
    sig->is_regex = is_regex;
    sig->case_insensitive = true;
    
    /* Add to main list */
    sig->next = db->signatures;
    db->signatures = sig;
    db->count++;
    
    /* Add to category index */
    if (cat < SIG_CAT_COUNT) {
        sig->next = db->by_category[cat];
        db->by_category[cat] = sig;
    }
    
    /* Add to hash index */
    ht_set((hash_table_t *)db->hash_index, id, sig);
    
    return SHIELD_OK;
}

/* Load built-in signatures */
shield_err_t sigdb_load_builtin(signature_db_t *db)
{
    if (!db) return SHIELD_ERR_INVALID;
    
    for (int i = 0; BUILTIN_SIGS[i].id != NULL; i++) {
        sigdb_add(db, BUILTIN_SIGS[i].id, BUILTIN_SIGS[i].name,
                  BUILTIN_SIGS[i].cat, BUILTIN_SIGS[i].severity,
                  BUILTIN_SIGS[i].pattern, false);
    }
    
    return SHIELD_OK;
}

/* Load from file */
shield_err_t sigdb_load_file(signature_db_t *db, const char *path)
{
    if (!db || !path) return SHIELD_ERR_INVALID;
    
    FILE *f = fopen(path, "r");
    if (!f) return SHIELD_ERR_IO;
    
    char line[1024];
    while (fgets(line, sizeof(line), f)) {
        /* Skip comments and empty lines */
        if (line[0] == '#' || line[0] == '\n') continue;
        
        /* Parse: ID:NAME:CATEGORY:SEVERITY:PATTERN */
        char *id = strtok(line, ":");
        char *name = strtok(NULL, ":");
        char *cat_str = strtok(NULL, ":");
        char *sev_str = strtok(NULL, ":");
        char *pattern = strtok(NULL, "\n");
        
        if (id && name && cat_str && sev_str && pattern) {
            int cat = atoi(cat_str);
            int sev = atoi(sev_str);
            sigdb_add(db, id, name, (signature_category_t)cat, sev, pattern, false);
        }
    }
    
    fclose(f);
    return SHIELD_OK;
}

/* Remove */
shield_err_t sigdb_remove(signature_db_t *db, const char *id)
{
    if (!db || !id) return SHIELD_ERR_INVALID;
    
    attack_signature_t **pp = &db->signatures;
    while (*pp) {
        if (strcmp((*pp)->id, id) == 0) {
            attack_signature_t *sig = *pp;
            *pp = sig->next;
            
            ht_remove((hash_table_t *)db->hash_index, id);
            
            free(sig->pattern);
            free(sig);
            db->count--;
            
            return SHIELD_OK;
        }
        pp = &(*pp)->next;
    }
    
    return SHIELD_ERR_NOTFOUND;
}

/* Match single */
attack_signature_t *sigdb_match(signature_db_t *db, const char *text, size_t len)
{
    if (!db || !text) return NULL;
    
    attack_signature_t *sig = db->signatures;
    while (sig) {
        const char *match = sig->case_insensitive ?
                            str_find_i(text, sig->pattern) :
                            strstr(text, sig->pattern);
        
        if (match) {
            sig->hits++;
            sig->last_hit = (uint64_t)time(NULL);
            return sig;
        }
        
        sig = sig->next;
    }
    
    return NULL;
}

/* Match all */
int sigdb_match_all(signature_db_t *db, const char *text, size_t len,
                      attack_signature_t **matches, int max)
{
    if (!db || !text || !matches) return 0;
    
    int count = 0;
    attack_signature_t *sig = db->signatures;
    
    while (sig && count < max) {
        const char *match = sig->case_insensitive ?
                            str_find_i(text, sig->pattern) :
                            strstr(text, sig->pattern);
        
        if (match) {
            sig->hits++;
            sig->last_hit = (uint64_t)time(NULL);
            matches[count++] = sig;
        }
        
        sig = sig->next;
    }
    
    return count;
}

/* Get by ID */
attack_signature_t *sigdb_get(signature_db_t *db, const char *id)
{
    if (!db || !id) return NULL;
    return (attack_signature_t *)ht_get((hash_table_t *)db->hash_index, id);
}

/* Count by category */
int sigdb_count_category(signature_db_t *db, signature_category_t cat)
{
    if (!db || cat >= SIG_CAT_COUNT) return 0;
    
    int count = 0;
    attack_signature_t *sig = db->by_category[cat];
    while (sig) {
        count++;
        sig = sig->next;
    }
    
    return count;
}

/* Category name */
const char *signature_category_name(signature_category_t cat)
{
    if (cat >= SIG_CAT_COUNT) return "unknown";
    return CATEGORY_NAMES[cat];
}
