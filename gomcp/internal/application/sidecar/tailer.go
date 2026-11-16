package sidecar

import (
	"bufio"
	"context"
	"io"
	"log/slog"
	"os"
	"time"
)

// Tailer follows a log file or stdin, emitting lines via a channel.
type Tailer struct {
	pollInterval time.Duration
}

// NewTailer creates a Tailer with the given poll interval for file changes.
func NewTailer(pollInterval time.Duration) *Tailer {
	if pollInterval <= 0 {
		pollInterval = 200 * time.Millisecond
	}
	return &Tailer{pollInterval: pollInterval}
}

// FollowFile tails a file, seeking to end on start.
// Sends lines on the returned channel until ctx is cancelled.
func (t *Tailer) FollowFile(ctx context.Context, path string) (<-chan string, error) {
	f, err := os.Open(path)
	if err != nil {
		return nil, err
	}

	// Seek to end — only process new lines.
	if _, err := f.Seek(0, io.SeekEnd); err != nil {
		f.Close()
		return nil, err
	}

	ch := make(chan string, 256)

	go func() {
		defer f.Close()
		defer close(ch)

		// H-2 fix: Use Scanner with 1MB max line size to prevent OOM.
		const maxLineSize = 1 << 20 // 1MB
		scanner := bufio.NewScanner(f)
		scanner.Buffer(make([]byte, 0, 64*1024), maxLineSize)

		for {
			select {
			case <-ctx.Done():
				return
			default:
			}

			if scanner.Scan() {
				line := scanner.Text()
				if line != "" {
					select {
					case ch <- line:
					case <-ctx.Done():
						return
					}
				}
				continue
			}

			// Scanner stopped — either EOF or error.
			if err := scanner.Err(); err != nil {
				slog.Error("sidecar: read error", "error", err)
				return
			}

			// EOF — wait and check for rotation.
			time.Sleep(t.pollInterval)

			if t.fileRotated(f, path) {
				slog.Info("sidecar: log rotated, reopening", "path", path)
				f.Close()
				newF, err := os.Open(path)
				if err != nil {
					slog.Error("sidecar: reopen failed", "path", path, "error", err)
					return
				}
				f = newF
				scanner = bufio.NewScanner(f)
				scanner.Buffer(make([]byte, 0, 64*1024), maxLineSize)
			} else {
				// Same file, re-create scanner at current position.
				scanner = bufio.NewScanner(f)
				scanner.Buffer(make([]byte, 0, 64*1024), maxLineSize)
			}
		}
	}()

	return ch, nil
}

// FollowStdin reads from stdin line by line.
func (t *Tailer) FollowStdin(ctx context.Context) <-chan string {
	ch := make(chan string, 256)

	go func() {
		defer close(ch)
		scanner := bufio.NewScanner(os.Stdin)
		for scanner.Scan() {
			select {
			case <-ctx.Done():
				return
			default:
			}
			line := scanner.Text()
			if line != "" {
				select {
				case ch <- line:
				case <-ctx.Done():
					return
				}
			}
		}
	}()

	return ch
}

// FollowReader reads from any io.Reader (for testing).
func (t *Tailer) FollowReader(ctx context.Context, r io.Reader) <-chan string {
	ch := make(chan string, 256)

	go func() {
		defer close(ch)
		scanner := bufio.NewScanner(r)
		for scanner.Scan() {
			select {
			case <-ctx.Done():
				return
			default:
			}
			line := scanner.Text()
			if line != "" {
				select {
				case ch <- line:
				case <-ctx.Done():
					return
				}
			}
		}
	}()

	return ch
}

// fileRotated checks if the file path now points to a different inode.
func (t *Tailer) fileRotated(current *os.File, path string) bool {
	curInfo, err1 := current.Stat()
	newInfo, err2 := os.Stat(path)
	if err1 != nil || err2 != nil {
		return false
	}
	return !os.SameFile(curInfo, newInfo)
}
