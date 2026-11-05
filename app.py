"""
app.py — Streamlit front-end for the Text-to-SQL Agent.

Run with:
    streamlit run app.py
"""

import os
import time
import logging

import streamlit as st
import pandas as pd
from dotenv import load_dotenv

from database import init_database, get_schema_info, get_table_sample, get_database_url
from sql_agent import TextToSQLAgent

# ─── Bootstrap ────────────────────────────────────────────────────────────────
load_dotenv()

# Streamlit Community Cloud stores secrets in st.secrets.
# Local development continues to use the project's .env file.
try:
    for secret_name in ("LLM_PROVIDER", "GROQ_API_KEY", "GROQ_MODEL"):
        if secret_name in st.secrets:
            os.environ[secret_name] = str(st.secrets[secret_name])
except Exception:
    # st.secrets may be unavailable during local development.
    pass

logging.basicConfig(level=logging.INFO)

# ─── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Text-to-SQL Agent",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── CSS ──────────────────────────────────────────────────────────────────────
st.markdown(
    """
<style>
/* ── Google Font ── */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

/* ── Root variables ── */
:root {
    --bg-dark:     #0d1117;
    --bg-card:     #161b22;
    --bg-card2:    #1c2130;
    --border:      #30363d;
    --accent:      #7c3aed;
    --accent2:     #a855f7;
    --accent-glow: rgba(124,58,237,.35);
    --success:     #10b981;
    --error:       #ef4444;
    --warning:     #f59e0b;
    --text-primary:#e6edf3;
    --text-muted:  #8b949e;
    --text-accent: #c084fc;
}

html, body, [data-testid="stAppViewContainer"] {
    background: var(--bg-dark);
    font-family: 'Inter', sans-serif;
    color: var(--text-primary);
}
[data-testid="stSidebar"] {
    background: var(--bg-card) !important;
    border-right: 1px solid var(--border);
}

/* ── Header ── */
.hero-header {
    text-align: center;
    padding: 2.5rem 1rem 1.5rem;
}
.hero-header h1 {
    font-size: 2.8rem;
    font-weight: 800;
    background: linear-gradient(135deg, #c084fc, #7c3aed, #4f46e5);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin: 0;
}
.hero-header p {
    color: var(--text-muted);
    font-size: 1.05rem;
    margin-top: .5rem;
}

/* ── Cards ── */
.card {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 1.4rem 1.6rem;
    margin-bottom: 1.2rem;
}
.card-title {
    font-size: .75rem;
    font-weight: 600;
    letter-spacing: .08em;
    text-transform: uppercase;
    color: var(--text-accent);
    margin-bottom: .8rem;
}

/* ── Pill badges ── */
.badge {
    display: inline-block;
    padding: .2rem .65rem;
    border-radius: 999px;
    font-size: .72rem;
    font-weight: 600;
    letter-spacing: .04em;
}
.badge-success { background: rgba(16,185,129,.15); color: var(--success); border: 1px solid rgba(16,185,129,.3); }
.badge-error   { background: rgba(239,68,68,.15);  color: var(--error);   border: 1px solid rgba(239,68,68,.3); }
.badge-warning { background: rgba(245,158,11,.15); color: var(--warning); border: 1px solid rgba(245,158,11,.3); }
.badge-info    { background: rgba(124,58,237,.15); color: var(--accent2); border: 1px solid rgba(124,58,237,.3); }

/* ── SQL display ── */
.sql-box {
    background: #0d1117;
    border: 1px solid #30363d;
    border-left: 3px solid var(--accent);
    border-radius: 8px;
    padding: 1rem 1.2rem;
    font-family: 'JetBrains Mono', 'Consolas', monospace;
    font-size: .88rem;
    color: #e6edf3;
    overflow-x: auto;
    white-space: pre-wrap;
    word-break: break-word;
}

/* ── Stat tiles ── */
.stat-row { display: flex; gap: 1rem; flex-wrap: wrap; margin-bottom: 1.2rem; }
.stat-tile {
    flex: 1; min-width: 120px;
    background: var(--bg-card2);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 1rem;
    text-align: center;
}
.stat-tile .num  { font-size: 1.9rem; font-weight: 700; color: var(--accent2); }
.stat-tile .lbl  { font-size: .72rem; color: var(--text-muted); margin-top: .2rem; }

/* ── Sample question chips ── */
.sample-chip {
    display: inline-block;
    background: rgba(124,58,237,.12);
    border: 1px solid rgba(124,58,237,.3);
    border-radius: 999px;
    padding: .32rem .9rem;
    font-size: .8rem;
    color: var(--text-accent);
    margin: .25rem;
    cursor: pointer;
    transition: background .2s;
}
.sample-chip:hover {
    background: rgba(124,58,237,.3);
}

/* ── Input area ── */
[data-testid="stTextArea"] textarea {
    background: var(--bg-card2) !important;
    border: 1px solid var(--border) !important;
    color: var(--text-primary) !important;
    border-radius: 10px !important;
    font-size: 1rem !important;
}
[data-testid="stTextArea"] textarea:focus {
    border-color: var(--accent) !important;
    box-shadow: 0 0 0 3px var(--accent-glow) !important;
}

/* ── Buttons ── */
[data-testid="stButton"] > button {
    background: linear-gradient(135deg, var(--accent), #4f46e5) !important;
    color: white !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    font-size: .95rem !important;
    padding: .55rem 1.4rem !important;
    transition: transform .15s, box-shadow .15s !important;
    box-shadow: 0 4px 15px var(--accent-glow) !important;
}
[data-testid="stButton"] > button:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 6px 20px var(--accent-glow) !important;
}

/* ── Dataframe ── */
[data-testid="stDataFrame"] {
    border: 1px solid var(--border) !important;
    border-radius: 10px !important;
    overflow: hidden !important;
}

/* ── Sidebar text ── */
.sidebar-section {
    background: #0d1117;
    border: 1px solid #30363d;
    border-radius: 8px;
    padding: .9rem 1rem;
    margin-bottom: 1rem;
    font-size: .82rem;
    color: var(--text-muted);
}
.sidebar-section code {
    background: rgba(124,58,237,.15);
    border-radius: 4px;
    padding: .1rem .4rem;
    color: var(--text-accent);
    font-size: .82rem;
}

/* ── Expander ── */
[data-testid="stExpander"] {
    background: var(--bg-card2) !important;
    border: 1px solid var(--border) !important;
    border-radius: 10px !important;
}
</style>
""",
    unsafe_allow_html=True,
)

# ─── Constants ────────────────────────────────────────────────────────────────

SAMPLE_QUESTIONS = [
    "List all employees with their department names",
    "Who are the top 5 highest-paid employees?",
    "What is the average salary per department?",
    "How many employees are in each department?",
    "Show me all employees hired after 2020",
    "Which department has the highest total budget?",
    "List active employees in the Engineering department",
    "Who earns more than $150,000?",
    "Show the salary history for all employees",
    "Which employees don't have a manager?",
    "What is the total payroll cost per department?",
    "List employees sorted by hire date (newest first)",
]

# ─── Session state ────────────────────────────────────────────────────────────

def _init_state():
    defaults = {
        "question": "",
        "result": None,
        "history": [],
        "db_url": get_database_url(),
        "agent": None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


_init_state()


# ─── Sidebar ──────────────────────────────────────────────────────────────────

def render_sidebar():
    with st.sidebar:
        st.markdown(
            "<div style='font-size:1.3rem;font-weight:700;color:#c084fc;"
            "margin-bottom:1rem;'>⚙️ Configuration</div>",
            unsafe_allow_html=True,
        )

        provider = os.getenv("LLM_PROVIDER", "groq").upper()
        model_env = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
        api_key_configured = bool(os.getenv("GROQ_API_KEY", "").strip())

        st.markdown(
            f"""
<div class="sidebar-section">
  <b>🤖 LLM Provider</b><br/>
  <code>{provider}</code> · <code>{model_env}</code><br/><br/>
  <b>🔑 Groq API Key</b><br/>
  <span class="badge {'badge-success' if api_key_configured else 'badge-warning'}">
    {'Configured' if api_key_configured else 'Not configured'}
  </span><br/><br/>
  <b>🗄️ Database</b><br/>
  <code>SQLite</code> · Local application database
</div>
""",
            unsafe_allow_html=True,
        )

        st.markdown("---")
        st.markdown(
            "<div style='color:#c084fc;font-size:.8rem;font-weight:600;"
            "letter-spacing:.06em;text-transform:uppercase;margin-bottom:.6rem;'>"
            "📋 Database Schema</div>",
            unsafe_allow_html=True,
        )
        with st.expander("View database schema"):
            try:
                schema = get_schema_info(st.session_state.db_url)
                st.code(schema, language="sql")
            except Exception as e:
                st.error(f"Schema error: {e}")

        st.markdown("---")

        if st.session_state.history:
            st.markdown(
                "<div style='color:#c084fc;font-size:.8rem;font-weight:600;"
                "letter-spacing:.06em;text-transform:uppercase;margin-bottom:.6rem;'>"
                "📜 Recent Queries</div>",
                unsafe_allow_html=True,
            )
            for i, h in enumerate(reversed(st.session_state.history[-8:])):
                icon = "✅" if h["success"] else "❌"
                label = (
                    f"{icon} {h['question'][:42]}…"
                    if len(h["question"]) > 42
                    else f"{icon} {h['question']}"
                )
                if st.button(label, key=f"hist_{i}", use_container_width=True):
                    st.session_state.question = h["question"]

        st.markdown("---")
        st.markdown(
            "<div style='font-size:.72rem;color:#8b949e;text-align:center;'>"
            "Text-to-SQL Agent · powered by LangChain<br/>"
            "SQLite database · Only SELECT queries execute safely.</div>",
            unsafe_allow_html=True,
        )


# ─── Main content ─────────────────────────────────────────────────────────────

def render_hero():
    st.markdown(
        """
<div class="hero-header">
  <h1>🤖 Text-to-SQL Agent</h1>
  <p>Ask any question in plain English — get instant SQL-powered answers from your database.</p>
</div>
""",
        unsafe_allow_html=True,
    )


def render_stats():
    """Show quick DB stats at the top."""
    try:
        from database import get_read_engine
        engine = get_read_engine(st.session_state.db_url)
        from sqlalchemy import text as sa_text
        with engine.connect() as c:
            emp   = c.execute(sa_text("SELECT COUNT(*) FROM employees")).scalar()
            depts = c.execute(sa_text("SELECT COUNT(*) FROM departments")).scalar()
            sal   = c.execute(sa_text("SELECT ROUND(AVG(amount),0) FROM salaries WHERE end_date IS NULL")).scalar()
        engine.dispose()

        st.markdown(
            f"""
<div class="stat-row">
  <div class="stat-tile"><div class="num">{emp}</div><div class="lbl">Employees</div></div>
  <div class="stat-tile"><div class="num">{depts}</div><div class="lbl">Departments</div></div>
  <div class="stat-tile"><div class="num">${sal:,.0f}</div><div class="lbl">Avg Salary</div></div>
  <div class="stat-tile"><div class="num">{len(st.session_state.history)}</div><div class="lbl">Queries Run</div></div>
</div>
""",
            unsafe_allow_html=True,
        )
    except Exception:
        pass  # silently skip stats if DB not ready


def render_sample_questions():
    st.markdown(
        "<div class='card-title'>💡 Sample Questions — click to try</div>",
        unsafe_allow_html=True,
    )
    cols = st.columns(3)
    for idx, q in enumerate(SAMPLE_QUESTIONS):
        with cols[idx % 3]:
            if st.button(q, key=f"samp_{idx}", use_container_width=True):
                st.session_state.question = q


def render_question_input():
    st.markdown("### 💬 Ask a Question")
    question = st.text_area(
        label="question_area",
        value=st.session_state.question,
        placeholder="e.g. Who are the top 5 highest-paid employees in Engineering?",
        height=110,
        label_visibility="collapsed",
        key="question_textarea",
    )
    st.session_state.question = question

    col_btn, col_clr, _ = st.columns([2, 1, 5])
    with col_btn:
        run = st.button("🚀 Generate & Run SQL", use_container_width=True)
    with col_clr:
        if st.button("🗑️ Clear", use_container_width=True):
            st.session_state.question = ""
            st.session_state.result = None
            st.rerun()

    return run


def _get_agent() -> TextToSQLAgent:
    if st.session_state.agent is None:
        st.session_state.agent = TextToSQLAgent(db_url=st.session_state.db_url)
    return st.session_state.agent


def render_result(result: dict):
    st.markdown("---")
    st.markdown("### 📊 Results")

    # ── SQL panel ──────────────────────────────────────────────────────────────
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown("<div class='card-title'>🔍 Generated SQL</div>", unsafe_allow_html=True)
        sql_display = result["sql"] if result["sql"] else "(no SQL generated)"
        st.markdown(
            f"<div class='sql-box'>{sql_display}</div>",
            unsafe_allow_html=True,
        )
    with col2:
        st.markdown("<div class='card-title'>📈 Execution Info</div>", unsafe_allow_html=True)
        # Status badge
        status = result["status"]
        if "✅" in status:
            badge_cls = "badge-success"
        elif "❌" in status or "⛔" in status:
            badge_cls = "badge-error"
        else:
            badge_cls = "badge-warning"

        st.markdown(status)

        if result["is_valid"]:
            st.markdown(
                f"<span class='badge badge-info'>🔢 {result['rows']} rows</span>",
                unsafe_allow_html=True,
            )

    st.markdown("<br/>", unsafe_allow_html=True)

    # ── Validation error ───────────────────────────────────────────────────────
    if not result["is_valid"] and result["validation_error"]:
        st.error(f"⛔ **Security check failed:** {result['validation_error']}")
        return

    # ── Dataframe ──────────────────────────────────────────────────────────────
    df: pd.DataFrame = result["dataframe"]
    if df is not None and not df.empty:
        st.markdown("<div class='card-title'>📋 Query Results</div>", unsafe_allow_html=True)
        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
            height=min(400, 40 + 35 * len(df)),
        )

        # Download button
        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="⬇️ Download CSV",
            data=csv,
            file_name="query_results.csv",
            mime="text/csv",
        )
    elif result["is_valid"]:
        st.info("ℹ️ The query returned no rows.")

    # ── Collapsible raw LLM output ─────────────────────────────────────────────
    if result.get("raw_llm"):
        with st.expander("🔎 View raw LLM response"):
            st.text(result["raw_llm"])


# ─── App entry-point ──────────────────────────────────────────────────────────

def main():
    render_sidebar()
    render_hero()

    # Create the SQLite database and seed sample records if needed.
    with st.spinner("Initializing SQLite database …"):
        try:
            init_database(st.session_state.db_url)
        except Exception as e:
            st.error(f"SQLite database initialization failed: {e}")
            st.stop()

    render_stats()

    with st.container():
        render_sample_questions()

    st.markdown("<br/>", unsafe_allow_html=True)

    run_clicked = render_question_input()

    if run_clicked:
        question = st.session_state.question.strip()
        if not question:
            st.warning("⚠️ Please enter a question first.")
        else:
            with st.spinner("🤖 Thinking… generating SQL …"):
                t0 = time.perf_counter()
                try:
                    agent = _get_agent()
                    result = agent.ask(question)
                except ValueError as exc:
                    st.error(f"⚙️ Configuration error: {exc}")
                    st.info(
                        "Configure `GROQ_API_KEY` in your local `.env` file "
                        "or in Streamlit Cloud → App settings → Secrets."
                    )
                    st.stop()
                except Exception as exc:
                    st.error(f"❌ Query failed: {exc}")
                    st.stop()

                result["elapsed"] = time.perf_counter() - t0

            st.session_state.result = result
            st.session_state.history.append(
                {
                    "question": question,
                    "sql": result["sql"],
                    "success": result["is_valid"] and ("✅" in result["status"]),
                }
            )

    if st.session_state.result:
        render_result(st.session_state.result)
        if "elapsed" in st.session_state.result:
            st.caption(
                f"⏱ Query completed in {st.session_state.result['elapsed']:.2f}s"
            )

    with st.expander("ℹ️ About this application"):
        st.markdown(
            """
**Text-to-SQL Agent** converts natural-language questions into SQL queries
using Groq and executes validated read-only queries against SQLite.

| Feature | Detail |
|---|---|
| LLM Provider | Groq (`openai/gpt-oss-120b`) |
| Database | SQLite |
| ORM | SQLAlchemy |
| Safety | Only SELECT queries execute. DDL/DML is blocked. |
| Sample Data | 23 employees · 7 departments · salary records |

**Architecture**
```
User question → Groq AI → SQL → safety validation → SQLite execution → results
```
            """
        )


if __name__ == "__main__":
    main()
