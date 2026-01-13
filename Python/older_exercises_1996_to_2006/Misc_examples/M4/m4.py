import pandas as pd
import numpy as np
import sys
sys.path.append('../../../')
from meps_utils import load_sas_data

data_path = '../../../data'

print("=" * 80)
print("AHRQ MEPS DATA USERS WORKSHOP -- JULY 2006")
print("COMPUTING NUMBER OF EVENTS ASSOCIATED WITH CONDITIONS")
print("=" * 80)

evnum_labels = {
    0: '0',
    '1-10': '1-10',
    '11-25': '11-25',
    '26-50': '26-50',
    '51+': '51+'
}

def categorize_evnum(x):
    if x == 0:
        return '0'
    elif 1 <= x <= 10:
        return '1-10'
    elif 11 <= x <= 25:
        return '11-25'
    elif 26 <= x <= 50:
        return '26-50'
    else:
        return '51+'

print("\n" + "-" * 80)
print("Method 1: Using evNUM Variables from Conditions File")
print("-" * 80)

cond = load_sas_data(f'{data_path}/h78.sas7bdat', columns=[
    'CONDIDX', 'ERNUM', 'HHNUM', 'IPNUM', 'OBNUM', 'OPNUM', 'RXNUM'
])

cond['TOTNUM'] = cond['ERNUM'] + cond['HHNUM'] + cond['IPNUM'] + cond['OBNUM'] + cond['OPNUM'] + cond['RXNUM']

print(f"\nTotal conditions: {len(cond):,}")

print("\nTotal Events per Condition (from evNUM variables):")
cond['TOTNUM_CAT'] = cond['TOTNUM'].apply(categorize_evnum)
print(cond['TOTNUM_CAT'].value_counts().sort_index())

print("\n" + "-" * 80)
print("Method 2: Using CLNK File Matches")
print("-" * 80)

clnk = load_sas_data(f'{data_path}/h77i1.sas7bdat', columns=[
    'CONDIDX', 'EVENTYPE'
])

clnk_sorted = clnk.sort_values('CONDIDX')

eventype_map = {1: 'OB', 2: 'OP', 3: 'ER', 4: 'IP', 7: 'HH', 8: 'RX'}

cond_cnt = clnk.groupby('CONDIDX').apply(
    lambda x: pd.Series({
        'ERCNT': (x['EVENTYPE'] == 3).sum(),
        'HHCNT': (x['EVENTYPE'] == 7).sum(),
        'IPCNT': (x['EVENTYPE'] == 4).sum(),
        'OBCNT': (x['EVENTYPE'] == 1).sum(),
        'OPCNT': (x['EVENTYPE'] == 2).sum(),
        'RXCNT': (x['EVENTYPE'] == 8).sum()
    })
).reset_index()

cond_cnt['TOTCNT'] = cond_cnt['ERCNT'] + cond_cnt['HHCNT'] + cond_cnt['IPCNT'] + cond_cnt['OBCNT'] + cond_cnt['OPCNT'] + cond_cnt['RXCNT']

print(f"\nConditions with events in CLNK: {len(cond_cnt):,}")

print("\nTotal Events per Condition (from CLNK matches):")
cond_cnt['TOTCNT_CAT'] = cond_cnt['TOTCNT'].apply(categorize_evnum)
print(cond_cnt['TOTCNT_CAT'].value_counts().sort_index())

print("\n" + "-" * 80)
print("Comparison: evNUM vs CLNK Counts")
print("-" * 80)

cond_merged = cond.merge(cond_cnt, on='CONDIDX', how='outer')

for col in ['ERCNT', 'HHCNT', 'IPCNT', 'OBCNT', 'OPCNT', 'RXCNT', 'TOTCNT']:
    cond_merged[col] = cond_merged[col].fillna(0).astype(int)

both = len(cond_merged[(cond_merged['TOTNUM'].notna()) & (cond_merged['TOTCNT'] > 0)])
justa = len(cond_merged[(cond_merged['TOTNUM'].notna()) & (cond_merged['TOTCNT'] == 0)])
justb = len(cond_merged[(cond_merged['TOTNUM'].isna()) & (cond_merged['TOTCNT'] > 0)])

print(f"\nConditions in both files: {both:,}")
print(f"Conditions only in COND file (no events): {justa:,}")
print(f"Conditions only in CLNK file: {justb:,}")

pct_with_events = (both / len(cond) * 100) if len(cond) > 0 else 0
print(f"\nPercent of conditions with events: {pct_with_events:.1f}%")

print("\n" + "-" * 80)
print("Cross-tabulation: TOTNUM vs TOTCNT")
print("-" * 80)

cond_merged['TOTNUM_CAT'] = cond_merged['TOTNUM'].apply(lambda x: categorize_evnum(x) if pd.notna(x) else 'Missing')
cond_merged['TOTCNT_CAT'] = cond_merged['TOTCNT'].apply(categorize_evnum)

crosstab = pd.crosstab(cond_merged['TOTNUM_CAT'], cond_merged['TOTCNT_CAT'], margins=True)
print(crosstab.to_string())
