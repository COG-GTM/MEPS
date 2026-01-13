import pandas as pd
import numpy as np
import sys
sys.path.append('../../../')
from meps_utils import load_sas_data

data_path = '../../../data'

print("=" * 80)
print("AHRQ MEPS DATA USERS WORKSHOP (LINKING) -- NOV/DEC 2004")
print("NHIS-MEPS Link")
print("=" * 80)

anylim_labels = {-9: 'Not Ascer', -1: 'Inapp', 1: 'Yes', 2: 'No'}
sex_labels = {1: 'Male', 2: 'Female'}
hstat_labels = {
    -9: 'Not Ascer', -8: 'DK', -7: 'Refused', -1: 'Inapp',
    1: 'Excellent', 2: 'Very Good', 3: 'Good', 4: 'Fair', 5: 'Poor',
    7: 'Refused', 8: 'Not Ascer', 9: 'DK'
}
nhislim_labels = {
    1: 'Limited', 2: 'Not Limited', 3: 'Unknown',
    7: 'Refused', 8: 'Not Ascer', 9: 'DK'
}
nhischron_labels = {
    0: 'Not Limited', 1: 'Lim, 1+ Chron Cond', 2: 'Lim, Not Chron',
    3: 'Lim, Chron Unk', 7: 'Refused', 8: 'Not Ascer', 9: 'DK'
}

print("\n" + "-" * 80)
print("2001 MEPS")
print("-" * 80)

meps01 = load_sas_data(f'{data_path}/h60.sas7bdat', columns=[
    'DUPERSID', 'ANYLIM01', 'RTHLTH31', 'RTHLTH42', 'RTHLTH53',
    'PERWT01F', 'VARSTR01', 'VARPSU01'
])

def get_meps_hstat(row):
    if row['RTHLTH53'] > 0:
        return row['RTHLTH53']
    elif row['RTHLTH42'] > 0:
        return row['RTHLTH42']
    elif row['RTHLTH31'] > 0:
        return row['RTHLTH31']
    return np.nan

meps01['MEPSHSTAT'] = meps01.apply(get_meps_hstat, axis=1)

print(f"\nNumber of MEPS 2001 records: {len(meps01):,}")

print("\nMEPS Health Status Distribution:")
for val in [1, 2, 3, 4, 5]:
    count = len(meps01[meps01['MEPSHSTAT'] == val])
    if count > 0:
        print(f"  {hstat_labels.get(val, str(val))}: {count:,}")

print("\n" + "-" * 80)
print("Note: This example requires NHIS-MEPS link files which are not")
print("included in the standard MEPS public use files.")
print("-" * 80)

print("\nThe original SAS code demonstrates how to:")
print("1. Read NHIS person files (1999, 2000)")
print("2. Read NHIS-MEPS link file")
print("3. Merge MEPS data with NHIS data using link file")
print("4. Compare health status and limitation status between surveys")

print("\n" + "-" * 80)
print("MEPS Variables Available for Analysis")
print("-" * 80)

print("\nAny Limitation (ANYLIM01) Distribution:")
for val in [-9, -1, 1, 2]:
    count = len(meps01[meps01['ANYLIM01'] == val])
    if count > 0:
        print(f"  {anylim_labels.get(val, str(val))}: {count:,}")

print("\n" + "-" * 80)
print("Weighted Analysis")
print("-" * 80)

meps01_valid = meps01[meps01['PERWT01F'] > 0].copy()

total_weight = meps01_valid['PERWT01F'].sum()
print(f"\nTotal weighted population: {total_weight:,.0f}")

print("\nWeighted Health Status Distribution:")
for val in [1, 2, 3, 4, 5]:
    subset = meps01_valid[meps01_valid['MEPSHSTAT'] == val]
    weight = subset['PERWT01F'].sum()
    pct = (weight / total_weight * 100) if total_weight > 0 else 0
    print(f"  {hstat_labels.get(val, str(val))}: {weight:,.0f} ({pct:.1f}%)")
