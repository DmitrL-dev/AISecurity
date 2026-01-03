/*
 * SENTINEL IMMUNE — Hive Forensics Module
 * 
 * Incident investigation and evidence collection.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#include "../include/hive.h"

#define MAX_INCIDENTS       1000
#define MAX_EVIDENCE        100
#define FORENSICS_MAGIC     0x464F5245  /* "FORE" */

/* Evidence types */
typedef enum {
    EVIDENCE_MEMORY_DUMP = 1,
    EVIDENCE_FILE,
    EVIDENCE_LOG,
    EVIDENCE_NETWORK,
    EVIDENCE_PROCESS,
    EVIDENCE_REGISTRY,
    EVIDENCE_SCREENSHOT
} evidence_type_t;

/* Evidence item */
typedef struct {
    uint64_t        evidence_id;
    evidence_type_t type;
    char            description[256];
    char            path[512];
    size_t          size;
    uint8_t         hash[32];
    time_t          collected_at;
    uint32_t        agent_id;
} evidence_item_t;

/* Incident record */
typedef struct {
    uint64_t        incident_id;
    char            title[128];
    char            description[512];
    time_t          created_at;
    time_t          updated_at;
    time_t          resolved_at;
    uint32_t        severity;       /* 1-5 */
    uint32_t        status;         /* 0=open, 1=investigating, 2=resolved */
    uint32_t        affected_agents;
    uint64_t        threat_event_id;
    
    /* Evidence */
    evidence_item_t evidence[MAX_EVIDENCE];
    uint32_t        evidence_count;
    
    /* Notes */
    char            notes[2048];
} incident_t;

/* Forensics database */
typedef struct {
    uint32_t    magic;
    uint32_t    version;
    incident_t  *incidents;
    uint64_t    incident_count;
    char        evidence_path[256];
} forensics_db_t;

/* Global DB */
static forensics_db_t g_forensics;

/* ==================== Initialization ==================== */

int
forensics_init(const char *evidence_path)
{
    memset(&g_forensics, 0, sizeof(forensics_db_t));
    
    g_forensics.magic = FORENSICS_MAGIC;
    g_forensics.version = 1;
    
    if (evidence_path) {
        strncpy(g_forensics.evidence_path, evidence_path,
                sizeof(g_forensics.evidence_path) - 1);
    } else {
        strcpy(g_forensics.evidence_path, "/var/immune/forensics");
    }
    
    /* Allocate incidents */
    g_forensics.incidents = calloc(MAX_INCIDENTS, sizeof(incident_t));
    if (!g_forensics.incidents) {
        return -1;
    }
    
    forensics_load();
    
    printf("FORENSICS: Initialized at %s\n", g_forensics.evidence_path);
    return 0;
}

void
forensics_shutdown(void)
{
    forensics_save();
    
    if (g_forensics.incidents) {
        free(g_forensics.incidents);
        g_forensics.incidents = NULL;
    }
    
    printf("FORENSICS: Shutdown complete\n");
}

/* ==================== Incident Management ==================== */

/* Create incident */
uint64_t
forensics_create_incident(const char *title, const char *description,
                          uint32_t severity, uint64_t threat_event_id)
{
    if (g_forensics.incident_count >= MAX_INCIDENTS)
        return 0;
    
    uint64_t id = g_forensics.incident_count + 1;
    incident_t *inc = &g_forensics.incidents[g_forensics.incident_count];
    
    memset(inc, 0, sizeof(incident_t));
    
    inc->incident_id = id;
    if (title) strncpy(inc->title, title, sizeof(inc->title) - 1);
    if (description) strncpy(inc->description, description, 
                             sizeof(inc->description) - 1);
    
    inc->severity = severity;
    inc->status = 0;  /* Open */
    inc->threat_event_id = threat_event_id;
    inc->created_at = time(NULL);
    inc->updated_at = inc->created_at;
    
    g_forensics.incident_count++;
    forensics_save();
    
    printf("FORENSICS: Created incident %lu: %s\n", id, title);
    return id;
}

/* Get incident */
incident_t*
forensics_get_incident(uint64_t incident_id)
{
    for (uint64_t i = 0; i < g_forensics.incident_count; i++) {
        if (g_forensics.incidents[i].incident_id == incident_id) {
            return &g_forensics.incidents[i];
        }
    }
    return NULL;
}

/* Update incident status */
int
forensics_update_status(uint64_t incident_id, uint32_t status)
{
    incident_t *inc = forensics_get_incident(incident_id);
    if (!inc) return -1;
    
    inc->status = status;
    inc->updated_at = time(NULL);
    
    if (status == 2) {  /* Resolved */
        inc->resolved_at = time(NULL);
    }
    
    forensics_save();
    return 0;
}

/* Add note to incident */
int
forensics_add_note(uint64_t incident_id, const char *note)
{
    incident_t *inc = forensics_get_incident(incident_id);
    if (!inc || !note) return -1;
    
    size_t current_len = strlen(inc->notes);
    size_t note_len = strlen(note);
    
    if (current_len + note_len + 50 < sizeof(inc->notes)) {
        time_t now = time(NULL);
        struct tm *tm = localtime(&now);
        char timestamp[32];
        strftime(timestamp, sizeof(timestamp), "%Y-%m-%d %H:%M:%S", tm);
        
        snprintf(inc->notes + current_len, sizeof(inc->notes) - current_len,
                 "\n[%s] %s", timestamp, note);
        
        inc->updated_at = time(NULL);
        forensics_save();
    }
    
    return 0;
}

/* ==================== Evidence Collection ==================== */

/* Add evidence to incident */
uint64_t
forensics_add_evidence(uint64_t incident_id, evidence_type_t type,
                       const char *description, const void *data, 
                       size_t size, uint32_t agent_id)
{
    incident_t *inc = forensics_get_incident(incident_id);
    if (!inc || inc->evidence_count >= MAX_EVIDENCE) return 0;
    
    uint64_t eid = (incident_id << 16) | (inc->evidence_count + 1);
    evidence_item_t *ev = &inc->evidence[inc->evidence_count];
    
    ev->evidence_id = eid;
    ev->type = type;
    ev->size = size;
    ev->agent_id = agent_id;
    ev->collected_at = time(NULL);
    
    if (description) {
        strncpy(ev->description, description, sizeof(ev->description) - 1);
    }
    
    /* Save evidence file */
    snprintf(ev->path, sizeof(ev->path), "%s/ev_%016lx.dat",
             g_forensics.evidence_path, eid);
    
    if (data && size > 0) {
        FILE *fp = fopen(ev->path, "wb");
        if (fp) {
            fwrite(data, 1, size, fp);
            fclose(fp);
        }
    }
    
    inc->evidence_count++;
    inc->updated_at = time(NULL);
    forensics_save();
    
    printf("FORENSICS: Added evidence %lu to incident %lu\n", 
           eid, incident_id);
    
    return eid;
}

/* Collect memory from agent */
int
forensics_collect_memory(uint64_t incident_id, uint32_t agent_id,
                         const char *region_desc)
{
    /* Would request memory dump from agent */
    printf("FORENSICS: Requesting memory dump from agent %u\n", agent_id);
    
    /* Add placeholder evidence */
    forensics_add_evidence(incident_id, EVIDENCE_MEMORY_DUMP,
                          region_desc, NULL, 0, agent_id);
    
    return 0;
}

/* Collect file from agent */
int
forensics_collect_file(uint64_t incident_id, uint32_t agent_id,
                       const char *file_path)
{
    /* Would request file from agent */
    printf("FORENSICS: Requesting file %s from agent %u\n", 
           file_path, agent_id);
    
    forensics_add_evidence(incident_id, EVIDENCE_FILE,
                          file_path, NULL, 0, agent_id);
    
    return 0;
}

/* Generate incident report */
void
forensics_generate_report(uint64_t incident_id, char *buffer, size_t size)
{
    incident_t *inc = forensics_get_incident(incident_id);
    if (!inc || !buffer) return;
    
    char *p = buffer;
    char *end = buffer + size;
    
    p += snprintf(p, end - p, "=== INCIDENT REPORT ===\n\n");
    p += snprintf(p, end - p, "ID: %lu\n", inc->incident_id);
    p += snprintf(p, end - p, "Title: %s\n", inc->title);
    p += snprintf(p, end - p, "Severity: %u/5\n", inc->severity);
    
    const char *status_str[] = {"Open", "Investigating", "Resolved"};
    p += snprintf(p, end - p, "Status: %s\n", 
                  inc->status <= 2 ? status_str[inc->status] : "Unknown");
    
    struct tm *tm;
    char time_buf[32];
    
    tm = localtime(&inc->created_at);
    strftime(time_buf, sizeof(time_buf), "%Y-%m-%d %H:%M:%S", tm);
    p += snprintf(p, end - p, "Created: %s\n", time_buf);
    
    if (inc->resolved_at > 0) {
        tm = localtime(&inc->resolved_at);
        strftime(time_buf, sizeof(time_buf), "%Y-%m-%d %H:%M:%S", tm);
        p += snprintf(p, end - p, "Resolved: %s\n", time_buf);
    }
    
    p += snprintf(p, end - p, "\nDescription:\n%s\n", inc->description);
    
    p += snprintf(p, end - p, "\nEvidence (%u items):\n", inc->evidence_count);
    for (uint32_t i = 0; i < inc->evidence_count && p < end - 100; i++) {
        evidence_item_t *ev = &inc->evidence[i];
        p += snprintf(p, end - p, "  [%lu] %s (%zu bytes)\n",
                      ev->evidence_id, ev->description, ev->size);
    }
    
    if (inc->notes[0]) {
        p += snprintf(p, end - p, "\nNotes:%s\n", inc->notes);
    }
    
    p += snprintf(p, end - p, "\n=== END REPORT ===\n");
}

/* ==================== Persistence ==================== */

int
forensics_save(void)
{
    char path[512];
    snprintf(path, sizeof(path), "%s/forensics.db", g_forensics.evidence_path);
    
    FILE *fp = fopen(path, "wb");
    if (!fp) return -1;
    
    fwrite(&g_forensics.magic, sizeof(uint32_t), 1, fp);
    fwrite(&g_forensics.version, sizeof(uint32_t), 1, fp);
    fwrite(&g_forensics.incident_count, sizeof(uint64_t), 1, fp);
    
    for (uint64_t i = 0; i < g_forensics.incident_count; i++) {
        fwrite(&g_forensics.incidents[i], sizeof(incident_t), 1, fp);
    }
    
    fclose(fp);
    return 0;
}

int
forensics_load(void)
{
    char path[512];
    snprintf(path, sizeof(path), "%s/forensics.db", g_forensics.evidence_path);
    
    FILE *fp = fopen(path, "rb");
    if (!fp) return -1;
    
    uint32_t magic, version;
    fread(&magic, sizeof(uint32_t), 1, fp);
    fread(&version, sizeof(uint32_t), 1, fp);
    
    if (magic != FORENSICS_MAGIC) {
        fclose(fp);
        return -1;
    }
    
    fread(&g_forensics.incident_count, sizeof(uint64_t), 1, fp);
    
    if (g_forensics.incident_count > MAX_INCIDENTS) {
        g_forensics.incident_count = MAX_INCIDENTS;
    }
    
    for (uint64_t i = 0; i < g_forensics.incident_count; i++) {
        fread(&g_forensics.incidents[i], sizeof(incident_t), 1, fp);
    }
    
    fclose(fp);
    printf("FORENSICS: Loaded %lu incidents\n", g_forensics.incident_count);
    
    return 0;
}
