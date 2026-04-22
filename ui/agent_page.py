"""Agent page: tabbed workflow UI for each operational agent.

render_agent_page(agent_key) is the single entry point.
Internal module names are never used in display strings — see ui/labels.py.
"""
from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ui.labels import (
    LABEL_RETAILER_AGENT, LABEL_ADMIN_AGENT, LABEL_BRAND_SCOUT_AGENT,
    LABEL_BRAND_SCOUT_SCOPE,
    RETAILER_AGENT_WORKFLOWS, ADMIN_AGENT_WORKFLOWS,
    STATUS_PILL_LABELS,
)


def render_agent_page(agent_key: str) -> None:
    """Render an agent's page. Called from render_existing_business_workspace()."""
    if st.button("← Agents", key="back_to_agents"):
        st.session_state["open_agent"] = None
        st.rerun()

    if agent_key == "retailer_agent":
        _render_tabbed_agent(
            name=LABEL_RETAILER_AGENT,
            tagline="Pitching, promoting, and tracking submission windows across your book.",
            workflows=RETAILER_AGENT_WORKFLOWS,
            active_renderers={"pitching": _render_retailer_pitching},
            internal_agent_name="retailer_pitcher",
        )
    elif agent_key == "admin_agent":
        _render_tabbed_agent(
            name=LABEL_ADMIN_AGENT,
            tagline="The paperwork side of your job — forms, POs, deductions, and demo spend — handled.",
            workflows=ADMIN_AGENT_WORKFLOWS,
            active_renderers={"new_item_forms": _render_admin_new_item_forms},
            internal_agent_name="admin_ops",
        )
    elif agent_key == "brand_scout_agent":
        _render_brand_scout_summary()
    else:
        st.error(f"Unknown agent key: {agent_key!r}")


def _render_tabbed_agent(
    name: str,
    tagline: str,
    workflows: list[dict],
    active_renderers: dict,
    internal_agent_name: str,
) -> None:
    st.markdown(
        f"<h1 style='font-family:\"Instrument Serif\", Georgia, serif; "
        f"font-size:44px; font-weight:400; margin-bottom:0.25rem;'>{name}</h1>",
        unsafe_allow_html=True,
    )
    st.markdown(
        f"<p style='font-family:\"Instrument Serif\", Georgia, serif; "
        f"font-style:italic; font-size:18px; color:#6b6b6b; margin-bottom:1.5rem;'>"
        f"{tagline}</p>",
        unsafe_allow_html=True,
    )

    # Loop status strip
    loop = _loop_status_for(internal_agent_name)
    active_count = sum(1 for w in workflows if w["status"] == "active")
    cols_status = st.columns([2, 2, 2, 1])
    with cols_status[0]:
        st.caption(f"↻ Last run: {loop['last_run']}")
    with cols_status[1]:
        st.caption(f"Next: {loop['next_run']}")
    with cols_status[2]:
        st.caption(f"Active workflows: {active_count}")
    with cols_status[3]:
        if st.button("Run now", key=f"run_{internal_agent_name}"):
            st.toast(f"{name} triggered. Running…")

    st.divider()

    # Workflow tabs — append status label for non-active workflows
    tab_labels = [
        w["label"] if w["status"] == "active"
        else f"{w['label']} · {STATUS_PILL_LABELS.get(w['status'], 'Coming soon')}"
        for w in workflows
    ]
    tabs = st.tabs(tab_labels)
    for tab, workflow in zip(tabs, workflows):
        with tab:
            if workflow["status"] == "active" and workflow["key"] in active_renderers:
                active_renderers[workflow["key"]]()
            else:
                _render_coming_soon(workflow)


def _render_coming_soon(workflow: dict) -> None:
    status_label = STATUS_PILL_LABELS.get(workflow["status"], "Coming soon")
    st.markdown(
        f'<div style="background:#FAFAF7; border:1px solid #EAEAEA; '
        f'border-radius:12px; padding:2rem; margin-top:1rem;">'
        f'<div style="text-transform:uppercase; letter-spacing:0.08em; '
        f'font-size:11px; color:#888;">Roadmap · {status_label}</div>'
        f'<div style="font-family:\'Instrument Serif\', Georgia, serif; '
        f'font-size:28px; margin-top:0.5rem; color:#1a1a1a;">{workflow["label"]}</div>'
        f'<div style="margin-top:0.75rem; color:#444; line-height:1.6;">'
        f'{workflow.get("description", "")}</div>'
        f'<div style="margin-top:1rem; color:#666; line-height:1.6; font-size:14px;">'
        f'{workflow.get("details", "")}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def _loop_status_for(internal_agent_name: str) -> dict:
    from datetime import datetime, timezone
    try:
        from memory import _get_client
        client = _get_client()
        result = (
            client.table("coordination_messages")
            .select("created_at")
            .eq("from_agent", internal_agent_name)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        if result.data:
            last = datetime.fromisoformat(
                result.data[0]["created_at"].replace("Z", "+00:00")
            )
            delta = datetime.now(timezone.utc) - last
            if delta.total_seconds() < 3600:
                last_str = f"{int(delta.total_seconds() / 60)} min ago"
            elif delta.total_seconds() < 86400:
                last_str = f"{int(delta.total_seconds() / 3600)} hr ago"
            else:
                last_str = f"{delta.days} day(s) ago"
        else:
            last_str = "Never"
    except Exception:
        last_str = "Unknown"
    return {"last_run": last_str, "next_run": "On next session start"}


def _render_retailer_pitching() -> None:
    from ui.retailer_pitcher_page import render_retailer_pitcher_page
    render_retailer_pitcher_page()


def _render_admin_new_item_forms() -> None:
    from ui.admin_ops_page import render_admin_ops_page
    render_admin_ops_page()


def _render_brand_scout_summary() -> None:
    st.markdown(
        f"<h1 style='font-family:\"Instrument Serif\", Georgia, serif; "
        f"font-size:44px; font-weight:400; margin-bottom:0.25rem;'>{LABEL_BRAND_SCOUT_AGENT}</h1>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<p style='font-family:\"Instrument Serif\", Georgia, serif; "
        "font-style:italic; font-size:18px; color:#6b6b6b; margin-bottom:1.5rem;'>"
        "Evaluation only — qualifying and scoring lives in the Brand Scout workspace.</p>",
        unsafe_allow_html=True,
    )
    st.info(LABEL_BRAND_SCOUT_SCOPE)
    if st.button("Open Brand Scout workspace →", type="primary", key="goto_brand_scout"):
        st.session_state["workspace"] = "brand_scout"
        st.session_state["open_agent"] = None
        st.rerun()
