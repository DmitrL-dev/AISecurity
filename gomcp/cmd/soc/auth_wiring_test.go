package main

import (
	"github.com/syntrex/gomcp/internal/infrastructure/sqlite"
	sochttp "github.com/syntrex/gomcp/internal/transport/http"
	"testing"
	"time"
)

func TestAuditSQLiteStartupWiresPersistentAuthTenantAndQuotaStores(t *testing.T) {
	t.Setenv("SOC_DEMO_MODE", "0")
	t.Setenv("SYNTREX_ADMIN_PASSWORD", "")
	db, err := sqlite.OpenMemory()
	if err != nil {
		t.Fatal(err)
	}
	defer db.Close()
	pool := db.SqlDB()
	server := sochttp.New(nil, 0) // No listener, SOC daemon or native engine is started.
	if err := configurePersistentAuthAndUsage(server, []byte("synthetic-local-auth-fixture-only"), pool); err != nil {
		t.Fatal(err)
	}
	for _, table := range []string{"users", "api_keys", "tenants", "usage_quotas"} {
		var count int
		if err := pool.QueryRow(`SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name=$1`, table).Scan(&count); err != nil || count != 1 {
			t.Fatalf("SQLite startup did not wire persistent %s store", table)
		}
	}
	var users int
	if err := pool.QueryRow(`SELECT COUNT(*) FROM users`).Scan(&users); err != nil || users < 1 {
		t.Fatal("auth store was initialized in memory instead of the provided SQLite pool")
	}
	if _, err := pool.Exec(`INSERT INTO tenants(id,name,slug,owner_user_id) VALUES ('fixture-tenant','synthetic tenant','fixture-tenant','fixture-owner')`); err != nil {
		t.Fatal(err)
	}
	now := time.Now().UTC()
	if _, err := pool.Exec(`INSERT INTO usage_quotas(id,ip_addr,scans_used,scans_limit,period_start,period_end) VALUES ('fixture-quota','synthetic-local-peer',1,2,$1,$2)`, now, now.Add(time.Hour)); err != nil {
		t.Fatal(err)
	}
	var used int
	if err := pool.QueryRow(`SELECT scans_used FROM usage_quotas WHERE id='fixture-quota'`).Scan(&used); err != nil || used != 1 {
		t.Fatal("quota fixture was not persisted in the shared SQLite pool")
	}
	if err := configurePersistentAuthAndUsage(server, nil, nil); err == nil {
		t.Fatal("missing persistence pool silently enabled memory-only startup")
	}
}
