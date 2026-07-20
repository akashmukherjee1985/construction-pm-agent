# app/database/connection.py

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.config import settings
from app.database.models import Base
import logging

# Get a logger for this module
# __name__ evaluates to "app.database.connection"
# This means log messages from this file are labelled clearly
logger = logging.getLogger(__name__)


# ── Engine ────────────────────────────────────────────────────────
# The engine is SQLAlchemy's connection to the database
# It manages the connection pool and translates Python to SQL
#
# create_engine() does NOT open a connection immediately
# It just stores the configuration — connections open on demand
#
# connect_args={"check_same_thread": False}
# → SQLite specific setting
# → By default SQLite only allows one thread to use a connection
# → We set this to False because FastAPI uses multiple threads
# → PostgreSQL doesn't need this setting at all
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False,
    # echo=True would print every SQL statement to console
    # useful for debugging, too noisy for normal use
)


# ── Session Factory ───────────────────────────────────────────────
# A session is a unit of work with the database
# Think of it like a shopping basket:
# - you add things to the basket (stage changes)
# - you checkout (commit) to make changes permanent
# - or you abandon the basket (rollback) to discard changes
#
# sessionmaker() creates a factory — a class that produces sessions
# We configure it once here and call it every time we need a session
SessionLocal = sessionmaker(
    autocommit=False,
    # autocommit=False → we manually call session.commit()
    # This gives us control over transactions
    # A transaction is a group of operations that succeed or fail together

    autoflush=False,
    # autoflush=False → don't automatically sync pending changes
    # before every query — we control this manually

    bind=engine
    # bind=engine → use our engine for all connections
)


def init_db():
    """
    Create all tables in the database.
    
    Base.metadata.create_all() looks at all classes that inherit
    from Base (our 5 models) and creates their corresponding tables
    if they don't already exist.
    
    If tables already exist, it does nothing — it does NOT drop
    and recreate them. So it's safe to call multiple times.
    
    This is called once when the application starts up.
    """
    logger.info("Initialising database...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created successfully.")


def get_db():
    """
    Database session dependency for FastAPI.
    
    This is a generator function (uses yield instead of return).
    FastAPI calls this for every request that needs database access.
    
    The try/finally pattern guarantees the session is always closed
    even if an error occurs during the request.
    
    Usage in FastAPI:
        def my_endpoint(db: Session = Depends(get_db)):
            ...
    
    We'll use this properly in Phase 6 when we build the API layer.
    """
    db = SessionLocal()
    try:
        yield db
        # yield pauses this function and gives the session to FastAPI
        # FastAPI runs the endpoint with this session
        # then execution returns here after the endpoint finishes
    finally:
        db.close()
        # always runs — closes the connection back to the pool


def execute_raw_sql(query: str, params: dict = None) -> list[dict]:
    """
    Execute a raw SQL query string and return results as a list of dicts.
    
    This is the function our AI agent will call when it generates
    a SQL query. The agent produces a query string, we execute it here,
    and return results in a clean format the LLM can read.
    
    Args:
        query: SQL query string, e.g. "SELECT COUNT(*) FROM workmen"
        params: optional dict of parameters for parameterised queries
                e.g. {"site": "Alpha"} for "WHERE site_name = :site"
    
    Returns:
        List of dicts, one dict per row
        e.g. [{"site_name": "Alpha", "worker_count": 47}]
    
    Why return list of dicts and not a DataFrame?
        The LLM reads text. A list of dicts serialises cleanly to
        a readable string. A DataFrame needs extra conversion steps.
    """
    with engine.connect() as connection:
        # "with" statement → context manager
        # automatically closes the connection when the block exits
        # even if an exception is raised

        result = connection.execute(
            text(query),
            # text() wraps a raw SQL string so SQLAlchemy knows
            # it's literal SQL and not an ORM expression
            params or {}
        )

        # result.keys() gives column names
        # result.fetchall() gives all rows as tuples
        # zip(keys, row) pairs column names with values
        # dict() converts those pairs to a dictionary
        columns = result.keys()
        rows = result.fetchall()
        return [dict(zip(columns, row)) for row in rows]
    


def get_schema_context() -> str:
    """
    Introspect the live database and return a formatted schema string
    that the LLM can read and understand.

    This is the RAG knowledge base for SQL generation.
    Instead of hardcoding table descriptions, we read the actual
    schema from the database at runtime.

    This means if the schema changes, the LLM automatically gets
    the updated schema on the next call — no code changes needed.

    Returns:
        A formatted string describing all tables and their columns.
        Example output:
            Table: sites
              - id (INTEGER) required
              - site_name (VARCHAR) required
              - status (VARCHAR) optional
            ...

    In production (PostgreSQL), replace the sqlite_master query with:
        SELECT table_name, column_name, data_type, is_nullable
        FROM information_schema.columns
        WHERE table_schema = 'public'
        ORDER BY table_name, ordinal_position;
    """
    # Step 1: Get all table names from SQLite's internal catalog
    # sqlite_master is SQLite's system table that tracks all objects
    tables_query = """
        SELECT name 
        FROM sqlite_master 
        WHERE type = 'table'
        AND name NOT LIKE 'sqlite_%'
        ORDER BY name;
    """
    # AND name NOT LIKE 'sqlite_%' excludes SQLite's internal tables
    # like sqlite_sequence which we don't want the LLM to see

    tables = execute_raw_sql(tables_query)
    # Returns: [{"name": "sites"}, {"name": "workmen"}, ...]

    if not tables:
        return "No tables found in database."

    schema_parts = []
    # We'll build the schema string piece by piece
    # then join them at the end

    # Step 2: For each table, get its column details
    for table_row in tables:
        table_name = table_row["name"]

        # pragma_table_info() is SQLite's built-in function
        # that returns column metadata for a given table
        columns_query = f"PRAGMA table_info({table_name});"
        columns = execute_raw_sql(columns_query)

        # Each column row contains:
        # cid (column index), name, type, notnull, dflt_value, pk
        # Example: {"cid": 0, "name": "id", "type": "INTEGER",
        #           "notnull": 1, "dflt_value": None, "pk": 1}

        # Build a readable description for this table
        table_description = f"Table: {table_name}\n"

        for col in columns:
            col_name = col["name"]
            col_type = col["type"]
            required = "required" if col["notnull"] else "optional"
            is_pk = " (PRIMARY KEY)" if col["pk"] else ""

            table_description += (
                f"  - {col_name} ({col_type}) "
                f"{required}{is_pk}\n"
            )

        schema_parts.append(table_description)

    # Step 3: Add relationship descriptions
    # SQLAlchemy ForeignKey constraints aren't easily introspected
    # in SQLite, so we document relationships explicitly
    # This helps the LLM write correct JOIN queries
    relationships = """
    Table Relationships:
    - workmen.site_name → sites.site_name
    - equipment_inventory.site_name → sites.site_name
    - materials.site_name → sites.site_name
    - incidents.site_name → sites.site_name

    Key Business Rules:
    - All monetary values are in USD
    - utilisation_percent ranges from 0.0 to 100.0
    - attendance_status values: present, absent, on_leave
    - Budget utilisation = (spent_budget / total_budget) * 100
    - Low stock alert when quantity_in_stock < minimum_stock_level
    - incidents.severity stores the level: low, medium, high, critical
    - incidents.incident_type stores the category: 'Fall from height',
        'Equipment failure', 'Near miss', etc.
    - For safety scoring always use the severity column NOT incident_type
    """

    # Join all parts with blank lines between tables
    full_schema = "\n".join(schema_parts) + "\n" + relationships

    return full_schema