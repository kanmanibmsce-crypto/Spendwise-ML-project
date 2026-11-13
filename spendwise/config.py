"""Paths and shared constants."""
import os
from pathlib import Path

HOME = Path(os.environ.get("SPENDWISE_HOME", Path.cwd() / ".spendwise"))
HOME.mkdir(parents=True, exist_ok=True)

STORE_CSV = HOME / "transactions.csv"        # categorized transactions of the user
MODEL_PATH = HOME / "categorizer.joblib"     # trained classifier
MODEL_REPORT = HOME / "categorizer_report.json"
CORRECTIONS_CSV = HOME / "corrections.csv"   # user feedback on categories
BUDGETS_JSON = HOME / "budgets.json"         # budgets the user accepted
EVENTS_LOG = HOME / "events.jsonl"           # product analytics events

USER_ID = os.environ.get("SPENDWISE_USER", "demo_user")
CURRENCY = os.environ.get("SPENDWISE_CURRENCY", "₹")

CATEGORIES = [
    "Food Delivery", "Groceries", "Dining Out", "Transport", "Shopping",
    "Bills & Utilities", "Rent", "Entertainment", "Health", "Travel",
    "Education", "Investments", "Transfers", "Vehicle Insurance",
    "Family Transfer",
]

# Used by the budget engine: essentials are harder to cut than discretionary spend.
ESSENTIAL = {"Groceries", "Rent", "Bills & Utilities", "Health", "Education", "Transport"}

CONFIDENCE_THRESHOLD = 0.45  # below this the classifier says "Uncategorized"


def money(x: float) -> str:
    return f"{CURRENCY}{x:,.0f}"
