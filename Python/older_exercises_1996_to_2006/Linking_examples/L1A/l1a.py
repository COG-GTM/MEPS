import pandas as pd
import numpy as np
import sys
sys.path.append('../../../')
from meps_utils import load_sas_data

data_path = '../../../data'

print("=" * 80)
print("AHRQ MEPS DATA USERS WORKSHOP (LINKING) -- NOV/DEC 2004")
print("Link 2000 and 2001 JOBS Files")
print("=" * 80)

yn_labels = {
    -9: 'Not Asc',
    -8: 'DK',
    -7: 'Refused',
    -1: 'Inappl',
    1: 'Yes',
    2: 'No'
}

jobs00 = load_sas_data(f'{data_path}/h40.sas7bdat', columns=[
    'DUPERSID', 'PANEL', 'RN', 'JOBSN', 'SUBTYPE', 'STILLAT',
    'SICKPAY', 'PAYDRVST', 'PAYVACTN'
])

jobs01 = load_sas_data(f'{data_path}/h56.sas7bdat', columns=[
    'DUPERSID', 'PANEL', 'RN', 'JOBSN', 'SUBTYPE', 'STILLAT',
    'SICKPAY', 'PAYDRVST', 'PAYVACTN'
])

print("\n" + "-" * 80)
print("2001 Current Main Jobs that Began in 2000")
print("-" * 80)

cmj01 = jobs01[
    (jobs01['PANEL'] == 5) & 
    (jobs01['RN'] == 3) & 
    (jobs01['SUBTYPE'] == 1) & 
    (jobs01['STILLAT'] == 1)
].copy()

print(f"\n2001 (Panel 5 Round 3) Records: {len(cmj01):,}")

print("\nJob Benefits Distribution (2001 Records):")
for var in ['SICKPAY', 'PAYDRVST', 'PAYVACTN']:
    print(f"\n  {var}:")
    for val in [-9, -8, -7, -1, 1, 2]:
        count = len(cmj01[cmj01[var] == val])
        if count > 0:
            print(f"    {yn_labels.get(val, str(val))}: {count:,}")

cmj00 = jobs00[
    (jobs00['PANEL'] == 5) & 
    (jobs00['RN'].isin([1, 2])) & 
    (jobs00['SUBTYPE'] == 1) & 
    (jobs00['STILLAT'] == -1)
].copy()

print(f"\n2000 (Panel 5 Round 1,2) Records: {len(cmj00):,}")

print("\nJob Benefits Distribution (2000 Records):")
for var in ['SICKPAY', 'PAYDRVST', 'PAYVACTN']:
    print(f"\n  {var}:")
    for val in [-9, -8, -7, -1, 1, 2]:
        count = len(cmj00[cmj00[var] == val])
        if count > 0:
            print(f"    {yn_labels.get(val, str(val))}: {count:,}")

cmj00_renamed = cmj00[['DUPERSID', 'JOBSN', 'SICKPAY', 'PAYDRVST', 'PAYVACTN']].copy()
cmj00_renamed = cmj00_renamed.rename(columns={
    'SICKPAY': 'SICKPAYX',
    'PAYDRVST': 'PAYDRVSTX',
    'PAYVACTN': 'PAYVACTNX'
})

new = cmj01.merge(cmj00_renamed, on=['DUPERSID', 'JOBSN'], how='inner')

print("\n" + "-" * 80)
print("Merged Records (Jobs in Both 2000 and 2001)")
print("-" * 80)

print(f"\nNumber of matched records: {len(new):,}")

print("\nComparison of 2000 vs 2001 Values:")

for var_01, var_00 in [('SICKPAY', 'SICKPAYX'), ('PAYDRVST', 'PAYDRVSTX'), ('PAYVACTN', 'PAYVACTNX')]:
    print(f"\n{var_00} (2000) vs {var_01} (2001):")
    crosstab = pd.crosstab(new[var_00], new[var_01], margins=True)
    print(crosstab.to_string())
