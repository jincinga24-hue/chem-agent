"""Claude CLI backend — shells out to `claude -p` using your Claude Code auth.

No API key required. Uses your existing Claude Code subscription.
"""
import json
import os
import subprocess


DEFAULT_MODEL = os.getenv("AGENT_MODEL", "opus")


class ClaudeCLIError(RuntimeError):
    pass


def claude_call(
    prompt: str,
    system_prompt: str | None = None,
    model: str = DEFAULT_MODEL,
    timeout_s: int = 180,
) -> str:
    """Send a prompt to Claude via the CLI. Returns the text result."""
    cmd = [
        "claude", "-p",
        "--model", model,
        "--output-format", "json",
        "--no-session-persistence",
    ]
    if system_prompt:
        cmd.extend(["--append-system-prompt", system_prompt])

    try:
        proc = subprocess.run(
            cmd,
            input=prompt,
            text=True,
            capture_output=True,
            timeout=timeout_s,
        )
    except subprocess.TimeoutExpired as e:
        raise ClaudeCLIError(f"claude -p timed out after {timeout_s}s") from e
    except FileNotFoundError as e:
        raise ClaudeCLIError("claude CLI not found on PATH. Is Claude Code installed?") from e

    if proc.returncode != 0:
        raise ClaudeCLIError(f"claude -p exited {proc.returncode}: {proc.stderr[:500]}")

    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError as e:
        raise ClaudeCLIError(f"claude output not JSON: {proc.stdout[:500]}") from e

    if payload.get("is_error"):
        raise ClaudeCLIError(f"claude reported error: {payload.get('result', payload)}")

    return payload.get("result", "")
