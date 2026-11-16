package soc

import (
	"os"
	"strings"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"

	domsoc "github.com/syntrex/gomcp/internal/domain/soc"
	"github.com/syntrex/gomcp/internal/infrastructure/audit"
)

// tamperDecisionLog corrupts a middle record of the decision log so the hash
// chain no longer verifies. It closes the logger first (Windows releases the file
// lock) — the report's Count()/PrevHash() read cached in-memory fields, and the
// integrity check re-reads the (now tampered) file from disk, so the verdict
// flips to BROKEN exactly as it would for a real on-disk tamper.
func tamperDecisionLog(t *testing.T, logger *audit.DecisionLogger) {
	t.Helper()
	path := logger.Path()
	require.NoError(t, logger.Close())

	data, err := os.ReadFile(path)
	require.NoError(t, err)
	lines := strings.Split(strings.TrimSpace(string(data)), "\n")
	require.GreaterOrEqual(t, len(lines), 2, "need at least 2 records to tamper a middle one")

	// Mutate the REASON field of the first record. Its content changes, so the
	// SECOND record's stored prev-hash (computed over the original first line) no
	// longer matches — the chain breaks at line 2. Format:
	// [ts] | MODULE | DECISION | REASON | PREV_HASH  (pipe-delimited).
	parts := strings.Split(lines[0], " | ")
	require.GreaterOrEqual(t, len(parts), 5)
	parts[3] = "TAMPERED-" + parts[3]
	lines[0] = strings.Join(parts, " | ")

	require.NoError(t, os.WriteFile(path, []byte(strings.Join(lines, "\n")+"\n"), 0o644))
}

// findReq returns the requirement with the given ID, failing the test if absent.
func findReq(t *testing.T, reqs []ComplianceRequirement, id string) ComplianceRequirement {
	t.Helper()
	for _, r := range reqs {
		if r.ID == id {
			return r
		}
	}
	t.Fatalf("requirement %s not found", id)
	return ComplianceRequirement{}
}

// hasEvidence reports whether any evidence item's Detail contains substr.
func hasEvidence(reqs []ComplianceRequirement, id, substr string) bool {
	for _, r := range reqs {
		if r.ID != id {
			continue
		}
		for _, e := range r.Evidence {
			if strings.Contains(e.Detail, substr) {
				return true
			}
		}
	}
	return false
}

// --- IMP8: EU AI Act evidence binding (chain VERIFIED ⇒ COMPLIANT) ---

// TestComplianceReport_ChainBackedRequirementsCompliantWhenVerified asserts that
// with a real, non-empty, verifying decision chain the chain-backed requirements
// (15.2 Data Governance, 15.4 Record-keeping) are COMPLIANT and carry the actual
// chain integrity evidence (VERIFIED + entry count), not a static string.
func TestComplianceReport_ChainBackedRequirementsCompliantWhenVerified(t *testing.T) {
	svc := newTestServiceWithLogger(t)

	// Record real decisions so the chain is non-empty and verifies.
	for i := 0; i < 3; i++ {
		require.NoError(t, svc.logger.Record(audit.ModuleSOC, "TEST_DECISION", "evidence binding"))
	}

	report, err := svc.ComplianceReport()
	require.NoError(t, err)

	gov := findReq(t, report.Requirements, "15.2")
	assert.Equal(t, ComplianceCompliant, gov.Status, "data governance COMPLIANT when chain verifies")
	assert.Empty(t, gov.Gap, "COMPLIANT requirement has no gap")

	rec := findReq(t, report.Requirements, "15.4")
	assert.Equal(t, ComplianceCompliant, rec.Status, "record-keeping COMPLIANT when chain verifies")

	// The evidence must be the REAL chain state, machine-verifiable.
	require.NotEmpty(t, gov.Evidence)
	var foundVerified, foundEntries bool
	for _, e := range gov.Evidence {
		if e.Source == "decision_chain" {
			assert.True(t, e.Verifiable, "decision_chain evidence must be marked verifiable")
			if strings.Contains(e.Detail, "integrity=VERIFIED") {
				foundVerified = true
			}
			if strings.Contains(e.Detail, "entries=") {
				foundEntries = true
			}
		}
	}
	assert.True(t, foundVerified, "evidence must state integrity=VERIFIED, got %+v", gov.Evidence)
	assert.True(t, foundEntries, "evidence must include the live entry count, got %+v", gov.Evidence)

	// Registry-backed requirements must carry the REAL live counts.
	assert.True(t, hasEvidence(report.Requirements, "15.1", "correlation_rules="),
		"risk-mgmt evidence must cite the live correlation rule count")
	assert.True(t, hasEvidence(report.Requirements, "15.6", "registered_sensors="),
		"human-oversight evidence must cite the live sensor count")
}

// TestComplianceReport_DegradesWhenChainAbsent asserts the report DEGRADES
// truthfully: with no decision logger the chain is empty/invalid, so the
// chain-backed requirements are NON_COMPLIANT (never COMPLIANT), they say so in
// their gap, and the overall rolls up to NON_COMPLIANT.
func TestComplianceReport_DegradesWhenChainAbsent(t *testing.T) {
	svc := newTestService(t) // no logger

	report, err := svc.ComplianceReport()
	require.NoError(t, err)

	gov := findReq(t, report.Requirements, "15.2")
	assert.Equal(t, ComplianceNonCompliant, gov.Status, "no chain ⇒ data governance NON_COMPLIANT")
	assert.NotEmpty(t, gov.Gap, "degraded requirement must explain the gap")

	rec := findReq(t, report.Requirements, "15.4")
	assert.Equal(t, ComplianceNonCompliant, rec.Status, "no chain ⇒ record-keeping NON_COMPLIANT")

	// Crucially: NEVER COMPLIANT without evidence.
	for _, r := range report.Requirements {
		if r.ID == "15.2" || r.ID == "15.4" {
			assert.NotEqual(t, ComplianceCompliant, r.Status,
				"%s must not be COMPLIANT without a verifying chain", r.ID)
		}
	}

	// Evidence still reflects the (empty) reality rather than claiming success.
	assert.True(t, hasEvidence(report.Requirements, "15.2", "chain_valid=false"),
		"evidence must honestly report chain_valid=false")

	assert.Equal(t, ComplianceNonCompliant, report.Overall,
		"overall NON_COMPLIANT when a machine-verified control fails")
}

// TestComplianceReport_DetectsTamperedChain asserts that a BROKEN chain (tampered
// log line) is reported NON_COMPLIANT with a gap pointing at the broken line —
// never COMPLIANT.
func TestComplianceReport_DetectsTamperedChain(t *testing.T) {
	svc := newTestServiceWithLogger(t)
	for i := 0; i < 3; i++ {
		require.NoError(t, svc.logger.Record(audit.ModuleSOC, "TEST_DECISION", "pre-tamper"))
	}
	// Verify it is healthy first.
	pre, err := svc.ComplianceReport()
	require.NoError(t, err)
	require.Equal(t, ComplianceCompliant, findReq(t, pre.Requirements, "15.4").Status)

	// Tamper: rewrite the log so a middle line's hash chain no longer matches.
	tamperDecisionLog(t, svc.logger)

	post, err := svc.ComplianceReport()
	require.NoError(t, err)
	rec := findReq(t, post.Requirements, "15.4")
	assert.Equal(t, ComplianceNonCompliant, rec.Status, "tampered chain ⇒ NON_COMPLIANT")
	assert.NotEmpty(t, rec.Gap, "tampered chain must explain the integrity failure")
	gov := findReq(t, post.Requirements, "15.2")
	assert.Equal(t, ComplianceNonCompliant, gov.Status, "tampered chain ⇒ data governance NON_COMPLIANT")
}

// --- IMP8: SOC 2 Common Criteria evidence binding ---

// TestSOC2ComplianceReport_AuditTrailCompliantWhenChainVerifies asserts CC7.3
// (audit-trail integrity) is COMPLIANT and chain-backed when the chain verifies,
// and that CC4.1 (monitoring) becomes COMPLIANT once events have been observed.
func TestSOC2ComplianceReport_AuditTrailCompliantWhenChainVerifies(t *testing.T) {
	svc := newTestServiceWithLogger(t)

	// Ingest a real event so monitoring has evidence AND the chain grows.
	ev := domsoc.NewSOCEvent(domsoc.SourceSentinelCore, domsoc.SeverityLow, "test", "soc2 monitoring evidence")
	_, _, err := svc.IngestEvent(ev)
	require.NoError(t, err)

	report, err := svc.SOC2ComplianceReport()
	require.NoError(t, err)
	assert.Equal(t, "SOC 2 Common Criteria (self-assessment)", report.Framework)
	assert.Len(t, report.Requirements, 4, "CC4.1, CC4.2, CC7.2, CC7.3")

	cc73 := findReq(t, report.Requirements, "CC7.3")
	assert.Equal(t, ComplianceCompliant, cc73.Status, "audit-trail integrity COMPLIANT when chain verifies")
	assert.True(t, hasEvidence(report.Requirements, "CC7.3", "integrity=VERIFIED"),
		"CC7.3 evidence must show the live chain integrity result")

	cc41 := findReq(t, report.Requirements, "CC4.1")
	assert.Equal(t, ComplianceCompliant, cc41.Status, "monitoring COMPLIANT once events observed")
	assert.True(t, hasEvidence(report.Requirements, "CC4.1", "events_total="),
		"CC4.1 evidence must cite the live events_total")

	cc42 := findReq(t, report.Requirements, "CC4.2")
	assert.Equal(t, ComplianceSelfAttested, cc42.Status, "deficiency remediation is self-attested")
}

// TestSOC2ComplianceReport_DegradesWhenEvidenceAbsent asserts SOC 2 degrades
// truthfully: with no logger (no chain) and no events, CC7.3 is NON_COMPLIANT and
// CC4.1 is NOT_ASSESSED (no monitoring activity to claim), and the overall is the
// honest non-conformant aggregate.
func TestSOC2ComplianceReport_DegradesWhenEvidenceAbsent(t *testing.T) {
	svc := newTestService(t) // no logger, no events

	report, err := svc.SOC2ComplianceReport()
	require.NoError(t, err)

	cc73 := findReq(t, report.Requirements, "CC7.3")
	assert.Equal(t, ComplianceNonCompliant, cc73.Status, "no chain ⇒ audit-trail NON_COMPLIANT")
	assert.NotEmpty(t, cc73.Gap)

	cc41 := findReq(t, report.Requirements, "CC4.1")
	assert.Equal(t, ComplianceNotAssessed, cc41.Status, "no events ⇒ monitoring NOT_ASSESSED, not claimed")
	assert.NotEmpty(t, cc41.Gap)

	// A failing machine-verified control forces the overall to NON_COMPLIANT.
	assert.Equal(t, ComplianceNonCompliant, report.Overall)
}

// TestShortHash verifies the chain-head display helper (keyed prefix preserved,
// long digest truncated, empty → "none").
func TestShortHash(t *testing.T) {
	assert.Equal(t, "none", shortHash(""))
	assert.Equal(t, "GENESIS", shortHash("GENESIS"))
	assert.Equal(t, "abcdef012345", shortHash("abcdef0123456789deadbeef"))   // 12-char prefix of the digest
	assert.Equal(t, "k1:abcdef012345", shortHash("k1:abcdef0123456789ff")) // keyID kept, digest truncated to 12
}
