# SpendWise AI: AIPM case study

## 1. Problem
People pay through several bank accounts, UPI apps and cards. Statements are long lists of cryptic narrations (`UPI/4432/SWIGGY/swiggy12@ybl`), so nobody can answer simple questions like *"Why did I save less this month?"*

**Target user:** a salaried urban professional aged 24–35 who uses UPI daily and has never kept a budget.

**Jobs to be done**
1. "Show me where my money goes without me tagging anything."
2. "Tell me when something is off."
3. "Tell me what I'll spend next month and where I can cut."
4. "Let me just ask."

## 2. Solution overview
Upload a CSV → auto-categorize → insights (patterns, anomalies, forecast, budget) → natural-language Q&A.

## 3. ML vs LLM: the decisions

| Capability | Chosen approach | Alternative considered | Why |
|---|---|---|---|
| Categorization | Logistic Regression on char n-grams | An LLM classifies each row | ~1000x cheaper, under 1 ms per row, deterministic, has a measurable accuracy. An LLM is a possible fallback for low-confidence rows only |
| Behaviour | KMeans on weekly profiles | Asking an LLM to "describe habits" | Needs numeric grouping; an LLM can't reliably cluster numbers |
| Anomalies | Isolation Forest + robust z | Fixed thresholds | Adapts to each user's own normal |
| Forecast | Best of naive / moving average / Ridge by backtested MAE | LLM prediction, Prophet | LLMs hallucinate numbers; Prophet is overkill for 12 data points |
| Explanation | LLM over computed facts | Templates only | Templates are rigid; an LLM handles varied phrasing and tone |

**Principle:** use ML where the output is a number or a label that can be measured, and GenAI where the output is language.

## 4. Metrics framework

| Layer | Metric | Target (v1) | How measured in this build |
|---|---|---|---|
| North star | % of users taking at least 1 recommended action per month | 25% | `recommendation_accepted` ÷ `recommendations_shown` events |
| Model | Transaction categorization accuracy | ≥ 95% | Hold-out test set; online proxy = user correction rate |
| Model | Forecast error (MAE / MAPE) | MAPE ≤ 10% | Rolling-origin backtest |
| Model | Anomaly precision | ≥ 70% of alerts confirmed | Future: "was this you?" feedback |
| Outcome | Budget adherence rate | ≥ 60% of categories within budget | `budget.adherence()` |
| Engagement | Monthly active users | Grow | Unique `user_id` in events over 30 days |
| Engagement | Questions per active user, helpful rate | ≥ 80% helpful | `question_asked`, `/good` and `/bad` |
| Guardrail | Hallucinated-number rate | 0 | LLM only gets facts JSON; spot-check numbers in answers against the facts |
| Guardrail | LLM cost per MAU | < ₹5 | Only aggregated facts are sent (~1 KB) |

## 5. Risks and mitigations
- **Privacy:** financial data is sensitive. Processing is local by default, and the LLM gets aggregates only, with no account numbers.
- **Wrong categories erode trust:** a confidence threshold sends unsure rows to "Uncategorized", and corrections make a one-tap feedback loop.
- **Alert fatigue:** a two-detector agreement keeps alerts to about 1–2 per month.
- **Judgmental tone:** advice is framed as "return to your normal", not "you overspent".
- **Not financial advice:** a disclaimer in the product, and no investment recommendations.

## 6. Results on the sample dataset
- Categorization accuracy: **97.5%** (hold-out); 99.9% of rows auto-categorized
- Forecast MAPE: **~4%** (moving average beat both the trend model and the naive one)
- Anomalies: all big planted one-offs caught (₹48,999 electronics, ₹3,850 party order, ₹2,900 airport cab), with 1–2 borderline extra flags
- Q&A: correctly explains the +23% month with shopping, transport and food delivery as the drivers

## 7. Roadmap
1. **v1.1:** LLM tool use instead of the regex router; LLM fallback for uncategorized rows
2. **v1.2:** Multi-account merge and transfer de-duplication
3. **v2:** Account Aggregator (India) integration instead of CSV upload; mobile UI
4. **Experiments:** recommendation wording A/B test; proactive weekly digest vs on-demand chat
