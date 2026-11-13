"""Run with:  python -m pytest -q"""
import os, tempfile
os.environ["SPENDWISE_HOME"] = tempfile.mkdtemp()

import pandas as pd
from spendwise import anomaly, assistant, categorizer, forecast, generate_data
from spendwise.data import load_bank_csv


def setup_module(_):
    global DF
    d = tempfile.mkdtemp()
    tr, st, *_ = generate_data.main(d)
    categorizer.train(tr)
    DF = categorizer.categorize(load_bank_csv(st))


def test_categorization_accuracy_above_target():
    import json
    from spendwise.config import MODEL_REPORT
    assert json.loads(MODEL_REPORT.read_text())["accuracy"] >= 0.90


def test_known_merchants():
    df = pd.DataFrame({"description": ["UPI/123/SWIGGY/x@ybl", "POS 99 UBER INDIA", "NETFLIX 4432"],
                       "direction": ["debit"] * 3})
    assert list(categorizer.categorize(df)["category"]) == ["Food Delivery", "Transport", "Entertainment"]


def test_injected_anomalies_found():
    found = anomaly.detect(DF)["amount"].tolist()
    assert 48999.0 in found and 2900.0 in found


def test_forecast_mae_reasonable():
    f = forecast.forecast_next_month(DF)
    assert f["mape_pct"] < 15


def test_expense_change_question():
    r = assistant.ask(DF, "Why did my expenses increase this month?", use_llm=False)
    assert r["intent"] == "expense_change"
    assert r["facts"]["total_pct"] > 0
    assert "increased" in r["answer"]


def test_intent_router():
    assert assistant.detect_intent("anything unusual?") == "anomalies"
    assert assistant.detect_intent("how much will I spend next month") == "forecast"
    assert assistant.detect_intent("why did my spending go up") == "expense_change"
