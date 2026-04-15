"""1-page HTML sell sheet renderer — letter size, densely laid out.

Deterministic HTML — no LLM in this module. The LLM produces narrative
fields (hero_line, why_now, proof_points, category_fit, next_step). This
module stitches them into a letter-sized layout that is screenshot-ready
for the demo and browser-printable to PDF by the broker.

Layout (top to bottom, ~816 × 1056 px letter):
  1. Header     brand name + "Prepared for <retailer>"
  2. Hero       big tagline + why-now paragraph
  3. Stats      4 tiles: velocity / margin / retail-count / certs-count
  4. Proof      bullet list, 4 points
  5. Retail     badge wall of confirmed retailers from Scout
  6. Fit        category-fit paragraph for this specific buyer
  7. Next step  1-sentence meeting ask
  8. Footer     score + "Sedge"
"""
from __future__ import annotations

import html
from typing import TypedDict


class SellSheetFields(TypedDict):
    brand_name: str
    category: str
    buyer_retailer: str
    hero_line: str
    why_now: str
    proof_points: list[str]
    velocity_label: str
    margin_label: str
    retail_count_label: str   # e.g. "5 confirmed banners"
    retailers_text: str       # comma-separated fallback text
    retailer_badges: list[str]  # list of retailer names with confirmed=true
    certifications: list[str]
    category_fit: str         # 2-3 sentences on fit with this buyer
    next_step: str            # 1-sentence meeting ask
    score: int


BASE_CSS = """
  @page { size: letter; margin: 0; }
  * { box-sizing: border-box; }
  body { margin: 0; padding: 28px 0; background: #efece3;
         font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
         color: #1b2a1d; }
  .sheet { width: 780px; min-height: 1020px; margin: 0 auto;
           background: #ffffff; padding: 42px 52px; position: relative;
           box-shadow: 0 2px 18px rgba(0,0,0,.08);
           border-top: 8px solid #2f5d3a; display: flex; flex-direction: column; }

  /* Header */
  .head { display: flex; justify-content: space-between; align-items: flex-end;
          padding-bottom: 10px; border-bottom: 1px solid #cfcfcf; }
  .brand { font-size: 34px; font-weight: 800; letter-spacing: -0.6px; }
  .tag   { text-align: right; font-size: 11px; letter-spacing: 1.3px;
           text-transform: uppercase; color: #5c6b5c; line-height: 1.6; }

  /* Hero */
  .hero  { margin: 18px 0 6px; font-size: 19px; font-weight: 600;
           line-height: 1.35; color: #1b2a1d; }
  .why   { font-size: 13px; color: #3c4a3c; line-height: 1.55; margin-bottom: 14px; }

  /* Stats strip */
  .stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px;
           margin: 10px 0 16px; }
  .stat  { background: #f2efe5; border-left: 3px solid #2f5d3a;
           padding: 10px 12px; }
  .stat h4 { margin: 0 0 4px; font-size: 10px; letter-spacing: 1.2px;
             text-transform: uppercase; color: #2f5d3a; }
  .stat p  { margin: 0; font-size: 12.5px; line-height: 1.35; color: #1b2a1d; }

  /* Section label */
  .label { font-size: 11px; letter-spacing: 1.4px; text-transform: uppercase;
           color: #2f5d3a; font-weight: 700; margin: 14px 0 6px; }

  /* Proof */
  .proof { margin: 0 0 10px; padding: 0 0 0 18px; font-size: 13px;
           line-height: 1.6; color: #1b2a1d; }
  .proof li { margin-bottom: 2px; }

  /* Retail badges */
  .badges { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 10px; }
  .badge  { border: 1.2px solid #2f5d3a; color: #2f5d3a; font-size: 11.5px;
            padding: 6px 10px; border-radius: 4px; font-weight: 600;
            letter-spacing: 0.3px; }
  .badges .empty { color: #777; border-color: #bbb; font-style: italic;
                   font-weight: 400; }

  /* Fit and next step */
  .fit { font-size: 12.5px; line-height: 1.55; color: #1b2a1d;
         background: #f2efe5; border-radius: 6px; padding: 12px 14px;
         margin-bottom: 10px; }
  .next { font-size: 12.5px; color: #1b2a1d; border-left: 3px solid #2f5d3a;
          padding: 8px 0 8px 14px; margin-bottom: 10px; font-weight: 600; }

  /* Footer */
  .foot { display: flex; justify-content: space-between; align-items: center;
          margin-top: auto; padding-top: 10px; border-top: 1px solid #cfcfcf;
          font-size: 10.5px; color: #707070; letter-spacing: 0.8px;
          text-transform: uppercase; }
  .score { font-weight: 800; color: #2f5d3a; font-size: 12.5px; }
"""


def _badge(retailer: str) -> str:
    return f'<span class="badge">{html.escape(retailer)}</span>'


def render(fields: SellSheetFields) -> str:
    def esc(x: str) -> str:
        return html.escape(x or "", quote=True)

    proofs = "\n".join(f"<li>{esc(p)}</li>" for p in fields["proof_points"])
    badges_html = (
        "\n".join(_badge(r) for r in fields["retailer_badges"])
        if fields["retailer_badges"]
        else '<span class="badge empty">No confirmed banners yet</span>'
    )
    certs_html = ", ".join(esc(c) for c in fields["certifications"]) or "—"

    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>{esc(fields['brand_name'])} — Sell Sheet</title>
<style>{BASE_CSS}</style></head><body><div class="sheet">

  <div class="head">
    <div class="brand">{esc(fields['brand_name'])}</div>
    <div class="tag">
      Prepared for<br>
      <strong style="color:#2f5d3a;font-size:13px;letter-spacing:0.8px;">
        {esc(fields['buyer_retailer'])}
      </strong><br>
      Category · {esc(fields['category'])}
    </div>
  </div>

  <p class="hero">{esc(fields['hero_line'])}</p>
  <p class="why">{esc(fields['why_now'])}</p>

  <div class="stats">
    <div class="stat"><h4>Velocity</h4><p>{esc(fields['velocity_label'])}</p></div>
    <div class="stat"><h4>Margin</h4><p>{esc(fields['margin_label'])}</p></div>
    <div class="stat"><h4>Retail Footprint</h4><p>{esc(fields['retail_count_label'])}</p></div>
    <div class="stat"><h4>Certifications</h4><p>{certs_html}</p></div>
  </div>

  <div class="label">Proof Points</div>
  <ul class="proof">{proofs}</ul>

  <div class="label">In Retail Today</div>
  <div class="badges">{badges_html}</div>

  <div class="label">Category Fit for {esc(fields['buyer_retailer'])}</div>
  <div class="fit">{esc(fields['category_fit'])}</div>

  <div class="next">Next step · {esc(fields['next_step'])}</div>

  <div class="foot">
    <span>Sedge Broker Readiness</span>
    <span class="score">Score {fields['score']}/100</span>
  </div>

</div></body></html>"""
