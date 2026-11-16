package auth

import (
	"database/sql"
	"errors"
	"fmt"
	"log/slog"
	"math"
	"reflect"
	"sync"
	"time"
)

// UsageInfo represents current usage state for a caller.
type UsageInfo struct {
	Plan        string    `json:"plan"`
	ScansUsed   int       `json:"scans_used"`
	ScansLimit  int       `json:"scans_limit"`
	Remaining   int       `json:"remaining"`
	PeriodStart time.Time `json:"period_start"`
	PeriodEnd   time.Time `json:"period_end"`
	Unlimited   bool      `json:"unlimited"`
}

// UsageTracker tracks scan usage per user/IP with monthly quotas.
type UsageTracker struct {
	mu      sync.Mutex
	db      *sql.DB
	initErr error
}

// NewUsageTracker creates a PostgreSQL/SQLite tracker. Initialization errors fail closed.
func NewUsageTracker(db *sql.DB) *UsageTracker {
	t := &UsageTracker{db: db}
	if db == nil {
		t.initErr = ErrUsageUnavailable
	} else {
		driver := reflect.TypeOf(db.Driver())
		if driver.Kind() == reflect.Pointer {
			driver = driver.Elem()
		}
		switch driver.PkgPath() {
		case "modernc.org/sqlite", "github.com/jackc/pgx/v5/stdlib":
			t.initErr = t.migrate()
		default:
			t.initErr = errors.New("unsupported quota SQL driver")
		}
	}

	return t
}

// ErrUsageUnavailable identifies unavailable or inconsistent quota storage.
var ErrUsageUnavailable = errors.New("usage quota temporarily unavailable")

// Ready reports initialization failure without allowing requests around the quota.
func (t *UsageTracker) Ready() error {
	if t == nil || t.db == nil {
		return ErrUsageUnavailable
	}
	if t.initErr != nil {
		return fmt.Errorf("%w: %v", ErrUsageUnavailable, t.initErr)
	}
	return nil
}

func (t *UsageTracker) migrate() error {
	tx, err := t.db.Begin()
	if err != nil {
		return err
	}
	defer tx.Rollback()
	statements := []string{
		`CREATE TABLE IF NOT EXISTS usage_quotas (
 id TEXT PRIMARY KEY, user_id TEXT, ip_addr TEXT,
 plan TEXT NOT NULL DEFAULT 'free', scans_used INTEGER NOT NULL DEFAULT 0,
 scans_limit INTEGER NOT NULL DEFAULT 1000, period_start TIMESTAMPTZ NOT NULL,
 period_end TIMESTAMPTZ NOT NULL)`,
		`CREATE UNIQUE INDEX IF NOT EXISTS idx_usage_user_period_unique ON usage_quotas(user_id, period_start) WHERE user_id IS NOT NULL`,
		`CREATE UNIQUE INDEX IF NOT EXISTS idx_usage_ip_period_unique ON usage_quotas(ip_addr, period_start) WHERE ip_addr IS NOT NULL`,
	}
	// A legacy duplicate makes index creation fail. Never choose, merge, or delete a row.
	for _, statement := range statements {
		if _, err = tx.Exec(statement); err != nil {
			return err
		}
	}
	return tx.Commit()
}

// currentPeriod returns the start and end of the current monthly billing period.
func currentPeriod() (time.Time, time.Time) {
	now := time.Now().UTC()
	start := time.Date(now.Year(), now.Month(), 1, 0, 0, 0, 0, time.UTC)
	end := start.AddDate(0, 1, 0)
	return start, end
}

// RecordScan atomically increments the scan counter and checks quota.
// Uses the free tier default limit (1000). For plan-aware quotas, use RecordScanWithLimit.
func (t *UsageTracker) RecordScan(userID, ip string) (int, error) {
	return t.RecordScanWithLimit(userID, ip, 1000)
}

// RecordScanWithLimit atomically increments the scan counter and checks against planLimit.
// planLimit: -1=unlimited, 0=no scans allowed, >0=monthly cap.
// Returns remaining scans. Returns error if quota exceeded.
func (t *UsageTracker) RecordScanWithLimit(userID, ip string, planLimit int) (int, error) {
	return t.recordScanWithLimit(userID, "", ip, planLimit)
}

// RecordScanForOwner meters every credential of an owner against the same ID.
// Legacy email buckets require an explicit migration; never reset their spend.
func (t *UsageTracker) RecordScanForOwner(ownerID, email, ip string, planLimit int) (int, error) {
	if ownerID == "" || email == "" {
		return 0, ErrUsageUnavailable
	}
	return t.recordScanWithLimit(ownerID, email, ip, planLimit)
}

func (t *UsageTracker) recordScanWithLimit(userID, legacyAlias, ip string, planLimit int) (int, error) {
	if err := t.Ready(); err != nil {
		return 0, err
	}
	if planLimit < -1 {
		return 0, ErrUsageUnavailable
	}
	if planLimit == 0 {
		return 0, ErrQuotaExceeded
	}
	column, key := usageKey(userID, ip)
	if key == "" {
		return 0, ErrUsageUnavailable
	}
	t.mu.Lock()
	defer t.mu.Unlock()
	tx, err := t.db.Begin()
	if err != nil {
		return 0, fmt.Errorf("%w: %v", ErrUsageUnavailable, err)
	}
	defer tx.Rollback()
	unavailable := func(err error) (int, error) { return 0, fmt.Errorf("%w: %v", ErrUsageUnavailable, err) }
	start, end := currentPeriod()
	if legacyAlias != "" && legacyAlias != userID {
		var aliases int
		if err = tx.QueryRow(`SELECT COUNT(*) FROM usage_quotas WHERE user_id=$1 AND period_start=$2`, legacyAlias, start).Scan(&aliases); err != nil {
			return unavailable(err)
		}
		if aliases != 0 {
			return unavailable(errors.New("legacy quota identity requires migration"))
		}
	}
	limit := planLimit
	plan := "free"
	if limit == -1 {
		limit = 0
		plan = "unlimited"
	} else if limit > 1000 {
		plan = "paid"
	}
	insert := fmt.Sprintf(`INSERT INTO usage_quotas (id, %s, plan, scans_used, scans_limit, period_start, period_end)
 VALUES ($1,$2,$3,0,$4,$5,$6) ON CONFLICT DO NOTHING`, column)
	if _, err = tx.Exec(insert, generateID("usg"), key, plan, limit, start, end); err != nil {
		return unavailable(err)
	}
	// Duplicate/corrupt legacy state is an unavailable source, never an arbitrary row.
	var count int
	if err = tx.QueryRow(fmt.Sprintf(`SELECT COUNT(*) FROM usage_quotas WHERE %s=$1 AND period_start=$2`, column), key, start).Scan(&count); err != nil {
		return unavailable(err)
	}
	if count != 1 {
		return unavailable(errors.New("ambiguous quota identity"))
	}
	var used, oldLimit int
	if err = tx.QueryRow(fmt.Sprintf(`SELECT scans_used, scans_limit FROM usage_quotas WHERE %s=$1 AND period_start=$2`, column), key, start).Scan(&used, &oldLimit); err != nil {
		return unavailable(err)
	}
	if used < 0 || oldLimit < 0 || used >= math.MaxInt32 {
		return unavailable(errors.New("invalid quota counter"))
	}
	update := fmt.Sprintf(`UPDATE usage_quotas SET scans_used=scans_used+1, scans_limit=$1, plan=$2
 WHERE %s=$3 AND period_start=$4 AND scans_used>=0 AND scans_used<2147483647
 AND ($1=0 OR scans_used<$1) RETURNING scans_used`, column)
	if err = tx.QueryRow(update, limit, plan, key, start).Scan(&used); err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			return 0, ErrQuotaExceeded
		}
		return unavailable(err)
	}
	if err = tx.Commit(); err != nil {
		return unavailable(err)
	}
	if planLimit == -1 {
		return -1, nil
	}
	return planLimit - used, nil
}

func usageKey(userID, ip string) (string, string) {
	if userID != "" {
		return "user_id", userID
	}
	return "ip_addr", ip
}

// GetUsageChecked never turns storage failures into fabricated unused quota.
func (t *UsageTracker) GetUsageChecked(userID, ip string) (*UsageInfo, error) {
	if err := t.Ready(); err != nil {
		return nil, err
	}
	column, key := usageKey(userID, ip)
	if key == "" {
		return nil, ErrUsageUnavailable
	}
	start, end := currentPeriod()
	rows, err := t.db.Query(fmt.Sprintf(`SELECT plan, scans_used, scans_limit FROM usage_quotas WHERE %s=$1 AND period_start=$2`, column), key, start)
	if err != nil {
		return nil, fmt.Errorf("%w: %v", ErrUsageUnavailable, err)
	}
	defer rows.Close()
	info := UsageInfo{Plan: "free", ScansLimit: 1000, Remaining: 1000, PeriodStart: start, PeriodEnd: end}
	count := 0
	for rows.Next() {
		count++
		if count > 1 {
			return nil, ErrUsageUnavailable
		}
		if err = rows.Scan(&info.Plan, &info.ScansUsed, &info.ScansLimit); err != nil {
			return nil, fmt.Errorf("%w: %v", ErrUsageUnavailable, err)
		}
	}
	if err = rows.Err(); err != nil {
		return nil, fmt.Errorf("%w: %v", ErrUsageUnavailable, err)
	}
	if info.ScansUsed < 0 || info.ScansLimit < 0 {
		return nil, ErrUsageUnavailable
	}
	if count > 0 {
		if info.ScansLimit == 0 {
			info.Unlimited = true
			info.Remaining = -1
		} else {
			info.Remaining = max(0, info.ScansLimit-info.ScansUsed)
		}
	}
	return &info, nil
}

// GetUsageForOwnerChecked rejects legacy aliases rather than presenting a fresh
// canonical bucket as unused. This method does not migrate or change any row.
func (t *UsageTracker) GetUsageForOwnerChecked(ownerID, email, ip string) (*UsageInfo, error) {
	if err := t.Ready(); err != nil {
		return nil, err
	}
	if ownerID == "" || email == "" {
		return nil, ErrUsageUnavailable
	}
	if email != ownerID {
		start, _ := currentPeriod()
		var aliases int
		if err := t.db.QueryRow(`SELECT COUNT(*) FROM usage_quotas WHERE user_id=$1 AND period_start=$2`, email, start).Scan(&aliases); err != nil {
			return nil, fmt.Errorf("%w: %v", ErrUsageUnavailable, err)
		}
		if aliases != 0 {
			return nil, ErrUsageUnavailable
		}
	}
	return t.GetUsageChecked(ownerID, ip)
}

// GetUsage is retained for source compatibility; nil means unavailable.
func (t *UsageTracker) GetUsage(userID, ip string) *UsageInfo {
	info, _ := t.GetUsageChecked(userID, ip)
	return info
}

// ResetExpired cleans up old quota records from previous periods.
func (t *UsageTracker) ResetExpired() {
	if t.db == nil {
		return
	}
	result, err := t.db.Exec(`DELETE FROM usage_quotas WHERE period_end < $1`, time.Now().UTC())
	if err != nil {
		slog.Error("usage: reset expired", "error", err)
		return
	}
	if n, _ := result.RowsAffected(); n > 0 {
		slog.Info("usage: cleaned expired quotas", "count", n)
	}
}
