# 👻 GhostBuster

> **IBM Bob IDE Hackathon Submission**  
> Theme: Improve a specific developer workflow — Bug Fixing & Bug Identification

![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue?logo=python&logoColor=white)
![Node 20+](https://img.shields.io/badge/Node-20%2B-green?logo=node.js&logoColor=white)
![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)
![Model: ModernBERT-large](https://img.shields.io/badge/AI-ModernBERT--large-purple?logo=huggingface&logoColor=white)
![Powered by IBM Bob IDE](https://img.shields.io/badge/Orchestration-IBM%20Bob%20IDE-054ADA?logo=ibm&logoColor=white)

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

| Requirement | Version | Purpose |
|---|---|---|
| Python | 3.11+ | Platform runtime |
| Node.js | 20+ | Demo-app tests + Stryker |
| Git | any | Clone + git blame in CausalTrace |
| Disk space | ~4 GB | Laya weights (804 MB) + node_modules (~600 MB) |

---

## Required API Keys

| Key | Variable | Required? | Where to get it |
|---|---|---|---|
| Anthropic (Claude) | `ANTHROPIC_API_KEY` | **Optional** — all modules have `--demo` mode | [console.anthropic.com](https://console.anthropic.com/) |
| HuggingFace | `HF_TOKEN` | **Optional** — only needed if unauthenticated downloads fail | [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens) |

> **Demo mode works without any API keys.** Set `ANTHROPIC_API_KEY` only when you want live Claude test generation / fix synthesis instead of pre-recorded demo output.

---

## Quick Start (6 Steps)

### Step 1 — Clone

```bash
git clone https://github.com/Adityachaudhari11/Ghost-Hunter-AI.git
cd Ghost-Hunter-AI
```

### Step 2 — Python environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Mac / Linux
source venv/bin/activate

pip install -r requirements.txt
```

### Step 3 — Download Laya model weights

The weights (~804 MB) are not in git — download from HuggingFace:

```bash
python -c "
from huggingface_hub import snapshot_download
snapshot_download('convaiinnovations/laya', local_dir='laya_model', ignore_patterns=['*.md'])
print('Laya model ready.')
"
```

> **HuggingFace repo:** https://huggingface.co/convaiinnovations/laya  
> If the download requires auth, set `HF_TOKEN` in your environment first.

### Step 4 — Demo app dependencies

```bash
cd demo-app
npm install
cd ..
```

### Step 5 — Set API keys (optional)

```bash
cp .env.example .env
# Edit .env and fill in ANTHROPIC_API_KEY if you want live Claude calls
```

```
# .env
ANTHROPIC_API_KEY=sk-ant-...    # Optional: Claude test generation
HF_TOKEN=hf_...                 # Optional: authenticated HuggingFace downloads
```

### Step 6 — Run the platform demo

```bash
python -m ghostbuster.run_platform --demo
```

---

## Running Tests

```bash
# All demo-app Jest tests (16 base + 4 MutaCI-generated)
cd demo-app
npx jest

# Only the MutaCI-generated pricing gap tests
npx jest tests/pricing.mutaci.test.ts

# With coverage
npx jest --coverage
```

---

## Running Individual Modules

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

### Live MutaCI run against class-validator (TypeScript, 10k+ stars)

```bash
# Clone the real-world target first
git clone https://github.com/typestack/class-validator.git real-target-jest
cd real-target-jest && npm install && cd ..

# Run (5-15 min, no --demo flag)
python -m ghostbuster.mutaci.run_mutaci --project real-target-jest/
```

---

## Project Structure

```
Ghost-Hunter-AI/
├── bob_sessions/                 # IBM Bob IDE integration
│   ├── session_config.json       # Agent mode config — Bob reads this
│   ├── tools/                    # MCP tool definitions (one per module)
│   │   ├── mutaci.json
│   │   ├── flakehunter.json
│   │   ├── causaltrace.json
│   │   └── bugport.json
│   └── workflows/                # Named agent workflows
│       ├── pr_review.json        # Triggered on PR open
│       └── incident_response.json
│
├── ghostbuster/                  # Core Python platform
│   ├── mutaci/                   # Module 1: PR mutation testing
│   ├── flakehunter/              # Module 2: CI flake classification + fix
│   ├── causaltrace/              # Module 3: Production incident RCA
│   ├── bugport/                  # Module 4: Production reproduction
│   ├── shared/
│   │   └── laya_client.py        # Laya AI wrapper (real model + heuristic fallback)
│   ├── laya_finetune/            # Domain fine-tuning for Laya
│   │   ├── train.py              # Fine-tuning script (full + LoRA)
│   │   └── data/
│   │       ├── ghostbuster_train.jsonl   # Labelled training data (Schema A)
│   │       └── README.md                 # Data format + labelling guide
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
├── real-target-jest/             # Clone separately: typestack/class-validator
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

## Laya Fine-Tuning (Domain Adaptation)

The base Laya checkpoint was trained on general agent tasks. GhostBuster includes a domain fine-tuning setup to improve accuracy on:

- **Flake root cause classification** (5 categories: async/state/ordering/environment/resource)
- **Mutation severity scoring** (10 levels, with soft labels for payment/security paths)
- **PII detection in code context** (code identifiers ≠ PII; email/token = PII)

```bash
# Full fine-tune (~2-4 hrs on A10G, ~8-10 GB VRAM):
python ghostbuster/laya_finetune/train.py

# LoRA fine-tune (~30-45 min on T4, ~8 GB VRAM):
python ghostbuster/laya_finetune/train.py --lora

# Dry run (validates script, no GPU required):
python ghostbuster/laya_finetune/train.py --dry-run
```

See [`ghostbuster/laya_finetune/data/README.md`](ghostbuster/laya_finetune/data/README.md) for the full data format, label guide, and collection strategy.

---

## Key Research Backing

- **Line coverage fallacy:** ρ = 0.112 correlation with actual bug detection (Inozemtseva & Holmes, 2014)
- **Flaky tests:** $2,250/dev/month wasted (Listfield, Meta Engineering, 2023)
- **PR-scoped mutation testing:** Meta proved feasible at scale (January 2025)
- **Human SRE vs AI RCA:** Humans still outperform AI at root cause analysis (80% vs 67%)

---

## License

Apache 2.0 — same as Laya AI.
