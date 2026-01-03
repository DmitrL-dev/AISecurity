/*
 * SENTINEL IMMUNE — Herd Immunity Header
 */

#ifndef IMMUNE_HERD_H
#define IMMUNE_HERD_H

#include <stdint.h>
#include <stdbool.h>
#include <time.h>

/* Forward declarations */
struct immune_hive;

/* Signature structure */
typedef struct {
    uint32_t id;
    char pattern[256];
    uint8_t severity;
    time_t created;
    uint32_t source_agent;
} herd_signature_t;

/* Herd functions */
int herd_init(struct immune_hive *hive);
void herd_shutdown(struct immune_hive *hive);

int herd_add_signature(struct immune_hive *hive, const char *pattern, uint8_t severity);
int herd_broadcast_signature(struct immune_hive *hive, herd_signature_t *sig);
int herd_sync_signatures(struct immune_hive *hive, uint32_t agent_id);

#endif /* IMMUNE_HERD_H */
