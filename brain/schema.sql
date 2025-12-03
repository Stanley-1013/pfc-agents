-- =============================================================================
-- NEUROMORPHIC BRAIN DATABASE SCHEMA
-- Version: 1.0.0
-- =============================================================================

-- 任務管理
CREATE TABLE IF NOT EXISTS tasks (
    id TEXT PRIMARY KEY,
    parent_id TEXT,
    project TEXT,
    description TEXT NOT NULL,
    status TEXT DEFAULT 'pending',
    priority INTEGER DEFAULT 5,
    assigned_agent TEXT,
    result TEXT,
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    -- 任務生命週期欄位
    phase TEXT DEFAULT 'execution',  -- execution, validation, documentation, completed
    requires_validation INTEGER DEFAULT 1,  -- 0=不需要, 1=需要驗證
    validation_status TEXT,  -- pending, approved, rejected, skipped
    validator_task_id TEXT,  -- 關聯的 critic 驗證任務 ID
    -- 時間戳記
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    FOREIGN KEY (parent_id) REFERENCES tasks(id),
    FOREIGN KEY (validator_task_id) REFERENCES tasks(id)
);

-- 任務依賴
CREATE TABLE IF NOT EXISTS task_dependencies (
    task_id TEXT,
    depends_on_task_id TEXT,
    PRIMARY KEY (task_id, depends_on_task_id),
    FOREIGN KEY (task_id) REFERENCES tasks(id),
    FOREIGN KEY (depends_on_task_id) REFERENCES tasks(id)
);

-- 工作記憶
CREATE TABLE IF NOT EXISTS working_memory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT,
    project TEXT,
    key TEXT NOT NULL,
    value TEXT,
    data_type TEXT DEFAULT 'string',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    FOREIGN KEY (task_id) REFERENCES tasks(id)
);

-- 長期記憶
CREATE TABLE IF NOT EXISTS long_term_memory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category TEXT NOT NULL,
    subcategory TEXT,
    project TEXT,
    title TEXT,
    content TEXT NOT NULL,
    importance INTEGER DEFAULT 5,
    access_count INTEGER DEFAULT 0,
    last_accessed TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'active',
    superseded_by INTEGER REFERENCES long_term_memory(id),
    last_validated TIMESTAMP
);

-- 情節記憶
CREATE TABLE IF NOT EXISTS episodes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project TEXT,
    session_id TEXT,
    event_type TEXT,
    summary TEXT NOT NULL,
    details TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Checkpoint
CREATE TABLE IF NOT EXISTS checkpoints (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project TEXT,
    task_id TEXT,
    agent TEXT,
    state TEXT NOT NULL,
    context_summary TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (task_id) REFERENCES tasks(id)
);

-- Agent 日誌
CREATE TABLE IF NOT EXISTS agent_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent TEXT NOT NULL,
    task_id TEXT,
    action TEXT,
    message TEXT,
    duration_ms INTEGER,
    tokens_used INTEGER,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (task_id) REFERENCES tasks(id)
);

-- FTS5 全文搜尋
CREATE VIRTUAL TABLE IF NOT EXISTS memory_fts USING fts5(
    content,
    category,
    project
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_project ON tasks(project);
CREATE INDEX IF NOT EXISTS idx_tasks_parent ON tasks(parent_id);
CREATE INDEX IF NOT EXISTS idx_working_memory_task ON working_memory(task_id);
CREATE INDEX IF NOT EXISTS idx_working_memory_key ON working_memory(key);
CREATE INDEX IF NOT EXISTS idx_long_term_category ON long_term_memory(category);
CREATE INDEX IF NOT EXISTS idx_long_term_status ON long_term_memory(status);
CREATE INDEX IF NOT EXISTS idx_episodes_project ON episodes(project);

-- FTS 觸發器
CREATE TRIGGER IF NOT EXISTS ltm_ai AFTER INSERT ON long_term_memory BEGIN
    INSERT INTO memory_fts(rowid, content, category, project)
    VALUES (NEW.id, NEW.content, NEW.category, NEW.project);
END;

CREATE TRIGGER IF NOT EXISTS ltm_ad AFTER DELETE ON long_term_memory BEGIN
    DELETE FROM memory_fts WHERE rowid = OLD.id;
END;

CREATE TRIGGER IF NOT EXISTS ltm_au AFTER UPDATE ON long_term_memory BEGIN
    DELETE FROM memory_fts WHERE rowid = OLD.id;
    INSERT INTO memory_fts(rowid, content, category, project)
    VALUES (NEW.id, NEW.content, NEW.category, NEW.project);
END;
