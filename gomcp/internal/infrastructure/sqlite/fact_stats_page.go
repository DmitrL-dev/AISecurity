package sqlite

import (
	"context"
	"crypto/rand"
	"crypto/sha256"
	"database/sql"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"time"
	"unicode/utf8"

	"github.com/syntrex/gomcp/internal/domain/memory"
	rlmscope "github.com/syntrex/gomcp/internal/domain/scope"
)

func requireFactStatsPageScope(ctx context.Context) (rlmscope.Scope, error) {
	sc, err := rlmscope.Require(ctx)
	if err != nil {
		return rlmscope.Scope{}, err
	}
	if sc.IsDefault() {
		return sc, nil
	}
	return rlmscope.RequireExactProject(ctx)
}

// FactStatsPage materializes every aggregate once, then serves bounded wire
// segments from that immutable snapshot. Continuations never rescan facts,
// repeat GROUP BY/OFFSET work, or broaden beyond the exact binary scope.
func (r *FactRepo) FactStatsPage(
	ctx context.Context,
	position *memory.FactStatsPagePosition,
) (*memory.FactStatsPage, error) {
	sc, err := requireFactStatsPageScope(ctx)
	if err != nil {
		return nil, err
	}
	if position != nil {
		if err := validateFactStatsPagePosition(*position); err != nil {
			return nil, err
		}
		return r.readFactStatsSnapshotPage(ctx, sc, *position)
	}
	return r.createFactStatsSnapshotPage(ctx, sc)
}

func validateFactStatsPagePosition(position memory.FactStatsPagePosition) error {
	if !validFactStatsSnapshotID(position.SnapshotID) ||
		position.ExpectedRows <= 0 || position.ExpectedDomains <= 0 ||
		position.ExpectedDomains > position.ExpectedRows ||
		position.ExpectedDomains > memory.FactStatsPageMaxDomains ||
		position.ExpectedSegments <= 0 ||
		position.ExpectedSegments > memory.FactStatsPageMaxSnapshotSegments ||
		position.SerializedBytes <= 0 ||
		position.SerializedBytes > memory.FactStatsPageMaxSerializedDomainScopeBytes ||
		position.SegmentIndex < 0 || position.SegmentIndex >= position.ExpectedSegments ||
		position.SegmentOffset < 0 ||
		position.SegmentOffset >= memory.FactStatsPageFrameRawBytes {
		return fmt.Errorf("invalid fact stats page position")
	}
	return nil
}

func validFactStatsSnapshotID(value string) bool {
	if len(value) != memory.FactStatsPageSnapshotIDBytes*2 {
		return false
	}
	decoded, err := hex.DecodeString(value)
	return err == nil && len(decoded) == memory.FactStatsPageSnapshotIDBytes && value == hex.EncodeToString(decoded)
}

func newFactStatsSnapshotID() (string, error) {
	random := make([]byte, memory.FactStatsPageSnapshotIDBytes)
	if _, err := rand.Read(random); err != nil {
		return "", fmt.Errorf("generate fact stats snapshot identity: %w", err)
	}
	return hex.EncodeToString(random), nil
}

func (r *FactRepo) createFactStatsSnapshotPage(
	ctx context.Context,
	sc rlmscope.Scope,
) (*memory.FactStatsPage, error) {
	tx, err := r.db.SqlDB().BeginTx(ctx, nil)
	if err != nil {
		return nil, fmt.Errorf("begin exact fact stats snapshot: %w", err)
	}
	defer func() { _ = tx.Rollback() }()

	nowUnix := time.Now().Unix()
	if _, err := tx.ExecContext(ctx, `DELETE FROM fact_stats_page_snapshots
		WHERE expires_at_unix <= ?`, nowUnix); err != nil {
		return nil, fmt.Errorf("clean expired fact stats snapshots: %w", err)
	}
	usage, sameScope, err := factStatsActiveSnapshotUsageTx(ctx, tx, sc, nowUnix)
	if err != nil {
		return nil, err
	}
	if sameScope != 0 {
		return nil, &memory.FactStatsPageSnapshotBusy{}
	}
	if usage.ActiveSnapshots >= memory.FactStatsPageMaxActiveSnapshots ||
		usage.ActiveSerializedBytes > memory.FactStatsPageMaxActiveSnapshotBytes-memory.FactStatsPageMaxSerializedDomainScopeBytes ||
		usage.ActiveSegments > memory.FactStatsPageMaxActiveSnapshotSegments-memory.FactStatsPageMaxSnapshotSegments {
		return nil, usage.capacityError()
	}

	sourceHighWater, err := factStatsHighWaterTx(ctx, tx)
	if err != nil {
		return nil, err
	}
	expectedRows, err := factStatsEligibleCountTx(ctx, tx, sc, sourceHighWater)
	if err != nil {
		return nil, err
	}
	if err := factStatsStoredDomainPreflightTx(ctx, tx, sc, sourceHighWater); err != nil {
		return nil, err
	}
	expectedDomains, err := factStatsDomainCountTx(ctx, tx, sc, sourceHighWater)
	if err != nil {
		return nil, err
	}
	if expectedDomains > expectedRows {
		return nil, fmt.Errorf("fact stats domain count exceeds eligible row count")
	}
	fixed, err := fixedFactStatsTx(ctx, tx, sc, sourceHighWater)
	if err != nil {
		return nil, err
	}
	if int64(fixed.TotalFacts) != expectedRows {
		return nil, fmt.Errorf("fact stats fixed count does not match eligible rows")
	}
	if expectedDomains == 0 {
		if err := tx.Commit(); err != nil {
			return nil, fmt.Errorf("commit empty fact stats snapshot: %w", err)
		}
		return &memory.FactStatsPage{
			ExpectedRows: expectedRows,
			Fixed:        fixed,
			Done:         true,
		}, nil
	}

	entries, err := factStatsDomainsTx(ctx, tx, sc, sourceHighWater, expectedRows, expectedDomains)
	if err != nil {
		return nil, err
	}
	snapshotID, err := newFactStatsSnapshotID()
	if err != nil {
		return nil, err
	}
	if _, err := tx.ExecContext(ctx, `INSERT INTO fact_stats_page_snapshots (
		snapshot_id, tenant_id, project_id, expected_rows, expected_domains,
		expected_segments, serialized_bytes, expires_at_unix
	) VALUES (?, ?, ?, ?, ?, 1, 1, ?)`,
		snapshotID, sc.TenantID, sc.ProjectID, expectedRows, expectedDomains,
		nowUnix+memory.FactStatsPageSnapshotTTLSeconds); err != nil {
		return nil, fmt.Errorf("create exact fact stats snapshot: %w", err)
	}

	var segmentIndex, serializedBytes int64
	for ordinal, entry := range entries {
		encoded, err := json.Marshal(entry)
		if err != nil || len(encoded) == 0 {
			return nil, fmt.Errorf("encode exact fact stats domain")
		}
		if int64(len(encoded)) > memory.FactStatsPageMaxSerializedDomainBytes {
			return nil, &memory.FactStatsPageResultOversize{
				Kind:               memory.FactStatsPageDomainResultOversizeKind,
				SerializedBytes:    int64(len(encoded)),
				MaxSerializedBytes: memory.FactStatsPageMaxSerializedDomainBytes,
			}
		}
		if int64(len(encoded)) > memory.FactStatsPageMaxSerializedDomainScopeBytes-serializedBytes {
			return nil, &memory.FactStatsPageResultOversize{
				Kind:               memory.FactStatsPageScopeResultOversizeKind,
				SerializedBytes:    serializedBytes + int64(len(encoded)),
				MaxSerializedBytes: memory.FactStatsPageMaxSerializedDomainScopeBytes,
			}
		}
		serializedBytes += int64(len(encoded))
		digest := sha256.Sum256(encoded)
		digestHex := hex.EncodeToString(digest[:])
		for offset := 0; offset < len(encoded); offset += memory.FactStatsPageFrameRawBytes {
			end := offset + memory.FactStatsPageFrameRawBytes
			if end > len(encoded) {
				end = len(encoded)
			}
			if _, err := tx.ExecContext(ctx, `INSERT INTO fact_stats_page_snapshot_segments (
				snapshot_id, segment_index, ordinal, sha256, total_bytes,
				offset_bytes, data, is_final
			) VALUES (?, ?, ?, ?, ?, ?, ?, ?)`,
				snapshotID, segmentIndex, ordinal, digestHex, len(encoded),
				offset, encoded[offset:end], end == len(encoded)); err != nil {
				return nil, fmt.Errorf("store exact fact stats snapshot segment: %w", err)
			}
			segmentIndex++
		}
	}
	if segmentIndex <= 0 || segmentIndex > memory.FactStatsPageMaxSnapshotSegments {
		return nil, fmt.Errorf("invalid exact fact stats snapshot segment count")
	}
	if _, err := tx.ExecContext(ctx, `UPDATE fact_stats_page_snapshots
		SET expected_segments = ?, serialized_bytes = ?
		WHERE snapshot_id COLLATE BINARY = ?
		  AND tenant_id COLLATE BINARY = ? AND project_id COLLATE BINARY = ?`,
		segmentIndex, serializedBytes, snapshotID, sc.TenantID, sc.ProjectID); err != nil {
		return nil, fmt.Errorf("finalize exact fact stats snapshot: %w", err)
	}

	position := memory.FactStatsPagePosition{
		SnapshotID:       snapshotID,
		ExpectedRows:     expectedRows,
		ExpectedDomains:  expectedDomains,
		ExpectedSegments: segmentIndex,
		SerializedBytes:  serializedBytes,
	}
	page, err := factStatsSnapshotSegmentsTx(ctx, tx, sc, position)
	if err != nil {
		return nil, err
	}
	page.Fixed = fixed
	if page.Done {
		if _, err := tx.ExecContext(ctx, `DELETE FROM fact_stats_page_snapshots
			WHERE snapshot_id COLLATE BINARY = ?
			  AND tenant_id COLLATE BINARY = ? AND project_id COLLATE BINARY = ?`,
			snapshotID, sc.TenantID, sc.ProjectID); err != nil {
			return nil, fmt.Errorf("release completed fact stats snapshot: %w", err)
		}
	}
	if err := tx.Commit(); err != nil {
		return nil, fmt.Errorf("commit exact fact stats snapshot: %w", err)
	}
	return page, nil
}

func (r *FactRepo) readFactStatsSnapshotPage(
	ctx context.Context,
	sc rlmscope.Scope,
	position memory.FactStatsPagePosition,
) (*memory.FactStatsPage, error) {
	tx, err := r.db.SqlDB().BeginTx(ctx, nil)
	if err != nil {
		return nil, fmt.Errorf("begin exact fact stats continuation: %w", err)
	}
	defer func() { _ = tx.Rollback() }()

	var expectedRows, expectedDomains, expectedSegments, serializedBytes, expiresAt int64
	err = tx.QueryRowContext(ctx, `SELECT expected_rows, expected_domains,
		expected_segments, serialized_bytes, expires_at_unix
		FROM fact_stats_page_snapshots
		WHERE snapshot_id COLLATE BINARY = ?
		  AND tenant_id COLLATE BINARY = ? AND project_id COLLATE BINARY = ?`,
		position.SnapshotID, sc.TenantID, sc.ProjectID,
	).Scan(&expectedRows, &expectedDomains, &expectedSegments, &serializedBytes, &expiresAt)
	if errors.Is(err, sql.ErrNoRows) {
		return nil, memory.ErrFactStatsPageChanged
	}
	if err != nil {
		return nil, fmt.Errorf("read exact fact stats snapshot bounds: %w", err)
	}
	if expiresAt <= time.Now().Unix() || expectedRows != position.ExpectedRows ||
		expectedDomains != position.ExpectedDomains || expectedSegments != position.ExpectedSegments ||
		serializedBytes != position.SerializedBytes {
		return nil, memory.ErrFactStatsPageChanged
	}
	page, err := factStatsSnapshotSegmentsTx(ctx, tx, sc, position)
	if err != nil {
		return nil, err
	}
	if page.Done {
		if _, err := tx.ExecContext(ctx, `DELETE FROM fact_stats_page_snapshots
			WHERE snapshot_id COLLATE BINARY = ?
			  AND tenant_id COLLATE BINARY = ? AND project_id COLLATE BINARY = ?`,
			position.SnapshotID, sc.TenantID, sc.ProjectID); err != nil {
			return nil, fmt.Errorf("release completed fact stats continuation: %w", err)
		}
	}
	if err := tx.Commit(); err != nil {
		return nil, fmt.Errorf("commit exact fact stats continuation: %w", err)
	}
	return page, nil
}

func factStatsSnapshotSegmentsTx(
	ctx context.Context,
	tx *sql.Tx,
	sc rlmscope.Scope,
	position memory.FactStatsPagePosition,
) (*memory.FactStatsPage, error) {
	rows, err := tx.QueryContext(ctx, `SELECT segment_index, ordinal,
		CASE WHEN typeof(sha256) = 'text' AND octet_length(sha256) = 64
			THEN sha256 ELSE '' END,
		total_bytes, offset_bytes,
		substr(data, 1, ?), is_final
		FROM fact_stats_page_snapshot_segments
		WHERE snapshot_id COLLATE BINARY = ? AND segment_index >= ?
		ORDER BY segment_index ASC
		LIMIT ?`,
		memory.FactStatsPageFrameRawBytes+1, position.SnapshotID,
		position.SegmentIndex, memory.FactStatsPageMaxSegmentsPerPage+1)
	if err != nil {
		return nil, fmt.Errorf("query exact fact stats snapshot segments: %w", err)
	}
	defer rows.Close()

	page := &memory.FactStatsPage{
		SnapshotID:        position.SnapshotID,
		ExpectedRows:      position.ExpectedRows,
		ExpectedDomains:   position.ExpectedDomains,
		ExpectedSegments:  position.ExpectedSegments,
		SerializedBytes:   position.SerializedBytes,
		NextSegmentIndex:  position.SegmentIndex,
		NextSegmentOffset: position.SegmentOffset,
		Segments:          make([]memory.FactStatsDomainSegment, 0, 16),
	}
	rawBytes := 0
	for len(page.Segments) < memory.FactStatsPageMaxSegmentsPerPage &&
		rawBytes < memory.FactStatsPageFrameRawBytes && rows.Next() {
		var (
			segmentIndex, ordinal, totalBytes, storedOffset int64
			digest                                          string
			data                                            []byte
			final                                           bool
		)
		if err := rows.Scan(&segmentIndex, &ordinal, &digest, &totalBytes, &storedOffset, &data, &final); err != nil {
			return nil, fmt.Errorf("scan exact fact stats snapshot segment metadata: %w", err)
		}
		if segmentIndex != page.NextSegmentIndex || ordinal < 0 || ordinal >= position.ExpectedDomains ||
			len(digest) != sha256.Size*2 || digest != hex.EncodeToString(mustDecodeFactStatsDigest(digest)) ||
			totalBytes <= 0 || totalBytes > memory.FactStatsPageMaxSerializedDomainBytes ||
			storedOffset < 0 || storedOffset >= totalBytes || len(data) == 0 ||
			len(data) > memory.FactStatsPageFrameRawBytes ||
			storedOffset+int64(len(data)) > totalBytes ||
			final != (storedOffset+int64(len(data)) == totalBytes) {
			return nil, memory.ErrFactStatsPageChanged
		}
		localOffset := 0
		if segmentIndex == position.SegmentIndex {
			localOffset = position.SegmentOffset
		}
		if localOffset < 0 || localOffset >= len(data) {
			return nil, memory.ErrFactStatsPageChanged
		}
		remaining := memory.FactStatsPageFrameRawBytes - rawBytes
		take := len(data) - localOffset
		if take > remaining {
			take = remaining
		}
		pieceFinal := final && localOffset+take == len(data)
		page.Segments = append(page.Segments, memory.FactStatsDomainSegment{
			SegmentIndex: segmentIndex,
			Ordinal:      ordinal,
			SHA256:       digest,
			TotalBytes:   int(totalBytes),
			StoredOffset: int(storedOffset),
			StoredBytes:  len(data),
			LocalOffset:  localOffset,
			Offset:       int(storedOffset) + localOffset,
			Data:         append([]byte(nil), data[localOffset:localOffset+take]...),
			SegmentFinal: localOffset+take == len(data),
			Final:        pieceFinal,
		})
		rawBytes += take
		if localOffset+take < len(data) {
			page.NextSegmentOffset = localOffset + take
			break
		}
		page.NextSegmentIndex++
		page.NextSegmentOffset = 0
	}
	if err := rows.Err(); err != nil {
		return nil, fmt.Errorf("iterate exact fact stats snapshot segments: %w", err)
	}
	if len(page.Segments) == 0 {
		return nil, memory.ErrFactStatsPageChanged
	}
	page.Done = page.NextSegmentIndex == position.ExpectedSegments && page.NextSegmentOffset == 0
	if page.NextSegmentIndex > position.ExpectedSegments ||
		(page.Done && rawBytes <= 0) {
		return nil, memory.ErrFactStatsPageChanged
	}
	return page, nil
}

type factStatsActiveSnapshotUsage struct {
	ActiveSnapshots       int64
	ActiveSerializedBytes int64
	ActiveSegments        int64
}

func (u factStatsActiveSnapshotUsage) capacityError() *memory.FactStatsPageSnapshotCapacity {
	return &memory.FactStatsPageSnapshotCapacity{
		ActiveSnapshots:       u.ActiveSnapshots,
		MaxActiveSnapshots:    memory.FactStatsPageMaxActiveSnapshots,
		ActiveSerializedBytes: u.ActiveSerializedBytes,
		MaxSerializedBytes:    memory.FactStatsPageMaxActiveSnapshotBytes,
		ActiveSegments:        u.ActiveSegments,
		MaxActiveSegments:     memory.FactStatsPageMaxActiveSnapshotSegments,
	}
}

func factStatsActiveSnapshotUsageTx(
	ctx context.Context,
	tx *sql.Tx,
	sc rlmscope.Scope,
	nowUnix int64,
) (factStatsActiveSnapshotUsage, int64, error) {
	var usage factStatsActiveSnapshotUsage
	var sameScope int64
	err := tx.QueryRowContext(ctx, `SELECT COUNT(*),
		COALESCE(SUM(serialized_bytes), 0),
		COALESCE(SUM(expected_segments), 0),
		COALESCE(SUM(CASE
			WHEN tenant_id COLLATE BINARY = ? AND project_id COLLATE BINARY = ?
			THEN 1 ELSE 0 END), 0)
		FROM fact_stats_page_snapshots
		WHERE expires_at_unix > ?`, sc.TenantID, sc.ProjectID, nowUnix).Scan(
		&usage.ActiveSnapshots, &usage.ActiveSerializedBytes,
		&usage.ActiveSegments, &sameScope)
	if err != nil {
		return factStatsActiveSnapshotUsage{}, 0,
			fmt.Errorf("measure active fact stats snapshot capacity: %w", err)
	}
	if usage.ActiveSnapshots < 0 || usage.ActiveSerializedBytes < 0 || usage.ActiveSegments < 0 ||
		sameScope < 0 || sameScope > 1 || sameScope > usage.ActiveSnapshots ||
		usage.ActiveSnapshots > memory.FactStatsPageMaxActiveSnapshots ||
		usage.ActiveSerializedBytes > memory.FactStatsPageMaxActiveSnapshotBytes ||
		usage.ActiveSegments > memory.FactStatsPageMaxActiveSnapshotSegments {
		return factStatsActiveSnapshotUsage{}, 0, memory.ErrFactStatsPageChanged
	}
	return usage, sameScope, nil
}

func mustDecodeFactStatsDigest(value string) []byte {
	decoded, err := hex.DecodeString(value)
	if err != nil || len(decoded) != sha256.Size {
		return nil
	}
	return decoded
}

func factStatsDomainsTx(
	ctx context.Context,
	tx *sql.Tx,
	sc rlmscope.Scope,
	snapshot, expectedRows, expectedDomains int64,
) ([]memory.FactStatsDomain, error) {
	rows, err := tx.QueryContext(ctx, `SELECT facts.domain, COUNT(*)
		FROM hierarchical_facts AS facts
		JOIN fact_export_sequence AS export_seq
			ON export_seq.fact_id COLLATE BINARY = facts.id COLLATE BINARY
		WHERE facts.tenant_id COLLATE BINARY = ?
		  AND facts.project_id COLLATE BINARY = ?
		  AND export_seq.seq <= ?
		  AND facts.domain IS NOT NULL AND facts.domain COLLATE BINARY != ''
		  AND (facts.session_id IS NULL OR facts.session_id COLLATE BINARY = '')
		GROUP BY facts.domain COLLATE BINARY
		ORDER BY facts.domain COLLATE BINARY ASC`, sc.TenantID, sc.ProjectID, snapshot)
	if err != nil {
		return nil, fmt.Errorf("query exact fact stats domains: %w", err)
	}
	defer rows.Close()
	entries := make([]memory.FactStatsDomain, 0, expectedDomains)
	var countedRows int64
	for rows.Next() {
		var entry memory.FactStatsDomain
		if err := rows.Scan(&entry.Domain, &entry.Count); err != nil {
			return nil, fmt.Errorf("scan exact fact stats domain: %w", err)
		}
		if entry.Domain == "" || !utf8.ValidString(entry.Domain) ||
			int64(len(entry.Domain)) > memory.FactStatsPageStoredDomainHardMaxBytes ||
			entry.Count <= 0 || int64(entry.Count) > expectedRows-countedRows {
			return nil, fmt.Errorf("invalid fact stats domain aggregate")
		}
		countedRows += int64(entry.Count)
		entries = append(entries, entry)
		if int64(len(entries)) > memory.FactStatsPageMaxDomains {
			return nil, &memory.FactStatsPageStoredOversize{Measurement: memory.BoundedSearchStoredOversize{
				Kind:          memory.BoundedSearchStoredRowCountOversizeKind,
				StoredRows:    int64(len(entries)),
				MaxStoredRows: memory.FactStatsPageMaxDomains,
			}}
		}
	}
	if err := rows.Err(); err != nil {
		return nil, fmt.Errorf("iterate exact fact stats domains: %w", err)
	}
	if int64(len(entries)) != expectedDomains {
		return nil, fmt.Errorf("fact stats domain count changed while materializing snapshot")
	}
	return entries, nil
}

func factStatsStoredDomainPreflightTx(
	ctx context.Context,
	tx *sql.Tx,
	sc rlmscope.Scope,
	snapshot int64,
) error {
	var maxDomainBytes, totalDomainBytes int64
	err := tx.QueryRowContext(ctx, `SELECT
		COALESCE(MAX(octet_length(facts.domain)), 0),
		COALESCE(SUM(octet_length(facts.domain)), 0)
		FROM hierarchical_facts AS facts
		JOIN fact_export_sequence AS export_seq
			ON export_seq.fact_id COLLATE BINARY = facts.id COLLATE BINARY
		WHERE facts.tenant_id COLLATE BINARY = ?
		  AND facts.project_id COLLATE BINARY = ?
		  AND export_seq.seq <= ?
		  AND facts.domain IS NOT NULL AND facts.domain COLLATE BINARY != ''
		  AND (facts.session_id IS NULL OR facts.session_id COLLATE BINARY = '')`,
		sc.TenantID, sc.ProjectID, snapshot,
	).Scan(&maxDomainBytes, &totalDomainBytes)
	if err != nil {
		return fmt.Errorf("preflight exact fact stats domains: %w", err)
	}
	if maxDomainBytes > memory.FactStatsPageStoredDomainHardMaxBytes {
		return &memory.FactStatsPageStoredOversize{Measurement: memory.BoundedSearchStoredOversize{
			Kind:           memory.BoundedSearchStoredRowOversizeKind,
			StoredBytes:    maxDomainBytes,
			MaxStoredBytes: memory.FactStatsPageStoredDomainHardMaxBytes,
		}}
	}
	if totalDomainBytes > memory.FactStatsPageStoredDomainScopeHardMaxBytes {
		return &memory.FactStatsPageStoredOversize{Measurement: memory.BoundedSearchStoredOversize{
			Kind:           memory.BoundedSearchStoredScopeOversizeKind,
			StoredBytes:    totalDomainBytes,
			MaxStoredBytes: memory.FactStatsPageStoredDomainScopeHardMaxBytes,
		}}
	}
	return nil
}

func factStatsHighWaterTx(ctx context.Context, tx *sql.Tx) (int64, error) {
	var highWater int64
	err := tx.QueryRowContext(ctx, `SELECT COALESCE(
		(SELECT seq FROM sqlite_sequence WHERE name = 'fact_export_sequence'), 0
	)`).Scan(&highWater)
	if err != nil {
		return 0, fmt.Errorf("capture fact stats page snapshot: %w", err)
	}
	if highWater < 0 {
		return 0, fmt.Errorf("invalid fact stats export sequence high-water")
	}
	return highWater, nil
}

func factStatsEligibleCountTx(
	ctx context.Context,
	tx *sql.Tx,
	sc rlmscope.Scope,
	snapshot int64,
) (int64, error) {
	var count int64
	err := tx.QueryRowContext(ctx, `SELECT COUNT(*)
		FROM hierarchical_facts AS facts
		JOIN fact_export_sequence AS export_seq
			ON export_seq.fact_id COLLATE BINARY = facts.id COLLATE BINARY
		WHERE facts.tenant_id COLLATE BINARY = ?
		  AND facts.project_id COLLATE BINARY = ?
		  AND export_seq.seq <= ?
		  AND (facts.session_id IS NULL OR facts.session_id COLLATE BINARY = '')`,
		sc.TenantID, sc.ProjectID, snapshot,
	).Scan(&count)
	if err != nil {
		return 0, fmt.Errorf("count exact fact stats rows: %w", err)
	}
	return count, nil
}

func factStatsDomainCountTx(
	ctx context.Context,
	tx *sql.Tx,
	sc rlmscope.Scope,
	snapshot int64,
) (int64, error) {
	var count int64
	err := tx.QueryRowContext(ctx, `SELECT COUNT(DISTINCT facts.domain COLLATE BINARY)
		FROM hierarchical_facts AS facts
		JOIN fact_export_sequence AS export_seq
			ON export_seq.fact_id COLLATE BINARY = facts.id COLLATE BINARY
		WHERE facts.tenant_id COLLATE BINARY = ?
		  AND facts.project_id COLLATE BINARY = ?
		  AND export_seq.seq <= ?
		  AND facts.domain IS NOT NULL AND facts.domain COLLATE BINARY != ''
		  AND (facts.session_id IS NULL OR facts.session_id COLLATE BINARY = '')`,
		sc.TenantID, sc.ProjectID, snapshot,
	).Scan(&count)
	if err != nil {
		return 0, fmt.Errorf("count exact fact stats domains: %w", err)
	}
	if count > memory.FactStatsPageMaxDomains {
		return 0, &memory.FactStatsPageStoredOversize{Measurement: memory.BoundedSearchStoredOversize{
			Kind:          memory.BoundedSearchStoredRowCountOversizeKind,
			StoredRows:    count,
			MaxStoredRows: memory.FactStatsPageMaxDomains,
		}}
	}
	return count, nil
}

func fixedFactStatsTx(
	ctx context.Context,
	tx *sql.Tx,
	sc rlmscope.Scope,
	snapshot int64,
) (*memory.FixedFactStoreStats, error) {
	const live = `facts.is_archived = 0 AND facts.is_stale = 0`
	const knownOrigins = `'unspecified', 'builtin', 'user', 'derived', 'external'`
	query := `SELECT
		COUNT(*),
		COALESCE(SUM(CASE WHEN ` + live + ` THEN 1 ELSE 0 END), 0),
		COALESCE(SUM(CASE WHEN facts.is_archived = 1 THEN 1 ELSE 0 END), 0),
		COALESCE(SUM(CASE WHEN facts.is_stale = 1 THEN 1 ELSE 0 END), 0),
		COALESCE(SUM(CASE WHEN facts.embedding IS NOT NULL THEN 1 ELSE 0 END), 0),
		COALESCE(SUM(CASE WHEN facts.source = 'genome' THEN 1 ELSE 0 END), 0),
		COALESCE(SUM(CASE WHEN facts.hit_count = 0 AND facts.created_at < ?
			AND facts.source != 'genome' AND facts.is_archived = 0 THEN 1 ELSE 0 END), 0),
		COALESCE(SUM(CASE WHEN facts.level = 0 THEN 1 ELSE 0 END), 0),
		COALESCE(SUM(CASE WHEN facts.level = 1 THEN 1 ELSE 0 END), 0),
		COALESCE(SUM(CASE WHEN facts.level = 2 THEN 1 ELSE 0 END), 0),
		COALESCE(SUM(CASE WHEN facts.level = 3 THEN 1 ELSE 0 END), 0),
		COALESCE(SUM(CASE WHEN facts.level NOT IN (0, 1, 2, 3) THEN 1 ELSE 0 END), 0),
		COALESCE(SUM(CASE WHEN ` + live + ` AND
			(facts.origin IS NULL OR facts.origin NOT IN (` + knownOrigins + `)) THEN 1 ELSE 0 END), 0),
		COALESCE(SUM(CASE WHEN ` + live + ` AND facts.origin = 'unspecified' THEN 1 ELSE 0 END), 0),
		COALESCE(SUM(CASE WHEN ` + live + ` AND facts.origin = 'builtin' THEN 1 ELSE 0 END), 0),
		COALESCE(SUM(CASE WHEN ` + live + ` AND facts.origin = 'user' THEN 1 ELSE 0 END), 0),
		COALESCE(SUM(CASE WHEN ` + live + ` AND facts.origin = 'derived' THEN 1 ELSE 0 END), 0),
		COALESCE(SUM(CASE WHEN ` + live + ` AND facts.origin = 'external' THEN 1 ELSE 0 END), 0)
	FROM hierarchical_facts AS facts
	JOIN fact_export_sequence AS export_seq
		ON export_seq.fact_id COLLATE BINARY = facts.id COLLATE BINARY
	WHERE facts.tenant_id COLLATE BINARY = ?
	  AND facts.project_id COLLATE BINARY = ?
	  AND export_seq.seq <= ?
	  AND (facts.session_id IS NULL OR facts.session_id COLLATE BINARY = '')`

	var (
		stats                                           memory.FixedFactStoreStats
		level0, level1, level2, level3, invalidLevels   int
		originUnknown, originUnspecified, originBuiltin int
		originUser, originDerived, originExternal       int
	)
	threshold := time.Now().AddDate(0, 0, -30).Format(timeFormat)
	err := tx.QueryRowContext(ctx, query,
		threshold, sc.TenantID, sc.ProjectID, snapshot,
	).Scan(
		&stats.TotalFacts,
		&stats.LiveFacts,
		&stats.ArchivedCount,
		&stats.StaleCount,
		&stats.WithEmbeddings,
		&stats.GeneCount,
		&stats.ColdCount,
		&level0, &level1, &level2, &level3, &invalidLevels,
		&originUnknown, &originUnspecified, &originBuiltin,
		&originUser, &originDerived, &originExternal,
	)
	if err != nil {
		return nil, fmt.Errorf("read fixed fact stats: %w", err)
	}
	if invalidLevels != 0 {
		return nil, fmt.Errorf("fact stats contain %d rows with invalid hierarchy levels", invalidLevels)
	}

	stats.ByLevel = make(map[memory.HierLevel]int, 4)
	for level, count := range map[memory.HierLevel]int{
		memory.LevelProject: level0,
		memory.LevelDomain:  level1,
		memory.LevelModule:  level2,
		memory.LevelSnippet: level3,
	} {
		if count > 0 {
			stats.ByLevel[level] = count
		}
	}
	stats.ByOrigin = make(map[memory.Origin]int, 5)
	for origin, count := range map[memory.Origin]int{
		memory.OriginUnspecified: originUnknown + originUnspecified,
		memory.OriginBuiltin:     originBuiltin,
		memory.OriginUser:        originUser,
		memory.OriginDerived:     originDerived,
		memory.OriginExternal:    originExternal,
	} {
		if count > 0 {
			stats.ByOrigin[origin] = count
		}
	}
	return &stats, nil
}
