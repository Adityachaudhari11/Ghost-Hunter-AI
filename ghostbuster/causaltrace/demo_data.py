"""
CausalTrace — Pre-recorded demo data for presentation.

Models a real incident flow:
  Sentry alert (TypeError in guest checkout) →
  Traced back to PR #447 (11 days ago) which removed a null check →
  Linked ticket had a warning about null user in guest flow

This mirrors the 2-hour SRE investigation that GhostBuster does in 90s.
"""

DEMO_SENTRY_EVENT = {
    "id": "evt_abc123",
    "title": "TypeError: Cannot read properties of null (reading 'id')",
    "culprit": "src/checkout/order.ts in processOrder",
    "timestamp": "2026-09-25T14:32:11Z",
    "environment": "production",
    "release": "v2.14.1",
    "stack_trace": [
        {"file": "src/checkout/order.ts", "line": 87, "function": "processOrder",
         "context": "const userId = user.id;  // ← TypeError here"},
        {"file": "src/checkout/checkout.controller.ts", "line": 142, "function": "handleCheckout",
         "context": "await processOrder(cart, user, paymentInfo)"},
        {"file": "src/routes/checkout.ts", "line": 28, "function": "POST /checkout",
         "context": "return checkoutController.handleCheckout(req, res)"},
    ],
    "tags": {"transaction": "POST /checkout", "user_type": "guest"},
    "event_count_last_24h": 847,
    "affected_users": 312,
}

DEMO_GIT_HISTORY = [
    {
        "sha": "f3a9b12",
        "short_sha": "f3a9b12",
        "author": "dev@company.com",
        "date": "2026-09-14T10:22:43Z",
        "pr_number": 447,
        "message": "refactor: simplify order processing, remove legacy null checks",
        "files_changed": ["src/checkout/order.ts", "src/checkout/order.test.ts"],
        "diff_summary": "-  if (!user || !user.id) { throw new Error('User required'); }\n-  const userId = user ? user.id : null;\n+  const userId = user.id;",
    },
    {
        "sha": "c2e1d45",
        "short_sha": "c2e1d45",
        "author": "dev2@company.com",
        "date": "2026-09-12T08:15:00Z",
        "pr_number": 441,
        "message": "feat: allow guest checkout without account creation",
        "files_changed": ["src/routes/checkout.ts", "src/checkout/checkout.controller.ts"],
        "diff_summary": "+  // Allow null user for guest flow\n+  const user = req.session.user || null;",
    },
]

DEMO_TICKET = {
    "id": "ENG-2847",
    "title": "Guest checkout: pass null user through checkout flow",
    "created": "2026-09-11T14:00:00Z",
    "status": "Done",
    "linked_pr": 441,
    "description": (
        "Guest users don't have accounts. The checkout flow should allow user=null "
        "for guests. Make sure downstream code handles null user gracefully. "
        "WARNING: processOrder and related functions must be updated to handle null user."
    ),
    "comments": [
        "PR #441 handles the route layer. Need follow-up to update processOrder.",
        "Follow-up ticket ENG-2901 created but not yet assigned.",
    ],
}

DEMO_CAUSAL_NARRATIVE = """
**Root Cause:** TypeError crash in production checkout (847 errors, 312 users affected)

**Causal Chain (reconstructed by GhostBuster in 90 seconds):**

1. **PR #441** (Sept 12) introduced guest checkout — correctly passes `user = null`
   for guest sessions through the route layer.

2. **ENG-2847 ticket** explicitly warned: "processOrder and related functions must be
   updated to handle null user." A follow-up ticket (ENG-2901) was created but never assigned.

3. **PR #447** (Sept 14, 11 days ago) refactored `order.ts` and removed the null guard:
   ```
   - if (!user || !user.id) { throw new Error('User required'); }
   - const userId = user ? user.id : null;
   + const userId = user.id;   ← crashes when user is null
   ```
   This change was reviewed without awareness of the guest-checkout null path.

4. **Result:** Every guest checkout crashes with `TypeError: Cannot read properties
   of null (reading 'id')` at `src/checkout/order.ts:87`.

**Fix:** Restore null guard in `processOrder`:
```typescript
const userId = user?.id ?? null;
if (!userId && !isGuestOrder(cart)) {
  throw new Error('User ID required for non-guest orders');
}
```

**Regression test generated:** `tests/checkout/order.guest.test.ts`
"""
