package pivot

import (
	"bytes"
	"io"
	"os"
	"runtime"
	"testing"
	"time"

	"github.com/stretchr/testify/assert"
)

type mockOracle struct {
	verdict string
	reason  string
}

func (m *mockOracle) VerifyAction(action string) (string, string) {
	return m.verdict, m.reason
}

func TestExecutor_NoZeroG(t *testing.T) {
	dir := t.TempDir()
	rec := &mockRecorder{}
	e := NewExecutor(dir, nil, rec)

	result := e.Execute("echo hello")
	assert.False(t, result.ZeroGMode)
	assert.Contains(t, result.Error, "ZERO-G mode required")
	assert.True(t, len(rec.decisions) > 0)
	assert.Contains(t, rec.decisions[0], "EXEC_BLOCKED")
}

func TestExecutor_OracleDeny(t *testing.T) {
	dir := t.TempDir()
	// Create .sentinel_leash with ZERO-G.
	createLeash(t, dir, "ZERO-G")

	oracle := &mockOracle{verdict: "DENY", reason: "denied by policy"}
	rec := &mockRecorder{}
	e := NewExecutor(dir+"/.rlm", oracle, rec)

	result := e.Execute("rm -rf /")
	assert.True(t, result.ZeroGMode)
	assert.False(t, result.OraclePass)
	assert.Contains(t, result.Error, "BLOCKED by Oracle")
}

func TestExecutor_OracleReviewBlocks(t *testing.T) {
	// SECURITY regression: a non-ALLOW verdict (REVIEW / unknown) must NOT
	// execute the command. The Oracle marks ambiguous actions as REVIEW
	// ("requires human review"); the executor must fail-closed and block.
	dir := t.TempDir()
	createLeash(t, dir, "ZERO-G")

	for _, verdict := range []string{"REVIEW", "UNKNOWN", ""} {
		oracle := &mockOracle{verdict: verdict, reason: "ambiguous"}
		rec := &mockRecorder{}
		e := NewExecutor(dir+"/.rlm", oracle, rec)

		result := e.Execute("echo should_not_run")
		assert.True(t, result.ZeroGMode)
		assert.False(t, result.OraclePass, "verdict %q must not pass the oracle gate", verdict)
		assert.Contains(t, result.Error, "BLOCKED by Oracle", "verdict %q must be blocked", verdict)
		// Command must never have executed.
		assert.NotContains(t, result.Stdout, "should_not_run", "verdict %q must not execute", verdict)
		assert.Equal(t, 0, result.ExitCode)
	}
}

func TestExecutor_Success(t *testing.T) {
	dir := t.TempDir()
	createLeash(t, dir, "ZERO-G")

	oracle := &mockOracle{verdict: "ALLOW", reason: "stealth"}
	rec := &mockRecorder{}
	e := NewExecutor(dir+"/.rlm", oracle, rec)
	e.SetTimeout(5 * time.Second)

	result := e.Execute("echo hello_pivot")
	assert.True(t, result.ZeroGMode)
	assert.True(t, result.OraclePass)
	assert.Equal(t, 0, result.ExitCode)
	assert.Contains(t, result.Stdout, "hello_pivot")
}

func TestExecutor_StealthPrefix(t *testing.T) {
	dir := t.TempDir()
	createLeash(t, dir, "ZERO-G")

	rec := &mockRecorder{}
	e := NewExecutor(dir+"/.rlm", nil, rec) // no oracle = passthrough

	result := e.Execute("stealth echo stealth_test")
	assert.True(t, result.OraclePass)
	assert.Contains(t, result.Stdout, "stealth_test")
}

func TestExecutor_Timeout(t *testing.T) {
	dir := t.TempDir()
	createLeash(t, dir, "ZERO-G")

	rec := &mockRecorder{}
	e := NewExecutor(dir+"/.rlm", nil, rec)
	e.SetTimeout(100 * time.Millisecond)

	// The command must outlive the timeout without being the shell itself:
	// `sh -c` stays the parent and `sleep` inherits the output pipes. The
	// previous `ping -n 10` meant ten pings only on Windows. On Linux -n is
	// numeric output, ping never stopped, and the killed shell left it holding
	// the pipes, so Execute never returned and CI hit the 10-minute test limit.
	cmdLine := "sleep 30; echo finished"
	if runtime.GOOS == "windows" {
		cmdLine = "ping -n 30 127.0.0.1 && echo finished"
	}

	start := time.Now()
	result := e.Execute(cmdLine)
	elapsed := time.Since(start)

	assert.NotEqual(t, 0, result.ExitCode)
	assert.NotContains(t, result.Stdout, "finished")
	assert.Less(t, elapsed, 10*time.Second,
		"the timeout must bound Execute even when a child of the shell holds the output pipes")
}

func TestParseCommand(t *testing.T) {
	parts := parseCommand("stealth echo hello")
	// Should strip "stealth " prefix.
	if runtime.GOOS == "windows" {
		assert.Equal(t, "cmd", parts[0])
		assert.Equal(t, "/C", parts[1])
	} else {
		assert.Equal(t, "sh", parts[0])
		assert.Equal(t, "-c", parts[1])
	}
	assert.Equal(t, "echo hello", parts[2])
}

func TestLimitedWriter(t *testing.T) {
	var buf = new(bytes.Buffer)
	lw := &limitedWriter{w: buf, limit: 10}
	lw.Write([]byte("12345"))
	lw.Write([]byte("67890"))
	lw.Write([]byte("overflow")) // Should be silently discarded.
	assert.Equal(t, "1234567890", buf.String())
}

// TestLimitedWriter_ShortWriteContract guards the io.Writer contract: a write
// that partially crosses the limit must report it consumed the FULL input
// (n == len(p), err == nil), not just the truncated portion. Otherwise io.Copy
// — which os/exec uses to drain the command's stdout/stderr — aborts with
// io.ErrShortWrite and a successful command's large output is misreported as a
// failed execution.
func TestLimitedWriter_ShortWriteContract(t *testing.T) {
	buf := new(bytes.Buffer)
	lw := &limitedWriter{w: buf, limit: 10}

	// First write fills 5 of 10.
	n, err := lw.Write([]byte("12345"))
	assert.NoError(t, err)
	assert.Equal(t, 5, n)

	// Second write of 8 bytes crosses the remaining 5: only 5 are stored,
	// but the writer must claim all 8 were consumed.
	n, err = lw.Write([]byte("ABCDEFGH"))
	assert.NoError(t, err)
	assert.Equal(t, 8, n, "must report full consumption, not the truncated count")
	assert.Equal(t, "12345ABCDE", buf.String())

	// Drive it through io.Copy exactly as os/exec does; truncation must NOT
	// surface as io.ErrShortWrite.
	buf2 := new(bytes.Buffer)
	lw2 := &limitedWriter{w: buf2, limit: 16}
	written, copyErr := io.Copy(lw2, bytes.NewReader(bytes.Repeat([]byte("X"), 1024)))
	assert.NoError(t, copyErr, "truncation must not produce io.ErrShortWrite")
	assert.Equal(t, int64(1024), written, "io.Copy must consume the whole source")
	assert.Equal(t, 16, buf2.Len(), "stored bytes stay capped at the limit")
}

// TestExecutor_LargeOutputNotFailure proves the end-to-end fix: a command that
// emits more than MaxOutputBytes succeeds (exit 0, no error), with stdout
// cleanly capped — it is NOT reported as a "short write" failure.
func TestExecutor_LargeOutputNotFailure(t *testing.T) {
	dir := t.TempDir()
	createLeash(t, dir, "ZERO-G")

	rec := &mockRecorder{}
	e := NewExecutor(dir+"/.rlm", nil, rec) // no oracle = passthrough
	e.SetTimeout(30 * time.Second)

	// Produce well over MaxOutputBytes (64KB) of stdout.
	var cmdLine string
	if runtime.GOOS == "windows" {
		cmdLine = "for /L %i in (1,1,4000) do @echo AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
	} else {
		cmdLine = "for i in $(seq 1 4000); do echo AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA; done"
	}

	result := e.Execute(cmdLine)
	assert.Empty(t, result.Error, "large output must not be reported as an execution error")
	assert.Equal(t, 0, result.ExitCode, "command succeeded; exit code must be 0")
	assert.LessOrEqual(t, len(result.Stdout), MaxOutputBytes, "stdout must be capped at the limit")
	assert.Greater(t, len(result.Stdout), 0, "stdout should contain the captured prefix")
}

func createLeash(t *testing.T, dir, mode string) {
	t.Helper()
	os.MkdirAll(dir+"/.rlm", 0o755)
	os.WriteFile(dir+"/.sentinel_leash", []byte(mode), 0o644)
}
