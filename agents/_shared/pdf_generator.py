"""ReportLab PDF templates for BrokerFlow's three live agents.

Public entry points:
  make_sell_sheet(card_data) -> bytes   # Retailer Pitcher
  make_one_pager(card_data) -> bytes    # Brand Scout
  make_new_item_form(card_data) -> bytes  # New Item Forms
  make_cost_build(card_data) -> bytes   # Retailer Pitcher (auxiliary)

Each takes a `card_data` dict (loose schema; only fields the template
uses are required) and returns the rendered PDF as bytes.

Visual identity:
  - Clean white background (printable for brokers)
  - Editorial serif headers (we use ReportLab's bundled Times-Roman as
    a stand-in for Instrument Serif since custom font registration would
    require shipping ttf files)
  - Generous 1-inch margins
  - "BrokerFlow" wordmark + page numbers in the footer
"""
from __future__ import annotations

import io
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)


# ── Shared style palette ────────────────────────────────────────────────────

CREAM     = colors.HexColor("#FAFAF7")
INK       = colors.HexColor("#1A1A18")
MUTED     = colors.HexColor("#8B8A83")
HAIRLINE  = colors.HexColor("#EAEAE4")
ACCENT    = colors.HexColor("#E8A33D")  # mustard
ACCENT_BG = colors.HexColor("#FBE9C2")  # mustard bg fill (NEEDS CONFIRMATION)
GREEN     = colors.HexColor("#2D5F3F")
RED_HIGH  = colors.HexColor("#B23A22")


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()["Normal"]
    return {
        "h1": ParagraphStyle(
            "h1", parent=base, fontName="Times-Roman", fontSize=30,
            leading=34, textColor=INK, spaceAfter=4, leftIndent=0,
        ),
        "h2": ParagraphStyle(
            "h2", parent=base, fontName="Times-Roman", fontSize=18,
            leading=22, textColor=INK, spaceAfter=8, spaceBefore=14,
        ),
        "subtitle_italic": ParagraphStyle(
            "subtitle_italic", parent=base, fontName="Times-Italic",
            fontSize=14, leading=18, textColor=MUTED, spaceAfter=18,
        ),
        "section": ParagraphStyle(
            "section", parent=base, fontName="Helvetica-Bold", fontSize=9,
            leading=11, textColor=MUTED, spaceAfter=6, spaceBefore=14,
        ),
        "body": ParagraphStyle(
            "body", parent=base, fontName="Helvetica", fontSize=10.5,
            leading=15, textColor=INK, spaceAfter=10,
        ),
        "body_serif": ParagraphStyle(
            "body_serif", parent=base, fontName="Times-Roman", fontSize=11,
            leading=16, textColor=INK, spaceAfter=10,
        ),
        "muted": ParagraphStyle(
            "muted", parent=base, fontName="Helvetica", fontSize=9,
            leading=12, textColor=MUTED, spaceAfter=4,
        ),
        "tag": ParagraphStyle(
            "tag", parent=base, fontName="Helvetica-Bold", fontSize=8,
            leading=10, textColor=INK, spaceAfter=2,
        ),
        "stat_num": ParagraphStyle(
            "stat_num", parent=base, fontName="Times-Roman", fontSize=24,
            leading=28, textColor=INK, alignment=1, spaceAfter=2,
        ),
        "stat_lbl": ParagraphStyle(
            "stat_lbl", parent=base, fontName="Helvetica", fontSize=8.5,
            leading=11, textColor=MUTED, alignment=1, spaceAfter=0,
        ),
    }


def _footer(canvas, doc) -> None:
    """BrokerFlow wordmark left, page number right, on every page."""
    canvas.saveState()
    canvas.setFont("Times-Roman", 9)
    canvas.setFillColor(MUTED)
    canvas.drawString(inch, 0.5 * inch, "BrokerFlow")
    canvas.drawRightString(LETTER[0] - inch, 0.5 * inch, f"Page {doc.page}")
    canvas.setStrokeColor(HAIRLINE)
    canvas.setLineWidth(0.5)
    canvas.line(inch, 0.7 * inch, LETTER[0] - inch, 0.7 * inch)
    canvas.restoreState()


def _new_doc(buf: io.BytesIO) -> BaseDocTemplate:
    doc = BaseDocTemplate(
        buf, pagesize=LETTER,
        leftMargin=inch, rightMargin=inch,
        topMargin=inch, bottomMargin=inch,
        title="BrokerFlow document",
    )
    frame = Frame(
        doc.leftMargin, doc.bottomMargin,
        doc.width, doc.height,
        id="main", showBoundary=0,
    )
    doc.addPageTemplates([
        PageTemplate(id="all", frames=frame, onPage=_footer)
    ])
    return doc


# ── Stat block helper (used by sell sheet + one-pager) ─────────────────────

def _stat_block(s: dict[str, ParagraphStyle], stats: list[tuple[str, str]]):
    """Three centered stat columns with a hairline border."""
    cells = [[
        [Paragraph(num, s["stat_num"]), Paragraph(lbl, s["stat_lbl"])]
        for num, lbl in stats
    ]]
    t = Table(cells, colWidths=[(LETTER[0] - 2 * inch) / len(stats)] * len(stats))
    t.setStyle(TableStyle([
        ("BOX",         (0, 0), (-1, -1), 0.5, HAIRLINE),
        ("LINEBEFORE",  (1, 0), (-1, -1), 0.5, HAIRLINE),
        ("VALIGN",      (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",  (0, 0), (-1, -1), 14),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
    ]))
    return t


# ── Sell sheet (Retailer Pitcher) ──────────────────────────────────────────

def make_sell_sheet(card_data: dict[str, Any]) -> bytes:
    s = _styles()
    buf = io.BytesIO()
    doc = _new_doc(buf)

    brand    = card_data.get("brand_name", "Brand")
    tagline  = card_data.get("tagline", "Independent CPG brand")
    category = card_data.get("category", "")
    retailer = card_data.get("retailer", "Retailer")
    contact  = card_data.get("contact", "Buyer")
    stats    = card_data.get("stats", [
        ("3.1×", "FAIRE VELOCITY"),
        ("$1.99", "INTRO PRICE"),
        ("32%", "RETAILER MARGIN"),
    ])
    story    = card_data.get("story", "")
    skus     = card_data.get("skus", [])
    margin_stack = card_data.get("margin_stack", [])
    coop_terms   = card_data.get("coop_terms", "")
    broker_name  = card_data.get("broker_name", "Nadia Vega")
    broker_email = card_data.get("broker_email", "nadia@vegabrokerage.com")
    broker_phone = card_data.get("broker_phone", "(415) 555-0114")

    flow: list = []
    flow.append(Paragraph(brand, s["h1"]))
    flow.append(Paragraph(f"<i>{tagline}{' · ' + category if category else ''}</i>",
                          s["subtitle_italic"]))

    flow.append(Paragraph(f"PROPOSED FOR {retailer.upper()}", s["section"]))
    flow.append(Spacer(1, 4))
    flow.append(_stat_block(s, stats))

    flow.append(Paragraph("BRAND STORY", s["section"]))
    for para in story.split("\n\n"):
        if para.strip():
            flow.append(Paragraph(para.strip(), s["body_serif"]))

    flow.append(Paragraph("CHANNEL PERFORMANCE", s["section"]))
    perf_rows = [["CHANNEL", "VELOCITY", "DENSITY", "NOTE"]]
    for row in card_data.get("channel_performance", [
        ["Faire",     "3.1×",  "Top 5% beverage", "PNW indexing strongest"],
        ["Instacart", "2.4×",  "12 banners",      "Promo-clean velocity"],
        ["Amazon",    "—",     "—",               "DTC-led, intentional"],
        ["DTC",       "+22%",  "12k subs",        "MoM growth Q1"],
    ]):
        perf_rows.append(row)
    perf = Table(perf_rows, colWidths=[1.4 * inch, 1.0 * inch, 1.6 * inch, 2.5 * inch])
    perf.setStyle(TableStyle([
        ("FONTNAME",  (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",  (0, 0), (-1, -1), 9),
        ("TEXTCOLOR", (0, 0), (-1, 0), MUTED),
        ("TEXTCOLOR", (0, 1), (-1, -1), INK),
        ("LINEBELOW", (0, 0), (-1, 0), 0.5, HAIRLINE),
        ("LINEBELOW", (0, 1), (-1, -2), 0.25, HAIRLINE),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING",    (0, 0), (-1, -1), 6),
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
    ]))
    flow.append(perf)

    if card_data.get("promo_note"):
        flow.append(Paragraph("PROMO INDEPENDENCE", s["section"]))
        flow.append(Paragraph(card_data["promo_note"], s["body"]))

    # ── Page 2 ──────────────────────────────────────────────────────────────
    from reportlab.platypus import PageBreak
    flow.append(PageBreak())
    flow.append(Paragraph(f"{brand} — SKU lineup", s["h2"]))

    if skus:
        sku_rows = [[
            "SKU", "CASE PACK", "DIMENSIONS", "UPC", "FOB", "SRP",
        ]]
        for sku in skus:
            sku_rows.append([
                sku.get("name", ""), sku.get("case_pack", ""),
                sku.get("dims", ""), sku.get("upc", ""),
                sku.get("fob", ""), sku.get("srp", ""),
            ])
        sku_t = Table(sku_rows, colWidths=[1.6 * inch, 0.9 * inch, 1.1 * inch,
                                            1.2 * inch, 0.7 * inch, 0.7 * inch])
        sku_t.setStyle(TableStyle([
            ("FONTNAME",  (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE",  (0, 0), (-1, -1), 8.5),
            ("TEXTCOLOR", (0, 0), (-1, 0), MUTED),
            ("TEXTCOLOR", (0, 1), (-1, -1), INK),
            ("LINEBELOW", (0, 0), (-1, 0), 0.5, HAIRLINE),
            ("LINEBELOW", (0, 1), (-1, -2), 0.25, HAIRLINE),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING",    (0, 0), (-1, -1), 6),
        ]))
        flow.append(sku_t)

    if margin_stack:
        flow.append(Paragraph("MARGIN STACK", s["section"]))
        ms_rows = [["LINE", "VALUE"]]
        for row in margin_stack:
            ms_rows.append(row)
        ms = Table(ms_rows, colWidths=[3 * inch, 1.5 * inch])
        ms.setStyle(TableStyle([
            ("FONTNAME",  (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE",  (0, 0), (-1, -1), 9),
            ("TEXTCOLOR", (0, 0), (-1, 0), MUTED),
            ("LINEBELOW", (0, 0), (-1, -2), 0.25, HAIRLINE),
            ("LINEABOVE", (0, -1), (-1, -1), 0.5, INK),
            ("FONTNAME",  (0, -1), (-1, -1), "Helvetica-Bold"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING",    (0, 0), (-1, -1), 6),
        ]))
        flow.append(ms)

    if coop_terms:
        flow.append(Paragraph("CO-OP / MDF TERMS PROPOSED", s["section"]))
        flow.append(Paragraph(coop_terms, s["body"]))

    flow.append(Spacer(1, 24))
    flow.append(Paragraph("CONTACT", s["section"]))
    flow.append(Paragraph(broker_name, s["body_serif"]))
    flow.append(Paragraph(
        f'{broker_email} &nbsp;·&nbsp; {broker_phone}', s["muted"],
    ))

    doc.build(flow)
    return buf.getvalue()


# ── Brand one-pager (Brand Scout) ──────────────────────────────────────────

def make_one_pager(card_data: dict[str, Any]) -> bytes:
    s = _styles()
    buf = io.BytesIO()
    doc = _new_doc(buf)

    brand    = card_data.get("brand_name", "Brand")
    category = card_data.get("category", "")
    score    = card_data.get("score", 0)
    tier     = card_data.get("tier", "Worth a Look")
    breakdown = card_data.get("breakdown", [
        ("Velocity proof",         22, 25),
        ("Distribution density",   16, 20),
        ("Margin viability",       14, 20),
        ("Brand story clarity",    18, 20),
        ("Promo independence",     17, 15),
    ])
    findings = card_data.get("findings", [])
    interest = card_data.get("interest", "")
    next_step = card_data.get("next_step", "")

    flow: list = []
    flow.append(Paragraph(brand, s["h1"]))
    flow.append(Paragraph(f"<i>{category}</i>", s["subtitle_italic"]))

    # Score block
    score_table = Table([[
        Paragraph(f"<b>{score}</b><font size=14 color='#8B8A83'>/100</font>",
                  ParagraphStyle("score", fontName="Times-Roman",
                                 fontSize=42, leading=46, textColor=INK)),
        Paragraph(f"<b>{tier}</b>", ParagraphStyle(
            "tier", fontName="Helvetica-Bold", fontSize=11, leading=14,
            textColor=GREEN if score >= 70 else
            (ACCENT if score >= 45 else MUTED),
        )),
    ]], colWidths=[2.0 * inch, 4.5 * inch])
    score_table.setStyle(TableStyle([
        ("VALIGN",       (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",   (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 10),
        ("LINEABOVE",    (0, 0), (-1, 0), 0.5, HAIRLINE),
        ("LINEBELOW",    (0, 0), (-1, -1), 0.5, HAIRLINE),
    ]))
    flow.append(score_table)

    # 5-criterion breakdown as a horizontal score grid
    flow.append(Paragraph("SCORING BREAKDOWN", s["section"]))
    bd_rows = [["CRITERION", "SCORE", "BAR"]]
    for name, got, of in breakdown:
        pct = max(0, min(100, int((got / of) * 100))) if of else 0
        # Render bar as a horizontal table cell with a colored cell
        bar = Table(
            [["", ""]],
            colWidths=[2.5 * inch * (pct / 100), 2.5 * inch * (1 - pct / 100)],
            rowHeights=[0.18 * inch],
        )
        bar.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (0, 0), ACCENT),
            ("BACKGROUND", (1, 0), (1, 0), HAIRLINE),
        ]))
        bd_rows.append([name, f"{got}/{of}", bar])
    bd = Table(bd_rows, colWidths=[2.6 * inch, 0.8 * inch, 2.6 * inch])
    bd.setStyle(TableStyle([
        ("FONTNAME",  (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",  (0, 0), (-1, -1), 9),
        ("TEXTCOLOR", (0, 0), (-1, 0), MUTED),
        ("LINEBELOW", (0, 0), (-1, -2), 0.25, HAIRLINE),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING",    (0, 0), (-1, -1), 8),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
    ]))
    flow.append(bd)

    # Findings
    flow.append(Paragraph("WHAT WE FOUND", s["section"]))
    for finding in findings:
        text = finding.get("text", "") if isinstance(finding, dict) else str(finding)
        source = finding.get("source", "") if isinstance(finding, dict) else ""
        src_html = (f'  <font color="#8B8A83" size=8>↗ {source}</font>'
                    if source else "")
        flow.append(Paragraph(f"• {text}{src_html}", s["body"]))

    if interest:
        flow.append(Paragraph("WHY THIS IS INTERESTING FOR YOUR BOOK", s["section"]))
        flow.append(Paragraph(interest, s["body_serif"]))

    if next_step:
        flow.append(Paragraph("RECOMMENDED NEXT STEP", s["section"]))
        flow.append(Paragraph(next_step, s["body_serif"]))

    doc.build(flow)
    return buf.getvalue()


# ── New item form (New Item Forms) ─────────────────────────────────────────

def make_new_item_form(card_data: dict[str, Any]) -> bytes:
    s = _styles()
    buf = io.BytesIO()
    doc = _new_doc(buf)

    retailer = card_data.get("retailer", "RETAILER").upper()
    brand    = card_data.get("brand_name", "Brand")
    skus     = card_data.get("skus", [])
    fields   = card_data.get("fields", [])
    outstanding = card_data.get("outstanding", [])
    certs    = card_data.get("certs", [])

    flow: list = []
    flow.append(Paragraph(f"{retailer} NEW ITEM SUBMISSION", s["section"]))
    flow.append(Paragraph(brand, s["h1"]))
    if skus:
        flow.append(Paragraph(
            "<i>" + " · ".join(skus) + "</i>",
            s["subtitle_italic"],
        ))

    # Filled fields — two-column table (label left, value right)
    flow.append(Paragraph("FORM FIELDS", s["section"]))
    rows = [["FIELD", "VALUE", "STATUS"]]
    for f in fields:
        rows.append([f.get("label", ""), f.get("value", ""), f.get("status", "OK")])
    if rows[1:]:
        ft = Table(rows, colWidths=[2.2 * inch, 3.0 * inch, 1.0 * inch])
        style_cmds = [
            ("FONTNAME",  (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE",  (0, 0), (-1, -1), 9),
            ("TEXTCOLOR", (0, 0), (-1, 0), MUTED),
            ("TEXTCOLOR", (0, 1), (-1, -1), INK),
            ("LINEBELOW", (0, 0), (-1, 0), 0.5, HAIRLINE),
            ("LINEBELOW", (0, 1), (-1, -2), 0.25, HAIRLINE),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING",    (0, 0), (-1, -1), 6),
            ("VALIGN",        (0, 0), (-1, -1), "TOP"),
        ]
        # Highlight rows where status != OK
        for i, f in enumerate(fields, start=1):
            if (f.get("status") or "").upper() != "OK":
                style_cmds.append(("BACKGROUND", (0, i), (-1, i), ACCENT_BG))
                style_cmds.append(("TEXTCOLOR", (2, i), (2, i),
                                   colors.HexColor("#7A4F00")))
        ft.setStyle(TableStyle(style_cmds))
        flow.append(ft)

    # Outstanding callout
    if outstanding:
        flow.append(Paragraph("OUTSTANDING — NEEDS BRAND CONFIRMATION",
                              s["section"]))
        for item in outstanding:
            flow.append(Paragraph(f"• {item}", s["body"]))

    # Certifications
    if certs:
        flow.append(Paragraph("REQUIRED CERTIFICATIONS", s["section"]))
        cert_rows = [["CERT", "ID", "EXPIRES", "STATUS"]]
        for c in certs:
            cert_rows.append([
                c.get("name", ""), c.get("id", ""),
                c.get("expires", ""), c.get("status", "current"),
            ])
        ct = Table(cert_rows, colWidths=[1.6 * inch, 1.6 * inch, 1.4 * inch, 1.4 * inch])
        cmds = [
            ("FONTNAME",  (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE",  (0, 0), (-1, -1), 9),
            ("TEXTCOLOR", (0, 0), (-1, 0), MUTED),
            ("LINEBELOW", (0, 0), (-1, 0), 0.5, HAIRLINE),
            ("LINEBELOW", (0, 1), (-1, -2), 0.25, HAIRLINE),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING",    (0, 0), (-1, -1), 6),
        ]
        for i, c in enumerate(certs, start=1):
            if "expir" in (c.get("status", "") or "").lower():
                cmds.append(("TEXTCOLOR", (2, i), (3, i), RED_HIGH))
                cmds.append(("FONTNAME", (2, i), (3, i), "Helvetica-Bold"))
        ct.setStyle(TableStyle(cmds))
        flow.append(ct)

    doc.build(flow)
    return buf.getvalue()


# ── Cost build (auxiliary, used alongside sell sheet) ──────────────────────

def make_cost_build(card_data: dict[str, Any]) -> bytes:
    s = _styles()
    buf = io.BytesIO()
    doc = _new_doc(buf)

    brand    = card_data.get("brand_name", "Brand")
    retailer = card_data.get("retailer", "Retailer")
    rows     = card_data.get("cost_rows", [
        ("Suggested retail (SRP)",      "$1.99"),
        ("Retailer margin",             "32% / $0.64"),
        ("Wholesale to retailer",       "$1.35"),
        ("Slotting fee (1× SKU)",       "$1,200"),
        ("Promo allowance (3 events)",  "$900"),
        ("Net wholesale to brand",      "$1.05"),
        ("COGS (per unit)",             "$0.62"),
        ("Brand contribution / unit",   "$0.43"),
    ])

    flow: list = []
    flow.append(Paragraph(f"{brand} × {retailer}", s["h2"]))
    flow.append(Paragraph("COST BUILD", s["section"]))
    cb = Table([["LINE ITEM", "VALUE"]] + list(rows),
               colWidths=[3.6 * inch, 2.0 * inch])
    cb.setStyle(TableStyle([
        ("FONTNAME",  (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",  (0, 0), (-1, -1), 10),
        ("TEXTCOLOR", (0, 0), (-1, 0), MUTED),
        ("LINEBELOW", (0, 0), (-1, -2), 0.25, HAIRLINE),
        ("LINEABOVE", (0, -1), (-1, -1), 0.5, INK),
        ("FONTNAME",  (0, -1), (-1, -1), "Helvetica-Bold"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING",    (0, 0), (-1, -1), 8),
    ]))
    flow.append(cb)
    flow.append(Spacer(1, 14))
    flow.append(Paragraph(
        "<i>All figures pre-tax, FOB origin. Margin assumes "
        "case-pack of 12 and 90-day pay terms.</i>",
        s["muted"],
    ))
    doc.build(flow)
    return buf.getvalue()


# ── Dispatch table ──────────────────────────────────────────────────────────

GENERATORS = {
    "sell_sheet":     make_sell_sheet,
    "one_pager":      make_one_pager,
    "new_item_form":  make_new_item_form,
    "cost_build":     make_cost_build,
}


def generate(doc_type: str, card_data: dict) -> bytes:
    """Generate a PDF by doc_type. Raises if unknown type."""
    if doc_type not in GENERATORS:
        raise ValueError(f"Unknown doc_type: {doc_type}")
    return GENERATORS[doc_type](card_data)
