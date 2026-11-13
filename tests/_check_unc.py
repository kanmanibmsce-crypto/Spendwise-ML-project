import sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
os.chdir(r"C:\Users\meeting\Spendwise-ML project")
import pandas as pd
sys.path.insert(0, r"C:\Users\meeting\Spendwise-ML project")

df = pd.read_csv(r"C:\Users\meeting\Spendwise-ML project\.spendwise\transactions.csv")
unc = df[df["category"] == "Uncategorized"]

print(f"Total transactions : {len(df)}")
print(f"Uncategorized      : {len(unc)}  ({len(unc)/len(df)*100:.1f}%)")
print(f"\nCategory distribution:")
print(df["category"].value_counts().to_string())
print(f"\nAll uncategorized descriptions ({len(unc)}):")
for i, row in unc.iterrows():
    print(f"  [{row.get('confidence','?'):.2f}]  {row['description']}")
