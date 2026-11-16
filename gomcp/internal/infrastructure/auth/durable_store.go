package auth

import (
	"errors"
	"regexp"
	"time"
)

// ErrStoreUnavailable never includes database errors or account data. A write
// error may mean the server committed and lost its reply; fail closed until a
// fresh store has loaded the authoritative database successfully.
var ErrStoreUnavailable = errors.New("auth: durable store unavailable")

func cloneUser(u *User) *User {
	c := *u
	if u.VerifyExpiry != nil {
		v := *u.VerifyExpiry
		c.VerifyExpiry = &v
	}
	if u.LastLoginAt != nil {
		v := *u.LastLoginAt
		c.LastLoginAt = &v
	}
	return &c
}
func cloneTenant(t *Tenant) *Tenant {
	c := *t
	for _, pair := range [][2]**int{{&c.CustomMaxEvents, &t.CustomMaxEvents}, {&c.CustomMaxScans, &t.CustomMaxScans}, {&c.CustomMaxUsers, &t.CustomMaxUsers}, {&c.CustomMaxSensors, &t.CustomMaxSensors}} {
		if *pair[1] != nil {
			v := **pair[1]
			*pair[0] = &v
		}
	}
	return &c
}
func (s *UserStore) Ready() error {
	s.mu.RLock()
	defer s.mu.RUnlock()
	if s.unhealthy {
		return ErrStoreUnavailable
	}
	return nil
}
func (s *TenantStore) Ready() error {
	s.mu.RLock()
	defer s.mu.RUnlock()
	if s.unhealthy {
		return ErrStoreUnavailable
	}
	return nil
}
func (s *UserStore) publishUserLocked(candidate *User) error {
	if s.unhealthy {
		return ErrStoreUnavailable
	}
	if err := s.persistUser(*candidate); err != nil {
		s.unhealthy = true
		return ErrStoreUnavailable
	}
	s.users[candidate.Email] = cloneUser(candidate)
	return nil
}
func (s *UserStore) mutateUser(id string, change func(*User) error) error {
	s.mu.Lock()
	defer s.mu.Unlock()
	if s.unhealthy {
		return ErrStoreUnavailable
	}
	if s.db != nil {
		return s.mutateUserDurably(id, change)
	}
	for _, u := range s.users {
		if u.ID == id || u.Email == id {
			candidate := cloneUser(u)
			if err := change(candidate); err != nil {
				return err
			}
			return s.publishUserLocked(candidate)
		}
	}
	return ErrUserNotFound
}
func (s *TenantStore) mutateTenant(id string, change func(*Tenant) error) error {
	s.mu.Lock()
	defer s.mu.Unlock()
	if s.unhealthy {
		return ErrStoreUnavailable
	}
	if s.db != nil {
		return s.mutateTenantDurably(id, change)
	}
	t, ok := s.tenants[id]
	if !ok {
		return ErrTenantNotFound
	}
	candidate := cloneTenant(t)
	if err := change(candidate); err != nil {
		return err
	}
	if err := s.persistTenant(*candidate); err != nil {
		s.unhealthy = true
		return ErrStoreUnavailable
	}
	s.tenants[id] = cloneTenant(candidate)
	return nil
}
func (s *UserStore) setTenant(id, tenantID string, verified bool) error {
	return s.mutateUser(id, func(u *User) error {
		u.TenantID = tenantID
		if verified {
			u.EmailVerified = true
		}
		return nil
	})
}

// deleteTenant serializes both maps in one order. No RAM deletion is visible
// until the database transaction is confirmed. Unknown commit latches both stores.
func deleteTenant(users *UserStore, tenants *TenantStore, id string, cascade bool) error {
	users.mu.Lock()
	defer users.mu.Unlock()
	tenants.mu.Lock()
	defer tenants.mu.Unlock()
	if users.unhealthy || tenants.unhealthy {
		return ErrStoreUnavailable
	}
	if _, ok := tenants.tenants[id]; !ok {
		return ErrTenantNotFound
	}
	if users.db != tenants.db {
		return ErrStoreUnavailable
	}
	if tenants.db != nil {
		tx, err := tenants.db.Begin()
		if err != nil {
			users.unhealthy = true
			tenants.unhealthy = true
			return ErrStoreUnavailable
		}
		defer tx.Rollback()
		if cascade {
			if _, err = tx.Exec(`DELETE FROM api_keys WHERE user_id IN (SELECT id FROM users WHERE tenant_id=$1)`, id); err != nil {
				users.unhealthy = true
				tenants.unhealthy = true
				return ErrStoreUnavailable
			}
			if _, err = tx.Exec(`DELETE FROM users WHERE tenant_id=$1`, id); err != nil {
				users.unhealthy = true
				tenants.unhealthy = true
				return ErrStoreUnavailable
			}
		}
		if _, err = tx.Exec(`DELETE FROM tenants WHERE id=$1`, id); err != nil {
			users.unhealthy = true
			tenants.unhealthy = true
			return ErrStoreUnavailable
		}
		if err = tx.Commit(); err != nil {
			users.unhealthy = true
			tenants.unhealthy = true
			return ErrStoreUnavailable
		}
	}
	if cascade {
		for email, u := range users.users {
			if u.TenantID == id {
				delete(users.users, email)
			}
		}
	}
	delete(tenants.tenants, id)
	return nil
}

// SQLite legacy CURRENT_TIMESTAMP rows can be returned as strings even though
// modern writes and PostgreSQL return time.Time. Reject unknown encodings.
var legacyMonotonicSuffix = regexp.MustCompile(` m=[+-][0-9]+(?:\.[0-9]+)?$`)

type storeTime struct {
	Time  time.Time
	Valid bool
}

func (t *storeTime) Scan(value any) error {
	if value == nil {
		t.Time = time.Time{}
		t.Valid = false
		return nil
	}
	if v, ok := value.(time.Time); ok {
		t.Time = v
		t.Valid = true
		return nil
	}
	var text string
	switch v := value.(type) {
	case string:
		text = v
	case []byte:
		text = string(v)
	default:
		return ErrStoreUnavailable
	}
	if suffix := legacyMonotonicSuffix.FindStringIndex(text); suffix != nil {
		text = text[:suffix[0]]
	}
	for _, layout := range []string{time.RFC3339Nano, "2006-01-02 15:04:05", "2006-01-02 15:04:05.999999999-07:00", "2006-01-02 15:04:05.999999999 -0700 MST"} {
		if v, err := time.Parse(layout, text); err == nil {
			t.Time = v
			t.Valid = true
			return nil
		}
	}
	return ErrStoreUnavailable
}
