/*
 * SENTINEL Shield - Umbrella Header
 * 
 * Include this header to get all Shield functionality
 */

#ifndef SENTINEL_SHIELD_H
#define SENTINEL_SHIELD_H

/* Version */
#define SHIELD_VERSION_MAJOR 1
#define SHIELD_VERSION_MINOR 2
#define SHIELD_VERSION_PATCH 0
#define SHIELD_VERSION_STRING "1.2.0"

/* ===== Core ===== */
#include "shield_common.h"
#include "shield_platform.h"
#include "shield_context.h"

/* ===== Zone and Rules ===== */
#include "shield_zone.h"
#include "shield_rule.h"
#include "shield_pattern.h"

/* ===== Guards ===== */
#include "shield_guard.h"

/* ===== Security Features ===== */
#include "shield_ratelimit.h"
#include "shield_blocklist.h"
#include "shield_session.h"
#include "shield_canary.h"
#include "shield_quarantine.h"
#include "shield_alert.h"
#include "shield_sanitizer.h"
#include "shield_fingerprint.h"

/* ===== Analysis (Sprint 9+) ===== */
#include "shield_semantic.h"
#include "shield_encoding.h"
#include "shield_signatures.h"
#include "shield_anomaly.h"
#include "shield_classifier.h"
#include "shield_ngram.h"
#include "shield_vectorizer.h"
#include "shield_embedding.h"

/* ===== Context Management ===== */
#include "shield_tokens.h"
#include "shield_context_window.h"
#include "shield_safety_prompt.h"
#include "shield_history.h"

/* ===== Output Processing ===== */
#include "shield_output_filter.h"
#include "shield_response_validator.h"

/* ===== Protocols ===== */
#include "protocol_stp.h"
#include "protocol_sbp.h"
#include "protocol_zdp.h"
#include "protocol_shsp.h"
#include "protocol_saf.h"
#include "protocol_ssrp.h"

/* ===== High Availability ===== */
#include "shield_ha.h"
#include "shield_health.h"

/* ===== Monitoring & Reporting ===== */
#include "shield_metrics.h"
#include "shield_event.h"
#include "shield_audit.h"
#include "shield_request_log.h"
#include "shield_stats.h"
#include "shield_report.h"

/* ===== Interfaces ===== */
#include "shield_cli.h"
#include "shield_api.h"
#include "shield_ffi.h"

/* ===== Extensions ===== */
#include "shield_plugin.h"
#include "shield_tls.h"
#include "shield_webhook.h"

/* ===== Reliability ===== */
#include "shield_timer.h"
#include "shield_circuit_breaker.h"
#include "shield_retry.h"
#include "shield_batch.h"

/* ===== Utilities ===== */
#include "shield_json.h"
#include "shield_syslog.h"
#include "shield_mempool.h"
#include "shield_ringbuf.h"
#include "shield_hashtable.h"
#include "shield_threadpool.h"
#include "shield_string.h"
#include "shield_base64.h"
#include "shield_entropy.h"

/* ===== eBPF (Linux only) ===== */
#ifdef __linux__
#include "shield_ebpf.h"
#endif

#endif /* SENTINEL_SHIELD_H */

