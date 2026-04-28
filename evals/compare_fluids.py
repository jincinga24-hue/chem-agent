"""Head-to-head: ChemAgent (tools) vs bare LLM (no tools) on the two
fluid-mechanics benchmark problems added for ENGR30002.

Writes a side-by-side JSON report to eval_results/compare-fluids-<ts>.json
and prints a summary table.
"""
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.agent import run_agent
from src.claude_cli import claude_call
from evals.judge import numerical_check


PROBLEMS_PATH = Path(__file__).parent / "problems.json"
RESULTS_DIR = Path(__file__).resolve().parents[1] / "eval_results"
FLUID_IDS = {"torricelli-tank-three-holes", "three-reservoir-junction-pressure"}

BARE_SYSTEM_PROMPT = (
    "You are a chemical engineering tutor. Solve the problem step by step "
    "using your general knowledge. You do NOT have access to any tools, "
    "calculators, or reference databases — rely on what you remember. "
    "For any literature values you need (pipe roughness, standard diameters, "
    "fitting K-values, fluid properties), state the value and cite the "
    "source you believe it comes from. End your reply with a line:\n"
    "FINAL ANSWER: <number> <units>"
)


def run_bare(problem: str) -> str:
    return claude_call(problem, system_prompt=BARE_SYSTEM_PROMPT)


def main():
    RESULTS_DIR.mkdir(exist_ok=True)
    problems = [p for p in json.loads(PROBLEMS_PATH.read_text()) if p["id"] in FLUID_IDS]

    run_id = datetime.now().strftime("%Y%m%d-%H%M%S")
    out_path = RESULTS_DIR / f"compare-fluids-{run_id}.json"

    rows = []
    for p in problems:
        print(f"\n=== {p['id']} (expected {p['expected_value']}, ±{p['tolerance_pct']}%) ===")

        print("[1/2] Running AGENT (tools enabled)...")
        ag = run_agent(p["problem"], verbose=False)
        agent_check = numerical_check(ag.final_answer, p["expected_value"], p["tolerance_pct"])
        print(f"  tool_calls={ag.tool_calls}  stopped={ag.stopped_reason}")
        print(f"  extracted={agent_check['extracted']}  match={agent_check['numerical_match']}")

        print("[2/2] Running BARE LLM (no tools)...")
        bare_answer = run_bare(p["problem"])
        bare_check = numerical_check(bare_answer, p["expected_value"], p["tolerance_pct"])
        print(f"  extracted={bare_check['extracted']}  match={bare_check['numerical_match']}")

        rows.append({
            "id": p["id"],
            "expected_value": p["expected_value"],
            "tolerance_pct": p["tolerance_pct"],
            "agent": {
                "final_answer": ag.final_answer,
                "tool_calls": ag.tool_calls,
                "stopped_reason": ag.stopped_reason,
                "extracted": agent_check["extracted"],
                "numerical_match": agent_check["numerical_match"],
            },
            "bare_llm": {
                "final_answer": bare_answer,
                "extracted": bare_check["extracted"],
                "numerical_match": bare_check["numerical_match"],
            },
        })

    summary = {
        "run_id": run_id,
        "agent_backend": "claude -p with ChemAgent tools (ReAct)",
        "bare_backend": "claude -p no tools, general knowledge only",
        "problems": rows,
        "agent_correct": sum(1 for r in rows if r["agent"]["numerical_match"]),
        "bare_correct": sum(1 for r in rows if r["bare_llm"]["numerical_match"]),
        "total": len(rows),
    }
    out_path.write_text(json.dumps(summary, indent=2))

    print("\n" + "=" * 72)
    print(f"{'Problem':<42} {'Expected':>10} {'Agent':>8} {'Bare':>8}")
    print("-" * 72)
    for r in rows:
        a_ext = r["agent"]["extracted"]
        b_ext = r["bare_llm"]["extracted"]
        a_str = f"{a_ext}" if isinstance(a_ext, (int, float)) else ("list" if isinstance(a_ext, list) else "none")
        b_str = f"{b_ext}" if isinstance(b_ext, (int, float)) else ("list" if isinstance(b_ext, list) else "none")
        a_mark = "Y" if r["agent"]["numerical_match"] else "N"
        b_mark = "Y" if r["bare_llm"]["numerical_match"] else "N"
        print(f"{r['id']:<42} {r['expected_value']:>10} {a_str+'['+a_mark+']':>8} {b_str+'['+b_mark+']':>8}")
    print("=" * 72)
    print(f"Agent: {summary['agent_correct']}/{summary['total']}   "
          f"Bare:  {summary['bare_correct']}/{summary['total']}")
    print(f"Saved: {out_path}")


if __name__ == "__main__":
    main()
