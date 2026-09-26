# 👻 GhostBuster

> **IBM Bob IDE Hackathon Submission**  
> Theme: Improve a specific developer workflow — Bug Fixing & Bug Identification

GhostBuster is a closed-loop, self-healing developer workflow that bridges live runtime telemetry directly into deterministic, compile-safe source code fixes — orchestrated entirely by IBM Bob IDE.

When a bug signal appears anywhere in the SDLC (CI failure, production incident, test flake, behavioral gap in a PR), GhostBuster catches it, explains it, and generates a fix. The engineer approves — they don't debug.

---

## Architecture

```
Bug Signal (PR diff / CI log / Sentry alert / production snapshot)
    │
    ▼
[LAYER 1: Laya AI — System 1, ~33ms, cannot hallucinate]
    │  "What type of failure?" (Choice)
    │  "How severe?" (Score 1–10)
    │  "Does this touch PII?" (Noul)
    │
    ▼
[LAYER 2: IBM Bob IDE — System 2, parallel subagents]
    │  Deep contextual analysis: traces + git + tickets + AST
    │  Causal synthesis and fix generation (Claude)
    │
    ▼
[LAYER 3: OpenRewrite — Deterministic execution]
    │  Compile-verified LST transformation
    │  No hallucinated diffs
    │
    ▼
PR Opened — Engineer approves, does not debug
```

**Laya AI** (convaiinnovations/laya, Apache 2.0) is a ModernBERT-large RL decision model (~421M params). It routes signals in ~33ms using typed primitives — structurally cannot hallucinate because it never generates free text.

---

## The 4 Modules

| Module | Signal | Bob Action |
|---|---|---|
| **MutaCI** | PR opened | Parallel mutation agents → behavioral gap report → targeted tests |
| **FlakeHunter** | CI test fails non-deterministically | Classify root cause → generate validated fix |
| **CausalTrace** | Production error (Sentry/Datadog/K8s) | Trace + git blame + ticket → causal narrative + fix |
| **BugPort** | Bug that can't be reproduced locally | Capture production snapshot → reproduce in 90s |

---

## Prerequisites

- Python 3.11+
- Node.js 20+
- Git
- ~4 GB free disk space (Laya weights = 804 MB)
- An Anthropic API key (optional — all modules have `--demo` mode without it)

---

## Setup

### 1. Clone this repo

```bash
git clone https://github.com/Adityachaudhari11/Ghost-Hunter-AI.git
cd Ghost-Hunter-AI
```

### 2. Clone the real-world target repo (for live MutaCI runs)

MutaCI runs against **class-validator** — a TypeScript + Jest project with 10k+ stars, used by real production teams.

```bash
git clone https://github.com/typestack/class-validator.git real-target-jest
cd real-target-jest && npm install && cd ..
```

### 3. Python environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Mac / Linux
source venv/bin/activate

pip install -r requirements.txt
pip install torch transformers safetensors numpy huggingface_hub
```

### 4. Download Laya model weights

The weights (~804 MB) are not in git. Download from HuggingFace:

```bash
python -c "
from huggingface_hub import snapshot_download
snapshot_download('convaiinnovations/laya', local_dir='laya_model', ignore_patterns=['*.md'])
print('Laya model ready.')
"
```

> **HuggingFace repo:** https://huggingface.co/convaiinnovations/laya  
> If the download fails unauthenticated, set `HF_TOKEN` in your environment.

### 5. Demo app dependencies

```bash
cd demo-app
npm install
cd ..
```

### 6. Environment variables

Copy `.env.example` to `.env` and fill in your key:

```bash
cp .env.example .env
```

```env
# .env.example

# Required for live Claude test generation (optional — demo mode works without it)
ANTHROPIC_API_KEY=sk-ant-...

# Optional: HuggingFace token for authenticated model downloads
HF_TOKEN=hf_...
```

---

## Running the Demo

### Full 5-module platform demo (recommended)

```bash
python -m ghostbuster.run_platform --demo
```

### Individual modules

```bash
# Module 1: MutaCI — PR behavioral gap detection
python -m ghostbuster.mutaci.run_mutaci --demo

# Module 2: FlakeHunter — CI flaky test root cause + fix
python -m ghostbuster.flakehunter.run_flakehunter --demo

# Module 3: CausalTrace — Production incident root cause
python -m ghostbuster.causaltrace.run_causaltrace --demo

# Module 4: BugPort — Production bug reproduction
python -m ghostbuster.bugport.run_bugport --demo
```

### Run against real code (MutaCI on class-validator)

```bash
python -m ghostbuster.mutaci.run_mutaci --project real-target-jest/
```

### Run the demo-app tests

```bash
cd demo-app
npx jest                               # 16 base tests
npx jest tests/pricing.mutaci.test.ts  # 4 MutaCI-generated tests
```

---

## Project Structure

```
Ghost-Hunter-AI/
├── ghostbuster/                  # Core Python platform
│   ├── mutaci/                   # Module 1: PR mutation testing
│   ├── flakehunter/              # Module 2: CI flake classification + fix
│   ├── causaltrace/              # Module 3: Production incident RCA
│   ├── bugport/                  # Module 4: Production reproduction
│   ├── shared/
│   │   └── laya_client.py        # Laya AI wrapper (real model + heuristic fallback)
│   └── run_platform.py           # Unified 5-min demo runner
│
├── laya_model/                   # Laya inference scripts (weights downloaded separately)
│   ├── rl_agent_api.py           # RLAgent class — system_one() inference API
│   ├── rl_common.py              # Model, training utilities, reward functions
│   └── rl_agent_config.json      # Model config (encoder, head_layers, temperature)
│
├── demo-app/                     # TypeScript project with intentionally thin tests
│   ├── src/                      # pricing.ts, cart.ts, inventory.ts
│   └── tests/                    # Base tests + MutaCI-generated tests
│
├── real-target-jest/             # Cloned separately — typestack/class-validator
├── requirements.txt
├── .env.example
└── .gitignore
```

---

## Tech Stack

| Component | Technology |
|---|---|
| Decision AI | Laya AI (ModernBERT-large, Apache 2.0, ~33ms) |
| Reasoning AI | Claude claude-sonnet-4-6 via Anthropic API |
| IDE Orchestration | IBM Bob IDE (agent mode, parallel tasks, subagents) |
| Mutation Testing | Stryker Mutator (TypeScript/Jest) |
| Code Transform | OpenRewrite LST (compile-verified patches) |
| Runtime Telemetry | MCP (Model Context Protocol) |
| Demo Language | TypeScript (demo-app) + Python (platform) |

---

## Key Research Backing

- **Line coverage fallacy:** ρ = 0.112 correlation with actual bug detection (Inozemtseva & Holmes, 2014)
- **Flaky tests:** $2,250/dev/month wasted (Listfield, Meta Engineering, 2023)
- **PR-scoped mutation testing:** Meta proved feasible at scale (January 2025)
- **Human SRE vs AI RCA:** Humans still outperform AI at root cause analysis (80% vs 67%)

---

## License

Apache 2.0 — same as Laya AI.
