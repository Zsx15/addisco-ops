# Schéma de base de données recommandé

## Table attempts

```sql
CREATE TABLE IF NOT EXISTS attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT DEFAULT 'default',
    document_id INTEGER,
    question TEXT NOT NULL,
    user_answer TEXT,
    expected_answer TEXT,
    correction TEXT,
    score REAL,
    error_type TEXT,
    topic TEXT,
    pedagogy_type TEXT,
    response_time_seconds REAL,
    success_after_retry INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Table documents

```sql
CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT,
    source_type TEXT,
    raw_text TEXT,
    cleaned_text TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Table chunks

```sql
CREATE TABLE IF NOT EXISTS chunks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id INTEGER,
    chunk_index INTEGER,
    section_title TEXT,
    chunk_text TEXT,
    embedding_id TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(document_id) REFERENCES documents(id)
);
```

## Table learning_profile

```sql
CREATE TABLE IF NOT EXISTS learning_profile (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT DEFAULT 'default',
    logical_efficiency REAL DEFAULT 0,
    procedural_efficiency REAL DEFAULT 0,
    narrative_efficiency REAL DEFAULT 0,
    analogy_efficiency REAL DEFAULT 0,
    preferred_pedagogy TEXT,
    fragile_topics TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```
