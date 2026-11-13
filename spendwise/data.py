"""Load bank statements in multiple formats and normalise to one schema:

    txn_id | date | description | amount (positive) | direction (debit/credit)

Supported formats:
    .csv  — comma-separated (any bank CSV export)
    .tsv  — tab-separated
    .txt  — auto-detects delimiter (tab, comma, pipe, semicolon)
    .xlsx — Excel 2007+
    .xls  — Excel 97-2003
    .ods  — OpenDocument Spreadsheet
    .pdf  — PDF bank statement (table extraction via pdfplumber)
"""
import hashlib
import re
from pathlib import Path

import pandas as pd

from .config import STORE_CSV


class PDFPasswordRequired(Exception):
    """Raised when a PDF is encrypted and no password (or a wrong one) was supplied."""

# ── column aliases ─────────────────────────────────────────────────────────────

ALIASES = {
    "date": [
        "date", "txn date", "transaction date", "value date",
        "posting date", "tran date", "trans date", "book date",
        "settlement date", "entry date",
    ],
    "description": [
        "description", "narration", "details", "particulars",
        "remarks", "transaction details", "transaction description",
        "memo", "reference", "narrative", "detail",
    ],
    "debit": [
        "debit", "withdrawal", "withdrawal amt", "withdrawal amt.",
        "dr", "debit amount", "debits", "paid out", "debit (inr)",
        "withdrawals", "debit amt",
    ],
    "credit": [
        "credit", "deposit", "deposit amt", "deposit amt.", "cr",
        "credit amount", "credits", "paid in", "credit (inr)",
        "deposits", "credit amt",
    ],
    "amount": [
        "amount", "amt", "transaction amount", "net amount",
        "value", "sum",
    ],
}


def _find(cols: list[str], key: str) -> str | None:
    for c in cols:
        if c.strip().lower() in ALIASES[key]:
            return c
    return None


# ── shared normalisation ───────────────────────────────────────────────────────

def _normalise(raw: pd.DataFrame) -> pd.DataFrame:
    """Detect date/description/amount columns and return the canonical schema."""
    # Strip column names
    raw.columns = [str(c).strip() for c in raw.columns]
    cols = list(raw.columns)

    dcol = _find(cols, "date")
    desc = _find(cols, "description")
    if not dcol or not desc:
        raise ValueError(
            f"Could not find date/description columns.\n"
            f"Columns found: {cols}\n"
            f"Expected one of: {ALIASES['date']}  and  {ALIASES['description']}"
        )

    df = pd.DataFrame()
    df["date"]        = pd.to_datetime(raw[dcol], dayfirst=True, errors="coerce")
    df["description"] = raw[desc].astype(str).str.strip()

    deb  = _find(cols, "debit")
    cred = _find(cols, "credit")
    amt  = _find(cols, "amount")

    if deb or cred:
        d      = pd.to_numeric(raw[deb].astype(str).str.replace(",", ""), errors="coerce").fillna(0) if deb else 0
        c      = pd.to_numeric(raw[cred].astype(str).str.replace(",", ""), errors="coerce").fillna(0) if cred else 0
        signed = c - d
    elif amt:
        signed = pd.to_numeric(raw[amt].astype(str).str.replace(",", ""), errors="coerce")
    else:
        raise ValueError(
            "Need Debit/Credit columns or a signed Amount column.\n"
            f"Columns found: {cols}"
        )

    df["amount"]    = pd.Series(signed).abs().values
    df["direction"] = ["credit" if s > 0 else "debit" for s in pd.Series(signed).values]

    bad = df["date"].isna() | (df["amount"] == 0)
    df  = df[~bad].copy()

    df["txn_id"] = [
        hashlib.md5(f"{r.date}{r.description}{r.amount}".encode()).hexdigest()[:8]
        for r in df.itertuples()
    ]
    df = df.drop_duplicates("txn_id")
    return df[["txn_id", "date", "description", "amount", "direction"]].sort_values("date")


def _find_header_row(df: pd.DataFrame) -> pd.DataFrame:
    """
    Scan rows to find the actual header (useful for Excel/ODS/PDF files that
    have account metadata rows above the transaction table).
    Returns a new DataFrame with the detected header row applied.
    """
    date_kws  = set(ALIASES["date"])
    desc_kws  = set(ALIASES["description"])

    for i, row in df.iterrows():
        cells = [str(v).strip().lower() for v in row.values]
        if any(c in date_kws for c in cells) and any(c in desc_kws for c in cells):
            new_df = df.iloc[int(i) + 1:].copy()
            new_df.columns = [str(v).strip() for v in df.iloc[int(i)].values]
            new_df = new_df.reset_index(drop=True)
            return new_df

    return df  # no header row found — use as-is


# ── format-specific loaders ───────────────────────────────────────────────────

def _load_flat(path, sep=None) -> pd.DataFrame:
    """CSV / TSV / TXT with auto-detected or supplied separator."""
    if sep is None:
        # Sniff from first 4 KB
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            sample = fh.read(4096)
        counts = {s: sample.count(s) for s in [",", "\t", "|", ";"]}
        sep = max(counts, key=counts.get)

    raw = pd.read_csv(path, sep=sep, thousands=",", encoding="utf-8", encoding_errors="replace")
    return _normalise(raw)


def _load_excel(path) -> pd.DataFrame:
    """Excel .xlsx / .xls — tries every sheet, picks the first with valid data."""
    xl   = pd.ExcelFile(path)
    last_err = None
    for sheet in xl.sheet_names:
        try:
            # Read without assuming a header; we'll detect it ourselves
            raw = pd.read_excel(path, sheet_name=sheet, header=None, dtype=str)
            raw = _find_header_row(raw)
            return _normalise(raw)
        except Exception as exc:
            last_err = exc
            continue
    raise ValueError(f"No valid transaction sheet found in Excel file. Last error: {last_err}")


def _load_ods(path) -> pd.DataFrame:
    """OpenDocument Spreadsheet (.ods)."""
    raw = pd.read_excel(path, engine="odf", header=None, dtype=str)
    raw = _find_header_row(raw)
    return _normalise(raw)


def _load_pdf(path, password: str | None = None) -> pd.DataFrame:
    """PDF bank statement — table extraction via pdfplumber.

    Handles:
    - Standard (unprotected) PDFs
    - Password-protected PDFs (WPS, Acrobat, etc.) — pass the password
    - Multi-page statements (tables are merged across pages)
    - PDFs whose header row appears only on the first page
    """
    try:
        import pdfplumber
        from pdfminer.pdfdocument import PDFPasswordIncorrect, PDFEncryptionError
    except ImportError:
        raise ImportError("pdfplumber is required for PDF support: pip install pdfplumber")

    pw = password or ""

    try:
        pdf_obj = pdfplumber.open(path, password=pw)
    except (PDFPasswordIncorrect, PDFEncryptionError):
        raise PDFPasswordRequired(
            "This PDF is password-protected. Please enter the password and try again."
        )
    except Exception as exc:
        # Some versions surface the encryption error wrapped in a generic Exception
        msg = str(exc).lower()
        if any(k in msg for k in ("password", "encrypt", "decrypt", "not allowed", "incorrect")):
            raise PDFPasswordRequired(
                "This PDF is password-protected. Please enter the password and try again."
            )
        raise

    all_rows: list[list] = []
    header:   list | None = None

    try:
        with pdf_obj:
            for page in pdf_obj.pages:
                # Attempt table extraction first
                tables = page.extract_tables()

                # If no tables found on this page, try line-based text as fallback
                if not tables:
                    continue

                for table in tables:
                    if not table:
                        continue
                    for row in table:
                        clean = [str(c).strip() if c else "" for c in row]
                        if not any(clean):
                            continue
                        if header is None:
                            lower = [v.lower() for v in clean]
                            date_hit = any(k in lower for k in ALIASES["date"])
                            desc_hit = any(k in lower for k in ALIASES["description"])
                            if date_hit and desc_hit:
                                header = clean
                            else:
                                all_rows.append(clean)
                        else:
                            all_rows.append(clean)

    except (PDFPasswordIncorrect, PDFEncryptionError):
        raise PDFPasswordRequired(
            "This PDF is password-protected. Please enter the password and try again."
        )
    except Exception as exc:
        msg = str(exc).lower()
        if any(k in msg for k in ("password", "encrypt", "decrypt", "not allowed", "incorrect")):
            raise PDFPasswordRequired(
                "This PDF is password-protected. Please enter the password and try again."
            )
        raise

    if not all_rows:
        raise ValueError(
            "No transaction table found in the PDF.\n"
            "• Check the PDF contains a formatted table (not a scanned image).\n"
            "• The table must have Date and Description columns.\n"
            "• If the PDF is image-based, convert it to a searchable PDF first."
        )

    if header:
        df = pd.DataFrame(all_rows, columns=header)
    else:
        df = pd.DataFrame(all_rows[1:], columns=all_rows[0])

    return _normalise(df)


# ── public entry points ────────────────────────────────────────────────────────

SUPPORTED_EXTENSIONS = {
    ".csv":  "CSV (comma-separated)",
    ".tsv":  "TSV (tab-separated)",
    ".txt":  "Text (auto-detected delimiter)",
    ".xlsx": "Excel 2007+ (.xlsx)",
    ".xls":  "Excel 97-2003 (.xls)",
    ".ods":  "OpenDocument Spreadsheet (.ods)",
    ".pdf":  "PDF bank statement",
}


def load_bank_csv(path) -> pd.DataFrame:
    """Legacy entry point — kept for CLI compatibility."""
    return _load_flat(path, sep=",")


def load_document(path, password: str | None = None) -> pd.DataFrame:
    """
    Universal loader: dispatch to the right parser based on file extension.
    Returns the canonical schema: txn_id, date, description, amount, direction.

    For password-protected PDFs, supply the password argument.
    Raises PDFPasswordRequired if the PDF is encrypted and no/wrong password given.
    """
    ext = Path(path).suffix.lower()
    if ext == ".csv":
        return _load_flat(path, sep=",")
    if ext == ".tsv":
        return _load_flat(path, sep="\t")
    if ext == ".txt":
        return _load_flat(path, sep=None)
    if ext in (".xlsx", ".xls"):
        return _load_excel(path)
    if ext == ".ods":
        return _load_ods(path)
    if ext == ".pdf":
        return _load_pdf(path, password=password)
    raise ValueError(
        f"Unsupported format '{ext}'. "
        f"Supported: {', '.join(SUPPORTED_EXTENSIONS)}"
    )


def save_store(df: pd.DataFrame, append=True):
    if append and STORE_CSV.exists():
        old = load_store()
        df  = pd.concat([old, df]).drop_duplicates("txn_id", keep="last")
    df.sort_values("date").to_csv(STORE_CSV, index=False)
    return df


def load_store() -> pd.DataFrame:
    if not STORE_CSV.exists():
        raise SystemExit("No transactions yet. Run:  python -m spendwise upload <file.csv>")
    df = pd.read_csv(STORE_CSV, parse_dates=["date"])
    return df


def expenses(df: pd.DataFrame) -> pd.DataFrame:
    """Debits only, with a month column."""
    e         = df[df["direction"] == "debit"].copy()
    e["month"] = e["date"].dt.to_period("M")
    return e


def monthly_by_category(df: pd.DataFrame) -> pd.DataFrame:
    e = expenses(df)
    return e.pivot_table(index="month", columns="category", values="amount", aggfunc="sum", fill_value=0)
