package audit

import (
	"compress/gzip"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"time"
)

const (
	// MaxLogSize is the default rotation threshold (100 MB).
	MaxLogSize int64 = 100 * 1024 * 1024
)

// RotationResult describes the outcome of a rotation attempt.
type RotationResult struct {
	Rotated      bool   `json:"rotated"`
	OriginalSize int64  `json:"original_size"`
	ArchivePath  string `json:"archive_path,omitempty"`
	ArchiveSize  int64  `json:"archive_size,omitempty"`
}

// RotateIfNeeded checks the decisions.log size and rotates if it exceeds maxSize.
// Rotation: rename → gzip compress → create new empty log.
// Returns rotation result.
func RotateIfNeeded(rlmDir string, maxSize int64) (RotationResult, error) {
	if maxSize <= 0 {
		maxSize = MaxLogSize
	}

	logPath := filepath.Join(rlmDir, decisionsFileName)
	info, err := os.Stat(logPath)
	if err != nil {
		if os.IsNotExist(err) {
			return RotationResult{Rotated: false}, nil
		}
		return RotationResult{}, err
	}

	if info.Size() < maxSize {
		return RotationResult{Rotated: false, OriginalSize: info.Size()}, nil
	}

	// Generate archive name with timestamp.
	ts := time.Now().Format("20060102_150405")
	archiveName := fmt.Sprintf("decisions_%s.log.gz", ts)
	archivePath := filepath.Join(rlmDir, archiveName)

	// Compress the log file.
	if err := compressFile(logPath, archivePath); err != nil {
		return RotationResult{}, fmt.Errorf("rotation: compress: %w", err)
	}

	archiveInfo, _ := os.Stat(archivePath)
	archiveSize := int64(0)
	if archiveInfo != nil {
		archiveSize = archiveInfo.Size()
	}

	// Truncate the original log (new empty file).
	if err := os.Truncate(logPath, 0); err != nil {
		return RotationResult{}, fmt.Errorf("rotation: truncate: %w", err)
	}

	return RotationResult{
		Rotated:      true,
		OriginalSize: info.Size(),
		ArchivePath:  archivePath,
		ArchiveSize:  archiveSize,
	}, nil
}

func compressFile(src, dst string) error {
	in, err := os.Open(src)
	if err != nil {
		return err
	}
	defer in.Close()

	out, err := os.Create(dst)
	if err != nil {
		return err
	}
	defer out.Close()

	gz := gzip.NewWriter(out)
	gz.Name = filepath.Base(src)
	gz.ModTime = time.Now()

	if _, err := io.Copy(gz, in); err != nil {
		return err
	}
	return gz.Close()
}
