"""Structured trace logging for ChemAgent runs.

Writes JSONL — one event per line — to traces/<run_id>/<problem_id>.jsonl.
Events include agent start/end, tool calls + results, parse errors, and final
answers, each with elapsed time. Useful for:

  - Debugging failed agent runs (replay reasoning chain)
  - Measuring per-tool latency and frequency
  - Building training data for fine-tuning
  - Evaluating which tools the agent actually uses

The Tracer is opt-in: pass a Tracer to run_agent(), or pass None to disable.
A NullTracer is provided for tests and callers that want to ignore tracing.
"""
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


class NullTracer:
    """No-op tracer. Useful for tests or when tracing is disabled."""

    def log(self, event_type: str, **payload: Any) -> None:
        pass

    def close(self) -> None:
        pass

    def __enter__(self) -> "NullTracer":
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()


class Tracer:
    """Append-only JSONL tracer for one agent run on one problem.

    Each event line is a JSON object with at least:
      - ts        ISO-8601 UTC timestamp
      - elapsed_s seconds since the tracer was created
      - event     event type (string)
      - payload   event-specific fields (flattened into the line)

    File layout: <base_dir>/<run_id>/<problem_id>.jsonl

    Usage:
        with Tracer(run_id="20260428-130000", problem_id="raft-mma") as tr:
            tr.log("agent_start", question=q)
            ...
            tr.log("tool_call", turn=0, tool="raft_kinetics", input={...})
            tr.log("tool_result", turn=0, tool="raft_kinetics", result={...}, latency_ms=4.2)
            tr.log("final_answer", answer="...")
    """

    def __init__(
        self,
        run_id: str,
        problem_id: str,
        base_dir: Path | str = Path("traces"),
    ) -> None:
        self.run_id = run_id
        self.problem_id = problem_id
        self.base_dir = Path(base_dir)
        self.path = self.base_dir / run_id / f"{problem_id}.jsonl"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._start_monotonic = time.monotonic()
        self._fh = self.path.open("a", encoding="utf-8")

    def log(self, event_type: str, **payload: Any) -> None:
        event: dict[str, Any] = {
            "ts": _now_iso(),
            "elapsed_s": round(time.monotonic() - self._start_monotonic, 4),
            "event": event_type,
            **payload,
        }
        self._fh.write(json.dumps(event, default=str) + "\n")
        self._fh.flush()

    def close(self) -> None:
        if not self._fh.closed:
            self._fh.close()

    def __enter__(self) -> "Tracer":
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()


def load_trace(path: Path | str) -> list[dict[str, Any]]:
    """Read a .jsonl trace file back into a list of events."""
    events = []
    p = Path(path)
    with p.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                events.append(json.loads(line))
    return events


def summarise_trace(events: list[dict[str, Any]]) -> dict[str, Any]:
    """Compute per-trace stats: tool counts, total time, success/failure."""
    tool_counts: dict[str, int] = {}
    tool_latency_ms: dict[str, list[float]] = {}
    total_time = 0.0
    final_answer = None
    parse_errors = 0
    for ev in events:
        et = ev.get("event")
        if et == "tool_result":
            tn = ev.get("tool", "?")
            tool_counts[tn] = tool_counts.get(tn, 0) + 1
            if "latency_ms" in ev:
                tool_latency_ms.setdefault(tn, []).append(ev["latency_ms"])
        elif et == "final_answer":
            final_answer = ev.get("answer", "")
        elif et == "parse_error":
            parse_errors += 1
        total_time = max(total_time, ev.get("elapsed_s", 0))
    return {
        "tool_counts": tool_counts,
        "tool_latency_ms_avg": {
            t: round(sum(v) / len(v), 2) for t, v in tool_latency_ms.items()
        },
        "total_time_s": round(total_time, 3),
        "parse_errors": parse_errors,
        "completed": final_answer is not None,
        "final_answer": final_answer,
        "n_events": len(events),
    }
