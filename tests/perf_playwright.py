"""
SpendWise AI — Playwright Performance Test Suite
=================================================
Measures load times, navigation latency, resource footprint, Core Web Vitals,
and ML-heavy page computation times.  Produces a self-contained HTML report.

Usage:
    python tests/perf_playwright.py
    python tests/perf_playwright.py --runs 5 --url http://localhost:8501
"""
from __future__ import annotations

import argparse
import base64
import io
import json
import math
import statistics
import sys
import time
from datetime import datetime
from pathlib import Path

from playwright.sync_api import Browser, Page, sync_playwright

# ── config ────────────────────────────────────────────────────────────────────
BASE_URL   = "http://localhost:8501"
RUNS       = 3           # iterations per page (averaged)
TIMEOUT_MS = 60_000      # max wait per page (heavy ML pages)
REPORT_DIR = Path(__file__).parent.parent / "reports"
CSV_PATH   = Path(__file__).parent.parent / "data" / "sample_bank_statement.csv"

PAGES = [
    "Dashboard",
    "Transactions",
    "Patterns",
    "Anomalies",
    "Forecast",
    "Budget",
    "Ask AI",
]

# page-specific element to confirm render is done  (:has-text is Playwright CSS)
PAGE_READY = {
    "Dashboard":     '[data-testid="stMain"] :is(h1,h2,h3):has-text("Dashboard")',
    "Transactions":  '[data-testid="stMain"] :is(h1,h2,h3):has-text("Transactions")',
    "Patterns":      '[data-testid="stMain"] :is(h1,h2,h3):has-text("Spending Patterns")',
    "Anomalies":     '[data-testid="stMain"] :is(h1,h2,h3):has-text("Unusual Expenses")',
    "Forecast":      '[data-testid="stMain"] :is(h1,h2,h3):has-text("Forecast")',
    "Budget":        '[data-testid="stMain"] :is(h1,h2,h3):has-text("Budget")',
    "Ask AI":        '[data-testid="stMain"] :is(h1,h2,h3):has-text("Ask AI")',
}

# ── helpers ───────────────────────────────────────────────────────────────────

def wait_for_streamlit(page: Page, ready_selector: str,
                       timeout: int = TIMEOUT_MS) -> float:
    """Wait until Streamlit finishes rendering.  Returns elapsed ms."""
    t0 = time.perf_counter()
    # Spinner may appear on ML-heavy pages; wait for it to vanish first
    try:
        page.wait_for_selector('[data-testid="stSpinner"]', state="visible", timeout=2_000)
        page.wait_for_selector('[data-testid="stSpinner"]', state="hidden",  timeout=timeout)
    except Exception:
        pass
    # Confirm target content is in the DOM
    page.wait_for_selector(ready_selector, timeout=timeout)
    return (time.perf_counter() - t0) * 1000


def nav_timing(page: Page) -> dict:
    return page.evaluate("""() => {
        const e = performance.getEntriesByType('navigation')[0];
        if (!e) return {};
        return {
            dns_ms:      +(e.domainLookupEnd - e.domainLookupStart).toFixed(2),
            tcp_ms:      +(e.connectEnd - e.connectStart).toFixed(2),
            ttfb_ms:     +(e.responseStart - e.requestStart).toFixed(2),
            dom_load_ms: +(e.domContentLoadedEventEnd - e.fetchStart).toFixed(2),
            full_load_ms:+(e.loadEventEnd - e.fetchStart).toFixed(2),
        };
    }""")


def resource_stats(page: Page) -> dict:
    return page.evaluate("""() => {
        const res = performance.getEntriesByType('resource');
        const byType = {};
        let totalBytes = 0, totalDur = 0;
        res.forEach(r => {
            const t = r.initiatorType || 'other';
            if (!byType[t]) byType[t] = {count:0, bytes:0, dur:0};
            byType[t].count++;
            byType[t].bytes += r.transferSize || 0;
            byType[t].dur   += r.duration || 0;
            totalBytes += r.transferSize || 0;
            totalDur   += r.duration || 0;
        });
        return {total_requests: res.length, total_bytes: totalBytes,
                total_dur_ms: +totalDur.toFixed(2), by_type: byType,
                slowest: res.sort((a,b)=>b.duration-a.duration)
                            .slice(0,5).map(r=>({
                                name: r.name.split('/').pop().split('?')[0].slice(0,50),
                                dur_ms: +r.duration.toFixed(2),
                                bytes: r.transferSize||0,
                                type: r.initiatorType
                            }))};
    }""")


def memory_stats(page: Page) -> dict | None:
    return page.evaluate("""() => {
        if (!performance.memory) return null;
        return {
            used_mb:  +(performance.memory.usedJSHeapSize  / 1048576).toFixed(2),
            total_mb: +(performance.memory.totalJSHeapSize / 1048576).toFixed(2),
            limit_mb: +(performance.memory.jsHeapSizeLimit / 1048576).toFixed(2),
        };
    }""")


def web_vitals(page: Page) -> dict:
    """Inject web-vitals polyfill and collect FCP/LCP/CLS estimates."""
    return page.evaluate("""() => {
        const fcp = performance.getEntriesByName('first-contentful-paint');
        return {
            fcp_ms: fcp.length ? +fcp[0].startTime.toFixed(2) : null,
        };
    }""")


def screenshot_b64(page: Page) -> str:
    png = page.screenshot(full_page=False)
    return base64.b64encode(png).decode()


def rating(ms: float | None) -> tuple[str, str]:
    """Return (label, css-color) for a millisecond value."""
    if ms is None:
        return "N/A", "#888"
    if ms < 500:
        return "Excellent", "#16a34a"
    if ms < 1_500:
        return "Good", "#65a30d"
    if ms < 3_000:
        return "Fair", "#d97706"
    return "Poor", "#dc2626"


def fmt_ms(ms: float | None) -> str:
    if ms is None:
        return "—"
    return f"{ms:,.0f} ms"


def fmt_kb(b: float) -> str:
    return f"{b/1024:,.1f} KB"


# ── test runner ───────────────────────────────────────────────────────────────

def run_initial_load(browser: Browser) -> dict:
    """Cold-start load: fresh context, navigate once, collect everything."""
    print("  [1/5] Cold-start initial load …", flush=True)
    ctx = browser.new_context()
    page = ctx.new_page()

    t0 = time.perf_counter()
    page.goto(BASE_URL, wait_until="domcontentloaded")
    render_ms = wait_for_streamlit(page, PAGE_READY["Dashboard"])
    cold_ms = (time.perf_counter() - t0) * 1000

    nt  = nav_timing(page)
    res = resource_stats(page)
    mem = memory_stats(page)
    vit = web_vitals(page)
    ss  = screenshot_b64(page)

    ctx.close()
    return dict(cold_ms=cold_ms, nav_timing=nt, resources=res,
                memory=mem, vitals=vit, screenshot=ss)


def run_page_navigations(browser: Browser) -> list[dict]:
    """Warm navigation: open app once, cycle through all pages N times."""
    print(f"  [2/5] Page navigation ({RUNS} runs × {len(PAGES)} pages) …", flush=True)
    ctx  = browser.new_context()
    page = ctx.new_page()
    page.goto(BASE_URL, wait_until="domcontentloaded")
    wait_for_streamlit(page, PAGE_READY["Dashboard"])

    page_results = []
    for pname in PAGES:
        times_ms, screenshots = [], []
        for run in range(RUNS):
            # navigate via sidebar radio
            page.locator(
                f'[data-testid="stSidebar"] label:has-text("{pname}")'
            ).first.click()
            elapsed = wait_for_streamlit(page, PAGE_READY[pname])
            times_ms.append(elapsed)
            if run == 0:
                screenshots.append(screenshot_b64(page))
            print(f"       {pname:14s} run {run+1}: {elapsed:6.0f} ms", flush=True)
            page.wait_for_timeout(400)  # let Streamlit settle between runs

        mem = memory_stats(page)
        page_results.append(dict(
            page=pname,
            times_ms=times_ms,
            mean_ms=statistics.mean(times_ms),
            min_ms=min(times_ms),
            max_ms=max(times_ms),
            stdev_ms=statistics.stdev(times_ms) if len(times_ms) > 1 else 0,
            p95_ms=sorted(times_ms)[math.ceil(0.95 * len(times_ms)) - 1],
            memory=mem,
            screenshot=screenshots[0] if screenshots else None,
        ))

    ctx.close()
    return page_results


def run_interaction_perf(browser: Browser) -> dict:
    """Measure filter/search interactions on the Transactions page."""
    print("  [3/5] Interaction performance …", flush=True)
    ctx  = browser.new_context()
    page = ctx.new_page()
    page.goto(BASE_URL, wait_until="domcontentloaded")
    wait_for_streamlit(page, PAGE_READY["Dashboard"])

    # Navigate to Transactions
    page.locator('[data-testid="stSidebar"] label:has-text("Transactions")').first.click()
    wait_for_streamlit(page, PAGE_READY["Transactions"])

    interactions = []

    # Category filter
    t0 = time.perf_counter()
    try:
        sel = page.locator('[data-testid="stSelectbox"]').nth(1)
        sel.click()
        page.wait_for_timeout(300)
        opts = page.locator('[data-testid="stSelectboxVirtualDropdown"] li')
        if opts.count() > 1:
            opts.nth(1).click()
        wait_for_streamlit(page, PAGE_READY["Transactions"])
        interactions.append(("Category filter", (time.perf_counter() - t0) * 1000))
    except Exception as exc:
        interactions.append(("Category filter", None))

    # Search box
    t0 = time.perf_counter()
    try:
        page.locator('[data-testid="stTextInput"] input').fill("UPI")
        page.wait_for_timeout(600)
        interactions.append(("Search input", (time.perf_counter() - t0) * 1000))
    except Exception:
        interactions.append(("Search input", None))

    ctx.close()
    return {"interactions": interactions}


def run_csv_upload(browser: Browser) -> dict | None:
    """Time the CSV upload + categorization pipeline."""
    print("  [4/5] CSV upload performance …", flush=True)
    if not CSV_PATH.exists():
        print("       sample CSV not found — skipping", flush=True)
        return None

    ctx  = browser.new_context()
    page = ctx.new_page()
    page.goto(BASE_URL, wait_until="domcontentloaded")
    wait_for_streamlit(page, PAGE_READY["Dashboard"])

    t0 = time.perf_counter()
    try:
        uploader = page.locator('[data-testid="stFileUploaderDropzone"] input[type="file"]')
        uploader.set_input_files(str(CSV_PATH))
        page.wait_for_timeout(500)

        import_btn = page.locator('[data-testid="stSidebar"] button:has-text("Import")')
        import_btn.click()

        # wait for success toast / spinner to clear
        try:
            page.wait_for_selector('[data-testid="stSpinner"]', state="visible", timeout=2_000)
        except Exception:
            pass
        try:
            page.wait_for_selector('[data-testid="stSpinner"]', state="hidden",  timeout=TIMEOUT_MS)
        except Exception:
            pass
        page.wait_for_timeout(1_000)
        upload_ms = (time.perf_counter() - t0) * 1000
        ss = screenshot_b64(page)
        ctx.close()
        return {"upload_ms": upload_ms, "screenshot": ss, "error": None}
    except Exception as exc:
        ctx.close()
        return {"upload_ms": None, "screenshot": None, "error": str(exc)}


def run_concurrent_load(browser: Browser, tabs: int = 3) -> dict:
    """Open N tabs simultaneously and measure combined load times."""
    print(f"  [5/5] Concurrent load ({tabs} tabs) …", flush=True)
    ctx   = browser.new_context()
    pages = [ctx.new_page() for _ in range(tabs)]
    times = []
    for p in pages:
        t0 = time.perf_counter()
        p.goto(BASE_URL, wait_until="domcontentloaded")
        wait_for_streamlit(p, PAGE_READY["Dashboard"])
        times.append((time.perf_counter() - t0) * 1000)
    ctx.close()
    return {"tabs": tabs, "times_ms": times,
            "mean_ms": statistics.mean(times), "max_ms": max(times)}


# ── HTML report ───────────────────────────────────────────────────────────────

def build_report(initial: dict, pages: list[dict],
                 interactions: dict, upload: dict | None,
                 concurrent: dict, ts: str) -> str:

    overall_score = _overall_score(pages)

    # ── summary table rows ──
    page_rows = ""
    for p in pages:
        lbl, color = rating(p["mean_ms"])
        mem_str = f"{p['memory']['used_mb']} MB" if p.get("memory") else "—"
        page_rows += f"""
        <tr>
          <td class="page-name">{p['page']}</td>
          <td>{fmt_ms(p['mean_ms'])}</td>
          <td>{fmt_ms(p['min_ms'])}</td>
          <td>{fmt_ms(p['max_ms'])}</td>
          <td>{fmt_ms(p['p95_ms'])}</td>
          <td>{fmt_ms(p['stdev_ms'])}</td>
          <td>{mem_str}</td>
          <td><span class="badge" style="background:{color}">{lbl}</span></td>
        </tr>"""

    # ── screenshots grid ──
    ss_cards = ""
    for p in pages:
        if p.get("screenshot"):
            lbl, color = rating(p["mean_ms"])
            ss_cards += f"""
            <div class="ss-card">
              <img src="data:image/png;base64,{p['screenshot']}" alt="{p['page']}">
              <div class="ss-label">
                {p['page']}
                <span class="badge" style="background:{color};font-size:0.7rem">{fmt_ms(p['mean_ms'])}</span>
              </div>
            </div>"""

    # ── resource table ──
    res = initial.get("resources", {})
    res_rows = ""
    for rtype, info in res.get("by_type", {}).items():
        res_rows += f"""
        <tr>
          <td>{rtype}</td>
          <td>{info['count']}</td>
          <td>{fmt_kb(info['bytes'])}</td>
          <td>{info['dur']:.0f} ms</td>
        </tr>"""

    slowest_rows = ""
    for r in res.get("slowest", []):
        slowest_rows += f"""
        <tr>
          <td class="mono">{r['name']}</td>
          <td>{r['type']}</td>
          <td>{fmt_ms(r['dur_ms'])}</td>
          <td>{fmt_kb(r['bytes'])}</td>
        </tr>"""

    # ── interaction rows ──
    int_rows = ""
    for name, ms in interactions.get("interactions", []):
        lbl, color = rating(ms)
        int_rows += f"""
        <tr>
          <td>{name}</td>
          <td>{fmt_ms(ms)}</td>
          <td><span class="badge" style="background:{color}">{lbl}</span></td>
        </tr>"""

    # ── upload row ──
    upload_section = ""
    if upload:
        if upload.get("error"):
            upload_section = f'<p class="warn">Upload test error: {upload["error"]}</p>'
        else:
            lbl, color = rating(upload.get("upload_ms"))
            upload_section = f"""
            <table class="data-table"><thead>
              <tr><th>Metric</th><th>Value</th><th>Rating</th></tr>
            </thead><tbody>
              <tr>
                <td>End-to-end CSV upload + categorization</td>
                <td>{fmt_ms(upload.get('upload_ms'))}</td>
                <td><span class="badge" style="background:{color}">{lbl}</span></td>
              </tr>
            </tbody></table>"""
            if upload.get("screenshot"):
                upload_section += f'<img src="data:image/png;base64,{upload["screenshot"]}" class="upload-ss" alt="After upload">'

    # ── chart data ──
    chart_labels = json.dumps([p["page"] for p in pages])
    chart_means  = json.dumps([round(p["mean_ms"]) for p in pages])
    chart_mins   = json.dumps([round(p["min_ms"])  for p in pages])
    chart_maxs   = json.dumps([round(p["max_ms"])  for p in pages])
    chart_colors = json.dumps([
        "#16a34a" if p["mean_ms"] < 500 else
        "#65a30d" if p["mean_ms"] < 1500 else
        "#d97706" if p["mean_ms"] < 3000 else
        "#dc2626"
        for p in pages
    ])

    # ── initial load card ──
    cold_ms  = initial.get("cold_ms", 0)
    nt       = initial.get("nav_timing", {})
    mem      = initial.get("memory") or {}
    vit      = initial.get("vitals") or {}
    fcp_ms   = vit.get("fcp_ms")
    cold_lbl, cold_color = rating(cold_ms)

    # ── concurrent load ──
    conc_rows = ""
    for i, t in enumerate(concurrent.get("times_ms", []), 1):
        lbl2, color2 = rating(t)
        conc_rows += f"""
        <tr>
          <td>Tab {i}</td><td>{fmt_ms(t)}</td>
          <td><span class="badge" style="background:{color2}">{lbl2}</span></td>
        </tr>"""

    # ── recommendations ──
    recs = _recommendations(initial, pages, upload, concurrent)
    rec_items = "".join(f"<li>{r}</li>" for r in recs)

    score_color = "#16a34a" if overall_score >= 80 else "#d97706" if overall_score >= 50 else "#dc2626"
    ss_initial = initial.get("screenshot", "")
    ss_initial_tag = f'<img src="data:image/png;base64,{ss_initial}" class="full-ss" alt="Initial load">' if ss_initial else ""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>SpendWise AI — Performance Report {ts}</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
  *{{box-sizing:border-box;margin:0;padding:0}}
  body{{font-family:'Segoe UI',system-ui,sans-serif;background:#f8fafc;color:#1e293b;line-height:1.6}}
  .header{{background:linear-gradient(135deg,#1e3a8a,#2563eb);color:#fff;padding:2.5rem 3rem}}
  .header h1{{font-size:2rem;margin-bottom:.25rem}}
  .header .meta{{opacity:.8;font-size:.9rem}}
  .score-ring{{display:inline-flex;flex-direction:column;align-items:center;
               background:rgba(255,255,255,.15);border-radius:12px;padding:.8rem 1.5rem;
               float:right;margin-top:-2rem}}
  .score-ring .score-val{{font-size:3rem;font-weight:700;color:{score_color}}}
  .score-ring .score-lbl{{font-size:.8rem;opacity:.85}}
  .container{{max-width:1200px;margin:0 auto;padding:2rem 1.5rem}}
  .section{{background:#fff;border-radius:12px;box-shadow:0 1px 4px rgba(0,0,0,.08);
            padding:1.5rem;margin-bottom:1.5rem}}
  .section h2{{font-size:1.15rem;margin-bottom:1rem;color:#1e3a8a;border-bottom:2px solid #e2e8f0;padding-bottom:.5rem}}
  .kpi-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(170px,1fr));gap:1rem;margin-bottom:1rem}}
  .kpi{{background:#f1f5f9;border-radius:8px;padding:1rem;text-align:center}}
  .kpi .val{{font-size:1.6rem;font-weight:700;color:#1e3a8a}}
  .kpi .lbl{{font-size:.8rem;color:#64748b;margin-top:.2rem}}
  .data-table{{width:100%;border-collapse:collapse;font-size:.9rem}}
  .data-table th{{background:#f1f5f9;text-align:left;padding:.6rem .8rem;color:#334155;font-weight:600}}
  .data-table td{{padding:.55rem .8rem;border-bottom:1px solid #e2e8f0;vertical-align:middle}}
  .data-table tr:last-child td{{border-bottom:none}}
  .data-table tr:hover td{{background:#f8fafc}}
  .page-name{{font-weight:600}}
  .badge{{display:inline-block;color:#fff;border-radius:9999px;padding:.15rem .7rem;font-size:.8rem;font-weight:600}}
  .mono{{font-family:monospace;font-size:.82rem}}
  .chart-wrap{{position:relative;height:280px}}
  .ss-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:1rem;margin-top:1rem}}
  .ss-card{{border:1px solid #e2e8f0;border-radius:8px;overflow:hidden}}
  .ss-card img{{width:100%;display:block}}
  .ss-label{{padding:.4rem .6rem;font-size:.82rem;font-weight:600;background:#f8fafc;
             display:flex;justify-content:space-between;align-items:center}}
  .full-ss{{width:100%;border-radius:8px;border:1px solid #e2e8f0;margin-top:.5rem}}
  .upload-ss{{width:100%;border-radius:8px;border:1px solid #e2e8f0;margin-top:.75rem}}
  .warn{{color:#dc2626;font-size:.9rem;padding:.5rem;background:#fef2f2;border-radius:6px}}
  .rec-list{{list-style:none;padding:0}}
  .rec-list li{{padding:.5rem .75rem;margin-bottom:.4rem;background:#eff6ff;
                border-left:3px solid #3b82f6;border-radius:0 6px 6px 0;font-size:.9rem}}
  .two-col{{display:grid;grid-template-columns:1fr 1fr;gap:1rem}}
  @media(max-width:700px){{.two-col{{grid-template-columns:1fr}}}}
</style>
</head>
<body>
<div class="header">
  <div class="score-ring">
    <span class="score-val">{overall_score}</span>
    <span class="score-lbl">/ 100 performance score</span>
  </div>
  <h1>SpendWise AI — Performance Report</h1>
  <p class="meta">Generated: {ts} &nbsp;|&nbsp; {RUNS} runs/page &nbsp;|&nbsp; Playwright Chromium &nbsp;|&nbsp; {BASE_URL}</p>
</div>

<div class="container">

  <!-- ── KPI summary ── -->
  <div class="section">
    <h2>Executive Summary</h2>
    <div class="kpi-grid">
      <div class="kpi">
        <div class="val" style="color:{cold_color}">{fmt_ms(cold_ms)}</div>
        <div class="lbl">Cold-start load</div>
      </div>
      <div class="kpi">
        <div class="val">{fmt_ms(statistics.mean([p['mean_ms'] for p in pages]))}</div>
        <div class="lbl">Avg page nav</div>
      </div>
      <div class="kpi">
        <div class="val">{fmt_ms(max(p['mean_ms'] for p in pages))}</div>
        <div class="lbl">Slowest page</div>
      </div>
      <div class="kpi">
        <div class="val">{fmt_ms(fcp_ms) if fcp_ms else "—"}</div>
        <div class="lbl">First Contentful Paint</div>
      </div>
      <div class="kpi">
        <div class="val">{fmt_kb(res.get('total_bytes',0))}</div>
        <div class="lbl">Total transfer size</div>
      </div>
      <div class="kpi">
        <div class="val">{res.get('total_requests','—')}</div>
        <div class="lbl">Network requests</div>
      </div>
      <div class="kpi">
        <div class="val">{mem.get('used_mb','—')} MB</div>
        <div class="lbl">JS heap used</div>
      </div>
      <div class="kpi">
        <div class="val">{fmt_ms(nt.get('ttfb_ms'))}</div>
        <div class="lbl">TTFB</div>
      </div>
    </div>
  </div>

  <!-- ── Navigation timing chart ── -->
  <div class="section">
    <h2>Page Navigation Times</h2>
    <div class="chart-wrap">
      <canvas id="navChart"></canvas>
    </div>
  </div>

  <!-- ── Page detail table ── -->
  <div class="section">
    <h2>Per-Page Performance ({RUNS} runs)</h2>
    <table class="data-table">
      <thead>
        <tr>
          <th>Page</th><th>Mean</th><th>Min</th><th>Max</th>
          <th>p95</th><th>Std Dev</th><th>JS Heap</th><th>Rating</th>
        </tr>
      </thead>
      <tbody>{page_rows}</tbody>
    </table>
  </div>

  <!-- ── Cold load ── -->
  <div class="section">
    <h2>Initial Cold-Start Load</h2>
    <div class="two-col">
      <div>
        <table class="data-table">
          <thead><tr><th>Metric</th><th>Value</th></tr></thead>
          <tbody>
            <tr><td>Cold-start wall time</td><td><strong>{fmt_ms(cold_ms)}</strong></td></tr>
            <tr><td>DNS lookup</td><td>{fmt_ms(nt.get('dns_ms'))}</td></tr>
            <tr><td>TCP connect</td><td>{fmt_ms(nt.get('tcp_ms'))}</td></tr>
            <tr><td>Time to First Byte (TTFB)</td><td>{fmt_ms(nt.get('ttfb_ms'))}</td></tr>
            <tr><td>DOM Content Loaded</td><td>{fmt_ms(nt.get('dom_load_ms'))}</td></tr>
            <tr><td>Full load event</td><td>{fmt_ms(nt.get('full_load_ms'))}</td></tr>
            <tr><td>First Contentful Paint</td><td>{fmt_ms(fcp_ms) if fcp_ms else '—'}</td></tr>
          </tbody>
        </table>
      </div>
      <div>
        {ss_initial_tag}
      </div>
    </div>
  </div>

  <!-- ── Resources ── -->
  <div class="section">
    <h2>Resource Breakdown</h2>
    <div class="two-col">
      <div>
        <h3 style="font-size:.95rem;margin-bottom:.5rem;color:#334155">By type</h3>
        <table class="data-table">
          <thead><tr><th>Type</th><th>Count</th><th>Size</th><th>Duration</th></tr></thead>
          <tbody>{res_rows}</tbody>
        </table>
      </div>
      <div>
        <h3 style="font-size:.95rem;margin-bottom:.5rem;color:#334155">5 slowest resources</h3>
        <table class="data-table">
          <thead><tr><th>Name</th><th>Type</th><th>Duration</th><th>Size</th></tr></thead>
          <tbody>{slowest_rows}</tbody>
        </table>
      </div>
    </div>
  </div>

  <!-- ── Interactions ── -->
  <div class="section">
    <h2>UI Interaction Latency</h2>
    <table class="data-table">
      <thead><tr><th>Interaction</th><th>Time</th><th>Rating</th></tr></thead>
      <tbody>{int_rows}</tbody>
    </table>
  </div>

  <!-- ── CSV upload ── -->
  <div class="section">
    <h2>CSV Upload &amp; ML Categorization Pipeline</h2>
    {upload_section if upload_section else '<p style="color:#64748b">Upload test not run.</p>'}
  </div>

  <!-- ── Concurrent load ── -->
  <div class="section">
    <h2>Concurrent Load ({concurrent.get('tabs',0)} simultaneous tabs)</h2>
    <table class="data-table">
      <thead><tr><th>Tab</th><th>Load Time</th><th>Rating</th></tr></thead>
      <tbody>{conc_rows}</tbody>
    </table>
    <p style="margin-top:.75rem;font-size:.85rem;color:#64748b">
      Mean: <strong>{fmt_ms(concurrent.get('mean_ms'))}</strong> &nbsp;|&nbsp;
      Max: <strong>{fmt_ms(concurrent.get('max_ms'))}</strong>
    </p>
  </div>

  <!-- ── Screenshots ── -->
  <div class="section">
    <h2>Page Screenshots</h2>
    <div class="ss-grid">
      {ss_cards}
    </div>
  </div>

  <!-- ── Recommendations ── -->
  <div class="section">
    <h2>Recommendations</h2>
    <ul class="rec-list">{rec_items}</ul>
  </div>

</div><!-- /container -->

<script>
new Chart(document.getElementById('navChart'), {{
  type: 'bar',
  data: {{
    labels: {chart_labels},
    datasets: [
      {{label:'Mean', data:{chart_means}, backgroundColor:{chart_colors}, borderRadius:4}},
      {{label:'Min',  data:{chart_mins},  backgroundColor:'rgba(100,116,139,.35)', borderRadius:4}},
      {{label:'Max',  data:{chart_maxs},  backgroundColor:'rgba(100,116,139,.15)', borderRadius:4}},
    ]
  }},
  options: {{
    responsive:true, maintainAspectRatio:false,
    plugins:{{legend:{{position:'top'}},
              tooltip:{{callbacks:{{label:c=>c.dataset.label+': '+c.parsed.y+' ms'}}}}}},
    scales:{{
      y:{{beginAtZero:true, title:{{display:true,text:'Milliseconds'}}}},
      x:{{grid:{{display:false}}}}
    }}
  }}
}});
</script>
</body>
</html>"""


def _overall_score(pages: list[dict]) -> int:
    """0-100 score based on mean navigation times."""
    scores = []
    for p in pages:
        ms = p["mean_ms"]
        if   ms < 500:   scores.append(100)
        elif ms < 1000:  scores.append(85)
        elif ms < 2000:  scores.append(65)
        elif ms < 4000:  scores.append(40)
        else:            scores.append(15)
    return round(statistics.mean(scores)) if scores else 0


def _recommendations(initial, pages, upload, concurrent) -> list[str]:
    recs = []
    for p in pages:
        if p["mean_ms"] > 3000:
            recs.append(
                f"<strong>{p['page']}</strong> averages {fmt_ms(p['mean_ms'])} — "
                "consider caching the ML computation with <code>@st.cache_data</code> "
                "or reducing dataset size for faster re-renders."
            )
    mem = (initial.get("memory") or {}).get("used_mb", 0)
    if mem and mem > 150:
        recs.append(
            f"JS heap is {mem} MB on load. Streamlit ships all dataframe data to the browser; "
            "paginate large tables or use <code>st.dataframe(height=...)</code> to limit rows."
        )
    res = initial.get("resources", {})
    if res.get("total_bytes", 0) > 3_000_000:
        recs.append(
            f"Total transfer is {fmt_kb(res['total_bytes'])}. "
            "Enable Streamlit's static-file compression or serve behind a CDN/reverse proxy."
        )
    if concurrent.get("max_ms", 0) > concurrent.get("mean_ms", 0) * 2:
        recs.append(
            "Max concurrent-tab load is 2× the mean — Streamlit spawns one Python thread per session. "
            "For multi-user load, consider running multiple Streamlit workers behind a load balancer."
        )
    if not recs:
        recs.append("All pages are within acceptable performance thresholds. Great work!")
    return recs


# ── entry point ───────────────────────────────────────────────────────────────

def main():
    global RUNS, BASE_URL  # noqa: PLW0603
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", type=int, default=RUNS)
    ap.add_argument("--url",  default=BASE_URL)
    ap.add_argument("--out",  default=str(REPORT_DIR))
    args = ap.parse_args()

    RUNS     = args.runs
    BASE_URL = args.url

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    print(f"\nSpendWise AI — Playwright Performance Suite")
    print(f"Target : {BASE_URL}")
    print(f"Runs   : {RUNS} per page\n")

    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            headless=True,
            args=["--enable-precise-memory-info", "--js-flags=--expose-gc"],
        )

        initial     = run_initial_load(browser)
        page_navs   = run_page_navigations(browser)
        interactions = run_interaction_perf(browser)
        upload_res  = run_csv_upload(browser)
        concurrent  = run_concurrent_load(browser)

        browser.close()

    report_html = build_report(initial, page_navs, interactions,
                               upload_res, concurrent, ts)

    out_path = REPORT_DIR / f"perf_report_{ts}.html"
    out_path.write_text(report_html, encoding="utf-8")

    print(f"\nDone. Report saved to:\n  {out_path}\n")

    # print quick summary
    print(f"{'Page':<16} {'Mean':>8} {'Min':>8} {'Max':>8}  Rating")
    print("-" * 55)
    for p in page_navs:
        lbl, _ = rating(p["mean_ms"])
        print(f"{p['page']:<16} {fmt_ms(p['mean_ms']):>8} {fmt_ms(p['min_ms']):>8} {fmt_ms(p['max_ms']):>8}  {lbl}")
    print(f"\nOverall score: {_overall_score(page_navs)} / 100")
    return str(out_path)


if __name__ == "__main__":
    # Unicode output fix only when run directly (not when imported)
    if hasattr(sys.stdout, "buffer"):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    main()
