package app

import (
	"context"
	"fmt"
	"sync"

	"github.com/sentinel-community/strike-force/internal/domain/entity"
	"github.com/sentinel-community/strike-force/internal/domain/port"
)

// Engine is the core orchestrator
type Engine struct {
	config    entity.AttackProfile
	brain     port.Brain
	evasion   port.Evasion
	transport port.Transport
	modules   []port.Module
	results   chan entity.Result
}

func NewEngine(
	cfg entity.AttackProfile,
	brain port.Brain,
	evasion port.Evasion,
	transport port.Transport,
	modules []port.Module,
) *Engine {
	return &Engine{
		config:    cfg,
		brain:     brain,
		evasion:   evasion,
		transport: transport,
		modules:   modules,
		results:   make(chan entity.Result, 10000), // Large buffer
	}
}

// Run executes the campaign against targets
func (e *Engine) Run(ctx context.Context, targets []entity.Target) {
	var wg sync.WaitGroup
	jobs := make(chan entity.Target, len(targets))

	// 1. Start Workers
	fmt.Printf("[*] Starting %d workers...\n", e.config.Concurrency)
	for i := 0; i < e.config.Concurrency; i++ {
		wg.Add(1)
		go e.worker(ctx, &wg, jobs)
	}

	// 2. Feed Targets (Initial seeding)
	for _, t := range targets {
		jobs <- t
	}
	close(jobs)

	// 3. Wait for completion
	wg.Wait()
	close(e.results)
}

func (e *Engine) worker(ctx context.Context, wg *sync.WaitGroup, jobs <-chan entity.Target) {
	defer wg.Done()

	for target := range jobs {
		// A. Run specific Modules first (Recon/Fingerprinting)
		for _, mod := range e.modules {
			modResults, err := mod.Execute(ctx, target)
			if err != nil {
				// logging?
				continue
			}
			for _, res := range modResults {
				e.results <- res
			}
		}

		// B. Enter Artemis Loop (Fuzzing/Attacks)
		// For high performance, we might limit this loop or run it in separate jobs.
		// Here we do a simple loop until exhaustion.
		history := []entity.Result{} // Local history for this target worker session

		for {
			select {
			case <-ctx.Done():
				return
			default:
			}

			// 1. Ask Brain
			payload, ok := e.brain.DecideNext(target, history)
			if !ok {
				break // Exhausted
			}

			// 2. Mutate (Evasion)
			// Apply random or specific mutation
			mutatedValue := e.evasion.Mutate(payload.Value, payload.Technique) // simple mapping
			payload.Value = mutatedValue

			// 3. Send (Transport)
			res, err := e.transport.Send(ctx, target, *payload)
			if err != nil {
				// Transport error (timeout etc)
				e.results <- entity.Result{Error: err, TargetID: target.ID}
				continue
			}

			// 4. Report to Brain
			e.brain.ReportResult(*res)
			history = append(history, *res)

			// 5. Stream result
			e.results <- *res
		}
	}
}

// Results returns the result channel
func (e *Engine) Results() <-chan entity.Result {
	return e.results
}
