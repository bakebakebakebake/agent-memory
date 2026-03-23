PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS memories (
    id TEXT PRIMARY KEY,
    content TEXT NOT NULL,
    memory_type TEXT NOT NULL,
    created_at TEXT NOT NULL,
    last_accessed TEXT NOT NULL,
    access_count INTEGER NOT NULL DEFAULT 0,
    valid_from TEXT,
    valid_until TEXT,
    trust_score REAL NOT NULL,
    importance REAL NOT NULL,
    layer TEXT NOT NULL,
    decay_rate REAL NOT NULL,
    source_id TEXT NOT NULL,
    causal_parent_id TEXT REFERENCES memories(id),
    supersedes_id TEXT REFERENCES memories(id),
    entity_refs_json TEXT NOT NULL,
    tags_json TEXT NOT NULL,
    deleted_at TEXT
);

CREATE TABLE IF NOT EXISTS memory_vectors (
    memory_id TEXT PRIMARY KEY REFERENCES memories(id) ON DELETE CASCADE,
    memory_rowid INTEGER UNIQUE,
    embedding_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS backend_meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS entity_index (
    entity TEXT NOT NULL,
    memory_id TEXT NOT NULL REFERENCES memories(id) ON DELETE CASCADE,
    PRIMARY KEY (entity, memory_id)
);

CREATE TABLE IF NOT EXISTS relations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id TEXT NOT NULL REFERENCES memories(id) ON DELETE CASCADE,
    target_id TEXT NOT NULL REFERENCES memories(id) ON DELETE CASCADE,
    relation_type TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE (source_id, target_id, relation_type)
);

CREATE TABLE IF NOT EXISTS evolution_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    memory_id TEXT NOT NULL REFERENCES memories(id) ON DELETE CASCADE,
    event_type TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    actor TEXT NOT NULL,
    operation TEXT NOT NULL,
    target_type TEXT NOT NULL,
    target_id TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_memories_memory_type ON memories(memory_type);
CREATE INDEX IF NOT EXISTS idx_memories_layer ON memories(layer);
CREATE INDEX IF NOT EXISTS idx_memories_created_at ON memories(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_memories_last_accessed ON memories(last_accessed DESC);
CREATE INDEX IF NOT EXISTS idx_memories_trust_score ON memories(trust_score DESC);
CREATE INDEX IF NOT EXISTS idx_memories_source_id ON memories(source_id);
CREATE INDEX IF NOT EXISTS idx_memories_causal_parent_id ON memories(causal_parent_id);
CREATE INDEX IF NOT EXISTS idx_memories_supersedes_id ON memories(supersedes_id);
CREATE INDEX IF NOT EXISTS idx_memories_deleted_at ON memories(deleted_at);
CREATE INDEX IF NOT EXISTS idx_memories_active_type_created ON memories(deleted_at, memory_type, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_entity_index_memory_id ON entity_index(memory_id);
CREATE INDEX IF NOT EXISTS idx_relations_source_type ON relations(source_id, relation_type);
CREATE INDEX IF NOT EXISTS idx_relations_target_type ON relations(target_id, relation_type);
CREATE INDEX IF NOT EXISTS idx_evolution_memory_created ON evolution_log(memory_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_target_created ON audit_log(target_id, created_at DESC);

CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts
USING fts5(
    content,
    tags,
    content = 'memories',
    content_rowid = 'rowid'
);

CREATE TRIGGER IF NOT EXISTS memories_ai AFTER INSERT ON memories BEGIN
    INSERT INTO memories_fts(rowid, content, tags)
    VALUES (
        new.rowid,
        new.content,
        trim(replace(replace(replace(replace(new.tags_json, '[', ' '), ']', ' '), '\"', ' '), ',', ' '))
    );
END;

CREATE TRIGGER IF NOT EXISTS memories_ad AFTER DELETE ON memories BEGIN
    INSERT INTO memories_fts(memories_fts, rowid, content, tags)
    VALUES (
        'delete',
        old.rowid,
        old.content,
        trim(replace(replace(replace(replace(old.tags_json, '[', ' '), ']', ' '), '\"', ' '), ',', ' '))
    );
END;

CREATE TRIGGER IF NOT EXISTS memories_au AFTER UPDATE ON memories BEGIN
    INSERT INTO memories_fts(memories_fts, rowid, content, tags)
    VALUES (
        'delete',
        old.rowid,
        old.content,
        trim(replace(replace(replace(replace(old.tags_json, '[', ' '), ']', ' '), '\"', ' '), ',', ' '))
    );
    INSERT INTO memories_fts(rowid, content, tags)
    VALUES (
        new.rowid,
        new.content,
        trim(replace(replace(replace(replace(new.tags_json, '[', ' '), ']', ' '), '\"', ' '), ',', ' '))
    );
END;
