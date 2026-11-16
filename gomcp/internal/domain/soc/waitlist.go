package soc

import "time"

// WaitlistEntry is a pre-signup registration interest. It carries cleartext PII
// (email + free-text company / use_case) and therefore lives in a DELETABLE store,
// so a subject's data can be erased on request (GDPR Art.17). This is deliberately
// NOT the immutable decision audit chain (which records only a salted hash that a
// signup occurred) and NOT the application log (which has no per-subject deletion).
type WaitlistEntry struct {
	ID        string    `json:"id"`
	Email     string    `json:"email"`
	Company   string    `json:"company,omitempty"`
	UseCase   string    `json:"use_case,omitempty"`
	CreatedAt time.Time `json:"created_at"`
}

// NewWaitlistEntry builds an entry with a collision-safe generated ID.
func NewWaitlistEntry(email, company, useCase string, now time.Time) WaitlistEntry {
	return WaitlistEntry{
		ID:        genID("wl"),
		Email:     email,
		Company:   company,
		UseCase:   useCase,
		CreatedAt: now,
	}
}
