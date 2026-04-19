"""Sandboxed Python executor for arbitrary numerical calculations.

Not a security sandbox — this trusts the LLM. Just restricts imports and
redirects stdout so the agent can see what was printed.
"""
import io
import math
import contextlib
import builtins


ALLOWED_MODULES = {"math", "numpy", "statistics"}


def _safe_import(name, *args, **kwargs):
    if name.split(".")[0] not in ALLOWED_MODULES:
        raise ImportError(f"Import of '{name}' is not allowed. Allowed: {ALLOWED_MODULES}")
    return __import__(name, *args, **kwargs)


def python_exec(code: str) -> dict:
    stdout = io.StringIO()
    try:
        try:
            import numpy as np  # optional
        except ImportError:
            np = None

        sandbox_globals = {
            "__builtins__": {
                **{k: getattr(builtins, k) for k in [
                    "abs", "all", "any", "bool", "dict", "enumerate", "filter",
                    "float", "int", "len", "list", "map", "max", "min", "pow",
                    "print", "range", "reversed", "round", "set", "sorted",
                    "str", "sum", "tuple", "zip",
                ]},
                "__import__": _safe_import,
            },
            "math": math,
            "np": np,
        }

        with contextlib.redirect_stdout(stdout):
            exec(code, sandbox_globals)

        output = stdout.getvalue().strip()
        if not output:
            return {
                "stdout": "",
                "warning": "No output printed. Use print() to return your result.",
            }
        return {"stdout": output}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "stdout": stdout.getvalue()}
