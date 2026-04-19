"""LLM-judge: uses `claude -p` to score agent answers. No API key needed."""
import json
import re

from src.claude_cli import claude_call
from src.prompts import JUDGE_PROMPT_NUMERICAL, JUDGE_PROMPT_QUALITATIVE


JSON_BLOCK_RE = re.compile(r"```json\s*(\{.*?\})\s*```", re.DOTALL)


def judge(problem: str, ground_truth: str, agent_answer: str, trace: list,
          qualitative: bool = False) -> dict:
    trace_str = json.dumps(trace, indent=2)[:6000]
    template = JUDGE_PROMPT_QUALITATIVE if qualitative else JUDGE_PROMPT_NUMERICAL
    prompt = template.format(
        problem=problem,
        ground_truth=ground_truth,
        agent_answer=agent_answer,
        trace=trace_str,
    )
    raw = claude_call(prompt)

    match = JSON_BLOCK_RE.search(raw)
    block = match.group(1) if match else raw.strip()
    try:
        return json.loads(block, strict=False)
    except json.JSONDecodeError:
        m2 = re.search(r"\{[^{}]*\"score\"[^{}]*\}", raw, re.DOTALL)
        if m2:
            try:
                return json.loads(m2.group(0), strict=False)
            except json.JSONDecodeError:
                pass
        return {"score": 0, "correct": False, "reasoning": f"Judge output unparseable: {raw[:300]}"}


def numerical_check(agent_answer: str, expected: float, tolerance_pct: float) -> dict:
    """Rule-based backup: extract numbers from agent answer, check vs expected."""
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
