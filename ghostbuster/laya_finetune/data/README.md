# Laya Fine-Tuning Data Directory

This directory holds training and validation data for domain-adapting Laya AI
to GhostBuster's three task types.

## File layout

```
data/
  ghostbuster_train.jsonl   ← main training file (600–1500 records)
  README.md                 ← this file
```

## Record format

Each line in `ghostbuster_train.jsonl` is a JSON object. Two schemas:

### Schema A — Standard Q&A (used by all three task types)

```json
{
  "state": "<context: CI log, mutant description, or DB field>",
  "qs": [
    {
      "t": "choice" | "score" | "noul",
      "ins": "<instruction>",
      "crit": <see below>,
      "y": <int — index of correct answer>,
      "soft": [<float>, ...]   // optional; must sum to 1.0
    }
  ]
}
```

**crit formats:**
- `choice`: `{"option_label": "description or null", ...}`
- `score`:  `["level 0 desc", "level 1 desc", ..., "level N desc"]`
- `noul`:   `{"false": "desc", "true": "desc"}` or `null`

---

## Data collection targets

| Task type           | Schema  | Target records | y labels      |
|---------------------|---------|----------------|---------------|
| FlakeHunter choice  | A       | 250 (50×5 cats)| 0=async 1=state 2=ordering 3=environment 4=resource |
| MutaCI score        | A       | 150–200        | 0–9 (use soft)  |
| BugPort PII noul    | A       | 200 (100+100)  | 0=not PII, 1=PII |

## Label guide

### FlakeHunter (choice) — 5 categories, y = index

| y | Label       | Key signals in the CI log                                          |
|---|-------------|--------------------------------------------------------------------|
| 0 | async       | timeout, sleep, settimeout, promise, await, ETIMEDOUT             |
| 1 | state       | shared, beforeall, global, mutation, reset, expected X received Y |
| 2 | ordering    | depends on, runs first, predecessor, sequence                     |
| 3 | environment | port, ECONNREFUSED, network, env var, external service, docker    |
| 4 | resource    | memory, OOM, CPU, disk, ENOSPC, file descriptor                   |

### MutaCI scoring (score) — 10 levels, use soft labels

| y | Level       | Example mutant                                                     |
|---|-------------|--------------------------------------------------------------------|
| 0 | trivial     | remove console.log statement                                       |
| 1 | very low    | change log level from 'info' to 'debug'                           |
| 2 | low         | off-by-one in an array index of a non-critical util                |
| 3 | medium-low  | wrong default value in an optional parameter                       |
| 4 | medium      | wrong comparison in an infrequently-used branch                    |
| 5 | medium-high | missing null check in a common code path                           |
| 6 | high        | wrong operator in a UI display calculation                         |
| 7 | very high   | wrong operator causing data loss in a write path                   |
| 8 | critical    | wrong arithmetic in a payment or pricing calculation               |
| 9 | severe      | security bypass via null check removal on auth path                |

### BugPort PII (noul) — binary, y=0 (not PII), y=1 (PII)

**NOT PII (y=0):** product_id, sku, git_sha, order_id, stock_level, is_active, created_at
**IS PII (y=1):** user_email, name, phone, ssn, password_hash, api_token, credit_card, ip_address

**Key insight:** `order_id` and `product_id` look like identifiers but are NOT personal data.
A general NLP model trained on prose text tends to over-predict these as PII (false positive).
The fine-tuning examples should explicitly teach the model that code-context identifiers ≠ PII.
