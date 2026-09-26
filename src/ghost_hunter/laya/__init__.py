"""Laya AI — System 1 decision layer.

Three primitives:
  - Choice: classify/route to one of N options
  - Score: numeric 1–10 severity/confidence
  - Noul: calibrated yes/no probability (safety gate)

Self-hosted (pip install laya) or fallback to heuristics offline.
Structurally cannot hallucinate — never generates free text.
"""
