import pandas as pd
import numpy as np
import sys
sys.path.append('../../../')
from meps_utils import load_sas_data, SurveyDesign, survey_freq

data_path = '../../../data'

print("=" * 80)
print("AHRQ MEPS DATA USERS WORKSHOP -- SEPTEMBER 2008")
print("DIABETES CARE SUPPLEMENT ESTIMATES")
print("=" * 80)

a1c_labels = {
    -9: 'NOT ASCERTAINED',
    -8: 'DK',
    -1: 'INAPPLICABLE'
}

ins_labels = {
    -9: 'NOT ASCERTAINED',
    -8: 'DK',
    -1: 'INAPPLICABLE',
    0: 'NO',
    1: 'YES'
}

fyc = load_sas_data(f'{data_path}/h97.sas7bdat', columns=[
    'DUPERSID', 'DIABW05F', 'VARSTR', 'VARPSU',
    'DSA1C53', 'DSINSU53'
])

fyc_valid = fyc[fyc['DIABW05F'] > 0].copy()

print(f"\nPersons with positive diabetes care weight: {len(fyc_valid):,}")

print("\n" + "-" * 80)
print("DSA1C53 - Number of Times Tested for Hemoglobin A1c")
print("-" * 80)

def categorize_a1c(x):
    if x == -9:
        return 'NOT ASCERTAINED'
    elif x == -8:
        return 'DK'
    elif x == -1:
        return 'INAPPLICABLE'
    elif 1 <= x <= 20:
        return '1-20 TIMES'
    elif 21 <= x <= 50:
        return '21-50 TIMES'
    elif x > 50:
        return '51 TIMES OR MORE'
    else:
        return 'OTHER'

fyc_valid['DSA1C53_CAT'] = fyc_valid['DSA1C53'].apply(categorize_a1c)

design = SurveyDesign(fyc_valid, strata='VARSTR', cluster='VARPSU', weight='DIABW05F')

total_weight = fyc_valid['DIABW05F'].sum()

print("\nFrequency Distribution:")
for cat in ['INAPPLICABLE', 'NOT ASCERTAINED', 'DK', '1-20 TIMES', '21-50 TIMES', '51 TIMES OR MORE']:
    subset = fyc_valid[fyc_valid['DSA1C53_CAT'] == cat]
    n = len(subset)
    weight = subset['DIABW05F'].sum()
    pct = (weight / total_weight * 100) if total_weight > 0 else 0
    if n > 0:
        print(f"  {cat}: n={n:,}, {pct:.1f}%")

print("\n" + "-" * 80)
print("DSINSU53 - Diabetes Treated with Insulin Injections")
print("-" * 80)

def categorize_insulin(x):
    if x == -9:
        return 'NOT ASCERTAINED'
    elif x == -8:
        return 'DK'
    elif x == -1:
        return 'INAPPLICABLE'
    elif x == 0:
        return 'NO'
    elif x == 1:
        return 'YES'
    else:
        return 'OTHER'

fyc_valid['DSINSU53_CAT'] = fyc_valid['DSINSU53'].apply(categorize_insulin)

print("\nFrequency Distribution:")
for cat in ['INAPPLICABLE', 'NOT ASCERTAINED', 'DK', 'NO', 'YES']:
    subset = fyc_valid[fyc_valid['DSINSU53_CAT'] == cat]
    n = len(subset)
    weight = subset['DIABW05F'].sum()
    pct = (weight / total_weight * 100) if total_weight > 0 else 0
    if n > 0:
        print(f"  {cat}: n={n:,}, {pct:.1f}%")

print("\n" + "-" * 80)
print("Note: These estimates use the Diabetes Care Supplement weight (DIABW05F)")
print("which is appropriate for analyses using questions from the DCS.")
print("-" * 80)
