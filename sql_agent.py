"""
sql_agent.py — LLM-powered Text-to-SQL translation and safe query execution.

Responsibilities
----------------
* Load Groq via LangChain.
* Build a prompt that includes the full SQLite schema + sample rows so the
  model has enough context to write accurate SQLite SQL.
* Parse the model response and extract a clean SQL statement.
* Validate that only safe SELECT queries are allowed (block all DML/DDL).
* Execute the query against SQLite and return results as a Pandas DataFrame.
"""

import re
import logging
import os
from typing import Tuple, Optional

import pandas as pd
from sqlalchemy import text
from langchain_core.messages import HumanMessage, SystemMessage
from dotenv import load_dotenv

from database import get_read_engine, get_schema_info, get_table_sample, get_database_url

load_dotenv(override=True)
logger = logging.getLogger(__name__)


# ─── Safety constants ─────────────────────────────────────────────────────────

_FORBIDDEN_KEYWORDS = {
    "INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE", "TRUNCATE",
    "REPLACE", "MERGE", "EXEC", "EXECUTE", "GRANT", "REVOKE",
    "LOAD", "OUTFILE", "DUMPFILE", "INTO OUTFILE", "INTO DUMPFILE",
}

_MAX_ROWS = 1000   # hard cap on returned rows


# ─── LLM factory ──────────────────────────────────────────────────────────────

def _load_llm():
    """Return an initialized LangChain Groq model."""

    api_key = os.getenv("GROQ_API_KEY", "")

    if not api_key or api_key == "your_groq_api_key_here":
        raise ValueError(
            "GROQ_API_KEY is missing from your .env file."
        )

    model = os.getenv(
        "GROQ_MODEL",
        "openai/gpt-oss-120b"
    )

    from langchain_groq import ChatGroq

    return ChatGroq(
        model=model,
        groq_api_key=api_key,
        temperature=0,
        max_tokens=256,
        timeout=30,
        max_retries=1
    )


# ─── System prompt builder ────────────────────────────────────────────────────

_SYSTEM_PROMPT_TEMPLATE = """\
You are an expert SQLite SQL assistant.
Your ONLY job is to convert the user's natural-language question into a single
valid SQLite SELECT query for the database described below.

STRICT RULES — follow every one:
1. Output ONLY a raw SQL SELECT statement.
   - No markdown code fences (no ``` or ```sql).
   - No explanations, comments, or prose before or after the SQL.
   - No trailing semicolon.
2. NEVER output INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, TRUNCATE,
   REPLACE, MERGE, EXEC, GRANT, REVOKE, LOAD, or any data-modification statement.
3. Use table and column names EXACTLY as shown in the schema below.
4. Use double quotes for identifiers only when needed; do not use MySQL-specific syntax.
5. Use explicit JOIN ... ON ... syntax (never implicit comma joins).
6. Add LIMIT {max_rows} if the query could return many rows.
7. Use SQLite-compatible syntax:
   - Date functions: date(), datetime(), strftime(), julianday()
   - Current date: date('now')
   - String functions: LIKE, LOWER(), UPPER(), SUBSTR()
   - String concatenation: ||
   - NULL handling: IS NULL, IS NOT NULL, COALESCE(), IFNULL()
   - Do not use MySQL-only functions such as YEAR(), MONTH(), DATE_FORMAT(),
     CURDATE(), or CONCAT().
8. If the question cannot be answered with the available schema, output exactly:
   UNABLE_TO_ANSWER

{schema}

SAMPLE DATA (a few rows from each table)
-----------------------------------------
{samples}
"""


def _build_system_prompt(db_url: Optional[str] = None) -> str:
    """Build the full system prompt with the live schema and sample rows."""
    schema = get_schema_info(db_url)
    samples_parts = []
    for table in ["departments", "employees", "salaries"]:
        samples_parts.append(
            f"-- {table} --\n{get_table_sample(table, db_url=db_url)}"
        )
    samples = "\n\n".join(samples_parts)
    return _SYSTEM_PROMPT_TEMPLATE.format(
        max_rows=_MAX_ROWS,
        schema=schema,
        samples=samples,
    )


# ─── SQL extraction & validation ──────────────────────────────────────────────
def _content_to_text(content) -> str:
    """Convert the model response content into plain text."""
    if isinstance(content, str):
        return content.strip()

    if isinstance(content, list):
        text_parts = []

        for item in content:
            if isinstance(item, str):
                text_parts.append(item)
            elif isinstance(item, dict):
                if item.get("type") == "text":
                    text_parts.append(item.get("text", ""))

        return "\n".join(text_parts).strip()

    return str(content).strip()
def _extract_sql(raw: str) -> str:
    """Strip markdown fences, backtick wrappers, and prose; return clean SQL."""
    # Remove ```sql … ``` or ``` … ```
    raw = re.sub(r"```(?:sql)?", "", raw, flags=re.IGNORECASE)
    raw = raw.strip().strip("`").strip()

    # Keep only the first statement (stop at a blank line)
    lines    = [ln.rstrip() for ln in raw.splitlines()]
    sql_lines = []
    for ln in lines:
        if ln == "" and sql_lines:
            break
        sql_lines.append(ln)

    return " ".join(sql_lines).strip().rstrip(";")


def _validate_sql(sql: str) -> Tuple[bool, str]:
    """Return (is_safe, error_message).

    Checks:
    * Not the UNABLE_TO_ANSWER sentinel.
    * Starts with SELECT or WITH (for CTEs).
    * Does not contain any forbidden keyword as a whole word.
    """
    if sql.upper().strip() == "UNABLE_TO_ANSWER":
        return False, "The question could not be answered with the available data."

    upper = sql.upper()

    if not re.match(r"^\s*(SELECT|WITH)\b", upper):
        return False, (
            "Generated query does not start with SELECT. "
            "Only read-only SELECT queries are permitted."
        )

    for kw in _FORBIDDEN_KEYWORDS:
        # Match as a whole word
        pattern = rf"\b{re.escape(kw)}\b"
        if re.search(pattern, upper):
            return False, (
                f"Query contains a forbidden keyword: {kw}. "
                "Only read-only SELECT queries are permitted."
            )

    return True, ""


# ─── Main public class ────────────────────────────────────────────────────────

class TextToSQLAgent:
    """Stateful agent: English question → SQLite SQL → results DataFrame."""

    def __init__(self, db_url: Optional[str] = None):
        self.db_url = db_url or get_database_url()
        self._llm   = None   # lazy-loaded on first use

    @property
    def llm(self):
        if self._llm is None:
            self._llm = _load_llm()
        return self._llm

    # ── Step 1: Generate SQL ──────────────────────────────────────────────────

    def generate_sql(self, user_question: str) -> Tuple[str, str]:
        """Return (sql, raw_llm_response).

        Raises ValueError if the LLM is not configured.
        Raises ConnectionError if the Groq API is unreachable.
        """
        system_prompt = _build_system_prompt(self.db_url)
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_question),
        ]
        try:
            response = self.llm.invoke(messages)
        except Exception as exc:
            err_str = str(exc).lower()
            if "api key" in err_str or "authentication" in err_str or "401" in err_str:
                raise ValueError(
                    "Groq API authentication failed. Check GROQ_API_KEY in your "
                    "Streamlit Secrets or local .env file."
                ) from exc
            if "quota" in err_str or "429" in err_str or "rate limit" in err_str:
                raise ConnectionError(
                    "Groq rate limit or quota reached. Wait and try again, or "
                    "check your usage at https://console.groq.com."
                ) from exc
            if "connection" in err_str or "timeout" in err_str or "network" in err_str:
                raise ConnectionError(
                    "Cannot reach the Groq API. Check your internet connection."
                ) from exc
            raise

        raw = _content_to_text(response.content)

        if not raw:
            raise ValueError("Groq returned an empty response. Please try again.")

        sql = _extract_sql(raw)
        return sql, raw

    # ── Step 2: Validate SQL ──────────────────────────────────────────────────

    def validate_sql(self, sql: str) -> Tuple[bool, str]:
        return _validate_sql(sql)

    # ── Step 3: Execute SQL ───────────────────────────────────────────────────

    def execute_sql(self, sql: str) -> Tuple[pd.DataFrame, str]:
        """Execute a validated SELECT statement and return (DataFrame, status_msg).

        Always uses the read engine.  Returns an empty DataFrame on error.
        """
        engine = get_read_engine(self.db_url)
        try:
            with engine.connect() as conn:
                result = conn.execute(text(sql))
                rows   = result.fetchmany(_MAX_ROWS)
                cols   = list(result.keys())
            df = pd.DataFrame(rows, columns=cols)
            n  = len(df)
            status = (
                f"✅ Query executed successfully — "
                f"{n} row{'s' if n != 1 else ''} returned."
            )
            return df, status
        except Exception as exc:
            logger.error("SQL execution error: %s", exc)
            friendly = _friendly_error(str(exc))
            return pd.DataFrame(), f"❌ {friendly}"
        finally:
            engine.dispose()

    # ── High-level convenience ────────────────────────────────────────────────

    def ask(self, question: str) -> dict:
        """Full pipeline: question → SQL → validation → execution → results.

        Returns a dict with keys:
            question, sql, raw_llm, is_valid, validation_error,
            dataframe, status, rows
        """
        result: dict = {
            "question":         question,
            "sql":              "",
            "raw_llm":          "",
            "is_valid":         False,
            "validation_error": "",
            "dataframe":        pd.DataFrame(),
            "status":           "",
            "rows":             0,
        }

        # ── 1. Generate ──────────────────────────────────────────────────────
        try:
            sql, raw = self.generate_sql(question)
        except (ValueError, ConnectionError) as exc:
            result["status"] = f"❌ {exc}"
            raise   # re-raise so app.py can show a targeted message
        except Exception as exc:
            result["status"] = f"❌ LLM Error: {exc}"
            return result

        result["sql"]     = sql
        result["raw_llm"] = raw

        # ── 2. Validate ──────────────────────────────────────────────────────
        is_valid, err = self.validate_sql(sql)
        result["is_valid"]         = is_valid
        result["validation_error"] = err

        if not is_valid:
            result["status"] = f"⛔ Validation failed: {err}"
            return result

        # ── 3. Execute ───────────────────────────────────────────────────────
        df, status        = self.execute_sql(sql)
        result["dataframe"] = df
        result["status"]    = status
        result["rows"]      = len(df)

        return result


# ─── Error formatting ─────────────────────────────────────────────────────────

def _friendly_error(raw: str) -> str:
    """Convert SQLite errors into user-friendly messages."""
    low = raw.lower()

    if "no such table" in low:
        match = re.search(r"no such table:\\s*([\\w.]+)", raw, re.IGNORECASE)
        name = match.group(1) if match else "unknown"
        return f"Table '{name}' does not exist in the SQLite database."

    if "no such column" in low:
        match = re.search(r"no such column:\\s*([\\w.]+)", raw, re.IGNORECASE)
        name = match.group(1) if match else "unknown"
        return f"Column '{name}' does not exist in the table."

    if "syntax error" in low or "no such function" in low:
        return "SQLite query error. Please rephrase your question."

    if "unable to open database file" in low:
        return (
            "SQLite cannot open its database file. Check that the app has "
            "permission to write to its project directory."
        )

    if "database is locked" in low:
        return "The SQLite database is busy. Please try again."

    if "operationalerror" in low:
        return f"SQLite operational error: {raw}"

    return raw
