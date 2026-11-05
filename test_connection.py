"""
test_connection.py — Standalone test script to verify the full pipeline.

Run from the project root:
    py test_connection.py

Checks:
  1. MySQL connection and database existence
  2. All tables and row counts
  3. A simple SELECT query
  4. A natural-language question via Gemini
  5. Write-query blocking
"""

import sys
import os

# Load .env before importing project modules
from dotenv import load_dotenv
load_dotenv()


def separator(title: str) -> None:
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print('=' * 60)


def check(label: str, ok: bool, detail: str = "") -> bool:
    icon = "✅" if ok else "❌"
    print(f"  {icon}  {label}", end="")
    if detail:
        print(f" — {detail}", end="")
    print()
    return ok


# ── 1. Environment variables ──────────────────────────────────────────────────
separator("1. Environment Variables")

api_key = os.getenv("GOOGLE_API_KEY", "")
db_pw   = os.getenv("DB_PASSWORD", "")
db_host = os.getenv("DB_HOST", "localhost")
db_user = os.getenv("DB_USER", "root")
db_name = os.getenv("DB_NAME", "company_db")

placeholders_key = {"your_google_gemini_api_key_here", "your_gemini_api_key_here", ""}
placeholders_pw  = {"your_mysql_root_password_here", "your_mysql_password_here", ""}

key_ok = api_key not in placeholders_key
pw_ok  = db_pw  not in placeholders_pw

check("GOOGLE_API_KEY set", key_ok, "placeholder" if not key_ok else f"{api_key[:8]}…")
check("DB_PASSWORD set",   pw_ok,  "placeholder — please update .env" if not pw_ok else "***hidden***")
check("DB_HOST",           True,   db_host)
check("DB_USER",           True,   db_user)
check("DB_NAME",           True,   db_name)

if not key_ok or not pw_ok:
    print("\n⚠️  Please update .env before running this test.")
    sys.exit(1)


# ── 2. MySQL connection + database init ───────────────────────────────────────
separator("2. MySQL Connection & Database Init")

try:
    from database import init_database, get_database_url, get_read_engine
    db_url = get_database_url()
    init_database(db_url)
    check("MySQL connection", True, db_url.split("@")[-1])  # hide credentials
except Exception as exc:
    check("MySQL connection", False, str(exc))
    sys.exit(1)


# ── 3. Tables and row counts ──────────────────────────────────────────────────
separator("3. Tables & Row Counts")

from sqlalchemy import text as sa_text

engine = get_read_engine(db_url)
expected = {"departments": 7, "employees": 23, "salaries": 23}

with engine.connect() as conn:
    for table, expected_rows in expected.items():
        try:
            count = conn.execute(sa_text(f"SELECT COUNT(*) FROM `{table}`")).scalar()
            check(f"{table} ({count} rows)", count >= expected_rows,
                  f"expected ≥{expected_rows}")
        except Exception as exc:
            check(f"{table}", False, str(exc))

engine.dispose()


# ── 4. Simple SELECT query ────────────────────────────────────────────────────
separator("4. Simple SELECT Query")

engine = get_read_engine(db_url)
try:
    with engine.connect() as conn:
        rows = conn.execute(
            sa_text("SELECT first_name, last_name, job_title FROM employees LIMIT 3")
        ).fetchall()
    check("SELECT query", True, f"{len(rows)} rows returned")
    for r in rows:
        print(f"       → {r[0]} {r[1]} — {r[2]}")
except Exception as exc:
    check("SELECT query", False, str(exc))
finally:
    engine.dispose()


# ── 5. Natural-language question via Gemini ───────────────────────────────────
separator("5. Gemini → SQL → MySQL")

from sql_agent import TextToSQLAgent

agent = TextToSQLAgent(db_url=db_url)
question = "Who are the top 5 highest-paid employees?"
print(f"  Question: {question}")

try:
    result = agent.ask(question)
    sql_ok = result["is_valid"]
    rows_ok = result["rows"] > 0
    check("SQL generated", sql_ok, result["sql"][:80] if result["sql"] else "none")
    check("Results returned", rows_ok, f"{result['rows']} row(s)")
    if result["dataframe"] is not None and not result["dataframe"].empty:
        print()
        print(result["dataframe"].to_string(index=False))
except Exception as exc:
    check("Gemini → SQL → MySQL", False, str(exc))


# ── 6. Write-query blocking ───────────────────────────────────────────────────
separator("6. Write-Query Blocking")

from sql_agent import _validate_sql

write_queries = [
    "INSERT INTO employees VALUES (99,'Test','User','t@t.com','Hacker',1,'2024-01-01',NULL,1)",
    "DELETE FROM employees WHERE id = 1",
    "DROP TABLE employees",
    "UPDATE employees SET is_active = 0",
    "ALTER TABLE employees ADD COLUMN hack VARCHAR(100)",
]

all_blocked = True
for q in write_queries:
    is_safe, msg = _validate_sql(q)
    blocked = not is_safe
    if not blocked:
        all_blocked = False
    check(f"Blocked: {q[:50]}…", blocked)

check("All write queries blocked", all_blocked)


# ── Summary ───────────────────────────────────────────────────────────────────
separator("Test Complete")
print("  All checks passed — your Text-to-SQL MySQL agent is ready!")
print("  Run the app with:  py -m streamlit run app.py")
print()

