package auth

import (
	"database/sql"
	"errors"
	"fmt"
	"log/slog"
	"sync"
	"time"
)

// Standard tenant errors.
var (
	ErrTenantNotFound = errors.New("auth: tenant not found")
	ErrTenantExists   = errors.New("auth: tenant already exists")
	ErrQuotaExceeded  = errors.New("auth: plan quota exceeded")
)

// Plan represents a subscription tier with resource limits.
type Plan struct {
	ID                string `json:"id"`
	Name              string `json:"name"`
	Description       string `json:"description,omitempty"`
	MaxUsers          int    `json:"max_users"`
	MaxEventsMonth    int    `json:"max_events_month"` // SOC event ingestion quota (-1=unlimited)
	MaxIncidents      int    `json:"max_incidents"`
	MaxSensors        int    `json:"max_sensors"`
	MaxScansMonth     int    `json:"max_scans_month"` // /api/v1/scan quota (-1=unlimited, 0=none)
	RetentionDays     int    `json:"retention_days"`
	SOCEnabled        bool   `json:"soc_enabled"` // SOC Dashboard access
	SLAEnabled        bool   `json:"sla_enabled"`
	SOAREnabled       bool   `json:"soar_enabled"`
	ComplianceEnabled bool   `json:"compliance_enabled"`
	OnPremise         bool   `json:"on_premise"`        // Enterprise: on-premise deployment
	PriceMonthCents   int    `json:"price_month_cents"` // 0 = free, -1 = custom pricing
}

// DefaultPlans defines the standard pricing tiers (prices in RUB kopecks).
var DefaultPlans = map[string]Plan{
	"free": {
		ID: "free", Name: "Free",
		Description: "Scanner API — 1 000 сканов/мес, все движки детекции, без SOC Dashboard",
		MaxUsers:    1, MaxEventsMonth: 1000, MaxIncidents: 100, MaxSensors: 1,
		MaxScansMonth: 1000,
		RetentionDays: 3,
		SOCEnabled:    false, SLAEnabled: false, SOAREnabled: false, ComplianceEnabled: false,
		PriceMonthCents: 0,
	},
	"demo": {
		ID: "demo", Name: "Demo Sandbox",
		Description: "Общая демо-песочница. Жёсткий лимит.",
		MaxUsers:    10, MaxEventsMonth: 1000, MaxIncidents: 100, MaxSensors: 5,
		MaxScansMonth: 1000,
		RetentionDays: 1,
		SOCEnabled:    true, SLAEnabled: false, SOAREnabled: false, ComplianceEnabled: false,
		PriceMonthCents: 0,
	},
	"starter": {
		ID: "starter", Name: "Starter",
		Description: "AI-мониторинг: до 5 сенсоров, базовая корреляция и алерты",
		MaxUsers:    10, MaxEventsMonth: 100000, MaxIncidents: 200, MaxSensors: 5,
		MaxScansMonth: 100000,
		RetentionDays: 30,
		SOCEnabled:    true, SLAEnabled: true, SOAREnabled: false, ComplianceEnabled: false,
		PriceMonthCents: 8990000, // 89 900 ₽/мес
	},
	"professional": {
		ID: "professional", Name: "Professional",
		Description: "Полный AI SOC: SOAR, compliance, расширенная аналитика",
		MaxUsers:    50, MaxEventsMonth: 500000, MaxIncidents: 1000, MaxSensors: 25,
		MaxScansMonth: 500000,
		RetentionDays: 90,
		SOCEnabled:    true, SLAEnabled: true, SOAREnabled: true, ComplianceEnabled: true,
		PriceMonthCents: 14990000, // 149 900 ₽/мес
	},
	"enterprise": {
		ID: "enterprise", Name: "Enterprise",
		Description: "On-premise / выделенный инстанс. Сертификация — на стороне заказчика",
		MaxUsers:    -1, MaxEventsMonth: -1, MaxIncidents: -1, MaxSensors: -1,
		MaxScansMonth: -1, // unlimited
		RetentionDays: 365,
		SOCEnabled:    true, SLAEnabled: true, SOAREnabled: true, ComplianceEnabled: true,
		OnPremise:       true,
		PriceMonthCents: -1, // по запросу
	},
}

// Tenant represents an isolated organization in the multi-tenant system.
type Tenant struct {
	ID                string    `json:"id"`
	Name              string    `json:"name"`
	Slug              string    `json:"slug"`
	PlanID            string    `json:"plan_id"`
	PaymentCustomerID string    `json:"payment_customer_id,omitempty"`
	PaymentSubID      string    `json:"payment_sub_id,omitempty"`
	OwnerUserID       string    `json:"owner_user_id"`
	Active            bool      `json:"active"`
	CreatedAt         time.Time `json:"created_at"`
	EventsThisMonth   int       `json:"events_this_month"`
	MonthResetAt      time.Time `json:"month_reset_at"`
	// Custom limits override plan limits when set (superadmin control).
	CustomMaxEvents  *int `json:"custom_max_events,omitempty"`
	CustomMaxScans   *int `json:"custom_max_scans,omitempty"`
	CustomMaxUsers   *int `json:"custom_max_users,omitempty"`
	CustomMaxSensors *int `json:"custom_max_sensors,omitempty"`
}

// GetPlan returns the tenant's plan configuration, with custom limits applied if set.
func (t *Tenant) GetPlan() Plan {
	p := DefaultPlans["free"]
	if plan, ok := DefaultPlans[t.PlanID]; ok {
		p = plan
	}
	// Apply custom limits overrides (superadmin control)
	if t.CustomMaxEvents != nil {
		p.MaxEventsMonth = *t.CustomMaxEvents
	}
	if t.CustomMaxScans != nil {
		p.MaxScansMonth = *t.CustomMaxScans
	}
	if t.CustomMaxUsers != nil {
		p.MaxUsers = *t.CustomMaxUsers
	}
	if t.CustomMaxSensors != nil {
		p.MaxSensors = *t.CustomMaxSensors
	}
	return p
}

// CanAccessSOC returns true if the tenant's plan includes SOC Dashboard access.
func (t *Tenant) CanAccessSOC() bool {
	return t.Active && t.GetPlan().SOCEnabled
}

// ScanLimit returns the monthly scan quota for this tenant (-1=unlimited).
func (t *Tenant) ScanLimit() int {
	return t.GetPlan().MaxScansMonth
}

// CanIngestEvent checks if the tenant can still ingest events this month.
func (t *Tenant) CanIngestEvent() bool {
	if !t.Active {
		return false
	}
	plan := t.GetPlan()
	if plan.MaxEventsMonth < 0 {
		return true // unlimited
	}
	return t.EventsThisMonth < plan.MaxEventsMonth
}

// TenantStore manages tenant records backed by SQLite.
type TenantStore struct {
	mu        sync.RWMutex
	unhealthy bool
	db        *sql.DB
	tenants   map[string]*Tenant // id -> Tenant
}

// NewTenantStore creates a tenant store.
func NewTenantStore(db *sql.DB) *TenantStore {
	s := &TenantStore{
		db:      db,
		tenants: make(map[string]*Tenant),
	}
	if db != nil {
		if err := s.migrate(); err != nil {
			s.unhealthy = true
		} else {
			s.loadFromDB()
		}
	}
	return s
}

func (s *TenantStore) migrate() error {
	_, err := s.db.Exec(`
		CREATE TABLE IF NOT EXISTS tenants (
			id                TEXT PRIMARY KEY,
			name              TEXT NOT NULL,
			slug              TEXT UNIQUE NOT NULL,
			plan_id           TEXT NOT NULL DEFAULT 'free',
			stripe_customer_id TEXT DEFAULT '',
			stripe_sub_id     TEXT DEFAULT '',
			owner_user_id     TEXT NOT NULL,
			active            BOOLEAN NOT NULL DEFAULT true,
			created_at        TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
			events_this_month INTEGER NOT NULL DEFAULT 0,
			month_reset_at    TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
		);
	`)
	if err != nil {
		return err
	}

	// Additive upgrade for existing databases. Probe each fixed column so
	// SQLite does not need unsupported ADD COLUMN IF NOT EXISTS syntax.
	for _, column := range []string{"custom_max_events", "custom_max_scans", "custom_max_users", "custom_max_sensors"} {
		rows, probeErr := s.db.Query("SELECT " + column + " FROM tenants WHERE 1=0")
		if probeErr == nil {
			rows.Close()
			continue
		}
		if _, err := s.db.Exec("ALTER TABLE tenants ADD COLUMN " + column + " INTEGER"); err != nil {
			return err
		}
	}
	// Add tenant_id column to users if missing
	_, _ = s.db.Exec(`ALTER TABLE users ADD COLUMN IF NOT EXISTS tenant_id TEXT DEFAULT ''`)
	return nil
}

func (s *TenantStore) loadFromDB() {
	rows, err := s.db.Query(`SELECT id, name, slug, plan_id, stripe_customer_id, stripe_sub_id, 
		owner_user_id, active, created_at, events_this_month, month_reset_at, custom_max_events,custom_max_scans,custom_max_users,custom_max_sensors FROM tenants`)
	if err != nil {
		s.unhealthy = true
		return
	}
	defer rows.Close()

	s.mu.Lock()
	defer s.mu.Unlock()
	candidate := make(map[string]*Tenant)
	seenSlugs := make(map[string]bool)
	for rows.Next() {
		var t Tenant
		var createdAt, resetAt storeTime
		if err := rows.Scan(&t.ID, &t.Name, &t.Slug, &t.PlanID, &t.PaymentCustomerID,
			&t.PaymentSubID, &t.OwnerUserID, &t.Active, &createdAt, &t.EventsThisMonth, &resetAt, &t.CustomMaxEvents, &t.CustomMaxScans, &t.CustomMaxUsers, &t.CustomMaxSensors); err != nil {
			s.unhealthy = true
			return
		}
		if !createdAt.Valid || !resetAt.Valid {
			s.unhealthy = true
			return
		}
		t.CreatedAt = createdAt.Time
		t.MonthResetAt = resetAt.Time
		if t.ID == "" || t.Slug == "" || candidate[t.ID] != nil || seenSlugs[t.Slug] {
			s.unhealthy = true
			return
		}
		seenSlugs[t.Slug] = true
		candidate[t.ID] = cloneTenant(&t)
	}
	if rows.Err() != nil {
		s.unhealthy = true
		return
	}
	s.tenants = candidate
	slog.Info("tenants loaded from DB", "count", len(s.tenants))
}

// persistTenant synchronously writes a locked candidate before publication.
func (s *TenantStore) persistTenant(t Tenant) error {
	if s.db == nil {
		return nil
	}
	_, err := s.db.Exec(`
		INSERT INTO tenants (id, name, slug, plan_id, stripe_customer_id, stripe_sub_id,
			owner_user_id, active, created_at, events_this_month, month_reset_at,custom_max_events,custom_max_scans,custom_max_users,custom_max_sensors)
		VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11,$12,$13,$14,$15)`,
		t.ID, t.Name, t.Slug, t.PlanID, t.PaymentCustomerID, t.PaymentSubID,
		t.OwnerUserID, t.Active, t.CreatedAt,
		t.EventsThisMonth, t.MonthResetAt, t.CustomMaxEvents, t.CustomMaxScans, t.CustomMaxUsers, t.CustomMaxSensors,
	)
	return err
}

// CreateTenant creates a new tenant and assigns an owner.
func (s *TenantStore) CreateTenant(name, slug, ownerUserID, planID string) (*Tenant, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	if s.unhealthy {
		return nil, ErrStoreUnavailable
	}

	for _, t := range s.tenants {
		if t.Slug == slug {
			return nil, ErrTenantExists
		}
	}

	if _, ok := DefaultPlans[planID]; !ok {
		planID = "starter"
	}

	t := &Tenant{
		ID:              generateID("tnt"),
		Name:            name,
		Slug:            slug,
		PlanID:          planID,
		OwnerUserID:     ownerUserID,
		Active:          true,
		CreatedAt:       time.Now().UTC(),
		EventsThisMonth: 0,
		MonthResetAt:    monthStart(time.Now().UTC().AddDate(0, 1, 0)),
	}

	if err := s.persistTenant(*t); err != nil {
		s.unhealthy = true
		return nil, ErrStoreUnavailable
	}
	s.tenants[t.ID] = cloneTenant(t)
	return cloneTenant(t), nil
}

// GetTenant returns a tenant by ID.
func (s *TenantStore) GetTenant(id string) (*Tenant, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	if s.unhealthy {
		return nil, ErrStoreUnavailable
	}
	if s.db != nil {
		t, err := readCurrentTenant(s.db, id, "id")
		if err == ErrTenantNotFound {
			return nil, err
		}
		if err != nil {
			s.unhealthy = true
			return nil, ErrStoreUnavailable
		}
		s.tenants[t.ID] = cloneTenant(t)
		return cloneTenant(t), nil
	}

	if s.unhealthy {
		return nil, ErrStoreUnavailable
	}
	t, ok := s.tenants[id]
	if !ok {
		return nil, ErrTenantNotFound
	}
	// SEC/correctness (pre-launch audit 18.06): return a SNAPSHOT, not the live
	// pointer — concurrent UpdatePlan/SetStripeIDs/IncrementEvents mutate *t under
	// the lock, so handing out the live pointer is a data race. Mutations go through
	// the store's by-ID methods, so a read snapshot is the correct contract.
	return cloneTenant(t), nil
}

// GetTenantBySlug returns a tenant by slug.
func (s *TenantStore) GetTenantBySlug(slug string) (*Tenant, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	if s.unhealthy {
		return nil, ErrStoreUnavailable
	}
	if s.db != nil {
		t, err := readCurrentTenant(s.db, slug, "slug")
		if err == ErrTenantNotFound {
			return nil, err
		}
		if err != nil {
			s.unhealthy = true
			return nil, ErrStoreUnavailable
		}
		s.tenants[t.ID] = cloneTenant(t)
		return cloneTenant(t), nil
	}

	if s.unhealthy {
		return nil, ErrStoreUnavailable
	}
	for _, t := range s.tenants {
		if t.Slug == slug {
			return cloneTenant(t), nil
		}
	}
	return nil, ErrTenantNotFound
}

// ListTenants returns all tenants.
func (s *TenantStore) ListTenants() []*Tenant {
	s.mu.RLock()
	defer s.mu.RUnlock()
	result := make([]*Tenant, 0, len(s.tenants))
	for _, t := range s.tenants {
		result = append(result, cloneTenant(t))
	}
	return result
}

// UpdatePlan changes a tenant's plan.
func (s *TenantStore) UpdatePlan(id, plan string) error {
	return s.mutateTenant(id, func(t *Tenant) error {
		if _, ok := DefaultPlans[plan]; !ok {
			return fmt.Errorf("auth: unknown plan")
		}
		t.PlanID = plan
		return nil
	})
}

// SetStripeIDs saves Stripe customer + subscription IDs.
func (s *TenantStore) SetStripeIDs(id, customer, subscription string) error {
	return s.mutateTenant(id, func(t *Tenant) error { t.PaymentCustomerID = customer; t.PaymentSubID = subscription; return nil })
}

// IncrementEvents increments the monthly event counter. Returns error if quota exceeded.
func (s *TenantStore) IncrementEvents(id string, count int) error {
	return s.mutateTenant(id, func(t *Tenant) error {
		if count < 0 {
			return ErrQuotaExceeded
		}
		if time.Now().UTC().After(t.MonthResetAt) {
			t.EventsThisMonth = 0
			t.MonthResetAt = monthStart(time.Now().UTC().AddDate(0, 1, 0))
		}
		plan := t.GetPlan()
		if t.EventsThisMonth < 0 || count > int(^uint(0)>>1)-t.EventsThisMonth {
			return ErrQuotaExceeded
		}
		if plan.MaxEventsMonth >= 0 && (count > plan.MaxEventsMonth || t.EventsThisMonth > plan.MaxEventsMonth-count) {
			return ErrQuotaExceeded
		}
		t.EventsThisMonth += count
		return nil
	})
}

// DeactivateTenant marks a tenant as inactive (subscription cancelled).
func (s *TenantStore) DeactivateTenant(id string) error {
	return s.mutateTenant(id, func(t *Tenant) error { t.Active = false; return nil })
}

func monthStart(t time.Time) time.Time {
	return time.Date(t.Year(), t.Month(), 1, 0, 0, 0, 0, t.Location())
}
