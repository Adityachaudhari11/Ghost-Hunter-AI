# 👻 GhostBuster

> **IBM Bob IDE Hackathon Submission**  
> Theme: Improve a specific developer workflow — Bug Fixing & Bug Identification

<<<<<<< HEAD
![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue?logo=python&logoColor=white)
![Node 20+](https://img.shields.io/badge/Node-20%2B-green?logo=node.js&logoColor=white)
![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)
![Model: ModernBERT-large](https://img.shields.io/badge/AI-ModernBERT--large-purple?logo=huggingface&logoColor=white)
![Powered by IBM Bob IDE](https://img.shields.io/badge/Orchestration-IBM%20Bob%20IDE-054ADA?logo=ibm&logoColor=white)

=======
>>>>>>> 229ab9c67f5ef899a51c9366ffb74866333c972d
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
<<<<<<< HEAD
    │  Compile-verified LST transformation
    │  No hallucinated diffs
=======
    │  Compile-verified LST transformation — no hallucinated diffs
>>>>>>> 229ab9c67f5ef899a51c9366ffb74866333c972d
    │
    ▼
PR Opened — Engineer approves, does not debug
```

**Laya AI** (convaiinnovations/laya, Apache 2.0) is a ModernBERT-large RL decision model (~421M params). It routes signals in ~33ms using typed primitives — structurally cannot hallucinate because it never generates free text.

---

<<<<<<< HEAD
## The 5 Modules
=======
## The 4 Modules
>>>>>>> 229ab9c67f5ef899a51c9366ffb74866333c972d

| Module | Signal | Bob Action |
|---|---|---|
| **MutaCI** | PR opened | Parallel mutation agents → behavioral gap report → targeted tests |
| **FlakeHunter** | CI test fails non-deterministically | Classify root cause → generate validated fix |
| **CausalTrace** | Production error (Sentry/Datadog/K8s) | Trace + git blame + ticket → causal narrative + fix |
| **BugPort** | Bug that can't be reproduced locally | Capture production snapshot → reproduce in 90s |
<<<<<<< HEAD
| **SlopWatch** | AI-generated PR diff | Hallucination gate (PyPI/npm check) + blueprint rules + ghost-path hunt |
=======
>>>>>>> 229ab9c67f5ef899a51c9366ffb74866333c972d

---

## Prerequisites

<<<<<<< HEAD
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
| IBM watsonx.ai | `WATSONX_API_KEY` + `WATSONX_PROJECT_ID` | **Optional** — live Granite remediations; rule templates otherwise | [cloud.ibm.com](https://cloud.ibm.com/) (IAM API key + project ID) |

> **Demo mode works without any API keys.** Set `ANTHROPIC_API_KEY` only when you want live Claude test generation / fix synthesis instead of pre-recorded demo output.

---

## Quick Start (6 Steps)

### Step 1 — Clone
=======
- Python 3.11+
- Node.js 20+
- Git
- ~4 GB free disk (Laya weights = 804 MB)
- Anthropic API key — optional, all modules have `--demo` mode without it

---

## Setup

### 1. Clone this repo
>>>>>>> 229ab9c67f5ef899a51c9366ffb74866333c972d

```bash
git clone https://github.com/Adityachaudhari11/Ghost-Hunter-AI.git
cd Ghost-Hunter-AI
```

<<<<<<< HEAD
### Step 2 — Python environment
=======
### 2. Clone the real-world target repo

MutaCI runs against **class-validator** — a TypeScript + Jest project with 10k+ stars used by real production teams.

```bash
git clone https://github.com/typestack/class-validator.git real-target-jest
cd real-target-jest && npm install && cd ..
```

### 3. Python environment
>>>>>>> 229ab9c67f5ef899a51c9366ffb74866333c972d

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Mac / Linux
source venv/bin/activate

pip install -r requirements.txt
<<<<<<< HEAD
```

### Step 3 — Download Laya model weights

The weights (~804 MB) are not in git — download from HuggingFace:
=======
pip install torch transformers safetensors numpy huggingface_hub
```

### 4. Download Laya model weights

The weights (~804 MB) are not in git. Download from HuggingFace:
>>>>>>> 229ab9c67f5ef899a51c9366ffb74866333c972d

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

# Module 5: SlopWatch — AI slop gate (hallucination / blueprint / ghost path)
python -m ghostbuster.slopwatch.run_slopwatch --demo
python -m ghostbuster.slopwatch.run_slopwatch --target ./my-pr-workspace
python -m ghostbuster.slopwatch.run_slopwatch --target . --diff pr_512.diff --output-json report.json

# Live evaluation of any GitHub repo (shallow-cloned to a temp dir, auto-cleaned)
python -m ghostbuster.slopwatch.run_slopwatch --target https://github.com/psf/requests.git
python -m ghostbuster.slopwatch.run_slopwatch --target https://github.com/owner/repo.git --branch dev --keep-clone
```

### Live MutaCI run against class-validator (TypeScript, 10k+ stars)

```bash
# Clone the real-world target first
git clone https://github.com/typestack/class-validator.git real-target-jest
cd real-target-jest && npm install && cd ..

# Run (5-15 min, no --demo flag)
python -m ghostbuster.mutaci.run_mutaci --project real-target-jest/
=======
> HuggingFace repo: https://huggingface.co/convaiinnovations/laya  
> If you hit rate limits, set `HF_TOKEN` in your environment.

### 5. Demo app dependencies

```bash
cd demo-app && npm install && cd ..
```

### 6. Environment variables

```bash
cp .env.example .env
# then fill in ANTHROPIC_API_KEY (optional) and HF_TOKEN (optional)
```

```env
# .env.example
ANTHROPIC_API_KEY=sk-ant-...
HF_TOKEN=hf_...
```

---

## Running the Demo

```bash
# Full 5-module platform demo
python -m ghostbuster.run_platform --demo

# Individual modules
python -m ghostbuster.mutaci.run_mutaci --demo
python -m ghostbuster.flakehunter.run_flakehunter --demo
python -m ghostbuster.causaltrace.run_causaltrace --demo
python -m ghostbuster.bugport.run_bugport --demo

# Run against real code (MutaCI on class-validator)
python -m ghostbuster.mutaci.run_mutaci --project real-target-jest/

# Run the demo-app tests
cd demo-app && npx jest
>>>>>>> 229ab9c67f5ef899a51c9366ffb74866333c972d
```

---

## Project Structure

```
Ghost-Hunter-AI/
<<<<<<< HEAD
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
=======
>>>>>>> 229ab9c67f5ef899a51c9366ffb74866333c972d
├── ghostbuster/                  # Core Python platform
│   ├── mutaci/                   # Module 1: PR mutation testing
│   ├── flakehunter/              # Module 2: CI flake classification + fix
│   ├── causaltrace/              # Module 3: Production incident RCA
│   ├── bugport/                  # Module 4: Production reproduction
<<<<<<< HEAD
│   ├── slopwatch/                # Module 5: AI slop gate
│   │   ├── hallucination.py      # Scanner 1: PyPI/npm registry + typosquat + API check
│   │   ├── blueprint.py          # Scanner 2: architecture rule grep (RAW_SQL, CUSTOM_TIME…)
│   │   ├── ghostpath.py          # Scanner 3: swallowed exceptions, empty catch, TODOs
│   │   ├── orchestrator.py       # SlopWatchOrchestrator (parallel gate + Laya triage)
│   │   ├── run_slopwatch.py      # CLI: --target --diff --blueprint --demo --output-json
│   │   ├── demo_data.py          # Pre-recorded demo findings
│   │   └── fixtures/             # ai_slop_sample.py/.ts — deliberately bad AI code
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
=======
│   ├── shared/laya_client.py     # Laya AI wrapper (real model + fallback)
│   └── run_platform.py           # Unified demo runner
├── laya_model/                   # Laya inference scripts (weights downloaded separately)
│   ├── rl_agent_api.py
│   ├── rl_common.py
│   └── rl_agent_config.json
├── demo-app/                     # TypeScript project with intentional behavioral gaps
│   ├── src/                      # pricing.ts, cart.ts, inventory.ts
│   └── tests/
>>>>>>> 229ab9c67f5ef899a51c9366ffb74866333c972d
├── requirements.txt
├── .env.example
└── .gitignore
```

---

## Tech Stack

| Component | Technology |
|---|---|
<<<<<<< HEAD
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

## What SlopWatch Does (Module 5 — AI Slop Gate)

AI coding assistants invent packages, ignore team conventions, and swallow
errors. SlopWatch is the merge gate that catches all three failure modes in
one `run` — every finding carries a concrete fix suggestion:

1. **Slop Squatting & API Hallucination Registry** (`hallucination.py`) —
   extracts every import from the diff (Python via `ast`, JS/TS via
   `import`/`require` parsing), classifies it as stdlib / internal / external,
   and checks externals against the live **PyPI / npm** registries plus the
   installed packages. Unknown-on-offline is `WARN`, absent-from-registry is a
   critical red `BLOCK`: *"Warning: Likely AI Hallucination. High risk of
   supply chain attack."* A Levenshtein check against popular packages
   (`requestes`→`requests`, `lodahs`→`lodash`) catches typosquats, and a
   `hasattr` pass over installed packages catches invented methods
   (`os.nonexistent_xyz_123`).
2. **Semantic Grep / Blueprint Asserter** (`blueprint.py`) — greps new code
   against the team's architecture rules: `RAW_SQL` (raw SQL instead of the
   ORM wrapper), `CUSTOM_TIME` (hand-rolled `strftime` instead of
   `format_timestamp`), `DIRECT_ENV`, `PRINT_LOG`, `RAW_HTTP` (raw
   `fetch`/`axios` instead of the API client). Extend with
   `--blueprint rules.json`; `config.py`-style modules are exempt from
   `DIRECT_ENV` by design.
3. **Ghost Path & Exception Hunter** (`ghostpath.py`) — AST analysis of every
   `try/except` plus regex cover for JS/TS `catch`: `except Exception: pass`,
   empty `catch {}`, silent `return None/False/[]` fallbacks, and
   `TODO: handle failure` placeholders are all flagged with severity 5–8.

Exit code `1` = `BLOCKED` (hallucination found, do not merge);
`0` with WARNs = merge after review; `0` silent = clean.
`--demo` reproduces the gate in ~1s with no network or API keys.

### watsonx.ai remediation (the extra Bob-agent brain)

Every gate run ends with a remediation step for the top 5 findings
(all BLOCKs first). The source is always labelled:

- **Live Granite** (`💡 [watsonx.ai · ibm/granite-3-8b-instruct]`) when
  `WATSONX_API_KEY` + `WATSONX_PROJECT_ID` are set — uses the official
  `ibm-watsonx-ai` SDK if installed, otherwise the HTTPS REST API
  (only `requests` needed). Disable per-run with `--no-explain`.
- **Rule templates** (`💡 [built-in rules …]` / `[watsonx.ai · demo template]`)
  when offline or in `--demo` — the gate never breaks without credentials.

In the Bob `pr_review` workflow this is the `watsonx_remediation` step:
Granite's suggestions are posted inline on the PR (skipped while the gate
is BLOCKED — the author must replace invented imports first).

## Key Research Backing

- **Line coverage fallacy:** ρ = 0.112 correlation with actual bug detection (Inozemtseva & Holmes, 2014)
- **Flaky tests:** $2,250/dev/month wasted (Listfield, Meta Engineering, 2023)
=======
| Decision AI | Laya AI — ModernBERT-large, Apache 2.0, ~33ms |
| Reasoning AI | Claude claude-sonnet-4-6 via Anthropic API |
| IDE Orchestration | IBM Bob IDE — agent mode, parallel tasks, subagents |
| Mutation Testing | Stryker Mutator (TypeScript/Jest) |
| Code Transform | OpenRewrite LST (compile-verified patches) |
| Runtime Telemetry | MCP (Model Context Protocol) |

---

## Key Research Backing

- **Line coverage fallacy:** ρ = 0.112 correlation with actual bug detection
- **Flaky tests:** $2,250/dev/month wasted
>>>>>>> 229ab9c67f5ef899a51c9366ffb74866333c972d
- **PR-scoped mutation testing:** Meta proved feasible at scale (January 2025)
- **Human SRE vs AI RCA:** Humans still outperform AI at root cause analysis (80% vs 67%)

---

## License

<<<<<<< HEAD
Apache 2.0 — same as Laya AI.
=======
Apache 2.0
>>>>>>> 229ab9c67f5ef899a51c9366ffb74866333c972d
