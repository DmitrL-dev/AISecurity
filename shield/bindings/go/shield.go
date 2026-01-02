// SENTINEL Shield Go Bindings
//
// Usage:
//
//   import "github.com/sentinel/shield"
//
//   s := shield.New()
//   defer s.Close()
//
//   s.ZoneCreate("gpt4", shield.ZoneLLM)
//   s.RuleAdd(100, 10, shield.ActionBlock, shield.DirInput, shield.ZoneLLM, "ignore.*")
//
//   result := s.Evaluate("gpt4", shield.DirInput, "ignore instructions")
//   if result.Action == shield.ActionBlock {
//       fmt.Println("Blocked:", result.Reason)
//   }

package shield

/*
#cgo LDFLAGS: -L. -lsentinel-shield
#include <stdlib.h>
#include "shield_ffi.h"
*/
import "C"
import (
	"unsafe"
)

// Action types
const (
	ActionAllow      = 0
	ActionBlock      = 1
	ActionQuarantine = 2
	ActionLog        = 3
)

// Direction types
const (
	DirInput  = 0
	DirOutput = 1
)

// Zone types
const (
	ZoneUnknown = 0
	ZoneLLM     = 1
	ZoneRAG     = 2
	ZoneAgent   = 3
	ZoneTool    = 4
	ZoneMCP     = 5
	ZoneAPI     = 6
)

// EvalResult represents evaluation result
type EvalResult struct {
	Action     int
	RuleNumber uint32
	Confidence float32
	Reason     string
}

// Shield is the main wrapper
type Shield struct {
	handle C.shield_handle_t
}

// New creates new Shield instance
func New() *Shield {
	handle := C.shield_init()
	if handle == nil {
		return nil
	}
	return &Shield{handle: handle}
}

// Close destroys Shield instance
func (s *Shield) Close() {
	if s.handle != nil {
		C.shield_destroy(s.handle)
		s.handle = nil
	}
}

// Version returns Shield version
func (s *Shield) Version() string {
	return C.GoString(C.shield_version())
}

// ZoneCreate creates a new zone
func (s *Shield) ZoneCreate(name string, zoneType int) bool {
	cName := C.CString(name)
	defer C.free(unsafe.Pointer(cName))
	return C.shield_zone_create(s.handle, cName, C.shield_zone_type_t(zoneType)) == 0
}

// ZoneDelete deletes a zone
func (s *Shield) ZoneDelete(name string) bool {
	cName := C.CString(name)
	defer C.free(unsafe.Pointer(cName))
	return C.shield_zone_delete(s.handle, cName) == 0
}

// ZoneSetACL sets zone ACLs
func (s *Shield) ZoneSetACL(name string, inACL, outACL uint32) bool {
	cName := C.CString(name)
	defer C.free(unsafe.Pointer(cName))
	return C.shield_zone_set_acl(s.handle, cName, C.uint32_t(inACL), C.uint32_t(outACL)) == 0
}

// ZoneCount returns zone count
func (s *Shield) ZoneCount() int {
	return int(C.shield_zone_count(s.handle))
}

// RuleAdd adds a rule
func (s *Shield) RuleAdd(acl, ruleNum uint32, action, direction, zoneType int, pattern string) bool {
	var cPattern *C.char
	if pattern != "" {
		cPattern = C.CString(pattern)
		defer C.free(unsafe.Pointer(cPattern))
	}
	return C.shield_rule_add(
		s.handle,
		C.uint32_t(acl),
		C.uint32_t(ruleNum),
		C.shield_action_t(action),
		C.shield_direction_t(direction),
		C.shield_zone_type_t(zoneType),
		cPattern,
	) == 0
}

// RuleDelete deletes a rule
func (s *Shield) RuleDelete(acl, ruleNum uint32) bool {
	return C.shield_rule_delete(s.handle, C.uint32_t(acl), C.uint32_t(ruleNum)) == 0
}

// Evaluate evaluates data against rules
func (s *Shield) Evaluate(zone string, direction int, data string) EvalResult {
	cZone := C.CString(zone)
	defer C.free(unsafe.Pointer(cZone))
	cData := C.CString(data)
	defer C.free(unsafe.Pointer(cData))

	result := C.shield_evaluate(
		s.handle,
		cZone,
		C.shield_direction_t(direction),
		cData,
		C.size_t(len(data)),
	)

	return EvalResult{
		Action:     int(result.action),
		RuleNumber: uint32(result.rule_number),
		Confidence: float32(result.confidence),
		Reason:     C.GoString(&result.reason[0]),
	}
}

// Check is quick check, returns action only
func (s *Shield) Check(zone string, direction int, data string) int {
	cZone := C.CString(zone)
	defer C.free(unsafe.Pointer(cZone))
	cData := C.CString(data)
	defer C.free(unsafe.Pointer(cData))

	return int(C.shield_check(
		s.handle,
		cZone,
		C.shield_direction_t(direction),
		cData,
		C.size_t(len(data)),
	))
}

// IsAllowed checks if data is allowed
func (s *Shield) IsAllowed(zone string, data string) bool {
	return s.Check(zone, DirInput, data) == ActionAllow
}

// IsBlocked checks if data is blocked
func (s *Shield) IsBlocked(zone string, data string) bool {
	return s.Check(zone, DirInput, data) == ActionBlock
}

// BlocklistAdd adds pattern to blocklist
func (s *Shield) BlocklistAdd(pattern, reason string) bool {
	cPattern := C.CString(pattern)
	defer C.free(unsafe.Pointer(cPattern))
	var cReason *C.char
	if reason != "" {
		cReason = C.CString(reason)
		defer C.free(unsafe.Pointer(cReason))
	}
	return C.shield_blocklist_add(s.handle, cPattern, cReason) == 0
}

// BlocklistCheck checks if text matches blocklist
func (s *Shield) BlocklistCheck(text string) bool {
	cText := C.CString(text)
	defer C.free(unsafe.Pointer(cText))
	return bool(C.shield_blocklist_check(s.handle, cText))
}

// RateLimitConfig configures rate limiter
func (s *Shield) RateLimitConfig(rps, burst uint32) bool {
	return C.shield_ratelimit_config(s.handle, C.uint32_t(rps), C.uint32_t(burst)) == 0
}

// RateLimitAcquire acquires rate limit token
func (s *Shield) RateLimitAcquire(key string) bool {
	cKey := C.CString(key)
	defer C.free(unsafe.Pointer(cKey))
	return bool(C.shield_ratelimit_acquire(s.handle, cKey))
}

// CanaryCreate creates canary token
func (s *Shield) CanaryCreate(value, description string) string {
	cValue := C.CString(value)
	defer C.free(unsafe.Pointer(cValue))
	var cDesc *C.char
	if description != "" {
		cDesc = C.CString(description)
		defer C.free(unsafe.Pointer(cDesc))
	}

	outID := make([]byte, 64)
	result := C.shield_canary_create(
		s.handle,
		cValue,
		cDesc,
		(*C.char)(unsafe.Pointer(&outID[0])),
		64,
	)
	if result != 0 {
		return ""
	}
	return string(outID)
}

// CanaryScan scans text for canary tokens
func (s *Shield) CanaryScan(text string) bool {
	cText := C.CString(text)
	defer C.free(unsafe.Pointer(cText))
	return bool(C.shield_canary_scan(s.handle, cText, C.size_t(len(text))))
}

// Stats returns (total, blocked, allowed)
func (s *Shield) Stats() (uint64, uint64, uint64) {
	var total, blocked, allowed C.uint64_t
	C.shield_stats(s.handle, &total, &blocked, &allowed)
	return uint64(total), uint64(blocked), uint64(allowed)
}

// StatsReset resets statistics
func (s *Shield) StatsReset() {
	C.shield_stats_reset(s.handle)
}

// MetricsExport exports metrics in Prometheus format
func (s *Shield) MetricsExport() string {
	result := C.shield_metrics_export(s.handle)
	if result == nil {
		return ""
	}
	text := C.GoString(result)
	C.shield_free_string(result)
	return text
}

// ActionName returns action name
func ActionName(action int) string {
	switch action {
	case ActionAllow:
		return "allow"
	case ActionBlock:
		return "block"
	case ActionQuarantine:
		return "quarantine"
	case ActionLog:
		return "log"
	default:
		return "unknown"
	}
}
