# Text-to-SQL Agent 🤖

A production-ready AI application that converts natural-language questions into MySQL SQL queries and displays real results — all inside a beautiful Streamlit dashboard.

**Stack:** Google Gemini · LangChain · MySQL 8.0 · SQLAlchemy · Streamlit · Python 3.11

---

## ✨ Features

| Feature | Detail |
|---|---|
| 🤖 **AI-powered** | Google Gemini (gemini-3.8-flash) via LangChain |
| 🗄️ **MySQL backend** | Full MySQL 8.0 support via SQLAlchemy + PyMySQL |
| 🔒 **Read-only safety** | Only `SELECT` queries execute; INSERT/UPDATE/DELETE/DROP/ALTER are blocked |
| 📊 **Live results** | Pageable Streamlit dataframe + CSV download |
| 🎨 **Premium UI** | Dark-mode dashboard with stats tiles, schema viewer, query history |
| 🌱 **Auto-seeded DB** | 23 employees · 7 departments · salary records created automatically |

---

## 🚀 Setup

### 1. Prerequisites

| Requirement | Version | Notes |
|---|---|---|
| Python | 3.11+ | Use `py` launcher on Windows |
| MySQL Server | 8.0+ | Service must be running |
| Google Gemini API key | — | Free at https://aistudio.google.com/apikey |

### 2. Install dependencies

```bash
py -m pip install -r requirements.txt
```

### 3. Configure environment variables

```bash
copy .env.example .env
```

Open `.env` and fill in **both** required values:

```env
# ── Gemini API Key ────────────────────────────────────────────────────────────
# Get yours FREE at: https://aistudio.google.com/apikey
GOOGLE_API_KEY=AIza...your_actual_key_here
GEMINI_MODEL=gemini-3.8-flash

# ── MySQL Credentials ─────────────────────────────────────────────────────────
DB_HOST=localhost
DB_PORT=3306
DB_NAME=company_db
DB_USER=root
DB_PASSWORD=your_actual_mysql_password
```

> **Security:** `.env` is in `.gitignore` and is never committed.
> Never share your `.env` file or paste its contents anywhere.

### 4. Test the setup

```bash
py test_connection.py
```

You should see all ✅ checks pass.

### 5. Run the app

```bash
py -m streamlit run app.py
```

Browser opens at **http://localhost:8501**

---

## 🗄️ Database Schema

The `company_db` MySQL database is created and seeded automatically on first run.

```sql
-- departments
id           INT     PRIMARY KEY
name         VARCHAR(100)  UNIQUE NOT NULL
location     VARCHAR(100)
budget       FLOAT

-- employees
id            INT     PRIMARY KEY
first_name    VARCHAR(50)   NOT NULL
last_name     VARCHAR(50)   NOT NULL
email         VARCHAR(120)  UNIQUE
job_title     VARCHAR(100)
department_id INT     → departments.id
hire_date     DATE
manager_id    INT     → employees.id  (self-join, nullable)
is_active     INT     (1 = active, 0 = inactive)

-- salaries
id             INT    PRIMARY KEY
employee_id    INT    → employees.id  NOT NULL
amount         FLOAT  NOT NULL
currency       VARCHAR(10)  DEFAULT 'USD'
effective_date DATE
end_date       DATE   (NULL = current salary)
```

---

## 💡 Example Questions

```
Who are the top 5 highest-paid employees?
What is the average salary per department?
How many employees are in each department?
List all employees hired after 2020
Which department has the highest total budget?
List active employees in the Engineering department
Who earns more than $150,000?
Show the salary history for all employees
Which employees don't have a manager?
What is the total payroll cost per department?
List employees sorted by hire date (newest first)
```

---

## 📁 Project Structure

```
Text-to-Sql-Agent/
├── app.py               # Streamlit UI
├── database.py          # SQLAlchemy models, MySQL init, schema introspection
├── sql_agent.py         # Gemini LLM, prompt builder, SQL validation & execution
├── test_connection.py   # End-to-end test script
├── requirements.txt     # Python dependencies
├── .env.example         # Environment template (safe to commit)
├── .env                 # Your secrets (git-ignored — NEVER commit)
└── README.md            # This file
```

---

## 🔒 Security Design

| Layer | Protection |
|---|---|
| **API keys** | Stored only in `.env`, never logged or displayed |
| **SQL validation** | Deny-list blocks INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, TRUNCATE, EXEC, GRANT, REVOKE, LOAD |
| **Row cap** | Results hard-limited to 1,000 rows |
| **Password masking** | DB password never shown in Streamlit UI or terminal |
| **URL encoding** | Passwords with special characters are URL-encoded automatically |

---

## 🛠️ Troubleshooting

| Problem | Fix |
|---|---|
| `GOOGLE_API_KEY is not set` | Add your real key to `.env` → https://aistudio.google.com/apikey |
| `Cannot connect to MySQL` | Make sure MySQL80 service is Running (Windows Services) |
| `Access denied for user 'root'` | Check `DB_PASSWORD` in `.env` matches your MySQL root password |
| `ModuleNotFoundError` | Run `py -m pip install -r requirements.txt` |
| `Table 'x' doesn't exist` | Run `py test_connection.py` — it will recreate tables |
| Query returns wrong results | Rephrase the question more specifically |

---

## 📦 Getting API Keys

| Provider | URL | Free Tier |
|---|---|---|
| Google Gemini | https://aistudio.google.com/apikey | ✅ Yes — no credit card needed |

---

*Built with ❤️ using Python · Streamlit · LangChain · Google Gemini · MySQL · SQLAlchemy*
