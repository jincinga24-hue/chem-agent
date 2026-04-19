"""Run ChemAgent against the benchmark problem set. Uses `claude -p` — no API key."""
import json
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.agent import run_agent
from evals.judge import judge, numerical_check


PROBLEMS_PATH = Path(__file__).parent / "problems.json"
RESULTS_DIR = Path(__file__).resolve().parents[1] / "eval_results"


def main():
    RESULTS_DIR.mkdir(exist_ok=True)
    problems = json.loads(PROBLEMS_PATH.read_text())

    run_id = datetime.now().strftime("%Y%m%d-%H%M%S")
    out_path = RESULTS_DIR / f"run-{run_id}.json"

    results = []
    total_score = 0
    for i, p in enumerate(problems, 1):
        print(f"\n[{i}/{len(problems)}] {p['id']} ({p['category']})")
        print(f"  Problem: {p['problem'][:110]}...")

        agent_result = run_agent(p["problem"], verbose=False)
        is_qualitative = p.get("expected_value") is None
        if is_qualitative:
            num_check = {"numerical_match": None, "extracted": None}
        else:
            num_check = numerical_check(
                agent_result.final_answer,
                p["expected_value"],
                p["tolerance_pct"],
            )
        judgement = judge(
            p["problem"],
            p["ground_truth"],
            agent_result.final_answer,
            agent_result.trace,
            qualitative=is_qualitative,
        )

        score = judgement.get("score", 0)
        total_score += score
        print(f"  Agent answer: {agent_result.final_answer[:150]}")
        print(f"  Tool calls: {agent_result.tool_calls} | Stop: {agent_result.stopped_reason}")
        print(f"  Numerical match: {num_check['numerical_match']} (extracted: {num_check['extracted']})")
        print(f"  Judge: {score}/10 — {judgement.get('reasoning', '')[:120]}")

        results.append({
            "id": p["id"],
            "category": p["category"],
            "score": score,
            "numerical_match": num_check["numerical_match"],
            "extracted_value": num_check["extracted"],
            "expected_value": p["expected_value"],
            "tool_calls": agent_result.tool_calls,
            "stopped_reason": agent_result.stopped_reason,
            "agent_answer": agent_result.final_answer,
            "judgement": judgement,
        })

    scored_numerical = [r for r in results if r["numerical_match"] is not None]
    summary = {
        "run_id": run_id,
        "backend": "claude -p",
        "total_score": total_score,
        "max_score": len(problems) * 10,
        "percent": round(total_score / (len(problems) * 10) * 100, 1),
        "correct_numerical": sum(1 for r in scored_numerical if r["numerical_match"]),
        "numerical_count": len(scored_numerical),
        "problem_count": len(problems),
        "results": results,
    }
    out_path.write_text(json.dumps(summary, indent=2))

    print("\n" + "=" * 60)
    print(f"TOTAL: {total_score}/{len(problems) * 10} ({summary['percent']}%)")
    print(f"Numerical correct: {summary['correct_numerical']}/{len(scored_numerical)}")
    print(f"Results saved to: {out_path}")


if __name__ == "__main__":
    main()
