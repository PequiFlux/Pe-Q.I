CREATE TABLE IF NOT EXISTS decision_records (
    decision_id TEXT PRIMARY KEY,
    request_id TEXT NOT NULL,
    scenario_id TEXT NOT NULL,
    variant TEXT NOT NULL,
    decision_status TEXT NOT NULL,
    recommended_truck_id TEXT,
    recommended_destination_id TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS audit_records (
    decision_id TEXT PRIMARY KEY,
    audit_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS operator_actions (
    action_id TEXT PRIMARY KEY,
    decision_id TEXT NOT NULL,
    action_type TEXT NOT NULL,
    reason TEXT NOT NULL,
    before_json TEXT NOT NULL,
    after_json TEXT NOT NULL,
    actor_id TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS benchmark_runs (
    run_id TEXT PRIMARY KEY,
    variant TEXT NOT NULL,
    scenario_id TEXT NOT NULL,
    metrics_json TEXT NOT NULL,
    success_flag INTEGER NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS artifact_index (
    artifact_ref TEXT PRIMARY KEY,
    sha256 TEXT NOT NULL,
    content_type TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

