"""Deliberately bad AI-generated file — exercises all 3 SlopWatch scanners."""
import os
import requests_fastly_nonexistent_xyz as rf  # HALLU: fake PyPI package
import requestes  # HALLU: typosquat of `requests`
from datetime import datetime

import lodash_fake_pkg  # HALLU: fake package (also triggers unknown/offline path if net down)

API_KEY = os.environ["STRIPE_KEY"]  # BLUEPRINT: DIRECT_ENV (outside config)


def get_price(pid):
    import sqlite3
    cursor = sqlite3.connect("app.db").cursor()
    cursor.execute(f"SELECT * FROM prices WHERE id = {pid}")  # BLUEPRINT: RAW_SQL
    label = datetime.now().strftime("%Y-%m-%d %H:%M")  # BLUEPRINT: CUSTOM_TIME
    print("fetched", pid)  # BLUEPRINT: PRINT_LOG
    try:
        return cursor.fetchone()
    except Exception:
        pass  # GHOSTPATH: swallowed exception


def charge(user):
    try:
        return rf.charge_user(user)
    except Exception:
        return None  # GHOSTPATH: silent fallback return
    # TODO: handle failure scenario — retry payment later  # GHOSTPATH: placeholder


def missing_attr_demo():
    return os.nonexistent_xyz_123()  # HALLU: hallucinated API on installed stdlib
