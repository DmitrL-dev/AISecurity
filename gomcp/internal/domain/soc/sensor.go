package soc

import (
	"time"
)

// SensorStatus represents the health state of a sensor (§11.3 state machine).
//
//	┌─────────┐  3 events  ┌─────────┐
//	│ UNKNOWN ├────────────►│ HEALTHY │◄──── heartbeat
//	└─────────┘             └────┬────┘
//	                             │ 3 missed heartbeats
//	                        ┌────▼─────┐
//	                        │ DEGRADED │
//	                        └────┬─────┘
//	                             │ 10 missed heartbeats
//	                        ┌────▼─────┐
//	                        │ OFFLINE  │── SOC alert → operator
//	                        └──────────┘
type SensorStatus string

const (
	SensorStatusUnknown  SensorStatus = "UNKNOWN"
	SensorStatusHealthy  SensorStatus = "HEALTHY"
	SensorStatusDegraded SensorStatus = "DEGRADED"
	SensorStatusOffline  SensorStatus = "OFFLINE"
)

// SensorType identifies the kind of sensor.
type SensorType string

const (
	SensorTypeSentinelCore SensorType = "sentinel-core"
	SensorTypeShield       SensorType = "shield"
	SensorTypeImmune       SensorType = "immune"
	SensorTypeMicroSwarm   SensorType = "micro-swarm"
	SensorTypeGoMCP        SensorType = "gomcp"
	SensorTypeExternal     SensorType = "external"
)

// HealthCheckThresholds for sensor lifecycle management.
const (
	EventsToHealthy         = 3  // Events needed to transition UNKNOWN → HEALTHY
	MissedHeartbeatDegraded = 3  // Missed heartbeats before DEGRADED
	MissedHeartbeatOffline  = 10 // Missed heartbeats before OFFLINE
	HeartbeatIntervalSec    = 60 // Expected heartbeat interval in seconds
)

// Sensor represents a registered sensor in the SOC (§11.3).
type Sensor struct {
	SensorID         string       `json:"sensor_id"`
	TenantID         string       `json:"tenant_id,omitempty"`
	SensorType       SensorType   `json:"sensor_type"`
	Status           SensorStatus `json:"status"`
	FirstSeen        time.Time    `json:"first_seen"`
	LastSeen         time.Time    `json:"last_seen"`
	EventCount       int          `json:"event_count"`
	MissedHeartbeats int          `json:"missed_heartbeats"`
	Hostname         string       `json:"hostname,omitempty"`
	Version          string       `json:"version,omitempty"`
}

// NewSensor creates a sensor entry upon first event ingest (auto-discovery).
func NewSensor(sensorID string, sensorType SensorType) Sensor {
	now := time.Now()
	return Sensor{
		SensorID:   sensorID,
		SensorType: sensorType,
		Status:     SensorStatusUnknown,
		FirstSeen:  now,
		LastSeen:   now,
		EventCount: 0,
	}
}

// RecordEvent increments the event counter and updates last_seen.
// Transitions UNKNOWN → HEALTHY after EventsToHealthy events.
func (s *Sensor) RecordEvent() {
	s.EventCount++
	s.LastSeen = time.Now()
	s.MissedHeartbeats = 0 // Reset on activity

	if s.Status == SensorStatusUnknown && s.EventCount >= EventsToHealthy {
		s.Status = SensorStatusHealthy
	}
	// Recover from degraded on activity
	if s.Status == SensorStatusDegraded {
		s.Status = SensorStatusHealthy
	}
}

// RecordHeartbeat updates last_seen and resets missed counter.
func (s *Sensor) RecordHeartbeat() {
	s.LastSeen = time.Now()
	s.MissedHeartbeats = 0
	if s.Status == SensorStatusDegraded || s.Status == SensorStatusUnknown {
		if s.EventCount >= EventsToHealthy {
			s.Status = SensorStatusHealthy
		}
	}
}

// MissHeartbeat increments the missed counter and transitions status.
// Returns true if a SOC alert should be generated (transition to OFFLINE).
func (s *Sensor) MissHeartbeat() (alertNeeded bool) {
	s.MissedHeartbeats++

	switch {
	case s.MissedHeartbeats >= MissedHeartbeatOffline && s.Status != SensorStatusOffline:
		s.Status = SensorStatusOffline
		return true // Generate SOC alert
	case s.MissedHeartbeats >= MissedHeartbeatDegraded && s.Status == SensorStatusHealthy:
		s.Status = SensorStatusDegraded
	}
	return false
}

// IsHealthy returns true if sensor is in HEALTHY state.
func (s *Sensor) IsHealthy() bool {
	return s.Status == SensorStatusHealthy
}

// TimeSinceLastSeen returns duration since last activity.
func (s *Sensor) TimeSinceLastSeen() time.Duration {
	return time.Since(s.LastSeen)
}
