"""ChemAgent ReAct loop powered by `claude -p` (no API key required)."""
import json
import re
from dataclasses import dataclass, field
from typing import Any

from .claude_cli import claude_call
from .prompts import SYSTEM_PROMPT
from .tools import TOOL_FUNCTIONS


MAX_TOOL_TURNS = 12
JSON_BLOCK_RE = re.compile(r"```json\s*(\{.*?\})\s*```", re.DOTALL)


@dataclass
class AgentResult:
    final_answer: str
    trace: list[dict[str, Any]] = field(default_factory=list)
    tool_calls: int = 0
    stopped_reason: str = ""


def _extract_action(raw: str) -> dict[str, Any]:
    match = JSON_BLOCK_RE.search(raw)
    block = match.group(1) if match else raw.strip()
    # Also handle plain JSON without fencing.
    try:
        return json.loads(block)
    except json.JSONDecodeError as e:
        raise ValueError(f"Could not parse action JSON: {e}\n---\n{raw[:400]}")


def _render_history(question: str, history: list[dict[str, Any]]) -> str:
    lines = [f"PROBLEM:\n{question}\n"]
    for step in history:
        if step["type"] == "tool_call":
            lines.append(f"\n[your previous action]")
            lines.append(f'```json\n{{"action": "tool_call", "tool": "{step["tool"]}", "input": {json.dumps(step["input"])}}}\n```')
            lines.append(f"\n[tool result]")
            lines.append(f"```json\n{json.dumps(step['result'])}\n```")
    lines.append("\nWhat is your next action? Respond with a single JSON code block as instructed.")
    return "\n".join(lines)


def run_agent(question: str, verbose: bool = False) -> AgentResult:
    history: list[dict[str, Any]] = []
    trace: list[dict[str, Any]] = []
    tool_calls = 0

    for turn in range(MAX_TOOL_TURNS):
        prompt = _render_history(question, history)
        if verbose:
            print(f"\n[turn {turn}] calling claude -p ...")

        raw = claude_call(prompt, system_prompt=SYSTEM_PROMPT)

        try:
            action = _extract_action(raw)
        except ValueError as e:
            trace.append({"turn": turn, "parse_error": str(e), "raw": raw[:500]})
            return AgentResult(final_answer=raw.strip(), trace=trace,
                               tool_calls=tool_calls, stopped_reason="parse_error")

        trace.append({"turn": turn, "action": action})

        if action.get("action") == "final_answer":
            answer = action.get("answer", "")
            if verbose:
                print(f"[turn {turn}] FINAL: {answer[:200]}")
            return AgentResult(final_answer=answer, trace=trace,
                               tool_calls=tool_calls, stopped_reason="final_answer")

        if action.get("action") != "tool_call":
            return AgentResult(final_answer=raw.strip(), trace=trace,
                               tool_calls=tool_calls, stopped_reason="unknown_action")

        tool_name = action.get("tool", "")
        tool_input = action.get("input", {})
        fn = TOOL_FUNCTIONS.get(tool_name)
        if fn is None:
            result: dict[str, Any] = {"error": f"Unknown tool: {tool_name}"}
        else:
            try:
                result = fn(**tool_input)
            except Exception as e:
                result = {"error": f"{type(e).__name__}: {e}"}

        tool_calls += 1
        if verbose:
            print(f"[turn {turn}] tool: {tool_name}({json.dumps(tool_input)[:80]})")
            print(f"[turn {turn}] result: {json.dumps(result)[:200]}")

        history.append({
            "type": "tool_call",
            "tool": tool_name,
            "input": tool_input,
            "result": result,
        })

    return AgentResult(final_answer="[max turns reached]", trace=trace,
                       tool_calls=tool_calls, stopped_reason="max_turns")
