"""ML concept: ANOMALY DETECTION — flag unusual expenses.

Two complementary detectors:
 1. Isolation Forest on [log amount, amount vs category median, merchant rarity,
    day-of-week] — catches multivariate oddities.
 2. Robust z-score within the category (median/MAD) — gives a human-readable reason.
A transaction is flagged when the Isolation Forest says so AND it is meaningfully
large for its category (keeps false alarms low: users ignore noisy alerts).
"""
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

from .categorizer import merchant_key
from .data import expenses


def detect(df: pd.DataFrame, contamination=0.02, min_robust_z=3.0) -> pd.DataFrame:
    e = expenses(df).copy()
    e["merchant"] = e["description"].map(merchant_key)
    med = e.groupby("category")["amount"].transform("median")
    mad = e.groupby("category")["amount"].transform(lambda s: (s - s.median()).abs().median()) + 1e-6
    e["robust_z"] = 0.6745 * (e["amount"] - med) / mad
    e["x_median"] = e["amount"] / med
    freq = e["merchant"].map(e["merchant"].value_counts())
    X = np.column_stack([
        np.log1p(e["amount"]), np.log1p(e["x_median"]), 1 / freq, e["date"].dt.day_of_week,
    ])
    iso = IsolationForest(n_estimators=300, contamination=contamination, random_state=0).fit(X)
    e["iso_score"] = -iso.score_samples(X)
    e["iso_flag"] = iso.predict(X) == -1
    e["is_anomaly"] = e["iso_flag"] & ((e["robust_z"] > min_robust_z) | (freq == 1) & (e["amount"] > med * 3))

    def reason(r):
        bits = []
        if r.x_median >= 2:
            bits.append(f"{r.x_median:.1f}x your typical {r.category} spend")
        if freq[r.Index] == 1:
            bits.append("first time at this merchant")
        if r.category == "Uncategorized":
            bits.append("could not be categorised")
        return "; ".join(bits) or "unusual combination of amount/merchant/day"

    out = e[e["is_anomaly"]].copy()
    out["reason"] = [reason(r) for r in out.itertuples()]
    return out.sort_values("iso_score", ascending=False)[
        ["txn_id", "date", "description", "category", "amount", "reason", "iso_score"]]
