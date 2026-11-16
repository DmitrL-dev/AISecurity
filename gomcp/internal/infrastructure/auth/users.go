package auth

import (
	"crypto/rand"
	"crypto/sha256"
	"database/sql"
	"encoding/hex"
	"errors"
	"fmt"
	"log/slog"
	"math/big"
	"os"
	"sync"
	"time"

	"golang.org/x/crypto/bcrypt"
)

// Standard user errors.
var (
	ErrUserNotFound      = errors.New("auth: user not found")
	ErrUserExists        = errors.New("auth: user already exists")
	ErrInvalidPassword   = errors.New("auth: invalid password")
	ErrUserDisabled      = errors.New("auth: account disabled")
	ErrEmailNotVerified  = errors.New("auth: email not verified")
	ErrInvalidVerifyCode = errors.New("auth: invalid or expired verification code")
)

// User represents an authenticated user in the system.
type User struct {
	ID            string     `json:"id"`
	Email         string     `json:"email"`
	DisplayName   string     `json:"display_name"`
	Role          string     `json:"role"` // admin, analyst, viewer
	TenantID      string     `json:"tenant_id,omitempty"`
	Active        bool       `json:"active"`
	EmailVerified bool       `json:"email_verified"`
	PasswordHash  string     `json:"-"` // never serialized
	VerifyToken   string     `json:"-"` // never serialized
	VerifyExpiry  *time.Time `json:"-"` // never serialized
	CreatedAt     time.Time  `json:"created_at"`
	LastLoginAt   *time.Time `json:"last_login_at,omitempty"`
}

// UserStore manages user credentials backed by SQLite.
// Falls back to in-memory store if no DB is provided.
type UserStore struct {
	mu        sync.RWMutex
	unhealthy bool
	db        *sql.DB
	users     map[string]*User // email -> User (in-memory cache / fallback)
	// key_hash -> when last_used was last written. Bounds the write to one per key per
	// lastUsedResolution, which is what lets it be synchronous on the request path.
	lastUsedWritten map[string]time.Time
}

// lastUsedResolution is how stale api_keys.last_used may be. "Used in the last minute" is all the
// column has to say, and writing it on every request would double the work of every authenticated call.
const lastUsedResolution = time.Minute

// NewUserStore creates a user store. If db is nil, uses in-memory only.
func NewUserStore(db ...*sql.DB) *UserStore {
	s := &UserStore{
		users:           make(map[string]*User),
		lastUsedWritten: make(map[string]time.Time),
	}

	if len(db) > 0 && db[0] != nil {
		s.db = db[0]
		if err := s.migrate(); err != nil {
			s.unhealthy = true
		} else {
			s.loadFromDB()
		}
	}

	if s.unhealthy {
		return s
	}

	// Ensure default admin exists or is updated
	adminPass := os.Getenv("SYNTREX_ADMIN_PASSWORD")
	if adminPass == "" {
		// If no env var, use a secure random password to prevent accidental exposure
		// if the database is clean, but do not override an existing admin's password.
		b := make([]byte, 16)
		rand.Read(b)
		adminPass = hex.EncodeToString(b)
	}

	hash, _ := bcrypt.GenerateFromPassword([]byte(adminPass), bcrypt.DefaultCost)

	if existingAdmin, err := s.GetByEmail("admin@syntrex.pro"); err == nil {
		// User exists. Let's update their password and role to superadmin
		// only if SYNTREX_ADMIN_PASSWORD was explicitly provided.
		if os.Getenv("SYNTREX_ADMIN_PASSWORD") != "" {
			if err := s.mutateUser(existingAdmin.ID, func(u *User) error { u.PasswordHash = string(hash); u.Role = "superadmin"; return nil }); err != nil {
				return s
			}
			slog.Info("default admin updated with password from SYNTREX_ADMIN_PASSWORD")
		}
	} else {
		if err != ErrUserNotFound {
			return s
		}
		// User does not exist, create it.
		if os.Getenv("SYNTREX_ADMIN_PASSWORD") == "" {
			// SEC (pre-launch audit 18.06): NEVER log the generated password. The admin
			// row is created with an unguessable random password (so the account is
			// inaccessible until bootstrapped); the operator sets SYNTREX_ADMIN_PASSWORD
			// and restarts to set a known password (handled by the existing-admin update
			// branch above). No secret is written to logs.
			slog.Warn("SYNTREX_ADMIN_PASSWORD not set — default admin created with an " +
				"unguessable random password that was NOT logged; set SYNTREX_ADMIN_PASSWORD and restart to control it")
		}
		admin := &User{
			ID:            generateID("usr"),
			Email:         "admin@syntrex.pro",
			DisplayName:   "Administrator",
			Role:          "superadmin",
			Active:        true,
			EmailVerified: true,
			PasswordHash:  string(hash),
			CreatedAt:     time.Now().UTC(),
		}
		s.mu.Lock()
		if err := s.persistUser(*admin); err != nil {
			s.unhealthy = true
		} else {
			s.users[admin.Email] = cloneUser(admin)
		}
		s.mu.Unlock()
		if s.unhealthy {
			return s
		}
		slog.Info("default admin created", "email", admin.Email)
	}

	return s
}

// migrate creates the users table if not exists.
func (s *UserStore) migrate() error {
	_, err := s.db.Exec(`
		CREATE TABLE IF NOT EXISTS users (
			id             TEXT PRIMARY KEY,
			email          TEXT UNIQUE NOT NULL,
			display_name   TEXT NOT NULL DEFAULT '',
			role           TEXT NOT NULL DEFAULT 'viewer',
			active         BOOLEAN NOT NULL DEFAULT true,
			email_verified BOOLEAN NOT NULL DEFAULT false,
			password_hash  TEXT NOT NULL,
			verify_token   TEXT DEFAULT '',
			verify_expiry  TIMESTAMPTZ,
			tenant_id      TEXT DEFAULT '',
			created_at     TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
			last_login_at  TIMESTAMPTZ
		);
		CREATE TABLE IF NOT EXISTS api_keys (
			id        TEXT PRIMARY KEY,
			user_id   TEXT NOT NULL REFERENCES users(id),
			key_hash  TEXT NOT NULL,
 key_prefix TEXT NOT NULL DEFAULT '',
			name      TEXT NOT NULL DEFAULT '',
			role      TEXT NOT NULL DEFAULT 'viewer',
			created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
			last_used  TIMESTAMPTZ
		);
	`)
	if err != nil {
		return err
	}
	// Add columns if upgrading from older schema (ignore errors if column exists)
	s.db.Exec(`ALTER TABLE api_keys ADD COLUMN key_prefix TEXT NOT NULL DEFAULT ''`)
	s.db.Exec(`ALTER TABLE users ADD COLUMN display_name TEXT NOT NULL DEFAULT ''`)
	s.db.Exec(`ALTER TABLE users ADD COLUMN role TEXT NOT NULL DEFAULT 'viewer'`)
	s.db.Exec(`ALTER TABLE users ADD COLUMN active BOOLEAN NOT NULL DEFAULT true`)
	s.db.Exec(`ALTER TABLE users ADD COLUMN email_verified BOOLEAN NOT NULL DEFAULT false`)
	s.db.Exec(`ALTER TABLE users ADD COLUMN password_hash TEXT NOT NULL DEFAULT ''`)
	// Legacy SaaS builds used a `password` column; new code uses password_hash.
	// Keep the old NOT NULL column harmless so inserts that omit it do not fail.
	s.db.Exec(`ALTER TABLE users ALTER COLUMN password SET DEFAULT ''`)
	s.db.Exec(`UPDATE users SET password = '' WHERE password IS NULL`)
	s.db.Exec(`ALTER TABLE users ADD COLUMN verify_token TEXT DEFAULT ''`)
	s.db.Exec(`ALTER TABLE users ADD COLUMN verify_expiry TIMESTAMPTZ`)
	s.db.Exec(`ALTER TABLE users ADD COLUMN tenant_id TEXT DEFAULT ''`)
	s.db.Exec(`ALTER TABLE users ADD COLUMN created_at TIMESTAMPTZ`)
	s.db.Exec(`ALTER TABLE users ADD COLUMN last_login_at TIMESTAMPTZ`)
	s.db.Exec(`UPDATE users SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL`)
	return nil
}

// loadFromDB loads all users from DB into memory cache.
func (s *UserStore) loadFromDB() {
	rows, err := s.db.Query(`SELECT id, email, display_name, role, active, email_verified, password_hash, verify_token, verify_expiry, created_at, last_login_at, COALESCE(tenant_id, '') FROM users`)
	if err != nil {
		s.unhealthy = true
		return
	}
	defer rows.Close()

	s.mu.Lock()
	defer s.mu.Unlock()
	candidate := make(map[string]*User)
	seenIDs := make(map[string]bool)
	for rows.Next() {
		var u User
		var lastLogin storeTime
		var createdAt storeTime
		var verifyToken sql.NullString
		var verifyExpiry storeTime
		if err := rows.Scan(&u.ID, &u.Email, &u.DisplayName, &u.Role, &u.Active, &u.EmailVerified, &u.PasswordHash, &verifyToken, &verifyExpiry, &createdAt, &lastLogin, &u.TenantID); err != nil {
			s.unhealthy = true
			return
		}
		if !createdAt.Valid {
			s.unhealthy = true
			return
		}
		u.CreatedAt = createdAt.Time
		if lastLogin.Valid {
			u.LastLoginAt = &lastLogin.Time
		}
		if verifyToken.Valid {
			u.VerifyToken = verifyToken.String
		}
		if verifyExpiry.Valid {
			u.VerifyExpiry = &verifyExpiry.Time
		}
		if u.ID == "" || u.Email == "" || candidate[u.Email] != nil || seenIDs[u.ID] {
			s.unhealthy = true
			return
		}
		seenIDs[u.ID] = true
		candidate[u.Email] = cloneUser(&u)
	}
	if rows.Err() != nil {
		s.unhealthy = true
		return
	}
	s.users = candidate
	slog.Info("users loaded from DB", "count", len(s.users))
}

// persistUser writes a user to DB (PostgreSQL-compatible upsert).
//
// Call under the store mutation lock and publish only after confirmed success.
func (s *UserStore) persistUser(u User) error {
	if s.db == nil {
		return nil
	}
	_, err := s.db.Exec(`
		INSERT INTO users (id, email, display_name, role, active, email_verified, password_hash, verify_token, verify_expiry, created_at, last_login_at, tenant_id)
		VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)`,
		u.ID, u.Email, u.DisplayName, u.Role, u.Active, u.EmailVerified, u.PasswordHash, u.VerifyToken, u.VerifyExpiry, u.CreatedAt, u.LastLoginAt, u.TenantID,
	)
	return err
}

// --- CRUD Operations ---

// CreateUser creates a new user with a hashed password and no tenant scoping.
func (s *UserStore) CreateUser(email, displayName, password, role string) (*User, error) {
	return s.CreateUserInTenant(email, displayName, password, role, "")
}

// CreateUserInTenant creates a user scoped to tenantID. Review 13.06 (audit B6):
// HandleCreateUser must propagate the caller's tenant — plain CreateUser left
// TenantID empty, orphaning users and breaking multi-tenant isolation. TenantID
// is set BEFORE the single persist (no async re-persist race).
func (s *UserStore) CreateUserInTenant(email, displayName, password, role, tenantID string) (*User, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	if s.unhealthy {
		return nil, ErrStoreUnavailable
	}

	if _, exists := s.users[email]; exists {
		return nil, ErrUserExists
	}

	// Also check DB for existing users (covers case where in-memory cache is stale)
	if s.db != nil {
		var count int
		if err := s.db.QueryRow(`SELECT COUNT(*) FROM users WHERE email = $1`, email).Scan(&count); err != nil {
			s.unhealthy = true
			return nil, ErrStoreUnavailable
		}
		if count > 0 {
			return nil, ErrUserExists
		}
	}

	hash, err := bcrypt.GenerateFromPassword([]byte(password), bcrypt.DefaultCost)
	if err != nil {
		return nil, fmt.Errorf("auth: hash password: %w", err)
	}

	u := &User{
		ID:           generateID("usr"),
		Email:        email,
		DisplayName:  displayName,
		Role:         role,
		TenantID:     tenantID,
		Active:       true,
		PasswordHash: string(hash),
		CreatedAt:    time.Now().UTC(),
	}

	if err := s.publishUserLocked(u); err != nil {
		return nil, err
	}
	return cloneUser(u), nil
}

// reloadUserByEmail refreshes one user from the DB into the cache (no-op when
// no DB is configured). Review 13.06 (audit D2): makes auth DB-authoritative so
// a user created / disabled / password-changed / deleted on another replica
// (Postgres backend, scaled out) is honored here on the next login instead of
// trusting a possibly-stale in-memory cache.
func (s *UserStore) reloadUserByEmail(email string) error {
	if s.db == nil {
		return nil
	}
	var u User
	var lastLogin storeTime
	var createdAt storeTime
	var verifyToken sql.NullString
	var verifyExpiry storeTime
	err := s.db.QueryRow(
		`SELECT id, email, display_name, role, active, email_verified, password_hash, verify_token, verify_expiry, created_at, last_login_at, COALESCE(tenant_id, '') FROM users WHERE email = $1`, email,
	).Scan(&u.ID, &u.Email, &u.DisplayName, &u.Role, &u.Active, &u.EmailVerified, &u.PasswordHash, &verifyToken, &verifyExpiry, &createdAt, &lastLogin, &u.TenantID)
	if err != nil {
		if err == sql.ErrNoRows {
			delete(s.users, email)
		}
		if err == sql.ErrNoRows {
			return nil
		}
		s.unhealthy = true
		return ErrStoreUnavailable
	}
	if !createdAt.Valid {
		s.unhealthy = true
		return ErrStoreUnavailable
	}
	u.CreatedAt = createdAt.Time
	if lastLogin.Valid {
		u.LastLoginAt = &lastLogin.Time
	}
	if verifyToken.Valid {
		u.VerifyToken = verifyToken.String
	}
	if verifyExpiry.Valid {
		u.VerifyExpiry = &verifyExpiry.Time
	}
	s.users[u.Email] = cloneUser(&u)
	return nil
}

// Authenticate validates email/password and returns the user.
func (s *UserStore) Authenticate(email, password string) (*User, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	if s.unhealthy {
		return nil, ErrStoreUnavailable
	}
	if err := s.reloadUserByEmail(email); err != nil {
		return nil, err
	}
	u, ok := s.users[email]
	if !ok {
		return nil, ErrUserNotFound
	}
	if !u.Active {
		return nil, ErrUserDisabled
	}
	if !u.EmailVerified {
		return nil, ErrEmailNotVerified
	}
	if err := bcrypt.CompareHashAndPassword([]byte(u.PasswordHash), []byte(password)); err != nil {
		return nil, ErrInvalidPassword
	}
	candidate := cloneUser(u)
	now := time.Now().UTC()
	candidate.LastLoginAt = &now
	if s.db != nil {
		result, err := s.db.Exec(`UPDATE users SET last_login_at=$1 WHERE id=$2`, now, u.ID)
		if err != nil {
			s.unhealthy = true
			return nil, ErrStoreUnavailable
		}
		n, err := result.RowsAffected()
		if err != nil || n != 1 {
			s.unhealthy = true
			return nil, ErrStoreUnavailable
		}
	}
	s.users[email] = candidate
	return cloneUser(candidate), nil
}

// SetVerifyToken generates a 6-digit verification code for a user.
func (s *UserStore) SetVerifyToken(email string) (string, error) {
	n, err := rand.Int(rand.Reader, big.NewInt(1000000))
	if err != nil {
		return "", err
	}
	code := fmt.Sprintf("%06d", n.Int64())
	expiry := time.Now().UTC().Add(24 * time.Hour)
	err = s.mutateUser(email, func(u *User) error { u.VerifyToken = code; u.VerifyExpiry = &expiry; return nil })
	if err != nil {
		return "", err
	}
	return code, nil
}
func (s *UserStore) VerifyEmail(email, code string) error {
	return s.mutateUser(email, func(u *User) error {
		if u.VerifyToken == "" || u.VerifyToken != code || (u.VerifyExpiry != nil && time.Now().After(*u.VerifyExpiry)) {
			return ErrInvalidVerifyCode
		}
		u.EmailVerified = true
		u.VerifyToken = ""
		u.VerifyExpiry = nil
		return nil
	})
}

// GetByEmail returns a user by email.
func (s *UserStore) GetByEmail(email string) (*User, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	if s.unhealthy {
		return nil, ErrStoreUnavailable
	}
	if s.db != nil {
		u, err := readCurrentUser(s.db, email, "email")
		if err == ErrUserNotFound {
			return nil, err
		}
		if err != nil {
			s.unhealthy = true
			return nil, ErrStoreUnavailable
		}
		s.users[u.Email] = cloneUser(u)
		return cloneUser(u), nil
	}

	if s.unhealthy {
		return nil, ErrStoreUnavailable
	}
	user, ok := s.users[email]
	if !ok {
		return nil, ErrUserNotFound
	}
	return cloneUser(user), nil
}

// GetByID returns a user by ID.
func (s *UserStore) GetByID(id string) (*User, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	if s.unhealthy {
		return nil, ErrStoreUnavailable
	}
	if s.db != nil {
		u, err := readCurrentUser(s.db, id, "id")
		if err == ErrUserNotFound {
			return nil, err
		}
		if err != nil {
			s.unhealthy = true
			return nil, ErrStoreUnavailable
		}
		s.users[u.Email] = cloneUser(u)
		return cloneUser(u), nil
	}

	if s.unhealthy {
		return nil, ErrStoreUnavailable
	}
	for _, u := range s.users {
		if u.ID == id {
			return cloneUser(u), nil
		}
	}
	return nil, ErrUserNotFound
}

// apiKeyOwnerSnapshot captures authorization fields atomically. Public user
// projections also return independent snapshots.
func (s *UserStore) apiKeyOwnerSnapshot(id string) (User, error) {
	s.mu.RLock()
	defer s.mu.RUnlock()
	if s.unhealthy {
		return User{}, ErrStoreUnavailable
	}
	for _, user := range s.users {
		if user.ID == id {
			return User{ID: user.ID, Role: user.Role, TenantID: user.TenantID, Active: user.Active}, nil
		}
	}
	return User{}, ErrUserNotFound
}

// ListUsers returns all users.
func (s *UserStore) ListUsers() []*User {
	s.mu.RLock()
	defer s.mu.RUnlock()
	result := make([]*User, 0, len(s.users))
	for _, u := range s.users {
		result = append(result, cloneUser(u))
	}
	return result
}

// UpdateUser updates a user's display name, role, and active status.
func (s *UserStore) UpdateUser(id, displayName, role string, active bool) error {
	return s.mutateUser(id, func(u *User) error {
		if displayName != "" {
			u.DisplayName = displayName
		}
		if role != "" {
			u.Role = role
		}
		u.Active = active
		return nil
	})
}

// ChangePassword updates a user's password.
func (s *UserStore) ChangePassword(id, newPassword string) error {
	hash, err := bcrypt.GenerateFromPassword([]byte(newPassword), bcrypt.DefaultCost)
	if err != nil {
		return err
	}
	return s.mutateUser(id, func(u *User) error { u.PasswordHash = string(hash); return nil })
}

// DeleteUser permanently removes a user.
func (s *UserStore) DeleteUser(id string) error {
	s.mu.Lock()
	defer s.mu.Unlock()
	if s.unhealthy {
		return ErrStoreUnavailable
	}
	for email, u := range s.users {
		if u.ID == id {
			if s.db != nil {
				tx, err := s.db.Begin()
				if err != nil {
					s.unhealthy = true
					return ErrStoreUnavailable
				}
				defer tx.Rollback()
				if _, err = tx.Exec(`DELETE FROM api_keys WHERE user_id=$1`, id); err != nil {
					s.unhealthy = true
					return ErrStoreUnavailable
				}
				if _, err = tx.Exec(`DELETE FROM users WHERE id=$1`, id); err != nil {
					s.unhealthy = true
					return ErrStoreUnavailable
				}
				if err = tx.Commit(); err != nil {
					s.unhealthy = true
					return ErrStoreUnavailable
				}
			}
			delete(s.users, email)
			return nil
		}
	}
	return ErrUserNotFound
}

type APIKey struct {
	ID        string     `json:"id"`
	UserID    string     `json:"user_id"`
	Name      string     `json:"name"`
	Role      string     `json:"role"`
	KeyPrefix string     `json:"key_prefix"` // first 8 chars for display
	CreatedAt time.Time  `json:"created_at"`
	LastUsed  *time.Time `json:"last_used,omitempty"`
}

// CreateAPIKey generates a new API key for a user. Returns the full key (only shown once).
func (s *UserStore) CreateAPIKey(userID, name, role string) (string, *APIKey, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	if s.unhealthy {
		return "", nil, ErrStoreUnavailable
	}

	rawKey := make([]byte, 32)
	if _, err := rand.Read(rawKey); err != nil {
		return "", nil, err
	}
	fullKey := "stx_" + hex.EncodeToString(rawKey)
	keyHash := hashKey(fullKey)

	ak := &APIKey{
		ID:        generateID("key"),
		UserID:    userID,
		Name:      name,
		Role:      role,
		KeyPrefix: fullKey[:12],
		CreatedAt: time.Now().UTC(),
	}

	if s.db != nil {
		_, err := s.db.Exec(`INSERT INTO api_keys (id, user_id, key_hash, name, role, key_prefix, created_at) VALUES ($1,$2,$3,$4,$5,$6,$7)`,
			ak.ID, ak.UserID, keyHash, ak.Name, ak.Role, ak.KeyPrefix, ak.CreatedAt)
		if err != nil {
			s.unhealthy = true
			return "", nil, ErrStoreUnavailable
		}
	}

	return fullKey, ak, nil
}

// ValidateAPIKey checks an API key and returns the associated role.
func (s *UserStore) ValidateAPIKey(key string) (string, string, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	if s.unhealthy {
		return "", "", ErrStoreUnavailable
	}

	if s.db == nil {
		return "", "", fmt.Errorf("no database for API keys")
	}
	keyHash := hashKey(key)
	var userID, role string
	err := s.db.QueryRow(`SELECT user_id, role FROM api_keys WHERE key_hash = $1`, keyHash).Scan(&userID, &role)
	if err != nil {
		return "", "", ErrInvalidToken
	}

	// Synchronous, at most once per key per lastUsedResolution. This was a fire-and-forget
	// goroutine: nothing waited for it, so it could still be writing after the store's database was
	// closed, at shutdown in production and in the CI go leg on 2026-10-27, where it left a sqlite
	// journal in a test's TempDir after cleanup had started. A failed write does not fail the
	// request, and it is not recorded, so the next request retries it.
	now := time.Now().UTC()
	if written, ok := s.lastUsedWritten[keyHash]; !ok || now.Sub(written) >= lastUsedResolution {
		if _, err := s.db.Exec(`UPDATE api_keys SET last_used = $1 WHERE key_hash = $2`, now, keyHash); err == nil {
			s.lastUsedWritten[keyHash] = now
		}
	}
	return userID, role, nil
}

// ListAPIKeys returns all API keys for a user.
func (s *UserStore) ListAPIKeys(userID string) ([]APIKey, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	if s.unhealthy {
		return nil, ErrStoreUnavailable
	}

	if s.db == nil {
		return nil, nil
	}
	rows, err := s.db.Query(`SELECT id, user_id, name, role, created_at, last_used FROM api_keys WHERE user_id = $1`, userID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var keys []APIKey
	for rows.Next() {
		var ak APIKey
		var lastUsed sql.NullTime
		if err := rows.Scan(&ak.ID, &ak.UserID, &ak.Name, &ak.Role, &ak.CreatedAt, &lastUsed); err != nil {
			continue
		}
		if lastUsed.Valid {
			ak.LastUsed = &lastUsed.Time
		}
		keys = append(keys, ak)
	}
	return keys, nil
}

// ListAllAPIKeys returns all API keys across all users (for superadmin).
func (s *UserStore) ListAllAPIKeys() ([]APIKey, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	if s.unhealthy {
		return nil, ErrStoreUnavailable
	}

	if s.db == nil {
		return nil, nil
	}
	rows, err := s.db.Query(`SELECT id, user_id, name, role, created_at, last_used FROM api_keys`)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var keys []APIKey
	for rows.Next() {
		var ak APIKey
		var lastUsed sql.NullTime
		if err := rows.Scan(&ak.ID, &ak.UserID, &ak.Name, &ak.Role, &ak.CreatedAt, &lastUsed); err != nil {
			continue
		}
		if lastUsed.Valid {
			ak.LastUsed = &lastUsed.Time
		}
		keys = append(keys, ak)
	}
	return keys, nil
}

// DeleteAPIKey revokes an API key.
func (s *UserStore) DeleteAPIKey(keyID, userID string) error {
	s.mu.Lock()
	defer s.mu.Unlock()
	if s.unhealthy {
		return ErrStoreUnavailable
	}

	if s.db == nil {
		return nil
	}
	_, err := s.db.Exec(`DELETE FROM api_keys WHERE id = $1 AND user_id = $2`, keyID, userID)
	if err != nil {
		s.unhealthy = true
		return ErrStoreUnavailable
	}
	return nil
}

// --- Helpers ---

func generateID(prefix string) string {
	b := make([]byte, 8)
	rand.Read(b)
	return fmt.Sprintf("%s-%s", prefix, hex.EncodeToString(b))
}

func hashKey(key string) string {
	h := sha256.Sum256([]byte(key))
	return hex.EncodeToString(h[:])
}
