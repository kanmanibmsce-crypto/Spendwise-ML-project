import os, sys, time
os.chdir(r"C:\Users\meeting\Spendwise-ML project")
sys.path.insert(0, r"C:\Users\meeting\Spendwise-ML project")
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1400, "height": 900})
    page.goto("http://localhost:8502", wait_until="domcontentloaded")
    time.sleep(2)
    page.wait_for_selector('[data-testid="stMain"] :is(h1,h2,h3):has-text("Dashboard")', timeout=25000)
    time.sleep(2)
    # Navigate to Anomalies
    page.locator('[data-testid="stSidebar"] label:has-text("Anomalies")').click()
    page.wait_for_selector('[data-testid="stMain"] :is(h1,h2,h3):has-text("Unusual Expenses")', timeout=25000)
    time.sleep(4)
    page.screenshot(path="anomalies_screenshot.png", full_page=True)
    browser.close()
    print("Done")
