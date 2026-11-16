//go:build unix

package pivot

import (
	"errors"
	"fmt"
	"os"
	"strconv"
	"strings"
	"syscall"
	"testing"
	"time"

	"github.com/stretchr/testify/require"
)

// TestExecutor_TimeoutKillsTheWholeProcessGroup: returning on time is not
// enough if the command's children keep running. The shell prints the pid of
// its background child and waits for it; after the timeout that child must be
// gone too.
func TestExecutor_TimeoutKillsTheWholeProcessGroup(t *testing.T) {
	dir := t.TempDir()
	createLeash(t, dir, "ZERO-G")

	e := NewExecutor(dir+"/.rlm", nil, &mockRecorder{})
	e.SetTimeout(300 * time.Millisecond)

	result := e.Execute("sleep 30 & echo $!; wait")
	pid, err := strconv.Atoi(strings.TrimSpace(result.Stdout))
	require.NoError(t, err, "stdout %q", result.Stdout)

	// SIGKILL is delivered asynchronously, and the orphan is reaped by
	// whichever process adopts it.
	deadline := time.Now().Add(5 * time.Second)
	for !processGone(pid) {
		if time.Now().After(deadline) {
			t.Fatalf("pid %d outlived the timeout of the command that started it", pid)
		}
		time.Sleep(20 * time.Millisecond)
	}
}

// processGone counts a zombie as gone: it has exited and only waits for its
// adopter to reap it, which a container's init may never do.
func processGone(pid int) bool {
	if err := syscall.Kill(pid, 0); errors.Is(err, syscall.ESRCH) {
		return true
	}
	stat, err := os.ReadFile(fmt.Sprintf("/proc/%d/stat", pid))
	if err != nil {
		return false
	}
	// The state follows the parenthesised command name, which may contain spaces.
	s := string(stat)
	i := strings.LastIndexByte(s, ')')
	return i >= 0 && i+2 < len(s) && s[i+2] == 'Z'
}
