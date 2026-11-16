package sqlite

import (
	"context"
	"database/sql"
	"fmt"

	"github.com/syntrex/gomcp/internal/domain/memory"
	rlmscope "github.com/syntrex/gomcp/internal/domain/scope"
)

const factPageStoredCreatedAtHardMaxBytes int64 = 128

type factPageMeasurement struct {
	rowCount         int64
	totalStoredBytes int64
}

// factPageCurrentScopePreflightTx runs before an initial snapshot high-water is
// captured. That ordering matters for a corrupt oversized id: even joining the
// export-sequence table on that id can cross SQLite's length limit before a
// later row scan gets a chance to reject it.
func factPageCurrentScopePreflightTx(
	ctx context.Context,
	tx *sql.Tx,
	sc rlmscope.Scope,
	level memory.HierLevel,
	maxStoredRowBytes int64,
) (factPageMeasurement, error) {
	return factPageMeasureTx(ctx, tx, "", `FROM hierarchical_facts
		WHERE hierarchical_facts.tenant_id COLLATE BINARY = ?
		  AND hierarchical_facts.project_id COLLATE BINARY = ?
		  AND hierarchical_facts.level = ?
		  AND (hierarchical_facts.session_id IS NULL OR hierarchical_facts.session_id COLLATE BINARY = '')`,
		maxStoredRowBytes, sc.TenantID, sc.ProjectID, int(level),
	)
}

// factPageExactRowPreflightTx proves that one immutable manifest item still
// names the same exact scope/key/export-sequence row before either factColumns
// or cached canonical bytes are used.
func factPageExactRowPreflightTx(
	ctx context.Context,
	tx *sql.Tx,
	sc rlmscope.Scope,
	level memory.HierLevel,
	maxStoredRowBytes int64,
	key memory.FactPageKey,
) error {
	measurement, err := factPageMeasureTx(ctx, tx, "", `FROM fact_export_sequence AS export_seq
	JOIN hierarchical_facts
	  ON hierarchical_facts.id COLLATE BINARY = export_seq.fact_id COLLATE BINARY
	WHERE export_seq.seq = ?
	  AND export_seq.fact_id COLLATE BINARY = ?
	  AND hierarchical_facts.tenant_id COLLATE BINARY = ?
	  AND hierarchical_facts.project_id COLLATE BINARY = ?
	  AND hierarchical_facts.level = ?
	  AND hierarchical_facts.created_at COLLATE BINARY = ?
	  AND hierarchical_facts.id COLLATE BINARY = ?
	  AND (hierarchical_facts.session_id IS NULL OR hierarchical_facts.session_id COLLATE BINARY = '')`,
		maxStoredRowBytes, key.Sequence, key.ID, sc.TenantID, sc.ProjectID,
		int(level), key.CreatedAt, key.ID,
	)
	if err != nil {
		return err
	}
	if measurement.rowCount != 1 {
		return memory.ErrFactPageChanged
	}
	return nil
}

// factPageMeasureTx uses octet_length, which reads TEXT/BLOB sizes from SQLite
// record metadata. Do not replace it with length(cast(... AS blob)).
func factPageMeasureTx(
	ctx context.Context,
	tx *sql.Tx,
	cteSQL string,
	selectionSQL string,
	maxStoredRowBytes int64,
	args ...any,
) (factPageMeasurement, error) {
	var rowCount, maxIDBytes, maxCreatedAtBytes, maxRowBytes, totalBytes int64
	err := tx.QueryRowContext(ctx, `WITH `+cteSQL+`measured AS (
		SELECT octet_length(hierarchical_facts.id) AS id_bytes,
			octet_length(hierarchical_facts.created_at) AS created_at_bytes,
			`+boundedSearchStoredVariableBytesSQL+` AS stored_variable_bytes
		`+selectionSQL+`
	)
	SELECT COUNT(*), COALESCE(MAX(id_bytes), 0),
		COALESCE(MAX(created_at_bytes), 0),
		COALESCE(MAX(stored_variable_bytes), 0),
		COALESCE(SUM(stored_variable_bytes), 0)
	FROM measured`, args...).Scan(
		&rowCount, &maxIDBytes, &maxCreatedAtBytes, &maxRowBytes, &totalBytes,
	)
	if err != nil {
		return factPageMeasurement{}, fmt.Errorf("preflight exact fact page snapshot: %w", err)
	}
	if maxIDBytes > boundedSearchStoredFactIDHardMaxBytes {
		return factPageMeasurement{}, factPageStoredOversize(
			memory.BoundedSearchStoredIdentityOversizeKind,
			maxIDBytes,
			boundedSearchStoredFactIDHardMaxBytes,
		)
	}
	if maxCreatedAtBytes > factPageStoredCreatedAtHardMaxBytes {
		return factPageMeasurement{}, factPageStoredOversize(
			memory.BoundedSearchStoredIdentityOversizeKind,
			maxCreatedAtBytes,
			factPageStoredCreatedAtHardMaxBytes,
		)
	}
	if maxRowBytes > maxStoredRowBytes {
		return factPageMeasurement{}, factPageStoredOversize(
			memory.BoundedSearchStoredRowOversizeKind,
			maxRowBytes,
			maxStoredRowBytes,
		)
	}
	if totalBytes > boundedSearchStoredSnapshotHardMaxBytes {
		return factPageMeasurement{}, factPageStoredOversize(
			memory.BoundedSearchStoredScopeOversizeKind,
			totalBytes,
			boundedSearchStoredSnapshotHardMaxBytes,
		)
	}
	if rowCount > boundedSearchStoredSnapshotHardMaxRows {
		return factPageMeasurement{}, &memory.FactPageStoredOversizeError{
			Measurement: memory.BoundedSearchStoredOversize{
				Kind:          memory.BoundedSearchStoredRowCountOversizeKind,
				StoredRows:    rowCount,
				MaxStoredRows: boundedSearchStoredSnapshotHardMaxRows,
			},
		}
	}
	return factPageMeasurement{rowCount: rowCount, totalStoredBytes: totalBytes}, nil
}

func factPageStoredOversize(kind string, storedBytes, maxStoredBytes int64) error {
	return &memory.FactPageStoredOversizeError{
		Measurement: memory.BoundedSearchStoredOversize{
			Kind:           kind,
			StoredBytes:    storedBytes,
			MaxStoredBytes: maxStoredBytes,
		},
	}
}
