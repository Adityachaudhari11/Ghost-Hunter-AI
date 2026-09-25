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
