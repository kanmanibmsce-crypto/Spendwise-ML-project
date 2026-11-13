"""AIPM metrics — product analytics from an append-only event log.

Every CLI command logs an event. `spendwise metrics` turns the log into the
metrics a PM would put on a dashboard:
  model quality : categorization accuracy (offline) + correction rate (online), forecast MAE
  outcome       : budget adherence rate, % users taking recommended actions
  engagement    : MAU, active days, questions asked, feature usage
"""
import json
from datetime import datetime, timedelta

import pandas as pd

from .config import CORRECTIONS_CSV, EVENTS_LOG, MODEL_REPORT, USER_ID


def log_event(name: str, **props):
    e = {"ts": datetime.now().isoformat(timespec="seconds"), "user_id": USER_ID, "event": name, **props}
    with open(EVENTS_LOG, "a") as f:
        f.write(json.dumps(e, default=str) + "\n")


def load_events() -> pd.DataFrame:
    if not EVENTS_LOG.exists():
        return pd.DataFrame(columns=["ts", "user_id", "event"])
    df = pd.read_json(EVENTS_LOG, lines=True)
    df["ts"] = pd.to_datetime(df["ts"])
    return df


def compute(df_txn=None) -> dict:
    ev = load_events()
    now = datetime.now()
    m = {}
    if MODEL_REPORT.exists():
        m["categorization_accuracy_offline"] = json.loads(MODEL_REPORT.read_text())["accuracy"]
    if df_txn is not None:
        n = int((df_txn["direction"] == "debit").sum())
        n_corr = len(pd.read_csv(CORRECTIONS_CSV)) if CORRECTIONS_CSV.exists() else 0
        m["user_correction_rate"] = n_corr / n if n else 0
        m["uncategorized_rate"] = float((df_txn["category"] == "Uncategorized").mean())
    if len(ev):
        recent = ev[ev["ts"] >= now - timedelta(days=30)]
        m["monthly_active_users"] = int(recent["user_id"].nunique())
        m["active_days_30d"] = int(recent["ts"].dt.date.nunique())
        m["questions_asked"] = int((ev["event"] == "question_asked").sum())
        m["feature_usage"] = ev["event"].value_counts().to_dict()
        shown = int(ev.loc[ev["event"] == "recommendations_shown", "n"].sum()) if "n" in ev else 0
        acted = int(ev.loc[ev["event"] == "recommendation_accepted", "n"].sum()) if "n" in ev else 0
        m["recommendations_shown"] = shown
        m["recommendations_accepted"] = acted
        m["pct_recommended_actions_taken"] = acted / shown if shown else 0
        fc = ev[ev["event"] == "forecast_viewed"]
        if len(fc) and "mae" in fc:
            m["forecast_mae"] = float(fc["mae"].iloc[-1])
            m["forecast_mape_pct"] = float(fc["mape_pct"].iloc[-1])
        q = ev[ev["event"] == "question_asked"]
        if len(q) and "engine" in q:
            m["llm_answer_share"] = float((q["engine"] == "llm").mean())
        fb = ev[ev["event"] == "answer_feedback"]
        if len(fb):
            m["answer_helpful_rate"] = float(fb["helpful"].mean())
    return m
