package lifecycle

import (
	"crypto/rand"
	"fmt"
	"log"
	"os"
)

// ShredDatabase irreversibly destroys a database file by overwriting
// its header with random bytes, making it unreadable without backup.
//
// For SQLite: overwrites first 100 bytes (header with magic bytes "SQLite format 3\000").
// For BoltDB: overwrites first 4096 bytes (two 4KB meta pages).
//
// WARNING: This operation is IRREVERSIBLE. Data is only recoverable from peer backup.
func ShredDatabase(dbPath string, headerSize int) error {
	f, err := os.OpenFile(dbPath, os.O_WRONLY, 0)
	if err != nil {
		return fmt.Errorf("shred: open %s: %w", dbPath, err)
	}
	defer f.Close()

	// Overwrite header with random bytes.
	noise := make([]byte, headerSize)
	if _, err := rand.Read(noise); err != nil {
		return fmt.Errorf("shred: random: %w", err)
	}

	if _, err := f.WriteAt(noise, 0); err != nil {
		return fmt.Errorf("shred: write %s: %w", dbPath, err)
	}

	// Force flush to disk.
	if err := f.Sync(); err != nil {
		return fmt.Errorf("shred: sync %s: %w", dbPath, err)
	}

	log.Printf("SHRED: %s header (%d bytes) destroyed", dbPath, headerSize)
	return nil
}

// ShredSQLite shreds a SQLite database (100-byte header).
func ShredSQLite(dbPath string) error {
	return ShredDatabase(dbPath, 100)
}

// ShredBoltDB shreds a BoltDB database (4096-byte meta pages).
func ShredBoltDB(dbPath string) error {
	return ShredDatabase(dbPath, 4096)
}

// ShredAll shreds all known database files in the .rlm directory.
func ShredAll(rlmDir string) []error {
	var errs []error

	sqlitePath := rlmDir + "/memory/memory_bridge_v2.db"
	if _, err := os.Stat(sqlitePath); err == nil {
		if err := ShredSQLite(sqlitePath); err != nil {
			errs = append(errs, err)
		}
	}

	boltPath := rlmDir + "/cache.db"
	if _, err := os.Stat(boltPath); err == nil {
		if err := ShredBoltDB(boltPath); err != nil {
			errs = append(errs, err)
		}
	}

	if len(errs) == 0 {
		log.Printf("SHRED: All databases destroyed in %s", rlmDir)
	}
	return errs
}
