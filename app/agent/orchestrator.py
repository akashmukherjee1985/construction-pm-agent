# app/agent/orchestrator.py
#
# The orchestrator is the brain of the system.
# It coordinates: LLM → Tools → Memory → Response
#
# ARCHITECTURE DECISION: why we implement our own loop
# instead of using LangChain's built-in AgentExecutor:
#
# LangChain's AgentExecutor is powerful but opaque —
# it's hard to see what's happening inside, hard to debug,
# and hard to customise for specific output formats.
#
# For learning purposes, we implement the ReAct loop manually.
# This means you see every step explicitly.
# Later in the multi-agent phase we'll use LangChain/CrewAI
# abstractions because by then you'll understand what they're doing.

from langchain_ollama import OllamaLLM
from app.config import settings
from app.agent.memory import ConversationMemory
from app.agent.prompts import (
    SYSTEM_PROMPT,
    AGENT_PROMPT,
    RESPONSE_FORMATTER_PROMPT,
    DASHBOARD_MAPPER_PROMPT,
    CHAIN_OF_THOUGHT_SQL_PROMPT,
)
from app.agent.tools import execute_sql_query, get_database_schema
from app.database.connection import get_schema_context
import json
import re
import logging

logger = logging.getLogger(__name__)


class ConstructionPMAgent:
    """
    The Construction PM Agent.

    Orchestrates the full pipeline:
    1. Receive user question
    2. Inject schema + history into prompt
    3. LLM reasons and generates SQL
    4. Execute SQL against database
    5. LLM formats results into natural language
    6. Identify relevant dashboard widget
    7. Return structured response to API layer
    """

    def __init__(self):
        # Initialise the LLM connection
        # We create two LLM instances with different temperatures
        # for different tasks in the pipeline

        # SQL generation LLM — temperature 0 for precision
        # We want deterministic, accurate SQL not creative variations
        self.llm_sql = OllamaLLM(
            model=settings.LLM_MODEL,
            base_url=settings.OLLAMA_BASE_URL,
            temperature=settings.LLM_TEMPERATURE_SQL,
        )

        # Response generation LLM — higher temperature for natural language
        # We want the response to sound conversational, not robotic
        self.llm_chat = OllamaLLM(
            model=settings.LLM_MODEL,
            base_url=settings.OLLAMA_BASE_URL,
            temperature=settings.LLM_TEMPERATURE_CHAT,
        )

        # Initialise memory
        self.memory = ConversationMemory()

        # Cache the schema so we don't query the DB on every request
        # Schema doesn't change at runtime so we load it once
        self._schema_cache: str = None

        logger.info(
            f"ConstructionPMAgent initialised with model: "
            f"{settings.LLM_MODEL}"
        )

    def _get_schema(self) -> str:
        """
        Get database schema, using cache if available.

        The underscore prefix (_get_schema) is a Python convention
        meaning this is a private method — internal use only,
        not part of the public interface.
        """
        if self._schema_cache is None:
            self._schema_cache = get_schema_context()
            logger.info("Schema loaded and cached.")
        return self._schema_cache

    def _extract_sql(self, llm_response: str) -> str | None:
        """
        Extract the SQL query from the LLM's response.

        The LLM responds with reasoning text AND the SQL query.
        We need to reliably pull out just the SQL.

        We look for several patterns:
        1. "SQL: SELECT ..." (our prompted format)
        2. ```sql ... ``` (markdown code blocks)
        3. Plain SELECT statement

        Args:
            llm_response: The full text response from the LLM

        Returns:
            The extracted SQL string, or None if not found
        """
        # Pattern 1: Our explicit "SQL:" label
        # re.IGNORECASE makes it case-insensitive
        # re.DOTALL makes . match newlines too
        sql_label_pattern = re.search(
            r'SQL:\s*(SELECT.*?)(?:\n\n|\Z)',
            llm_response,
            re.IGNORECASE | re.DOTALL
        )
        if sql_label_pattern:
            return sql_label_pattern.group(1).strip()

        # Pattern 2: Markdown code block ```sql ... ```
        code_block_pattern = re.search(
            r'```(?:sql)?\s*(SELECT.*?)```',
            llm_response,
            re.IGNORECASE | re.DOTALL
        )
        if code_block_pattern:
            return code_block_pattern.group(1).strip()

        # Pattern 3: Raw SELECT statement
        select_pattern = re.search(
            r'(SELECT\s+.*?)(?:;|\Z)',
            llm_response,
            re.IGNORECASE | re.DOTALL
        )
        if select_pattern:
            return select_pattern.group(1).strip()

        logger.warning(
            f"Could not extract SQL from response: "
            f"{llm_response[:200]}"
        )
        return None

    def _is_complex_question(self, question: str) -> bool:
        """
        Determine if a question requires Chain of Thought reasoning.

        Simple questions → standard AGENT_PROMPT
        Complex questions → CHAIN_OF_THOUGHT_SQL_PROMPT

        We detect complexity by looking for keywords that suggest
        multi-step reasoning, comparisons, or calculations.
        """
        complexity_indicators = [
            "compare", "comparison", "versus", "vs",
            "best", "worst", "highest", "lowest", "most", "least",
            "trend", "over time", "between",
            "percentage", "ratio", "rate",
            "across all", "overall",
            "which site", "rank", "ranking",
            "relative to", "compared to",
        ]

        question_lower = question.lower()
        return any(
            indicator in question_lower
            for indicator in complexity_indicators
        )

    def process_question(self, user_question: str) -> dict:
        """
        Main entry point — processes a user question end to end.

        This is the function the FastAPI endpoint calls.

        Args:
            user_question: The manager's natural language question

        Returns:
            dict with keys:
                - answer: natural language response
                - sql_query: the SQL that was executed
                - raw_results: the query results as list of dicts
                - dashboard: relevant dashboard info
                - session: session metadata
                - error: error message if something failed
        """
        logger.info(f"Processing question: {user_question}")

        # Add user message to memory
        self.memory.add_user_message(user_question)

        # Get schema and conversation history
        schema = self._get_schema()
        history = self.memory.get_formatted_history(max_turns=6)
        context_hints = self.memory.get_context_hints()

        try:
            # ── STEP 1: SQL GENERATION ─────────────────────────────
            # Choose prompt based on question complexity
            if self._is_complex_question(user_question):
                logger.info("Complex question detected — using CoT prompt")
                sql_prompt = CHAIN_OF_THOUGHT_SQL_PROMPT.format(
                    schema=schema,
                    history=history,
                    question=user_question
                )
            else:
                logger.info("Standard question — using agent prompt")
                sql_prompt = AGENT_PROMPT.format(
                    schema=schema,
                    history=history + "\n" + context_hints,
                    question=user_question
                )

            # Send to LLM for SQL generation
            logger.info("Sending prompt to LLM for SQL generation...")
            llm_sql_response = self.llm_sql.invoke(sql_prompt)
            logger.info(f"LLM SQL response received: {llm_sql_response[:200]}")

            # ── STEP 2: SQL EXTRACTION ─────────────────────────────
            sql_query = self._extract_sql(llm_sql_response)

            if not sql_query:
                # LLM couldn't generate SQL — question may not need it
                # e.g. "hello" or "what can you help me with?"
                response = (
                    "I couldn't determine what data to retrieve for that "
                    "question. Could you rephrase it? For example: "
                    "'How many workers are on Alpha Tower?' or "
                    "'Show me all open safety incidents.'"
                )
                self.memory.add_assistant_message(response)
                return {
                    "answer": response,
                    "sql_query": None,
                    "raw_results": [],
                    "dashboard": None,
                    "session": self.memory.get_session_summary(),
                    "error": None
                }

            # ── STEP 3: SQL EXECUTION ──────────────────────────────
            logger.info(f"Executing SQL: {sql_query}")

            # Use our tool directly (bypassing LangChain tool call
            # since we're in a manual loop)
            raw_results_str = execute_sql_query.func(sql_query)
            # .func gives us the underlying Python function
            # without the LangChain tool wrapper

            # Parse results back to Python objects
            try:
                raw_results = json.loads(raw_results_str)
                if isinstance(raw_results, str):
                    # Error message returned as string
                    raw_results = []
            except (json.JSONDecodeError, TypeError):
                raw_results = []

            # ── STEP 4: RESPONSE GENERATION ───────────────────────
            # Send question + SQL results back to LLM
            # for natural language response generation
            response_prompt = RESPONSE_FORMATTER_PROMPT.format(
                question=user_question,
                sql_query=sql_query,
                query_results=raw_results_str,
                history=history
            )

            logger.info("Generating natural language response...")
            natural_language_response = self.llm_chat.invoke(response_prompt)

            # ── STEP 5: DASHBOARD MAPPING ──────────────────────────
            dashboard_info = None
            try:
                from app.dashboard.metadata import get_dashboard_metadata
                dashboard_metadata = get_dashboard_metadata()

                dashboard_prompt = DASHBOARD_MAPPER_PROMPT.format(
                    dashboard_metadata=json.dumps(
                        dashboard_metadata, indent=2
                    ),
                    question=user_question,
                    sql_query=sql_query
                )

                dashboard_response = self.llm_sql.invoke(dashboard_prompt)

                # Extract JSON from dashboard response
                # More robust JSON extraction
                json_match = re.search(
                    r'\{.*\}',
                    dashboard_response,
                    re.DOTALL
                )
                if json_match:
                    raw_json = json_match.group()
                    # Fix common LLM JSON mistakes
                    # Replace single quotes with double quotes
                    raw_json = raw_json.replace("'", '"')
                    # Remove trailing commas before closing braces/brackets
                    raw_json = re.sub(r',\s*}', '}', raw_json)
                    raw_json = re.sub(r',\s*]', ']', raw_json)
                    try:
                        dashboard_info = json.loads(raw_json)
                    except json.JSONDecodeError as json_err:
                        logger.warning(
                            f"Dashboard JSON parse failed after cleanup: {json_err}"
                        )
                        dashboard_info = None

            except Exception as e:
                logger.warning(f"Dashboard mapping failed: {e}")
                # Non-critical — agent still works without dashboard info

            # ── STEP 6: STORE IN MEMORY ────────────────────────────
            self.memory.add_assistant_message(
                natural_language_response,
                sql_query=sql_query
            )

            logger.info("Question processed successfully.")

            return {
                "answer": natural_language_response,
                "sql_query": sql_query,
                "raw_results": raw_results if isinstance(
                    raw_results, list
                ) else [],
                "dashboard": dashboard_info,
                "session": self.memory.get_session_summary(),
                "error": None
            }

        except Exception as e:
            error_msg = f"Agent error: {str(e)}"
            logger.error(error_msg, exc_info=True)
            # exc_info=True includes the full stack trace in the log

            self.memory.add_assistant_message(
                f"I encountered an error processing your question: {str(e)}"
            )

            return {
                "answer": "I encountered an error. Please try again.",
                "sql_query": None,
                "raw_results": [],
                "dashboard": None,
                "session": self.memory.get_session_summary(),
                "error": error_msg
            }

    def reset(self) -> dict:
        """
        Hard reset — clears all conversation memory.
        Called when user clicks the reset button in the UI.
        """
        self.memory.hard_reset()
        return {
            "message": "Conversation reset successfully.",
            "session": self.memory.get_session_summary()
        }