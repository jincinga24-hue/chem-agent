"""CLI entry point for ChemAgent.

Usage:
    python examples/run_agent.py "What is the molecular weight of aspirin?"
"""
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.agent import run_agent


def main():
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("ERROR: set ANTHROPIC_API_KEY in .env")
        sys.exit(1)

    if len(sys.argv) < 2:
        question = "What is the molecular weight of aspirin in g/mol?"
        print(f"No question provided. Using default: {question}\n")
    else:
        question = " ".join(sys.argv[1:])

    result = run_agent(question, verbose=True)

    print("\n" + "=" * 60)
    print("FINAL ANSWER:")
    print(result.final_answer)
    print(f"\nTool calls: {result.tool_calls} | Stopped: {result.stopped_reason}")


if __name__ == "__main__":
    main()
