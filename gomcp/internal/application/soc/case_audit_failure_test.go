package soc

import (
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
	domsoc "github.com/syntrex/gomcp/internal/domain/soc"
	"github.com/syntrex/gomcp/internal/infrastructure/audit"
)

func TestSOCIncidentMutationsRejectDecisionLogFailure(t *testing.T) {
	for _, op := range []string{"verdict", "assign", "status", "note"} {
		t.Run(op, func(t *testing.T) {
			base := newTestService(t)
			incident := domsoc.NewIncident("synthetic incident", domsoc.SeverityHigh, "synthetic-rule")
			incident.TenantID = "synthetic-tenant"
			require.NoError(t, base.repo.InsertIncident(incident))
			before, err := base.repo.GetIncident(incident.ID)
			require.NoError(t, err)
			logger, err := audit.NewDecisionLogger(t.TempDir())
			require.NoError(t, err)
			require.NoError(t, logger.Close())
			svc := NewService(base.repo, logger)
			switch op {
			case "verdict":
				err = svc.UpdateVerdict(incident.ID, domsoc.StatusInvestigating)
			case "assign":
				err = svc.AssignIncident(incident.ID, "synthetic-analyst")
			case "status":
				err = svc.ChangeIncidentStatus(incident.ID, domsoc.StatusInvestigating, "synthetic-actor")
			case "note":
				_, err = svc.AddIncidentNote(incident.ID, "synthetic-actor", "synthetic note")
			}
			assert.Error(t, err, "audit write failure must reject incident mutation")
			after, getErr := base.repo.GetIncident(incident.ID)
			require.NoError(t, getErr)
			assert.Equal(t, before, after, "failed decision audit must leave stored incident unchanged")
		})
	}
}

func TestSOCIncidentMutationsSucceedWhenDecisionLogAccepts(t *testing.T) {
	for _, op := range []string{"verdict", "assign", "status", "note"} {
		t.Run(op, func(t *testing.T) {
			base := newTestService(t)
			incident := domsoc.NewIncident("synthetic success", domsoc.SeverityHigh, "synthetic-rule")
			incident.TenantID = "synthetic-tenant"
			require.NoError(t, base.repo.InsertIncident(incident))
			logger, err := audit.NewDecisionLogger(t.TempDir())
			require.NoError(t, err)
			t.Cleanup(func() { _ = logger.Close() })
			svc := NewService(base.repo, logger)
			switch op {
			case "verdict":
				err = svc.UpdateVerdict(incident.ID, domsoc.StatusInvestigating)
			case "assign":
				err = svc.AssignIncident(incident.ID, "synthetic-analyst")
			case "status":
				err = svc.ChangeIncidentStatus(incident.ID, domsoc.StatusInvestigating, "synthetic-actor")
			case "note":
				_, err = svc.AddIncidentNote(incident.ID, "synthetic-actor", "synthetic note")
			}
			require.NoError(t, err)
			require.Equal(t, 1, logger.Count())
			stored, err := base.repo.GetIncident(incident.ID)
			require.NoError(t, err)
			switch op {
			case "verdict", "status":
				require.Equal(t, domsoc.StatusInvestigating, stored.Status)
			case "assign":
				require.Equal(t, "synthetic-analyst", stored.AssignedTo)
			case "note":
				require.Len(t, stored.Notes, 1)
			}
		})
	}
}
