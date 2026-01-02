/*
 * SENTINEL Shield - Report Generator
 * 
 * Generate security reports
 */

#ifndef SHIELD_REPORT_H
#define SHIELD_REPORT_H

#include "shield_common.h"

/* Report format */
typedef enum report_format {
    REPORT_TEXT,
    REPORT_JSON,
    REPORT_HTML,
    REPORT_MARKDOWN,
    REPORT_PDF,         /* Requires external lib */
} report_format_t;

/* Report type */
typedef enum report_type {
    REPORT_DAILY,
    REPORT_WEEKLY,
    REPORT_MONTHLY,
    REPORT_INCIDENT,
    REPORT_AUDIT,
    REPORT_EXECUTIVE,
} report_type_t;

/* Report section */
typedef struct report_section {
    char            title[64];
    char            *content;
    int             priority;
    struct report_section *next;
} report_section_t;

/* Report */
typedef struct security_report {
    char            title[128];
    report_type_t   type;
    report_format_t format;
    
    uint64_t        generated_at;
    uint64_t        period_start;
    uint64_t        period_end;
    
    report_section_t *sections;
    int             section_count;
    
    /* Generated content */
    char            *output;
    size_t          output_len;
} security_report_t;

/* API */
shield_err_t report_init(security_report_t *report, const char *title,
                           report_type_t type, report_format_t format);
void report_destroy(security_report_t *report);

/* Sections */
shield_err_t report_add_section(security_report_t *report,
                                  const char *title, const char *content);
shield_err_t report_add_stats(security_report_t *report, void *stats);
shield_err_t report_add_incidents(security_report_t *report, void *incidents);

/* Generate */
shield_err_t report_generate(security_report_t *report);

/* Save */
shield_err_t report_save(security_report_t *report, const char *path);
shield_err_t report_send_email(security_report_t *report, const char *to);

/* Templates */
shield_err_t report_daily_template(security_report_t *report, void *ctx);
shield_err_t report_incident_template(security_report_t *report, void *incident);

#endif /* SHIELD_REPORT_H */
