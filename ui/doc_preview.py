"""HTML templates for the in-app side-panel doc preview.

Each render function takes a payload dict from
agents/_shared/document_data.py and returns the body HTML the side panel
puts inside its scroll area. Same data the PDF generator uses, so the
in-app view always matches what the broker can forward as a PDF.

Public API:
  render_preview_body(doc_type, payload) -> (eyebrow, title, subtitle, body_html)
"""
from __future__ import annotations

from html import escape
from typing import Any


# ── Shared atoms ─────────────────────────────────────────────────────────────

def _section_h(title: str) -> str:
    return f'<div class="bf-doc-section-h">{title}</div>'


def _stat_block(stats: list[tuple[str, str]]) -> str:
    cells = "".join(
        '<div class="bf-doc-stat">'
        f'<div class="bf-doc-stat-num">{escape(num)}</div>'
        f'<div class="bf-doc-stat-lbl">{escape(lbl)}</div>'
        '</div>'
        for num, lbl in stats
    )
    return f'<div class="bf-doc-statgrid">{cells}</div>'


def _table(headers: list[str], rows: list[list[str]],
           col_widths: list[str] | None = None,
           row_classes: list[str] | None = None) -> str:
    head = "".join(f'<th>{escape(h)}</th>' for h in headers)
    body_rows = []
    for i, row in enumerate(rows):
        cls = (row_classes[i] if row_classes and i < len(row_classes) else "")
        cells = "".join(
            f'<td>{cell if cell.startswith("<") else escape(str(cell))}</td>'
            for cell in row
        )
        body_rows.append(f'<tr class="{cls}">{cells}</tr>')
    cw_html = ""
    if col_widths:
        cols = "".join(f'<col style="width:{w}">' for w in col_widths)
        cw_html = f"<colgroup>{cols}</colgroup>"
    return (
        f'<table class="bf-doc-table">{cw_html}'
        f'<thead><tr>{head}</tr></thead>'
        f'<tbody>{"".join(body_rows)}</tbody>'
        '</table>'
    )


# ── Sell sheet ──────────────────────────────────────────────────────────────

def _render_sell_sheet(p: dict[str, Any]) -> tuple[str, str, str, str]:
    brand    = p.get("brand_name", "Brand")
    tagline  = p.get("tagline", "")
    retailer = p.get("retailer", "Retailer")
    contact  = p.get("contact", "")

    sections: list[str] = []

    # PROPOSED FOR
    stats = p.get("stats", [])
    sections.append(_section_h(f"PROPOSED FOR {retailer.upper()}"))
    if stats:
        sections.append(_stat_block(stats))

    # BRAND STORY
    story = (p.get("story", "") or "").strip()
    if story:
        sections.append(_section_h("BRAND STORY"))
        for para in story.split("\n\n"):
            para = para.strip()
            if para:
                sections.append(f'<p class="bf-doc-prose">{escape(para)}</p>')

    # CHANNEL PERFORMANCE
    perf = p.get("channel_performance", [])
    if perf:
        sections.append(_section_h("CHANNEL PERFORMANCE"))
        sections.append(_table(
            ["Channel", "Velocity", "Density", "Note"],
            perf,
            col_widths=["18%", "16%", "26%", "40%"],
        ))

    # PROMO INDEPENDENCE
    if p.get("promo_note"):
        sections.append(_section_h("PROMO INDEPENDENCE"))
        sections.append(f'<p class="bf-doc-prose">{escape(p["promo_note"])}</p>')

    # SKU LINEUP
    skus = p.get("skus", [])
    if skus:
        sections.append(_section_h("SKU LINEUP"))
        rows = [[
            s.get("name", ""), s.get("case_pack", ""), s.get("dims", ""),
            s.get("upc", ""), s.get("fob", ""), s.get("srp", ""),
        ] for s in skus]
        sections.append(_table(
            ["SKU", "Case pack", "Dimensions", "UPC", "FOB", "SRP"],
            rows,
            col_widths=["28%", "12%", "16%", "20%", "12%", "12%"],
        ))

    # MARGIN STACK
    stack = p.get("margin_stack", [])
    if stack:
        sections.append(_section_h("MARGIN STACK"))
        last = len(stack) - 1
        rows = [[label, value] for label, value in stack]
        row_classes = ["" for _ in stack]
        if rows:
            row_classes[last] = "bf-doc-table-total"
        sections.append(_table(
            ["", ""], rows, col_widths=["68%", "32%"],
            row_classes=row_classes,
        ))

    # CO-OP TERMS
    if p.get("coop_terms"):
        sections.append(_section_h("CO-OP / MDF TERMS PROPOSED"))
        sections.append(f'<p class="bf-doc-prose">{escape(p["coop_terms"])}</p>')

    # CONTACT
    if p.get("broker_name"):
        sections.append(_section_h("CONTACT"))
        sections.append(
            f'<p class="bf-doc-prose"><strong>{escape(p["broker_name"])}</strong><br>'
            f'<span class="bf-doc-muted">{escape(p.get("broker_email",""))} '
            f'&middot; {escape(p.get("broker_phone",""))}</span></p>'
        )

    eyebrow = "DOCUMENT · SELL SHEET"
    title    = f"{brand} × {retailer}"
    subtitle = (
        " · ".join(filter(None, [
            p.get("tagline", ""),
            f"contact: {contact}" if contact else "",
        ])) or tagline
    )
    return eyebrow, title, subtitle, "".join(sections)


# ── One-pager ───────────────────────────────────────────────────────────────

def _render_one_pager(p: dict[str, Any]) -> tuple[str, str, str, str]:
    brand    = p.get("brand_name", "Brand")
    category = p.get("category", "")
    score    = int(p.get("score", 0))
    tier     = p.get("tier", "")

    # SCORE block (single big stat)
    tier_color = (
        "#2D5F3F" if score >= 70 else
        "#B07A1C" if score >= 45 else "#8B8A83"
    )
    score_html = (
        '<div class="bf-doc-score-block">'
        f'<div class="bf-doc-score-num">{score}'
        f'<span class="bf-doc-score-of">/100</span></div>'
        f'<div class="bf-doc-score-tier" style="color:{tier_color};">'
        f'{escape(tier)}</div>'
        '</div>'
    )

    sections: list[str] = [score_html]

    # 5-criterion breakdown — bar viz
    bd = p.get("breakdown", [])
    if bd:
        sections.append(_section_h("SCORING BREAKDOWN"))
        bars = []
        for name, got, of in bd:
            pct = max(0, min(100, int((got / of) * 100))) if of else 0
            bars.append(
                '<div class="bf-doc-bar-row">'
                f'<div class="bf-doc-bar-name">{escape(name)}</div>'
                f'<div class="bf-doc-bar-score">{got}/{of}</div>'
                '<div class="bf-doc-bar-track">'
                f'<div class="bf-doc-bar-fill" style="width:{pct}%;"></div>'
                '</div>'
                '</div>'
            )
        sections.append('<div class="bf-doc-bars">' + "".join(bars) + '</div>')

    # WHAT WE FOUND
    findings = p.get("findings", [])
    if findings:
        sections.append(_section_h("WHAT WE FOUND"))
        items = []
        for f in findings:
            text = f.get("text", "") if isinstance(f, dict) else str(f)
            source = f.get("source", "") if isinstance(f, dict) else ""
            src_html = (f'<span class="bf-doc-source">&#8599; {source}</span>'
                        if source else "")
            items.append(
                '<div class="bf-doc-finding">'
                f'<span class="bf-doc-finding-text">{escape(text)}</span>'
                f'{src_html}'
                '</div>'
            )
        sections.append('<div class="bf-doc-findings">' + "".join(items) + '</div>')

    # WHY THIS FITS YOUR BOOK
    if p.get("interest"):
        sections.append(_section_h("WHY THIS FITS YOUR BOOK"))
        sections.append(f'<p class="bf-doc-prose">{escape(p["interest"])}</p>')

    # RECOMMENDED NEXT STEP
    if p.get("next_step"):
        sections.append(_section_h("RECOMMENDED NEXT STEP"))
        sections.append(
            f'<div class="bf-doc-callout">{escape(p["next_step"])}</div>'
        )

    eyebrow = "DOCUMENT · BRAND ONE-PAGER"
    title    = brand
    subtitle = " · ".join(filter(None, [category, tier])) if (category or tier) else ""
    return eyebrow, title, subtitle, "".join(sections)


# ── New item form ───────────────────────────────────────────────────────────

def _render_new_item_form(p: dict[str, Any]) -> tuple[str, str, str, str]:
    retailer = p.get("retailer", "Retailer")
    brand    = p.get("brand_name", "Brand")
    skus     = p.get("skus", [])
    fields   = p.get("fields", [])
    outstanding = p.get("outstanding", [])
    certs    = p.get("certs", [])

    filled  = sum(1 for f in fields if (f.get("status") or "").upper() == "OK")
    total   = len(fields)

    sections: list[str] = []

    if skus:
        sections.append(_section_h("SKU LIST"))
        sections.append(
            '<ul class="bf-doc-bullet-list">' +
            "".join(f"<li>{escape(s)}</li>" for s in skus) +
            '</ul>'
        )

    if fields:
        sections.append(_section_h("FORM FIELDS"))
        rows = []
        row_classes = []
        for f in fields:
            status = (f.get("status") or "OK").upper()
            tag = (
                '<span class="bf-doc-status-tag bf-doc-status-tag--needs">'
                'NEEDS CONFIRMATION</span>'
                if status != "OK" else
                '<span class="bf-doc-status-tag">OK</span>'
            )
            rows.append([
                f.get("label", ""),
                f.get("value", "") or "&mdash;",
                tag,
            ])
            row_classes.append("bf-doc-row--needs" if status != "OK" else "")
        sections.append(_table(
            ["Field", "Value", "Status"], rows,
            col_widths=["38%", "44%", "18%"],
            row_classes=row_classes,
        ))

    if outstanding:
        sections.append(_section_h("OUTSTANDING — NEEDS BRAND CONFIRMATION"))
        sections.append(
            '<ul class="bf-doc-bullet-list">' +
            "".join(f"<li>{escape(item)}</li>" for item in outstanding) +
            '</ul>'
        )

    if certs:
        sections.append(_section_h("REQUIRED CERTIFICATIONS"))
        rows = []
        row_classes = []
        for c in certs:
            status = c.get("status", "current")
            expiring = "expir" in (status or "").lower()
            rows.append([
                c.get("name", ""), c.get("id", ""),
                c.get("expires", ""), status,
            ])
            row_classes.append("bf-doc-row--alert" if expiring else "")
        sections.append(_table(
            ["Cert", "ID", "Expires", "Status"], rows,
            col_widths=["28%", "22%", "22%", "28%"],
            row_classes=row_classes,
        ))

    eyebrow = "DOCUMENT · NEW ITEM FORM"
    title    = f"{brand} × {retailer}"
    subtitle = (f"{filled} of {total} fields filled"
                if total else "Form draft")
    return eyebrow, title, subtitle, "".join(sections)


# ── Cost build (auxiliary doc — render as a simple table) ───────────────────

def _render_cost_build(p: dict[str, Any]) -> tuple[str, str, str, str]:
    brand    = p.get("brand_name", "Brand")
    retailer = p.get("retailer", "Retailer")
    rows     = p.get("cost_rows", [
        ("Suggested retail (SRP)",      "$1.99"),
        ("Retailer margin",             "32% / $0.64"),
        ("Wholesale to retailer",       "$1.35"),
        ("Slotting fee (1× SKU)",       "$1,200"),
        ("Promo allowance (3 events)",  "$900"),
        ("Net wholesale to brand",      "$1.05"),
        ("COGS (per unit)",             "$0.62"),
        ("Brand contribution / unit",   "$0.43"),
    ])
    sections: list[str] = [
        _section_h("COST BUILD"),
        _table(["Line item", "Value"], list(rows),
               col_widths=["66%", "34%"]),
        '<p class="bf-doc-prose bf-doc-muted" style="margin-top:14px;">'
        '<em>All figures pre-tax, FOB origin. Margin assumes case-pack '
        'of 12 and 90-day pay terms.</em></p>',
    ]
    eyebrow = "DOCUMENT · COST BUILD"
    title = f"{brand} × {retailer}"
    subtitle = "Margin & terms"
    return eyebrow, title, subtitle, "".join(sections)


# ── Dispatch ────────────────────────────────────────────────────────────────

_RENDERERS = {
    "sell_sheet":     _render_sell_sheet,
    "one_pager":      _render_one_pager,
    "new_item_form":  _render_new_item_form,
    "cost_build":     _render_cost_build,
}


def render_preview_body(doc_type: str,
                        payload: dict[str, Any]) -> tuple[str, str, str, str]:
    """Return (eyebrow, title, subtitle, body_html) for the doc panel."""
    fn = _RENDERERS.get(doc_type)
    if not fn:
        return ("DOCUMENT", doc_type.replace("_", " ").title(), "",
                f'<p class="bf-doc-prose">No preview template for '
                f'<code>{doc_type}</code>.</p>')
    return fn(payload)


# ── Side-panel CSS (loaded once per render) ─────────────────────────────────

PREVIEW_CSS = """
<style>
.bf-doc-preview-body {
    padding: 24px 30px 80px;
    overflow-y: auto;
    flex: 1 1 auto;
    background: #FAFAF7;
    color: #1A1A18;
    font-family: 'Inter', sans-serif;
}
.bf-doc-preview-body::-webkit-scrollbar { width: 4px; }
.bf-doc-preview-body::-webkit-scrollbar-thumb { background: #EAEAE4; border-radius: 99px; }

.bf-doc-section-h {
    font-family: 'Inter', sans-serif;
    font-size: 10.5px;
    font-weight: 600;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: #8B8A83;
    margin: 28px 0 12px;
}
.bf-doc-section-h:first-child { margin-top: 0; }

.bf-doc-prose {
    font-family: 'Instrument Serif', Georgia, serif !important;
    font-size: 16px !important;
    line-height: 1.7 !important;
    color: #1A1A18 !important;
    margin: 0 0 14px !important;
}
.bf-doc-muted { color: #8B8A83 !important; }

/* Stat blocks (sell sheet) */
.bf-doc-statgrid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 14px;
    margin: 8px 0 6px;
}
.bf-doc-stat {
    border: 1px solid #EAEAE4;
    background: #FFFFFF;
    border-radius: 10px;
    padding: 18px 14px;
    text-align: center;
}
.bf-doc-stat-num {
    font-family: 'Instrument Serif', Georgia, serif !important;
    font-size: 28px;
    line-height: 1.1;
    color: #1A1A18;
    font-weight: 400;
}
.bf-doc-stat-lbl {
    font-family: 'Inter', sans-serif !important;
    font-size: 10px;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: #8B8A83;
    margin-top: 6px;
}

/* Tables */
.bf-doc-table {
    width: 100%;
    border-collapse: collapse;
    font-family: 'Inter', sans-serif;
    font-size: 13px;
    color: #1A1A18;
}
.bf-doc-table thead th {
    text-align: left;
    font-size: 10.5px;
    font-weight: 600;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: #8B8A83;
    padding: 8px 10px;
    border-bottom: 1px solid #EAEAE4;
}
.bf-doc-table tbody td {
    padding: 10px 10px;
    border-bottom: 1px solid #F2F2EE;
    vertical-align: top;
}
.bf-doc-table tbody tr:last-child td { border-bottom: none; }
.bf-doc-table-total td {
    font-weight: 600;
    border-top: 1px solid #1A1A18 !important;
    border-bottom: none !important;
}
.bf-doc-row--needs td { background: #FBE9C2; }
.bf-doc-row--alert td { color: #B23A22; font-weight: 500; }

.bf-doc-status-tag {
    font-family: 'Inter', sans-serif;
    font-size: 9.5px;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: #8B8A83;
    background: #F2F2EE;
    padding: 3px 7px;
    border-radius: 4px;
    white-space: nowrap;
}
.bf-doc-status-tag--needs {
    background: #FBE9C2;
    color: #7A4F00;
}

/* Bullet lists */
.bf-doc-bullet-list {
    margin: 0 0 6px 0;
    padding-left: 20px;
    font-family: 'Inter', sans-serif;
    font-size: 13.5px;
    color: #1A1A18;
}
.bf-doc-bullet-list li {
    margin-bottom: 6px;
    line-height: 1.55;
}

/* One-pager: score block */
.bf-doc-score-block {
    display: flex;
    align-items: baseline;
    gap: 18px;
    padding: 22px 0 16px;
    border-bottom: 1px solid #EAEAE4;
    margin-bottom: 8px;
}
.bf-doc-score-num {
    font-family: 'Instrument Serif', Georgia, serif !important;
    font-size: 56px;
    line-height: 1;
    color: #1A1A18;
    font-weight: 400;
}
.bf-doc-score-of {
    font-size: 22px;
    color: #8B8A83;
    margin-left: 4px;
}
.bf-doc-score-tier {
    font-family: 'Inter', sans-serif !important;
    font-size: 13px;
    font-weight: 600;
    letter-spacing: 0.04em;
}

/* One-pager: bar viz */
.bf-doc-bars { margin: 6px 0; }
.bf-doc-bar-row {
    display: grid;
    grid-template-columns: 200px 60px 1fr;
    gap: 14px;
    align-items: center;
    padding: 7px 0;
    border-bottom: 1px solid #F2F2EE;
}
.bf-doc-bar-row:last-child { border-bottom: none; }
.bf-doc-bar-name {
    font-family: 'Inter', sans-serif;
    font-size: 13px;
    color: #1A1A18;
}
.bf-doc-bar-score {
    font-family: 'JetBrains Mono', monospace;
    font-size: 12px;
    color: #57564F;
}
.bf-doc-bar-track {
    height: 6px;
    background: #F2F2EE;
    border-radius: 99px;
    overflow: hidden;
}
.bf-doc-bar-fill {
    height: 100%;
    background: #E8A33D;
    border-radius: 99px;
}

/* One-pager: findings */
.bf-doc-findings { margin: 0 0 6px; }
.bf-doc-finding {
    display: flex;
    justify-content: space-between;
    gap: 14px;
    padding: 8px 0;
    border-bottom: 1px solid #F2F2EE;
    font-family: 'Inter', sans-serif;
    font-size: 13px;
    color: #1A1A18;
    line-height: 1.5;
}
.bf-doc-finding:last-child { border-bottom: none; }
.bf-doc-source {
    font-family: 'JetBrains Mono', monospace;
    font-size: 10.5px;
    color: #8B8A83;
    letter-spacing: 0.06em;
    white-space: nowrap;
    margin-top: 2px;
}

/* One-pager: callout */
.bf-doc-callout {
    background: #FFF7E8;
    border-left: 3px solid #E8A33D;
    padding: 12px 16px;
    border-radius: 0 6px 6px 0;
    font-family: 'Instrument Serif', Georgia, serif !important;
    font-size: 16px;
    line-height: 1.6;
    color: #1A1A18;
}
</style>
"""
