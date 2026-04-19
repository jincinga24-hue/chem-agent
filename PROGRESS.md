# ChemAgent — Progress Log

Last updated: 2026-04-19

## Current state

- **Repo:** https://github.com/jincinga24-hue/chem-agent (public)
- **Local:** `~/Documents/Playground/chem-agent`
- **Version:** v0.2
- **Benchmark:** 228/230 (99.1%), 22/22 numerical problems correct
- **Tests:** 25/25 passing
- **Backend:** `claude -p` subprocess (uses Claude Code auth, no API key)

## What's built (v0.1 + v0.2)

### Tools
- `molecular.py` — RDKit: MW, logP, SMILES parsing, name→SMILES (17 common compounds)
- `thermo.py` — Antoine vapor pressure (water, ethanol, methanol, benzene, toluene, acetone), ideal gas volume
- `python_exec.py` — sandboxed Python with `math`, `numpy`, `scipy`, `statistics`
- `literature.py` — arxiv.org Atom API search, no key required

### Agent
- ReAct loop over `claude -p`
- Max 12 tool turns
- JSON action parsing with `strict=False` (tolerates multi-line code)
- Trace logging + structured result dataclass

### Eval harness
- 23 problems across 10 ChemE subdomains
- LLM-judge scoring (numerical rubric + qualitative rubric)
- Numerical tolerance check as backup
- Results saved to `eval_results/run-<timestamp>.json`

### Subdomains covered
molecular, thermo, non-ideal thermo, reactor design (CSTR/PFR/batch/multi-step), separation (Fenske, Rachford-Rice, Underwood), heat transfer (LMTD/NTU/composite wall/condenser), bioreactor (Monod), mass transfer (Kremser), fluid flow (Ergun/pipe friction), optimization (Wilson fit/kinetic regression/Underwood root), literature

## Commit history

1. `ff83650` scaffold ChemAgent — Anthropic SDK backend
2. `a48d475` refactor: swap to `claude -p` subprocess backend
3. `6575ebb` expand benchmark to 15 problems
4. `419f810` add arxiv search + 5 harder problems + fix Antoine bug
5. `678ff13` qualitative judge + scipy sandbox + 3 optimization problems + parse fix
6. `74df52d` README + LICENSE
7. `7e62ec3` add v0.2 benchmark score to README

## Known limitations (documented in README)

- ReAct JSON parsing — multi-line code strings needed `strict=False` fix
- No persistent memory between runs
- Python sandbox restricts imports but trusts the LLM (not a security sandbox)
- Benchmark problems are textbook-style, not research-messy

## Next-up roadmap

### v0.3 — RAG over Perry's Handbook (next C-week priority)
Goal: stop hallucinating correlations, ground answers in real reference material.
Tasks:
- Source Perry's PDF (or equivalent: Smith/Van Ness thermo, Fogler reactor design)
- Chunk + embed (llama-index or raw with sentence-transformers)
- Vector store (chroma local, no cloud)
- Add `reference_search` tool to agent
- Add 5 problems that require citing a textbook

### v0.4 — Trace logging + LangGraph refactor
- Structured trace export to JSON per run (already partial)
- Optional: migrate ReAct loop to LangGraph for parallel tool use
- Add `eval_results/` trending dashboard script

### v0.5 — DWSIM integration
- Install DWSIM, test Python API
- Add `dwsim_simulate` tool: takes column/reactor spec JSON, returns converged results
- Problems: distillation sizing with rigorous VLE, heat exchanger rating, reactor optimization

### v0.6 — Lab-in-the-loop (aspirational)
- Agent proposes experiments
- Runs DWSIM simulation as virtual lab
- Updates hypothesis, iterates

## Portfolio next-moves (non-code)

- [ ] Pin `chem-agent` on GitHub profile
- [ ] Add to LinkedIn Featured section
- [ ] Write blog post: "I'm a ChemE student. Here's the LLM agent I built for my own homework." (~600 words)
- [ ] Email one Uni Melb professor doing ML for chemistry/materials — show repo, ask to contribute
- [ ] Share on Twitter/X tagged with #AI4Science or similar — Andrew White (@andrewwhite01) is the community hub

## To resume next session

1. `cd ~/Documents/Playground/chem-agent`
2. `source .venv/bin/activate`
3. `pytest tests/` — confirm 25/25 still passing
4. Pick v0.3 RAG or another roadmap item
5. Read this file + README for context

## Quick commands

```bash
# Run one question
python examples/run_agent.py "Calculate vapor pressure of ethanol at 50 C"

# Run full eval (takes ~15 min)
python evals/run_eval.py

# Run tests
pytest tests/ -v

# Check last eval result
ls -t eval_results/ | head -1
```
