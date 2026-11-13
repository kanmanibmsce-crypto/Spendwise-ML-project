"""ML concept: CLUSTERING — discover spending behaviour.

Each WEEK becomes a vector: total spend, share of each category, weekend share,
number of transactions. KMeans groups similar weeks; k is chosen by silhouette
score. Each cluster is then described in plain words ("Heavy food-delivery weeks").
"""
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler

from .data import expenses


def weekly_features(df: pd.DataFrame) -> pd.DataFrame:
    from .anomaly import detect
    e = expenses(df)
    # fixed costs and one-off anomalies hide day-to-day behaviour
    e = e[~e["category"].isin(["Rent", "Bills & Utilities", "Uncategorized"])]
    e = e[~e["txn_id"].isin(detect(df)["txn_id"])]
    e["week"] = e["date"].dt.to_period("W")
    e["weekend"] = e["date"].dt.dayofweek >= 5
    share = e.pivot_table(index="week", columns="category", values="amount", aggfunc="sum", fill_value=0)
    total = share.sum(1)
    share = share.div(total, axis=0).add_prefix("share_")
    feats = share.assign(
        total=total,
        n_txn=e.groupby("week").size(),
        weekend_share=e[e["weekend"]].groupby("week")["amount"].sum().reindex(share.index, fill_value=0) / total,
    )
    return feats.fillna(0)


def cluster_weeks(df: pd.DataFrame, k_range=range(2, 5)):
    feats = weekly_features(df)
    X = StandardScaler().fit_transform(feats)
    best = None
    for k in k_range:
        if k >= len(feats):
            break
        km = KMeans(n_clusters=k, n_init=10, random_state=0).fit(X)
        s = silhouette_score(X, km.labels_)
        if best is None or s > best[1]:
            best = (km, s, k)
    km, sil, k = best
    feats["cluster"] = km.labels_
    profiles = []
    overall = feats.drop(columns="cluster").mean()
    for c, g in feats.groupby("cluster"):
        m = g.drop(columns="cluster").mean()
        share_cols = [col for col in m.index if col.startswith("share_")]
        lift = (m[share_cols] - overall[share_cols]).sort_values(ascending=False)
        top = lift.index[0].replace("share_", "")
        level = "High-spend" if m["total"] > overall["total"] * 1.15 else (
            "Low-spend" if m["total"] < overall["total"] * 0.85 else "Typical")
        profiles.append({
            "cluster": int(c),
            "label": f"{level} weeks, {top}-heavy",
            "weeks": len(g),
            "avg_weekly_spend": float(m["total"]),
            "top_category_share": float(m["share_" + top]),
            "weekend_share": float(m["weekend_share"]),
            "recent_weeks": int((g.index >= feats.index[-4]).sum()),
        })
    return sorted(profiles, key=lambda p: -p["avg_weekly_spend"]), round(float(sil), 3), feats


def recurring_merchants(df: pd.DataFrame, min_months=6) -> pd.DataFrame:
    """Subscriptions / recurring payments: same merchant seen in many months."""
    from .categorizer import merchant_key
    e = expenses(df)
    e["merchant"] = e["description"].map(merchant_key)
    g = e.groupby("merchant").agg(months=("month", "nunique"), avg=("amount", "mean"),
                                  std=("amount", "std"), category=("category", "first"))
    g = g[(g["months"] >= min_months) & (g["std"].fillna(0) / g["avg"] < 0.08)]
    return g.sort_values("avg", ascending=False)
