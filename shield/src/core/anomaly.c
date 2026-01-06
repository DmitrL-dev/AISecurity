/*
 * SENTINEL Shield - Anomaly Detector Implementation
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>

#include "shield_anomaly.h"
#include "shield_timer.h"
#include "shield_entropy.h"
#include "shield_string_safe.h"

/* Update statistics window */
static void stat_update(stat_window_t *stat, double value)
{
    stat->sum += value;
    stat->sum_sq += value * value;
    stat->count++;
    
    if (stat->count == 1 || value < stat->min) stat->min = value;
    if (stat->count == 1 || value > stat->max) stat->max = value;
}

/* Get mean */
static double stat_mean(stat_window_t *stat)
{
    if (stat->count == 0) return 0;
    return stat->sum / stat->count;
}

/* Get standard deviation */
static double stat_stddev(stat_window_t *stat)
{
    if (stat->count < 2) return 0;
    
    double mean = stat_mean(stat);
    double variance = (stat->sum_sq / stat->count) - (mean * mean);
    
    return variance > 0 ? sqrt(variance) : 0;
}

/* Initialize */
shield_err_t anomaly_init(anomaly_detector_t *detector)
{
    if (!detector) return SHIELD_ERR_INVALID;
    
    memset(detector, 0, sizeof(*detector));
    detector->z_threshold = 3.0f;  /* 3 standard deviations */
    detector->min_samples = 100;
    
    return SHIELD_OK;
}

/* Destroy */
void anomaly_destroy(anomaly_detector_t *detector)
{
    /* Nothing to free */
    (void)detector;
}

/* Record request statistics */
void anomaly_record_request(anomaly_detector_t *detector, size_t len, float entropy)
{
    if (!detector) return;
    
    stat_update(&detector->length_stats, (double)len);
    stat_update(&detector->entropy_stats, (double)entropy);
    
    /* Track timing */
    uint64_t now = time_now_ms();
    if (detector->last_request_time > 0) {
        double interval = (double)(now - detector->last_request_time);
        stat_update(&detector->interval_stats, interval);
    }
    detector->last_request_time = now;
}

/* Analyze text for anomalies */
shield_err_t anomaly_analyze(anomaly_detector_t *detector,
                               const char *text, size_t len,
                               anomaly_result_t *result)
{
    if (!detector || !text || !result) {
        return SHIELD_ERR_INVALID;
    }
    
    memset(result, 0, sizeof(*result));
    result->type = ANOMALY_NONE;
    
    detector->analyzed++;
    
    /* Need minimum samples for detection */
    if (detector->length_stats.count < detector->min_samples) {
        /* Just record and return */
        float entropy = calculate_entropy((const uint8_t *)text, len);
        anomaly_record_request(detector, len, entropy);
        shield_strcopy_s(result->description, sizeof(result->description), "Insufficient samples for detection");
        return SHIELD_OK;
    }
    
    float max_score = 0;
    anomaly_type_t detected_type = ANOMALY_NONE;
    
    /* Check length anomaly */
    double len_mean = stat_mean(&detector->length_stats);
    double len_stddev = stat_stddev(&detector->length_stats);
    
    if (len_stddev > 0) {
        double z = fabs((double)len - len_mean) / len_stddev;
        result->z_score = (float)z;
        
        if (z > detector->z_threshold) {
            float score = (float)(z - detector->z_threshold) / 3.0f;
            if (score > 1.0f) score = 1.0f;
            
            if (score > max_score) {
                max_score = score;
                detected_type = ANOMALY_LENGTH;
            }
        }
    }
    
    /* Check entropy anomaly */
    float entropy = calculate_entropy((const uint8_t *)text, len);
    double ent_mean = stat_mean(&detector->entropy_stats);
    double ent_stddev = stat_stddev(&detector->entropy_stats);
    
    if (ent_stddev > 0) {
        double z = fabs(entropy - ent_mean) / ent_stddev;
        
        if (z > detector->z_threshold) {
            float score = (float)(z - detector->z_threshold) / 3.0f;
            if (score > 1.0f) score = 1.0f;
            
            if (score > max_score) {
                max_score = score;
                detected_type = ANOMALY_ENTROPY;
            }
        }
    }
    
    /* Check timing anomaly */
    if (detector->last_request_time > 0) {
        uint64_t now = time_now_ms();
        double interval = (double)(now - detector->last_request_time);
        
        double int_mean = stat_mean(&detector->interval_stats);
        double int_stddev = stat_stddev(&detector->interval_stats);
        
        if (int_stddev > 0 && int_mean > 0) {
            double z = fabs(interval - int_mean) / int_stddev;
            
            if (z > detector->z_threshold) {
                float score = (float)(z - detector->z_threshold) / 3.0f;
                if (score > 1.0f) score = 1.0f;
                
                if (score > max_score) {
                    max_score = score;
                    detected_type = ANOMALY_TIMING;
                }
            }
        }
    }
    
    /* Record for future detection */
    anomaly_record_request(detector, len, entropy);
    
    /* Set result */
    result->type = detected_type;
    result->score = max_score;
    
    if (detected_type != ANOMALY_NONE) {
        detector->anomalies_detected++;
        
        switch (detected_type) {
        case ANOMALY_LENGTH:
            snprintf(result->description, sizeof(result->description),
                     "Unusual length: %zu (mean: %.0f, stddev: %.0f)",
                     len, len_mean, len_stddev);
            break;
        case ANOMALY_ENTROPY:
            snprintf(result->description, sizeof(result->description),
                     "Unusual entropy: %.2f (mean: %.2f, stddev: %.2f)",
                     entropy, ent_mean, ent_stddev);
            break;
        case ANOMALY_TIMING:
            snprintf(result->description, sizeof(result->description),
                     "Unusual request timing");
            break;
        default:
            shield_strcopy_s(result->description, sizeof(result->description), "Anomaly detected");
        }
    } else {
        shield_strcopy_s(result->description, sizeof(result->description), "Normal");
    }
    
    return SHIELD_OK;
}

/* Get mean length */
double anomaly_get_mean_length(anomaly_detector_t *detector)
{
    return detector ? stat_mean(&detector->length_stats) : 0;
}

/* Get stddev length */
double anomaly_get_stddev_length(anomaly_detector_t *detector)
{
    return detector ? stat_stddev(&detector->length_stats) : 0;
}

/* Reset */
void anomaly_reset(anomaly_detector_t *detector)
{
    if (!detector) return;
    
    memset(&detector->length_stats, 0, sizeof(detector->length_stats));
    memset(&detector->entropy_stats, 0, sizeof(detector->entropy_stats));
    memset(&detector->interval_stats, 0, sizeof(detector->interval_stats));
    
    detector->last_request_time = 0;
    detector->analyzed = 0;
    detector->anomalies_detected = 0;
}
