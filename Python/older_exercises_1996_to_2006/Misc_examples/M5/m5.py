import pandas as pd
import numpy as np
import sys
sys.path.append('../../../')
from meps_utils import load_sas_data

data_path = '../../../data'

print("=" * 80)
print("AHRQ MEPS DATA USERS WORKSHOP -- SEPTEMBER 2008")
print("TWO DIFFERENT SETS OF PRIORITY CONDITIONS")
print("=" * 80)

icd9_labels = {
    '250': 'DIABETES MELLITUS',
    '401': 'ESSENTIAL HYPERTENSION',
    '492': 'EMPHYSEMA',
    '493': 'ASTHMA'
}

yesno_labels = {-1: 'INAPPLICABLE', 0: 'NO', 1: 'YES'}
prio_labels = {1: 'YES', 2: 'NO'}

print("\n" + "-" * 80)
print("Variables from 2005 Conditions File")
print("-" * 80)

cond = load_sas_data(f'{data_path}/h96.sas7bdat', columns=[
    'DUPERSID', 'CONDIDX', 'ICD9CODX', 'PRIOLIST'
])

cond_priority = cond[cond['ICD9CODX'].isin(['250', '401', '492', '493'])].copy()

print(f"\nTotal priority condition records: {len(cond_priority):,}")

print("\nCondition Level - ICD9 Code Distribution:")
for icd9 in ['250', '401', '492', '493']:
    count = len(cond_priority[cond_priority['ICD9CODX'] == icd9])
    print(f"  {icd9} ({icd9_labels[icd9]}): {count:,}")

print("\nCondition Level - ICD9 by PRIOLIST:")
crosstab = pd.crosstab(cond_priority['ICD9CODX'], cond_priority['PRIOLIST'])
print(crosstab.to_string())

cond_sorted = cond_priority.sort_values('DUPERSID')

condpers = cond_sorted.groupby('DUPERSID').apply(
    lambda x: pd.Series({
        'C_DIABETES': 1 if (x['ICD9CODX'] == '250').any() else 0,
        'C_HYPERTENSION': 1 if (x['ICD9CODX'] == '401').any() else 0,
        'C_EMPHYSEMA': 1 if (x['ICD9CODX'] == '492').any() else 0,
        'C_ASTHMA': 1 if (x['ICD9CODX'] == '493').any() else 0
    })
).reset_index()

print("\n" + "-" * 80)
print("Variables from 2005 Conditions File - Person Level")
print("-" * 80)

for var in ['C_DIABETES', 'C_ASTHMA', 'C_HYPERTENSION', 'C_EMPHYSEMA']:
    count_yes = (condpers[var] == 1).sum()
    count_no = (condpers[var] == 0).sum()
    print(f"\n{var}:")
    print(f"  Yes: {count_yes:,}")
    print(f"  No: {count_no:,}")

print("\n" + "-" * 80)
print("Variables from 2005 Full-Year File")
print("-" * 80)

fyc = load_sas_data(f'{data_path}/h97.sas7bdat', columns=[
    'DUPERSID', 'DIABDX53', 'ASTHDX53', 'HIBPDX53', 'EMPHDX53',
    'VARPSU', 'VARSTR', 'PERWT05F'
])

fyc = fyc.rename(columns={
    'DIABDX53': 'PC_DIABETES',
    'ASTHDX53': 'PC_ASTHMA',
    'HIBPDX53': 'PC_HYPERTENSION',
    'EMPHDX53': 'PC_EMPHYSEMA'
})

for col in ['PC_DIABETES', 'PC_ASTHMA', 'PC_HYPERTENSION', 'PC_EMPHYSEMA']:
    fyc[col] = fyc[col].apply(lambda x: 0 if x == 2 or x < -1 else (1 if x == 1 else 0))

print("\nPerson Level - Priority Condition Questions from Full-Year File:")
for var in ['PC_DIABETES', 'PC_ASTHMA', 'PC_HYPERTENSION', 'PC_EMPHYSEMA']:
    count_yes = (fyc[var] == 1).sum()
    count_no = (fyc[var] == 0).sum()
    print(f"\n{var}:")
    print(f"  Yes: {count_yes:,}")
    print(f"  No: {count_no:,}")

print("\n" + "-" * 80)
print("Comparison: Conditions File vs Full-Year File")
print("-" * 80)

fycond = fyc.merge(condpers, on='DUPERSID', how='left')

for col in ['C_DIABETES', 'C_HYPERTENSION', 'C_EMPHYSEMA', 'C_ASTHMA']:
    fycond[col] = fycond[col].fillna(0).astype(int)

both = len(fycond[(fycond['C_DIABETES'].notna())])
print(f"\nTotal persons in merged file: {len(fycond):,}")

comparisons = [
    ('C_DIABETES', 'PC_DIABETES', 'Diabetes'),
    ('C_ASTHMA', 'PC_ASTHMA', 'Asthma'),
    ('C_HYPERTENSION', 'PC_HYPERTENSION', 'Hypertension'),
    ('C_EMPHYSEMA', 'PC_EMPHYSEMA', 'Emphysema')
]

for c_var, pc_var, label in comparisons:
    print(f"\n{label}:")
    crosstab = pd.crosstab(fycond[c_var], fycond[pc_var], margins=True)
    crosstab.index = ['No (COND)', 'Yes (COND)', 'All']
    crosstab.columns = ['No (FY)', 'Yes (FY)', 'All']
    print(crosstab.to_string())
