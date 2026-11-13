# SpendWise AI – Personal Finance Intelligence Assistant (CLI)

An AI assistant that reads your bank-statement CSV, categorizes every transaction, finds spending patterns, flags unusual expenses, forecasts next month, suggests budgets and answers questions in plain English.

```
$ spendwise ask "Why did my expenses increase this month?"

🤖 Your expenses increased by 23% in 2026-10 compared with 2026-09 (₹59,052 → ₹72,424).
   The main contributors were shopping, transport and food delivery.
   Shopping spending increased by 141% (₹5,216 → ₹12,555).
   [intent: expense_change | engine: template]
```

**Core design idea:** traditional ML computes the numbers and the LLM only explains them. Because of this split, the assistant can't invent figures. It also runs offline, costs nothing per question, and each part can be tested on its own.

| Problem | Approach | Why this and not an LLM |
|---|---|---|
| Categorize transactions | **Classification**: TF-IDF char n-grams + Logistic Regression | Fast, cheap, measurable accuracy, knows when it's unsure |
| Spending behaviour | **Clustering**: KMeans on weekly profiles | Unsupervised; discovers "modes" nobody labelled |
| Unusual expenses | **Anomaly detection**: Isolation Forest + robust z-score | Needs to be explainable ("24x your usual") and have few false alarms |
| Next month's spend | **Forecasting**: naive vs moving average vs Ridge trend, backtested | LLMs are bad at arithmetic; MAE is the metric |
| Budget advice | Transparent rules on top of ML outputs | Users (and regulators) need to know *why* |
| Q&A | **LLM** (Claude) over computed facts, with a template fallback | Language is where GenAI adds value |

---

## Quick start (5 minutes)

```bash
# 1. Python 3.10+
python3 -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 2. Run everything on built-in sample data
python -m spendwise demo

# 3. Optional: turn on LLM answers
export ANTHROPIC_API_KEY=sk-ant-...                       # Windows: set ANTHROPIC_API_KEY=...
python -m spendwise chat
```

### All commands

| Command | What it does |
|---|---|
| `python -m spendwise generate-data` | Creates `data/training_labeled.csv` + a 12-month `data/sample_bank_statement.csv` |
| `python -m spendwise train` | Trains the categorizer and prints hold-out accuracy + F1 per category |
| `python -m spendwise upload <file.csv>` | Imports a bank CSV (Debit/Credit or signed Amount columns) and auto-categorizes it |
| `python -m spendwise transactions [--category X] [--uncategorized]` | Lists transactions |
| `python -m spendwise summary` | Monthly spend by category, with a text bar chart |
| `python -m spendwise patterns` | Behaviour clusters, subscriptions, spend by weekday |
| `python -m spendwise anomalies` | Unusual expenses, with a reason for each |
| `python -m spendwise forecast` | Next month's forecast, the model chosen and its MAE |
| `python -m spendwise budget [--accept]` | Budget suggestions, a 50/30/20 check and adherence tracking |
| `python -m spendwise ask "..." [--facts] [--no-llm]` | Asks one question; `--facts` shows exactly what the LLM saw |
| `python -m spendwise chat` | Interactive chat; type `/good` or `/bad` to rate answers |
| `python -m spendwise correct <txn_id> "<Category>"` | Fixes a category (the feedback loop) |
| `python -m spendwise metrics` | AIPM metrics dashboard |
| `python -m pytest -q` | Runs the tests |

Your data is stored in `./.spendwise/` (set `SPENDWISE_HOME` to change it). Nothing leaves your machine unless you set an API key, and even then only aggregated facts are sent, never raw transactions.

---

## Project structure

```
spendwise-ai/
├── spendwise/
│   ├── cli.py            # all CLI commands (argparse)
│   ├── config.py         # paths, categories, thresholds
│   ├── generate_data.py  # synthetic labelled data + realistic bank statement
│   ├── data.py           # CSV loader/normalizer for different bank formats
│   ├── categorizer.py    # CLASSIFICATION + user-correction feedback loop
│   ├── patterns.py       # CLUSTERING + recurring-payment detection
│   ├── anomaly.py        # ANOMALY DETECTION
│   ├── forecast.py       # FORECASTING + backtest MAE
│   ├── budget.py         # recommendations + budget adherence
│   ├── assistant.py      # intent router → analytics tool → LLM/template answer
│   └── metrics.py        # event logging + AIPM metrics
├── tests/test_spendwise.py
├── docs/AIPM_CASE_STUDY.md   # PRD, metrics, ML-vs-LLM decisions, risks, roadmap
└── data/                     # generated CSVs
```

---

# Step-by-step build guide

Build it in this order. Each phase gives you something that works, plus one product decision you can talk about in an interview. Commit to git after every phase, because your commit history is part of the portfolio.

### Phase 0: Frame the problem (½ day, no code)
1. Write a one-page PRD covering the user, the problem, success metrics and non-goals. Use `docs/AIPM_CASE_STUDY.md` as a template.
2. Pick a persona, for example *"Priya, 28, Bengaluru, uses 2 bank accounts + UPI, can't explain why she saved less this month."*
3. Choose a **north-star metric**. Here it's *% of users who take at least one recommended action per month*.
4. Decide what stays out of v1: investments, credit score and multi-currency.

### Phase 1: Set up and get data (½ day)
1. `mkdir spendwise-ai && cd spendwise-ai && git init`, create a virtualenv and install `pandas scikit-learn joblib`.
2. Real bank data is private, so **generate synthetic data** (`generate_data.py`):
   - A labelled training set: merchant names wrapped in realistic UPI/POS/NEFT narrations.
   - A 12-month statement with a known story baked in: a Diwali-month spike in shopping, food delivery and transport, plus 4 planted anomalies. You know the right answers, so you can check the AI against them.
3. Write `data.py` to normalise different bank formats (HDFC-style Debit/Credit, a signed Amount column, `dd/mm/yyyy` dates) into one schema.
4. ▶ `python -m spendwise generate-data`
5. 💡 **PM point:** "Data availability is the first product risk. I designed a synthetic dataset with ground truth so I could evaluate every model before touching real user data."

### Phase 2: Classification, categorizing transactions (1 day)
1. Clean the narrations: strip UPI ids, reference numbers and bank prefixes.
2. Vectorize with character n-grams. They cope with noisy text like `SWIGGY*ORDER`, `Swiggy`, `swiggy12@ybl`.
3. Train Logistic Regression and evaluate on a 20% hold-out (accuracy and F1 per class).
4. Add a **confidence threshold**: below 0.45 the transaction is marked `Uncategorized` instead of guessed.
5. Add the **feedback loop**: `correct` saves a user rule, and `train` retrains with those labels upweighted.
6. ▶ `python -m spendwise train` then `python -m spendwise upload data/sample_bank_statement.csv`
7. 💡 **PM point:** "Precision vs coverage trade-off. A wrong category destroys trust more than 'I'm not sure'. I set the threshold so roughly 1% needs review."

### Phase 3: Spending patterns with clustering (½ day)
1. Turn each week into a vector: category shares, total spend, weekend share and transaction count.
2. Scale the features, run KMeans for k = 2–4 and pick k by **silhouette score**.
3. Name each cluster automatically by its biggest difference from the average week, for example "High-spend weeks, Travel-heavy".
4. Bonus: detect subscriptions, meaning the same merchant in 6 or more months at a near-constant amount.
5. ▶ `python -m spendwise patterns`
6. 💡 **PM point:** the silhouette score is low (~0.14), so these clusters are soft. Be honest that they're *exploratory insight*, not a feature to build automation on.

### Phase 4: Anomaly detection (½ day)
1. Features: log amount, amount ÷ category median, merchant rarity and day of week.
2. Isolation Forest finds the outliers, and a robust z-score (median/MAD) inside each category confirms them. Only transactions both methods agree on get flagged, which keeps alerts rare.
3. Generate a human-readable reason for every flag.
4. ▶ `python -m spendwise anomalies`. Check that the planted ₹48,999 Croma purchase and the ₹2,900 Uber ride are caught.
5. 💡 **PM point:** "Alert fatigue. A 2% contamination rate means about 1–2 alerts a month, which users will actually read."

### Phase 5: Forecasting (½ day)
1. Aggregate to monthly totals and **remove one-off anomalies first**.
2. Compare three models with a rolling-origin backtest: naive, a 3-month moving average and a Ridge trend.
3. Pick the one with the lowest **MAE**. In this data the simple moving average wins, at about 4% error.
4. ▶ `python -m spendwise forecast`
5. 💡 **PM point:** "The simplest model won. I'd ship it and only add complexity (Prophet/ARIMA) if MAE on real users justifies it."

### Phase 6: Budget recommendations (½ day)
1. Baseline = the median of the previous 3 months.
2. Discretionary categories that grew more than 15% → suggest going back to the baseline. Essentials that grew → "check for one-offs". Everything else → a gentle 10% trim.
3. Sanity-check against the 50/30/20 rule using detected salary credits.
4. `--accept` saves the budgets, and the next month's adherence is tracked automatically.
5. ▶ `python -m spendwise budget --accept`
6. 💡 **PM point:** recommendations are **rules, not a black box**, because they must be explainable and must not feel judgmental.

### Phase 7: LLM assistant (1 day)
1. **Intent router**: a regex router maps each question to an intent (expense_change, category_spend, anomalies, forecast, budget, subscriptions, patterns, top_merchants).
2. **Tools**: each intent calls deterministic pandas/ML code and returns a small JSON of facts.
3. **LLM**: Claude gets the question plus the facts, with a system prompt that says *"use ONLY these facts, never invent numbers"*.
4. **Fallback**: with no API key, or if the API errors, a template writes the answer, so the product never breaks.
5. ▶ `python -m spendwise ask "Why did my expenses increase this month?" --facts`
6. 💡 **PM point:** this is the "when to use ML vs GenAI" story. It also keeps costs down, because only about 1 KB of facts goes to the LLM, not thousands of transactions, which is better for privacy too.
7. Stretch: replace the regex router with LLM tool use (function calling) and compare their accuracy on 50 sample questions.

### Phase 8: Metrics and instrumentation (½ day)
1. Every command appends an event to `.spendwise/events.jsonl`.
2. `metrics` computes categorization accuracy, user correction rate, forecast MAE/MAPE, budget adherence, % of recommended actions taken, MAU, active days, questions asked and the helpful rate from `/good` and `/bad`.
3. ▶ `python -m spendwise metrics`

### Phase 9: Quality and portfolio packaging (1 day)
1. `python -m pytest -q`: the tests check accuracy ≥ 90%, that the planted anomalies are found, forecast MAPE < 15% and the intent router.
2. Record a 2-minute terminal demo with [asciinema](https://asciinema.org) or a screen recording.
3. Push to GitHub with this README, the case study and screenshots of the CLI output.
4. Write a LinkedIn/Medium post called *"When to use ML vs an LLM: building a personal-finance AI"*.
5. Try it on **your own** bank CSV export. Real data will break things, and writing up what broke makes a great "learnings" section.

---

## Ideas to extend
- Multiple accounts and users (a `--user` flag, which makes MAU meaningful)
- Category-level forecasts with prediction intervals
- An LLM fallback that classifies low-confidence transactions (cost vs accuracy experiment)
- A Streamlit UI on top of the same modules
- A/B test of the recommendation wording, measuring % of actions taken
