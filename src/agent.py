"""ChemAgent ReAct loop powered by `claude -p` (no API key required)."""
import json
import re
import time
from dataclasses import dataclass, field
from typing import Any

from .claude_cli import claude_call
from .prompts import SYSTEM_PROMPT
from .tools import TOOL_FUNCTIONS
from .tracing import NullTracer, Tracer


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
    # strict=False tolerates literal newlines/tabs inside JSON string values —
    # common when Claude writes multi-line Python inside a "code" field.
    try:
        return json.loads(block, strict=False)
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


def run_agent(
    question: str,
    verbose: bool = False,
    tracer: Tracer | NullTracer | None = None,
) -> AgentResult:
    """Run the agent on a single question.

    tracer: optional Tracer for structured per-event logging to JSONL.
            If None, a NullTracer is used (no-op, no file I/O).
    """
    tr = tracer if tracer is not None else NullTracer()
    history: list[dict[str, Any]] = []
    trace: list[dict[str, Any]] = []
    tool_calls = 0

    tr.log("agent_start", question=question, max_turns=MAX_TOOL_TURNS)

    for turn in range(MAX_TOOL_TURNS):
        prompt = _render_history(question, history)
        if verbose:
            print(f"\n[turn {turn}] calling claude -p ...")

        t0 = time.monotonic()
        raw = claude_call(prompt, system_prompt=SYSTEM_PROMPT)
        llm_latency_ms = round((time.monotonic() - t0) * 1000, 2)
        tr.log("llm_response", turn=turn, latency_ms=llm_latency_ms, chars=len(raw))

        try:
            action = _extract_action(raw)
        except ValueError as e:
            trace.append({"turn": turn, "parse_error": str(e), "raw": raw[:500]})
            tr.log("parse_error", turn=turn, error=str(e), raw_prefix=raw[:300])
            tr.log("agent_end", reason="parse_error", tool_calls=tool_calls)
            return AgentResult(final_answer=raw.strip(), trace=trace,
                               tool_calls=tool_calls, stopped_reason="parse_error")

        trace.append({"turn": turn, "action": action})

        if action.get("action") == "final_answer":
            answer = action.get("answer", "")
            if verbose:
                print(f"[turn {turn}] FINAL: {answer[:200]}")
            tr.log("final_answer", turn=turn, answer=answer)
            tr.log("agent_end", reason="final_answer", tool_calls=tool_calls)
            return AgentResult(final_answer=answer, trace=trace,
                               tool_calls=tool_calls, stopped_reason="final_answer")

        if action.get("action") != "tool_call":
            tr.log("unknown_action", turn=turn, action=action)
            tr.log("agent_end", reason="unknown_action", tool_calls=tool_calls)
            return AgentResult(final_answer=raw.strip(), trace=trace,
                               tool_calls=tool_calls, stopped_reason="unknown_action")

        tool_name = action.get("tool", "")
        tool_input = action.get("input", {})
        tr.log("tool_call", turn=turn, tool=tool_name, input=tool_input)

        fn = TOOL_FUNCTIONS.get(tool_name)
        t0 = time.monotonic()
        if fn is None:
            result: dict[str, Any] = {"error": f"Unknown tool: {tool_name}"}
        else:
            try:
                result = fn(**tool_input)
            except Exception as e:
                result = {"error": f"{type(e).__name__}: {e}"}
        tool_latency_ms = round((time.monotonic() - t0) * 1000, 2)

        tool_calls += 1
        tr.log(
            "tool_result",
            turn=turn,
            tool=tool_name,
            latency_ms=tool_latency_ms,
            result=result,
            error=result.get("error") if isinstance(result, dict) else None,
        )
        if verbose:
            print(f"[turn {turn}] tool: {tool_name}({json.dumps(tool_input)[:80]})")
            print(f"[turn {turn}] result: {json.dumps(result, default=str)[:200]}")

        history.append({
            "type": "tool_call",
            "tool": tool_name,
            "input": tool_input,
            "result": result,
        })

    tr.log("agent_end", reason="max_turns", tool_calls=tool_calls)
    return AgentResult(final_answer="[max turns reached]", trace=trace,
                       tool_calls=tool_calls, stopped_reason="max_turns")
