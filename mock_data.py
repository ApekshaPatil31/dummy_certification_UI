"""
app/mock_data.py
----------------
In-memory stand-in for the eventual `queries.py` + `connection.py` SQL layer,
so the wireframe runs as a local POC with NO Databricks / Spark / warehouse.

The function signatures here mirror what `queries.py` will expose, so wiring the
real backend later is a drop-in swap: replace the bodies with `run_query(sql)`
calls and delete this module. Every "row" is a plain dict matching the
`certification_ledger` schema (see sync/ddl_governance_schemas.py); `rationale`
is the JSON the engine writes (see sync/certification_ledger_sync._build_rationale).

State note: human decisions are appended into `st.session_state` so Certify /
Reject visibly update the rest of the app within a session (no persistence).
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import streamlit as st

# --------------------------------------------------------------------------- #
# Seed ledger rows — what the engine has already written for the Gold layer.
# Mirrors the states the real engine emits: proposed_certified / proposed_rejected
# (engine recommendations) + certified / rejected (prior human decisions) + error.
# --------------------------------------------------------------------------- #

_NOW = datetime(2026, 6, 17, 9, 30, tzinfo=timezone.utc)


def _rationale(*, object_name, layer, to_version, total, passed, errored,
               final_state, baseline_verdict, checks, quarantined_rows=0,
               acted_rows=0, strategy=None, escalated_rules=None,
               auto_approved_rules=None):
    """Build a rationale JSON blob matching LedgerWriter._build_rationale shape."""
    failed = total - passed
    return json.dumps({
        "schema_version": 1,
        "run_id": f"run-{object_name.split('.')[-1]}",
        "layer": layer,
        "object": object_name,
        "decided_at": _NOW.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "scope": {"mode": "FULL", "from_version": None, "to_version": to_version},
        "summary": {"total": total, "passed": passed, "failed": failed, "errored": errored},
        "baseline_verdict": baseline_verdict,
        "final_state": final_state,
        "auto_approved": False,
        "checks": checks,
        "row_level": {
            "failed_rules": sum(1 for c in checks if c.get("rule_type") == "row_level" and c["verdict"] != "PASS"),
            "remediation": {
                "strategy": strategy,
                "quarantined_rows": quarantined_rows,
                "acted_rows": acted_rows,
                "quarantine_run_id": f"run-{object_name.split('.')[-1]}",
            },
        },
        "asset_level": {
            "failed_rules": sum(1 for c in checks if c.get("rule_type") == "asset_level" and c["verdict"] != "PASS"),
            "auto_approved_rules": auto_approved_rules or [],
            "escalated_rules": escalated_rules or [],
            "deferred_to": None,
        },
        "unresolved": [],
    }, indent=2)


_SEED_ROWS: list[dict] = [
    # 1. Engine recommends CERTIFY — all asset-level checks pass, a few row-level
    #    failures already quarantined + purged.
    {
        "ledger_id": "led-0001",
        "run_id": "run-gold_customer_inventory_health",
        "object": "almr_dev_marts.customer_inventory.gold_customer_inventory_health",
        "layer": "Gold",
        "state": "proposed_certified",
        "decided_by": "engine",
        "decided_at": _NOW - timedelta(hours=2),
        "decision_source": "initial",
        "last_certified_version": None,
        "created_at": _NOW - timedelta(hours=2),
        "rationale": _rationale(
            object_name="almr_dev_marts.customer_inventory.gold_customer_inventory_health",
            layer="Gold", to_version=7, total=6, passed=5, errored=0,
            final_state="proposed_certified", baseline_verdict="rejected",
            strategy="delete", quarantined_rows=42, acted_rows=42,
            checks=[
                {"rule_id": "R-SCHEMA-001", "rule_name": "schema_conformance", "rule_type": "asset_level", "criticality": "high", "verdict": "PASS"},
                {"rule_id": "R-FRESH-001", "rule_name": "timeliness", "rule_type": "asset_level", "criticality": "medium", "verdict": "PASS"},
                {"rule_id": "R-COMPL-002", "rule_name": "completeness_customer_id", "rule_type": "row_level", "criticality": "high", "verdict": "PASS"},
                {"rule_id": "R-UNIQ-001", "rule_name": "uniqueness_pk", "rule_type": "row_level", "criticality": "high", "verdict": "PASS"},
                {"rule_id": "R-VALID-003", "rule_name": "value_range_stock_qty", "rule_type": "row_level", "criticality": "medium", "verdict": "FAIL",
                 "mandatory": True, "failed_rows": 42, "disposition": "quarantined+purged",
                 "quarantine_table": "almr_dev_marts.quarantine_gold.customer_inventory_health"},
                {"rule_id": "R-VALID-004", "rule_name": "value_range_reorder_pt", "rule_type": "row_level", "criticality": "low", "verdict": "PASS"},
            ],
        ),
    },
    # 2. Engine recommends REJECT — schema_conformance (asset-level) failed and is
    #    NOT remediable, so it escalated the decision to a human.
    {
        "ledger_id": "led-0002",
        "run_id": "run-gold_sales_summary",
        "object": "almr_dev_marts.sales.gold_sales_summary",
        "layer": "Gold",
        "state": "proposed_rejected",
        "decided_by": "engine",
        "decided_at": _NOW - timedelta(hours=5),
        "decision_source": "initial",
        "last_certified_version": None,
        "created_at": _NOW - timedelta(hours=5),
        "rationale": _rationale(
            object_name="almr_dev_marts.sales.gold_sales_summary",
            layer="Gold", to_version=14, total=5, passed=3, errored=0,
            final_state="proposed_rejected", baseline_verdict="rejected",
            strategy="delete", quarantined_rows=11, acted_rows=11,
            escalated_rules=["R-SCHEMA-001"],
            checks=[
                {"rule_id": "R-SCHEMA-001", "rule_name": "schema_conformance", "rule_type": "asset_level", "criticality": "high", "verdict": "FAIL",
                 "mandatory": True, "disposition": "escalated_to_review",
                 "details": {"missing_columns": ["net_revenue_usd"], "unexpected_columns": ["net_rev"]}},
                {"rule_id": "R-FRESH-001", "rule_name": "timeliness", "rule_type": "asset_level", "criticality": "medium", "verdict": "PASS"},
                {"rule_id": "R-COMPL-001", "rule_name": "completeness_order_id", "rule_type": "row_level", "criticality": "high", "verdict": "PASS"},
                {"rule_id": "R-UNIQ-001", "rule_name": "uniqueness_pk", "rule_type": "row_level", "criticality": "high", "verdict": "PASS"},
                {"rule_id": "R-VALID-009", "rule_name": "value_range_amount", "rule_type": "row_level", "criticality": "medium", "verdict": "FAIL",
                 "mandatory": True, "failed_rows": 11, "disposition": "quarantined+purged",
                 "quarantine_table": "almr_dev_marts.quarantine_gold.sales_summary"},
            ],
        ),
    },
    # 3. Another engine CERTIFY recommendation, clean run.
    {
        "ledger_id": "led-0003",
        "run_id": "run-gold_order_fulfillment",
        "object": "almr_dev_marts.orders.gold_order_fulfillment",
        "layer": "Gold",
        "state": "proposed_certified",
        "decided_by": "engine",
        "decided_at": _NOW - timedelta(hours=1),
        "decision_source": "initial",
        "last_certified_version": None,
        "created_at": _NOW - timedelta(hours=1),
        "rationale": _rationale(
            object_name="almr_dev_marts.orders.gold_order_fulfillment",
            layer="Gold", to_version=22, total=4, passed=4, errored=0,
            final_state="proposed_certified", baseline_verdict="certified",
            checks=[
                {"rule_id": "R-SCHEMA-001", "rule_name": "schema_conformance", "rule_type": "asset_level", "criticality": "high", "verdict": "PASS"},
                {"rule_id": "R-FRESH-001", "rule_name": "timeliness", "rule_type": "asset_level", "criticality": "medium", "verdict": "PASS"},
                {"rule_id": "R-COMPL-001", "rule_name": "completeness_order_id", "rule_type": "row_level", "criticality": "high", "verdict": "PASS"},
                {"rule_id": "R-UNIQ-001", "rule_name": "uniqueness_pk", "rule_type": "row_level", "criticality": "high", "verdict": "PASS"},
            ],
        ),
    },
    # 4. Already certified by a human (prior decision in history).
    {
        "ledger_id": "led-0004",
        "run_id": "run-gold_revenue_recognition",
        "object": "almr_dev_marts.finance.gold_revenue_recognition",
        "layer": "Gold",
        "state": "certified",
        "decided_by": "priya.menon@alamar.io",
        "decided_at": _NOW - timedelta(days=1, hours=3),
        "decision_source": "human_review",
        "last_certified_version": 31,
        "created_at": _NOW - timedelta(days=1, hours=3),
        "rationale": json.dumps({
            "schema_version": 1,
            "reviewed_ledger_id": "led-0004-proposed",
            "engine_state": "proposed_certified",
            "reviewer": "priya.menon@alamar.io",
            "human_comment": "Verified against finance close; safe to certify.",
            "certified_version": 31,
        }, indent=2),
    },
    # 5. Engine errored — a check or remediation step failed; needs a re-run.
    {
        "ledger_id": "led-0005",
        "run_id": "run-gold_stock_movements",
        "object": "almr_dev_marts.inventory.gold_stock_movements",
        "layer": "Gold",
        "state": "error",
        "decided_by": "engine",
        "decided_at": _NOW - timedelta(hours=8),
        "decision_source": "initial",
        "last_certified_version": None,
        "created_at": _NOW - timedelta(hours=8),
        "rationale": _rationale(
            object_name="almr_dev_marts.inventory.gold_stock_movements",
            layer="Gold", to_version=None, total=4, passed=2, errored=1,
            final_state="error", baseline_verdict="rejected",
            checks=[
                {"rule_id": "R-SCHEMA-001", "rule_name": "schema_conformance", "rule_type": "asset_level", "criticality": "high", "verdict": "PASS"},
                {"rule_id": "R-FRESH-001", "rule_name": "timeliness", "rule_type": "asset_level", "criticality": "medium", "verdict": "PASS"},
                {"rule_id": "R-UNIQ-001", "rule_name": "uniqueness_pk", "rule_type": "row_level", "criticality": "high", "verdict": "ERROR",
                 "mandatory": True, "disposition": "error", "details": {"error": "AnalysisException: column 'movement_id' not found"}},
                {"rule_id": "R-COMPL-001", "rule_name": "completeness_sku", "rule_type": "row_level", "criticality": "high", "verdict": "FAIL",
                 "mandatory": True, "failed_rows": 3, "disposition": "reported_only"},
            ],
        ),
    },
    # 6. Previously rejected by a human.
    {
        "ledger_id": "led-0006",
        "run_id": "run-gold_customer_360",
        "object": "almr_dev_marts.customer.gold_customer_360",
        "layer": "Gold",
        "state": "rejected",
        "decided_by": "arjun.rao@alamar.io",
        "decided_at": _NOW - timedelta(days=2),
        "decision_source": "human_review",
        "last_certified_version": None,
        "created_at": _NOW - timedelta(days=2),
        "rationale": json.dumps({
            "schema_version": 1,
            "reviewed_ledger_id": "led-0006-proposed",
            "engine_state": "proposed_rejected",
            "reviewer": "arjun.rao@alamar.io",
            "human_comment": "Schema drift confirmed with source team; rejecting until upstream fix lands.",
            "certified_version": None,
        }, indent=2),
    },
]


# --------------------------------------------------------------------------- #
# Session-backed store. Seeds once per session; human decisions append here.
# --------------------------------------------------------------------------- #

def _ledger() -> list[dict]:
    if "ledger_rows" not in st.session_state:
        # copy so re-runs don't mutate the module-level seed
        st.session_state.ledger_rows = [dict(r) for r in _SEED_ROWS]
    return st.session_state.ledger_rows


def _latest_per_object() -> dict[str, dict]:
    """Latest ledger row per object (the §1.1 'latest-per-object' view)."""
    latest: dict[str, dict] = {}
    for row in _ledger():
        cur = latest.get(row["object"])
        if cur is None or row["decided_at"] > cur["decided_at"]:
            latest[row["object"]] = row
    return latest


_PROPOSED = ("proposed_certified", "proposed_rejected")


# --------------------------------------------------------------------------- #
# Read API — mirrors the eventual queries.py surface.
# --------------------------------------------------------------------------- #

def get_pending_objects(layer: str | None = None,
                        since: "datetime | None" = None) -> list[dict]:
    """
    Gold objects whose latest decision is still an engine recommendation.

    Optional filters mirror the page controls:
      layer  — keep only this layer (None / 'All' = no filter).
      since  — keep only rows recommended at/after this timestamp (None = all time).
    """
    rows = [r for r in _latest_per_object().values() if r["state"] in _PROPOSED]
    if layer and layer != "All":
        rows = [r for r in rows if r["layer"] == layer]
    if since is not None:
        rows = [r for r in rows if r["decided_at"] >= since]
    return sorted(rows, key=lambda r: r["decided_at"], reverse=True)


def get_layers() -> list[str]:
    """Distinct layers present in the ledger (for the layer filter)."""
    return sorted({r["layer"] for r in _ledger()})


def get_all_objects() -> list[str]:
    """Every Gold object the engine has evaluated (for the asset-detail filter)."""
    return sorted(_latest_per_object().keys())


def get_latest_for_object(object_name: str) -> dict | None:
    return _latest_per_object().get(object_name)


def get_history_for_object(object_name: str) -> list[dict]:
    """Full ledger history for an object, newest first (the audit timeline)."""
    rows = [r for r in _ledger() if r["object"] == object_name]
    return sorted(rows, key=lambda r: r["decided_at"], reverse=True)


def get_home_counts() -> dict:
    latest = list(_latest_per_object().values())
    return {
        "certified_by_humans": sum(1 for r in latest if r["state"] == "certified"),
        "pending_hitl": sum(1 for r in latest if r["state"] in _PROPOSED),
        "high_risk": sum(1 for r in latest if r["state"] == "proposed_rejected"),
        "errored": sum(1 for r in latest if r["state"] == "error"),
        "total_gold_objects": len(latest),
    }


def get_recently_reviewed(limit: int = 5) -> list[dict]:
    rows = [r for r in _ledger() if r["decision_source"] == "human_review"]
    rows.sort(key=lambda r: r["decided_at"], reverse=True)
    return rows[:limit]


def summarize_rationale(rationale_json: str) -> str:
    """
    Canned natural-language summary standing in for the `ai_query(...)` call.
    Derives plain English from the structured rationale so the wireframe shows
    the real shape of the panel without a live LLM endpoint.
    """
    data = json.loads(rationale_json)
    summ = data.get("summary", {})
    asset = data.get("asset_level", {})
    rl = data.get("row_level", {})
    rem = rl.get("remediation", {})
    state = data.get("final_state", "")

    parts = []
    if state == "proposed_certified":
        parts.append(
            f"The engine recommends **certifying** this object. All asset-level "
            f"checks passed ({summ.get('passed', 0)}/{summ.get('total', 0)} checks total)."
        )
    elif state == "proposed_rejected":
        esc = ", ".join(asset.get("escalated_rules", [])) or "an asset-level rule"
        parts.append(
            f"The engine recommends **rejecting** this object because {esc} failed. "
            f"Asset-level failures cannot be auto-remediated and were escalated for review."
        )
    elif state == "error":
        parts.append(
            "The run **errored** before a verdict could be reached — a check or "
            "remediation step failed. The object should be re-run before review."
        )

    q = rem.get("quarantined_rows", 0)
    if q:
        parts.append(
            f"{q} row-level violation(s) were quarantined and "
            f"{rem.get('strategy', 'removed')}d from the mart, so the reviewed "
            f"version contains only conforming rows."
        )
    return " ".join(parts)


# --------------------------------------------------------------------------- #
# Write API — the one mutation. Appends a human-review row (§4).
# --------------------------------------------------------------------------- #

def record_human_decision(*, proposed_row: dict, decision: str, decided_by: str,
                          comment: str | None = None) -> dict:
    """
    Append a human-review row to the in-memory ledger, mirroring the planned
    LedgerWriter.record_human_decision. Returns the new row.
    """
    import uuid

    scope_to_version = None
    try:
        scope_to_version = json.loads(proposed_row["rationale"]).get("scope", {}).get("to_version")
    except (KeyError, ValueError, TypeError):
        pass

    certified_version = scope_to_version if decision == "certified" else None
    new_row = {
        "ledger_id": f"led-{uuid.uuid4().hex[:8]}",
        "run_id": proposed_row["run_id"],
        "object": proposed_row["object"],
        "layer": proposed_row["layer"],
        "state": decision,
        "decided_by": decided_by,
        "decided_at": datetime.now(timezone.utc),
        "decision_source": "human_review",
        "last_certified_version": certified_version,
        "created_at": datetime.now(timezone.utc),
        "rationale": json.dumps({
            "schema_version": 1,
            "reviewed_ledger_id": proposed_row["ledger_id"],
            "engine_state": proposed_row["state"],
            "reviewer": decided_by,
            "human_comment": comment,
            "certified_version": certified_version,
        }, indent=2),
    }
    _ledger().append(new_row)
    return new_row


# --------------------------------------------------------------------------- #
# Live Delta versions — stand-in for `DESCRIBE HISTORY <object>` (app.md §3.2.1).
# Used ONLY to drive the stale-version banner; never to decide the certified
# version. Some objects are deliberately ahead of their reviewed version so the
# wireframe shows the warning. Anything not listed is assumed up to date.
# --------------------------------------------------------------------------- #

_LIVE_VERSIONS: dict[str, int] = {
    # reviewed v7 → table has since advanced to v9 (STALE — banner fires)
    "almr_dev_marts.customer_inventory.gold_customer_inventory_health": 9,
    # reviewed v14 → still v14 (fresh, no banner)
    "almr_dev_marts.sales.gold_sales_summary": 14,
    # reviewed v22 → still v22 (fresh, no banner)
    "almr_dev_marts.orders.gold_order_fulfillment": 22,
}


def get_live_version(object_name: str, reviewed_version: int | None = None) -> int | None:
    """Current Delta version of the object (POC stand-in for DESCRIBE HISTORY)."""
    return _LIVE_VERSIONS.get(object_name, reviewed_version)


def disposition_text(check: dict) -> str:
    """
    Human-readable disposition for one check (app.md §3 / ledger §8), e.g.
      row_level failure   → "11 rows quarantined"
      asset_level failure → "Escalated for review"
    Passing/errored checks get a short status instead of a raw count.
    """
    verdict = (check.get("verdict") or "").upper()
    rule_type = check.get("rule_type", "")
    if verdict == "PASS":
        return "—"
    if verdict == "ERROR":
        return "Errored — needs re-run"
    if rule_type == "asset_level":
        return "Escalated for review"
    if rule_type == "row_level":
        n = check.get("failed_rows")
        return f"{n} rows quarantined" if n else "Quarantined"
    return "Reported only"


# --------------------------------------------------------------------------- #
# Display helpers shared by pages.
# --------------------------------------------------------------------------- #

STATE_BADGE = {
    "proposed_certified": ("🟡", "Engine recommends CERTIFY"),
    "proposed_rejected": ("🔴", "Engine recommends REJECT"),
    "certified": ("🟢", "Certified by human"),
    "rejected": ("⛔", "Rejected by human"),
    "error": ("⚠️", "Run errored"),
}


def state_label(state: str) -> str:
    icon, text = STATE_BADGE.get(state, ("•", state))
    return f"{icon} {text}"


def relative_time(ts: datetime) -> str:
    delta = datetime.now(timezone.utc) - ts
    secs = delta.total_seconds()
    if secs < 3600:
        return f"{int(secs // 60)}m ago"
    if secs < 86400:
        return f"{int(secs // 3600)}h ago"
    return f"{int(secs // 86400)}d ago"
