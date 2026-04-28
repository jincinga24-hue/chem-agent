# ChemAgent

Autonomous chemistry/chemical-engineering research agent. Plans, reasons, and solves ChemE problems using LLM tool-use over molecular, thermodynamic, computational, and literature tools.

**Backend:** [`claude -p`](https://docs.claude.com/en/docs/claude-code/cli-reference) — uses your Claude Code auth. No separate API key required.

**v0.2 benchmark:** 228/230 (99.1%), 22/22 numerical problems correct across 10 ChemE subdomains.

**v0.3 (in progress):** added polymer chemistry (RAFT kinetics), peptide / AMP descriptors, structured trace logging, and RAG over a polymer-chemistry corpus — 29 benchmark problems across 17 categories, **104 unit tests**, 96.9% on the v0.3 baseline run.

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
- **Fluids module** — Colebrook/Swamee-Jain, three-reservoir networks, Crane TP-410 fittings
- **Polymer module** — RAFT kinetics (Arrhenius rate constants for 6 monomers, 3 initiators, 4 RAFT agents) with Müller dispersity, inverse target-DP design
- **Peptide / AMP module** — net charge (Henderson-Hasselbalch), Kyte-Doolittle hydrophobicity, Eisenberg hydrophobic moment μH, Chou-Fasman helix propensity — for SNAPP / antimicrobial peptide design
- **Trace logging** — every agent run writes a JSONL trace (`traces/<run_id>/<problem_id>.jsonl`) with timestamps, tool calls, latencies, and final answers. Replayable and analysable.
- **RAG (BM25)** — pure-Python BM25 over a polymer-chemistry corpus (`corpus/`). No ML dependencies. Currently covers RAFT mechanism + kinetics, AMP design, SNAPPs, polymer dispersity. Easily extended by dropping more `.txt` / `.md` files into the corpus.
- **Pytest** — 104 unit tests on tools
- **LLM-judge eval harness** — 29 problems across 17 ChemE subdomains

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
    fluids.py      pipe roughness, Reynolds, friction factors, three-reservoir solver
    polymer.py     RAFT polymerization kinetics + inverse target-DP design
    peptide.py     net charge, hydrophobic moment, helix propensity, AMP-likeness
    knowledge.py   BM25 RAG over corpus/ — keyword-grounded retrieval
  tracing.py     structured JSONL trace logger
corpus/             plain-text knowledge corpus (RAFT, AMPs, SNAPPs, dispersity)
evals/
  problems.json   29 benchmark problems + ground truth
  judge.py        LLM-judge scoring
  run_eval.py     runs agent on all problems with per-problem traces
traces/             JSONL traces, one file per problem per run
tests/
  test_tools.py     unit tests for molecular/thermo/python_exec/literature
  test_fluids.py    unit tests for fluids module
  test_polymer.py   unit tests for RAFT kinetics
  test_peptide.py   unit tests for peptide / AMP descriptors
  test_tracing.py   unit tests for trace logging
  test_knowledge.py unit tests for RAG / BM25
```

## Benchmark: 29 problems across 17 ChemE subdomains

| Category | Problems | Example |
|----------|----------|---------|
| Molecular | 1 | MW of aspirin via RDKit |
| Thermodynamics | 1 | Antoine vapor pressure of ethanol at 50°C |
| Non-ideal thermo | 1 | Wilson activity coefficient for ethanol-water |
| Reactor design | 3 | CSTR, PFR (1st order), batch (2nd order) |
| Separation | 2 | Fenske min stages, Rachford-Rice VLE flash |
| Heat transfer | 4 | LMTD, NTU-effectiveness, composite wall, steam condenser |
| Bioreactor | 1 | Monod chemostat steady state |
| Mass transfer | 1 | Kremser absorption stages |
| Fluid flow | 2 | Ergun packed bed, pipe friction pump power |
| Fluid mechanics | 2 | Torricelli three-jet tank, three-reservoir junction (Colebrook) |
| Mass balance | 1 | Two-stream NaCl mixer |
| Unit conversion | 1 | SCFM methane → kg/h |
| Design | 1 | Multi-step aspirin CSTR sizing |
| Optimization | 3 | Wilson parameter fit, kinetic order regression, Underwood root |
| Literature | 1 | Qualitative arxiv search |
| **Polymer** | **2** | **RAFT MMA Mn prediction; inverse target-DP design** |
| **Peptide / AMP** | **2** | **Melittin net charge at pH 7.4; α-helical hydrophobic moment** |

## Roadmap

- [x] v0.1 — single-step tool-use, 5 problems eval, `claude -p` backend
- [x] v0.2 — 23 problems, 10 subdomains, scipy sandbox, arxiv tool, qualitative judge
- [x] v0.3a — fluids (Colebrook, three-reservoir), polymer (RAFT kinetics), peptide / AMP descriptors
- [x] v0.3b — structured trace logging (JSONL per problem) + RAG over polymer-chemistry corpus (BM25)
- [ ] v0.3c — extend corpus to full Odian/Moad chapters + Perry's Handbook excerpts; switch BM25 to embedding-based retrieval
- [ ] v0.4 — LangGraph refactor for parallel tool use, polymer informatics (polyBERT / property prediction)
- [ ] v0.5 — DWSIM integration for real process simulation
- [ ] v0.6 — lab-in-the-loop: agent proposes + runs experiments

## Known limitations

- ReAct loop assumes Claude emits well-formed JSON. Multi-line Python code strings require `json.loads(..., strict=False)` — handled but is a known text-based tool-use failure mode. Native tool-use API (Anthropic SDK) would avoid it.
- Benchmark problems are textbook-style. Real research problems would need more ambiguity tolerance and missing-data handling.
- No persistent memory — each run is independent.
- Sandbox is not a security sandbox; it restricts imports but trusts the LLM.

## License

MIT
