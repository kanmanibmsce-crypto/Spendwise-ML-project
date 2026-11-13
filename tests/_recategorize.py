"""Re-run categorization on stored transactions and report improvement."""
import sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
os.chdir(r"C:\Users\meeting\Spendwise-ML project")
sys.path.insert(0, r"C:\Users\meeting\Spendwise-ML project")

import pandas as pd
from spendwise.data import load_store, save_store
from spendwise import categorizer

# Load existing store
df = load_store()
print(f"Loaded {len(df)} transactions")

before_unc = (df["category"] == "Uncategorized").sum()
print(f"Uncategorized before: {before_unc} ({before_unc/len(df)*100:.1f}%)")

# Strip old category columns and re-run
raw = df.drop(columns=["category", "confidence", "source"], errors="ignore")
df_new = categorizer.categorize(raw)

after_unc = (df_new["category"] == "Uncategorized").sum()
print(f"Uncategorized after : {after_unc} ({after_unc/len(df_new)*100:.1f}%)")
print(f"Improvement         : {before_unc - after_unc} fewer uncategorized")
print()
print("New category distribution:")
print(df_new["category"].value_counts().to_string())

print()
print("Source breakdown:")
print(df_new["source"].value_counts().to_string())

# Save back
save_store(df_new, append=False)
print("\nStore updated.")
