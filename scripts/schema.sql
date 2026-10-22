-- Postgres schema for the bank credit-explanation milestone.
-- Instructor-approved substitute for the brief's MongoDB collections;
-- table names and columns mirror brief.md's documented fields exactly.

CREATE TABLE IF NOT EXISTS demo_identities (
    customer_id TEXT PRIMARY KEY,
    demo_token TEXT UNIQUE NOT NULL,
    display_name TEXT,
    scenario TEXT
);
CREATE INDEX IF NOT EXISTS idx_demo_identities_token ON demo_identities (demo_token);

CREATE TABLE IF NOT EXISTS customer_assessments (
    customer_id TEXT PRIMARY KEY,
    status TEXT,
    as_of_date TEXT,
    model_version TEXT,
    risk_probability DOUBLE PRECISION,
    score INTEGER,
    tier TEXT,
    credit_limit_idr BIGINT,
    average_balance_36m DOUBLE PRECISION,
    features JSONB,
    reason_codes JSONB,
    customer_note TEXT
);

CREATE TABLE IF NOT EXISTS monthly_balances (
    customer_id TEXT NOT NULL,
    month TEXT NOT NULL,
    closing_balance_idr BIGINT NOT NULL,
    PRIMARY KEY (customer_id, month)
);
CREATE INDEX IF NOT EXISTS idx_monthly_balances_customer ON monthly_balances (customer_id);
