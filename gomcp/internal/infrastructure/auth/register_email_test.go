package auth

import (
	"bytes"
	"encoding/json"
	"errors"
	"net/http"
	"net/http/httptest"
	"testing"
)

// Registration had no tests at all, and the untested part was the branch that decides what to tell
// a user about an email nobody sent.
//
// Two claims in the code were false and pointed in the same wrong direction. The doc comment on
// HandleRegister and the startup warning in cmd/soc both said the verification code is returned in
// the API response when email is unconfigured. It is not — a previous fix removed it. A false
// security note costs more than a missing one: an operator hardens against a leak that does not
// exist while the real defect goes unnamed.
//
// The real defect was the promise. With no sender, the handler created the account, generated a
// code, and answered «Verification code sent to your email». The user waits for a message that was
// never sent, and cannot re-register because the address is taken.

func registerBody(email string) *bytes.Reader {
	body, _ := json.Marshal(map[string]string{
		"email":    email,
		"password": "correct horse battery",
		"name":     "Owner",
		"org_name": "Acme",
		"org_slug": "acme",
	})
	return bytes.NewReader(body)
}

func postRegister(t *testing.T, emailFn EmailSendFunc) (*httptest.ResponseRecorder, *UserStore) {
	t.Helper()
	// Pinned rather than inherited: SOC_REGISTRATION_OPEN=false in the ambient environment would
	// turn every case below into a 403 and the suite would pass by never reaching the code it tests.
	t.Setenv("SOC_REGISTRATION_OPEN", "true")
	users := NewUserStore()
	tenants := NewTenantStore(nil)
	handler := HandleRegister(users, tenants, []byte("test-secret-not-a-real-key"), emailFn)

	rec := httptest.NewRecorder()
	req := httptest.NewRequest(http.MethodPost, "/api/auth/register", registerBody("owner@example.test"))
	handler(rec, req)
	return rec, users
}

func decodeBody(t *testing.T, rec *httptest.ResponseRecorder) map[string]any {
	t.Helper()
	var out map[string]any
	if err := json.Unmarshal(rec.Body.Bytes(), &out); err != nil {
		t.Fatalf("response is not JSON: %v — %s", err, rec.Body.String())
	}
	return out
}

func TestRegistrationWithoutEmailRefusesAndCreatesNothing(t *testing.T) {
	t.Setenv("SOC_EMAIL_DEV_MODE", "")
	rec, users := postRegister(t, nil)

	if rec.Code != http.StatusServiceUnavailable {
		t.Errorf("status = %d, want 503 — a deployment that cannot verify must not promise to", rec.Code)
	}
	// Nothing created is the load-bearing half. Refusing after the row exists leaves an account
	// nobody can verify and whose address nobody can reuse.
	if _, err := users.GetByEmail("owner@example.test"); err == nil {
		t.Error("a user was created by a registration that was refused")
	}
}

func TestRegistrationNeverPutsTheCodeInTheResponse(t *testing.T) {
	// The claim two comments used to make. Checked in both configurations, because a leak that
	// exists in only one of them is still a leak.
	var sent string
	for _, mode := range []string{"1", ""} {
		t.Run("dev_mode="+mode, func(t *testing.T) {
			t.Setenv("SOC_EMAIL_DEV_MODE", mode)
			var emailFn EmailSendFunc
			if mode == "" {
				emailFn = func(_, _, code string) error { sent = code; return nil }
			}
			rec, _ := postRegister(t, emailFn)
			body := rec.Body.String()
			for _, key := range []string{"code", "verification_code", "verify_token"} {
				if got := decodeBody(t, rec)[key]; got != nil {
					t.Errorf("response carries %q = %v", key, got)
				}
			}
			if sent != "" && bytes.Contains([]byte(body), []byte(sent)) {
				t.Error("the code that went to email also went into the response")
			}
		})
	}
}

func TestRegistrationInDevModeSaysTheCodeIsInTheLog(t *testing.T) {
	// The degraded mode has to be asked for, and when asked for it must describe itself. A user
	// reading «check your email» on a deployment with no email has no way to find the code.
	t.Setenv("SOC_EMAIL_DEV_MODE", "1")
	rec, users := postRegister(t, nil)

	if rec.Code != http.StatusCreated {
		t.Fatalf("status = %d, want 201 with the explicit dev opt-in", rec.Code)
	}
	body := decodeBody(t, rec)
	if delivered, ok := body["email_delivered"].(bool); !ok || delivered {
		t.Errorf("email_delivered = %v, want false — no email was sent", body["email_delivered"])
	}
	message, _ := body["message"].(string)
	if !bytes.Contains([]byte(message), []byte("server log")) {
		t.Errorf("message = %q, which does not tell the reader where the code is", message)
	}
	if _, err := users.GetByEmail("owner@example.test"); err != nil {
		t.Errorf("dev mode should still register: %v", err)
	}
}

func TestAFailedSendIsReportedAsAFailedSend(t *testing.T) {
	// Previously this path returned «Verification code sent to your email» after the send errored.
	// The account and code exist, so it is recoverable — but only if the user is told to ask for a
	// resend instead of told to check an inbox nothing arrived in.
	rec, users := postRegister(t, func(_, _, _ string) error {
		return errors.New("resend: 502 bad gateway")
	})

	if rec.Code != http.StatusCreated {
		t.Fatalf("status = %d, want 201 — the account was created", rec.Code)
	}
	body := decodeBody(t, rec)
	if delivered, ok := body["email_delivered"].(bool); !ok || delivered {
		t.Errorf("email_delivered = %v, want false", body["email_delivered"])
	}
	message, _ := body["message"].(string)
	if bytes.Contains([]byte(message), []byte("sent to your email")) {
		t.Errorf("message = %q, which claims a send that failed", message)
	}
	if _, err := users.GetByEmail("owner@example.test"); err != nil {
		t.Errorf("the account should exist so a resend can succeed: %v", err)
	}
}

func TestASuccessfulSendSaysSoAndCarriesTheCodeNowhere(t *testing.T) {
	var toEmail, code string
	rec, _ := postRegister(t, func(to, _, c string) error {
		toEmail, code = to, c
		return nil
	})

	if rec.Code != http.StatusCreated {
		t.Fatalf("status = %d, want 201", rec.Code)
	}
	if toEmail != "owner@example.test" {
		t.Errorf("email went to %q", toEmail)
	}
	if code == "" {
		t.Error("no verification code was generated")
	}
	body := decodeBody(t, rec)
	if delivered, ok := body["email_delivered"].(bool); !ok || !delivered {
		t.Errorf("email_delivered = %v, want true", body["email_delivered"])
	}
}
