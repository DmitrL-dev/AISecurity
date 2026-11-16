package audit

import (
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func TestDecisionLogger_Record(t *testing.T) {
	dir := t.TempDir()
	dl, err := NewDecisionLogger(dir)
	require.NoError(t, err)
	defer dl.Close()

	err = dl.Record(ModuleSynapse, "ACCEPT_SYNAPSE", "similarity=0.92, threshold=0.85")
	require.NoError(t, err)

	err = dl.Record(ModulePeer, "TRUST_UPGRADE", "peer_abc: UNKNOWN → VERIFIED")
	require.NoError(t, err)

	err = dl.Record(ModuleMode, "MODE_TRANSITION", "ARMED → ZERO-G")
	require.NoError(t, err)

	assert.Equal(t, 3, dl.Count())
	assert.NotEqual(t, "GENESIS", dl.PrevHash())

	// Verify file content.
	data, err := os.ReadFile(filepath.Join(dir, "decisions.log"))
	require.NoError(t, err)
	lines := strings.Split(strings.TrimSpace(string(data)), "\n")
	assert.Len(t, lines, 3)

	// First line should have GENESIS as PrevHash.
	assert.Contains(t, lines[0], "| GENESIS")
	assert.Contains(t, lines[0], "SYNAPSE")
	assert.Contains(t, lines[0], "ACCEPT_SYNAPSE")

	// Second line should NOT have GENESIS.
	assert.NotContains(t, lines[1], "GENESIS")
	assert.Contains(t, lines[1], "PEER")
}

func TestDecisionLogger_HashChain(t *testing.T) {
	dir := t.TempDir()
	dl, err := NewDecisionLogger(dir)
	require.NoError(t, err)

	// Record 10 decisions to build a chain.
	for i := 0; i < 10; i++ {
		err := dl.Record(ModuleDIPWatcher, "ALERT", "test alert")
		require.NoError(t, err)
	}
	dl.Close()

	assert.Equal(t, 10, dl.Count())
}

// Review 14.06 round-5: the verifier skipped the GENESIS link, so deleting a
// PREFIX of the log (keeping a self-consistent clean suffix) passed as valid.
// The first record must link to GENESIS; a prefix-deleted log must be flagged.
func TestVerifyChainFromFile_DetectsPrefixDeletion(t *testing.T) {
	dir := t.TempDir()
	dl, err := NewDecisionLogger(dir)
	require.NoError(t, err)
	for i := 0; i < 4; i++ {
		require.NoError(t, dl.Record(ModuleSynapse, "DECISION", "reason"))
	}
	dl.Close()
	path := filepath.Join(dir, "decisions.log")

	// Intact chain verifies clean.
	valid, broken, err := VerifyChainFromFile(path, nil)
	require.NoError(t, err)
	assert.Equal(t, 4, valid)
	assert.Equal(t, 0, broken)

	// Delete the first two records. The new first line's stored prev-hash is a
	// real hash, not GENESIS, so verification must flag it at line 1.
	data, err := os.ReadFile(path)
	require.NoError(t, err)
	lines := strings.Split(strings.TrimSpace(string(data)), "\n")
	require.Len(t, lines, 4)
	require.NoError(t, os.WriteFile(path, []byte(strings.Join(lines[2:], "\n")+"\n"), 0o644))

	valid, broken, err = VerifyChainFromFile(path, nil)
	require.NoError(t, err)
	assert.Equal(t, 1, broken, "prefix-deleted log must be flagged broken at line 1 (missing genesis link)")
	assert.Equal(t, 0, valid)
}

// Review 14.06 round-5: a KEYED (HMAC) chain verifies with the key and CANNOT be
// re-forged without it — closing the keyless full-reforge gap.
func TestVerifyChainFromFile_KeyedRoundtripAndForgeResistance(t *testing.T) {
	dir := t.TempDir()
	t.Setenv("SOC_HMAC_SECRET", "test-hmac-secret-at-least-32-bytes-long!")
	t.Setenv("SOC_HMAC_KEY_ID", "k1")
	dl, err := NewDecisionLogger(dir)
	require.NoError(t, err)
	require.True(t, dl.HMACEnabled(), "SOC_HMAC_SECRET must enable keyed mode")
	for i := 0; i < 4; i++ {
		require.NoError(t, dl.Record(ModuleSynapse, "DECISION", "reason"))
	}
	dl.Close()
	path := filepath.Join(dir, "decisions.log")

	// Verifies with the correct keyset.
	valid, broken, err := VerifyChainFromFile(path, dl.Keyset())
	require.NoError(t, err)
	assert.Equal(t, 4, valid)
	assert.Equal(t, 0, broken)

	// Without the key (the attacker can recompute plain SHA-256 — the public
	// algorithm — but not the HMAC): verification must FAIL at the first keyed link.
	_, brokenNoKey, err := VerifyChainFromFile(path, nil)
	require.NoError(t, err)
	assert.NotEqual(t, 0, brokenNoKey, "keyed chain must NOT verify without the key")

	// Wrong key also fails.
	_, brokenWrong, _ := VerifyChainFromFile(path, map[string][]byte{"k1": []byte("a-completely-wrong-key-of-32-bytes-len!!")})
	assert.NotEqual(t, 0, brokenWrong, "keyed chain must NOT verify with the wrong key")
}

// Review 14.06 round-6 (self-caught): DOWNGRADE attack. SHA-256 is public, so an
// attacker who can write the log can reforge the WHOLE history as legacy (keyless)
// links. If the verifier honoured legacy links while a key is configured, that
// forged chain would verify — defeating the HMAC entirely. A keyless-format chain
// MUST be rejected once a key is held.
func TestVerifyChainFromFile_RejectsLegacyDowngradeWhenKeyed(t *testing.T) {
	dir := t.TempDir()
	// Build a KEYLESS chain (no SOC_HMAC_SECRET) — exactly what an attacker can forge
	// without the key: bare SHA-256 links from GENESIS.
	dl, err := NewDecisionLogger(dir)
	require.NoError(t, err)
	require.False(t, dl.HMACEnabled(), "must be keyless for this test")
	for i := 0; i < 4; i++ {
		require.NoError(t, dl.Record(ModuleSynapse, "DECISION", "reason"))
	}
	dl.Close()
	path := filepath.Join(dir, "decisions.log")

	// Keyless chain verifies under NO keyset (legacy deployment) — baseline.
	valid, broken, err := VerifyChainFromFile(path, nil)
	require.NoError(t, err)
	assert.Equal(t, 4, valid)
	assert.Equal(t, 0, broken)

	// But under a CONFIGURED keyset (keyed deployment) the same legacy chain must be
	// flagged broken at the first link (line 2) — the downgrade is refused.
	keyset := map[string][]byte{"k1": []byte("a-real-key-of-at-least-thirty-two-bytes!")}
	valid, broken, err = VerifyChainFromFile(path, keyset)
	require.NoError(t, err)
	assert.Equal(t, 2, broken, "legacy (downgraded) link must be rejected when a key is configured")
	assert.Equal(t, 1, valid, "only the GENESIS record passes before the downgrade is caught")
}

// Rotation: a chain signed under k1 still verifies when the keyset also carries
// the new current key k2 — old entries remain verifiable through a key rotation
// as long as the retired key is kept in the keyset.
func TestVerifyChainFromFile_RotationKeysetVerifiesOldEntries(t *testing.T) {
	dir := t.TempDir()
	t.Setenv("SOC_HMAC_SECRET", "key-one-at-least-thirty-two-bytes-long!!")
	t.Setenv("SOC_HMAC_KEY_ID", "k1")
	dl, err := NewDecisionLogger(dir)
	require.NoError(t, err)
	for i := 0; i < 3; i++ {
		require.NoError(t, dl.Record(ModuleSynapse, "X", "r"))
	}
	dl.Close()
	path := filepath.Join(dir, "decisions.log")

	rotationKeyset := map[string][]byte{
		"k2": []byte("key-two-the-new-current-thirty-two-byte!"), // new current key
		"k1": []byte("key-one-at-least-thirty-two-bytes-long!!"), // retired key, kept
	}
	valid, broken, err := VerifyChainFromFile(path, rotationKeyset)
	require.NoError(t, err)
	assert.Equal(t, 3, valid)
	assert.Equal(t, 0, broken)
}

// Chain-head resume: a restart must CONTINUE the existing chain, not fork a new
// GENESIS segment. Before the fix, a second logger over the same file linked its
// first record to GENESIS, so VerifyChainFromFile flagged a seam at that line.
func TestDecisionLogger_ResumeChainAcrossRestart(t *testing.T) {
	dir := t.TempDir()
	path := filepath.Join(dir, "decisions.log")

	// First "process": write N records.
	dl1, err := NewDecisionLogger(dir)
	require.NoError(t, err)
	for i := 0; i < 5; i++ {
		require.NoError(t, dl1.Record(ModuleSOC, "DECISION", "first run"))
	}
	headAfterRun1 := dl1.PrevHash()
	require.NoError(t, dl1.Close())

	// "Restart": a fresh logger over the SAME file must seed prevHash from the last
	// record's hash (not GENESIS), so appended records continue the same chain.
	dl2, err := NewDecisionLogger(dir)
	require.NoError(t, err)
	assert.Equal(t, headAfterRun1, dl2.PrevHash(), "restart must resume from the last chain head, not GENESIS")
	assert.NotEqual(t, "GENESIS", dl2.PrevHash())
	for i := 0; i < 3; i++ {
		require.NoError(t, dl2.Record(ModuleSOC, "DECISION", "second run"))
	}
	require.NoError(t, dl2.Close())

	// The full file (8 records across two "processes") must verify with NO seam.
	valid, broken, err := VerifyChainFromFile(path, nil)
	require.NoError(t, err)
	assert.Equal(t, 0, broken, "resumed chain must have no seam at the restart boundary")
	assert.Equal(t, 8, valid)
}

// Resume must also hold for a KEYED (HMAC) chain: the head hash is recomputed with
// the same key, so the keyed chain continues seamlessly across a restart.
func TestDecisionLogger_ResumeChainAcrossRestart_Keyed(t *testing.T) {
	dir := t.TempDir()
	path := filepath.Join(dir, "decisions.log")
	t.Setenv("SOC_HMAC_SECRET", "resume-test-hmac-secret-at-least-32-bytes!")
	t.Setenv("SOC_HMAC_KEY_ID", "k1")

	dl1, err := NewDecisionLogger(dir)
	require.NoError(t, err)
	require.True(t, dl1.HMACEnabled())
	for i := 0; i < 4; i++ {
		require.NoError(t, dl1.Record(ModuleSOC, "DECISION", "first"))
	}
	keyset := dl1.Keyset()
	require.NoError(t, dl1.Close())

	dl2, err := NewDecisionLogger(dir)
	require.NoError(t, err)
	assert.NotEqual(t, "GENESIS", dl2.PrevHash(), "keyed restart must resume, not fork GENESIS")
	for i := 0; i < 4; i++ {
		require.NoError(t, dl2.Record(ModuleSOC, "DECISION", "second"))
	}
	require.NoError(t, dl2.Close())

	valid, broken, err := VerifyChainFromFile(path, keyset)
	require.NoError(t, err)
	assert.Equal(t, 0, broken, "keyed resumed chain must verify with no seam")
	assert.Equal(t, 8, valid)
}

// An empty existing file must fall back to GENESIS (no crash, fresh chain).
func TestDecisionLogger_ResumeEmptyFileIsGenesis(t *testing.T) {
	dir := t.TempDir()
	path := filepath.Join(dir, "decisions.log")
	require.NoError(t, os.WriteFile(path, []byte{}, 0o600))

	dl, err := NewDecisionLogger(dir)
	require.NoError(t, err)
	defer dl.Close()
	assert.Equal(t, "GENESIS", dl.PrevHash(), "empty file must start a fresh GENESIS chain")
	require.NoError(t, dl.Record(ModuleSOC, "DECISION", "r"))

	valid, broken, err := VerifyChainFromFile(path, nil)
	require.NoError(t, err)
	assert.Equal(t, 0, broken)
	assert.Equal(t, 1, valid)
}

// A torn tail must not be spliced with a newly appended decision.
func TestDecisionLogger_ResumeRejectsTrailingPartialLine(t *testing.T) {
	dir := t.TempDir()
	path := filepath.Join(dir, "decisions.log")
	l, err := NewDecisionLogger(dir)
	require.NoError(t, err)
	require.NoError(t, l.Record(ModuleSOC, "DECISION", "synthetic"))
	require.NoError(t, l.Close())
	f, err := os.OpenFile(path, os.O_WRONLY|os.O_APPEND, 0o600)
	require.NoError(t, err)
	_, err = f.WriteString("synthetic partial")
	require.NoError(t, err)
	require.NoError(t, f.Close())
	before, err := os.ReadFile(path)
	require.NoError(t, err)
	l, err = NewDecisionLogger(dir)
	if l != nil {
		_ = l.Close()
	}
	require.Error(t, err)
	after, err := os.ReadFile(path)
	require.NoError(t, err)
	assert.Equal(t, before, after)
}

func TestDecisionLogger_AllModules(t *testing.T) {
	dir := t.TempDir()
	dl, err := NewDecisionLogger(dir)
	require.NoError(t, err)
	defer dl.Close()

	modules := []DecisionModule{ModuleSynapse, ModulePeer, ModuleMode, ModuleDIPWatcher, ModuleOracle, ModuleGenome, ModuleDoctor}
	for _, m := range modules {
		err := dl.Record(m, "TEST", "testing module "+string(m))
		require.NoError(t, err)
	}
	assert.Equal(t, 7, dl.Count())
}

func TestExtractPrevHash(t *testing.T) {
	line := "[2026-03-09T21:00:00.000+10:00] | SYNAPSE | ACCEPT | reason | abc123hash"
	hash := extractPrevHash(line)
	assert.Equal(t, "abc123hash", hash)
}

func TestSplitLines(t *testing.T) {
	lines := splitLines("line1\nline2\r\nline3")
	assert.Len(t, lines, 3)
	assert.Equal(t, "line1", lines[0])
	assert.Equal(t, "line2", lines[1])
	assert.Equal(t, "line3", lines[2])
}
