package soc

import (
	"fmt"
	"os"
	"time"

	"gopkg.in/yaml.v3"
)

// RuleConfig is the YAML format for custom correlation rules (§7.5).
//
// Example rules.yaml:
//
//	rules:
//	  - id: CUSTOM-001
//	    name: API Key Spray
//	    required_categories: [auth_bypass, brute_force]
//	    min_events: 5
//	    time_window: 2m
//	    severity: HIGH
//	    kill_chain_phase: Reconnaissance
//	    mitre_mapping: [T1110]
//	    cross_sensor: true
type RuleConfig struct {
	Rules []YAMLRule `yaml:"rules"`
}

// YAMLRule is a single custom correlation rule loaded from YAML.
type YAMLRule struct {
	ID                 string   `yaml:"id"`
	Name               string   `yaml:"name"`
	RequiredCategories []string `yaml:"required_categories"`
	MinEvents          int      `yaml:"min_events"`
	TimeWindow         string   `yaml:"time_window"` // e.g., "5m", "10m", "1h"
	Severity           string   `yaml:"severity"`
	KillChainPhase     string   `yaml:"kill_chain_phase"`
	MITREMapping       []string `yaml:"mitre_mapping"`
	Description        string   `yaml:"description"`
	CrossSensor        bool     `yaml:"cross_sensor"` // Allow cross-sensor correlation
}

// LoadRulesFromYAML loads custom correlation rules from a YAML file.
// Returns nil and no error if the file doesn't exist (optional config).
func LoadRulesFromYAML(path string) ([]SOCCorrelationRule, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		if os.IsNotExist(err) {
			return nil, nil // Optional — no custom rules
		}
		return nil, fmt.Errorf("read rules file: %w", err)
	}

	var cfg RuleConfig
	if err := yaml.Unmarshal(data, &cfg); err != nil {
		return nil, fmt.Errorf("parse rules YAML: %w", err)
	}

	rules := make([]SOCCorrelationRule, 0, len(cfg.Rules))
	for _, yr := range cfg.Rules {
		dur, err := time.ParseDuration(yr.TimeWindow)
		if err != nil {
			return nil, fmt.Errorf("rule %s: invalid time_window %q: %w", yr.ID, yr.TimeWindow, err)
		}

		if yr.MinEvents == 0 {
			yr.MinEvents = 2 // Default
		}

		rules = append(rules, SOCCorrelationRule{
			ID:                 yr.ID,
			Name:               yr.Name,
			RequiredCategories: yr.RequiredCategories,
			MinEvents:          yr.MinEvents,
			TimeWindow:         dur,
			Severity:           EventSeverity(yr.Severity),
			KillChainPhase:     yr.KillChainPhase,
			MITREMapping:       yr.MITREMapping,
			Description:        yr.Description,
			CrossSensor:        yr.CrossSensor,
		})
	}
	return rules, nil
}
