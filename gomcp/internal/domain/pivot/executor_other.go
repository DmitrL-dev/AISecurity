//go:build !unix

package pivot

import "os/exec"

// killProcessTree keeps the default cancellation, which kills only the direct
// child. There is no process group to signal here; Execute's WaitDelay still
// bounds how long a surviving grandchild can hold the output pipes.
func killProcessTree(*exec.Cmd) {}
