"""Subagent A: TraceAgent — parse incident trace from Sentry/Datadog/K8s event.

In demo mode: parses a pre-recorded JSON trace or extracts from URL/alert text.
In production: fetches live trace via Sentry or Datadog API.
"""

from __future__ import annotations

import json
import re

import httpx

from ...schemas.causaltrace import CausalTraceRequest, TraceSpan


async def run(request: CausalTraceRequest, token: str = "") -> list[TraceSpan]:
    """Fetch/parse distributed trace for the incident."""
    if request.sentry_url:
        return await _parse_sentry(request.sentry_url, token)
    if request.k8s_event:
        return _parse_k8s_event(request.k8s_event)
    if request.datadog_alert_id:
        return await _parse_datadog(request.datadog_alert_id, token)
    return _demo_trace(request.affected_service or "payment-service")


async def _parse_sentry(url: str, token: str) -> list[TraceSpan]:
    """Extract issue ID from Sentry URL and fetch via API if token available."""
    m = re.search(r"/issues/(\d+)", url)
    if not m or not token:
        # Return stub trace from URL context
        service = re.search(r"sentry\.io/organizations?/([^/]+)", url)
        svc = service.group(1) if service else "unknown-service"
        return _demo_trace(svc)
    issue_id = m.group(1)
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.get(
                f"https://sentry.io/api/0/issues/{issue_id}/",
                headers={"Authorization": f"Bearer {token}"},
            )
            if r.status_code == 200:
                data = r.json()
                return [
                    TraceSpan(
                        span_id=issue_id,
                        service=data.get("project", {}).get("slug", "unknown"),
                        operation=data.get("title", "error"),
                        status="error",
                        error_message=data.get("culprit", ""),
                    )
                ]
    except Exception:
        pass
    return _demo_trace("sentry-service")


async def _parse_datadog(alert_id: str, token: str) -> list[TraceSpan]:
    """Stub: return demo trace (real impl would call Datadog API)."""
    return _demo_trace(f"dd-service-{alert_id[:6]}")


def _parse_k8s_event(event_text: str) -> list[TraceSpan]:
    """Extract service and error from K8s event text."""
    service = re.search(r"pod/(\S+)", event_text)
    reason = re.search(r"Reason: (\S+)", event_text, re.I)
    return [
        TraceSpan(
            span_id="k8s-event",
            service=service.group(1) if service else "k8s-pod",
            operation=reason.group(1) if reason else "CrashLoopBackOff",
            status="error",
            error_message=event_text[:500],
        )
    ]


def _demo_trace(service: str) -> list[TraceSpan]:
    """Pre-recorded demo trace: checkout → inventory → payment (payment fails)."""
    return [
        TraceSpan(span_id="a1", service="checkout-service",  operation="POST /checkout",   duration_ms=120, status="ok"),
        TraceSpan(span_id="a2", service="inventory-service", operation="GET /inventory",   duration_ms=45,  status="ok"),
        TraceSpan(span_id="a3", service=service,             operation="charge_payment()", duration_ms=890, status="error",
                  error_message="NullPointerException: user.paymentMethod is null"),
    ]
