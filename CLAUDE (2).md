# CLAUDE.md

Guidance for Claude Code when working in this repository.

## Project
**SpendWise AI**: a personal-finance intelligence assistant that runs from the command line. It reads bank-statement CSVs, categorizes transactions, finds spending patterns, detects anomalies, forecasts next month, suggests budgets and answers questions in natural language.
This is an **AI Product Management portfolio project**. Clarity, explainability and measurable metrics matter more than model complexity.

## Core design principle (do not break)
**Traditional ML / pandas compute every number, and the LLM only explains them.**
- The LLM (`assistant.llm_answer`) receives only the question plus a small JSON of precomputed facts.
- Never let the LLM do arithmetic, classify rows in bulk, or see raw transactions/account numbers.
- Every LLM path must keep a template fallback (`assistant.template_answer`), so the app works with no API key or network.

## Commands
```bash
pip install -r requirements.txt
python -m spendwise demo                      # full pipeline on sample data (regenerates data + model)
python -m spendwise generate-data             # data/training_labeled.csv + data/sample_bank_statement.csv
python -m spendwise train                     # train categorizer, prints accuracy + F1
python -m spendwise upload <file.csv> [--replace]
python -m spendwise transactions [--category X] [--uncategorized] [-n 20]
python -m spendwise summary | patterns | anomalies | forecast
python -m spendwise budget [--accept]
python -m spendwise ask "question" [--facts] [--no-llm]
python -m spendwise chat [--no-llm]           # /facts /good /bad /quit
python -m spendwise correct <txn_id> "<Category>"
python -m spendwise metrics
python -m pytest -q                           # run tests (must pass before finishing any task)
```

## Architecture (`spendwise/`)
| File | Role | ML concept |
|---|---|---|
| `config.py` | Paths (`SPENDWISE_HOME`, default `./.spendwise/`), categories, `ESSENTIAL` set, confidence threshold, `money()` formatter | — |
| `generate_data.py` | Synthetic labelled training data + a 12-month statement with a known story (last month: shopping/food delivery/transport up) and 4 planted anomalies | — |
| `data.py` | Normalizes any bank CSV → `txn_id, date, description, amount (positive), direction (debit/credit)`; store helpers; `monthly_by_category()` | — |
| `categorizer.py` | TF-IDF char n-grams + LogisticRegression; confidence < threshold → `Uncategorized`; user corrections override by `merchant_key()`; credits → `Income` | Classification |
| `patterns.py` | KMeans on weekly spend profiles (k chosen by silhouette); recurring/subscription detection | Clustering |
| `anomaly.py` | IsolationForest + robust z-score (median/MAD) per category; both must agree; human-readable `reason` | Anomaly detection |
| `forecast.py` | naive vs 3-month moving average vs Ridge trend, picked by rolling backtest MAE; anomalies excluded first | Forecasting |
| `budget.py` | Transparent rules: baseline = 3-month median; 50/30/20 check; `adherence()` | Rules |
| `assistant.py` | Regex intent router → analytics "tool" → facts dict → Claude (if `ANTHROPIC_API_KEY`) or template | LLM |
| `metrics.py` | Append-only `events.jsonl`; computes AIPM metrics | — |
| `cli.py` | argparse subcommands; every command calls `metrics.log_event(...)` | — |

Data flow: `upload` → `data.load_bank_csv` → `categorizer.categorize` → `.spendwise/transactions.csv` → every other command reads it via `data.load_store()`.

## Conventions
- Python 3.10+, pandas + scikit-learn only. Don't add heavy dependencies (Prophet, torch, LangChain) without asking.
- Keep models simple and explainable. Any new model must be compared against a simple baseline using a metric (accuracy, MAE, precision).
- Currency is INR (`₹`). Format money only through `config.money()`. Dates are parsed `dayfirst=True` (Indian bank format).
- Expenses = `direction == "debit"`; use `data.expenses()` rather than filtering by hand.
- New CLI command checklist: add `cmd_<name>`, register its subparser in `main()`, log an event, and document it in README.md and here.
- New assistant intent checklist: add a regex to `INTENTS` (order matters, first match wins), a facts function in `run_tool`, a branch in `template_answer`, and a router test in `tests/`.
- Use `random_state=0`/fixed seeds everywhere so demo output is reproducible.
- Output is plain-text CLI (no rich/colour libraries); widths fit ~72–100 columns.

## Metrics (AIPM): keep these computable
Categorization accuracy (hold-out) and user correction rate · Forecast MAE/MAPE · Budget adherence rate · % recommended actions taken (`recommendation_accepted` ÷ `recommendations_shown`) · MAU · active days · questions asked · LLM-answered share · answer helpful rate. If you change a feature, make sure its events still feed `metrics.compute()`.

## Tests and quality gates (`tests/test_spendwise.py`)
- Categorization accuracy ≥ 90%
- Planted anomalies (₹48,999 Croma, ₹2,900 Uber) detected
- Forecast MAPE < 15%
- "Why did my expenses increase this month?" → intent `expense_change`, positive change
- If you change `generate_data.py`, re-run `demo` and the tests; the sample "story" must still hold.

## Privacy and safety
- Never commit `.spendwise/` (user data, models, events) or real bank statements; both are in `.gitignore`.
- Never send raw transactions, account numbers or descriptions in bulk to an external API.
- Budget advice stays non-judgmental ("return to your usual level") and is not investment advice.

## Roadmap / good next tasks
1. Replace the regex intent router with LLM tool use (function calling); compare accuracy on ~50 test questions.
2. LLM fallback for `Uncategorized` rows only (measure cost vs accuracy gain).
3. Multi-user support (`SPENDWISE_USER`) so MAU is meaningful; multi-account merge and transfer de-duplication.
4. Category-level forecasts with prediction intervals.
5. Optional Streamlit UI reusing the same modules.
