package sqlite

import (
	"context"
	"database/sql"
	"errors"
	"fmt"
	"time"

	"github.com/syntrex/gomcp/internal/domain/causal"
	rlmscope "github.com/syntrex/gomcp/internal/domain/scope"
)

const (
	boundedCausalJSONWorstCaseExpansion  int64 = 6
	boundedCausalDualRenderExpansion     int64 = 12
	boundedCausalFixedReserveBytes       int64 = 512
	boundedCausalPerNodeReserveBytes     int64 = 256
	boundedCausalStoredRowHardMaxBytes   int64 = 16 * 1024 * 1024
	boundedCausalStoredScopeHardMaxBytes int64 = 32 * 1024 * 1024
)

const boundedCausalStoredNodeBytesSQL = `
	COALESCE(octet_length(id), 0)
	+ COALESCE(octet_length(tenant_id), 0)
	+ COALESCE(octet_length(project_id), 0)
	+ COALESCE(octet_length(node_type), 0)
	+ COALESCE(octet_length(content), 0)
	+ COALESCE(octet_length(created_at), 0)`

const boundedCausalStoredNeighbourBytesSQL = `
	COALESCE(octet_length(n.id), 0)
	+ COALESCE(octet_length(n.tenant_id), 0)
	+ COALESCE(octet_length(n.project_id), 0)
	+ COALESCE(octet_length(n.node_type), 0)
	+ COALESCE(octet_length(n.content), 0)
	+ COALESCE(octet_length(n.created_at), 0)
	+ COALESCE(octet_length(e.edge_type), 0)`

// The transport serializes each node once in chain JSON and renders content
// and IDs again in Mermaid before JSON-escaping that string. Six bytes per
// source byte covers encoding/json's worst-case escaping. Decision IDs also
// occur on every Mermaid edge, hence the maxNodes-dependent multiplier.
const boundedCausalDecisionResultUpperSQL = `
	COALESCE(octet_length(id), 0) * ? * ?
	+ COALESCE(octet_length(content), 0) * ?
	+ (
		COALESCE(octet_length(tenant_id), 0)
		+ COALESCE(octet_length(project_id), 0)
		+ COALESCE(octet_length(node_type), 0)
		+ COALESCE(octet_length(created_at), 0)
	) * ?`

const boundedCausalNeighbourResultUpperSQL = `
	(
		COALESCE(octet_length(n.id), 0)
		+ COALESCE(octet_length(n.content), 0)
	) * ?
	+ (
		COALESCE(octet_length(n.tenant_id), 0)
		+ COALESCE(octet_length(n.project_id), 0)
		+ COALESCE(octet_length(n.node_type), 0)
		+ COALESCE(octet_length(n.created_at), 0)
		+ COALESCE(octet_length(e.edge_type), 0)
	) * ?`

type boundedCausalLinkKey struct {
	nodeRowID int64
	edgeRowID int64
	direction int
}

// GetChainBounded preserves direct-neighbour semantics while proving, from
// SQLite record metadata, that every value selected into Go fits the caller's
// wire budget. Preflight, identity selection, and materialization share one
// read transaction.
func (r *CausalRepo) GetChainBounded(
	ctx context.Context,
	query string,
	maxDepth, maxNodes, maxResultBytes int,
) (*causal.Chain, error) {
	if maxDepth != causal.BoundedCausalMaxDepth ||
		maxNodes < 1 || maxNodes > causal.BoundedCausalMaxNodes ||
		maxResultBytes < 1 || maxResultBytes > causal.BoundedCausalMaxResultBytes {
		return nil, fmt.Errorf("invalid bounded causal limits")
	}
	sc, err := rlmscope.RequireExactDefault(ctx)
	if err != nil {
		return nil, err
	}
	tx, err := r.db.SqlDB().BeginTx(ctx, &sql.TxOptions{ReadOnly: true})
	if err != nil {
		return nil, fmt.Errorf("begin bounded causal snapshot: %w", err)
	}
	defer func() { _ = tx.Rollback() }()

	if err := preflightBoundedCausalDecisionCandidates(ctx, tx, sc); err != nil {
		return nil, err
	}

	chain := &causal.Chain{}
	var decisionRowID int64
	err = tx.QueryRowContext(ctx, `SELECT rowid
		FROM causal_nodes
		WHERE tenant_id COLLATE BINARY = ?
		  AND project_id COLLATE BINARY = ?
		  AND node_type COLLATE BINARY = 'decision'
		  AND content LIKE ?
		ORDER BY rowid
		LIMIT 1`, sc.TenantID, sc.ProjectID, "%"+query+"%").Scan(&decisionRowID)
	if errors.Is(err, sql.ErrNoRows) {
		if err := tx.Commit(); err != nil {
			return nil, fmt.Errorf("commit bounded causal snapshot: %w", err)
		}
		return chain, nil
	}
	if err != nil {
		return nil, fmt.Errorf("query bounded causal decision identity: %w", err)
	}

	// Reject an oversized decision before its ID is used for edge lookup or
	// selected into Go. This metadata-only pass also covers the no-edge case.
	if err := preflightBoundedCausalSelection(
		ctx, tx, sc, decisionRowID, nil, maxNodes, maxResultBytes,
	); err != nil {
		return nil, err
	}
	if err := preflightBoundedCausalNeighbourCandidates(ctx, tx, sc, decisionRowID); err != nil {
		return nil, err
	}
	links, err := selectBoundedCausalLinkKeys(ctx, tx, sc, decisionRowID, maxNodes)
	if err != nil {
		return nil, err
	}
	if len(links) >= maxNodes {
		return nil, causal.ErrCausalChainTooLarge
	}
	if err := preflightBoundedCausalSelection(
		ctx, tx, sc, decisionRowID, links, maxNodes, maxResultBytes,
	); err != nil {
		return nil, err
	}

	var decisionID, tenantID, projectID, nodeType, content, createdAt string
	err = tx.QueryRowContext(ctx, `SELECT id, tenant_id, project_id, node_type, content, created_at
		FROM causal_nodes
		WHERE rowid = ?
		  AND tenant_id COLLATE BINARY = ?
		  AND project_id COLLATE BINARY = ?
		  AND node_type COLLATE BINARY = 'decision'`,
		decisionRowID, sc.TenantID, sc.ProjectID).Scan(
		&decisionID, &tenantID, &projectID, &nodeType, &content, &createdAt,
	)
	if err != nil {
		return nil, fmt.Errorf("load bounded causal decision: %w", err)
	}
	created, _ := time.Parse(timeFormat, createdAt)
	chain.Decision = &causal.Node{
		ID: decisionID, TenantID: tenantID, ProjectID: projectID,
		Type: causal.NodeType(nodeType), Content: content, CreatedAt: created,
	}
	chain.TotalNodes = 1

	for _, link := range links {
		var nid, nTenant, nProject, nt, nc, nca, edgeType string
		err := tx.QueryRowContext(ctx, `SELECT n.id, n.tenant_id, n.project_id,
			n.node_type, n.content, n.created_at, e.edge_type
		FROM causal_nodes n
		JOIN causal_edges e ON e.rowid = ?
		WHERE n.rowid = ?
		  AND n.tenant_id COLLATE BINARY = ?
		  AND n.project_id COLLATE BINARY = ?
		  AND e.tenant_id COLLATE BINARY = ?
		  AND e.project_id COLLATE BINARY = ?`,
			link.edgeRowID, link.nodeRowID,
			sc.TenantID, sc.ProjectID, sc.TenantID, sc.ProjectID,
		).Scan(&nid, &nTenant, &nProject, &nt, &nc, &nca, &edgeType)
		if err != nil {
			return nil, fmt.Errorf("load bounded causal neighbour: %w", err)
		}
		timestamp, _ := time.Parse(timeFormat, nca)
		node := &causal.Node{
			ID: nid, TenantID: nTenant, ProjectID: nProject,
			Type: causal.NodeType(nt), Content: nc, CreatedAt: timestamp,
		}
		chain.TotalNodes++
		appendBoundedCausalNeighbour(chain, node, causal.EdgeType(edgeType), link.direction)
	}
	if err := tx.Commit(); err != nil {
		return nil, fmt.Errorf("commit bounded causal snapshot: %w", err)
	}
	return chain, nil
}

func boundedCausalReserve(maxNodes int) int64 {
	return boundedCausalFixedReserveBytes + boundedCausalPerNodeReserveBytes*int64(maxNodes)
}

func boundedCausalDecisionUpperArgs(maxNodes int) []any {
	return []any{
		boundedCausalJSONWorstCaseExpansion,
		maxNodes + 1,
		boundedCausalDualRenderExpansion,
		boundedCausalJSONWorstCaseExpansion,
	}
}

func boundedCausalNeighbourUpperArgs() []any {
	return []any{
		boundedCausalDualRenderExpansion,
		boundedCausalJSONWorstCaseExpansion,
	}
}

func preflightBoundedCausalDecisionCandidates(
	ctx context.Context,
	tx *sql.Tx,
	sc rlmscope.Scope,
) error {
	var maxStoredRow, totalStored int64
	err := tx.QueryRowContext(ctx, `WITH measured AS (
		SELECT `+boundedCausalStoredNodeBytesSQL+` AS stored_bytes
		FROM causal_nodes
		WHERE tenant_id COLLATE BINARY = ?
		  AND project_id COLLATE BINARY = ?
		  AND node_type COLLATE BINARY = 'decision'
	)
	SELECT COALESCE(MAX(stored_bytes), 0), COALESCE(SUM(stored_bytes), 0)
	FROM measured`, sc.TenantID, sc.ProjectID).Scan(&maxStoredRow, &totalStored)
	if err != nil {
		return fmt.Errorf("preflight bounded causal decision candidates: %w", err)
	}
	return validateBoundedCausalStoredBytes(maxStoredRow, totalStored)
}

func validateBoundedCausalStoredBytes(maxRow, total int64) error {
	if maxRow > boundedCausalStoredRowHardMaxBytes {
		return &causal.StoredCausalOversizeError{
			Kind:        causal.StoredCausalNodeOversizeKind,
			Measurement: causal.StoredCausalBytesMeasurement,
			Measured:    maxRow,
			Maximum:     boundedCausalStoredRowHardMaxBytes,
		}
	}
	if total > boundedCausalStoredScopeHardMaxBytes {
		return &causal.StoredCausalOversizeError{
			Kind:        causal.StoredCausalScopeOversizeKind,
			Measurement: causal.StoredCausalBytesMeasurement,
			Measured:    total,
			Maximum:     boundedCausalStoredScopeHardMaxBytes,
		}
	}
	return nil
}

func preflightBoundedCausalNeighbourCandidates(
	ctx context.Context,
	tx *sql.Tx,
	sc rlmscope.Scope,
	decisionRowID int64,
) error {
	var maxStoredRow, totalStored int64
	err := tx.QueryRowContext(ctx, `WITH decision AS (
		SELECT id
		FROM causal_nodes
		WHERE rowid = ?
		  AND tenant_id COLLATE BINARY = ?
		  AND project_id COLLATE BINARY = ?
		  AND node_type COLLATE BINARY = 'decision'
	), measured AS (
		SELECT `+boundedCausalStoredNeighbourBytesSQL+` AS stored_bytes
		FROM decision d
		JOIN causal_edges e ON e.to_id COLLATE BINARY = d.id COLLATE BINARY
		JOIN causal_nodes n ON n.id COLLATE BINARY = e.from_id COLLATE BINARY
		WHERE e.tenant_id COLLATE BINARY = ?
		  AND e.project_id COLLATE BINARY = ?
		  AND n.tenant_id COLLATE BINARY = ?
		  AND n.project_id COLLATE BINARY = ?
		UNION ALL
		SELECT `+boundedCausalStoredNeighbourBytesSQL+` AS stored_bytes
		FROM decision d
		JOIN causal_edges e ON e.from_id COLLATE BINARY = d.id COLLATE BINARY
		JOIN causal_nodes n ON n.id COLLATE BINARY = e.to_id COLLATE BINARY
		WHERE e.tenant_id COLLATE BINARY = ?
		  AND e.project_id COLLATE BINARY = ?
		  AND n.tenant_id COLLATE BINARY = ?
		  AND n.project_id COLLATE BINARY = ?
	)
	SELECT COALESCE(MAX(stored_bytes), 0), COALESCE(SUM(stored_bytes), 0)
	FROM measured`,
		decisionRowID, sc.TenantID, sc.ProjectID,
		sc.TenantID, sc.ProjectID, sc.TenantID, sc.ProjectID,
		sc.TenantID, sc.ProjectID, sc.TenantID, sc.ProjectID,
	).Scan(&maxStoredRow, &totalStored)
	if err != nil {
		return fmt.Errorf("preflight bounded causal neighbour candidates: %w", err)
	}
	return validateBoundedCausalStoredBytes(maxStoredRow, totalStored)
}

func selectBoundedCausalLinkKeys(
	ctx context.Context,
	tx *sql.Tx,
	sc rlmscope.Scope,
	decisionRowID int64,
	maxNodes int,
) ([]boundedCausalLinkKey, error) {
	rows, err := tx.QueryContext(ctx, `WITH decision AS (
		SELECT id
		FROM causal_nodes
		WHERE rowid = ?
		  AND tenant_id COLLATE BINARY = ?
		  AND project_id COLLATE BINARY = ?
		  AND node_type COLLATE BINARY = 'decision'
	), neighbours AS (
		SELECT n.rowid AS node_rowid, e.rowid AS edge_rowid, 0 AS direction,
			n.rowid AS sort_rowid
		FROM decision d
		JOIN causal_edges e ON e.to_id COLLATE BINARY = d.id COLLATE BINARY
		JOIN causal_nodes n ON n.id COLLATE BINARY = e.from_id COLLATE BINARY
		WHERE e.tenant_id COLLATE BINARY = ?
		  AND e.project_id COLLATE BINARY = ?
		  AND n.tenant_id COLLATE BINARY = ?
		  AND n.project_id COLLATE BINARY = ?
		UNION ALL
		SELECT n.rowid AS node_rowid, e.rowid AS edge_rowid, 1 AS direction,
			n.rowid AS sort_rowid
		FROM decision d
		JOIN causal_edges e ON e.from_id COLLATE BINARY = d.id COLLATE BINARY
		JOIN causal_nodes n ON n.id COLLATE BINARY = e.to_id COLLATE BINARY
		WHERE e.tenant_id COLLATE BINARY = ?
		  AND e.project_id COLLATE BINARY = ?
		  AND n.tenant_id COLLATE BINARY = ?
		  AND n.project_id COLLATE BINARY = ?
	)
	SELECT node_rowid, edge_rowid, direction
	FROM neighbours
	ORDER BY direction, sort_rowid, edge_rowid
	LIMIT ?`,
		decisionRowID, sc.TenantID, sc.ProjectID,
		sc.TenantID, sc.ProjectID, sc.TenantID, sc.ProjectID,
		sc.TenantID, sc.ProjectID, sc.TenantID, sc.ProjectID,
		maxNodes)
	if err != nil {
		return nil, fmt.Errorf("query bounded causal neighbour identities: %w", err)
	}
	defer rows.Close()
	links := make([]boundedCausalLinkKey, 0, maxNodes)
	for rows.Next() {
		var link boundedCausalLinkKey
		if err := rows.Scan(&link.nodeRowID, &link.edgeRowID, &link.direction); err != nil {
			return nil, fmt.Errorf("scan bounded causal neighbour identity: %w", err)
		}
		links = append(links, link)
	}
	if err := rows.Err(); err != nil {
		return nil, fmt.Errorf("iterate bounded causal neighbour identities: %w", err)
	}
	return links, nil
}

func preflightBoundedCausalSelection(
	ctx context.Context,
	tx *sql.Tx,
	sc rlmscope.Scope,
	decisionRowID int64,
	links []boundedCausalLinkKey,
	maxNodes, maxResultBytes int,
) error {
	var decisionUpper int64
	args := boundedCausalDecisionUpperArgs(maxNodes)
	args = append(args, decisionRowID, sc.TenantID, sc.ProjectID)
	err := tx.QueryRowContext(ctx, `SELECT `+boundedCausalDecisionResultUpperSQL+`
	FROM causal_nodes
	WHERE rowid = ?
	  AND tenant_id COLLATE BINARY = ?
	  AND project_id COLLATE BINARY = ?
	  AND node_type COLLATE BINARY = 'decision'`, args...).Scan(&decisionUpper)
	if err != nil {
		return fmt.Errorf("preflight bounded causal decision selection: %w", err)
	}
	if err := validateBoundedCausalNodeUpper(decisionUpper, maxNodes, maxResultBytes); err != nil {
		return err
	}
	totalUpper := decisionUpper
	for _, link := range links {
		var neighbourUpper int64
		args := boundedCausalNeighbourUpperArgs()
		args = append(args, link.edgeRowID, link.nodeRowID,
			sc.TenantID, sc.ProjectID, sc.TenantID, sc.ProjectID)
		err := tx.QueryRowContext(ctx, `SELECT `+boundedCausalNeighbourResultUpperSQL+`
		FROM causal_nodes n
		JOIN causal_edges e ON e.rowid = ?
		WHERE n.rowid = ?
		  AND n.tenant_id COLLATE BINARY = ?
		  AND n.project_id COLLATE BINARY = ?
		  AND e.tenant_id COLLATE BINARY = ?
		  AND e.project_id COLLATE BINARY = ?`,
			args...).Scan(&neighbourUpper)
		if err != nil {
			return fmt.Errorf("preflight bounded causal neighbour selection: %w", err)
		}
		if err := validateBoundedCausalNodeUpper(neighbourUpper, maxNodes, maxResultBytes); err != nil {
			return err
		}
		totalUpper += neighbourUpper
	}
	estimated := totalUpper + boundedCausalReserve(maxNodes)
	if estimated > int64(maxResultBytes) {
		return &causal.StoredCausalOversizeError{
			Kind:        causal.StoredCausalScopeOversizeKind,
			Measurement: causal.StoredCausalResultMeasurement,
			Measured:    estimated,
			Maximum:     int64(maxResultBytes),
		}
	}
	return nil
}

func validateBoundedCausalNodeUpper(nodeUpper int64, maxNodes, maxResultBytes int) error {
	estimated := nodeUpper + boundedCausalReserve(maxNodes)
	if nodeUpper > 0 && estimated > int64(maxResultBytes) {
		return &causal.StoredCausalOversizeError{
			Kind:        causal.StoredCausalNodeOversizeKind,
			Measurement: causal.StoredCausalResultMeasurement,
			Measured:    estimated,
			Maximum:     int64(maxResultBytes),
		}
	}
	return nil
}

func appendBoundedCausalNeighbour(
	chain *causal.Chain,
	node *causal.Node,
	edgeType causal.EdgeType,
	direction int,
) {
	if direction == 0 {
		switch edgeType {
		case causal.EdgeJustifies:
			chain.Reasons = append(chain.Reasons, node)
		case causal.EdgeConstrains:
			chain.Constraints = append(chain.Constraints, node)
		default:
			switch node.Type {
			case causal.NodeAlternative:
				chain.Alternatives = append(chain.Alternatives, node)
			case causal.NodeReason:
				chain.Reasons = append(chain.Reasons, node)
			case causal.NodeConstraint:
				chain.Constraints = append(chain.Constraints, node)
			}
		}
		return
	}
	switch edgeType {
	case causal.EdgeCauses:
		chain.Consequences = append(chain.Consequences, node)
	default:
		switch node.Type {
		case causal.NodeConsequence:
			chain.Consequences = append(chain.Consequences, node)
		case causal.NodeAlternative:
			chain.Alternatives = append(chain.Alternatives, node)
		}
	}
}
