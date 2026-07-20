# app/agent/tools.py
#
# Tools are the agent's hands — they let it interact with the world.
# Each function here is something the agent can DECIDE to call.
#
# The LLM reads the docstring of each tool to understand:
# - What the tool does
# - When to use it
# - What inputs to provide
#
# This means DOCSTRINGS ARE PART OF YOUR PROMPT ENGINEERING.
# Write them clearly — the LLM's tool selection depends on them.

from langchain.tools import tool
from app.database.connection import execute_raw_sql, get_schema_context
from app.config import settings
import json
import logging

logger = logging.getLogger(__name__)


@tool
def get_database_schema(dummy_input: str = "") -> str:
    """
    Returns the complete database schema including all tables,
    columns, data types, and relationships.

    Use this tool FIRST before writing any SQL query.
    This tells you exactly what tables and columns exist so you
    can write accurate queries without hallucinating column names.

    Returns a formatted string describing the entire database schema.
    No input required — pass an empty string.
    """
    # @tool decorator from LangChain converts this function into
    # a Tool object the agent can call.
    # The function name becomes the tool name.
    # The docstring becomes the tool description the LLM reads.

    logger.info("Tool called: get_database_schema")
    try:
        schema = get_schema_context()
        return schema
    except Exception as e:
        logger.error(f"Schema retrieval failed: {e}")
        return f"Error retrieving schema: {str(e)}"


@tool
def execute_sql_query(sql_query: str) -> str:
    """
    Executes a SQL SELECT query against the construction database
    and returns the results.

    Use this tool to answer questions about:
    - Worker counts, attendance, roles on specific sites
    - Equipment status, utilisation, maintenance schedules
    - Material stock levels and consumption
    - Safety incidents by site, severity, or status
    - Budget utilisation and site financial data
    - Any aggregations, comparisons, or KPI calculations

    IMPORTANT RULES:
    - Only SELECT queries are allowed
    - Always check the schema first to ensure column names are correct
    - Use exact enum values: status must be 'active'/'on_hold'/
      'completed'/'planning', severity must be 'low'/'medium'/
      'high'/'critical'
    - Round decimal results to 2 places

    Args:
        sql_query: A valid SQLite SELECT query string

    Returns:
        Query results as a JSON string, or an error message.
        Results format: [{"column": "value", ...}, ...]
    """
    logger.info(f"Tool called: execute_sql_query")
    logger.info(f"Query: {sql_query}")

    # Security check — only allow SELECT statements
    # strip() removes leading/trailing whitespace
    # upper() converts to uppercase for case-insensitive check
    cleaned_query = sql_query.strip()
    if not cleaned_query.upper().startswith("SELECT"):
        error_msg = (
            "Security violation: only SELECT queries are permitted. "
            f"Received: {cleaned_query[:50]}..."
        )
        logger.warning(error_msg)
        return error_msg

    try:
        results = execute_raw_sql(cleaned_query)

        if not results:
            return "Query executed successfully but returned no results."

        # Convert to JSON string so the LLM can read it cleanly
        # indent=2 makes it human-readable with proper indentation
        result_str = json.dumps(results, indent=2, default=str)
        # default=str handles non-serialisable types like datetime
        # by converting them to strings

        logger.info(f"Query returned {len(results)} rows")

        # If result is very large, truncate to avoid overwhelming
        # the context window
        if len(results) > 50:
            truncated = results[:50]
            result_str = json.dumps(truncated, indent=2, default=str)
            result_str += f"\n... (showing 50 of {len(results)} rows)"

        return result_str

    except Exception as e:
        error_msg = f"Query execution failed: {str(e)}"
        logger.error(error_msg)
        return error_msg


@tool
def get_dashboard_info(query_context: str) -> str:
    """
    Returns dashboard and widget metadata relevant to the current query.

    Use this tool AFTER executing a SQL query to identify which
    dashboard panel and widget should be displayed alongside the answer.

    Provide a brief description of what the SQL query retrieved,
    for example:
    - "worker attendance for Alpha Tower site"
    - "equipment under maintenance across all sites"
    - "budget utilisation by site"
    - "critical safety incidents"

    Returns dashboard metadata as a JSON string.

    Args:
        query_context: Brief description of what data was retrieved
    """
    logger.info(f"Tool called: get_dashboard_info | context: {query_context}")

    try:
        # Import here to avoid circular imports
        from app.dashboard.metadata import get_dashboard_metadata
        metadata = get_dashboard_metadata()
        return json.dumps(metadata, indent=2)
    except Exception as e:
        logger.error(f"Dashboard metadata retrieval failed: {e}")
        return f"Error retrieving dashboard metadata: {str(e)}"


# ── Tool Registry ─────────────────────────────────────────────────
# A list of all tools available to the agent.
# The agent receives this list and can call any tool in it.
# To add a new capability to the agent, write a new @tool function
# and add it to this list — no other code changes needed.

AGENT_TOOLS = [
    get_database_schema,
    execute_sql_query,
    get_dashboard_info,
]