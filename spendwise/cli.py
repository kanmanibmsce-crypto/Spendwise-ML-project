"""SpendWise AI command-line interface.

    python -m spendwise demo                 # run the whole pipeline on sample data
    python -m spendwise generate-data
    python -m spendwise train [--data data/training_labeled.csv]
    python -m spendwise upload <bank.csv>
    python -m spendwise transactions [--category X] [--uncategorized] [-n 20]
    python -m spendwise summary
    python -m spendwise patterns
    python -m spendwise anomalies
    python -m spendwise forecast
    python -m spendwise budget [--accept]
    python -m spendwise ask "Why did my expenses increase this month?"
    python -m spendwise chat
    python -m spendwise correct <txn_id> "<Category>"
    python -m spendwise metrics
"""
import argparse
import sys

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import pandas as pd

from . import anomaly, assistant, budget, categorizer, forecast, generate_data, metrics, patterns
from .config import CATEGORIES, STORE_CSV, money
from .data import expenses, load_bank_csv, load_document, load_store, monthly_by_category, save_store

W = 72


def h(title):
    print("\n" + "=" * W + f"\n {title}\n" + "=" * W)


def bar(v, vmax, width=28):
    return "█" * int(round(width * v / vmax)) if vmax else ""


# ---------------- commands ----------------

def cmd_generate(a):
    tr, st, n1, n2 = generate_data.main(a.out)
    print(f"✓ Training data : {tr} ({n1} labelled rows)\n✓ Bank statement: {st} ({n2} rows)")


def cmd_train(a):
    h("Training transaction classifier (TF-IDF char n-grams + Logistic Regression)")
    r = categorizer.train(a.data)
    print(f"Train rows: {r['n_train']}   Test rows: {r['n_test']}")
    print(f"Hold-out accuracy: {r['accuracy']:.1%}   ← AIPM metric: categorization accuracy")
    print("\nF1 per category:")
    for c, f1 in sorted(r["per_class"].items(), key=lambda kv: kv[1]):
        print(f"  {c:<18} {f1:.3f} {bar(f1, 1, 20)}")
    metrics.log_event("model_trained", accuracy=r["accuracy"])


def cmd_upload(a):
    df = load_document(a.file)
    df = categorizer.categorize(df)
    all_df = save_store(df, append=not a.replace)
    deb = df[df.direction == "debit"]
    h(f"Uploaded {a.file}")
    print(f"Rows parsed       : {len(df)}  ({len(deb)} expenses, {len(df) - len(deb)} credits)")
    print(f"Date range        : {df.date.min().date()} → {df.date.max().date()}")
    print(f"Auto-categorized  : {(deb.category != 'Uncategorized').mean():.1%} of expenses "
          f"(avg confidence {deb.confidence.mean():.2f})")
    print(f"Needs review      : {(deb.category == 'Uncategorized').sum()} transactions "
          f"→ `spendwise transactions --uncategorized`")
    print(f"Total stored      : {len(all_df)} transactions in {STORE_CSV}")
    metrics.log_event("csv_uploaded", rows=len(df))


def cmd_transactions(a):
    df = load_store()
    if a.category:
        df = df[df.category.str.lower() == a.category.lower()]
    if a.uncategorized:
        df = df[df.category == "Uncategorized"]
    out = df.tail(a.n)[["txn_id", "date", "description", "amount", "direction", "category", "confidence"]].copy()
    out["date"] = out["date"].dt.date
    out["description"] = out["description"].str[:38]
    print(out.to_string(index=False))
    metrics.log_event("transactions_viewed")


def cmd_summary(a):
    df = load_store()
    mbc = monthly_by_category(df)
    h("Monthly spending by category (last 6 months)")
    t = mbc.tail(6).T
    t["avg"] = mbc.mean()
    print(t.round(0).astype(int).sort_values("avg", ascending=False).to_string())
    totals = mbc.sum(1)
    h("Monthly total expenses")
    for mth, v in totals.items():
        print(f"  {mth}  {money(v):>10}  {bar(v, totals.max())}")
    metrics.log_event("summary_viewed")


def cmd_patterns(a):
    df = load_store()
    prof, sil, feats = patterns.cluster_weeks(df)
    h(f"Spending behaviour clusters (KMeans on weekly profiles, k={len(prof)}, silhouette={sil})")
    for p in prof:
        print(f"• {p['label']:<38} {p['weeks']:>2} weeks | avg {money(p['avg_weekly_spend'])}/wk | "
              f"weekend {p['weekend_share']:.0%} | last 4 wks: {p['recent_weeks']}")
    rec = patterns.recurring_merchants(df)
    h("Recurring payments / subscriptions")
    if len(rec):
        for m, r in rec.iterrows():
            print(f"  {m:<24} {money(r.avg):>9}/mo  seen {r.months} months  [{r.category}]")
    else:
        print("  none detected")
    e = expenses(df)
    dow = e.groupby(e.date.dt.day_name())["amount"].sum()
    h("Spend by weekday")
    for d in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]:
        print(f"  {d:<10} {money(dow.get(d, 0)):>10} {bar(dow.get(d, 0), dow.max())}")
    metrics.log_event("patterns_viewed", k=len(prof))


def cmd_anomalies(a):
    df = load_store()
    an = anomaly.detect(df, contamination=a.contamination)
    h(f"Unusual expenses (Isolation Forest + robust z-score) — {len(an)} found")
    for r in an.itertuples():
        print(f"⚠ {r.date.date()}  {money(r.amount):>9}  {r.description[:34]:<34} [{r.category}]\n    ↳ {r.reason}")
    metrics.log_event("anomalies_viewed", n=len(an))


def cmd_forecast(a):
    df = load_store()
    f = forecast.forecast_next_month(df)
    h(f"Forecast for {f['next_month']}")
    print(f"Predicted total : {money(f['forecast_total'])}   (last month {money(f['last_month_total'])})")
    print(f"Model chosen    : {f['model']}  (lowest backtest MAE)")
    print("Backtest MAE    : " + " | ".join(f"{m} {money(v)}" for m, v in f["backtest_mae"].items()))
    print(f"Forecast error  : MAE {money(f['mae'])}  ≈ {f['mape_pct']:.1f}% of an average month  ← AIPM metric")
    print("\nBy category:")
    mx = max(f["per_category"].values())
    for c, v in f["per_category"].items():
        print(f"  {c:<18} {money(v):>9} {bar(v, mx, 20)}")
    metrics.log_event("forecast_viewed", mae=f["mae"], mape_pct=f["mape_pct"])


def cmd_budget(a):
    df = load_store()
    b = budget.recommend(df)
    h(f"Budget suggestions based on {b['month']}")
    print(f"{'Category':<18}{'Last mo':>10}{'Usual':>10}{'Suggest':>10}{'Save':>9}  Why")
    for r in b["recommendations"]:
        print(f"{r['category']:<18}{money(r['last_month']):>10}{money(r['baseline']):>10}"
              f"{money(r['suggested_budget']):>10}{money(r['potential_saving']):>9}  {r['why']}")
    print(f"\nPotential monthly saving: {money(b['total_potential_saving'])}")
    if "rule_50_30_20" in b:
        r = b["rule_50_30_20"]
        print(f"50/30/20 check (income {money(b['income'])}): needs {r['needs_pct']:.0f}% | "
              f"wants {r['wants_pct']:.0f}% | savings {r['savings_pct']:.0f}%  (target 50/30/20)")
    actionable = [r for r in b["recommendations"] if r["potential_saving"] > 0]
    metrics.log_event("recommendations_shown", n=len(actionable))
    adh = budget.adherence(df)
    if adh:
        print(f"\nBudget adherence for {adh['month']}: {adh['rate']:.0%} of budgeted categories on track")
    if a.accept:
        chosen = {r["category"]: r["suggested_budget"] for r in b["recommendations"]}
        budget.save_budgets(chosen)
        metrics.log_event("recommendation_accepted", n=len(actionable))
        print("✓ Budgets saved. `spendwise budget` will now report adherence.")
    else:
        print("\nRun `spendwise budget --accept` to adopt these budgets.")


def _print_answer(res, show_facts=False):
    print(f"\n🤖 {res['answer']}\n")
    print(f"   [intent: {res['intent']} | engine: {res['engine']}]")
    if show_facts:
        import json
        print(json.dumps(res["facts"], indent=1, default=str)[:2500])


def cmd_ask(a):
    df = load_store()
    q = " ".join(a.question)
    res = assistant.ask(df, q, use_llm=not a.no_llm)
    _print_answer(res, a.facts)
    metrics.log_event("question_asked", intent=res["intent"], engine=res["engine"])


def cmd_chat(a):
    df = load_store()
    print("SpendWise AI chat — ask about your money. Commands: /facts, /good, /bad, /quit")
    print("Try: why did my expenses increase this month? | how much on food delivery? | anything unusual?")
    last, show = None, False
    while True:
        try:
            q = input("\nyou › ").strip()
        except (EOFError, KeyboardInterrupt):
            print(); break
        if not q:
            continue
        if q in ("/quit", "/exit", "quit", "exit"):
            break
        if q == "/facts":
            show = not show; print(f"show facts: {show}"); continue
        if q in ("/good", "/bad") and last:
            metrics.log_event("answer_feedback", intent=last["intent"], helpful=int(q == "/good"))
            print("thanks for the feedback!"); continue
        last = assistant.ask(df, q, use_llm=not a.no_llm)
        _print_answer(last, show)
        metrics.log_event("question_asked", intent=last["intent"], engine=last["engine"])


def cmd_correct(a):
    df = load_store()
    if a.category not in CATEGORIES:
        sys.exit(f"Category must be one of: {', '.join(CATEGORIES)}")
    row = df[df.txn_id == a.txn_id]
    if row.empty:
        sys.exit("txn_id not found (see `spendwise transactions`)")
    r = row.iloc[0]
    categorizer.add_correction(r.description, a.category, r.category)
    df = categorizer.categorize(df.drop(columns=["category", "confidence", "source"]))
    save_store(df, append=False)
    print(f"✓ '{r.description[:40]}' {r.category} → {a.category}. Rule applied to similar merchants; "
          f"run `spendwise train` to retrain with your feedback.")
    metrics.log_event("category_corrected", old=r.category, new=a.category)


def cmd_metrics(a):
    try:
        df = load_store()
    except SystemExit:
        df = None
    if df is not None:
        adh = budget.adherence(df)
    m = metrics.compute(df)
    h("AIPM metrics dashboard")
    pct = lambda x: f"{x:.1%}"
    rows = [
        ("Model quality", "Categorization accuracy (hold-out)", m.get("categorization_accuracy_offline"), pct),
        ("Model quality", "User correction rate (online proxy)", m.get("user_correction_rate"), pct),
        ("Model quality", "Uncategorized rate", m.get("uncategorized_rate"), pct),
        ("Model quality", "Forecast MAE", m.get("forecast_mae"), money),
        ("Model quality", "Forecast MAPE", m.get("forecast_mape_pct"), lambda x: f"{x:.1f}%"),
        ("Outcome", "Budget adherence rate", adh.get("rate") if df is not None and adh else None, pct),
        ("Outcome", "% recommended actions taken", m.get("pct_recommended_actions_taken"), pct),
        ("Engagement", "Monthly active users", m.get("monthly_active_users"), str),
        ("Engagement", "Active days (30d)", m.get("active_days_30d"), str),
        ("Engagement", "Questions asked", m.get("questions_asked"), str),
        ("Engagement", "LLM-answered share", m.get("llm_answer_share"), pct),
        ("Engagement", "Answer helpful rate (/good vs /bad)", m.get("answer_helpful_rate"), pct),
    ]
    for grp, name, v, fmt in rows:
        print(f"{grp:<14}{name:<40}{fmt(v) if v is not None else '—':>12}")
    if m.get("feature_usage"):
        print("\nFeature usage (events):")
        for k, v in m["feature_usage"].items():
            print(f"  {k:<26}{v:>5}")


def cmd_demo(a):
    from types import SimpleNamespace as NS
    cmd_generate(NS(out="data"))
    cmd_train(NS(data="data/training_labeled.csv"))
    cmd_upload(NS(file="data/sample_bank_statement.csv", replace=True))
    cmd_summary(NS())
    cmd_patterns(NS())
    cmd_anomalies(NS(contamination=0.02))
    cmd_forecast(NS())
    cmd_budget(NS(accept=False))
    for q in ["Why did my expenses increase this month?", "How much did I spend on food delivery?",
              "Anything unusual in my spending?", "How much will I spend next month?"]:
        h(f"you › {q}")
        cmd_ask(NS(question=[q], no_llm=False, facts=False))
    cmd_metrics(NS())


def main(argv=None):
    p = argparse.ArgumentParser(prog="spendwise", description="SpendWise AI – Personal Finance Intelligence Assistant")
    s = p.add_subparsers(dest="cmd", required=True)
    s.add_parser("demo", help="run full pipeline on sample data").set_defaults(fn=cmd_demo)
    g = s.add_parser("generate-data", help="create synthetic training + statement CSVs")
    g.add_argument("--out", default="data"); g.set_defaults(fn=cmd_generate)
    t = s.add_parser("train", help="train the transaction classifier")
    t.add_argument("--data", default="data/training_labeled.csv"); t.set_defaults(fn=cmd_train)
    u = s.add_parser("upload", help="import + categorize a bank CSV")
    u.add_argument("file"); u.add_argument("--replace", action="store_true", help="replace instead of append")
    u.set_defaults(fn=cmd_upload)
    tx = s.add_parser("transactions", help="list transactions")
    tx.add_argument("--category"); tx.add_argument("--uncategorized", action="store_true")
    tx.add_argument("-n", type=int, default=20); tx.set_defaults(fn=cmd_transactions)
    s.add_parser("summary", help="monthly spend by category").set_defaults(fn=cmd_summary)
    s.add_parser("patterns", help="clustering of spending behaviour").set_defaults(fn=cmd_patterns)
    an = s.add_parser("anomalies", help="detect unusual expenses")
    an.add_argument("--contamination", type=float, default=0.02); an.set_defaults(fn=cmd_anomalies)
    s.add_parser("forecast", help="forecast next month").set_defaults(fn=cmd_forecast)
    b = s.add_parser("budget", help="budget suggestions"); b.add_argument("--accept", action="store_true")
    b.set_defaults(fn=cmd_budget)
    q = s.add_parser("ask", help="ask a question in natural language")
    q.add_argument("question", nargs="+"); q.add_argument("--no-llm", action="store_true")
    q.add_argument("--facts", action="store_true", help="show the computed facts sent to the LLM")
    q.set_defaults(fn=cmd_ask)
    c = s.add_parser("chat", help="interactive assistant"); c.add_argument("--no-llm", action="store_true")
    c.set_defaults(fn=cmd_chat)
    co = s.add_parser("correct", help="fix a transaction's category (feedback loop)")
    co.add_argument("txn_id"); co.add_argument("category"); co.set_defaults(fn=cmd_correct)
    s.add_parser("metrics", help="AIPM metrics dashboard").set_defaults(fn=cmd_metrics)
    a = p.parse_args(argv)
    pd.set_option("display.width", 160)
    a.fn(a)


if __name__ == "__main__":
    main()
