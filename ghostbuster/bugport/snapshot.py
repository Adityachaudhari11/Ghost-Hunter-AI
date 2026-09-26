"""
BugPort — Production Bug Snapshot.

Represents a PII-masked capture of minimal execution context needed to
reproduce a production bug locally. The sidecar captures this in production;
BugPort reconstructs it locally via 3 parallel Bob subagents.

Snapshot contains:
  - call_stack: the exact frames (file, line, function)
  - db_query_result: minimal DB rows involved in the bug (PII-masked)
  - env_spec: node version, OS, memory, key env flags
  - git_sha: exact commit running in production
  - race_window_ms: timing window for race conditions (if applicable)
"""

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class BugSnapshot:
    bug_id: str
    description: str
    git_sha: str
    call_stack: list[dict]
    db_query_result: list[dict]       # PII-masked
    env_spec: dict
    race_window_ms: Optional[int] = None
    custom_state: dict = field(default_factory=dict)


# ── Demo snapshot — race condition in inventory reservation ────────────────
DEMO_SNAPSHOT = BugSnapshot(
    bug_id="BUG-9182",
    description="Race condition: double-reservation of the last stock unit causes oversell",
    git_sha="a7c3f29",
    call_stack=[
        {"file": "src/inventory.ts", "line": 44, "function": "reserveStock",
         "context": "if (entry.available < quantity) throw new InsufficientStockError()"},
        {"file": "src/checkout/order.ts", "line": 102, "function": "processOrder",
         "context": "await inventory.reserveStock(item.productId, item.quantity)"},
        {"file": "src/checkout/checkout.controller.ts", "line": 158, "function": "handleCheckout",
         "context": "await Promise.all(cart.items.map(item => processOrder(cart, user, item)))"},
    ],
    db_query_result=[
        {"product_id": "PROD-XYZ-***", "available": 1, "reserved": 4, "total": 5},
    ],
    env_spec={
        "node": "20.11.0",
        "platform": "linux/amd64",
        "memory_mb": 512,
        "INVENTORY_LOCK": "false",
        "DB_POOL_SIZE": "10",
    },
    race_window_ms=12,
    custom_state={
        "concurrent_checkouts": 2,
        "product_id": "PROD-XYZ-***",
        "quantity_per_checkout": 1,
    },
)
