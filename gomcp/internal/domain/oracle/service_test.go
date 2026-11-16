package oracle

import (
	"testing"

	"github.com/stretchr/testify/assert"
)

func TestService_DefaultMode(t *testing.T) {
	svc := NewService()
	assert.Equal(t, OModeArmed, svc.GetMode())
}

func TestService_SetMode(t *testing.T) {
	svc := NewService()
	svc.SetMode(OModeZeroG)
	assert.Equal(t, OModeZeroG, svc.GetMode())

	svc.SetMode(OModeSafe)
	assert.Equal(t, OModeSafe, svc.GetMode())
}

func TestService_Evaluate_Armed_CleanContent(t *testing.T) {
	svc := NewService()
	result := svc.Evaluate("normal project fact about architecture")

	assert.Equal(t, EvalAllow, result.Verdict)
	assert.Equal(t, "STANDARD", result.Origin)
	assert.Equal(t, "ARMED", result.Mode)
}

func TestService_Evaluate_Armed_SecretBlocked(t *testing.T) {
	svc := NewService()
	result := svc.Evaluate(`api_key = "sk-1234567890abcdefghijklmnopqrstuv"`)

	assert.Equal(t, EvalDenySecret, result.Verdict)
	assert.Equal(t, "SECURITY", result.Origin)
	assert.NotEmpty(t, result.Detections)
}

func TestService_Evaluate_ZeroG_CleanContent(t *testing.T) {
	svc := NewService()
	svc.SetMode(OModeZeroG)

	result := svc.Evaluate("offensive research data for red team analysis")
	assert.Equal(t, EvalRawIntent, result.Verdict)
	assert.Equal(t, "RAW_INTENT", result.Origin)
	assert.Equal(t, "ZERO-G", result.Mode)
}

func TestService_Evaluate_ZeroG_SecretStillBlocked(t *testing.T) {
	svc := NewService()
	svc.SetMode(OModeZeroG)

	// Even in ZERO-G, secrets are ALWAYS blocked.
	result := svc.Evaluate(`password = "super_secret_password_123"`)
	assert.Equal(t, EvalDenySecret, result.Verdict)
	assert.Equal(t, "SECURITY", result.Origin)
}

func TestService_Evaluate_Safe_AllBlocked(t *testing.T) {
	svc := NewService()
	svc.SetMode(OModeSafe)

	result := svc.Evaluate("any content in safe mode")
	assert.Equal(t, EvalDenySafe, result.Verdict)
	assert.Equal(t, "SAFE_MODE", result.Origin)
}

func TestService_EvaluateWrite_Safe(t *testing.T) {
	svc := NewService()
	svc.SetMode(OModeSafe)

	result := svc.EvaluateWrite()
	assert.Equal(t, EvalDenySafe, result.Verdict)
}

func TestService_EvaluateWrite_Armed(t *testing.T) {
	svc := NewService()
	result := svc.EvaluateWrite()
	assert.Equal(t, EvalAllow, result.Verdict)
}

func TestFormatOriginTag(t *testing.T) {
	assert.Equal(t, "origin:RAW_INTENT",
		FormatOriginTag(&EvalResult{Origin: "RAW_INTENT"}))
	assert.Equal(t, "origin:STANDARD",
		FormatOriginTag(&EvalResult{Origin: "STANDARD"}))
}

func TestEvalVerdict_String(t *testing.T) {
	assert.Equal(t, "ALLOW", EvalAllow.String())
	assert.Equal(t, "DENY:SECRET", EvalDenySecret.String())
	assert.Equal(t, "DENY:ETHICAL", EvalDenyEthical.String())
	assert.Equal(t, "ALLOW:RAW_INTENT", EvalRawIntent.String())
	assert.Equal(t, "DENY:SAFE_MODE", EvalDenySafe.String())
}
