package sqlite

import (
	"context"
	"database/sql"
	"errors"
	"fmt"
	"strings"
	"time"

	"github.com/syntrex/gomcp/internal/domain/memory"
	rlmscope "github.com/syntrex/gomcp/internal/domain/scope"
	modernsqlite "modernc.org/sqlite"
)

const (
	sessionTurnClaimSchemaVersion = 1
	sessionTurnClaimLease         = 2 * time.Minute
	maxSessionTurnClaimGeneration = int64(^uint64(0) >> 1)
	// This is longer than the gateway's five-minute upstream HTTP timeout.
	// Once it expires, uncertainty is durable and still cannot be stolen.
	sessionTurnUncertaintyWindow             = 15 * time.Minute
	sessionTurnClaimReceiptTrigger           = "session_turn_claim_receipt_complete_v1"
	sessionTurnClaimFactIDInsertBoundTrigger = "session_turn_claim_fact_id_insert_bound_v1"
	sessionTurnClaimFactIDUpdateBoundTrigger = "session_turn_claim_fact_id_update_bound_v1"
)

var sessionTurnClaimMigrationStatements = []string{
	`CREATE TABLE IF NOT EXISTS session_turn_claims (
		tenant_id TEXT NOT NULL,
		project_id TEXT NOT NULL,
		session_id TEXT NOT NULL CHECK (session_id <> ''),
		turn_id TEXT NOT NULL CHECK (
			length(turn_id) = 69 AND substr(turn_id, 1, 5) = 'turn_'
			AND substr(turn_id, 6) NOT GLOB '*[^0-9a-f]*'
		),
		request_ref TEXT NOT NULL CHECK (
			length(request_ref) = 95
			AND substr(request_ref, 1, 31) = 'session-turn-request-v1:sha256:'
			AND substr(request_ref, 32) NOT GLOB '*[^0-9a-f]*'
		),
		state TEXT NOT NULL CHECK (state IN ('CLAIMED', 'EXECUTING', 'COMPLETED', 'UNCERTAIN')),
		owner_token TEXT CHECK (
			owner_token IS NULL OR (
				length(owner_token) = 70 AND substr(owner_token, 1, 6) = 'claim_'
				AND substr(owner_token, 7) NOT GLOB '*[^0-9a-f]*'
			)
		),
		generation INTEGER NOT NULL CHECK (generation >= 1),
		lease_until_unix INTEGER,
		execution_started_unix INTEGER,
		uncertainty_deadline_unix INTEGER,
		completed_fact_id TEXT,
		created_at_unix INTEGER NOT NULL CHECK (created_at_unix > 0),
		updated_at_unix INTEGER NOT NULL CHECK (
			updated_at_unix > 0 AND updated_at_unix >= created_at_unix
		),
		schema_version INTEGER NOT NULL CHECK (schema_version = 1),
		PRIMARY KEY (tenant_id, project_id, session_id, turn_id),
		CHECK (
			(state = 'CLAIMED'
				AND owner_token IS NOT NULL AND lease_until_unix IS NOT NULL
				AND execution_started_unix IS NULL AND uncertainty_deadline_unix IS NULL
				AND completed_fact_id IS NULL)
			OR
			(state = 'EXECUTING'
				AND owner_token IS NOT NULL AND lease_until_unix IS NULL
				AND execution_started_unix IS NOT NULL
				AND uncertainty_deadline_unix >= execution_started_unix
				AND completed_fact_id IS NULL)
			OR
			(state = 'UNCERTAIN'
				AND owner_token IS NULL AND lease_until_unix IS NULL
				AND execution_started_unix IS NOT NULL
				AND uncertainty_deadline_unix >= execution_started_unix
				AND completed_fact_id IS NULL)
			OR
			(state = 'COMPLETED'
				AND owner_token IS NULL AND lease_until_unix IS NULL
				AND completed_fact_id IS NOT NULL AND completed_fact_id <> ''
				AND length(CAST(completed_fact_id AS BLOB)) BETWEEN 1 AND 256
				AND ((execution_started_unix IS NULL AND uncertainty_deadline_unix IS NULL)
					OR (execution_started_unix IS NOT NULL
						AND uncertainty_deadline_unix >= execution_started_unix)))
		)
	)`,
	// Existing v1 tables predate the fact-id byte bound, so additive triggers
	// enforce it on both direct inserts and receipt-driven completion updates.
	`CREATE TRIGGER IF NOT EXISTS ` + sessionTurnClaimFactIDInsertBoundTrigger + `
		BEFORE INSERT ON session_turn_claims
		WHEN NEW.state = 'COMPLETED' AND (
			NEW.completed_fact_id IS NULL
			OR length(CAST(NEW.completed_fact_id AS BLOB)) NOT BETWEEN 1 AND 256
		)
		BEGIN
			SELECT RAISE(ABORT, 'completed session turn fact id exceeds hard limit');
		END`,
	`CREATE TRIGGER IF NOT EXISTS ` + sessionTurnClaimFactIDUpdateBoundTrigger + `
		BEFORE UPDATE OF state, completed_fact_id ON session_turn_claims
		WHEN NEW.state = 'COMPLETED' AND (
			NEW.completed_fact_id IS NULL
			OR length(CAST(NEW.completed_fact_id AS BLOB)) NOT BETWEEN 1 AND 256
		)
		BEGIN
			SELECT RAISE(ABORT, 'completed session turn fact id exceeds hard limit');
		END`,
	// Receipt insertion and claim completion share the same SQLite transaction.
	// The trigger is intentionally opportunistic: an N-1 writer that knows only
	// receipts remains rollback-compatible, while a matching new claim is made
	// COMPLETED before that receipt can commit.
	`CREATE TRIGGER IF NOT EXISTS ` + sessionTurnClaimReceiptTrigger + `
		AFTER INSERT ON session_turn_receipts
		BEGIN
			UPDATE session_turn_claims
			SET state = 'COMPLETED', owner_token = NULL, lease_until_unix = NULL,
				completed_fact_id = NEW.fact_id,
				updated_at_unix = CAST(strftime('%s', 'now') AS INTEGER)
			WHERE tenant_id = NEW.tenant_id AND project_id = NEW.project_id
			  AND session_id = NEW.session_id AND turn_id = NEW.turn_id
			  AND request_ref = (
				SELECT code_ref FROM hierarchical_facts
				WHERE tenant_id = NEW.tenant_id AND project_id = NEW.project_id
				  AND session_id = NEW.session_id AND id = NEW.fact_id
			  );
		END`,
}

func (r *FactRepo) migrateSessionTurnClaims() error {
	for _, statement := range sessionTurnClaimMigrationStatements {
		if _, err := r.db.Exec(statement); err != nil {
			return fmt.Errorf("migrate session turn claims: %w", err)
		}
	}
	if err := r.validateSessionTurnClaimSchema(); err != nil {
		return err
	}
	return r.validateSessionTurnClaimBehavior()
}

func (r *FactRepo) validateSessionTurnClaimSchema() error {
	rows, err := r.db.Query(`PRAGMA table_info('session_turn_claims')`)
	if err != nil {
		return fmt.Errorf("inspect session turn claim columns: %w", err)
	}
	var columns []sqliteColumnShape
	for rows.Next() {
		var cid int
		var column sqliteColumnShape
		var defaultValue sql.NullString
		if err := rows.Scan(
			&cid, &column.name, &column.declType, &column.notNull, &defaultValue, &column.primaryKey,
		); err != nil {
			rows.Close()
			return fmt.Errorf("scan session turn claim columns: %w", err)
		}
		column.declType = strings.ToUpper(column.declType)
		column.hasDefault = defaultValue.Valid
		columns = append(columns, column)
	}
	if err := rows.Err(); err != nil {
		rows.Close()
		return fmt.Errorf("iterate session turn claim columns: %w", err)
	}
	rows.Close()
	expected := []sqliteColumnShape{
		{name: "tenant_id", declType: "TEXT", notNull: 1, primaryKey: 1},
		{name: "project_id", declType: "TEXT", notNull: 1, primaryKey: 2},
		{name: "session_id", declType: "TEXT", notNull: 1, primaryKey: 3},
		{name: "turn_id", declType: "TEXT", notNull: 1, primaryKey: 4},
		{name: "request_ref", declType: "TEXT", notNull: 1},
		{name: "state", declType: "TEXT", notNull: 1},
		{name: "owner_token", declType: "TEXT"},
		{name: "generation", declType: "INTEGER", notNull: 1},
		{name: "lease_until_unix", declType: "INTEGER"},
		{name: "execution_started_unix", declType: "INTEGER"},
		{name: "uncertainty_deadline_unix", declType: "INTEGER"},
		{name: "completed_fact_id", declType: "TEXT"},
		{name: "created_at_unix", declType: "INTEGER", notNull: 1},
		{name: "updated_at_unix", declType: "INTEGER", notNull: 1},
		{name: "schema_version", declType: "INTEGER", notNull: 1},
	}
	if !sameSQLiteColumnShapes(columns, expected) {
		return fmt.Errorf("incompatible session_turn_claims schema: exact v1 columns required")
	}
	indexes, err := r.uniqueIndexColumns("session_turn_claims")
	if err != nil {
		return err
	}
	if len(indexes) != 1 || !containsExactColumns(indexes, []string{
		"tenant_id", "project_id", "session_id", "turn_id",
	}) {
		return fmt.Errorf("incompatible session_turn_claims schema: exact BINARY primary key required")
	}
	return nil
}

func (r *FactRepo) validateSessionTurnClaimBehavior() error {
	ctx := context.Background()
	seed := fmt.Sprintf("%x", time.Now().UTC().UnixNano())
	if len(seed) < 16 {
		seed = fmt.Sprintf("%016s", seed)
	}
	tenantID := "TurnClaimProbeTenant-" + seed
	projectID := "TurnClaimProbeProject-" + seed
	sessionID := "TurnClaimProbeSession-" + seed
	turnID := "turn_" + strings.Repeat("a", 64)
	requestRef := memory.SessionTurnRequestRefPrefix + strings.Repeat("b", 64)
	otherRequestRef := memory.SessionTurnRequestRefPrefix + strings.Repeat("c", 64)
	ownerToken := memory.SessionTurnClaimTokenPrefix + strings.Repeat("d", 64)
	now := time.Now().UTC().Unix()
	if now <= 0 {
		return fmt.Errorf("validate session turn claim behavior: invalid wall clock")
	}

	r.db.mu.Lock()
	defer r.db.mu.Unlock()
	tx, err := r.db.db.BeginTx(ctx, nil)
	if err != nil {
		return fmt.Errorf("validate session turn claim behavior: begin probe: %w", err)
	}
	defer func() { _ = tx.Rollback() }()

	insertScopedClaim := func(
		candidateTenant, candidateProject, candidateSession, candidateTurn, candidateRequest string,
		state memory.SessionTurnClaimState,
		owner *string,
		lease, execution, uncertainty *int64,
		completed *string,
	) error {
		_, err := tx.ExecContext(ctx, `INSERT INTO session_turn_claims
			(tenant_id, project_id, session_id, turn_id, request_ref, state,
			 owner_token, generation, lease_until_unix, execution_started_unix,
			 uncertainty_deadline_unix, completed_fact_id, created_at_unix,
			 updated_at_unix, schema_version)
			VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?, ?, ?, ?, ?)`,
			candidateTenant, candidateProject, candidateSession, candidateTurn, candidateRequest,
			string(state), owner, lease, execution, uncertainty, completed,
			now, now, sessionTurnClaimSchemaVersion)
		return err
	}
	insertClaim := func(
		candidateSession, candidateTurn, candidateRequest string,
		state memory.SessionTurnClaimState,
		owner *string,
		lease, execution, uncertainty *int64,
		completed *string,
	) error {
		return insertScopedClaim(
			tenantID, projectID, candidateSession, candidateTurn, candidateRequest,
			state, owner, lease, execution, uncertainty, completed,
		)
	}
	lease := now + int64(sessionTurnClaimLease/time.Second)
	invalidOwner := "claim_bad"
	oversizedCompletedFactID := strings.Repeat("f", memory.SessionTurnCompletedFactIDMaxBytes+1)
	invalid := []struct {
		name                          string
		session, turn, request        string
		state                         memory.SessionTurnClaimState
		owner                         *string
		lease, execution, uncertainty *int64
		completed                     *string
	}{
		{name: "empty session", session: "", turn: turnID, request: requestRef, state: memory.SessionTurnClaimed, owner: &ownerToken, lease: &lease},
		{name: "invalid turn", session: sessionID, turn: "turn_bad", request: requestRef, state: memory.SessionTurnClaimed, owner: &ownerToken, lease: &lease},
		{name: "invalid request", session: sessionID, turn: turnID, request: "request_bad", state: memory.SessionTurnClaimed, owner: &ownerToken, lease: &lease},
		{name: "invalid owner", session: sessionID, turn: turnID, request: requestRef, state: memory.SessionTurnClaimed, owner: &invalidOwner, lease: &lease},
		{name: "claimed without lease", session: sessionID, turn: turnID, request: requestRef, state: memory.SessionTurnClaimed, owner: &ownerToken},
		{name: "executing shape", session: sessionID, turn: turnID, request: requestRef, state: memory.SessionTurnExecuting, owner: &ownerToken, lease: &lease},
		{name: "unknown state", session: sessionID, turn: turnID, request: requestRef, state: "BROKEN", owner: &ownerToken, lease: &lease},
		{name: "oversized completed fact id", session: sessionID, turn: turnID, request: requestRef, state: memory.SessionTurnCompleted, completed: &oversizedCompletedFactID},
	}
	for _, probe := range invalid {
		if err := insertClaim(
			probe.session, probe.turn, probe.request, probe.state, probe.owner,
			probe.lease, probe.execution, probe.uncertainty, probe.completed,
		); err == nil {
			return fmt.Errorf("incompatible session_turn_claims schema: %s constraint is not enforced", probe.name)
		}
	}

	if err := insertClaim(
		sessionID, turnID, requestRef, memory.SessionTurnClaimed,
		&ownerToken, &lease, nil, nil, nil,
	); err != nil {
		return fmt.Errorf("incompatible session_turn_claims schema: valid claim rejected: %w", err)
	}
	siblingScopes := []struct {
		tenantID, projectID, sessionID string
	}{
		{tenantID: tenantID + "Sibling", projectID: projectID, sessionID: sessionID},
		{tenantID: tenantID, projectID: projectID + "Sibling", sessionID: sessionID},
		{tenantID: tenantID, projectID: projectID, sessionID: sessionID + "Sibling"},
	}
	for _, sibling := range siblingScopes {
		if err := insertScopedClaim(
			sibling.tenantID, sibling.projectID, sibling.sessionID, turnID, requestRef,
			memory.SessionTurnClaimed, &ownerToken, &lease, nil, nil, nil,
		); err != nil {
			return fmt.Errorf("validate sibling scope claim setup: %w", err)
		}
	}
	updateBoundTurn := "turn_" + strings.Repeat("9", 64)
	if err := insertClaim(
		sessionID, updateBoundTurn, requestRef, memory.SessionTurnClaimed,
		&ownerToken, &lease, nil, nil, nil,
	); err != nil {
		return fmt.Errorf("validate completed fact id update bound setup: %w", err)
	}
	if _, err := tx.ExecContext(ctx, `UPDATE session_turn_claims
		SET state = 'COMPLETED', owner_token = NULL, lease_until_unix = NULL,
			completed_fact_id = ?
		WHERE tenant_id = ? AND project_id = ? AND session_id = ? AND turn_id = ?`,
		oversizedCompletedFactID, tenantID, projectID, sessionID, updateBoundTurn,
	); err == nil {
		return fmt.Errorf("incompatible session_turn_claims schema: oversized completed fact id update accepted")
	}
	var boundedState string
	var boundedCompleted sql.NullString
	if err := tx.QueryRowContext(ctx, `SELECT state, completed_fact_id
		FROM session_turn_claims
		WHERE tenant_id = ? AND project_id = ? AND session_id = ? AND turn_id = ?`,
		tenantID, projectID, sessionID, updateBoundTurn,
	).Scan(&boundedState, &boundedCompleted); err != nil {
		return fmt.Errorf("validate completed fact id update bound state: %w", err)
	}
	if boundedState != string(memory.SessionTurnClaimed) || boundedCompleted.Valid {
		return fmt.Errorf("incompatible session_turn_claims schema: rejected completed fact id update mutated claim")
	}
	for _, alias := range [][4]string{
		{strings.ToLower(tenantID), projectID, sessionID, turnID},
		{tenantID, strings.ToLower(projectID), sessionID, turnID},
		{tenantID, projectID, strings.ToLower(sessionID), turnID},
		{tenantID, projectID, sessionID, strings.ToUpper(turnID)},
	} {
		var matches int
		if err := tx.QueryRowContext(ctx, `SELECT COUNT(*) FROM session_turn_claims
			WHERE tenant_id = ? AND project_id = ? AND session_id = ? AND turn_id = ?`,
			alias[0], alias[1], alias[2], alias[3],
		).Scan(&matches); err != nil {
			return fmt.Errorf("validate session_turn_claims exact comparison: %w", err)
		}
		if matches != 0 {
			return fmt.Errorf("incompatible session_turn_claims schema: exact BINARY key comparison required")
		}
	}
	caseVariantScopes := []struct {
		tenantID, projectID, sessionID string
	}{
		{tenantID: strings.ToLower(tenantID), projectID: projectID, sessionID: sessionID},
		{tenantID: tenantID, projectID: strings.ToLower(projectID), sessionID: sessionID},
		{tenantID: tenantID, projectID: projectID, sessionID: strings.ToLower(sessionID)},
	}
	for _, sibling := range caseVariantScopes {
		if err := insertScopedClaim(
			sibling.tenantID, sibling.projectID, sibling.sessionID, turnID, requestRef,
			memory.SessionTurnClaimed, &ownerToken, &lease, nil, nil, nil,
		); err != nil {
			return fmt.Errorf("validate case-variant scope claim setup: %w", err)
		}
	}

	insertReceiptFact := func(factID, candidateTurn, codeRef string) error {
		created := time.Now().UTC().Round(0)
		fact := memory.NewFact("session turn claim trigger probe", memory.LevelDomain, "conversation", "chat")
		fact.ID = factID
		fact.TenantID = tenantID
		fact.ProjectID = projectID
		fact.SessionID = sessionID
		fact.CodeRef = codeRef
		fact.Source = "session_memory"
		fact.Origin = memory.OriginDerived
		fact.CreatedAt = created
		fact.ValidFrom = created
		fact.UpdatedAt = created
		_, err := tx.ExecContext(ctx, `INSERT INTO hierarchical_facts
			(id, tenant_id, project_id, content, level, domain, module, code_ref,
			 created_at, valid_from, is_stale, is_archived, confidence, source,
			 session_id, origin)
			VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 0, 1.0, ?, ?, ?)`,
			fact.ID, tenantID, projectID, fact.Content, int(fact.Level), fact.Domain,
			fact.Module, fact.CodeRef, created.Format(timeFormat), created.Format(timeFormat),
			fact.Source, sessionID, string(fact.Origin))
		if err != nil {
			return err
		}
		_, err = tx.ExecContext(ctx, `INSERT INTO session_turn_receipts
			(tenant_id, project_id, session_id, turn_id, fact_id, payload_version,
			 payload_sha256, created_at)
			VALUES (?, ?, ?, ?, ?, ?, ?, ?)`,
			tenantID, projectID, sessionID, candidateTurn, fact.ID,
			sessionTurnPayloadVersion, sessionTurnPayloadSHA256(
				rlmscope.New(tenantID, projectID), sessionID, fact,
			), created.Format(timeFormat))
		return err
	}
	factID := "TurnClaimProbeFact-" + seed
	if err := insertReceiptFact(factID, turnID, requestRef); err != nil {
		return fmt.Errorf("validate session turn claim receipt trigger: %w", err)
	}
	var state string
	var storedOwner, completedFact sql.NullString
	if err := tx.QueryRowContext(ctx, `SELECT state, owner_token, completed_fact_id
		FROM session_turn_claims
		WHERE tenant_id = ? AND project_id = ? AND session_id = ? AND turn_id = ?`,
		tenantID, projectID, sessionID, turnID,
	).Scan(&state, &storedOwner, &completedFact); err != nil {
		return fmt.Errorf("validate session turn claim receipt transition: %w", err)
	}
	if state != string(memory.SessionTurnCompleted) || storedOwner.Valid ||
		!completedFact.Valid || completedFact.String != factID {
		return fmt.Errorf("incompatible session turn claim receipt trigger: matching receipt did not complete claim")
	}
	var siblingTurnState string
	var siblingTurnCompletedFact sql.NullString
	if err := tx.QueryRowContext(ctx, `SELECT state, completed_fact_id
		FROM session_turn_claims
		WHERE tenant_id = ? AND project_id = ? AND session_id = ? AND turn_id = ?`,
		tenantID, projectID, sessionID, updateBoundTurn,
	).Scan(&siblingTurnState, &siblingTurnCompletedFact); err != nil {
		return fmt.Errorf("validate sibling turn claim state: %w", err)
	}
	if siblingTurnState != string(memory.SessionTurnClaimed) || siblingTurnCompletedFact.Valid {
		return fmt.Errorf("incompatible session turn claim receipt trigger: sibling turn claim was completed")
	}
	for _, sibling := range siblingScopes {
		var siblingState string
		var siblingCompletedFact sql.NullString
		if err := tx.QueryRowContext(ctx, `SELECT state, completed_fact_id
			FROM session_turn_claims
			WHERE tenant_id = ? AND project_id = ? AND session_id = ? AND turn_id = ?`,
			sibling.tenantID, sibling.projectID, sibling.sessionID, turnID,
		).Scan(&siblingState, &siblingCompletedFact); err != nil {
			return fmt.Errorf("validate sibling scope claim state: %w", err)
		}
		if siblingState != string(memory.SessionTurnClaimed) || siblingCompletedFact.Valid {
			return fmt.Errorf("incompatible session turn claim receipt trigger: sibling scope claim was completed")
		}
	}
	for _, sibling := range caseVariantScopes {
		var siblingState string
		var siblingCompletedFact sql.NullString
		if err := tx.QueryRowContext(ctx, `SELECT state, completed_fact_id
			FROM session_turn_claims
			WHERE tenant_id = ? AND project_id = ? AND session_id = ? AND turn_id = ?`,
			sibling.tenantID, sibling.projectID, sibling.sessionID, turnID,
		).Scan(&siblingState, &siblingCompletedFact); err != nil {
			return fmt.Errorf("validate case-variant scope claim state: %w", err)
		}
		if siblingState != string(memory.SessionTurnClaimed) || siblingCompletedFact.Valid {
			return fmt.Errorf("incompatible session turn claim receipt trigger: case-variant scope claim was completed")
		}
	}

	mismatchTurn := "turn_" + strings.Repeat("e", 64)
	mismatchOwner := memory.SessionTurnClaimTokenPrefix + strings.Repeat("f", 64)
	if err := insertClaim(
		sessionID, mismatchTurn, requestRef, memory.SessionTurnClaimed,
		&mismatchOwner, &lease, nil, nil, nil,
	); err != nil {
		return fmt.Errorf("validate mismatched receipt claim setup: %w", err)
	}
	if err := insertReceiptFact("TurnClaimMismatchFact-"+seed, mismatchTurn, otherRequestRef); err != nil {
		return fmt.Errorf("validate mismatched receipt claim trigger: %w", err)
	}
	if err := tx.QueryRowContext(ctx, `SELECT state FROM session_turn_claims
		WHERE tenant_id = ? AND project_id = ? AND session_id = ? AND turn_id = ?`,
		tenantID, projectID, sessionID, mismatchTurn,
	).Scan(&state); err != nil {
		return fmt.Errorf("validate mismatched receipt claim state: %w", err)
	}
	if state != string(memory.SessionTurnClaimed) {
		return fmt.Errorf("incompatible session turn claim receipt trigger: mismatched request completed claim")
	}
	if err := tx.Rollback(); err != nil {
		return fmt.Errorf("validate session turn claim behavior: roll back probe: %w", err)
	}
	return nil
}

type storedSessionTurnClaim struct {
	requestRef           string
	state                memory.SessionTurnClaimState
	ownerToken           sql.NullString
	generation           int64
	leaseUntil           sql.NullInt64
	executionStarted     sql.NullInt64
	uncertaintyDeadline  sql.NullInt64
	completedFactID      sql.NullString
	completedFactPresent bool
	createdAt, updatedAt int64
	schemaVersion        int
}

func loadSessionTurnClaimTx(
	ctx context.Context,
	tx *sql.Tx,
	sc rlmscope.Scope,
	sessionID, turnID string,
) (*storedSessionTurnClaim, error) {
	var stored storedSessionTurnClaim
	var completedFactBytes int64
	var completedFactText bool
	err := tx.QueryRowContext(ctx, `SELECT request_ref, state, owner_token, generation,
		lease_until_unix, execution_started_unix, uncertainty_deadline_unix,
		completed_fact_id IS NOT NULL,
		COALESCE(octet_length(completed_fact_id), 0),
		typeof(completed_fact_id) = 'text',
		created_at_unix, updated_at_unix, schema_version
		FROM session_turn_claims
		WHERE tenant_id = ? AND project_id = ? AND session_id = ? AND turn_id = ?`,
		sc.TenantID, sc.ProjectID, sessionID, turnID,
	).Scan(
		&stored.requestRef, &stored.state, &stored.ownerToken, &stored.generation,
		&stored.leaseUntil, &stored.executionStarted, &stored.uncertaintyDeadline,
		&stored.completedFactPresent, &completedFactBytes, &completedFactText,
		&stored.createdAt, &stored.updatedAt, &stored.schemaVersion,
	)
	if errors.Is(err, sql.ErrNoRows) {
		return nil, nil
	}
	if err != nil {
		return nil, fmt.Errorf("read session turn claim: %w", err)
	}
	if stored.completedFactPresent {
		if !completedFactText || completedFactBytes < 1 ||
			completedFactBytes > memory.SessionTurnCompletedFactIDMaxBytes {
			return nil, memory.ErrSessionTurnClaimIntegrity
		}
		var completedFactID string
		err := tx.QueryRowContext(ctx, `SELECT completed_fact_id
			FROM session_turn_claims
			WHERE tenant_id = ? AND project_id = ? AND session_id = ? AND turn_id = ?
			  AND typeof(completed_fact_id) = 'text'
			  AND octet_length(completed_fact_id) BETWEEN 1 AND ?`,
			sc.TenantID, sc.ProjectID, sessionID, turnID,
			memory.SessionTurnCompletedFactIDMaxBytes,
		).Scan(&completedFactID)
		if errors.Is(err, sql.ErrNoRows) {
			return nil, memory.ErrSessionTurnClaimIntegrity
		}
		if err != nil {
			return nil, fmt.Errorf("read bounded completed session turn fact identity: %w", err)
		}
		stored.completedFactID = sql.NullString{String: completedFactID, Valid: true}
	}
	if err := validateStoredSessionTurnClaim(&stored); err != nil {
		return nil, err
	}
	return &stored, nil
}

func validateStoredSessionTurnClaim(stored *storedSessionTurnClaim) error {
	if stored == nil || stored.schemaVersion != sessionTurnClaimSchemaVersion ||
		memory.ValidateSessionTurnRequestRef(stored.requestRef) != nil ||
		!stored.state.IsValid() || stored.generation < 1 ||
		stored.createdAt <= 0 || stored.updatedAt < stored.createdAt ||
		stored.completedFactPresent != stored.completedFactID.Valid {
		return memory.ErrSessionTurnClaimIntegrity
	}
	validOwner := stored.ownerToken.Valid && memory.ValidateSessionTurnClaimToken(stored.ownerToken.String) == nil
	switch stored.state {
	case memory.SessionTurnClaimed:
		if !validOwner || !stored.leaseUntil.Valid || stored.executionStarted.Valid ||
			stored.uncertaintyDeadline.Valid || stored.completedFactID.Valid {
			return memory.ErrSessionTurnClaimIntegrity
		}
	case memory.SessionTurnExecuting:
		if !validOwner || stored.leaseUntil.Valid || !stored.executionStarted.Valid ||
			!stored.uncertaintyDeadline.Valid ||
			stored.uncertaintyDeadline.Int64 < stored.executionStarted.Int64 ||
			stored.completedFactID.Valid {
			return memory.ErrSessionTurnClaimIntegrity
		}
	case memory.SessionTurnUncertain:
		if stored.ownerToken.Valid || stored.leaseUntil.Valid || !stored.executionStarted.Valid ||
			!stored.uncertaintyDeadline.Valid ||
			stored.uncertaintyDeadline.Int64 < stored.executionStarted.Int64 ||
			stored.completedFactID.Valid {
			return memory.ErrSessionTurnClaimIntegrity
		}
	case memory.SessionTurnCompleted:
		validExecutionPair := (!stored.executionStarted.Valid && !stored.uncertaintyDeadline.Valid) ||
			(stored.executionStarted.Valid && stored.uncertaintyDeadline.Valid &&
				stored.uncertaintyDeadline.Int64 >= stored.executionStarted.Int64)
		if stored.ownerToken.Valid || stored.leaseUntil.Valid || !validExecutionPair ||
			!stored.completedFactID.Valid ||
			memory.ValidateSessionTurnCompletedFactID(stored.completedFactID.String) != nil {
			return memory.ErrSessionTurnClaimIntegrity
		}
	}
	return nil
}

func (stored *storedSessionTurnClaim) public(turnID, ownerToken string, now int64) *memory.SessionTurnClaim {
	owned := false
	if stored.ownerToken.Valid && stored.ownerToken.String == ownerToken {
		switch stored.state {
		case memory.SessionTurnClaimed:
			owned = stored.leaseUntil.Valid && stored.leaseUntil.Int64 > now
		case memory.SessionTurnExecuting:
			owned = stored.uncertaintyDeadline.Valid && stored.uncertaintyDeadline.Int64 > now
		}
	}
	claim := &memory.SessionTurnClaim{
		Version:    sessionTurnClaimSchemaVersion,
		TurnID:     turnID,
		RequestRef: stored.requestRef,
		State:      stored.state,
		Owned:      owned,
		Generation: stored.generation,
	}
	if stored.leaseUntil.Valid {
		claim.LeaseUntilUnix = stored.leaseUntil.Int64
	}
	if stored.executionStarted.Valid {
		claim.ExecutionStartedUnix = stored.executionStarted.Int64
	}
	if stored.uncertaintyDeadline.Valid {
		claim.UncertaintyDeadlineUnix = stored.uncertaintyDeadline.Int64
	}
	if stored.completedFactID.Valid {
		claim.CompletedFactID = stored.completedFactID.String
	}
	return claim
}

func validateSessionTurnClaimInput(sessionID, turnID, requestRef, ownerToken string) error {
	if err := rlmscope.ValidateSessionID(sessionID); err != nil {
		return err
	}
	if err := rlmscope.ValidateTurnID(turnID); err != nil {
		return err
	}
	if err := memory.ValidateSessionTurnRequestRef(requestRef); err != nil {
		return err
	}
	return memory.ValidateSessionTurnClaimToken(ownerToken)
}

func reconcileSessionTurnClaimReceiptTx(
	ctx context.Context,
	tx *sql.Tx,
	sc rlmscope.Scope,
	sessionID, turnID, requestRef, ownerToken string,
	now int64,
	stored *storedSessionTurnClaim,
	fact *memory.Fact,
	receipt *memory.SessionTurnReceipt,
) (*memory.SessionTurnClaim, error) {
	if fact == nil || receipt == nil || receipt.FactID != fact.ID ||
		memory.ValidateSessionTurnRequestRef(fact.CodeRef) != nil {
		return nil, memory.ErrSessionTurnClaimIntegrity
	}
	if fact.CodeRef != requestRef {
		return nil, memory.ErrSessionTurnConflict
	}
	if stored != nil {
		if stored.requestRef != requestRef {
			return nil, memory.ErrSessionTurnClaimIntegrity
		}
		if stored.state == memory.SessionTurnCompleted &&
			(!stored.completedFactID.Valid || stored.completedFactID.String != fact.ID) {
			return nil, memory.ErrSessionTurnClaimIntegrity
		}
		result, err := tx.ExecContext(ctx, `UPDATE session_turn_claims
			SET state = ?, owner_token = NULL, lease_until_unix = NULL,
				completed_fact_id = ?, updated_at_unix = ?
			WHERE tenant_id = ? AND project_id = ? AND session_id = ? AND turn_id = ?
			  AND request_ref = ?`,
			string(memory.SessionTurnCompleted), fact.ID, now,
			sc.TenantID, sc.ProjectID, sessionID, turnID, requestRef)
		if err != nil {
			return nil, fmt.Errorf("reconcile completed session turn claim: %w", err)
		}
		if changed, _ := result.RowsAffected(); changed != 1 {
			return nil, memory.ErrSessionTurnClaimIntegrity
		}
	} else {
		_, err := tx.ExecContext(ctx, `INSERT INTO session_turn_claims
			(tenant_id, project_id, session_id, turn_id, request_ref, state,
			 owner_token, generation, lease_until_unix, execution_started_unix,
			 uncertainty_deadline_unix, completed_fact_id, created_at_unix,
			 updated_at_unix, schema_version)
			VALUES (?, ?, ?, ?, ?, ?, NULL, 1, NULL, NULL, NULL, ?, ?, ?, ?)`,
			sc.TenantID, sc.ProjectID, sessionID, turnID, requestRef,
			string(memory.SessionTurnCompleted), fact.ID, now, now,
			sessionTurnClaimSchemaVersion)
		if err != nil {
			return nil, fmt.Errorf("record completed session turn claim: %w", err)
		}
	}
	completed, err := loadSessionTurnClaimTx(ctx, tx, sc, sessionID, turnID)
	if err != nil || completed == nil {
		if err == nil {
			err = memory.ErrSessionTurnClaimIntegrity
		}
		return nil, err
	}
	return completed.public(turnID, ownerToken, now), nil
}

func (r *FactRepo) AcquireSessionTurnClaim(
	ctx context.Context,
	sessionID, turnID, requestRef, ownerToken string,
) (*memory.SessionTurnClaim, error) {
	return r.acquireSessionTurnClaimAt(
		ctx, sessionID, turnID, requestRef, ownerToken,
		time.Now().UTC().Unix(), sessionTurnClaimLease,
	)
}

func (r *FactRepo) acquireSessionTurnClaimAt(
	ctx context.Context,
	sessionID, turnID, requestRef, ownerToken string,
	now int64,
	lease time.Duration,
) (*memory.SessionTurnClaim, error) {
	for attempt := 0; attempt < 8; attempt++ {
		claim, err := r.acquireSessionTurnClaimAtOnce(
			ctx, sessionID, turnID, requestRef, ownerToken, now, lease,
		)
		if !sessionTurnClaimSQLiteBusy(err) {
			return claim, err
		}
		select {
		case <-ctx.Done():
			return nil, ctx.Err()
		case <-time.After(time.Duration(attempt+1) * time.Millisecond):
		}
	}
	return nil, fmt.Errorf("acquire session turn claim: SQLite writer remained busy")
}

func (r *FactRepo) acquireSessionTurnClaimAtOnce(
	ctx context.Context,
	sessionID, turnID, requestRef, ownerToken string,
	now int64,
	lease time.Duration,
) (*memory.SessionTurnClaim, error) {
	sc, err := rlmscope.RequireSessionScope(ctx, sessionID)
	if err != nil {
		return nil, err
	}
	if err := validateSessionTurnClaimInput(sessionID, turnID, requestRef, ownerToken); err != nil {
		return nil, err
	}
	leaseSeconds := int64(lease / time.Second)
	if now <= 0 || leaseSeconds <= 0 || now > maxSessionTurnClaimGeneration-leaseSeconds {
		return nil, fmt.Errorf("invalid session turn claim clock or lease")
	}

	r.db.mu.Lock()
	defer r.db.mu.Unlock()
	tx, err := r.db.db.BeginTx(ctx, nil)
	if err != nil {
		return nil, fmt.Errorf("begin session turn claim acquisition: %w", err)
	}
	defer func() { _ = tx.Rollback() }()
	projectNow, err := acquireProjectWriteTx(ctx, tx, sc)
	if err != nil {
		return nil, err
	}
	stored, err := loadSessionTurnClaimTx(ctx, tx, sc, sessionID, turnID)
	if err != nil {
		return nil, err
	}
	fact, receipt, err := loadSessionTurnReceiptTx(ctx, tx, sc, sessionID, turnID)
	if err != nil {
		return nil, err
	}
	if receipt != nil {
		claim, err := reconcileSessionTurnClaimReceiptTx(
			ctx, tx, sc, sessionID, turnID, requestRef, ownerToken, now, stored, fact, receipt,
		)
		if err != nil {
			return nil, err
		}
		if err := tx.Commit(); err != nil {
			return nil, fmt.Errorf("commit completed session turn claim reconciliation: %w", err)
		}
		return claim, nil
	}
	if stored != nil && stored.requestRef != requestRef {
		return nil, memory.ErrSessionTurnConflict
	}
	if stored == nil {
		if err := requireProjectWritableAndTouchTx(ctx, tx, sc, projectNow); err != nil {
			return nil, err
		}
		leaseUntil := now + leaseSeconds
		_, err := tx.ExecContext(ctx, `INSERT INTO session_turn_claims
			(tenant_id, project_id, session_id, turn_id, request_ref, state,
			 owner_token, generation, lease_until_unix, execution_started_unix,
			 uncertainty_deadline_unix, completed_fact_id, created_at_unix,
			 updated_at_unix, schema_version)
			VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?, NULL, NULL, NULL, ?, ?, ?)`,
			sc.TenantID, sc.ProjectID, sessionID, turnID, requestRef,
			string(memory.SessionTurnClaimed), ownerToken, leaseUntil, now, now,
			sessionTurnClaimSchemaVersion)
		if err != nil {
			return nil, fmt.Errorf("insert session turn claim: %w", err)
		}
	} else {
		switch stored.state {
		case memory.SessionTurnClaimed:
			if stored.ownerToken.String == ownerToken ||
				(stored.leaseUntil.Valid && stored.leaseUntil.Int64 <= now) {
				if err := requireProjectWritableAndTouchTx(ctx, tx, sc, projectNow); err != nil {
					return nil, err
				}
				generation := stored.generation
				if stored.ownerToken.String != ownerToken {
					if generation == maxSessionTurnClaimGeneration {
						return nil, memory.ErrSessionTurnClaimIntegrity
					}
					generation++
				}
				result, err := tx.ExecContext(ctx, `UPDATE session_turn_claims
					SET owner_token = ?, generation = ?, lease_until_unix = ?, updated_at_unix = ?
					WHERE tenant_id = ? AND project_id = ? AND session_id = ? AND turn_id = ?
					  AND request_ref = ? AND state = 'CLAIMED'`,
					ownerToken, generation, now+leaseSeconds, now,
					sc.TenantID, sc.ProjectID, sessionID, turnID, requestRef)
				if err != nil {
					return nil, fmt.Errorf("renew or steal session turn claim: %w", err)
				}
				if changed, _ := result.RowsAffected(); changed != 1 {
					return nil, memory.ErrSessionTurnClaimIntegrity
				}
			}
		case memory.SessionTurnExecuting:
			if stored.uncertaintyDeadline.Int64 <= now {
				result, err := tx.ExecContext(ctx, `UPDATE session_turn_claims
					SET state = 'UNCERTAIN', owner_token = NULL, updated_at_unix = ?
					WHERE tenant_id = ? AND project_id = ? AND session_id = ? AND turn_id = ?
					  AND request_ref = ? AND state = 'EXECUTING'
					  AND uncertainty_deadline_unix <= ?`,
					now, sc.TenantID, sc.ProjectID, sessionID, turnID, requestRef, now)
				if err != nil {
					return nil, fmt.Errorf("mark stale session turn execution uncertain: %w", err)
				}
				if changed, _ := result.RowsAffected(); changed != 1 {
					return nil, memory.ErrSessionTurnClaimIntegrity
				}
			}
		case memory.SessionTurnCompleted:
			return nil, memory.ErrSessionTurnClaimIntegrity
		case memory.SessionTurnUncertain:
		}
	}
	current, err := loadSessionTurnClaimTx(ctx, tx, sc, sessionID, turnID)
	if err != nil || current == nil {
		if err == nil {
			err = memory.ErrSessionTurnClaimIntegrity
		}
		return nil, err
	}
	claim := current.public(turnID, ownerToken, now)
	if err := tx.Commit(); err != nil {
		return nil, fmt.Errorf("commit session turn claim acquisition: %w", err)
	}
	return claim, nil
}

func (r *FactRepo) BeginSessionTurnExecution(
	ctx context.Context,
	sessionID, turnID, requestRef, ownerToken string,
) (*memory.SessionTurnClaim, error) {
	return r.beginSessionTurnExecutionAt(
		ctx, sessionID, turnID, requestRef, ownerToken,
		time.Now().UTC().Unix(), sessionTurnUncertaintyWindow,
	)
}

func (r *FactRepo) beginSessionTurnExecutionAt(
	ctx context.Context,
	sessionID, turnID, requestRef, ownerToken string,
	now int64,
	uncertaintyWindow time.Duration,
) (*memory.SessionTurnClaim, error) {
	for attempt := 0; attempt < 8; attempt++ {
		claim, err := r.beginSessionTurnExecutionAtOnce(
			ctx, sessionID, turnID, requestRef, ownerToken, now, uncertaintyWindow,
		)
		if !sessionTurnClaimSQLiteBusy(err) {
			return claim, err
		}
		select {
		case <-ctx.Done():
			return nil, ctx.Err()
		case <-time.After(time.Duration(attempt+1) * time.Millisecond):
		}
	}
	return nil, fmt.Errorf("begin session turn execution: SQLite writer remained busy")
}

func (r *FactRepo) beginSessionTurnExecutionAtOnce(
	ctx context.Context,
	sessionID, turnID, requestRef, ownerToken string,
	now int64,
	uncertaintyWindow time.Duration,
) (*memory.SessionTurnClaim, error) {
	sc, err := rlmscope.RequireSessionScope(ctx, sessionID)
	if err != nil {
		return nil, err
	}
	if err := validateSessionTurnClaimInput(sessionID, turnID, requestRef, ownerToken); err != nil {
		return nil, err
	}
	uncertaintySeconds := int64(uncertaintyWindow / time.Second)
	if now <= 0 || uncertaintySeconds <= 0 || now > maxSessionTurnClaimGeneration-uncertaintySeconds {
		return nil, fmt.Errorf("invalid session turn execution clock or deadline")
	}

	r.db.mu.Lock()
	defer r.db.mu.Unlock()
	tx, err := r.db.db.BeginTx(ctx, nil)
	if err != nil {
		return nil, fmt.Errorf("begin session turn execution transition: %w", err)
	}
	defer func() { _ = tx.Rollback() }()
	projectNow, err := acquireProjectWriteTx(ctx, tx, sc)
	if err != nil {
		return nil, err
	}
	stored, err := loadSessionTurnClaimTx(ctx, tx, sc, sessionID, turnID)
	if err != nil {
		return nil, err
	}
	fact, receipt, err := loadSessionTurnReceiptTx(ctx, tx, sc, sessionID, turnID)
	if err != nil {
		return nil, err
	}
	if receipt != nil {
		claim, err := reconcileSessionTurnClaimReceiptTx(
			ctx, tx, sc, sessionID, turnID, requestRef, ownerToken, now, stored, fact, receipt,
		)
		if err != nil {
			return nil, err
		}
		if err := tx.Commit(); err != nil {
			return nil, fmt.Errorf("commit completed session turn execution reconciliation: %w", err)
		}
		return claim, nil
	}
	if stored == nil {
		return nil, memory.ErrSessionTurnClaimNotFound
	}
	if stored.requestRef != requestRef {
		return nil, memory.ErrSessionTurnConflict
	}
	if stored.state == memory.SessionTurnExecuting &&
		stored.uncertaintyDeadline.Int64 <= now {
		result, err := tx.ExecContext(ctx, `UPDATE session_turn_claims
			SET state = 'UNCERTAIN', owner_token = NULL, updated_at_unix = ?
			WHERE tenant_id = ? AND project_id = ? AND session_id = ? AND turn_id = ?
			  AND request_ref = ? AND state = 'EXECUTING'
			  AND uncertainty_deadline_unix <= ?`,
			now, sc.TenantID, sc.ProjectID, sessionID, turnID, requestRef, now)
		if err != nil {
			return nil, fmt.Errorf("mark stale session turn execution uncertain: %w", err)
		}
		if changed, _ := result.RowsAffected(); changed != 1 {
			return nil, memory.ErrSessionTurnClaimIntegrity
		}
		stored, err = loadSessionTurnClaimTx(ctx, tx, sc, sessionID, turnID)
		if err != nil || stored == nil {
			if err == nil {
				err = memory.ErrSessionTurnClaimIntegrity
			}
			return nil, err
		}
	}
	if stored.state == memory.SessionTurnClaimed &&
		stored.ownerToken.Valid && stored.ownerToken.String == ownerToken &&
		stored.leaseUntil.Valid && stored.leaseUntil.Int64 > now {
		if err := requireProjectWritableAndTouchTx(ctx, tx, sc, projectNow); err != nil {
			return nil, err
		}
		deadline := now + uncertaintySeconds
		result, err := tx.ExecContext(ctx, `UPDATE session_turn_claims
			SET state = 'EXECUTING', lease_until_unix = NULL,
				execution_started_unix = ?, uncertainty_deadline_unix = ?,
				updated_at_unix = ?
			WHERE tenant_id = ? AND project_id = ? AND session_id = ? AND turn_id = ?
			  AND request_ref = ? AND state = 'CLAIMED' AND owner_token = ?`,
			now, deadline, now, sc.TenantID, sc.ProjectID, sessionID, turnID,
			requestRef, ownerToken)
		if err != nil {
			return nil, fmt.Errorf("begin session turn execution: %w", err)
		}
		if changed, _ := result.RowsAffected(); changed != 1 {
			return nil, memory.ErrSessionTurnClaimIntegrity
		}
	} else if stored.state == memory.SessionTurnExecuting &&
		stored.ownerToken.Valid && stored.ownerToken.String == ownerToken {
		// Idempotent acknowledgement recovery: the gateway calls this before
		// provider send, so retrying the transition after a lost MCP response
		// cannot duplicate provider work.
		if err := requireProjectWritableAndTouchTx(ctx, tx, sc, projectNow); err != nil {
			return nil, err
		}
	}
	current, err := loadSessionTurnClaimTx(ctx, tx, sc, sessionID, turnID)
	if err != nil || current == nil {
		if err == nil {
			err = memory.ErrSessionTurnClaimIntegrity
		}
		return nil, err
	}
	claim := current.public(turnID, ownerToken, now)
	if err := tx.Commit(); err != nil {
		return nil, fmt.Errorf("commit session turn execution transition: %w", err)
	}
	return claim, nil
}

func sessionTurnClaimSQLiteBusy(err error) bool {
	var sqliteErr *modernsqlite.Error
	return errors.As(err, &sqliteErr) && sqliteErr.Code()&0xff == 5
}
