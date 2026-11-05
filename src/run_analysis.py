"""
run_analysis.py - execute every sql/0[1-5]_*.sql file against PostgreSQL and export the result
of each query to outputs/<query_name>.csv  (used by make_charts.py and the README tables).

Connection uses the standard libpq environment variables, so no credentials live in code:
    export PGHOST=localhost PGPORT=5432 PGUSER=postgres PGDATABASE=pricing
    psql -f sql/00_schema_and_load.sql          # one-time: create table + load CSV
    python src/run_analysis.py
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs"
OUT.mkdir(exist_ok=True)

for sql_file in sorted((ROOT / "sql").glob("0[1-5]_*.sql")):
    target = OUT / f"{sql_file.stem}.csv"
    with open(target, "w") as fh:
        res = subprocess.run(["psql", "-X", "-q", "--csv", "-v", "ON_ERROR_STOP=1", "-f", str(sql_file)],
                             stdout=fh, stderr=subprocess.PIPE, text=True)
    if res.returncode != 0:
        sys.exit(f"[FAILED] {sql_file.name}\n{res.stderr}")
    n = sum(1 for _ in open(target)) - 1
    print(f"[ok] {sql_file.name:<36} -> outputs/{target.name} ({n} rows)")
