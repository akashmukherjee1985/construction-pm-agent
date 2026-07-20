# test_agent.py
# Quick end-to-end test of the agent pipeline
# Run with: python test_agent.py

import logging

# Configure logging so we can see what the agent is doing
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(name)s | %(levelname)s | %(message)s'
)

from app.agent.orchestrator import ConstructionPMAgent

def test_agent():
    print("\n" + "="*60)
    print("CONSTRUCTION PM AGENT — END TO END TEST")
    print("="*60 + "\n")

    # Initialise the agent
    agent = ConstructionPMAgent()

    # Test questions — ordered from simple to complex
    test_questions = [
        # Simple — single table, no joins
        "How many workers are currently present on Alpha Tower?",

        # Follow-up — tests conversation memory
        "What about Beta Highway?",

        # Medium — aggregation
        "Show me the budget utilisation for all active sites.",

        # Complex — multi-step reasoning, CoT should trigger
        "Which site has the worst safety record?",
    ]

    for i, question in enumerate(test_questions, 1):
        print(f"Question {i}: {question}")
        print("-" * 40)

        result = agent.process_question(question)

        print(f"SQL Generated:\n{result['sql_query']}\n")
        print(f"Answer:\n{result['answer']}\n")

        if result['dashboard']:
            print(f"Dashboard: {result['dashboard'].get('dashboard')}")
            print(f"Widget: {result['dashboard'].get('widget')}")
            print(f"Filters: {result['dashboard'].get('filters')}\n")

        if result['error']:
            print(f"ERROR: {result['error']}\n")

        print("=" * 60 + "\n")

    # Test hard reset
    print("Testing hard reset...")
    reset_result = agent.reset()
    print(f"Reset result: {reset_result['message']}\n")

    # After reset, follow-up should not have context
    print("Question after reset (should not have context):")
    result = agent.process_question("What about that site?")
    print(f"Answer: {result['answer']}\n")


if __name__ == "__main__":
    test_agent()