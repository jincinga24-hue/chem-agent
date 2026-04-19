"""LLM-judge: scores an agent's answer against ground truth."""
import json
import os
import re

from anthropic import Anthropic
from dotenv import load_dotenv

from src.prompts import JUDGE_PROMPT

load_dotenv()

JUDGE_MODEL = os.getenv("JUDGE_MODEL", "claude-opus-4-7")


def judge(problem: str, ground_truth: str, agent_answer: str, trace: list) -> dict:
    client = Anthropic()
    trace_str = json.dumps(trace, indent=2)[:8000]

    response = client.messages.create(
        model=JUDGE_MODEL,
        max_tokens=1024,
        messages=[{
            "role": "user",
            "content": JUDGE_PROMPT.format(
                problem=problem,
                ground_truth=ground_truth,
                agent_answer=agent_answer,
                trace=trace_str,
            ),
        }],
    )

    text = "\n".join(b.text for b in response.content if b.type == "text")
    match = re.search(r"\{[^{}]*\"score\"[^{}]*\}", text, re.DOTALL)
    if not match:
        return {"score": 0, "correct": False, "reasoning": f"Judge output unparseable: {text[:300]}"}

    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError as e:
        return {"score": 0, "correct": False, "reasoning": f"JSON parse failure: {e}"}


def numerical_check(agent_answer: str, expected: float, tolerance_pct: float) -> dict:
    """Backup rule-based check: extract numbers from agent answer, check vs expected."""
    numbers = re.findall(r"-?\d+\.?\d*(?:[eE][-+]?\d+)?", agent_answer.replace(",", ""))
    if not numbers:
        return {"numerical_match": False, "extracted": None}
    for raw in numbers:
        try:
            val = float(raw)
        except ValueError:
            continue
        if expected == 0:
            if abs(val) < tolerance_pct / 100:
                return {"numerical_match": True, "extracted": val}
        elif abs(val - expected) / abs(expected) * 100 <= tolerance_pct:
            return {"numerical_match": True, "extracted": val}
    return {"numerical_match": False, "extracted": [float(n) for n in numbers[:5]]}
