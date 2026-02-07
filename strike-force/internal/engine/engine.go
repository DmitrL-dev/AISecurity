package engine

import (
	"log"

	"github.com/sentinel-community/strike-force/internal/config"
)

// Engine is the core orchestration controller
type Engine struct {
	cfg *config.Config
}

// New creates a new Engine instance
func New(cfg *config.Config) *Engine {
	return &Engine{
		cfg: cfg,
	}
}

// Run starts the attack orchestration
func (e *Engine) Run() error {
	log.Printf("Starting Engine with %d workers targeting %s", e.cfg.ThreadPoolSize, e.cfg.TargetURL)
	return nil
}
