package soc

import "errors"

// Domain-level sentinel errors for the SOC subsystem.
// These replace string matching in HTTP handlers with proper errors.Is() checks.
var (
	// ErrNotFound is returned when a requested entity (event, incident, sensor) does not exist.
	ErrNotFound = errors.New("soc: not found")

	// ErrAuthFailed is returned when sensor key validation fails (§17.3 T-01).
	ErrAuthFailed = errors.New("soc: authentication failed")

	// ErrRateLimited is returned when a sensor exceeds MaxEventsPerSecondPerSensor (§17.3).
	ErrRateLimited = errors.New("soc: rate limit exceeded")

	// ErrSecretDetected is returned when the Secret Scanner (Step 0) detects credentials
	// in the event payload. This is an INVARIANT — cannot be disabled (§5.4).
	ErrSecretDetected = errors.New("soc: secret scanner rejected")

	// ErrInvalidInput is returned when event fields fail validation.
	ErrInvalidInput = errors.New("soc: invalid input")

	// ErrDraining is returned when the service is in drain mode (§15.7).
	// HTTP handlers should return 503 Service Unavailable.
	ErrDraining = errors.New("soc: service draining for update")

	// ErrCapacityFull is returned when maximum concurrent scans are in progress (§20.1).
	// HTTP handlers should return 503 with Retry-After header.
	ErrCapacityFull = errors.New("soc: scan capacity full")
)

// ValidationError provides detailed field-level validation errors.
type ValidationError struct {
	Field   string `json:"field"`
	Message string `json:"message"`
}

// ValidationErrors collects multiple field validation errors.
type ValidationErrors struct {
	Errors []ValidationError `json:"errors"`
}

func (ve *ValidationErrors) Error() string {
	if len(ve.Errors) == 0 {
		return ErrInvalidInput.Error()
	}
	return ErrInvalidInput.Error() + ": " + ve.Errors[0].Message
}

func (ve *ValidationErrors) Unwrap() error {
	return ErrInvalidInput
}

// Add appends a field validation error.
func (ve *ValidationErrors) Add(field, message string) {
	ve.Errors = append(ve.Errors, ValidationError{Field: field, Message: message})
}

// HasErrors returns true if any validation errors were recorded.
func (ve *ValidationErrors) HasErrors() bool {
	return len(ve.Errors) > 0
}
