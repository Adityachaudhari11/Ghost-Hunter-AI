"""DB models. Hackathon: in-memory store in API; Postgres tables for scale.

Tables planned: User, Organization, Repository, Review, ReviewFinding,
Evidence, AgentRun, PentestProject, PentestRun, TestCase, TestResult,
RecoveryTask, AuditLog. Keep simple; add Alembic migrations post-hackathon.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ReviewRow:
    id: str
    repo: str = ""
    pr_number: int = 0
    report_json: dict = field(default_factory=dict)


@dataclass
class PentestRunRow:
    id: str
    target: str = "local-test-app"
    report_json: dict = field(default_factory=dict)


# NOTE: production mapping (SQLAlchemy + Postgres) intentionally deferred
# to keep 48h scope on analyzers. DATABASE_URL is read from env when added.
