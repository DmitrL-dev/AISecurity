package httpserver

import (
	"net/http"
	"testing"
)

// Regression for the mega-review 17.06 HIGH (cross-plane slug squatting): the
// signed provision/SSO channels must REFUSE to act on a tenant that was NOT
// spectorn-provisioned (i.e. has a non-empty owner — a public self-service
// registration). Even if an attacker manages to own a tenant whose slug equals a
// victim's spectorn tenant_id, they must not receive the victim's paid plan or an
// SSO-minted admin JWT. (Helpers newProvisionTestServer/postProvision/
// newSSOTestServer/postSSO/provTestKey live in provision_admin_test.go +
// sso_admin_test.go — same package.)

func TestProvisionTenant_RefusesSelfServiceOwnedSlug(t *testing.T) {
	s := newProvisionTestServer(t)
	priv := provTestKey(t)

	// Attacker self-service-registered this slug → tenant has a REAL owner.
	if _, err := s.tenantStore.CreateTenant("Attacker", "u_victimhash", "attacker-uid", "free"); err != nil {
		t.Fatalf("seed attacker tenant: %v", err)
	}

	// A victim's paid upgrade tries to provision the same slug → must be refused.
	w := postProvision(t, s, priv, "u_victimhash", "professional", "nonce-sq")
	if w.Code != http.StatusConflict {
		t.Fatalf("provision of a self-service-owned slug must be 409, got %d (body=%s)", w.Code, w.Body.String())
	}
	tn, _ := s.tenantStore.GetTenantBySlug("u_victimhash")
	if tn == nil || tn.PlanID != "free" {
		t.Fatalf("attacker-owned tenant must NOT be upgraded; plan=%v", tn)
	}
}

func TestSSOExchange_RefusesSelfServiceOwnedSlug(t *testing.T) {
	s := newSSOTestServer(t)
	priv := provTestKey(t)

	// Attacker self-service tenant squatting a victim's slug (non-empty owner).
	if _, err := s.tenantStore.CreateTenant("Attacker", "u_victimhash", "attacker-uid", "professional"); err != nil {
		t.Fatalf("seed attacker tenant: %v", err)
	}

	// Victim SSO for that slug must be refused (404 = no token minted into the
	// attacker's tenant). Same status as "not provisioned" (no existence oracle).
	w := postSSO(t, s, priv, "u_victimhash", "u_victimhash", "nonce-sq")
	if w.Code != http.StatusNotFound {
		t.Fatalf("SSO for a self-service-owned slug must be refused (404), got %d (body=%s)", w.Code, w.Body.String())
	}
}
