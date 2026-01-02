/*
 * SENTINEL Shield - Report Generator Implementation
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#include "shield_report.h"
#include "shield_stats.h"

/* Initialize */
shield_err_t report_init(security_report_t *report, const char *title,
                           report_type_t type, report_format_t format)
{
    if (!report || !title) return SHIELD_ERR_INVALID;
    
    memset(report, 0, sizeof(*report));
    strncpy(report->title, title, sizeof(report->title) - 1);
    report->type = type;
    report->format = format;
    report->generated_at = (uint64_t)time(NULL);
    
    return SHIELD_OK;
}

/* Destroy */
void report_destroy(security_report_t *report)
{
    if (!report) return;
    
    report_section_t *section = report->sections;
    while (section) {
        report_section_t *next = section->next;
        free(section->content);
        free(section);
        section = next;
    }
    
    free(report->output);
}

/* Add section */
shield_err_t report_add_section(security_report_t *report,
                                  const char *title, const char *content)
{
    if (!report || !title || !content) return SHIELD_ERR_INVALID;
    
    report_section_t *section = calloc(1, sizeof(report_section_t));
    if (!section) return SHIELD_ERR_NOMEM;
    
    strncpy(section->title, title, sizeof(section->title) - 1);
    section->content = strdup(content);
    section->priority = report->section_count;
    
    section->next = report->sections;
    report->sections = section;
    report->section_count++;
    
    return SHIELD_OK;
}

/* Add stats section */
shield_err_t report_add_stats(security_report_t *report, void *stats_ptr)
{
    if (!report || !stats_ptr) return SHIELD_ERR_INVALID;
    
    stats_collector_t *stats = (stats_collector_t *)stats_ptr;
    
    char buf[2048];
    snprintf(buf, sizeof(buf),
        "Total Requests: %lu\n"
        "Blocked: %lu (%.1f%%)\n"
        "Allowed: %lu\n"
        "Alerts Fired: %lu\n"
        "Alerts Resolved: %lu\n"
        "Avg Latency: %.2f ms\n"
        "Uptime: %lu seconds\n",
        (unsigned long)stats->current.requests_total.total,
        (unsigned long)stats->current.requests_blocked.total,
        stats->current.requests_total.total > 0 ?
            100.0 * stats->current.requests_blocked.total / 
            stats->current.requests_total.total : 0,
        (unsigned long)stats->current.requests_allowed.total,
        (unsigned long)stats->current.alerts_fired,
        (unsigned long)stats->current.alerts_resolved,
        stats->current.latency.count > 0 ?
            (double)stats->current.latency.sum_us / 
            stats->current.latency.count / 1000.0 : 0,
        (unsigned long)stats->current.uptime_seconds
    );
    
    return report_add_section(report, "Statistics Summary", buf);
}

/* Generate report */
shield_err_t report_generate(security_report_t *report)
{
    if (!report) return SHIELD_ERR_INVALID;
    
    size_t buf_size = 8192;
    char *buf = malloc(buf_size);
    if (!buf) return SHIELD_ERR_NOMEM;
    
    size_t pos = 0;
    
    /* Header */
    switch (report->format) {
    case REPORT_JSON:
        pos += snprintf(buf + pos, buf_size - pos, "{\n");
        pos += snprintf(buf + pos, buf_size - pos, 
            "  \"title\": \"%s\",\n", report->title);
        pos += snprintf(buf + pos, buf_size - pos,
            "  \"generated\": %lu,\n", (unsigned long)report->generated_at);
        pos += snprintf(buf + pos, buf_size - pos, "  \"sections\": [\n");
        break;
        
    case REPORT_MARKDOWN:
        pos += snprintf(buf + pos, buf_size - pos, "# %s\n\n", report->title);
        pos += snprintf(buf + pos, buf_size - pos, 
            "*Generated: %s*\n\n", ctime((time_t *)&report->generated_at));
        break;
        
    case REPORT_HTML:
        pos += snprintf(buf + pos, buf_size - pos,
            "<!DOCTYPE html>\n<html>\n<head>\n"
            "<title>%s</title>\n"
            "<style>body{font-family:sans-serif;margin:20px;}"
            "h1{color:#333;}h2{color:#666;}</style>\n"
            "</head>\n<body>\n<h1>%s</h1>\n",
            report->title, report->title);
        break;
        
    default:  /* TEXT */
        pos += snprintf(buf + pos, buf_size - pos,
            "=== %s ===\n\n", report->title);
    }
    
    /* Sections */
    int section_num = 0;
    report_section_t *section = report->sections;
    while (section) {
        switch (report->format) {
        case REPORT_JSON:
            if (section_num > 0) pos += snprintf(buf + pos, buf_size - pos, ",\n");
            pos += snprintf(buf + pos, buf_size - pos,
                "    {\"title\": \"%s\", \"content\": \"...\"}",
                section->title);
            break;
            
        case REPORT_MARKDOWN:
            pos += snprintf(buf + pos, buf_size - pos, "## %s\n\n", section->title);
            pos += snprintf(buf + pos, buf_size - pos, "%s\n\n", section->content);
            break;
            
        case REPORT_HTML:
            pos += snprintf(buf + pos, buf_size - pos,
                "<h2>%s</h2>\n<pre>%s</pre>\n",
                section->title, section->content);
            break;
            
        default:
            pos += snprintf(buf + pos, buf_size - pos,
                "--- %s ---\n%s\n\n", section->title, section->content);
        }
        
        section_num++;
        section = section->next;
    }
    
    /* Footer */
    switch (report->format) {
    case REPORT_JSON:
        pos += snprintf(buf + pos, buf_size - pos, "\n  ]\n}\n");
        break;
    case REPORT_HTML:
        pos += snprintf(buf + pos, buf_size - pos, "</body>\n</html>\n");
        break;
    default:
        break;
    }
    
    report->output = buf;
    report->output_len = pos;
    
    return SHIELD_OK;
}

/* Save to file */
shield_err_t report_save(security_report_t *report, const char *path)
{
    if (!report || !path || !report->output) return SHIELD_ERR_INVALID;
    
    FILE *f = fopen(path, "w");
    if (!f) return SHIELD_ERR_IO;
    
    fwrite(report->output, 1, report->output_len, f);
    fclose(f);
    
    return SHIELD_OK;
}

/* Send email (stub) */
shield_err_t report_send_email(security_report_t *report, const char *to)
{
    if (!report || !to) return SHIELD_ERR_INVALID;
    
    LOG_INFO("Email send requested to %s (not implemented)", to);
    
    return SHIELD_OK;
}

/* Daily template */
shield_err_t report_daily_template(security_report_t *report, void *ctx)
{
    if (!report) return SHIELD_ERR_INVALID;
    
    report_add_section(report, "Executive Summary",
        "This report summarizes security activity for the past 24 hours.");
    
    if (ctx) {
        report_add_stats(report, ctx);
    }
    
    report_add_section(report, "Recommendations",
        "1. Review blocked requests for false positives\n"
        "2. Update signature database if new patterns detected\n"
        "3. Monitor anomaly trends");
    
    return SHIELD_OK;
}

/* Incident template (stub) */
shield_err_t report_incident_template(security_report_t *report, void *incident)
{
    if (!report) return SHIELD_ERR_INVALID;
    
    report_add_section(report, "Incident Details",
        "Incident report template.");
    
    return SHIELD_OK;
}
