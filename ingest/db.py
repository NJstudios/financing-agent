
import os
import datetime
import psycopg2 # type: ignore
from psycopg2.extras import execute_values # type: ignore

DB_URL = os.getenv("DATABASE_URL")

def get_conn():
    return psycopg2.connect(DB_URL) # connecting to database

def store_filing(cik: str, accession: str, form: str, sha256: str) -> int:
    """
    Inserts into filings, returns filing_id.
    """
    sql = """
    INSERT INTO filings (cik, accession, form, sha256)
    VALUES (%s, %s, %s, %s)
    ON CONFLICT (accession) DO UPDATE
      SET sha256 = EXCLUDED.sha256
    RETURNING filing_id
    """

    with get_conn() as conn, conn.cursor() as cur: 
        cur.execute(sql, (cik, accession, form, sha256))
        return cur.fetchone()[0] # returning ID
    
def store_metrics(filing_id: int, metrics: dict[str, float | None]) -> None:
    """
    Upserts wide metrics and tall metric_points.
    """

    cols = ", ".join(metrics.keys())
    vals = [metrics[k] for k in metrics]
    placeholders = ", ".join(["%s"] * len(vals))
    upsert_sql = f"""
    INSERT INTO filing_metrics (filing_id, {cols})
    VALUES (%s, {placeholders})
    ON CONFLICT (filing_id) DO UPDATE SET
      {", ".join(f"{k}=EXCLUDED.{k}" for k in metrics)}
    """
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(upsert_sql, [filing_id]+vals)

        points = [
            (filing_id, metric, metrics[metric], datetime.datetime.utcnow())
            for metric in metrics
            if metrics[metric] is not None
        ]
        execute_values(cur,
            """
            INSERT INTO metric_points (filing_id, metric_name, metric_value, captured_at)
            VALUES %s
            ON CONFLICT (filing_id, metric_name) DO UPDATE
              SET metric_value = EXCLUDED.metric_value,
                  captured_at   = EXCLUDED.captured_at
            """,
            points
        )
        conn.commit()