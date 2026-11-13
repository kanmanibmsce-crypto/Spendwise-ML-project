import sys, io, pandas as pd, numpy as np
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import os; os.chdir(r"C:\Users\meeting\Spendwise-ML project")

df = pd.read_csv(r'.spendwise\transactions.csv', parse_dates=['date'])
expenses = df[df['direction']=='debit']
income   = df[df['direction']=='credit']
df['month'] = df['date'].dt.to_period('M')
expenses = expenses.copy()
expenses['month'] = expenses['date'].dt.to_period('M')
monthly_exp = expenses.groupby('month')['amount'].sum().sort_index()

print('=== BASIC ===')
print(f'Total txns: {len(df)}')
print(f'Expense txns: {len(expenses)}')
print(f'Income txns: {len(income)}')
print(f'Date range: {df.date.min().date()} to {df.date.max().date()}')
print(f'Months: {df["month"].nunique()}')
print(f'Total spend: {expenses.amount.sum():,.0f}')
print(f'Total income: {income.amount.sum():,.0f}')
unc = (df['category']=='Uncategorized').sum()
print(f'Uncategorized: {unc}')

print('\n=== LAST MONTH ===')
last_m = monthly_exp.index[-1]
last_exp = expenses[expenses['month']==last_m]
print(f'Month: {last_m}')
print(f'Spend: {last_exp.amount.sum():,.0f}')
print(f'Txns: {len(last_exp)}')
avg = last_exp.amount.mean()
print(f'Avg: {avg:,.0f}')

prev_m = monthly_exp.index[-2]
prev_exp = expenses[expenses['month']==prev_m]
pct_change = (last_exp.amount.sum()-prev_exp.amount.sum())/prev_exp.amount.sum()*100
print(f'Prev month ({prev_m}): {prev_exp.amount.sum():,.0f}')
print(f'MoM change: {pct_change:+.1f}%')

print('\n=== MONTHLY EXPENSES ===')
for m, v in monthly_exp.items():
    print(f'  {m}: {v:,.0f}')

print('\n=== CATEGORY DIST (expenses) ===')
cd = expenses.groupby('category')['amount'].agg(['sum','count']).sort_values('sum',ascending=False)
total_spend = expenses['amount'].sum()
for cat,(s,c) in cd.iterrows():
    print(f'  {cat}: {s:,.0f} ({c} txns, {s/total_spend*100:.1f}%)')

print('\n=== TOP 5 CATEGORIES BY COUNT ===')
top5 = expenses['category'].value_counts().head(5)
for cat,cnt in top5.items():
    print(f'  {cat}: {cnt} txns')

print('\n=== SOURCES ===')
if 'source' in df.columns:
    print(df['source'].value_counts().to_string())

print('\n=== CORRECTIONS ===')
import os
cf = r'.spendwise\corrections.csv'
if os.path.exists(cf):
    corr = pd.read_csv(cf)
    print(f'Corrections saved: {len(corr)}')
else:
    print('No corrections file')
