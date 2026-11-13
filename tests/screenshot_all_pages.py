"""Capture screenshots of all 8 pages for the portfolio report."""
import os, sys, time
os.chdir(r"C:\Users\meeting\Spendwise-ML project")
sys.path.insert(0, r"C:\Users\meeting\Spendwise-ML project")
sys.stdout = __import__('io').TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from playwright.sync_api import sync_playwright

PAGES = [
    ("Dashboard",   '[data-testid="stMain"] :is(h1,h2,h3):has-text("Dashboard")',           "ss_dashboard.png"),
    ("Transactions",'[data-testid="stMain"] :is(h1,h2,h3):has-text("Transactions")',        "ss_transactions.png"),
    ("Review",      '[data-testid="stMain"] :is(h1,h2,h3):has-text("Uncategorized Review")', "ss_review.png"),
    ("Patterns",    '[data-testid="stMain"] :is(h1,h2,h3):has-text("Spending Patterns")',   "ss_patterns.png"),
    ("Anomalies",   '[data-testid="stMain"] :is(h1,h2,h3):has-text("Unusual Expenses")',    "ss_anomalies.png"),
    ("Forecast",    '[data-testid="stMain"] :is(h1,h2,h3):has-text("Forecast")',            "ss_forecast.png"),
    ("Budget",      '[data-testid="stMain"] :is(h1,h2,h3):has-text("Budget")',              "ss_budget.png"),
    ("Ask AI",      '[data-testid="stMain"] :is(h1,h2,h3):has-text("Ask AI")',              "ss_ask_ai.png"),
]

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1400, "height": 900})
    page.goto("http://localhost:8502", wait_until="domcontentloaded")
    time.sleep(3)

    for nav_name, ready_sel, filename in PAGES:
        label = page.locator(f'[data-testid="stSidebar"] label:has-text("{nav_name}")')
        label.click()
        try:
            page.wait_for_selector(ready_sel, timeout=25000)
        except Exception:
            pass
        time.sleep(3)
        page.screenshot(path=filename, full_page=False)
        print(f"Saved {filename}")

    browser.close()
print("All screenshots done.")
