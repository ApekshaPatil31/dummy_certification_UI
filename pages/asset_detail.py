"""
pages/asset_detail.py — per-object certification dashboard (app.md §6)
----------------------------------------------------------------------
object filter → three cards (quarantine count, last certified version,
decided-by) → ledger history timeline.

a.k.a. certification_dashboard.py. Reads go through mock_data (POC backend).
"""

import json

import streamlit as st

import mock_data as data


def show_asset_detail():
    st.title("📊 Asset Detail")
    st.caption("Per-object certification status and full ledger history (Gold layer).")

    objects = data.get_all_objects()
    if not objects:
        st.info("No Gold objects have been evaluated yet.")
        return

    selected = st.selectbox(
        "Gold object",
        objects,
        format_func=lambda o: o.split(".")[-1],
        key="asset_selected_object",
    )
    st.caption(f"`{selected}`")

    latest = data.get_latest_for_object(selected)
    history = data.get_history_for_object(selected)

    # Latest rationale → quarantine count.
    quarantine_count = "—"
    try:
        r = json.loads(latest["rationale"])
        quarantine_count = r.get("row_level", {}).get("remediation", {}).get("quarantined_rows", "—")
    except (KeyError, ValueError, TypeError):
        pass

    # Last certified version = latest state='certified' row's version.
    certified_rows = [h for h in history if h["state"] == "certified"]
    if certified_rows:
        last_certified = certified_rows[0]["last_certified_version"]
        last_certified_str = f"v{last_certified}" if last_certified is not None else "—"
    else:
        last_certified_str = "Never certified by a human"

    st.divider()

    # ---- Three cards ------------------------------------------------------
    c1, c2, c3 = st.columns(3)
    c1.metric("Quarantined rows (last run)", quarantine_count)
    c2.metric("Last certified version", last_certified_str)
    c3.metric("Decided by (latest)", latest["decided_by"])

    # Current disposition badge.
    st.markdown(f"**Current status:** {data.state_label(latest['state'])} "
                f"· {data.relative_time(latest['decided_at'])}")

    st.divider()

    # ---- Ledger history timeline -----------------------------------------
    st.subheader("Ledger history")
    st.caption("Every decision for this object, newest first — the audit timeline.")

    rows_view = []
    for h in history:
        comment = ""
        try:
            comment = json.loads(h["rationale"]).get("human_comment") or ""
        except (ValueError, TypeError):
            pass
        rows_view.append({
            "state": data.state_label(h["state"]),
            "decided_by": h["decided_by"],
            "decided_at": h["decided_at"].strftime("%Y-%m-%d %H:%M UTC"),
            "source": h["decision_source"],
            "version": h["last_certified_version"] if h["last_certified_version"] is not None else "",
            "comment": comment,
        })
    st.dataframe(rows_view, use_container_width=True, hide_index=True)
