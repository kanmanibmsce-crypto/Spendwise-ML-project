"""ML + rule-based transaction classifier.

Pipeline (in priority order):
  1. User corrections  — exact merchant overrides saved by the user (highest trust)
  2. Rule-based layer  — MCC codes embedded in UPIOUT strings + VPA/keyword patterns
  3. ML model          — TF-IDF char n-gram + Logistic Regression for the rest
  4. Confidence gate   — ML results below threshold become "Uncategorized"

The rule layer handles the "UPIOUT" transactions that flood uncategorized buckets.
Indian UPI bank narrations embed a 4-digit ISO-8583 MCC at the end of the string
(e.g. /5812 = restaurant, /5411 = grocery). We decode those directly.
"""
import json
import re

import joblib
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

from .config import CONFIDENCE_THRESHOLD, CORRECTIONS_CSV, MODEL_PATH, MODEL_REPORT

# ── text cleaning (used by ML vectoriser) ─────────────────────────────────────

NOISE = re.compile(
    r"(\b(upi|pos|neft|imps|ach|bil|onl|vin|payment|bangalore|in)\b"
    r"|@\w+|\d+|[/\-_*])",
    re.I,
)


def clean(text: str) -> str:
    t = NOISE.sub(" ", str(text).lower())
    return re.sub(r"\s+", " ", t).strip()


def merchant_key(text: str) -> str:
    toks = [t for t in clean(text).split() if len(t) > 2]
    return " ".join(toks[:2])


# ── MCC → category map ────────────────────────────────────────────────────────
# Source: ISO 18245 / Visa/Mastercard MCC reference
# Only codes that appear in real Indian UPI statements are listed.

MCC_CATEGORY: dict[str, str] = {
    # Groceries & Food Retail
    "5411": "Groceries",        # Grocery stores / supermarkets
    "5422": "Groceries",        # Meat / fish stores
    "5441": "Groceries",        # Candy / nut stores
    "5451": "Groceries",        # Dairy products
    "5300": "Groceries",        # Wholesale clubs / warehouse
    "5311": "Groceries",        # Department stores (supermarket-type)
    "5331": "Groceries",        # Variety stores
    "5399": "Groceries",        # Miscellaneous general merchandise

    # Dining Out
    "5812": "Dining Out",       # Eating places / restaurants
    "5813": "Dining Out",       # Bars / cocktail lounges
    "5462": "Dining Out",       # Bakeries

    # Food Delivery
    "5814": "Food Delivery",    # Fast food restaurants
    "5811": "Food Delivery",    # Caterers
    "5912": "Health",           # Drug stores / pharmacies (also 5912 below)

    # Transport & Fuel
    "5541": "Transport",        # Service stations / petrol pumps
    "5542": "Transport",        # Automated fuel dispensers
    "7538": "Transport",        # Auto service / repair shops
    "4121": "Transport",        # Taxicabs / limousines / ride-hailing
    "4111": "Transport",        # Local / suburban commuter transport
    "4112": "Transport",        # Passenger railways
    "4131": "Transport",        # Bus lines
    "7523": "Transport",        # Parking lots / garages
    "7513": "Transport",        # Truck / utility trailer rentals
    "5571": "Transport",        # Motorcycle shops
    "5551": "Transport",        # Boat dealers
    "5561": "Transport",        # Camper / recreational vehicle dealers

    # Bills & Utilities
    "4900": "Bills & Utilities",  # Electric / gas / water utilities
    "4814": "Bills & Utilities",  # Telecommunication services
    "4815": "Bills & Utilities",  # Phone services
    "4816": "Bills & Utilities",  # Computer network / ISP
    "4899": "Bills & Utilities",  # Cable / satellite / other pay TV
    "6300": "Bills & Utilities",  # Insurance
    "6381": "Bills & Utilities",  # Insurance premiums
    "9311": "Bills & Utilities",  # Tax payments (govt)
    "9222": "Bills & Utilities",  # Fines / govt services
    "9399": "Bills & Utilities",  # Govt services

    # Health & Medical
    "5912": "Health",           # Drug stores / pharmacies
    "8011": "Health",           # Doctors / physicians
    "8021": "Health",           # Dentists
    "8031": "Health",           # Osteopathic physicians
    "8041": "Health",           # Chiropractors
    "8042": "Health",           # Optometrists
    "8049": "Health",           # Podiatrists / foot care
    "8062": "Health",           # Hospitals
    "8071": "Health",           # Medical / dental labs
    "8099": "Health",           # Health practitioners
    "5047": "Health",           # Medical / dental supplies
    "5122": "Health",           # Drugs / druggist sundries
    "7230": "Health",           # Beauty / barber shops
    "7298": "Health",           # Health and beauty spas
    "5977": "Health",           # Cosmetic stores

    # Shopping
    "5611": "Shopping",         # Men's clothing stores
    "5621": "Shopping",         # Women's ready-to-wear stores
    "5631": "Shopping",         # Women's accessories / specialty
    "5641": "Shopping",         # Children's / infants' clothing
    "5651": "Shopping",         # Family clothing stores
    "5661": "Shopping",         # Shoe stores
    "5699": "Shopping",         # Misc apparel / accessories
    "5137": "Shopping",         # Women's / children's / infants' clothing
    "5732": "Shopping",         # Electronics / music stores
    "5945": "Shopping",         # Hobby / toy / game shops
    "5940": "Shopping",         # Sporting goods stores
    "5941": "Shopping",         # Sporting goods
    "5943": "Shopping",         # Stationery / office supplies
    "5992": "Shopping",         # Florists
    "5944": "Shopping",         # Jewelry stores
    "5999": "Shopping",         # Misc retail
    "5200": "Shopping",         # Home supply / hardware stores
    "5251": "Shopping",         # Hardware stores
    "5712": "Shopping",         # Furniture stores
    "5722": "Shopping",         # Household appliance stores
    "5311": "Shopping",         # Department stores
    "5969": "Shopping",         # Other direct marketing
    "5462": "Dining Out",       # Bakeries (already above)
    "5422": "Groceries",        # Meat stores (already above)
    "5451": "Groceries",        # Dairy (already above)
    "4215": "Shopping",         # Courier / delivery services
    "4214": "Shopping",         # Motor freight carriers
    "5422": "Groceries",

    # Entertainment
    "7832": "Entertainment",    # Motion picture theaters
    "7922": "Entertainment",    # Theatrical / concert producers
    "7996": "Entertainment",    # Amusement parks / carnivals
    "7999": "Entertainment",    # Recreation services
    "7801": "Entertainment",    # Govt-licensed casinos
    "7802": "Entertainment",    # Golf courses
    "7911": "Entertainment",    # Dance halls / studios
    "5735": "Entertainment",    # Music stores
    "5816": "Entertainment",    # Digital goods / in-app purchases
    "7372": "Entertainment",    # Computer programming / software

    # Education
    "8220": "Education",        # Colleges / universities
    "8244": "Education",        # Business / secretarial schools
    "8249": "Education",        # Trade / vocational schools
    "8299": "Education",        # Educational services / tutoring
    "8211": "Education",        # Elementary / secondary schools

    # Travel
    "3000": "Travel",           # Airlines
    "4411": "Travel",           # Cruise lines
    "7011": "Travel",           # Hotels / motels / resorts
    "7012": "Travel",           # Timeshares
    "4722": "Travel",           # Travel agencies
    "4723": "Travel",           # Package tour operators
    "7512": "Travel",           # Car rental agencies

    # Investments (shown in app but not in budget suggestions)
    "6211": "Investments",      # Security brokers / dealers
    "6010": "Investments",      # Manual cash disbursements
    "6012": "Investments",      # Financial institutions

    "5973": "Shopping",           # Religious goods / gift shops (Paytm misc retail)
    "5912": "Health",             # Drug stores / pharmacies (duplicate key, kept for clarity)

    # MCC 0000 means the merchant didn't register a category — skip it
    "0000": None,
}

# ── VPA / description keyword rules ───────────────────────────────────────────
# Each entry: (compiled regex, category)
# Applied to the raw description (lowercased, whitespace-normalised).
# First match wins.

_RULES: list[tuple[re.Pattern, str]] = [
    # ── Specific known merchants / services ───────────────────────────────────

    # Home loan / housing EMI
    (re.compile(r"lichf|lichousefi|lichousefin|lic\s*housing|home\s*loan|housing\s*loan|achdr.*lic", re.I), "Bills & Utilities"),
    # Insurance
    (re.compile(r"gpay.?insurance|icicilombard|hdfcergo|bajajallianz|starhealth|niacl|licil|policybazaar|godigit|acko", re.I), "Bills & Utilities"),
    # Utilities via GPay
    (re.compile(r"gpay.?utility|bwssb|bescom|tneb|cesc|msedcl|tata.?power|adani.?elec|nbpdcl|sbpdcl", re.I), "Bills & Utilities"),
    # Mobile alerts / bank charges
    (re.compile(r"chrg.*mob.?alert|mob.?alert|sms.?alert|annual.*fee|card.*fee|bank.*charge", re.I), "Bills & Utilities"),
    # Loan repayments
    (re.compile(r"loan\s*pay|emi\s*pay|repayment|ach.*loan|ach.*emi|bajaj.*finance|hdfc.*loan|sbi.*loan|icici.*loan", re.I), "Bills & Utilities"),

    # ── Investments ───────────────────────────────────────────────────────────
    (re.compile(r"mb\s*wealth|wealth.*mf\s*order|sip\s*inst|mf\s*order|mutual\s*fund|nps\s*|ppf\s*|epfo|zerodha|groww|kuvera|coin.*zerodha|uti\s*silver|etf\s*|sip.*fed", re.I), "Investments"),

    # ── Personal Transfers ────────────────────────────────────────────────────
    (re.compile(r"mb\s*imps.*sbin0040586|kanmani\s*jayap|indirajayapalan|self\s*transfer", re.I), "Transfers"),

    # ── Food Delivery ─────────────────────────────────────────────────────────
    (re.compile(r"swiggy|zomato|eatsure|faasos|freshmenu|box8|rebel\s*foods|dunzo.*food|magicpin.*food|thrive.*food", re.I), "Food Delivery"),
    (re.compile(r"licious|cf\.licious|cashfreensdlp.*5411|freshtohome|eatclub|oven\s*story", re.I), "Food Delivery"),

    # ── Groceries ─────────────────────────────────────────────────────────────
    (re.compile(r"bigbasket|milkbasket|supr\s*daily|jiomart|dmart|nature.*basket|spencers|more.*retail|nilgiris|ueirorganic|ammasamayalfood|sprouts", re.I), "Groceries"),
    (re.compile(r"blinkit|zepto|instamart|swiggy.*grocery|dunzo.*grocery", re.I), "Groceries"),

    # ── Transport ─────────────────────────────────────────────────────────────
    (re.compile(r"olacabs|uber|rapido|yulu|bounce.*ev|porter.*logistic|fastag|netc.*fastag|hpcl|iocl|bpcl|essar.*petrol|shell.*petrol", re.I), "Transport"),
    (re.compile(r"redbus|irctc|makemytrip.*train|goibibo.*train|ksrtc|apsrtc|bmtc|metro.*rail|namma.*metro", re.I), "Transport"),

    # ── Shopping ─────────────────────────────────────────────────────────────
    (re.compile(r"amazon|flipkart|myntra|nykaa|ajio|meesho|snapdeal|shopclues|tata.*cliq|reliance.*digital|croma|vijay.*sales", re.I), "Shopping"),
    (re.compile(r"peterengland|fabindia|westside|lifestyle|pantaloons|zara|h&m|marks.*spencer|max.*fashion", re.I), "Shopping"),
    (re.compile(r"ekart|delhivery|bluedart|dtdc|shiprocket|xpressbees|shadowfax", re.I), "Shopping"),
    (re.compile(r"to\s*ecm.*google\s*play|googleplay|google\s*play", re.I), "Entertainment"),

    # ── Entertainment ─────────────────────────────────────────────────────────
    (re.compile(r"netflix|amazon\s*prime|hotstar|disney|sony\s*liv|zee5|jiocinema|bookmyshow|pvr|inox\s*movies|spotify|gaana|wynk|youtube\s*premium", re.I), "Entertainment"),
    (re.compile(r"to\s*ecm.*google", re.I), "Entertainment"),

    # ── Education ────────────────────────────────────────────────────────────
    (re.compile(r"coursera|udemy|byju|unacademy|upgrad|khan\s*academy|great\s*learning|simplilearn|deeplearning\.ai|edureka|lambda\s*school", re.I), "Education"),

    # ── Health ───────────────────────────────────────────────────────────────
    (re.compile(r"apollo\s*pharm|medplus|netmeds|1mg|healthkart|pharmeasy|tata.*health|jainmedical|manipal\s*pharm", re.I), "Health"),
    (re.compile(r"cult\.fit|cure\.fit|classpass|gympass|fitpass", re.I), "Health"),

    # ── Vehicle Insurance ─────────────────────────────────────────────────────
    (re.compile(r"motor\s*insur|vehicle\s*insur|bike\s*insur|car\s*insur|two.?wheel.*insur|four.?wheel.*insur", re.I), "Vehicle Insurance"),
    (re.compile(r"bajaj.*motor|icicilombard.*motor|hdfcergo.*motor|acko.*motor|tataAIG.*motor|digit.*motor|new\s*india.*motor", re.I), "Vehicle Insurance"),
    (re.compile(r"vahan|rc\s*renewal|fastag.*insur|nitin.*motor", re.I), "Vehicle Insurance"),

    # ── Bills & Utilities ────────────────────────────────────────────────────
    (re.compile(r"airtel|jio\s*recharge|vi\s*recharge|vodafone|bsnl|act\s*fibernet|hathway|tikona|tata\s*sky|dish\s*tv|d2h\s*recharge", re.I), "Bills & Utilities"),
    (re.compile(r"paytm.*recharge|phonepe.*recharge|google.*recharge|bbps", re.I), "Bills & Utilities"),

    # ── Travel ───────────────────────────────────────────────────────────────
    (re.compile(r"makemytrip|goibibo|yatra|cleartrip|easemytrip|oyo\s*rooms|treebo|fabhotels|airbnb|mmt\s*hotel|indigo|spicejet|air\s*india|vistara", re.I), "Travel"),

    # ── Health hints in UPIOUT description path ───────────────────────────────
    (re.compile(r"typhoid|vaccination|vaccine|blood.?test|diagnostic|lab.?test|covid.?test|fever.?med", re.I), "Health"),

    # ── Food hints embedded in UPIOUT narration path ──────────────────────────
    (re.compile(r"/ice.?cream|/kulfi|/dessert|/gelato", re.I), "Dining Out"),
    (re.compile(r"/frui|/vegetable|/sabji|/veggies", re.I), "Groceries"),

    # ── Porter logistics / delivery app ──────────────────────────────────────
    (re.compile(r"/porter/|porter.*delivery|porter.*logis", re.I), "Transport"),

    # ── Unknown merchant fallback ────────────────────────────────────────────
    (re.compile(r"unknown\s*merchant", re.I), "Transfers"),

    # ── Named personal VPAs seen in this dataset ──────────────────────────────
    (re.compile(
        r"santosh1308|selvarani\d|sundarsindhu|shivaranjini|sandyrocks"
        r"|rohitak\d|vnnalini|lovelysuri|abdulmutalib|jayaramavs|abhirajsanu"
        r"|aafiyamehza|dvalli\d|sree\.rama\d|xj77@paytm",
        re.I), "Transfers"),

    # ── Phone-number UPI IDs (10-digit Indian mobile number before @) ─────────
    (re.compile(r"upiout.*?/\d{9,12}-?\d*@", re.I), "Transfers"),

    # ── Generic personal bank VPA handles: ybl/ibl/nyes/fam are rarely business
    (re.compile(r"upiout.*?/[a-z0-9][a-zA-Z0-9._-]{2,}@(ybl|ibl|nyes|fam)\b", re.I), "Transfers"),

    # ── Personal name+number VPAs on okaxis/oksbi/okhdfcb/okicici handles ─────
    (re.compile(r"upiout.*?/[a-z0-9][a-zA-Z0-9._-]*\d{2,}[a-zA-Z0-9._-]*@(okhdfcb|okaxis|oksbi|okicici)\b", re.I), "Transfers"),
]


def _apply_rules(description: str) -> tuple[str, float] | None:
    """
    Try to categorise a transaction using rules only.
    Returns (category, confidence) or None if no rule matches.

    Priority:
      1. VPA / keyword pattern rules (regex)
      2. MCC code embedded at end of UPIOUT narration
    """
    raw = str(description).replace("\n", " ").strip()
    lower = raw.lower()

    # --- 1. Keyword / VPA rules (highest specificity) -------------------------
    for pattern, category in _RULES:
        if pattern.search(lower):
            return (category, 0.90)

    # --- 2. MCC code from UPIOUT narrations -----------------------------------
    # Format: .../<VPA>/<anything>/NNNN  where NNNN is 4-digit MCC
    mcc_match = re.search(r"/(\d{4})\s*$", raw.replace("\n", " "))
    if mcc_match:
        mcc = mcc_match.group(1)
        cat = MCC_CATEGORY.get(mcc)
        if cat:
            return (cat, 0.85)

    return None


# ── ML pipeline ───────────────────────────────────────────────────────────────

def build_pipeline() -> Pipeline:
    return Pipeline([
        ("tfidf", TfidfVectorizer(
            preprocessor=clean, analyzer="char_wb",
            ngram_range=(2, 5), min_df=2, sublinear_tf=True,
        )),
        ("clf", LogisticRegression(max_iter=3000, C=8)),
    ])


def train(training_csv) -> dict:
    df = pd.read_csv(training_csv)
    if CORRECTIONS_CSV.exists():
        corr = pd.read_csv(CORRECTIONS_CSV)[["description", "category"]]
        df = pd.concat([df, corr, corr, corr])
    X_tr, X_te, y_tr, y_te = train_test_split(
        df["description"], df["category"], test_size=0.2, random_state=0, stratify=df["category"],
    )
    pipe = build_pipeline().fit(X_tr, y_tr)
    pred = pipe.predict(X_te)
    report = {
        "accuracy": round(accuracy_score(y_te, pred), 4),
        "n_train": len(X_tr), "n_test": len(X_te),
        "per_class": {k: round(v["f1-score"], 3) for k, v in
                      classification_report(y_te, pred, output_dict=True).items()
                      if k not in ("accuracy", "macro avg", "weighted avg")},
    }
    pipe.fit(df["description"], df["category"])
    joblib.dump(pipe, MODEL_PATH)
    MODEL_REPORT.write_text(json.dumps(report, indent=2))
    return report


def _corrections() -> dict:
    if not CORRECTIONS_CSV.exists():
        return {}
    c = pd.read_csv(CORRECTIONS_CSV)
    return {merchant_key(d): cat for d, cat in zip(c["description"], c["category"])}


# ── main categorize function ──────────────────────────────────────────────────

def categorize(df: pd.DataFrame) -> pd.DataFrame:
    """
    Categorise every transaction using the layered pipeline:
      rules → ML model → confidence gate → user corrections → income override.
    """
    if not MODEL_PATH.exists():
        raise SystemExit("No model yet. Run:  python -m spendwise train")

    pipe = joblib.load(MODEL_PATH)
    df   = df.copy()

    # ── Step 1: Run ML model on all transactions ───────────────────────────────
    proba   = pipe.predict_proba(df["description"])
    classes = pipe.classes_
    df["category"]   = classes[proba.argmax(1)]
    df["confidence"] = proba.max(1).round(3)
    df["source"]     = "model"
    df.loc[df["confidence"] < CONFIDENCE_THRESHOLD, "category"] = "Uncategorized"

    # ── Step 2: Override with rule-based classifier where ML was uncertain ──────
    # Rules apply to ALL transactions, not just uncategorized ones, so a known
    # MCC or VPA always wins over a low-confidence ML prediction.
    rule_mask = (df["category"] == "Uncategorized") | (df["confidence"] < 0.65)
    for idx in df.index[rule_mask]:
        result = _apply_rules(df.at[idx, "description"])
        if result:
            cat, conf = result
            df.at[idx, "category"]   = cat
            df.at[idx, "confidence"] = conf
            df.at[idx, "source"]     = "rule"

    # ── Step 3: User corrections (highest priority — always wins) ──────────────
    overrides = _corrections()
    if overrides:
        keys = df["description"].map(merchant_key)
        hit  = keys.isin(overrides)
        df.loc[hit, "category"]   = keys[hit].map(overrides)
        df.loc[hit, ["confidence", "source"]] = [1.0, "user_rule"]

    # ── Step 4: Credits are always Income ─────────────────────────────────────
    df.loc[df["direction"] == "credit", ["category", "confidence", "source"]] = ["Income", 1.0, "rule"]

    return df


def add_correction(description: str, category: str, predicted: str):
    row = pd.DataFrame([{"description": description, "category": category, "predicted": predicted}])
    row.to_csv(CORRECTIONS_CSV, mode="a", header=not CORRECTIONS_CSV.exists(), index=False)
