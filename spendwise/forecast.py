"""ML concept: REGRESSION / TIME-SERIES FORECASTING — predict next month's spend.

We compare simple, explainable models with a rolling-origin backtest and pick
the one with the lowest MAE (Mean Absolute Error) — the AIPM metric.

  * naive          : next month = last month
  * moving_avg_3   : mean of last 3 months
  * linear_trend   : Ridge regression on [month index, last month, 3-mo avg]

Large one-off anomalies are capped before fitting so one big purchase does not
distort the forecast.
"""
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge

from .data import monthly_by_category


def _cap(s: pd.Series) -> pd.Series:
    med = s.median()
    return s.clip(upper=med * 2.0) if med > 0 else s


def _predict(model: str, hist: np.ndarray) -> float:
    if model == "naive":
        return hist[-1]
    if model == "moving_avg_3":
        return hist[-3:].mean()
    # linear_trend with lag features
    if len(hist) < 5:
        return hist[-3:].mean()
    rows, ys = [], []
    for t in range(3, len(hist)):
        rows.append([t, hist[t - 3:t].mean()])
        ys.append(hist[t])
    scale = hist.mean() or 1
    m = Ridge(alpha=1.0).fit(np.array(rows) / [1, scale], np.array(ys) / scale)
    t = len(hist)
    return float(m.predict([[t, hist[-3:].mean() / scale]])[0] * scale)


MODELS = ["naive", "moving_avg_3", "linear_trend"]


def backtest(series: pd.Series, min_train=6) -> dict:
    vals = _cap(series).values.astype(float)
    errs = {m: [] for m in MODELS}
    for cut in range(min_train, len(vals)):
        for m in MODELS:
            errs[m].append(abs(_predict(m, vals[:cut]) - series.values[cut]))
    return {m: float(np.mean(e)) if e else float("nan") for m, e in errs.items()}


def forecast_next_month(df: pd.DataFrame) -> dict:
    from .anomaly import detect
    one_offs = detect(df)  # don't let a one-time ₹49k purchase drive next month's forecast
    df = df[~df["txn_id"].isin(one_offs["txn_id"])]
    df = df[df["category"] != "Uncategorized"]
    mbc = monthly_by_category(df)
    total = mbc.sum(axis=1)
    scores = backtest(total)
    best = min(scores, key=scores.get)
    next_total = _predict(best, _cap(total).values.astype(float))
    per_cat = {}
    for c in mbc.columns:
        per_cat[c] = max(0.0, _predict("moving_avg_3" if best == "naive" else best,
                                       _cap(mbc[c]).values.astype(float)))
    # scale category forecasts to agree with the total
    s = sum(per_cat.values()) or 1
    per_cat = {c: v * next_total / s for c, v in per_cat.items()}
    return {
        "next_month": str(total.index[-1] + 1),
        "forecast_total": next_total,
        "model": best,
        "backtest_mae": scores,
        "mae": scores[best],
        "mape_pct": 100 * scores[best] / total.mean(),
        "last_month_total": float(total.iloc[-1]),
        "excluded_one_offs": int(len(one_offs)),
        "per_category": dict(sorted(per_cat.items(), key=lambda kv: -kv[1])),
        "history": {str(k): float(v) for k, v in total.items()},
    }
