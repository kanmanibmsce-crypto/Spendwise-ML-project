"""Quick smoke-test: convert sample CSV to every supported format, then load each."""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import tempfile, shutil
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from spendwise.data import load_document, load_bank_csv

SAMPLE_CSV = ROOT / "data" / "sample_bank_statement.csv"

# Load reference data
ref = load_bank_csv(str(SAMPLE_CSV))
print(f"Reference CSV: {len(ref)} rows")

results = {}

# ── CSV ──────────────────────────────────────────────────────────────────────
try:
    df = load_document(str(SAMPLE_CSV))
    results["CSV"] = (True, len(df))
except Exception as e:
    results["CSV"] = (False, str(e))

# ── TSV ──────────────────────────────────────────────────────────────────────
try:
    raw = pd.read_csv(SAMPLE_CSV)
    with tempfile.NamedTemporaryFile(suffix=".tsv", delete=False, mode="w") as f:
        raw.to_csv(f, sep="\t", index=False)
        tsv_path = f.name
    df = load_document(tsv_path)
    results["TSV"] = (True, len(df))
except Exception as e:
    results["TSV"] = (False, str(e))

# ── TXT (pipe-delimited) ──────────────────────────────────────────────────────
try:
    raw = pd.read_csv(SAMPLE_CSV)
    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False, mode="w") as f:
        raw.to_csv(f, sep="|", index=False)
        txt_path = f.name
    df = load_document(txt_path)
    results["TXT"] = (True, len(df))
except Exception as e:
    results["TXT"] = (False, str(e))

# ── XLSX ─────────────────────────────────────────────────────────────────────
try:
    raw = pd.read_csv(SAMPLE_CSV)
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
        xlsx_path = f.name
    raw.to_excel(xlsx_path, index=False)
    df = load_document(xlsx_path)
    results["XLSX"] = (True, len(df))
except Exception as e:
    results["XLSX"] = (False, str(e))

# ── XLS ──────────────────────────────────────────────────────────────────────
try:
    import xlwt  # optional legacy
    results["XLS"] = ("SKIP", "xlwt not installed (xlrd read-only for .xls)")
except ImportError:
    results["XLS"] = ("SKIP", "xlwt not installed — .xls write not possible in test")

# ── ODS ──────────────────────────────────────────────────────────────────────
try:
    raw = pd.read_csv(SAMPLE_CSV)
    with tempfile.NamedTemporaryFile(suffix=".ods", delete=False) as f:
        ods_path = f.name
    raw.to_excel(ods_path, engine="odf", index=False)
    df = load_document(ods_path)
    results["ODS"] = (True, len(df))
except Exception as e:
    results["ODS"] = (False, str(e))

# ── PDF ───────────────────────────────────────────────────────────────────────
# We can't easily create a real PDF in a test without reportlab/fpdf,
# so we just verify the import path works.
try:
    import pdfplumber
    results["PDF"] = ("SKIP", "pdfplumber installed OK — no synthetic PDF in test")
except ImportError as e:
    results["PDF"] = (False, str(e))

# ── summary ──────────────────────────────────────────────────────────────────
print("\nFormat test results:")
print(f"{'Format':<8} {'Status':<8} {'Detail'}")
print("-" * 50)
for fmt, (ok, detail) in results.items():
    status = "PASS" if ok is True else "SKIP" if ok == "SKIP" else "FAIL"
    print(f"{fmt:<8} {status:<8} {detail}")
