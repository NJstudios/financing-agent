-- infra/init.sql

-- 1. Filings master table
CREATE TABLE IF NOT EXISTS filings (
  filing_id      SERIAL       PRIMARY KEY,
  cik             TEXT         NOT NULL,
  accession       TEXT         NOT NULL UNIQUE,
  form            TEXT         NOT NULL,
  filed_at        TIMESTAMPTZ  DEFAULT now(),
  sha256          TEXT,
  created_at      TIMESTAMPTZ  DEFAULT now()
);

-- 2. Wide metrics table
CREATE TABLE IF NOT EXISTS filing_metrics (
  filing_id             INT       PRIMARY KEY
                             REFERENCES filings(filing_id) ON DELETE CASCADE,
  revenue               DOUBLE PRECISION,
  gross_profit          DOUBLE PRECISION,
  operating_income      DOUBLE PRECISION,
  net_income            DOUBLE PRECISION,
  operating_cash_flow   DOUBLE PRECISION,
  capital_expenditures  DOUBLE PRECISION,
  total_assets          DOUBLE PRECISION,
  total_liabilities     DOUBLE PRECISION,
  shareholders_equity   DOUBLE PRECISION,
  current_assets        DOUBLE PRECISION,    -- NEW
  current_liabilities   DOUBLE PRECISION,    -- NEW
  cash_and_equivalents  DOUBLE PRECISION,    -- NEW
  created_at            TIMESTAMPTZ DEFAULT now()
);

-- 3. Tall metrics (time-series) table
CREATE TABLE IF NOT EXISTS metric_points (
  filing_id     INT       REFERENCES filings(filing_id) ON DELETE CASCADE,
  metric_name   TEXT      NOT NULL,
  metric_value  DOUBLE PRECISION,
  captured_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (filing_id, metric_name)
);
