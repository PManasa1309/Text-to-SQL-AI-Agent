"""
database.py — SQLite database creation, seeding, and schema introspection.

Responsibilities
----------------
* Build a local SQLite connection URL.
* Create the SQLite database file and required tables automatically.
* Create and seed the Department, Employee, and Salary tables with realistic
  sample data if they do not already contain rows.
* Expose a SQLAlchemy engine for validated SELECT query execution.
* Introspect all tables and return a human-readable schema string for the LLM.
"""

import os
import logging
from datetime import date
from typing import Optional

from sqlalchemy import (
    create_engine,
    inspect,
    text,
    Column,
    Integer,
    String,
    Date,
    Float,
    ForeignKey,
    event,
)
from sqlalchemy.orm import DeclarativeBase, Session
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


# ─── Declarative base ─────────────────────────────────────────────────────────

class Base(DeclarativeBase):
    pass


class Department(Base):
    __tablename__ = "departments"

    id         = Column(Integer, primary_key=True)
    name       = Column(String(100), nullable=False, unique=True)
    location   = Column(String(100))
    budget     = Column(Float)


class Employee(Base):
    __tablename__ = "employees"

    id            = Column(Integer, primary_key=True)
    first_name    = Column(String(50),  nullable=False)
    last_name     = Column(String(50),  nullable=False)
    email         = Column(String(120), unique=True)
    job_title     = Column(String(100))
    department_id = Column(Integer, ForeignKey("departments.id"))
    hire_date     = Column(Date)
    manager_id    = Column(Integer, ForeignKey("employees.id"), nullable=True)
    is_active     = Column(Integer, default=1)   # 1 = active, 0 = inactive


class Salary(Base):
    __tablename__ = "salaries"

    id             = Column(Integer, primary_key=True)
    employee_id    = Column(Integer, ForeignKey("employees.id"), nullable=False)
    amount         = Column(Float,   nullable=False)
    currency       = Column(String(10), default="USD")
    effective_date = Column(Date)
    end_date       = Column(Date, nullable=True)   # NULL = current salary


# ─── Seed data ────────────────────────────────────────────────────────────────

_DEPARTMENTS = [
    {"id": 1, "name": "Engineering",  "location": "San Francisco", "budget": 5_000_000.0},
    {"id": 2, "name": "Marketing",    "location": "New York",      "budget": 2_000_000.0},
    {"id": 3, "name": "Sales",        "location": "Chicago",       "budget": 3_000_000.0},
    {"id": 4, "name": "HR",           "location": "Austin",        "budget": 1_000_000.0},
    {"id": 5, "name": "Finance",      "location": "Boston",        "budget": 1_500_000.0},
    {"id": 6, "name": "Product",      "location": "Seattle",       "budget": 2_500_000.0},
    {"id": 7, "name": "Data Science", "location": "San Francisco", "budget": 2_000_000.0},
]

_EMPLOYEES = [
    # Engineering
    {"id": 1,  "first_name": "Alice",  "last_name": "Johnson",  "email": "alice.johnson@company.com",  "job_title": "VP of Engineering",      "department_id": 1, "hire_date": date(2018, 3, 15), "manager_id": None, "is_active": 1},
    {"id": 2,  "first_name": "Bob",    "last_name": "Smith",    "email": "bob.smith@company.com",      "job_title": "Senior Engineer",        "department_id": 1, "hire_date": date(2019, 7, 1),  "manager_id": 1,   "is_active": 1},
    {"id": 3,  "first_name": "Carol",  "last_name": "Williams", "email": "carol.williams@company.com", "job_title": "Engineer",               "department_id": 1, "hire_date": date(2021, 1, 20), "manager_id": 2,   "is_active": 1},
    {"id": 4,  "first_name": "David",  "last_name": "Brown",    "email": "david.brown@company.com",    "job_title": "Junior Engineer",        "department_id": 1, "hire_date": date(2023, 6, 5),  "manager_id": 2,   "is_active": 1},
    {"id": 5,  "first_name": "Eva",    "last_name": "Davis",    "email": "eva.davis@company.com",      "job_title": "DevOps Engineer",        "department_id": 1, "hire_date": date(2020, 9, 14), "manager_id": 1,   "is_active": 1},
    # Marketing
    {"id": 6,  "first_name": "Frank",  "last_name": "Miller",   "email": "frank.miller@company.com",   "job_title": "Marketing Director",     "department_id": 2, "hire_date": date(2017, 5, 22), "manager_id": None, "is_active": 1},
    {"id": 7,  "first_name": "Grace",  "last_name": "Wilson",   "email": "grace.wilson@company.com",   "job_title": "Senior Marketing Mgr",   "department_id": 2, "hire_date": date(2019, 11, 3), "manager_id": 6,   "is_active": 1},
    {"id": 8,  "first_name": "Hank",   "last_name": "Moore",    "email": "hank.moore@company.com",     "job_title": "Content Strategist",     "department_id": 2, "hire_date": date(2022, 2, 28), "manager_id": 7,   "is_active": 1},
    # Sales
    {"id": 9,  "first_name": "Iris",   "last_name": "Taylor",   "email": "iris.taylor@company.com",    "job_title": "Sales Director",         "department_id": 3, "hire_date": date(2016, 8, 10), "manager_id": None, "is_active": 1},
    {"id": 10, "first_name": "Jack",   "last_name": "Anderson", "email": "jack.anderson@company.com",  "job_title": "Sales Manager",          "department_id": 3, "hire_date": date(2018, 4, 18), "manager_id": 9,   "is_active": 1},
    {"id": 11, "first_name": "Karen",  "last_name": "Thomas",   "email": "karen.thomas@company.com",   "job_title": "Sales Representative",   "department_id": 3, "hire_date": date(2020, 10, 7), "manager_id": 10,  "is_active": 1},
    {"id": 12, "first_name": "Liam",   "last_name": "Jackson",  "email": "liam.jackson@company.com",   "job_title": "Sales Representative",   "department_id": 3, "hire_date": date(2021, 3, 25), "manager_id": 10,  "is_active": 0},
    # HR
    {"id": 13, "first_name": "Mia",    "last_name": "White",    "email": "mia.white@company.com",      "job_title": "HR Director",            "department_id": 4, "hire_date": date(2015, 6, 30), "manager_id": None, "is_active": 1},
    {"id": 14, "first_name": "Nathan", "last_name": "Harris",   "email": "nathan.harris@company.com",  "job_title": "HR Manager",             "department_id": 4, "hire_date": date(2019, 8, 12), "manager_id": 13,  "is_active": 1},
    # Finance
    {"id": 15, "first_name": "Olivia", "last_name": "Martin",   "email": "olivia.martin@company.com",  "job_title": "CFO",                    "department_id": 5, "hire_date": date(2014, 1, 5),  "manager_id": None, "is_active": 1},
    {"id": 16, "first_name": "Paul",   "last_name": "Garcia",   "email": "paul.garcia@company.com",    "job_title": "Financial Analyst",      "department_id": 5, "hire_date": date(2020, 5, 11), "manager_id": 15,  "is_active": 1},
    # Product
    {"id": 17, "first_name": "Quinn",  "last_name": "Martinez", "email": "quinn.martinez@company.com", "job_title": "VP of Product",          "department_id": 6, "hire_date": date(2017, 9, 20), "manager_id": None, "is_active": 1},
    {"id": 18, "first_name": "Rachel", "last_name": "Robinson", "email": "rachel.robinson@company.com","job_title": "Senior Product Manager", "department_id": 6, "hire_date": date(2019, 12, 2), "manager_id": 17,  "is_active": 1},
    {"id": 19, "first_name": "Sam",    "last_name": "Clark",    "email": "sam.clark@company.com",      "job_title": "Product Manager",        "department_id": 6, "hire_date": date(2021, 7, 14), "manager_id": 18,  "is_active": 1},
    # Data Science
    {"id": 20, "first_name": "Tina",   "last_name": "Rodriguez","email": "tina.rodriguez@company.com", "job_title": "Head of Data Science",   "department_id": 7, "hire_date": date(2018, 11, 8), "manager_id": None, "is_active": 1},
    {"id": 21, "first_name": "Uma",    "last_name": "Lewis",    "email": "uma.lewis@company.com",      "job_title": "Data Scientist",         "department_id": 7, "hire_date": date(2020, 3, 3),  "manager_id": 20,  "is_active": 1},
    {"id": 22, "first_name": "Victor", "last_name": "Lee",      "email": "victor.lee@company.com",     "job_title": "ML Engineer",            "department_id": 7, "hire_date": date(2021, 9, 6),  "manager_id": 20,  "is_active": 1},
    {"id": 23, "first_name": "Wendy",  "last_name": "Walker",   "email": "wendy.walker@company.com",   "job_title": "Data Analyst",           "department_id": 7, "hire_date": date(2022, 4, 19), "manager_id": 20,  "is_active": 1},
]

_SALARIES = [
    # Engineering
    {"id": 1,  "employee_id": 1,  "amount": 195000, "currency": "USD", "effective_date": date(2023, 1, 1),  "end_date": None},
    {"id": 2,  "employee_id": 2,  "amount": 145000, "currency": "USD", "effective_date": date(2023, 1, 1),  "end_date": None},
    {"id": 3,  "employee_id": 3,  "amount": 110000, "currency": "USD", "effective_date": date(2023, 1, 1),  "end_date": None},
    {"id": 4,  "employee_id": 4,  "amount":  85000, "currency": "USD", "effective_date": date(2023, 6, 1),  "end_date": None},
    {"id": 5,  "employee_id": 5,  "amount": 125000, "currency": "USD", "effective_date": date(2023, 1, 1),  "end_date": None},
    # Marketing
    {"id": 6,  "employee_id": 6,  "amount": 165000, "currency": "USD", "effective_date": date(2023, 1, 1),  "end_date": None},
    {"id": 7,  "employee_id": 7,  "amount": 115000, "currency": "USD", "effective_date": date(2023, 1, 1),  "end_date": None},
    {"id": 8,  "employee_id": 8,  "amount":  80000, "currency": "USD", "effective_date": date(2023, 1, 1),  "end_date": None},
    # Sales
    {"id": 9,  "employee_id": 9,  "amount": 175000, "currency": "USD", "effective_date": date(2023, 1, 1),  "end_date": None},
    {"id": 10, "employee_id": 10, "amount": 120000, "currency": "USD", "effective_date": date(2023, 1, 1),  "end_date": None},
    {"id": 11, "employee_id": 11, "amount":  75000, "currency": "USD", "effective_date": date(2023, 1, 1),  "end_date": None},
    {"id": 12, "employee_id": 12, "amount":  70000, "currency": "USD", "effective_date": date(2021, 3, 1),  "end_date": date(2022, 12, 31)},
    # HR
    {"id": 13, "employee_id": 13, "amount": 155000, "currency": "USD", "effective_date": date(2023, 1, 1),  "end_date": None},
    {"id": 14, "employee_id": 14, "amount": 105000, "currency": "USD", "effective_date": date(2023, 1, 1),  "end_date": None},
    # Finance
    {"id": 15, "employee_id": 15, "amount": 210000, "currency": "USD", "effective_date": date(2023, 1, 1),  "end_date": None},
    {"id": 16, "employee_id": 16, "amount":  95000, "currency": "USD", "effective_date": date(2023, 1, 1),  "end_date": None},
    # Product
    {"id": 17, "employee_id": 17, "amount": 185000, "currency": "USD", "effective_date": date(2023, 1, 1),  "end_date": None},
    {"id": 18, "employee_id": 18, "amount": 145000, "currency": "USD", "effective_date": date(2023, 1, 1),  "end_date": None},
    {"id": 19, "employee_id": 19, "amount": 115000, "currency": "USD", "effective_date": date(2023, 1, 1),  "end_date": None},
    # Data Science
    {"id": 20, "employee_id": 20, "amount": 175000, "currency": "USD", "effective_date": date(2023, 1, 1),  "end_date": None},
    {"id": 21, "employee_id": 21, "amount": 130000, "currency": "USD", "effective_date": date(2023, 1, 1),  "end_date": None},
    {"id": 22, "employee_id": 22, "amount": 140000, "currency": "USD", "effective_date": date(2023, 1, 1),  "end_date": None},
    {"id": 23, "employee_id": 23, "amount": 100000, "currency": "USD", "effective_date": date(2023, 1, 1),  "end_date": None},
]




# ─── SQLite connection and engine ─────────────────────────────────────────────

def get_database_url() -> str:
    """Return the SQLite database URL.

    SQLITE_DB_PATH can optionally override the database filename.
    By default, company.db is created in the project directory.
    """
    db_path = os.getenv("SQLITE_DB_PATH", "company.db")
    if db_path == ":memory:":
        return "sqlite://"
    return f"sqlite:///{db_path}"


def _make_engine(url: Optional[str] = None):
    """Create a SQLAlchemy engine for SQLite."""
    engine = create_engine(
        url or get_database_url(),
        echo=False,
        connect_args={"check_same_thread": False},
    )

    # Enforce SQLite foreign-key constraints on each new connection.
    @event.listens_for(engine, "connect")
    def _enable_foreign_keys(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return engine


# ─── Public API ───────────────────────────────────────────────────────────────

def init_database(db_url: Optional[str] = None) -> None:
    """Create SQLite tables and seed sample data when the tables are empty."""
    engine = _make_engine(db_url)
    try:
        Base.metadata.create_all(engine)
        logger.info("SQLite tables created / verified.")

        with Session(engine) as session:
            existing = session.execute(
                text("SELECT COUNT(*) FROM departments")
            ).scalar() or 0

            if existing == 0:
                logger.info("Seeding SQLite database with sample data...")
                session.execute(Department.__table__.insert(), _DEPARTMENTS)
                session.execute(Employee.__table__.insert(), _EMPLOYEES)
                session.execute(Salary.__table__.insert(), _SALARIES)
                session.commit()
                logger.info(
                    "Seeded %d departments, %d employees, and %d salaries.",
                    len(_DEPARTMENTS), len(_EMPLOYEES), len(_SALARIES)
                )
            else:
                logger.info("SQLite database already contains data; skipping seed.")
    except Exception:
        engine.dispose()
        raise
    finally:
        engine.dispose()


def get_read_engine(db_url: Optional[str] = None):
    """Return a SQLAlchemy engine for query execution.

    SQL write operations must remain blocked by the validation layer in
    sql_agent.py. SQLite is a local file database, not a remote service.
    """
    return _make_engine(db_url)


def get_schema_info(db_url: Optional[str] = None) -> str:
    """Inspect SQLite tables and return a schema description for the LLM."""
    engine = _make_engine(db_url)
    try:
        inspector = inspect(engine)
        table_names = inspector.get_table_names()
        lines = ["DATABASE SCHEMA (SQLite)\n" + "=" * 50]

        for table_name in table_names:
            lines.append(f"\nTable: {table_name}")
            lines.append("-" * 30)

            for col in inspector.get_columns(table_name):
                nullable = "" if col["nullable"] else " NOT NULL"
                lines.append(
                    f"  {col['name']:30s} {str(col['type']):20s}{nullable}"
                )

            foreign_keys = inspector.get_foreign_keys(table_name)
            if foreign_keys:
                lines.append("  -- Foreign Keys --")
                for fk in foreign_keys:
                    local_cols = ", ".join(fk["constrained_columns"])
                    ref_table = fk["referred_table"]
                    ref_cols = ", ".join(fk["referred_columns"])
                    lines.append(f"  {local_cols} -> {ref_table}.{ref_cols}")

            with engine.connect() as conn:
                row_count = conn.execute(
                    text(f'SELECT COUNT(*) FROM "{table_name}"')
                ).scalar()
            lines.append(f"  -- ~{row_count} rows --")

        return "\n".join(lines)
    finally:
        engine.dispose()


def get_table_sample(
    table_name: str, limit: int = 3, db_url: Optional[str] = None
) -> str:
    """Return a few sample rows from a SQLite table."""
    # Table names are selected from SQLAlchemy's inspector, not user input.
    engine = _make_engine(db_url)
    try:
        inspector = inspect(engine)
        if table_name not in inspector.get_table_names():
            return f"(unknown table: {table_name})"

        with engine.connect() as conn:
            rows = conn.execute(
                text(f'SELECT * FROM "{table_name}" LIMIT :lim'),
                {"lim": limit},
            ).fetchall()

        if not rows:
            return f"(no rows in {table_name})"

        col_names = list(rows[0]._mapping.keys())
        header = " | ".join(col_names)
        separator = "-" * len(header)
        body = "\n".join(" | ".join(str(value) for value in row) for row in rows)
        return f"{header}\n{separator}\n{body}"
    except Exception as exc:
        return f"(error sampling {table_name}: {exc})"
    finally:
        engine.dispose()
