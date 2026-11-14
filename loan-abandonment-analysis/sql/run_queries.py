"""Run the analysis queries in 02_analysis_queries.sql against the SQLite DB produced by the ETL.
Usage (repo root):  python sql/run_queries.py
"""
import sqlite3
from pathlib import Path

db = Path("data/processed/loan_abandonment.db")
queries = [q.strip() for q in Path("sql/02_analysis_queries.sql").read_text().split(";") if "SELECT" in q]
with sqlite3.connect(db) as con:
    for i, q in enumerate(queries, 1):
        title = next((l for l in q.splitlines() if l.startswith("--")), f"-- Query {i}")
        cur = con.execute(q)
        cols = [d[0] for d in cur.description]
        rows = cur.fetchall()
        print(f"\n{title}\n  " + " | ".join(cols))
        for r in rows[:8]:
            print("  " + " | ".join(str(x) for x in r))
