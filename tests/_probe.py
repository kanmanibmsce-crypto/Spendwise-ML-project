import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    pg = b.new_page()
    pg.goto("http://localhost:8501")
    pg.wait_for_load_state("networkidle", timeout=30000)
    pg.wait_for_timeout(4000)

    headings = pg.evaluate("""() => {
        const hs = document.querySelectorAll('h1,h2,h3,[data-testid]');
        return Array.from(hs).slice(0, 20).map(h => h.tagName + '|' + (h.dataset.testid||'') + ': ' + h.textContent.trim().slice(0,60));
    }""")
    print("DOM elements:")
    for h in headings:
        print(" ", h)

    # try locator approach
    try:
        pg.get_by_role("heading", name="Dashboard").wait_for(timeout=3000)
        print("get_by_role heading Dashboard: FOUND")
    except Exception as e:
        print("get_by_role heading Dashboard: NOT FOUND", e)

    b.close()
