# Sedge

**AI-powered workflow tool for independent CPG food brokers.**

Sedge automates the research, pitching, and paperwork that brokers do by hand — so they can spend more time selling and less time on spreadsheets.

---

## What it does

### Brand Scout
Evaluates whether a CPG brand is worth pursuing. You enter a brand name, and Sedge researches it across Amazon, Instacart, social media, and trade press — then scores it across five criteria:

- **Velocity Proof** — Amazon reviews, ratings, Subscribe & Save, SPINS mentions
- **Distribution Density** — estimated door count, retail chain presence, Faire listing
- **Margin Viability** — SRP vs. category benchmarks, funding raised
- **Brand Story Clarity** — hero product, founder story, social following, certifications
- **Promotional Independence** — DTC channel, TPR frequency, Subscribe & Save

Scores 70+ are Established, 45–69 are Broker Ready, below 45 are Too Early. For qualifying brands, Sedge drafts a personalized outreach email to the founder.

### Retailer Pitcher
Generates retailer-ready pitch packages for Whole Foods, Sprouts, and Erewhon. Each package includes a buyer-persona-tailored outreach email and a 1-page sell sheet — ready to send.

### Admin & Ops
Autofills Whole Foods new item setup forms from Brand Scout data. Sedge matches extracted brand fields to WFM form fields, flags required gaps, and exports a filled Excel file.

### Dashboard
One-click orchestrator that runs all three agents in sequence for any brand — Brand Scout → three retailer pitches → WFM form — with an approval screen before anything is sent.

---

## Tech stack

| Layer | Tool |
|---|---|
| UI | Streamlit |
| Agent framework | LangGraph |
| LLM | Claude (Anthropic) |
| Memory / database | Supabase (Postgres) |
| Hosting | Railway |

---

## Running locally

```bash
pip install -r requirements.txt
streamlit run ui/sedge_app.py
```

Requires a `.env` file with:

```
ANTHROPIC_API_KEY=...
SUPABASE_URL=...
SUPABASE_SERVICE_ROLE_KEY=...
TAVILY_API_KEY=...
```
