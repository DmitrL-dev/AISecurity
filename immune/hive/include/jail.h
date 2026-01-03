/*
 * SENTINEL IMMUNE — Jail Quarantine Header
 */

#ifndef IMMUNE_JAIL_H
#define IMMUNE_JAIL_H

#include <sys/types.h>

/* Jail management */
int jail_quarantine_init(void);
void jail_quarantine_shutdown(void);

/* Process quarantine */
int quarantine_process(pid_t pid, int threat_level, const char *reason);
int quarantine_release_process(pid_t pid);
int quarantine_kill_process(pid_t pid);

/* File quarantine */
int quarantine_file(const char *path, int threat_level, const char *reason);
int quarantine_restore_file(const char *original_path);
int quarantine_delete_file(const char *original_path);

/* Reporting */
void quarantine_status(void);
int quarantine_export_json(const char *filename);

#endif /* IMMUNE_JAIL_H */
