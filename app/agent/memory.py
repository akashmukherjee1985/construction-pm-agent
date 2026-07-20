# app/agent/memory.py
#
# Memory is what separates a chatbot from a conversational agent.
# Without memory, every question is treated as the first message —
# follow-up questions like "what about that site?" break completely.
#
# We implement a simple but effective conversation buffer:
# - Stores the last N turns of conversation
# - Formats history for injection into prompts
# - Supports hard reset (clears everything)
# - Tracks session metadata

from datetime import datetime
from typing import Optional
from app.config import settings
import logging

logger = logging.getLogger(__name__)


class ConversationMemory:
    """
    Manages conversation history for the construction PM agent.

    This is an in-memory implementation — history lives in a Python
    list and is lost when the server restarts.

    In production you would persist this to:
    - Redis (for fast access, automatic expiry)
    - PostgreSQL (for permanent audit trail)
    - A session store (for multi-user support)

    For our learning project, in-memory is perfect — it keeps the
    focus on the agent logic without infrastructure complexity.
    """

    def __init__(self):
        # List of conversation turns
        # Each turn is a dict: {"role": "user"/"assistant", "content": "..."}
        self.turns: list[dict] = []

        # Session metadata
        self.session_start: datetime = datetime.now()
        self.question_count: int = 0
        self.last_sql_query: Optional[str] = None
        self.last_site_mentioned: Optional[str] = None

        logger.info("ConversationMemory initialised.")

    def add_user_message(self, message: str) -> None:
        """
        Add a user message to the conversation history.

        Args:
            message: The user's question or input
        """
        self.turns.append({
            "role": "user",
            "content": message,
            "timestamp": datetime.now().isoformat()
        })
        self.question_count += 1

        # Track the last site mentioned for context resolution
        # e.g. if user says "what about Alpha Tower?" followed by
        # "how many workers?", we know they mean Alpha Tower workers
        sites = [
            "Alpha Tower", "Beta Highway",
            "Gamma Industrial", "Delta Mall", "Epsilon Bridge"
        ]
        for site in sites:
            if site.lower() in message.lower():
                self.last_site_mentioned = site
                break

        # Enforce max history limit
        # Keep the most recent N turns
        # Each "turn" is one message, so max_turns = max_messages
        max_turns = settings.MAX_CONVERSATION_HISTORY
        if len(self.turns) > max_turns:
            # Remove oldest turns from the front
            # Preserve system context by keeping recent history
            self.turns = self.turns[-max_turns:]
            logger.debug(f"Trimmed history to {max_turns} turns")

    def add_assistant_message(self, message: str, sql_query: str = None) -> None:
        """
        Add an assistant response to the conversation history.

        Args:
            message: The agent's response
            sql_query: The SQL query used to generate this response
                      Stored for context in follow-up questions
        """
        self.turns.append({
            "role": "assistant",
            "content": message,
            "timestamp": datetime.now().isoformat()
        })

        if sql_query:
            self.last_sql_query = sql_query

    def get_formatted_history(self, max_turns: int = 10) -> str:
        """
        Format conversation history as a string for prompt injection.

        Takes the last max_turns messages and formats them as:
            User: <message>
            Assistant: <response>
            User: <message>
            ...

        This formatted string is injected into {history} placeholder
        in our prompt templates.

        Args:
            max_turns: How many recent turns to include
                      Fewer = smaller context, faster response
                      More = better context, slower response

        Returns:
            Formatted conversation history string
        """
        if not self.turns:
            return "No previous conversation."

        # Take the most recent turns
        recent_turns = self.turns[-max_turns:]

        formatted_lines = []
        for turn in recent_turns:
            role = turn["role"].capitalize()
            # Capitalize: "user" → "User", "assistant" → "Assistant"
            content = turn["content"]

            # Truncate very long assistant messages in history
            # The full response was shown to the user already
            # In history we just need enough for context
            if role == "Assistant" and len(content) > 300:
                content = content[:300] + "... [truncated]"

            formatted_lines.append(f"{role}: {content}")

        return "\n".join(formatted_lines)

    def get_context_hints(self) -> str:
        """
        Generate context hints based on conversation state.

        These hints help the LLM resolve ambiguous references
        like "that site", "those workers", "the same equipment".

        Returns:
            A string of context hints for the current session
        """
        hints = []

        if self.last_site_mentioned:
            hints.append(
                f"Last site mentioned: {self.last_site_mentioned}"
            )

        if self.last_sql_query:
            hints.append(
                f"Last SQL query run: {self.last_sql_query}"
            )

        if self.question_count > 0:
            hints.append(
                f"Questions asked this session: {self.question_count}"
            )

        if not hints:
            return "No context from previous questions."

        return "\n".join(hints)

    def hard_reset(self) -> None:
        """
        Clear all conversation history and reset session state.

        This is what happens when the user clicks the reset button
        in the Streamlit UI. Everything is wiped — the agent starts
        completely fresh with no memory of previous questions.

        Use case: manager wants to start a completely new line of
        inquiry without previous context affecting responses.
        """
        self.turns = []
        self.session_start = datetime.now()
        self.question_count = 0
        self.last_sql_query = None
        self.last_site_mentioned = None
        logger.info("Conversation memory hard reset.")

    def get_session_summary(self) -> dict:
        """
        Returns metadata about the current session.
        Useful for logging and debugging.
        """
        return {
            "session_start": self.session_start.isoformat(),
            "question_count": self.question_count,
            "turns_in_memory": len(self.turns),
            "last_site_mentioned": self.last_site_mentioned,
            "session_duration_minutes": round(
                (datetime.now() - self.session_start).seconds / 60, 1
            )
        }