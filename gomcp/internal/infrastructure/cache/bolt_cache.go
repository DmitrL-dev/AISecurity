package cache

import (
	"context"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"sync"

	"github.com/syntrex/gomcp/internal/domain/memory"
	rlmscope "github.com/syntrex/gomcp/internal/domain/scope"
	bolt "go.etcd.io/bbolt"
)

var l0Bucket = []byte("l0_facts")

// BoltCache implements memory.HotCache using bbolt for L0 fact caching.
type BoltCache struct {
	db *bolt.DB
	mu sync.RWMutex
}

// NewBoltCache opens or creates a bbolt database for caching.
func NewBoltCache(path string) (*BoltCache, error) {
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		return nil, fmt.Errorf("create cache directory: %w", err)
	}
	db, err := bolt.Open(path, 0o600, &bolt.Options{NoSync: false})
	if err != nil {
		return nil, fmt.Errorf("open bolt cache: %w", err)
	}

	// Ensure bucket exists.
	err = db.Update(func(tx *bolt.Tx) error {
		_, err := tx.CreateBucketIfNotExists(l0Bucket)
		return err
	})
	if err != nil {
		db.Close()
		return nil, fmt.Errorf("create bucket: %w", err)
	}

	return &BoltCache{db: db}, nil
}

// NewBoltCacheInMemory creates an in-memory bolt cache (for testing).
// bbolt doesn't support true in-memory, so we use a temp file.
func NewBoltCacheFromDB(db *bolt.DB) (*BoltCache, error) {
	err := db.Update(func(tx *bolt.Tx) error {
		_, err := tx.CreateBucketIfNotExists(l0Bucket)
		return err
	})
	if err != nil {
		return nil, fmt.Errorf("create bucket: %w", err)
	}
	return &BoltCache{db: db}, nil
}

// GetL0Facts returns all cached L0 (project-level) facts.
func (c *BoltCache) GetL0Facts(ctx context.Context) ([]*memory.Fact, error) {
	c.mu.RLock()
	defer c.mu.RUnlock()

	sc := rlmscope.FromContext(ctx)
	var facts []*memory.Fact
	err := c.db.View(func(tx *bolt.Tx) error {
		b := tx.Bucket(l0Bucket)
		if b == nil {
			return nil
		}
		return b.ForEach(func(k, v []byte) error {
			var f memory.Fact
			if err := json.Unmarshal(v, &f); err != nil {
				return fmt.Errorf("unmarshal fact %s: %w", string(k), err)
			}
			if f.TenantID == "" {
				f.TenantID = rlmscope.DefaultTenantID
			}
			if f.ProjectID == "" {
				f.ProjectID = rlmscope.DefaultProjectID
			}
			if f.TenantID != sc.TenantID || f.ProjectID != sc.ProjectID {
				return nil
			}
			// HotCache is a legacy project-wide surface. Old cache files may
			// contain session facts written before exact isolation existed; do
			// not let those rows bypass the SQLite session_id predicates.
			if f.SessionID != "" {
				return nil
			}
			facts = append(facts, &f)
			return nil
		})
	})
	return facts, err
}

// InvalidateFact removes a single fact from the cache.
func (c *BoltCache) InvalidateFact(ctx context.Context, id string) error {
	c.mu.Lock()
	defer c.mu.Unlock()

	sc := rlmscope.FromContext(ctx)
	return c.db.Update(func(tx *bolt.Tx) error {
		b := tx.Bucket(l0Bucket)
		if b == nil {
			return nil
		}
		_ = b.Delete([]byte(id)) // legacy unscoped key
		return b.Delete(cacheKey(sc, id))
	})
}

// WarmUp populates the cache with a batch of L0 facts.
func (c *BoltCache) WarmUp(ctx context.Context, facts []*memory.Fact) error {
	c.mu.Lock()
	defer c.mu.Unlock()

	sc := rlmscope.FromContext(ctx)
	return c.db.Update(func(tx *bolt.Tx) error {
		b := tx.Bucket(l0Bucket)
		if b == nil {
			return fmt.Errorf("l0_facts bucket not found")
		}
		for _, f := range facts {
			if f == nil || f.SessionID != "" {
				continue
			}
			f.TenantID = sc.TenantID
			f.ProjectID = sc.ProjectID
			data, err := json.Marshal(f)
			if err != nil {
				return fmt.Errorf("marshal fact %s: %w", f.ID, err)
			}
			if err := b.Put(cacheKey(sc, f.ID), data); err != nil {
				return fmt.Errorf("put fact %s: %w", f.ID, err)
			}
		}
		return nil
	})
}

func cacheKey(sc rlmscope.Scope, id string) []byte {
	sc = sc.Normalize()
	return []byte(sc.TenantID + "\x00" + sc.ProjectID + "\x00" + id)
}

// Close closes the bbolt database.
func (c *BoltCache) Close() error {
	return c.db.Close()
}

// Ensure BoltCache implements memory.HotCache.
var _ memory.HotCache = (*BoltCache)(nil)
