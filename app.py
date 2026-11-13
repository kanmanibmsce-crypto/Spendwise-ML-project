"""SpendWise AI — Streamlit web UI.

Reuses all existing spendwise modules unchanged.
Run: streamlit run app.py
"""
import sys
import os
from pathlib import Path

import tempfile

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent))

st.set_page_config(
    page_title="SpendWise AI",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
[data-testid="stMetricValue"] { font-size: 1.6rem; }
.anomaly-card {
    background: #fff3cd; border-left: 4px solid #ffc107;
    padding: .75rem 1rem; border-radius: 6px; margin-bottom: .5rem;
}
.good-card {
    background: #d1e7dd; border-left: 4px solid #198754;
    padding: .75rem 1rem; border-radius: 6px; margin-bottom: .5rem;
}
</style>
""", unsafe_allow_html=True)


# ── Data loading ──────────────────────────────────────────────────────────────
@st.cache_data(ttl=60)
def load_data() -> pd.DataFrame:
    from spendwise.data import load_store
    return load_store()


def get_data():
    try:
        return load_data()
    except SystemExit:
        return None


def upload_and_process(uploaded_file, replace=False, pdf_password=None):
    from spendwise.data import load_document, save_store, SUPPORTED_EXTENSIONS, PDFPasswordRequired
    from spendwise import categorizer
    from spendwise.config import MODEL_PATH

    file_ext = Path(uploaded_file.name).suffix.lower()
    if file_ext not in SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"Unsupported file type '{file_ext}'. "
            f"Accepted: {', '.join(SUPPORTED_EXTENSIONS)}"
        )

    with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp:
        tmp.write(uploaded_file.getvalue())
        tmp_path = tmp.name

    try:
        new_df = load_document(tmp_path, password=pdf_password or None)
    except PDFPasswordRequired:
        raise  # let the UI handle this specifically
    finally:
        os.unlink(tmp_path)

    if not MODEL_PATH.exists():
        training_path = Path(__file__).parent / "data" / "training_labeled.csv"
        if not training_path.exists():
            raise ValueError(
                "No trained model found. Run `python -m spendwise demo` once to initialize."
            )
        categorizer.train(str(training_path))

    new_df = categorizer.categorize(new_df)
    all_df = save_store(new_df, append=not replace)
    return new_df, all_df


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("💰 SpendWise AI")
    st.caption("Personal Finance Intelligence")
    st.divider()
    page = st.radio(
        "Navigate",
        ["Dashboard", "Transactions", "Review", "Patterns", "Anomalies", "Forecast", "Budget", "Ask AI"],
        label_visibility="collapsed",
    )
    st.divider()
    if st.button("Refresh data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    if st.button("Re-categorize all", use_container_width=True, help="Re-run ML + rule classifier on every stored transaction"):
        from spendwise.data import load_store, save_store
        from spendwise import categorizer
        with st.spinner("Re-categorizing…"):
            try:
                raw = load_store().drop(columns=["category", "confidence", "source"], errors="ignore")
                updated = categorizer.categorize(raw)
                save_store(updated, append=False)
                unc_after = (updated["category"] == "Uncategorized").sum()
                st.cache_data.clear()
                st.success(f"Done. Uncategorized: {unc_after} / {len(updated)}")
                st.rerun()
            except Exception as exc:
                st.error(f"Re-categorize failed: {exc}")

    st.divider()
    st.markdown("**Upload bank statement**")
    st.caption("CSV · Excel · ODS · PDF · TSV · TXT")
    uploaded = st.file_uploader(
        "Bank statement",
        type=["csv", "xlsx", "xls", "ods", "pdf", "tsv", "txt"],
        label_visibility="collapsed",
    )
    replace_existing = st.checkbox("Replace all existing data", value=False)

    if uploaded:
        st.caption(f"File: {uploaded.name}")
        is_pdf = uploaded.name.lower().endswith(".pdf")

        # Show password field for PDFs — either because it's always relevant,
        # or because a previous attempt flagged this file as protected.
        pdf_needs_password = st.session_state.get("pdf_needs_password", False)
        pdf_password = None
        if is_pdf:
            if pdf_needs_password:
                st.warning("This PDF is password-protected.")
            pdf_password = st.text_input(
                "PDF password (leave blank if none)",
                type="password",
                key="pdf_password_input",
            )

        if st.button("Import", type="primary", use_container_width=True):
            from spendwise.data import PDFPasswordRequired
            ext_label = Path(uploaded.name).suffix.upper()
            with st.spinner(f"Parsing {ext_label} and categorizing transactions…"):
                try:
                    new_df, all_df = upload_and_process(
                        uploaded,
                        replace=replace_existing,
                        pdf_password=pdf_password if pdf_password else None,
                    )
                    st.session_state.pdf_needs_password = False
                    deb = new_df[new_df["direction"] == "debit"]
                    st.success(
                        f"Imported {len(new_df)} rows "
                        f"({len(deb)} expenses). "
                        f"Total stored: {len(all_df)}."
                    )
                    st.cache_data.clear()
                    st.rerun()
                except PDFPasswordRequired:
                    st.session_state.pdf_needs_password = True
                    st.error(
                        "This PDF is password-protected. "
                        "Enter the password in the field above and click Import again."
                    )
                except Exception as exc:
                    st.error(f"Import failed: {exc}")

df = get_data()

if df is not None:
    _unc_count = int((df["category"] == "Uncategorized").sum())
    if _unc_count > 0:
        with st.sidebar:
            st.warning(f"{_unc_count} uncategorized — go to **Review**")

if df is None:
    st.info("No transactions yet. Upload your bank statement using the sidebar, or load the sample data.")
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("#### Upload your bank statement")
        st.markdown(
            "Use the **Upload bank statement** panel in the sidebar. "
            "Accepted formats:"
        )
        st.markdown(
            "- **CSV** — comma-separated export\n"
            "- **Excel** — `.xlsx` / `.xls`\n"
            "- **ODS** — OpenDocument Spreadsheet\n"
            "- **PDF** — PDF bank statement (table extraction)\n"
            "- **TSV / TXT** — tab or auto-detected delimiter"
        )
    with col_b:
        st.markdown("#### Load sample data")
        st.markdown("Run the following command once in your terminal, then click **Refresh data**.")
        st.code("python -m spendwise demo")
    st.stop()


# ── Helpers ───────────────────────────────────────────────────────────────────
from spendwise.config import money, CATEGORIES
from spendwise.data import expenses, monthly_by_category


def fmt_inr(val):
    return f"₹{val:,.0f}"


def pct_delta(a, b):
    if b == 0:
        return None
    return f"{100*(a/b - 1):+.1f}%"


# ══════════════════════════════════════════════════════════════════════════════
# DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════
if page == "Dashboard":
    st.header("Dashboard")

    mbc = monthly_by_category(df)
    total = mbc.sum(axis=1)
    last_month = str(total.index[-1])
    prev_month = str(total.index[-2]) if len(total) >= 2 else None

    last_total = float(total.iloc[-1])
    prev_total = float(total.iloc[-2]) if prev_month else None
    exp = expenses(df)
    last_txns = exp[exp["month"] == exp["month"].max()]
    top_cat = last_txns.groupby("category")["amount"].sum().idxmax()

    # KPI row
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Last month spend", fmt_inr(last_total),
              delta=pct_delta(last_total, prev_total) if prev_total else None)
    c2.metric("Transactions", len(last_txns))
    c3.metric("Biggest category", top_cat)
    avg_txn = last_txns["amount"].mean()
    c4.metric("Avg transaction", fmt_inr(avg_txn))

    st.divider()

    # Monthly totals bar chart
    st.subheader("Monthly spending")
    total_df = total.reset_index()
    total_df.columns = ["Month", "Amount"]
    total_df["Month"] = total_df["Month"].astype(str)
    st.bar_chart(total_df.set_index("Month")["Amount"], use_container_width=True)

    st.divider()

    # Category breakdown for last month
    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader(f"Spending by category — {last_month}")
        cat_data = mbc.iloc[-1].sort_values(ascending=False)
        cat_df = cat_data.reset_index()
        cat_df.columns = ["Category", "Amount"]
        cat_df = cat_df[cat_df["Amount"] > 0]
        st.bar_chart(cat_df.set_index("Category"), use_container_width=True)

    with col_right:
        st.subheader("Month-over-month by category")
        if len(mbc) >= 2:
            compare = pd.DataFrame({
                "Last month": mbc.iloc[-1],
                "Prev month": mbc.iloc[-2],
            }).sort_values("Last month", ascending=False)
            compare = compare[compare["Last month"] > 0]
            st.bar_chart(compare, use_container_width=True)

    # Subscriptions quick view
    st.divider()
    st.subheader("Recurring payments")
    from spendwise.patterns import recurring_merchants
    recur = recurring_merchants(df)
    if not recur.empty:
        recur_df = recur.reset_index()[["merchant", "avg", "months", "category"]]
        recur_df.columns = ["Merchant", "Monthly (₹)", "Months seen", "Category"]
        recur_df["Monthly (₹)"] = recur_df["Monthly (₹)"].map(lambda x: f"₹{x:,.0f}")
        st.dataframe(recur_df, use_container_width=True, hide_index=True)
    else:
        st.info("No recurring payments detected.")


# ══════════════════════════════════════════════════════════════════════════════
# TRANSACTIONS
# ══════════════════════════════════════════════════════════════════════════════
elif page == "Transactions":
    st.header("Transactions")

    exp_df = expenses(df).copy()
    exp_df["month"] = exp_df["month"].astype(str)

    # Filters
    f1, f2, f3 = st.columns(3)
    with f1:
        months = sorted(exp_df["month"].unique(), reverse=True)
        sel_month = st.selectbox("Month", ["All"] + months)
    with f2:
        cats = sorted(exp_df["category"].dropna().unique())
        sel_cat = st.selectbox("Category", ["All"] + cats)
    with f3:
        search = st.text_input("Search description")

    filtered = exp_df.copy()
    if sel_month != "All":
        filtered = filtered[filtered["month"] == sel_month]
    if sel_cat != "All":
        filtered = filtered[filtered["category"] == sel_cat]
    if search:
        filtered = filtered[filtered["description"].str.contains(search, case=False, na=False)]

    filtered = filtered.sort_values("date", ascending=False)

    st.caption(f"{len(filtered)} transactions  •  Total: {fmt_inr(filtered['amount'].sum())}")

    display = filtered[["date", "description", "amount", "category"]].copy()
    display["date"] = display["date"].dt.strftime("%d %b %Y")
    display["amount"] = display["amount"].map(lambda x: f"₹{x:,.0f}")
    display.columns = ["Date", "Description", "Amount", "Category"]
    st.dataframe(display, use_container_width=True, hide_index=True, height=500)


# ══════════════════════════════════════════════════════════════════════════════
# PATTERNS
# ══════════════════════════════════════════════════════════════════════════════
elif page == "Patterns":
    st.header("Spending Patterns")

    with st.spinner("Running clustering..."):
        from spendwise.patterns import cluster_weeks, recurring_merchants
        profiles, silhouette, feats = cluster_weeks(df)

    st.caption(f"KMeans on weekly profiles — k={len(profiles)}, silhouette={silhouette:.2f} (soft clusters, exploratory)")

    # Cluster cards
    cols = st.columns(len(profiles))
    for col, p in zip(cols, profiles):
        with col:
            st.metric(p["label"], fmt_inr(p["avg_weekly_spend"]) + "/wk",
                      delta=f"{p['weeks']} weeks total, {p['recent_weeks']} recent")

    st.divider()

    # Weekday spend
    st.subheader("Spend by day of week")
    exp_df = expenses(df).copy()
    exp_df["weekday"] = exp_df["date"].dt.day_of_week
    day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    weekday_spend = exp_df.groupby("weekday")["amount"].sum().reindex(range(7), fill_value=0)
    weekday_df = pd.DataFrame({"Day": day_names, "Total Spend": weekday_spend.values})
    st.bar_chart(weekday_df.set_index("Day"), use_container_width=True)

    st.divider()

    # Subscriptions
    st.subheader("Subscriptions & recurring payments")
    recur = recurring_merchants(df)
    if not recur.empty:
        r = recur.reset_index()
        r = r[["merchant", "avg", "months", "category"]]
        r.columns = ["Merchant", "Monthly (avg ₹)", "Months seen", "Category"]
        r["Monthly (avg ₹)"] = r["Monthly (avg ₹)"].map(lambda x: f"₹{x:,.0f}")
        st.dataframe(r, use_container_width=True, hide_index=True)
    else:
        st.info("No recurring payments detected.")


# ══════════════════════════════════════════════════════════════════════════════
# ANOMALIES
# ══════════════════════════════════════════════════════════════════════════════
elif page == "Anomalies":
    st.header("Unusual Expenses")
    st.caption("Flagged by Isolation Forest + robust z-score — both must agree to reduce false alarms.")

    with st.spinner("Scanning for anomalies..."):
        from spendwise.anomaly import detect
        anom = detect(df)

    if anom.empty:
        st.success("No unusual expenses found.")
    else:
        st.info(f"{len(anom)} unusual transaction(s) detected")
        for row in anom.itertuples():
            st.markdown(f"""
<div class="anomaly-card">
  <strong>{row.date.strftime('%d %b %Y')}</strong> &nbsp;·&nbsp;
  <strong>₹{row.amount:,.0f}</strong> &nbsp;·&nbsp; {row.category}<br>
  <small>{row.description}</small><br>
  <em>{row.reason}</em>
</div>""", unsafe_allow_html=True)

        st.divider()
        st.subheader("Details")
        display = anom[["date", "description", "category", "amount", "reason"]].copy()
        display["date"] = display["date"].dt.strftime("%d %b %Y")
        display["amount"] = display["amount"].map(lambda x: f"₹{x:,.0f}")
        display.columns = ["Date", "Description", "Category", "Amount", "Reason"]
        st.dataframe(display, use_container_width=True, hide_index=True)


# ══════════════════════════════════════════════════════════════════════════════
# FORECAST
# ══════════════════════════════════════════════════════════════════════════════
elif page == "Forecast":
    st.header("Forecast")

    with st.spinner("Running backtest & forecast..."):
        from spendwise.forecast import forecast_next_month
        fc = forecast_next_month(df)

    c1, c2, c3 = st.columns(3)
    c1.metric("Forecast — " + fc["next_month"], fmt_inr(fc["forecast_total"]),
              delta=f"vs last month {fmt_inr(fc['last_month_total'])}")
    c2.metric("Model", fc["model"].replace("_", " "))
    c3.metric("Backtest MAE", fmt_inr(fc["mae"]) + f"  ({fc['mape_pct']:.1f}%)")

    st.divider()

    # Model comparison
    st.subheader("Model comparison (backtest MAE)")
    mae_df = pd.DataFrame(list(fc["backtest_mae"].items()), columns=["Model", "MAE (₹)"])
    mae_df["Model"] = mae_df["Model"].str.replace("_", " ")
    mae_df = mae_df.sort_values("MAE (₹)")
    st.bar_chart(mae_df.set_index("Model"), use_container_width=True)

    st.divider()

    # Per-category forecast
    st.subheader("By category")
    cat_fc = pd.DataFrame(list(fc["per_category"].items()), columns=["Category", "Forecast (₹)"])
    cat_fc = cat_fc[cat_fc["Forecast (₹)"] > 0].sort_values("Forecast (₹)", ascending=False)
    st.bar_chart(cat_fc.set_index("Category"), use_container_width=True)

    st.divider()

    # Historical spend
    st.subheader("Historical monthly spend")
    hist_df = pd.DataFrame(list(fc["history"].items()), columns=["Month", "Amount (₹)"])
    # append forecast point
    forecast_row = pd.DataFrame([[fc["next_month"] + " (forecast)", fc["forecast_total"]]],
                                 columns=["Month", "Amount (₹)"])
    hist_df = pd.concat([hist_df, forecast_row], ignore_index=True)
    st.line_chart(hist_df.set_index("Month"), use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# BUDGET
# ══════════════════════════════════════════════════════════════════════════════
elif page == "Budget":
    st.header("Budget")

    from spendwise.budget import save_budgets, load_budgets
    from spendwise.data import expenses

    exp_df = expenses(df).copy()
    exp_df["month"] = exp_df["month"].astype(str)

    # Month picker
    months = sorted(exp_df["month"].unique(), reverse=True)
    sel_month = st.selectbox("Month", months)

    month_txns = exp_df[exp_df["month"] == sel_month]
    cats = sorted(month_txns["category"].dropna().unique())
    spent_by_cat = month_txns.groupby("category")["amount"].sum()

    saved = load_budgets()

    st.subheader("Set your budget")
    st.caption("Type a budget for each category, then click Save.")

    # Form prevents mid-edit reruns that would reset the inputs
    with st.form(key=f"budget_form_{sel_month}"):
        h1, h2, h3 = st.columns([3, 2, 2])
        h1.markdown("**Category**")
        h2.markdown("**Budget (₹)**")
        h3.markdown("**Spent this month (₹)**")

        budget_inputs = {}
        for cat in cats:
            current_budget = float(saved.get(cat, 0))
            spent_amt = float(spent_by_cat.get(cat, 0))
            c1, c2, c3 = st.columns([3, 2, 2])
            c1.markdown(cat)
            budget_inputs[cat] = c2.number_input(
                label=cat,
                min_value=0.0,
                value=current_budget,
                step=100.0,
                format="%.0f",
                label_visibility="collapsed",
            )
            c3.markdown(f"₹{spent_amt:,.0f}")

        saved_ok = st.form_submit_button("Save budgets", type="primary", use_container_width=True)

    if saved_ok:
        new_budgets = {cat: v for cat, v in budget_inputs.items() if v > 0}
        save_budgets(new_budgets)
        st.success(f"Budgets saved for {len(new_budgets)} categories.")
        saved = new_budgets  # reflect immediately in the progress section below

    # Status bar per category
    st.divider()
    st.subheader(f"Transactions — {sel_month}")

    sel_cat = st.selectbox("Filter by category", ["All"] + cats, key="budget_cat_filter")

    for cat in cats:
        budget = budget_inputs.get(cat, 0)
        spent = float(spent_by_cat.get(cat, 0))

        if sel_cat != "All" and cat != sel_cat:
            continue

        label = f"{cat}  —  Spent ₹{spent:,.0f}"
        if budget > 0:
            label += f" / Budget ₹{budget:,.0f}"

        with st.expander(label, expanded=(sel_cat == cat)):
            if budget > 0:
                ratio = min(spent / budget, 1.0)
                st.progress(
                    ratio,
                    text=f"{'Over budget' if spent > budget else 'Within budget'}  ({spent / budget * 100:.0f}%)",
                )

            cat_txns = month_txns[month_txns["category"] == cat].sort_values("date", ascending=False)
            if cat_txns.empty:
                st.info("No transactions this month.")
            else:
                disp = cat_txns[["date", "description", "amount"]].copy()
                disp["date"] = disp["date"].dt.strftime("%d %b %Y")
                disp["amount"] = disp["amount"].map(lambda x: f"₹{x:,.0f}")
                disp.columns = ["Date", "Description", "Amount"]
                st.dataframe(disp, use_container_width=True, hide_index=True)


# ══════════════════════════════════════════════════════════════════════════════
# REVIEW UNCATEGORIZED
# ══════════════════════════════════════════════════════════════════════════════
elif page == "Review":
    st.header("Uncategorized Review")
    st.caption("Fix transactions the AI couldn't classify. Corrections are saved and used for future uploads.")

    from spendwise.data import load_store, save_store
    from spendwise.config import CORRECTIONS_CSV, CATEGORIES

    # Always load fresh — this page writes back to the store
    all_df = load_store()
    unc = all_df[all_df["category"] == "Uncategorized"].copy()
    total_unc = len(unc)

    if total_unc == 0:
        st.success("All transactions are categorized. Nothing to review.")
        st.stop()

    st.info(f"{total_unc} transaction(s) need a category")

    PAGE_SIZE = 25
    total_pages = max(1, (total_unc - 1) // PAGE_SIZE + 1)

    if "review_page" not in st.session_state:
        st.session_state.review_page = 0
    # Clamp after a save shrinks the list
    if st.session_state.review_page >= total_pages:
        st.session_state.review_page = max(0, total_pages - 1)

    start = st.session_state.review_page * PAGE_SIZE
    end = min(start + PAGE_SIZE, total_unc)
    page_unc = unc.iloc[start:end]

    # Pagination controls
    col_prev, col_info, col_next = st.columns([1, 2, 1])
    with col_prev:
        if st.button("← Previous", disabled=st.session_state.review_page == 0, use_container_width=True):
            st.session_state.review_page -= 1
            st.rerun()
    with col_info:
        st.markdown(
            f"<div style='text-align:center;padding-top:8px'>"
            f"Page {st.session_state.review_page + 1} of {total_pages}"
            f"&nbsp;&nbsp;({start + 1}–{end} of {total_unc})"
            f"</div>",
            unsafe_allow_html=True,
        )
    with col_next:
        if st.button("Next →", disabled=st.session_state.review_page >= total_pages - 1, use_container_width=True):
            st.session_state.review_page += 1
            st.rerun()

    st.divider()

    # Header row
    h1, h2, h3, h4 = st.columns([2, 5, 2, 3])
    h1.markdown("**Date**")
    h2.markdown("**Description**")
    h3.markdown("**Amount**")
    h4.markdown("**Assign category**")

    cat_options = ["(skip)"] + sorted(CATEGORIES)

    for orig_idx, row in page_unc.iterrows():
        c1, c2, c3, c4 = st.columns([2, 5, 2, 3])
        date_str = (
            row["date"].strftime("%d %b %Y")
            if hasattr(row["date"], "strftime")
            else str(row["date"])
        )
        c1.markdown(date_str)
        desc = str(row.get("description", ""))
        c2.markdown(f"`{desc[:58]}{'…' if len(desc) > 58 else ''}`")
        c3.markdown(f"₹{float(row['amount']):,.0f}")
        c4.selectbox(
            label="category",
            options=cat_options,
            index=0,
            label_visibility="collapsed",
            key=f"rev_cat_{orig_idx}",
        )

    st.divider()

    col_save, col_skip = st.columns([3, 1])
    with col_save:
        save_clicked = st.button("Save corrections", type="primary", use_container_width=True)
    with col_skip:
        if st.button("Next page →", use_container_width=True, disabled=st.session_state.review_page >= total_pages - 1):
            st.session_state.review_page += 1
            st.rerun()

    if save_clicked:
        corrections = {
            orig_idx: st.session_state[f"rev_cat_{orig_idx}"]
            for orig_idx in page_unc.index
            if st.session_state.get(f"rev_cat_{orig_idx}", "(skip)") != "(skip)"
        }

        if not corrections:
            st.warning("No categories selected on this page. Use the dropdowns to assign a category, then click Save.")
        else:
            # Apply to store
            updated_df = all_df.copy()
            new_corr_rows = []
            for idx, cat in corrections.items():
                updated_df.loc[idx, "category"] = cat
                updated_df.loc[idx, "confidence"] = 1.0
                updated_df.loc[idx, "source"] = "user"
                new_corr_rows.append({
                    "description": str(all_df.loc[idx, "description"]),
                    "category": cat,
                })
            save_store(updated_df, append=False)

            # Persist to corrections.csv so future auto-categorization learns from these
            corr_df = pd.DataFrame(new_corr_rows)
            if CORRECTIONS_CSV.exists():
                existing_corr = pd.read_csv(CORRECTIONS_CSV)
                combined_corr = pd.concat([existing_corr, corr_df]).drop_duplicates(
                    subset=["description"], keep="last"
                )
            else:
                combined_corr = corr_df
            combined_corr.to_csv(CORRECTIONS_CSV, index=False)

            remaining = total_unc - len(corrections)
            st.cache_data.clear()
            st.success(
                f"Saved {len(corrections)} correction(s). "
                + (f"{remaining} uncategorized remaining." if remaining > 0 else "All transactions categorized!")
            )
            st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# ASK AI
# ══════════════════════════════════════════════════════════════════════════════
elif page == "Ask AI":
    st.header("Ask AI")
    st.caption("Questions are answered by ML-computed facts. The LLM (Claude) explains them if an API key is set.")

    # Suggested questions
    suggestions = [
        "Why did my expenses increase this month?",
        "How much did I spend on food delivery?",
        "Anything unusual in my spending?",
        "How much will I spend next month?",
        "What are my subscriptions?",
        "Where does most of my money go?",
        "Give me budget advice.",
    ]

    st.markdown("**Try a question:**")
    cols = st.columns(4)
    if "question" not in st.session_state:
        st.session_state.question = ""

    for i, sug in enumerate(suggestions):
        if cols[i % 4].button(sug, use_container_width=True):
            st.session_state.question = sug

    question = st.text_input("Or type your own question:", value=st.session_state.question, key="q_input")

    use_llm = st.checkbox("Use Claude LLM (requires ANTHROPIC_API_KEY)", value=bool(os.environ.get("ANTHROPIC_API_KEY")))

    if st.button("Ask", type="primary", use_container_width=True) and question.strip():
        with st.spinner("Thinking..."):
            from spendwise.assistant import ask
            result = ask(df, question, use_llm=use_llm)

        st.divider()
        engine_label = "Claude LLM" if result["engine"] == "llm" else "Template engine"
        st.caption(f"Intent: `{result['intent']}` · Engine: {engine_label}")
        st.markdown(f"### Answer\n{result['answer']}")

        with st.expander("Show facts sent to LLM"):
            import json
            st.json(result["facts"])

    # Chat history
    if "history" not in st.session_state:
        st.session_state.history = []

    if st.session_state.get("last_q") != question and question.strip() and st.session_state.get("answered"):
        st.session_state.history.append((question, st.session_state.last_answer))

    if st.session_state.history:
        st.divider()
        st.subheader("Previous questions")
        for q, a in reversed(st.session_state.history[-5:]):
            with st.expander(q):
                st.write(a)
