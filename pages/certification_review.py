"""
pages/certification_review.py — the core HITL flow (app.md §3)
--------------------------------------------------------------
dropdown → preview proposed verdict + NL rationale → certify / reject.

Reads/writes go through mock_data (the in-memory POC backend). The function
signature and layout match the planned production page, so swapping mock_data
for queries.py later leaves this code largely intact.
"""

import json
from datetime import datetime, timedelta, timezone

import streamlit as st

import mock_data as data

# Recent-range options for the time filter (replaces the calendar picker).
# label -> lookback window; None = no time bound ("All").
_TIME_RANGES = {
    "All": None,
    "Last 7 Days": timedelta(days=7),
    "Past Month": timedelta(days=30),
    "Last 90 Days": timedelta(days=90),
}


def _verdict_pill(state: str):
    icon, text = data.STATE_BADGE.get(state, ("•", state))
    color = {"proposed_certified": "#b88600",
             "proposed_rejected": "#c0392b"}.get(state, "#444")
    st.markdown(
        f"<span style='background:{color};color:white;padding:4px 12px;"
        f"border-radius:14px;font-weight:600;font-size:14px'>{icon} {text}</span>",
        unsafe_allow_html=True,
    )


def show_certification_review(current_user: str):
    st.title("🏥 Certification Review")
    st.caption(
        "Human-in-the-loop review of the **Gold** layer. The engine proposes a "
        "verdict; you certify or reject it."
    )
    counts = data.get_home_counts()
    s1, s2, s3 = st.columns(3)
    s1.metric("✅ Certified", counts["certified_by_humans"])
    s2.metric("🟡 Pending", counts["pending_hitl"])
    s3.metric("📦 Total objects", counts["total_gold_objects"])
    # ---- 3.1 Controls row — the "global search bar" -----------------------
    # Three filters side by side. Layer + time are read first because the object
    # dropdown's options depend on them.
    c1, c2, c3 = st.columns([3, 1.2, 1.4])

    with c2:
        layer = st.selectbox(
            "Layer",
            ["All"] + data.get_layers(),
            key="review_layer_filter",
        )
    with c3:
        time_label = st.selectbox(
            "Recommended within",
            list(_TIME_RANGES),
            key="review_time_filter",
        )

    window = _TIME_RANGES[time_label]
    since = datetime.now(timezone.utc) - window if window else None
    pending = data.get_pending_objects(layer=layer, since=since)

    with c1:
        if not pending:
            st.success("🎉 No Gold objects match these filters.")
            return
        options = [r["object"] for r in pending]
        selected = st.selectbox(
            "Gold table pending review",
            options,
            format_func=lambda o: o.split(".")[-1],
            key="review_selected_object",
        )

    row = next(r for r in pending if r["object"] == selected)
    rationale = json.loads(row["rationale"])
    scope = rationale.get("scope", {})
    reviewed_version = scope.get("to_version")

    st.divider()

    # ---- 3.2 Preview panel ------------------------------------------------
    left, right = st.columns([2, 1])

    with left:
        st.subheader(selected.split(".")[-1])
        st.caption(f"`{selected}`")
        _verdict_pill(row["state"])

        # 3.2.1 Stale-version banner (display-only comparison). live_version is a
        # read-only DESCRIBE HISTORY stand-in — it never changes what gets certified.
        live_version = data.get_live_version(selected, reviewed_version)
        if reviewed_version is None:
            st.info("ℹ️ Version not tracked for this object — "
                    "certifying will leave `last_certified_version` empty.")
        elif live_version is not None and live_version > reviewed_version:
            st.warning(
                f"⚠️ This review covers **v{reviewed_version}**. The table has since "
                f"advanced to **v{live_version}** — those changes are **not** part of "
                f"this certification and will need their own run."
            )

        # NL rationale (stand-in for ai_query).
        st.markdown("**Why the engine proposed this verdict**")
        st.info(data.summarize_rationale(row["rationale"]))

        # Structured rationale facts. Failed-row counts are excluded as a raw
        # column and folded into the descriptive Disposition instead (e.g.
        # "11 rows quarantined" / "Escalated for review").
        with st.expander("📋 Check-by-check evidence", expanded=True):
            checks_view = [
                {
                    "rule": c["rule_name"],
                    "type": c["rule_type"],
                    "criticality": c.get("criticality", ""),
                    "verdict": c["verdict"],
                    "disposition": data.disposition_text(c),
                }
                for c in rationale.get("checks", [])
            ]
            st.dataframe(checks_view, use_container_width=True, hide_index=True)

        with st.expander("🔬 Raw rationale JSON"):
            st.json(rationale)

    with right:
        st.markdown("**Run details**")
        st.metric("Reviewed version", f"v{reviewed_version}" if reviewed_version is not None else "—")
        summ = rationale.get("summary", {})
        st.metric("Checks passed", f"{summ.get('passed', 0)} / {summ.get('total', 0)}")
        rem = rationale.get("row_level", {}).get("remediation", {})
        st.metric("Rows quarantined", rem.get("quarantined_rows", 0))
        st.metric("Engine Certification time", data.relative_time(row["decided_at"]))
        st.caption(f"run_id: `{row['run_id']}`")

    st.divider()

    # ---- 3.4 / 3.5 Decision capture --------------------------------------
    st.subheader("Your decision")
    comment = st.text_area(
        "Comment (optional — recommended when rejecting)",
        key="review_comment",
        placeholder="e.g. Verified against finance close; safe to certify.",
    )

    # Centered decision buttons.
    _pad_l, b1, b2, _pad_r = st.columns([3, 1.4, 1.4, 3])
    with b1:
        certify = st.button("✅ Certify", type="primary", use_container_width=True)
    with b2:
        reject = st.button("❌ Reject", use_container_width=True)

    if certify or reject:
        decision = "certified" if certify else "rejected"
        data.record_human_decision(
            proposed_row=row,
            decision=decision,
            decided_by=current_user,
            comment=comment or None,
        )
        verb = "certified ✅" if certify else "rejected ❌"
        st.success(f"**{selected.split('.')[-1]}** marked **{verb}** by {current_user}.")
        st.caption("Select another table above to continue reviewing.")
        # Clear selection-bound widgets so a re-run lands on the next pending item.
        for k in ("review_selected_object", "review_comment"):
            st.session_state.pop(k, None)
        st.rerun()
