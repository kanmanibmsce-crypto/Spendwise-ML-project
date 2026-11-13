"""Budget recommendations + adherence tracking.

Rules (transparent on purpose — users and PMs must be able to explain them):
  * Baseline per category = median of last 3 months (robust to one-off spikes).
  * Discretionary categories that grew >15% vs baseline -> suggest returning to
    baseline, i.e. a cut of (last month - baseline).
  * Discretionary categories otherwise -> suggest a gentle 10% trim.
  * Essentials -> keep baseline.
  * Sanity check against income with the 50/30/20 rule.
"""
import json

import pandas as pd

from .config import BUDGETS_JSON, ESSENTIAL
from .data import expenses, monthly_by_category


def recommend(df: pd.DataFrame) -> dict:
    mbc = monthly_by_category(df)
    last = mbc.iloc[-1]
    base = mbc.iloc[-4:-1].median() if len(mbc) >= 4 else mbc.median()
    recs = []
    for c in mbc.columns:
        if c in ("Uncategorized",):
            continue
        b, l = float(base[c]), float(last[c])
        if c in ESSENTIAL and b > 0 and l > b * 1.15:
            suggested, why = b, f"essential, but up {100*(l/b-1):.0f}% — check for one-offs"
        elif c in ESSENTIAL:
            suggested, why = max(b, l), "essential: keep at your usual level"
        elif b > 0 and l > b * 1.15:
            suggested, why = b, f"up {100*(l/b-1):.0f}% vs your 3-month median — return to normal"
        else:
            suggested, why = max(b, l) * 0.9, "discretionary: 10% trim is usually painless"
        recs.append({"category": c, "last_month": l, "baseline": b, "suggested_budget": round(suggested, -1),
                     "potential_saving": max(0.0, round(l - suggested, -1)), "why": why,
                     "type": "essential" if c in ESSENTIAL else "discretionary"})
    recs.sort(key=lambda r: -r["potential_saving"])
    income = df[df["direction"] == "credit"].assign(month=lambda d: d["date"].dt.to_period("M"))
    monthly_income = float(income.groupby("month")["amount"].sum().median()) if len(income) else None
    last_total = float(last.sum())
    out = {"month": str(mbc.index[-1]), "recommendations": recs, "last_month_total": last_total,
           "total_potential_saving": sum(r["potential_saving"] for r in recs)}
    if monthly_income:
        needs = sum(r["last_month"] for r in recs if r["type"] == "essential")
        wants = sum(r["last_month"] for r in recs if r["type"] == "discretionary")
        out["income"] = monthly_income
        out["rule_50_30_20"] = {
            "needs_pct": 100 * needs / monthly_income, "wants_pct": 100 * wants / monthly_income,
            "savings_pct": 100 * (monthly_income - last_total) / monthly_income,
        }
    return out


def save_budgets(budgets: dict):
    BUDGETS_JSON.write_text(json.dumps(budgets, indent=2))


def load_budgets() -> dict:
    return json.loads(BUDGETS_JSON.read_text()) if BUDGETS_JSON.exists() else {}


def adherence(df: pd.DataFrame, month: str | None = None) -> dict:
    """Budget adherence rate = share of budgeted categories where spend <= budget."""
    budgets = load_budgets()
    if not budgets:
        return {}
    e = expenses(df)
    month = month or str(e["month"].max())
    spent = e[e["month"].astype(str) == month].groupby("category")["amount"].sum()
    rows = [{"category": c, "budget": b, "spent": float(spent.get(c, 0)), "within": float(spent.get(c, 0)) <= b}
            for c, b in budgets.items()]
    rate = sum(r["within"] for r in rows) / len(rows)
    return {"month": month, "rate": rate, "rows": rows}
