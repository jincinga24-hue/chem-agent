# ChemAgent

Autonomous chemistry/ChemE research agent. Plans, reasons, and solves chemical engineering problems using LLM tool-use over molecular + thermodynamic + computational tools.

**Why this exists:** Bridge between domain chemistry knowledge and modern LLM agent systems. Portfolio project positioning me at the AI × chemistry intersection.

## What it does

Given a ChemE problem like "Design a CSTR for first-order reaction A→B with k=0.1/s, CA0=2 mol/L, X=0.8, v=10 L/min", ChemAgent:

1. Plans a solution approach
2. Calls tools — molecular property lookup (RDKit), thermodynamic calcs (Antoine eq), Python execution for math
3. Produces a reasoned answer with steps shown
4. Is evaluated by an LLM-judge against a ground-truth benchmark

## Stack

- **Anthropic Claude** (tool-use native API) — agent brain
- **RDKit** — molecular properties, SMILES parsing
- **Python sandbox** — arbitrary calculations
- **Pytest** — unit tests on tools
- **LLM-judge eval harness** — 5 textbook problems, scored 0-10

## Setup

```bash
cd chem-agent
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # add ANTHROPIC_API_KEY
```

## Run

```bash
# Run agent on a single problem
python examples/run_agent.py "Calculate molecular weight of aspirin"

# Run full eval suite
python evals/run_eval.py
```

## Architecture

```
src/
  agent.py        — tool-use loop with Claude
  prompts.py      — system prompts
  tools/
    molecular.py  — RDKit wrappers (MW, logP, SMILES)
    thermo.py     — Antoine vapor pressure, heat capacity
    python_exec.py — sandboxed calculator
evals/
  problems.json   — 5 benchmark ChemE problems + ground truth
  judge.py        — LLM-judge scoring
  run_eval.py     — runs agent on all problems, reports score
tests/
  test_tools.py   — unit tests
```

## Roadmap

- [x] v0.1 — single-step tool-use, 5 problems eval
- [ ] v0.2 — multi-step planning, 20 problems, trace logging
- [ ] v0.3 — LangGraph refactor, RAG over ChemE textbook
- [ ] v0.4 — DWSIM integration for real process simulation
- [ ] v0.5 — literature search tool (arxiv + PubMed)

## Eval benchmark (v0.1)

| # | Problem type | Tools required |
|---|-------------|----------------|
| 1 | Molecular weight lookup | molecular.mw |
| 2 | Vapor pressure calc | thermo.antoine |
| 3 | CSTR sizing | python_exec |
| 4 | Distillation stages (Fenske) | python_exec |
| 5 | Mass balance | python_exec |
