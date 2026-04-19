# ChemAgent

Autonomous chemistry/ChemE research agent. Plans, reasons, and solves chemical engineering problems using LLM tool-use over molecular + thermodynamic + computational tools.

**Backend:** [`claude -p`](https://docs.claude.com/en/docs/claude-code/cli-reference) — uses your existing Claude Code auth. No separate API key required.

## What it does

Given a ChemE problem like "Design a CSTR for first-order reaction A→B with k=0.1/s, CA0=2 mol/L, X=0.8, v=10 L/min", ChemAgent:

1. Plans a solution approach (ReAct loop)
2. Calls tools — molecular lookup (RDKit), thermo (Antoine), Python execution for math
3. Produces a reasoned answer with steps
4. Is scored by an LLM-judge against a ground-truth benchmark

## Stack

- **`claude -p`** (ReAct JSON actions) — agent brain, uses your Claude Code subscription
- **RDKit** — molecular properties, SMILES parsing
- **Python sandbox** — arbitrary calculations
- **Pytest** — 18 unit tests on tools
- **LLM-judge eval harness** — 5 textbook problems, scored 0-10

## Setup

```bash
cd chem-agent
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Prerequisite: [Claude Code](https://docs.claude.com/en/docs/claude-code) installed and authenticated.

## Run

```bash
# Run agent on a single problem
python examples/run_agent.py "Calculate molecular weight of aspirin"

# Run full eval suite
python evals/run_eval.py

# Run tests
pytest tests/
```

## Architecture

```
src/
  agent.py        — ReAct tool-use loop
  claude_cli.py   — subprocess wrapper for `claude -p`
  prompts.py      — system + judge prompts
  tools/
    molecular.py  — RDKit wrappers (MW, logP, SMILES)
    thermo.py     — Antoine vapor pressure, ideal gas
    python_exec.py — sandboxed calculator
evals/
  problems.json   — 5 benchmark ChemE problems
  judge.py        — LLM-judge scoring
  run_eval.py     — runs agent on all problems, reports score
tests/
  test_tools.py   — 18 unit tests
```

## Roadmap

- [x] v0.1 — single-step tool-use, 5 problems eval, claude -p backend
- [ ] v0.2 — 20 problems (reactors, heat exchangers, pinch, separations)
- [ ] v0.3 — literature search tool (arxiv + PubMed APIs)
- [ ] v0.4 — RAG over Perry's Handbook PDFs
- [ ] v0.5 — DWSIM integration for real process simulation

## Eval benchmark (v0.1)

| # | Problem type | Tools required |
|---|-------------|----------------|
| 1 | Molecular weight lookup | name_to_smiles, molecular_weight |
| 2 | Vapor pressure (Antoine) | antoine_vapor_pressure |
| 3 | CSTR sizing | python_exec |
| 4 | Distillation stages (Fenske) | python_exec |
| 5 | Mass balance | python_exec |
