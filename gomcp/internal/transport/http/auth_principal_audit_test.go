package httpserver

import (
	"database/sql"
	"github.com/syntrex/gomcp/internal/infrastructure/auth"
	"net/http"
	"net/http/httptest"
	"path/filepath"
	"strings"
	"testing"
	"time"
)

func TestAuditServerBoundJWTRejectsDurableDowngrade(t *testing.T) {
	t.Setenv("SOC_DEMO_MODE", "0")
	db, err := sql.Open("sqlite", filepath.Join(t.TempDir(), "bound-auth.db"))
	if err != nil {
		t.Fatal(err)
	}
	defer db.Close()
	db.SetMaxOpenConns(1)
	server := New(nil, 0)
	secret := []byte(strings.Repeat("s", 32))
	server.SetJWTAuth(secret, db)
	if err = server.AuthStoresHealthy(); err != nil {
		t.Fatal(err)
	}
	owner, err := server.userStore.GetByEmail("admin@syntrex.pro")
	if err != nil {
		t.Fatal(err)
	}
	token, err := auth.Sign(auth.Claims{Sub: owner.Email, Role: "superadmin", TokenType: "access", Exp: time.Now().Add(time.Hour).Unix()}, secret)
	if err != nil {
		t.Fatal(err)
	}
	reached := false
	handler := server.jwtAuth.Middleware(server.rbac.Require(RoleSuperadmin, func(w http.ResponseWriter, r *http.Request) { reached = true; w.WriteHeader(200) }))
	request := func() int {
		reached = false
		r := httptest.NewRequest("GET", "/api/operator-fixture", nil)
		r.Header.Set("Authorization", "Bearer "+token)
		w := httptest.NewRecorder()
		handler.ServeHTTP(w, r)
		return w.Code
	}
	if request() != 200 || !reached {
		t.Fatal("current operator rejected")
	}
	if err = server.userStore.UpdateUser(owner.ID, "", "viewer", true); err != nil {
		t.Fatal(err)
	}
	if request() != 401 || reached {
		t.Fatal("server retained old JWT operator authority after durable downgrade")
	}
}
