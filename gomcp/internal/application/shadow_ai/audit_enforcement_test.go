package shadow_ai

import (
	"context"
	"testing"
)

func TestAuditManualBlockDoesNotClaimDetectOnlyAsEnforced(t *testing.T) {
	controller := &ShadowAIController{fallback: NewFallbackManager(NewPluginRegistry(), "detect_only")}
	for _, kind := range []string{"domain", "ip", "host"} {
		if err := controller.ManualBlock(context.Background(), BlockRequest{TargetType: kind, Target: "synthetic.invalid"}); err == nil {
			t.Fatalf("%s claimed containment with no plugin", kind)
		}
	}
}
