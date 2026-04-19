# ChemAgent

Autonomous chemistry/chemical-engineering research agent. Plans, reasons, and solves ChemE problems using LLM tool-use over molecular, thermodynamic, computational, and literature tools.

**Backend:** [`claude -p`](https://docs.claude.com/en/docs/claude-code/cli-reference) — uses your Claude Code auth. No separate API key required.

## Why

Most LLM agents are built by CS engineers against software tasks. This one is built by a chemical engineering student to tackle *domain* problems — unit operations, kinetics, thermodynamics, separations — the kind of work a process engineer or research chemist does. It's positioned at the intersection of AI agent building and chemical engineering, a combination that's scarce in 2026.

## What it does

Given a problem like:

> Design a CSTR for aspirin production via salicylic acid + acetic anhydride with rate r = k·[SA]·[AA], k = 0.001 L/(mol·s). Feed [SA]_0 = 2.0 mol/L, [AA]_0 = 2.2 mol/L (10% excess). Target 80% conversion of SA. Plant must produce 100 kg/day of aspirin (MW 180). Compute the required CSTR volume.

ChemAgent:

1. Plans a solution path (ReAct loop, JSON actions)
2. Calls tools — molecular lookup (RDKit), vapor pressure (Antoine), Python execution with scipy, arxiv literature search
3. Returns a reasoned answer with equations, units, and final value
4. Is scored by an LLM-judge against a ground-truth benchmark

## Stack

- **`claude -p`** (ReAct JSON actions) — agent brain
- **RDKit** — molecular properties, SMILES parsing
- **Antoine equation** — vapor pressure for 6 common solvents
- **Python sandbox** — arbitrary math with `math`, `numpy`, `scipy`
- **arxiv API** — literature search, no key needed
- **Pytest** — 25 unit tests on tools
- **LLM-judge eval harness** — 23 problems across 10 ChemE subdomains

## Setup

```bash
git clone https://github.com/jincinga24-hue/chem-agent
cd chem-agent
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Prerequisite: [Claude Code](https://docs.claude.com/en/docs/claude-code) installed and authenticated.

## Run

```bash
# Single question
python examples/run_agent.py "Calculate vapor pressure of ethanol at 50 C"

# Full benchmark
python evals/run_eval.py

# Unit tests
pytest tests/
```

## Architecture

```
src/
  agent.py        ReAct tool-use loop
  claude_cli.py   subprocess wrapper for claude -p
  prompts.py      system + judge prompts (numerical and qualitative rubrics)
  tools/
    molecular.py   RDKit wrappers (MW, logP, SMILES)
    thermo.py      Antoine vapor pressure, ideal gas
    python_exec.py sandboxed Python (math, numpy, scipy)
    literature.py  arxiv search (Atom API)
evals/
  problems.json   23 benchmark problems + ground truth
  judge.py        LLM-judge scoring
  run_eval.py     runs agent on all problems, reports score
tests/
  test_tools.py   25 unit tests
```

## Benchmark: 23 problems across 10 ChemE subdomains

| Category | Problems | Example |
|----------|----------|---------|
| Molecular | 1 | MW of aspirin via RDKit |
| Thermodynamics | 1 | Antoine vapor pressure of ethanol at 50°C |
| Non-ideal thermo | 1 | Wilson activity coefficient for ethanol-water |
| Reactor design | 4 | CSTR, PFR (1st order), batch (2nd order), multi-step aspirin CSTR |
| Separation | 3 | Fenske min stages, Rachford-Rice VLE flash, Underwood min reflux |
| Heat transfer | 4 | LMTD, NTU-effectiveness, composite wall, steam condenser |
| Bioreactor | 1 | Monod chemostat steady state |
| Mass transfer | 1 | Kremser absorption stages |
| Fluid flow | 2 | Ergun packed bed, pipe friction pump power |
| Mass balance | 1 | Two-stream NaCl mixer |
| Unit conversion | 1 | SCFM methane → kg/h |
| Optimization | 3 | Wilson parameter fit, kinetic order regression, Underwood root |
| Literature | 1 | Qualitative arxiv search |

## Roadmap

- [x] v0.1 — single-step tool-use, 5 problems eval, `claude -p` backend
- [x] v0.2 — 23 problems, 10 subdomains, scipy sandbox, arxiv tool, qualitative judge
- [ ] v0.3 — RAG over Perry's Handbook + textbook PDFs
- [ ] v0.4 — trace logging, LangGraph refactor for parallel tool use
- [ ] v0.5 — DWSIM integration for real process simulation
- [ ] v0.6 — lab-in-the-loop: agent proposes + runs experiments

## Known limitations

- ReAct loop assumes Claude emits well-formed JSON. Multi-line Python code strings require `json.loads(..., strict=False)` — handled but is a known text-based tool-use failure mode. Native tool-use API (Anthropic SDK) would avoid it.
- Benchmark problems are textbook-style. Real research problems would need more ambiguity tolerance and missing-data handling.
- No persistent memory — each run is independent.
- Sandbox is not a security sandbox; it restricts imports but trusts the LLM.

## License

MIT
