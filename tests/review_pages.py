"""Quick smoke-test: visit every page, capture title + any error banners."""
import sys, io, os, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
os.chdir(r"C:\Users\meeting\Spendwise-ML project")
sys.path.insert(0, r"C:\Users\meeting\Spendwise-ML project")

from playwright.sync_api import sync_playwright

BASE_URL = "http://localhost:8502"
PAGES = [
    ("Dashboard",     '[data-testid="stMain"] :is(h1,h2,h3):has-text("Dashboard")'),
    ("Transactions",  '[data-testid="stMain"] :is(h1,h2,h3):has-text("Transactions")'),
    ("Review",        '[data-testid="stMain"] :is(h1,h2,h3):has-text("Uncategorized Review")'),
    ("Patterns",      '[data-testid="stMain"] :is(h1,h2,h3):has-text("Spending Patterns")'),
    ("Anomalies",     '[data-testid="stMain"] :is(h1,h2,h3):has-text("Unusual Expenses")'),
    ("Forecast",      '[data-testid="stMain"] :is(h1,h2,h3):has-text("Forecast")'),
    ("Budget",        '[data-testid="stMain"] :is(h1,h2,h3):has-text("Budget")'),
    ("Ask AI",        '[data-testid="stMain"] :is(h1,h2,h3):has-text("Ask AI")'),
]

TIMEOUT = 30_000

def get_errors(page):
    """Return list of visible error/exception banners."""
    errors = []
    for sel in [
        '[data-testid="stException"]',
        '[data-testid="stAlert"][kind="error"]',
        '.stException',
    ]:
        els = page.query_selector_all(sel)
        for el in els:
            txt = el.inner_text().strip()
            if txt:
                errors.append(txt[:200])
    return errors

def get_warnings(page):
    warnings = []
    for el in page.query_selector_all('[data-testid="stAlert"]'):
        kind = el.get_attribute("data-baseweb") or ""
        txt = el.inner_text().strip()
        if txt and "uncategorized" not in txt.lower():
            warnings.append(txt[:120])
    return warnings

results = []

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context()
    pg = context.new_page()

    # Open app once; wait for initial load
    pg.goto(BASE_URL, wait_until="domcontentloaded")
    time.sleep(2)

    for page_name, ready_sel in PAGES:
        print(f"\n{'='*55}")
        print(f"  PAGE: {page_name}")
        print(f"{'='*55}")

        # Click the nav radio
        nav_label = pg.locator(f'[data-testid="stSidebar"] label:has-text("{page_name}")')
        try:
            nav_label.click(timeout=5000)
        except Exception as e:
            print(f"  [WARN] Could not click nav '{page_name}': {e}")

        t0 = time.time()
        try:
            pg.wait_for_selector(ready_sel, timeout=TIMEOUT)
            elapsed = (time.time() - t0) * 1000
            print(f"  Load time  : {elapsed:.0f} ms")
            status = "OK"
        except Exception as e:
            elapsed = (time.time() - t0) * 1000
            print(f"  [TIMEOUT]  : {elapsed:.0f} ms — {e}")
            status = "TIMEOUT"

        errs = get_errors(pg)
        warns = get_warnings(pg)

        if errs:
            status = "ERROR"
            print(f"  Errors ({len(errs)}):")
            for e in errs:
                print(f"    - {e[:180]}")
        else:
            print(f"  Errors     : none")

        if warns:
            print(f"  Warnings ({len(warns)}):")
            for w in warns:
                print(f"    - {w}")

        # Capture main content summary
        main_text = pg.locator('[data-testid="stMain"]').inner_text()
        lines = [l.strip() for l in main_text.splitlines() if l.strip()][:6]
        print(f"  Content    : {' | '.join(lines)}")

        results.append({"page": page_name, "status": status, "load_ms": int(elapsed)})

    browser.close()

print(f"\n\n{'='*55}")
print("  SUMMARY")
print(f"{'='*55}")
print(f"{'Page':<18} {'Status':<10} {'Load (ms)'}")
print(f"{'-'*18} {'-'*10} {'-'*10}")
for r in results:
    icon = "✓" if r["status"] == "OK" else "✗"
    print(f"{icon} {r['page']:<17} {r['status']:<10} {r['load_ms']}")

ok = sum(1 for r in results if r["status"] == "OK")
print(f"\n{ok}/{len(results)} pages passed")
