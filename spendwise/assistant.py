"""LLM layer — answer questions in natural language.

Design principle (the key AIPM talking point):
    ML / pandas compute the NUMBERS  ->  the LLM only EXPLAINS them.

1. Route the question to an intent (cheap keyword router; could be an LLM call).
2. Run the matching analytics "tool" to get a facts dict (deterministic, testable).
3. If ANTHROPIC_API_KEY is set, Claude turns the facts into a friendly answer and
   is told never to invent numbers. Otherwise a template answer is used, so the
   product still works offline and costs nothing.
"""
import json
import os
import re

import pandas as pd

from . import anomaly, budget, forecast, patterns
from .config import money
from .data import expenses, monthly_by_category

CATEGORY_WORDS = {
    "Food Delivery": ["food delivery", "swiggy", "zomato", "ordering food", "delivery"],
    "Groceries": ["grocer", "blinkit", "zepto", "bigbasket", "instamart"],
    "Dining Out": ["dining", "restaurant", "eating out", "cafe", "coffee"],
    "Transport": ["transport", "uber", "ola", "cab", "fuel", "petrol", "travel to work", "commute"],
    "Shopping": ["shopping", "amazon", "flipkart", "myntra", "clothes"],
    "Bills & Utilities": ["bill", "utilit", "electricity", "internet", "phone", "recharge"],
    "Rent": ["rent"],
    "Entertainment": ["entertainment", "netflix", "movie", "spotify", "ott"],
    "Health": ["health", "medic", "pharma", "doctor", "gym", "fitness"],
    "Travel": ["trip", "flight", "train", "hotel", "vacation", "holiday"],
    "Education": ["education", "course", "learning", "udemy", "books"],
}

INTENTS = [
    ("expense_change", r"why.*(increase|decrease|higher|lower|more|less|change|up|down|jump|rise|rose|drop)|compare|went up|went down|gone up|change|vs last month"),
    ("anomalies", r"unusual|anomal|suspicious|strange|weird|odd|fraud|spike"),
    ("forecast", r"forecast|predict|next month|expect|projection|will i spend"),
    ("budget", r"budget|save|saving|cut|reduce|afford|advice|recommend"),
    ("subscriptions", r"subscription|recurring|every month|auto.?pay"),
    ("patterns", r"pattern|habit|behaviou?r|weekend|cluster"),
    ("top_merchants", r"where.*money|top merchant|most money|biggest|largest|where does"),
    ("category_spend", r"how much|spent on|spend on|spending on"),
]


def detect_intent(q: str) -> str:
    ql = q.lower()
    for name, pat in INTENTS:
        if re.search(pat, ql):
            return name
    return "summary"


def find_category(q: str):
    ql = q.lower()
    for cat, words in CATEGORY_WORDS.items():
        if any(w in ql for w in words):
            return cat
    return None


# ---------- analytics "tools" -> facts ----------

def facts_expense_change(df):
    mbc = monthly_by_category(df)
    cur, prev = mbc.iloc[-1], mbc.iloc[-2]
    delta = (cur - prev).sort_values(ascending=False)
    pct = lambda a, b: (100 * (a / b - 1)) if b else None
    drivers = [{"category": c, "this_month": float(cur[c]), "last_month": float(prev[c]),
                "change": float(delta[c]), "pct": pct(cur[c], prev[c])} for c in delta.index]
    return {"this_month": str(mbc.index[-1]), "last_month": str(mbc.index[-2]),
            "total_this": float(cur.sum()), "total_last": float(prev.sum()),
            "total_pct": pct(cur.sum(), prev.sum()),
            "top_increases": [d for d in drivers if d["change"] > 0][:3],
            "top_decreases": [d for d in drivers[::-1] if d["change"] < 0][:2]}


def facts_category(df, cat):
    mbc = monthly_by_category(df)
    if cat not in mbc:
        return {"category": cat, "found": False}
    s = mbc[cat]
    e = expenses(df)
    e = e[(e["category"] == cat) & (e["month"] == mbc.index[-1])]
    return {"category": cat, "found": True, "month": str(mbc.index[-1]), "this_month": float(s.iloc[-1]),
            "avg_prev_3": float(s.iloc[-4:-1].mean()), "n_txn": len(e),
            "avg_txn": float(e["amount"].mean()) if len(e) else 0}


def facts_top_merchants(df):
    from .categorizer import merchant_key
    e = expenses(df)
    e = e[e["month"] == e["month"].max()]
    top = e.groupby(e["description"].map(merchant_key))["amount"].agg(["sum", "count"]).nlargest(5, "sum")
    by_cat = e.groupby("category")["amount"].sum().nlargest(5)
    return {"month": str(e["month"].max()),
            "top_merchants": [{"merchant": m, "spent": float(r["sum"]), "txns": int(r["count"])} for m, r in top.iterrows()],
            "top_categories": {k: float(v) for k, v in by_cat.items()}}


def facts_anomalies(df):
    a = anomaly.detect(df).head(5)
    return {"count": len(a), "items": [{"date": str(r.date.date()), "description": r.description[:45],
                                        "category": r.category, "amount": float(r.amount), "reason": r.reason}
                                       for r in a.itertuples()]}


def facts_patterns(df):
    prof, sil, feats = patterns.cluster_weeks(df)
    e = expenses(df)
    wk = e[e["date"].dt.dayofweek >= 5]["amount"].sum() / e["amount"].sum()
    return {"clusters": prof, "silhouette": sil, "weekend_share_of_spend": float(wk)}


def run_tool(intent, df, q):
    if intent == "expense_change":
        return facts_expense_change(df)
    if intent == "category_spend":
        return facts_category(df, find_category(q) or "Food Delivery")
    if intent == "top_merchants":
        return facts_top_merchants(df)
    if intent == "anomalies":
        return facts_anomalies(df)
    if intent == "forecast":
        f = forecast.forecast_next_month(df)
        f.pop("history"); f["per_category"] = dict(list(f["per_category"].items())[:5])
        return f
    if intent == "budget":
        b = budget.recommend(df); b["recommendations"] = b["recommendations"][:4]
        return b
    if intent == "subscriptions":
        r = patterns.recurring_merchants(df)
        return {"recurring": [{"merchant": m, "monthly": float(x.avg), "category": x.category}
                              for m, x in r.iterrows()]}
    if intent == "patterns":
        return facts_patterns(df)
    out = facts_expense_change(df)
    out["top_categories"] = facts_top_merchants(df)["top_categories"]
    return out


# ---------- answer generation ----------

def _pct(p):
    return "n/a" if p is None else f"{p:+.0f}%"


def template_answer(intent, f, q):
    if intent in ("expense_change", "summary"):
        up = f["total_pct"] is not None and f["total_pct"] >= 0
        s = (f"Your expenses {'increased' if up else 'decreased'} by {abs(f['total_pct']):.0f}% in {f['this_month']} "
             f"compared with {f['last_month']} ({money(f['total_last'])} → {money(f['total_this'])}).")
        items = f["top_increases"] if up else f["top_decreases"]
        if items:
            names = [d["category"].lower() for d in items]
            s += f" The main contributors were {', '.join(names[:-1]) + ' and ' + names[-1] if len(names) > 1 else names[0]}."
            d = items[0]
            s += f" {d['category']} spending {'increased' if d['change'] > 0 else 'decreased'} by {abs(d['pct'] or 0):.0f}% ({money(d['last_month'])} → {money(d['this_month'])})."
        return s
    if intent == "category_spend":
        if not f["found"]:
            return f"I couldn't find any {f['category']} spending."
        diff = 100 * (f["this_month"] / f["avg_prev_3"] - 1) if f["avg_prev_3"] else 0
        return (f"In {f['month']} you spent {money(f['this_month'])} on {f['category']} across {f['n_txn']} transactions "
                f"(avg {money(f['avg_txn'])} each). That is {diff:+.0f}% vs your previous 3-month average of {money(f['avg_prev_3'])}.")
    if intent == "top_merchants":
        ms = "; ".join(f"{m['merchant']} {money(m['spent'])} ({m['txns']}x)" for m in f["top_merchants"][:3])
        return f"In {f['month']} most of your money went to: {ms}."
    if intent == "anomalies":
        if not f["count"]:
            return "Nothing unusual stood out."
        lines = [f"- {i['date']}: {money(i['amount'])} at {i['description']} ({i['reason']})" for i in f["items"]]
        return f"I found {f['count']} unusual transaction(s):\n" + "\n".join(lines)
    if intent == "forecast":
        cats = ", ".join(f"{c} {money(v)}" for c, v in list(f["per_category"].items())[:3])
        return (f"I expect you to spend about {money(f['forecast_total'])} in {f['next_month']} "
                f"(last month: {money(f['last_month_total'])}). Biggest buckets: {cats}. "
                f"Typical error of this model is ±{money(f['mae'])} ({f['mape_pct']:.0f}%).")
    if intent == "budget":
        r = [x for x in f["recommendations"] if x["potential_saving"] > 0][:3]
        lines = [f"- {x['category']}: budget {money(x['suggested_budget'])} (save ~{money(x['potential_saving'])}; {x['why']})" for x in r]
        return f"You could save about {money(f['total_potential_saving'])}/month:\n" + "\n".join(lines)
    if intent == "subscriptions":
        if not f["recurring"]:
            return "I didn't find any recurring fixed-amount payments."
        return "Recurring payments: " + "; ".join(f"{r['merchant']} ~{money(r['monthly'])}" for r in f["recurring"])
    if intent == "patterns":
        c = f["clusters"][0]
        return (f"Your weeks fall into {len(f['clusters'])} spending modes. The costliest is '{c['label']}' "
                f"(~{money(c['avg_weekly_spend'])}/week, {c['weeks']} weeks, {c['recent_weeks']} of the last 4). "
                f"{100*f['weekend_share_of_spend']:.0f}% of your spending happens on weekends.")
    return json.dumps(f, default=str)[:600]


SYSTEM = """You are SpendWise AI, a friendly personal-finance assistant for an Indian user (currency ₹).
Answer the user's question using ONLY the JSON facts provided. Never invent or recompute numbers;
round to whole rupees and whole percentages. Be concise (2-5 sentences), lead with the direct answer,
then the main reasons, then at most one practical suggestion. If the facts can't answer the question, say so."""


def llm_answer(q, intent, facts):
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        return None
    try:
        import anthropic
    except ImportError:
        return None
    client = anthropic.Anthropic()
    msg = client.messages.create(
        model=os.environ.get("SPENDWISE_MODEL", "claude-sonnet-4-6"),
        max_tokens=400, system=SYSTEM,
        messages=[{"role": "user", "content": f"Question: {q}\nIntent: {intent}\nFacts:\n{json.dumps(facts, default=str, indent=1)}"}],
    )
    return msg.content[0].text.strip()


def ask(df: pd.DataFrame, q: str, use_llm=True):
    intent = detect_intent(q)
    facts = run_tool(intent, df, q)
    ans = None
    if use_llm:
        try:
            ans = llm_answer(q, intent, facts)
        except Exception as ex:  # network/API errors -> fall back gracefully
            ans = None
            print(f"(LLM unavailable: {ex.__class__.__name__}; using template answer)")
    return {"intent": intent, "facts": facts, "answer": ans or template_answer(intent, facts, q),
            "engine": "llm" if ans else "template"}
