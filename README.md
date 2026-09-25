# Ghost-Hunter-AI

Ghost-Hunter-AI is a code review tool focused on finding problems that can easily be missed in **AI-generated code**.

The idea is simple: AI can generate code quickly, but developers still have to spend time checking whether the code actually fits the project, whether the dependencies are real, and whether the code handles failures properly.

Ghost-Hunter-AI aims to automate these repetitive checks before a developer spends time doing the full review.

---

## Problem

AI coding tools have made it much faster to generate features, but the generated code is not always reliable.

A pull request generated with the help of AI can contain things such as:

* A package or API that does not actually exist
* A dependency that is not used or needed
* Code that does not follow the project's architecture
* A new implementation of something that already exists in the project
* Empty or overly broad exception handling
* `TODO` or placeholder error handling
* Fallback logic that hides an actual failure
* Unnecessary code added to the project

Finding these issues manually takes time. More importantly, some of them are easy to overlook during a normal code review.

The project therefore focuses on one specific workflow:

> **Reviewing AI-generated changes before they are merged.**

---

# Proposed Solution

Ghost-Hunter-AI takes a pull request or code change and breaks the review into smaller checks.

Instead of asking one AI agent to review everything, the review is divided between specialized agents.

```text
                    Pull Request
                         |
                         v
                IBM Bob 2.0
              Review Orchestrator
                         |
        +----------------+----------------+
        |                |                |
        v                v                v
 Dependency         Blueprint         Ghost Path
   Check              Check             Check
        |                |                |
        v                v                v
 npm / PyPI        Project Rules       AST Analysis
 Registry          + Codebase
        |                |                |
        +----------------+----------------+
                         |
                         v
                 Reuse / Duplicate
                      Check
                         |
                         v
                   Final Report
                         |
                         v
                  Human Reviewer
```

The final decision is still made by the developer. The tool is meant to reduce the amount of repetitive checking required from them.

---

# Main Checks

## 1. Dependency and API Hallucination Check

The first check looks at new imports, packages and external API references introduced by the change.

For supported ecosystems, the tool verifies whether the package exists in the actual registry.

For example:

```python
import superfastjson
```

If the package cannot be found:

```text
CRITICAL

Package: superfastjson

Registry: PyPI
Found: No

Reason:
The package could not be verified in the package registry.

Possible AI-generated dependency hallucination.
```

The tool will not automatically call this a malicious package. It reports the missing package as a risk that needs to be verified.

This check is motivated by research on **package hallucinations and slopsquatting**, where LLM-generated code can refer to packages that do not exist and those names can potentially be registered by attackers.

---

## 2. Blueprint / Project Rule Check

A common problem with AI-generated code is that it may be valid code but still be wrong for the particular project.

For example, a project may have a rule:

```text
All database operations must go through the Repository layer.
```

But an AI-generated change adds:

```python
cursor.execute("SELECT * FROM users")
```

Ghost-Hunter-AI should report:

```text
ARCHITECTURE VIOLATION

Rule:
Database access must use Repository classes.

Detected:
Direct SQL execution.

Expected:
UserRepository
```

The project rules can come from files such as:

```text
README.md
AGENTS.md
ARCHITECTURE.md
CONTRIBUTING.md
coding guidelines
```

The goal is to make the review specific to the repository instead of using only generic coding rules.

---

## 3. Ghost Path / Exception Check

This check looks specifically at how the new code handles failures.

For example:

```python
try:
    process_payment()
except Exception:
    pass
```

The tool reports:

```text
GHOST PATH

Location:
payment_service.py

Problem:
The exception is caught and ignored.

Possible result:
A failure may not be visible to the rest of the application.

Severity:
High
```

Other patterns that can be checked include:

```python
except Exception:
    pass
```

```python
except:
    pass
```

```python
# TODO: handle failure
```

```python
raise NotImplementedError()
```

and suspicious fallbacks such as:

```python
except Exception:
    return {}
```

The purpose is not to say that every fallback is wrong. The tool highlights patterns that deserve review.

---

## 4. Internal Code Reuse Check

AI often writes a new implementation without knowing that the project already has a utility for the same task.

Example:

```python
def format_date(timestamp):
    ...
```

while the project already contains:

```python
DateUtils.format_timestamp()
```

Ghost-Hunter-AI searches the existing codebase for similar functionality.

Possible result:

```text
POSSIBLE DUPLICATE

New function:
format_date()

Similar existing function:
DateUtils.format_timestamp()

The existing implementation may be reusable.
```

This helps prevent unnecessary code and keeps the codebase consistent.

---

# How IBM Bob 2.0 Fits In

IBM Bob 2.0 is used as the orchestration layer for the review process.

The main review agent receives the change and delegates different parts of the review to specialized agents.

For example:

```text
Bob 2.0
   |
   +-- Dependency Agent
   |
   +-- Blueprint Agent
   |
   +-- Ghost Path Agent
   |
   +-- Code Reuse Agent
   |
   +-- Final Review Agent
```

The independent checks can be performed in parallel where possible.

This is important to the project because the hackathon is not only about using AI to write the application. The prototype demonstrates how **agent mode, subagents and parallel tasks can be used to manage an actual developer workflow**.

---

# Review Process

The planned workflow is:

### Step 1 — Select a project

Use a real or sample GitHub project containing normal project documentation and source code.

### Step 2 — Create an AI-generated change

Generate a feature or modification using an AI coding assistant.

The test PR will intentionally contain a few realistic problems so that the system can be evaluated.

### Step 3 — Submit the change for review

Ghost-Hunter-AI receives the PR diff.

### Step 4 — Understand the project

The system reads the relevant project documentation and existing code.

### Step 5 — Run the review agents

The following checks are performed:

```text
Dependency / API verification
          +
Architecture / project rules
          +
Exception and failure paths
          +
Internal code reuse
```

### Step 6 — Collect evidence

Each finding should include:

* File
* Line or code location
* Problem
* Evidence
* Severity
* Reason for the finding

### Step 7 — Generate the review report

The results are combined into one report for the developer.

### Step 8 — Developer makes the final decision

The developer can inspect the finding and decide whether to:

```text
Fix it
Ignore it
Investigate it
Request changes
```

---

# Example Review

Suppose an AI-generated PR contains:

```python
import superfastjson

def get_user(user_id):
    try:
        cursor.execute(
            "SELECT * FROM users WHERE id = ?",
            (user_id,)
        )
    except Exception:
        pass

    return {}
```

The project already has:

```python
UserRepository.get_user()
```

Ghost-Hunter-AI could identify:

```text
1. Dependency

[CRITICAL]
superfastjson could not be verified in PyPI.


2. Architecture

[HIGH]
Direct SQL is used even though the project requires
the Repository layer.


3. Exception handling

[HIGH]
Exception is caught and ignored.


4. Internal reuse

[MEDIUM]
UserRepository.get_user() already provides similar
functionality.


5. Fallback

[MEDIUM]
An empty dictionary is returned after an exception,
which may hide the original failure.
```

The developer then receives these findings instead of having to discover all of them manually.

---

# Measuring the Impact

The hackathon requires the solution to demonstrate an improvement in the developer workflow.

Therefore, the prototype will compare manual review with Ghost-Hunter-AI.

The evaluation will measure:

| Metric                           | Manual Review | Ghost-Hunter-AI |
| -------------------------------- | ------------: | --------------: |
| Time required for initial review |      Measured |        Measured |
| Dependency checks                |        Manual |       Automated |
| Architecture checks              |        Manual |       Automated |
| Error-path checks                |        Manual |       Automated |
| Issues detected                  |      Measured |        Measured |
| Review iterations                |      Measured |        Measured |

We will use several sample PRs containing known issues and record the actual results.

The project will not assume a predefined improvement percentage. The final numbers will come from the prototype testing.

---

# 48-Hour Hackathon Scope

The first version will focus on doing a small number of checks properly rather than trying to become a complete static-analysis platform.

### Supported languages

Initial target:

```text
Python
JavaScript / TypeScript
```

### Core functionality

```text
✓ GitHub PR / diff input
✓ Import and dependency extraction
✓ npm / PyPI package verification
✓ Project documentation analysis
✓ Architecture rule checking
✓ Exception and fallback analysis
✓ Internal code similarity checking
✓ Agent-based review orchestration
✓ Review report / dashboard
```

### Not part of the initial prototype

```text
✗ Automatic code merging
✗ Fully autonomous code changes
✗ Complete vulnerability scanner
✗ Support for every programming language
✗ Guaranteed detection of every AI hallucination
```

These can be considered for future versions.

---

# Technology Stack

The exact implementation may change during development, but the planned stack is:

```text
IBM Bob 2.0
        |
        v
Agent / Subagent Workflow
        |
        +-- Python
        +-- FastAPI
        +-- AST / Static Analysis
        +-- npm / PyPI Registry APIs
        +-- Git / GitHub
        +-- Embeddings / Semantic Search
        |
        v
React + TypeScript Dashboard
```

---

# Why This Approach?

Traditional code review tools are useful for finding known classes of issues such as syntax problems, lint violations, or known security patterns.

Ghost-Hunter-AI focuses on a different part of the workflow:

> **Checking whether AI-generated code is appropriate for the specific project in which it is being introduced.**

The review therefore combines:

```text
External verification
        +
Static analysis
        +
Repository context
        +
Agent-based reasoning
```

No single component is expected to catch every problem.

---

# Research Motivation

The dependency verification part of the project is based on existing research into **LLM package hallucinations** and **slopsquatting**.

Research has shown that code-generating language models can generate package names that do not exist in package registries. This creates a potential software supply-chain risk if an attacker registers one of these commonly hallucinated package names.

This provides the motivation for checking AI-generated dependencies against real package registries.

The project extends the idea into the wider code-review workflow by also checking:

```text
External dependencies
Project architecture
Failure handling
Existing code reuse
```

---

# Expected Outcome

At the end of the hackathon, the prototype should demonstrate:

```text
AI-generated code
       ↓
Pull Request
       ↓
IBM Bob 2.0
       ↓
Parallel specialized review
       ↓
Issues + evidence
       ↓
Developer review
```

The expected benefit is a reduction in the amount of repetitive checking that a developer has to perform during code review, while keeping the developer responsible for the final decision.

---

# Project Status

🚧 **Hackathon Prototype — In Development**

The current focus is on implementing and demonstrating the core review workflow within the 48-hour hackathon.

---

## Project Goal

> **Find the ghosts in AI-generated code before they reach production.**
Module 1 — AI Code Review Auditor

Your existing Ghost-Hunter functionality:

Dependency/API Hallucination
Blueprint/Architecture violations
Ghost paths & swallowed exceptions
Duplicate/internal code detection
Evidence-based review report
Module 2 — AI Pentest Reliability Auditor

The new Idea A:

Coverage Auditor — Did the scanner actually perform the planned tests?
Failure Auditor — Which tool calls/tests failed?
Evidence Auditor — Is there enough evidence to support the reported result?
Consistency Auditor — Do repeated runs on the same controlled application produce materially different results?
Recovery Agent — Investigates missing/failed checks and retries within defined limits.
Reliability Report — Shows what was verified versus what remains unverified.

GitHub Repository:

`https://github.com/Adityachaudhari11/Ghost-Hunter-AI`

---

# Implementation Plan

This section is the build plan for Module 1 (AI Code Review Auditor) and Module 2 (AI Pentest Reliability Auditor). Follow phases in order. Do not skip T0 contracts.

## 1. Tech Stack

```text
Backend:        Python 3.11, FastAPI, Uvicorn, Pydantic v2, asyncio
Code analysis:  Python `ast`, JS/TS `tree-sitter` (+ Node 20 for parsing helpers)
Registries:     PyPI JSON API (https://pypi.org/pypi/<pkg>/json),
                npm registry (https://registry.npmjs.org/<pkg>)
Similarity:     sentence-transformers + FAISS (fallback: scikit-learn cosine)
GitHub input:   PyGithub or `gh` CLI + git diff parsing
Orchestration:  IBM Bob 2.0 subagents via `orchestrator/adapter.py`,
                fallback: `asyncio.gather()` + direct LLM calls
Frontend:       React + TypeScript + Vite (read-only report viewer)
Tests/Lint:     pytest, ruff, tsc, eslint
```

Shared contracts (define first, before any agent):

* `Finding`: `id, module, severity (CRITICAL|HIGH|MEDIUM|LOW), confidence, file, line_start, line_end, snippet, problem, evidence, suggestion`
* `ReliabilityReport`: `verified[], unverified[], coverage_pct, flaky[], recovery_attempts[]`

## 2. Phased Tasks

### T0 — Contracts + fixtures (blocks all, ~4h)

* `T0.1` Define `schemas/finding.py` and `schemas/reliability.py` with Pydantic validators.
* `T0.2` Create `demo-target-repo/` (small owned FastAPI app + `ARCHITECTURE.md`, `AGENTS.md`, `UserRepository.py`, `DateUtils.py`).
* `T0.3` Create 3 synthetic PR diffs with known ghosts + `expected-findings.json`.
* `T0.4` Create `pentest_plan.json` + 3 `tool_calls.jsonl` runs (missing check, timeout, contradictory verdict).
* Done when: `pytest schemas/` passes and fixtures have ground truth.

### T1 — Input layer (~6h)

* `T1.1` PR normalizer: PR URL / local diff -> `changed_files, hunks, new_imports`.
* `T1.2` Pentest normalizer: plan + jsonl -> normalized run table.
* `T1.3` Context builder: repo docs -> `architecture_rules.json` (`{rule, source, keywords}`).
* Done when: fixtures parse without manual fixes.

### T2 — Module 1 deterministic core (~8h, demoable alone)

* `T2.1` Dependency Agent: AST import extract (Py `ast`, JS/TS `tree-sitter`), diff vs `main`, PyPI/npm existence check, unused-import scan.
* `T2.2` Ghost-Path Agent: AST patterns (`except Exception: pass`, bare `except:`, `return {}/None` fallback, `TODO`, `NotImplementedError`, empty `.catch()`).
* Done when: synthetic PR yields expected CRITICAL+HIGH with file/line evidence.

### T3 — Module 1 LLM agents (~10h)

* `T3.1` Blueprint Agent: retrieve top-3 rules per hunk, LLM verdict with mandatory `rule_id` citation.
* `T3.2` Reuse Agent: index existing functions, cosine search (`>0.82 flag, 0.70-0.82 LLM review`), LLM verdict `duplicate/related/novel`.
* `T3.3` Merger + Final Report builder (dedupe, severity sort, JSON + Markdown).
* Done when: no finding lacks `evidence + rule_id/confidence`.

### T4 — Module 2 auditors (~10h)

* `T4.1` Coverage Auditor (`planned - executed_ok`) + Failure Auditor (classify `tool-error/timeout/auth/target-unreachable`).
* `T4.2` Evidence Auditor (claim requires request+response artifact) + Consistency Auditor (diff N=2-3 runs, flag flaky).
* `T4.3` Recovery Agent: max 2 retries, timeout cap, allowlist `curl, nmap -sV` read-only, denylist exploits/DoS/brute-force, owned demo app only.
* Done when: missing/failed/weak/flaky cases flagged; 1 retry recovers.

### T5 — API + Dashboard (~6h)

* `T5.1` FastAPI: `POST /review/pr`, `POST /audit/pentest`, `GET /jobs/{id}`, `GET /report/{id}`.
* `T5.2` React viewer: findings table (filter by severity/module), evidence drawer, verified/unverified gauge.
* `T5.3` Wire `orchestrator/adapter.py` for Bob 2.0 fan-out/fan-in with asyncio fallback.
* Done when: `POST` fixture -> `GET` report round-trips locally.

### T6 — Eval + demo (~4h)

* Run manual vs. Ghost-Hunter timing table in `Measuring the Impact`, record real numbers. No assumed percentages.
* Demo script: `AI PR -> report -> human Fix/Ignore/Investigate`.

Critical path: `T0 -> T1 -> T2 -> T3 -> T5 -> T6`. T4 parallelizes after T0.

## 3. Correct Way to Follow This Plan

1. Work phase by phase. Do not start T2 before T0 validators pass.
2. One branch per task (`t0-contracts`, `t2-deps`, ...), squash-merge after `pytest + ruff` pass.
3. Every agent output must validate against `schemas/`. Reject free-text-only findings.
4. Keep dashboard read-only. No auto-merge, no auto-fix, no live scans outside the owned demo app.
5. Update this README only with measured results, not projections.

Suggested local loop:

```bash
python -m venv .venv
pip install -r requirements.txt
cp .env.example .env   # then fill in your own keys, never commit .env
pytest -q
uvicorn app.main:app --reload
```

## 4. Credentials Policy (no leaks)

Rules:

```text
1. Never commit `.env`, `.env.local`, `*.pem`, `*.key`, or any file containing tokens.
2. Commit only `.env.example` with placeholder values.
3. `.gitignore` must contain: `.env`, `.env.*`, `!.env.example`, `*.pem`, `*.key`.
4. Load secrets only via environment variables (`os.getenv`), never hardcoded.
5. Do not print secrets in logs/reports. Redact `Authorization`, `token`, `api_key` fields.
6. If a secret is accidentally committed: rotate it immediately, purge history, do not just delete the file.
7. Enable GitHub secret scanning / push protection on the repo.
```

Planned `.env.example` (placeholders only, create when backend work starts — do not create real `.env` in git):

```bash
# Copy to .env and fill locally. Never commit .env.
GITHUB_TOKEN=ghp_REPLACE_ME
LLM_API_KEY=REPLACE_ME
LLM_BASE_URL=https://REPLACE_ME
LLM_MODEL=REPLACE_ME
BOB_API_KEY=REPLACE_ME
BOB_BASE_URL=https://REPLACE_ME
REPORT_DIR=./reports
DEMO_TARGET_REPO=./demo-target-repo
```

Verify before each commit:

```bash
git status --porcelain
git check-ignore -v .env
grep -r "ghp_\|sk-\|api_key.*[A-Za-z0-9]\{16\}" --exclude-dir=.git --exclude=.env.example . || true
```
