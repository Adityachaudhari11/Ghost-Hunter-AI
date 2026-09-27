# SecurePort — Deployment-Ready Security Scanner Plan

## Overview

**Goal:** Add a 5th GhostBuster module called **SecurePort** that takes any app (local path or GitHub URL) and makes it deployment-ready by:

1. **Gray-box pen testing** — static + lightweight dynamic analysis of the code for OWASP-class vulnerabilities (injection, auth bypass, insecure deserialization, exposed secrets, SSRF, etc.)
2. **API key / secret detection and mocking** — finds hardcoded secrets, replaces them with `os.environ["KEY"]` / `process.env.KEY` references, generates `.env.example` stubs and mock values so tests keep passing
3. **Deployment readiness report** — a structured checklist of what was fixed, what needs manual review, and what blocks deployment

The module follows the identical orchestrator pattern used by the 4 existing modules:
- `LayaClient` for fast (~33ms) Laya decisions (choice: which vulnerability class, noul: is this a real secret, score: severity)
- `--demo` mode with pre-recorded data so it runs without any API keys
- A Bob IDE MCP tool definition so it can be triggered from the session
- A new `security_scan` workflow in `bob_sessions/workflows/`

**Scope:** New Python module only. No changes to existing modules, no Laya fine-tuning, no test infra changes.

---

## Architecture Diagram (text)

```
Input: local path OR GitHub URL
         │
         ▼
[SecurePort Orchestrator]
    │
    ├─► Clone/validate repo (GitAgent)
    │
    ├─► [PARALLEL Bob subagents]
    │      ├─ SecretScanAgent   — find hardcoded keys, tokens, passwords
    │      ├─ VulnScanAgent     — static OWASP checks (injection, auth, SSRF, etc.)
    │      └─ DepScanAgent      — outdated/vulnerable npm/pip dependencies
    │
    ├─► Laya AI decisions per finding:
    │      choice: which vulnerability class
    │      noul: is this a real secret (vs test fixture / example value)
    │      score: severity 1-10
    │
    ├─► SecretMocker
    │      replace hardcoded → os.environ / process.env
    │      write .env.example stubs
    │      generate mock values for tests
    │
    ├─► FixGenerator (Claude, optional)
    │      generate patches for high-severity vulns
    │
    └─► DeploymentReport
           ✅ fixed automatically
           ⚠️  review required
           🚫 blocks deployment
```

---

## Sub-Tasks

---

### Sub-Task 1 — Core Orchestrator Scaffold

**Status:** [ ] pending

**Intent:**
Create the `ghostbuster/secureport/` package with the same structural pattern as the 4 existing modules. This is the foundation that all other sub-tasks build on.

**Expected Outcomes:**
- `ghostbuster/secureport/__init__.py` exists
- `ghostbuster/secureport/orchestrator.py` has a `SecurePortOrchestrator` class with `__init__(demo_mode)` and `run(target, anthropic_api_key)` that returns a structured report dict
- `ghostbuster/secureport/run_secureport.py` is a CLI entry point with `--target`, `--demo`, `--anthropic-api-key` args
- `python -m ghostbuster.secureport.run_secureport --demo` runs without error and prints a banner + summary
- `ghostbuster/run_platform.py` is updated to include SecurePort as Module 5 when `--module all` or `--module secureport`

**Todo List:**
1. Create `ghostbuster/secureport/__init__.py` (empty, just exports)
2. Create `ghostbuster/secureport/orchestrator.py` with `SecurePortOrchestrator` class:
   - `__init__(self, demo_mode=False)` — init `LayaClient`, print header banner
   - `run(self, target=".", anthropic_api_key="") -> dict` — dispatch to `_run_demo_animated()` or `_run_real()`
   - `_run_demo_animated()` — use pre-recorded demo data, animate output, return report dict
   - `_run_real(target, client)` — placeholder that imports and calls the real scanners
3. Create `ghostbuster/secureport/run_secureport.py` as CLI entry point:
   - `argparse` with `--target` (default: `.`), `--demo` flag, `--anthropic-api-key`
   - Loads `.env` via `python-dotenv` if present
   - Instantiates and runs `SecurePortOrchestrator`
4. Add Module 5 block to `ghostbuster/run_platform.py` (after BugPort, before Platform Summary)
5. Add `secureport` to `--module` choices in `run_platform.py`

**Relevant Context:**
- Pattern to follow: `ghostbuster/bugport/orchestrator.py` — same `__init__` / `run` / `_run_demo_animated` / `_run_real` structure
- CLI pattern: `ghostbuster/bugport/run_bugport.py`
- Platform runner: `ghostbuster/run_platform.py` lines 58–110 (module blocks pattern)
- `LayaClient` import: `from ghostbuster.shared.laya_client import LayaClient`
- API key pattern: `key = anthropic_api_key or os.environ.get("ANTHROPIC_API_KEY")`

---

### Sub-Task 2 — Demo Data

**Status:** [ ] pending

**Intent:**
Create realistic pre-recorded demo data for SecurePort so the `--demo` flag produces convincing output with zero external calls. This is what judges see in the 5-minute demo.

**Expected Outcomes:**
- `ghostbuster/secureport/demo_data.py` contains a `DEMO_TARGET` dict with a realistic fake repo structure (name, files, language)
- `DEMO_FINDINGS` list contains 6–8 pre-recorded findings across all 3 finding types (secret, vuln, dep):
  - 2 hardcoded secrets (Stripe key, AWS secret) — `noul` = 0.97 (real secret)
  - 1 env var example value — `noul` = 0.08 (not a real secret, ignore)
  - 2 OWASP vulns (SQL injection in raw query, missing auth on admin route)
  - 1 outdated dependency with known CVE
  - 1 SSRF-adjacent pattern (unvalidated URL fetch)
- `DEMO_MOCKED_FILES` dict shows before/after for the 2 secret-replacement patches
- `DEMO_ENV_EXAMPLE` string shows the generated `.env.example` additions
- `DEMO_MOCK_VALUES` dict shows test mock values generated for each replaced key

**Todo List:**
1. Create `ghostbuster/secureport/demo_data.py`
2. Define `DEMO_TARGET` with fake repo metadata (name, language, file count)
3. Define `DEMO_FINDINGS` list — each finding is a dict with: `id`, `type` (secret/vuln/dep), `file`, `line`, `severity` (1-10), `laya_score`, `laya_noul`, `description`, `cwe`, `fix`
4. Define `DEMO_MOCKED_FILES` with before/after patches for 2 hardcoded secrets
5. Define `DEMO_ENV_EXAMPLE` string (the 2 new lines to add to `.env.example`)
6. Define `DEMO_MOCK_VALUES` dict (key name → safe mock value for tests)

**Relevant Context:**
- Follow the pattern in `ghostbuster/causaltrace/demo_data.py` (DEMO_SENTRY_EVENT, DEMO_GIT_HISTORY, DEMO_TICKET)
- Follow the pattern in `ghostbuster/bugport/snapshot.py` (BugSnapshot dataclass + DEMO_SNAPSHOT)
- Demo findings should be realistic enough to tell the deployment-readiness story

---

### Sub-Task 3 — Secret Scanner

**Status:** [ ] pending

**Intent:**
Create the `SecretScanAgent` — a static scanner that finds hardcoded API keys, tokens, and passwords in source code using regex patterns, then uses Laya `noul` to confirm each match is a real secret (not a test fixture or placeholder).

**Expected Outcomes:**
- `ghostbuster/secureport/secret_scanner.py` exports a `scan_secrets(file_path) -> list[dict]` function
- Detects common secret patterns: AWS keys, Stripe keys, GitHub tokens, generic `api_key =`, JWT secrets, private key PEM blocks, passwords in connection strings
- Each finding has: `file`, `line`, `match_type`, `raw_value` (truncated to 6 chars + `***`), `laya_noul` (real vs fixture), `severity`
- Laya `noul` call: `"This value '{truncated}' in {context} is a real production secret or API key (not a placeholder, test fixture, or example value)"`
- Returns only findings where `laya_noul > 0.5` (filtered by Laya)
- Works on `.ts`, `.js`, `.py`, `.env`, `.yaml`, `.json` files
- In demo mode, returns `DEMO_FINDINGS` secret subset directly

**Todo List:**
1. Create `ghostbuster/secureport/secret_scanner.py`
2. Define `SECRET_PATTERNS` dict — mapping pattern name to compiled regex:
   - `aws_key`: `AKIA[0-9A-Z]{16}`
   - `stripe_key`: `sk_live_[0-9a-zA-Z]{24,}`
   - `github_token`: `ghp_[0-9a-zA-Z]{36}`
   - `generic_api_key`: `(api_key|apikey|API_KEY)\s*[=:]\s*["'][^"']{10,}["']`
   - `jwt_secret`: `(jwt_secret|JWT_SECRET|secret_key)\s*[=:]\s*["'][^"']{8,}["']`
   - `password_in_url`: `(postgresql|mysql|mongodb)://[^:]+:[^@]+@`
   - `private_key_pem`: `-----BEGIN (RSA |EC )?PRIVATE KEY-----`
3. Define `IGNORE_PATTERNS` list — values to skip: `YOUR_KEY_HERE`, `sk-ant-...`, `example`, `placeholder`, `<YOUR_`, `INSERT_`, `TODO`, `CHANGEME`
4. Implement `scan_file(file_path: str, laya: LayaClient) -> list[dict]` — read file, find all regex matches, filter IGNORE_PATTERNS, call Laya noul per match, return confirmed findings
5. Implement `scan_secrets(target_dir: str, laya: LayaClient) -> list[dict]` — walk directory, skip `.git/`, `node_modules/`, `venv/`, call `scan_file` per eligible file
6. Add Laya noul call with context string as described above

**Relevant Context:**
- `LayaClient.noul(statement) -> float` — returns 0.0–1.0 probability statement is true
- Heuristic fallback already handles `"secret"`, `"token"`, `"password"` keywords (returns 0.82)
- See `ghostbuster/bugport/orchestrator.py` lines 65–67 for the PII noul pattern to mirror
- `IGNORE_PATTERNS` is critical — the `.env.example` in this repo has `sk-ant-...` and `hf_...` which must NOT be flagged

---

### Sub-Task 4 — Vulnerability Scanner

**Status:** [ ] pending

**Intent:**
Create the `VulnScanAgent` — a static OWASP-class vulnerability scanner that checks source code for injection risks, missing auth, SSRF patterns, insecure deserialization, and similar gray-box findings. Uses Laya `choice` to classify the vulnerability type and Laya `score` to rate severity.

**Expected Outcomes:**
- `ghostbuster/secureport/vuln_scanner.py` exports `scan_vulns(target_dir, laya) -> list[dict]`
- Detects at minimum: SQL injection (raw string queries), command injection (shell=True / exec), missing auth on route handlers, SSRF (unvalidated URL fetch), hardcoded admin credentials, eval() / exec() on user input
- Each finding has: `file`, `line`, `cwe`, `vuln_type`, `severity` (Laya score 1-10), `snippet`, `fix_suggestion`
- Laya `choice` call: `"Vulnerability pattern in {file}:{line}: '{snippet}'. What OWASP class is this?"` with options `["injection", "broken_auth", "ssrf", "insecure_deserialization", "security_misconfiguration", "sensitive_data_exposure"]`
- Laya `score` call: `"Vulnerability: {vuln_type} in {file}:{line}. Snippet: '{snippet}'. Rate severity for production deployment."` scale (1-10)
- Returns findings sorted by severity descending

**Todo List:**
1. Create `ghostbuster/secureport/vuln_scanner.py`
2. Define `VULN_PATTERNS` list — each entry is a dict with `name`, `pattern` (regex), `cwe`, `default_fix`, supporting `.ts`, `.js`, `.py`
   - SQL injection: `(execute|query|raw)\s*\(.*\+` or `f"SELECT.*{`
   - Command injection: `subprocess.*shell=True` or `exec\(` or `eval\(`
   - SSRF: `(fetch|requests\.get|axios\.get)\s*\(.*req\.(params|query|body)`
   - Hardcoded admin: `(admin|root|superuser)\s*[=:]\s*["'].*["']` + `password\s*[=:]`
   - Missing auth: route decorator without auth middleware (heuristic: `@app.route` or `router.get` without guard)
3. Implement `scan_file_vulns(file_path, laya) -> list[dict]` — apply all patterns, build context string, call Laya choice + score per match
4. Implement `scan_vulns(target_dir, laya) -> list[dict]` — walk directory, aggregate, sort by severity
5. Map each vuln class to a CWE number for the report (CWE-89 SQL injection, CWE-78 command injection, CWE-918 SSRF, etc.)

**Relevant Context:**
- `LayaClient.choice(context, options)` — see `ghostbuster/mutaci/orchestrator.py` lines 82–85 for pattern
- `LayaClient.score(context, scale)` — see `ghostbuster/mutaci/orchestrator.py` lines 119–120 for pattern
- Gray-box level: static analysis only (no running the code); findings are heuristic, not guaranteed

---

### Sub-Task 5 — Secret Mocker (env var replacement + mock values)

**Status:** [ ] pending

**Intent:**
Create the `SecretMocker` — the component that takes confirmed secret findings and produces: (a) patched source files where hardcoded values are replaced by env var references, (b) new `.env.example` entries, and (c) mock values for tests so nothing breaks.

**Expected Outcomes:**
- `ghostbuster/secureport/secret_mocker.py` exports:
  - `mock_secret(finding: dict, language: str) -> MockResult` — returns the replacement snippet and mock value
  - `apply_mocks(target_dir: str, findings: list[dict]) -> MockSummary` — applies all replacements and writes `.env.example`
- For TypeScript/JS: replaces `"sk_live_abc123"` with `process.env.STRIPE_SECRET_KEY` and adds `STRIPE_SECRET_KEY=sk_live_xxx` to `.env.example`
- For Python: replaces `"sk_live_abc123"` with `os.environ["STRIPE_SECRET_KEY"]` (or `os.environ.get("STRIPE_SECRET_KEY")`)
- Each mock value is a clearly fake but valid-format value (e.g., `sk_live_MOCK_VALUE_FOR_TESTS_ONLY_DO_NOT_USE`)
- A `MockResult` dataclass has: `env_var_name`, `replacement_code`, `mock_value`, `env_example_line`
- A `MockSummary` has: `patched_files` (list), `env_example_additions` (list of strings), `mock_values` (dict)
- Does NOT write files in demo mode — only returns the report of what would be done

**Todo List:**
1. Create `ghostbuster/secureport/secret_mocker.py`
2. Define `MockResult` dataclass and `MockSummary` dataclass
3. Implement `infer_env_var_name(finding: dict) -> str` — derives canonical env var name from match_type:
   - `aws_key` → `AWS_SECRET_ACCESS_KEY`
   - `stripe_key` → `STRIPE_SECRET_KEY`
   - `github_token` → `GITHUB_TOKEN`
   - `generic_api_key` → upper-snake-case of the original variable name
   - `jwt_secret` → `JWT_SECRET`
4. Implement `make_mock_value(match_type: str, env_var_name: str) -> str` — creates clearly-fake value:
   - Preserves prefix format (e.g. `sk_live_MOCK_TEST_VALUE`)
   - Appends `_MOCK_VALUE_FOR_TESTS` suffix when no natural prefix
5. Implement `mock_secret(finding, language) -> MockResult` — builds the replacement code snippet based on language
6. Implement `apply_mocks(target_dir, findings, dry_run=False) -> MockSummary` — applies all replacements in-place, updates `.env.example`

**Relevant Context:**
- demo-app uses TypeScript → `process.env.KEY`
- GhostBuster platform uses Python → `os.environ.get("KEY", "")`
- `.env.example` already has `ANTHROPIC_API_KEY=sk-ant-...` — append new entries, never overwrite
- `dry_run=True` in demo mode — return summary without touching files
- Language detection: `.ts`/`.js`/`.tsx`/`.jsx` → TypeScript; `.py` → Python; `.go` → Go; else → generic

---

### Sub-Task 6 — MCP Tool Definition + Bob Workflow

**Status:** [ ] pending

**Intent:**
Wire SecurePort into Bob IDE by adding a `secureport.json` MCP tool definition, a `security_scan.json` workflow, and updating `session_config.json` to register both.

**Expected Outcomes:**
- `bob_sessions/tools/secureport.json` exists with full input/output schema
- `bob_sessions/workflows/security_scan.json` defines a 4-step workflow: clone/validate → parallel scan → mock secrets → generate report
- `bob_sessions/session_config.json` lists `secureport.json` in the `tools` array and `security_scan.json` in the `workflows` array

**Todo List:**
1. Create `bob_sessions/tools/secureport.json`:
   - `name`: `secureport`
   - `description`: 1-sentence description of the gray-box security scan + deployment-readiness check
   - `invocation.args`: `["-m", "ghostbuster.secureport.run_secureport"]`
   - `input_schema`: `target` (string, local path or GitHub URL, default `.`), `demo` (bool), `anthropic_api_key` (string)
   - `output_schema`: `secrets_found` (int), `secrets_mocked` (int), `vulns_found` (int), `high_severity_count` (int), `deployment_blocked` (bool), `env_example_additions` (array), `report` (string)
   - `laya_decision`: all 3 types used — choice (vuln class), noul (real secret), score (severity)
   - 2 examples: demo run, live run on GitHub URL
2. Create `bob_sessions/workflows/security_scan.json`:
   - trigger: `pre_deploy` or `manual`
   - Steps: `clone_target` → `parallel_scan` → `mock_secrets` → `generate_report`
3. Update `bob_sessions/session_config.json`:
   - Add `"bob_sessions/tools/secureport.json"` to `tools` array
   - Add `"bob_sessions/workflows/security_scan.json"` to `workflows` array

**Relevant Context:**
- Follow exact JSON structure of `bob_sessions/tools/bugport.json` (has noul laya_decision)
- Follow exact step structure of `bob_sessions/workflows/incident_response.json`
- `session_config.json` current `tools` array has 4 entries — add 5th

---

### Sub-Task 7 — README + API Key Reference Update

**Status:** [ ] pending

**Intent:**
Update `README.md` to document SecurePort, the API key table, and the concept of mock values. This is the final deliverable judges read.

**Expected Outcomes:**
- README module table has a 5th row for SecurePort
- A new "SecurePort — Deployment Readiness" section explains what the module does, what it scans, and how mock values work
- The API key table is accurate (no new keys required; same 2 optional keys)
- Running instructions include: `python -m ghostbuster.secureport.run_secureport --demo`
- Project structure tree includes `ghostbuster/secureport/`
- `.env.example` has a comment explaining that SecurePort will append entries for detected secrets

**Todo List:**
1. Add `secureport` row to the 4-module table in README.md
2. Add a "SecurePort — Deployment Readiness" section after the module table
3. Add `python -m ghostbuster.secureport.run_secureport --demo` to the "Running Individual Modules" section
4. Update the project structure tree to include `ghostbuster/secureport/`
5. Update `.env.example` to add a comment block explaining SecurePort mock value stubs

**Relevant Context:**
- README.md module table is at line 41 (4 rows currently)
- Running Individual Modules section lists 4 `python -m ghostbuster...` commands
- Project structure tree starts at line 163
- `.env.example` has 2 keys with comments

---

## Implementation Order

Sub-tasks must be implemented in this order (each depends on the previous):

```
1 → 2 → 3 → 4 → 5 → 6 → 7
Scaffold → Demo Data → Scanners → Mocker → Bob Wire → README
```

Sub-tasks 3 and 4 (SecretScanner and VulnScanner) can be done in parallel once Sub-task 2 is done.
