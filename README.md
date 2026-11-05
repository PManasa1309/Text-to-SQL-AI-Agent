# Text-to-SQL AI Agent 🤖

An AI-powered application that converts natural-language questions into MySQL SQL queries and displays real database results through an interactive Streamlit dashboard.

Ask questions in simple English, and the AI agent generates the corresponding SQL query, validates it for safety, executes it against the MySQL database, and displays the results.

**Tech Stack:** Python · Groq API · Llama / GPT-OSS · LangChain · MySQL 8.0 · SQLAlchemy · PyMySQL · Streamlit

---

## ✨ Features

| Feature | Description |
|---|---|
| 🤖 **AI-powered SQL generation** | Uses Groq API with `openai/gpt-oss-120b` to convert natural-language questions into SQL queries |
| 🗄️ **MySQL integration** | Connects to MySQL 8.0 using SQLAlchemy and PyMySQL |
| 🔒 **SQL safety validation** | Allows read-only SELECT queries and blocks potentially destructive SQL operations |
| 📊 **Live query results** | Displays database results in an interactive Streamlit dataframe |
| 📥 **CSV export** | Download query results as CSV files |
| 🎨 **Interactive dashboard** | User-friendly interface for submitting questions and viewing generated SQL and results |
| 🌱 **Database initialization** | Creates and initializes the required database tables and sample records |

---

## 🚀 Installation and Setup

### 1. Prerequisites

| Requirement | Version | Notes |
|---|---|---|
| Python | 3.11+ | Required to run the application |
| MySQL Server | 8.0+ | Must be installed and running |
| Git | Latest | For version control |
| Groq API Key | — | Obtain a free API key from Groq Console |

### 2. Clone the Repository

```bash
git clone https://github.com/YOUR_USERNAME/Text-to-SQL-AI-Agent.git
cd Text-to-SQL-AI-Agent
```

### 3. Create a Virtual Environment

**Windows:**

```powershell
py -m venv .venv
.venv\Scripts\activate
```

### 4. Install Dependencies

```bash
py -m pip install -r requirements.txt
```

### 5. Configure Environment Variables

Create your `.env` file using the example template:

```powershell
copy .env.example .env
```

Open `.env` and configure your credentials:

```env
# Groq AI Configuration
LLM_PROVIDER=groq
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=openai/gpt-oss-120b

# MySQL Database Configuration
DB_HOST=localhost
DB_PORT=3306
DB_NAME=company_db
DB_USER=root
DB_PASSWORD=your_mysql_password_here
```

**Get your Groq API key:**

https://console.groq.com/keys

Replace the placeholder values with your actual credentials.

> **Security:** Never upload your `.env` file or expose your API key and database password publicly. The `.env` file is excluded through `.gitignore`.

### 6. Test the Database Connection

```bash
py test_connection.py
```

Make sure your MySQL server is running before executing the test.

### 7. Run the Application

```bash
py -m streamlit run app.py
```

Open the application in your browser:

```text
http://localhost:8501
```

---

## 🗄️ Database Schema

The application uses a MySQL database named `company_db`.

The database initialization process creates the required tables and sample records.

### Tables

**1. Departments**

| Column | Description |
|---|---|
| id | Department ID |
| name | Department name |
| location | Department location |
| budget | Department budget |

**2. Employees**

| Column | Description |
|---|---|
| id | Employee ID |
| first_name | Employee first name |
| last_name | Employee last name |
| email | Employee email |
| job_title | Employee designation |
| department_id | Reference to department |
| hire_date | Employee joining date |
| manager_id | Reference to manager |
| is_active | Employee active status |

**3. Salaries**

| Column | Description |
|---|---|
| id | Salary record ID |
| employee_id | Reference to employee |
| amount | Salary amount |
| currency | Salary currency |
| effective_date | Salary effective date |
| end_date | Salary end date |

---

## 💡 Example Questions

You can ask questions in natural language, such as:

```text
Who are the top 5 highest-paid employees?

What is the average salary per department?

How many employees are in each department?

List all employees hired after 2020.

Which department has the highest total budget?

List active employees in the Engineering department.

Who earns more than $150,000?

Show the salary history for all employees.

Which employees don't have a manager?

What is the total payroll cost per department?

List employees sorted by hire date (newest first).
```

---

## 📁 Project Structure

```text
Text-to-Sql-Agent/
│
├── app.py               # Streamlit user interface
├── database.py          # MySQL database connection and initialization
├── sql_agent.py         # Groq LLM integration and SQL generation
├── test_connection.py   # Database connection testing
├── requirements.txt     # Python dependencies
├── .env.example         # Environment configuration template
├── .gitignore           # Excludes sensitive and unnecessary files
├── .env                 # Private credentials (not uploaded)
└── README.md            # Project documentation
```

---

## 🔒 Security Features

| Security Layer | Implementation |
|---|---|
| API key protection | Groq API key stored in `.env` |
| Database credentials | MySQL credentials stored in environment variables |
| SQL validation | Restricts execution to permitted read-only SQL queries |
| Dangerous query blocking | Blocks INSERT, UPDATE, DELETE, DROP, ALTER and other restricted operations |
| Result limitation | Limits query results to prevent excessive data retrieval |
| Password protection | Credentials are not displayed in the application interface |
| Git security | `.env` and virtual environments excluded using `.gitignore` |

---

## 🛠️ Troubleshooting

| Problem | Possible Solution |
|---|---|
| `GROQ_API_KEY is missing` | Add your valid Groq API key to `.env` |
| `Invalid API key` | Verify your Groq API key in the Groq Console |
| `Model not found` | Check that `GROQ_MODEL` is set to a supported model |
| `Cannot connect to MySQL` | Make sure your MySQL server is running |
| `Access denied for user` | Verify your MySQL username and password |
| `ModuleNotFoundError` | Run `py -m pip install -r requirements.txt` |
| Tables not found | Run `py test_connection.py` and check database initialization |
| SQL generation error | Check your Groq API configuration and model availability |

---

## 🔑 API Configuration

**AI Provider:** Groq

**Model:** `openai/gpt-oss-120b`

**API Key:** https://console.groq.com/keys

The application uses LangChain's Groq integration to communicate with the language model.

---

## 👩‍💻 Developed With

**Python | Streamlit | Groq API | LangChain | MySQL | SQLAlchemy**

Built with ❤️ as an AI-powered Text-to-SQL project to explore Generative AI, natural-language processing, database integration and automated SQL generation.

