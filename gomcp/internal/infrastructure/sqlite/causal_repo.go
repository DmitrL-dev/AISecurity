package sqlite

import (
	"context"
	"fmt"
	"time"

	"github.com/syntrex/gomcp/internal/domain/causal"
	rlmscope "github.com/syntrex/gomcp/internal/domain/scope"
)

// CausalRepo implements causal.CausalStore using SQLite.
// Compatible with causal_chains.db schema.
type CausalRepo struct {
	db *DB
}

// NewCausalRepo creates a CausalRepo and ensures the schema exists.
func NewCausalRepo(db *DB) (*CausalRepo, error) {
	repo := &CausalRepo{db: db}
	if err := repo.migrate(); err != nil {
		return nil, fmt.Errorf("causal repo migrate: %w", err)
	}
	return repo, nil
}

func (r *CausalRepo) migrate() error {
	stmts := []string{
		`CREATE TABLE IF NOT EXISTS causal_nodes (
			id TEXT PRIMARY KEY,
			tenant_id TEXT NOT NULL DEFAULT 'local',
			project_id TEXT NOT NULL DEFAULT 'default',
			node_type TEXT NOT NULL,
			content TEXT NOT NULL,
			created_at TEXT DEFAULT CURRENT_TIMESTAMP,
			session_id TEXT,
			metadata TEXT DEFAULT '{}'
		)`,
		`CREATE TABLE IF NOT EXISTS causal_edges (
			tenant_id TEXT NOT NULL DEFAULT 'local',
			project_id TEXT NOT NULL DEFAULT 'default',
			from_id TEXT NOT NULL,
			to_id TEXT NOT NULL,
			edge_type TEXT NOT NULL,
			strength REAL DEFAULT 1.0,
			created_at TEXT DEFAULT CURRENT_TIMESTAMP,
			PRIMARY KEY (from_id, to_id, edge_type),
			FOREIGN KEY (from_id) REFERENCES causal_nodes(id),
			FOREIGN KEY (to_id) REFERENCES causal_nodes(id)
		)`,
		`CREATE INDEX IF NOT EXISTS idx_nodes_scope_type ON causal_nodes(tenant_id, project_id, node_type)`,
		`CREATE INDEX IF NOT EXISTS idx_edges_scope_from ON causal_edges(tenant_id, project_id, from_id)`,
		`CREATE INDEX IF NOT EXISTS idx_edges_scope_to ON causal_edges(tenant_id, project_id, to_id)`,
		`CREATE INDEX IF NOT EXISTS idx_nodes_type ON causal_nodes(node_type)`,
		`CREATE INDEX IF NOT EXISTS idx_nodes_session ON causal_nodes(session_id)`,
		`CREATE INDEX IF NOT EXISTS idx_edges_from ON causal_edges(from_id)`,
		`CREATE INDEX IF NOT EXISTS idx_edges_to ON causal_edges(to_id)`,
	}
	for _, s := range stmts {
		if _, err := r.db.Exec(s); err != nil {
			return fmt.Errorf("exec migration: %w", err)
		}
	}
	_, _ = r.db.Exec(`ALTER TABLE causal_nodes ADD COLUMN tenant_id TEXT NOT NULL DEFAULT 'local'`)
	_, _ = r.db.Exec(`ALTER TABLE causal_nodes ADD COLUMN project_id TEXT NOT NULL DEFAULT 'default'`)
	_, _ = r.db.Exec(`ALTER TABLE causal_edges ADD COLUMN tenant_id TEXT NOT NULL DEFAULT 'local'`)
	_, _ = r.db.Exec(`ALTER TABLE causal_edges ADD COLUMN project_id TEXT NOT NULL DEFAULT 'default'`)
	return nil
}

// AddNode inserts a causal node.
func (r *CausalRepo) AddNode(ctx context.Context, node *causal.Node) error {
	sc := rlmscope.FromContext(ctx)
	node.TenantID = sc.TenantID
	node.ProjectID = sc.ProjectID
	if err := node.Validate(); err != nil {
		return fmt.Errorf("validate node: %w", err)
	}
	_, err := r.db.Exec(`INSERT INTO causal_nodes (id, tenant_id, project_id, node_type, content, created_at)
		VALUES (?, ?, ?, ?, ?, ?)`,
		node.ID, node.TenantID, node.ProjectID, string(node.Type), node.Content, node.CreatedAt.Format(timeFormat),
	)
	if err != nil {
		return fmt.Errorf("insert node: %w", err)
	}
	return nil
}

// AddEdge inserts a causal edge.
func (r *CausalRepo) AddEdge(ctx context.Context, edge *causal.Edge) error {
	sc := rlmscope.FromContext(ctx)
	edge.TenantID = sc.TenantID
	edge.ProjectID = sc.ProjectID
	if err := edge.Validate(); err != nil {
		return fmt.Errorf("validate edge: %w", err)
	}
	if err := r.ensureNodesInScope(sc, edge.FromID, edge.ToID); err != nil {
		return err
	}
	_, err := r.db.Exec(`INSERT INTO causal_edges (tenant_id, project_id, from_id, to_id, edge_type)
		VALUES (?, ?, ?, ?, ?)`,
		edge.TenantID, edge.ProjectID, edge.FromID, edge.ToID, string(edge.Type),
	)
	if err != nil {
		return fmt.Errorf("insert edge: %w", err)
	}
	return nil
}

func (r *CausalRepo) ensureNodesInScope(sc rlmscope.Scope, ids ...string) error {
	for _, id := range ids {
		var count int
		if err := r.db.QueryRow(`SELECT COUNT(*) FROM causal_nodes
			WHERE id = ? AND tenant_id = ? AND project_id = ?`,
			id, sc.TenantID, sc.ProjectID,
		).Scan(&count); err != nil {
			return fmt.Errorf("check causal node scope: %w", err)
		}
		if count == 0 {
			return fmt.Errorf("causal node %s not found in scope %s", id, sc.String())
		}
	}
	return nil
}

// GetChain builds a causal chain around a decision node matching the query.
func (r *CausalRepo) GetChain(ctx context.Context, query string, maxDepth int) (*causal.Chain, error) {
	sc := rlmscope.FromContext(ctx)
	chain := &causal.Chain{}

	// Find decision node matching query.
	row := r.db.QueryRow(`SELECT id, tenant_id, project_id, node_type, content, created_at
		FROM causal_nodes
		WHERE tenant_id = ? AND project_id = ? AND node_type = 'decision' AND content LIKE ?
		LIMIT 1`,
		sc.TenantID, sc.ProjectID, "%"+query+"%")

	var id, tenantID, projectID, nodeType, content, createdAt string
	err := row.Scan(&id, &tenantID, &projectID, &nodeType, &content, &createdAt)
	if err != nil {
		// No decision found — return empty chain.
		return chain, nil
	}

	t, _ := time.Parse(timeFormat, createdAt)
	chain.Decision = &causal.Node{
		ID: id, TenantID: tenantID, ProjectID: projectID,
		Type: causal.NodeType(nodeType), Content: content, CreatedAt: t,
	}
	chain.TotalNodes = 1

	// Find all connected nodes via edges.
	// Incoming edges (nodes that point TO the decision).
	inRows, err := r.db.Query(`SELECT n.id, n.tenant_id, n.project_id, n.node_type, n.content, n.created_at, e.edge_type
		FROM causal_edges e JOIN causal_nodes n ON e.from_id = n.id
		WHERE e.tenant_id = ? AND e.project_id = ?
		  AND n.tenant_id = ? AND n.project_id = ?
		  AND e.to_id = ?`,
		sc.TenantID, sc.ProjectID, sc.TenantID, sc.ProjectID, id)
	if err != nil {
		return nil, fmt.Errorf("query incoming edges: %w", err)
	}
	defer inRows.Close()

	for inRows.Next() {
		var nid, nTenant, nProject, nt, nc, nca, et string
		if err := inRows.Scan(&nid, &nTenant, &nProject, &nt, &nc, &nca, &et); err != nil {
			return nil, fmt.Errorf("scan incoming: %w", err)
		}
		tt, _ := time.Parse(timeFormat, nca)
		node := &causal.Node{
			ID: nid, TenantID: nTenant, ProjectID: nProject,
			Type: causal.NodeType(nt), Content: nc, CreatedAt: tt,
		}
		chain.TotalNodes++

		switch causal.EdgeType(et) {
		case causal.EdgeJustifies:
			chain.Reasons = append(chain.Reasons, node)
		case causal.EdgeConstrains:
			chain.Constraints = append(chain.Constraints, node)
		default:
			// Classify by node type if edge type doesn't match.
			switch causal.NodeType(nt) {
			case causal.NodeAlternative:
				chain.Alternatives = append(chain.Alternatives, node)
			case causal.NodeReason:
				chain.Reasons = append(chain.Reasons, node)
			case causal.NodeConstraint:
				chain.Constraints = append(chain.Constraints, node)
			}
		}
	}
	if err := inRows.Err(); err != nil {
		return nil, err
	}

	// Outgoing edges (nodes that the decision points TO).
	outRows, err := r.db.Query(`SELECT n.id, n.tenant_id, n.project_id, n.node_type, n.content, n.created_at, e.edge_type
		FROM causal_edges e JOIN causal_nodes n ON e.to_id = n.id
		WHERE e.tenant_id = ? AND e.project_id = ?
		  AND n.tenant_id = ? AND n.project_id = ?
		  AND e.from_id = ?`,
		sc.TenantID, sc.ProjectID, sc.TenantID, sc.ProjectID, id)
	if err != nil {
		return nil, fmt.Errorf("query outgoing edges: %w", err)
	}
	defer outRows.Close()

	for outRows.Next() {
		var nid, nTenant, nProject, nt, nc, nca, et string
		if err := outRows.Scan(&nid, &nTenant, &nProject, &nt, &nc, &nca, &et); err != nil {
			return nil, fmt.Errorf("scan outgoing: %w", err)
		}
		tt, _ := time.Parse(timeFormat, nca)
		node := &causal.Node{
			ID: nid, TenantID: nTenant, ProjectID: nProject,
			Type: causal.NodeType(nt), Content: nc, CreatedAt: tt,
		}
		chain.TotalNodes++

		switch causal.EdgeType(et) {
		case causal.EdgeCauses:
			chain.Consequences = append(chain.Consequences, node)
		default:
			switch causal.NodeType(nt) {
			case causal.NodeConsequence:
				chain.Consequences = append(chain.Consequences, node)
			case causal.NodeAlternative:
				chain.Alternatives = append(chain.Alternatives, node)
			}
		}
	}
	if err := outRows.Err(); err != nil {
		return nil, err
	}

	return chain, nil
}

// Stats returns aggregate statistics about the causal store.
func (r *CausalRepo) Stats(ctx context.Context) (*causal.CausalStats, error) {
	sc := rlmscope.FromContext(ctx)
	stats := &causal.CausalStats{
		ByType: make(map[causal.NodeType]int),
	}

	row := r.db.QueryRow(`SELECT COUNT(*) FROM causal_nodes WHERE tenant_id = ? AND project_id = ?`,
		sc.TenantID, sc.ProjectID)
	if err := row.Scan(&stats.TotalNodes); err != nil {
		return nil, err
	}

	row = r.db.QueryRow(`SELECT COUNT(*) FROM causal_edges WHERE tenant_id = ? AND project_id = ?`,
		sc.TenantID, sc.ProjectID)
	if err := row.Scan(&stats.TotalEdges); err != nil {
		return nil, err
	}

	rows, err := r.db.Query(`SELECT node_type, COUNT(*) FROM causal_nodes
		WHERE tenant_id = ? AND project_id = ? GROUP BY node_type`,
		sc.TenantID, sc.ProjectID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	for rows.Next() {
		var nt string
		var count int
		if err := rows.Scan(&nt, &count); err != nil {
			return nil, err
		}
		stats.ByType[causal.NodeType(nt)] = count
	}
	return stats, rows.Err()
}

// Ensure CausalRepo implements causal.CausalStore.
var _ causal.CausalStore = (*CausalRepo)(nil)
