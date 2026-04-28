"""Unit tests for the tracing module."""
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.tracing import NullTracer, Tracer, load_trace, summarise_trace


class TestNullTracer:
    def test_log_is_noop(self):
        nt = NullTracer()
        nt.log("anything", foo=1, bar="x")  # must not raise
        nt.close()

    def test_context_manager(self):
        with NullTracer() as nt:
            nt.log("event")


class TestTracer:
    def test_writes_jsonl_one_event_per_line(self, tmp_path):
        with Tracer(run_id="r1", problem_id="p1", base_dir=tmp_path) as tr:
            tr.log("agent_start", question="hello")
            tr.log("tool_call", turn=0, tool="x", input={"a": 1})
            tr.log("tool_result", turn=0, tool="x", latency_ms=4.2, result={"ok": True})
            tr.log("final_answer", turn=1, answer="42")
            tr.log("agent_end", reason="final_answer", tool_calls=1)

        path = tmp_path / "r1" / "p1.jsonl"
        assert path.exists()
        lines = path.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 5
        # each line is valid JSON
        events = [json.loads(line) for line in lines]
        assert events[0]["event"] == "agent_start"
        assert events[0]["question"] == "hello"
        assert events[2]["latency_ms"] == 4.2
        # all events have a timestamp + elapsed
        for e in events:
            assert "ts" in e
            assert "elapsed_s" in e

    def test_elapsed_increases_monotonically(self, tmp_path):
        with Tracer(run_id="r2", problem_id="p2", base_dir=tmp_path) as tr:
            tr.log("a")
            tr.log("b")
            tr.log("c")
        events = load_trace(tmp_path / "r2" / "p2.jsonl")
        assert events[0]["elapsed_s"] <= events[1]["elapsed_s"] <= events[2]["elapsed_s"]

    def test_load_trace_roundtrip(self, tmp_path):
        with Tracer(run_id="r3", problem_id="p3", base_dir=tmp_path) as tr:
            tr.log("event_a", x=1)
            tr.log("event_b", y=[1, 2, 3])
        events = load_trace(tmp_path / "r3" / "p3.jsonl")
        assert len(events) == 2
        assert events[0]["x"] == 1
        assert events[1]["y"] == [1, 2, 3]

    def test_handles_non_serializable_via_default_str(self, tmp_path):
        # Path objects are not JSON-serializable by default, but our Tracer
        # uses default=str, so they should be coerced.
        with Tracer(run_id="r4", problem_id="p4", base_dir=tmp_path) as tr:
            tr.log("event", path=Path("/tmp/x"))
        events = load_trace(tmp_path / "r4" / "p4.jsonl")
        assert events[0]["path"] == "/tmp/x"

    def test_separate_problems_separate_files(self, tmp_path):
        with Tracer(run_id="r5", problem_id="alpha", base_dir=tmp_path) as tr:
            tr.log("event_for_alpha")
        with Tracer(run_id="r5", problem_id="beta", base_dir=tmp_path) as tr:
            tr.log("event_for_beta")
        assert (tmp_path / "r5" / "alpha.jsonl").exists()
        assert (tmp_path / "r5" / "beta.jsonl").exists()

    def test_append_mode_within_same_tracer(self, tmp_path):
        # Re-opening the same problem id with a fresh Tracer should append, not truncate.
        with Tracer(run_id="r6", problem_id="p", base_dir=tmp_path) as tr:
            tr.log("first")
        with Tracer(run_id="r6", problem_id="p", base_dir=tmp_path) as tr:
            tr.log("second")
        events = load_trace(tmp_path / "r6" / "p.jsonl")
        assert len(events) == 2
        assert events[0]["event"] == "first"
        assert events[1]["event"] == "second"


class TestSummariseTrace:
    def test_counts_tool_calls(self, tmp_path):
        with Tracer(run_id="r", problem_id="p", base_dir=tmp_path) as tr:
            tr.log("tool_result", tool="raft_kinetics", latency_ms=2.0)
            tr.log("tool_result", tool="raft_kinetics", latency_ms=4.0)
            tr.log("tool_result", tool="peptide_properties", latency_ms=1.5)
            tr.log("final_answer", answer="42")
        events = load_trace(tmp_path / "r" / "p.jsonl")
        s = summarise_trace(events)
        assert s["tool_counts"] == {"raft_kinetics": 2, "peptide_properties": 1}
        assert s["tool_latency_ms_avg"]["raft_kinetics"] == 3.0
        assert s["completed"] is True
        assert s["final_answer"] == "42"

    def test_marks_incomplete(self, tmp_path):
        with Tracer(run_id="r", problem_id="p", base_dir=tmp_path) as tr:
            tr.log("tool_call", tool="x")
        events = load_trace(tmp_path / "r" / "p.jsonl")
        s = summarise_trace(events)
        assert s["completed"] is False
        assert s["final_answer"] is None

    def test_counts_parse_errors(self, tmp_path):
        with Tracer(run_id="r", problem_id="p", base_dir=tmp_path) as tr:
            tr.log("parse_error", error="bad json")
            tr.log("parse_error", error="bad json again")
        events = load_trace(tmp_path / "r" / "p.jsonl")
        s = summarise_trace(events)
        assert s["parse_errors"] == 2
