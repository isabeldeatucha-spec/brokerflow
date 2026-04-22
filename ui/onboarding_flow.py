"""Brand Onboarding Flow UI.

3-step stepper:
  Step 1 — Input form (brand name, website, file upload, manual overrides)
  Step 2 — Running (6-node progress rows streaming from the LangGraph)
  Step 3 — Review (completeness %, missing fields, conflicts, editable record,
            coordination messages emitted)
"""
from __future__ import annotations

import tempfile
from pathlib import Path

import streamlit as st

SANDBOX_BRAND_NAMES = {"Chomps", "Fishwife", "Graza", "Olipop", "Magic Spoon"}

_NODE_LABELS = {
    "load_prior_knowledge": ("Check what we already know",          ""),
    "extract_from_uploads": ("Read the files you uploaded",         ""),
    "merge_and_reconcile":  ("Reconcile conflicts",                 ""),
    "score_completeness":   ("Check what's missing",                ""),
    "persist_and_log":      ("Save to your book",                   ""),
    "notify_downstream":    ("Hand off to Retailer & Admin agents", ""),
}

_NODE_ORDER = list(_NODE_LABELS.keys())


def _section(title: str) -> None:
    st.markdown(
        f'<p class="sedge-section-title" style="margin-top:24px;">{title}</p>',
        unsafe_allow_html=True,
    )


def _render_step_1() -> None:
    _section("STEP 1 OF 3 — BRAND INFO")
    st.markdown(
        '<h2 style="font-family:\'Instrument Serif\', serif; font-size:28px; '
        'font-weight:400; margin:0 0 20px 0;">Add a brand to your book</h2>',
        unsafe_allow_html=True,
    )

    if st.session_state.get("sandbox_mode"):
        st.warning(
            "⚠️ Sandbox data is loaded. If you onboard a brand with the same "
            "name as a sandbox brand (Chomps, Fishwife, Graza, Olipop, Magic Spoon), "
            "the sandbox record will be replaced with your real data. "
            "To avoid this, clear sandbox first or pick a different brand name."
        )

    with st.form("onboarding_input_form"):
        brand_name = st.text_input(
            "Brand name *",
            placeholder="e.g. Fishwife",
            value=st.session_state.get("ob_brand_name", ""),
        )
        website_url = st.text_input(
            "Website URL",
            placeholder="https://eatfishwife.com",
            value=st.session_state.get("ob_website_url", ""),
        )
        uploaded_files = st.file_uploader(
            "Upload brand materials (PDF, DOCX, CSV, TXT)",
            accept_multiple_files=True,
            type=["pdf", "docx", "csv", "txt", "md"],
        )
        st.markdown("**Manual overrides** (optional — key: value, one per line)")
        overrides_raw = st.text_area(
            "Manual overrides",
            placeholder="category: beverages\nwholesale_price_range: $3.00–$4.00",
            height=100,
            label_visibility="collapsed",
            value=st.session_state.get("ob_overrides_raw", ""),
        )
        submitted = st.form_submit_button("Run onboarding →", type="primary", use_container_width=True)

    if submitted:
        if not brand_name.strip():
            st.error("Brand name is required.")
            return

        # Save uploaded files to temp dir
        file_paths: list[str] = []
        if uploaded_files:
            tmp_dir = tempfile.mkdtemp(prefix="sedge_ob_")
            for uf in uploaded_files:
                dest = Path(tmp_dir) / uf.name
                dest.write_bytes(uf.read())
                file_paths.append(str(dest))

        # Parse overrides
        overrides: dict = {}
        for line in overrides_raw.strip().splitlines():
            if ":" in line:
                k, _, v = line.partition(":")
                overrides[k.strip()] = v.strip()

        st.session_state["ob_brand_name"] = brand_name.strip()
        st.session_state["ob_website_url"] = website_url.strip()
        st.session_state["ob_overrides_raw"] = overrides_raw
        st.session_state["ob_file_paths"] = file_paths
        st.session_state["ob_overrides"] = overrides
        st.session_state["ob_step"] = 2
        st.rerun()


def _render_step_2() -> None:
    brand_name = st.session_state.get("ob_brand_name", "?")
    _section("STEP 2 OF 3 — RUNNING")
    st.markdown(
        f'<h2 style="font-family:\'Instrument Serif\', serif; font-size:28px; '
        f'font-weight:400; margin:0 0 20px 0;">Onboarding {brand_name}</h2>',
        unsafe_allow_html=True,
    )

    from agents.brand_onboarding.graph import get_graph
    from agents.orchestrator.contracts import OnboardingInput

    ob_input = OnboardingInput(
        brand_name=st.session_state["ob_brand_name"],
        website_url=st.session_state.get("ob_website_url") or None,
        uploaded_file_paths=st.session_state.get("ob_file_paths", []),
        manual_overrides=st.session_state.get("ob_overrides", {}),
    )

    node_slots = {node: st.empty() for node in _NODE_ORDER}
    for node in _NODE_ORDER:
        label, subtitle = _NODE_LABELS[node]
        node_slots[node].markdown(
            _progress_row(label, "pending", subtitle),
            unsafe_allow_html=True,
        )

    graph = get_graph()
    final_state = None
    completed_nodes: set[str] = set()

    try:
        for chunk in graph.stream({"input": ob_input}):
            for node_name in chunk:
                if node_name in _NODE_LABELS:
                    completed_nodes.add(node_name)
                    label, subtitle = _NODE_LABELS[node_name]
                    node_slots[node_name].markdown(
                        _progress_row(label, "check", subtitle),
                        unsafe_allow_html=True,
                    )
            final_state = chunk

        # Mark any remaining nodes as done
        for node in _NODE_ORDER:
            if node not in completed_nodes:
                label, subtitle = _NODE_LABELS[node]
                node_slots[node].markdown(
                    _progress_row(label, "check", subtitle),
                    unsafe_allow_html=True,
                )

        # Extract final handoff from last chunk
        last_values = list(final_state.values())[0] if final_state else {}
        handoff = last_values.get("handoff")
        st.session_state["ob_handoff"] = handoff
        st.session_state["ob_final_state"] = last_values
        st.session_state["ob_step"] = 3
        st.rerun()

    except Exception as exc:
        for node in _NODE_ORDER:
            if node not in completed_nodes:
                label, subtitle = _NODE_LABELS[node]
                node_slots[node].markdown(
                    _progress_row(label, "x", str(exc)[:80]),
                    unsafe_allow_html=True,
                )
        st.error(f"Onboarding failed: {exc}")
        if st.button("← Try again", key="ob_retry_btn"):
            st.session_state["ob_step"] = 1
            st.rerun()


def _progress_row(label: str, icon_type: str, status_text: str) -> str:
    icons = {
        "pending": '<span style="color:#C8C7BF; font-size:16px;">○</span>',
        "spinner": (
            '<div class="sedge-spin" style="width:16px; height:16px; '
            'border:2px solid #EAEAE4; border-top-color:#1A1A18; '
            'border-radius:50%; display:inline-block;"></div>'
        ),
        "check": '<span style="color:#2D5F3F; font-size:16px;">&#10003;</span>',
        "x":     '<span style="color:#8B2F2F; font-size:16px;">&#10007;</span>',
    }
    return (
        f'<div style="display:flex; align-items:center; gap:16px; padding:10px 0;'
        f'border-bottom:1px solid #F2F2EE;">'
        f'<div style="width:20px; flex-shrink:0;">{icons.get(icon_type, "○")}</div>'
        f'<div style="flex:1;">'
        f'<div style="font-size:14px; font-weight:500; color:#1A1A18;">{label}</div>'
        f'<div style="font-size:12px; color:#8B8A83; margin-top:2px;">{status_text}</div>'
        f'</div>'
        f'</div>'
    )


def _render_step_3() -> None:
    _section("STEP 3 OF 3 — REVIEW")
    handoff = st.session_state.get("ob_handoff")
    final_state = st.session_state.get("ob_final_state", {})

    brand_name = st.session_state.get("ob_brand_name", "?")
    pct = (handoff.completeness_pct if handoff else 0) or 0
    pct_color = "#2D5F3F" if pct >= 70 else ("#B8860B" if pct >= 40 else "#8B2F2F")

    st.markdown(
        f'<h2 style="font-family:\'Instrument Serif\', serif; font-size:28px; '
        f'font-weight:400; margin:0 0 4px 0;">{brand_name}</h2>'
        f'<p style="font-size:24px; font-weight:600; color:{pct_color}; margin:0 0 20px 0;">'
        f'{pct:.0f}% complete</p>',
        unsafe_allow_html=True,
    )

    if handoff and handoff.missing_fields:
        st.markdown(
            '<div style="background:#FEF9EE; border:1px solid #F0E6C0; border-radius:8px; '
            'padding:12px 16px; margin-bottom:16px;">'
            f'<p style="font-size:13px; color:#8B6914; margin:0;">'
            f'<strong>Missing fields ({len(handoff.missing_fields)}):</strong> '
            f'{", ".join(handoff.missing_fields)}'
            f'</p></div>',
            unsafe_allow_html=True,
        )

    if handoff and handoff.conflicts:
        with st.expander(f"{len(handoff.conflicts)} conflict{'s' if len(handoff.conflicts) != 1 else ''} auto-resolved"):
            for c in handoff.conflicts:
                st.markdown(
                    f"- **{c['field']}**: Scout said `{c.get('scout_value')}`, "
                    f"extraction said `{c.get('extracted_value')}` → "
                    f"*{c.get('resolution', 'resolved')}*"
                )

    record = (handoff.canonical_record if handoff else {}) or {}

    # Product catalog section
    _section("PRODUCT CATALOG")
    products = record.get("products") or []
    if not products:
        st.info("No products extracted. Add them manually below, or confirm and add later.")
    else:
        st.caption(f"{len(products)} SKU(s) extracted. ⭐ marks the flagship product.")
        for i, sku in enumerate(products):
            flagship_marker = "⭐ " if sku.get("is_flagship") else ""
            with st.expander(
                f"{flagship_marker}{sku.get('sku_name', 'Unnamed SKU')}",
                expanded=sku.get("is_flagship", False),
            ):
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.text_input("SKU name", sku.get("sku_name", ""), key=f"sku_{i}_name", disabled=True)
                    st.text_input("UPC", sku.get("upc") or "", key=f"sku_{i}_upc", disabled=True)
                    st.text_input("Net weight", sku.get("net_weight") or "", key=f"sku_{i}_weight", disabled=True)
                with col2:
                    st.number_input(
                        "Wholesale cost ($)",
                        value=float(sku.get("wholesale_cost") or 0),
                        key=f"sku_{i}_wholesale", disabled=True,
                    )
                    st.number_input(
                        "MSRP ($)",
                        value=float(sku.get("msrp") or 0),
                        key=f"sku_{i}_msrp", disabled=True,
                    )
                    st.number_input(
                        "Margin %",
                        value=float(sku.get("margin_pct") or 0),
                        key=f"sku_{i}_margin", disabled=True,
                    )
                with col3:
                    st.number_input(
                        "Case pack",
                        value=int(sku.get("case_pack") or 0),
                        key=f"sku_{i}_pack", disabled=True,
                    )
                    st.number_input(
                        "Cases/pallet",
                        value=int(sku.get("cases_per_pallet") or 0),
                        key=f"sku_{i}_pallet", disabled=True,
                    )
                    st.text_input(
                        "Storage",
                        sku.get("storage_temp") or "",
                        key=f"sku_{i}_storage", disabled=True,
                    )
                if sku.get("ingredients"):
                    st.caption(f"**Ingredients:** {sku['ingredients']}")
                if sku.get("allergens"):
                    st.caption(f"**Allergens:** {', '.join(sku['allergens'])}")

    if record:
        _section("CANONICAL RECORD")
        editable: dict = {}
        display_keys = [k for k in record if k not in ("source_files",)]
        col_a, col_b = st.columns(2)
        for i, key in enumerate(display_keys):
            val = record.get(key)
            col = col_a if i % 2 == 0 else col_b
            with col:
                str_val = (
                    ", ".join(val) if isinstance(val, list)
                    else str(val) if val is not None
                    else ""
                )
                editable[key] = st.text_input(
                    key.replace("_", " ").title(),
                    value=str_val,
                    key=f"ob_field_{key}",
                )

    # Coordination messages emitted
    messages_emitted = final_state.get("messages_emitted", [])
    if messages_emitted:
        _section("COORDINATION MESSAGES EMITTED")
        for msg in messages_emitted:
            st.markdown(
                f'<div style="display:flex; align-items:center; gap:8px; '
                f'padding:6px 0; font-size:13px; color:#2D5F3F;">'
                f'<span>&#10003;</span> <span>{msg}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )

    is_colliding = (
        (handoff.brand_name if handoff else brand_name) in SANDBOX_BRAND_NAMES
        and st.session_state.get("sandbox_mode")
    )
    if is_colliding:
        st.error(
            f"Cannot confirm: '{handoff.brand_name if handoff else brand_name}' conflicts with an "
            "active sandbox brand. Clear sandbox (toggle off in Operate tab) and re-run onboarding, "
            "or rename this brand."
        )

    st.markdown("<div style='margin-top:24px;'></div>", unsafe_allow_html=True)
    col_back, col_done = st.columns([1, 2])
    with col_back:
        if st.button("← Onboard another", key="ob_another_btn", use_container_width=True):
            for k in ["ob_step", "ob_brand_name", "ob_website_url", "ob_overrides_raw",
                      "ob_file_paths", "ob_overrides", "ob_handoff", "ob_final_state",
                      "onboarding_active"]:
                st.session_state.pop(k, None)
            st.rerun()
    with col_done:
        if st.button(
            "Confirm & go live",
            type="primary",
            key="ob_done_btn",
            use_container_width=True,
            disabled=is_colliding,
        ):
            for k in ["ob_step", "ob_brand_name", "ob_website_url", "ob_overrides_raw",
                      "ob_file_paths", "ob_overrides", "ob_handoff", "ob_final_state",
                      "onboarding_active"]:
                st.session_state.pop(k, None)
            st.rerun()


def render_onboarding_flow() -> None:
    st.markdown(
        "<hr style='border:none; border-top:1px solid #EAEAE4; margin:32px 0 24px;'>",
        unsafe_allow_html=True,
    )

    step = st.session_state.get("ob_step", 1)

    if step == 1:
        _render_step_1()
    elif step == 2:
        _render_step_2()
    elif step == 3:
        _render_step_3()
    else:
        _render_step_1()
