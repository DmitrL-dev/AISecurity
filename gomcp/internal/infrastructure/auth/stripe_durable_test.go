package auth

import (
	"crypto/hmac"
	"crypto/sha256"
	"encoding/hex"
	"fmt"
	"net/http/httptest"
	"strings"
	"testing"
	"time"
)

func TestAuditStripeAcknowledgesOnlyConfirmedCombinedMutation(t *testing.T) {
	const secret = "synthetic-local-webhook-signing-fixture"
	t.Setenv("STRIPE_WEBHOOK_SECRET", secret)
	for _, kind := range []string{"customer.subscription.updated", "customer.subscription.deleted"} {
		t.Run(kind, func(t *testing.T) {
			db, _, store, u := durableFixture(t)
			tenant, err := store.CreateTenant("Fixture", "fixture", u.ID, "starter")
			if err != nil {
				t.Fatal(err)
			}
			if err = store.SetStripeIDs(tenant.ID, "old-synthetic-customer", "old-synthetic-sub"); err != nil {
				t.Fatal(err)
			}
			id := "fixture-" + kind
			stripeWebhookCache.Delete(id)
			defer stripeWebhookCache.Delete(id)
			body := fmt.Sprintf(`{"id":%q,"type":%q,"data":{"object":{"customer":"new-synthetic-customer","id":"new-synthetic-sub","metadata":{"tenant_id":%q,"plan_id":"enterprise"}}}}`, id, kind, tenant.ID)
			timestamp := fmt.Sprint(time.Now().Unix())
			mac := hmac.New(sha256.New, []byte(secret))
			mac.Write([]byte(timestamp + "." + body))
			signature := "t=" + timestamp + ",v1=" + hex.EncodeToString(mac.Sum(nil))
			request := func(current *TenantStore) int {
				r := httptest.NewRequest("POST", "/api/billing/webhook", strings.NewReader(body))
				r.Header.Set("Stripe-Signature", signature)
				w := httptest.NewRecorder()
				HandleStripeWebhook(current)(w, r)
				return w.Code
			}
			if _, err = db.Exec(`CREATE TRIGGER reject_webhook BEFORE UPDATE ON tenants BEGIN SELECT RAISE(ABORT,'synthetic rejection');END`); err != nil {
				t.Fatal(err)
			}
			if code := request(store); code != 503 {
				t.Fatalf("failed write acknowledged: %d", code)
			}
			if _, cached := stripeWebhookCache.Load(id); cached {
				t.Fatal("failed write cached as applied")
			}
			var plan, customer, subscription string
			if err = db.QueryRow(`SELECT plan_id,stripe_customer_id,stripe_sub_id FROM tenants WHERE id=$1`, tenant.ID).Scan(&plan, &customer, &subscription); err != nil || plan != "starter" || customer != "old-synthetic-customer" || subscription != "old-synthetic-sub" {
				t.Fatal("partial webhook mutation committed")
			}
			if _, err = db.Exec(`DROP TRIGGER reject_webhook`); err != nil {
				t.Fatal(err)
			} // Owned temporary fixture only.
			recovered := NewTenantStore(db)
			if code := request(recovered); code != 200 {
				t.Fatalf("retry failed: %d", code)
			}
			if _, cached := stripeWebhookCache.Load(id); !cached {
				t.Fatal("confirmed write not cached")
			}
			restarted := NewTenantStore(db)
			got, err := restarted.GetTenant(tenant.ID)
			if err != nil {
				t.Fatal(err)
			}
			expectedPlan, expectedSub := "enterprise", "new-synthetic-sub"
			if kind == "customer.subscription.deleted" {
				expectedPlan = "free"
				expectedSub = ""
			}
			if got.PlanID != expectedPlan || got.PaymentCustomerID != "new-synthetic-customer" || got.PaymentSubID != expectedSub {
				t.Fatal("combined webhook mutation did not survive restart")
			}
			if request(restarted) != 200 {
				t.Fatal("confirmed duplicate rejected")
			}
		})
	}
}
