/*
 * SENTINEL IMMUNE — Hive Network Header
 */

#ifndef IMMUNE_NETWORK_H
#define IMMUNE_NETWORK_H

#include <stdint.h>
#include "hive.h"

/* Network functions */
int   hive_network_start(immune_hive_t *hive, uint16_t port);
void* hive_network_thread(void *arg);

/* API functions */
int   hive_api_start(immune_hive_t *hive, uint16_t port);
void* hive_api_thread(void *arg);

#endif /* IMMUNE_NETWORK_H */
