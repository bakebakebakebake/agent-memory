package storage

import (
	"context"
	"database/sql"
	"encoding/json"
	"fmt"
	"math"
	"os"
	"regexp"
	"sort"
	"strings"
	"time"

	memoryv1 "github.com/bakebakebakebake/agent-memory/go-server/gen/memory/v1"
	"github.com/bakebakebakebake/agent-memory/go-server/internal/storage/migrations"
	_ "github.com/mattn/go-sqlite3"
)

var ftsQueryPattern = regexp.MustCompile(`[\p{Han}\w-]+`)

type Backend struct {
	db           *sql.DB
	DatabasePath string
}

func New(databasePath string) (*Backend, error) {
	db, err := sql.Open("sqlite3", databasePath)
	if err != nil {
		return nil, fmt.Errorf("open sqlite database: %w", err)
	}
	if _, err := db.Exec("PRAGMA foreign_keys = ON"); err != nil {
		return nil, fmt.Errorf("enable foreign keys: %w", err)
	}
	if databasePath != ":memory:" {
		if _, err := db.Exec("PRAGMA journal_mode = WAL"); err != nil {
			return nil, fmt.Errorf("enable wal: %w", err)
		}
	}
	if err := migrations.Apply(db); err != nil {
		return nil, err
	}
	return &Backend{db: db, DatabasePath: databasePath}, nil
}

func (backend *Backend) Close() error {
	return backend.db.Close()
}

func (backend *Backend) AddMemory(ctx context.Context, item *memoryv1.MemoryItem) (*memoryv1.MemoryItem, error) {
	tx, err := backend.db.BeginTx(ctx, nil)
	if err != nil {
		return nil, err
	}
	defer tx.Rollback()
	entityJSON, err := json.Marshal(item.EntityRefs)
	if err != nil {
		return nil, err
	}
	tagsJSON, err := json.Marshal(item.Tags)
	if err != nil {
		return nil, err
	}
	result, err := tx.ExecContext(
		ctx,
		`INSERT INTO memories (
			id, content, memory_type, created_at, last_accessed, access_count,
			valid_from, valid_until, trust_score, importance, layer, decay_rate,
			source_id, causal_parent_id, supersedes_id, entity_refs_json, tags_json, deleted_at
		) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
		item.Id, item.Content, item.MemoryType, item.CreatedAt, item.LastAccessed, item.AccessCount,
		nullable(item.ValidFrom), nullable(item.ValidUntil), item.TrustScore, item.Importance, item.Layer, item.DecayRate,
		item.SourceId, nullable(item.CausalParentId), nullable(item.SupersedesId), string(entityJSON), string(tagsJSON), nullable(item.DeletedAt),
	)
	if err != nil {
		return nil, err
	}
	rowid, err := result.LastInsertId()
	if err != nil {
		return nil, err
	}
	embeddingJSON, err := json.Marshal(item.Embedding)
	if err != nil {
		return nil, err
	}
	if _, err := tx.ExecContext(ctx, `INSERT INTO memory_vectors (memory_id, memory_rowid, embedding_json) VALUES (?, ?, ?)`, item.Id, rowid, string(embeddingJSON)); err != nil {
		return nil, err
	}
	for _, entity := range item.EntityRefs {
		if _, err := tx.ExecContext(ctx, `INSERT OR IGNORE INTO entity_index (entity, memory_id) VALUES (?, ?)`, strings.ToLower(entity), item.Id); err != nil {
			return nil, err
		}
	}
	if err := appendEvolutionTx(ctx, tx, item.Id, "created", map[string]any{"source_id": item.SourceId}); err != nil {
		return nil, err
	}
	if err := appendAuditTx(ctx, tx, "system", "create", "memory", item.Id, map[string]any{"source_id": item.SourceId}); err != nil {
		return nil, err
	}
	if err := tx.Commit(); err != nil {
		return nil, err
	}
	return item, nil
}

func (backend *Backend) GetMemory(ctx context.Context, memoryID string) (*memoryv1.MemoryItem, error) {
	row := backend.db.QueryRowContext(ctx, `
		SELECT m.*, v.embedding_json
		FROM memories m
		LEFT JOIN memory_vectors v ON v.memory_id = m.id
		WHERE m.id = ?`, memoryID)
	return scanMemory(row)
}

func (backend *Backend) UpdateMemory(ctx context.Context, item *memoryv1.MemoryItem) (*memoryv1.MemoryItem, error) {
	tx, err := backend.db.BeginTx(ctx, nil)
	if err != nil {
		return nil, err
	}
	defer tx.Rollback()
	entityJSON, err := json.Marshal(item.EntityRefs)
	if err != nil {
		return nil, err
	}
	tagsJSON, err := json.Marshal(item.Tags)
	if err != nil {
		return nil, err
	}
	if _, err := tx.ExecContext(
		ctx,
		`UPDATE memories SET
			content = ?, memory_type = ?, created_at = ?, last_accessed = ?, access_count = ?,
			valid_from = ?, valid_until = ?, trust_score = ?, importance = ?, layer = ?, decay_rate = ?,
			source_id = ?, causal_parent_id = ?, supersedes_id = ?, entity_refs_json = ?, tags_json = ?, deleted_at = ?
		WHERE id = ?`,
		item.Content, item.MemoryType, item.CreatedAt, item.LastAccessed, item.AccessCount,
		nullable(item.ValidFrom), nullable(item.ValidUntil), item.TrustScore, item.Importance, item.Layer, item.DecayRate,
		item.SourceId, nullable(item.CausalParentId), nullable(item.SupersedesId), string(entityJSON), string(tagsJSON), nullable(item.DeletedAt), item.Id,
	); err != nil {
		return nil, err
	}
	embeddingJSON, err := json.Marshal(item.Embedding)
	if err != nil {
		return nil, err
	}
	if _, err := tx.ExecContext(ctx, `UPDATE memory_vectors SET embedding_json = ? WHERE memory_id = ?`, string(embeddingJSON), item.Id); err != nil {
		return nil, err
	}
	if _, err := tx.ExecContext(ctx, `DELETE FROM entity_index WHERE memory_id = ?`, item.Id); err != nil {
		return nil, err
	}
	for _, entity := range item.EntityRefs {
		if _, err := tx.ExecContext(ctx, `INSERT OR IGNORE INTO entity_index (entity, memory_id) VALUES (?, ?)`, strings.ToLower(entity), item.Id); err != nil {
			return nil, err
		}
	}
	if err := appendEvolutionTx(ctx, tx, item.Id, "updated", map[string]any{"source_id": item.SourceId}); err != nil {
		return nil, err
	}
	if err := appendAuditTx(ctx, tx, "system", "update", "memory", item.Id, map[string]any{"source_id": item.SourceId}); err != nil {
		return nil, err
	}
	if err := tx.Commit(); err != nil {
		return nil, err
	}
	return item, nil
}

func (backend *Backend) SoftDeleteMemory(ctx context.Context, memoryID string) (bool, error) {
	result, err := backend.db.ExecContext(ctx, `UPDATE memories SET deleted_at = ? WHERE id = ? AND deleted_at IS NULL`, time.Now().UTC().Format(time.RFC3339Nano), memoryID)
	if err != nil {
		return false, err
	}
	affected, err := result.RowsAffected()
	if err != nil {
		return false, err
	}
	if affected == 0 {
		return false, nil
	}
	if err := appendEvolution(ctx, backend.db, memoryID, "deleted", map[string]any{}); err != nil {
		return false, err
	}
	if err := appendAudit(ctx, backend.db, "system", "delete", "memory", memoryID, map[string]any{}); err != nil {
		return false, err
	}
	return true, nil
}

func (backend *Backend) TouchMemory(ctx context.Context, memoryID string) error {
	_, err := backend.db.ExecContext(ctx, `UPDATE memories SET access_count = access_count + 1, last_accessed = ? WHERE id = ? AND deleted_at IS NULL`, time.Now().UTC().Format(time.RFC3339Nano), memoryID)
	return err
}

func (backend *Backend) SearchFullText(ctx context.Context, query string, limit int32, memoryType string) ([]*memoryv1.SearchResult, error) {
	terms := ftsQueryPattern.FindAllString(strings.ToLower(query), -1)
	if len(terms) == 0 {
		return []*memoryv1.SearchResult{}, nil
	}
	queryText := `
		SELECT m.*, v.embedding_json
		FROM memories m
		LEFT JOIN memory_vectors v ON v.memory_id = m.id
		WHERE m.deleted_at IS NULL`
	args := []any{}
	for _, term := range terms {
		queryText += ` AND (LOWER(m.content) LIKE ? OR LOWER(m.tags_json) LIKE ?)`
		pattern := "%" + term + "%"
		args = append(args, pattern, pattern)
	}
	if memoryType != "" {
		queryText += ` AND m.memory_type = ?`
		args = append(args, memoryType)
	}
	queryText += ` ORDER BY m.created_at DESC LIMIT ?`
	args = append(args, limit)
	rows, err := backend.db.QueryContext(ctx, queryText, args...)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	results := []*memoryv1.SearchResult{}
	for rows.Next() {
		item, err := scanMemoryRows(rows)
		if err != nil {
			return nil, err
		}
		score := lexicalScore(query, item.Content, item.Tags)
		results = append(results, &memoryv1.SearchResult{Item: item, Score: score, MatchedBy: []string{"full_text"}})
	}
	return results, rows.Err()
}

func (backend *Backend) SearchByEntities(ctx context.Context, entities []string, limit int32, memoryType string) ([]*memoryv1.SearchResult, error) {
	if len(entities) == 0 {
		return []*memoryv1.SearchResult{}, nil
	}
	placeholders := strings.TrimSuffix(strings.Repeat("?,", len(entities)), ",")
	queryText := fmt.Sprintf(`
		SELECT m.*, v.embedding_json, COUNT(*) AS entity_hits
		FROM entity_index e
		JOIN memories m ON m.id = e.memory_id
		LEFT JOIN memory_vectors v ON v.memory_id = m.id
		WHERE e.entity IN (%s)
		  AND m.deleted_at IS NULL`, placeholders)
	args := make([]any, 0, len(entities)+2)
	for _, entity := range entities {
		args = append(args, strings.ToLower(entity))
	}
	if memoryType != "" {
		queryText += ` AND m.memory_type = ?`
		args = append(args, memoryType)
	}
	queryText += ` GROUP BY m.id ORDER BY entity_hits DESC, m.created_at DESC LIMIT ?`
	args = append(args, limit)
	rows, err := backend.db.QueryContext(ctx, queryText, args...)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	results := []*memoryv1.SearchResult{}
	for rows.Next() {
		item, score, err := scanMemoryWithScore(rows)
		if err != nil {
			return nil, err
		}
		results = append(results, &memoryv1.SearchResult{Item: item, Score: score, MatchedBy: []string{"entity"}})
	}
	return results, rows.Err()
}

func (backend *Backend) SearchByVector(ctx context.Context, embedding []float32, limit int32, memoryType string) ([]*memoryv1.SearchResult, error) {
	queryText := `
		SELECT m.*, v.embedding_json
		FROM memories m
		JOIN memory_vectors v ON v.memory_id = m.id
		WHERE m.deleted_at IS NULL`
	args := []any{}
	if memoryType != "" {
		queryText += ` AND m.memory_type = ?`
		args = append(args, memoryType)
	}
	rows, err := backend.db.QueryContext(ctx, queryText, args...)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	results := []*memoryv1.SearchResult{}
	for rows.Next() {
		item, err := scanMemoryRows(rows)
		if err != nil {
			return nil, err
		}
		score := cosineSimilarity(item.Embedding, embedding)
		results = append(results, &memoryv1.SearchResult{Item: item, Score: score, MatchedBy: []string{"semantic"}})
	}
	sort.Slice(results, func(i, j int) bool { return results[i].Score > results[j].Score })
	if len(results) > int(limit) {
		results = results[:limit]
	}
	return results, nil
}

func (backend *Backend) TraceAncestors(ctx context.Context, memoryID string, maxDepth int32) ([]*memoryv1.MemoryItem, error) {
	rows, err := backend.db.QueryContext(ctx, `
		WITH RECURSIVE ancestors(id, depth) AS (
			SELECT causal_parent_id, 1
			FROM memories
			WHERE id = ? AND causal_parent_id IS NOT NULL
			UNION ALL
			SELECT m.causal_parent_id, a.depth + 1
			FROM ancestors a
			JOIN memories m ON m.id = a.id
			WHERE a.depth < ? AND m.causal_parent_id IS NOT NULL
		)
		SELECT m.*, v.embedding_json
		FROM ancestors a
		JOIN memories m ON m.id = a.id
		LEFT JOIN memory_vectors v ON v.memory_id = m.id
		WHERE m.deleted_at IS NULL
		ORDER BY a.depth ASC`, memoryID, maxDepth)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	items := []*memoryv1.MemoryItem{}
	for rows.Next() {
		item, err := scanMemoryRows(rows)
		if err != nil {
			return nil, err
		}
		items = append(items, item)
	}
	return items, rows.Err()
}

func (backend *Backend) TraceDescendants(ctx context.Context, memoryID string, maxDepth int32) ([]*memoryv1.MemoryItem, error) {
	rows, err := backend.db.QueryContext(ctx, `
		WITH RECURSIVE descendants(id, depth) AS (
			SELECT id, 1
			FROM memories
			WHERE causal_parent_id = ?
			UNION ALL
			SELECT m.id, d.depth + 1
			FROM descendants d
			JOIN memories m ON m.causal_parent_id = d.id
			WHERE d.depth < ?
		)
		SELECT m.*, v.embedding_json
		FROM descendants d
		JOIN memories m ON m.id = d.id
		LEFT JOIN memory_vectors v ON v.memory_id = m.id
		WHERE m.deleted_at IS NULL
		ORDER BY d.depth ASC, m.created_at ASC`, memoryID, maxDepth)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	items := []*memoryv1.MemoryItem{}
	for rows.Next() {
		item, err := scanMemoryRows(rows)
		if err != nil {
			return nil, err
		}
		items = append(items, item)
	}
	return items, rows.Err()
}

func (backend *Backend) ListMemories(ctx context.Context, includeDeleted bool) ([]*memoryv1.MemoryItem, error) {
	queryText := `SELECT m.*, v.embedding_json FROM memories m LEFT JOIN memory_vectors v ON v.memory_id = m.id`
	if !includeDeleted {
		queryText += ` WHERE m.deleted_at IS NULL`
	}
	queryText += ` ORDER BY m.created_at DESC`
	rows, err := backend.db.QueryContext(ctx, queryText)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	items := []*memoryv1.MemoryItem{}
	for rows.Next() {
		item, err := scanMemoryRows(rows)
		if err != nil {
			return nil, err
		}
		items = append(items, item)
	}
	return items, rows.Err()
}

func (backend *Backend) AddRelation(ctx context.Context, edge *memoryv1.RelationEdge) (bool, error) {
	result, err := backend.db.ExecContext(ctx, `INSERT OR IGNORE INTO relations (source_id, target_id, relation_type, created_at) VALUES (?, ?, ?, ?)`, edge.SourceId, edge.TargetId, edge.RelationType, edge.CreatedAt)
	if err != nil {
		return false, err
	}
	count, err := result.RowsAffected()
	if err != nil {
		return false, err
	}
	return count > 0, nil
}

func (backend *Backend) ListRelations(ctx context.Context, memoryID string) ([]*memoryv1.RelationEdge, error) {
	queryText := `SELECT source_id, target_id, relation_type, created_at FROM relations`
	args := []any{}
	if memoryID != "" {
		queryText += ` WHERE source_id = ? OR target_id = ?`
		args = append(args, memoryID, memoryID)
	}
	queryText += ` ORDER BY created_at DESC`
	rows, err := backend.db.QueryContext(ctx, queryText, args...)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	items := []*memoryv1.RelationEdge{}
	for rows.Next() {
		edge := &memoryv1.RelationEdge{}
		if err := rows.Scan(&edge.SourceId, &edge.TargetId, &edge.RelationType, &edge.CreatedAt); err != nil {
			return nil, err
		}
		items = append(items, edge)
	}
	return items, rows.Err()
}

func (backend *Backend) RelationExistsBetween(ctx context.Context, leftID string, rightID string, relationTypes []string) (bool, error) {
	queryText := `SELECT 1 FROM relations WHERE ((source_id = ? AND target_id = ?) OR (source_id = ? AND target_id = ?))`
	args := []any{leftID, rightID, rightID, leftID}
	if len(relationTypes) > 0 {
		placeholders := strings.TrimSuffix(strings.Repeat("?,", len(relationTypes)), ",")
		queryText += ` AND relation_type IN (` + placeholders + `)`
		for _, relationType := range relationTypes {
			args = append(args, relationType)
		}
	}
	queryText += ` LIMIT 1`
	row := backend.db.QueryRowContext(ctx, queryText, args...)
	var value int
	if err := row.Scan(&value); err != nil {
		if err == sql.ErrNoRows {
			return false, nil
		}
		return false, err
	}
	return true, nil
}

func (backend *Backend) GetEvolutionEvents(ctx context.Context, memoryID string, limit int32) ([]*memoryv1.EvolutionEvent, error) {
	queryText := `SELECT memory_id, event_type, payload_json, created_at FROM evolution_log`
	args := []any{}
	if memoryID != "" {
		queryText += ` WHERE memory_id = ?`
		args = append(args, memoryID)
	}
	queryText += ` ORDER BY created_at DESC LIMIT ?`
	args = append(args, limit)
	rows, err := backend.db.QueryContext(ctx, queryText, args...)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	items := []*memoryv1.EvolutionEvent{}
	for rows.Next() {
		event := &memoryv1.EvolutionEvent{}
		if err := rows.Scan(&event.MemoryId, &event.EventType, &event.PayloadJson, &event.CreatedAt); err != nil {
			return nil, err
		}
		items = append(items, event)
	}
	return items, rows.Err()
}

func (backend *Backend) GetAuditEvents(ctx context.Context, limit int32) ([]*memoryv1.AuditEvent, error) {
	rows, err := backend.db.QueryContext(ctx, `SELECT actor, operation, target_type, target_id, payload_json, created_at FROM audit_log ORDER BY created_at DESC LIMIT ?`, limit)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	items := []*memoryv1.AuditEvent{}
	for rows.Next() {
		event := &memoryv1.AuditEvent{}
		if err := rows.Scan(&event.Actor, &event.Operation, &event.TargetType, &event.TargetId, &event.PayloadJson, &event.CreatedAt); err != nil {
			return nil, err
		}
		items = append(items, event)
	}
	return items, rows.Err()
}

func (backend *Backend) HealthSnapshot(ctx context.Context) (*memoryv1.HealthSnapshot, error) {
	row := backend.db.QueryRowContext(ctx, `
		SELECT
			SUM(CASE WHEN deleted_at IS NULL THEN 1 ELSE 0 END) AS active_memories,
			AVG(CASE WHEN deleted_at IS NULL THEN trust_score END) AS average_trust_score,
			SUM(CASE WHEN deleted_at IS NULL AND julianday('now') - julianday(last_accessed) > 30 THEN 1 ELSE 0 END) AS stale_memories
		FROM memories`)
	var activeMemories sql.NullInt64
	var avgTrust sql.NullFloat64
	var staleMemories sql.NullInt64
	if err := row.Scan(&activeMemories, &avgTrust, &staleMemories); err != nil {
		return nil, err
	}
	orphanRow := backend.db.QueryRowContext(ctx, `
		SELECT COUNT(*) AS orphan_memories
		FROM memories m
		WHERE m.deleted_at IS NULL
		  AND NOT EXISTS (SELECT 1 FROM relations r WHERE r.source_id = m.id OR r.target_id = m.id)
		  AND m.access_count <= 1`)
	var orphanMemories sql.NullInt64
	if err := orphanRow.Scan(&orphanMemories); err != nil {
		return nil, err
	}
	conflictRow := backend.db.QueryRowContext(ctx, `SELECT COUNT(*) AS unresolved_conflicts FROM relations WHERE relation_type = 'contradicts'`)
	var unresolved sql.NullInt64
	if err := conflictRow.Scan(&unresolved); err != nil {
		return nil, err
	}
	auditRow := backend.db.QueryRowContext(ctx, `SELECT COUNT(*) AS audit_events FROM audit_log`)
	var auditEvents sql.NullInt64
	if err := auditRow.Scan(&auditEvents); err != nil {
		return nil, err
	}
	var databaseSize int64
	if backend.DatabasePath != ":memory:" {
		if info, err := os.Stat(backend.DatabasePath); err == nil {
			databaseSize = info.Size()
		}
	}
	snapshot := &memoryv1.HealthSnapshot{
		TotalMemories:       int32(activeMemories.Int64),
		AverageTrustScore:   avgTrust.Float64,
		UnresolvedConflicts: int32(unresolved.Int64),
		AuditEvents:         int32(auditEvents.Int64),
		DatabaseSizeBytes:   databaseSize,
	}
	if activeMemories.Int64 > 0 {
		snapshot.StaleRatio = float64(staleMemories.Int64) / float64(activeMemories.Int64)
		snapshot.OrphanRatio = float64(orphanMemories.Int64) / float64(activeMemories.Int64)
	}
	return snapshot, nil
}

func nullable(value string) any {
	if value == "" {
		return nil
	}
	return value
}

func cosineSimilarity(left []float32, right []float32) float64 {
	if len(left) == 0 || len(right) == 0 {
		return 0
	}
	size := len(left)
	if len(right) < size {
		size = len(right)
	}
	var numerator float64
	var leftNorm float64
	var rightNorm float64
	for index := range size {
		numerator += float64(left[index] * right[index])
		leftNorm += float64(left[index] * left[index])
		rightNorm += float64(right[index] * right[index])
	}
	if leftNorm == 0 || rightNorm == 0 {
		return 0
	}
	return numerator / (math.Sqrt(leftNorm) * math.Sqrt(rightNorm))
}

func lexicalScore(query string, content string, tags []string) float64 {
	queryTerms := ftsQueryPattern.FindAllString(strings.ToLower(query), -1)
	if len(queryTerms) == 0 {
		return 0
	}
	text := strings.ToLower(content + " " + strings.Join(tags, " "))
	matches := 0
	for _, term := range queryTerms {
		if strings.Contains(text, term) {
			matches++
		}
	}
	return float64(matches) / float64(len(queryTerms))
}

func scanMemory(row *sql.Row) (*memoryv1.MemoryItem, error) {
	item := &memoryv1.MemoryItem{}
	var entityJSON string
	var tagsJSON string
	var embeddingJSON sql.NullString
	var validFrom sql.NullString
	var validUntil sql.NullString
	var causalParentID sql.NullString
	var supersedesID sql.NullString
	var deletedAt sql.NullString
	err := row.Scan(
		&item.Id, &item.Content, &item.MemoryType, &item.CreatedAt, &item.LastAccessed, &item.AccessCount,
		&validFrom, &validUntil, &item.TrustScore, &item.Importance, &item.Layer, &item.DecayRate,
		&item.SourceId, &causalParentID, &supersedesID, &entityJSON, &tagsJSON, &deletedAt, &embeddingJSON,
	)
	if err != nil {
		if err == sql.ErrNoRows {
			return nil, nil
		}
		return nil, err
	}
	populateOptionalFields(item, entityJSON, tagsJSON, embeddingJSON, validFrom, validUntil, causalParentID, supersedesID, deletedAt)
	return item, nil
}

func scanMemoryRows(rows *sql.Rows) (*memoryv1.MemoryItem, error) {
	item := &memoryv1.MemoryItem{}
	var entityJSON string
	var tagsJSON string
	var embeddingJSON sql.NullString
	var validFrom sql.NullString
	var validUntil sql.NullString
	var causalParentID sql.NullString
	var supersedesID sql.NullString
	var deletedAt sql.NullString
	if err := rows.Scan(
		&item.Id, &item.Content, &item.MemoryType, &item.CreatedAt, &item.LastAccessed, &item.AccessCount,
		&validFrom, &validUntil, &item.TrustScore, &item.Importance, &item.Layer, &item.DecayRate,
		&item.SourceId, &causalParentID, &supersedesID, &entityJSON, &tagsJSON, &deletedAt, &embeddingJSON,
	); err != nil {
		return nil, err
	}
	populateOptionalFields(item, entityJSON, tagsJSON, embeddingJSON, validFrom, validUntil, causalParentID, supersedesID, deletedAt)
	return item, nil
}

func scanMemoryWithScore(rows *sql.Rows) (*memoryv1.MemoryItem, float64, error) {
	item := &memoryv1.MemoryItem{}
	var entityJSON string
	var tagsJSON string
	var embeddingJSON sql.NullString
	var validFrom sql.NullString
	var validUntil sql.NullString
	var causalParentID sql.NullString
	var supersedesID sql.NullString
	var deletedAt sql.NullString
	var score float64
	if err := rows.Scan(
		&item.Id, &item.Content, &item.MemoryType, &item.CreatedAt, &item.LastAccessed, &item.AccessCount,
		&validFrom, &validUntil, &item.TrustScore, &item.Importance, &item.Layer, &item.DecayRate,
		&item.SourceId, &causalParentID, &supersedesID, &entityJSON, &tagsJSON, &deletedAt, &embeddingJSON, &score,
	); err != nil {
		return nil, 0, err
	}
	populateOptionalFields(item, entityJSON, tagsJSON, embeddingJSON, validFrom, validUntil, causalParentID, supersedesID, deletedAt)
	return item, score, nil
}

func populateOptionalFields(
	item *memoryv1.MemoryItem,
	entityJSON string,
	tagsJSON string,
	embeddingJSON sql.NullString,
	validFrom sql.NullString,
	validUntil sql.NullString,
	causalParentID sql.NullString,
	supersedesID sql.NullString,
	deletedAt sql.NullString,
) {
	_ = json.Unmarshal([]byte(entityJSON), &item.EntityRefs)
	_ = json.Unmarshal([]byte(tagsJSON), &item.Tags)
	if embeddingJSON.Valid {
		_ = json.Unmarshal([]byte(embeddingJSON.String), &item.Embedding)
	}
	if validFrom.Valid {
		item.ValidFrom = validFrom.String
	}
	if validUntil.Valid {
		item.ValidUntil = validUntil.String
	}
	if causalParentID.Valid {
		item.CausalParentId = causalParentID.String
	}
	if supersedesID.Valid {
		item.SupersedesId = supersedesID.String
	}
	if deletedAt.Valid {
		item.DeletedAt = deletedAt.String
	}
}

func appendEvolution(ctx context.Context, db *sql.DB, memoryID string, eventType string, payload map[string]any) error {
	payloadJSON, err := json.Marshal(payload)
	if err != nil {
		return err
	}
	_, err = db.ExecContext(ctx, `INSERT INTO evolution_log (memory_id, event_type, payload_json, created_at) VALUES (?, ?, ?, ?)`, memoryID, eventType, string(payloadJSON), time.Now().UTC().Format(time.RFC3339Nano))
	return err
}

func appendEvolutionTx(ctx context.Context, tx *sql.Tx, memoryID string, eventType string, payload map[string]any) error {
	payloadJSON, err := json.Marshal(payload)
	if err != nil {
		return err
	}
	_, err = tx.ExecContext(ctx, `INSERT INTO evolution_log (memory_id, event_type, payload_json, created_at) VALUES (?, ?, ?, ?)`, memoryID, eventType, string(payloadJSON), time.Now().UTC().Format(time.RFC3339Nano))
	return err
}

func appendAudit(ctx context.Context, db *sql.DB, actor string, operation string, targetType string, targetID string, payload map[string]any) error {
	payloadJSON, err := json.Marshal(payload)
	if err != nil {
		return err
	}
	_, err = db.ExecContext(ctx, `INSERT INTO audit_log (actor, operation, target_type, target_id, payload_json, created_at) VALUES (?, ?, ?, ?, ?, ?)`, actor, operation, targetType, targetID, string(payloadJSON), time.Now().UTC().Format(time.RFC3339Nano))
	return err
}

func appendAuditTx(ctx context.Context, tx *sql.Tx, actor string, operation string, targetType string, targetID string, payload map[string]any) error {
	payloadJSON, err := json.Marshal(payload)
	if err != nil {
		return err
	}
	_, err = tx.ExecContext(ctx, `INSERT INTO audit_log (actor, operation, target_type, target_id, payload_json, created_at) VALUES (?, ?, ?, ?, ?, ?)`, actor, operation, targetType, targetID, string(payloadJSON), time.Now().UTC().Format(time.RFC3339Nano))
	return err
}
