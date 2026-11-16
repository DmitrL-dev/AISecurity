package auth

import (
	"testing"
	"time"
)

var testSecret = []byte("test-secret-must-be-at-least-32-bytes-long!")

func TestSign_Verify_RoundTrip(t *testing.T) {
	claims := Claims{
		Sub:  "admin",
		Role: "admin",
		Exp:  time.Now().Add(time.Hour).Unix(),
	}

	token, err := Sign(claims, testSecret)
	if err != nil {
		t.Fatalf("Sign: %v", err)
	}

	got, err := Verify(token, testSecret)
	if err != nil {
		t.Fatalf("Verify: %v", err)
	}

	if got.Sub != "admin" {
		t.Errorf("Sub = %q, want admin", got.Sub)
	}
	if got.Role != "admin" {
		t.Errorf("Role = %q, want admin", got.Role)
	}
	if got.Iss != "sentinel-soc" {
		t.Errorf("Iss = %q, want sentinel-soc", got.Iss)
	}
}

func TestVerify_ExpiredToken(t *testing.T) {
	token, _ := Sign(Claims{
		Sub: "user",
		Role: "viewer",
		Exp: time.Now().Add(-time.Hour).Unix(),
	}, testSecret)

	_, err := Verify(token, testSecret)
	if err != ErrExpiredToken {
		t.Errorf("expected ErrExpiredToken, got %v", err)
	}
}

func TestVerify_InvalidSignature(t *testing.T) {
	token, _ := Sign(Claims{
		Sub: "user",
		Role: "viewer",
		Exp: time.Now().Add(time.Hour).Unix(),
	}, testSecret)

	wrongSecret := []byte("wrong-secret-that-is-also-32-bytes-x")
	_, err := Verify(token, wrongSecret)
	if err != ErrInvalidToken {
		t.Errorf("expected ErrInvalidToken, got %v", err)
	}
}

func TestVerify_MalformedToken(t *testing.T) {
	_, err := Verify("not.a.valid.jwt", testSecret)
	if err != ErrInvalidToken {
		t.Errorf("expected ErrInvalidToken, got %v", err)
	}

	_, err = Verify("", testSecret)
	if err != ErrInvalidToken {
		t.Errorf("expected ErrInvalidToken for empty token, got %v", err)
	}
}

func TestSign_ShortSecret(t *testing.T) {
	_, err := Sign(Claims{Sub: "x", Exp: time.Now().Add(time.Hour).Unix()}, []byte("short"))
	if err != ErrInvalidSecret {
		t.Errorf("expected ErrInvalidSecret, got %v", err)
	}
}

func TestNewAccessToken(t *testing.T) {
	token, err := NewAccessToken("analyst", "analyst", testSecret, 0)
	if err != nil {
		t.Fatalf("NewAccessToken: %v", err)
	}
	claims, err := Verify(token, testSecret)
	if err != nil {
		t.Fatalf("Verify: %v", err)
	}
	if claims.Sub != "analyst" || claims.Role != "analyst" {
		t.Errorf("unexpected claims: %+v", claims)
	}
	// Default TTL = 15 min, check expiry is within 16 min
	if claims.Exp > time.Now().Add(16*time.Minute).Unix() {
		t.Error("access token TTL too long")
	}
}

func TestNewRefreshToken(t *testing.T) {
	token, err := NewRefreshToken("admin", "admin", testSecret, 0)
	if err != nil {
		t.Fatalf("NewRefreshToken: %v", err)
	}
	claims, err := Verify(token, testSecret)
	if err != nil {
		t.Fatalf("Verify: %v", err)
	}
	// Default TTL = 7 days
	if claims.Exp < time.Now().Add(6*24*time.Hour).Unix() {
		t.Error("refresh token TTL too short")
	}
}
