"""ChemAgent tool-use loop via Anthropic SDK."""
import os
import json
from dataclasses import dataclass, field
from typing import Any

from anthropic import Anthropic
from dotenv import load_dotenv

from .prompts import SYSTEM_PROMPT
from .tools import TOOL_FUNCTIONS, TOOL_SCHEMAS

load_dotenv()

DEFAULT_MODEL = os.getenv("AGENT_MODEL", "claude-opus-4-7")
MAX_TOOL_TURNS = 12


@dataclass
class AgentResult:
    final_answer: str
    trace: list[dict[str, Any]] = field(default_factory=list)
    tool_calls: int = 0
    stopped_reason: str = ""


def run_agent(question: str, model: str = DEFAULT_MODEL, verbose: bool = False) -> AgentResult:
    client = Anthropic()
    messages: list[dict[str, Any]] = [{"role": "user", "content": question}]
    trace: list[dict[str, Any]] = []
    tool_calls = 0

    for turn in range(MAX_TOOL_TURNS):
        response = client.messages.create(
            model=model,
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            tools=TOOL_SCHEMAS,
            messages=messages,
        )

        trace.append({"turn": turn, "stop_reason": response.stop_reason, "content": [
            {"type": b.type, **({"text": b.text} if b.type == "text" else {
                "tool": b.name, "input": b.input, "id": b.id,
            })} for b in response.content
        ]})

        if verbose:
            for block in response.content:
                if block.type == "text":
                    print(f"[turn {turn}] {block.text}")
                elif block.type == "tool_use":
                    print(f"[turn {turn}] tool: {block.name}({json.dumps(block.input)[:120]})")

        if response.stop_reason == "end_turn":
            final = "\n".join(b.text for b in response.content if b.type == "text")
            return AgentResult(final_answer=final.strip(), trace=trace,
                               tool_calls=tool_calls, stopped_reason="end_turn")

        if response.stop_reason != "tool_use":
            return AgentResult(final_answer="[no answer]", trace=trace,
                               tool_calls=tool_calls, stopped_reason=response.stop_reason)

        messages.append({"role": "assistant", "content": response.content})

        tool_results_content: list[dict[str, Any]] = []
        for block in response.content:
            if block.type != "tool_use":
                continue
            tool_calls += 1
            fn = TOOL_FUNCTIONS.get(block.name)
            if fn is None:
                result = {"error": f"Unknown tool: {block.name}"}
            else:
                try:
                    result = fn(**block.input)
                except Exception as e:
                    result = {"error": f"{type(e).__name__}: {e}"}
            tool_results_content.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": json.dumps(result),
            })

        messages.append({"role": "user", "content": tool_results_content})

    return AgentResult(final_answer="[max turns reached]", trace=trace,
                       tool_calls=tool_calls, stopped_reason="max_turns")
