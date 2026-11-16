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

# ── Credentials store ────────────────────────────────────────────────────────
USERS = {
    "admin":      "spendwise123",
    "spendwise":  "finance@2026",
}

# ── Auth gate ─────────────────────────────────────────────────────────────────
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.markdown("""
<style>
html, body, .stApp { background: #13131f; font-family: 'Inter','Segoe UI',sans-serif; }
.login-wrap {
    max-width: 420px; margin: 6vh auto 0; padding: 2.5rem 2.5rem 2rem;
    background: #1e1e2e;
    border: 1px solid rgba(255,79,31,.25);
    border-radius: 24px;
    box-shadow: 0 20px 60px rgba(0,0,0,.5);
}
.login-logo {
    display: flex; align-items: center; gap: .75rem;
    justify-content: center; margin-bottom: 1.8rem;
}
.login-brand {
    font-size: 2rem; font-weight: 800; color: #f0f0f5; letter-spacing: -.03em;
}
.login-brand span { color: #ff4f1f; }
.login-title {
    font-size: 1.3rem; font-weight: 700; color: #f0f0f5;
    text-align: center; margin-bottom: .3rem;
}
.login-sub {
    font-size: .92rem; color: #6868a0;
    text-align: center; margin-bottom: 1.8rem;
}
.login-divider {
    border: none; border-top: 1px solid rgba(255,255,255,.07); margin: 1.4rem 0;
}
.login-footer {
    text-align: center; font-size: .8rem; color: #3a3a5a; margin-top: 1.2rem;
}
/* Input styling */
input[type="text"], input[type="password"] {
    background: #13131f !important;
    border: 1.5px solid rgba(255,79,31,.3) !important;
    border-radius: 10px !important;
    color: #f0f0f5 !important;
    font-size: 1rem !important;
    padding: .6rem 1rem !important;
}
input[type="text"]:focus, input[type="password"]:focus {
    border-color: #ff4f1f !important;
    box-shadow: 0 0 0 3px rgba(255,79,31,.18) !important;
}
label { color: #9898c0 !important; font-size: .95rem !important; }
/* Login button */
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg,#ff4f1f,#ff7a3d) !important;
    border: none !important; color: #fff !important;
    font-size: 1.05rem !important; font-weight: 700 !important;
    border-radius: 12px !important; padding: .65rem 1rem !important;
    width: 100% !important;
    box-shadow: 0 4px 18px rgba(255,79,31,.4) !important;
    transition: transform .2s, box-shadow .2s !important;
}
.stButton > button[kind="primary"]:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 8px 28px rgba(255,79,31,.55) !important;
}
</style>
""", unsafe_allow_html=True)

    st.markdown("""
<div class="login-wrap">
  <div class="login-logo">
    <svg width="40" height="40" viewBox="0 0 42 42" fill="none" xmlns="http://www.w3.org/2000/svg">
      <rect width="42" height="42" rx="12" fill="url(#lg)"/>
      <polyline points="7,30 14,21 20,25 27,14 35,18"
                stroke="white" stroke-width="2.8" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
      <circle cx="35" cy="18" r="2.5" fill="white"/>
      <defs>
        <linearGradient id="lg" x1="0" y1="0" x2="42" y2="42" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stop-color="#ff4f1f"/>
          <stop offset="100%" stop-color="#ff8c42"/>
        </linearGradient>
      </defs>
    </svg>
    <div class="login-brand">Spend<span>Wise</span></div>
  </div>
  <div class="login-title">Welcome back</div>
  <div class="login-sub">Sign in to your finance dashboard</div>
</div>
""", unsafe_allow_html=True)

    with st.container():
        _, mid, _ = st.columns([1, 2.5, 1])
        with mid:
            username = st.text_input("Username", placeholder="Enter username", key="login_user")
            password = st.text_input("Password", placeholder="Enter password", type="password", key="login_pass")
            st.write("")
            login_btn = st.button("Sign In →", type="primary", use_container_width=True)

            if login_btn:
                if username in USERS and USERS[username] == password:
                    st.session_state.authenticated = True
                    st.session_state.logged_in_user = username
                    st.rerun()
                else:
                    st.error("Invalid username or password.")

    st.markdown("""
<div style="text-align:center;margin-top:1.5rem;font-size:.82rem;color:#3a3a5a;">
  © 2026 SpendWise &nbsp;·&nbsp; Personal Finance Intelligence
</div>
""", unsafe_allow_html=True)

    st.stop()

# ── Theme state (must come before CSS injection) ─────────────────────────────
if "dark_mode" not in st.session_state:
    st.session_state.dark_mode = True

_dark = st.session_state.dark_mode

# ── Colour tokens ─────────────────────────────────────────────────────────────
if _dark:
    _bg        = "#13131f"
    _card      = "#1e1e2e"
    _sidebar   = "#13131f"
    _text      = "#f0f0f5"
    _muted     = "#6868a0"
    _border    = "rgba(255,255,255,.05)"
    _inputbg   = "#1e1e2e"
    _inputbdr  = "rgba(255,255,255,.08)"
    _metricbg  = "#1e1e2e"
    _sectionc  = "#9898c0"
    _dfborder  = "rgba(255,255,255,.05)"
    _expbg     = "#1e1e2e"
else:
    _bg        = "#f0f2f8"
    _card      = "#ffffff"
    _sidebar   = "#ffffff"
    _text      = "#1a1a2e"
    _muted     = "#7070a0"
    _border    = "rgba(0,0,0,.08)"
    _inputbg   = "#ffffff"
    _inputbdr  = "rgba(0,0,0,.12)"
    _metricbg  = "#ffffff"
    _sectionc  = "#555580"
    _dfborder  = "rgba(0,0,0,.08)"
    _expbg     = "#ffffff"

# ── Design system — Dynamic theme ────────────────────────────────────────────
st.markdown(f"""
<style>
/* ── Base typography ────────────────────────────────────────────── */
html, body, [class*="css"] {{
    font-family: 'Inter', 'Segoe UI', system-ui, sans-serif;
    font-size: 16px !important;
    color: {_text} !important;
}}

/* ── Theme-sensitive overrides ──────────────────────────────────── */
.stApp                                      {{ background: {_bg} !important; }}
[data-testid="stSidebar"]                   {{ background: {_sidebar} !important; }}
.kpi-card, [data-testid="stMetric"]         {{ background: {_card}; }}
[data-testid="stExpander"]                  {{ background: {_expbg} !important; }}
[data-testid="stDataFrame"]                 {{ border-color: {_dfborder} !important; }}
[data-testid="stSelectbox"] > div > div,
.stTextInput > div > div > input            {{ background: {_inputbg} !important; border-color: {_inputbdr} !important; color: {_text} !important; }}
[data-testid="stFileUploader"]              {{ background: {_inputbg} !important; }}
.sec-header                                 {{ color: {_sectionc}; border-color: {_border}; }}
.profile-card                               {{ background: {_card}; }}
.notif-btn                                  {{ background: {_card}; }}
hr                                          {{ border-color: {_border} !important; }}
.stMarkdown p                               {{ color: {_text} !important; }}
[data-testid="stMetricLabel"]               {{ color: {_muted} !important; }}
[data-testid="stMetricValue"]               {{ color: {_text} !important; }}
.kpi-value                                  {{ color: {_text} !important; }}
.kpi-label                                  {{ color: {_muted} !important; }}
.kpi-delta                                  {{ color: {_muted} !important; }}
.brand-name                                 {{ color: {_text} !important; }}
.brand-tagline                              {{ color: {_muted} !important; }}
.profile-name                               {{ color: {_text} !important; }}
.profile-role                               {{ color: {_muted} !important; }}
.page-title                                 {{ color: {_text} !important; }}
.page-subtitle                              {{ color: {_muted} !important; }}
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] span,
[data-testid="stSidebar"] label             {{ color: {_muted} !important; }}
</style>
""", unsafe_allow_html=True)

# ── Static design system (accent colours, layout — same in both modes) ────────
st.markdown("""
<style>
/* Global readable body text */
p, li, span, div, label, td, th {
    font-size: 1rem !important;
    line-height: 1.6 !important;
}
.stMarkdown p { font-size: 1rem !important; color: #c8c8e0 !important; }

/* ── App shell ──────────────────────────────────────────────────── */
.stApp {
    background: #13131f;
}

/* ── Sidebar ────────────────────────────────────────────────────── */
[data-testid="stSidebar"] {
    background: #13131f !important;
    border-right: 2px solid rgba(255,79,31,.55) !important;
}
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] span,
[data-testid="stSidebar"] label { color: #9999b8 !important; }

/* ── Brand ──────────────────────────────────────────────────────── */
.brand-wrap { padding: .4rem 0 1.1rem; }
.brand-logo-row {
    display: flex; align-items: center; gap: .75rem;
}
.brand-header-row {
    display: flex; align-items: center;
    justify-content: space-between; width: 100%;
}
.notif-btn {
    position: relative; cursor: pointer;
    background: #1e1e2e;
    border: 1px solid rgba(255,79,31,.2);
    border-radius: 10px;
    width: 38px; height: 38px;
    display: flex; align-items: center; justify-content: center;
    font-size: 1.2rem;
    transition: background .2s, border-color .2s;
    flex-shrink: 0;
}
.notif-btn:hover {
    background: rgba(255,79,31,.15);
    border-color: rgba(255,79,31,.5);
}
.notif-badge {
    position: absolute; top: -5px; right: -5px;
    background: #ff4f1f;
    color: #fff; font-size: .62rem; font-weight: 700;
    width: 17px; height: 17px; border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    border: 2px solid #13131f;
    line-height: 1;
}
.brand-name {
    font-size: 2.4rem !important; font-weight: 800; letter-spacing: -.03em; color: #f0f0f5;
    line-height: 1.1;
}
.brand-name span { color: #ff4f1f; font-size: 2.4rem !important; }
.brand-tagline {
    font-size: .95rem; font-weight: 500; color: #c0c0e0;
    letter-spacing: .04em; margin-top: 4px;
}

/* ── Nav radio ──────────────────────────────────────────────────── */
[data-testid="stRadio"] > div { gap: 4px !important; }
[data-testid="stRadio"] label {
    padding: .7rem 1.1rem !important; border-radius: 10px !important;
    font-size: 1.15rem !important; font-weight: 500 !important;
    color: #ffffff !important; cursor: pointer;
    transition: background .15s, color .15s;
}
[data-testid="stRadio"] label:hover {
    background: rgba(255,79,31,.12) !important; color: #ff7a50 !important;
}
[data-testid="stRadio"] label[data-checked="true"],
[data-testid="stRadio"] label:has(input:checked) {
    background: rgba(255,79,31,.18) !important;
    color: #ff6035 !important; font-weight: 700 !important;
}

/* ── Page title ─────────────────────────────────────────────────── */
.page-title {
    font-size: 2.2rem; font-weight: 800; letter-spacing: -.03em;
    color: #f0f0f5; line-height: 1.15; margin-bottom: .2rem;
}
.page-title span { color: #ff4f1f; }
.page-subtitle { font-size: 1rem; color: #6a6a8a; margin-bottom: 1.6rem; letter-spacing: .01em; }

/* ── KPI card ───────────────────────────────────────────────────── */
.kpi-card {
    background: #1e1e2e;
    border: 1px solid rgba(255,255,255,.04);
    border-radius: 20px;
    padding: 1.4rem 1.5rem 1.6rem;
    position: relative; overflow: hidden;
    box-shadow: 0 8px 32px rgba(0,0,0,.35);
    transition: transform .2s ease, box-shadow .2s ease;
}
.kpi-card:hover {
    transform: translateY(-4px);
    box-shadow: 0 12px 40px rgba(255,79,31,.18);
}
.kpi-card .kpi-accent-bar {
    position: absolute; bottom: 0; left: 0; right: 0; height: 3px;
    background: linear-gradient(90deg, #ff4f1f, #ff7a3d);
    border-radius: 0 0 20px 20px;
}
.kpi-label {
    font-size: .82rem; color: #6868a0; text-transform: uppercase;
    letter-spacing: .1em; margin-bottom: .55rem;
}
.kpi-value {
    font-size: 2.1rem; font-weight: 800; color: #f0f0f5; line-height: 1;
    letter-spacing: -.02em;
}
.kpi-delta { font-size: .92rem; font-weight: 600; margin-top: .55rem; }
.kpi-delta.up     { color: #ff4f1f; }
.kpi-delta.down   { color: #ff4f1f; }
.kpi-delta.neutral{ color: #6868a0; }
.kpi-icon {
    position: absolute; top: 1.1rem; right: 1.2rem;
    font-size: 1.9rem; opacity: 1;
    line-height: 1;
}

/* ── Section header ─────────────────────────────────────────────── */
.sec-header {
    font-size: .95rem; font-weight: 700; color: #9898c0;
    text-transform: uppercase; letter-spacing: .1em;
    padding-bottom: .55rem;
    border-bottom: 1px solid rgba(255,255,255,.07);
    margin-bottom: 1.1rem;
}

/* ── Info / anomaly / good banners ──────────────────────────────── */
.info-banner {
    background: rgba(255,79,31,.07); border: 1px solid rgba(255,79,31,.22);
    border-radius: 12px; padding: .85rem 1.2rem; color: #ff9070;
    font-size: 1rem; margin-bottom: 1rem; line-height: 1.6;
}
.anomaly-card {
    background: rgba(255,79,31,.07); border-left: 3px solid #ff4f1f;
    border-radius: 0 12px 12px 0; padding: .85rem 1.1rem; margin-bottom: .6rem;
}
.anomaly-card strong { color: #f0f0f5; }
.anomaly-card small, .anomaly-card em { color: #ff9070; display: block; margin-top: 3px; }
.good-card {
    background: rgba(34,197,94,.07); border-left: 3px solid #22c55e;
    border-radius: 0 12px 12px 0; padding: .85rem 1.1rem; margin-bottom: .6rem;
}
.good-card strong { color: #f0f0f5; }
.good-card small, .good-card em { color: #86efac; display: block; margin-top: 3px; }

/* ── Stat mini-card (compact) ───────────────────────────────────── */
.stat-row {
    display: flex; gap: .6rem; margin-bottom: 1rem; flex-wrap: wrap;
}
.stat-chip {
    background: #1e1e2e; border: 1px solid rgba(255,255,255,.05);
    border-radius: 12px; padding: .6rem 1rem;
    display: flex; flex-direction: column; min-width: 120px;
}
.stat-chip .s-label { font-size: .82rem; color: #6868a0; text-transform: uppercase; letter-spacing: .08em; }
.stat-chip .s-value { font-size: 1.25rem; font-weight: 700; color: #f0f0f5; margin-top: 2px; }

/* ── Buttons ────────────────────────────────────────────────────── */
.stButton > button {
    border-radius: 10px !important; font-weight: 600 !important;
    transition: all .2s ease !important; font-size: 1rem !important;
    letter-spacing: .01em !important; padding: .45rem 1.1rem !important;
}
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #ff4f1f 0%, #ff7a3d 100%) !important;
    border: none !important; color: #fff !important;
}
.stButton > button[kind="primary"]:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 6px 24px rgba(255,79,31,.5) !important;
}
.stButton > button[kind="secondary"] {
    background: rgba(255,79,31,.1) !important;
    border: 1px solid rgba(255,79,31,.3) !important;
    color: #ff7050 !important;
}

/* ── Divider ────────────────────────────────────────────────────── */
hr { border: none !important; border-top: 1px solid rgba(255,255,255,.05) !important; margin: 1.4rem 0 !important; }

/* ── Dataframe ──────────────────────────────────────────────────── */
[data-testid="stDataFrame"] {
    border-radius: 16px !important; overflow: hidden;
    border: 1px solid rgba(255,255,255,.05) !important;
    box-shadow: 0 4px 20px rgba(0,0,0,.3) !important;
}

/* ── Expander ───────────────────────────────────────────────────── */
[data-testid="stExpander"] {
    background: #1e1e2e !important;
    border: 1px solid rgba(255,255,255,.05) !important;
    border-radius: 14px !important; margin-bottom: .5rem;
    box-shadow: 0 2px 12px rgba(0,0,0,.2);
}

/* ── Progress bar ───────────────────────────────────────────────── */
.stProgress > div > div > div {
    background: linear-gradient(90deg, #ff4f1f, #ff7a3d) !important;
    border-radius: 100px;
}

/* ── File uploader ──────────────────────────────────────────────── */
[data-testid="stFileUploader"] {
    background: #1e1e2e !important;
    border: 2px dashed rgba(255,79,31,.3) !important;
    border-radius: 14px !important;
}
[data-testid="stFileUploader"]:hover { border-color: rgba(255,79,31,.6) !important; }

/* ── Spinner ────────────────────────────────────────────────────── */
.stSpinner > div { border-top-color: #ff4f1f !important; }

/* ── st.metric fallback ─────────────────────────────────────────── */
[data-testid="stMetric"] {
    background: #1e1e2e;
    border: 1px solid rgba(255,255,255,.05);
    border-radius: 16px; padding: 1.1rem 1.3rem;
    box-shadow: 0 4px 16px rgba(0,0,0,.25);
}
[data-testid="stMetricLabel"] {
    font-size: .9rem !important; color: #6868a0 !important;
    text-transform: uppercase; letter-spacing: .08em;
}
[data-testid="stMetricValue"] {
    font-size: 2rem !important; font-weight: 800 !important; color: #f0f0f5 !important;
}
[data-testid="stMetricDelta"] { color: #ff4f1f !important; font-weight: 600 !important; font-size: 1rem !important; }

/* ── Chart containers ───────────────────────────────────────────── */
[data-testid="stVegaLiteChart"],
[data-testid="stArrowVegaLiteChart"] {
    background: #1e1e2e !important;
    border: 1px solid rgba(255,255,255,.05) !important;
    border-radius: 16px; padding: .5rem;
    box-shadow: 0 4px 20px rgba(0,0,0,.25);
}

/* ── Selectbox / text input ─────────────────────────────────────── */
[data-testid="stSelectbox"] > div > div,
.stTextInput > div > div > input {
    background: #1e1e2e !important;
    border: 1px solid rgba(255,255,255,.08) !important;
    border-radius: 10px !important; color: #f0f0f5 !important;
}
.stTextInput > div > div > input:focus {
    border-color: rgba(255,79,31,.5) !important;
    box-shadow: 0 0 0 2px rgba(255,79,31,.12) !important;
}

/* ── Suggestion pill buttons ────────────────────────────────────── */
.sug-row .stButton > button {
    background: #1e1e2e !important;
    border: 1px solid rgba(255,79,31,.25) !important;
    color: #ff7050 !important; font-size: .8rem !important;
    border-radius: 100px !important;
}
.sug-row .stButton > button:hover {
    background: rgba(255,79,31,.12) !important; transform: none !important;
}

/* ── Empty state ────────────────────────────────────────────────── */
.empty-state {
    background: #1e1e2e; border: 1px dashed rgba(255,79,31,.25);
    border-radius: 20px; padding: 3.5rem 2rem; text-align: center; margin: 2rem 0;
    box-shadow: 0 8px 32px rgba(0,0,0,.3);
}
.empty-icon { font-size: 3rem; margin-bottom: 1rem; opacity: .6; }
.empty-title { font-size: 1.3rem; font-weight: 800; color: #f0f0f5; margin-bottom: .5rem; }
.empty-desc  { font-size: .86rem; color: #4a4a6a; max-width: 420px; margin: 0 auto 1.5rem; line-height: 1.6; }

/* ── Checkbox ───────────────────────────────────────────────────── */
[data-testid="stCheckbox"] span { color: #9999b8 !important; font-size: 1rem !important; }

/* ── Dashboard search + date filter bar ────────────────────────── */
.search-bar-wrap {
    background: #1e1e2e;
    border: 1px solid rgba(255,79,31,.25);
    border-radius: 16px;
    padding: 1rem 1.2rem .8rem;
    margin-bottom: 1.4rem;
}
/* Search input */
.search-bar-wrap input[type="text"],
input[placeholder*="Search by description"] {
    background: #13131f !important;
    border: 1.5px solid rgba(255,79,31,.3) !important;
    border-radius: 10px !important;
    font-size: 1rem !important;
    color: #f0f0f5 !important;
    transition: border-color .2s, box-shadow .2s !important;
}
input[placeholder*="Search by description"]:focus {
    border-color: #ff4f1f !important;
    box-shadow: 0 0 0 3px rgba(255,79,31,.18) !important;
}
/* Date inputs */
.search-bar-wrap input[type="date"],
[data-testid="stDateInput"] input {
    background: #13131f !important;
    border: 1.5px solid rgba(255,79,31,.3) !important;
    border-radius: 10px !important;
    color: #f0f0f5 !important;
    font-size: .95rem !important;
}
[data-testid="stDateInput"] label { font-size: .85rem !important; color: #6868a0 !important; }
/* Clear button */
.search-bar-wrap .stButton > button {
    background: rgba(239,68,68,.1) !important;
    border: 1px solid rgba(239,68,68,.3) !important;
    color: #f87171 !important;
    border-radius: 10px !important;
    font-size: 1rem !important; font-weight: 700 !important;
    padding: .4rem .7rem !important;
}
.search-bar-wrap .stButton > button:hover {
    background: rgba(239,68,68,.22) !important;
    border-color: rgba(239,68,68,.55) !important;
}

/* ── Dashboard search bar ───────────────────────────────────────── */
[data-testid="stTextInput"]:has(input[aria-label=""]) > div > div > input,
input[placeholder*="Search transactions"] {
    background: #1e1e2e !important;
    border: 1.5px solid rgba(255,79,31,.35) !important;
    border-radius: 12px !important;
    padding: .65rem 1.1rem !important;
    font-size: 1rem !important;
    color: #f0f0f5 !important;
    width: 100% !important;
    transition: border-color .2s, box-shadow .2s !important;
}
input[placeholder*="Search transactions"]:focus {
    border-color: #ff4f1f !important;
    box-shadow: 0 0 0 3px rgba(255,79,31,.18) !important;
    outline: none !important;
}

/* ── Dashboard footer ───────────────────────────────────────────── */
.dash-footer {
    margin-top: 3rem;
    border-top: 1px solid rgba(255,79,31,.2);
    padding-top: 1.5rem;
}
.dash-footer-inner {
    display: flex; flex-direction: column; gap: .9rem;
    align-items: center; text-align: center;
}
.dash-footer-brand {
    display: flex; align-items: center; gap: .6rem;
    font-size: 1rem; color: #9898c0;
}
.dash-footer-brand strong { color: #ff4f1f; }
.dash-footer-links {
    display: flex; gap: 2rem;
    font-size: .9rem; color: #55557a;
}
.dash-footer-links span {
    cursor: pointer; transition: color .15s;
}
.dash-footer-links span:hover { color: #ff4f1f !important; }
.dash-footer-copy {
    font-size: .82rem; color: #3a3a5a; margin-top: .2rem;
}

/* ── Logout button ──────────────────────────────────────────────── */
[data-testid="stSidebar"] [data-testid="stButton"]:has(button[key="logout_btn"]) button,
[data-testid="stSidebar"] .stButton:last-child > button {
    background: rgba(239,68,68,.1) !important;
    border: 1px solid rgba(239,68,68,.35) !important;
    color: #f87171 !important;
    font-weight: 600 !important;
    border-radius: 10px !important;
    margin-top: .3rem;
    transition: background .2s, border-color .2s !important;
}
[data-testid="stSidebar"] .stButton:last-child > button:hover {
    background: rgba(239,68,68,.22) !important;
    border-color: rgba(239,68,68,.6) !important;
}

/* ── Profile card ───────────────────────────────────────────────── */
.profile-card {
    display: flex; align-items: center; gap: .75rem;
    background: #1e1e2e;
    border: 1px solid rgba(255,79,31,.2);
    border-radius: 14px; padding: .8rem 1rem;
    margin-top: .5rem;
}
.profile-avatar {
    position: relative; flex-shrink: 0;
}
.online-dot {
    position: absolute; bottom: 1px; right: 1px;
    width: 11px; height: 11px; border-radius: 50%;
    background: #22c55e; border: 2px solid #13131f;
}
.profile-info { flex: 1; min-width: 0; }
.profile-name {
    font-size: 1rem; font-weight: 700; color: #f0f0f5;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.profile-role {
    font-size: .82rem; color: #6868a0; margin-top: 1px;
}
.profile-menu {
    font-size: 1.3rem; color: #55557a; cursor: pointer;
    padding: 0 .2rem; letter-spacing: .05em;
    transition: color .15s;
}
.profile-menu:hover { color: #ff4f1f; }

/* ── Caption / small text — force readable size ─────────────────── */
.stCaption, [data-testid="stCaptionContainer"] p,
small { font-size: .95rem !important; color: #7878a0 !important; }

/* ── Selectbox label & value ────────────────────────────────────── */
[data-testid="stSelectbox"] label,
[data-testid="stSelectbox"] [data-baseweb="select"] span { font-size: 1rem !important; }

/* ── Text input label ───────────────────────────────────────────── */
.stTextInput label { font-size: 1rem !important; color: #9898c0 !important; }

/* ── Anomaly / good card text ───────────────────────────────────── */
.anomaly-card, .anomaly-card strong, .anomaly-card small, .anomaly-card em,
.good-card,    .good-card strong,    .good-card small,    .good-card em {
    font-size: 1rem !important; line-height: 1.65 !important;
}

/* ── Dataframe cell text ────────────────────────────────────────── */
[data-testid="stDataFrame"] td,
[data-testid="stDataFrame"] th { font-size: .95rem !important; }

/* ── Review page column header labels ──────────────────────────── */
.review-col-header { font-size: .9rem !important; color: #7878a0; text-transform: uppercase; letter-spacing: .08em; }

/* ── Expander summary text ──────────────────────────────────────── */
[data-testid="stExpander"] summary p { font-size: 1rem !important; }

/* ── Number input ───────────────────────────────────────────────── */
.stNumberInput label { font-size: 1rem !important; color: #9898c0 !important; }

/* ── Form ───────────────────────────────────────────────────────── */
[data-testid="stForm"] label { font-size: 1rem !important; }
</style>
""", unsafe_allow_html=True)


# ── Helpers ────────────────────────────────────────────────────────────────
def page_title(icon: str, title: str, subtitle: str = ""):
    st.markdown(
        f'<div class="page-title"><span>{icon}</span> {title}</div>'
        f'<div class="page-subtitle">{subtitle}</div>',
        unsafe_allow_html=True,
    )


def kpi_card(label: str, value: str, delta: str = "", icon: str = "", delta_dir: str = "neutral"):
    delta_html = f'<div class="kpi-delta {delta_dir}">{delta}</div>' if delta else ""
    st.markdown(f"""
<div class="kpi-card">
  <div class="kpi-accent-bar"></div>
  <span class="kpi-icon">{icon}</span>
  <div class="kpi-label">{label}</div>
  <div class="kpi-value">{value}</div>
  {delta_html}
</div>""", unsafe_allow_html=True)


def sec_header(text: str):
    st.markdown(f'<div class="sec-header">{text}</div>', unsafe_allow_html=True)


def fmt_inr(val):
    return f"₹{val:,.0f}"


def pct_delta(a, b):
    if b == 0:
        return None
    return f"{100*(a/b - 1):+.1f}%"


def pct_dir(a, b):
    if b == 0:
        return "neutral"
    return "up" if a <= b else "down"


# ── Data loading ───────────────────────────────────────────────────────────
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
        raise
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


# ── Sidebar ────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
<div class="brand-wrap">
  <div class="brand-header-row">
    <div class="brand-logo-row">
      <svg width="42" height="42" viewBox="0 0 42 42" fill="none" xmlns="http://www.w3.org/2000/svg">
        <rect width="42" height="42" rx="12" fill="url(#grad)"/>
        <polyline points="7,30 14,21 20,25 27,14 35,18"
                  stroke="white" stroke-width="2.8" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
        <circle cx="35" cy="18" r="2.5" fill="white"/>
        <defs>
          <linearGradient id="grad" x1="0" y1="0" x2="42" y2="42" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stop-color="#ff4f1f"/>
            <stop offset="100%" stop-color="#ff8c42"/>
          </linearGradient>
        </defs>
      </svg>
      <div>
        <div class="brand-name">Spend<span>Wise</span></div>
        <div class="brand-tagline">Personal Finance Intelligence</div>
      </div>
    </div>
    <div style="display:flex;align-items:center;gap:.45rem;">
      <div class="notif-btn">
        🔔
        <span class="notif-badge">3</span>
      </div>
      <div class="notif-btn">
        ⚙️
      </div>
    </div>
  </div>
</div>""", unsafe_allow_html=True)

    # Dark / light mode toggle
    tog_col, tog_label = st.columns([1, 3])
    with tog_col:
        new_mode = st.toggle("", value=st.session_state.dark_mode, key="_dm_toggle",
                             label_visibility="collapsed")
    with tog_label:
        st.markdown(
            f'<div style="padding-top:.45rem;font-size:.95rem;color:#9898c0;">'
            f'{"🌙 Dark mode" if st.session_state.dark_mode else "☀️ Light mode"}</div>',
            unsafe_allow_html=True,
        )
    if new_mode != st.session_state.dark_mode:
        st.session_state.dark_mode = new_mode
        st.rerun()

    st.divider()

    page = st.radio(
        "nav",
        ["Dashboard", "Transactions", "Review", "Patterns", "Anomalies", "Forecast", "Budget", "Ask AI"],
        label_visibility="collapsed",
        format_func=lambda x: {
            "Dashboard":    "🏠  Dashboard",
            "Transactions": "💳  Transactions",
            "Review":       "✏️  Review",
            "Patterns":     "📊  Patterns",
            "Anomalies":    "⚠️  Anomalies",
            "Forecast":     "🔮  Forecast",
            "Budget":       "🎯  Budget",
            "Ask AI":       "🤖  Ask AI",
        }.get(x, x),
    )

    st.divider()

    col_r, col_rc = st.columns(2)
    with col_r:
        if st.button("↺ Refresh", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
    with col_rc:
        if st.button("Re-tag all", use_container_width=True,
                     help="Re-run ML + rule classifier on every stored transaction"):
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
    st.markdown('<span style="font-size:.95rem;color:#7878a0;text-transform:uppercase;letter-spacing:.08em;font-weight:600;">Upload statement</span>', unsafe_allow_html=True)
    st.caption("CSV · Excel · ODS · PDF · TSV · TXT")

    uploaded = st.file_uploader(
        "Bank statement",
        type=["csv", "xlsx", "xls", "ods", "pdf", "tsv", "txt"],
        label_visibility="collapsed",
    )
    replace_existing = st.checkbox("Replace all existing data", value=False)

    if uploaded:
        st.caption(f"📎 {uploaded.name}")
        is_pdf = uploaded.name.lower().endswith(".pdf")
        pdf_needs_password = st.session_state.get("pdf_needs_password", False)
        pdf_password = None
        if is_pdf:
            if pdf_needs_password:
                st.warning("PDF is password-protected.")
            pdf_password = st.text_input("PDF password (blank if none)", type="password", key="pdf_pw")

        if st.button("⬆ Import", type="primary", use_container_width=True):
            from spendwise.data import PDFPasswordRequired
            with st.spinner(f"Parsing & categorising…"):
                try:
                    new_df, all_df = upload_and_process(
                        uploaded, replace=replace_existing,
                        pdf_password=pdf_password if pdf_password else None,
                    )
                    st.session_state.pdf_needs_password = False
                    deb = new_df[new_df["direction"] == "debit"]
                    st.success(f"✓ {len(new_df)} rows imported ({len(deb)} expenses). Total: {len(all_df)}")
                    st.cache_data.clear()
                    st.rerun()
                except PDFPasswordRequired:
                    st.session_state.pdf_needs_password = True
                    st.error("PDF is password-protected — enter password above.")
                except Exception as exc:
                    st.error(f"Import failed: {exc}")

    # ── Profile card at bottom of sidebar ─────────────────────────
    st.markdown("<div style='flex:1'></div>", unsafe_allow_html=True)
    st.divider()
    st.markdown("""
<div class="profile-card">
  <div class="profile-avatar">
    <svg width="44" height="44" viewBox="0 0 44 44" xmlns="http://www.w3.org/2000/svg">
      <circle cx="22" cy="22" r="22" fill="url(#avatarGrad)"/>
      <text x="22" y="27" text-anchor="middle"
            font-family="Inter,Segoe UI,sans-serif" font-size="17" font-weight="700"
            fill="white">M</text>
      <defs>
        <linearGradient id="avatarGrad" x1="0" y1="0" x2="44" y2="44" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stop-color="#ff4f1f"/>
          <stop offset="100%" stop-color="#ff8c42"/>
        </linearGradient>
      </defs>
    </svg>
    <span class="online-dot"></span>
  </div>
  <div class="profile-info">
    <div class="profile-name">My Account</div>
    <div class="profile-role">Finance User</div>
  </div>
</div>
""", unsafe_allow_html=True)
    if st.button("⏻  Log out", use_container_width=True, key="logout_btn"):
        st.session_state.authenticated = False
        st.session_state.logged_in_user = ""
        st.rerun()

df = get_data()

if df is not None:
    _unc = int((df["category"] == "Uncategorized").sum())
    if _unc > 0:
        with st.sidebar:
            st.markdown(
                f'<div style="background:rgba(255,79,31,.1);border:1px solid rgba(255,79,31,.3);'
                f'border-radius:10px;padding:.7rem 1rem;font-size:1rem;color:#ff9070;">'
                f'⚠️ {_unc} uncategorized — go to <strong>Review</strong></div>',
                unsafe_allow_html=True,
            )

# ── Empty / onboarding state ───────────────────────────────────────────────
if df is None:
    page_title("💰", "SpendWise AI", "Personal finance powered by machine learning")

    st.markdown("""
<div class="empty-state">
  <div class="empty-icon">📂</div>
  <div class="empty-title">No transactions yet</div>
  <div class="empty-desc">Upload your bank statement from the sidebar, or run the sample data command below to get started.</div>
</div>""", unsafe_allow_html=True)

    col_a, col_b = st.columns(2)
    with col_a:
        sec_header("Upload your bank statement")
        st.markdown(
            '<div class="info-banner">'
            "Use the <strong>Upload statement</strong> panel in the sidebar. "
            "Supported: <strong>CSV</strong>, <strong>Excel</strong>, <strong>ODS</strong>, "
            "<strong>PDF</strong>, <strong>TSV</strong>, <strong>TXT</strong>"
            "</div>", unsafe_allow_html=True,
        )
    with col_b:
        sec_header("Load sample data")
        st.markdown('<div class="info-banner">Run this command once in your terminal, then click <strong>↺ Refresh</strong> in the sidebar.</div>', unsafe_allow_html=True)
        st.code("python -m spendwise demo")
    st.stop()


from spendwise.config import money, CATEGORIES
from spendwise.data import expenses, monthly_by_category


# ══════════════════════════════════════════════════════════════════════════════
# DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════
if page == "Dashboard":
    # ── Title ──────────────────────────────────────────────────────
    page_title("🏠", "Dashboard", "Your financial overview at a glance")

    # ── Search + date filter bar ───────────────────────────────────
    from spendwise.data import expenses as _exp
    _all_exp = _exp(df).copy()
    _min_date = _all_exp["date"].min().date()
    _max_date = _all_exp["date"].max().date()

    with st.container():
        s_col, d1_col, d2_col, clr_col = st.columns([3, 1.5, 1.5, 0.6])
        with s_col:
            dash_search = st.text_input(
                "", placeholder="🔍  Search by description or category…",
                key="dash_search", label_visibility="collapsed",
            )
        with d1_col:
            date_from = st.date_input(
                "From", value=_min_date, min_value=_min_date, max_value=_max_date,
                key="dash_date_from",
            )
        with d2_col:
            date_to = st.date_input(
                "To", value=_max_date, min_value=_min_date, max_value=_max_date,
                key="dash_date_to",
            )
        with clr_col:
            st.write("")
            if st.button("✕", key="dash_clear", help="Clear filters"):
                st.session_state.dash_search    = ""
                st.session_state.dash_date_from = _min_date
                st.session_state.dash_date_to   = _max_date
                st.rerun()

    # ── Apply filters ──────────────────────────────────────────────
    _active = dash_search.strip() or date_from != _min_date or date_to != _max_date

    if _active:
        results = _all_exp.copy()
        results = results[
            (results["date"].dt.date >= date_from) &
            (results["date"].dt.date <= date_to)
        ]
        if dash_search.strip():
            results = results[
                results["description"].str.contains(dash_search, case=False, na=False) |
                results["category"].str.contains(dash_search, case=False, na=False)
            ]
        results = results.sort_values("date", ascending=False)

        filter_desc = []
        if dash_search.strip():
            filter_desc.append(f'keyword <strong>"{dash_search}"</strong>')
        if date_from != _min_date or date_to != _max_date:
            filter_desc.append(f'<strong>{date_from.strftime("%d %b %Y")}</strong> → <strong>{date_to.strftime("%d %b %Y")}</strong>')

        if results.empty:
            st.markdown(
                f'<div class="info-banner">No transactions found for {" · ".join(filter_desc)}</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f'<div class="info-banner">Showing <strong>{len(results)}</strong> transaction(s)'
                f'{" for " + " · ".join(filter_desc) if filter_desc else ""}'
                f' &nbsp;·&nbsp; Total: <strong>{fmt_inr(results["amount"].sum())}</strong></div>',
                unsafe_allow_html=True,
            )
            disp = results[["date", "description", "amount", "category"]].copy()
            disp["date"] = disp["date"].dt.strftime("%d %b %Y")
            disp["amount"] = disp["amount"].map(lambda x: f"₹{x:,.0f}")
            disp.columns = ["Date", "Description", "Amount", "Category"]
            st.dataframe(disp, use_container_width=True, hide_index=True, height=440)
        st.stop()

    mbc = monthly_by_category(df)
    total = mbc.sum(axis=1)
    last_month = str(total.index[-1])
    prev_month = str(total.index[-2]) if len(total) >= 2 else None

    last_total = float(total.iloc[-1])
    prev_total = float(total.iloc[-2]) if prev_month else None
    exp = expenses(df)
    last_txns = exp[exp["month"] == exp["month"].max()]
    top_cat = last_txns.groupby("category")["amount"].sum().idxmax()
    avg_txn = last_txns["amount"].mean()

    # KPI row — custom cards
    c1, c2, c3, c4 = st.columns(4)
    delta_str = pct_delta(last_total, prev_total) if prev_total else ""
    delta_d = pct_dir(last_total, prev_total) if prev_total else "neutral"
    with c1:
        kpi_card("Last month spend", fmt_inr(last_total), delta_str, "💸", delta_d)
    with c2:
        kpi_card("Transactions", str(len(last_txns)), "", "🔁")
    with c3:
        kpi_card("Top category", top_cat, "", "🏆")
    with c4:
        kpi_card("Avg transaction", fmt_inr(avg_txn), "", "📈")

    st.divider()

    # Monthly totals chart
    sec_header("Monthly spending trend")
    total_df = total.reset_index()
    total_df.columns = ["Month", "Amount"]
    total_df["Month"] = total_df["Month"].astype(str)
    st.bar_chart(total_df.set_index("Month")["Amount"], use_container_width=True, height=240)

    st.divider()

    col_left, col_right = st.columns(2)
    with col_left:
        sec_header(f"Breakdown — {last_month}")
        cat_data = mbc.iloc[-1].sort_values(ascending=False)
        cat_df = cat_data.reset_index()
        cat_df.columns = ["Category", "Amount"]
        cat_df = cat_df[cat_df["Amount"] > 0]
        st.bar_chart(cat_df.set_index("Category"), use_container_width=True, height=260)

    with col_right:
        sec_header("Month-over-month comparison")
        if len(mbc) >= 2:
            compare = pd.DataFrame({
                "Last month": mbc.iloc[-1],
                "Prev month": mbc.iloc[-2],
            }).sort_values("Last month", ascending=False)
            compare = compare[compare["Last month"] > 0]
            st.bar_chart(compare, use_container_width=True, height=260)

    st.divider()

    sec_header("Recurring payments")
    from spendwise.patterns import recurring_merchants
    recur = recurring_merchants(df)
    if not recur.empty:
        recur_df = recur.reset_index()[["merchant", "avg", "months", "category"]]
        recur_df.columns = ["Merchant", "Monthly (₹)", "Months seen", "Category"]
        recur_df["Monthly (₹)"] = recur_df["Monthly (₹)"].map(lambda x: f"₹{x:,.0f}")
        st.dataframe(recur_df, use_container_width=True, hide_index=True)
    else:
        st.markdown('<div class="info-banner">No recurring payments detected yet.</div>', unsafe_allow_html=True)

    # ── Dashboard footer ───────────────────────────────────────────────────
    st.markdown("""
<div class="dash-footer">
  <div class="dash-footer-inner">
    <div class="dash-footer-brand">
      <svg width="22" height="22" viewBox="0 0 42 42" fill="none" xmlns="http://www.w3.org/2000/svg">
        <rect width="42" height="42" rx="12" fill="url(#fgrad)"/>
        <polyline points="7,30 14,21 20,25 27,14 35,18"
                  stroke="white" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
        <circle cx="35" cy="18" r="2.5" fill="white"/>
        <defs>
          <linearGradient id="fgrad" x1="0" y1="0" x2="42" y2="42" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stop-color="#ff4f1f"/>
            <stop offset="100%" stop-color="#ff8c42"/>
          </linearGradient>
        </defs>
      </svg>
      <span><strong>SpendWise AI</strong> &nbsp;·&nbsp; Personal Finance Intelligence</span>
    </div>
    <div class="dash-footer-links">
      <span>Dashboard</span>
      <span>Transactions</span>
      <span>Forecast</span>
      <span>Budget</span>
    </div>
    <div class="dash-footer-copy">
      © 2026 SpendWise AI &nbsp;·&nbsp; Powered by Machine Learning
    </div>
  </div>
</div>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# TRANSACTIONS
# ══════════════════════════════════════════════════════════════════════════════
elif page == "Transactions":
    page_title("🔁", "Transactions", "Browse and filter all your expenses")

    exp_df = expenses(df).copy()
    exp_df["month"] = exp_df["month"].astype(str)

    f1, f2, f3 = st.columns(3)
    with f1:
        months = sorted(exp_df["month"].unique(), reverse=True)
        sel_month = st.selectbox("Month", ["All"] + months)
    with f2:
        cats = sorted(exp_df["category"].dropna().unique())
        sel_cat = st.selectbox("Category", ["All"] + cats)
    with f3:
        search = st.text_input("🔍  Search description")

    filtered = exp_df.copy()
    if sel_month != "All":
        filtered = filtered[filtered["month"] == sel_month]
    if sel_cat != "All":
        filtered = filtered[filtered["category"] == sel_cat]
    if search:
        filtered = filtered[filtered["description"].str.contains(search, case=False, na=False)]
    filtered = filtered.sort_values("date", ascending=False)

    total_amt = filtered['amount'].sum()
    st.markdown(
        f'<div class="info-banner">Showing <strong>{len(filtered)}</strong> transactions &nbsp;·&nbsp; '
        f'Total: <strong>{fmt_inr(total_amt)}</strong></div>',
        unsafe_allow_html=True,
    )

    display = filtered[["date", "description", "amount", "category"]].copy()
    display["date"] = display["date"].dt.strftime("%d %b %Y")
    display["amount"] = display["amount"].map(lambda x: f"₹{x:,.0f}")
    display.columns = ["Date", "Description", "Amount", "Category"]
    st.dataframe(display, use_container_width=True, hide_index=True, height=520)


# ══════════════════════════════════════════════════════════════════════════════
# PATTERNS
# ══════════════════════════════════════════════════════════════════════════════
elif page == "Patterns":
    page_title("📊", "Spending Patterns", "ML-powered insights into your habits")

    with st.spinner("Running clustering…"):
        from spendwise.patterns import cluster_weeks, recurring_merchants
        profiles, silhouette, feats = cluster_weeks(df)

    st.markdown(
        f'<div class="info-banner">KMeans on weekly profiles — '
        f'<strong>k={len(profiles)}</strong>, silhouette score: <strong>{silhouette:.2f}</strong></div>',
        unsafe_allow_html=True,
    )

    cols = st.columns(len(profiles))
    for col, p in zip(cols, profiles):
        with col:
            kpi_card(p["label"], fmt_inr(p["avg_weekly_spend"]) + "/wk",
                     f"{p['weeks']} weeks total, {p['recent_weeks']} recent", "📅")

    st.divider()

    sec_header("Spend by day of week")
    exp_df2 = expenses(df).copy()
    exp_df2["weekday"] = exp_df2["date"].dt.day_of_week
    day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    weekday_spend = exp_df2.groupby("weekday")["amount"].sum().reindex(range(7), fill_value=0)
    weekday_df = pd.DataFrame({"Day": day_names, "Total Spend": weekday_spend.values})
    st.bar_chart(weekday_df.set_index("Day"), use_container_width=True, height=240)

    st.divider()

    sec_header("Subscriptions & recurring payments")
    recur = recurring_merchants(df)
    if not recur.empty:
        r = recur.reset_index()[["merchant", "avg", "months", "category"]]
        r.columns = ["Merchant", "Monthly avg (₹)", "Months seen", "Category"]
        r["Monthly avg (₹)"] = r["Monthly avg (₹)"].map(lambda x: f"₹{x:,.0f}")
        st.dataframe(r, use_container_width=True, hide_index=True)
    else:
        st.markdown('<div class="info-banner">No recurring payments detected.</div>', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# ANOMALIES
# ══════════════════════════════════════════════════════════════════════════════
elif page == "Anomalies":
    page_title("⚠️", "Unusual Expenses", "Isolation Forest + robust z-score detection")

    with st.spinner("Scanning for anomalies…"):
        from spendwise.anomaly import detect
        anom = detect(df)

    if anom.empty:
        st.markdown('<div class="good-card"><strong>✓ All clear</strong><br><em>No unusual expenses found in your transaction history.</em></div>', unsafe_allow_html=True)
    else:
        st.markdown(
            f'<div class="anomaly-card"><strong>⚠ {len(anom)} unusual transaction(s) flagged</strong></div>',
            unsafe_allow_html=True,
        )
        st.divider()
        for row in anom.itertuples():
            st.markdown(f"""
<div class="anomaly-card">
  <strong>{row.date.strftime('%d %b %Y')}</strong> &nbsp;·&nbsp;
  <strong>₹{row.amount:,.0f}</strong> &nbsp;·&nbsp; <span style="color:#fcd34d">{row.category}</span><br>
  <small>{row.description}</small><br>
  <em>{row.reason}</em>
</div>""", unsafe_allow_html=True)

        st.divider()
        sec_header("Details table")
        display = anom[["date", "description", "category", "amount", "reason"]].copy()
        display["date"] = display["date"].dt.strftime("%d %b %Y")
        display["amount"] = display["amount"].map(lambda x: f"₹{x:,.0f}")
        display.columns = ["Date", "Description", "Category", "Amount", "Reason"]
        st.dataframe(display, use_container_width=True, hide_index=True)


# ══════════════════════════════════════════════════════════════════════════════
# FORECAST
# ══════════════════════════════════════════════════════════════════════════════
elif page == "Forecast":
    page_title("🔮", "Forecast", "ML-powered next-month spending prediction")

    with st.spinner("Running backtest & forecast…"):
        from spendwise.forecast import forecast_next_month
        fc = forecast_next_month(df)

    fc_total = fc["forecast_total"]
    last_total = fc["last_month_total"]
    delta_fc = pct_delta(fc_total, last_total)
    delta_d = pct_dir(fc_total, last_total)

    c1, c2, c3 = st.columns(3)
    with c1:
        kpi_card("Forecast — " + fc["next_month"], fmt_inr(fc_total),
                 f"vs {fmt_inr(last_total)} last month", "🔮", delta_d)
    with c2:
        kpi_card("Best model", fc["model"].replace("_", " "), "", "🧠")
    with c3:
        kpi_card("Backtest MAE", fmt_inr(fc["mae"]), f"{fc['mape_pct']:.1f}% error", "📉")

    st.divider()

    sec_header("Model comparison (backtest MAE)")
    mae_df = pd.DataFrame(list(fc["backtest_mae"].items()), columns=["Model", "MAE (₹)"])
    mae_df["Model"] = mae_df["Model"].str.replace("_", " ")
    mae_df = mae_df.sort_values("MAE (₹)")
    st.bar_chart(mae_df.set_index("Model"), use_container_width=True, height=220)

    st.divider()

    col_l, col_r = st.columns(2)
    with col_l:
        sec_header("Per-category forecast")
        cat_fc = pd.DataFrame(list(fc["per_category"].items()), columns=["Category", "Forecast (₹)"])
        cat_fc = cat_fc[cat_fc["Forecast (₹)"] > 0].sort_values("Forecast (₹)", ascending=False)
        st.bar_chart(cat_fc.set_index("Category"), use_container_width=True, height=260)

    with col_r:
        sec_header("Historical + forecast trend")
        hist_df = pd.DataFrame(list(fc["history"].items()), columns=["Month", "Amount (₹)"])
        forecast_row = pd.DataFrame([[fc["next_month"] + " ★", fc["forecast_total"]]],
                                     columns=["Month", "Amount (₹)"])
        hist_df = pd.concat([hist_df, forecast_row], ignore_index=True)
        st.line_chart(hist_df.set_index("Month"), use_container_width=True, height=260)


# ══════════════════════════════════════════════════════════════════════════════
# BUDGET
# ══════════════════════════════════════════════════════════════════════════════
elif page == "Budget":
    page_title("🎯", "Budget", "Set limits and track spending against them")

    from spendwise.budget import save_budgets, load_budgets

    exp_df3 = expenses(df).copy()
    exp_df3["month"] = exp_df3["month"].astype(str)

    months = sorted(exp_df3["month"].unique(), reverse=True)
    sel_month = st.selectbox("Month", months)

    month_txns = exp_df3[exp_df3["month"] == sel_month]
    cats = sorted(month_txns["category"].dropna().unique())
    spent_by_cat = month_txns.groupby("category")["amount"].sum()
    saved = load_budgets()

    sec_header("Set budgets")
    st.caption("Type a budget for each category, then click Save.")

    with st.form(key=f"budget_form_{sel_month}"):
        h1, h2, h3 = st.columns([3, 2, 2])
        h1.markdown("**Category**")
        h2.markdown("**Budget (₹)**")
        h3.markdown("**Spent this month**")

        budget_inputs = {}
        for cat in cats:
            current_budget = float(saved.get(cat, 0))
            spent_amt = float(spent_by_cat.get(cat, 0))
            over = current_budget > 0 and spent_amt > current_budget
            c1, c2, c3 = st.columns([3, 2, 2])
            c1.markdown(cat)
            budget_inputs[cat] = c2.number_input(
                label=cat, min_value=0.0, value=current_budget,
                step=100.0, format="%.0f", label_visibility="collapsed",
            )
            color = "#ff4f1f" if over else "#22c55e" if current_budget > 0 else "#55557a"
            c3.markdown(f'<span style="color:{color};font-weight:600">₹{spent_amt:,.0f}</span>', unsafe_allow_html=True)

        saved_ok = st.form_submit_button("💾  Save budgets", type="primary", use_container_width=True)

    if saved_ok:
        new_budgets = {cat: v for cat, v in budget_inputs.items() if v > 0}
        save_budgets(new_budgets)
        st.success(f"✓ Budgets saved for {len(new_budgets)} categories.")
        saved = new_budgets

    st.divider()
    sec_header(f"Spending tracker — {sel_month}")

    sel_cat = st.selectbox("Filter by category", ["All"] + cats, key="budget_cat_filter")

    for cat in cats:
        budget = budget_inputs.get(cat, 0)
        spent = float(spent_by_cat.get(cat, 0))
        if sel_cat != "All" and cat != sel_cat:
            continue

        over = budget > 0 and spent > budget
        status_icon = "🔴" if over else ("🟢" if budget > 0 else "⚪")
        label = f"{status_icon} {cat}  —  ₹{spent:,.0f}"
        if budget > 0:
            label += f" / ₹{budget:,.0f}"

        with st.expander(label, expanded=(sel_cat == cat)):
            if budget > 0:
                ratio = min(spent / budget, 1.0)
                pct_text = f"{'🚨 Over budget' if over else '✓ Within budget'}  ({spent / budget * 100:.0f}%)"
                st.progress(ratio, text=pct_text)

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
    page_title("✏️", "Review", "Fix transactions the AI couldn't classify")

    from spendwise.data import load_store, save_store
    from spendwise.config import CORRECTIONS_CSV, CATEGORIES

    all_df = load_store()
    unc = all_df[all_df["category"] == "Uncategorized"].copy()
    total_unc = len(unc)

    if total_unc == 0:
        st.markdown('<div class="good-card"><strong>✓ All transactions categorized</strong><br><em>Nothing to review right now.</em></div>', unsafe_allow_html=True)
        st.stop()

    st.markdown(
        f'<div class="anomaly-card"><strong>✏️ {total_unc} transaction(s) need a category</strong><br>'
        f'<em>Use the dropdowns below to assign, then click Save.</em></div>',
        unsafe_allow_html=True,
    )

    PAGE_SIZE = 25
    total_pages = max(1, (total_unc - 1) // PAGE_SIZE + 1)
    if "review_page" not in st.session_state:
        st.session_state.review_page = 0
    if st.session_state.review_page >= total_pages:
        st.session_state.review_page = max(0, total_pages - 1)

    start = st.session_state.review_page * PAGE_SIZE
    end = min(start + PAGE_SIZE, total_unc)
    page_unc = unc.iloc[start:end]

    col_prev, col_info, col_next = st.columns([1, 2, 1])
    with col_prev:
        if st.button("← Prev", disabled=st.session_state.review_page == 0, use_container_width=True):
            st.session_state.review_page -= 1
            st.rerun()
    with col_info:
        st.markdown(
            f"<div style='text-align:center;padding-top:8px;color:#9898c0;font-size:1rem'>"
            f"Page {st.session_state.review_page + 1} of {total_pages} &nbsp;·&nbsp; "
            f"{start + 1}–{end} of {total_unc}</div>",
            unsafe_allow_html=True,
        )
    with col_next:
        if st.button("Next →", disabled=st.session_state.review_page >= total_pages - 1, use_container_width=True):
            st.session_state.review_page += 1
            st.rerun()

    st.divider()

    h1, h2, h3, h4 = st.columns([2, 5, 2, 3])
    h1.markdown('<span class="review-col-header">Date</span>', unsafe_allow_html=True)
    h2.markdown('<span class="review-col-header">Description</span>', unsafe_allow_html=True)
    h3.markdown('<span class="review-col-header">Amount</span>', unsafe_allow_html=True)
    h4.markdown('<span class="review-col-header">Assign category</span>', unsafe_allow_html=True)

    cat_options = ["(skip)"] + sorted(CATEGORIES)
    for orig_idx, row in page_unc.iterrows():
        c1, c2, c3, c4 = st.columns([2, 5, 2, 3])
        date_str = row["date"].strftime("%d %b %Y") if hasattr(row["date"], "strftime") else str(row["date"])
        c1.markdown(f'<span style="color:#9898c0;font-size:1rem">{date_str}</span>', unsafe_allow_html=True)
        desc = str(row.get("description", ""))
        c2.markdown(f'<span style="font-family:monospace;font-size:.95rem;color:#e2e8f0">{desc[:58]}{"…" if len(desc)>58 else ""}</span>', unsafe_allow_html=True)
        c3.markdown(f'<span style="color:#ff7050;font-weight:700;font-size:1rem">₹{float(row["amount"]):,.0f}</span>', unsafe_allow_html=True)
        c4.selectbox("category", cat_options, index=0, label_visibility="collapsed", key=f"rev_cat_{orig_idx}")

    st.divider()

    col_save, col_skip = st.columns([3, 1])
    with col_save:
        save_clicked = st.button("💾  Save corrections", type="primary", use_container_width=True)
    with col_skip:
        if st.button("Next →", use_container_width=True, disabled=st.session_state.review_page >= total_pages - 1):
            st.session_state.review_page += 1
            st.rerun()

    if save_clicked:
        corrections = {
            orig_idx: st.session_state[f"rev_cat_{orig_idx}"]
            for orig_idx in page_unc.index
            if st.session_state.get(f"rev_cat_{orig_idx}", "(skip)") != "(skip)"
        }
        if not corrections:
            st.warning("No categories selected. Use the dropdowns to assign a category first.")
        else:
            updated_df = all_df.copy()
            new_corr_rows = []
            for idx, cat in corrections.items():
                updated_df.loc[idx, "category"] = cat
                updated_df.loc[idx, "confidence"] = 1.0
                updated_df.loc[idx, "source"] = "user"
                new_corr_rows.append({"description": str(all_df.loc[idx, "description"]), "category": cat})
            save_store(updated_df, append=False)

            corr_df = pd.DataFrame(new_corr_rows)
            if CORRECTIONS_CSV.exists():
                existing_corr = pd.read_csv(CORRECTIONS_CSV)
                combined_corr = pd.concat([existing_corr, corr_df]).drop_duplicates(subset=["description"], keep="last")
            else:
                combined_corr = corr_df
            combined_corr.to_csv(CORRECTIONS_CSV, index=False)

            remaining = total_unc - len(corrections)
            st.cache_data.clear()
            st.success(
                f"✓ Saved {len(corrections)} correction(s). "
                + (f"{remaining} remaining." if remaining > 0 else "All transactions categorized!")
            )
            st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# ASK AI
# ══════════════════════════════════════════════════════════════════════════════
elif page == "Ask AI":
    page_title("🤖", "Ask AI", "Questions answered by ML-computed facts, explained by Claude")

    suggestions = [
        "Why did my expenses increase?",
        "How much on food delivery?",
        "Anything unusual?",
        "Forecast next month",
        "What are my subscriptions?",
        "Where does most money go?",
        "Give me budget advice",
    ]

    st.markdown('<div class="sec-header">Suggested questions</div>', unsafe_allow_html=True)
    if "question" not in st.session_state:
        st.session_state.question = ""

    with st.container():
        st.markdown('<div class="sug-row">', unsafe_allow_html=True)
        cols = st.columns(4)
        for i, sug in enumerate(suggestions):
            if cols[i % 4].button(sug, use_container_width=True, key=f"sug_{i}"):
                st.session_state.question = sug
        st.markdown('</div>', unsafe_allow_html=True)

    st.divider()

    question = st.text_input("💬  Or type your own question:", value=st.session_state.question, key="q_input")
    use_llm = st.checkbox(
        "Use Claude LLM for natural language answers (requires ANTHROPIC_API_KEY)",
        value=bool(os.environ.get("ANTHROPIC_API_KEY")),
    )

    if st.button("Ask →", type="primary", use_container_width=True) and question.strip():
        with st.spinner("Thinking…"):
            from spendwise.assistant import ask
            result = ask(df, question, use_llm=use_llm)

        st.divider()
        engine_label = "🤖 Claude LLM" if result["engine"] == "llm" else "⚙️ Template engine"
        st.markdown(
            f'<div class="info-banner">Intent: <code>{result["intent"]}</code> &nbsp;·&nbsp; {engine_label}</div>',
            unsafe_allow_html=True,
        )
        st.markdown(f"### {result['answer']}")

        with st.expander("Show raw facts sent to LLM"):
            import json
            st.json(result["facts"])

    if "history" not in st.session_state:
        st.session_state.history = []

    if st.session_state.history:
        st.divider()
        sec_header("Previous questions")
        for q, a in reversed(st.session_state.history[-5:]):
            with st.expander(q):
                st.write(a)
