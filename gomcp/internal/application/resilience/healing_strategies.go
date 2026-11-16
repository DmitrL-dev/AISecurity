package resilience

import "time"

// Built-in healing strategies per ТЗ §4.1.1.
// These are registered at startup via HealingEngine.RegisterStrategy().

// DefaultStrategies returns the 5 built-in healing strategies.
func DefaultStrategies() []HealingStrategy {
	return []HealingStrategy{
		RestartComponentStrategy(),
		RollbackConfigStrategy(),
		RecoverDatabaseStrategy(),
		RecoverRulesStrategy(),
		RecoverNetworkStrategy(),
	}
}

// RestartComponentStrategy handles component crashes and offline states.
// Trigger: component_offline OR component_critical, 2 consecutive failures within 5m.
// Actions: graceful_stop → clear_temp → start → verify → notify.
// Rollback: escalate to next strategy.
func RestartComponentStrategy() HealingStrategy {
	return HealingStrategy{
		ID:   "RESTART_COMPONENT",
		Name: "Component Restart",
		Trigger: TriggerCondition{
			Statuses:            []ComponentStatus{StatusOffline, StatusCritical},
			ConsecutiveFailures: 2,
			WithinWindow:        5 * time.Minute,
		},
		Actions: []Action{
			{Type: ActionGracefulStop, Timeout: 10 * time.Second, OnError: "continue"},
			{Type: ActionClearTempFiles, Timeout: 5 * time.Second, OnError: "continue"},
			{Type: ActionStartComponent, Timeout: 30 * time.Second, OnError: "abort"},
			{Type: ActionVerifyHealth, Timeout: 60 * time.Second, OnError: "abort"},
			{Type: ActionNotifySOC, Timeout: 5 * time.Second, OnError: "continue",
				Params: map[string]interface{}{
					"severity": "INFO",
					"message":  "Component restarted successfully",
				},
			},
		},
		Rollback: RollbackPlan{
			OnFailure: "escalate",
			Actions: []Action{
				{Type: ActionNotifyArchitect, Timeout: 5 * time.Second,
					Params: map[string]interface{}{
						"severity": "CRITICAL",
						"message":  "Component restart failed after max attempts",
					},
				},
			},
		},
		MaxAttempts: 3,
		Cooldown:    5 * time.Minute,
	}
}

// RollbackConfigStrategy handles config tampering or validation failures.
// Trigger: config_tampering_detected OR config_validation_failed.
// Actions: freeze → verify_backup → rollback → restart → verify → notify.
func RollbackConfigStrategy() HealingStrategy {
	return HealingStrategy{
		ID:   "ROLLBACK_CONFIG",
		Name: "Configuration Rollback",
		Trigger: TriggerCondition{
			Metrics: []string{"config_tampering", "config_validation"},
		},
		Actions: []Action{
			{Type: ActionFreezeConfig, Timeout: 5 * time.Second, OnError: "abort"},
			{Type: ActionRollbackConfig, Timeout: 15 * time.Second, OnError: "abort"},
			{Type: ActionStartComponent, Timeout: 30 * time.Second, OnError: "rollback"},
			{Type: ActionVerifyConfig, Timeout: 10 * time.Second, OnError: "abort"},
			{Type: ActionNotifyArchitect, Timeout: 5 * time.Second, OnError: "continue",
				Params: map[string]interface{}{
					"severity": "WARNING",
					"message":  "Config rolled back due to tampering",
				},
			},
		},
		Rollback: RollbackPlan{
			OnFailure: "enter_safe_mode",
			Actions: []Action{
				{Type: ActionEnterSafeMode, Timeout: 10 * time.Second},
			},
		},
		MaxAttempts: 1,
		Cooldown:    1 * time.Hour,
	}
}

// RecoverDatabaseStrategy handles SQLite corruption.
// Trigger: database_corruption OR sqlite_integrity_failed.
// Actions: readonly → backup → restore → verify → resume → notify.
func RecoverDatabaseStrategy() HealingStrategy {
	return HealingStrategy{
		ID:   "RECOVER_DATABASE",
		Name: "Database Recovery",
		Trigger: TriggerCondition{
			Metrics: []string{"database_corruption", "sqlite_integrity"},
		},
		Actions: []Action{
			{Type: ActionSwitchReadOnly, Timeout: 5 * time.Second, OnError: "abort"},
			{Type: ActionBackupDB, Timeout: 30 * time.Second, OnError: "continue"},
			{Type: ActionRestoreSnapshot, Timeout: 60 * time.Second, OnError: "abort",
				Params: map[string]interface{}{
					"snapshot_age_max": "1h",
				},
			},
			{Type: ActionVerifyIntegrity, Timeout: 30 * time.Second, OnError: "abort"},
			{Type: ActionResumeWrites, Timeout: 5 * time.Second, OnError: "abort"},
			{Type: ActionNotifySOC, Timeout: 5 * time.Second, OnError: "continue",
				Params: map[string]interface{}{
					"severity": "WARNING",
					"message":  "Database recovered from snapshot",
				},
			},
		},
		Rollback: RollbackPlan{
			OnFailure: "enter_lockdown",
			Actions: []Action{
				{Type: ActionEnterSafeMode, Timeout: 10 * time.Second},
				{Type: ActionNotifyArchitect, Timeout: 5 * time.Second,
					Params: map[string]interface{}{
						"severity": "CRITICAL",
						"message":  "Database recovery failed",
					},
				},
			},
		},
		MaxAttempts: 2,
		Cooldown:    2 * time.Hour,
	}
}

// RecoverRulesStrategy handles correlation rule poisoning.
// Trigger: rule execution failure rate > 50%.
// Actions: disable_suspicious → revert_baseline → verify → reload → notify.
func RecoverRulesStrategy() HealingStrategy {
	return HealingStrategy{
		ID:   "RECOVER_RULES",
		Name: "Rule Poisoning Defense",
		Trigger: TriggerCondition{
			Metrics: []string{"rule_execution_failure_rate", "correlation_rule_anomaly"},
		},
		Actions: []Action{
			{Type: ActionDisableRules, Timeout: 10 * time.Second, OnError: "abort",
				Params: map[string]interface{}{
					"criteria": "failure_rate > 80%",
				},
			},
			{Type: ActionRevertRules, Timeout: 15 * time.Second, OnError: "abort"},
			{Type: ActionReloadEngine, Timeout: 30 * time.Second, OnError: "abort"},
			{Type: ActionVerifyHealth, Timeout: 30 * time.Second, OnError: "continue"},
			{Type: ActionNotifyArchitect, Timeout: 5 * time.Second, OnError: "continue",
				Params: map[string]interface{}{
					"severity": "WARNING",
					"message":  "Rules recovered from baseline",
				},
			},
		},
		Rollback: RollbackPlan{
			OnFailure: "disable_correlation",
		},
		MaxAttempts: 2,
		Cooldown:    4 * time.Hour,
	}
}

// RecoverNetworkStrategy handles network partition or mTLS cert expiry.
// Trigger: network_partition_detected OR mTLS_cert_expired.
// Actions: isolate → regen_certs → verify → restore → notify.
func RecoverNetworkStrategy() HealingStrategy {
	return HealingStrategy{
		ID:   "RECOVER_NETWORK",
		Name: "Network Isolation Recovery",
		Trigger: TriggerCondition{
			Metrics: []string{"network_partition", "mtls_cert_expiry"},
		},
		Actions: []Action{
			{Type: ActionIsolateNetwork, Timeout: 5 * time.Second, OnError: "abort",
				Params: map[string]interface{}{
					"scope": "external_only",
				},
			},
			{Type: ActionRegenCerts, Timeout: 30 * time.Second, OnError: "abort",
				Params: map[string]interface{}{
					"validity": "24h",
				},
			},
			{Type: ActionVerifyHealth, Timeout: 30 * time.Second, OnError: "rollback"},
			{Type: ActionRestoreNetwork, Timeout: 10 * time.Second, OnError: "abort"},
			{Type: ActionNotifySOC, Timeout: 5 * time.Second, OnError: "continue",
				Params: map[string]interface{}{
					"severity": "INFO",
					"message":  "Network connectivity restored",
				},
			},
		},
		Rollback: RollbackPlan{
			OnFailure: "maintain_isolation",
			Actions: []Action{
				{Type: ActionNotifyArchitect, Timeout: 5 * time.Second,
					Params: map[string]interface{}{
						"severity": "CRITICAL",
						"message":  "Network recovery failed, maintaining isolation",
					},
				},
			},
		},
		MaxAttempts: 3,
		Cooldown:    1 * time.Hour,
	}
}
