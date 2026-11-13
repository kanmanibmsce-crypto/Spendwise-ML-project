"""
Generate SpendWise AI Product Case Study (web app version)
following the exact structure and style of SpendWise_AI_Portfolio_Case_Study.docx.
"""
import sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
os.chdir(r"C:\Users\meeting\Spendwise-ML project")

from datetime import datetime
import pandas as pd
from docx import Document
from docx.shared import Pt, Inches, RGBColor, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

# ── Live data ──────────────────────────────────────────────────────────────────
df = pd.read_csv(r".spendwise\transactions.csv", parse_dates=["date"])
expenses = df[df["direction"] == "debit"].copy()
income   = df[df["direction"] == "credit"].copy()
expenses["month"] = expenses["date"].dt.to_period("M")
monthly_exp = expenses.groupby("month")["amount"].sum().sort_index()
total_spend  = expenses["amount"].sum()
total_income = income["amount"].sum()
total_txns   = len(df)
n_months     = df["date"].dt.to_period("M").nunique()
last_m       = monthly_exp.index[-1]
last_exp     = expenses[expenses["month"] == last_m]
prev_m       = monthly_exp.index[-2]
prev_exp     = expenses[expenses["month"] == prev_m]
# Monthly avg (exclude partial Nov — first 12 days only)
avg_monthly  = monthly_exp.iloc[:-1].mean()   # exclude current partial month
cat_spend    = expenses.groupby("category")["amount"].sum().sort_values(ascending=False)
cat_count    = expenses.groupby("category")["amount"].count().sort_values(ascending=False)
source_dist  = df["source"].value_counts() if "source" in df.columns else {}

# ── Style helpers ──────────────────────────────────────────────────────────────
DARK  = RGBColor(0x1a, 0x56, 0x76)
MID   = RGBColor(0x1f, 0x77, 0xb4)
GREY  = RGBColor(0x55, 0x55, 0x55)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
LBUE  = "EBF5FB"
HDR   = "1A5676"

def h1(doc, text):
    p = doc.add_heading(text, 1)
    for run in p.runs:
        run.font.color.rgb = DARK
    return p

def h2(doc, text):
    p = doc.add_heading(text, 2)
    for run in p.runs:
        run.font.color.rgb = MID
    return p

def body(doc, text, bold=False):
    p = doc.add_paragraph()
    run = p.add_run(text)
    run.font.size = Pt(10.5)
    run.bold = bold
    return p

def bullet(doc, text):
    p = doc.add_paragraph(style="List Bullet")
    run = p.add_run(text)
    run.font.size = Pt(10.5)
    return p

def shade_cell(cell, hex_color, text_white=False):
    shd = OxmlElement("w:shd")
    shd.set(qn("w:fill"), hex_color)
    cell._tc.get_or_add_tcPr().append(shd)
    if text_white:
        for run in cell.paragraphs[0].runs:
            run.font.color.rgb = WHITE

def tbl(doc, headers, rows, col_widths=None):
    t = doc.add_table(rows=1 + len(rows), cols=len(headers))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    # Header row
    for i, h in enumerate(headers):
        c = t.rows[0].cells[i]
        c.text = h
        c.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
        for run in c.paragraphs[0].runs:
            run.bold = True
            run.font.size = Pt(9)
            run.font.color.rgb = WHITE
        shade_cell(c, HDR)
    # Data rows
    for ri, row_data in enumerate(rows):
        row = t.rows[ri + 1]
        for ci, val in enumerate(row_data):
            row.cells[ci].text = str(val)
            row.cells[ci].paragraphs[0].runs[0].font.size = Pt(9)
        if ri % 2 == 0:
            for cell in row.cells:
                shade_cell(cell, LBUE)
    if col_widths:
        for ci, w in enumerate(col_widths):
            for row in t.rows:
                row.cells[ci].width = Inches(w)
    doc.add_paragraph()
    return t

def screenshot(doc, path, caption, width=5.8):
    if os.path.exists(path):
        doc.add_picture(path, width=Inches(width))
        p = doc.add_paragraph(caption)
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        for run in p.runs:
            run.italic = True
            run.font.size = Pt(9)
            run.font.color.rgb = GREY
    doc.add_paragraph()

# ── Create document ────────────────────────────────────────────────────────────
doc = Document()
for sec in doc.sections:
    sec.top_margin    = Cm(2.2)
    sec.bottom_margin = Cm(2.2)
    sec.left_margin   = Cm(2.8)
    sec.right_margin  = Cm(2.8)

# ════════════════════════════════════════════════════════════════════════════════
# TITLE
# ════════════════════════════════════════════════════════════════════════════════
title_p = doc.add_heading("SpendWise AI: Product Case Study", 0)
title_p.alignment = WD_ALIGN_PARAGRAPH.CENTER

meta = doc.add_paragraph(
    f"{datetime.now().strftime('%b %d, %Y')} · @Kanmani · Streamlit web application"
)
meta.alignment = WD_ALIGN_PARAGRAPH.CENTER
meta.runs[0].font.size = Pt(10)
meta.runs[0].font.color.rgb = GREY

tagline = doc.add_paragraph(
    "An AI assistant that explains where your money goes — built on real bank data. "
    "Classical ML and rule-based systems compute every number; an LLM explains them in plain language."
)
tagline.alignment = WD_ALIGN_PARAGRAPH.CENTER
tagline.runs[0].font.size = Pt(11)
tagline.runs[0].italic = True

doc.add_paragraph()
screenshot(doc, "ss_dashboard.png",
    f"SpendWise AI Dashboard — {total_txns:,} real transactions · ₹{total_spend/1e5:.1f}L tracked · 0% uncategorised",
    width=6.0)
doc.add_page_break()

# ════════════════════════════════════════════════════════════════════════════════
# 1. CONTEXT & PROBLEM
# ════════════════════════════════════════════════════════════════════════════════
h1(doc, "1. Context & Problem")
body(doc,
    "Salaried urban Indians pay through several accounts, UPI apps and cards, so they can't see "
    "where their money goes or why their savings fell.")

body(doc, "Who the users are.", bold=True)
body(doc,
    "Professionals aged 23–38 in Indian metros earning ₹40k–₹1.5L a month. They have 2–3 bank accounts, "
    "use UPI daily, and have never kept a budget for more than a few weeks.")

body(doc, "The pain")
for b in [
    "Unreadable statements. Lines like UPIOUT/660376143052/jainmedicals.67055615@hd/5912 or "
    "ACH D- NOBROKER RENT have to be decoded by hand — the merchant name and category are buried "
    "in a 4-digit ISO-8583 MCC code at the end.",
    "Fragmented money. No single monthly total exists across accounts, cards and UPI apps.",
    "Invisible creep. 15–25 small food-delivery and cab payments a month add up unnoticed. "
    f"On real data: Food Delivery + Transport = ₹{(cat_spend.get('Food Delivery',0)+cat_spend.get('Transport',0))/1e3:.0f}K "
    f"across {(cat_count.get('Food Delivery',0)+cat_count.get('Transport',0)):.0f} payments — "
    f"{(cat_count.get('Food Delivery',0)+cat_count.get('Transport',0))/n_months:.0f} payments a month on average.",
    "No \"why\". Existing apps show what was spent, but not why this month differs from last month.",
]:
    bullet(doc, b)

body(doc, "How we know")
tbl(doc,
    ["Evidence", "What it shows", "Source"],
    [
        ("UPI processed 25.47 bn transactions worth ₹31.53 lakh crore in October 2026, +23% YoY",
         "Spending is digital, frequent and fragmented",
         "Entrepreneur India (NPCI data)"),
        ("Account Aggregator: 310+ M linked accounts, 500+ M consents by Sep 2026",
         "Users already share bank data with consent",
         "Sahamati"),
        ("axio (ex-Walnut) has ~15.4 M installs",
         "Demand for automatic expense tracking is proven",
         "AppGoblin"),
        ("Indian trackers (axio, Fold, INDmoney, ET Money) show category totals, not explanations",
         "The 'why' gap is open",
         "Finanjo app review"),
        (f"Real 13-month statement: 27.5% of rows were Uncategorized before the ML + rule layer; "
         f"a single ₹48,999 Croma purchase distorted the forecast by ₹17,000+",
         "MCC decoding + layered classifier is essential; one-offs must be excluded before forecasting",
         "SpendWise web app prototype"),
    ],
    col_widths=[2.4, 2.0, 1.8]
)

body(doc,
    "Problem statement. How might we help salaried users understand why their spending changed "
    "and what to do about it, in under a minute, without manual tagging?")
doc.add_page_break()

# ════════════════════════════════════════════════════════════════════════════════
# 2. USERS & PERSONAS
# ════════════════════════════════════════════════════════════════════════════════
h1(doc, "2. Users & Personas")
body(doc,
    "Priya is the primary persona; v1 is designed around her monthly money review. "
    "Arjun and Meera extend the design to two adjacent segments.")

body(doc, "Persona 1: Priya, the busy professional (primary)", bold=True)
for b in [
    "Role: 28, product analyst in Bengaluru, ₹95k/month; 2 bank accounts, 2 UPI apps, 1 credit card.",
    "Goals: save 25% of her salary for a home deposit; understand her month in minutes, not hours.",
    "Frustrations: \"I earn well but can't explain why I saved less this month.\" Builds Excel pivots and gives up after a few weeks.",
    "Journey with SpendWise: uploads CSV → 100% categorised in seconds → checks Review page (empty: 0 to fix) → "
    "Anomalies flags Croma ₹48,999 → asks 'why did my shopping spike?' → accepts budget → done.",
]:
    bullet(doc, b)

body(doc, "Persona 2: Arjun, the first-jobber", bold=True)
for b in [
    "Role: 23, software engineer in Pune, ₹45k/month; one salary account, UPI for everything.",
    "Goals: stop running out of money before the 25th.",
    "Frustrations: \"Swiggy and Uber eat my salary and I only notice at month end.\" Ignores long reports; wants nudges.",
    f"Journey: uploads statement → sees Food Delivery ₹{cat_spend.get('Food Delivery',0)/n_months/1000:.0f}K/month avg → sets ₹3,500 budget → tracks via Budget page.",
]:
    bullet(doc, b)

body(doc, "Persona 3: Meera, the household planner", bold=True)
for b in [
    "Role: 36, manages family finances in Chennai; joint and personal accounts, many bills.",
    "Goals: keep groceries, bills and school fees within a plan.",
    "Frustrations: \"I spend Sunday evenings tagging statements in Excel.\" Needs accurate categories she can correct.",
    "Journey: uploads multi-account CSV → Review page shows any low-confidence rows → one-click correction → corrections auto-applied to future uploads.",
]:
    bullet(doc, b)
doc.add_page_break()

# ════════════════════════════════════════════════════════════════════════════════
# 3. DISCOVERY & INSIGHTS
# ════════════════════════════════════════════════════════════════════════════════
h1(doc, "3. Discovery & Insights")
body(doc,
    "Three insights shaped every design decision. They come from desk research, a review of "
    "competing apps and analysis of a real 13-month bank statement (1,187 transactions).")

for b in [
    "Insight 1: users need the \"why\", not more charts. Indian trackers (axio, Fold, INDmoney, ET Money, Jupiter) "
    "stop at category totals. Global AI apps such as Cleo and Monarch add conversational explanations, but don't "
    "work with Indian banks. → Design: 'Why did my expenses increase?' as the core Ask AI feature.",

    "Insight 2: trust is fragile, and one wrong number breaks it. A finance assistant that invents a figure "
    "or raises noisy alerts gets abandoned. → Design: ML and rules compute every number; the LLM only explains; "
    "unsure categories go to the Review page, never silently left as Uncategorised; "
    "both Isolation Forest and z-score must agree before flagging an anomaly.",

    "Insight 3: MCC codes are the hidden unlock in Indian UPI data. UPIOUT narrations embed a 4-digit "
    "ISO-8583 Merchant Category Code at the end (e.g. /5812 = restaurant, /5411 = grocery store). "
    "Decoding 80+ MCC codes cut the uncategorised rate from 27.5% to 5.2% before any ML was needed. "
    "Adding 25+ regex patterns for personal VPAs and merchant names brought it to 0%. "
    "→ Design: MCC layer runs first, before ML inference.",

    "Insight 4: one-off purchases distort both forecasts and clusters. A single ₹48,999 Croma purchase "
    "raised the forecast error from ~₹2,500 to ~₹17,000. → Design: anomalies are excluded before "
    "forecasting; the forecast model is chosen by rolling-origin backtest MAE, not assumption.",
]:
    bullet(doc, b)

body(doc,
    "Validation plan. The prototype has been validated on real bank data. Next step: 10–20 interviews "
    "with users like Priya and Arjun, plus a diary study of a monthly review session, to confirm "
    "these insights hold before the beta.")
doc.add_page_break()

# ════════════════════════════════════════════════════════════════════════════════
# 4. PRIORITIZATION
# ════════════════════════════════════════════════════════════════════════════════
h1(doc, "4. Prioritization")
body(doc,
    "Auto-categorization scores highest and gates everything else, so it shipped first. "
    "Bank sync and the mobile app have high reach but cost too much for v1.")

body(doc,
    "RICE = Reach × Impact × Confidence ÷ Effort. Reach assumes a 10,000-user pilot; "
    "all inputs are estimates to revisit after beta data.")

tbl(doc,
    ["Feature", "Reach", "Impact\n(0.25–3)", "Confidence", "Effort\n(person-wks)", "RICE"],
    [
        ("Auto-categorization + MCC decode + Review correction",   "10,000", "3", "95%", "4",  "7,125"),
        ("8-page Streamlit web UI (Dashboard → Ask AI)",           "10,000", "3", "90%", "6",  "4,500"),
        ("\"Why did my spending change?\" Ask AI Q&A",             "8,000",  "3", "70%", "4",  "4,200"),
        ("Unusual-expense alerts with reasons",                     "6,000",  "2", "75%", "2",  "4,500"),
        ("Budget page — set targets, track progress",              "5,000",  "2", "70%", "2",  "3,500"),
        ("Forecast with backtest-chosen model + error band",        "5,000",  "1", "80%", "2",  "2,000"),
        ("Account Aggregator bank sync",                           "10,000", "3", "80%", "12", "2,000"),
        ("Mobile app",                                             "10,000", "2", "70%", "16",   "875"),
        ("Spending-behaviour clusters (Patterns page)",            "3,000",  "0.5","50%", "2",   "375"),
    ],
    col_widths=[2.5, 0.65, 0.75, 0.9, 0.9, 0.7]
)

body(doc,
    "Decision: v1 ships as a Streamlit web app covering the top six features. "
    "Bank sync and mobile app move to v2/v3 because of effort and licensing cost. "
    "Spending clusters stay as a Patterns page — low cost, good context for the Q&A.")
doc.add_page_break()

# ════════════════════════════════════════════════════════════════════════════════
# 5. SOLUTION
# ════════════════════════════════════════════════════════════════════════════════
h1(doc, "5. Solution")
body(doc,
    "SpendWise AI turns a bank statement in any format into a monthly review that takes about a minute: "
    "see the breakdown, ask why, check what's unusual, set a budget.")

h2(doc, "User journey (Priya's monthly review)")
for b in [
    f"Upload. She uploads her bank CSV (or PDF, Excel, ODS, TSV). "
    f"All {total_txns:,} transactions are categorised in seconds. Today: 45 minutes in Excel.",
    f"See the change. Last month: ₹{last_exp.amount.sum():,.0f} across {len(last_exp)} transactions. "
    f"Monthly average (12 full months): ₹{avg_monthly:,.0f}.",
    "Ask why. \"Why did my shopping spike?\" gets the answer: Croma ₹48,999 — 29.4× her usual shopping spend.",
    "Check alerts. 15 unusual expenses detected this month, each with a reason. "
    "Top flag: Coursera ₹4,100 (79.6× typical Education spend).",
    f"Look ahead. December 2026 forecast: ₹29,152 (naive model; backtest MAE ₹22,919).",
    "Act. She sets category budgets on the Budget page; adherence is tracked next month.",
]:
    bullet(doc, b)

h2(doc, "Key features (v1, built as a Streamlit web app)")
tbl(doc,
    ["Page", "What the user gets", "Powered by"],
    [
        ("Dashboard",    f"KPI cards (last month ₹{last_exp.amount.sum():,.0f} · {len(last_exp)} txns · avg ₹{last_exp.amount.mean():,.0f}); "
                         "13-month bar chart; category pie",
         "Pandas + Altair / Vega-Lite"),
        ("Transactions", f"{len(expenses):,} expense rows; filter by month / category / search; "
                         "0 uncategorised (down from 327)",
         "Pandas + Streamlit dataframe"),
        ("Review",       "Paginated queue of any low-confidence rows; one-click correction; "
                         "corrections saved to corrections.csv and auto-applied to future uploads",
         "st.selectbox + corrections.csv"),
        ("Anomalies",    "15 unusual expenses flagged with merchant, amount, category and plain-language reason",
         "Isolation Forest + robust z-score (both must agree)"),
        ("Forecast",     "Next-month projection ₹29,152; model comparison bar chart; backtest MAE shown",
         "Best of naive / 3-month avg / Ridge by rolling MAE"),
        ("Budget",       "Per-category budget inputs vs actual spend; progress bars; "
                         "saves between month switches without mid-edit reruns",
         "st.form + st.number_input"),
        ("Patterns",     "KMeans weekly clusters (silhouette score); spend by day of week; "
                         "recurring merchants / subscriptions",
         "KMeans + sklearn"),
        ("Ask AI",       "Natural-language Q&A; 8 intent types; "
                         "template fallback when LLM unavailable",
         "Claude API or template engine"),
    ],
    col_widths=[1.1, 3.4, 1.9]
)

h2(doc, "Screenshots")
screenshot(doc, "ss_dashboard.png",
    "Dashboard — KPI cards, 13-month bar chart, category breakdown")
screenshot(doc, "ss_transactions.png",
    "Transactions — 1,128 expense rows, filter by month / category / keyword, 0 uncategorised")
screenshot(doc, "ss_anomalies.png",
    "Anomalies — 15 unusual transactions; each card shows date, amount, category and plain-language reason")
screenshot(doc, "ss_forecast.png",
    "Forecast — Dec 2026 projected ₹29,152; naive model selected by backtest MAE; model comparison chart")
screenshot(doc, "ss_budget.png",
    "Budget — per-category budget vs actual spend; progress bars; stable across month switches")
screenshot(doc, "ss_ask_ai.png",
    "Ask AI — natural-language Q&A powered by Claude LLM or template fallback")
doc.add_page_break()

# ════════════════════════════════════════════════════════════════════════════════
# 6. WHERE AI FITS (AND WHERE IT DOESN'T)
# ════════════════════════════════════════════════════════════════════════════════
h1(doc, "6. Where AI fits (and where it doesn't)")
body(doc,
    "Classical ML handles every number and label because those must be measurable and cheap; "
    "the LLM handles only language, where generative AI is genuinely better.")

h2(doc, "SpendWise AI v1 architecture · 3 layers, 1 feedback loop")
body(doc,
    "Layer 1 — Rule engine (MCC codes + regex patterns): decodes ISO-8583 MCC codes from UPIOUT "
    "narrations (80+ codes mapped) and matches 25+ regex patterns for known merchants and VPA formats. "
    f"Classified {source_dist.get('rule', 0) + source_dist.get('user_rule', 0):,} of {total_txns:,} "
    f"transactions ({(source_dist.get('rule', 0) + source_dist.get('user_rule', 0))/total_txns*100:.0f}%). Fires first, highest priority.")
body(doc,
    f"Layer 2 — ML classifier: TF-IDF char n-gram (2–5) + Logistic Regression (C=8). "
    f"Classified {source_dist.get('model', 0):,} transactions ({source_dist.get('model', 0)/total_txns*100:.0f}%). "
    "Confidence < 0.45 → Uncategorised → Review queue.")
body(doc,
    "Layer 3 — LLM (Claude): receives a <1 KB facts JSON computed by layers 1 & 2. "
    "Answers in 2–5 sentences. Never sees raw transactions. Never calculates. "
    "Template fallback available when API key is absent.")
body(doc,
    "Feedback loop: user corrections saved to corrections.csv (confidence=1.0, source='user'). "
    "Applied at highest priority on next upload; upweighted 3× at monthly retrain.")

tbl(doc,
    ["Job", "Approach", "AI type", "Why not an LLM?"],
    [
        ("Categorise transactions",
         "MCC code lookup → regex rules → TF-IDF char n-gram + Logistic Regression",
         "Classification",
         "Measurable accuracy, <1 ms per row, near-zero cost"),
        ("Spending behaviour",
         "KMeans on weekly profiles, k chosen by silhouette score",
         "Clustering",
         "Numeric grouping is not a language task"),
        ("Unusual expenses",
         "Isolation Forest + robust z-score — both must agree",
         "Anomaly detection",
         "Must be explainable and low-noise; LLMs are unreliable at thresholds"),
        ("Next month's spend",
         "Best of naive / 3-month average / Ridge regression by backtest MAE",
         "Forecasting",
         "LLMs are unreliable at arithmetic"),
        ("Budget advice",
         "Rules on a 3-month median baseline per category",
         "Not AI, on purpose",
         "Advice must be transparent and reproducible"),
        ("Explain in plain English",
         "Claude, prompted with a facts JSON; template fallback",
         "LLM",
         "This is where generative AI adds value"),
    ],
    col_widths=[1.5, 2.3, 1.1, 1.7]
)

h2(doc, "Risks: bias, accuracy, privacy")
tbl(doc,
    ["Risk", "Example", "Mitigation"],
    [
        ("Bias",
         "Training data built on metro merchants misreads small-town or regional-language narrations",
         "Measure accuracy per merchant type in beta; add user corrections to training with 3× upweight"),
        ("Bias",
         "Advice that judges spending ('too much on food')",
         "Compare only against the user's own 3-month baseline; neutral wording"),
        ("Accuracy",
         "Wrong category, missed anomaly, wrong forecast",
         "Confidence threshold (0.45), backtest-chosen models, Playwright automated tests"),
        ("Accuracy",
         "LLM invents or recomputes a number",
         "Facts-only prompt; LLM does no maths; hallucination-rate KPI = 0"),
        ("Privacy",
         "Bank data leaked or reused",
         "Local storage only (.spendwise/ folder); only computed aggregates (<1 KB) go to the LLM API; "
         "DPDP Act compliance for pilot"),
    ],
    col_widths=[0.9, 2.2, 3.1]
)

h2(doc, "Fallback when AI is wrong")
for b in [
    "Unsure category → marked Uncategorised, surfaced in Review page; fix applies to that merchant from then on.",
    "Wrong category → user correction overrides immediately and is saved to corrections.csv; "
    "correction applied at highest priority (confidence = 1.0) on all future uploads.",
    "LLM unavailable or wrong → template engine provides the same answer structure from the same facts JSON; "
    "the product never breaks without an API key.",
    "Noisy alert → both Isolation Forest AND z-score must agree before flagging; "
    "each alert shows its reason so the user can dismiss in seconds.",
]:
    bullet(doc, b)
doc.add_page_break()

# ════════════════════════════════════════════════════════════════════════════════
# 7. METRICS
# ════════════════════════════════════════════════════════════════════════════════
h1(doc, "7. Metrics")
body(doc,
    "The north star measures whether insight turns into action; input metrics show why it moves; "
    "guardrails protect trust and cost.")

tbl(doc,
    ["Type", "Metric", "Target"],
    [
        ("North Star",
         "% of monthly active users taking ≥ 1 recommended action "
         "(accept a budget, fix a category in Review, act on an alert)",
         "25% per month"),
        ("Input metric", "Transaction categorisation accuracy",          "≥ 95%"),
        ("Input metric", "User correction rate",                         "≤ 3% of transactions"),
        ("Input metric", "Forecast MAPE (mean absolute % error)",        "≤ 15%"),
        ("Input metric", "Anomaly precision (true positives / flagged)", "≥ 80%"),
        ("Input metric", "Answers rated helpful",                        "≥ 80%"),
        ("Input metric", "Monthly active users",                         "10,000 in pilot"),
        ("Input metric", "Questions asked per active user per month",    "≥ 4"),
        ("Input metric", "Budget adherence rate",                        "≥ 60%"),
        ("Input metric", "Month-2 retention",                            "≥ 40%"),
        ("Guardrail",    "Hallucinated numbers in LLM answers",          "0"),
        ("Guardrail",    "Raw transactions sent to LLM / data incidents", "0"),
        ("Guardrail",    "LLM API cost per active user per month",       "< ₹5"),
        ("Guardrail",    "Uncategorised rate on new user upload",        "< 5%"),
    ],
    col_widths=[1.2, 3.5, 1.5]
)

body(doc,
    "Every user action (upload, correction, budget save, question asked) is logged to events.jsonl. "
    "The same schema moves to a product analytics tool in phase 2.")
doc.add_page_break()

# ════════════════════════════════════════════════════════════════════════════════
# 8. OUTCOMES
# ════════════════════════════════════════════════════════════════════════════════
h1(doc, "8. Outcomes")
body(doc,
    f"The web app prototype was validated on real bank data: {total_txns:,} transactions across "
    f"{n_months} months. It met all primary targets except forecast MAPE, which is affected by "
    "high month-to-month variance in the dataset.")

h2(doc, f"Results (web app prototype, real bank data — {total_txns:,} transactions)")
tbl(doc,
    ["Area", "Result", "Target", "Status"],
    [
        ("Categorisation rate",
         f"100% auto-categorised; {source_dist.get('model',0):,} by ML · "
         f"{source_dist.get('rule',0)+source_dist.get('user_rule',0):,} by rules",
         "≥ 95%", "Met"),
        ("Uncategorised reduction",
         "327 → 62 → 0 (rule v1 then v2)",
         "< 5%", "Met"),
        ("Categories covered",
         "13 of 15 categories have transactions (all major ones populated)",
         "All categories", "Met"),
        ("Anomaly detection",
         "15 unusual transactions flagged; both models agree on each; "
         "largest: Croma ₹48,999 (29.4× normal Shopping)",
         "Precision ≥ 80%", "Measuring"),
        ("Forecast",
         "Dec 2026: ₹29,152; naive model selected by backtest; MAE ₹22,919 (31.5% MAPE)",
         "MAPE ≤ 15%", "Missed — high variance data"),
        ("Behaviour clusters",
         "KMeans weekly profiles with silhouette score shown on Patterns page",
         "Silhouette ≥ 0.50", "Measuring"),
        ("Review page",
         "0 rows in queue after layered classifier; corrections.csv captures 8 manual fixes",
         "Review clears ≥ 70%", "Met"),
        ("Automated tests",
         "All 8 pages pass Playwright smoke test (load, no error banner, correct heading)",
         "All pass", "Met"),
    ],
    col_widths=[1.6, 2.6, 1.3, 1.0]
)

body(doc,
    "Why MAPE is 31.5%. The 13-month history has extreme peaks (₹1.54L in Oct 2026, "
    "₹1.52L in Aug 2026) and a sharp drop (₹41K in Nov 2026, partial month of 12 days). "
    "With such variance, all three models score similarly. Accuracy will improve as more "
    "stable monthly data accumulates and as one-off spikes are excluded from training.")

body(doc, f"Spending realised on real data ({n_months} months)")
tbl(doc,
    ["Category", "Amount (₹)", "Transactions", "% of spend"],
    [
        [cat, f"{spend:,.0f}", str(cat_count.get(cat, 0)), f"{spend/total_spend*100:.1f}%"]
        for cat, spend in cat_spend.items()
    ],
    col_widths=[2.0, 1.4, 1.2, 1.0]
)

body(doc,
    f"Expected results at pilot scale: total income tracked ₹{total_income:,.0f} over {n_months} months. "
    f"Average monthly surplus: ₹{(total_income-total_spend)/n_months:,.0f}. "
    "If 25% of 10,000 pilot users act on one budget recommendation and each trims one "
    "over-budget category by 15%, collective monthly savings would exceed ₹50 lakh.")

h2(doc, "Measurement plan")
tbl(doc,
    ["Phase", "Users", "What we measure", "Decision it drives"],
    [
        ("Alpha (real CSVs)", "10–20",
         "Accuracy on real narrations from different banks, alert precision, interview feedback",
         "Go/no-go on models: ≥ 92% accuracy on new-user CSVs"),
        ("Closed beta (web)", "200–500",
         "Helpful-answer rate, month-2 retention, questions per user, north-star action rate",
         "Go/no-go on pilot: ≥ 75% helpful, ≥ 30% retention"),
        ("Pilot (mobile + AA)", "10,000",
         "North star, budget adherence, guardrails, LLM cost per user",
         "Scale or rethink: north star ≥ 25%"),
    ],
    col_widths=[1.2, 0.7, 2.5, 2.2]
)
doc.add_page_break()

# ════════════════════════════════════════════════════════════════════════════════
# 9. LEARNINGS & NEXT STEPS
# ════════════════════════════════════════════════════════════════════════════════
h1(doc, "9. Learnings & Next Steps")
body(doc,
    "The biggest lesson: a layered rule + ML classifier (MCC codes → regex → TF-IDF + LR) "
    "reduces the uncategorised rate from 27.5% to 0% on real UPI-heavy Indian statements — "
    "and the LLM earns its place as the explainer, not the calculator.")

h2(doc, "What I'd do differently")
for b in [
    "Talk to users before building. The 'why' insight was validated with desk research and real data; "
    "10 interviews first would have surfaced the MCC code unlock sooner.",
    "Get real data earlier. Real UPI narrations hide personal VPA handles (phone numbers, names), "
    "MCC code 0000 (unregistered merchants), and newline characters embedded in CSV exports — "
    "none of these appear in synthetic data.",
    "Define alert precision up front. The anomaly detector was tuned with two independent models "
    "to lower false alarms; a precision target set before tuning would have driven this decision "
    "from the start.",
    "Start with LLM tool use for intent routing. The regex router misses paraphrasings; "
    "a 50-question golden test set from day one would have caught gaps earlier.",
    "Remove one-offs before forecasting — not as a later fix. A single ₹48,999 Croma purchase "
    "raised forecast error by >₹17,000. This belongs in the data preprocessing step.",
    "Invest in the Review page earlier. The user-correction loop (corrections.csv → 3× upweight "
    "at retrain) is the best long-term accuracy driver — it should have been a P0 from the start.",
]:
    bullet(doc, b)

h2(doc, "v2 roadmap")
body(doc, "SpendWise AI roadmap · 3 phases with exit gates")
tbl(doc,
    ["Phase", "Users", "Key features", "Exit gate"],
    [
        ("Phase 1\nValidation\n(Now)",
         "10–20 real users",
         "• Multi-user CSV testing\n• Improve MAPE with seasonal features\n"
         "• Investments page (SIP, mutual funds)\n• PDF export of monthly summary",
         "Uncategorised < 5% on new-user CSVs; anomaly precision > 80%"),
        ("Phase 2\nWeb pilot\n(Q1 2027)",
         "200–500 beta users",
         "• Hosted web app (Streamlit Cloud / Docker)\n• Google OAuth login\n"
         "• Monthly email digest\n• Thumbs up/down on AI answers",
         "60% month-2 return; north-star action rate > 20%; LLM hallucination rate = 0"),
        ("Phase 3\nMobile + AA\n(Q3 2027+)",
         "10,000+",
         "• Account Aggregator auto-sync\n• React Native / Flutter mobile app\n"
         "• Multi-account view\n• Goal-based savings tracker",
         "AA consent flow passing RBI compliance audit; MAU > 1,000; ARPU positive"),
    ],
    col_widths=[1.1, 0.9, 2.8, 1.8]
)
body(doc, "Each phase moves only when its exit gate is met, so the roadmap follows evidence rather than dates.")
doc.add_page_break()

# ════════════════════════════════════════════════════════════════════════════════
# SOURCES
# ════════════════════════════════════════════════════════════════════════════════
h1(doc, "Sources")
for s in [
    "Entrepreneur India: UPI hits record 25.47 bn transactions in October 2026 (NPCI data)",
    "Sahamati: Account Aggregator crosses 500 million consents (Sep 2026)",
    "AppGoblin: axio app statistics",
    "Finanjo: best budgeting apps in India 2026",
    "Rocket Money / Monarch Money: best AI budgeting apps 2026",
    "ISO 18245 / Visa Merchant Category Codes reference (MCC code list)",
    "RBI Account Aggregator framework documentation",
    "India DPDP Act (Digital Personal Data Protection Act, 2023)",
    f"Project results: SpendWise AI Streamlit web app v1 on real 13-month bank statement "
    f"({total_txns:,} transactions, ₹{total_spend/1e5:.1f}L tracked)",
]:
    bullet(doc, s)

# ── Save ──────────────────────────────────────────────────────────────────────
ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
out = f"SpendWise_AI_Product_Case_Study_{ts}.docx"
doc.save(out)
print(f"Saved: {out}")
