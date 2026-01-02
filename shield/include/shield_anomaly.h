/*
 * SENTINEL Shield - Anomaly Detector
 * 
 * Detect statistical anomalies in request patterns
 */

#ifndef SHIELD_ANOMALY_H
#define SHIELD_ANOMALY_H

#include "shield_common.h"

/* Anomaly types */
typedef enum anomaly_type {
    ANOMALY_NONE = 0,
    ANOMALY_LENGTH,         /* Unusual length */
    ANOMALY_FREQUENCY,      /* Unusual request rate */
    ANOMALY_ENTROPY,        /* Unusual entropy */
    ANOMALY_PATTERN,        /* Unusual pattern */
    ANOMALY_TIMING,         /* Unusual timing */
    ANOMALY_SEQUENCE,       /* Unusual sequence */
} anomaly_type_t;

/* Anomaly detection result */
typedef struct anomaly_result {
    anomaly_type_t  type;
    float           score;          /* 0-1, higher = more anomalous */
    float           z_score;        /* Standard deviations from mean */
    char            description[128];
} anomaly_result_t;

/* Statistics window */
typedef struct stat_window {
    double          sum;
    double          sum_sq;
    int             count;
    double          min;
    double          max;
} stat_window_t;

/* Anomaly detector */
typedef struct anomaly_detector {
    /* Length statistics */
    stat_window_t   length_stats;
    
    /* Entropy statistics */
    stat_window_t   entropy_stats;
    
    /* Timing statistics */
    stat_window_t   interval_stats;
    uint64_t        last_request_time;
    
    /* Thresholds */
    float           z_threshold;    /* Z-score threshold for anomaly */
    int             min_samples;    /* Minimum samples before detection */
    
    /* Stats */
    uint64_t        analyzed;
    uint64_t        anomalies_detected;
} anomaly_detector_t;

/* API */
shield_err_t anomaly_init(anomaly_detector_t *detector);
void anomaly_destroy(anomaly_detector_t *detector);

/* Analyze */
shield_err_t anomaly_analyze(anomaly_detector_t *detector,
                               const char *text, size_t len,
                               anomaly_result_t *result);

/* Update statistics */
void anomaly_record_request(anomaly_detector_t *detector, size_t len, float entropy);

/* Query */
double anomaly_get_mean_length(anomaly_detector_t *detector);
double anomaly_get_stddev_length(anomaly_detector_t *detector);

/* Reset */
void anomaly_reset(anomaly_detector_t *detector);

#endif /* SHIELD_ANOMALY_H */
