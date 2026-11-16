//go:build unix

package pivot

import (
	"errors"
	"os"
	"os/exec"
	"syscall"
)

// killProcessTree starts the command in its own process group and makes the
// context cancellation signal the whole group, so the shell and everything it
// spawned die together when the timeout fires.
func killProcessTree(cmd *exec.Cmd) {
	cmd.SysProcAttr = &syscall.SysProcAttr{Setpgid: true}
	cmd.Cancel = func() error {
		// A negative pid addresses the process group led by the shell.
		err := syscall.Kill(-cmd.Process.Pid, syscall.SIGKILL)
		if errors.Is(err, syscall.ESRCH) {
			return os.ErrProcessDone
		}
		return err
	}
}
