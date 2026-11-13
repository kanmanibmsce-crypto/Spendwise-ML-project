"""Synthetic data generator.

Creates two files:
  data/training_labeled.csv   - labelled descriptions used to train the classifier
  data/sample_bank_statement.csv - 12 months of a realistic Indian bank statement
                                   (Date, Description, Debit, Credit) with a
                                   built-in story: spending jumps in the last month
                                   (food delivery +~32%, shopping, transport) and a
                                   few injected anomalies.
"""
import random
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

MERCHANTS = {
    "Food Delivery": ["SWIGGY", "ZOMATO", "ZOMATO LTD", "SWIGGY BUNDL", "EATSURE", "DOMINOS ONLINE"],
    "Groceries": ["BIGBASKET", "BLINKIT", "ZEPTO", "DMART", "SWIGGY INSTAMART", "MORE RETAIL", "JIOMART"],
    "Dining Out": ["THIRD WAVE COFFEE", "CHAI POINT", "MTR RESTAURANT", "TRUFFLES", "STARBUCKS", "BARBEQUE NATION"],
    "Transport": ["UBER INDIA", "OLA CABS", "RAPIDO", "NAMMA METRO", "HPCL FUEL", "IOCL PETROL", "FASTAG RECHARGE"],
    "Shopping": ["AMAZON IN", "AMZN MKTP", "FLIPKART", "MYNTRA", "AJIO", "NYKAA", "DECATHLON", "CROMA"],
    "Bills & Utilities": ["BESCOM ELECTRICITY", "AIRTEL POSTPAID", "JIO RECHARGE", "ACT FIBERNET", "BWSSB WATER", "INDANE GAS"],
    "Rent": ["RENT PAYMENT", "NOBROKER RENT", "HOUSE RENT LANDLORD"],
    "Entertainment": ["NETFLIX", "SPOTIFY", "BOOKMYSHOW", "HOTSTAR", "PVR CINEMAS", "AMAZON PRIME"],
    "Health": ["APOLLO PHARMACY", "PHARMEASY", "PRACTO", "CULTFIT", "1MG", "MANIPAL HOSPITAL"],
    "Travel": ["MAKEMYTRIP", "IRCTC", "INDIGO AIRLINES", "GOIBIBO", "REDBUS", "OYO ROOMS"],
    "Education": ["UDEMY", "COURSERA", "UPGRAD", "KINDLE EBOOKS", "UNACADEMY"],
}

TEMPLATES = [
    "UPI/{ref}/{m}/{vpa}@ybl/Payment",
    "UPI-{m}-{vpa}@okaxis-{ref}",
    "POS {ref} {m} BANGALORE IN",
    "{m} {ref}",
    "ACH D- {m}-{ref}",
    "NEFT/{ref}/{m}",
    "BIL/ONL/{ref}/{m}",
    "VIN/{m}/{ref}",
]


def _desc(merchant: str, rng: random.Random) -> str:
    t = rng.choice(TEMPLATES)
    ref = str(rng.randint(10**9, 10**12))
    vpa = merchant.lower().replace(" ", "")[:10] + str(rng.randint(1, 99))
    m = merchant
    r = rng.random()
    if r < 0.25:
        m = m.title()
    elif r < 0.35:
        m = m.replace(" ", "")
    return t.format(m=m, ref=ref, vpa=vpa)


def make_training(n_per_class=250, seed=7) -> pd.DataFrame:
    rng = random.Random(seed)
    rows = []
    for cat, ms in MERCHANTS.items():
        for _ in range(n_per_class):
            rows.append({"description": _desc(rng.choice(ms), rng), "category": cat})
    # a little label noise like real hand-labelled data
    df = pd.DataFrame(rows).sample(frac=1, random_state=seed).reset_index(drop=True)
    noisy = df.sample(frac=0.02, random_state=seed).index
    df.loc[noisy, "category"] = rng.choices(list(MERCHANTS), k=len(noisy))
    return df


# Variable spend: (transactions per month, typical amount) — urban professional
VARIABLE = {
    "Food Delivery": (14, 420), "Groceries": (8, 900), "Dining Out": (5, 650),
    "Transport": (22, 260), "Shopping": (4, 1900), "Entertainment": (2, 500), "Health": (2, 850),
}
VARIABLE_MERCHANTS = {**MERCHANTS, "Entertainment": ["BOOKMYSHOW", "PVR CINEMAS"],
                      "Bills & Utilities": ["JIO RECHARGE", "INDANE GAS"]}
# Fixed monthly payments: (merchant, category, day of month, amount or None=variable)
FIXED = [
    ("NOBROKER RENT", "Rent", 5, 22000), ("NETFLIX", "Entertainment", 10, 649),
    ("SPOTIFY", "Entertainment", 12, 119), ("AIRTEL POSTPAID", "Bills & Utilities", 15, 799),
    ("ACT FIBERNET", "Bills & Utilities", 18, 1179), ("BESCOM ELECTRICITY", "Bills & Utilities", 20, None),
    ("CULTFIT", "Health", 2, 1499),
]
# One-off events: (yyyy, m, d, merchant, category, amount)
ONE_OFFS = [
    (2025, 12, 22, "MAKEMYTRIP", "Travel", 14200), (2025, 12, 27, "OYO ROOMS", "Travel", 6400),
    (2026, 1, 9, "UDEMY", "Education", 3499), (2026, 4, 17, "IRCTC", "Travel", 2850),
    (2026, 4, 18, "GOIBIBO", "Travel", 5200), (2026, 7, 6, "COURSERA", "Education", 4100),
]
# Last month story (Diwali season): what the assistant must explain
LAST_MONTH_LIFT = {"Food Delivery": 1.32, "Shopping": 1.75, "Transport": 1.30}


def make_statement(months=12, end=date(2026, 10, 31), seed=42) -> pd.DataFrame:
    rng = random.Random(seed)
    nprng = np.random.default_rng(seed)
    month_starts = pd.date_range(end=pd.Timestamp(end), periods=months, freq="MS")
    rows = []
    for i, ms in enumerate(month_starts):
        days = pd.Period(ms, "M").days_in_month
        last = i == len(month_starts) - 1
        trend = 1 + 0.006 * i  # slow lifestyle inflation
        base = ms.date()
        rows.append((base, "NEFT/SALARY/ACME TECHNOLOGIES PVT LTD", 0.0, 95000.0))
        for merchant, cat, day, amt in FIXED:
            a = amt if amt else round(nprng.normal(1350, 180) * (1.25 if ms.month in (4, 5) else 1), 2)
            rows.append((base + timedelta(days=day - 1), f"ACH D- {merchant}-{rng.randint(10**8, 10**9)}", a, 0.0))
        for cat, (freq, mean_amt) in VARIABLE.items():
            lift = LAST_MONTH_LIFT.get(cat, 1.0) if last else 1.0
            n = max(0, int(round(freq * (lift if cat == "Food Delivery" else 1))) + int(nprng.integers(-1, 2)))
            for _ in range(n):
                amt = nprng.lognormal(np.log(mean_amt), 0.28) * trend
                if cat != "Food Delivery":
                    amt *= lift
                d = base + timedelta(days=rng.randint(0, days - 1))
                rows.append((d, _desc(rng.choice(VARIABLE_MERCHANTS[cat]), rng), round(amt, 2), 0.0))
    for y, m, d, merchant, cat, amt in ONE_OFFS:
        rows.append((date(y, m, d), _desc(merchant, rng), float(amt), 0.0))
    # injected anomalies — the detector should find these
    rows.append((date(2026, 6, 14), _desc("CROMA", rng), 48999.0, 0.0))          # big electronics buy
    rows.append((date(2026, 8, 15), _desc("ZOMATO", rng), 3850.0, 0.0))         # party order
    rows.append((date(2026, 10, 22), _desc("UBER INDIA", rng), 2900.0, 0.0))    # airport ride
    rows.append((date(2026, 3, 11), "UPI/88231/UNKNOWN MERCHANT XJ/xj77@paytm", 15000.0, 0.0))
    df = pd.DataFrame(rows, columns=["Date", "Description", "Debit", "Credit"])
    df = df.sort_values("Date").reset_index(drop=True)
    df["Date"] = pd.to_datetime(df["Date"]).dt.strftime("%d/%m/%Y")
    return df


def main(out_dir="data"):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    tr = make_training()
    tr.to_csv(out / "training_labeled.csv", index=False)
    st = make_statement()
    st.to_csv(out / "sample_bank_statement.csv", index=False)
    return out / "training_labeled.csv", out / "sample_bank_statement.csv", len(tr), len(st)
