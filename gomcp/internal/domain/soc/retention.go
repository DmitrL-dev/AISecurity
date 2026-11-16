package soc

import (
	"sync"
	"time"
)

// DataRetentionPolicy implements §19 — configurable data lifecycle management.
// Enforces retention windows and auto-archives/purges old events.
type DataRetentionPolicy struct {
	mu       sync.RWMutex
	policies map[string]RetentionRule
}

// RetentionRule defines how long data of a given type is kept.
type RetentionRule struct {
	DataType    string        `json:"data_type"`    // events, incidents, audit, anomaly_alerts
	RetainDays  int           `json:"retain_days"`  // Max age in days
	Action      string        `json:"action"`       // archive, delete, compress
	Enabled     bool          `json:"enabled"`
	LastRun     time.Time     `json:"last_run"`
	ItemsPurged int           `json:"items_purged"`
}

// NewDataRetentionPolicy creates default retention rules.
func NewDataRetentionPolicy() *DataRetentionPolicy {
	return &DataRetentionPolicy{
		policies: map[string]RetentionRule{
			"events": {
				DataType:   "events",
				RetainDays: 90,
				Action:     "archive",
				Enabled:    true,
			},
			"incidents": {
				DataType:   "incidents",
				RetainDays: 365,
				Action:     "archive",
				Enabled:    true,
			},
			"audit": {
				DataType:   "audit",
				RetainDays: 730, // 2 years for compliance
				Action:     "compress",
				Enabled:    true,
			},
			"anomaly_alerts": {
				DataType:   "anomaly_alerts",
				RetainDays: 30,
				Action:     "delete",
				Enabled:    true,
			},
			"playbook_log": {
				DataType:   "playbook_log",
				RetainDays: 180,
				Action:     "archive",
				Enabled:    true,
			},
		},
	}
}

// SetPolicy updates a retention rule.
func (d *DataRetentionPolicy) SetPolicy(dataType string, retainDays int, action string) {
	d.mu.Lock()
	defer d.mu.Unlock()
	d.policies[dataType] = RetentionRule{
		DataType:   dataType,
		RetainDays: retainDays,
		Action:     action,
		Enabled:    true,
	}
}

// GetPolicy returns the retention rule for a data type.
func (d *DataRetentionPolicy) GetPolicy(dataType string) (RetentionRule, bool) {
	d.mu.RLock()
	defer d.mu.RUnlock()
	r, ok := d.policies[dataType]
	return r, ok
}

// ListPolicies returns all retention policies.
func (d *DataRetentionPolicy) ListPolicies() []RetentionRule {
	d.mu.RLock()
	defer d.mu.RUnlock()
	result := make([]RetentionRule, 0, len(d.policies))
	for _, r := range d.policies {
		result = append(result, r)
	}
	return result
}

// IsExpired checks if a timestamp has exceeded the retention window.
func (d *DataRetentionPolicy) IsExpired(dataType string, timestamp time.Time) bool {
	d.mu.RLock()
	defer d.mu.RUnlock()
	r, ok := d.policies[dataType]
	if !ok || !r.Enabled {
		return false
	}
	cutoff := time.Now().AddDate(0, 0, -r.RetainDays)
	return timestamp.Before(cutoff)
}

// Enforce runs retention checks and returns items to purge.
// In production, this would interact with the database.
func (d *DataRetentionPolicy) Enforce(dataType string, timestamps []time.Time) (expired int) {
	d.mu.Lock()
	defer d.mu.Unlock()

	r, ok := d.policies[dataType]
	if !ok || !r.Enabled {
		return 0
	}

	cutoff := time.Now().AddDate(0, 0, -r.RetainDays)
	for _, t := range timestamps {
		if t.Before(cutoff) {
			expired++
		}
	}

	r.LastRun = time.Now()
	r.ItemsPurged += expired
	d.policies[dataType] = r
	return expired
}

// RetentionStats returns retention policy statistics.
func (d *DataRetentionPolicy) RetentionStats() map[string]any {
	d.mu.RLock()
	defer d.mu.RUnlock()
	// Copy the policies map: returning the internal map would let the caller
	// read it (e.g. JSON-marshal) after the lock is released, racing with
	// SetPolicy/Enforce writers (fatal "concurrent map read and map write").
	policies := make(map[string]RetentionRule, len(d.policies))
	for k, v := range d.policies {
		policies[k] = v
	}
	return map[string]any{
		"total_policies": len(d.policies),
		"policies":       policies,
	}
}
