/*
 * SENTINEL IMMUNE — HAMMER2 Header
 */

#ifndef IMMUNE_HAMMER2_H
#define IMMUNE_HAMMER2_H

#include <stdint.h>
#include <stddef.h>

/* Snapshot management */
int hammer2_snapshot_create(const char *reason);
int hammer2_snapshot_rollback(const char *snap_name);
int hammer2_snapshot_cleanup(int keep_count);
void hammer2_snapshot_list(void);

/* Forensic timeline */
int forensic_record(const char *event_type, const char *details, int create_snapshot);
int forensic_export_json(const char *filename);

/* Quarantine integration */
int quarantine_with_snapshot(const char *threat_path, const char *threat_type);
int quarantine_rollback(const char *threat_path);

#endif /* IMMUNE_HAMMER2_H */
